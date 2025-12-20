# -*- coding: utf-8 -*-
"""
网络安全防护模块 - 工控系统安全保障
Cybersecurity Protection Module - ICS Security Assurance

包含：
- 入侵检测系统 (IDS)
- 异常行为分析
- 访问控制与审计
- 安全态势感知
- 应急响应

对标IEC 62443工控网络安全标准
"""

from yjdt.security.intrusion_detection import (
    IntrusionDetectionSystem,
    DetectionRule,
    ThreatAlert,
    ThreatLevel,
    AttackType,
)

from yjdt.security.behavior_analysis import (
    BehaviorAnalyzer,
    BehaviorProfile,
    AnomalyScore,
    OperatorBehavior,
)

from yjdt.security.access_control import (
    AccessController,
    User,
    Role,
    Permission,
    AuditLog,
    AuthResult,
)

from yjdt.security.situational_awareness import (
    SecuritySituationAwareness,
    ThreatIntelligence,
    SecurityMetric,
    RiskAssessment,
)

__all__ = [
    # 入侵检测
    "IntrusionDetectionSystem",
    "DetectionRule",
    "ThreatAlert",
    "ThreatLevel",
    "AttackType",

    # 行为分析
    "BehaviorAnalyzer",
    "BehaviorProfile",
    "AnomalyScore",
    "OperatorBehavior",

    # 访问控制
    "AccessController",
    "User",
    "Role",
    "Permission",
    "AuditLog",
    "AuthResult",

    # 态势感知
    "SecuritySituationAwareness",
    "ThreatIntelligence",
    "SecurityMetric",
    "RiskAssessment",
]
