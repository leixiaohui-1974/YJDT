# -*- coding: utf-8 -*-
"""
评价诊断模块 - 状态评估与故障诊断
Evaluation and Diagnosis Module

功能：
- 运行状态综合评价
- 设备健康度评估
- 故障检测与诊断
- 根因分析
- 劣化趋势分析
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


class HealthLevel(Enum):
    """健康等级"""
    EXCELLENT = "excellent"     # 优秀 (90-100)
    GOOD = "good"               # 良好 (75-90)
    FAIR = "fair"               # 一般 (60-75)
    POOR = "poor"               # 较差 (40-60)
    CRITICAL = "critical"       # 危险 (<40)


class FaultSeverity(Enum):
    """故障严重程度"""
    NORMAL = 0
    MINOR = 1
    MODERATE = 2
    SEVERE = 3
    CRITICAL = 4


@dataclass
class HealthIndex:
    """健康指数"""
    component: str
    index: float                        # 0-100
    level: HealthLevel
    trend: str                          # improving/stable/degrading
    contributing_factors: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DiagnosisResult:
    """诊断结果"""
    fault_detected: bool
    fault_type: Optional[str]
    severity: FaultSeverity
    confidence: float                   # 0-1
    symptoms: List[str] = field(default_factory=list)
    root_causes: List[str] = field(default_factory=list)
    affected_components: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RootCauseAnalysis:
    """根因分析"""
    event: str
    root_causes: List[Tuple[str, float]]    # (原因, 概率)
    contributing_factors: List[str]
    evidence: Dict[str, Any] = field(default_factory=dict)
    causal_chain: List[str] = field(default_factory=list)


class StateEvaluator:
    """
    状态评估器

    综合评价系统运行状态
    """

    def __init__(self):
        # 评价权重
        self.weights = {
            "hydraulic": 0.25,
            "mechanical": 0.25,
            "electrical": 0.25,
            "thermal": 0.15,
            "control": 0.10,
        }

        # 阈值定义
        self.thresholds = {
            "speed_deviation": {"warning": 2, "alarm": 5, "trip": 10},  # %
            "vibration": {"warning": 150, "alarm": 250, "trip": 350},  # μm
            "bearing_temp": {"warning": 70, "alarm": 80, "trip": 90},  # ℃
            "stator_temp": {"warning": 110, "alarm": 125, "trip": 140},
            "power_factor": {"warning": 0.85, "alarm": 0.80, "trip": 0.70},
            "pressure_deviation": {"warning": 10, "alarm": 20, "trip": 30},  # %
        }

        # 历史数据
        self.history: List[Dict[str, Any]] = []

    def evaluate(self, state: Dict[str, float]) -> Dict[str, HealthIndex]:
        """综合状态评价"""
        evaluations = {}

        # 水力系统评价
        evaluations["hydraulic"] = self._evaluate_hydraulic(state)

        # 机械系统评价
        evaluations["mechanical"] = self._evaluate_mechanical(state)

        # 电气系统评价
        evaluations["electrical"] = self._evaluate_electrical(state)

        # 热力系统评价
        evaluations["thermal"] = self._evaluate_thermal(state)

        # 综合评价
        evaluations["overall"] = self._evaluate_overall(evaluations)

        # 记录历史
        self.history.append({
            "timestamp": datetime.now(),
            "state": state.copy(),
            "evaluations": {k: v.index for k, v in evaluations.items()}
        })

        return evaluations

    def _evaluate_hydraulic(self, state: Dict[str, float]) -> HealthIndex:
        """水力系统评价"""
        scores = {}

        # 水头稳定性
        head = state.get("hydraulic_net_head", 480)
        head_deviation = abs(head - 480) / 480 * 100
        scores["head_stability"] = max(0, 100 - head_deviation * 5)

        # 流量稳定性
        flow = state.get("hydraulic_turbine_flow", 200)
        flow_target = 200
        flow_deviation = abs(flow - flow_target) / flow_target * 100
        scores["flow_stability"] = max(0, 100 - flow_deviation * 3)

        # 压力状态
        pressure = state.get("hydraulic_penstock_pressure", 5)
        pressure_ref = 5.0
        pressure_deviation = abs(pressure - pressure_ref) / pressure_ref * 100
        scores["pressure_status"] = max(0, 100 - pressure_deviation * 4)

        # 综合得分
        index = np.mean(list(scores.values()))
        level = self._index_to_level(index)

        recommendations = []
        if scores["head_stability"] < 70:
            recommendations.append("检查上游水位调节")
        if scores["pressure_status"] < 70:
            recommendations.append("检查压力钢管状态")

        return HealthIndex(
            component="hydraulic_system",
            index=index,
            level=level,
            trend=self._calculate_trend("hydraulic"),
            contributing_factors=scores,
            recommendations=recommendations,
        )

    def _evaluate_mechanical(self, state: Dict[str, float]) -> HealthIndex:
        """机械系统评价"""
        scores = {}

        # 转速稳定性
        speed = state.get("mechanical_speed", 100)
        speed_deviation = abs(speed - 100) / 100 * 100
        scores["speed_stability"] = max(0, 100 - speed_deviation * 10)

        # 振动状态
        vibration = state.get("mechanical_vibration", 100)
        vib_threshold = self.thresholds["vibration"]
        if vibration < vib_threshold["warning"]:
            scores["vibration_status"] = 100 - vibration / vib_threshold["warning"] * 30
        elif vibration < vib_threshold["alarm"]:
            scores["vibration_status"] = 70 - (vibration - vib_threshold["warning"]) / 100 * 30
        else:
            scores["vibration_status"] = max(0, 40 - (vibration - vib_threshold["alarm"]) / 100 * 40)

        # 轴承温度
        bearing_temp = state.get("mechanical_bearing_temp", 55)
        temp_threshold = self.thresholds["bearing_temp"]
        if bearing_temp < temp_threshold["warning"]:
            scores["bearing_condition"] = 100 - (bearing_temp - 40) / 30 * 30
        elif bearing_temp < temp_threshold["alarm"]:
            scores["bearing_condition"] = 70 - (bearing_temp - temp_threshold["warning"]) / 10 * 30
        else:
            scores["bearing_condition"] = max(0, 40 - (bearing_temp - temp_threshold["alarm"]) / 10 * 40)

        index = np.mean(list(scores.values()))
        level = self._index_to_level(index)

        recommendations = []
        if scores["vibration_status"] < 70:
            recommendations.append("安排振动诊断检查")
        if scores["bearing_condition"] < 70:
            recommendations.append("检查轴承润滑和冷却")

        return HealthIndex(
            component="mechanical_system",
            index=index,
            level=level,
            trend=self._calculate_trend("mechanical"),
            contributing_factors=scores,
            recommendations=recommendations,
        )

    def _evaluate_electrical(self, state: Dict[str, float]) -> HealthIndex:
        """电气系统评价"""
        scores = {}

        # 功率输出
        power = state.get("electrical_active_power", 800)
        power_target = 800
        power_deviation = abs(power - power_target) / power_target * 100
        scores["power_output"] = max(0, 100 - power_deviation * 5)

        # 频率稳定性
        frequency = state.get("electrical_frequency", 50)
        freq_deviation = abs(frequency - 50) / 50 * 100
        scores["frequency_stability"] = max(0, 100 - freq_deviation * 50)

        # 电压稳定性
        voltage = state.get("electrical_voltage", 20)
        voltage_deviation = abs(voltage - 20) / 20 * 100
        scores["voltage_stability"] = max(0, 100 - voltage_deviation * 20)

        index = np.mean(list(scores.values()))
        level = self._index_to_level(index)

        recommendations = []
        if scores["frequency_stability"] < 70:
            recommendations.append("检查调速器响应")
        if scores["voltage_stability"] < 70:
            recommendations.append("检查励磁系统")

        return HealthIndex(
            component="electrical_system",
            index=index,
            level=level,
            trend=self._calculate_trend("electrical"),
            contributing_factors=scores,
            recommendations=recommendations,
        )

    def _evaluate_thermal(self, state: Dict[str, float]) -> HealthIndex:
        """热力系统评价"""
        scores = {}

        # 定子温度
        stator_temp = state.get("thermal_stator_temp", 85)
        temp_threshold = self.thresholds["stator_temp"]
        if stator_temp < temp_threshold["warning"]:
            scores["stator_thermal"] = 100 - (stator_temp - 60) / 50 * 30
        elif stator_temp < temp_threshold["alarm"]:
            scores["stator_thermal"] = 70 - (stator_temp - temp_threshold["warning"]) / 15 * 30
        else:
            scores["stator_thermal"] = max(0, 40 - (stator_temp - temp_threshold["alarm"]) / 15 * 40)

        # 转子温度
        rotor_temp = state.get("thermal_rotor_temp", 75)
        scores["rotor_thermal"] = max(0, 100 - (rotor_temp - 50) / 50 * 50)

        # 冷却效率
        cooling_outlet = state.get("thermal_cooling_outlet", 30)
        cooling_efficiency = 100 - (cooling_outlet - 20) / 20 * 50
        scores["cooling_efficiency"] = max(0, min(100, cooling_efficiency))

        index = np.mean(list(scores.values()))
        level = self._index_to_level(index)

        recommendations = []
        if scores["stator_thermal"] < 70:
            recommendations.append("检查定子冷却系统")
        if scores["cooling_efficiency"] < 70:
            recommendations.append("清洗冷却器，检查冷却水流量")

        return HealthIndex(
            component="thermal_system",
            index=index,
            level=level,
            trend=self._calculate_trend("thermal"),
            contributing_factors=scores,
            recommendations=recommendations,
        )

    def _evaluate_overall(self, subsystem_evals: Dict[str, HealthIndex]) -> HealthIndex:
        """综合评价"""
        weighted_sum = 0
        total_weight = 0

        for key, weight in self.weights.items():
            if key in subsystem_evals:
                weighted_sum += subsystem_evals[key].index * weight
                total_weight += weight

        index = weighted_sum / total_weight if total_weight > 0 else 50
        level = self._index_to_level(index)

        # 汇总建议
        all_recommendations = []
        for eval_result in subsystem_evals.values():
            all_recommendations.extend(eval_result.recommendations)

        return HealthIndex(
            component="overall",
            index=index,
            level=level,
            trend=self._calculate_trend("overall"),
            contributing_factors={k: v.index for k, v in subsystem_evals.items()},
            recommendations=all_recommendations[:5],
        )

    def _index_to_level(self, index: float) -> HealthLevel:
        """指数转等级"""
        if index >= 90:
            return HealthLevel.EXCELLENT
        elif index >= 75:
            return HealthLevel.GOOD
        elif index >= 60:
            return HealthLevel.FAIR
        elif index >= 40:
            return HealthLevel.POOR
        else:
            return HealthLevel.CRITICAL

    def _calculate_trend(self, component: str) -> str:
        """计算趋势"""
        if len(self.history) < 10:
            return "stable"

        recent = [h["evaluations"].get(component, 50) for h in self.history[-10:]]
        slope = np.polyfit(range(len(recent)), recent, 1)[0]

        if slope > 1:
            return "improving"
        elif slope < -1:
            return "degrading"
        else:
            return "stable"


class FaultDiagnosisEngine:
    """
    故障诊断引擎

    基于规则和模式识别的故障诊断
    """

    def __init__(self):
        # 故障特征库
        self.fault_signatures = {
            "bearing_wear": {
                "symptoms": ["高振动", "高温度", "异常噪声"],
                "indicators": {"vibration": (">", 200), "bearing_temp": (">", 75)},
                "severity": FaultSeverity.MODERATE,
            },
            "cavitation": {
                "symptoms": ["振动增大", "效率下降", "噪声异常"],
                "indicators": {"vibration": (">", 180), "efficiency": ("<", 0.88)},
                "severity": FaultSeverity.MODERATE,
            },
            "governor_instability": {
                "symptoms": ["功率波动", "转速波动"],
                "indicators": {"power_oscillation": (">", 5), "speed_oscillation": (">", 1)},
                "severity": FaultSeverity.MINOR,
            },
            "excitation_fault": {
                "symptoms": ["电压波动", "无功异常"],
                "indicators": {"voltage_deviation": (">", 3), "reactive_power_swing": (">", 50)},
                "severity": FaultSeverity.MODERATE,
            },
            "cooling_degradation": {
                "symptoms": ["温度升高", "冷却水温高"],
                "indicators": {"stator_temp": (">", 100), "cooling_outlet": (">", 35)},
                "severity": FaultSeverity.MINOR,
            },
            "water_hammer": {
                "symptoms": ["压力尖峰", "振动冲击"],
                "indicators": {"pressure_spike": (">", 30), "transient_vibration": (">", 300)},
                "severity": FaultSeverity.SEVERE,
            },
        }

        # 诊断历史
        self.diagnosis_history: List[DiagnosisResult] = []

    def diagnose(self, state: Dict[str, float],
                 historical_data: Optional[List[Dict]] = None) -> DiagnosisResult:
        """执行故障诊断"""
        detected_faults = []
        all_symptoms = []
        affected_components = set()

        # 提取特征
        features = self._extract_features(state, historical_data)

        # 匹配故障模式
        for fault_name, signature in self.fault_signatures.items():
            match_score = self._match_signature(features, signature["indicators"])

            if match_score > 0.6:  # 匹配阈值
                detected_faults.append((fault_name, match_score, signature))
                all_symptoms.extend(signature["symptoms"])

        # 确定最可能的故障
        if detected_faults:
            # 按匹配分数排序
            detected_faults.sort(key=lambda x: x[1], reverse=True)
            primary_fault = detected_faults[0]

            fault_type = primary_fault[0]
            confidence = primary_fault[1]
            severity = primary_fault[2]["severity"]

            # 根因分析
            root_causes = self._analyze_root_causes(fault_type, features)

            # 推荐措施
            actions = self._get_recommended_actions(fault_type, severity)

            result = DiagnosisResult(
                fault_detected=True,
                fault_type=fault_type,
                severity=severity,
                confidence=confidence,
                symptoms=list(set(all_symptoms)),
                root_causes=root_causes,
                affected_components=list(affected_components),
                recommended_actions=actions,
            )
        else:
            result = DiagnosisResult(
                fault_detected=False,
                fault_type=None,
                severity=FaultSeverity.NORMAL,
                confidence=0.95,
            )

        self.diagnosis_history.append(result)
        return result

    def _extract_features(self, state: Dict[str, float],
                          historical: Optional[List[Dict]]) -> Dict[str, float]:
        """提取诊断特征"""
        features = {}

        # 直接特征
        features["vibration"] = state.get("mechanical_vibration", 100)
        features["bearing_temp"] = state.get("mechanical_bearing_temp", 55)
        features["stator_temp"] = state.get("thermal_stator_temp", 85)
        features["cooling_outlet"] = state.get("thermal_cooling_outlet", 30)

        # 偏差特征
        features["voltage_deviation"] = abs(state.get("electrical_voltage", 20) - 20) / 20 * 100
        features["speed_deviation"] = abs(state.get("mechanical_speed", 100) - 100)

        # 波动特征（如果有历史数据）
        if historical and len(historical) >= 10:
            powers = [h.get("electrical_active_power", 800) for h in historical[-10:]]
            speeds = [h.get("mechanical_speed", 100) for h in historical[-10:]]
            features["power_oscillation"] = np.std(powers)
            features["speed_oscillation"] = np.std(speeds)
        else:
            features["power_oscillation"] = 0
            features["speed_oscillation"] = 0

        return features

    def _match_signature(self, features: Dict[str, float],
                         indicators: Dict[str, Tuple]) -> float:
        """匹配故障特征"""
        matches = 0
        total = len(indicators)

        for indicator, (operator, threshold) in indicators.items():
            value = features.get(indicator, 0)

            if operator == ">" and value > threshold:
                matches += 1
            elif operator == "<" and value < threshold:
                matches += 1
            elif operator == "=" and abs(value - threshold) < threshold * 0.1:
                matches += 1

        return matches / total if total > 0 else 0

    def _analyze_root_causes(self, fault_type: str,
                             features: Dict[str, float]) -> List[str]:
        """分析根本原因"""
        root_cause_map = {
            "bearing_wear": [
                "润滑不良",
                "负荷过重",
                "轴对中不良",
                "材料疲劳",
            ],
            "cavitation": [
                "吸出高度不足",
                "运行工况偏离设计点",
                "进水流道不畅",
            ],
            "governor_instability": [
                "调速器参数不当",
                "水流惯性时间过大",
                "传感器故障",
            ],
            "excitation_fault": [
                "AVR参数异常",
                "励磁绕组故障",
                "电刷接触不良",
            ],
            "cooling_degradation": [
                "冷却器堵塞",
                "冷却水流量不足",
                "环境温度过高",
            ],
            "water_hammer": [
                "导叶关闭过快",
                "调压室容量不足",
                "保护误动",
            ],
        }

        return root_cause_map.get(fault_type, ["原因待分析"])

    def _get_recommended_actions(self, fault_type: str,
                                  severity: FaultSeverity) -> List[str]:
        """获取推荐措施"""
        actions = []

        # 通用措施
        if severity >= FaultSeverity.SEVERE:
            actions.append("立即降负荷或停机")
            actions.append("通知值长和检修人员")

        # 故障特定措施
        action_map = {
            "bearing_wear": ["检查轴承润滑", "测量轴承间隙", "安排计划检修"],
            "cavitation": ["调整运行水位", "优化运行工况", "检查过流部件"],
            "governor_instability": ["检查调速器参数", "校验传感器", "检查油系统"],
            "excitation_fault": ["检查AVR设置", "检查电刷", "测量绝缘电阻"],
            "cooling_degradation": ["清洗冷却器", "检查水泵", "检查阀门开度"],
            "water_hammer": ["检查导叶关闭时间", "检查调压室", "核实保护定值"],
        }

        actions.extend(action_map.get(fault_type, []))

        return actions
