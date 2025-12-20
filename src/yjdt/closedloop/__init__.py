# -*- coding: utf-8 -*-
"""
闭环仿真框架 - 本体仿真→数据同化→评价诊断→预测→调度→控制
Closed-Loop Simulation Framework

实现完整的智能控制闭环：
1. 本体仿真 (Physical Simulation) - 多物理场耦合仿真
2. 数据同化 (Data Assimilation) - 观测数据融合校正
3. 评价诊断 (Evaluation & Diagnosis) - 状态评估与故障诊断
4. 预测 (Prediction) - 短期/中期/长期预测
5. 调度 (Scheduling) - 优化调度决策
6. 控制 (Control) - 闭环控制执行

对标L0-L5智能化等级评价体系
"""

from yjdt.closedloop.physical_simulation import (
    PhysicalSimulator,
    MultiPhysicsModel,
    HydraulicDomain,
    MechanicalDomain,
    ElectricalDomain,
    ThermalDomain,
    DomainType,
    CouplingMatrix,
)

from yjdt.closedloop.data_assimilation import (
    DataAssimilator,
    EnsembleKalmanFilter,
    FourDVar,
    ParticleFilter,
    AssimilationResult,
    ObservationOperator,
    AssimilationMethod,
)

from yjdt.closedloop.evaluation_diagnosis import (
    StateEvaluator,
    FaultDiagnosisEngine,
    HealthIndex,
    DiagnosisResult,
    RootCauseAnalysis,
    HealthLevel,
)

from yjdt.closedloop.prediction_engine import (
    PredictionEngine,
    ShortTermPredictor,
    MediumTermPredictor,
    LongTermPredictor,
    UncertaintyQuantification,
    PredictionResult,
    PredictionHorizon,
)

from yjdt.closedloop.optimal_scheduling import (
    OptimalScheduler,
    AGCController,
    AVCController,
    CascadeSchedule,
    UnitSchedule,
    SchedulingHorizon,
    OptimizationObjective,
    SchedulingResult,
    SchedulingConstraint,
)

from yjdt.closedloop.control_executor import (
    ControlExecutor,
    ControlCommand,
    ControlFeedback,
    SafetyMonitor,
    InterlockCondition,
    ControlMode,
    CommandStatus,
    CommandPriority,
)

from yjdt.closedloop.closed_loop_coordinator import (
    ClosedLoopCoordinator,
    LoopState,
    LoopConfiguration,
    LoopCycleResult,
    InLoopTester,
)

__all__ = [
    # 本体仿真
    "PhysicalSimulator",
    "MultiPhysicsModel",
    "HydraulicDomain",
    "MechanicalDomain",
    "ElectricalDomain",
    "ThermalDomain",
    "DomainType",
    "CouplingMatrix",

    # 数据同化
    "DataAssimilator",
    "EnsembleKalmanFilter",
    "FourDVar",
    "ParticleFilter",
    "AssimilationResult",
    "ObservationOperator",
    "AssimilationMethod",

    # 评价诊断
    "StateEvaluator",
    "FaultDiagnosisEngine",
    "HealthIndex",
    "DiagnosisResult",
    "RootCauseAnalysis",
    "HealthLevel",

    # 预测
    "PredictionEngine",
    "ShortTermPredictor",
    "MediumTermPredictor",
    "LongTermPredictor",
    "UncertaintyQuantification",
    "PredictionResult",
    "PredictionHorizon",

    # 调度
    "OptimalScheduler",
    "AGCController",
    "AVCController",
    "CascadeSchedule",
    "UnitSchedule",
    "SchedulingHorizon",
    "OptimizationObjective",
    "SchedulingResult",
    "SchedulingConstraint",

    # 控制
    "ControlExecutor",
    "ControlCommand",
    "ControlFeedback",
    "SafetyMonitor",
    "InterlockCondition",
    "ControlMode",
    "CommandStatus",
    "CommandPriority",

    # 协调器
    "ClosedLoopCoordinator",
    "LoopState",
    "LoopConfiguration",
    "LoopCycleResult",
    "InLoopTester",
]
