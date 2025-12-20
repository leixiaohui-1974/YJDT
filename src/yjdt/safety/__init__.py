# -*- coding: utf-8 -*-
"""
安全分析模块 - 全方位安全保障
Safety Analysis Module - Comprehensive Safety Assurance

包含：
- 概率安全分析 (PSA/FTA/ETA)
- 智能故障诊断与预测维护
- 应急响应决策支持

对标核电站安全分析方法
"""

from yjdt.safety.psa_analysis import (
    PSAAnalyzer,
    FaultTree,
    FaultTreeAnalyzer,
    FaultTreeGate,
    BasicEvent,
    EventTree,
    EventTreeHeading,
    AccidentSequence,
    CommonCauseFailureAnalyzer,
    GateType,
    EventType,
)

from yjdt.safety.intelligent_diagnosis import (
    FaultDiagnoser,
    DiagnosisResult,
    PredictiveMaintenance,
    HealthAssessment,
    HealthStatus,
    FaultSeverity,
    FaultCategory,
    SignalProcessor,
    HealthIndicator,
)

from yjdt.safety.emergency_response import (
    EmergencyResponseCoordinator,
    EmergencyPlanLibrary,
    EmergencyEvent,
    EmergencyPlan,
    ResponseAction,
    EmergencyLevel,
    EventCategory,
    ResponsePhase,
)

__all__ = [
    # PSA分析
    "PSAAnalyzer",
    "FaultTree",
    "FaultTreeAnalyzer",
    "FaultTreeGate",
    "BasicEvent",
    "EventTree",
    "EventTreeHeading",
    "AccidentSequence",
    "CommonCauseFailureAnalyzer",
    "GateType",
    "EventType",

    # 智能诊断
    "FaultDiagnoser",
    "DiagnosisResult",
    "PredictiveMaintenance",
    "HealthAssessment",
    "HealthStatus",
    "FaultSeverity",
    "FaultCategory",
    "SignalProcessor",
    "HealthIndicator",

    # 应急响应
    "EmergencyResponseCoordinator",
    "EmergencyPlanLibrary",
    "EmergencyEvent",
    "EmergencyPlan",
    "ResponseAction",
    "EmergencyLevel",
    "EventCategory",
    "ResponsePhase",
]
