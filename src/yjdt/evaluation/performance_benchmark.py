# -*- coding: utf-8 -*-
"""
性能基准测试 - 智能化系统性能评估
Performance Benchmark - Intelligence System Performance Evaluation

功能：
- 性能指标定义
- 基准测试执行
- 结果分析
- 对标评价
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import time


class BenchmarkCategory(Enum):
    """基准测试类别"""
    RESPONSE_TIME = "response_time"         # 响应时间
    ACCURACY = "accuracy"                   # 准确性
    RELIABILITY = "reliability"             # 可靠性
    SCALABILITY = "scalability"             # 可扩展性
    THROUGHPUT = "throughput"               # 吞吐量
    RESOURCE = "resource"                   # 资源消耗


@dataclass
class BenchmarkMetric:
    """基准测试指标"""
    metric_id: str
    name: str
    category: BenchmarkCategory
    description: str
    unit: str
    target_value: float
    threshold_excellent: float
    threshold_good: float
    threshold_acceptable: float
    direction: str = "lower"    # "lower" or "higher" is better


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    metric_id: str
    measured_value: float
    target_value: float
    score: float                            # 0-100
    grade: str                              # A/B/C/D/F
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BenchmarkSuiteResult:
    """基准测试套件结果"""
    suite_id: str
    timestamp: datetime
    overall_score: float
    overall_grade: str
    results: Dict[str, BenchmarkResult]
    category_scores: Dict[BenchmarkCategory, float]
    passed_count: int
    failed_count: int
    summary: str


class PerformanceBenchmark:
    """
    性能基准测试系统

    功能：
    - 定义性能指标
    - 执行基准测试
    - 结果评估
    - 生成报告
    """

    def __init__(self):
        # 基准指标库
        self.metrics: Dict[str, BenchmarkMetric] = {}

        # 测试函数
        self.test_functions: Dict[str, Callable] = {}

        # 测试历史
        self.history: List[BenchmarkSuiteResult] = []

        # 初始化指标
        self._initialize_metrics()

    def _initialize_metrics(self):
        """初始化基准指标"""
        # 响应时间指标
        self._add_metric(
            "RT_001", "控制指令响应时间", BenchmarkCategory.RESPONSE_TIME,
            "从指令发出到执行完成的时间", "ms",
            target=100, excellent=50, good=100, acceptable=200, direction="lower"
        )
        self._add_metric(
            "RT_002", "故障检测响应时间", BenchmarkCategory.RESPONSE_TIME,
            "从故障发生到检测告警的时间", "ms",
            target=500, excellent=200, good=500, acceptable=1000, direction="lower"
        )
        self._add_metric(
            "RT_003", "状态刷新周期", BenchmarkCategory.RESPONSE_TIME,
            "监控数据刷新周期", "ms",
            target=1000, excellent=500, good=1000, acceptable=2000, direction="lower"
        )
        self._add_metric(
            "RT_004", "调度决策时间", BenchmarkCategory.RESPONSE_TIME,
            "优化调度计算时间", "s",
            target=30, excellent=10, good=30, acceptable=60, direction="lower"
        )

        # 准确性指标
        self._add_metric(
            "AC_001", "状态估计精度", BenchmarkCategory.ACCURACY,
            "状态估计误差百分比", "%",
            target=2, excellent=1, good=2, acceptable=5, direction="lower"
        )
        self._add_metric(
            "AC_002", "故障诊断准确率", BenchmarkCategory.ACCURACY,
            "故障正确诊断比例", "%",
            target=95, excellent=98, good=95, acceptable=90, direction="higher"
        )
        self._add_metric(
            "AC_003", "预测准确率", BenchmarkCategory.ACCURACY,
            "短期预测MAPE", "%",
            target=5, excellent=2, good=5, acceptable=10, direction="lower"
        )
        self._add_metric(
            "AC_004", "控制精度", BenchmarkCategory.ACCURACY,
            "设定值跟踪误差", "%",
            target=1, excellent=0.5, good=1, acceptable=2, direction="lower"
        )

        # 可靠性指标
        self._add_metric(
            "RE_001", "系统可用率", BenchmarkCategory.RELIABILITY,
            "系统正常运行时间比例", "%",
            target=99.9, excellent=99.99, good=99.9, acceptable=99, direction="higher"
        )
        self._add_metric(
            "RE_002", "MTBF", BenchmarkCategory.RELIABILITY,
            "平均无故障时间", "h",
            target=10000, excellent=50000, good=10000, acceptable=5000, direction="higher"
        )
        self._add_metric(
            "RE_003", "MTTR", BenchmarkCategory.RELIABILITY,
            "平均修复时间", "min",
            target=30, excellent=10, good=30, acceptable=60, direction="lower"
        )
        self._add_metric(
            "RE_004", "数据完整率", BenchmarkCategory.RELIABILITY,
            "采集数据完整性", "%",
            target=99.9, excellent=99.99, good=99.9, acceptable=99, direction="higher"
        )

        # 吞吐量指标
        self._add_metric(
            "TH_001", "数据处理能力", BenchmarkCategory.THROUGHPUT,
            "每秒处理数据点数", "点/s",
            target=10000, excellent=50000, good=10000, acceptable=5000, direction="higher"
        )
        self._add_metric(
            "TH_002", "并发用户支持", BenchmarkCategory.THROUGHPUT,
            "同时在线用户数", "个",
            target=50, excellent=100, good=50, acceptable=20, direction="higher"
        )
        self._add_metric(
            "TH_003", "告警处理能力", BenchmarkCategory.THROUGHPUT,
            "每秒告警处理数", "个/s",
            target=100, excellent=500, good=100, acceptable=50, direction="higher"
        )

        # 资源消耗指标
        self._add_metric(
            "RS_001", "CPU利用率", BenchmarkCategory.RESOURCE,
            "正常运行时CPU占用", "%",
            target=30, excellent=20, good=30, acceptable=50, direction="lower"
        )
        self._add_metric(
            "RS_002", "内存利用率", BenchmarkCategory.RESOURCE,
            "正常运行时内存占用", "%",
            target=50, excellent=30, good=50, acceptable=70, direction="lower"
        )
        self._add_metric(
            "RS_003", "网络带宽占用", BenchmarkCategory.RESOURCE,
            "网络通信带宽占用比例", "%",
            target=20, excellent=10, good=20, acceptable=40, direction="lower"
        )

        # 可扩展性指标
        self._add_metric(
            "SC_001", "线性扩展性", BenchmarkCategory.SCALABILITY,
            "负载增加时性能下降比例", "%",
            target=10, excellent=5, good=10, acceptable=20, direction="lower"
        )
        self._add_metric(
            "SC_002", "设备接入能力", BenchmarkCategory.SCALABILITY,
            "可接入设备数量上限", "台",
            target=1000, excellent=5000, good=1000, acceptable=500, direction="higher"
        )

    def _add_metric(self, metric_id: str, name: str,
                    category: BenchmarkCategory,
                    description: str, unit: str,
                    target: float, excellent: float,
                    good: float, acceptable: float,
                    direction: str = "lower"):
        """添加基准指标"""
        self.metrics[metric_id] = BenchmarkMetric(
            metric_id=metric_id,
            name=name,
            category=category,
            description=description,
            unit=unit,
            target_value=target,
            threshold_excellent=excellent,
            threshold_good=good,
            threshold_acceptable=acceptable,
            direction=direction,
        )

    def register_test(self, metric_id: str, test_function: Callable):
        """注册测试函数"""
        self.test_functions[metric_id] = test_function

    def run_benchmark(self, metric_id: str,
                      measured_value: float = None) -> BenchmarkResult:
        """
        执行单项基准测试

        Args:
            metric_id: 指标ID
            measured_value: 测量值（若为None则执行测试函数）

        Returns:
            测试结果
        """
        if metric_id not in self.metrics:
            raise ValueError(f"Unknown metric: {metric_id}")

        metric = self.metrics[metric_id]

        # 获取测量值
        if measured_value is None:
            if metric_id in self.test_functions:
                measured_value = self.test_functions[metric_id]()
            else:
                raise ValueError(f"No test function for {metric_id}")

        # 评分
        score, grade = self._evaluate_metric(metric, measured_value)

        # 是否通过
        if metric.direction == "lower":
            passed = measured_value <= metric.threshold_acceptable
        else:
            passed = measured_value >= metric.threshold_acceptable

        return BenchmarkResult(
            metric_id=metric_id,
            measured_value=measured_value,
            target_value=metric.target_value,
            score=score,
            grade=grade,
            passed=passed,
            details={
                "metric_name": metric.name,
                "unit": metric.unit,
                "category": metric.category.value,
            },
        )

    def _evaluate_metric(self, metric: BenchmarkMetric,
                         value: float) -> tuple:
        """评估指标得分和等级"""
        if metric.direction == "lower":
            # 越小越好
            if value <= metric.threshold_excellent:
                score = 100
                grade = "A"
            elif value <= metric.threshold_good:
                # 在excellent和good之间线性插值
                ratio = (value - metric.threshold_excellent) / (metric.threshold_good - metric.threshold_excellent)
                score = 100 - ratio * 15
                grade = "B"
            elif value <= metric.threshold_acceptable:
                ratio = (value - metric.threshold_good) / (metric.threshold_acceptable - metric.threshold_good)
                score = 85 - ratio * 25
                grade = "C"
            else:
                # 超出acceptable
                overshoot = (value - metric.threshold_acceptable) / metric.threshold_acceptable
                score = max(0, 60 - overshoot * 60)
                grade = "D" if score >= 40 else "F"
        else:
            # 越大越好
            if value >= metric.threshold_excellent:
                score = 100
                grade = "A"
            elif value >= metric.threshold_good:
                ratio = (metric.threshold_excellent - value) / (metric.threshold_excellent - metric.threshold_good)
                score = 100 - ratio * 15
                grade = "B"
            elif value >= metric.threshold_acceptable:
                ratio = (metric.threshold_good - value) / (metric.threshold_good - metric.threshold_acceptable)
                score = 85 - ratio * 25
                grade = "C"
            else:
                undershoot = (metric.threshold_acceptable - value) / metric.threshold_acceptable
                score = max(0, 60 - undershoot * 60)
                grade = "D" if score >= 40 else "F"

        return score, grade

    def run_suite(self, measurements: Dict[str, float] = None) -> BenchmarkSuiteResult:
        """
        执行基准测试套件

        Args:
            measurements: 各指标测量值字典

        Returns:
            套件测试结果
        """
        suite_id = f"BENCH_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        results = {}
        category_scores: Dict[BenchmarkCategory, List[float]] = {}

        measurements = measurements or {}

        for metric_id, metric in self.metrics.items():
            value = measurements.get(metric_id)
            if value is not None:
                result = self.run_benchmark(metric_id, value)
                results[metric_id] = result

                # 按类别收集分数
                cat = metric.category
                if cat not in category_scores:
                    category_scores[cat] = []
                category_scores[cat].append(result.score)

        # 计算类别平均分
        cat_avg = {
            cat: np.mean(scores)
            for cat, scores in category_scores.items()
        }

        # 计算总体分数
        if results:
            overall_score = np.mean([r.score for r in results.values()])
        else:
            overall_score = 0

        # 确定总体等级
        if overall_score >= 90:
            overall_grade = "A"
        elif overall_score >= 75:
            overall_grade = "B"
        elif overall_score >= 60:
            overall_grade = "C"
        elif overall_score >= 40:
            overall_grade = "D"
        else:
            overall_grade = "F"

        # 统计通过/失败
        passed_count = sum(1 for r in results.values() if r.passed)
        failed_count = len(results) - passed_count

        # 生成摘要
        summary = self._generate_summary(results, overall_score, overall_grade)

        suite_result = BenchmarkSuiteResult(
            suite_id=suite_id,
            timestamp=datetime.now(),
            overall_score=overall_score,
            overall_grade=overall_grade,
            results=results,
            category_scores=cat_avg,
            passed_count=passed_count,
            failed_count=failed_count,
            summary=summary,
        )

        self.history.append(suite_result)
        return suite_result

    def _generate_summary(self, results: Dict[str, BenchmarkResult],
                          score: float, grade: str) -> str:
        """生成测试摘要"""
        total = len(results)
        passed = sum(1 for r in results.values() if r.passed)

        # 找出最好和最差的指标
        if results:
            best = max(results.values(), key=lambda r: r.score)
            worst = min(results.values(), key=lambda r: r.score)

            summary = (
                f"基准测试完成：总分{score:.1f}分（{grade}级），"
                f"通过{passed}/{total}项。"
                f"最佳：{best.details['metric_name']}（{best.score:.0f}分），"
                f"待改进：{worst.details['metric_name']}（{worst.score:.0f}分）。"
            )
        else:
            summary = "无测试结果"

        return summary

    def compare_results(self, result1: BenchmarkSuiteResult,
                        result2: BenchmarkSuiteResult) -> Dict[str, Any]:
        """比较两次测试结果"""
        comparison = {
            "suite1": result1.suite_id,
            "suite2": result2.suite_id,
            "time_span": (result2.timestamp - result1.timestamp).total_seconds() / 3600,
            "score_change": result2.overall_score - result1.overall_score,
            "grade_change": f"{result1.overall_grade} -> {result2.overall_grade}",
            "metric_changes": {},
            "improved": [],
            "degraded": [],
        }

        # 比较各指标
        for metric_id in set(result1.results.keys()) & set(result2.results.keys()):
            r1 = result1.results[metric_id]
            r2 = result2.results[metric_id]
            change = r2.score - r1.score

            comparison["metric_changes"][metric_id] = {
                "name": r1.details["metric_name"],
                "score_change": change,
                "value_change": r2.measured_value - r1.measured_value,
            }

            if change > 5:
                comparison["improved"].append(r1.details["metric_name"])
            elif change < -5:
                comparison["degraded"].append(r1.details["metric_name"])

        comparison["overall_improved"] = comparison["score_change"] > 0

        return comparison

    def get_metrics_by_category(self, category: BenchmarkCategory) -> List[BenchmarkMetric]:
        """按类别获取指标"""
        return [m for m in self.metrics.values() if m.category == category]

    def generate_report(self, result: BenchmarkSuiteResult) -> Dict[str, Any]:
        """生成测试报告"""
        # 按类别组织结果
        by_category = {}
        for metric_id, bench_result in result.results.items():
            cat = bench_result.details["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append({
                "metric": bench_result.details["metric_name"],
                "value": bench_result.measured_value,
                "target": bench_result.target_value,
                "unit": bench_result.details["unit"],
                "score": bench_result.score,
                "grade": bench_result.grade,
                "passed": bench_result.passed,
            })

        return {
            "report_id": f"RPT_{result.suite_id}",
            "generated_at": datetime.now().isoformat(),
            "executive_summary": {
                "overall_score": round(result.overall_score, 1),
                "overall_grade": result.overall_grade,
                "passed": result.passed_count,
                "failed": result.failed_count,
                "total": result.passed_count + result.failed_count,
            },
            "category_scores": {
                cat.value: round(score, 1)
                for cat, score in result.category_scores.items()
            },
            "detailed_results": by_category,
            "summary": result.summary,
            "recommendations": self._generate_recommendations(result),
        }

    def _generate_recommendations(self, result: BenchmarkSuiteResult) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 按分数排序，找出最差的指标
        sorted_results = sorted(
            result.results.values(),
            key=lambda r: r.score
        )

        for r in sorted_results[:5]:  # 最差的5项
            if r.score < 60:
                metric = self.metrics[r.metric_id]
                recommendations.append(
                    f"优先改进{r.details['metric_name']}："
                    f"当前{r.measured_value}{r.details['unit']}，"
                    f"目标{metric.target_value}{r.details['unit']}"
                )

        return recommendations

