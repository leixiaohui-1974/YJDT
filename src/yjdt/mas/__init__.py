# -*- coding: utf-8 -*-
"""
MAS (Multi-Agent System) - 多智能体系统模块

ODD感知的多智能体运行控制系统
"""

from .odd_aware_mas import (
    # 枚举类型
    AgentType,
    OperationMode,
    ScenarioType,

    # 数据类
    ObjectiveFunction,
    ODDScenario,
    AgentDecision,

    # 场景生成
    ODDScenarioGenerator,

    # 指标聚合
    MultiSourceIndicatorAggregator,

    # 目标函数管理
    AdaptiveObjectiveManager,

    # 智能体
    ODDAwareAgent,
    CentralCoordinatorAgent,
    StationControllerAgent,
    UnitControllerAgent,

    # MAS系统
    ODDAwareMASSystem,

    # 工厂函数
    create_yajiang_mas_system,
)

__all__ = [
    "AgentType",
    "OperationMode",
    "ScenarioType",
    "ObjectiveFunction",
    "ODDScenario",
    "AgentDecision",
    "ODDScenarioGenerator",
    "MultiSourceIndicatorAggregator",
    "AdaptiveObjectiveManager",
    "ODDAwareAgent",
    "CentralCoordinatorAgent",
    "StationControllerAgent",
    "UnitControllerAgent",
    "ODDAwareMASSystem",
    "create_yajiang_mas_system",
]
