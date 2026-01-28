# -*- coding: utf-8 -*-
"""
YJDT报告生成器

自动生成各类分析报告
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: str
    level: int = 2
    subsections: List['ReportSection'] = field(default_factory=list)


@dataclass
class SimulationReport:
    """仿真报告"""
    simulation_id: str
    scenario_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    time_steps: int
    status: str
    metrics: Dict[str, float]
    time_series_summary: Dict[str, Dict]
    violations: List[Dict]
    conclusions: List[str]


@dataclass
class OptimizationReport:
    """优化报告"""
    optimization_id: str
    target: str
    algorithm: str
    start_time: datetime
    end_time: datetime
    iterations: int
    initial_objective: float
    final_objective: float
    improvement: float
    optimal_parameters: Dict[str, float]
    convergence_history: List[float]
    constraints_satisfied: bool
    recommendations: List[str]


@dataclass
class VerificationReport:
    """验证报告"""
    verification_id: str
    design_id: str
    verification_level: str
    start_time: datetime
    end_time: datetime
    scenarios_total: int
    scenarios_passed: int
    scenarios_failed: int
    overall_status: str
    criteria_results: List[Dict]
    odd_compliance: Dict
    recommendations: List[str]


@dataclass
class SystemReport:
    """系统综合报告"""
    report_id: str
    report_type: str
    generated_at: datetime
    system_version: str
    project_name: str
    sections: List[ReportSection] = field(default_factory=list)
    simulation_reports: List[SimulationReport] = field(default_factory=list)
    optimization_reports: List[OptimizationReport] = field(default_factory=list)
    verification_reports: List[VerificationReport] = field(default_factory=list)


class ReportGenerator:
    """报告生成器"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_simulation_report(
        self,
        report: SimulationReport,
        format: str = "markdown"
    ) -> str:
        """生成仿真报告"""
        if format == "markdown":
            return self._simulation_to_markdown(report)
        elif format == "html":
            return self._simulation_to_html(report)
        elif format == "json":
            return self._to_json(report)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def generate_optimization_report(
        self,
        report: OptimizationReport,
        format: str = "markdown"
    ) -> str:
        """生成优化报告"""
        if format == "markdown":
            return self._optimization_to_markdown(report)
        elif format == "html":
            return self._optimization_to_html(report)
        elif format == "json":
            return self._to_json(report)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def generate_verification_report(
        self,
        report: VerificationReport,
        format: str = "markdown"
    ) -> str:
        """生成验证报告"""
        if format == "markdown":
            return self._verification_to_markdown(report)
        elif format == "html":
            return self._verification_to_html(report)
        elif format == "json":
            return self._to_json(report)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def generate_system_report(
        self,
        report: SystemReport,
        format: str = "markdown"
    ) -> str:
        """生成系统综合报告"""
        if format == "markdown":
            return self._system_to_markdown(report)
        elif format == "html":
            return self._system_to_html(report)
        elif format == "json":
            return self._to_json(report)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def save_report(self, content: str, filename: str) -> Path:
        """保存报告到文件"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def _simulation_to_markdown(self, report: SimulationReport) -> str:
        """仿真报告转Markdown"""
        md = f"""# 仿真报告

**报告ID:** {report.simulation_id}
**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. 仿真概况

| 项目 | 值 |
|------|-----|
| 场景名称 | {report.scenario_name} |
| 开始时间 | {report.start_time.strftime('%Y-%m-%d %H:%M:%S')} |
| 结束时间 | {report.end_time.strftime('%Y-%m-%d %H:%M:%S')} |
| 仿真时长 | {report.duration:.1f} 秒 |
| 时间步数 | {report.time_steps} |
| 状态 | **{report.status}** |

## 2. 关键指标

| 指标 | 数值 |
|------|------|
"""
        for name, value in report.metrics.items():
            md += f"| {name} | {value:.4f} |\n"

        md += f"""
