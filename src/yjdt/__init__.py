"""
雅江水电梯级分层分布式智能控制系统
Yajiang Hydropower Cascade Distributed Intelligent Control System (YJDT)

本系统实现了完整的水电站仿真与控制功能，包括：
- 水力系统MOC水锤计算
- 水轮机/发电机全要素仿真
- 传感器和执行器仿真
- 分层分布式控制（PID/MPC/QP求解器）
- 多智能体梯级协调（共识协议/ADMM分布式优化）
- 雅江特色场景库（高海拔/地震/冰川融水）
- 全场景生成与识别（100%覆盖，含万年一遇极端场景）
- 闭环仿真框架（本体仿真→数据同化→评价诊断→预测→调度→控制）
- L0-L5智能化等级评价体系
- 全场景在环测试框架
- 概率安全分析（PSA/FTA/ETA）
- 智能故障诊断与预测维护
- 应急响应决策支持
- 实时监控与报警管理
- 数字孪生与预测仿真（实时校准/UKF/RLS）
- 网络安全防护（IDS/RBAC/态势感知/攻击仿真）
- 调度优化求解（日前/日内/实时/AGC）
- 软件在环测试
- 可视化界面
- L4级自主运行中试平台（对抗性场景/HIL测试/具身智能/设计验证风洞）
- 系统集成入口（统一Facade/Builder模式/组件编排）
- 工业数据对接（SCADA/OPC-UA/Modbus/历史数据库）
- 场景数据适配器（运行数据采集/场景匹配/数据驱动场景生成）
- REST API服务（FastAPI/OpenAPI/WebSocket实时推送）
- 数据持久化（SQLite/Repository模式/时间序列存储）
- ODD识别体系（规则引擎/状态机/覆盖率分析/违规检测）
- MBD优化设计（水力/机电/控制/安全/经济全覆盖优化）
- 优化算法框架（梯度/全局/多目标/鲁棒优化算法自动选择）
- 设计-验证-反馈闭环（持续改进机制）
- 灵活性与安全性优化（响应速度/爬坡率/压力裕度/稳定裕度）
- MAS全自主运行（L5级全自主/分层降级/ODD边界守护）

对标核电站安全分析与工业4.0标准，确保极端场景安全高效
实现"设计即验证、建设即演练"范式
"""

__version__ = "2.2.0"
__author__ = "Hydropower Research Team"

# ==============================================================================
# 新增模块 - 面向运行能力的设计评估与验证
# ==============================================================================

# ODD (设计运行域)
from yjdt.odd.operational_design_domain import (
    SystemODD,
    ODDValidator,
    ODDZone,
    DegradationLevel,
    BoundaryLimit,
    TransientBoundary,
    CascadeBoundary,
    StationODD,
    SystemODDState,
    create_yajiang_bigbend_odd,
)

# MBD (模型驱动设计)
from yjdt.mbd.model_based_design import (
    CascadeHydropowerModel,
    ParameterOptimizer,
    SensitivityAnalyzer,
    ReverseDesignOptimizer,
    DesignParameter,
    DesignScheme,
    DesignObjective,
    create_yajiang_mbd_model,
)

# MAS (ODD感知多智能体系统)
from yjdt.mas.odd_aware_mas import (
    ODDAwareMASSystem,
    CentralCoordinatorAgent,
    StationControllerAgent,
    UnitControllerAgent,
    ODDScenarioGenerator,
    AdaptiveObjectiveManager,
    MultiSourceIndicatorAggregator,
    create_yajiang_mas_system,
)

# MAS全自主运行
from yjdt.mas.autonomous_operation import (
    FullAutonomousMAS,
    AutonomyLevel,
    ODDBoundaryGuard,
    DegradationController,
    ZoneController,
    ControlAction,
    AutonomousDecision,
    create_yajiang_autonomous_mas,
)

# ODD识别体系
from yjdt.odd.odd_identification import (
    ODDRuleEngine,
    ODDScanner,
    ODDStateMachine,
    ODDCoverageAnalyzer,
    ODDRule,
    ODDViolation,
    ODDScanResult,
    create_default_odd_rules,
)

# MBD高级优化
from yjdt.mbd.advanced_optimization import (
    MultiObjectiveOptimizer,
    RobustnessOptimizer,
    ODDConstrainedDesigner,
    DesignSpaceExplorer,
    DesignVariable,
    ParetoSolution,
    create_cascade_optimization_problem,
)

