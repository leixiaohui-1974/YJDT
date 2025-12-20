"""
传感器仿真模块
Sensor Simulation Module

实现各类传感器的仿真，包括：
- 测量噪声和误差模型
- 动态特性（延迟、滞后）
- 故障模式仿真
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum


class SensorStatus(Enum):
    """传感器状态"""
    NORMAL = "normal"           # 正常
    DEGRADED = "degraded"       # 性能下降
    DRIFT = "drift"             # 漂移
    STUCK = "stuck"             # 卡死
    NOISE = "noise"             # 噪声增大
    FAILED = "failed"           # 失效
    OFFLINE = "offline"         # 离线


class FaultType(Enum):
    """故障类型"""
    NONE = "none"
    BIAS = "bias"               # 偏差故障
    DRIFT = "drift"             # 漂移故障
    STUCK = "stuck"             # 卡死故障
    NOISE = "noise"             # 噪声故障
    DEAD_ZONE = "dead_zone"     # 死区故障
    SATURATION = "saturation"   # 饱和故障
    COMPLETE_FAILURE = "complete_failure"  # 完全失效


@dataclass
class SensorParams:
    """传感器通用参数"""
    name: str = "sensor"
    unit: str = ""
    range_min: float = 0.0          # 量程下限
    range_max: float = 100.0        # 量程上限
    accuracy: float = 0.01          # 精度 (% of range)
    resolution: float = 0.001       # 分辨率 (% of range)
    time_constant: float = 0.05     # 时间常数 (s)
    sample_rate: float = 100.0      # 采样率 (Hz)
    noise_std: float = 0.001        # 噪声标准差 (% of range)
    drift_rate: float = 0.0         # 漂移速率 (%/hour)
    hysteresis: float = 0.0         # 滞后 (% of range)
    dead_band: float = 0.0          # 死区 (% of range)


class SensorBase(ABC):
    """传感器基类"""

    def __init__(self, params: SensorParams):
        self.params = params

        # 状态变量
        self.status = SensorStatus.NORMAL
        self.fault_type = FaultType.NONE
        self.raw_value = 0.0          # 真实值
        self.measured_value = 0.0      # 测量值
        self.filtered_value = 0.0      # 滤波后的值
        self.previous_value = 0.0      # 上一次测量值

        # 故障参数
        self.fault_magnitude = 0.0     # 故障幅值
        self.stuck_value = 0.0         # 卡死值
        self.drift_accumulated = 0.0   # 累积漂移

        # 时间记录
        self.last_sample_time = 0.0
        self.start_time = 0.0

        # 历史数据
        self.history: Dict[str, List[float]] = {
            'time': [],
            'raw': [],
            'measured': [],
            'filtered': [],
            'status': [],
        }

    def measure(
        self,
        true_value: float,
        current_time: float,
        dt: float
    ) -> float:
        """
        执行测量

        Args:
            true_value: 真实物理量值
            current_time: 当前时间 (s)
            dt: 时间步长 (s)

        Returns:
            测量值
        """
        self.raw_value = true_value

        # 检查采样时间
        if current_time - self.last_sample_time < 1.0 / self.params.sample_rate:
            return self.measured_value

        self.last_sample_time = current_time

        # 应用传感器动态特性
        value = self._apply_dynamics(true_value, dt)

        # 应用测量误差
        value = self._apply_errors(value, current_time)

        # 应用故障效应
        value = self._apply_fault(value, current_time)

        # 量程限制
        value = np.clip(value, self.params.range_min, self.params.range_max)

        # 分辨率量化
        resolution = self.params.resolution * (self.params.range_max - self.params.range_min)
        if resolution > 0:
            value = np.round(value / resolution) * resolution

        self.previous_value = self.measured_value
        self.measured_value = value

        # 滤波
        self.filtered_value = self._apply_filter(value, dt)

        # 记录历史
        self._record_history(current_time)

        return self.measured_value

    def _apply_dynamics(self, value: float, dt: float) -> float:
        """应用传感器动态特性（一阶滞后）"""
        tau = self.params.time_constant
        if tau > 0 and dt > 0:
            alpha = dt / (tau + dt)
            return alpha * value + (1 - alpha) * self.measured_value
        return value

    def _apply_errors(self, value: float, current_time: float) -> float:
        """应用测量误差"""
        range_span = self.params.range_max - self.params.range_min

        # 随机噪声
        noise = np.random.normal(0, self.params.noise_std * range_span)
        value += noise

        # 精度误差
        accuracy_error = np.random.uniform(-1, 1) * self.params.accuracy * range_span
        value += accuracy_error

        # 漂移
        if self.params.drift_rate > 0:
            hours_elapsed = (current_time - self.start_time) / 3600
            self.drift_accumulated = self.params.drift_rate * hours_elapsed * range_span
            value += self.drift_accumulated

        # 滞后效应
        if self.params.hysteresis > 0:
            hysteresis = self.params.hysteresis * range_span
            if value > self.previous_value:
                value -= hysteresis / 2
            else:
                value += hysteresis / 2

        return value

    def _apply_fault(self, value: float, current_time: float) -> float:
        """应用故障效应"""
        if self.fault_type == FaultType.NONE:
            return value

        range_span = self.params.range_max - self.params.range_min

        if self.fault_type == FaultType.BIAS:
            return value + self.fault_magnitude * range_span

        elif self.fault_type == FaultType.DRIFT:
            drift = self.fault_magnitude * (current_time - self.start_time) / 100
            return value + drift * range_span

        elif self.fault_type == FaultType.STUCK:
            return self.stuck_value

        elif self.fault_type == FaultType.NOISE:
            extra_noise = np.random.normal(0, self.fault_magnitude * range_span)
            return value + extra_noise

        elif self.fault_type == FaultType.DEAD_ZONE:
            if abs(value - self.previous_value) < self.fault_magnitude * range_span:
                return self.previous_value
            return value

        elif self.fault_type == FaultType.SATURATION:
            sat_limit = self.fault_magnitude * range_span
            center = (self.params.range_max + self.params.range_min) / 2
            return np.clip(value, center - sat_limit, center + sat_limit)

        elif self.fault_type == FaultType.COMPLETE_FAILURE:
            self.status = SensorStatus.FAILED
            return 0.0  # 或返回最后有效值

        return value

    def _apply_filter(self, value: float, dt: float) -> float:
        """低通滤波"""
        cutoff_freq = 10.0  # Hz
        alpha = dt / (1 / (2 * np.pi * cutoff_freq) + dt)
        return alpha * value + (1 - alpha) * self.filtered_value

    def inject_fault(
        self,
        fault_type: FaultType,
        magnitude: float = 0.1,
        stuck_value: Optional[float] = None
    ):
        """
        注入故障

        Args:
            fault_type: 故障类型
            magnitude: 故障幅值
            stuck_value: 卡死值（仅用于stuck故障）
        """
        self.fault_type = fault_type
        self.fault_magnitude = magnitude

        if fault_type == FaultType.STUCK:
            self.stuck_value = stuck_value if stuck_value is not None else self.measured_value
            self.status = SensorStatus.STUCK

        elif fault_type == FaultType.DRIFT:
            self.status = SensorStatus.DRIFT

        elif fault_type == FaultType.NOISE:
            self.status = SensorStatus.NOISE

        elif fault_type == FaultType.COMPLETE_FAILURE:
            self.status = SensorStatus.FAILED

        else:
            self.status = SensorStatus.DEGRADED

    def clear_fault(self):
        """清除故障"""
        self.fault_type = FaultType.NONE
        self.fault_magnitude = 0.0
        self.status = SensorStatus.NORMAL
        self.drift_accumulated = 0.0

    def _record_history(self, current_time: float):
        """记录历史数据"""
        self.history['time'].append(current_time)
        self.history['raw'].append(self.raw_value)
        self.history['measured'].append(self.measured_value)
        self.history['filtered'].append(self.filtered_value)
        self.history['status'].append(self.status.value)

    def get_health_score(self) -> float:
        """获取健康评分 (0-1)"""
        if self.status == SensorStatus.NORMAL:
            return 1.0
        elif self.status == SensorStatus.DEGRADED:
            return 0.7
        elif self.status in [SensorStatus.DRIFT, SensorStatus.NOISE]:
            return 0.5
        elif self.status == SensorStatus.STUCK:
            return 0.2
        elif self.status == SensorStatus.FAILED:
            return 0.0
        return 0.5


class PressureSensor(SensorBase):
    """压力传感器"""

    def __init__(
        self,
        name: str = "pressure",
        range_max: float = 10.0,  # MPa
        accuracy: float = 0.005,
    ):
        params = SensorParams(
            name=name,
            unit="MPa",
            range_min=0.0,
            range_max=range_max,
            accuracy=accuracy,
            resolution=0.0001,
            time_constant=0.02,
            sample_rate=1000.0,
            noise_std=0.0005,
        )
        super().__init__(params)


class FlowSensor(SensorBase):
    """流量传感器"""

    def __init__(
        self,
        name: str = "flow",
        range_max: float = 300.0,  # m³/s
        accuracy: float = 0.01,
    ):
        params = SensorParams(
            name=name,
            unit="m³/s",
            range_min=0.0,
            range_max=range_max,
            accuracy=accuracy,
            resolution=0.01,
            time_constant=0.1,
            sample_rate=100.0,
            noise_std=0.002,
        )
        super().__init__(params)


class LevelSensor(SensorBase):
    """水位传感器"""

    def __init__(
        self,
        name: str = "level",
        range_min: float = 0.0,
        range_max: float = 200.0,  # m
        accuracy: float = 0.001,
    ):
        params = SensorParams(
            name=name,
            unit="m",
            range_min=range_min,
            range_max=range_max,
            accuracy=accuracy,
            resolution=0.001,
            time_constant=0.5,
            sample_rate=10.0,
            noise_std=0.0002,
        )
        super().__init__(params)


class SpeedSensor(SensorBase):
    """转速传感器"""

    def __init__(
        self,
        name: str = "speed",
        range_max: float = 500.0,  # r/min
        accuracy: float = 0.001,
    ):
        params = SensorParams(
            name=name,
            unit="r/min",
            range_min=0.0,
            range_max=range_max,
            accuracy=accuracy,
            resolution=0.01,
            time_constant=0.01,
            sample_rate=1000.0,
            noise_std=0.0001,
        )
        super().__init__(params)


class PowerSensor(SensorBase):
    """功率传感器"""

    def __init__(
        self,
        name: str = "power",
        range_max: float = 1200.0,  # MW
        accuracy: float = 0.005,
    ):
        params = SensorParams(
            name=name,
            unit="MW",
            range_min=-100.0,  # 允许电动状态
            range_max=range_max,
            accuracy=accuracy,
            resolution=0.01,
            time_constant=0.05,
            sample_rate=100.0,
            noise_std=0.001,
        )
        super().__init__(params)


class TemperatureSensor(SensorBase):
    """温度传感器"""

    def __init__(
        self,
        name: str = "temperature",
        range_min: float = -20.0,  # °C
        range_max: float = 150.0,  # °C
        accuracy: float = 0.01,
    ):
        params = SensorParams(
            name=name,
            unit="°C",
            range_min=range_min,
            range_max=range_max,
            accuracy=accuracy,
            resolution=0.1,
            time_constant=5.0,  # 温度传感器响应慢
            sample_rate=1.0,
            noise_std=0.005,
        )
        super().__init__(params)


class VibrationSensor(SensorBase):
    """振动传感器"""

    def __init__(
        self,
        name: str = "vibration",
        range_max: float = 500.0,  # μm
        accuracy: float = 0.02,
    ):
        params = SensorParams(
            name=name,
            unit="μm",
            range_min=0.0,
            range_max=range_max,
            accuracy=accuracy,
            resolution=0.1,
            time_constant=0.001,
            sample_rate=10000.0,  # 高频采样
            noise_std=0.01,
        )
        super().__init__(params)


class PositionSensor(SensorBase):
    """位置传感器（用于导叶开度等）"""

    def __init__(
        self,
        name: str = "position",
        range_min: float = 0.0,   # %
        range_max: float = 100.0,  # %
        accuracy: float = 0.005,
    ):
        params = SensorParams(
            name=name,
            unit="%",
            range_min=range_min,
            range_max=range_max,
            accuracy=accuracy,
            resolution=0.01,
            time_constant=0.01,
            sample_rate=500.0,
            noise_std=0.0005,
        )
        super().__init__(params)


class SensorArray:
    """传感器阵列管理类"""

    def __init__(self):
        self.sensors: Dict[str, SensorBase] = {}

    def add_sensor(self, sensor_id: str, sensor: SensorBase):
        """添加传感器"""
        self.sensors[sensor_id] = sensor

    def remove_sensor(self, sensor_id: str):
        """移除传感器"""
        if sensor_id in self.sensors:
            del self.sensors[sensor_id]

    def measure_all(
        self,
        true_values: Dict[str, float],
        current_time: float,
        dt: float
    ) -> Dict[str, float]:
        """测量所有传感器"""
        measurements = {}
        for sensor_id, sensor in self.sensors.items():
            if sensor_id in true_values:
                measurements[sensor_id] = sensor.measure(
                    true_values[sensor_id],
                    current_time,
                    dt
                )
        return measurements

    def get_all_status(self) -> Dict[str, SensorStatus]:
        """获取所有传感器状态"""
        return {
            sensor_id: sensor.status
            for sensor_id, sensor in self.sensors.items()
        }

    def get_health_report(self) -> Dict[str, Dict]:
        """获取健康报告"""
        report = {}
        for sensor_id, sensor in self.sensors.items():
            report[sensor_id] = {
                'name': sensor.params.name,
                'status': sensor.status.value,
                'health_score': sensor.get_health_score(),
                'fault_type': sensor.fault_type.value,
                'current_value': sensor.measured_value,
            }
        return report