## 3. 时间序列摘要

"""
        for var_name, summary in report.time_series_summary.items():
            md += f"""### {var_name}

- 最大值: {summary.get('max', 'N/A')}
- 最小值: {summary.get('min', 'N/A')}
- 平均值: {summary.get('mean', 'N/A')}
- 标准差: {summary.get('std', 'N/A')}

"""

        if report.violations:
            md += """## 4. 违规记录

| 时间 | 参数 | 违规类型 | 实际值 | 阈值 |
|------|------|----------|--------|------|
"""
            for v in report.violations:
                md += f"| {v.get('time', 'N/A')} | {v.get('parameter', 'N/A')} | {v.get('type', 'N/A')} | {v.get('actual', 'N/A')} | {v.get('threshold', 'N/A')} |\n"

        md += """
## 5. 结论

"""
        for i, conclusion in enumerate(report.conclusions, 1):
            md += f"{i}. {conclusion}\n"

        md += """
---
*本报告由YJDT系统自动生成*
"""
        return md

    def _optimization_to_markdown(self, report: OptimizationReport) -> str:
        """优化报告转Markdown"""
        improvement_pct = report.improvement * 100

        md = f"""# 优化报告

**报告ID:** {report.optimization_id}
**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. 优化概况

| 项目 | 值 |
|------|-----|
| 优化目标 | {report.target} |
| 优化算法 | {report.algorithm} |
| 开始时间 | {report.start_time.strftime('%Y-%m-%d %H:%M:%S')} |
| 结束时间 | {report.end_time.strftime('%Y-%m-%d %H:%M:%S')} |
| 迭代次数 | {report.iterations} |

## 2. 优化结果

| 指标 | 值 |
|------|-----|
| 初始目标函数值 | {report.initial_objective:.6f} |
| 最终目标函数值 | {report.final_objective:.6f} |
| 改进幅度 | **{improvement_pct:.2f}%** |
| 约束满足 | {'是' if report.constraints_satisfied else '否'} |

## 3. 最优参数

| 参数名称 | 最优值 |
|----------|--------|
"""
        for name, value in report.optimal_parameters.items():
            md += f"| {name} | {value:.6f} |\n"

        md += """
## 4. 收敛历史

迭代次数: {iterations}

目标函数变化趋势:
""".format(iterations=report.iterations)

        # 简单文本图表
        if report.convergence_history:
            max_val = max(report.convergence_history)
            min_val = min(report.convergence_history)
            range_val = max_val - min_val if max_val != min_val else 1

            md += "```\n"
            for i, val in enumerate(report.convergence_history[::max(1, len(report.convergence_history)//10)]):
                bar_len = int((val - min_val) / range_val * 40)
                md += f"Iter {i*10:4d}: {'█' * bar_len}{'░' * (40-bar_len)} {val:.4f}\n"
            md += "```\n"

        md += """
## 5. 建议

"""
        for i, rec in enumerate(report.recommendations, 1):
            md += f"{i}. {rec}\n"

        md += """
---
*本报告由YJDT系统自动生成*
"""
        return md

    def _verification_to_markdown(self, report: VerificationReport) -> str:
        """验证报告转Markdown"""
        pass_rate = report.scenarios_passed / report.scenarios_total * 100 if report.scenarios_total > 0 else 0

        md = f"""# 验证报告

**报告ID:** {report.verification_id}
**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. 验证概况

| 项目 | 值 |
|------|-----|
| 设计方案ID | {report.design_id} |
| 验证级别 | {report.verification_level} |
| 开始时间 | {report.start_time.strftime('%Y-%m-%d %H:%M:%S')} |
| 结束时间 | {report.end_time.strftime('%Y-%m-%d %H:%M:%S')} |
| 总体状态 | **{report.overall_status}** |

## 2. 场景验证结果

