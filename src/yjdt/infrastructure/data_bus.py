# -*- coding: utf-8 -*-
"""
统一数据总线 - Unified Data Bus

功能：
- 标准化信号格式
- 事件驱动通信
- 发布-订阅模式
- 数据溯源和审计
- 时间同步
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime
from enum import Enum
from collections import deque
import threading
import uuid
import time


class SignalQuality(Enum):
    """信号质量"""
    GOOD = 0            # 正常
    UNCERTAIN = 1       # 不确定
    BAD = 2             # 坏值
    STALE = 3           # 过期
    SIMULATED = 4       # 模拟值


class EventType(Enum):
    """事件类型"""
    # 状态事件
    STATE_UPDATED = "state_updated"
    STATE_CHANGED = "state_changed"

    # 告警事件
    ALARM_RAISED = "alarm_raised"
    ALARM_CLEARED = "alarm_cleared"
    ALARM_ACKNOWLEDGED = "alarm_acknowledged"

    # 故障事件
    FAULT_DETECTED = "fault_detected"
    FAULT_CLEARED = "fault_cleared"
    FAULT_ISOLATED = "fault_isolated"

    # 控制事件
    COMMAND_ISSUED = "command_issued"
    COMMAND_EXECUTED = "command_executed"
    COMMAND_FAILED = "command_failed"

    # 系统事件
    MODULE_STARTED = "module_started"
    MODULE_STOPPED = "module_stopped"
    CONFIG_CHANGED = "config_changed"

    # 诊断事件
    DIAGNOSIS_COMPLETED = "diagnosis_completed"
    PREDICTION_UPDATED = "prediction_updated"

    # 用户事件
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_ACTION = "user_action"


class Priority(Enum):
    """优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Signal:
    """
    标准化信号格式

    包含值、时间戳、质量和元数据
    """
    name: str
    value: Any
    timestamp: datetime
    quality: SignalQuality = SignalQuality.GOOD
    unit: str = ""
    source: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    # 溯源信息
    trace_id: str = ""
    parent_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "quality": self.quality.value,
            "unit": self.unit,
            "source": self.source,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Signal':
        return cls(
            name=data["name"],
            value=data["value"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            quality=SignalQuality(data.get("quality", 0)),
            unit=data.get("unit", ""),
            source=data.get("source", ""),
            tags=data.get("tags", {}),
        )


@dataclass
class Event:
    """
    标准化事件格式

    用于模块间异步通信
    """
    event_id: str
    event_type: EventType
    timestamp: datetime
    source: str
    payload: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    correlation_id: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "payload": self.payload,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "tags": self.tags,
        }


@dataclass
class Subscription:
    """订阅"""
    subscription_id: str
    subscriber: str
    event_types: Set[EventType]
    callback: Callable[[Event], None]
    filter_tags: Dict[str, str] = field(default_factory=dict)
    priority_filter: Optional[Priority] = None
    created_at: datetime = field(default_factory=datetime.now)


