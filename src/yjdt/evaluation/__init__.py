# -*- coding: utf-8 -*-
"""
智能化评价模块 - L0-L5智能化等级评价体系
Intelligence Evaluation Module - L0-L5 Intelligence Level Assessment

类似自动驾驶分级标准，定义水电站智能化六个等级：
L0: 人工控制 - 完全人工操作
L1: 辅助控制 - 单一功能辅助
L2: 部分自动 - 多功能协同辅助
L3: 条件自动 - 特定场景自动控制
L4: 高度自动 - 大部分场景自动控制
L5: 完全自动 - 全场景无人值守
"""

from yjdt.evaluation.intelligence_level import (
    IntelligenceLevel,
    IntelligenceLevelEvaluator,
    LevelRequirement,
    EvaluationResult,
    DimensionScore,
)

from yjdt.evaluation.capability_assessment import (
    CapabilityAssessment,
    CapabilityDimension,
    CapabilityIndicator,
    MaturityLevel,
)

from yjdt.evaluation.scenario_coverage import (
    ScenarioCoverageEvaluator,
    CoverageResult,
    ScenarioCategory,
)

from yjdt.evaluation.performance_benchmark import (
    PerformanceBenchmark,
    BenchmarkResult,
    BenchmarkMetric,
)

__all__ = [
    # 智能化等级
    "IntelligenceLevel",
    "IntelligenceLevelEvaluator",
    "LevelRequirement",
    "EvaluationResult",
    "DimensionScore",

    # 能力评估
    "CapabilityAssessment",
    "CapabilityDimension",
    "CapabilityIndicator",
    "MaturityLevel",

    # 场景覆盖
    "ScenarioCoverageEvaluator",
    "CoverageResult",
    "ScenarioCategory",

    # 性能基准
    "PerformanceBenchmark",
    "BenchmarkResult",
    "BenchmarkMetric",
]
