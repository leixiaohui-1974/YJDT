# -*- coding: utf-8 -*-
"""
MBD与仿真验证集成模块

实现优化设计与仿真验证的完整闭环:
1. 优化设计 → 仿真验证 → ODD检查 → 反馈调整
2. 设计参数自动映射到仿真模型
3. 仿真结果自动评估与优化反馈
4. 支持批量设计方案比选

作者: Hydropower Research Team
版本: 2.2.0
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime
import numpy as np


class VerificationStatus(Enum):
    """验证状态"""
    PENDING = "pending"           # 待验证
    RUNNING = "running"           # 验证中
    PASSED = "passed"             # 验证通过
    FAILED = "failed"             # 验证失败
    WARNING = "warning"           # 有警告
    CONDITIONAL = "conditional"   # 有条件通过


class DesignStage(Enum):
    """设计阶段"""
    CONCEPTUAL = "conceptual"     # 概念设计
    PRELIMINARY = "preliminary"   # 初步设计
    DETAILED = "detailed"         # 详细设计
    FINAL = "final"               # 最终设计


class VerificationLevel(Enum):
    """验证级别"""
    QUICK = "quick"               # 快速验证
    STANDARD = "standard"         # 标准验证
    COMPREHENSIVE = "comprehensive"  # 全面验证
    CERTIFICATION = "certification"  # 认证级验证


@dataclass
class DesignToSimulationMapping:
    """设计参数到仿真模型的映射"""
    design_param: str            # 设计参数名
    simulation_param: str        # 仿真参数名
    transform: Optional[Callable] = None  # 转换函数
    unit_conversion: float = 1.0  # 单位转换系数
    description: str = ""


@dataclass
class SimulationScenario:
    """仿真场景定义"""
    scenario_id: str
    name: str
    description: str
    scenario_type: str           # normal, extreme, boundary, fault
    duration: float              # 仿真时长(秒)
    initial_conditions: Dict[str, float] = field(default_factory=dict)
    disturbances: List[Dict] = field(default_factory=list)
    acceptance_criteria: Dict[str, Dict] = field(default_factory=dict)
    priority: int = 1            # 优先级 1-5


@dataclass
class SimulationResult:
    """仿真结果"""
    scenario_id: str
    execution_time: float        # 执行时间(秒)
    time_series: Dict[str, np.ndarray]  # 时间序列数据
    metrics: Dict[str, float]    # 评价指标
    violations: List[Dict]       # 违规记录
    max_values: Dict[str, float]  # 最大值
    min_values: Dict[str, float]  # 最小值
    steady_state: Dict[str, float]  # 稳态值


@dataclass
class VerificationCriterion:
    """验证准则"""
    criterion_id: str
    name: str
    parameter: str               # 被评估的参数
    condition: str               # 条件类型: max, min, range, rate, duration
    threshold: float             # 阈值
    tolerance: float = 0.0       # 容差
    severity: str = "critical"   # critical, major, minor
    description: str = ""


@dataclass
class VerificationOutcome:
    """验证结果"""
    criterion_id: str
    status: VerificationStatus
    actual_value: float
    threshold: float
    margin: float               # 裕度百分比
    details: str = ""


@dataclass
class DesignVerificationReport:
    """设计验证报告"""
    design_id: str
    design_stage: DesignStage
    verification_level: VerificationLevel
    timestamp: datetime
    design_parameters: Dict[str, float]
    scenarios_run: int
    scenarios_passed: int
    overall_status: VerificationStatus
    outcomes: List[VerificationOutcome]
    recommendations: List[str]
    odd_compliance: Dict[str, Any]
    performance_summary: Dict[str, float]


class DesignParameterMapper:
    """设计参数映射器 - 将设计参数映射到仿真模型"""

    def __init__(self):
        self.mappings: Dict[str, DesignToSimulationMapping] = {}
        self._setup_default_mappings()

    def _setup_default_mappings(self):
        """设置默认映射"""
        # 水力系统参数映射
        self.add_mapping(DesignToSimulationMapping(
            design_param="tunnel_diameter",
            simulation_param="hydraulic.pipeline.diameter",
            description="隧洞直径"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="tunnel_length",
            simulation_param="hydraulic.pipeline.length",
            description="隧洞长度"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="surge_tank_area",
            simulation_param="hydraulic.surge_tank.area",
            description="调压室面积"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="surge_tank_height",
            simulation_param="hydraulic.surge_tank.height",
            description="调压室高度"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="penstock_diameter",
            simulation_param="hydraulic.penstock.diameter",
            description="压力管道直径"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="penstock_length",
            simulation_param="hydraulic.penstock.length",
            description="压力管道长度"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="penstock_thickness",
            simulation_param="hydraulic.penstock.wall_thickness",
            description="压力管道壁厚"
        ))

        # 水轮机参数映射
        self.add_mapping(DesignToSimulationMapping(
            design_param="turbine_rated_power",
            simulation_param="turbine.rated_power",
            unit_conversion=1e6,  # MW to W
            description="水轮机额定功率"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="turbine_rated_head",
            simulation_param="turbine.rated_head",
            description="水轮机额定水头"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="turbine_rated_flow",
            simulation_param="turbine.rated_flow",
            description="水轮机额定流量"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="turbine_inertia",
            simulation_param="turbine.inertia",
            description="水轮机转动惯量"
        ))

        # 发电机参数映射
        self.add_mapping(DesignToSimulationMapping(
            design_param="generator_capacity",
            simulation_param="generator.rated_power",
            unit_conversion=1e6,  # MVA to VA
            description="发电机容量"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="generator_inertia",
            simulation_param="generator.inertia_constant",
            description="发电机惯性时间常数"
        ))

        # 控制系统参数映射
        self.add_mapping(DesignToSimulationMapping(
            design_param="governor_kp",
            simulation_param="governor.pid.kp",
            description="调速器比例增益"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="governor_ki",
            simulation_param="governor.pid.ki",
            description="调速器积分增益"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="governor_kd",
            simulation_param="governor.pid.kd",
            description="调速器微分增益"
        ))
        self.add_mapping(DesignToSimulationMapping(
            design_param="guide_vane_rate_limit",
            simulation_param="governor.guide_vane.rate_limit",
            description="导叶开度变化速率限制"
        ))

    def add_mapping(self, mapping: DesignToSimulationMapping):
        """添加映射"""
        self.mappings[mapping.design_param] = mapping

    def map_design_to_simulation(self, design_params: Dict[str, float]) -> Dict[str, float]:
        """将设计参数映射到仿真参数"""
        sim_params = {}

        for param_name, value in design_params.items():
            if param_name in self.mappings:
                mapping = self.mappings[param_name]

                # 应用转换函数
                if mapping.transform:
                    value = mapping.transform(value)

                # 应用单位转换
                value = value * mapping.unit_conversion

                sim_params[mapping.simulation_param] = value
            else:
                # 未映射的参数直接传递
                sim_params[param_name] = value

        return sim_params


class SimulationScenarioLibrary:
    """仿真场景库"""

    def __init__(self):
        self.scenarios: Dict[str, SimulationScenario] = {}
        self._setup_standard_scenarios()

    def _setup_standard_scenarios(self):
        """设置标准验证场景"""
        # 稳态运行验证
        self.add_scenario(SimulationScenario(
            scenario_id="SS001",
            name="额定负荷稳态运行",
            description="额定工况下的稳态运行验证",
            scenario_type="normal",
            duration=300.0,
            initial_conditions={
                "power_setpoint": 1.0,
                "frequency": 50.0,
                "guide_vane": 0.8
            },
            acceptance_criteria={
                "frequency_deviation": {"max": 0.2, "unit": "Hz"},
                "power_deviation": {"max": 2.0, "unit": "%"},
                "pressure_oscillation": {"max": 5.0, "unit": "%"}
            },
            priority=1
        ))

        # 负荷阶跃响应
        self.add_scenario(SimulationScenario(
            scenario_id="LS001",
            name="10%负荷阶跃增加",
            description="10%负荷阶跃增加响应测试",
            scenario_type="normal",
            duration=120.0,
            initial_conditions={
                "power_setpoint": 0.8,
                "frequency": 50.0
            },
            disturbances=[{
                "time": 10.0,
                "type": "step",
                "parameter": "power_setpoint",
                "magnitude": 0.1
            }],
            acceptance_criteria={
                "frequency_nadir": {"min": 49.5, "unit": "Hz"},
                "settling_time": {"max": 60.0, "unit": "s"},
                "overshoot": {"max": 5.0, "unit": "%"}
            },
            priority=1
        ))

        # 甩负荷测试
        self.add_scenario(SimulationScenario(
            scenario_id="LR001",
            name="100%甩负荷",
            description="满负荷甩负荷测试（最恶劣工况）",
            scenario_type="extreme",
            duration=180.0,
            initial_conditions={
                "power_setpoint": 1.0,
                "frequency": 50.0,
                "guide_vane": 0.9
            },
            disturbances=[{
                "time": 10.0,
                "type": "step",
                "parameter": "electrical_load",
                "magnitude": -1.0
            }],
            acceptance_criteria={
                "max_pressure_rise": {"max": 40.0, "unit": "%"},
                "max_speed_rise": {"max": 50.0, "unit": "%"},
                "surge_tank_max": {"max": 0.95, "unit": "pu"},
                "surge_tank_min": {"min": 0.05, "unit": "pu"}
            },
            priority=1
        ))

        # 调压室稳定性测试
        self.add_scenario(SimulationScenario(
            scenario_id="ST001",
            name="调压室振荡稳定性",
            description="调压室水位振荡稳定性测试",
            scenario_type="boundary",
            duration=600.0,
            initial_conditions={
                "power_setpoint": 0.8
            },
            disturbances=[
                {"time": 10.0, "type": "step", "parameter": "power_setpoint", "magnitude": 0.1},
                {"time": 60.0, "type": "step", "parameter": "power_setpoint", "magnitude": -0.1},
                {"time": 120.0, "type": "step", "parameter": "power_setpoint", "magnitude": 0.1}
            ],
            acceptance_criteria={
                "damping_ratio": {"min": 0.05, "unit": ""},
                "oscillation_decay": {"condition": "decreasing"}
            },
            priority=2
        ))

        # AGC跟踪测试
        self.add_scenario(SimulationScenario(
            scenario_id="AGC001",
            name="AGC调频响应",
            description="AGC调频信号跟踪测试",
            scenario_type="normal",
            duration=300.0,
            initial_conditions={
                "power_setpoint": 0.7
            },
            disturbances=[{
                "time": 10.0,
                "type": "agc_signal",
                "parameter": "agc_command",
                "profile": "standard_agc"
            }],
            acceptance_criteria={
                "response_delay": {"max": 10.0, "unit": "s"},
                "tracking_error": {"max": 3.0, "unit": "%"},
                "ramp_rate": {"min": 2.0, "unit": "%/min"}
            },
            priority=2
        ))

        # 导叶卡涩测试
        self.add_scenario(SimulationScenario(
            scenario_id="FT001",
            name="导叶卡涩故障",
            description="单台机组导叶卡涩故障响应",
            scenario_type="fault",
            duration=120.0,
            initial_conditions={
                "power_setpoint": 0.8
            },
            disturbances=[{
                "time": 10.0,
                "type": "fault",
                "parameter": "guide_vane_stuck",
                "unit": 1
            }],
            acceptance_criteria={
                "system_stability": {"condition": "stable"},
                "power_reduction": {"max": 20.0, "unit": "%"}
            },
            priority=3
        ))

        # 级联协调测试
        self.add_scenario(SimulationScenario(
            scenario_id="CC001",
            name="五站级联协调",
            description="五站级联协调运行测试",
            scenario_type="normal",
            duration=600.0,
            initial_conditions={
                "total_power_setpoint": 0.8
            },
            disturbances=[{
                "time": 60.0,
                "type": "cascade_reallocation",
                "parameter": "power_distribution",
                "target": [0.7, 0.8, 0.85, 0.8, 0.75]
            }],
            acceptance_criteria={
                "coordination_error": {"max": 5.0, "unit": "%"},
                "pressure_wave_damping": {"min": 0.7, "unit": ""},
                "transition_time": {"max": 120.0, "unit": "s"}
            },
            priority=2
        ))

        # 水锤边界测试
        self.add_scenario(SimulationScenario(
            scenario_id="WH001",
            name="水锤压力边界",
            description="水锤压力边界测试",
            scenario_type="boundary",
            duration=60.0,
            initial_conditions={
                "power_setpoint": 1.0,
                "guide_vane": 0.9
            },
            disturbances=[{
                "time": 5.0,
                "type": "emergency_close",
                "parameter": "guide_vane",
                "rate": "maximum"
            }],
            acceptance_criteria={
                "max_pressure": {"max": 1.4, "unit": "pu"},
                "min_pressure": {"min": 0.6, "unit": "pu"}
            },
            priority=1
        ))

    def add_scenario(self, scenario: SimulationScenario):
        """添加场景"""
        self.scenarios[scenario.scenario_id] = scenario

    def get_scenarios_by_type(self, scenario_type: str) -> List[SimulationScenario]:
        """按类型获取场景"""
        return [s for s in self.scenarios.values() if s.scenario_type == scenario_type]

    def get_scenarios_by_priority(self, max_priority: int) -> List[SimulationScenario]:
        """按优先级获取场景"""
        return [s for s in self.scenarios.values() if s.priority <= max_priority]


class VerificationCriteriaManager:
    """验证准则管理器"""

    def __init__(self):
        self.criteria: Dict[str, VerificationCriterion] = {}
        self._setup_standard_criteria()

    def _setup_standard_criteria(self):
        """设置标准验证准则"""
        # 安全性准则
        self.add_criterion(VerificationCriterion(
            criterion_id="S001",
            name="最大水锤压力",
            parameter="max_pressure_rise",
            condition="max",
            threshold=40.0,
            tolerance=2.0,
            severity="critical",
            description="水锤压力升高不超过40%"
        ))
        self.add_criterion(VerificationCriterion(
            criterion_id="S002",
            name="最大转速上升",
            parameter="max_speed_rise",
            condition="max",
            threshold=50.0,
            tolerance=2.0,
            severity="critical",
            description="甩负荷时转速上升不超过50%"
        ))
        self.add_criterion(VerificationCriterion(
            criterion_id="S003",
            name="调压室最高水位",
            parameter="surge_tank_max_level",
            condition="max",
            threshold=0.95,
            tolerance=0.02,
            severity="critical",
            description="调压室最高水位不超过95%"
        ))
        self.add_criterion(VerificationCriterion(
            criterion_id="S004",
            name="调压室最低水位",
            parameter="surge_tank_min_level",
            condition="min",
            threshold=0.05,
            tolerance=0.02,
            severity="critical",
            description="调压室最低水位不低于5%"
        ))

        # 稳定性准则
        self.add_criterion(VerificationCriterion(
            criterion_id="ST001",
            name="调压室阻尼比",
            parameter="damping_ratio",
            condition="min",
            threshold=0.05,
            tolerance=0.01,
            severity="major",
            description="调压室振荡阻尼比不低于0.05"
        ))
        self.add_criterion(VerificationCriterion(
            criterion_id="ST002",
            name="频率稳定性",
            parameter="frequency_stability_margin",
            condition="min",
            threshold=10.0,
            tolerance=1.0,
            severity="major",
            description="频率稳定裕度不低于10%"
        ))

        # 性能准则
        self.add_criterion(VerificationCriterion(
            criterion_id="P001",
            name="负荷响应时间",
            parameter="settling_time",
            condition="max",
            threshold=60.0,
            tolerance=5.0,
            severity="minor",
            description="负荷响应调节时间不超过60秒"
        ))
        self.add_criterion(VerificationCriterion(
            criterion_id="P002",
            name="AGC响应速率",
            parameter="ramp_rate",
            condition="min",
            threshold=2.0,
            tolerance=0.1,
            severity="minor",
            description="AGC响应速率不低于2%/min"
        ))
        self.add_criterion(VerificationCriterion(
            criterion_id="P003",
            name="频率偏差",
            parameter="frequency_deviation",
            condition="max",
            threshold=0.2,
            tolerance=0.02,
            severity="major",
            description="稳态频率偏差不超过±0.2Hz"
        ))

        # ODD相关准则
        self.add_criterion(VerificationCriterion(
            criterion_id="ODD001",
            name="ODD边界裕度",
            parameter="odd_boundary_margin",
            condition="min",
            threshold=10.0,
            tolerance=2.0,
            severity="major",
            description="运行参数距ODD边界裕度不低于10%"
        ))

    def add_criterion(self, criterion: VerificationCriterion):
        """添加准则"""
        self.criteria[criterion.criterion_id] = criterion

    def evaluate(self, criterion_id: str, actual_value: float) -> VerificationOutcome:
        """评估单个准则"""
        if criterion_id not in self.criteria:
            raise ValueError(f"Unknown criterion: {criterion_id}")

        criterion = self.criteria[criterion_id]
        threshold = criterion.threshold
        tolerance = criterion.tolerance

        # 计算裕度
        if criterion.condition == "max":
            margin = (threshold - actual_value) / threshold * 100
            passed = actual_value <= threshold + tolerance
        elif criterion.condition == "min":
            margin = (actual_value - threshold) / threshold * 100
            passed = actual_value >= threshold - tolerance
        else:
            margin = 0.0
            passed = True

        # 确定状态
        if passed:
            if margin > 20:
                status = VerificationStatus.PASSED
            elif margin > 10:
                status = VerificationStatus.PASSED
            else:
                status = VerificationStatus.WARNING
        else:
            status = VerificationStatus.FAILED

        return VerificationOutcome(
            criterion_id=criterion_id,
            status=status,
            actual_value=actual_value,
            threshold=threshold,
            margin=margin,
            details=f"{criterion.name}: 实际值={actual_value:.3f}, 阈值={threshold:.3f}, 裕度={margin:.1f}%"
        )


class SimulationExecutor:
    """仿真执行器"""

    def __init__(self, simulator=None):
        self.simulator = simulator
        self.param_mapper = DesignParameterMapper()

    def execute_scenario(
        self,
        scenario: SimulationScenario,
        design_params: Dict[str, float]
    ) -> SimulationResult:
        """执行仿真场景"""
        # 映射设计参数到仿真参数
        sim_params = self.param_mapper.map_design_to_simulation(design_params)

        # 执行仿真（这里是模拟实现）
        start_time = datetime.now()

        # 模拟仿真结果
        time_steps = int(scenario.duration / 0.1)
        t = np.linspace(0, scenario.duration, time_steps)

        # 生成模拟数据
        time_series = self._simulate_response(t, scenario, design_params)

        # 计算指标
        metrics = self._calculate_metrics(time_series, scenario)

        # 检查违规
        violations = self._check_violations(metrics, scenario.acceptance_criteria)

        execution_time = (datetime.now() - start_time).total_seconds()

        return SimulationResult(
            scenario_id=scenario.scenario_id,
            execution_time=execution_time,
            time_series=time_series,
            metrics=metrics,
            violations=violations,
            max_values={k: float(np.max(v)) for k, v in time_series.items()},
            min_values={k: float(np.min(v)) for k, v in time_series.items()},
            steady_state={k: float(v[-100:].mean()) for k, v in time_series.items()}
        )

    def _simulate_response(
        self,
        t: np.ndarray,
        scenario: SimulationScenario,
        design_params: Dict[str, float]
    ) -> Dict[str, np.ndarray]:
        """模拟系统响应"""
        n = len(t)

        # 基础参数
        damping = design_params.get('damping_ratio', 0.1)
        natural_freq = design_params.get('natural_frequency', 0.1)

        # 生成典型响应
        frequency = 50.0 * np.ones(n)
        power = np.ones(n) * scenario.initial_conditions.get('power_setpoint', 0.8)
        pressure = np.ones(n)
        guide_vane = np.ones(n) * scenario.initial_conditions.get('guide_vane', 0.8)
        surge_level = 0.5 * np.ones(n)

        # 应用扰动
        for dist in scenario.disturbances:
            dist_time = dist['time']
            dist_type = dist['type']
            magnitude = dist.get('magnitude', 0)

            idx_start = int(dist_time / (t[1] - t[0]))

            if dist_type == 'step':
                if dist['parameter'] == 'power_setpoint':
                    power[idx_start:] += magnitude
                    # 频率响应
                    for i in range(idx_start, n):
                        dt = t[i] - t[idx_start]
                        freq_response = magnitude * 2 * np.exp(-damping * natural_freq * dt) * \
                                       np.sin(natural_freq * np.sqrt(1 - damping**2) * dt)
                        frequency[i] = 50.0 - freq_response
                elif dist['parameter'] == 'electrical_load':
                    # 甩负荷响应
                    for i in range(idx_start, n):
                        dt = t[i] - t[idx_start]
                        # 转速上升
                        speed_rise = abs(magnitude) * 30 * (1 - np.exp(-dt / 5.0))
                        frequency[i] = 50.0 + speed_rise * 50.0 / 100.0
                        # 压力升高
                        pressure_rise = abs(magnitude) * 20 * np.exp(-dt / 2.0) * np.sin(2 * np.pi * dt / 4)
                        pressure[i] = 1.0 + pressure_rise / 100.0
                        # 调压室水位
                        surge_rise = abs(magnitude) * 0.3 * (1 - np.exp(-dt / 30.0)) * np.cos(2 * np.pi * dt / 60)
                        surge_level[i] = 0.5 + surge_rise

        return {
            'time': t,
            'frequency': frequency,
            'power': power,
            'pressure': pressure,
            'guide_vane': guide_vane,
            'surge_level': surge_level
        }

    def _calculate_metrics(
        self,
        time_series: Dict[str, np.ndarray],
        scenario: SimulationScenario
    ) -> Dict[str, float]:
        """计算评价指标"""
        metrics = {}

        freq = time_series.get('frequency', np.array([50.0]))
        pressure = time_series.get('pressure', np.array([1.0]))
        surge = time_series.get('surge_level', np.array([0.5]))

        # 频率指标
        metrics['frequency_deviation'] = float(np.max(np.abs(freq - 50.0)))
        metrics['frequency_nadir'] = float(np.min(freq))
        metrics['frequency_peak'] = float(np.max(freq))

        # 压力指标
        metrics['max_pressure_rise'] = float((np.max(pressure) - 1.0) * 100)
        metrics['min_pressure'] = float(np.min(pressure))
        metrics['max_pressure'] = float(np.max(pressure))

        # 转速指标
        metrics['max_speed_rise'] = float((np.max(freq) - 50.0) / 50.0 * 100)

        # 调压室指标
        metrics['surge_tank_max'] = float(np.max(surge))
        metrics['surge_tank_min'] = float(np.min(surge))

        # 稳定性指标
        metrics['settling_time'] = self._estimate_settling_time(time_series)
        metrics['damping_ratio'] = self._estimate_damping(time_series)

        return metrics

    def _estimate_settling_time(self, time_series: Dict[str, np.ndarray]) -> float:
        """估算调节时间"""
        freq = time_series.get('frequency', np.array([50.0]))
        t = time_series.get('time', np.arange(len(freq)))

        steady_state = freq[-100:].mean() if len(freq) > 100 else freq[-1]
        threshold = 0.02 * 50.0  # 2%带宽

        for i in range(len(freq) - 1, -1, -1):
            if abs(freq[i] - steady_state) > threshold:
                return float(t[min(i + 1, len(t) - 1)])

        return 0.0

    def _estimate_damping(self, time_series: Dict[str, np.ndarray]) -> float:
        """估算阻尼比"""
        surge = time_series.get('surge_level', np.array([0.5]))

        # 找峰值
        peaks = []
        for i in range(1, len(surge) - 1):
            if surge[i] > surge[i-1] and surge[i] > surge[i+1]:
                peaks.append(surge[i] - 0.5)

        if len(peaks) >= 2:
            # 对数递减法估算阻尼比
            ratio = abs(peaks[0] / peaks[1]) if peaks[1] != 0 else 1.0
            if ratio > 1:
                delta = np.log(ratio)
                damping = delta / np.sqrt(4 * np.pi**2 + delta**2)
                return float(damping)

        return 0.1  # 默认阻尼比

    def _check_violations(
        self,
        metrics: Dict[str, float],
        acceptance_criteria: Dict[str, Dict]
    ) -> List[Dict]:
        """检查违规"""
        violations = []

        for param, criteria in acceptance_criteria.items():
            if param in metrics:
                value = metrics[param]

                if 'max' in criteria and value > criteria['max']:
                    violations.append({
                        'parameter': param,
                        'condition': 'max',
                        'threshold': criteria['max'],
                        'actual': value,
                        'unit': criteria.get('unit', '')
                    })

                if 'min' in criteria and value < criteria['min']:
                    violations.append({
                        'parameter': param,
                        'condition': 'min',
                        'threshold': criteria['min'],
                        'actual': value,
                        'unit': criteria.get('unit', '')
                    })

        return violations


class MBDSimulationVerificationIntegrator:
    """MBD与仿真验证集成器"""

    def __init__(self):
        self.param_mapper = DesignParameterMapper()
        self.scenario_library = SimulationScenarioLibrary()
        self.criteria_manager = VerificationCriteriaManager()
        self.executor = SimulationExecutor()
        self.verification_history: List[DesignVerificationReport] = []

    def verify_design(
        self,
        design_id: str,
        design_params: Dict[str, float],
        verification_level: VerificationLevel = VerificationLevel.STANDARD,
        design_stage: DesignStage = DesignStage.PRELIMINARY
    ) -> DesignVerificationReport:
        """验证设计方案"""
        # 根据验证级别选择场景
        if verification_level == VerificationLevel.QUICK:
            scenarios = self.scenario_library.get_scenarios_by_priority(1)
        elif verification_level == VerificationLevel.STANDARD:
            scenarios = self.scenario_library.get_scenarios_by_priority(2)
        elif verification_level == VerificationLevel.COMPREHENSIVE:
            scenarios = self.scenario_library.get_scenarios_by_priority(3)
        else:  # CERTIFICATION
            scenarios = list(self.scenario_library.scenarios.values())

        # 执行所有场景
        all_outcomes: List[VerificationOutcome] = []
        scenarios_passed = 0
        performance_summary = {}

        for scenario in scenarios:
            result = self.executor.execute_scenario(scenario, design_params)

            # 评估准则
            scenario_passed = True
            for criterion_id, criterion in self.criteria_manager.criteria.items():
                if criterion.parameter in result.metrics:
                    outcome = self.criteria_manager.evaluate(
                        criterion_id,
                        result.metrics[criterion.parameter]
                    )
                    all_outcomes.append(outcome)

                    if outcome.status == VerificationStatus.FAILED:
                        scenario_passed = False

            if scenario_passed:
                scenarios_passed += 1

            # 汇总性能
            for key, value in result.metrics.items():
                if key not in performance_summary:
                    performance_summary[key] = []
                performance_summary[key].append(value)

        # 计算平均性能
        for key in performance_summary:
            performance_summary[key] = float(np.mean(performance_summary[key]))

        # 确定总体状态
        failed_count = sum(1 for o in all_outcomes if o.status == VerificationStatus.FAILED)
        warning_count = sum(1 for o in all_outcomes if o.status == VerificationStatus.WARNING)

        if failed_count > 0:
            overall_status = VerificationStatus.FAILED
        elif warning_count > 0:
            overall_status = VerificationStatus.WARNING
        else:
            overall_status = VerificationStatus.PASSED

        # 生成建议
        recommendations = self._generate_recommendations(all_outcomes, design_params)

        # ODD符合性
        odd_compliance = self._check_odd_compliance(performance_summary)

        report = DesignVerificationReport(
            design_id=design_id,
            design_stage=design_stage,
            verification_level=verification_level,
            timestamp=datetime.now(),
            design_parameters=design_params,
            scenarios_run=len(scenarios),
            scenarios_passed=scenarios_passed,
            overall_status=overall_status,
            outcomes=all_outcomes,
            recommendations=recommendations,
            odd_compliance=odd_compliance,
            performance_summary=performance_summary
        )

        self.verification_history.append(report)
        return report

    def _generate_recommendations(
        self,
        outcomes: List[VerificationOutcome],
        design_params: Dict[str, float]
    ) -> List[str]:
        """生成设计改进建议"""
        recommendations = []

        for outcome in outcomes:
            if outcome.status == VerificationStatus.FAILED:
                criterion = self.criteria_manager.criteria.get(outcome.criterion_id)
                if criterion:
                    if "压力" in criterion.name:
                        recommendations.append(
                            f"建议: 增大调压室面积或优化导叶关闭规律以降低水锤压力"
                        )
                    elif "转速" in criterion.name:
                        recommendations.append(
                            f"建议: 增大机组转动惯量或优化调速器参数以限制转速上升"
                        )
                    elif "调压室" in criterion.name:
                        recommendations.append(
                            f"建议: 调整调压室尺寸以满足水位约束"
                        )
                    elif "频率" in criterion.name:
                        recommendations.append(
                            f"建议: 优化调速器PID参数以改善频率响应"
                        )
                    elif "阻尼" in criterion.name:
                        recommendations.append(
                            f"建议: 增大调压室阻抗孔面积以提高阻尼比"
                        )

            elif outcome.status == VerificationStatus.WARNING:
                if outcome.margin < 15:
                    recommendations.append(
                        f"注意: {outcome.criterion_id} 裕度较小({outcome.margin:.1f}%)，"
                        f"建议进行敏感性分析"
                    )

        return list(set(recommendations))  # 去重

    def _check_odd_compliance(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """检查ODD符合性"""
        odd_compliance = {
            "overall": True,
            "zones": {},
            "boundary_margins": {}
        }

        # 检查各项指标与ODD边界的关系
        odd_boundaries = {
            "max_pressure_rise": {"optimal": 20, "normal": 30, "restricted": 40},
            "max_speed_rise": {"optimal": 30, "normal": 40, "restricted": 50},
            "frequency_deviation": {"optimal": 0.1, "normal": 0.2, "restricted": 0.5}
        }

        for param, boundaries in odd_boundaries.items():
            if param in metrics:
                value = metrics[param]

                if value <= boundaries["optimal"]:
                    zone = "OPTIMAL"
                    margin = (boundaries["optimal"] - value) / boundaries["optimal"] * 100
                elif value <= boundaries["normal"]:
                    zone = "NORMAL"
                    margin = (boundaries["normal"] - value) / boundaries["normal"] * 100
                elif value <= boundaries["restricted"]:
                    zone = "RESTRICTED"
                    margin = (boundaries["restricted"] - value) / boundaries["restricted"] * 100
                    odd_compliance["overall"] = False
                else:
                    zone = "FORBIDDEN"
                    margin = 0
                    odd_compliance["overall"] = False

                odd_compliance["zones"][param] = zone
                odd_compliance["boundary_margins"][param] = margin

        return odd_compliance

    def compare_designs(
        self,
        designs: List[Dict[str, Any]],
        verification_level: VerificationLevel = VerificationLevel.STANDARD
    ) -> Dict[str, Any]:
        """比较多个设计方案"""
        comparison = {
            "designs": [],
            "ranking": [],
            "best_design": None,
            "comparison_matrix": {}
        }

        scores = []

        for design in designs:
            design_id = design.get('id', f"design_{len(comparison['designs'])}")
            design_params = design.get('parameters', {})

            # 验证设计
            report = self.verify_design(
                design_id=design_id,
                design_params=design_params,
                verification_level=verification_level
            )

            # 计算综合评分
            score = self._calculate_design_score(report)

            comparison["designs"].append({
                "id": design_id,
                "report": report,
                "score": score
            })

            scores.append((design_id, score))

        # 排名
        scores.sort(key=lambda x: x[1], reverse=True)
        comparison["ranking"] = [s[0] for s in scores]
        comparison["best_design"] = scores[0][0] if scores else None

        # 比较矩阵
        for d in comparison["designs"]:
            comparison["comparison_matrix"][d["id"]] = {
                "overall_status": d["report"].overall_status.value,
                "scenarios_passed": f"{d['report'].scenarios_passed}/{d['report'].scenarios_run}",
                "score": d["score"]
            }

        return comparison

    def _calculate_design_score(self, report: DesignVerificationReport) -> float:
        """计算设计方案综合评分"""
        score = 100.0

        # 根据验证结果扣分
        for outcome in report.outcomes:
            if outcome.status == VerificationStatus.FAILED:
                criterion = self.criteria_manager.criteria.get(outcome.criterion_id)
                if criterion:
                    if criterion.severity == "critical":
                        score -= 20
                    elif criterion.severity == "major":
                        score -= 10
                    else:
                        score -= 5
            elif outcome.status == VerificationStatus.WARNING:
                score -= 2

        # 根据裕度加分
        avg_margin = np.mean([o.margin for o in report.outcomes if o.margin > 0])
        if avg_margin > 20:
            score += 10
        elif avg_margin > 10:
            score += 5

        # 确保分数在合理范围内
        return max(0.0, min(100.0, score))

    def generate_feedback_for_optimization(
        self,
        report: DesignVerificationReport
    ) -> Dict[str, Any]:
        """生成用于优化的反馈信息"""
        feedback = {
            "parameter_adjustments": {},
            "constraint_violations": [],
            "objective_weights": {},
            "sensitivity_hints": []
        }

        for outcome in report.outcomes:
            criterion = self.criteria_manager.criteria.get(outcome.criterion_id)
            if not criterion:
                continue

            if outcome.status == VerificationStatus.FAILED:
                # 生成参数调整建议
                if "压力" in criterion.name:
                    feedback["parameter_adjustments"]["surge_tank_area"] = {
                        "direction": "increase",
                        "suggested_change": 10,  # 百分比
                        "reason": "降低水锤压力"
                    }
                    feedback["parameter_adjustments"]["closure_time"] = {
                        "direction": "increase",
                        "suggested_change": 20,
                        "reason": "减缓导叶关闭速度"
                    }

                elif "转速" in criterion.name:
                    feedback["parameter_adjustments"]["turbine_inertia"] = {
                        "direction": "increase",
                        "suggested_change": 15,
                        "reason": "限制转速上升"
                    }

                elif "阻尼" in criterion.name:
                    feedback["parameter_adjustments"]["orifice_area"] = {
                        "direction": "increase",
                        "suggested_change": 10,
                        "reason": "提高调压室阻尼"
                    }

                # 记录约束违反
                feedback["constraint_violations"].append({
                    "criterion": criterion.name,
                    "actual": outcome.actual_value,
                    "threshold": outcome.threshold,
                    "severity": criterion.severity
                })

            # 根据裕度调整目标权重
            if outcome.margin < 10:
                feedback["objective_weights"][criterion.parameter] = 1.5  # 增加权重
                feedback["sensitivity_hints"].append(
                    f"{criterion.parameter}裕度较小，建议进行敏感性分析"
                )
            elif outcome.margin > 30:
                feedback["objective_weights"][criterion.parameter] = 0.8  # 降低权重

        return feedback


def create_yajiang_verification_integrator() -> MBDSimulationVerificationIntegrator:
    """创建雅江工程验证集成器"""
    integrator = MBDSimulationVerificationIntegrator()

    # 添加雅江工程特定场景
    integrator.scenario_library.add_scenario(SimulationScenario(
        scenario_id="YJ001",
        name="雅江大拐弯引水隧洞充水",
        description="76km引水隧洞充水过程仿真",
        scenario_type="normal",
        duration=7200.0,  # 2小时
        initial_conditions={
            "tunnel_empty": True,
            "filling_rate": 100.0  # m³/s
        },
        acceptance_criteria={
            "max_pressure": {"max": 1.2, "unit": "pu"},
            "filling_time": {"max": 7200, "unit": "s"},
            "air_pocket_formation": {"condition": "none"}
        },
        priority=2
    ))

    integrator.scenario_library.add_scenario(SimulationScenario(
        scenario_id="YJ002",
        name="五站级联甩负荷",
        description="五站同时甩负荷极端场景",
        scenario_type="extreme",
        duration=300.0,
        initial_conditions={
            "all_stations_full_load": True
        },
        disturbances=[{
            "time": 10.0,
            "type": "cascade_trip",
            "parameter": "all_stations",
            "sequence": "simultaneous"
        }],
        acceptance_criteria={
            "max_pressure_rise": {"max": 45.0, "unit": "%"},
            "cascade_stability": {"condition": "stable"},
            "no_cavitation": {"condition": True}
        },
        priority=1
    ))

    integrator.scenario_library.add_scenario(SimulationScenario(
        scenario_id="YJ003",
        name="冰川融水洪峰",
        description="冰川融水洪峰期间运行",
        scenario_type="boundary",
        duration=3600.0,
        initial_conditions={
            "inflow_multiplier": 1.5
        },
        acceptance_criteria={
            "spillway_activation": {"max": 0.8, "unit": "pu"},
            "reservoir_safety": {"condition": True}
        },
        priority=2
    ))

    # 添加雅江工程特定验证准则
    integrator.criteria_manager.add_criterion(VerificationCriterion(
        criterion_id="YJ001",
        name="76km隧洞水锤",
        parameter="tunnel_pressure_rise",
        condition="max",
        threshold=35.0,
        tolerance=2.0,
        severity="critical",
        description="76km引水隧洞水锤压力升高限制"
    ))

    integrator.criteria_manager.add_criterion(VerificationCriterion(
        criterion_id="YJ002",
        name="级联压力波传递",
        parameter="cascade_pressure_wave_attenuation",
        condition="min",
        threshold=0.6,
        tolerance=0.05,
        severity="major",
        description="级联压力波衰减系数"
    ))

    return integrator


# 导出
__all__ = [
    "VerificationStatus",
    "DesignStage",
    "VerificationLevel",
    "DesignToSimulationMapping",
    "SimulationScenario",
    "SimulationResult",
    "VerificationCriterion",
    "VerificationOutcome",
    "DesignVerificationReport",
    "DesignParameterMapper",
    "SimulationScenarioLibrary",
    "VerificationCriteriaManager",
    "SimulationExecutor",
    "MBDSimulationVerificationIntegrator",
    "create_yajiang_verification_integrator",
]
