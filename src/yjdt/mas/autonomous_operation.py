# -*- coding: utf-8 -*-
"""
全自主运行MAS模块 - Autonomous Operation MAS

在ODD范围内实现全自主运行：
- 运行区域（Operational）：全自主优化运行
- 受限区域（Restricted）：自主安全控制
- 禁止区域（Forbidden）：自主保护降级

核心能力：
- ODD感知的自主决策
- 分层降级控制
- 多智能体协同
- 自适应目标函数
- 安全边界守护

参考：YX工程面向运行能力的设计评估与运行逻辑验证关键技术研究
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable, Set
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import logging
import copy
import threading
from queue import PriorityQueue

logger = logging.getLogger(__name__)


class AutonomyLevel(Enum):
    """自主等级"""
    FULL_AUTONOMOUS = 5         # 完全自主（最优区域）
    HIGH_AUTONOMOUS = 4         # 高度自主（正常区域）
    SUPERVISED_AUTONOMOUS = 3   # 监督自主（降级区域）
    ASSISTED = 2                # 辅助模式（受限区域）
    MANUAL = 1                  # 人工模式（应急区域）
    LOCKDOWN = 0                # 锁定模式（禁止区域）


class OperationMode(Enum):
    """运行模式"""
    ECONOMIC = "economic"               # 经济优化
    RELIABILITY = "reliability"         # 可靠性优先
    FLEXIBILITY = "flexibility"         # 灵活响应
    SAFETY = "safety"                   # 安全优先
    EMERGENCY = "emergency"             # 应急模式
    PROTECTION = "protection"           # 保护模式


class DecisionPriority(Enum):
    """决策优先级"""
    CRITICAL = 0        # 关键（立即执行）
    HIGH = 1            # 高优先级
    NORMAL = 2          # 正常优先级
    LOW = 3             # 低优先级
    BACKGROUND = 4      # 后台任务


@dataclass
class OperationContext:
    """运行上下文"""
    timestamp: datetime
    odd_zone: str
    autonomy_level: AutonomyLevel
    operation_mode: OperationMode

    # 系统状态
    system_state: Dict[str, float] = field(default_factory=dict)

    # ODD状态
    odd_violations: List[Dict] = field(default_factory=list)
    boundary_distances: Dict[str, float] = field(default_factory=dict)

    # 约束
    active_constraints: List[str] = field(default_factory=list)

    # 目标权重
    objective_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class ControlAction:
    """控制动作"""
    action_id: str
    action_type: str
    target: str                         # 目标对象
    parameters: Dict[str, float]        # 动作参数

    priority: DecisionPriority = DecisionPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)

    # 约束检查
    odd_checked: bool = False
    safety_checked: bool = False

    # 执行状态
    executed: bool = False
    execution_result: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutonomousDecision:
    """自主决策"""
    decision_id: str
    timestamp: datetime
    context: OperationContext

    # 决策内容
    actions: List[ControlAction] = field(default_factory=list)

    # 决策依据
    reasoning: str = ""
    confidence: float = 0.0

    # 验证结果
    odd_validated: bool = False
    safety_validated: bool = False


class AutonomousController(ABC):
    """
    自主控制器基类

    定义自主控制的通用接口
    """

    def __init__(self, controller_id: str, name: str):
        self.controller_id = controller_id
        self.name = name
        self.autonomy_level = AutonomyLevel.HIGH_AUTONOMOUS
        self.operation_mode = OperationMode.RELIABILITY

        # 状态
        self.enabled = True
        self.last_decision: AutonomousDecision = None

        # 回调
        self.decision_callbacks: List[Callable] = []

    @abstractmethod
    def decide(self, context: OperationContext) -> AutonomousDecision:
        """做出自主决策"""
        pass

    @abstractmethod
    def execute(self, decision: AutonomousDecision) -> bool:
        """执行决策"""
        pass

    def set_autonomy_level(self, level: AutonomyLevel):
        """设置自主等级"""
        self.autonomy_level = level
        logger.info(f"{self.name} 自主等级设置为: {level.name}")

    def set_operation_mode(self, mode: OperationMode):
        """设置运行模式"""
        self.operation_mode = mode
        logger.info(f"{self.name} 运行模式设置为: {mode.value}")


class ODDBoundaryGuard:
    """
    ODD边界守护器

    确保所有控制动作不越过ODD边界
    """

    def __init__(self, odd_config: Dict[str, Any] = None):
        self.odd_config = odd_config or {}
        self.boundaries: Dict[str, Dict] = {}
        self.violation_log: List[Dict] = []

        self._init_default_boundaries()

    def _init_default_boundaries(self):
        """初始化默认边界"""
        self.boundaries = {
            "pressure": {
                "optimal": (4.5, 5.0),
                "normal": (4.0, 5.5),
                "degraded": (3.5, 6.0),
                "restricted": (3.0, 6.5),
                "forbidden_below": 2.5,
                "forbidden_above": 7.0,
            },
            "flow": {
                "optimal": (800, 1000),
                "normal": (600, 1100),
                "degraded": (400, 1200),
                "restricted": (200, 1300),
                "forbidden_below": 0,
                "forbidden_above": 1500,
            },
            "frequency": {
                "optimal": (49.95, 50.05),
                "normal": (49.8, 50.2),
                "degraded": (49.5, 50.5),
                "restricted": (48.0, 52.0),
                "forbidden_below": 45.0,
                "forbidden_above": 55.0,
            },
            "guide_vane_rate": {
                "optimal": (0, 0.05),
                "normal": (0, 0.08),
                "degraded": (0, 0.10),
                "restricted": (0, 0.15),
                "forbidden_above": 0.20,
            },
        }

    def validate_action(self, action: ControlAction,
                        current_state: Dict[str, float],
                        current_zone: str) -> Tuple[bool, str, Dict]:
        """
        验证控制动作是否在ODD边界内

        Returns:
            (是否有效, 原因, 修正后的动作参数)
        """
        action_type = action.action_type
        params = action.parameters

        # 获取当前区域的边界
        zone_boundaries = self._get_zone_boundaries(current_zone)

        # 预测动作后的状态
        predicted_state = self._predict_state(current_state, action)

        # 检查预测状态是否在边界内
        violations = []
        corrected_params = params.copy()

        for var, value in predicted_state.items():
            if var in zone_boundaries:
                bounds = zone_boundaries[var]
                min_val, max_val = bounds.get("min", float('-inf')), bounds.get("max", float('inf'))

                if value < min_val:
                    violations.append(f"{var}预测值{value:.2f}低于下限{min_val:.2f}")
                    # 修正参数
                    corrected_params = self._correct_action(
                        action, var, "increase", current_state
                    )
                elif value > max_val:
                    violations.append(f"{var}预测值{value:.2f}高于上限{max_val:.2f}")
                    # 修正参数
                    corrected_params = self._correct_action(
                        action, var, "decrease", current_state
                    )

        if violations:
            reason = "; ".join(violations)
            self.violation_log.append({
                "timestamp": datetime.now().isoformat(),
                "action": action.action_id,
                "violations": violations,
            })
            return False, reason, corrected_params

        return True, "动作在ODD边界内", params

    def _get_zone_boundaries(self, zone: str) -> Dict[str, Dict]:
        """获取区域边界"""
        zone_bounds = {}
        for var, bounds in self.boundaries.items():
            if zone in bounds:
                zone_range = bounds[zone]
                zone_bounds[var] = {"min": zone_range[0], "max": zone_range[1]}
            else:
                # 使用forbidden边界作为默认
                zone_bounds[var] = {
                    "min": bounds.get("forbidden_below", float('-inf')),
                    "max": bounds.get("forbidden_above", float('inf')),
                }
        return zone_bounds

    def _predict_state(self, current_state: Dict[str, float],
                       action: ControlAction) -> Dict[str, float]:
        """预测动作后的状态"""
        predicted = current_state.copy()

        action_type = action.action_type
        params = action.parameters

        if action_type == "guide_vane":
            # 导叶动作影响流量和压力
            delta = params.get("delta", 0)
            predicted["flow"] = predicted.get("flow", 0) + delta * 100
            predicted["pressure"] = predicted.get("pressure", 0) - delta * 0.5

        elif action_type == "power_setpoint":
            # 功率设定影响频率
            delta_p = params.get("delta_power", 0)
            predicted["frequency"] = predicted.get("frequency", 50) + delta_p * 0.001

        elif action_type == "emergency_shutdown":
            # 紧急停机
            predicted["flow"] = 0
            predicted["power"] = 0

        return predicted

    def _correct_action(self, action: ControlAction,
                        variable: str, direction: str,
                        current_state: Dict[str, float]) -> Dict[str, float]:
        """修正动作参数"""
        corrected = action.parameters.copy()

        if action.action_type == "guide_vane":
            if direction == "increase":
                corrected["delta"] = max(corrected.get("delta", 0) - 0.01, -0.1)
            else:
                corrected["delta"] = min(corrected.get("delta", 0) + 0.01, 0.1)

        elif action.action_type == "power_setpoint":
            if direction == "increase":
                corrected["delta_power"] = min(corrected.get("delta_power", 0) + 10, 100)
            else:
                corrected["delta_power"] = max(corrected.get("delta_power", 0) - 10, -100)

        return corrected

    def calculate_boundary_distance(self,
                                    state: Dict[str, float],
                                    zone: str) -> Dict[str, float]:
        """计算到边界的距离"""
        distances = {}
        zone_bounds = self._get_zone_boundaries(zone)

        for var, value in state.items():
            if var in zone_bounds:
                bounds = zone_bounds[var]
                min_val, max_val = bounds.get("min", 0), bounds.get("max", 0)

                dist_to_lower = value - min_val
                dist_to_upper = max_val - value

                distances[f"{var}_to_lower"] = dist_to_lower
                distances[f"{var}_to_upper"] = dist_to_upper
                distances[f"{var}_min_distance"] = min(dist_to_lower, dist_to_upper)

        return distances


class AdaptiveObjectiveManager:
    """
    自适应目标函数管理器

    根据ODD状态自动调整目标函数权重
    """

    def __init__(self):
        self.base_weights = {
            "economy": 0.3,
            "safety": 0.3,
            "reliability": 0.2,
            "flexibility": 0.1,
            "efficiency": 0.1,
        }
        self.current_weights = self.base_weights.copy()
        self.weight_history: List[Dict] = []

    def update_weights(self, context: OperationContext) -> Dict[str, float]:
        """根据上下文更新权重"""
        new_weights = self.base_weights.copy()

        # 根据ODD区域调整
        zone = context.odd_zone
        if zone == "optimal":
            # 最优区域：经济性优先
            new_weights["economy"] = 0.4
            new_weights["safety"] = 0.2
        elif zone == "normal":
            # 正常区域：均衡
            pass
        elif zone in ["degraded", "restricted"]:
            # 降级/受限区域：安全优先
            new_weights["economy"] = 0.1
            new_weights["safety"] = 0.5
            new_weights["reliability"] = 0.3
        elif zone == "emergency":
            # 应急区域：安全最高
            new_weights["economy"] = 0.0
            new_weights["safety"] = 0.7
            new_weights["reliability"] = 0.2
            new_weights["flexibility"] = 0.1
        elif zone == "forbidden":
            # 禁止区域：仅安全
            new_weights["economy"] = 0.0
            new_weights["safety"] = 1.0
            new_weights["reliability"] = 0.0
            new_weights["flexibility"] = 0.0
            new_weights["efficiency"] = 0.0

        # 根据边界距离微调
        if context.boundary_distances:
            min_distance = min(
                v for k, v in context.boundary_distances.items()
                if "min_distance" in k
            ) if context.boundary_distances else float('inf')

            if min_distance < 0.1:  # 接近边界
                safety_boost = 0.2 * (1 - min_distance / 0.1)
                new_weights["safety"] += safety_boost
                new_weights["economy"] = max(0, new_weights["economy"] - safety_boost)

        # 根据运行模式调整
        if context.operation_mode == OperationMode.ECONOMIC:
            new_weights["economy"] *= 1.5
        elif context.operation_mode == OperationMode.SAFETY:
            new_weights["safety"] *= 1.5

        # 归一化
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v/total for k, v in new_weights.items()}

        self.current_weights = new_weights
        self.weight_history.append({
            "timestamp": datetime.now().isoformat(),
            "zone": zone,
            "weights": new_weights.copy(),
        })

        return new_weights

    def get_objective_value(self, metrics: Dict[str, float]) -> float:
        """计算综合目标值"""
        value = 0
        for name, weight in self.current_weights.items():
            metric_value = metrics.get(name, 0)
            value += weight * metric_value
        return value


class DegradationController:
    """
    降级控制器

    管理系统降级策略
    """

    def __init__(self):
        self.degradation_strategies: Dict[str, Dict] = {}
        self.current_level = 0
        self.degradation_history: List[Dict] = []

        self._init_default_strategies()

    def _init_default_strategies(self):
        """初始化默认降级策略"""
        self.degradation_strategies = {
            0: {
                "name": "最优运行",
                "description": "全功能，全自主",
                "allowed_actions": ["all"],
                "capacity_limit": 1.0,
                "response_time_limit": None,
            },
            1: {
                "name": "正常运行",
                "description": "标准自主控制",
                "allowed_actions": ["optimization", "regulation", "coordination"],
                "capacity_limit": 1.0,
                "response_time_limit": 60,
            },
            2: {
                "name": "预警运行",
                "description": "限制优化，保守控制",
                "allowed_actions": ["regulation", "coordination"],
                "capacity_limit": 0.95,
                "response_time_limit": 30,
            },
            3: {
                "name": "降级运行",
                "description": "安全优先，减少协同",
                "allowed_actions": ["safety_control", "basic_regulation"],
                "capacity_limit": 0.8,
                "response_time_limit": 15,
            },
            4: {
                "name": "应急运行",
                "description": "最小化运行，准备停机",
                "allowed_actions": ["emergency_control"],
                "capacity_limit": 0.5,
                "response_time_limit": 5,
            },
            5: {
                "name": "保护停机",
                "description": "有序停机，保护设备",
                "allowed_actions": ["shutdown", "protection"],
                "capacity_limit": 0,
                "response_time_limit": 1,
            },
        }

    def degrade(self, reason: str) -> Dict[str, Any]:
        """执行降级"""
        if self.current_level < 5:
            old_level = self.current_level
            self.current_level += 1

            self.degradation_history.append({
                "timestamp": datetime.now().isoformat(),
                "from_level": old_level,
                "to_level": self.current_level,
                "reason": reason,
                "action": "degrade",
            })

            logger.warning(f"系统降级: L{old_level} -> L{self.current_level}, 原因: {reason}")

        return self.get_current_strategy()

    def upgrade(self, reason: str) -> Dict[str, Any]:
        """执行升级（恢复）"""
        if self.current_level > 0:
            old_level = self.current_level
            self.current_level -= 1

            self.degradation_history.append({
                "timestamp": datetime.now().isoformat(),
                "from_level": old_level,
                "to_level": self.current_level,
                "reason": reason,
                "action": "upgrade",
            })

            logger.info(f"系统升级: L{old_level} -> L{self.current_level}, 原因: {reason}")

        return self.get_current_strategy()

    def get_current_strategy(self) -> Dict[str, Any]:
        """获取当前降级策略"""
        return self.degradation_strategies.get(
            self.current_level,
            self.degradation_strategies[1]
        )

    def is_action_allowed(self, action_type: str) -> bool:
        """检查动作是否允许"""
        strategy = self.get_current_strategy()
        allowed = strategy.get("allowed_actions", [])
        return "all" in allowed or action_type in allowed


class ZoneController:
    """
    区域控制器

    针对不同ODD区域的专用控制逻辑
    """

    def __init__(self, boundary_guard: ODDBoundaryGuard,
                 degradation_controller: DegradationController,
                 objective_manager: AdaptiveObjectiveManager):
        self.boundary_guard = boundary_guard
        self.degradation = degradation_controller
        self.objectives = objective_manager

    def control_optimal_zone(self, context: OperationContext) -> List[ControlAction]:
        """最优区域控制 - 全自主优化"""
        actions = []

        # 经济优化调度
        if context.operation_mode == OperationMode.ECONOMIC:
            # 分析当前状态，寻找优化机会
            power = context.system_state.get("total_power", 0)
            efficiency = context.system_state.get("efficiency", 0.9)

            if efficiency < 0.92:
                # 优化效率
                actions.append(ControlAction(
                    action_id=f"opt_{datetime.now().strftime('%H%M%S')}",
                    action_type="efficiency_optimization",
                    target="system",
                    parameters={"target_efficiency": 0.93},
                    priority=DecisionPriority.LOW,
                ))

        return actions

    def control_normal_zone(self, context: OperationContext) -> List[ControlAction]:
        """正常区域控制 - 标准自主"""
        actions = []

        # 频率调节
        frequency = context.system_state.get("frequency", 50)
        if abs(frequency - 50) > 0.1:
            delta_p = (50 - frequency) * 100  # 简化的调频逻辑
            actions.append(ControlAction(
                action_id=f"freq_{datetime.now().strftime('%H%M%S')}",
                action_type="power_setpoint",
                target="system",
                parameters={"delta_power": delta_p},
                priority=DecisionPriority.NORMAL,
            ))

        return actions

    def control_degraded_zone(self, context: OperationContext) -> List[ControlAction]:
        """降级区域控制 - 保守自主"""
        actions = []

        # 减少出力
        current_power = context.system_state.get("total_power", 0)
        capacity_limit = self.degradation.get_current_strategy()["capacity_limit"]
        max_power = context.system_state.get("max_power", current_power)

        if current_power > max_power * capacity_limit:
            reduction = current_power - max_power * capacity_limit
            actions.append(ControlAction(
                action_id=f"reduce_{datetime.now().strftime('%H%M%S')}",
                action_type="power_reduction",
                target="system",
                parameters={"reduction": reduction},
                priority=DecisionPriority.HIGH,
            ))

        return actions

    def control_restricted_zone(self, context: OperationContext) -> List[ControlAction]:
        """受限区域控制 - 安全优先自主"""
        actions = []

        # 紧急降载
        actions.append(ControlAction(
            action_id=f"restrict_{datetime.now().strftime('%H%M%S')}",
            action_type="load_shedding",
            target="system",
            parameters={"shed_ratio": 0.2},
            priority=DecisionPriority.HIGH,
        ))

        # 准备应急
        actions.append(ControlAction(
            action_id=f"prep_{datetime.now().strftime('%H%M%S')}",
            action_type="emergency_preparation",
            target="system",
            parameters={"alert_level": "high"},
            priority=DecisionPriority.NORMAL,
        ))

        return actions

    def control_emergency_zone(self, context: OperationContext) -> List[ControlAction]:
        """应急区域控制 - 应急自主"""
        actions = []

        # 最小化运行
        actions.append(ControlAction(
            action_id=f"min_{datetime.now().strftime('%H%M%S')}",
            action_type="minimum_operation",
            target="system",
            parameters={"keep_units": 1},
            priority=DecisionPriority.CRITICAL,
        ))

        return actions

    def control_forbidden_zone(self, context: OperationContext) -> List[ControlAction]:
        """禁止区域控制 - 保护自主"""
        actions = []

        # 紧急停机
        actions.append(ControlAction(
            action_id=f"stop_{datetime.now().strftime('%H%M%S')}",
            action_type="emergency_shutdown",
            target="all_units",
            parameters={"controlled": True, "sequence": "priority"},
            priority=DecisionPriority.CRITICAL,
        ))

        # 隔离保护
        actions.append(ControlAction(
            action_id=f"isolate_{datetime.now().strftime('%H%M%S')}",
            action_type="isolation",
            target="affected_systems",
            parameters={"isolation_level": "full"},
            priority=DecisionPriority.CRITICAL,
        ))

        return actions


class FullAutonomousMAS:
    """
    全自主运行多智能体系统

    在ODD范围内实现运行、受限、禁止区域的全自主运行
    """

    def __init__(self, odd=None, model=None):
        self.odd = odd
        self.model = model

        # 核心组件
        self.boundary_guard = ODDBoundaryGuard()
        self.degradation = DegradationController()
        self.objectives = AdaptiveObjectiveManager()
        self.zone_controller = ZoneController(
            self.boundary_guard,
            self.degradation,
            self.objectives
        )

        # 决策队列
        self.decision_queue: PriorityQueue = PriorityQueue()
        self.pending_actions: List[ControlAction] = []

        # 状态
        self.current_context: OperationContext = None
        self.autonomy_level = AutonomyLevel.HIGH_AUTONOMOUS

        # 历史
        self.decision_history: List[AutonomousDecision] = []
        self.action_history: List[ControlAction] = []

        # 控制周期
        self.control_cycle_ms = 100  # 100ms控制周期

    def initialize(self, initial_state: Dict[str, float] = None):
        """初始化系统"""
        state = initial_state or {}

        self.current_context = OperationContext(
            timestamp=datetime.now(),
            odd_zone="normal",
            autonomy_level=self.autonomy_level,
            operation_mode=OperationMode.RELIABILITY,
            system_state=state,
        )

        logger.info("全自主运行MAS初始化完成")

    def update_state(self, new_state: Dict[str, float]):
        """更新系统状态"""
        if self.current_context is None:
            self.initialize(new_state)
            return

        self.current_context.system_state = new_state
        self.current_context.timestamp = datetime.now()

        # 更新边界距离
        self.current_context.boundary_distances = self.boundary_guard.calculate_boundary_distance(
            new_state, self.current_context.odd_zone
        )

    def set_odd_zone(self, zone: str, violations: List[Dict] = None):
        """设置ODD区域"""
        if self.current_context:
            old_zone = self.current_context.odd_zone
            self.current_context.odd_zone = zone
            self.current_context.odd_violations = violations or []

            # 根据区域调整自主等级
            self._adjust_autonomy_for_zone(zone)

            # 更新目标权重
            self.objectives.update_weights(self.current_context)

            if old_zone != zone:
                logger.info(f"ODD区域变化: {old_zone} -> {zone}")

    def _adjust_autonomy_for_zone(self, zone: str):
        """根据区域调整自主等级"""
        zone_autonomy = {
            "optimal": AutonomyLevel.FULL_AUTONOMOUS,
            "normal": AutonomyLevel.HIGH_AUTONOMOUS,
            "degraded": AutonomyLevel.SUPERVISED_AUTONOMOUS,
            "restricted": AutonomyLevel.ASSISTED,
            "emergency": AutonomyLevel.MANUAL,
            "forbidden": AutonomyLevel.LOCKDOWN,
        }
        self.autonomy_level = zone_autonomy.get(zone, AutonomyLevel.HIGH_AUTONOMOUS)
        if self.current_context:
            self.current_context.autonomy_level = self.autonomy_level

    def run_control_cycle(self) -> AutonomousDecision:
        """运行一个控制周期"""
        if self.current_context is None:
            return None

        # 1. 根据当前区域获取控制动作
        zone = self.current_context.odd_zone
        actions = self._get_zone_actions(zone)

        # 2. 验证所有动作
        validated_actions = []
        for action in actions:
            valid, reason, corrected_params = self.boundary_guard.validate_action(
                action,
                self.current_context.system_state,
                zone
            )

            if valid:
                action.odd_checked = True
                validated_actions.append(action)
            else:
                # 使用修正后的参数重试
                action.parameters = corrected_params
                valid2, _, _ = self.boundary_guard.validate_action(
                    action,
                    self.current_context.system_state,
                    zone
                )
                if valid2:
                    action.odd_checked = True
                    validated_actions.append(action)
                else:
                    logger.warning(f"动作{action.action_id}无法满足ODD约束: {reason}")

        # 3. 检查降级策略允许
        allowed_actions = []
        for action in validated_actions:
            if self.degradation.is_action_allowed(action.action_type):
                action.safety_checked = True
                allowed_actions.append(action)
            else:
                logger.warning(f"动作{action.action_type}在当前降级等级不允许")

        # 4. 创建决策
        decision = AutonomousDecision(
            decision_id=f"dec_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            timestamp=datetime.now(),
            context=copy.deepcopy(self.current_context),
            actions=allowed_actions,
            reasoning=f"区域{zone}自主控制决策",
            confidence=1.0 if allowed_actions else 0.5,
            odd_validated=True,
            safety_validated=True,
        )

        self.decision_history.append(decision)
        return decision

    def _get_zone_actions(self, zone: str) -> List[ControlAction]:
        """根据区域获取控制动作"""
        context = self.current_context

        if zone == "optimal":
            return self.zone_controller.control_optimal_zone(context)
        elif zone == "normal":
            return self.zone_controller.control_normal_zone(context)
        elif zone == "degraded":
            return self.zone_controller.control_degraded_zone(context)
        elif zone == "restricted":
            return self.zone_controller.control_restricted_zone(context)
        elif zone == "emergency":
            return self.zone_controller.control_emergency_zone(context)
        elif zone == "forbidden":
            return self.zone_controller.control_forbidden_zone(context)
        else:
            return self.zone_controller.control_normal_zone(context)

    def execute_decision(self, decision: AutonomousDecision) -> Dict[str, Any]:
        """执行决策"""
        results = {
            "decision_id": decision.decision_id,
            "executed_actions": [],
            "failed_actions": [],
            "summary": "",
        }

        for action in decision.actions:
            try:
                success = self._execute_action(action)
                if success:
                    action.executed = True
                    results["executed_actions"].append(action.action_id)
                else:
                    results["failed_actions"].append(action.action_id)
            except Exception as e:
                logger.error(f"执行动作{action.action_id}失败: {e}")
                results["failed_actions"].append(action.action_id)

            self.action_history.append(action)

        n_exec = len(results["executed_actions"])
        n_fail = len(results["failed_actions"])
        results["summary"] = f"执行{n_exec}个动作成功，{n_fail}个失败"

        return results

    def _execute_action(self, action: ControlAction) -> bool:
        """执行单个动作"""
        # 这里是实际的控制接口
        # 在真实系统中会调用SCADA/DCS接口

        logger.info(f"执行动作: {action.action_type} -> {action.target}")
        action.execution_result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
        }
        return True

    def handle_odd_violation(self, violation: Dict[str, Any]):
        """处理ODD违规"""
        severity = violation.get("severity", "warning")

        if severity in ["critical", "emergency"]:
            # 严重违规：立即降级
            self.degradation.degrade(f"ODD违规: {violation.get('rule', 'unknown')}")

            # 生成保护动作
            protection_actions = self._generate_protection_actions(violation)
            for action in protection_actions:
                self.pending_actions.append(action)

        elif severity == "major":
            # 主要违规：警告并准备降级
            logger.warning(f"ODD主要违规: {violation}")

        else:
            # 轻微违规：记录
            logger.info(f"ODD违规: {violation}")

    def _generate_protection_actions(self, violation: Dict) -> List[ControlAction]:
        """生成保护动作"""
        actions = []

        violated_var = violation.get("variable", "")

        if "pressure" in violated_var:
            # 压力违规：快速减载
            actions.append(ControlAction(
                action_id=f"prot_pressure_{datetime.now().strftime('%H%M%S')}",
                action_type="rapid_load_reduction",
                target="system",
                parameters={"reduction_rate": 0.3},
                priority=DecisionPriority.CRITICAL,
            ))

        elif "frequency" in violated_var:
            # 频率违规：启动调频
            actions.append(ControlAction(
                action_id=f"prot_freq_{datetime.now().strftime('%H%M%S')}",
                action_type="frequency_regulation",
                target="all_units",
                parameters={"mode": "emergency"},
                priority=DecisionPriority.CRITICAL,
            ))

        return actions

    def request_recovery(self) -> bool:
        """请求恢复（升级）"""
        # 检查是否满足恢复条件
        if self.current_context is None:
            return False

        zone = self.current_context.odd_zone
        violations = self.current_context.odd_violations

        if zone in ["optimal", "normal"] and not violations:
            self.degradation.upgrade("ODD状态恢复正常")
            return True

        return False

    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "timestamp": datetime.now().isoformat(),
            "odd_zone": self.current_context.odd_zone if self.current_context else "unknown",
            "autonomy_level": self.autonomy_level.name,
            "degradation_level": self.degradation.current_level,
            "operation_mode": self.current_context.operation_mode.value if self.current_context else "unknown",
            "objective_weights": self.objectives.current_weights,
            "pending_actions": len(self.pending_actions),
            "total_decisions": len(self.decision_history),
        }


def create_yajiang_autonomous_mas(odd=None, model=None) -> FullAutonomousMAS:
    """创建雅江大拐弯工程全自主MAS"""
    mas = FullAutonomousMAS(odd, model)

    # 配置边界守护器（使用工程参数）
    mas.boundary_guard.boundaries["pressure"] = {
        "optimal": (4.5, 5.0),
        "normal": (4.0, 5.5),
        "degraded": (3.5, 6.0),
        "restricted": (3.0, 6.5),
        "forbidden_below": 2.0,
        "forbidden_above": 7.5,
    }

    mas.boundary_guard.boundaries["flow"] = {
        "optimal": (1600, 1900),
        "normal": (1200, 2000),
        "degraded": (800, 2100),
        "restricted": (400, 2200),
        "forbidden_below": 0,
        "forbidden_above": 2500,
    }

    # 初始化
    initial_state = {
        "total_power": 50000,
        "frequency": 50.0,
        "system_pressure": 4.8,
        "system_flow": 1800,
        "efficiency": 0.91,
        "max_power": 60000,
    }
    mas.initialize(initial_state)

    return mas
