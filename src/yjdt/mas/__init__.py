# -*- coding: utf-8 -*-
"""
MAS (Multi-Agent System) - 多智能体系统模块

ODD感知的多智能体运行控制系统

核心功能:
- ODD感知的智能体决策
- 多源指标聚合与场景生成
- 自适应目标函数管理
- 全自主运行控制
- 分层降级控制
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

from .autonomous_operation import (
    # 枚举类型
    AutonomyLevel,
    OperationMode as AutonomousOperationMode,
    DecisionPriority,

    # 数据类
    OperationContext,
    ControlAction,
    AutonomousDecision,

    # 控制器
    AutonomousController,
    ODDBoundaryGuard,
    AdaptiveObjectiveManager as AutonomousObjectiveManager,
    DegradationController,
    ZoneController,

    # 全自主MAS
    FullAutonomousMAS,

    # 工厂函数
    create_yajiang_autonomous_mas,
)

__all__ = [
    # ODD感知MAS
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

    # 全自主运行
    "AutonomyLevel",
    "AutonomousOperationMode",
    "DecisionPriority",
    "OperationContext",
    "ControlAction",
    "AutonomousDecision",
    "AutonomousController",
    "ODDBoundaryGuard",
    "AutonomousObjectiveManager",
    "DegradationController",
    "ZoneController",
    "FullAutonomousMAS",
    "create_yajiang_autonomous_mas",
]
