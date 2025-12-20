# -*- coding: utf-8 -*-
"""
能力评估 - 智能化能力成熟度评估
Capability Assessment - Intelligence Capability Maturity Evaluation

功能：
- 多维度能力评估
- 成熟度等级判定
- 能力差距分析
- 提升建议生成
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class MaturityLevel(Enum):
    """成熟度等级"""
    INITIAL = 1         # 初始级
    MANAGED = 2         # 受管理级
    DEFINED = 3         # 已定义级
    MEASURED = 4        # 已测量级
    OPTIMIZING = 5      # 优化级


class CapabilityDimension(Enum):
    """能力维度"""
    # 感知层能力
    DATA_ACQUISITION = "data_acquisition"       # 数据采集
    SIGNAL_PROCESSING = "signal_processing"     # 信号处理
    STATE_MONITORING = "state_monitoring"       # 状态监测
    ANOMALY_DETECTION = "anomaly_detection"     # 异常检测

    # 分析层能力
    DATA_ANALYTICS = "data_analytics"           # 数据分析
    FAULT_DIAGNOSIS = "fault_diagnosis"         # 故障诊断
    TREND_PREDICTION = "trend_prediction"       # 趋势预测
    HEALTH_ASSESSMENT = "health_assessment"     # 健康评估

    # 决策层能力
    OPTIMIZATION = "optimization"               # 优化决策
    SCHEDULING = "scheduling"                   # 调度决策
    EMERGENCY_RESPONSE = "emergency_response"   # 应急决策
    ADAPTIVE_CONTROL = "adaptive_control"       # 自适应控制

    # 执行层能力
    CONTROL_EXECUTION = "control_execution"     # 控制执行
    SAFETY_PROTECTION = "safety_protection"     # 安全保护
    COORDINATION = "coordination"               # 协调配合
    SELF_HEALING = "self_healing"              # 自愈恢复

    # 支撑能力
    CYBERSECURITY = "cybersecurity"             # 网络安全
    KNOWLEDGE_MANAGEMENT = "knowledge_mgmt"     # 知识管理
    HUMAN_MACHINE_INTERFACE = "hmi"             # 人机界面
    SYSTEM_INTEGRATION = "integration"          # 系统集成


@dataclass
class CapabilityIndicator:
    """能力指标"""
    indicator_id: str
    name: str
    dimension: CapabilityDimension
    description: str
    measurement_method: str
    target_value: float
    unit: str = ""
    weight: float = 1.0


@dataclass
class CapabilityScore:
    """能力得分"""
    dimension: CapabilityDimension
    maturity_level: MaturityLevel
    score: float                        # 0-100
    indicators: Dict[str, float]        # 各指标得分
    gaps: List[str]                     # 差距
    recommendations: List[str]          # 建议


class CapabilityAssessment:
    """
    能力评估系统

    功能：
    - 定义能力指标体系
    - 执行能力评估
    - 识别能力差距
    - 制定提升路线
    """

    def __init__(self):
        # 能力指标库
        self.indicators: Dict[str, CapabilityIndicator] = {}

        # 成熟度阈值
        self.maturity_thresholds = {
            MaturityLevel.INITIAL: 20,
            MaturityLevel.MANAGED: 40,
            MaturityLevel.DEFINED: 60,
            MaturityLevel.MEASURED: 80,
            MaturityLevel.OPTIMIZING: 95,
        }

        # 初始化指标
        self._initialize_indicators()

    def _initialize_indicators(self):
        """初始化能力指标"""
        # 数据采集能力
        self._add_indicator(
            "DA_001", "传感器覆盖率", CapabilityDimension.DATA_ACQUISITION,
            "关键测点传感器配置比例", "已配置传感器数/应配置传感器数×100", 100, "%"
        )
        self._add_indicator(
            "DA_002", "数据完整率", CapabilityDimension.DATA_ACQUISITION,
            "采集数据完整性", "有效数据量/应采数据量×100", 99.9, "%"
        )
        self._add_indicator(
            "DA_003", "采样精度", CapabilityDimension.DATA_ACQUISITION,
            "采样分辨率达标率", "满足精度要求的测点比例", 100, "%"
        )

        # 状态监测能力
        self._add_indicator(
            "SM_001", "监测范围覆盖", CapabilityDimension.STATE_MONITORING,
            "状态监测设备覆盖率", "已监测设备/应监测设备×100", 100, "%"
        )
        self._add_indicator(
            "SM_002", "实时性", CapabilityDimension.STATE_MONITORING,
            "状态更新周期", "数据刷新周期", 1, "s"
        )

        # 异常检测能力
        self._add_indicator(
            "AD_001", "检测准确率", CapabilityDimension.ANOMALY_DETECTION,
            "异常检测正确率", "(TP+TN)/(TP+TN+FP+FN)×100", 95, "%"
        )
        self._add_indicator(
            "AD_002", "漏报率", CapabilityDimension.ANOMALY_DETECTION,
            "异常漏检比例", "FN/(TP+FN)×100，越低越好", 2, "%"
        )
        self._add_indicator(
            "AD_003", "响应时延", CapabilityDimension.ANOMALY_DETECTION,
            "异常发现到告警时间", "检测延迟", 5, "s"
        )

        # 故障诊断能力
        self._add_indicator(
            "FD_001", "诊断准确率", CapabilityDimension.FAULT_DIAGNOSIS,
            "故障诊断正确率", "正确诊断次数/总诊断次数×100", 90, "%"
        )
        self._add_indicator(
            "FD_002", "故障覆盖", CapabilityDimension.FAULT_DIAGNOSIS,
            "可诊断故障类型覆盖", "已建模故障类型/典型故障类型×100", 95, "%"
        )
        self._add_indicator(
            "FD_003", "根因定位", CapabilityDimension.FAULT_DIAGNOSIS,
            "根本原因定位准确率", "根因正确定位/总诊断×100", 85, "%"
        )

        # 趋势预测能力
        self._add_indicator(
            "TP_001", "短期预测精度", CapabilityDimension.TREND_PREDICTION,
            "1小时内预测MAPE", "平均绝对百分比误差", 5, "%"
        )
        self._add_indicator(
            "TP_002", "中期预测精度", CapabilityDimension.TREND_PREDICTION,
            "24小时预测MAPE", "平均绝对百分比误差", 10, "%"
        )

        # 优化决策能力
        self._add_indicator(
            "OPT_001", "优化效果", CapabilityDimension.OPTIMIZATION,
            "相对人工决策效益提升", "智能决策效益/人工决策效益×100-100", 10, "%"
        )
        self._add_indicator(
            "OPT_002", "求解速度", CapabilityDimension.OPTIMIZATION,
            "优化问题求解时间", "从输入到输出时间", 60, "s"
        )

        # 应急响应能力
        self._add_indicator(
            "ER_001", "场景覆盖", CapabilityDimension.EMERGENCY_RESPONSE,
            "应急预案覆盖率", "已建预案场景/识别风险场景×100", 95, "%"
        )
        self._add_indicator(
            "ER_002", "响应时间", CapabilityDimension.EMERGENCY_RESPONSE,
            "应急响应启动时间", "事件发生到响应启动", 30, "s"
        )

        # 控制执行能力
        self._add_indicator(
            "CE_001", "控制精度", CapabilityDimension.CONTROL_EXECUTION,
            "设定值跟踪误差", "实际值与设定值偏差", 1, "%"
        )
        self._add_indicator(
            "CE_002", "执行可靠性", CapabilityDimension.CONTROL_EXECUTION,
            "控制指令执行成功率", "成功执行/总指令×100", 99.9, "%"
        )

        # 安全保护能力
        self._add_indicator(
            "SP_001", "保护覆盖", CapabilityDimension.SAFETY_PROTECTION,
            "安全保护功能覆盖率", "已实现保护/应有保护×100", 100, "%"
        )
        self._add_indicator(
            "SP_002", "保护可靠性", CapabilityDimension.SAFETY_PROTECTION,
            "保护正确动作率", "正确动作次数/应动作次数×100", 99.99, "%"
        )

        # 网络安全能力
        self._add_indicator(
            "CS_001", "安全防护等级", CapabilityDimension.CYBERSECURITY,
            "等保测评等级", "网络安全等级保护", 3, "级"
        )
        self._add_indicator(
            "CS_002", "入侵检测率", CapabilityDimension.CYBERSECURITY,
            "网络攻击检测率", "检测到的攻击/实际攻击×100", 99, "%"
        )

        # 人机界面能力
        self._add_indicator(
            "HMI_001", "可用性评分", CapabilityDimension.HUMAN_MACHINE_INTERFACE,
            "用户体验评分", "基于用户调研的可用性评分", 85, "分"
        )
        self._add_indicator(
            "HMI_002", "信息可视化", CapabilityDimension.HUMAN_MACHINE_INTERFACE,
            "关键信息展示完整度", "可视化呈现的关键信息比例", 95, "%"
        )

    def _add_indicator(self, indicator_id: str, name: str,
                       dimension: CapabilityDimension,
                       description: str, method: str,
                       target: float, unit: str = ""):
        """添加指标"""
        self.indicators[indicator_id] = CapabilityIndicator(
            indicator_id=indicator_id,
            name=name,
            dimension=dimension,
            description=description,
            measurement_method=method,
            target_value=target,
            unit=unit,
        )

    def assess(self, measurements: Dict[str, float]) -> Dict[CapabilityDimension, CapabilityScore]:
        """
        执行能力评估

        Args:
            measurements: 各指标测量值（指标ID -> 测量值）

        Returns:
            各维度能力得分
        """
        # 按维度分组指标
        dimension_indicators: Dict[CapabilityDimension, List[CapabilityIndicator]] = {}
        for indicator in self.indicators.values():
            dim = indicator.dimension
            if dim not in dimension_indicators:
                dimension_indicators[dim] = []
            dimension_indicators[dim].append(indicator)

        # 评估各维度
        results = {}
        for dim, indicators in dimension_indicators.items():
            indicator_scores = {}
            gaps = []
            recommendations = []

            for ind in indicators:
                measured = measurements.get(ind.indicator_id, 0)
                target = ind.target_value

                # 计算得分（考虑指标方向）
                if ind.unit in ["%", "分", "级"]:
                    # 越大越好
                    score = min(100, measured / target * 100) if target > 0 else 0
                else:
                    # 越小越好（如响应时间）
                    score = max(0, 100 - (measured - target) / target * 100) if target > 0 else 100

                indicator_scores[ind.indicator_id] = score

                # 识别差距
                if score < 80:
                    gaps.append(f"{ind.name}未达标（{measured}{ind.unit} vs 目标{target}{ind.unit}）")
                    recommendations.append(f"提升{ind.name}至{target}{ind.unit}")

            # 计算维度综合分数
            dim_score = np.mean(list(indicator_scores.values())) if indicator_scores else 0

            # 判定成熟度
            maturity = self._determine_maturity(dim_score)

            results[dim] = CapabilityScore(
                dimension=dim,
                maturity_level=maturity,
                score=dim_score,
                indicators=indicator_scores,
                gaps=gaps,
                recommendations=recommendations,
            )

        return results

    def _determine_maturity(self, score: float) -> MaturityLevel:
        """判定成熟度等级"""
        for level in reversed(list(MaturityLevel)):
            if score >= self.maturity_thresholds[level]:
                return level
        return MaturityLevel.INITIAL

    def get_overall_maturity(self, dimension_scores: Dict[CapabilityDimension, CapabilityScore]) -> MaturityLevel:
        """获取整体成熟度"""
        if not dimension_scores:
            return MaturityLevel.INITIAL

        # 取各维度成熟度的最低值
        min_level = min(score.maturity_level.value for score in dimension_scores.values())
        return MaturityLevel(min_level)

    def generate_improvement_plan(self,
                                  dimension_scores: Dict[CapabilityDimension, CapabilityScore],
                                  target_maturity: MaturityLevel) -> Dict[str, Any]:
        """
        生成能力提升计划

        Args:
            dimension_scores: 当前能力评分
            target_maturity: 目标成熟度

        Returns:
            提升计划
        """
        target_score = self.maturity_thresholds[target_maturity]

        plan = {
            "target_maturity": target_maturity.name,
            "target_score": target_score,
            "dimension_plans": {},
            "priority_actions": [],
        }

        for dim, score in dimension_scores.items():
            gap = target_score - score.score
            if gap > 0:
                dim_plan = {
                    "current_score": score.score,
                    "gap": gap,
                    "maturity_gap": target_maturity.value - score.maturity_level.value,
                    "actions": score.recommendations,
                    "priority": "high" if gap > 30 else "medium" if gap > 15 else "low",
                }
                plan["dimension_plans"][dim.value] = dim_plan

                if dim_plan["priority"] == "high":
                    plan["priority_actions"].extend(score.recommendations[:2])

        return plan

    def get_capability_radar_data(self,
                                  dimension_scores: Dict[CapabilityDimension, CapabilityScore]) -> Dict[str, float]:
        """获取雷达图数据"""
        return {
            dim.value: score.score
            for dim, score in dimension_scores.items()
        }

