# -*- coding: utf-8 -*-
"""
数字孪生模块 - 虚实融合智能运维
Digital Twin Module - Cyber-Physical Intelligent Operation

包含：
- 物理模型同步
- 实时状态估计
- 预测仿真
- 虚拟传感器
- 故障预演
- 优化决策支持

对标工业4.0数字孪生标准
"""

from yjdt.digital_twin.twin_engine import (
    DigitalTwinEngine,
    TwinState,
    SyncMode,
    TwinAccuracy,
)

from yjdt.digital_twin.state_estimator import (
    StateEstimator,
    KalmanFilter,
    ParticleFilter,
    EstimationResult,
)

from yjdt.digital_twin.virtual_sensor import (
    VirtualSensor,
    SoftSensor,
    SensorFusion,
    VirtualMeasurement,
)

from yjdt.digital_twin.predictive_simulation import (
    PredictiveSimulator,
    WhatIfScenario,
    SimulationResult,
    OptimizationObjective,
)

__all__ = [
    # 孪生引擎
    "DigitalTwinEngine",
    "TwinState",
    "SyncMode",
    "TwinAccuracy",

    # 状态估计
    "StateEstimator",
    "KalmanFilter",
    "ParticleFilter",
    "EstimationResult",

    # 虚拟传感器
    "VirtualSensor",
    "SoftSensor",
    "SensorFusion",
    "VirtualMeasurement",

    # 预测仿真
    "PredictiveSimulator",
    "WhatIfScenario",
    "SimulationResult",
    "OptimizationObjective",
]
