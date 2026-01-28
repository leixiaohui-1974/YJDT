# -*- coding: utf-8 -*-
"""
MBD (Model-Based Design) - 模型驱动设计模块

面向YX工程的模型驱动设计与参数优化
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

__all__ = [
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
]
