# -*- coding: utf-8 -*-
"""
报警管理系统 - 多级报警与智能处置
Alarm Management System - Multi-level Alarm and Intelligent Handling

功能：
- 四级报警分类（预警/一般/重要/紧急）
- 报警闪烁/确认/复位管理
- 报警升级与降级策略
- 报警抑制与屏蔽
- 报警统计与分析
- SOE事件顺序记录

对标DL/T 5003电力系统调度自动化标准
"""

import numpy as np
from enum import Enum, IntEnum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict
import threading


class AlarmLevel(IntEnum):
    """报警级别"""
    INFO = 0          # 提示信息
    WARNING = 1       # 预警（黄色）
    ALARM = 2         # 一般报警（橙色）
    CRITICAL = 3      # 重要报警（红色）
    EMERGENCY = 4     # 紧急报警（红色闪烁）


class AlarmType(Enum):
    """报警类型"""
    PROCESS = "process"           # 过程报警（测量值越限）
    DEVICE = "device"             # 设备报警（设备故障）
    SYSTEM = "system"             # 系统报警（通信/软件）
    PROTECTION = "protection"     # 保护报警（保护动作）
    SAFETY = "safety"             # 安全报警（人身/设备安全）
    ENVIRONMENT = "environment"   # 环境报警（地震/洪水）
    SECURITY = "security"         # 安保报警（入侵/网络攻击）


class AlarmState(Enum):
    """报警状态"""
    ACTIVE = "active"             # 激活（未确认）
    ACKNOWLEDGED = "acknowledged"  # 已确认
    CLEARED = "cleared"           # 已清除
    SUPPRESSED = "suppressed"     # 已抑制
    SHELVED = "shelved"           # 已搁置


@dataclass
class Alarm:
    """报警对象"""
    alarm_id: str                           # 报警ID
    source_id: str                          # 源点ID
    source_name: str                        # 源点名称
    level: AlarmLevel                       # 报警级别
    alarm_type: AlarmType                   # 报警类型
    message: str                            # 报警消息
    description: str = ""                   # 详细描述

    # 时间戳
    occur_time: datetime = field(default_factory=datetime.now)
    ack_time: Optional[datetime] = None
    clear_time: Optional[datetime] = None

    # 状态
    state: AlarmState = AlarmState.ACTIVE
    ack_user: Optional[str] = None

    # 报警值
    value: Optional[float] = None
    limit: Optional[float] = None
    unit: Optional[str] = None

    # 报警计数
    occurrence_count: int = 1
    escalation_count: int = 0

    # 关联信息
    related_alarms: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)

    # 优先级评分
    priority_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alarm_id": self.alarm_id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "level": self.level.name,
            "type": self.alarm_type.value,
            "message": self.message,
            "description": self.description,
            "occur_time": self.occur_time.isoformat(),
            "ack_time": self.ack_time.isoformat() if self.ack_time else None,
            "clear_time": self.clear_time.isoformat() if self.clear_time else None,
            "state": self.state.value,
            "ack_user": self.ack_user,
            "value": self.value,
            "limit": self.limit,
            "unit": self.unit,
            "occurrence_count": self.occurrence_count,
            "priority_score": self.priority_score,
            "recommended_actions": self.recommended_actions,
        }


@dataclass
class AlarmEscalation:
    """报警升级规则"""
    from_level: AlarmLevel
    to_level: AlarmLevel
    condition: str                          # 升级条件
    time_threshold: float                   # 时间阈值(秒)
    occurrence_threshold: int = 1           # 发生次数阈值
    auto_escalate: bool = True              # 自动升级


class AlarmHandler:
    """报警处理器基类"""

    def handle(self, alarm: Alarm) -> bool:
        """处理报警，返回是否成功"""
        raise NotImplementedError

    def get_priority(self) -> int:
        """获取处理器优先级"""
        return 0