| 统计项 | 数值 |
|--------|------|
| 场景总数 | {report.scenarios_total} |
| 通过场景 | {report.scenarios_passed} |
| 失败场景 | {report.scenarios_failed} |
| 通过率 | **{pass_rate:.1f}%** |

## 3. 准则验证详情

| 准则ID | 准则名称 | 状态 | 实际值 | 阈值 | 裕度 |
|--------|----------|------|--------|------|------|
"""
        for result in report.criteria_results:
            status_icon = "✅" if result.get('status') == 'passed' else "❌"
            md += f"| {result.get('id', 'N/A')} | {result.get('name', 'N/A')} | {status_icon} | {result.get('actual', 'N/A')} | {result.get('threshold', 'N/A')} | {result.get('margin', 'N/A')}% |\n"

        md += """
## 4. ODD符合性

"""
        if report.odd_compliance:
            md += f"- 总体符合: {'是' if report.odd_compliance.get('overall', False) else '否'}\n"
            if 'zones' in report.odd_compliance:
                md += "\n各参数ODD区域:\n"
                for param, zone in report.odd_compliance.get('zones', {}).items():
                    md += f"  - {param}: {zone}\n"

        md += """
## 5. 建议

"""
        for i, rec in enumerate(report.recommendations, 1):
            md += f"{i}. {rec}\n"

        md += """
---
*本报告由YJDT系统自动生成*
"""
        return md

    def _system_to_markdown(self, report: SystemReport) -> str:
        """系统报告转Markdown"""
        md = f"""# YJDT系统综合报告

**报告ID:** {report.report_id}
**报告类型:** {report.report_type}
**生成时间:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
**系统版本:** {report.system_version}
**项目名称:** {report.project_name}

---

"""
        # 添加各章节
        for section in report.sections:
            md += self._section_to_markdown(section)

        # 添加子报告摘要
        if report.simulation_reports:
            md += "\n## 仿真报告摘要\n\n"
            md += "| ID | 场景 | 状态 | 时长 |\n"
            md += "|-----|------|------|------|\n"
            for sim in report.simulation_reports:
                md += f"| {sim.simulation_id} | {sim.scenario_name} | {sim.status} | {sim.duration:.1f}s |\n"

        if report.optimization_reports:
            md += "\n## 优化报告摘要\n\n"
            md += "| ID | 目标 | 算法 | 改进 |\n"
            md += "|-----|------|------|------|\n"
            for opt in report.optimization_reports:
                md += f"| {opt.optimization_id} | {opt.target} | {opt.algorithm} | {opt.improvement*100:.1f}% |\n"

        if report.verification_reports:
            md += "\n## 验证报告摘要\n\n"
            md += "| ID | 设计 | 级别 | 状态 |\n"
            md += "|-----|------|------|------|\n"
            for ver in report.verification_reports:
                md += f"| {ver.verification_id} | {ver.design_id} | {ver.verification_level} | {ver.overall_status} |\n"

        md += """
