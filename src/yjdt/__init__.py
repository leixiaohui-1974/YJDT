"""
雅江水电梯级分层分布式智能控制系统
Yajiang Hydropower Cascade Distributed Intelligent Control System (YJDT)

本系统实现了完整的水电站仿真与控制功能，包括：
- 水力系统MOC水锤计算
- 水轮机/发电机全要素仿真
- 传感器和执行器仿真
- 分层分布式控制（PID/MPC）
- 雅江特色场景库（高海拔/地震/冰川融水）
- 全场景生成与识别（100%覆盖，含万年一遇极端场景）
- 闭环仿真框架（本体仿真→数据同化→评价诊断→预测→调度→控制）
- L0-L5智能化等级评价体系
- 全场景在环测试框架
- 概率安全分析（PSA/FTA/ETA）
- 智能故障诊断与预测维护
- 应急响应决策支持
- 实时监控与报警管理
- 数字孪生与预测仿真
- 网络安全防护（IDS/RBAC/态势感知）
- 软件在环测试
- 可视化界面
- L4级自主运行中试平台（对抗性场景/HIL测试/具身智能/设计验证风洞）

对标核电站安全分析与工业4.0标准，确保极端场景安全高效
实现"设计即验证、建设即演练"范式
"""

__version__ = "1.5.0"
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
from yjdt.scenarios.yajiang_scenarios import YajiangScenarioLibrary, YajiangScenario
from yjdt.safety.psa_analysis import PSAAnalyzer, FaultTree, FaultTreeAnalyzer, EventTree
from yjdt.safety.intelligent_diagnosis import FaultDiagnoser, PredictiveMaintenance, HealthAssessment
from yjdt.safety.emergency_response import EmergencyResponseCoordinator, EmergencyPlanLibrary
from yjdt.monitoring.realtime_monitor import RealtimeMonitor
from yjdt.monitoring.alarm_manager import AlarmManager
from yjdt.monitoring.trend_analyzer import TrendAnalyzer
from yjdt.monitoring.data_recorder import DataRecorder
from yjdt.digital_twin.twin_engine import DigitalTwinEngine
from yjdt.digital_twin.state_estimator import StateEstimator, KalmanFilter
from yjdt.digital_twin.virtual_sensor import VirtualSensor, SensorFusion
from yjdt.digital_twin.predictive_simulation import PredictiveSimulator
from yjdt.security.intrusion_detection import IntrusionDetectionSystem
from yjdt.security.behavior_analysis import BehaviorAnalyzer
from yjdt.security.access_control import AccessController
from yjdt.security.situational_awareness import SecuritySituationAwareness

# 闭环仿真框架
from yjdt.closedloop.physical_simulation import PhysicalSimulator, MultiPhysicsModel
from yjdt.closedloop.data_assimilation import DataAssimilator, EnsembleKalmanFilter
from yjdt.closedloop.evaluation_diagnosis import StateEvaluator, FaultDiagnosisEngine
from yjdt.closedloop.prediction_engine import PredictionEngine
from yjdt.closedloop.optimal_scheduling import OptimalScheduler, AGCController
from yjdt.closedloop.control_executor import ControlExecutor, SafetyMonitor
from yjdt.closedloop.closed_loop_coordinator import ClosedLoopCoordinator, InLoopTester

# 智能化评价
from yjdt.evaluation.intelligence_level import IntelligenceLevelEvaluator, IntelligenceLevel
from yjdt.evaluation.capability_assessment import CapabilityAssessment
from yjdt.evaluation.scenario_coverage import ScenarioCoverageEvaluator
from yjdt.evaluation.performance_benchmark import PerformanceBenchmark

# 测试框架
from yjdt.testing.scenario_test import ScenarioTestRunner, ScenarioTestCase
from yjdt.testing.closed_loop_test import ClosedLoopTestHarness, TestScenarioInjector
from yjdt.testing.automated_test import AutomatedTestFramework
from yjdt.testing.test_report import TestReportGenerator

