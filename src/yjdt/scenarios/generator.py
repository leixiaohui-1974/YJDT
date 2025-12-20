"""
全场景生成模块
Scenario Generation Module

实现水电站运行的各类场景自动生成：
- 正常运行场景
- 过渡过程场景
- 故障场景
- 极端工况场景
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import json
import hashlib


class ScenarioType(Enum):
    """场景类型"""
    # 正常运行场景
    NORMAL_OPERATION = "normal_operation"
    STEADY_STATE = "steady_state"
    LOAD_FOLLOWING = "load_following"

    # 启停场景
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"

    # 过渡过程场景
    LOAD_INCREASE = "load_increase"
    LOAD_DECREASE = "load_decrease"
    LOAD_REJECTION = "load_rejection"
    LOAD_ACCEPTANCE = "load_acceptance"

    # 调频场景
    PRIMARY_FREQUENCY = "primary_frequency"
    SECONDARY_FREQUENCY = "secondary_frequency"
    AGC_RESPONSE = "agc_response"

    # 故障场景
    SENSOR_FAULT = "sensor_fault"
    ACTUATOR_FAULT = "actuator_fault"
    CONTROLLER_FAULT = "controller_fault"
    COMMUNICATION_FAULT = "communication_fault"
    HYDRAULIC_FAULT = "hydraulic_fault"
    ELECTRICAL_FAULT = "electrical_fault"

    # 电网故障
    GRID_FAULT = "grid_fault"
    VOLTAGE_DIP = "voltage_dip"
    FREQUENCY_DEVIATION = "frequency_deviation"
    ISLAND_OPERATION = "island_operation"

    # 极端工况
    MAXIMUM_HEAD = "maximum_head"
    MINIMUM_HEAD = "minimum_head"
    FLOOD_CONDITION = "flood_condition"
    DROUGHT_CONDITION = "drought_condition"

    # 复合场景
    CASCADING_FAILURE = "cascading_failure"
    MULTI_FAULT = "multi_fault"


class SeverityLevel(Enum):
    """严重程度等级"""
    INFO = 1        # 信息
    LOW = 2         # 低
    MEDIUM = 3      # 中
    HIGH = 4        # 高
    CRITICAL = 5    # 严重


@dataclass
class ScenarioEvent:
    """场景事件"""
    time: float                    # 发生时间 (s)
    event_type: str               # 事件类型
    target: str                   # 作用对象
    parameters: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0         # 持续时间 (s)
    description: str = ""         # 描述


@dataclass
class ScenarioCondition:
    """场景初始/边界条件"""
    # 水力条件
    upstream_level: float = 2170.0     # 上游水位 (m)
    downstream_level: float = 1690.0   # 下游水位 (m)
    inflow: float = 1000.0             # 来水流量 (m³/s)

    # 机组条件
    initial_power: float = 500.0       # 初始功率 (MW)
    initial_opening: float = 0.5       # 初始开度
    initial_speed: float = 166.7       # 初始转速 (r/min)

    # 电网条件
    grid_voltage: float = 1.0          # 电网电压 (pu)
    grid_frequency: float = 50.0       # 电网频率 (Hz)
    grid_load: float = 10000.0         # 系统负荷 (MW)

    # 环境条件
    temperature: float = 20.0          # 温度 (°C)
    humidity: float = 60.0             # 湿度 (%)


@dataclass
class Scenario:
    """场景定义"""
    scenario_id: str                   # 场景ID
    name: str                          # 场景名称
    scenario_type: ScenarioType       # 场景类型
    severity: SeverityLevel           # 严重程度
    description: str                   # 场景描述

    # 时间参数
    duration: float = 300.0            # 场景持续时间 (s)
    sample_time: float = 0.01          # 采样时间 (s)

    # 条件
    initial_condition: ScenarioCondition = field(default_factory=ScenarioCondition)
    boundary_conditions: Dict[str, Callable[[float], float]] = field(default_factory=dict)

    # 事件序列
    events: List[ScenarioEvent] = field(default_factory=list)

    # 评估标准
    success_criteria: Dict[str, float] = field(default_factory=dict)
    failure_criteria: Dict[str, float] = field(default_factory=dict)

    # 元数据
    tags: List[str] = field(default_factory=list)
    created_by: str = ""
    version: str = "1.0"

    def get_hash(self) -> str:
        """获取场景哈希值"""
        content = f"{self.name}{self.scenario_type.value}{self.duration}"
        for event in self.events:
            content += f"{event.time}{event.event_type}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'scenario_id': self.scenario_id,
            'name': self.name,
            'type': self.scenario_type.value,
            'severity': self.severity.value,
            'description': self.description,
            'duration': self.duration,
            'events': [
                {
                    'time': e.time,
                    'type': e.event_type,
                    'target': e.target,
                    'params': e.parameters,
                }
                for e in self.events
            ],
        }


class ScenarioGenerator:
    """
    场景生成器

    自动生成各类测试场景
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 默认参数
        self.default_duration = 300.0
        self.default_sample_time = 0.01

        # 场景模板
        self.templates: Dict[ScenarioType, Callable] = {
            ScenarioType.LOAD_REJECTION: self._generate_load_rejection,
            ScenarioType.LOAD_INCREASE: self._generate_load_change,
            ScenarioType.LOAD_DECREASE: self._generate_load_change,
            ScenarioType.STARTUP: self._generate_startup,
            ScenarioType.SHUTDOWN: self._generate_shutdown,
            ScenarioType.SENSOR_FAULT: self._generate_sensor_fault,
            ScenarioType.ACTUATOR_FAULT: self._generate_actuator_fault,
            ScenarioType.GRID_FAULT: self._generate_grid_fault,
            ScenarioType.PRIMARY_FREQUENCY: self._generate_frequency_response,
            ScenarioType.FLOOD_CONDITION: self._generate_extreme_hydraulic,
        }

        # 生成的场景列表
        self.generated_scenarios: List[Scenario] = []

    def generate(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """
        生成指定类型的场景

        Args:
            scenario_type: 场景类型
            **kwargs: 额外参数

        Returns:
            生成的场景
        """
        generator = self.templates.get(scenario_type)
        if generator is None:
            raise ValueError(f"不支持的场景类型: {scenario_type}")

        scenario = generator(scenario_type, **kwargs)
        self.generated_scenarios.append(scenario)

        return scenario

    def generate_batch(
        self,
        scenario_types: List[ScenarioType],
        variations: int = 1
    ) -> List[Scenario]:
        """批量生成场景"""
        scenarios = []

        for stype in scenario_types:
            for v in range(variations):
                # 添加一些随机变化
                variation_params = {
                    'variation_index': v,
                    'random_seed': np.random.randint(10000),
                }
                scenario = self.generate(stype, **variation_params)
                scenarios.append(scenario)

        return scenarios

    def _generate_load_rejection(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """生成甩负荷场景"""
        rejection_ratio = kwargs.get('rejection_ratio', 1.0)  # 甩负荷比例
        rejection_time = kwargs.get('rejection_time', 10.0)   # 甩负荷时刻

        scenario = Scenario(
            scenario_id=f"LR_{rejection_ratio:.0%}_{kwargs.get('variation_index', 0)}",
            name=f"甩负荷{rejection_ratio:.0%}",
            scenario_type=scenario_type,
            severity=SeverityLevel.HIGH if rejection_ratio >= 0.5 else SeverityLevel.MEDIUM,
            description=f"在t={rejection_time}s时发生{rejection_ratio:.0%}甩负荷",
            duration=self.default_duration,
        )

        # 设置初始条件
        scenario.initial_condition.initial_power = 800.0  # MW

        # 添加甩负荷事件
        scenario.events.append(ScenarioEvent(
            time=rejection_time,
            event_type="load_rejection",
            target="generator",
            parameters={
                'rejection_ratio': rejection_ratio,
                'breaker_trip': True,
            },
            description=f"机组甩{rejection_ratio:.0%}负荷"
        ))

        # 设置评估标准
        scenario.success_criteria = {
            'max_speed_rise': 1.3,      # 最大转速上升不超过30%
            'max_pressure_rise': 1.5,   # 最大压力上升不超过50%
            'settling_time': 120.0,     # 稳定时间不超过120s
        }

        scenario.failure_criteria = {
            'runaway_speed': 1.8,       # 飞逸转速
            'negative_pressure': True,  # 出现负压
        }

        scenario.tags = ['transient', 'load_rejection', 'water_hammer']

        return scenario

    def _generate_load_change(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """生成负荷变化场景"""
        change_rate = kwargs.get('change_rate', 0.2)  # 变化比例
        change_time = kwargs.get('change_time', 10.0)  # 变化开始时刻
        ramp_duration = kwargs.get('ramp_duration', 30.0)  # 变化持续时间

        is_increase = scenario_type == ScenarioType.LOAD_INCREASE
        direction = "增" if is_increase else "减"

        scenario = Scenario(
            scenario_id=f"LC_{direction}_{change_rate:.0%}",
            name=f"负荷{direction}加{change_rate:.0%}",
            scenario_type=scenario_type,
            severity=SeverityLevel.LOW,
            description=f"在t={change_time}s开始，负荷在{ramp_duration}s内{direction}加{change_rate:.0%}",
            duration=self.default_duration,
        )

        scenario.initial_condition.initial_power = 500.0

        # 负荷变化事件
        scenario.events.append(ScenarioEvent(
            time=change_time,
            event_type="load_ramp",
            target="load_controller",
            parameters={
                'change_rate': change_rate if is_increase else -change_rate,
                'duration': ramp_duration,
            },
            duration=ramp_duration,
        ))

        scenario.success_criteria = {
            'max_frequency_deviation': 0.5,  # 频率偏差不超过0.5Hz
            'settling_time': 60.0,
        }

        scenario.tags = ['normal_operation', 'load_change']

        return scenario

    def _generate_startup(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """生成启动场景"""
        startup_mode = kwargs.get('mode', 'normal')  # normal, fast, black_start

        scenario = Scenario(
            scenario_id=f"SU_{startup_mode}",
            name=f"机组启动-{startup_mode}",
            scenario_type=scenario_type,
            severity=SeverityLevel.MEDIUM,
            description=f"机组{startup_mode}模式启动过程",
            duration=600.0,  # 启动过程较长
        )

        # 初始状态：停机
        scenario.initial_condition.initial_power = 0.0
        scenario.initial_condition.initial_opening = 0.0
        scenario.initial_condition.initial_speed = 0.0

        # 启动事件序列
        events = [
            ScenarioEvent(
                time=0.0,
                event_type="open_inlet_valve",
                target="inlet_valve",
                description="开启进水阀"
            ),
            ScenarioEvent(
                time=30.0,
                event_type="speed_no_load",
                target="governor",
                parameters={'target_speed': 166.7},
                description="空载转速"
            ),
            ScenarioEvent(
                time=120.0,
                event_type="excitation_build_up",
                target="exciter",
                description="励磁建压"
            ),
            ScenarioEvent(
                time=180.0,
                event_type="synchronization",
                target="breaker",
                description="同期并网"
            ),
            ScenarioEvent(
                time=210.0,
                event_type="load_up",
                target="governor",
                parameters={'target_power': 500.0, 'ramp_rate': 50.0},
                description="带负荷"
            ),
        ]
        scenario.events = events

        scenario.success_criteria = {
            'startup_time': 300.0,      # 启动时间
            'sync_success': True,        # 同期成功
        }

        scenario.tags = ['startup', 'sequence']

        return scenario

    def _generate_shutdown(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """生成停机场景"""
        shutdown_mode = kwargs.get('mode', 'normal')

        scenario = Scenario(
            scenario_id=f"SD_{shutdown_mode}",
            name=f"机组停机-{shutdown_mode}",
            scenario_type=scenario_type,
            severity=SeverityLevel.MEDIUM if shutdown_mode == 'normal' else SeverityLevel.HIGH,
            description=f"机组{shutdown_mode}模式停机过程",
            duration=300.0,
        )

        scenario.initial_condition.initial_power = 500.0

        events = [
            ScenarioEvent(
                time=0.0,
                event_type="load_down",
                target="governor",
                parameters={'target_power': 0.0, 'ramp_rate': 30.0},
                description="降负荷"
            ),
            ScenarioEvent(
                time=60.0,
                event_type="breaker_open",
                target="breaker",
                description="开断路器"
            ),
            ScenarioEvent(
                time=90.0,
                event_type="speed_down",
                target="governor",
                parameters={'target_speed': 0.0},
                description="降转速"
            ),
            ScenarioEvent(
                time=180.0,
                event_type="close_inlet_valve",
                target="inlet_valve",
                description="关闭进水阀"
            ),
        ]
        scenario.events = events

        scenario.tags = ['shutdown', 'sequence']

        return scenario

    def _generate_sensor_fault(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """生成传感器故障场景"""
        fault_type = kwargs.get('fault_type', 'drift')  # drift, stuck, noise, bias
        sensor_type = kwargs.get('sensor', 'speed_sensor')
        fault_time = kwargs.get('fault_time', 50.0)
        fault_magnitude = kwargs.get('magnitude', 0.1)

        scenario = Scenario(
            scenario_id=f"SF_{sensor_type}_{fault_type}",
            name=f"传感器故障-{sensor_type}-{fault_type}",
            scenario_type=scenario_type,
            severity=SeverityLevel.MEDIUM,
            description=f"{sensor_type}在t={fault_time}s发生{fault_type}故障",
            duration=self.default_duration,
        )

        scenario.events.append(ScenarioEvent(
            time=fault_time,
            event_type="sensor_fault_injection",
            target=sensor_type,
            parameters={
                'fault_type': fault_type,
                'magnitude': fault_magnitude,
            },
            description=f"{sensor_type}发生{fault_type}故障"
        ))

        scenario.success_criteria = {
            'fault_detection_time': 10.0,   # 故障检测时间
            'fault_isolation': True,         # 故障隔离
            'system_stable': True,           # 系统保持稳定
        }

        scenario.tags = ['fault', 'sensor', fault_type]

        return scenario

    def _generate_actuator_fault(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """生成执行器故障场景"""
        fault_type = kwargs.get('fault_type', 'stuck')
        actuator_type = kwargs.get('actuator', 'guide_vane')
        fault_time = kwargs.get('fault_time', 50.0)
        stuck_position = kwargs.get('stuck_position', 0.5)

        scenario = Scenario(
            scenario_id=f"AF_{actuator_type}_{fault_type}",
            name=f"执行器故障-{actuator_type}-{fault_type}",
            scenario_type=scenario_type,
            severity=SeverityLevel.HIGH,
            description=f"{actuator_type}在t={fault_time}s发生{fault_type}故障",
            duration=self.default_duration,
        )

        scenario.events.append(ScenarioEvent(
            time=fault_time,
            event_type="actuator_fault_injection",
            target=actuator_type,
            parameters={
                'fault_type': fault_type,
                'stuck_position': stuck_position,
            },
            description=f"{actuator_type}卡在{stuck_position:.0%}位置"
        ))

        scenario.success_criteria = {
            'emergency_response': True,
            'safe_shutdown': True,
        }

        scenario.tags = ['fault', 'actuator', fault_type]

        return scenario

    def _generate_grid_fault(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """生成电网故障场景"""
        fault_subtype = kwargs.get('subtype', 'three_phase')
        fault_time = kwargs.get('fault_time', 50.0)
        fault_duration = kwargs.get('fault_duration', 0.15)  # 秒
        fault_location = kwargs.get('location', 0.5)

        scenario = Scenario(
            scenario_id=f"GF_{fault_subtype}",
            name=f"电网故障-{fault_subtype}",
            scenario_type=scenario_type,
            severity=SeverityLevel.HIGH,
            description=f"t={fault_time}s发生{fault_subtype}短路故障，持续{fault_duration}s",
            duration=self.default_duration,
        )

        scenario.events.append(ScenarioEvent(
            time=fault_time,
            event_type="grid_fault",
            target="grid",
            parameters={
                'fault_type': fault_subtype,
                'duration': fault_duration,
                'location': fault_location,
            },
            duration=fault_duration,
            description=f"{fault_subtype}短路故障"
        ))

        # 故障清除
        scenario.events.append(ScenarioEvent(
            time=fault_time + fault_duration,
            event_type="fault_clear",
            target="grid",
            description="故障清除"
        ))

        scenario.success_criteria = {
            'transient_stability': True,  # 暂态稳定
            'max_swing': 120.0,           # 最大摇摆角度
        }

        scenario.tags = ['fault', 'grid', 'transient']

        return scenario

    def _generate_frequency_response(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """生成调频响应场景"""
        freq_deviation = kwargs.get('deviation', -0.5)  # Hz
        step_time = kwargs.get('step_time', 10.0)

        scenario = Scenario(
            scenario_id=f"FR_{freq_deviation:+.2f}Hz",
            name=f"一次调频响应",
            scenario_type=scenario_type,
            severity=SeverityLevel.LOW,
            description=f"电网频率阶跃变化{freq_deviation:+.2f}Hz的调频响应",
            duration=120.0,
        )

        scenario.events.append(ScenarioEvent(
            time=step_time,
            event_type="frequency_step",
            target="grid",
            parameters={
                'delta_f': freq_deviation,
            },
            description=f"频率阶跃{freq_deviation:+.2f}Hz"
        ))

        scenario.success_criteria = {
            'response_time': 3.0,         # 响应时间 < 3s
            'settling_time': 30.0,        # 稳定时间 < 30s
            'steady_state_error': 0.05,   # 稳态误差
        }

        scenario.tags = ['frequency_regulation', 'primary']

        return scenario

    def _generate_extreme_hydraulic(
        self,
        scenario_type: ScenarioType,
        **kwargs
    ) -> Scenario:
        """生成极端水力工况场景"""
        condition = kwargs.get('condition', 'flood')

        if condition == 'flood':
            scenario = Scenario(
                scenario_id="EH_flood",
                name="洪水工况",
                scenario_type=ScenarioType.FLOOD_CONDITION,
                severity=SeverityLevel.HIGH,
                description="洪水期间的极端运行工况",
                duration=3600.0,  # 1小时
            )
            scenario.initial_condition.upstream_level = 2200.0
            scenario.initial_condition.inflow = 3000.0
        else:
            scenario = Scenario(
                scenario_id="EH_drought",
                name="枯水工况",
                scenario_type=ScenarioType.DROUGHT_CONDITION,
                severity=SeverityLevel.MEDIUM,
                description="枯水期间的低水头运行",
                duration=3600.0,
            )
            scenario.initial_condition.upstream_level = 2140.0
            scenario.initial_condition.inflow = 200.0

        scenario.tags = ['extreme', 'hydraulic', condition]

        return scenario


class ScenarioLibrary:
    """
    场景库

    管理和存储场景集合
    """

    def __init__(self):
        self.scenarios: Dict[str, Scenario] = {}
        self.categories: Dict[str, List[str]] = {}

    def add_scenario(self, scenario: Scenario):
        """添加场景"""
        self.scenarios[scenario.scenario_id] = scenario

        # 更新分类
        category = scenario.scenario_type.value
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(scenario.scenario_id)

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """获取场景"""
        return self.scenarios.get(scenario_id)

    def get_by_type(self, scenario_type: ScenarioType) -> List[Scenario]:
        """按类型获取场景"""
        category = scenario_type.value
        scenario_ids = self.categories.get(category, [])
        return [self.scenarios[sid] for sid in scenario_ids if sid in self.scenarios]

    def get_by_severity(self, min_severity: SeverityLevel) -> List[Scenario]:
        """按严重程度筛选"""
        return [
            s for s in self.scenarios.values()
            if s.severity.value >= min_severity.value
        ]

    def get_by_tags(self, tags: List[str]) -> List[Scenario]:
        """按标签筛选"""
        return [
            s for s in self.scenarios.values()
            if any(tag in s.tags for tag in tags)
        ]

    def generate_test_suite(
        self,
        coverage: str = "basic"
    ) -> List[Scenario]:
        """
        生成测试套件

        Args:
            coverage: 覆盖范围 ("basic", "standard", "comprehensive")

        Returns:
            测试场景列表
        """
        generator = ScenarioGenerator()
        suite = []

        if coverage == "basic":
            # 基本测试：关键场景
            types = [
                ScenarioType.LOAD_REJECTION,
                ScenarioType.STARTUP,
                ScenarioType.SHUTDOWN,
                ScenarioType.PRIMARY_FREQUENCY,
            ]
        elif coverage == "standard":
            # 标准测试：更多场景
            types = [
                ScenarioType.LOAD_REJECTION,
                ScenarioType.LOAD_INCREASE,
                ScenarioType.LOAD_DECREASE,
                ScenarioType.STARTUP,
                ScenarioType.SHUTDOWN,
                ScenarioType.PRIMARY_FREQUENCY,
                ScenarioType.SENSOR_FAULT,
                ScenarioType.ACTUATOR_FAULT,
            ]
        else:
            # 全面测试
            types = list(ScenarioType)

        for stype in types:
            try:
                scenario = generator.generate(stype)
                suite.append(scenario)
                self.add_scenario(scenario)
            except ValueError:
                continue  # 跳过不支持的场景类型

        return suite

    def export_to_json(self, filepath: str):
        """导出到JSON"""
        data = {
            'scenarios': [s.to_dict() for s in self.scenarios.values()],
            'categories': self.categories,
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'total_scenarios': len(self.scenarios),
            'categories': {k: len(v) for k, v in self.categories.items()},
            'severity_distribution': {
                s.name: sum(1 for sc in self.scenarios.values() if sc.severity == s)
                for s in SeverityLevel
            },
        }
