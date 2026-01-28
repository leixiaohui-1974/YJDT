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
]
