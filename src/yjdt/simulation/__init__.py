"""仿真引擎和软件在环测试模块"""

from yjdt.simulation.engine import (
    SimulationEngine,
    SimulationConfig,
    SimulationResult,
    HydropowerUnitSimulator,
    CascadeSimulator,
)

from yjdt.simulation.sil_testing import (
    SILTestFramework,
    TestCase,
    TestSuite,
    TestResult,
    TestReport,
    EvaluationCriteria,
)

__all__ = [
    "SimulationEngine",
    "SimulationConfig",
    "SimulationResult",
    "HydropowerUnitSimulator",
    "CascadeSimulator",
    "SILTestFramework",
    "TestCase",
    "TestSuite",
    "TestResult",
    "TestReport",
    "EvaluationCriteria",
]
