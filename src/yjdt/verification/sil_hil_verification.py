# -*- coding: utf-8 -*-
"""
SIL/HIL验证框架 - Software/Hardware-in-the-Loop Verification

基于YX工程（雅鲁藏布江大拐弯截弯取直引水梯级发电工程）的验证框架

核心功能：
- ODD边界验证
- 系统级运行逻辑验证
- MAS策略验证
- 级联效应验证
- 降级能力验证
- 设计参数回归测试

验证目标：
- 把原本只能在投运后暴露的运行风险，前移到设计阶段识别与验证
- 避免"软件里没问题、上机就出问题"

参考：YX工程面向运行能力的设计评估与运行逻辑验证关键技术研究
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from enum import Enum
import logging
import json
import copy

logger = logging.getLogger(__name__)


class VerificationLevel(Enum):
    """验证级别"""
    MIL = "mil"                         # Model-in-the-Loop
    SIL = "sil"                         # Software-in-the-Loop
    HIL = "hil"                         # Hardware-in-the-Loop
    PILOT = "pilot"                     # 中试平台


class VerificationScope(Enum):
    """验证范围"""
    UNIT = "unit"                       # 机组级
    STATION = "station"                 # 电站级
    CASCADE = "cascade"                 # 梯级级
    SYSTEM = "system"                   # 系统级


class TestCategory(Enum):
    """测试类别"""
    ODD_BOUNDARY = "odd_boundary"       # ODD边界验证
    TRANSIENT = "transient"             # 暂态响应验证
    CASCADE_EFFECT = "cascade_effect"   # 级联效应验证
    DEGRADATION = "degradation"         # 降级能力验证
    COORDINATION = "coordination"       # 协调策略验证
    PROTECTION = "protection"           # 保护逻辑验证
    RECOVERY = "recovery"               # 恢复能力验证
    PARAMETER = "parameter"             # 参数敏感性验证


class TestResult(Enum):
    """测试结果"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class VerificationCriteria:
    """验证准则"""
    name: str
    description: str
    category: TestCategory

    # 通过条件
    pass_conditions: List[Dict[str, Any]] = field(default_factory=list)

    # 警告条件
    warning_conditions: List[Dict[str, Any]] = field(default_factory=list)

    # 失败条件
    fail_conditions: List[Dict[str, Any]] = field(default_factory=list)

    # 权重
    weight: float = 1.0


@dataclass
class VerificationTestCase:
    """验证测试用例"""
    test_id: str
    name: str
    description: str
    category: TestCategory
    scope: VerificationScope
    level: VerificationLevel

    # 测试配置
    scenario: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, float] = field(default_factory=dict)
    duration: float = 300.0

    # 验证准则
    criteria: List[VerificationCriteria] = field(default_factory=list)

    # 优先级
    priority: int = 2  # 1=critical, 2=high, 3=medium, 4=low

    # 标签
    tags: List[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    """验证结果"""
    test_id: str
    test_name: str
    result: TestResult
    score: float

    # 详细结果
    criteria_results: Dict[str, TestResult] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)

    # ODD状态记录
    odd_coverage: float = 0.0
    odd_violations: List[Dict[str, Any]] = field(default_factory=list)

    # 时序数据
    time_series: Dict[str, List[float]] = field(default_factory=dict)

    # 执行信息
    start_time: datetime = None
    end_time: datetime = None
    duration: float = 0.0

    # 问题与建议
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class VerificationReport:
    """验证报告"""
    report_id: str
    title: str
    level: VerificationLevel
    scope: VerificationScope
    created_at: datetime

    # 总体结果
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    warning_tests: int = 0
    overall_score: float = 0.0

    # 分类结果
    category_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 测试结果列表
    test_results: List[VerificationResult] = field(default_factory=list)

    # ODD验证摘要
    odd_summary: Dict[str, Any] = field(default_factory=dict)

    # 建议
    recommendations: List[str] = field(default_factory=list)


