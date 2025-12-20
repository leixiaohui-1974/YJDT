"""
软件在环测试框架
Software-in-the-Loop (SIL) Testing Framework

对标无人驾驶汽车的SIL测试方法，实现：
- 全场景自动化测试
- 性能评估和对比
- 覆盖率分析
- 测试报告生成
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import hashlib


class TestStatus(Enum):
    """测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestPriority(Enum):
    """测试优先级"""
    CRITICAL = 1    # 关键测试
    HIGH = 2        # 高优先级
    MEDIUM = 3      # 中等优先级
    LOW = 4         # 低优先级


@dataclass
class EvaluationCriteria:
    """评估准则"""
    name: str
    description: str = ""

    # 性能指标阈值
    max_overshoot: float = 30.0          # 最大超调量 (%)
    max_settling_time: float = 60.0      # 最大调节时间 (s)
    max_rise_time: float = 10.0          # 最大上升时间 (s)
    max_steady_error: float = 0.02       # 最大稳态误差 (pu)

    # 安全指标阈值
    max_speed_rise: float = 30.0         # 最大转速上升 (%)
    max_pressure_rise: float = 50.0      # 最大压力上升 (%)
    min_pressure: float = -0.3           # 最小压力 (MPa) - 防止气蚀

    # 稳定性指标
    min_gain_margin: float = 2.0         # 最小增益裕度
    min_phase_margin: float = 30.0       # 最小相位裕度 (度)

    # 可靠性指标
    fault_detection_time: float = 5.0    # 故障检测时间 (s)
    fault_isolation_success: bool = True  # 故障隔离成功

    # 权重
    weights: Dict[str, float] = field(default_factory=lambda: {
        'performance': 0.30,
        'safety': 0.40,
        'stability': 0.20,
        'reliability': 0.10,
    })


@dataclass
class TestCase:
    """测试用例"""
    test_id: str
    name: str
    description: str = ""
    priority: TestPriority = TestPriority.MEDIUM

    # 场景引用
    scenario_id: str = ""
    scenario: Any = None

    # 评估准则
    criteria: EvaluationCriteria = field(default_factory=EvaluationCriteria)

    # 测试配置
    timeout: float = 600.0               # 超时时间 (s)
    retry_count: int = 0                 # 重试次数
    parallel: bool = False               # 是否并行执行

    # 元数据
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    author: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    status: TestStatus
    score: float = 0.0

    # 详细指标
    metrics: Dict[str, float] = field(default_factory=dict)
    criteria_results: Dict[str, bool] = field(default_factory=dict)

    # 执行信息
    start_time: str = ""
    end_time: str = ""
    duration: float = 0.0

    # 仿真数据
    simulation_data: Dict[str, np.ndarray] = field(default_factory=dict)

    # 日志和错误
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'test_id': self.test_id,
            'status': self.status.value,
            'score': self.score,
            'metrics': self.metrics,
            'criteria_results': self.criteria_results,
            'duration': self.duration,
            'errors': self.errors,
        }


@dataclass
class TestSuite:
    """测试套件"""
    suite_id: str
    name: str
    description: str = ""

    # 测试用例
    test_cases: List[TestCase] = field(default_factory=list)

    # 执行配置
    stop_on_failure: bool = False
    parallel_execution: bool = False
    max_parallel: int = 4

    # 统计信息
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0

    def add_test(self, test: TestCase):
        """添加测试用例"""
        self.test_cases.append(test)
        self.total_tests = len(self.test_cases)

    def get_tests_by_priority(self, priority: TestPriority) -> List[TestCase]:
        """按优先级获取测试"""
        return [t for t in self.test_cases if t.priority == priority]

    def get_tests_by_tag(self, tag: str) -> List[TestCase]:
        """按标签获取测试"""
        return [t for t in self.test_cases if tag in t.tags]


class TestReport:
    """
    测试报告

    生成和管理测试报告
    """

    def __init__(self, suite: TestSuite, results: List[TestResult]):
        self.suite = suite
        self.results = results
        self.generated_at = datetime.now().isoformat()

        # 统计
        self.summary = self._generate_summary()

    def _generate_summary(self) -> Dict:
        """生成摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        error = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)

        avg_score = np.mean([r.score for r in self.results]) if self.results else 0

        total_duration = sum(r.duration for r in self.results)

        return {
            'suite_name': self.suite.name,
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'error': error,
            'skipped': skipped,
            'pass_rate': passed / total * 100 if total > 0 else 0,
            'average_score': avg_score,
            'total_duration': total_duration,
        }

    def generate_markdown(self) -> str:
        """生成Markdown报告"""
        report = f"""
