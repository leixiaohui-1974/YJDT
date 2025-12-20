# -*- coding: utf-8 -*-
"""
控制执行器 - 闭环控制指令执行
Control Executor - Closed-loop Control Command Execution

功能：
- 控制指令验证与执行
- 安全联锁检查
- 控制效果监测
- 故障安全处理
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum


class ControlMode(Enum):
    """控制模式"""
    MANUAL = "manual"               # 手动
    SEMI_AUTO = "semi_auto"         # 半自动
    AUTO = "auto"                   # 自动
    REMOTE = "remote"               # 远程
    EMERGENCY = "emergency"         # 应急


class CommandStatus(Enum):
    """指令状态"""
    PENDING = "pending"             # 待执行
    VALIDATING = "validating"       # 验证中
    EXECUTING = "executing"         # 执行中
    COMPLETED = "completed"         # 已完成
    FAILED = "failed"               # 失败
    REJECTED = "rejected"           # 拒绝
    TIMEOUT = "timeout"             # 超时


class CommandPriority(Enum):
    """指令优先级"""
    EMERGENCY = 0                   # 紧急（最高）
    HIGH = 1                        # 高
    NORMAL = 2                      # 正常
    LOW = 3                         # 低


@dataclass
class ControlCommand:
    """控制指令"""
    command_id: str
    target: str                     # 控制目标（设备ID）
    variable: str                   # 控制变量
    setpoint: float                 # 设定值
    unit: str = ""
    priority: CommandPriority = CommandPriority.NORMAL
    source: str = "scheduler"       # 指令来源
    mode: ControlMode = ControlMode.AUTO
    timeout: float = 30.0           # 超时时间（秒）
    status: CommandStatus = CommandStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    result: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterlockCondition:
    """联锁条件"""
    interlock_id: str
    name: str
    description: str
    check_function: Callable[[Dict], bool]
    severity: str = "block"         # "block", "warn", "log"
    active: bool = True


@dataclass
class ControlFeedback:
    """控制反馈"""
    command_id: str
    target: str
    variable: str
    setpoint: float
    actual_value: float
    error: float
    settled: bool
    settle_time: float              # 秒
    overshoot: float                # %
    timestamp: datetime = field(default_factory=datetime.now)


class ControlExecutor:
    """
    控制执行器

    功能：
    - 指令队列管理
    - 安全验证
    - 执行与监控
    - 效果评估
    """

    def __init__(self):
        # 指令队列
        self.command_queue: List[ControlCommand] = []
        self.command_history: List[ControlCommand] = []

        # 联锁条件
        self.interlocks: Dict[str, InterlockCondition] = {}

        # 控制反馈
        self.feedback_history: List[ControlFeedback] = []

        # 设备状态
        self.device_states: Dict[str, Dict[str, Any]] = {}

        # 配置
        self.config = {
            "max_queue_size": 100,
            "default_timeout": 30.0,
            "feedback_interval": 1.0,
            "settling_threshold": 0.02,     # 2%误差视为稳定
            "max_overshoot": 10.0,          # 最大超调10%
        }

        # 初始化联锁
        self._initialize_interlocks()
        self._command_counter = 0

    def _initialize_interlocks(self):
        """初始化安全联锁"""
        default_interlocks = [
            InterlockCondition(
                "IL001",
                "水位联锁",
                "水位超限时禁止增加出力",
                lambda state: state.get("water_level", 0) < state.get("max_level", 100),
                "block"
            ),
            InterlockCondition(
                "IL002",
                "温度联锁",
                "轴承温度过高时限制运行",
                lambda state: state.get("bearing_temp", 0) < 80,
                "block"
            ),
            InterlockCondition(
                "IL003",
                "振动联锁",
                "振动超限时禁止升负荷",
                lambda state: state.get("vibration", 0) < 100,
                "block"
            ),
            InterlockCondition(
                "IL004",
                "压力联锁",
                "蜗壳压力异常时保护",
                lambda state: state.get("spiral_case_pressure", 0) < 5.0,
                "block"
            ),
            InterlockCondition(
                "IL005",
                "通信联锁",
                "通信中断时转本地控制",
                lambda state: state.get("comm_status", True),
                "warn"
            ),
        ]

        for interlock in default_interlocks:
            self.interlocks[interlock.interlock_id] = interlock

    def submit_command(self, target: str, variable: str, setpoint: float,
                       priority: CommandPriority = CommandPriority.NORMAL,
                       source: str = "scheduler",
                       mode: ControlMode = ControlMode.AUTO) -> ControlCommand:
        """
        提交控制指令

        Args:
            target: 控制目标
            variable: 控制变量
            setpoint: 设定值
            priority: 优先级
            source: 来源
            mode: 控制模式

        Returns:
            控制指令对象
        """
        self._command_counter += 1
        command_id = f"CMD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._command_counter:04d}"

        command = ControlCommand(
            command_id=command_id,
            target=target,
            variable=variable,
            setpoint=setpoint,
            priority=priority,
            source=source,
            mode=mode,
            timeout=self.config["default_timeout"],
        )

        # 加入队列（按优先级排序）
        self.command_queue.append(command)
        self.command_queue.sort(key=lambda c: c.priority.value)

        # 限制队列大小
        if len(self.command_queue) > self.config["max_queue_size"]:
            # 移除最低优先级的指令
            self.command_queue = self.command_queue[:self.config["max_queue_size"]]

        return command

    def validate_command(self, command: ControlCommand) -> Tuple[bool, List[str]]:
        """
        验证控制指令

        Args:
            command: 控制指令

        Returns:
            (是否通过, 拒绝原因列表)
        """
        command.status = CommandStatus.VALIDATING
        rejection_reasons = []

        # 获取设备状态
        state = self.device_states.get(command.target, {})

        # 检查联锁
        for interlock in self.interlocks.values():
            if not interlock.active:
                continue

            try:
                if not interlock.check_function(state):
                    if interlock.severity == "block":
                        rejection_reasons.append(f"联锁触发: {interlock.name}")
                    elif interlock.severity == "warn":
                        command.result["warnings"] = command.result.get("warnings", [])
                        command.result["warnings"].append(interlock.name)
            except Exception as e:
                rejection_reasons.append(f"联锁检查异常: {interlock.interlock_id}")

        # 检查设定值范围
        limits = self._get_variable_limits(command.target, command.variable)
        if limits:
            if command.setpoint < limits["min"]:
                rejection_reasons.append(
                    f"设定值低于下限: {command.setpoint} < {limits['min']}"
                )
            if command.setpoint > limits["max"]:
                rejection_reasons.append(
                    f"设定值高于上限: {command.setpoint} > {limits['max']}"
                )

        # 检查变化率
        current_value = state.get(command.variable, 0)
        rate_limit = self._get_rate_limit(command.target, command.variable)
        if rate_limit and abs(command.setpoint - current_value) > rate_limit:
            # 可以接受但需要分步执行
            command.result["step_execution"] = True
            command.result["steps"] = self._calculate_steps(
                current_value, command.setpoint, rate_limit
            )

        is_valid = len(rejection_reasons) == 0

        if not is_valid:
            command.status = CommandStatus.REJECTED
            command.result["rejection_reasons"] = rejection_reasons

        return is_valid, rejection_reasons

    def _get_variable_limits(self, target: str, variable: str) -> Optional[Dict[str, float]]:
        """获取变量限制"""
        # 简化实现
        limits_map = {
            "power": {"min": 0, "max": 600, "unit": "MW"},
            "guide_vane": {"min": 0, "max": 100, "unit": "%"},
            "frequency": {"min": 49.5, "max": 50.5, "unit": "Hz"},
            "voltage": {"min": 0.95, "max": 1.05, "unit": "p.u."},
            "water_level": {"min": -5, "max": 5, "unit": "m"},
        }
        return limits_map.get(variable)

    def _get_rate_limit(self, target: str, variable: str) -> Optional[float]:
        """获取变化率限制"""
        rate_limits = {
            "power": 50,        # MW/min
            "guide_vane": 10,   # %/min
        }
        return rate_limits.get(variable)

    def _calculate_steps(self, current: float, target: float,
                         rate_limit: float) -> List[float]:
        """计算分步执行序列"""
        direction = 1 if target > current else -1
        steps = [current]
        value = current

        while abs(value - target) > rate_limit:
            value += direction * rate_limit
            steps.append(value)

        steps.append(target)
        return steps

    def execute_command(self, command: ControlCommand) -> bool:
        """
        执行控制指令

        Args:
            command: 控制指令

        Returns:
            是否成功
        """
        # 验证
        is_valid, _ = self.validate_command(command)
        if not is_valid:
            return False

        command.status = CommandStatus.EXECUTING
        command.executed_at = datetime.now()

        try:
            # 检查是否需要分步执行
            if command.result.get("step_execution"):
                steps = command.result["steps"]
                for step in steps:
                    self._apply_setpoint(command.target, command.variable, step)
                    # 实际应用中这里需要等待
            else:
                self._apply_setpoint(command.target, command.variable, command.setpoint)

            command.status = CommandStatus.COMPLETED
            command.result["success"] = True

        except Exception as e:
            command.status = CommandStatus.FAILED
            command.result["error"] = str(e)
            return False

        finally:
            # 移入历史
            if command in self.command_queue:
                self.command_queue.remove(command)
            self.command_history.append(command)

            # 限制历史长度
            if len(self.command_history) > 10000:
                self.command_history = self.command_history[-10000:]

        return True

    def _apply_setpoint(self, target: str, variable: str, value: float):
        """应用设定值"""
        if target not in self.device_states:
            self.device_states[target] = {}

        self.device_states[target][variable] = value
        self.device_states[target]["last_update"] = datetime.now()

    def process_queue(self) -> List[ControlCommand]:
        """处理指令队列"""
        processed = []

        for command in list(self.command_queue):
            # 检查超时
            age = (datetime.now() - command.created_at).total_seconds()
            if age > command.timeout:
                command.status = CommandStatus.TIMEOUT
                self.command_queue.remove(command)
                self.command_history.append(command)
                continue

            # 执行
            success = self.execute_command(command)
            processed.append(command)

            if not success:
                break  # 失败时停止处理

        return processed

    def monitor_feedback(self, target: str, variable: str,
                         actual_value: float) -> Optional[ControlFeedback]:
        """
        监控控制反馈

        Args:
            target: 控制目标
            variable: 控制变量
            actual_value: 实际值

        Returns:
            控制反馈
        """
        # 查找对应的指令
        recent_commands = [
            c for c in self.command_history
            if c.target == target and c.variable == variable
            and c.status == CommandStatus.COMPLETED
        ]

        if not recent_commands:
            return None

        command = recent_commands[-1]
        setpoint = command.setpoint
        error = actual_value - setpoint

        # 判断是否稳定
        threshold = abs(setpoint) * self.config["settling_threshold"]
        settled = abs(error) < threshold

        # 计算调节时间
        if command.executed_at:
            settle_time = (datetime.now() - command.executed_at).total_seconds()
        else:
            settle_time = 0

        # 计算超调
        if setpoint != 0:
            overshoot = max(0, (abs(error) / abs(setpoint) - 1) * 100) if not settled else 0
        else:
            overshoot = 0

        feedback = ControlFeedback(
            command_id=command.command_id,
            target=target,
            variable=variable,
            setpoint=setpoint,
            actual_value=actual_value,
            error=error,
            settled=settled,
            settle_time=settle_time,
            overshoot=overshoot,
        )

        self.feedback_history.append(feedback)

        # 限制历史长度
        if len(self.feedback_history) > 10000:
            self.feedback_history = self.feedback_history[-10000:]

        return feedback

    def update_device_state(self, target: str, state: Dict[str, Any]):
        """更新设备状态"""
        if target not in self.device_states:
            self.device_states[target] = {}
        self.device_states[target].update(state)
        self.device_states[target]["last_update"] = datetime.now()

    def emergency_stop(self, target: str = None) -> List[ControlCommand]:
        """
        紧急停机

        Args:
            target: 目标设备（None表示全部）

        Returns:
            发出的紧急指令列表
        """
        emergency_commands = []

        targets = [target] if target else list(self.device_states.keys())

        for t in targets:
            # 发出紧急停机指令
            cmd = self.submit_command(
                target=t,
                variable="power",
                setpoint=0,
                priority=CommandPriority.EMERGENCY,
                source="emergency_stop",
                mode=ControlMode.EMERGENCY,
            )
            emergency_commands.append(cmd)

            # 立即执行
            self.execute_command(cmd)

        return emergency_commands

    def get_command_statistics(self) -> Dict[str, Any]:
        """获取指令统计"""
        total = len(self.command_history)
        if total == 0:
            return {"total": 0}

        status_counts = {}
        for cmd in self.command_history:
            status = cmd.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # 执行时间统计
        exec_times = []
        for cmd in self.command_history:
            if cmd.executed_at and cmd.created_at:
                exec_time = (cmd.executed_at - cmd.created_at).total_seconds()
                exec_times.append(exec_time)

        return {
            "total": total,
            "queue_size": len(self.command_queue),
            "status_distribution": status_counts,
            "success_rate": status_counts.get("completed", 0) / total * 100,
            "avg_execution_time": np.mean(exec_times) if exec_times else 0,
            "max_execution_time": np.max(exec_times) if exec_times else 0,
        }

    def get_control_quality(self, target: str = None,
                            variable: str = None) -> Dict[str, Any]:
        """获取控制品质"""
        feedbacks = self.feedback_history

        if target:
            feedbacks = [f for f in feedbacks if f.target == target]
        if variable:
            feedbacks = [f for f in feedbacks if f.variable == variable]

        if not feedbacks:
            return {"error": "No feedback data"}

        errors = [f.error for f in feedbacks]
        settle_times = [f.settle_time for f in feedbacks if f.settled]
        overshoots = [f.overshoot for f in feedbacks]

        return {
            "sample_count": len(feedbacks),
            "mae": np.mean(np.abs(errors)),
            "rmse": np.sqrt(np.mean(np.array(errors) ** 2)),
            "avg_settle_time": np.mean(settle_times) if settle_times else None,
            "avg_overshoot": np.mean(overshoots),
            "max_overshoot": np.max(overshoots),
            "settling_rate": len(settle_times) / len(feedbacks) * 100,
        }


# 需要导入Tuple
from typing import Tuple


class SafetyMonitor:
    """
    安全监视器

    功能：
    - 实时安全监控
    - 保护动作
    - 事件记录
    """

    def __init__(self, executor: ControlExecutor):
        self.executor = executor

        # 保护配置
        self.protections = {
            "overspeed": {"threshold": 1.1, "action": "trip", "delay": 0},
            "undervoltage": {"threshold": 0.85, "action": "alarm", "delay": 5},
            "overcurrent": {"threshold": 1.2, "action": "reduce", "delay": 1},
            "overtemperature": {"threshold": 85, "action": "reduce", "delay": 10},
            "overvibration": {"threshold": 150, "action": "trip", "delay": 0},
        }

        # 事件记录
        self.events: List[Dict[str, Any]] = []

    def check_protection(self, measurements: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        检查保护条件

        Args:
            measurements: 测量值

        Returns:
            触发的保护动作列表
        """
        actions = []

        # 超速保护
        if measurements.get("speed_ratio", 1.0) > self.protections["overspeed"]["threshold"]:
            actions.append({
                "protection": "overspeed",
                "value": measurements.get("speed_ratio"),
                "action": "trip",
                "timestamp": datetime.now(),
            })

        # 欠压保护
        if measurements.get("voltage_pu", 1.0) < self.protections["undervoltage"]["threshold"]:
            actions.append({
                "protection": "undervoltage",
                "value": measurements.get("voltage_pu"),
                "action": "alarm",
                "timestamp": datetime.now(),
            })

        # 过流保护
        if measurements.get("current_ratio", 1.0) > self.protections["overcurrent"]["threshold"]:
            actions.append({
                "protection": "overcurrent",
                "value": measurements.get("current_ratio"),
                "action": "reduce_load",
                "timestamp": datetime.now(),
            })

        # 过温保护
        if measurements.get("temperature", 0) > self.protections["overtemperature"]["threshold"]:
            actions.append({
                "protection": "overtemperature",
                "value": measurements.get("temperature"),
                "action": "reduce_load",
                "timestamp": datetime.now(),
            })

        # 振动保护
        if measurements.get("vibration", 0) > self.protections["overvibration"]["threshold"]:
            actions.append({
                "protection": "overvibration",
                "value": measurements.get("vibration"),
                "action": "trip",
                "timestamp": datetime.now(),
            })

        # 记录事件
        for action in actions:
            self.events.append(action)
            self._execute_protection_action(action)

        return actions

    def _execute_protection_action(self, action: Dict[str, Any]):
        """执行保护动作"""
        if action["action"] == "trip":
            # 紧急停机
            self.executor.emergency_stop()
        elif action["action"] == "reduce_load":
            # 降负荷
            for target in self.executor.device_states:
                current_power = self.executor.device_states[target].get("power", 0)
                self.executor.submit_command(
                    target=target,
                    variable="power",
                    setpoint=current_power * 0.5,
                    priority=CommandPriority.HIGH,
                    source="protection",
                )
        elif action["action"] == "alarm":
            # 仅告警
            pass