# AI智能诊断
from yjdt.ai.deep_diagnosis import (
    EnsembleDiagnosisEngine,
    IsolationForest,
    LSTMPredictor,
    AutoEncoderDetector,
)

# 基础设施
from yjdt.infrastructure.data_bus import DataBus, Signal, Event, EventType
from yjdt.infrastructure.config_manager import ConfigManager, SystemConfig

# 高级水力仿真
from yjdt.core.advanced_hydraulic import (
    NonlinearPipeline,
    BranchPipelineNetwork,
    EquipmentDegradation,
)

# L4级自主运行中试平台
from yjdt.pilot_platform.adversarial_generator import (
    AdversarialScenarioGenerator,
    CornerCaseSearcher,
    FailureModeSynthesizer,
    ScenarioDiffusionModel,
)
from yjdt.pilot_platform.hil_framework import (
    HILTestBench,
    ControllerInterface,
    RealTimeSimulator,
    PowerLevelInterface,
    HILTestCase,
)
from yjdt.pilot_platform.embodied_intelligence import (
    EmbodiedAgent,
    RobotTrainer,
    VisualPerceptionModule,
    AutonomousNavigator,
    EmergencyEscapeAgent,
)
from yjdt.pilot_platform.design_verification import (
    DesignVerificationWindTunnel,
    MultiSchemeComparator,
    SurgeTankOptimizer,
    WaterHammerAnalyzer,
)

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
    "YajiangScenarioLibrary",
    "YajiangScenario",
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
    # 实时监控
    "RealtimeMonitor",
    "AlarmManager",
    "TrendAnalyzer",
    "DataRecorder",
    # 数字孪生
    "DigitalTwinEngine",
    "StateEstimator",
    "KalmanFilter",
    "VirtualSensor",
    "SensorFusion",
    "PredictiveSimulator",
    # 网络安全
    "IntrusionDetectionSystem",
    "BehaviorAnalyzer",
    "AccessController",
    "SecuritySituationAwareness",
    # 闭环仿真框架
    "PhysicalSimulator",
    "MultiPhysicsModel",
    "DataAssimilator",
    "EnsembleKalmanFilter",
    "StateEvaluator",
    "FaultDiagnosisEngine",
    "PredictionEngine",
    "OptimalScheduler",
    "AGCController",
    "ControlExecutor",
    "SafetyMonitor",
    "ClosedLoopCoordinator",
    "InLoopTester",
    # 智能化评价
    "IntelligenceLevelEvaluator",
    "IntelligenceLevel",
    "CapabilityAssessment",
    "ScenarioCoverageEvaluator",
    "PerformanceBenchmark",
    # 测试框架
    "ScenarioTestRunner",
    "ScenarioTestCase",
    "ClosedLoopTestHarness",
    "TestScenarioInjector",
    "AutomatedTestFramework",
    "TestReportGenerator",
    # AI智能诊断
    "EnsembleDiagnosisEngine",
    "IsolationForest",
    "LSTMPredictor",
    "AutoEncoderDetector",
    # 基础设施
    "DataBus",
    "Signal",
    "Event",
    "EventType",
    "ConfigManager",
    "SystemConfig",
    # 高级水力仿真
    "NonlinearPipeline",
    "BranchPipelineNetwork",
    "EquipmentDegradation",
    # L4级自主运行中试平台
    "AdversarialScenarioGenerator",
    "CornerCaseSearcher",
    "FailureModeSynthesizer",
    "ScenarioDiffusionModel",
    "HILTestBench",
    "ControllerInterface",
    "RealTimeSimulator",
    "PowerLevelInterface",
    "HILTestCase",
    "EmbodiedAgent",
    "RobotTrainer",
    "VisualPerceptionModule",
    "AutonomousNavigator",
    "EmergencyEscapeAgent",
    "DesignVerificationWindTunnel",
    "MultiSchemeComparator",
    "SurgeTankOptimizer",
    "WaterHammerAnalyzer",
]