class ODDBoundaryVerifier:
    """
    ODD边界验证器

    验证系统运行是否在ODD边界内
    """

    def __init__(self, odd: 'SystemODD'):
        self.odd = odd
        self.verification_results: List[Dict[str, Any]] = []

    def verify_pressure_boundary(self, simulation_result: Dict[str, Any]) -> Dict[str, Any]:
        """验证压力边界"""
        result = {
            "boundary": "pressure",
            "passed": True,
            "violations": [],
            "metrics": {},
        }

        pressure_data = simulation_result.get("system", {}).get("pressure", [])
        if len(pressure_data) == 0:
            result["passed"] = False
            result["violations"].append("无压力数据")
            return result

        pressure_boundary = self.odd.system_boundaries.get("system_pressure")
        if not pressure_boundary:
            return result

        # 检查绝对边界
        max_pressure = np.max(pressure_data)
        min_pressure = np.min(pressure_data)

        result["metrics"]["max_pressure"] = max_pressure
        result["metrics"]["min_pressure"] = min_pressure
        result["metrics"]["avg_pressure"] = np.mean(pressure_data)

        # 超出绝对边界
        if max_pressure > pressure_boundary.absolute_max:
            result["passed"] = False
            result["violations"].append(
                f"最大压力{max_pressure:.2f}MPa超过绝对上限{pressure_boundary.absolute_max}MPa"
            )

        if min_pressure < pressure_boundary.absolute_min:
            result["passed"] = False
            result["violations"].append(
                f"最小压力{min_pressure:.2f}MPa低于绝对下限{pressure_boundary.absolute_min}MPa"
            )

        # 统计区域分布
        time_in_zones = {zone.value: 0 for zone in self.odd.odd.ODDZone}
        for p in pressure_data:
            zone = pressure_boundary.get_zone(p)
            time_in_zones[zone.value] += 1

        total_points = len(pressure_data)
        result["metrics"]["zone_distribution"] = {
            zone: count / total_points * 100
            for zone, count in time_in_zones.items()
        }

        self.verification_results.append(result)
        return result

    def verify_transient_boundary(self, simulation_result: Dict[str, Any]) -> Dict[str, Any]:
        """验证瞬变边界"""
        result = {
            "boundary": "transient",
            "passed": True,
            "violations": [],
            "metrics": {},
        }

        pressure_data = simulation_result.get("system", {}).get("pressure", [])
        time_data = simulation_result.get("time", [])

        if len(pressure_data) < 2 or len(time_data) < 2:
            return result

        # 计算压力变化率
        dt = time_data[1] - time_data[0] if len(time_data) > 1 else 0.01
        pressure_gradient = np.diff(pressure_data) / dt

        max_gradient = np.max(np.abs(pressure_gradient))
        result["metrics"]["max_pressure_gradient"] = max_gradient

        # 检查是否超过瞬变边界
        if max_gradient > self.odd.transient_boundary.max_pressure_gradient:
            result["passed"] = False
            result["violations"].append(
                f"压力变化率{max_gradient:.3f}MPa/s超过限制"
                f"{self.odd.transient_boundary.max_pressure_gradient}MPa/s"
            )

        self.verification_results.append(result)
        return result

    def verify_cascade_boundary(self, simulation_result: Dict[str, Any]) -> Dict[str, Any]:
        """验证级联边界"""
        result = {
            "boundary": "cascade",
            "passed": True,
            "violations": [],
            "metrics": {},
        }

        # 检查级联深度
        cascade_events = simulation_result.get("cascade_events", [])
        max_depth = 0

        for event in cascade_events:
            depth = event.get("cascade_depth", 0)
            if depth > max_depth:
                max_depth = depth

        result["metrics"]["max_cascade_depth"] = max_depth

        if max_depth > self.odd.cascade_boundary.max_cascade_depth:
            result["passed"] = False
            result["violations"].append(
                f"级联深度{max_depth}超过限制{self.odd.cascade_boundary.max_cascade_depth}"
            )

        self.verification_results.append(result)
        return result

    def verify_all_boundaries(self, simulation_result: Dict[str, Any]) -> Dict[str, Any]:
        """验证所有边界"""
        results = {
            "pressure": self.verify_pressure_boundary(simulation_result),
            "transient": self.verify_transient_boundary(simulation_result),
            "cascade": self.verify_cascade_boundary(simulation_result),
        }

        # 综合结果
        overall_passed = all(r["passed"] for r in results.values())
        all_violations = []
        for r in results.values():
            all_violations.extend(r.get("violations", []))

        return {
            "overall_passed": overall_passed,
            "boundary_results": results,
            "total_violations": len(all_violations),
            "violations": all_violations,
        }


