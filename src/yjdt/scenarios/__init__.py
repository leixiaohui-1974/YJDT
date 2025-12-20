"""
场景生成与识别模块 - 100%全场景覆盖
Scenario Generation and Recognition Module - 100% Coverage

包含：
- 基础场景生成器
- 极端场景生成器（万年一遇级别）
- 场景识别器（AI）
- 覆盖度分析器
- 安全裕度评估器
"""

from yjdt.scenarios.generator import (
    ScenarioGenerator,
    Scenario,
    ScenarioType,
    ScenarioLibrary,
)

from yjdt.scenarios.recognizer import (
    ScenarioRecognizer,
    RecognitionResult,
    AnomalyDetector,
)

from yjdt.scenarios.extreme_scenarios import (
    ExtremeScenarioGenerator,
    ExtremeScenario,
    ProbabilityLevel,
    ScenarioCategory,
    SafetyLevel,
    SafetyMeasure,
    AcceptanceCriteria,
)

from yjdt.scenarios.coverage_analyzer import (
    ScenarioCoverageAnalyzer,
    SafetyMarginEvaluator,
    CoverageDimension,
    CoverageGap,
)

__all__ = [
    # 基础场景
    "ScenarioGenerator",
    "Scenario",
    "ScenarioType",
    "ScenarioLibrary",

    # 场景识别
    "ScenarioRecognizer",
    "RecognitionResult",
    "AnomalyDetector",

    # 极端场景（万年一遇）
    "ExtremeScenarioGenerator",
    "ExtremeScenario",
    "ProbabilityLevel",
    "ScenarioCategory",
    "SafetyLevel",
    "SafetyMeasure",
    "AcceptanceCriteria",

    # 覆盖度分析
    "ScenarioCoverageAnalyzer",
    "SafetyMarginEvaluator",
    "CoverageDimension",
    "CoverageGap",
]
