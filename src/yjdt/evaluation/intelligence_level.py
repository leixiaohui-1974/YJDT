# -*- coding: utf-8 -*-
"""
智能化等级评价 - L0-L5水电站智能化分级标准
Intelligence Level Evaluation - L0-L5 Hydropower Station Intelligence Grading

参考标准：
- 《水电厂智能化技术导则》
- 《智能水电站技术规范》
- 类比自动驾驶SAE J3016分级标准

等级定义：
L0 - 人工控制: 完全依赖人工操作，无智能辅助
L1 - 辅助控制: 单一功能智能辅助（如AGC/AVC）
L2 - 部分自动: 多功能协同辅助，人工监督决策
L3 - 条件自动: 特定场景下自动运行，人工应急干预
L4 - 高度自动: 大部分场景自动，极端场景人工
L5 - 完全自动: 全场景无人值守智能运行
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


class IntelligenceLevel(Enum):
    """智能化等级"""
    L0 = 0      # 人工控制 Manual Control
    L1 = 1      # 辅助控制 Assisted Control
    L2 = 2      # 部分自动 Partial Automation
    L3 = 3      # 条件自动 Conditional Automation
    L4 = 4      # 高度自动 High Automation
    L5 = 5      # 完全自动 Full Automation


class EvaluationDimension(Enum):
    """评价维度"""
    PERCEPTION = "perception"           # 感知能力
    COGNITION = "cognition"             # 认知能力
    DECISION = "decision"               # 决策能力
    EXECUTION = "execution"             # 执行能力
    LEARNING = "learning"               # 学习能力
    INTERACTION = "interaction"         # 人机交互


@dataclass
class LevelRequirement:
    """等级要求"""
    level: IntelligenceLevel
    name: str
    description: str

    # 各维度最低要求分数 (0-100)
    dimension_requirements: Dict[EvaluationDimension, float]

    # 场景覆盖要求
    scenario_coverage_min: float        # 最低场景覆盖率 (%)
    autonomous_rate_min: float          # 最低自主决策率 (%)

    # 性能要求
    response_time_max: float            # 最大响应时间 (秒)
    accuracy_min: float                 # 最低准确率 (%)
    availability_min: float             # 最低可用率 (%)

    # 安全要求
    safety_integrity_level: int         # 安全完整性等级 (SIL 1-4)
    mtbf_hours_min: float              # 平均无故障时间 (小时)


@dataclass
class DimensionScore:
    """维度评分"""
    dimension: EvaluationDimension
    score: float                        # 0-100
    sub_scores: Dict[str, float] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """评价结果"""
    evaluation_id: str
    timestamp: datetime
    overall_level: IntelligenceLevel
    overall_score: float                # 0-100

    dimension_scores: Dict[EvaluationDimension, DimensionScore]
    scenario_coverage: float            # %
    autonomous_rate: float              # %

    strengths: List[str]
    weaknesses: List[str]
    improvement_path: List[str]         # 升级路径

    # 详细指标
    metrics: Dict[str, float] = field(default_factory=dict)


class IntelligenceLevelEvaluator:
    """
    智能化等级评价器

    功能：
    - 多维度综合评价
    - 等级判定
    - 升级路径规划
    """

    def __init__(self):
        # 初始化等级要求
        self.level_requirements = self._define_level_requirements()

        # 维度权重
        self.dimension_weights = {
            EvaluationDimension.PERCEPTION: 0.20,
            EvaluationDimension.COGNITION: 0.20,
            EvaluationDimension.DECISION: 0.25,
            EvaluationDimension.EXECUTION: 0.15,
            EvaluationDimension.LEARNING: 0.10,
            EvaluationDimension.INTERACTION: 0.10,
        }

        # 评价历史
        self.evaluation_history: List[EvaluationResult] = []

    def _define_level_requirements(self) -> Dict[IntelligenceLevel, LevelRequirement]:
        """定义各等级要求"""
        requirements = {}

        # L0 - 人工控制
        requirements[IntelligenceLevel.L0] = LevelRequirement(
            level=IntelligenceLevel.L0,
            name="人工控制",
            description="完全依赖人工操作，系统仅提供基础监视功能",
            dimension_requirements={
                EvaluationDimension.PERCEPTION: 20,
                EvaluationDimension.COGNITION: 10,
                EvaluationDimension.DECISION: 0,
                EvaluationDimension.EXECUTION: 10,
                EvaluationDimension.LEARNING: 0,
                EvaluationDimension.INTERACTION: 30,
            },
            scenario_coverage_min=0,
            autonomous_rate_min=0,
            response_time_max=60,
            accuracy_min=0,
            availability_min=90,
            safety_integrity_level=1,
            mtbf_hours_min=1000,
        )

        # L1 - 辅助控制
        requirements[IntelligenceLevel.L1] = LevelRequirement(
            level=IntelligenceLevel.L1,
            name="辅助控制",
            description="单一功能智能辅助，如AGC/AVC自动调节",
            dimension_requirements={
                EvaluationDimension.PERCEPTION: 40,
                EvaluationDimension.COGNITION: 30,
                EvaluationDimension.DECISION: 20,
                EvaluationDimension.EXECUTION: 40,
                EvaluationDimension.LEARNING: 10,
                EvaluationDimension.INTERACTION: 50,
            },
            scenario_coverage_min=20,
            autonomous_rate_min=10,
            response_time_max=30,
            accuracy_min=85,
            availability_min=95,
            safety_integrity_level=2,
            mtbf_hours_min=5000,
        )

        # L2 - 部分自动
        requirements[IntelligenceLevel.L2] = LevelRequirement(
            level=IntelligenceLevel.L2,
            name="部分自动",
            description="多功能协同辅助，人工监督下自动控制",
            dimension_requirements={
                EvaluationDimension.PERCEPTION: 60,
                EvaluationDimension.COGNITION: 50,
                EvaluationDimension.DECISION: 40,
                EvaluationDimension.EXECUTION: 60,
                EvaluationDimension.LEARNING: 30,
                EvaluationDimension.INTERACTION: 60,
            },
            scenario_coverage_min=40,
            autonomous_rate_min=30,
            response_time_max=10,
            accuracy_min=90,
            availability_min=98,
            safety_integrity_level=2,
            mtbf_hours_min=10000,
        )

        # L3 - 条件自动
        requirements[IntelligenceLevel.L3] = LevelRequirement(
            level=IntelligenceLevel.L3,
            name="条件自动",
            description="特定场景下完全自动运行，人工负责应急干预",
            dimension_requirements={
                EvaluationDimension.PERCEPTION: 75,
                EvaluationDimension.COGNITION: 70,
                EvaluationDimension.DECISION: 65,
                EvaluationDimension.EXECUTION: 75,
                EvaluationDimension.LEARNING: 50,
                EvaluationDimension.INTERACTION: 70,
            },
            scenario_coverage_min=60,
            autonomous_rate_min=60,
            response_time_max=5,
            accuracy_min=95,
            availability_min=99,
            safety_integrity_level=3,
            mtbf_hours_min=20000,
        )

        # L4 - 高度自动
        requirements[IntelligenceLevel.L4] = LevelRequirement(
            level=IntelligenceLevel.L4,
            name="高度自动",
            description="大部分场景自动运行，仅极端场景需人工介入",
            dimension_requirements={
                EvaluationDimension.PERCEPTION: 85,
                EvaluationDimension.COGNITION: 85,
                EvaluationDimension.DECISION: 80,
                EvaluationDimension.EXECUTION: 85,
                EvaluationDimension.LEARNING: 70,
                EvaluationDimension.INTERACTION: 80,
            },
            scenario_coverage_min=85,
            autonomous_rate_min=85,
            response_time_max=2,
            accuracy_min=98,
            availability_min=99.5,
            safety_integrity_level=3,
            mtbf_hours_min=50000,
        )

        # L5 - 完全自动
        requirements[IntelligenceLevel.L5] = LevelRequirement(
            level=IntelligenceLevel.L5,
            name="完全自动",
            description="全场景无人值守智能运行，具备自主学习进化能力",
            dimension_requirements={
                EvaluationDimension.PERCEPTION: 95,
                EvaluationDimension.COGNITION: 95,
                EvaluationDimension.DECISION: 95,
                EvaluationDimension.EXECUTION: 95,
                EvaluationDimension.LEARNING: 90,
                EvaluationDimension.INTERACTION: 90,
            },
            scenario_coverage_min=99,
            autonomous_rate_min=99,
            response_time_max=1,
            accuracy_min=99.5,
            availability_min=99.9,
            safety_integrity_level=4,
            mtbf_hours_min=100000,
        )

        return requirements

    def evaluate(self, system_capabilities: Dict[str, Any]) -> EvaluationResult:
        """
        执行智能化等级评价

        Args:
            system_capabilities: 系统能力数据

        Returns:
            评价结果
        """
        evaluation_id = f"EVAL_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 评价各维度
        dimension_scores = {}
        for dimension in EvaluationDimension:
            score = self._evaluate_dimension(dimension, system_capabilities)
            dimension_scores[dimension] = score

        # 计算综合分数
        overall_score = sum(
            score.score * self.dimension_weights[dim]
            for dim, score in dimension_scores.items()
        )

        # 获取场景覆盖率和自主决策率
        scenario_coverage = system_capabilities.get("scenario_coverage", 0)
        autonomous_rate = system_capabilities.get("autonomous_rate", 0)

        # 判定等级
        overall_level = self._determine_level(
            dimension_scores, scenario_coverage, autonomous_rate
        )

        # 分析优劣势
        strengths, weaknesses = self._analyze_strengths_weaknesses(dimension_scores)

        # 规划升级路径
        improvement_path = self._plan_improvement_path(
            overall_level, dimension_scores, scenario_coverage, autonomous_rate
        )

        result = EvaluationResult(
            evaluation_id=evaluation_id,
            timestamp=datetime.now(),
            overall_level=overall_level,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            scenario_coverage=scenario_coverage,
            autonomous_rate=autonomous_rate,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_path=improvement_path,
            metrics=system_capabilities.get("metrics", {}),
        )

        self.evaluation_history.append(result)
        return result

    def _evaluate_dimension(self, dimension: EvaluationDimension,
                            capabilities: Dict) -> DimensionScore:
        """评价单一维度"""
        sub_scores = {}
        evidence = []
        recommendations = []

        if dimension == EvaluationDimension.PERCEPTION:
            # 感知能力评价
            sub_scores["sensor_coverage"] = capabilities.get("sensor_coverage", 0)
            sub_scores["data_quality"] = capabilities.get("data_quality", 0)
            sub_scores["fusion_accuracy"] = capabilities.get("fusion_accuracy", 0)
            sub_scores["anomaly_detection"] = capabilities.get("anomaly_detection_rate", 0)

            if sub_scores["sensor_coverage"] < 80:
                recommendations.append("增加关键设备传感器覆盖")
            if sub_scores["fusion_accuracy"] < 90:
                recommendations.append("优化多源数据融合算法")

        elif dimension == EvaluationDimension.COGNITION:
            # 认知能力评价
            sub_scores["state_estimation"] = capabilities.get("state_estimation_accuracy", 0)
            sub_scores["fault_diagnosis"] = capabilities.get("fault_diagnosis_accuracy", 0)
            sub_scores["trend_prediction"] = capabilities.get("prediction_accuracy", 0)
            sub_scores["knowledge_base"] = capabilities.get("knowledge_coverage", 0)

            if sub_scores["fault_diagnosis"] < 85:
                recommendations.append("完善故障诊断知识库")

        elif dimension == EvaluationDimension.DECISION:
            # 决策能力评价
            sub_scores["optimization_quality"] = capabilities.get("optimization_quality", 0)
            sub_scores["response_speed"] = self._score_response_time(
                capabilities.get("avg_response_time", 60)
            )
            sub_scores["decision_accuracy"] = capabilities.get("decision_accuracy", 0)
            sub_scores["safety_compliance"] = capabilities.get("safety_compliance", 0)

            if sub_scores["decision_accuracy"] < 90:
                recommendations.append("增强决策模型训练数据")

        elif dimension == EvaluationDimension.EXECUTION:
            # 执行能力评价
            sub_scores["control_precision"] = capabilities.get("control_precision", 0)
            sub_scores["tracking_error"] = 100 - capabilities.get("tracking_error", 100)
            sub_scores["actuator_reliability"] = capabilities.get("actuator_reliability", 0)
            sub_scores["interlock_coverage"] = capabilities.get("interlock_coverage", 0)

        elif dimension == EvaluationDimension.LEARNING:
            # 学习能力评价
            sub_scores["model_adaptation"] = capabilities.get("model_adaptation", 0)
            sub_scores["online_learning"] = capabilities.get("online_learning", 0)
            sub_scores["experience_accumulation"] = capabilities.get("experience_db_size", 0) / 10000 * 100
            sub_scores["knowledge_transfer"] = capabilities.get("knowledge_transfer", 0)

        elif dimension == EvaluationDimension.INTERACTION:
            # 人机交互评价
            sub_scores["hmi_usability"] = capabilities.get("hmi_usability", 0)
            sub_scores["alarm_management"] = capabilities.get("alarm_quality", 0)
            sub_scores["decision_transparency"] = capabilities.get("explainability", 0)
            sub_scores["override_capability"] = capabilities.get("override_capability", 0)

        # 计算维度总分
        if sub_scores:
            score = np.mean(list(sub_scores.values()))
        else:
            score = 0

        return DimensionScore(
            dimension=dimension,
            score=score,
            sub_scores=sub_scores,
            evidence=evidence,
            recommendations=recommendations,
        )

    def _score_response_time(self, response_time: float) -> float:
        """响应时间转换为分数"""
        if response_time <= 1:
            return 100
        elif response_time <= 5:
            return 90
        elif response_time <= 10:
            return 75
        elif response_time <= 30:
            return 50
        else:
            return max(0, 100 - response_time)

    def _determine_level(self, dimension_scores: Dict[EvaluationDimension, DimensionScore],
                         scenario_coverage: float,
                         autonomous_rate: float) -> IntelligenceLevel:
        """判定智能化等级"""
        # 从高到低检查是否满足各等级要求
        for level in reversed(list(IntelligenceLevel)):
            if self._meets_level_requirements(
                level, dimension_scores, scenario_coverage, autonomous_rate
            ):
                return level

        return IntelligenceLevel.L0

    def _meets_level_requirements(self, level: IntelligenceLevel,
                                  dimension_scores: Dict,
                                  scenario_coverage: float,
                                  autonomous_rate: float) -> bool:
        """检查是否满足等级要求"""
        req = self.level_requirements[level]

        # 检查各维度分数
        for dim, min_score in req.dimension_requirements.items():
            if dimension_scores[dim].score < min_score:
                return False

        # 检查场景覆盖率
        if scenario_coverage < req.scenario_coverage_min:
            return False

        # 检查自主决策率
        if autonomous_rate < req.autonomous_rate_min:
            return False

        return True

    def _analyze_strengths_weaknesses(self,
                                       dimension_scores: Dict) -> Tuple[List[str], List[str]]:
        """分析优劣势"""
        strengths = []
        weaknesses = []

        avg_score = np.mean([s.score for s in dimension_scores.values()])

        for dim, score in dimension_scores.items():
            dim_name = self._get_dimension_name(dim)

            if score.score >= avg_score + 10:
                strengths.append(f"{dim_name}能力突出（{score.score:.0f}分）")
            elif score.score <= avg_score - 10:
                weaknesses.append(f"{dim_name}能力不足（{score.score:.0f}分）")

            # 添加具体子项分析
            for sub_name, sub_score in score.sub_scores.items():
                if sub_score < 60:
                    weaknesses.append(f"{dim_name}-{sub_name}需提升")

        return strengths, weaknesses

    def _get_dimension_name(self, dimension: EvaluationDimension) -> str:
        """获取维度中文名"""
        names = {
            EvaluationDimension.PERCEPTION: "感知",
            EvaluationDimension.COGNITION: "认知",
            EvaluationDimension.DECISION: "决策",
            EvaluationDimension.EXECUTION: "执行",
            EvaluationDimension.LEARNING: "学习",
            EvaluationDimension.INTERACTION: "交互",
        }
        return names.get(dimension, str(dimension))

    def _plan_improvement_path(self, current_level: IntelligenceLevel,
                                dimension_scores: Dict,
                                scenario_coverage: float,
                                autonomous_rate: float) -> List[str]:
        """规划升级路径"""
        path = []

        if current_level == IntelligenceLevel.L5:
            return ["已达最高等级，保持持续优化"]

        # 下一等级目标
        next_level = IntelligenceLevel(current_level.value + 1)
        next_req = self.level_requirements[next_level]

        path.append(f"目标：升级至{next_req.name}（L{next_level.value}）")

        # 分析差距
        for dim, min_score in next_req.dimension_requirements.items():
            current = dimension_scores[dim].score
            gap = min_score - current
            if gap > 0:
                dim_name = self._get_dimension_name(dim)
                path.append(f"提升{dim_name}能力：{current:.0f}→{min_score:.0f}（+{gap:.0f}分）")

        # 场景覆盖差距
        if scenario_coverage < next_req.scenario_coverage_min:
            gap = next_req.scenario_coverage_min - scenario_coverage
            path.append(f"扩展场景覆盖：{scenario_coverage:.0f}%→{next_req.scenario_coverage_min:.0f}%")

        # 自主决策率差距
        if autonomous_rate < next_req.autonomous_rate_min:
            gap = next_req.autonomous_rate_min - autonomous_rate
            path.append(f"提高自主决策率：{autonomous_rate:.0f}%→{next_req.autonomous_rate_min:.0f}%")

        return path

    def compare_evaluations(self, eval1: EvaluationResult,
                            eval2: EvaluationResult) -> Dict[str, Any]:
        """比较两次评价结果"""
        comparison = {
            "eval1_id": eval1.evaluation_id,
            "eval2_id": eval2.evaluation_id,
            "time_span": (eval2.timestamp - eval1.timestamp).days,
            "level_change": eval2.overall_level.value - eval1.overall_level.value,
            "score_change": eval2.overall_score - eval1.overall_score,
            "dimension_changes": {},
        }

        for dim in EvaluationDimension:
            change = eval2.dimension_scores[dim].score - eval1.dimension_scores[dim].score
            comparison["dimension_changes"][dim.value] = change

        comparison["improved"] = comparison["score_change"] > 0
        comparison["level_up"] = comparison["level_change"] > 0

        return comparison

    def generate_report(self, result: EvaluationResult) -> Dict[str, Any]:
        """生成评价报告"""
        level_req = self.level_requirements[result.overall_level]

        report = {
            "report_id": f"RPT_{result.evaluation_id}",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "intelligence_level": f"L{result.overall_level.value}",
                "level_name": level_req.name,
                "overall_score": round(result.overall_score, 1),
                "scenario_coverage": f"{result.scenario_coverage:.1f}%",
                "autonomous_rate": f"{result.autonomous_rate:.1f}%",
            },
            "dimension_analysis": {
                dim.value: {
                    "score": round(score.score, 1),
                    "sub_scores": score.sub_scores,
                    "recommendations": score.recommendations,
                }
                for dim, score in result.dimension_scores.items()
            },
            "radar_chart_data": {
                dim.value: score.score
                for dim, score in result.dimension_scores.items()
            },
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "improvement_path": result.improvement_path,
            "next_level_requirements": (
                self.level_requirements[
                    IntelligenceLevel(min(result.overall_level.value + 1, 5))
                ].dimension_requirements
            ),
        }

        return report

