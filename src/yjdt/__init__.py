"""
雅江水电梯级分层分布式智能控制系统
Yajiang Hydropower Cascade Distributed Intelligent Control System (YJDT)

本系统实现了完整的水电站仿真与控制功能，包括：
- 水力系统MOC水锤计算
- 水轮机/发电机全要素仿真
- 传感器和执行器仿真
- 分层分布式控制（PID/MPC）
- 全场景生成与识别（100%覆盖，含万年一遇极端场景）
- 概率安全分析（PSA/FTA/ETA）
- 智能故障诊断与预测维护
- 应急响应决策支持
- 软件在环测试
- 可视化界面

对标核电站安全分析方法，确保极端场景安全高效
"""

__version__ = "1.1.0"
__author__ = "Hydropower Research Team"

from yjdt.core.hydraulic import HydraulicSystem, Pipeline, SurgeTank
from yjdt.core.turbine import FrancisTurbine, PeltonTurbine
from yjdt.core.generator import SynchronousGenerator
from yjdt.core.governor import PIDGovernor, MPCGovernor
from yjdt.simulation.engine import SimulationEngine
from yjdt.control.distributed import DistributedController
from yjdt.scenarios.generator import ScenarioGenerator
from yjdt.scenarios.recognizer import ScenarioRecognizer
from yjdt.scenarios.extreme_scenarios import ExtremeScenarioGenerator
from yjdt.scenarios.coverage_analyzer import ScenarioCoverageAnalyzer, SafetyMarginEvaluator
from yjdt.safety.psa_analysis import PSAAnalyzer, FaultTree, FaultTreeAnalyzer, EventTree
from yjdt.safety.intelligent_diagnosis import FaultDiagnoser, PredictiveMaintenance, HealthAssessment
from yjdt.safety.emergency_response import EmergencyResponseCoordinator, EmergencyPlanLibrary

__all__ = [
    # 核心仿真模型
    "HydraulicSystem",
    "Pipeline",
    "SurgeTank",
    "FrancisTurbine",
    "PeltonTurbine",
    "SynchronousGenerator",
    "PIDGovernor",
    "MPCGovernor",
    # 仿真与控制
    "SimulationEngine",
    "DistributedController",
    # 场景系统
    "ScenarioGenerator",
    "ScenarioRecognizer",
    "ExtremeScenarioGenerator",
    "ScenarioCoverageAnalyzer",
    "SafetyMarginEvaluator",
    # 安全分析
    "PSAAnalyzer",
    "FaultTree",
    "FaultTreeAnalyzer",
    "EventTree",
    "FaultDiagnoser",
    "PredictiveMaintenance",
    "HealthAssessment",
    "EmergencyResponseCoordinator",
    "EmergencyPlanLibrary",
]