# 软件在环测试报告

**测试套件**: {self.suite.name}
**生成时间**: {self.generated_at}

## 1. 测试摘要

| 指标 | 值 |
|------|-----|
| 总测试数 | {self.summary['total_tests']} |
| 通过 | {self.summary['passed']} |
| 失败 | {self.summary['failed']} |
| 错误 | {self.summary['error']} |
| 跳过 | {self.summary['skipped']} |
| 通过率 | {self.summary['pass_rate']:.1f}% |
| 平均得分 | {self.summary['average_score']:.2f} |
| 总耗时 | {self.summary['total_duration']:.2f}s |

## 2. 详细结果

"""
        for result in self.results:
            status_emoji = {
                TestStatus.PASSED: "[PASS]",
                TestStatus.FAILED: "[FAIL]",
                TestStatus.ERROR: "[ERROR]",
                TestStatus.SKIPPED: "[SKIP]",
            }.get(result.status, "")

            report += f"""
### {result.test_id} {status_emoji}

- 状态: {result.status.value}
- 得分: {result.score:.2f}
- 耗时: {result.duration:.2f}s

**关键指标:**
"""
            for metric, value in result.metrics.items():
                report += f"- {metric}: {value:.4f}\n"

            if result.errors:
                report += "\n**错误:**\n"
                for error in result.errors:
                    report += f"- {error}\n"

        report += """
## 3. 建议