class AlarmManager:
    """
    报警管理器

    功能：
    - 多级报警管理与优先级排序
    - 报警确认、清除、抑制
    - 报警升级与自动处理
    - 报警统计与历史记录
    - SOE事件顺序记录（1ms精度）
    """

    def __init__(self):
        self.active_alarms: Dict[str, Alarm] = {}
        self.alarm_history: List[Alarm] = []
        self.soe_records: List[Dict[str, Any]] = []
        self.suppressed_sources: Set[str] = set()
        self.shelved_sources: Dict[str, datetime] = {}
        self.handlers: List[AlarmHandler] = []
        self.escalation_rules: List[AlarmEscalation] = []
        self._lock = threading.Lock()
        self._alarm_counter = 0

        # 报警统计
        self.stats = {
            "total_alarms": 0,
            "active_count": 0,
            "unacked_count": 0,
            "by_level": defaultdict(int),
            "by_type": defaultdict(int),
            "by_source": defaultdict(int),
        }

        # 初始化默认升级规则
        self._initialize_escalation_rules()

        # 初始化推荐处置库
        self._initialize_action_library()

    def _initialize_escalation_rules(self):
        """初始化报警升级规则"""
        self.escalation_rules = [
            # 预警超过5分钟未处理升级为一般报警
            AlarmEscalation(
                from_level=AlarmLevel.WARNING,
                to_level=AlarmLevel.ALARM,
                condition="unacknowledged",
                time_threshold=300,
                auto_escalate=True
            ),
            # 一般报警超过2分钟未处理升级为重要报警
            AlarmEscalation(
                from_level=AlarmLevel.ALARM,
                to_level=AlarmLevel.CRITICAL,
                condition="unacknowledged",
                time_threshold=120,
                auto_escalate=True
            ),
            # 重复发生3次以上升级
            AlarmEscalation(
                from_level=AlarmLevel.WARNING,
                to_level=AlarmLevel.ALARM,
                condition="repeated",
                time_threshold=0,
                occurrence_threshold=3,
                auto_escalate=True
            ),
            # 安全相关报警直接升级
            AlarmEscalation(
                from_level=AlarmLevel.ALARM,
                to_level=AlarmLevel.EMERGENCY,
                condition="safety_related",
                time_threshold=0,
                auto_escalate=True
            ),
        ]

    def _initialize_action_library(self):
        """初始化推荐处置库"""
        self.action_library = {
            # 水力系统报警处置
            "HYD_上游水位_HH": [
                "立即开启溢洪道泄洪",
                "降低发电负荷减少下泄",
                "通知水调中心协调调度",
                "启动防洪应急预案",
            ],
            "HYD_上游水位_LL": [
                "降低发电负荷",
                "检查上游来水情况",
                "通知水调中心",
                "准备停机保水",
            ],
            "HYD_蜗壳压力_HH": [
                "紧急减负荷",
                "检查导叶开度",
                "检查调压室水位",
                "准备停机",
            ],

            # 水轮机报警处置
            "TRB_转速_HH": [
                "紧急停机",
                "检查调速器",
                "检查导叶卡涩",
                "联系检修",
            ],
            "TRB_振动_HH": [
                "降低负荷",
                "检查轴承状态",
                "检查水力条件",
                "安排停机检查",
            ],
            "TRB_轴承温度_HH": [
                "降低负荷",
                "检查冷却系统",
                "检查润滑油",
                "准备停机",
            ],

            # 发电机报警处置
            "GEN_定子温度_HH": [
                "降低有功负荷",
                "降低无功出力",
                "检查冷却系统",
                "安排停机检修",
            ],
            "GEN_定子电流_HH": [
                "降低负荷",
                "检查短路故障",
                "检查接地故障",
                "准备停机",
            ],

            # 电网报警处置
            "GRID_频率_LL": [
                "增加发电出力",
                "协调AGC控制",
                "准备切负荷",
                "联系调度中心",
            ],
            "GRID_频率_HH": [
                "降低发电出力",
                "协调AGC控制",
                "联系调度中心",
            ],

            # 环境报警处置
            "ENV_地震_HH": [
                "启动地震应急预案",
                "检查设备状态",
                "准备停机",
                "人员撤离到安全区",
            ],
        }

    def generate_alarm(self, source_id: str, source_name: str,
                       level: AlarmLevel, alarm_type: AlarmType,
                       message: str, value: Optional[float] = None,
                       limit: Optional[float] = None,
                       unit: Optional[str] = None) -> Optional[Alarm]:
        """生成报警"""
        with self._lock:
            # 检查是否被抑制
            if source_id in self.suppressed_sources:
                return None

            # 检查是否被搁置
            if source_id in self.shelved_sources:
                if datetime.now() < self.shelved_sources[source_id]:
                    return None
                else:
                    del self.shelved_sources[source_id]

            # 检查是否已存在活动报警
            existing_key = f"{source_id}_{level.name}"
            if existing_key in self.active_alarms:
                # 更新已有报警
                alarm = self.active_alarms[existing_key]
                alarm.occurrence_count += 1
                alarm.value = value
                self._record_soe("alarm_repeated", alarm)
                return alarm

            # 生成新报警
            self._alarm_counter += 1
            alarm_id = f"ALM_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._alarm_counter:04d}"

            alarm = Alarm(
                alarm_id=alarm_id,
                source_id=source_id,
                source_name=source_name,
                level=level,
                alarm_type=alarm_type,
                message=message,
                value=value,
                limit=limit,
                unit=unit,
            )

            # 计算优先级评分
            alarm.priority_score = self._calculate_priority(alarm)

            # 获取推荐处置
            alarm.recommended_actions = self._get_recommended_actions(alarm)

            # 添加到活动报警
            self.active_alarms[existing_key] = alarm

            # 更新统计
            self.stats["total_alarms"] += 1
            self.stats["active_count"] = len(self.active_alarms)
            self.stats["unacked_count"] = sum(
                1 for a in self.active_alarms.values()
                if a.state == AlarmState.ACTIVE
            )
            self.stats["by_level"][level.name] += 1
            self.stats["by_type"][alarm_type.value] += 1
            self.stats["by_source"][source_id] += 1

            # 记录SOE
            self._record_soe("alarm_occur", alarm)

            # 调用处理器
            self._dispatch_handlers(alarm)

            return alarm

    def _calculate_priority(self, alarm: Alarm) -> float:
        """计算报警优先级评分"""
        score = 0.0

        # 基础分数（级别）
        level_scores = {
            AlarmLevel.INFO: 10,
            AlarmLevel.WARNING: 30,
            AlarmLevel.ALARM: 50,
            AlarmLevel.CRITICAL: 80,
            AlarmLevel.EMERGENCY: 100,
        }
        score += level_scores.get(alarm.level, 0)

        # 类型加权
        type_weights = {
            AlarmType.SAFETY: 1.5,
            AlarmType.PROTECTION: 1.3,
            AlarmType.ENVIRONMENT: 1.4,
            AlarmType.SECURITY: 1.3,
            AlarmType.DEVICE: 1.1,
            AlarmType.PROCESS: 1.0,
            AlarmType.SYSTEM: 0.9,
        }
        score *= type_weights.get(alarm.alarm_type, 1.0)

        # 重复发生加分
        score += min(alarm.occurrence_count * 2, 20)

        return score

    def _get_recommended_actions(self, alarm: Alarm) -> List[str]:
        """获取推荐处置措施"""
        # 尝试精确匹配
        key = f"{alarm.source_id.split('_')[0]}_{alarm.source_name}_{alarm.level.name[0]}{alarm.level.name[-1]}"
        if key in self.action_library:
            return self.action_library[key]

        # 通用处置
        generic_actions = {
            AlarmLevel.WARNING: ["监视参数变化", "准备处置措施"],
            AlarmLevel.ALARM: ["确认报警", "分析原因", "准备应对措施"],
            AlarmLevel.CRITICAL: ["立即处置", "降低负荷", "准备停机"],
            AlarmLevel.EMERGENCY: ["紧急停机", "启动应急预案", "人员撤离"],
        }
        return generic_actions.get(alarm.level, ["确认报警"])

    def _record_soe(self, event_type: str, alarm: Alarm):
        """记录SOE事件"""
        soe_record = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "alarm_id": alarm.alarm_id,
            "source_id": alarm.source_id,
            "level": alarm.level.name,
            "message": alarm.message,
            "value": alarm.value,
        }
        self.soe_records.append(soe_record)

        # 保留最近10000条
        if len(self.soe_records) > 10000:
            self.soe_records = self.soe_records[-10000:]

    def _dispatch_handlers(self, alarm: Alarm):
        """分发给处理器"""
        sorted_handlers = sorted(self.handlers, key=lambda h: h.get_priority(), reverse=True)
        for handler in sorted_handlers:
            try:
                if handler.handle(alarm):
                    break  # 处理成功则停止
            except Exception as e:
                pass

    def acknowledge(self, alarm_id: str, user: str) -> bool:
        """确认报警"""
        with self._lock:
            for key, alarm in self.active_alarms.items():
                if alarm.alarm_id == alarm_id:
                    alarm.state = AlarmState.ACKNOWLEDGED
                    alarm.ack_time = datetime.now()
                    alarm.ack_user = user
                    self._record_soe("alarm_ack", alarm)
                    self._update_unacked_count()
                    return True
            return False

    def acknowledge_all(self, user: str, level: Optional[AlarmLevel] = None) -> int:
        """批量确认报警"""
        count = 0
        with self._lock:
            for alarm in self.active_alarms.values():
                if alarm.state == AlarmState.ACTIVE:
                    if level is None or alarm.level == level:
                        alarm.state = AlarmState.ACKNOWLEDGED
                        alarm.ack_time = datetime.now()
                        alarm.ack_user = user
                        self._record_soe("alarm_ack", alarm)
                        count += 1
            self._update_unacked_count()
        return count

    def clear(self, alarm_id: str) -> bool:
        """清除报警"""
        with self._lock:
            for key, alarm in list(self.active_alarms.items()):
                if alarm.alarm_id == alarm_id:
                    alarm.state = AlarmState.CLEARED
                    alarm.clear_time = datetime.now()
                    self._record_soe("alarm_clear", alarm)

                    # 移到历史
                    self.alarm_history.append(alarm)
                    del self.active_alarms[key]

                    # 保留最近1000条历史
                    if len(self.alarm_history) > 1000:
                        self.alarm_history = self.alarm_history[-1000:]

                    self.stats["active_count"] = len(self.active_alarms)
                    self._update_unacked_count()
                    return True
            return False

    def suppress(self, source_id: str):
        """抑制报警源"""
        self.suppressed_sources.add(source_id)

    def unsuppress(self, source_id: str):
        """取消抑制"""
        self.suppressed_sources.discard(source_id)

    def shelve(self, source_id: str, duration: float):
        """搁置报警源（指定时长，秒）"""
        self.shelved_sources[source_id] = datetime.now() + timedelta(seconds=duration)

    def _update_unacked_count(self):
        """更新未确认计数"""
        self.stats["unacked_count"] = sum(
            1 for a in self.active_alarms.values()
            if a.state == AlarmState.ACTIVE
        )

    def check_escalation(self):
        """检查并执行报警升级"""
        now = datetime.now()
        with self._lock:
            for alarm in list(self.active_alarms.values()):
                for rule in self.escalation_rules:
                    if alarm.level != rule.from_level:
                        continue

                    should_escalate = False

                    if rule.condition == "unacknowledged":
                        if alarm.state == AlarmState.ACTIVE:
                            elapsed = (now - alarm.occur_time).total_seconds()
                            if elapsed >= rule.time_threshold:
                                should_escalate = True

                    elif rule.condition == "repeated":
                        if alarm.occurrence_count >= rule.occurrence_threshold:
                            should_escalate = True

                    elif rule.condition == "safety_related":
                        if alarm.alarm_type == AlarmType.SAFETY:
                            should_escalate = True

                    if should_escalate and rule.auto_escalate:
                        alarm.level = rule.to_level
                        alarm.escalation_count += 1
                        alarm.priority_score = self._calculate_priority(alarm)
                        self._record_soe("alarm_escalate", alarm)

    def get_active_alarms(self, level: Optional[AlarmLevel] = None,
                          alarm_type: Optional[AlarmType] = None) -> List[Alarm]:
        """获取活动报警列表"""
        alarms = list(self.active_alarms.values())

        if level is not None:
            alarms = [a for a in alarms if a.level == level]

        if alarm_type is not None:
            alarms = [a for a in alarms if a.alarm_type == alarm_type]

        # 按优先级排序
        alarms.sort(key=lambda a: a.priority_score, reverse=True)

        return alarms

    def get_alarm_summary(self) -> Dict[str, Any]:
        """获取报警摘要"""
        active = self.get_active_alarms()
        by_level = defaultdict(int)
        by_type = defaultdict(int)

        for alarm in active:
            by_level[alarm.level.name] += 1
            by_type[alarm.alarm_type.value] += 1

        return {
            "active_count": len(active),
            "unacked_count": self.stats["unacked_count"],
            "by_level": dict(by_level),
            "by_type": dict(by_type),
            "highest_level": max((a.level for a in active), default=AlarmLevel.INFO).name,
            "recent_alarms": [a.to_dict() for a in active[:10]],
        }

    def get_soe_records(self, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """获取SOE记录"""
        records = self.soe_records

        if start_time:
            records = [r for r in records if r["timestamp"] >= start_time]
        if end_time:
            records = [r for r in records if r["timestamp"] <= end_time]

        # 按时间倒序
        records = sorted(records, key=lambda r: r["timestamp"], reverse=True)

        return records[:limit]

    def register_handler(self, handler: AlarmHandler):
        """注册报警处理器"""
        self.handlers.append(handler)

    def unregister_handler(self, handler: AlarmHandler):
        """注销报警处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
