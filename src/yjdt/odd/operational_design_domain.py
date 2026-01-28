# -*- coding: utf-8 -*-
"""
系统级设计运行域 - Operational Design Domain (ODD)

基于YX工程（雅鲁藏布江大拐弯截弯取直引水梯级发电工程）的系统级ODD定义

核心功能：
- 系统级ODD边界定义与管理
- 有压五梯级系统压力边界
- 系统瞬变边界
- 级联降级边界
- ODD状态监控与预警
- ODD边界验证

参考：YX工程面向运行能力的设计评估与运行逻辑验证关键技术研究
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable, Set
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ODDBoundaryType(Enum):
    """ODD边界类型"""
    PRESSURE = "pressure"               # 压力边界
    FLOW = "flow"                       # 流量边界
    SPEED = "speed"                     # 转速边界
    POWER = "power"                     # 功率边界
    WATER_LEVEL = "water_level"         # 水位边界
    TEMPERATURE = "temperature"          # 温度边界
    TRANSIENT = "transient"             # 瞬变边界
    CASCADE = "cascade"                 # 级联边界
    COORDINATION = "coordination"        # 协调边界


class ODDZone(Enum):
    """ODD运行区域"""
    OPTIMAL = "optimal"                 # 最优运行区
    NORMAL = "normal"                   # 正常运行区
    DEGRADED = "degraded"               # 降级运行区
    RESTRICTED = "restricted"            # 受限运行区
    EMERGENCY = "emergency"              # 应急运行区
    FORBIDDEN = "forbidden"              # 禁止区


class DegradationLevel(Enum):
    """降级等级"""
    L0_OPTIMAL = 0                      # 最优运行
    L1_NORMAL = 1                       # 正常运行
    L2_ALERT = 2                        # 预警
    L3_DEGRADED = 3                     # 降级运行
    L4_EMERGENCY = 4                    # 应急运行
    L5_SHUTDOWN = 5                     # 紧急停机


@dataclass
class BoundaryLimit:
    """边界限值"""
    name: str
    boundary_type: ODDBoundaryType
    unit: str

    # 限值定义
    optimal_min: float                   # 最优运行下限
    optimal_max: float                   # 最优运行上限
    normal_min: float                    # 正常运行下限
    normal_max: float                    # 正常运行上限
    degraded_min: float                  # 降级运行下限
    degraded_max: float                  # 降级运行上限
    emergency_min: float                 # 应急运行下限
    emergency_max: float                 # 应急运行上限
    absolute_min: float                  # 绝对下限（禁止区）
    absolute_max: float                  # 绝对上限（禁止区）

    # 变化率限制
    max_rise_rate: float = float('inf')  # 最大上升速率
    max_fall_rate: float = float('inf')  # 最大下降速率

    # 时间约束
    max_duration_in_degraded: float = 3600.0  # 降级区最大停留时间(s)
    max_duration_in_emergency: float = 300.0   # 应急区最大停留时间(s)

    def get_zone(self, value: float) -> ODDZone:
        """判断当前值所在区域"""
        if value < self.absolute_min or value > self.absolute_max:
            return ODDZone.FORBIDDEN
        elif value < self.emergency_min or value > self.emergency_max:
            return ODDZone.EMERGENCY
        elif value < self.degraded_min or value > self.degraded_max:
            return ODDZone.RESTRICTED
        elif value < self.normal_min or value > self.normal_max:
            return ODDZone.DEGRADED
        elif value < self.optimal_min or value > self.optimal_max:
            return ODDZone.NORMAL
        else:
            return ODDZone.OPTIMAL


@dataclass
class TransientBoundary:
    """瞬变边界"""
    name: str
    description: str

    # 多站同步动作约束
    max_simultaneous_actions: int = 2    # 最大同时动作站数
    min_action_interval: float = 5.0     # 最小动作间隔(s)
    max_guide_vane_rate: float = 0.1     # 导叶最大动作速率(pu/s)

    # 压力波叠加约束
    max_pressure_wave_amplitude: float = 0.3  # 最大压力波幅值(pu)
    max_pressure_gradient: float = 0.5   # 最大压力梯度(MPa/s)

    # 甩负荷约束
    max_load_rejection_rate: float = 0.5  # 最大甩负荷比例
    load_rejection_protection_delay: float = 0.5  # 保护动作延迟(s)

    # 调压设施工作区间
    surge_tank_min_level_ratio: float = 0.2  # 调压室最低水位比
    surge_tank_max_level_ratio: float = 0.9  # 调压室最高水位比


@dataclass
class CascadeBoundary:
    """级联降级边界"""
    name: str

    # 级联保护触发条件
    cascade_protection_enabled: bool = True
    max_cascade_depth: int = 3           # 最大级联深度

    # 降级序列优先级（稳压力优先）
    degradation_priority: List[str] = field(default_factory=lambda: [
        "maintain_pressure",             # 维持压力稳定
        "maintain_frequency",            # 维持频率稳定
        "maintain_power_balance",        # 维持功率平衡
        "minimize_equipment_stress",     # 减小设备应力
    ])

    # 恢复条件
    recovery_delay: float = 60.0         # 恢复延迟时间(s)
    recovery_rate: float = 0.1           # 恢复速率(pu/min)


@dataclass
class StationODD:
    """单站ODD配置"""
    station_id: str
    station_name: str

    # 水力边界
    pressure_boundary: BoundaryLimit = None
    flow_boundary: BoundaryLimit = None
    head_boundary: BoundaryLimit = None

    # 机电边界
    speed_boundary: BoundaryLimit = None
    power_boundary: BoundaryLimit = None
    voltage_boundary: BoundaryLimit = None

    # 温度边界
    temperature_boundary: BoundaryLimit = None

    # 运行约束
    min_operating_units: int = 1
    max_startup_per_hour: int = 4
    min_unit_online_time: float = 1800.0  # 最小开机时间(s)


@dataclass
class SystemODDState:
    """系统ODD状态"""
    timestamp: datetime
    overall_zone: ODDZone
    degradation_level: DegradationLevel

    # 各站状态
    station_zones: Dict[str, ODDZone] = field(default_factory=dict)

    # 边界状态
    boundary_violations: List[Dict[str, Any]] = field(default_factory=list)

    # 瞬变状态
    active_transients: List[str] = field(default_factory=list)

    # 级联状态
    cascade_active: bool = False
    cascade_depth: int = 0

    # 时间累计
    time_in_current_zone: float = 0.0


class SystemODD:
    """
    系统级设计运行域 (ODD)

    核心功能：
    1. 定义有压五梯级系统的运行边界
    2. 识别"单站合法但系统不可接受"的状态组合
    3. 支持系统级降级能力评估
    4. 提供ODD边界验证接口

    设计原则：
    - ODD边界是硬约束，MAS不能突破
    - 系统级ODD > 单站ODD
    - 支持从最优运行→安全运行→保底运行的有序退化
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # 梯级电站ODD配置
        self.stations: Dict[str, StationODD] = {}

        # 系统级边界
        self.system_boundaries: Dict[str, BoundaryLimit] = {}

        # 瞬变边界
        self.transient_boundary = TransientBoundary(
            name="系统瞬变边界",
            description="有压五梯级系统瞬变约束"
        )

        # 级联边界
        self.cascade_boundary = CascadeBoundary(name="级联降级边界")

        # 当前状态
        self.current_state = SystemODDState(
            timestamp=datetime.now(),
            overall_zone=ODDZone.NORMAL,
            degradation_level=DegradationLevel.L1_NORMAL
        )

        # 状态历史
        self.state_history: List[SystemODDState] = []

        # 违规记录
        self.violation_log: List[Dict[str, Any]] = []

        # 回调函数
        self.zone_change_callbacks: List[Callable] = []
        self.violation_callbacks: List[Callable] = []

        # 初始化默认配置
        self._init_default_boundaries()

    def _init_default_boundaries(self):
        """初始化默认的ODD边界（基于YX工程参数）"""

        # 系统级压力边界（有压引水系统）
        self.system_boundaries["system_pressure"] = BoundaryLimit(
            name="系统压力边界",
            boundary_type=ODDBoundaryType.PRESSURE,
            unit="MPa",
            optimal_min=4.5,
            optimal_max=5.0,
            normal_min=4.0,
            normal_max=5.5,
            degraded_min=3.5,
            degraded_max=6.0,
            emergency_min=3.0,
            emergency_max=6.5,
            absolute_min=0.0,            # 防止负压气蚀
            absolute_max=7.0,            # 防止超压
            max_rise_rate=0.5,           # MPa/s
            max_fall_rate=0.5,
        )

        # 系统级流量边界
        self.system_boundaries["system_flow"] = BoundaryLimit(
            name="系统流量边界",
            boundary_type=ODDBoundaryType.FLOW,
            unit="m³/s",
            optimal_min=800,
            optimal_max=1000,
            normal_min=600,
            normal_max=1100,
            degraded_min=400,
            degraded_max=1200,
            emergency_min=200,
            emergency_max=1300,
            absolute_min=0,
            absolute_max=1500,
            max_rise_rate=50,            # m³/s/s
            max_fall_rate=100,           # 甩负荷时允许快速下降
        )

        # 系统频率边界
        self.system_boundaries["system_frequency"] = BoundaryLimit(
            name="系统频率边界",
            boundary_type=ODDBoundaryType.SPEED,
            unit="Hz",
            optimal_min=49.95,
            optimal_max=50.05,
            normal_min=49.8,
            normal_max=50.2,
            degraded_min=49.5,
            degraded_max=50.5,
            emergency_min=48.0,
            emergency_max=52.0,
            absolute_min=45.0,
            absolute_max=55.0,
            max_rise_rate=0.5,           # Hz/s
            max_fall_rate=0.5,
        )

        # 调压室水位边界
        self.system_boundaries["surge_tank_level"] = BoundaryLimit(
            name="调压室水位边界",
            boundary_type=ODDBoundaryType.WATER_LEVEL,
            unit="m",
            optimal_min=60,
            optimal_max=100,
            normal_min=40,
            normal_max=110,
            degraded_min=30,
            degraded_max=115,
            emergency_min=20,
            emergency_max=118,
            absolute_min=10,             # 防止空气进入
            absolute_max=120,            # 防止溢出
            max_rise_rate=2.0,           # m/s
            max_fall_rate=2.0,
        )

    def add_station(self, station_odd: StationODD):
        """添加电站ODD配置"""
        self.stations[station_odd.station_id] = station_odd
        self.current_state.station_zones[station_odd.station_id] = ODDZone.NORMAL
        logger.info(f"添加电站ODD配置: {station_odd.station_name}")

    def configure_cascade_stations(self, stations_config: List[Dict[str, Any]]):
        """配置梯级电站组"""
        for config in stations_config:
            station_odd = StationODD(
                station_id=config["id"],
                station_name=config["name"],
                pressure_boundary=self._create_pressure_boundary(config),
                flow_boundary=self._create_flow_boundary(config),
                speed_boundary=self._create_speed_boundary(config),
                power_boundary=self._create_power_boundary(config),
            )
            self.add_station(station_odd)

    def _create_pressure_boundary(self, config: Dict) -> BoundaryLimit:
        """创建压力边界"""
        rated_head = config.get("rated_head", 480)
        rated_pressure = rated_head * 9.81 * 1000 / 1e6  # MPa

        return BoundaryLimit(
            name=f"{config['name']}压力边界",
            boundary_type=ODDBoundaryType.PRESSURE,
            unit="MPa",
            optimal_min=rated_pressure * 0.95,
            optimal_max=rated_pressure * 1.05,
            normal_min=rated_pressure * 0.90,
            normal_max=rated_pressure * 1.15,
            degraded_min=rated_pressure * 0.80,
            degraded_max=rated_pressure * 1.25,
            emergency_min=rated_pressure * 0.70,
            emergency_max=rated_pressure * 1.35,
            absolute_min=0,
            absolute_max=rated_pressure * 1.50,
        )

    def _create_flow_boundary(self, config: Dict) -> BoundaryLimit:
        """创建流量边界"""
        rated_flow = config.get("rated_flow", 210)
        num_units = config.get("num_units", 4)
        total_flow = rated_flow * num_units

        return BoundaryLimit(
            name=f"{config['name']}流量边界",
            boundary_type=ODDBoundaryType.FLOW,
            unit="m³/s",
            optimal_min=total_flow * 0.6,
            optimal_max=total_flow * 1.0,
            normal_min=total_flow * 0.3,
            normal_max=total_flow * 1.05,
            degraded_min=total_flow * 0.2,
            degraded_max=total_flow * 1.10,
            emergency_min=0,
            emergency_max=total_flow * 1.15,
            absolute_min=0,
            absolute_max=total_flow * 1.20,
        )

    def _create_speed_boundary(self, config: Dict) -> BoundaryLimit:
        """创建转速边界"""
        rated_speed = config.get("rated_speed", 166.7)

        return BoundaryLimit(
            name=f"{config['name']}转速边界",
            boundary_type=ODDBoundaryType.SPEED,
            unit="rpm",
            optimal_min=rated_speed * 0.995,
            optimal_max=rated_speed * 1.005,
            normal_min=rated_speed * 0.98,
            normal_max=rated_speed * 1.02,
            degraded_min=rated_speed * 0.95,
            degraded_max=rated_speed * 1.10,
            emergency_min=rated_speed * 0.90,
            emergency_max=rated_speed * 1.20,
            absolute_min=0,
            absolute_max=rated_speed * 1.80,  # 飞逸转速
        )

    def _create_power_boundary(self, config: Dict) -> BoundaryLimit:
        """创建功率边界"""
        rated_power = config.get("rated_power", 1000)
        num_units = config.get("num_units", 4)
        total_power = rated_power * num_units

        return BoundaryLimit(
            name=f"{config['name']}功率边界",
            boundary_type=ODDBoundaryType.POWER,
            unit="MW",
            optimal_min=total_power * 0.6,
            optimal_max=total_power * 1.0,
            normal_min=total_power * 0.3,
            normal_max=total_power * 1.0,
            degraded_min=total_power * 0.1,
            degraded_max=total_power * 1.0,
            emergency_min=0,
            emergency_max=total_power * 1.05,
            absolute_min=0,
            absolute_max=total_power * 1.10,
        )

    def evaluate_state(self, measurements: Dict[str, Dict[str, float]],
                       timestamp: datetime = None) -> SystemODDState:
        """
        评估当前系统ODD状态

        Args:
            measurements: 各站测量值 {station_id: {variable: value}}
            timestamp: 时间戳

        Returns:
            系统ODD状态
        """
        timestamp = timestamp or datetime.now()

        # 评估各站状态
        station_zones = {}
        boundary_violations = []
        worst_zone = ODDZone.OPTIMAL

        for station_id, values in measurements.items():
            if station_id not in self.stations:
                continue

            station_odd = self.stations[station_id]
            station_zone, violations = self._evaluate_station(station_odd, values)
            station_zones[station_id] = station_zone
            boundary_violations.extend(violations)

            # 更新最差区域
            if station_zone.value > worst_zone.value:
                worst_zone = station_zone

        # 评估系统级边界
        system_violations = self._evaluate_system_boundaries(measurements)
        boundary_violations.extend(system_violations)

        # 评估瞬变状态
        transient_violations = self._evaluate_transient_boundaries(measurements)
        boundary_violations.extend(transient_violations)

        # 确定系统级区域
        if system_violations:
            for v in system_violations:
                zone = v.get("zone", ODDZone.NORMAL)
                if zone.value > worst_zone.value:
                    worst_zone = zone

        # 确定降级等级
        degradation_level = self._zone_to_degradation(worst_zone)

        # 创建状态
        new_state = SystemODDState(
            timestamp=timestamp,
            overall_zone=worst_zone,
            degradation_level=degradation_level,
            station_zones=station_zones,
            boundary_violations=boundary_violations,
        )

        # 检测区域变化
        if new_state.overall_zone != self.current_state.overall_zone:
            self._on_zone_change(self.current_state.overall_zone, new_state.overall_zone)

        # 处理违规
        if boundary_violations:
            self._on_violation(boundary_violations)

        # 更新状态
        self.state_history.append(self.current_state)
        self.current_state = new_state

        return new_state

    def _evaluate_station(self, station_odd: StationODD,
                          values: Dict[str, float]) -> Tuple[ODDZone, List[Dict]]:
        """评估单站ODD状态"""
        worst_zone = ODDZone.OPTIMAL
        violations = []

        # 检查各边界
        boundary_checks = [
            ("pressure", station_odd.pressure_boundary, values.get("pressure")),
            ("flow", station_odd.flow_boundary, values.get("flow")),
            ("speed", station_odd.speed_boundary, values.get("speed")),
            ("power", station_odd.power_boundary, values.get("power")),
        ]

        for name, boundary, value in boundary_checks:
            if boundary is None or value is None:
                continue

            zone = boundary.get_zone(value)
            if zone.value > worst_zone.value:
                worst_zone = zone

            if zone != ODDZone.OPTIMAL:
                violations.append({
                    "station_id": station_odd.station_id,
                    "boundary": name,
                    "value": value,
                    "zone": zone,
                    "limits": {
                        "optimal": (boundary.optimal_min, boundary.optimal_max),
                        "normal": (boundary.normal_min, boundary.normal_max),
                    },
                })

        return worst_zone, violations

    def _evaluate_system_boundaries(self,
                                    measurements: Dict[str, Dict[str, float]]) -> List[Dict]:
        """评估系统级边界"""
        violations = []

        # 计算系统级指标
        total_pressure = 0
        total_flow = 0
        station_count = 0

        for station_id, values in measurements.items():
            if "pressure" in values:
                total_pressure += values["pressure"]
                station_count += 1
            if "flow" in values:
                total_flow += values["flow"]

        # 评估系统压力
        if station_count > 0:
            avg_pressure = total_pressure / station_count
            pressure_boundary = self.system_boundaries.get("system_pressure")
            if pressure_boundary:
                zone = pressure_boundary.get_zone(avg_pressure)
                if zone != ODDZone.OPTIMAL:
                    violations.append({
                        "boundary": "system_pressure",
                        "value": avg_pressure,
                        "zone": zone,
                        "type": "system_level",
                    })

        # 评估系统流量
        flow_boundary = self.system_boundaries.get("system_flow")
        if flow_boundary:
            zone = flow_boundary.get_zone(total_flow)
            if zone != ODDZone.OPTIMAL:
                violations.append({
                    "boundary": "system_flow",
                    "value": total_flow,
                    "zone": zone,
                    "type": "system_level",
                })

        return violations

    def _evaluate_transient_boundaries(self,
                                       measurements: Dict[str, Dict[str, float]]) -> List[Dict]:
        """评估瞬变边界"""
        violations = []

        # 检查压力变化率
        for station_id, values in measurements.items():
            pressure_rate = values.get("pressure_rate", 0)
            if abs(pressure_rate) > self.transient_boundary.max_pressure_gradient:
                violations.append({
                    "boundary": "pressure_gradient",
                    "station_id": station_id,
                    "value": pressure_rate,
                    "limit": self.transient_boundary.max_pressure_gradient,
                    "zone": ODDZone.RESTRICTED,
                    "type": "transient",
                })

        return violations

    def _zone_to_degradation(self, zone: ODDZone) -> DegradationLevel:
        """区域映射到降级等级"""
        mapping = {
            ODDZone.OPTIMAL: DegradationLevel.L0_OPTIMAL,
            ODDZone.NORMAL: DegradationLevel.L1_NORMAL,
            ODDZone.DEGRADED: DegradationLevel.L2_ALERT,
            ODDZone.RESTRICTED: DegradationLevel.L3_DEGRADED,
            ODDZone.EMERGENCY: DegradationLevel.L4_EMERGENCY,
            ODDZone.FORBIDDEN: DegradationLevel.L5_SHUTDOWN,
        }
        return mapping.get(zone, DegradationLevel.L1_NORMAL)

    def _on_zone_change(self, old_zone: ODDZone, new_zone: ODDZone):
        """区域变化回调"""
        logger.warning(f"ODD区域变化: {old_zone.value} -> {new_zone.value}")
        for callback in self.zone_change_callbacks:
            try:
                callback(old_zone, new_zone)
            except Exception as e:
                logger.error(f"区域变化回调执行失败: {e}")

    def _on_violation(self, violations: List[Dict]):
        """违规回调"""
        self.violation_log.extend(violations)
        for callback in self.violation_callbacks:
            try:
                callback(violations)
            except Exception as e:
                logger.error(f"违规回调执行失败: {e}")

    def check_action_allowed(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        """
        检查动作是否在ODD允许范围内

        Args:
            action: 动作描述

        Returns:
            (是否允许, 原因)
        """
        action_type = action.get("type", "")

        # 检查当前是否在禁止区
        if self.current_state.overall_zone == ODDZone.FORBIDDEN:
            return False, "系统处于禁止区，不允许常规操作"

        # 检查多站同步动作
        if action_type == "simultaneous_action":
            stations = action.get("stations", [])
            if len(stations) > self.transient_boundary.max_simultaneous_actions:
                return False, f"同时动作站数({len(stations)})超过限制({self.transient_boundary.max_simultaneous_actions})"

        # 检查导叶动作速率
        if action_type == "guide_vane_change":
            rate = action.get("rate", 0)
            if rate > self.transient_boundary.max_guide_vane_rate:
                return False, f"导叶动作速率({rate})超过限制"

        # 检查甩负荷
        if action_type == "load_rejection":
            rate = action.get("rate", 0)
            if rate > self.transient_boundary.max_load_rejection_rate:
                return False, f"甩负荷比例({rate})超过限制"

        return True, "动作在ODD允许范围内"

    def get_available_capacity(self) -> Dict[str, float]:
        """获取当前可用容量（基于ODD约束）"""
        capacity = {}

        for station_id, station_odd in self.stations.items():
            zone = self.current_state.station_zones.get(station_id, ODDZone.NORMAL)

            if zone == ODDZone.FORBIDDEN:
                capacity[station_id] = 0
            elif zone == ODDZone.EMERGENCY:
                # 应急模式下限制容量
                if station_odd.power_boundary:
                    capacity[station_id] = station_odd.power_boundary.emergency_max * 0.5
                else:
                    capacity[station_id] = 0
            elif zone in [ODDZone.DEGRADED, ODDZone.RESTRICTED]:
                # 降级模式下部分容量
                if station_odd.power_boundary:
                    capacity[station_id] = station_odd.power_boundary.degraded_max * 0.8
                else:
                    capacity[station_id] = 0
            else:
                # 正常/最优模式
                if station_odd.power_boundary:
                    capacity[station_id] = station_odd.power_boundary.normal_max
                else:
                    capacity[station_id] = 0

        return capacity

    def get_degradation_strategy(self) -> Dict[str, Any]:
        """获取当前降级策略"""
        level = self.current_state.degradation_level

        strategies = {
            DegradationLevel.L0_OPTIMAL: {
                "mode": "optimal",
                "description": "最优运行模式",
                "actions": ["经济优化调度", "全功能可用"],
            },
            DegradationLevel.L1_NORMAL: {
                "mode": "normal",
                "description": "正常运行模式",
                "actions": ["标准调度", "全功能可用"],
            },
            DegradationLevel.L2_ALERT: {
                "mode": "alert",
                "description": "预警模式",
                "actions": ["限制大幅度调整", "加强监控", "准备降级"],
            },
            DegradationLevel.L3_DEGRADED: {
                "mode": "degraded",
                "description": "降级运行模式",
                "actions": ["稳压力优先", "减少协同动作", "保守控制"],
            },
            DegradationLevel.L4_EMERGENCY: {
                "mode": "emergency",
                "description": "应急运行模式",
                "actions": ["最小化运行", "单站独立控制", "准备停机"],
            },
            DegradationLevel.L5_SHUTDOWN: {
                "mode": "shutdown",
                "description": "紧急停机模式",
                "actions": ["有序停机", "保护设备"],
            },
        }

        return strategies.get(level, strategies[DegradationLevel.L1_NORMAL])

    def export_odd_specification(self) -> Dict[str, Any]:
        """导出ODD规格文档"""
        spec = {
            "system": {
                "name": "YX工程有压五梯级系统ODD",
                "version": "1.0",
                "created": datetime.now().isoformat(),
            },
            "system_boundaries": {
                name: {
                    "type": boundary.boundary_type.value,
                    "unit": boundary.unit,
                    "optimal": (boundary.optimal_min, boundary.optimal_max),
                    "normal": (boundary.normal_min, boundary.normal_max),
                    "degraded": (boundary.degraded_min, boundary.degraded_max),
                    "emergency": (boundary.emergency_min, boundary.emergency_max),
                    "absolute": (boundary.absolute_min, boundary.absolute_max),
                }
                for name, boundary in self.system_boundaries.items()
            },
            "transient_boundaries": {
                "max_simultaneous_actions": self.transient_boundary.max_simultaneous_actions,
                "min_action_interval": self.transient_boundary.min_action_interval,
                "max_guide_vane_rate": self.transient_boundary.max_guide_vane_rate,
                "max_pressure_gradient": self.transient_boundary.max_pressure_gradient,
            },
            "cascade_boundaries": {
                "max_cascade_depth": self.cascade_boundary.max_cascade_depth,
                "degradation_priority": self.cascade_boundary.degradation_priority,
            },
            "stations": {
                station_id: {
                    "name": station.station_name,
                    "boundaries": {
                        "pressure": station.pressure_boundary is not None,
                        "flow": station.flow_boundary is not None,
                        "speed": station.speed_boundary is not None,
                        "power": station.power_boundary is not None,
                    }
                }
                for station_id, station in self.stations.items()
            },
        }

        return spec


class ODDValidator:
    """
    ODD验证器

    用于验证设计方案、运行策略是否满足ODD约束
    """

    def __init__(self, odd: SystemODD):
        self.odd = odd
        self.validation_results: List[Dict[str, Any]] = []

    def validate_design_scheme(self, scheme: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证设计方案是否满足ODD

        Args:
            scheme: 设计方案

        Returns:
            验证结果
        """
        results = {
            "scheme_id": scheme.get("id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "passed": True,
            "checks": [],
            "warnings": [],
            "errors": [],
        }

        # 检查压力设计裕度
        design_pressure = scheme.get("design_pressure", 0)
        pressure_boundary = self.odd.system_boundaries.get("system_pressure")
        if pressure_boundary:
            if design_pressure > pressure_boundary.absolute_max:
                results["passed"] = False
                results["errors"].append(f"设计压力({design_pressure}MPa)超过绝对上限")
            elif design_pressure > pressure_boundary.emergency_max:
                results["warnings"].append(f"设计压力({design_pressure}MPa)进入应急区间")
            results["checks"].append({
                "item": "压力设计",
                "value": design_pressure,
                "limit": pressure_boundary.normal_max,
                "passed": design_pressure <= pressure_boundary.normal_max,
            })

        # 检查调速参数
        governor_params = scheme.get("governor", {})
        kp = governor_params.get("kp", 0)
        ki = governor_params.get("ki", 0)

        # 检查是否可能导致系统振荡
        if kp > 5.0 or ki > 0.5:
            results["warnings"].append("调速参数可能导致系统级低频振荡风险")
            results["checks"].append({
                "item": "调速参数",
                "value": {"kp": kp, "ki": ki},
                "passed": False,
                "reason": "参数可能引起系统振荡",
            })

        self.validation_results.append(results)
        return results

    def validate_operation_scenario(self,
                                    scenario: Dict[str, Any],
                                    simulation_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        验证运行场景是否在ODD内

        Args:
            scenario: 运行场景
            simulation_results: 仿真结果（可选）

        Returns:
            验证结果
        """
        results = {
            "scenario_id": scenario.get("id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "passed": True,
            "odd_coverage": 0.0,
            "zone_distribution": {},
            "violations": [],
        }

        if simulation_results:
            # 分析仿真结果中的ODD状态
            time_series = simulation_results.get("time", [])
            states = simulation_results.get("states", [])

            zone_counts = {zone: 0 for zone in ODDZone}

            for i, state in enumerate(states):
                # 评估每个时刻的ODD状态
                odd_state = self.odd.evaluate_state(state)
                zone_counts[odd_state.overall_zone] += 1

                if odd_state.boundary_violations:
                    for v in odd_state.boundary_violations:
                        v["time"] = time_series[i] if i < len(time_series) else i
                        results["violations"].append(v)

            # 计算区域分布
            total = sum(zone_counts.values())
            if total > 0:
                results["zone_distribution"] = {
                    zone.value: count / total * 100
                    for zone, count in zone_counts.items()
                }

            # 计算ODD覆盖率（在正常区域内的时间比例）
            normal_time = zone_counts[ODDZone.OPTIMAL] + zone_counts[ODDZone.NORMAL]
            results["odd_coverage"] = normal_time / total * 100 if total > 0 else 0

            # 判断是否通过
            if zone_counts[ODDZone.FORBIDDEN] > 0:
                results["passed"] = False
                results["failure_reason"] = "进入禁止区域"
            elif results["odd_coverage"] < 80:
                results["passed"] = False
                results["failure_reason"] = "ODD覆盖率不足80%"

        self.validation_results.append(results)
        return results

    def generate_validation_report(self) -> str:
        """生成验证报告"""
        report = """
# ODD验证报告

## 验证概要

| 项目 | 结果 |
|------|------|
"""
        passed = sum(1 for r in self.validation_results if r.get("passed", False))
        total = len(self.validation_results)

        report += f"| 总验证数 | {total} |\n"
        report += f"| 通过数 | {passed} |\n"
        report += f"| 通过率 | {passed/total*100:.1f}% |\n"

        report += "\n## 详细结果\n\n"

        for result in self.validation_results:
            status = "[PASS]" if result.get("passed") else "[FAIL]"
            report += f"### {result.get('scheme_id', result.get('scenario_id', 'unknown'))} {status}\n\n"

            if result.get("errors"):
                report += "**错误:**\n"
                for error in result["errors"]:
                    report += f"- {error}\n"

            if result.get("warnings"):
                report += "**警告:**\n"
                for warning in result["warnings"]:
                    report += f"- {warning}\n"

            if result.get("odd_coverage"):
                report += f"**ODD覆盖率:** {result['odd_coverage']:.1f}%\n"

            report += "\n"

        return report


def create_yajiang_bigbend_odd() -> SystemODD:
    """
    创建雅鲁藏布江大拐弯工程系统ODD

    基于YX工程有压五梯级系统参数
    """
    odd = SystemODD()

    # 配置五个梯级电站
    cascade_stations = [
        {
            "id": "YJ01",
            "name": "墨脱水电站",
            "rated_head": 480,
            "rated_flow": 210,
            "rated_power": 1000,
            "rated_speed": 166.7,
            "num_units": 6,
        },
        {
            "id": "YJ02",
            "name": "多雄藏布水电站",
            "rated_head": 450,
            "rated_flow": 200,
            "rated_power": 800,
            "rated_speed": 166.7,
            "num_units": 4,
        },
        {
            "id": "YJ03",
            "name": "达木水电站",
            "rated_head": 400,
            "rated_flow": 180,
            "rated_power": 600,
            "rated_speed": 150,
            "num_units": 3,
        },
        {
            "id": "YJ04",
            "name": "巴玉水电站",
            "rated_head": 350,
            "rated_flow": 160,
            "rated_power": 500,
            "rated_speed": 150,
            "num_units": 3,
        },
        {
            "id": "YJ05",
            "name": "通德水电站",
            "rated_head": 300,
            "rated_flow": 150,
            "rated_power": 400,
            "rated_speed": 125,
            "num_units": 2,
        },
    ]

    odd.configure_cascade_stations(cascade_stations)

    # 配置系统级瞬变边界（针对有压系统特点）
    odd.transient_boundary = TransientBoundary(
        name="有压五梯级瞬变边界",
        description="考虑压力波传播、叠加与级联效应",
        max_simultaneous_actions=2,
        min_action_interval=10.0,      # 长引水系统需要更长间隔
        max_guide_vane_rate=0.05,      # 保守的导叶动作速率
        max_pressure_wave_amplitude=0.25,
        max_pressure_gradient=0.3,
        max_load_rejection_rate=0.3,   # 限制单次甩负荷比例
        surge_tank_min_level_ratio=0.25,
        surge_tank_max_level_ratio=0.85,
    )

    # 配置级联边界
    odd.cascade_boundary = CascadeBoundary(
        name="五梯级级联边界",
        max_cascade_depth=2,           # 最多允许2级级联
        degradation_priority=[
            "maintain_pressure",       # 稳压力优先
            "maintain_frequency",
            "maintain_power_balance",
            "minimize_cascade_effect",
        ],
        recovery_delay=120.0,          # 恢复需要较长稳定时间
        recovery_rate=0.05,
    )

    return odd