"""
        # 根据结果生成建议
        if self.summary['pass_rate'] < 80:
            report += "- 警告：通过率低于80%，需要检查系统设计\n"

        failed_tests = [r for r in self.results if r.status == TestStatus.FAILED]
        if failed_tests:
            report += f"- 有{len(failed_tests)}个测试失败，需要分析原因\n"

        return report

    def export_json(self, filepath: str):
        """导出JSON格式"""
        data = {
            'suite': {
                'id': self.suite.suite_id,
                'name': self.suite.name,
                'description': self.suite.description,
            },
            'summary': self.summary,
            'results': [r.to_dict() for r in self.results],
            'generated_at': self.generated_at,
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class SILTestFramework:
    """
    软件在环测试框架

    对标无人驾驶汽车的测试方法
    """

    def __init__(self):
        self.test_suites: Dict[str, TestSuite] = {}
        self.results: Dict[str, TestResult] = {}

        # 仿真引擎
        self.simulator = None

        # 场景库
        self.scenario_library = None

        # 设计方案
        self.design_schemes: Dict[str, Any] = {}

        # 评估器
        self.evaluator = TestEvaluator()

    def set_simulator(self, simulator):
        """设置仿真器"""
        self.simulator = simulator

    def set_scenario_library(self, library):
        """设置场景库"""
        self.scenario_library = library

    def add_design_scheme(self, scheme_id: str, scheme):
        """添加设计方案"""
        self.design_schemes[scheme_id] = scheme

    def create_test_suite(
        self,
        suite_id: str,
        name: str,
        coverage: str = "standard"
    ) -> TestSuite:
        """
        创建测试套件

        Args:
            suite_id: 套件ID
            name: 套件名称
            coverage: 覆盖范围 ("minimal", "standard", "comprehensive")

        Returns:
            测试套件
        """
        suite = TestSuite(suite_id=suite_id, name=name)

        # 根据覆盖范围添加测试用例
        if self.scenario_library:
            scenarios = self.scenario_library.generate_test_suite(coverage)

            for scenario in scenarios:
                test = TestCase(
                    test_id=f"TEST_{scenario.scenario_id}",
                    name=f"测试-{scenario.name}",
                    description=scenario.description,
                    scenario_id=scenario.scenario_id,
                    scenario=scenario,
                    priority=self._map_severity_to_priority(scenario.severity),
                    tags=scenario.tags,
                )
                suite.add_test(test)

        self.test_suites[suite_id] = suite
        return suite

    def _map_severity_to_priority(self, severity) -> TestPriority:
        """映射严重程度到测试优先级"""
        from yjdt.scenarios.generator import SeverityLevel
        mapping = {
            SeverityLevel.CRITICAL: TestPriority.CRITICAL,
            SeverityLevel.HIGH: TestPriority.HIGH,
            SeverityLevel.MEDIUM: TestPriority.MEDIUM,
            SeverityLevel.LOW: TestPriority.LOW,
            SeverityLevel.INFO: TestPriority.LOW,
        }
        return mapping.get(severity, TestPriority.MEDIUM)

    def run_test(self, test: TestCase) -> TestResult:
        """
        运行单个测试

        Args:
            test: 测试用例

        Returns:
            测试结果
        """
        result = TestResult(
            test_id=test.test_id,
            status=TestStatus.RUNNING,
            start_time=datetime.now().isoformat(),
        )

        try:
            # 运行仿真
            if self.simulator and test.scenario:
                sim_result = self.simulator.run_scenario(test.scenario)
                result.simulation_data = sim_result.data

                # 评估结果
                evaluation = self.evaluator.evaluate(
                    sim_result,
                    test.criteria,
                    test.scenario
                )

                result.metrics = evaluation['metrics']
                result.criteria_results = evaluation['criteria_results']
                result.score = evaluation['score']

                # 判断通过/失败
                if evaluation['all_passed']:
                    result.status = TestStatus.PASSED
                else:
                    result.status = TestStatus.FAILED
                    result.errors = evaluation['failures']

            else:
                result.status = TestStatus.SKIPPED
                result.logs.append("缺少仿真器或场景")

        except Exception as e:
            result.status = TestStatus.ERROR
            result.errors.append(str(e))

        result.end_time = datetime.now().isoformat()
        # 计算耗时
        start = datetime.fromisoformat(result.start_time)
        end = datetime.fromisoformat(result.end_time)
        result.duration = (end - start).total_seconds()

        self.results[test.test_id] = result
        return result

    def run_suite(self, suite: TestSuite) -> TestReport:
        """
        运行测试套件

        Args:
            suite: 测试套件

        Returns:
            测试报告
        """
        results = []

        # 按优先级排序
        sorted_tests = sorted(suite.test_cases, key=lambda t: t.priority.value)

        for test in sorted_tests:
            result = self.run_test(test)
            results.append(result)

            # 更新统计
            if result.status == TestStatus.PASSED:
                suite.passed_tests += 1
            elif result.status == TestStatus.FAILED:
                suite.failed_tests += 1

                if suite.stop_on_failure:
                    break

            elif result.status == TestStatus.ERROR:
                suite.error_tests += 1

        return TestReport(suite, results)

    def compare_schemes(
        self,
        scheme_ids: List[str],
        suite: TestSuite
    ) -> Dict[str, TestReport]:
        """
        对比多个设计方案

        Args:
            scheme_ids: 方案ID列表
            suite: 测试套件

        Returns:
            各方案的测试报告
        """
        reports = {}

        for scheme_id in scheme_ids:
            scheme = self.design_schemes.get(scheme_id)
            if scheme is None:
                continue

            # 配置仿真器使用该方案
            # (实际实现需要根据方案重新配置仿真器)

            report = self.run_suite(suite)
            reports[scheme_id] = report

        return reports

    def generate_comparison_report(
        self,
        reports: Dict[str, TestReport]
    ) -> str:
        """生成对比报告"""
        report = """
# 设计方案对比测试报告

## 综合对比

