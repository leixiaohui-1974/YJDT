"""
执行器仿真模块
Actuator Simulation Module

实现各类执行器的仿真，包括：
- 导叶伺服机构
- 阀门执行器
- 励磁系统执行器
- 断路器
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum


class ActuatorStatus(Enum):
    """执行器状态"""
    NORMAL = "normal"           # 正常
    MOVING = "moving"           # 动作中
    BLOCKED = "blocked"         # 阻塞
    STUCK = "stuck"             # 卡死
    SLOW = "slow"               # 动作缓慢
    OVERLOAD = "overload"       # 过载
    FAILED = "failed"           # 失效


class ActuatorFaultType(Enum):
    """执行器故障类型"""
    NONE = "none"
    STUCK = "stuck"                 # 卡死
    SLOW_RESPONSE = "slow"          # 响应慢
    DEAD_ZONE = "dead_zone"         # 死区增大
    BACKLASH = "backlash"           # 间隙增大
    POSITION_ERROR = "position_error"  # 位置误差
    COMPLETE_FAILURE = "failure"    # 完全失效


@dataclass
class ActuatorParams:
    """执行器通用参数"""
    name: str = "actuator"
    position_min: float = 0.0       # 最小位置
    position_max: float = 1.0       # 最大位置
    speed_open: float = 0.1         # 开启速度 (pu/s)
    speed_close: float = 0.15       # 关闭速度 (pu/s)
    time_constant: float = 0.5      # 时间常数 (s)
    dead_band: float = 0.001        # 死区 (pu)
    backlash: float = 0.002         # 回差 (pu)
    position_accuracy: float = 0.005  # 位置精度 (pu)
    force_limit: float = 1.0        # 力限制 (pu)
    power_consumption: float = 10.0  # 额定功耗 (kW)


class ActuatorBase(ABC):
    """执行器基类"""

    def __init__(self, params: ActuatorParams):
        self.params = params

        # 状态变量
        self.status = ActuatorStatus.NORMAL
        self.fault_type = ActuatorFaultType.NONE
        self.position = 0.0           # 当前位置 (pu)
        self.command = 0.0            # 指令位置 (pu)
        self.velocity = 0.0           # 当前速度 (pu/s)
        self.force = 0.0              # 当前力/力矩 (pu)
        self.power = 0.0              # 当前功耗 (kW)

        # 故障参数
        self.fault_magnitude = 0.0
        self.stuck_position = 0.0

        # 历史记录
        self.history: Dict[str, List[float]] = {
            'time': [],
            'position': [],
            'command': [],
            'velocity': [],
            'force': [],
            'status': [],
        }

    def set_command(self, command: float):
        """设置指令"""
        self.command = np.clip(command, self.params.position_min, self.params.position_max)

    def update(
        self,
        dt: float,
        current_time: float,
        external_force: float = 0.0
    ) -> float:
        """
        更新执行器状态

        Args:
            dt: 时间步长 (s)
            current_time: 当前时间 (s)
            external_force: 外部负载力 (pu)

        Returns:
            当前位置 (pu)
        """
        # 计算误差
        error = self.command - self.position

        # 应用死区
        if abs(error) < self.params.dead_band:
            error = 0.0
            self.status = ActuatorStatus.NORMAL
        else:
            self.status = ActuatorStatus.MOVING

        # 应用故障效应
        error = self._apply_fault(error)

        # 计算期望速度
        if error > 0:
            desired_velocity = min(error / self.params.time_constant, self.params.speed_open)
        else:
            desired_velocity = max(error / self.params.time_constant, -self.params.speed_close)

        # 一阶动态
        tau = self.params.time_constant
        self.velocity = (desired_velocity - self.velocity) * dt / tau + self.velocity

        # 更新位置
        new_position = self.position + self.velocity * dt

        # 位置限制
        new_position = np.clip(
            new_position,
            self.params.position_min,
            self.params.position_max
        )

        # 位置精度量化
        accuracy = self.params.position_accuracy
        if accuracy > 0:
            new_position = np.round(new_position / accuracy) * accuracy

        self.position = new_position

        # 计算力
        self.force = abs(self.velocity) * (1 + external_force)

        # 计算功耗
        self.power = self.params.power_consumption * abs(self.velocity) / self.params.speed_open

        # 记录历史
        self._record_history(current_time)

        return self.position

    def _apply_fault(self, error: float) -> float:
        """应用故障效应"""
        if self.fault_type == ActuatorFaultType.NONE:
            return error

        if self.fault_type == ActuatorFaultType.STUCK:
            self.position = self.stuck_position
            self.status = ActuatorStatus.STUCK
            return 0.0

        elif self.fault_type == ActuatorFaultType.SLOW_RESPONSE:
            # 减慢响应
            return error * (1 - self.fault_magnitude)

        elif self.fault_type == ActuatorFaultType.DEAD_ZONE:
            # 增大死区
            dead_zone = self.params.dead_band * (1 + self.fault_magnitude * 10)
            if abs(error) < dead_zone:
                return 0.0
            return error

        elif self.fault_type == ActuatorFaultType.BACKLASH:
            # 增大回差
            backlash = self.params.backlash * (1 + self.fault_magnitude * 5)
            if abs(error) < backlash:
                return 0.0
            if error > 0:
                return error - backlash
            return error + backlash

        elif self.fault_type == ActuatorFaultType.POSITION_ERROR:
            # 位置偏差
            return error + self.fault_magnitude * (self.params.position_max - self.params.position_min)

        elif self.fault_type == ActuatorFaultType.COMPLETE_FAILURE:
            self.status = ActuatorStatus.FAILED
            return 0.0

        return error

    def inject_fault(
        self,
        fault_type: ActuatorFaultType,
        magnitude: float = 0.1,
        stuck_position: Optional[float] = None
    ):
        """注入故障"""
        self.fault_type = fault_type
        self.fault_magnitude = magnitude

        if fault_type == ActuatorFaultType.STUCK:
            self.stuck_position = stuck_position if stuck_position is not None else self.position
            self.status = ActuatorStatus.STUCK

        elif fault_type == ActuatorFaultType.SLOW_RESPONSE:
            self.status = ActuatorStatus.SLOW

        elif fault_type == ActuatorFaultType.COMPLETE_FAILURE:
            self.status = ActuatorStatus.FAILED

    def clear_fault(self):
        """清除故障"""
        self.fault_type = ActuatorFaultType.NONE
        self.fault_magnitude = 0.0
        self.status = ActuatorStatus.NORMAL

    def emergency_close(self, dt: float, current_time: float):
        """紧急关闭"""
        self.command = self.params.position_min
        # 使用最大关闭速度
        self.velocity = -self.params.speed_close
        self.position = max(
            self.params.position_min,
            self.position + self.velocity * dt
        )
        self._record_history(current_time)

    def _record_history(self, current_time: float):
        """记录历史"""
        self.history['time'].append(current_time)
        self.history['position'].append(self.position)
        self.history['command'].append(self.command)
        self.history['velocity'].append(self.velocity)
        self.history['force'].append(self.force)
        self.history['status'].append(self.status.value)

    def get_health_score(self) -> float:
        """获取健康评分"""
        if self.status == ActuatorStatus.NORMAL:
            return 1.0
        elif self.status == ActuatorStatus.MOVING:
            return 0.95
        elif self.status == ActuatorStatus.SLOW:
            return 0.6
        elif self.status == ActuatorStatus.BLOCKED:
            return 0.3
        elif self.status == ActuatorStatus.STUCK:
            return 0.1
        elif self.status == ActuatorStatus.FAILED:
            return 0.0
        return 0.5


class GuideVaneActuator(ActuatorBase):
    """
    导叶伺服执行器

    实现水轮机导叶的电液伺服控制
    """

    def __init__(
        self,
        name: str = "guide_vane",
        speed_open: float = 0.08,     # 开启速度 (pu/s)
        speed_close: float = 0.125,    # 关闭速度 (pu/s)
        time_constant: float = 0.5,    # 伺服时间常数 (s)
    ):
        params = ActuatorParams(
            name=name,
            position_min=0.0,
            position_max=1.0,
            speed_open=speed_open,
            speed_close=speed_close,
            time_constant=time_constant,
            dead_band=0.002,
            backlash=0.003,
            position_accuracy=0.001,
            force_limit=1.5,
            power_consumption=50.0,  # kW
        )
        super().__init__(params)

        # 导叶特有参数
        self.num_vanes = 24
        self.water_pressure_feedback = 0.0  # 水压反馈

    def update(
        self,
        dt: float,
        current_time: float,
        water_pressure: float = 0.0
    ) -> float:
        """
        更新导叶位置

        Args:
            dt: 时间步长
            current_time: 当前时间
            water_pressure: 水压 (用于计算水力矩)

        Returns:
            导叶开度
        """
        # 水压对关闭速度的影响
        self.water_pressure_feedback = water_pressure
        pressure_factor = 1.0 - 0.1 * water_pressure  # 高压时关闭稍慢
        effective_close_speed = self.params.speed_close * pressure_factor

        # 暂存原速度
        original_speed = self.params.speed_close
        self.params.speed_close = effective_close_speed

        position = super().update(dt, current_time, water_pressure)

        # 恢复
        self.params.speed_close = original_speed

        return position

    def get_flow_coefficient(self) -> float:
        """获取流量系数（与开度相关）"""
        # 简化的流量-开度关系
        y = self.position
        # 非线性关系
        return 0.1 + 0.9 * y - 0.1 * y**2


class ValveActuator(ActuatorBase):
    """
    阀门执行器

    实现进水阀、事故阀等的控制
    """

    def __init__(
        self,
        name: str = "valve",
        valve_type: str = "gate",  # gate, butterfly, ball
        speed: float = 0.05,       # 动作速度 (pu/s)
    ):
        params = ActuatorParams(
            name=name,
            position_min=0.0,
            position_max=1.0,
            speed_open=speed,
            speed_close=speed * 1.2,  # 关闭稍快
            time_constant=1.0,
            dead_band=0.005,
            backlash=0.01,
            position_accuracy=0.005,
            power_consumption=20.0,
        )
        super().__init__(params)

        self.valve_type = valve_type

    def get_flow_characteristic(self) -> callable:
        """获取流量特性曲线"""
        if self.valve_type == "gate":
            # 闸阀：快开特性
            def characteristic(opening):
                return np.sqrt(opening)
        elif self.valve_type == "butterfly":
            # 蝶阀：等百分比特性
            def characteristic(opening):
                return np.exp(3 * (opening - 1))
        else:
            # 默认线性
            def characteristic(opening):
                return opening

        return characteristic


class ExciterActuator(ActuatorBase):
    """
    励磁系统执行器

    实现励磁电压的控制
    """

    def __init__(
        self,
        name: str = "exciter",
        ceiling_voltage: float = 3.0,  # 顶值电压 (pu)
        response_time: float = 0.1,    # 响应时间 (s)
    ):
        params = ActuatorParams(
            name=name,
            position_min=0.0,
            position_max=ceiling_voltage,
            speed_open=ceiling_voltage / response_time,
            speed_close=ceiling_voltage / (response_time * 0.5),
            time_constant=response_time,
            dead_band=0.001,
            position_accuracy=0.001,
            power_consumption=500.0,  # kW
        )
        super().__init__(params)

        self.ceiling_voltage = ceiling_voltage
        self.field_current = 0.0

    def update(
        self,
        dt: float,
        current_time: float,
        field_current: float = 0.0
    ) -> float:
        """更新励磁电压"""
        self.field_current = field_current

        # 限制励磁电压以防止过励磁
        max_voltage = self.ceiling_voltage * (1 - 0.1 * field_current)
        original_max = self.params.position_max
        self.params.position_max = max_voltage

        voltage = super().update(dt, current_time)

        self.params.position_max = original_max

        return voltage

    def get_excitation_voltage(self) -> float:
        """获取励磁电压"""
        return self.position


class BreakerActuator(ActuatorBase):
    """
    断路器执行器

    实现断路器的分合闸控制
    """

    def __init__(
        self,
        name: str = "breaker",
        close_time: float = 0.05,   # 合闸时间 (s)
        open_time: float = 0.03,    # 分闸时间 (s)
    ):
        params = ActuatorParams(
            name=name,
            position_min=0.0,        # 分闸
            position_max=1.0,        # 合闸
            speed_open=1.0 / close_time,
            speed_close=1.0 / open_time,
            time_constant=0.01,
            dead_band=0.01,
            position_accuracy=0.1,  # 断路器只有开/关
            power_consumption=5.0,
        )
        super().__init__(params)

        self.close_time = close_time
        self.open_time = open_time
        self.is_closed = False
        self.operation_count = 0

    def close(self, current_time: float):
        """合闸"""
        self.command = 1.0
        self.is_closed = True
        self.operation_count += 1

    def open(self, current_time: float):
        """分闸"""
        self.command = 0.0
        self.is_closed = False
        self.operation_count += 1

    def trip(self, current_time: float):
        """跳闸（紧急分闸）"""
        self.position = 0.0
        self.command = 0.0
        self.is_closed = False
        self.operation_count += 1
        self._record_history(current_time)

    def update(
        self,
        dt: float,
        current_time: float,
        trip_signal: bool = False
    ) -> float:
        """
        更新断路器状态

        Args:
            dt: 时间步长
            current_time: 当前时间
            trip_signal: 跳闸信号

        Returns:
            断路器状态 (0=分闸, 1=合闸)
        """
        if trip_signal:
            self.trip(current_time)
            return self.position

        return super().update(dt, current_time)

    def get_state(self) -> str:
        """获取断路器状态"""
        if self.position > 0.9:
            return "closed"
        elif self.position < 0.1:
            return "open"
        else:
            return "transitioning"


class ActuatorGroup:
    """执行器组管理类"""

    def __init__(self):
        self.actuators: Dict[str, ActuatorBase] = {}

    def add_actuator(self, actuator_id: str, actuator: ActuatorBase):
        """添加执行器"""
        self.actuators[actuator_id] = actuator

    def set_commands(self, commands: Dict[str, float]):
        """设置命令"""
        for actuator_id, command in commands.items():
            if actuator_id in self.actuators:
                self.actuators[actuator_id].set_command(command)

    def update_all(self, dt: float, current_time: float) -> Dict[str, float]:
        """更新所有执行器"""
        positions = {}
        for actuator_id, actuator in self.actuators.items():
            positions[actuator_id] = actuator.update(dt, current_time)
        return positions

    def get_all_status(self) -> Dict[str, ActuatorStatus]:
        """获取所有状态"""
        return {
            actuator_id: actuator.status
            for actuator_id, actuator in self.actuators.items()
        }

    def emergency_shutdown(self, dt: float, current_time: float):
        """紧急停机"""
        for actuator in self.actuators.values():
            if hasattr(actuator, 'emergency_close'):
                actuator.emergency_close(dt, current_time)
            elif isinstance(actuator, BreakerActuator):
                actuator.trip(current_time)
