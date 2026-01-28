# -*- coding: utf-8 -*-
"""
YJDT报告生成模块

支持多种报告格式：
- Markdown报告
- HTML报告
- PDF报告（需要额外依赖）
- JSON数据导出
"""

from .report_generator import (
    ReportGenerator,
    SimulationReport,
    OptimizationReport,
    VerificationReport,
    SystemReport,
    create_report_generator,
)

__all__ = [
    "ReportGenerator",
    "SimulationReport",
    "OptimizationReport",
    "VerificationReport",
    "SystemReport",
    "create_report_generator",
]
