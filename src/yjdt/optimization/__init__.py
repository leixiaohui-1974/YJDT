"""
设计优化模块
Design Optimization Module

对标无人驾驶汽车开发模式，实现：
- 多方案设计对比评估
- 传感器布设优化
- 设备选型优化
- 控制策略优化
- 全生命周期效益分析
"""

from yjdt.optimization.design_optimizer import (
    DesignOptimizer,
    DesignScheme,
    SchemeComparator,
    OptimizationResult,
)

from yjdt.optimization.sensor_placement import (
    SensorPlacementOptimizer,
    SensorConfiguration,
    ObservabilityAnalyzer,
)

from yjdt.optimization.equipment_selection import (
    EquipmentSelector,
    EquipmentDatabase,
    SelectionCriteria,
)

from yjdt.optimization.lifecycle import (
    LifecycleAnalyzer,
    CostBenefitAnalysis,
    ReliabilityAnalysis,
)

from yjdt.optimization.controller_tuning import (
    ControllerOptimizer,
    TuningMethod,
    PerformanceIndex,
)

__all__ = [
    "DesignOptimizer",
    "DesignScheme",
    "SchemeComparator",
    "OptimizationResult",
    "SensorPlacementOptimizer",
    "SensorConfiguration",
    "ObservabilityAnalyzer",
    "EquipmentSelector",
    "EquipmentDatabase",
    "SelectionCriteria",
    "LifecycleAnalyzer",
    "CostBenefitAnalysis",
    "ReliabilityAnalysis",
    "ControllerOptimizer",
    "TuningMethod",
    "PerformanceIndex",
]