| 方案 | 通过率 | 平均得分 | 总耗时 |
|------|--------|----------|--------|
"""
        for scheme_id, test_report in reports.items():
            summary = test_report.summary
            report += f"| {scheme_id} | {summary['pass_rate']:.1f}% | {summary['average_score']:.2f} | {summary['total_duration']:.1f}s |\n"

        report += "\n## 详细分析\n"

        # 找出最佳方案
        best_scheme = max(reports.items(), key=lambda x: x[1].summary['average_score'])
        report += f"\n**推荐方案**: {best_scheme[0]} (得分: {best_scheme[1].summary['average_score']:.2f})\n"

        return report


class TestEvaluator:
    """测试评估器"""

    def evaluate(
        self,
        sim_result,
        criteria: EvaluationCriteria,
        scenario
    ) -> Dict:
        """
        评估仿真结果

        Args:
            sim_result: 仿真结果
            criteria: 评估准则
            scenario: 场景

        Returns:
            评估结果
        """
        metrics = {}
        criteria_results = {}
        failures = []

        # 提取关键数据
        time = sim_result.time if hasattr(sim_result, 'time') else np.array([])
        data = sim_result.data if hasattr(sim_result, 'data') else {}

        # 性能评估
        if 'speed' in data:
            speed = data['speed']
            if len(speed) > 0:
                # 超调量
                rated_speed = 166.7
                overshoot = (np.max(speed) - rated_speed) / rated_speed * 100
                metrics['overshoot'] = overshoot
                passed = overshoot <= criteria.max_overshoot
                criteria_results['max_overshoot'] = passed
                if not passed:
                    failures.append(f"超调量超限: {overshoot:.1f}% > {criteria.max_overshoot}%")

                # 转速上升
                speed_rise = (np.max(speed) - speed[0]) / speed[0] * 100 if speed[0] > 0 else 0
                metrics['speed_rise'] = speed_rise
                passed = speed_rise <= criteria.max_speed_rise
                criteria_results['max_speed_rise'] = passed
                if not passed:
                    failures.append(f"转速上升超限: {speed_rise:.1f}%")

        # 调节时间
        if 'speed' in data and len(time) > 0:
            speed = data['speed']
            rated_speed = 166.7
            tolerance = 0.02 * rated_speed

            settled = np.abs(speed - rated_speed) < tolerance
            if np.any(settled):
                settling_idx = np.where(settled)[0]
                if len(settling_idx) > 0:
                    # 找到最后一个超出容差的时刻
                    not_settled = np.where(~settled)[0]
                    if len(not_settled) > 0:
                        settling_time = time[not_settled[-1]]
                    else:
                        settling_time = 0
                else:
                    settling_time = time[-1]
            else:
                settling_time = time[-1]

            metrics['settling_time'] = settling_time
            passed = settling_time <= criteria.max_settling_time
            criteria_results['max_settling_time'] = passed
            if not passed:
                failures.append(f"调节时间超限: {settling_time:.1f}s")

        # 压力评估
        if 'pressure' in data:
            pressure = data['pressure']
            if len(pressure) > 0:
                max_pressure = np.max(pressure)
                min_pressure = np.min(pressure)

                metrics['max_pressure'] = max_pressure
                metrics['min_pressure'] = min_pressure

                # 压力上升
                pressure_rise = (max_pressure - pressure[0]) / (pressure[0] + 1e-6) * 100
                passed = pressure_rise <= criteria.max_pressure_rise
                criteria_results['max_pressure_rise'] = passed
                if not passed:
                    failures.append(f"压力上升超限: {pressure_rise:.1f}%")

                # 负压检查
                passed = min_pressure >= criteria.min_pressure
                criteria_results['min_pressure'] = passed
                if not passed:
                    failures.append(f"出现负压: {min_pressure:.2f} MPa")

        # 稳态误差
        if 'speed' in data and len(data['speed']) > 100:
            steady_speed = np.mean(data['speed'][-100:])
            steady_error = abs(steady_speed - 166.7) / 166.7
            metrics['steady_error'] = steady_error
            passed = steady_error <= criteria.max_steady_error
            criteria_results['max_steady_error'] = passed
            if not passed:
                failures.append(f"稳态误差超限: {steady_error*100:.2f}%")

        # 计算综合得分
        score = self._calculate_score(metrics, criteria_results, criteria)

        all_passed = all(criteria_results.values()) if criteria_results else True

        return {
            'metrics': metrics,
            'criteria_results': criteria_results,
            'failures': failures,
            'score': score,
            'all_passed': all_passed,
        }

    def _calculate_score(
        self,
        metrics: Dict[str, float],
        criteria_results: Dict[str, bool],
        criteria: EvaluationCriteria
    ) -> float:
        """计算综合得分"""
        scores = {}

        # 性能得分
        perf_score = 100
        if 'overshoot' in metrics:
            perf_score -= min(metrics['overshoot'], 50)
        if 'settling_time' in metrics:
            perf_score -= min(metrics['settling_time'] / 2, 30)
        scores['performance'] = max(0, perf_score)

        # 安全得分
        safety_score = 100
        failed_safety = sum(
            1 for k, v in criteria_results.items()
            if 'pressure' in k or 'speed_rise' in k
            if not v
        )
        safety_score -= failed_safety * 30
        scores['safety'] = max(0, safety_score)

        # 稳定性得分
        stability_score = 100
        if 'steady_error' in metrics:
            stability_score -= metrics['steady_error'] * 500
        scores['stability'] = max(0, stability_score)

        # 可靠性得分
        reliability_score = 100 if all(criteria_results.values()) else 70
        scores['reliability'] = reliability_score

        # 加权总分
        total = sum(
            scores.get(k, 0) * w
            for k, w in criteria.weights.items()
        )

        return total
