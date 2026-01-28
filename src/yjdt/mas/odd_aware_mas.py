# -*- coding: utf-8 -*-
"""
ODD感知的多智能体系统 - ODD-Aware Multi-Agent System (MAS)

基于YX工程（雅鲁藏布江大拐弯截弯取直引水梯级发电工程）的增强MAS实现

核心功能：
- 在ODD边界内运行的协同控制
- 基于ODD的场景生成与扫描
- 多源指标驱动的目标函数自动更新
- 安全降级策略
- 与既有SCADA/保护体系融合

工程红线：
1. 不突破ODD边界（ODD是硬约束）
2. 不绕过既有SCADA与保护体系
3. 可旁路、可退出，不形成单点风险

参考：YX工程面向运行能力的设计评估与运行逻辑验证关键技术研究
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable, Set
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import threading
import queue
import time
import logging
import copy

# 导入ODD模块
import sys
sys.path.append('..')
try:
    from ..odd.operational_design_domain import (
        SystemODD, ODDZone, DegradationLevel,
        SystemODDState, BoundaryLimit
    )
except ImportError:
    # 如果直接运行，使用相对路径
    pass

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """智能体类型"""
    CENTRAL_COORDINATOR = "central_coordinator"     # 中心协调智能体
    STATION_CONTROLLER = "station_controller"       # 电站控制智能体
    UNIT_CONTROLLER = "unit_controller"             # 机组控制智能体
    SAFETY_SUPERVISOR = "safety_supervisor"         # 安全监督智能体
    DISPATCH_OPTIMIZER = "dispatch_optimizer"       # 调度优化智能体


class OperationMode(Enum):
    """运行模式"""
    AUTONOMOUS = "autonomous"           # 自主模式
    SUPERVISED = "supervised"           # 监督模式
    MANUAL = "manual"                   # 人工模式
    DEGRADED = "degraded"               # 降级模式
    EMERGENCY = "emergency"             # 应急模式


class ScenarioType(Enum):
    """场景类型"""
    NORMAL_OPERATION = "normal_operation"           # 正常运行
    LOAD_TRACKING = "load_tracking"                 # 负荷跟踪
    TRANSIENT = "transient"                         # 暂态过程
    FAULT = "fault"                                 # 故障场景
    CASCADE_EVENT = "cascade_event"                 # 级联事件
    EXTREME = "extreme"                             # 极端场景


@dataclass
class ObjectiveFunction:
    """目标函数"""
    name: str
    description: str

    # 目标权重
    weights: Dict[str, float] = field(default_factory=lambda: {
        "safety": 0.40,           # 安全性权重
        "stability": 0.25,        # 稳定性权重
        "economy": 0.20,          # 经济性权重
        "environment": 0.10,      # 环境效益权重
        "flexibility": 0.05,      # 灵活性权重
    })

    # 约束条件
    constraints: List[Dict[str, Any]] = field(default_factory=list)

    # 目标值
    targets: Dict[str, float] = field(default_factory=dict)

    # 自适应参数
    adaptive_enabled: bool = True
    adaptation_rate: float = 0.1

    def calculate(self, metrics: Dict[str, float]) -> float:
        """计算目标函数值"""
        score = 0.0
        for key, weight in self.weights.items():
            if key in metrics:
                score += weight * metrics[key]
        return score

    def update_weights(self, performance_feedback: Dict[str, float]):
        """根据运行反馈自适应更新权重"""
        if not self.adaptive_enabled:
            return

        # 基于反馈调整权重
        for key in self.weights:
            if key in performance_feedback:
                # 性能差的维度增加权重
                delta = (1.0 - performance_feedback[key]) * self.adaptation_rate
                self.weights[key] = min(0.5, max(0.05, self.weights[key] + delta))

        # 归一化
        total = sum(self.weights.values())
        if total > 0:
            for key in self.weights:
                self.weights[key] /= total


@dataclass
class ODDScenario:
    """ODD边界内的场景"""
    scenario_id: str
    scenario_type: ScenarioType
    name: str
    description: str

    # ODD约束
    odd_zone: ODDZone
    boundary_constraints: Dict[str, Tuple[float, float]]

    # 场景参数
    initial_conditions: Dict[str, float]
    events: List[Dict[str, Any]]
    duration: float

    # 多源指标
    indicators: Dict[str, float] = field(default_factory=dict)

    # 元数据
    probability: float = 0.0
    severity: int = 1
    tags: List[str] = field(default_factory=list)


@dataclass
class AgentDecision:
    """智能体决策"""
    agent_id: str
    timestamp: datetime
    decision_type: str

    # 决策内容
    actions: Dict[str, Any]
    targets: Dict[str, float]

    # ODD状态
    odd_zone: ODDZone
    odd_compliant: bool

    # 协调信息
    coordination_required: bool = False
    coordination_peers: List[str] = field(default_factory=list)

    # 置信度
    confidence: float = 1.0


class ODDScenarioGenerator:
    """
    ODD边界内的场景生成器

    在ODD约束下生成有效的运行场景
    """

    def __init__(self, odd: 'SystemODD'):
        self.odd = odd
        self.generated_scenarios: List[ODDScenario] = []

    def generate_normal_scenarios(self, count: int = 10) -> List[ODDScenario]:
        """生成正常运行场景"""
        scenarios = []

        for i in range(count):
            # 在正常ODD范围内随机采样
            pressure_boundary = self.odd.system_boundaries.get("system_pressure")
            flow_boundary = self.odd.system_boundaries.get("system_flow")

            if pressure_boundary and flow_boundary:
                pressure = np.random.uniform(
                    pressure_boundary.normal_min,
                    pressure_boundary.normal_max
                )
                flow = np.random.uniform(
                    flow_boundary.normal_min,
                    flow_boundary.normal_max
                )

                scenario = ODDScenario(
                    scenario_id=f"NORMAL_{i:03d}",
                    scenario_type=ScenarioType.NORMAL_OPERATION,
                    name=f"正常运行场景{i+1}",
                    description="正常运行工况下的稳态场景",
                    odd_zone=ODDZone.NORMAL,
                    boundary_constraints={
                        "pressure": (pressure_boundary.normal_min, pressure_boundary.normal_max),
                        "flow": (flow_boundary.normal_min, flow_boundary.normal_max),
                    },
                    initial_conditions={
                        "system_pressure": pressure,
                        "system_flow": flow,
                        "frequency": 50.0,
                    },
                    events=[],
                    duration=300.0,
                    probability=0.8,
                    severity=1,
                    tags=["normal", "steady_state"],
                )
                scenarios.append(scenario)

        self.generated_scenarios.extend(scenarios)
        return scenarios

    def generate_transient_scenarios(self, count: int = 10) -> List[ODDScenario]:
        """生成暂态场景"""
        scenarios = []

        transient_types = [
            ("load_increase", "加负荷"),
            ("load_decrease", "减负荷"),
            ("unit_start", "机组启动"),
            ("unit_stop", "机组停机"),
        ]

        for i in range(count):
            trans_type, trans_name = transient_types[i % len(transient_types)]

            # 确保场景在ODD边界内
            pressure_boundary = self.odd.system_boundaries.get("system_pressure")

            events = []
            if trans_type == "load_increase":
                events.append({
                    "time": 60.0,
                    "type": "load_change",
                    "magnitude": np.random.uniform(0.1, 0.3),
                    "direction": "increase",
                })
            elif trans_type == "load_decrease":
                events.append({
                    "time": 60.0,
                    "type": "load_change",
                    "magnitude": np.random.uniform(0.1, 0.3),
                    "direction": "decrease",
                })

            scenario = ODDScenario(
                scenario_id=f"TRANS_{i:03d}",
                scenario_type=ScenarioType.TRANSIENT,
                name=f"{trans_name}暂态场景{i+1}",
                description=f"梯级系统{trans_name}暂态过程",
                odd_zone=ODDZone.NORMAL,
                boundary_constraints={
                    "pressure": (
                        pressure_boundary.degraded_min if pressure_boundary else 3.0,
                        pressure_boundary.degraded_max if pressure_boundary else 7.0
                    ),
                    "max_pressure_rate": self.odd.transient_boundary.max_pressure_gradient,
                },
                initial_conditions={
                    "system_pressure": 5.0,
                    "system_flow": 1000,
                    "frequency": 50.0,
                },
                events=events,
                duration=300.0,
                probability=0.15,
                severity=2,
                tags=["transient", trans_type],
            )
            scenarios.append(scenario)

        self.generated_scenarios.extend(scenarios)
        return scenarios

    def generate_cascade_scenarios(self, count: int = 5) -> List[ODDScenario]:
        """生成级联场景"""
        scenarios = []

        for i in range(count):
            # 级联事件序列
            events = [
                {
                    "time": 30.0,
                    "type": "station_trip",
                    "station": f"YJ0{(i % 5) + 1}",
                    "cause": "protection_triggered",
                },
                {
                    "time": 35.0,
                    "type": "cascade_response",
                    "affected_stations": [f"YJ0{((i+1) % 5) + 1}"],
                    "response": "power_redistribution",
                },
            ]

            scenario = ODDScenario(
                scenario_id=f"CASCADE_{i:03d}",
                scenario_type=ScenarioType.CASCADE_EVENT,
                name=f"级联事件场景{i+1}",
                description="保护触发引发的级联响应场景",
                odd_zone=ODDZone.DEGRADED,
                boundary_constraints={
                    "max_cascade_depth": self.odd.cascade_boundary.max_cascade_depth,
                    "recovery_time": self.odd.cascade_boundary.recovery_delay,
                },
                initial_conditions={
                    "system_pressure": 5.0,
                    "system_flow": 1000,
                    "frequency": 50.0,
                },
                events=events,
                duration=600.0,
                probability=0.04,
                severity=4,
                tags=["cascade", "protection", "degradation"],
            )
            scenarios.append(scenario)

        self.generated_scenarios.extend(scenarios)
        return scenarios

    def generate_boundary_scenarios(self, count: int = 10) -> List[ODDScenario]:
        """生成边界测试场景"""
        scenarios = []

        boundaries_to_test = [
            ("pressure_upper", "system_pressure", "upper"),
            ("pressure_lower", "system_pressure", "lower"),
            ("flow_upper", "system_flow", "upper"),
            ("flow_lower", "system_flow", "lower"),
        ]

        for i in range(count):
            boundary_name, boundary_key, direction = boundaries_to_test[i % len(boundaries_to_test)]
            boundary = self.odd.system_boundaries.get(boundary_key)

            if boundary:
                # 接近但不超过边界
                if direction == "upper":
                    target_value = boundary.normal_max * 0.95
                else:
                    target_value = boundary.normal_min * 1.05

                events = [
                    {
                        "time": 60.0,
                        "type": "approach_boundary",
                        "target": boundary_key,
                        "value": target_value,
                    }
                ]

                scenario = ODDScenario(
                    scenario_id=f"BOUNDARY_{i:03d}",
                    scenario_type=ScenarioType.NORMAL_OPERATION,
                    name=f"边界测试场景-{boundary_name}",
                    description=f"测试{boundary_key}的{direction}边界响应",
                    odd_zone=ODDZone.NORMAL,
                    boundary_constraints={
                        boundary_key: (boundary.normal_min, boundary.normal_max),
                    },
                    initial_conditions={
                        "system_pressure": 5.0,
                        "system_flow": 1000,
                        "frequency": 50.0,
                    },
                    events=events,
                    duration=300.0,
                    probability=0.01,
                    severity=2,
                    tags=["boundary_test", boundary_name],
                )
                scenarios.append(scenario)

        self.generated_scenarios.extend(scenarios)
        return scenarios

    def validate_scenario(self, scenario: ODDScenario) -> Tuple[bool, List[str]]:
        """验证场景是否在ODD边界内"""
        issues = []

        # 检查初始条件
        for key, value in scenario.initial_conditions.items():
            if key in ["system_pressure", "pressure"]:
                boundary = self.odd.system_boundaries.get("system_pressure")
                if boundary and (value < boundary.absolute_min or value > boundary.absolute_max):
                    issues.append(f"初始压力{value}超出绝对边界")

        # 检查事件是否可能导致越界
        for event in scenario.events:
            event_type = event.get("type", "")
            if event_type == "load_change":
                magnitude = event.get("magnitude", 0)
                if magnitude > self.odd.transient_boundary.max_load_rejection_rate:
                    issues.append(f"负荷变化幅度{magnitude}超过限制")

        return len(issues) == 0, issues


class MultiSourceIndicatorAggregator:
    """
    多源指标聚合器

    整合来自不同来源的运行指标
    """

    def __init__(self):
        self.indicators: Dict[str, Dict[str, float]] = {}
        self.indicator_weights: Dict[str, float] = {}
        self.history: List[Dict[str, Any]] = []

    def add_indicator_source(self, source_name: str, weight: float = 1.0):
        """添加指标来源"""
        self.indicators[source_name] = {}
        self.indicator_weights[source_name] = weight

    def update_indicators(self, source_name: str, values: Dict[str, float]):
        """更新指标值"""
        if source_name in self.indicators:
            self.indicators[source_name].update(values)
            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "source": source_name,
                "values": values.copy(),
            })

    def aggregate(self) -> Dict[str, float]:
        """聚合多源指标"""
        aggregated = {}
        indicator_counts = {}

        for source_name, values in self.indicators.items():
            weight = self.indicator_weights.get(source_name, 1.0)

            for key, value in values.items():
                if key not in aggregated:
                    aggregated[key] = 0
                    indicator_counts[key] = 0

                aggregated[key] += value * weight
                indicator_counts[key] += weight

        # 归一化
        for key in aggregated:
            if indicator_counts[key] > 0:
                aggregated[key] /= indicator_counts[key]

        return aggregated

    def get_trend(self, indicator_name: str, window: int = 10) -> Optional[float]:
        """获取指标趋势"""
        values = []
        for record in self.history[-window:]:
            if indicator_name in record.get("values", {}):
                values.append(record["values"][indicator_name])

        if len(values) >= 2:
            # 简单线性趋势
            x = np.arange(len(values))
            slope = np.polyfit(x, values, 1)[0]
            return slope

        return None


class AdaptiveObjectiveManager:
    """
    自适应目标函数管理器

    根据场景和多源指标自动更新目标函数
    """

    def __init__(self):
        self.objectives: Dict[str, ObjectiveFunction] = {}
        self.indicator_aggregator = MultiSourceIndicatorAggregator()
        self.update_history: List[Dict[str, Any]] = []

    def register_objective(self, agent_id: str, objective: ObjectiveFunction):
        """注册目标函数"""
        self.objectives[agent_id] = objective

    def update_from_scenario(self, scenario: ODDScenario):
        """根据场景更新目标函数"""
        for agent_id, objective in self.objectives.items():
            # 根据场景类型调整权重
            if scenario.scenario_type == ScenarioType.CASCADE_EVENT:
                # 级联事件优先安全
                objective.weights["safety"] = min(0.6, objective.weights["safety"] + 0.1)
                objective.weights["economy"] = max(0.1, objective.weights["economy"] - 0.05)

            elif scenario.scenario_type == ScenarioType.TRANSIENT:
                # 暂态优先稳定
                objective.weights["stability"] = min(0.4, objective.weights["stability"] + 0.05)

            elif scenario.odd_zone in [ODDZone.DEGRADED, ODDZone.EMERGENCY]:
                # 降级/应急模式
                objective.weights["safety"] = 0.5
                objective.weights["stability"] = 0.3
                objective.weights["economy"] = 0.1
                objective.weights["flexibility"] = 0.1

            # 归一化
            total = sum(objective.weights.values())
            if total > 0:
                for key in objective.weights:
                    objective.weights[key] /= total

        self._record_update("scenario", scenario.scenario_id)

    def update_from_indicators(self, indicators: Dict[str, float]):
        """根据多源指标更新目标函数"""
        for agent_id, objective in self.objectives.items():
            if not objective.adaptive_enabled:
                continue

            # 计算性能反馈
            performance = {}

            # 安全性反馈
            if "pressure_deviation" in indicators:
                performance["safety"] = 1.0 - min(1.0, abs(indicators["pressure_deviation"]) / 0.5)

            # 稳定性反馈
            if "frequency_deviation" in indicators:
                performance["stability"] = 1.0 - min(1.0, abs(indicators["frequency_deviation"]) / 0.5)

            # 经济性反馈
            if "efficiency" in indicators:
                performance["economy"] = indicators["efficiency"]

            # 更新权重
            objective.update_weights(performance)

        self._record_update("indicators", indicators)

    def update_from_odd_state(self, odd_state: 'SystemODDState'):
        """根据ODD状态更新目标函数"""
        zone = odd_state.overall_zone

        for agent_id, objective in self.objectives.items():
            if zone == ODDZone.OPTIMAL:
                # 最优区可以追求经济性
                objective.weights["economy"] = 0.3
                objective.weights["safety"] = 0.3

            elif zone == ODDZone.DEGRADED:
                # 降级区优先安全和稳定
                objective.weights["safety"] = 0.45
                objective.weights["stability"] = 0.35
                objective.weights["economy"] = 0.15

            elif zone == ODDZone.EMERGENCY:
                # 应急区完全优先安全
                objective.weights["safety"] = 0.6
                objective.weights["stability"] = 0.3
                objective.weights["economy"] = 0.05

            # 归一化
            total = sum(objective.weights.values())
            if total > 0:
                for key in objective.weights:
                    objective.weights[key] /= total

        self._record_update("odd_state", zone.value)

    def _record_update(self, trigger_type: str, trigger_value: Any):
        """记录更新历史"""
        self.update_history.append({
            "timestamp": datetime.now().isoformat(),
            "trigger_type": trigger_type,
            "trigger_value": str(trigger_value),
            "objectives_snapshot": {
                agent_id: obj.weights.copy()
                for agent_id, obj in self.objectives.items()
            }
        })


class ODDAwareAgent(ABC):
    """
    ODD感知智能体基类

    所有智能体必须遵守ODD约束
    """

    def __init__(self, agent_id: str, agent_type: AgentType, odd: 'SystemODD'):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.odd = odd

        # 运行状态
        self.operation_mode = OperationMode.SUPERVISED
        self.is_active = True

        # 目标函数
        self.objective = ObjectiveFunction(
            name=f"{agent_id}_objective",
            description=f"{agent_type.value}的目标函数"
        )

        # 决策历史
        self.decision_history: List[AgentDecision] = []

        # 邻居智能体
        self.neighbors: Set[str] = set()

        # 消息队列
        self.message_queue: queue.Queue = queue.Queue()

    @abstractmethod
    def make_decision(self, state: Dict[str, Any]) -> AgentDecision:
        """做出决策"""
        pass

    def check_odd_compliance(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        """检查动作是否符合ODD约束"""
        return self.odd.check_action_allowed(action)

    def update_objective(self, indicators: Dict[str, float]):
        """更新目标函数"""
        self.objective.update_weights(indicators)


class CentralCoordinatorAgent(ODDAwareAgent):
    """
    中心协调智能体

    负责：
    - 系统级协调决策
    - 场景识别与响应
    - 目标函数分发
    - 降级策略管理
    """

    def __init__(self, agent_id: str, odd: 'SystemODD'):
        super().__init__(agent_id, AgentType.CENTRAL_COORDINATOR, odd)

        # 下属智能体
        self.station_agents: Dict[str, 'StationControllerAgent'] = {}

        # 场景生成器
        self.scenario_generator = ODDScenarioGenerator(odd)

        # 目标函数管理器
        self.objective_manager = AdaptiveObjectiveManager()

        # 指标聚合器
        self.indicator_aggregator = MultiSourceIndicatorAggregator()

        # 系统状态
        self.system_state: Dict[str, Any] = {}

        # 配置指标来源
        self._setup_indicator_sources()

    def _setup_indicator_sources(self):
        """设置指标来源"""
        self.indicator_aggregator.add_indicator_source("scada", weight=1.0)
        self.indicator_aggregator.add_indicator_source("pmu", weight=0.8)
        self.indicator_aggregator.add_indicator_source("prediction", weight=0.6)
        self.indicator_aggregator.add_indicator_source("simulation", weight=0.5)

    def add_station_agent(self, agent: 'StationControllerAgent'):
        """添加电站智能体"""
        self.station_agents[agent.agent_id] = agent
        self.neighbors.add(agent.agent_id)
        self.objective_manager.register_objective(agent.agent_id, agent.objective)

    def make_decision(self, state: Dict[str, Any]) -> AgentDecision:
        """协调决策"""
        self.system_state = state

        # 评估ODD状态
        odd_state = self.odd.evaluate_state(state.get("measurements", {}))

        # 根据ODD状态更新目标函数
        self.objective_manager.update_from_odd_state(odd_state)

        # 确定运行模式
        if odd_state.overall_zone == ODDZone.FORBIDDEN:
            self.operation_mode = OperationMode.EMERGENCY
        elif odd_state.overall_zone in [ODDZone.EMERGENCY, ODDZone.RESTRICTED]:
            self.operation_mode = OperationMode.DEGRADED
        elif odd_state.overall_zone == ODDZone.DEGRADED:
            self.operation_mode = OperationMode.SUPERVISED
        else:
            self.operation_mode = OperationMode.AUTONOMOUS

        # 计算系统级目标
        targets = self._calculate_system_targets(state, odd_state)

        # 分配到各站
        actions = self._allocate_to_stations(targets, odd_state)

        # 检查ODD合规性
        compliant, reason = self.check_odd_compliance({"type": "system_coordination", **actions})

        decision = AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            decision_type="system_coordination",
            actions=actions,
            targets=targets,
            odd_zone=odd_state.overall_zone,
            odd_compliant=compliant,
            coordination_required=True,
            coordination_peers=list(self.station_agents.keys()),
            confidence=0.9 if compliant else 0.5,
        )

        self.decision_history.append(decision)
        return decision

    def _calculate_system_targets(self, state: Dict[str, Any],
                                   odd_state: 'SystemODDState') -> Dict[str, float]:
        """计算系统级目标"""
        targets = {}

        # 基于ODD区域确定目标
        if odd_state.overall_zone == ODDZone.OPTIMAL:
            targets["power_target"] = state.get("load_demand", 5000)
            targets["frequency_target"] = 50.0
            targets["pressure_target"] = 5.0

        elif odd_state.overall_zone in [ODDZone.DEGRADED, ODDZone.RESTRICTED]:
            # 降级模式下保守目标
            targets["power_target"] = state.get("load_demand", 5000) * 0.9
            targets["frequency_target"] = 50.0
            targets["pressure_target"] = 5.0

        elif odd_state.overall_zone == ODDZone.EMERGENCY:
            # 应急模式最小化运行
            targets["power_target"] = state.get("min_power", 2000)
            targets["frequency_target"] = 50.0
            targets["pressure_target"] = 5.0

        return targets

    def _allocate_to_stations(self, targets: Dict[str, float],
                               odd_state: 'SystemODDState') -> Dict[str, Any]:
        """分配目标到各站"""
        allocations = {}
        total_power = targets.get("power_target", 5000)

        # 获取各站可用容量
        available = self.odd.get_available_capacity()

        # 按比例分配
        total_available = sum(available.values())
        if total_available > 0:
            for station_id, capacity in available.items():
                ratio = capacity / total_available
                allocations[station_id] = {
                    "power_target": total_power * ratio,
                    "pressure_target": targets.get("pressure_target", 5.0),
                    "mode": self.operation_mode.value,
                }

        return allocations

    def process_scenario(self, scenario: ODDScenario):
        """处理场景"""
        # 验证场景
        valid, issues = self.scenario_generator.validate_scenario(scenario)

        if valid:
            # 更新目标函数
            self.objective_manager.update_from_scenario(scenario)

            # 通知下属智能体
            for agent in self.station_agents.values():
                agent.receive_scenario_update(scenario)

    def update_from_indicators(self, indicators: Dict[str, float], source: str):
        """更新指标"""
        self.indicator_aggregator.update_indicators(source, indicators)

        # 聚合指标
        aggregated = self.indicator_aggregator.aggregate()

        # 更新目标函数
        self.objective_manager.update_from_indicators(aggregated)


class StationControllerAgent(ODDAwareAgent):
    """
    电站控制智能体

    负责：
    - 电站级控制决策
    - 执行协调指令
    - 本地优化
    - 安全约束执行
    """

    def __init__(self, agent_id: str, station_id: str, odd: 'SystemODD'):
        super().__init__(agent_id, AgentType.STATION_CONTROLLER, odd)

        self.station_id = station_id

        # 机组智能体
        self.unit_agents: Dict[str, 'UnitControllerAgent'] = {}

        # 电站状态
        self.station_state: Dict[str, float] = {}

        # 当前目标
        self.current_targets: Dict[str, float] = {}

        # 协调员引用
        self.coordinator: Optional[CentralCoordinatorAgent] = None

    def set_coordinator(self, coordinator: CentralCoordinatorAgent):
        """设置协调员"""
        self.coordinator = coordinator

    def add_unit_agent(self, agent: 'UnitControllerAgent'):
        """添加机组智能体"""
        self.unit_agents[agent.agent_id] = agent
        self.neighbors.add(agent.agent_id)

    def make_decision(self, state: Dict[str, Any]) -> AgentDecision:
        """电站级决策"""
        self.station_state = state

        # 获取ODD状态
        odd_state = self.odd.current_state
        station_zone = odd_state.station_zones.get(self.station_id, ODDZone.NORMAL)

        # 本地优化
        actions = self._local_optimization(state, station_zone)

        # 分配到机组
        unit_allocations = self._allocate_to_units(actions)

        # 检查ODD合规性
        compliant, reason = self.check_odd_compliance({
            "type": "station_control",
            "station_id": self.station_id,
            **actions
        })

        decision = AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            decision_type="station_control",
            actions={"allocations": unit_allocations, **actions},
            targets=self.current_targets,
            odd_zone=station_zone,
            odd_compliant=compliant,
            coordination_required=len(self.unit_agents) > 1,
            coordination_peers=list(self.unit_agents.keys()),
        )

        self.decision_history.append(decision)
        return decision

    def _local_optimization(self, state: Dict[str, Any],
                            zone: ODDZone) -> Dict[str, Any]:
        """本地优化"""
        actions = {}

        # 当前功率
        current_power = state.get("power", 0)
        target_power = self.current_targets.get("power_target", current_power)

        # 功率调整
        power_error = target_power - current_power
        max_adjustment = 50  # MW/step

        if zone in [ODDZone.DEGRADED, ODDZone.EMERGENCY]:
            max_adjustment = 20  # 降级模式下更保守

        adjustment = np.clip(power_error, -max_adjustment, max_adjustment)
        actions["power_adjustment"] = adjustment

        # 压力控制
        current_pressure = state.get("pressure", 5.0)
        target_pressure = self.current_targets.get("pressure_target", 5.0)

        if abs(current_pressure - target_pressure) > 0.1:
            actions["pressure_control"] = "active"
        else:
            actions["pressure_control"] = "maintain"

        return actions

    def _allocate_to_units(self, actions: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """分配到机组"""
        allocations = {}
        power_adjustment = actions.get("power_adjustment", 0)

        # 均分到各机组
        n_units = len(self.unit_agents)
        if n_units > 0:
            per_unit = power_adjustment / n_units
            for unit_id in self.unit_agents:
                allocations[unit_id] = {
                    "power_adjustment": per_unit,
                    "mode": self.operation_mode.value,
                }

        return allocations

    def receive_scenario_update(self, scenario: ODDScenario):
        """接收场景更新"""
        # 根据场景调整本地目标
        if scenario.scenario_type == ScenarioType.CASCADE_EVENT:
            # 级联事件，准备降级
            self.operation_mode = OperationMode.DEGRADED

        elif scenario.scenario_type == ScenarioType.TRANSIENT:
            # 暂态场景，限制调整速率
            pass

    def receive_coordination_targets(self, targets: Dict[str, float]):
        """接收协调目标"""
        self.current_targets = targets


class UnitControllerAgent(ODDAwareAgent):
    """
    机组控制智能体

    负责：
    - 机组级控制
    - 设备安全约束
    - 本地保护
    """

    def __init__(self, agent_id: str, unit_id: str, station_id: str, odd: 'SystemODD'):
        super().__init__(agent_id, AgentType.UNIT_CONTROLLER, odd)

        self.unit_id = unit_id
        self.station_id = station_id

        # 机组状态
        self.unit_state: Dict[str, float] = {}

        # 控制参数
        self.control_params = {
            "guide_vane_rate_limit": 0.1,  # pu/s
            "power_rate_limit": 50,         # MW/s
        }

    def make_decision(self, state: Dict[str, Any]) -> AgentDecision:
        """机组级决策"""
        self.unit_state = state

        # 本地控制计算
        actions = self._compute_control(state)

        # 检查ODD合规性
        compliant, reason = self.check_odd_compliance({
            "type": "unit_control",
            "unit_id": self.unit_id,
            "guide_vane_rate": actions.get("guide_vane_rate", 0),
        })

        decision = AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            decision_type="unit_control",
            actions=actions,
            targets={},
            odd_zone=self.odd.current_state.overall_zone,
            odd_compliant=compliant,
        )

        self.decision_history.append(decision)
        return decision

    def _compute_control(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """计算控制量"""
        actions = {}

        # 导叶开度控制
        current_gv = state.get("guide_vane", 0.8)
        target_power = state.get("power_target", 0)
        current_power = state.get("power", 0)

        power_error = target_power - current_power
        gv_adjustment = power_error * 0.001  # 简化的控制律

        # 应用速率限制
        gv_adjustment = np.clip(
            gv_adjustment,
            -self.control_params["guide_vane_rate_limit"],
            self.control_params["guide_vane_rate_limit"]
        )

        actions["guide_vane_command"] = current_gv + gv_adjustment
        actions["guide_vane_rate"] = abs(gv_adjustment)

        return actions


class ODDAwareMASSystem:
    """
    ODD感知多智能体系统

    集成ODD、MAS、场景生成的完整系统
    """

    def __init__(self, odd: 'SystemODD'):
        self.odd = odd

        # 中心协调智能体
        self.coordinator: Optional[CentralCoordinatorAgent] = None

        # 所有智能体
        self.agents: Dict[str, ODDAwareAgent] = {}

        # 场景生成器
        self.scenario_generator = ODDScenarioGenerator(odd)

        # 系统状态
        self.system_time = 0.0
        self.running = False

    def setup_cascade_system(self, stations_config: List[Dict[str, Any]]):
        """设置梯级系统"""
        # 创建中心协调智能体
        self.coordinator = CentralCoordinatorAgent("COORDINATOR", self.odd)
        self.agents["COORDINATOR"] = self.coordinator

        # 创建电站和机组智能体
        for station_config in stations_config:
            station_id = station_config["id"]

            # 电站智能体
            station_agent = StationControllerAgent(
                f"STATION_{station_id}",
                station_id,
                self.odd
            )
            station_agent.set_coordinator(self.coordinator)
            self.coordinator.add_station_agent(station_agent)
            self.agents[station_agent.agent_id] = station_agent

            # 机组智能体
            num_units = station_config.get("num_units", 4)
            for i in range(num_units):
                unit_id = f"{station_id}_U{i+1}"
                unit_agent = UnitControllerAgent(
                    f"UNIT_{unit_id}",
                    unit_id,
                    station_id,
                    self.odd
                )
                station_agent.add_unit_agent(unit_agent)
                self.agents[unit_agent.agent_id] = unit_agent

    def generate_scenarios(self) -> List[ODDScenario]:
        """生成全套场景"""
        scenarios = []

        scenarios.extend(self.scenario_generator.generate_normal_scenarios(20))
        scenarios.extend(self.scenario_generator.generate_transient_scenarios(15))
        scenarios.extend(self.scenario_generator.generate_cascade_scenarios(10))
        scenarios.extend(self.scenario_generator.generate_boundary_scenarios(10))

        return scenarios

    def run_scenario(self, scenario: ODDScenario, duration: float = None) -> Dict[str, Any]:
        """运行场景"""
        duration = duration or scenario.duration

        # 通知协调员
        self.coordinator.process_scenario(scenario)

        # 初始化状态
        state = scenario.initial_conditions.copy()
        results = {
            "time": [],
            "states": [],
            "decisions": [],
            "odd_zones": [],
        }

        # 仿真循环
        dt = 0.1
        t = 0.0

        while t < duration:
            # 处理场景事件
            for event in scenario.events:
                if abs(event.get("time", -1) - t) < dt:
                    state = self._apply_event(state, event)

            # 各智能体决策
            coordinator_decision = self.coordinator.make_decision({"measurements": {
                station_id: state for station_id in self.odd.stations
            }})

            # 记录结果
            results["time"].append(t)
            results["states"].append(copy.deepcopy(state))
            results["decisions"].append(coordinator_decision)
            results["odd_zones"].append(self.odd.current_state.overall_zone.value)

            t += dt

        return results

    def _apply_event(self, state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
        """应用场景事件"""
        new_state = state.copy()

        event_type = event.get("type", "")

        if event_type == "load_change":
            direction = event.get("direction", "increase")
            magnitude = event.get("magnitude", 0.1)

            if direction == "increase":
                new_state["load_demand"] = state.get("load_demand", 5000) * (1 + magnitude)
            else:
                new_state["load_demand"] = state.get("load_demand", 5000) * (1 - magnitude)

        elif event_type == "station_trip":
            station = event.get("station", "")
            # 标记电站跳闸
            new_state[f"{station}_tripped"] = True

        return new_state

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "odd_state": {
                "zone": self.odd.current_state.overall_zone.value,
                "degradation_level": self.odd.current_state.degradation_level.value,
            },
            "coordinator_mode": self.coordinator.operation_mode.value if self.coordinator else None,
            "agents_count": len(self.agents),
            "scenarios_generated": len(self.scenario_generator.generated_scenarios),
        }


def create_yajiang_mas_system() -> ODDAwareMASSystem:
    """创建雅鲁藏布江大拐弯工程MAS系统"""
    from ..odd.operational_design_domain import create_yajiang_bigbend_odd

    # 创建ODD
    odd = create_yajiang_bigbend_odd()

    # 创建MAS系统
    mas = ODDAwareMASSystem(odd)

    # 配置梯级电站
    stations = [
        {"id": "YJ01", "name": "墨脱", "num_units": 6},
        {"id": "YJ02", "name": "多雄藏布", "num_units": 4},
        {"id": "YJ03", "name": "达木", "num_units": 3},
        {"id": "YJ04", "name": "巴玉", "num_units": 3},
        {"id": "YJ05", "name": "通德", "num_units": 2},
    ]

    mas.setup_cascade_system(stations)

    return mas
