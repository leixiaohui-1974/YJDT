# -*- coding: utf-8 -*-
"""
数字孪生引擎 - 物理实体的虚拟映射
Digital Twin Engine - Virtual Mapping of Physical Entity

功能：
- 多模型融合（水力/机械/电气/热力）
- 实时数据同步
- 状态一致性校验
- 模型自适应校正
- 置信度评估
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime, timedelta
import threading


class SyncMode(Enum):
    """同步模式"""
    REALTIME = "realtime"           # 实时同步（<100ms）
    PERIODIC = "periodic"           # 周期同步（1s）
    ON_DEMAND = "on_demand"         # 按需同步
    PREDICTIVE = "predictive"       # 预测同步


class TwinAccuracy(Enum):
    """孪生精度等级"""
    HIGH = "high"                   # 高精度（误差<1%）
    MEDIUM = "medium"               # 中精度（误差<5%）
    LOW = "low"                     # 低精度（误差<10%）
    DEGRADED = "degraded"           # 降级（误差>10%）


@dataclass
class TwinState:
    """孪生状态"""
    # 水力状态
    upstream_level: float = 2100.0      # 上游水位 (m)
    downstream_level: float = 1550.0    # 下游水位 (m)
    head: float = 550.0                 # 净水头 (m)
    flow_rate: float = 200.0            # 流量 (m³/s)
    penstock_pressure: float = 5.0      # 压力钢管压力 (MPa)
    surge_tank_level: float = 2100.0    # 调压室水位 (m)

    # 机械状态
    speed: float = 100.0                # 转速 (rpm)
    guide_vane_opening: float = 0.8     # 导叶开度 (0-1)
    mechanical_power: float = 800.0     # 机械功率 (MW)
    vibration_x: float = 50.0           # X方向振动 (μm)
    vibration_y: float = 50.0           # Y方向振动 (μm)
    bearing_temp: float = 55.0          # 轴承温度 (℃)

    # 电气状态
    active_power: float = 800.0         # 有功功率 (MW)
    reactive_power: float = 100.0       # 无功功率 (Mvar)
    voltage: float = 20.0               # 端电压 (kV)
    current: float = 15.0               # 定子电流 (kA)
    frequency: float = 50.0             # 频率 (Hz)
    power_factor: float = 0.99          # 功率因数
    excitation_current: float = 2500.0  # 励磁电流 (A)

    # 热力状态
    stator_temp: float = 85.0           # 定子温度 (℃)
    rotor_temp: float = 75.0            # 转子温度 (℃)
    cooling_water_temp: float = 25.0    # 冷却水温度 (℃)
    oil_temp: float = 45.0              # 油温 (℃)

    # 元信息
    timestamp: datetime = field(default_factory=datetime.now)
    accuracy: TwinAccuracy = TwinAccuracy.HIGH
    confidence: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hydraulic": {
                "upstream_level": self.upstream_level,
                "downstream_level": self.downstream_level,
                "head": self.head,
                "flow_rate": self.flow_rate,
                "penstock_pressure": self.penstock_pressure,
                "surge_tank_level": self.surge_tank_level,
            },
            "mechanical": {
                "speed": self.speed,
                "guide_vane_opening": self.guide_vane_opening,
                "mechanical_power": self.mechanical_power,
                "vibration_x": self.vibration_x,
                "vibration_y": self.vibration_y,
                "bearing_temp": self.bearing_temp,
            },
            "electrical": {
                "active_power": self.active_power,
                "reactive_power": self.reactive_power,
                "voltage": self.voltage,
                "current": self.current,
                "frequency": self.frequency,
                "power_factor": self.power_factor,
                "excitation_current": self.excitation_current,
            },
            "thermal": {
                "stator_temp": self.stator_temp,
                "rotor_temp": self.rotor_temp,
                "cooling_water_temp": self.cooling_water_temp,
                "oil_temp": self.oil_temp,
            },
            "meta": {
                "timestamp": self.timestamp.isoformat(),
                "accuracy": self.accuracy.value,
                "confidence": self.confidence,
            }
        }

    def copy(self) -> 'TwinState':
        """创建副本"""
        return TwinState(
            upstream_level=self.upstream_level,
            downstream_level=self.downstream_level,
            head=self.head,
            flow_rate=self.flow_rate,
            penstock_pressure=self.penstock_pressure,
            surge_tank_level=self.surge_tank_level,
            speed=self.speed,
            guide_vane_opening=self.guide_vane_opening,
            mechanical_power=self.mechanical_power,
            vibration_x=self.vibration_x,
            vibration_y=self.vibration_y,
            bearing_temp=self.bearing_temp,
            active_power=self.active_power,
            reactive_power=self.reactive_power,
            voltage=self.voltage,
            current=self.current,
            frequency=self.frequency,
            power_factor=self.power_factor,
            excitation_current=self.excitation_current,
            stator_temp=self.stator_temp,
            rotor_temp=self.rotor_temp,
            cooling_water_temp=self.cooling_water_temp,
            oil_temp=self.oil_temp,
            timestamp=datetime.now(),
            accuracy=self.accuracy,
            confidence=self.confidence,
        )


class DigitalTwinEngine:
    """
    数字孪生引擎

    功能：
    - 物理模型实时镜像
    - 多源数据融合
    - 状态估计与预测
    - 模型自校正
    - 异常检测与诊断
    """

    def __init__(self, unit_id: str = "YJ_UNIT_001"):
        self.unit_id = unit_id
        self.current_state = TwinState()
        self.predicted_state = TwinState()
        self.historical_states: List[TwinState] = []

        self.sync_mode = SyncMode.REALTIME
        self.is_running = False
        self._lock = threading.Lock()

        # 模型参数
        self.model_params = {
            # 水轮机参数
            "rated_power": 1000.0,          # MW
            "rated_head": 480.0,            # m
            "rated_speed": 100.0,           # rpm
            "rated_flow": 230.0,            # m³/s
            "efficiency_peak": 0.94,

            # 发电机参数
            "rated_voltage": 20.0,          # kV
            "rated_current": 23.1,          # kA
            "rated_power_factor": 0.9,
            "inertia_constant": 8.0,        # s

            # 水力参数
            "water_time_constant": 12.0,    # s
            "penstock_length": 25000.0,     # m
            "penstock_area": 80.0,          # m²
        }

        # 校正系数
        self.correction_factors = {
            "power": 1.0,
            "flow": 1.0,
            "efficiency": 1.0,
        }

        # 误差统计
        self.error_stats = {
            "power_rmse": 0.0,
            "speed_rmse": 0.0,
            "flow_rmse": 0.0,
            "last_calibration": None,
        }

    def update_from_measurements(self, measurements: Dict[str, float]) -> TwinState:
        """
        根据测量值更新孪生状态

        Args:
            measurements: 测量值字典

        Returns:
            更新后的孪生状态
        """
        with self._lock:
            # 更新直接测量值
            if "upstream_level" in measurements:
                self.current_state.upstream_level = measurements["upstream_level"]
            if "downstream_level" in measurements:
                self.current_state.downstream_level = measurements["downstream_level"]
            if "speed" in measurements:
                self.current_state.speed = measurements["speed"]
            if "guide_vane_opening" in measurements:
                self.current_state.guide_vane_opening = measurements["guide_vane_opening"]
            if "active_power" in measurements:
                self.current_state.active_power = measurements["active_power"]
            if "reactive_power" in measurements:
                self.current_state.reactive_power = measurements["reactive_power"]
            if "voltage" in measurements:
                self.current_state.voltage = measurements["voltage"]
            if "current" in measurements:
                self.current_state.current = measurements["current"]
            if "frequency" in measurements:
                self.current_state.frequency = measurements["frequency"]
            if "bearing_temp" in measurements:
                self.current_state.bearing_temp = measurements["bearing_temp"]
            if "stator_temp" in measurements:
                self.current_state.stator_temp = measurements["stator_temp"]

            # 计算派生量
            self._calculate_derived_values()

            # 更新时间戳和置信度
            self.current_state.timestamp = datetime.now()
            self.current_state.confidence = self._calculate_confidence(measurements)
            self.current_state.accuracy = self._evaluate_accuracy()

            # 保存历史
            self.historical_states.append(self.current_state.copy())
            if len(self.historical_states) > 3600:
                self.historical_states = self.historical_states[-3600:]

            return self.current_state

    def _calculate_derived_values(self):
        """计算派生值（基于物理模型）"""
        state = self.current_state
        params = self.model_params

        # 计算净水头
        state.head = state.upstream_level - state.downstream_level

        # 计算压力钢管压力 (静压)
        state.penstock_pressure = state.head * 9.81 * 1000 / 1e6  # MPa

        # 估算流量 (基于功率和水头)
        if state.head > 0 and state.active_power > 0:
            # P = ρgQHη
            # Q = P / (ρgHη)
            efficiency = self._estimate_efficiency(state.guide_vane_opening, state.head)
            rho = 1000  # kg/m³
            g = 9.81    # m/s²
            state.flow_rate = (state.active_power * 1e6) / (rho * g * state.head * efficiency)
            state.flow_rate *= self.correction_factors["flow"]

        # 估算机械功率
        if state.head > 0:
            efficiency = self._estimate_efficiency(state.guide_vane_opening, state.head)
            rho = 1000
            g = 9.81
            state.mechanical_power = rho * g * state.flow_rate * state.head * efficiency / 1e6
            state.mechanical_power *= self.correction_factors["power"]

        # 计算功率因数
        apparent_power = np.sqrt(state.active_power**2 + state.reactive_power**2)
        if apparent_power > 0:
            state.power_factor = state.active_power / apparent_power

        # 估算励磁电流 (简化模型)
        state.excitation_current = 2000 + 1000 * state.reactive_power / 200

    def _estimate_efficiency(self, opening: float, head: float) -> float:
        """估算水轮机效率"""
        # 简化的效率曲线模型
        peak_efficiency = self.model_params["efficiency_peak"]
        rated_head = self.model_params["rated_head"]

        # 开度影响
        opening_factor = 1 - 0.3 * (opening - 0.8)**2

        # 水头影响
        head_ratio = head / rated_head
        head_factor = 1 - 0.2 * (head_ratio - 1)**2

        efficiency = peak_efficiency * opening_factor * head_factor
        efficiency *= self.correction_factors["efficiency"]

        return np.clip(efficiency, 0.5, 0.96)

    def _calculate_confidence(self, measurements: Dict[str, float]) -> float:
        """计算置信度"""
        # 基于测量点数量和质量
        base_confidence = 0.7
        measurement_bonus = len(measurements) * 0.02
        return min(base_confidence + measurement_bonus, 0.99)

    def _evaluate_accuracy(self) -> TwinAccuracy:
        """评估精度等级"""
        confidence = self.current_state.confidence

        if confidence >= 0.95:
            return TwinAccuracy.HIGH
        elif confidence >= 0.85:
            return TwinAccuracy.MEDIUM
        elif confidence >= 0.70:
            return TwinAccuracy.LOW
        else:
            return TwinAccuracy.DEGRADED

    def predict(self, horizon: float, control_inputs: Optional[Dict[str, float]] = None) -> TwinState:
        """
        预测未来状态

        Args:
            horizon: 预测时长(秒)
            control_inputs: 控制输入变化

        Returns:
            预测状态
        """
        predicted = self.current_state.copy()
        control_inputs = control_inputs or {}

        # 应用控制输入
        if "guide_vane_opening" in control_inputs:
            target_opening = control_inputs["guide_vane_opening"]
            # 导叶动作时间约5秒
            opening_rate = 0.2  # per second
            delta = target_opening - predicted.guide_vane_opening
            predicted.guide_vane_opening += np.sign(delta) * min(abs(delta), opening_rate * horizon)

        if "excitation_voltage" in control_inputs:
            # 励磁调节响应
            pass

        # 预测功率变化
        if "power_setpoint" in control_inputs:
            target_power = control_inputs["power_setpoint"]
            # 功率响应时间常数约10秒
            tau = 10.0
            predicted.active_power += (target_power - predicted.active_power) * (1 - np.exp(-horizon/tau))

        # 预测温度变化
        # 简化热模型：温度趋向于与功率相关的稳态值
        steady_state_bearing_temp = 45 + 20 * predicted.active_power / 1000
        tau_thermal = 300.0  # 热时间常数5分钟
        predicted.bearing_temp += (steady_state_bearing_temp - predicted.bearing_temp) * (1 - np.exp(-horizon/tau_thermal))

        steady_state_stator_temp = 60 + 40 * predicted.active_power / 1000
        predicted.stator_temp += (steady_state_stator_temp - predicted.stator_temp) * (1 - np.exp(-horizon/tau_thermal))

        # 重新计算派生量
        state_backup = self.current_state
        self.current_state = predicted
        self._calculate_derived_values()
        predicted = self.current_state
        self.current_state = state_backup

        predicted.timestamp = datetime.now() + timedelta(seconds=horizon)
        predicted.confidence *= 0.9  # 预测置信度衰减

        self.predicted_state = predicted
        return predicted

    def calibrate(self, actual_measurements: Dict[str, float]) -> Dict[str, float]:
        """
        校正模型参数

        Args:
            actual_measurements: 实际测量值

        Returns:
            校正系数
        """
        errors = {}

        # 功率校正
        if "active_power" in actual_measurements and self.current_state.active_power > 0:
            actual_power = actual_measurements["active_power"]
            predicted_power = self.current_state.mechanical_power
            if predicted_power > 0:
                power_error = (actual_power - predicted_power) / predicted_power
                self.correction_factors["power"] *= (1 + power_error * 0.1)  # 渐进校正
                errors["power"] = power_error

        # 流量校正
        if "flow_rate" in actual_measurements and self.current_state.flow_rate > 0:
            actual_flow = actual_measurements["flow_rate"]
            predicted_flow = self.current_state.flow_rate
            flow_error = (actual_flow - predicted_flow) / predicted_flow
            self.correction_factors["flow"] *= (1 + flow_error * 0.1)
            errors["flow"] = flow_error

        # 更新误差统计
        self.error_stats["last_calibration"] = datetime.now()

        return errors

    def run_what_if(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行假设场景分析

        Args:
            scenario: 场景定义

        Returns:
            分析结果
        """
        # 保存当前状态
        original_state = self.current_state.copy()

        # 应用场景条件
        if "initial_conditions" in scenario:
            for key, value in scenario["initial_conditions"].items():
                if hasattr(self.current_state, key):
                    setattr(self.current_state, key, value)

        # 运行仿真
        results = []
        horizon = scenario.get("duration", 60)
        dt = scenario.get("dt", 1.0)
        steps = int(horizon / dt)

        control_sequence = scenario.get("control_sequence", [])
        control_idx = 0

        for step in range(steps):
            t = step * dt

            # 应用控制序列
            control_inputs = {}
            while control_idx < len(control_sequence):
                ctrl = control_sequence[control_idx]
                if ctrl["time"] <= t:
                    control_inputs.update(ctrl.get("inputs", {}))
                    control_idx += 1
                else:
                    break

            # 预测下一步
            predicted = self.predict(dt, control_inputs)

            results.append({
                "time": t,
                "state": predicted.to_dict(),
            })

            self.current_state = predicted

        # 恢复原状态
        self.current_state = original_state

        # 分析结果
        analysis = self._analyze_scenario_results(results, scenario)

        return {
            "scenario": scenario,
            "results": results,
            "analysis": analysis,
        }

    def _analyze_scenario_results(self, results: List[Dict],
                                  scenario: Dict) -> Dict[str, Any]:
        """分析场景结果"""
        if not results:
            return {}

        powers = [r["state"]["electrical"]["active_power"] for r in results]
        speeds = [r["state"]["mechanical"]["speed"] for r in results]
        temps = [r["state"]["thermal"]["bearing_temp"] for r in results]

        analysis = {
            "power": {
                "min": min(powers),
                "max": max(powers),
                "final": powers[-1],
            },
            "speed": {
                "min": min(speeds),
                "max": max(speeds),
                "deviation": max(abs(s - 100) for s in speeds),
            },
            "temperature": {
                "max": max(temps),
                "final": temps[-1],
            },
            "safety": {
                "overspeed": any(s > 120 for s in speeds),
                "overtemp": any(t > 80 for t in temps),
            }
        }

        return analysis

    def get_state(self) -> TwinState:
        """获取当前状态"""
        return self.current_state

    def get_state_history(self, duration: float = 3600) -> List[TwinState]:
        """获取历史状态"""
        cutoff = datetime.now() - timedelta(seconds=duration)
        return [s for s in self.historical_states if s.timestamp >= cutoff]

    def compare_with_physical(self, physical_measurements: Dict[str, float]) -> Dict[str, Any]:
        """
        与物理实体比较

        Args:
            physical_measurements: 物理测量值

        Returns:
            差异分析
        """
        differences = {}
        state = self.current_state

        comparisons = [
            ("active_power", state.active_power, "MW"),
            ("speed", state.speed, "rpm"),
            ("flow_rate", state.flow_rate, "m³/s"),
            ("voltage", state.voltage, "kV"),
            ("bearing_temp", state.bearing_temp, "℃"),
        ]

        for name, twin_value, unit in comparisons:
            if name in physical_measurements:
                physical_value = physical_measurements[name]
                diff = twin_value - physical_value
                rel_diff = diff / physical_value * 100 if physical_value != 0 else 0

                differences[name] = {
                    "twin_value": twin_value,
                    "physical_value": physical_value,
                    "difference": diff,
                    "relative_difference_percent": rel_diff,
                    "unit": unit,
                    "status": "good" if abs(rel_diff) < 5 else "warning" if abs(rel_diff) < 10 else "error"
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "differences": differences,
            "overall_accuracy": self.current_state.accuracy.value,
        }
