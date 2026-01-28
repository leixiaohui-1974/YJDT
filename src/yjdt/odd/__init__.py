# -*- coding: utf-8 -*-
"""
ODD (Operational Design Domain) - 设计运行域模块

面向YX工程有压五梯级系统的系统级ODD定义与验证

核心功能:
- ODD边界定义与管理
- 规则驱动的ODD扫描与识别
- ODD状态机管理
- ODD覆盖率分析
- ODD违规检测与预警
"""

from .operational_design_domain import (
    # 枚举类型
    ODDBoundaryType,
    ODDZone,
    DegradationLevel,

    # 数据类
    BoundaryLimit,
    TransientBoundary,
    CascadeBoundary,
    StationODD,
    SystemODDState,

    # 核心类
    SystemODD,
    ODDValidator,

    # 工厂函数
    create_yajiang_bigbend_odd,
)

from .odd_identification import (
    # 枚举类型
    ODDRuleType,
    ODDScanMode,
    ODDViolationSeverity,
    ODDStateTransition,

    # 数据类
    ODDRule,
    ODDViolation,
    ODDScanResult,
    ODDState,

    # 规则引擎
    ODDRuleEngine,

    # 扫描器
    ODDScanner,

    # 状态机
    ODDStateMachine,

    # 覆盖率分析
    ODDCoverageAnalyzer,

    # 工厂函数
    create_default_odd_rules,
)

__all__ = [
    # 基础ODD
    "ODDBoundaryType",
    "ODDZone",
    "DegradationLevel",
    "BoundaryLimit",
    "TransientBoundary",
    "CascadeBoundary",
    "StationODD",
    "SystemODDState",
    "SystemODD",
    "ODDValidator",
    "create_yajiang_bigbend_odd",

    # ODD识别体系
    "ODDRuleType",
    "ODDScanMode",
    "ODDViolationSeverity",
    "ODDStateTransition",
    "ODDRule",
    "ODDViolation",
    "ODDScanResult",
    "ODDState",
    "ODDRuleEngine",
    "ODDScanner",
    "ODDStateMachine",
    "ODDCoverageAnalyzer",
    "create_default_odd_rules",
]
