# -*- coding: utf-8 -*-
"""
测试报告生成器 - Test Report Generator

功能：
- 测试报告生成
- 覆盖率报告
- 性能报告
- 合规性报告
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json


class ReportFormat(Enum):
    """报告格式"""
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: Any
    order: int = 0


@dataclass
class CoverageReport:
    """覆盖率报告"""
    report_id: str
    timestamp: datetime

    # 场景覆盖
    scenario_total: int
    scenario_covered: int
    scenario_coverage: float

    # 功能覆盖
    function_total: int
    function_covered: int
    function_coverage: float

    # 代码覆盖
    code_lines_total: int = 0
    code_lines_covered: int = 0
    code_coverage: float = 0.0

    # 按类别
    category_coverage: Dict[str, float] = field(default_factory=dict)

    # 未覆盖项
    uncovered_items: List[str] = field(default_factory=list)


@dataclass
class PerformanceReport:
    """性能报告"""
    report_id: str
    timestamp: datetime

    # 响应时间
    avg_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float

    # 吞吐量
    throughput: float
    peak_throughput: float

    # 资源使用
    avg_cpu: float
    max_cpu: float
    avg_memory: float
    max_memory: float

    # 稳定性
    error_rate: float
    timeout_rate: float

    # 详细数据
    metrics_history: Dict[str, List[float]] = field(default_factory=dict)


@dataclass
class ComplianceReport:
    """合规性报告"""
    report_id: str
    timestamp: datetime

    # 合规标准
    standards: List[str]

    # 检查结果
    total_checks: int
    passed_checks: int
    failed_checks: int
    compliance_rate: float

    # 违规项
    violations: List[Dict[str, Any]] = field(default_factory=list)

    # 建议
    recommendations: List[str] = field(default_factory=list)


class TestReportGenerator:
    """
    测试报告生成器

    功能：
    - 生成各类测试报告
    - 多格式输出
    - 报告模板
    """

    def __init__(self):
        self.reports: List[Any] = []
        self.templates: Dict[str, str] = {}

        self._init_templates()

    def _init_templates(self):
        """初始化报告模板"""
        self.templates["summary"] = """
# 测试执行报告

## 概述
- 报告ID: {report_id}
- 生成时间: {timestamp}
- 测试状态: {status}

## 测试结果
- 总测试数: {total}
- 通过: {passed}
- 失败: {failed}
- 跳过: {skipped}
- 通过率: {pass_rate:.1f}%

## 执行时间
- 开始时间: {start_time}
- 结束时间: {end_time}
- 总耗时: {duration:.2f}秒

## 失败用例
{failed_cases}

## 建议
{recommendations}
"""

        self.templates["coverage"] = """
# 覆盖率报告

## 场景覆盖
- 总场景数: {scenario_total}
- 已覆盖: {scenario_covered}
- 覆盖率: {scenario_coverage:.1f}%

## 功能覆盖
- 总功能数: {function_total}
- 已覆盖: {function_covered}
- 覆盖率: {function_coverage:.1f}%

## 按类别覆盖率
{category_details}

