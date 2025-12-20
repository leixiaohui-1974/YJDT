# -*- coding: utf-8 -*-
"""
基础设施模块 - Infrastructure Components

功能：
- 统一数据总线
- 配置管理
- 事件驱动架构
- 日志管理
- 性能分析
"""

from yjdt.infrastructure.data_bus import (
    DataBus,
    Signal,
    Event,
    EventType,
    SignalQuality,
    Subscription,
)

from yjdt.infrastructure.config_manager import (
    ConfigManager,
    SystemConfig,
    ModuleConfig,
    ValidationError,
)

from yjdt.infrastructure.logging_manager import (
    configure_logging,
    get_logger,
    set_log_level,
    add_file_handler,
    log_performance,
    audit_log,
    LogContext,
    AuditLogger,
)

from yjdt.infrastructure.profiling_manager import (
    profile_function,
    PerformanceMonitor,
    PerformanceMetrics,
    FunctionProfiler,
    PerformanceCollector,
    PerformanceReport,
    start_profiling,
    stop_profiling,
    get_function_stats,
    get_top_functions,
    reset_profiling,
)

__all__ = [
    # 数据总线
    "DataBus",
    "Signal",
    "Event",
    "EventType",
    "SignalQuality",
    "Subscription",
    # 配置管理
    "ConfigManager",
    "SystemConfig",
    "ModuleConfig",
    "ValidationError",
    # 日志管理
    "configure_logging",
    "get_logger",
    "set_log_level",
    "add_file_handler",
    "log_performance",
    "audit_log",
    "LogContext",
    "AuditLogger",
    # 性能分析
    "profile_function",
    "PerformanceMonitor",
    "PerformanceMetrics",
    "FunctionProfiler",
    "PerformanceCollector",
    "PerformanceReport",
    "start_profiling",
    "stop_profiling",
    "get_function_stats",
    "get_top_functions",
    "reset_profiling",
]