---
*本报告由YJDT系统自动生成*
"""
        return md

    def _section_to_markdown(self, section: ReportSection) -> str:
        """章节转Markdown"""
        prefix = "#" * section.level
        md = f"\n{prefix} {section.title}\n\n{section.content}\n"
        for subsection in section.subsections:
            md += self._section_to_markdown(subsection)
        return md

    def _simulation_to_html(self, report: SimulationReport) -> str:
        """仿真报告转HTML"""
        md_content = self._simulation_to_markdown(report)
        return self._markdown_to_html(md_content, "仿真报告")

    def _optimization_to_html(self, report: OptimizationReport) -> str:
        """优化报告转HTML"""
        md_content = self._optimization_to_markdown(report)
        return self._markdown_to_html(md_content, "优化报告")

    def _verification_to_html(self, report: VerificationReport) -> str:
        """验证报告转HTML"""
        md_content = self._verification_to_markdown(report)
        return self._markdown_to_html(md_content, "验证报告")

    def _system_to_html(self, report: SystemReport) -> str:
        """系统报告转HTML"""
        md_content = self._system_to_markdown(report)
        return self._markdown_to_html(md_content, "系统报告")

    def _markdown_to_html(self, md_content: str, title: str) -> str:
        """Markdown转HTML"""
        # 简单转换，实际可使用markdown库
        html_body = md_content.replace("\n", "<br>\n")
        html_body = html_body.replace("# ", "<h1>").replace("\n<br>", "</h1>\n")
        html_body = html_body.replace("## ", "<h2>").replace("\n<br>", "</h2>\n")
        html_body = html_body.replace("**", "<strong>").replace("**", "</strong>")

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>YJDT - {title}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 40px; }}
        h1 {{ color: #00d4ff; }}
        h2 {{ color: #0099cc; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #00d4ff; color: white; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""

    def _to_json(self, report: Any) -> str:
        """报告转JSON"""
        from dataclasses import asdict

        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(asdict(report), indent=2, ensure_ascii=False, default=convert_datetime)


def create_report_generator(output_dir: str = "./reports") -> ReportGenerator:
    """创建报告生成器"""
    return ReportGenerator(output_dir)


# 便捷函数
def generate_quick_report(
    report_type: str,
    data: Dict[str, Any],
    output_dir: str = "./reports"
) -> Path:
    """快速生成报告"""
    generator = ReportGenerator(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if report_type == "simulation":
        report = SimulationReport(
            simulation_id=data.get('id', f"SIM_{timestamp}"),
            scenario_name=data.get('scenario', '未知场景'),
            start_time=data.get('start_time', datetime.now()),
            end_time=data.get('end_time', datetime.now()),
            duration=data.get('duration', 0),
            time_steps=data.get('time_steps', 0),
            status=data.get('status', '完成'),
            metrics=data.get('metrics', {}),
            time_series_summary=data.get('time_series_summary', {}),
            violations=data.get('violations', []),
            conclusions=data.get('conclusions', ['仿真完成'])
        )
        content = generator.generate_simulation_report(report)
        filename = f"simulation_report_{timestamp}.md"

    elif report_type == "optimization":
        report = OptimizationReport(
            optimization_id=data.get('id', f"OPT_{timestamp}"),
            target=data.get('target', '未知'),
            algorithm=data.get('algorithm', '未知'),
            start_time=data.get('start_time', datetime.now()),
            end_time=data.get('end_time', datetime.now()),
            iterations=data.get('iterations', 0),
            initial_objective=data.get('initial_objective', 0),
            final_objective=data.get('final_objective', 0),
            improvement=data.get('improvement', 0),
            optimal_parameters=data.get('optimal_parameters', {}),
            convergence_history=data.get('convergence_history', []),
            constraints_satisfied=data.get('constraints_satisfied', True),
            recommendations=data.get('recommendations', [])
        )
        content = generator.generate_optimization_report(report)
        filename = f"optimization_report_{timestamp}.md"

    elif report_type == "verification":
        report = VerificationReport(
            verification_id=data.get('id', f"VER_{timestamp}"),
            design_id=data.get('design_id', 'default'),
            verification_level=data.get('level', 'standard'),
            start_time=data.get('start_time', datetime.now()),
            end_time=data.get('end_time', datetime.now()),
            scenarios_total=data.get('scenarios_total', 0),
            scenarios_passed=data.get('scenarios_passed', 0),
            scenarios_failed=data.get('scenarios_failed', 0),
            overall_status=data.get('status', '未知'),
            criteria_results=data.get('criteria_results', []),
            odd_compliance=data.get('odd_compliance', {}),
            recommendations=data.get('recommendations', [])
        )
        content = generator.generate_verification_report(report)
        filename = f"verification_report_{timestamp}.md"

    else:
        raise ValueError(f"未知的报告类型: {report_type}")

    return generator.save_report(content, filename)