## 未覆盖项
{uncovered_list}
"""

    def generate_summary_report(self, test_results: List[Any],
                                 format: ReportFormat = ReportFormat.MARKDOWN) -> str:
        """
        生成摘要报告

        Args:
            test_results: 测试结果列表
            format: 输出格式

        Returns:
            报告内容
        """
        report_id = f"RPT_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 统计
        total = len(test_results)
        passed = sum(1 for r in test_results if getattr(r, 'status', None) == 'passed' or
                     (hasattr(r, 'status') and r.status.value == 'passed'))
        failed = sum(1 for r in test_results if getattr(r, 'status', None) == 'failed' or
                     (hasattr(r, 'status') and r.status.value == 'failed'))
        skipped = total - passed - failed

        pass_rate = passed / total * 100 if total > 0 else 0

        # 时间统计
        if test_results and hasattr(test_results[0], 'start_time'):
            start_time = min(r.start_time for r in test_results if hasattr(r, 'start_time'))
            end_time = max(r.end_time for r in test_results if hasattr(r, 'end_time') and r.end_time)
            duration = (end_time - start_time).total_seconds()
        else:
            start_time = datetime.now()
            end_time = datetime.now()
            duration = 0

        # 失败用例
        failed_cases = []
        for r in test_results:
            status = getattr(r, 'status', None)
            if status and (status == 'failed' or getattr(status, 'value', '') == 'failed'):
                failed_cases.append(f"- {getattr(r, 'test_name', r.test_id)}: {getattr(r, 'error_message', '')}")

        failed_cases_str = "\n".join(failed_cases) if failed_cases else "无"

        # 建议
        recommendations = []
        if failed > 0:
            recommendations.append(f"有{failed}个测试用例失败，需要排查原因")
        if pass_rate < 80:
            recommendations.append("测试通过率低于80%，建议加强质量管控")
        if pass_rate >= 95:
            recommendations.append("测试通过率良好，保持当前质量水平")

        recommendations_str = "\n".join(f"- {r}" for r in recommendations)

        # 生成报告
        if format == ReportFormat.MARKDOWN:
            report = self.templates["summary"].format(
                report_id=report_id,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status="通过" if failed == 0 else "失败",
                total=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                pass_rate=pass_rate,
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(start_time, 'strftime') else str(start_time),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(end_time, 'strftime') else str(end_time),
                duration=duration,
                failed_cases=failed_cases_str,
                recommendations=recommendations_str,
            )
        elif format == ReportFormat.JSON:
            report = json.dumps({
                "report_id": report_id,
                "timestamp": datetime.now().isoformat(),
                "status": "passed" if failed == 0 else "failed",
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "pass_rate": pass_rate,
                },
                "duration_seconds": duration,
                "failed_cases": failed_cases,
                "recommendations": recommendations,
            }, ensure_ascii=False, indent=2)
        else:
            report = f"Report {report_id}: {passed}/{total} passed"

        return report

    def generate_coverage_report(self, coverage_data: Dict[str, Any],
                                  format: ReportFormat = ReportFormat.MARKDOWN) -> CoverageReport:
        """
        生成覆盖率报告

        Args:
            coverage_data: 覆盖率数据
            format: 输出格式

        Returns:
            覆盖率报告
        """
        report = CoverageReport(
            report_id=f"COV_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now(),
            scenario_total=coverage_data.get("scenario_total", 0),
            scenario_covered=coverage_data.get("scenario_covered", 0),
            scenario_coverage=coverage_data.get("scenario_coverage", 0),
            function_total=coverage_data.get("function_total", 0),
            function_covered=coverage_data.get("function_covered", 0),
            function_coverage=coverage_data.get("function_coverage", 0),
            category_coverage=coverage_data.get("category_coverage", {}),
            uncovered_items=coverage_data.get("uncovered_items", []),
        )

        self.reports.append(report)
        return report

    def generate_performance_report(self, performance_data: Dict[str, Any]) -> PerformanceReport:
        """
        生成性能报告

        Args:
            performance_data: 性能数据

        Returns:
            性能报告
        """
        response_times = performance_data.get("response_times", [0])

        report = PerformanceReport(
            report_id=f"PERF_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now(),
            avg_response_time=np.mean(response_times),
            max_response_time=np.max(response_times),
            p95_response_time=np.percentile(response_times, 95),
            p99_response_time=np.percentile(response_times, 99),
            throughput=performance_data.get("throughput", 0),
            peak_throughput=performance_data.get("peak_throughput", 0),
            avg_cpu=performance_data.get("avg_cpu", 0),
            max_cpu=performance_data.get("max_cpu", 0),
            avg_memory=performance_data.get("avg_memory", 0),
            max_memory=performance_data.get("max_memory", 0),
            error_rate=performance_data.get("error_rate", 0),
            timeout_rate=performance_data.get("timeout_rate", 0),
            metrics_history=performance_data.get("metrics_history", {}),
        )

        self.reports.append(report)
        return report

    def generate_compliance_report(self, compliance_data: Dict[str, Any]) -> ComplianceReport:
        """
        生成合规性报告

        Args:
            compliance_data: 合规性数据

        Returns:
            合规性报告
        """
        checks = compliance_data.get("checks", [])
        passed = sum(1 for c in checks if c.get("passed", False))
        failed = len(checks) - passed

        report = ComplianceReport(
            report_id=f"COMP_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now(),
            standards=compliance_data.get("standards", []),
            total_checks=len(checks),
            passed_checks=passed,
            failed_checks=failed,
            compliance_rate=passed / len(checks) * 100 if checks else 0,
            violations=[c for c in checks if not c.get("passed", False)],
            recommendations=compliance_data.get("recommendations", []),
        )

        self.reports.append(report)
        return report

    def generate_comprehensive_report(self, test_results: List[Any],
                                        coverage_data: Dict[str, Any],
                                        performance_data: Dict[str, Any],
                                        format: ReportFormat = ReportFormat.JSON) -> Dict[str, Any]:
        """
        生成综合报告

        Args:
            test_results: 测试结果
            coverage_data: 覆盖率数据
            performance_data: 性能数据
            format: 输出格式

        Returns:
            综合报告
        """
        report_id = f"FULL_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 生成各类报告
        summary = self.generate_summary_report(test_results, ReportFormat.JSON)
        coverage = self.generate_coverage_report(coverage_data)
        performance = self.generate_performance_report(performance_data)

        # 计算综合评分
        test_score = (json.loads(summary)["summary"]["pass_rate"]
                     if isinstance(summary, str) else 0)
        coverage_score = coverage.scenario_coverage
        performance_score = max(0, 100 - performance.avg_response_time / 10)

        overall_score = (test_score * 0.4 + coverage_score * 0.3 + performance_score * 0.3)

        comprehensive = {
            "report_id": report_id,
            "timestamp": datetime.now().isoformat(),
            "overall_score": overall_score,
            "grade": self._score_to_grade(overall_score),
            "test_summary": json.loads(summary) if isinstance(summary, str) else summary,
            "coverage": {
                "scenario_coverage": coverage.scenario_coverage,
                "function_coverage": coverage.function_coverage,
            },
            "performance": {
                "avg_response_time": performance.avg_response_time,
                "p95_response_time": performance.p95_response_time,
                "error_rate": performance.error_rate,
            },
            "recommendations": self._generate_recommendations(
                test_score, coverage_score, performance_score
            ),
        }

        return comprehensive

    def _score_to_grade(self, score: float) -> str:
        """分数转等级"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_recommendations(self, test_score: float,
                                   coverage_score: float,
                                   performance_score: float) -> List[str]:
        """生成建议"""
        recommendations = []

        if test_score < 80:
            recommendations.append("测试通过率低于80%，建议排查失败用例")
        if coverage_score < 80:
            recommendations.append("场景覆盖率不足80%，建议扩展测试场景")
        if performance_score < 70:
            recommendations.append("响应时间较长，建议进行性能优化")

        if not recommendations:
            recommendations.append("各项指标良好，保持当前质量水平")

        return recommendations

    def export_report(self, report: Any, filepath: str,
                      format: ReportFormat = ReportFormat.JSON):
        """
        导出报告

        Args:
            report: 报告对象
            filepath: 文件路径
            format: 输出格式
        """
        if format == ReportFormat.JSON:
            with open(filepath, 'w', encoding='utf-8') as f:
                if hasattr(report, '__dict__'):
                    json.dump(report.__dict__, f, ensure_ascii=False, indent=2, default=str)
                else:
                    json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        elif format == ReportFormat.MARKDOWN:
            with open(filepath, 'w', encoding='utf-8') as f:
                if isinstance(report, str):
                    f.write(report)
                else:
                    f.write(f"# Report\n\n{report}")

    def get_report_history(self, limit: int = 10) -> List[Any]:
        """获取报告历史"""
        return self.reports[-limit:]