# 雅江工程MBD优化设计
from yjdt.mbd.yajiang_optimization_design import (
    HydraulicSystemOptimizer,
    ElectromechanicalOptimizer,
    ControlSystemOptimizer,
    CascadeCoordinationOptimizer,
    SafetyProtectionOptimizer,
    TransientProcessOptimizer,
    OperatingConditionOptimizer,
    EconomicOptimizer,
    YajiangMBDOptimizer,
    create_yajiang_mbd_optimizer,
)

# MBD优化框架
from yjdt.mbd.optimization_framework import (
    OptimizationAlgorithm,
    ProblemType,
    AlgorithmSelector,
    UnifiedOptimizer,
    DesignVerificationLoop,
    FlexibilityOptimizer,
    SafetyOptimizer,
    IntegratedOptimizationFramework,
    FlexibilityMetrics,
    SafetyMetrics,
)

# MBD仿真验证集成
from yjdt.mbd.simulation_verification_integration import (
    MBDSimulationVerificationIntegrator,
    SimulationScenarioLibrary,
    VerificationCriteriaManager,
    DesignParameterMapper,
    VerificationStatus,
    DesignStage,
    VerificationLevel,
    DesignVerificationReport,
    create_yajiang_verification_integrator,
)

# SIL/HIL验证框架
from yjdt.verification.sil_hil_verification import (
    SILVerificationFramework,
    HILVerificationFramework,
    IntegratedVerificationSystem,
    ODDBoundaryVerifier,
    VerificationTestCase,
    VerificationResult,
    VerificationReport,
)

# 级联仿真
from yjdt.simulation.cascade_simulation import (
    CascadeSimulator,
    SingleStationSimulator,
    HydraulicCouplingModel,
    PressureWaveModel,
    CascadeState,
    StationState,
    create_yajiang_cascade_simulator,
)

from yjdt.core.hydraulic import HydraulicSystem, Pipeline, SurgeTank
from yjdt.core.turbine import FrancisTurbine, PeltonTurbine
from yjdt.core.generator import SynchronousGenerator
from yjdt.core.governor import PIDGovernor, MPCGovernor
from yjdt.simulation.engine import SimulationEngine
from yjdt.control.distributed import DistributedController
from yjdt.control.mpc_solver import MPCSolver, QPSolver, DistributedMPCSolver
from yjdt.control.multi_agent import CascadeCoordinator, HydropowerStationAgent, ConsensusProtocol
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
from yjdt.digital_twin.realtime_calibration import RealtimeCalibrator, TwinModelCalibrator
from yjdt.security.intrusion_detection import IntrusionDetectionSystem
from yjdt.security.behavior_analysis import BehaviorAnalyzer
from yjdt.security.access_control import AccessController
from yjdt.security.situational_awareness import SecuritySituationAwareness
from yjdt.security.attack_simulation import AttackSimulator, DataInjectionAttack, ProtocolAttack

# 调度优化
from yjdt.optimization.scheduling_solver import (
    CascadeSchedulingSolver,
    RealTimeDispatcher,
    LinearProgramSolver,
    MixedIntegerSolver,
    ADMMSolver,
    HydropowerUnit,
    Reservoir,
    SchedulingResult,
)

# 系统集成
from yjdt.integration.system_facade import (
    YJDTSystem,
    SystemBuilder,
    ComponentRegistry,
    IntegrationContext,
    SystemMode,
)
from yjdt.integration.data_connector import (
    DataConnector,
    SCADAConnector,
    HistorianConnector,
    OPCUAClient,
    RealtimeDataBridge,
)
from yjdt.integration.scenario_data_adapter import (
    ScenarioDataAdapter,
    OperationalDataCollector,
    ScenarioMatcher,
    DataDrivenScenarioGenerator,
)

# REST API服务
from yjdt.api.server import (
    create_app,
    APIServer,
    get_app,
)
from yjdt.api.websocket import (
    WebSocketManager,
    RealtimeDataStreamer,
)