class SILVerificationFramework:
    """
    SIL验证框架

    功能：
    - 运行逻辑正确性验证
    - 策略切换验证
    - 大规模场景覆盖
    - 高频、低成本、大规模覆盖
    """

    def __init__(self, odd: 'SystemODD', mas: 'ODDAwareMASSystem', model: 'SystemModel'):
        self.odd = odd
        self.mas = mas
        self.model = model

        # ODD边界验证器
        self.odd_verifier = ODDBoundaryVerifier(odd)

        # 测试用例库
        self.test_cases: List[VerificationTestCase] = []

        # 验证结果
        self.results: List[VerificationResult] = []

        # 初始化标准测试用例
        self._init_standard_test_cases()

    def _init_standard_test_cases(self):
        """初始化标准测试用例"""
        # ODD边界测试
        self.test_cases.append(VerificationTestCase(
            test_id="SIL_ODD_001",
            name="正常运行ODD边界验证",
            description="验证正常运行条件下系统保持在ODD边界内",
            category=TestCategory.ODD_BOUNDARY,
            scope=VerificationScope.SYSTEM,
            level=VerificationLevel.SIL,
            scenario={"type": "normal_operation"},
            duration=300.0,
            criteria=[
                VerificationCriteria(
                    name="压力边界",
                    description="系统压力保持在正常ODD范围内",
                    category=TestCategory.ODD_BOUNDARY,
                    pass_conditions=[
                        {"metric": "odd_coverage", "operator": ">=", "value": 95}
                    ],
                    fail_conditions=[
                        {"metric": "forbidden_zone_time", "operator": ">", "value": 0}
                    ],
                )
            ],
            priority=1,
            tags=["odd", "normal", "boundary"],
        ))

        # 暂态响应测试
        self.test_cases.append(VerificationTestCase(
            test_id="SIL_TRANS_001",
            name="甩负荷暂态响应验证",
            description="验证甩负荷条件下系统暂态响应在ODD边界内",
            category=TestCategory.TRANSIENT,
            scope=VerificationScope.SYSTEM,
            level=VerificationLevel.SIL,
            scenario={"type": "load_rejection", "magnitude": 0.3},
            duration=180.0,
            criteria=[
                VerificationCriteria(
                    name="转速超调",
                    description="转速超调不超过限制",
                    category=TestCategory.TRANSIENT,
                    pass_conditions=[
                        {"metric": "speed_overshoot", "operator": "<=", "value": 30}
                    ],
                ),
                VerificationCriteria(
                    name="压力波动",
                    description="压力波动不超过ODD边界",
                    category=TestCategory.TRANSIENT,
                    pass_conditions=[
                        {"metric": "max_pressure_rise", "operator": "<=", "value": 50}
                    ],
                )
            ],
            priority=1,
            tags=["transient", "load_rejection"],
        ))

        # 级联效应测试
        self.test_cases.append(VerificationTestCase(
            test_id="SIL_CASCADE_001",
            name="保护触发级联效应验证",
            description="验证保护触发后的级联响应在可控范围内",
            category=TestCategory.CASCADE_EFFECT,
            scope=VerificationScope.CASCADE,
            level=VerificationLevel.SIL,
            scenario={"type": "protection_triggered", "station": "YJ01"},
            duration=300.0,
            criteria=[
                VerificationCriteria(
                    name="级联深度",
                    description="级联深度不超过允许值",
                    category=TestCategory.CASCADE_EFFECT,
                    pass_conditions=[
                        {"metric": "cascade_depth", "operator": "<=", "value": 2}
                    ],
                ),
                VerificationCriteria(
                    name="系统恢复",
                    description="系统能够恢复到稳定状态",
                    category=TestCategory.CASCADE_EFFECT,
                    pass_conditions=[
                        {"metric": "recovery_time", "operator": "<=", "value": 120}
                    ],
                )
            ],
            priority=1,
            tags=["cascade", "protection"],
        ))

        # 降级能力测试
        self.test_cases.append(VerificationTestCase(
            test_id="SIL_DEG_001",
            name="系统降级能力验证",
            description="验证系统从最优运行→安全运行→保底运行的有序退化能力",
            category=TestCategory.DEGRADATION,
            scope=VerificationScope.SYSTEM,
            level=VerificationLevel.SIL,
            scenario={"type": "progressive_degradation"},
            duration=600.0,
            criteria=[
                VerificationCriteria(
                    name="有序降级",
                    description="降级过程有序进行，无崩溃",
                    category=TestCategory.DEGRADATION,
                    pass_conditions=[
                        {"metric": "degradation_orderly", "operator": "==", "value": True}
                    ],
                )
            ],
            priority=1,
            tags=["degradation", "safety"],
        ))

        # 协调策略测试
        self.test_cases.append(VerificationTestCase(
            test_id="SIL_COORD_001",
            name="多站协调策略验证",
            description="验证多站协同动作的策略正确性",
            category=TestCategory.COORDINATION,
            scope=VerificationScope.CASCADE,
            level=VerificationLevel.SIL,
            scenario={"type": "multi_station_coordination"},
            duration=300.0,
            criteria=[
                VerificationCriteria(
                    name="协调一致性",
                    description="多站动作协调一致",
                    category=TestCategory.COORDINATION,
                    pass_conditions=[
                        {"metric": "coordination_success_rate", "operator": ">=", "value": 95}
                    ],
                )
            ],
            priority=2,
            tags=["coordination", "multi_station"],
        ))

    def add_test_case(self, test_case: VerificationTestCase):
        """添加测试用例"""
        self.test_cases.append(test_case)

    def run_test(self, test_case: VerificationTestCase) -> VerificationResult:
        """运行单个测试"""
        start_time = datetime.now()

        result = VerificationResult(
            test_id=test_case.test_id,
            test_name=test_case.name,
            result=TestResult.PASSED,
            score=100.0,
            start_time=start_time,
        )

        try:
            # 运行仿真
            sim_result = self.model.simulate(
                test_case.parameters,
                test_case.scenario,
                test_case.duration
            )

            # ODD边界验证
            odd_verification = self.odd_verifier.verify_all_boundaries(sim_result)
            result.odd_violations = odd_verification["violations"]

            # 计算ODD覆盖率
            if "pressure" in odd_verification["boundary_results"]:
                zone_dist = odd_verification["boundary_results"]["pressure"]["metrics"].get(
                    "zone_distribution", {}
                )
                normal_coverage = zone_dist.get("optimal", 0) + zone_dist.get("normal", 0)
                result.odd_coverage = normal_coverage

            # 提取指标
            result.metrics = self._extract_metrics(sim_result, test_case)

            # 评估准则
            for criterion in test_case.criteria:
                criterion_result = self._evaluate_criterion(criterion, result.metrics)
                result.criteria_results[criterion.name] = criterion_result

                if criterion_result == TestResult.FAILED:
                    result.result = TestResult.FAILED
                    result.score -= 30 * criterion.weight
                elif criterion_result == TestResult.WARNING:
                    if result.result != TestResult.FAILED:
                        result.result = TestResult.WARNING
                    result.score -= 10 * criterion.weight

            # ODD违规降低得分
            if odd_verification["total_violations"] > 0:
                result.result = TestResult.FAILED
                result.score -= 20 * odd_verification["total_violations"]

            result.score = max(0, result.score)

            # 生成建议
            result.recommendations = self._generate_recommendations(result, test_case)

        except Exception as e:
            result.result = TestResult.ERROR
            result.score = 0
            result.issues.append(str(e))
            logger.error(f"测试执行错误: {e}")

        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()

        self.results.append(result)
        return result

    def _extract_metrics(self, sim_result: Dict[str, Any],
                         test_case: VerificationTestCase) -> Dict[str, float]:
        """提取测试指标"""
        metrics = {}

        system = sim_result.get("system", {})

        # 压力指标
        pressure = system.get("pressure", [])
        if len(pressure) > 0:
            metrics["max_pressure"] = np.max(pressure)
            metrics["min_pressure"] = np.min(pressure)
            metrics["pressure_std"] = np.std(pressure)

            # 压力上升率
            initial_pressure = pressure[0] if len(pressure) > 0 else 5.0
            max_pressure = np.max(pressure)
            metrics["max_pressure_rise"] = (max_pressure - initial_pressure) / initial_pressure * 100

        # 频率指标
        frequency = system.get("frequency", [])
        if len(frequency) > 0:
            metrics["max_frequency"] = np.max(frequency)
            metrics["min_frequency"] = np.min(frequency)
            metrics["frequency_std"] = np.std(frequency)

            # 转速超调（基于频率）
            target_freq = 50.0
            max_deviation = max(abs(np.max(frequency) - target_freq),
                               abs(np.min(frequency) - target_freq))
            metrics["speed_overshoot"] = max_deviation / target_freq * 100

        # ODD覆盖率
        # 这里简化处理，实际需要基于ODD状态评估
        metrics["odd_coverage"] = 95.0

        return metrics

    def _evaluate_criterion(self, criterion: VerificationCriteria,
                            metrics: Dict[str, float]) -> TestResult:
        """评估单个准则"""
        # 检查失败条件
        for condition in criterion.fail_conditions:
            if self._check_condition(condition, metrics):
                return TestResult.FAILED

        # 检查警告条件
        for condition in criterion.warning_conditions:
            if self._check_condition(condition, metrics):
                return TestResult.WARNING

        # 检查通过条件
        all_pass_met = True
        for condition in criterion.pass_conditions:
            if not self._check_condition(condition, metrics):
                all_pass_met = False
                break

        return TestResult.PASSED if all_pass_met else TestResult.WARNING

    def _check_condition(self, condition: Dict[str, Any],
                         metrics: Dict[str, float]) -> bool:
        """检查单个条件"""
        metric_name = condition.get("metric", "")
        operator = condition.get("operator", "")
        value = condition.get("value", 0)

        if metric_name not in metrics:
            return False

        metric_value = metrics[metric_name]

        if operator == ">=":
            return metric_value >= value
        elif operator == "<=":
            return metric_value <= value
        elif operator == ">":
            return metric_value > value
        elif operator == "<":
            return metric_value < value
        elif operator == "==":
            return metric_value == value
        elif operator == "!=":
            return metric_value != value

        return False

    def _generate_recommendations(self, result: VerificationResult,
                                   test_case: VerificationTestCase) -> List[str]:
        """生成建议"""
        recommendations = []

        if result.result == TestResult.FAILED:
            # 基于失败的准则生成建议
            for criterion_name, criterion_result in result.criteria_results.items():
                if criterion_result == TestResult.FAILED:
                    recommendations.append(f"需要检查与'{criterion_name}'相关的设计参数")

        if result.odd_coverage < 90:
            recommendations.append("ODD覆盖率不足，建议优化控制策略以提高在正常ODD区域的时间占比")

        if len(result.odd_violations) > 0:
            recommendations.append(f"存在{len(result.odd_violations)}次ODD违规，需要调整设计参数或控制策略")

        return recommendations

    def run_all_tests(self, categories: List[TestCategory] = None) -> VerificationReport:
        """运行所有测试"""
        test_cases = self.test_cases
        if categories:
            test_cases = [tc for tc in test_cases if tc.category in categories]

        report = VerificationReport(
            report_id=f"SIL_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title="SIL验证报告",
            level=VerificationLevel.SIL,
            scope=VerificationScope.SYSTEM,
            created_at=datetime.now(),
            total_tests=len(test_cases),
        )

        for test_case in test_cases:
            result = self.run_test(test_case)

            if result.result == TestResult.PASSED:
                report.passed_tests += 1
            elif result.result == TestResult.FAILED:
                report.failed_tests += 1
            elif result.result == TestResult.WARNING:
                report.warning_tests += 1

            report.test_results.append(result)

        # 计算总分
        if report.total_tests > 0:
            report.overall_score = sum(r.score for r in report.test_results) / report.total_tests

        # ODD验证摘要
        total_odd_violations = sum(len(r.odd_violations) for r in report.test_results)
        avg_odd_coverage = np.mean([r.odd_coverage for r in report.test_results]) if report.test_results else 0

        report.odd_summary = {
            "total_violations": total_odd_violations,
            "average_coverage": avg_odd_coverage,
            "all_boundaries_respected": total_odd_violations == 0,
        }

        # 生成总体建议
        if report.failed_tests > 0:
            report.recommendations.append(f"有{report.failed_tests}个测试失败，需要检查相关设计")
        if total_odd_violations > 0:
            report.recommendations.append("存在ODD违规，需要优化运行策略")

        return report


