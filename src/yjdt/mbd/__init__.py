# -*- coding: utf-8 -*-
"""
MBD (Model-Based Design) - 模型驱动设计模块

面向YX工程的模型驱动设计与参数优化

核心功能:
- 基础模型驱动设计
- 高级多目标优化
- 鲁棒性优化
- ODD约束设计
- 设计空间探索
- 雅江工程全覆盖优化设计
- 优化算法框架与自动选择
- 设计-仿真验证-反馈闭环
"""

from .model_based_design import (
    # 枚举类型
    DesignObjective,
    ParameterType,
    OptimizationMethod,

    # 数据类
    DesignParameter,
    DesignScheme,
    OptimizationResult,
    SensitivityResult,

    # 模型类
    SystemModel,
    CascadeHydropowerModel,

    # 优化器
    ParameterOptimizer,
    SensitivityAnalyzer,
    ReverseDesignOptimizer,

    # 工厂函数
    create_yajiang_mbd_model,
)

from .advanced_optimization import (
    # 枚举类型
    OptimizationObjective,
    DesignSpaceType,
    RobustnessLevel,

    # 数据类
    DesignVariable,
    ObjectiveFunction,
    DesignConstraint,
    ParetoSolution,
    OptimizationResult as AdvancedOptimizationResult,

    # 多目标优化器
    MultiObjectiveOptimizer,

    # 鲁棒性优化
    RobustnessOptimizer,

    # ODD约束设计
    ODDConstrainedDesigner,

    # 设计空间探索
    DesignSpaceExplorer,

    # 工厂函数
    create_cascade_optimization_problem,
)

from .yajiang_optimization_design import (
    # 水力系统优化
    HydraulicSystemOptimizer,
    # 机电设备优化
    ElectromechanicalOptimizer,
    # 控制系统优化
    ControlSystemOptimizer,
    # 级联协调优化
    CascadeCoordinationOptimizer,
    # 安全保护优化
    SafetyProtectionOptimizer,
    # 过渡过程优化
    TransientProcessOptimizer,
    # 运行工况优化
    OperatingConditionOptimizer,
    # 经济性优化
    EconomicOptimizer,
    # 综合优化器
    YajiangMBDOptimizer,
    create_yajiang_mbd_optimizer,
)

from .optimization_framework import (
    # 枚举
    OptimizationAlgorithm,
    ProblemType,
    FlexibilityMetrics,
    SafetyMetrics,
    # 数据类
    OptimizationProblem,
    AlgorithmConfig,
    VerificationResult,
    DesignFeedback,
    # 算法选择
    AlgorithmSelector,
    # 统一优化器
    UnifiedOptimizer,
    # 设计闭环
    DesignVerificationLoop,
    # 灵活性优化
    FlexibilityOptimizer,
    # 安全性优化
    SafetyOptimizer,
    # 综合框架
    IntegratedOptimizationFramework,
)

from .simulation_verification_integration import (
    # 枚举
    VerificationStatus,
    DesignStage,
    VerificationLevel,
    # 数据类
    DesignToSimulationMapping,
    SimulationScenario,
    SimulationResult,
    VerificationCriterion,
    VerificationOutcome,
    DesignVerificationReport,
    # 核心类
    DesignParameterMapper,
    SimulationScenarioLibrary,
    VerificationCriteriaManager,
    SimulationExecutor,
    MBDSimulationVerificationIntegrator,
    # 工厂函数
    create_yajiang_verification_integrator,
)

__all__ = [
    # 基础MBD
    "DesignObjective",
    "ParameterType",
    "OptimizationMethod",
    "DesignParameter",
    "DesignScheme",
    "OptimizationResult",
    "SensitivityResult",
    "SystemModel",
    "CascadeHydropowerModel",
    "ParameterOptimizer",
    "SensitivityAnalyzer",
    "ReverseDesignOptimizer",
    "create_yajiang_mbd_model",

    # 高级优化
    "OptimizationObjective",
    "DesignSpaceType",
    "RobustnessLevel",
    "DesignVariable",
    "ObjectiveFunction",
    "DesignConstraint",
    "ParetoSolution",
    "AdvancedOptimizationResult",
    "MultiObjectiveOptimizer",
    "RobustnessOptimizer",
    "ODDConstrainedDesigner",
    "DesignSpaceExplorer",
    "create_cascade_optimization_problem",

    # 雅江工程优化设计
    "HydraulicSystemOptimizer",
    "ElectromechanicalOptimizer",
    "ControlSystemOptimizer",
    "CascadeCoordinationOptimizer",
    "SafetyProtectionOptimizer",
    "TransientProcessOptimizer",
    "OperatingConditionOptimizer",
    "EconomicOptimizer",
    "YajiangMBDOptimizer",
    "create_yajiang_mbd_optimizer",

    # 优化框架
    "OptimizationAlgorithm",
    "ProblemType",
    "FlexibilityMetrics",
    "SafetyMetrics",
    "OptimizationProblem",
    "AlgorithmConfig",
    "VerificationResult",
    "DesignFeedback",
    "AlgorithmSelector",
    "UnifiedOptimizer",
    "DesignVerificationLoop",
    "FlexibilityOptimizer",
    "SafetyOptimizer",
    "IntegratedOptimizationFramework",

    # 仿真验证集成
    "VerificationStatus",
    "DesignStage",
    "VerificationLevel",
    "DesignToSimulationMapping",
    "SimulationScenario",
    "SimulationResult",
    "VerificationCriterion",
    "VerificationOutcome",
    "DesignVerificationReport",
    "DesignParameterMapper",
    "SimulationScenarioLibrary",
    "VerificationCriteriaManager",
    "SimulationExecutor",
    "MBDSimulationVerificationIntegrator",
    "create_yajiang_verification_integrator",
]
