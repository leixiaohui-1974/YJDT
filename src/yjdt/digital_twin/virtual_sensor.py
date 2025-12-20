# -*- coding: utf-8 -*-
"""
虚拟传感器 - 软测量与传感器融合
Virtual Sensor - Soft Sensing and Sensor Fusion

功能：
- 软传感器（基于模型推算）
- 传感器冗余与投票
- 传感器故障检测
- 数据融合与重构
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime
from enum import Enum


class SensorStatus(Enum):
    """传感器状态"""
    NORMAL = "normal"
    DEGRADED = "degraded"
    FAULTY = "faulty"
    OFFLINE = "offline"


@dataclass
class VirtualMeasurement:
    """虚拟测量值"""
    name: str
    value: float
    unit: str
    confidence: float
    source: str                             # physical/virtual/fused
    timestamp: datetime = field(default_factory=datetime.now)
    quality: int = 100                      # 0-100


class SoftSensor:
    """
    软传感器

    基于物理模型或数据驱动模型估算难以直接测量的变量
    """

    def __init__(self, name: str, output_name: str, unit: str):
        self.name = name
        self.output_name = output_name
        self.unit = unit

        # 模型
        self.model: Optional[Callable] = None
        self.input_names: List[str] = []

        # 校正参数
        self.bias = 0.0
        self.gain = 1.0

        # 历史
        self.history: List[VirtualMeasurement] = []

    def set_model(self, model: Callable, input_names: List[str]):
        """设置软测量模型"""
        self.model = model
        self.input_names = input_names

    def calculate(self, inputs: Dict[str, float]) -> VirtualMeasurement:
        """计算软测量值"""
        if self.model is None:
            return VirtualMeasurement(
                name=self.output_name,
                value=0.0,
                unit=self.unit,
                confidence=0.0,
                source="virtual"
            )

        # 提取输入
        input_values = [inputs.get(name, 0.0) for name in self.input_names]

        # 计算
        try:
            raw_value = self.model(*input_values)
            value = self.gain * raw_value + self.bias
            confidence = 0.9  # 基础置信度
        except Exception as e:
            value = 0.0
            confidence = 0.0

        measurement = VirtualMeasurement(
            name=self.output_name,
            value=value,
            unit=self.unit,
            confidence=confidence,
            source="virtual"
        )

        self.history.append(measurement)
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

        return measurement

    def calibrate(self, measured_value: float, inputs: Dict[str, float]):
        """校正软传感器"""
        if self.model is None:
            return

        # 计算当前输出
        input_values = [inputs.get(name, 0.0) for name in self.input_names]
        try:
            predicted = self.model(*input_values)
            if abs(predicted) > 1e-6:
                # 更新增益
                self.gain = 0.9 * self.gain + 0.1 * measured_value / predicted
            # 更新偏置
            self.bias = 0.9 * self.bias + 0.1 * (measured_value - self.gain * predicted)
        except Exception:
            pass


class VirtualSensor:
    """
    虚拟传感器管理器

    管理多个软传感器和传感器融合
    """

    def __init__(self):
        self.soft_sensors: Dict[str, SoftSensor] = {}
        self.physical_sensors: Dict[str, Dict[str, Any]] = {}
        self.fused_values: Dict[str, VirtualMeasurement] = {}

        # 初始化标准软传感器
        self._initialize_soft_sensors()

    def _initialize_soft_sensors(self):
        """初始化水电站常用软传感器"""
        # 效率软传感器
        efficiency_sensor = SoftSensor("efficiency_sensor", "efficiency", "%")
        efficiency_sensor.set_model(
            lambda P, Q, H: (P * 1e6) / (1000 * 9.81 * Q * H) * 100 if Q * H > 0 else 0,
            ["active_power", "flow_rate", "head"]
        )
        self.soft_sensors["efficiency"] = efficiency_sensor

        # 空蚀系数软传感器
        sigma_sensor = SoftSensor("sigma_sensor", "cavitation_sigma", "-")
        sigma_sensor.set_model(
            lambda Hs, Hv, H: (10.33 - Hs - Hv) / H if H > 0 else 0,
            ["suction_head", "vapor_pressure_head", "head"]
        )
        self.soft_sensors["cavitation_sigma"] = sigma_sensor

        # 轴承剩余寿命软传感器
        bearing_rul_sensor = SoftSensor("bearing_rul", "bearing_rul", "hours")
        bearing_rul_sensor.set_model(
            lambda T, V: max(0, 50000 - 100 * (T - 50) - 50 * (V - 50)) if T > 0 else 50000,
            ["bearing_temp", "vibration"]
        )
        self.soft_sensors["bearing_rul"] = bearing_rul_sensor

        # 发电机损耗软传感器
        loss_sensor = SoftSensor("generator_loss", "generator_loss", "MW")
        loss_sensor.set_model(
            lambda Pm, Pe: Pm - Pe if Pm > Pe else 0,
            ["mechanical_power", "active_power"]
        )
        self.soft_sensors["generator_loss"] = loss_sensor

    def register_physical_sensor(self, sensor_id: str, config: Dict[str, Any]):
        """注册物理传感器"""
        self.physical_sensors[sensor_id] = {
            "config": config,
            "status": SensorStatus.NORMAL,
            "last_value": None,
            "last_update": None,
        }

    def update_physical_sensor(self, sensor_id: str, value: float,
                               quality: int = 100) -> Optional[VirtualMeasurement]:
        """更新物理传感器读数"""
        if sensor_id not in self.physical_sensors:
            return None

        sensor = self.physical_sensors[sensor_id]
        sensor["last_value"] = value
        sensor["last_update"] = datetime.now()
        sensor["quality"] = quality

        # 检测故障
        if quality < 50:
            sensor["status"] = SensorStatus.DEGRADED
        elif quality < 20:
            sensor["status"] = SensorStatus.FAULTY

        return VirtualMeasurement(
            name=sensor_id,
            value=value,
            unit=sensor["config"].get("unit", ""),
            confidence=quality / 100.0,
            source="physical",
            quality=quality
        )

    def get_soft_measurement(self, name: str,
                             inputs: Dict[str, float]) -> Optional[VirtualMeasurement]:
        """获取软测量值"""
        if name not in self.soft_sensors:
            return None

        return self.soft_sensors[name].calculate(inputs)

    def get_all_soft_measurements(self,
                                  inputs: Dict[str, float]) -> Dict[str, VirtualMeasurement]:
        """获取所有软测量值"""
        results = {}
        for name, sensor in self.soft_sensors.items():
            results[name] = sensor.calculate(inputs)
        return results


class SensorFusion:
    """
    传感器融合

    多传感器数据融合与质量评估
    """

    def __init__(self):
        self.sensors: Dict[str, List[Dict[str, Any]]] = {}  # 变量名 -> 传感器列表
        self.fusion_methods = {
            "weighted_average": self._weighted_average,
            "voting": self._voting,
            "kalman": self._kalman_fusion,
            "best_quality": self._best_quality,
        }

    def register_sensor(self, variable: str, sensor_id: str,
                        weight: float = 1.0, priority: int = 0):
        """注册传感器到变量"""
        if variable not in self.sensors:
            self.sensors[variable] = []

        self.sensors[variable].append({
            "sensor_id": sensor_id,
            "weight": weight,
            "priority": priority,
            "last_value": None,
            "last_quality": 100,
        })

    def update_sensor(self, sensor_id: str, value: float, quality: int = 100):
        """更新传感器值"""
        for variable, sensor_list in self.sensors.items():
            for sensor in sensor_list:
                if sensor["sensor_id"] == sensor_id:
                    sensor["last_value"] = value
                    sensor["last_quality"] = quality

    def fuse(self, variable: str, method: str = "weighted_average") -> Optional[VirtualMeasurement]:
        """融合传感器数据"""
        if variable not in self.sensors:
            return None

        sensor_list = self.sensors[variable]
        valid_sensors = [s for s in sensor_list if s["last_value"] is not None and s["last_quality"] > 20]

        if not valid_sensors:
            return None

        fusion_fn = self.fusion_methods.get(method, self._weighted_average)
        value, confidence = fusion_fn(valid_sensors)

        return VirtualMeasurement(
            name=variable,
            value=value,
            unit="",
            confidence=confidence,
            source="fused"
        )

    def _weighted_average(self, sensors: List[Dict]) -> Tuple[float, float]:
        """加权平均融合"""
        total_weight = 0.0
        weighted_sum = 0.0

        for sensor in sensors:
            weight = sensor["weight"] * sensor["last_quality"] / 100.0
            weighted_sum += sensor["last_value"] * weight
            total_weight += weight

        if total_weight > 0:
            value = weighted_sum / total_weight
            confidence = min(total_weight / len(sensors), 1.0)
        else:
            value = 0.0
            confidence = 0.0

        return value, confidence

    def _voting(self, sensors: List[Dict]) -> Tuple[float, float]:
        """投票融合（中值）"""
        values = [s["last_value"] for s in sensors]
        value = float(np.median(values))

        # 计算一致性作为置信度
        std = np.std(values)
        mean = np.mean(values)
        cv = std / abs(mean) if mean != 0 else 1.0
        confidence = max(0, 1 - cv)

        return value, confidence

    def _kalman_fusion(self, sensors: List[Dict]) -> Tuple[float, float]:
        """卡尔曼融合"""
        # 简化实现：使用方差倒数加权
        variances = [(100 - s["last_quality"]) / 100.0 + 0.01 for s in sensors]
        weights = [1.0 / v for v in variances]
        total_weight = sum(weights)

        value = sum(s["last_value"] * w for s, w in zip(sensors, weights)) / total_weight
        fused_variance = 1.0 / total_weight
        confidence = 1.0 - min(fused_variance, 1.0)

        return value, confidence

    def _best_quality(self, sensors: List[Dict]) -> Tuple[float, float]:
        """选择最佳质量传感器"""
        best = max(sensors, key=lambda s: s["last_quality"])
        return best["last_value"], best["last_quality"] / 100.0

    def detect_faulty_sensor(self, variable: str, threshold: float = 2.0) -> List[str]:
        """检测故障传感器"""
        if variable not in self.sensors:
            return []

        sensor_list = self.sensors[variable]
        valid_sensors = [s for s in sensor_list if s["last_value"] is not None]

        if len(valid_sensors) < 3:
            return []

        values = [s["last_value"] for s in valid_sensors]
        median = np.median(values)
        mad = np.median([abs(v - median) for v in values])

        faulty = []
        for sensor in valid_sensors:
            if mad > 0:
                deviation = abs(sensor["last_value"] - median) / mad
                if deviation > threshold:
                    faulty.append(sensor["sensor_id"])

        return faulty

    def get_redundancy_status(self, variable: str) -> Dict[str, Any]:
        """获取冗余状态"""
        if variable not in self.sensors:
            return {"error": "Variable not found"}

        sensor_list = self.sensors[variable]
        total = len(sensor_list)
        healthy = sum(1 for s in sensor_list if s["last_quality"] > 50)
        faulty = self.detect_faulty_sensor(variable)

        return {
            "variable": variable,
            "total_sensors": total,
            "healthy_sensors": healthy,
            "faulty_sensors": faulty,
            "redundancy_level": "high" if healthy >= 3 else "medium" if healthy >= 2 else "low",
        }