class HILVerificationFramework:
    """
    HIL验证框架

    功能：
    - 真实控制硬件验证
    - 通信时延验证
    - 信号接口验证
    - 时序确定性验证
    """

    def __init__(self, odd: 'SystemODD', hil_testbench: 'HILTestBench'):
        self.odd = odd
        self.testbench = hil_testbench

        # 测试用例
        self.test_cases: List[VerificationTestCase] = []

        # 验证结果
        self.results: List[VerificationResult] = []

        # 时序要求
        self.timing_requirements = {
            "max_latency_ms": 10.0,
            "max_jitter_ms": 1.0,
            "max_missed_cycles": 0,
        }

        # 初始化HIL测试用例
        self._init_hil_test_cases()

    def _init_hil_test_cases(self):
        """初始化HIL测试用例"""
        # 时序验证
        self.test_cases.append(VerificationTestCase(
            test_id="HIL_TIMING_001",
            name="控制时序确定性验证",
            description="验证控制系统满足10ms确定性时序要求",
            category=TestCategory.PROTECTION,
            scope=VerificationScope.SYSTEM,
            level=VerificationLevel.HIL,
            duration=60.0,
            criteria=[
                VerificationCriteria(
                    name="最大延迟",
                    description="控制延迟不超过10ms",
                    category=TestCategory.PROTECTION,
                    pass_conditions=[
                        {"metric": "max_latency_ms", "operator": "<=", "value": 10.0}
                    ],
                ),
                VerificationCriteria(
                    name="时序抖动",
                    description="时序抖动不超过1ms",
                    category=TestCategory.PROTECTION,
                    pass_conditions=[
                        {"metric": "jitter_ms", "operator": "<=", "value": 1.0}
                    ],
                )
            ],
            priority=1,
            tags=["hil", "timing", "deterministic"],
        ))

        # 保护逻辑验证
        self.test_cases.append(VerificationTestCase(
            test_id="HIL_PROT_001",
            name="保护逻辑响应验证",
            description="验证保护逻辑在真实硬件上的响应正确性",
            category=TestCategory.PROTECTION,
            scope=VerificationScope.SYSTEM,
            level=VerificationLevel.HIL,
            scenario={"type": "protection_test", "fault": "overpressure"},
            duration=30.0,
            criteria=[
                VerificationCriteria(
                    name="保护响应时间",
                    description="保护动作在规定时间内完成",
                    category=TestCategory.PROTECTION,
                    pass_conditions=[
                        {"metric": "protection_response_time", "operator": "<=", "value": 0.5}
                    ],
                )
            ],
            priority=1,
            tags=["hil", "protection"],
        ))

    def run_test(self, test_case: VerificationTestCase) -> VerificationResult:
        """运行HIL测试"""
        start_time = datetime.now()

        result = VerificationResult(
            test_id=test_case.test_id,
            test_name=test_case.name,
            result=TestResult.PASSED,
            score=100.0,
            start_time=start_time,
        )

        try:
            # 配置HIL测试台
            from ..pilot_platform.hil_framework import HILTestCase as HILCase

            hil_case = HILCase(
                test_id=test_case.test_id,
                name=test_case.name,
                description=test_case.description,
                duration=test_case.duration,
                initial_conditions=test_case.parameters,
            )

            # 运行HIL测试
            hil_result = self.testbench.run_test(hil_case)

            # 提取时序指标
            result.metrics["max_latency_ms"] = hil_result.max_latency_ms
            result.metrics["avg_latency_ms"] = hil_result.avg_latency_ms
            result.metrics["jitter_ms"] = hil_result.jitter_ms
            result.metrics["missed_cycles"] = hil_result.missed_cycles

            # 评估时序要求
            if hil_result.max_latency_ms > self.timing_requirements["max_latency_ms"]:
                result.result = TestResult.FAILED
                result.issues.append(
                    f"最大延迟{hil_result.max_latency_ms:.2f}ms超过要求"
                )
                result.score -= 30

            if hil_result.jitter_ms > self.timing_requirements["max_jitter_ms"]:
                result.result = TestResult.WARNING
                result.issues.append(
                    f"时序抖动{hil_result.jitter_ms:.2f}ms超过要求"
                )
                result.score -= 15

            if hil_result.missed_cycles > self.timing_requirements["max_missed_cycles"]:
                result.result = TestResult.FAILED
                result.issues.append(
                    f"错过{hil_result.missed_cycles}个控制周期"
                )
                result.score -= 40

            # 评估准则
            for criterion in test_case.criteria:
                criterion_result = self._evaluate_criterion(criterion, result.metrics)
                result.criteria_results[criterion.name] = criterion_result

            result.score = max(0, result.score)

        except Exception as e:
            result.result = TestResult.ERROR
            result.score = 0
            result.issues.append(str(e))
            logger.error(f"HIL测试执行错误: {e}")

        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()

        self.results.append(result)
        return result

    def _evaluate_criterion(self, criterion: VerificationCriteria,
                            metrics: Dict[str, float]) -> TestResult:
        """评估准则"""
        for condition in criterion.fail_conditions:
            if self._check_condition(condition, metrics):
                return TestResult.FAILED

        for condition in criterion.pass_conditions:
            if not self._check_condition(condition, metrics):
                return TestResult.FAILED

        return TestResult.PASSED

    def _check_condition(self, condition: Dict[str, Any],
                         metrics: Dict[str, float]) -> bool:
        """检查条件"""
        metric_name = condition.get("metric", "")
        operator = condition.get("operator", "")
        value = condition.get("value", 0)

        if metric_name not in metrics:
            return False

        metric_value = metrics[metric_name]

        if operator == "<=":
            return metric_value <= value
        elif operator == ">=":
            return metric_value >= value
        elif operator == "<":
            return metric_value < value
        elif operator == ">":
            return metric_value > value

        return False