class DataBus:
    """
    统一数据总线

    实现发布-订阅模式的模块间通信
    """

    def __init__(self, buffer_size: int = 10000):
        # 信号存储
        self._signals: Dict[str, Signal] = {}
        self._signal_history: Dict[str, deque] = {}
        self._history_size = 1000

        # 事件队列
        self._event_queue: deque = deque(maxlen=buffer_size)
        self._event_history: deque = deque(maxlen=buffer_size)

        # 订阅管理
        self._subscriptions: Dict[str, Subscription] = {}
        self._event_subscribers: Dict[EventType, List[str]] = {}

        # 时间同步
        self._time_offset = 0.0  # 与参考时间的偏移
        self._reference_time: Optional[datetime] = None

        # 统计
        self._stats = {
            "signals_published": 0,
            "events_published": 0,
            "events_delivered": 0,
            "errors": 0,
        }

        # 线程安全
        self._lock = threading.RLock()
        self._event_lock = threading.Lock()

        # 后台处理
        self._running = False
        self._processor_thread: Optional[threading.Thread] = None

    def start(self):
        """启动数据总线"""
        self._running = True
        self._processor_thread = threading.Thread(
            target=self._process_events,
            daemon=True
        )
        self._processor_thread.start()

    def stop(self):
        """停止数据总线"""
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=2.0)

    def publish_signal(self, signal: Signal):
        """
        发布信号

        Args:
            signal: 信号对象
        """
        with self._lock:
            # 添加溯源ID
            if not signal.trace_id:
                signal.trace_id = str(uuid.uuid4())

            # 存储当前值
            self._signals[signal.name] = signal

            # 添加到历史
            if signal.name not in self._signal_history:
                self._signal_history[signal.name] = deque(maxlen=self._history_size)
            self._signal_history[signal.name].append(signal)

            self._stats["signals_published"] += 1

    def publish_signals(self, signals: List[Signal]):
        """批量发布信号"""
        for signal in signals:
            self.publish_signal(signal)

    def get_signal(self, name: str) -> Optional[Signal]:
        """
        获取信号当前值

        Args:
            name: 信号名称

        Returns:
            信号对象或None
        """
        with self._lock:
            return self._signals.get(name)

    def get_signal_value(self, name: str, default: Any = None) -> Any:
        """获取信号值"""
        signal = self.get_signal(name)
        return signal.value if signal else default

    def get_signal_history(self, name: str,
                           limit: int = 100) -> List[Signal]:
        """
        获取信号历史

        Args:
            name: 信号名称
            limit: 返回数量限制

        Returns:
            历史信号列表
        """
        with self._lock:
            history = self._signal_history.get(name, deque())
            return list(history)[-limit:]

    def publish_event(self, event: Event):
        """
        发布事件

        Args:
            event: 事件对象
        """
        with self._event_lock:
            # 确保有ID
            if not event.event_id:
                event.event_id = str(uuid.uuid4())

            self._event_queue.append(event)
            self._stats["events_published"] += 1

    def create_event(self, event_type: EventType, source: str,
                     payload: Dict[str, Any],
                     priority: Priority = Priority.NORMAL) -> Event:
        """创建并发布事件"""
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=self.get_synchronized_time(),
            source=source,
            payload=payload,
            priority=priority,
        )
        self.publish_event(event)
        return event

    def subscribe(self, subscriber: str,
                  event_types: List[EventType],
                  callback: Callable[[Event], None],
                  filter_tags: Dict[str, str] = None) -> str:
        """
        订阅事件

        Args:
            subscriber: 订阅者标识
            event_types: 订阅的事件类型列表
            callback: 回调函数
            filter_tags: 过滤标签

        Returns:
            订阅ID
        """
        subscription_id = str(uuid.uuid4())

        subscription = Subscription(
            subscription_id=subscription_id,
            subscriber=subscriber,
            event_types=set(event_types),
            callback=callback,
            filter_tags=filter_tags or {},
        )

        with self._lock:
            self._subscriptions[subscription_id] = subscription

            # 更新事件类型索引
            for event_type in event_types:
                if event_type not in self._event_subscribers:
                    self._event_subscribers[event_type] = []
                self._event_subscribers[event_type].append(subscription_id)

        return subscription_id

    def unsubscribe(self, subscription_id: str):
        """取消订阅"""
        with self._lock:
            if subscription_id in self._subscriptions:
                subscription = self._subscriptions[subscription_id]

                # 从索引中移除
                for event_type in subscription.event_types:
                    if event_type in self._event_subscribers:
                        self._event_subscribers[event_type].remove(subscription_id)

                del self._subscriptions[subscription_id]

    def _process_events(self):
        """事件处理循环"""
        while self._running:
            try:
                with self._event_lock:
                    if self._event_queue:
                        event = self._event_queue.popleft()
                    else:
                        event = None

                if event:
                    self._dispatch_event(event)
                    self._event_history.append(event)
                else:
                    time.sleep(0.001)  # 1ms

            except Exception as e:
                self._stats["errors"] += 1

    def _dispatch_event(self, event: Event):
        """分发事件给订阅者"""
        subscriber_ids = self._event_subscribers.get(event.event_type, [])

        for sub_id in subscriber_ids:
            subscription = self._subscriptions.get(sub_id)
            if not subscription:
                continue

            # 检查过滤条件
            if not self._matches_filter(event, subscription):
                continue

            try:
                subscription.callback(event)
                self._stats["events_delivered"] += 1
            except Exception as e:
                self._stats["errors"] += 1

    def _matches_filter(self, event: Event, subscription: Subscription) -> bool:
        """检查事件是否匹配订阅过滤条件"""
        # 检查优先级
        if subscription.priority_filter is not None:
            if event.priority.value < subscription.priority_filter.value:
                return False

        # 检查标签
        for key, value in subscription.filter_tags.items():
            if event.tags.get(key) != value:
                return False

        return True

    def set_reference_time(self, reference_time: datetime):
        """设置参考时间"""
        self._reference_time = reference_time
        self._time_offset = (reference_time - datetime.now()).total_seconds()

    def get_synchronized_time(self) -> datetime:
        """获取同步时间"""
        if self._reference_time:
            return datetime.now() + timedelta(seconds=self._time_offset)
        return datetime.now()

    def get_all_signal_names(self) -> List[str]:
        """获取所有信号名称"""
        with self._lock:
            return list(self._signals.keys())

    def get_signals_by_source(self, source: str) -> List[Signal]:
        """按来源获取信号"""
        with self._lock:
            return [s for s in self._signals.values() if s.source == source]

    def get_signals_by_tag(self, tag_key: str, tag_value: str) -> List[Signal]:
        """按标签获取信号"""
        with self._lock:
            return [
                s for s in self._signals.values()
                if s.tags.get(tag_key) == tag_value
            ]

    def get_recent_events(self, event_type: EventType = None,
                          limit: int = 100) -> List[Event]:
        """获取最近的事件"""
        with self._event_lock:
            events = list(self._event_history)

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                **self._stats,
                "active_signals": len(self._signals),
                "active_subscriptions": len(self._subscriptions),
                "event_queue_size": len(self._event_queue),
                "event_history_size": len(self._event_history),
            }

    def clear_history(self):
        """清除历史数据"""
        with self._lock:
            for history in self._signal_history.values():
                history.clear()

        with self._event_lock:
            self._event_history.clear()

    def export_snapshot(self) -> Dict[str, Any]:
        """导出当前快照"""
        with self._lock:
            signals = {
                name: signal.to_dict()
                for name, signal in self._signals.items()
            }

        with self._event_lock:
            recent_events = [e.to_dict() for e in list(self._event_history)[-100:]]

        return {
            "timestamp": datetime.now().isoformat(),
            "signals": signals,
            "recent_events": recent_events,
            "statistics": self.get_statistics(),
        }


