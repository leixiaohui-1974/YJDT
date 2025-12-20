# -*- coding: utf-8 -*-
"""
实时监控模块 - 全方位运行态势感知
Real-time Monitoring Module - Comprehensive Operational Awareness

包含：
- 实时数据采集与处理
- 多级报警管理系统
- 趋势分析与预警
- 运行状态可视化
- 历史数据记录与回放

对标工业4.0智能监控标准
"""

from yjdt.monitoring.realtime_monitor import (
    RealtimeMonitor,
    MonitoringPoint,
    DataAcquisition,
    SignalQuality,
    MonitoringStatus,
)

from yjdt.monitoring.alarm_manager import (
    AlarmManager,
    Alarm,
    AlarmLevel,
    AlarmType,
    AlarmState,
    AlarmHandler,
    AlarmEscalation,
)

from yjdt.monitoring.trend_analyzer import (
    TrendAnalyzer,
    TrendDirection,
    TrendAlert,
    PredictiveAlert,
    AnomalyScore,
)

from yjdt.monitoring.data_recorder import (
    DataRecorder,
    HistoricalQuery,
    DataPlayback,
    RecordingMode,
    CompressionLevel,
)

__all__ = [
    # 实时监控
    "RealtimeMonitor",
    "MonitoringPoint",
    "DataAcquisition",
    "SignalQuality",
    "MonitoringStatus",

    # 报警管理
    "AlarmManager",
    "Alarm",
    "AlarmLevel",
    "AlarmType",
    "AlarmState",
    "AlarmHandler",
    "AlarmEscalation",

    # 趋势分析
    "TrendAnalyzer",
    "TrendDirection",
    "TrendAlert",
    "PredictiveAlert",
    "AnomalyScore",

    # 数据记录
    "DataRecorder",
    "HistoricalQuery",
    "DataPlayback",
    "RecordingMode",
    "CompressionLevel",
]