class IntegratedVerificationSystem:
    """
    集成验证系统

    整合MIL/SIL/HIL验证的完整系统
    """

    def __init__(self, odd: 'SystemODD', mas: 'ODDAwareMASSystem',
                 model: 'SystemModel', hil_testbench: 'HILTestBench' = None):
        self.odd = odd
        self.mas = mas
        self.model = model

        # SIL验证框架
        self.sil_framework = SILVerificationFramework(odd, mas, model)

        # HIL验证框架（可选）
        self.hil_framework = None
        if hil_testbench:
            self.hil_framework = HILVerificationFramework(odd, hil_testbench)

        # 验证结果
        self.verification_history: List[VerificationReport] = []

    def run_full_verification(self, include_hil: bool = False) -> Dict[str, VerificationReport]:
        """运行完整验证"""
        reports = {}

        # SIL验证
        logger.info("开始SIL验证...")
        sil_report = self.sil_framework.run_all_tests()
        reports["sil"] = sil_report
        logger.info(f"SIL验证完成: {sil_report.passed_tests}/{sil_report.total_tests}通过")

        # HIL验证
        if include_hil and self.hil_framework:
            logger.info("开始HIL验证...")
            hil_report = self._run_hil_verification()
            reports["hil"] = hil_report
            logger.info(f"HIL验证完成: {hil_report.passed_tests}/{hil_report.total_tests}通过")

        self.verification_history.extend(reports.values())
        return reports

    def _run_hil_verification(self) -> VerificationReport:
        """运行HIL验证"""
        report = VerificationReport(
            report_id=f"HIL_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title="HIL验证报告",
            level=VerificationLevel.HIL,
            scope=VerificationScope.SYSTEM,
            created_at=datetime.now(),
            total_tests=len(self.hil_framework.test_cases),
        )

        for test_case in self.hil_framework.test_cases:
            result = self.hil_framework.run_test(test_case)

            if result.result == TestResult.PASSED:
                report.passed_tests += 1
            elif result.result == TestResult.FAILED:
                report.failed_tests += 1
            elif result.result == TestResult.WARNING:
                report.warning_tests += 1

            report.test_results.append(result)

        if report.total_tests > 0:
            report.overall_score = sum(r.score for r in report.test_results) / report.total_tests

        return report

    def generate_comprehensive_report(self, reports: Dict[str, VerificationReport]) -> str:
        """生成综合报告"""
        report_md = """
# 综合验证报告

## 验证概要

| 验证级别 | 总测试数 | 通过 | 失败 | 警告 | 得分 |
|----------|----------|------|------|------|------|
"""
        for level, report in reports.items():
            report_md += f"| {level.upper()} | {report.total_tests} | {report.passed_tests} | "
            report_md += f"{report.failed_tests} | {report.warning_tests} | {report.overall_score:.1f} |\n"

        report_md += "\n## ODD验证结果\n\n"

        for level, report in reports.items():
            if report.odd_summary:
                report_md += f"### {level.upper()}\n"
                report_md += f"- ODD违规次数: {report.odd_summary.get('total_violations', 0)}\n"
                report_md += f"- 平均ODD覆盖率: {report.odd_summary.get('average_coverage', 0):.1f}%\n"
                report_md += f"- 所有边界满足: {'是' if report.odd_summary.get('all_boundaries_respected') else '否'}\n\n"

        report_md += "## 详细测试结果\n\n"

        for level, report in reports.items():
            report_md += f"### {level.upper()}测试\n\n"
            for result in report.test_results:
                status = {
                    TestResult.PASSED: "[PASS]",
                    TestResult.FAILED: "[FAIL]",
                    TestResult.WARNING: "[WARN]",
                    TestResult.ERROR: "[ERROR]",
                }.get(result.result, "")

                report_md += f"#### {result.test_name} {status}\n\n"
                report_md += f"- 得分: {result.score:.1f}\n"
                report_md += f"- 耗时: {result.duration:.2f}s\n"

                if result.issues:
                    report_md += "- 问题:\n"
                    for issue in result.issues:
                        report_md += f"  - {issue}\n"

                if result.recommendations:
                    report_md += "- 建议:\n"
                    for rec in result.recommendations:
                        report_md += f"  - {rec}\n"

                report_md += "\n"

        report_md += "## 总体建议\n\n"

        all_recommendations = []
        for report in reports.values():
            all_recommendations.extend(report.recommendations)

        for rec in list(set(all_recommendations)):
            report_md += f"- {rec}\n"

        return report_md