# 需要导入timedelta
from datetime import timedelta


class SignalAggregator:
    """
    信号聚合器

    用于计算统计值和派生信号
    """

    def __init__(self, data_bus: DataBus):
        self.data_bus = data_bus
        self.aggregations: Dict[str, Dict[str, Any]] = {}

    def add_aggregation(self, output_name: str,
                        input_signals: List[str],
                        aggregation_type: str,
                        window_size: int = 60):
        """
        添加聚合定义

        Args:
            output_name: 输出信号名
            input_signals: 输入信号列表
            aggregation_type: 聚合类型 (mean, max, min, sum, std)
            window_size: 窗口大小
        """
        self.aggregations[output_name] = {
            "inputs": input_signals,
            "type": aggregation_type,
            "window": window_size,
        }

    def compute(self) -> List[Signal]:
        """计算所有聚合"""
        results = []

        for output_name, config in self.aggregations.items():
            values = []
            for input_name in config["inputs"]:
                history = self.data_bus.get_signal_history(
                    input_name, config["window"]
                )
                values.extend([s.value for s in history if isinstance(s.value, (int, float))])

            if values:
                if config["type"] == "mean":
                    result = np.mean(values)
                elif config["type"] == "max":
                    result = np.max(values)
                elif config["type"] == "min":
                    result = np.min(values)
                elif config["type"] == "sum":
                    result = np.sum(values)
                elif config["type"] == "std":
                    result = np.std(values)
                else:
                    result = values[-1]

                signal = Signal(
                    name=output_name,
                    value=result,
                    timestamp=datetime.now(),
                    quality=SignalQuality.GOOD,
                    source="aggregator",
                    tags={"type": "derived"},
                )
                results.append(signal)
                self.data_bus.publish_signal(signal)

        return results


class EventCorrelator:
    """
    事件关联器

    用于识别相关事件和事件模式
    """

    def __init__(self, data_bus: DataBus, time_window: float = 60.0):
        self.data_bus = data_bus
        self.time_window = time_window  # 秒
        self.correlation_rules: List[Dict[str, Any]] = []

    def add_correlation_rule(self, name: str,
                             trigger_events: List[EventType],
                             condition: Callable[[List[Event]], bool],
                             action: Callable[[List[Event]], None]):
        """
        添加关联规则

        Args:
            name: 规则名称
            trigger_events: 触发事件类型
            condition: 条件判断函数
            action: 执行动作
        """
        self.correlation_rules.append({
            "name": name,
            "triggers": trigger_events,
            "condition": condition,
            "action": action,
        })

    def correlate(self, event: Event) -> List[Event]:
        """
        查找关联事件

        Args:
            event: 当前事件

        Returns:
            关联事件列表
        """
        recent_events = self.data_bus.get_recent_events(limit=1000)

        # 时间窗口过滤
        window_start = event.timestamp - timedelta(seconds=self.time_window)
        correlated = [
            e for e in recent_events
            if e.timestamp >= window_start and e.event_id != event.event_id
        ]

        # 检查关联规则
        for rule in self.correlation_rules:
            if event.event_type in rule["triggers"]:
                matching = [e for e in correlated if e.event_type in rule["triggers"]]
                if rule["condition"](matching):
                    rule["action"](matching)

        return correlated

