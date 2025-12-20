# -*- coding: utf-8 -*-
"""
全场景在环测试模块 - Full-scenario In-loop Testing Module

功能：
- 闭环在环测试（HIL/SIL）
- 场景注入测试
- 自动化测试用例
- 测试报告生成

测试类型：
- SIL: 软件在环测试
- HIL: 硬件在环测试
- MIL: 模型在环测试
"""

from yjdt.testing.scenario_test import (
    ScenarioTestRunner,
    ScenarioTestCase,
    TestResult,
    TestSuite,
)

from yjdt.testing.closed_loop_test import (
    ClosedLoopTestHarness,
    HarnessConfiguration,
    TestScenarioInjector,
    ResponseValidator,
)

from yjdt.testing.automated_test import (
    AutomatedTestFramework,
    TestScheduler,
    RegressionTest,
    ContinuousIntegration,
)

from yjdt.testing.test_report import (
    TestReportGenerator,
    CoverageReport,
    PerformanceReport,
    ComplianceReport,
)

__all__ = [
    # 场景测试
    "ScenarioTestRunner",
    "ScenarioTestCase",
    "TestResult",
    "TestSuite",

    # 闭环测试
    "ClosedLoopTestHarness",
    "HarnessConfiguration",
    "TestScenarioInjector",
    "ResponseValidator",

    # 自动化测试
    "AutomatedTestFramework",
    "TestScheduler",
    "RegressionTest",
    "ContinuousIntegration",

    # 测试报告
    "TestReportGenerator",
    "CoverageReport",
    "PerformanceReport",
    "ComplianceReport",
]
