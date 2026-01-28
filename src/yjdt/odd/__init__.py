# -*- coding: utf-8 -*-
"""
ODD (Operational Design Domain) - 设计运行域模块

面向YX工程有压五梯级系统的系统级ODD定义与验证
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

__all__ = [
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
]