# 数据持久化
from yjdt.persistence.database import (
    Database,
    SQLiteDatabase,
    DatabaseManager,
    get_database_manager,
)
from yjdt.persistence.repository import (
    SimulationRepository,
    ScenarioRepository,
    TimeSeriesRepository,
    AlarmRepository,
)

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
    # MPC求解器
    "MPCSolver",
    "QPSolver",
    "DistributedMPCSolver",
    # 多智能体协调
    "CascadeCoordinator",
    "HydropowerStationAgent",
    "ConsensusProtocol",
    # 数字孪生校准
    "RealtimeCalibrator",
    "TwinModelCalibrator",
    # 攻击仿真
    "AttackSimulator",
    "DataInjectionAttack",
    "ProtocolAttack",
    # 调度优化
    "CascadeSchedulingSolver",
    "RealTimeDispatcher",
    "LinearProgramSolver",
    "MixedIntegerSolver",
    "ADMMSolver",
    "HydropowerUnit",
    "Reservoir",
    "SchedulingResult",
    # 系统集成
    "YJDTSystem",
    "SystemBuilder",
    "ComponentRegistry",
    "IntegrationContext",
    "SystemMode",
    "DataConnector",
    "SCADAConnector",
    "HistorianConnector",
    "OPCUAClient",
    "RealtimeDataBridge",
    "ScenarioDataAdapter",
    "OperationalDataCollector",
    "ScenarioMatcher",
    "DataDrivenScenarioGenerator",
    # REST API服务
    "create_app",
    "APIServer",
    "get_app",
    "WebSocketManager",
    "RealtimeDataStreamer",
    # 数据持久化
    "Database",
    "SQLiteDatabase",
    "DatabaseManager",
    "get_database_manager",
    "SimulationRepository",
    "ScenarioRepository",
    "TimeSeriesRepository",
    "AlarmRepository",
    # ==============================================================================
    # 新增模块 - 面向运行能力的设计评估与验证
    # ==============================================================================
    # ODD (设计运行域)
    "SystemODD",
    "ODDValidator",
    "ODDZone",
    "DegradationLevel",
    "BoundaryLimit",
    "TransientBoundary",
    "CascadeBoundary",
    "StationODD",
    "SystemODDState",
    "create_yajiang_bigbend_odd",
    # MBD (模型驱动设计)
    "CascadeHydropowerModel",
    "ParameterOptimizer",
    "SensitivityAnalyzer",
    "ReverseDesignOptimizer",
    "DesignParameter",
    "DesignScheme",
    "DesignObjective",
    "create_yajiang_mbd_model",
    # MAS (ODD感知多智能体系统)
    "ODDAwareMASSystem",
    "CentralCoordinatorAgent",
    "StationControllerAgent",
    "UnitControllerAgent",
    "ODDScenarioGenerator",
    "AdaptiveObjectiveManager",
    "MultiSourceIndicatorAggregator",
    "create_yajiang_mas_system",
    # SIL/HIL验证框架
    "SILVerificationFramework",
    "HILVerificationFramework",
    "IntegratedVerificationSystem",
    "ODDBoundaryVerifier",
    "VerificationTestCase",
    "VerificationResult",
    "VerificationReport",
    # 级联仿真
    "CascadeSimulator",
    "SingleStationSimulator",
    "HydraulicCouplingModel",
    "PressureWaveModel",
    "CascadeState",
    "StationState",
    "create_yajiang_cascade_simulator",
    # MAS全自主运行
    "FullAutonomousMAS",
    "AutonomyLevel",
    "ODDBoundaryGuard",
    "DegradationController",
    "ZoneController",
    "ControlAction",
    "AutonomousDecision",
    "create_yajiang_autonomous_mas",
    # ODD识别体系
    "ODDRuleEngine",
    "ODDScanner",
    "ODDStateMachine",
    "ODDCoverageAnalyzer",
    "ODDRule",
    "ODDViolation",
    "ODDScanResult",
    "create_default_odd_rules",
    # MBD高级优化
    "MultiObjectiveOptimizer",
    "RobustnessOptimizer",
    "ODDConstrainedDesigner",
    "DesignSpaceExplorer",
    "DesignVariable",
    "ParetoSolution",
    "create_cascade_optimization_problem",
    # 雅江工程MBD优化设计
    "HydraulicSystemOptimizer",
    "ElectromechanicalOptimizer",
    "ControlSystemOptimizer",
    "CascadeCoordinationOptimizer",
    "SafetyProtectionOptimizer",
    "TransientProcessOptimizer",
    "OperatingConditionOptimizer",
    "EconomicOptimizer",
    "YajiangMBDOptimizer",
    "create_yajiang_mbd_optimizer",
    # MBD优化框架
    "OptimizationAlgorithm",
    "ProblemType",
    "AlgorithmSelector",
    "UnifiedOptimizer",
    "DesignVerificationLoop",
    "FlexibilityOptimizer",
    "SafetyOptimizer",
    "IntegratedOptimizationFramework",
    "FlexibilityMetrics",
    "SafetyMetrics",
    # MBD仿真验证集成
    "MBDSimulationVerificationIntegrator",
    "SimulationScenarioLibrary",
    "VerificationCriteriaManager",
    "DesignParameterMapper",
    "VerificationStatus",
    "DesignStage",
    "VerificationLevel",
    "DesignVerificationReport",
    "create_yajiang_verification_integrator",
]
