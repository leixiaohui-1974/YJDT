# -*- coding: utf-8 -*-
"""
安全态势感知 - 综合安全状态评估
Security Situational Awareness - Comprehensive Security Assessment

功能：
- 安全态势综合评估
- 威胁情报整合
- 风险量化分析
- 安全趋势预测
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict


class SecurityLevel(Enum):
    """安全等级"""
    SAFE = 0              # 安全
    GUARDED = 1           # 警戒
    ELEVATED = 2          # 提升
    HIGH = 3              # 高
    SEVERE = 4            # 严重


@dataclass
class ThreatIntelligence:
    """威胁情报"""
    intel_id: str
    source: str                             # 情报来源
    threat_type: str                        # 威胁类型
    indicators: List[str]                   # 指标(IOC)
    severity: str                           # 严重程度
    description: str
    recommended_actions: List[str] = field(default_factory=list)
    valid_until: Optional[datetime] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityMetric:
    """安全指标"""
    metric_id: str
    name: str
    value: float                            # 0-100
    weight: float = 1.0                     # 权重
    category: str = "general"               # 分类
    trend: str = "stable"                   # rising/falling/stable
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskAssessment:
    """风险评估"""
    assessment_id: str
    overall_risk: float                     # 0-100
    security_level: SecurityLevel
    metrics: Dict[str, float]               # 各项指标
    threats: List[str]                      # 当前威胁
    vulnerabilities: List[str]              # 漏洞
    recommendations: List[str]              # 建议
    timestamp: datetime = field(default_factory=datetime.now)


class SecuritySituationAwareness:
    """
    安全态势感知系统

    功能：
    - 多源安全数据融合
    - 综合态势评估
    - 风险量化分析
    - 趋势预测
    """

    def __init__(self):
        self.threat_intel: Dict[str, ThreatIntelligence] = {}
        self.metrics: Dict[str, SecurityMetric] = {}
        self.assessments: List[RiskAssessment] = []

        # 态势历史
        self.situation_history: List[Dict[str, Any]] = []

        # 指标权重
        self.metric_weights = {
            "network_security": 0.2,
            "access_control": 0.15,
            "intrusion_detection": 0.2,
            "behavior_anomaly": 0.15,
            "vulnerability": 0.15,
            "compliance": 0.15,
        }

        # 初始化默认指标
        self._initialize_metrics()

    def _initialize_metrics(self):
        """初始化安全指标"""
        default_metrics = [
            SecurityMetric("NET_SECURITY", "网络安全", 85, 0.2, "network"),
            SecurityMetric("ACCESS_CTRL", "访问控制", 90, 0.15, "access"),
            SecurityMetric("IDS_SCORE", "入侵检测", 80, 0.2, "detection"),
            SecurityMetric("BEHAVIOR", "行为分析", 85, 0.15, "behavior"),
            SecurityMetric("VULN_SCORE", "漏洞状态", 75, 0.15, "vulnerability"),
            SecurityMetric("COMPLIANCE", "合规性", 90, 0.15, "compliance"),
        ]

        for metric in default_metrics:
            self.metrics[metric.metric_id] = metric

    def update_metric(self, metric_id: str, value: float,
                      trend: str = "stable") -> Optional[SecurityMetric]:
        """更新安全指标"""
        if metric_id not in self.metrics:
            return None

        metric = self.metrics[metric_id]
        old_value = metric.value
        metric.value = max(0, min(100, value))
        metric.trend = trend
        metric.timestamp = datetime.now()

        # 判断趋势
        if value > old_value + 5:
            metric.trend = "rising"
        elif value < old_value - 5:
            metric.trend = "falling"

        return metric

    def add_threat_intel(self, intel: ThreatIntelligence):
        """添加威胁情报"""
        self.threat_intel[intel.intel_id] = intel

    def get_active_threats(self) -> List[ThreatIntelligence]:
        """获取活动威胁情报"""
        now = datetime.now()
        active = []

        for intel in self.threat_intel.values():
            if intel.valid_until is None or intel.valid_until > now:
                active.append(intel)

        return active

    def assess_situation(self) -> RiskAssessment:
        """评估安全态势"""
        # 计算综合风险分数
        weighted_sum = 0.0
        total_weight = 0.0

        metric_values = {}
        for metric in self.metrics.values():
            weight = self.metric_weights.get(metric.category, 0.1)
            weighted_sum += (100 - metric.value) * weight  # 转换为风险值
            total_weight += weight
            metric_values[metric.name] = metric.value

        overall_risk = weighted_sum / total_weight if total_weight > 0 else 50

        # 确定安全等级
        security_level = self._determine_level(overall_risk)

        # 收集威胁
        active_threats = self.get_active_threats()
        threat_names = [t.threat_type for t in active_threats]

        # 识别漏洞
        vulnerabilities = self._identify_vulnerabilities()

        # 生成建议
        recommendations = self._generate_recommendations(
            overall_risk, security_level, metric_values
        )

        assessment = RiskAssessment(
            assessment_id=f"ASSESS_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            overall_risk=overall_risk,
            security_level=security_level,
            metrics=metric_values,
            threats=threat_names,
            vulnerabilities=vulnerabilities,
            recommendations=recommendations,
        )

        self.assessments.append(assessment)

        # 记录历史
        self.situation_history.append({
            "timestamp": datetime.now(),
            "overall_risk": overall_risk,
            "security_level": security_level.name,
        })

        # 限制历史长度
        if len(self.situation_history) > 10000:
            self.situation_history = self.situation_history[-10000:]

        return assessment

    def _determine_level(self, risk: float) -> SecurityLevel:
        """确定安全等级"""
        if risk < 20:
            return SecurityLevel.SAFE
        elif risk < 40:
            return SecurityLevel.GUARDED
        elif risk < 60:
            return SecurityLevel.ELEVATED
        elif risk < 80:
            return SecurityLevel.HIGH
        else:
            return SecurityLevel.SEVERE

    def _identify_vulnerabilities(self) -> List[str]:
        """识别漏洞"""
        vulnerabilities = []

        for metric in self.metrics.values():
            if metric.value < 70:
                vulnerabilities.append(f"{metric.name}指标偏低({metric.value:.0f})")

            if metric.trend == "falling":
                vulnerabilities.append(f"{metric.name}呈下降趋势")

        # 检查威胁情报相关漏洞
        active_threats = self.get_active_threats()
        for threat in active_threats:
            if threat.severity in ["high", "critical"]:
                vulnerabilities.append(f"存在{threat.threat_type}威胁")

        return vulnerabilities

    def _generate_recommendations(self, risk: float, level: SecurityLevel,
                                   metrics: Dict[str, float]) -> List[str]:
        """生成安全建议"""
        recommendations = []

        # 基于整体风险
        if level == SecurityLevel.SEVERE:
            recommendations.append("立即启动安全应急响应预案")
            recommendations.append("隔离受影响系统")
            recommendations.append("通知安全管理团队")

        elif level == SecurityLevel.HIGH:
            recommendations.append("加强安全监控频率")
            recommendations.append("审查近期安全事件")
            recommendations.append("验证关键系统完整性")

        elif level == SecurityLevel.ELEVATED:
            recommendations.append("检查异常活动")
            recommendations.append("更新安全规则")

        # 基于具体指标
        for name, value in metrics.items():
            if value < 60:
                if "网络" in name:
                    recommendations.append("加强网络边界防护")
                elif "访问" in name:
                    recommendations.append("审查用户权限配置")
                elif "入侵" in name:
                    recommendations.append("更新入侵检测规则")
                elif "漏洞" in name:
                    recommendations.append("进行安全漏洞扫描")

        # 去重
        recommendations = list(dict.fromkeys(recommendations))

        return recommendations

    def get_situation_summary(self) -> Dict[str, Any]:
        """获取态势摘要"""
        if not self.assessments:
            assessment = self.assess_situation()
        else:
            assessment = self.assessments[-1]

        # 趋势分析
        if len(self.situation_history) >= 2:
            recent = self.situation_history[-10:]
            risks = [s["overall_risk"] for s in recent]
            trend = "rising" if risks[-1] > risks[0] + 5 else \
                    "falling" if risks[-1] < risks[0] - 5 else "stable"
        else:
            trend = "unknown"

        return {
            "current_level": assessment.security_level.name,
            "overall_risk": assessment.overall_risk,
            "trend": trend,
            "active_threats": len(self.get_active_threats()),
            "vulnerability_count": len(assessment.vulnerabilities),
            "metrics": assessment.metrics,
            "top_recommendations": assessment.recommendations[:3],
            "timestamp": assessment.timestamp.isoformat(),
        }

    def get_trend_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """获取趋势分析"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [s for s in self.situation_history if s["timestamp"] >= cutoff]

        if not recent:
            return {"error": "Insufficient data"}

        risks = [s["overall_risk"] for s in recent]
        levels = [s["security_level"] for s in recent]

        return {
            "period_hours": hours,
            "data_points": len(recent),
            "risk_stats": {
                "min": float(np.min(risks)),
                "max": float(np.max(risks)),
                "mean": float(np.mean(risks)),
                "std": float(np.std(risks)),
                "current": risks[-1] if risks else 0,
            },
            "level_distribution": {
                level: levels.count(level)
                for level in set(levels)
            },
            "trend": "improving" if risks[-1] < risks[0] else \
                     "degrading" if risks[-1] > risks[0] else "stable",
        }

    def simulate_attack_impact(self, attack_type: str,
                               affected_systems: List[str]) -> Dict[str, Any]:
        """模拟攻击影响"""
        # 基础影响评估
        base_impact = {
            "port_scan": 10,
            "dos": 40,
            "malware": 60,
            "ransomware": 80,
            "apt": 90,
            "insider_threat": 70,
        }

        impact_score = base_impact.get(attack_type, 50)

        # 根据受影响系统调整
        critical_systems = ["scada", "plc", "hmi", "historian", "engineering_workstation"]
        critical_count = sum(1 for s in affected_systems if s.lower() in critical_systems)
        impact_score += critical_count * 5

        impact_score = min(impact_score, 100)

        # 预测后果
        consequences = []
        if impact_score > 80:
            consequences.extend([
                "可能导致生产中断",
                "关键数据面临风险",
                "需要启动应急响应",
            ])
        elif impact_score > 60:
            consequences.extend([
                "部分系统功能受影响",
                "需要隔离受影响系统",
            ])
        elif impact_score > 40:
            consequences.extend([
                "系统性能可能下降",
                "需要加强监控",
            ])

        # 建议措施
        mitigation = []
        if attack_type == "dos":
            mitigation.extend(["启用流量限制", "增加带宽冗余", "激活DDoS防护"])
        elif attack_type == "malware":
            mitigation.extend(["隔离感染主机", "更新防病毒签名", "扫描网络"])
        elif attack_type == "ransomware":
            mitigation.extend(["立即隔离", "验证备份完整性", "通知管理层"])
        elif attack_type == "insider_threat":
            mitigation.extend(["审查用户活动", "限制权限", "加强审计"])

        return {
            "attack_type": attack_type,
            "affected_systems": affected_systems,
            "impact_score": impact_score,
            "consequences": consequences,
            "mitigation_measures": mitigation,
            "estimated_recovery_time": f"{impact_score // 10}小时" if impact_score < 50 else f"{impact_score // 5}小时",
        }

    def generate_report(self) -> Dict[str, Any]:
        """生成安全报告"""
        summary = self.get_situation_summary()
        trend = self.get_trend_analysis(24)

        active_threats = self.get_active_threats()
        threat_summary = [
            {
                "type": t.threat_type,
                "severity": t.severity,
                "description": t.description,
            }
            for t in active_threats[:5]
        ]

        metric_details = [
            {
                "name": m.name,
                "value": m.value,
                "trend": m.trend,
                "category": m.category,
            }
            for m in self.metrics.values()
        ]

        return {
            "report_id": f"RPT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "executive_summary": {
                "security_level": summary["current_level"],
                "overall_risk": summary["overall_risk"],
                "trend": summary["trend"],
            },
            "threat_intelligence": {
                "active_count": len(active_threats),
                "top_threats": threat_summary,
            },
            "metrics": metric_details,
            "trend_analysis": trend,
            "recommendations": summary["top_recommendations"],
        }
