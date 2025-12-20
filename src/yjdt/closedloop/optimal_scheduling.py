# -*- coding: utf-8 -*-
"""
优化调度 - 梯级电站群协同优化
Optimal Scheduling - Cascade Hydropower Coordinated Optimization

功能：
- 短期调度优化（日前/日内）
- 中长期调度（周/月/年）
- 多目标优化（发电/安全/环保）
- AGC/AVC协调
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
from enum import Enum


class SchedulingHorizon(Enum):
    """调度时域"""
    REALTIME = "realtime"        # 实时 (<5分钟)
    INTRADAY = "intraday"        # 日内 (5分钟-24小时)
    DAY_AHEAD = "day_ahead"      # 日前 (24-48小时)
    WEEK = "week"                # 周调度
    MONTH = "month"              # 月调度


class OptimizationObjective(Enum):
    """优化目标"""
    MAX_GENERATION = "max_generation"           # 最大发电量
    MAX_REVENUE = "max_revenue"                 # 最大收益
    MIN_SPILLAGE = "min_spillage"               # 最小弃水
    MIN_WATER_USE = "min_water_use"             # 最小用水
    MAX_EFFICIENCY = "max_efficiency"           # 最高效率
    LOAD_FOLLOWING = "load_following"           # 负荷跟踪
    FREQUENCY_REGULATION = "frequency_regulation"  # 调频服务
    MULTI_OBJECTIVE = "multi_objective"         # 多目标


@dataclass
class SchedulingConstraint:
    """调度约束"""
    constraint_id: str
    name: str
    constraint_type: str        # "equality" or "inequality"
    variable: str
    limit_type: str             # "min", "max", "equal"
    value: float
    unit: str = ""
    priority: int = 1           # 1=硬约束, 2=软约束


@dataclass
class UnitSchedule:
    """机组调度计划"""
    unit_id: str
    timestamps: List[datetime]
    power_setpoints: List[float]        # MW
    guide_vane_positions: List[float]   # %
    head_estimates: List[float]         # m
    efficiency_estimates: List[float]   # %
    status: List[str]                   # "running", "standby", "maintenance"


@dataclass
class CascadeSchedule:
    """梯级调度计划"""
    schedule_id: str
    horizon: SchedulingHorizon
    start_time: datetime
    end_time: datetime
    unit_schedules: Dict[str, UnitSchedule]
    total_power: List[float]            # 总出力
    cascade_efficiency: List[float]     # 梯级效率
    water_consumption: List[float]      # 耗水量
    revenue_estimate: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SchedulingResult:
    """调度优化结果"""
    success: bool
    schedule: Optional[CascadeSchedule]
    objective_value: float
    constraint_violations: List[str]
    solver_info: Dict[str, Any] = field(default_factory=dict)


class OptimalScheduler:
    """
    优化调度器

    功能：
    - 梯级电站协同优化
    - 多时间尺度调度
    - 多目标优化
    - 约束处理
    """

    def __init__(self):
        # 电站配置
        self.stations = {}
        self.units = {}

        # 约束集
        self.constraints: Dict[str, SchedulingConstraint] = {}

        # 价格信号
        self.price_forecast: Dict[datetime, float] = {}

        # 来水预测
        self.inflow_forecast: Dict[str, List[float]] = {}

        # 负荷预测
        self.load_forecast: List[float] = []

        # 初始化默认配置
        self._initialize_cascade()
        self._initialize_constraints()

    def _initialize_cascade(self):
        """初始化梯级配置"""
        # 雅江梯级电站群（简化配置）
        self.stations = {
            "yajiang_1": {
                "name": "雅江一级",
                "capacity": 3000,           # MW
                "units": 6,
                "unit_capacity": 500,       # MW
                "design_head": 500,         # m
                "min_head": 450,
                "max_head": 520,
                "reservoir_capacity": 1e9,  # m³
            },
            "yajiang_2": {
                "name": "雅江二级",
                "capacity": 2400,
                "units": 4,
                "unit_capacity": 600,
                "design_head": 400,
                "min_head": 360,
                "max_head": 420,
                "reservoir_capacity": 5e8,
            },
            "yajiang_3": {
                "name": "雅江三级",
                "capacity": 1800,
                "units": 3,
                "unit_capacity": 600,
                "design_head": 300,
                "min_head": 270,
                "max_head": 320,
                "reservoir_capacity": 3e8,
            },
        }

        # 初始化机组
        for station_id, station in self.stations.items():
            for i in range(station["units"]):
                unit_id = f"{station_id}_U{i+1}"
                self.units[unit_id] = {
                    "station": station_id,
                    "capacity": station["unit_capacity"],
                    "min_power": station["unit_capacity"] * 0.3,
                    "efficiency_curve": self._create_efficiency_curve(station["design_head"]),
                    "status": "available",
                    "maintenance_due": None,
                }

    def _create_efficiency_curve(self, design_head: float) -> Callable:
        """创建效率曲线"""
        def efficiency(power_ratio: float, head_ratio: float) -> float:
            # 简化的效率曲线
            base_eff = 0.92
            power_factor = 1 - 0.1 * (power_ratio - 0.8) ** 2
            head_factor = 1 - 0.05 * (head_ratio - 1.0) ** 2
            return base_eff * power_factor * head_factor
        return efficiency

    def _initialize_constraints(self):
        """初始化调度约束"""
        default_constraints = [
            # 系统约束
            SchedulingConstraint(
                "C001", "系统功率平衡", "equality",
                "total_power", "equal", 0, "MW", 1
            ),
            SchedulingConstraint(
                "C002", "旋转备用", "inequality",
                "spinning_reserve", "min", 300, "MW", 1
            ),

            # 水库约束
            SchedulingConstraint(
                "C003", "水库最低水位", "inequality",
                "water_level", "min", 0, "m", 1
            ),
            SchedulingConstraint(
                "C004", "水库最高水位", "inequality",
                "water_level", "max", 0, "m", 1
            ),

            # 生态约束
            SchedulingConstraint(
                "C005", "最小生态流量", "inequality",
                "eco_flow", "min", 50, "m³/s", 1
            ),

            # 机组约束
            SchedulingConstraint(
                "C006", "机组启停次数限制", "inequality",
                "start_stop_count", "max", 4, "次/天", 2
            ),

            # 电网约束
            SchedulingConstraint(
                "C007", "送出通道容量", "inequality",
                "transmission", "max", 6000, "MW", 1
            ),
        ]

        for constraint in default_constraints:
            self.constraints[constraint.constraint_id] = constraint

    def set_forecast(self, forecast_type: str, data: Any):
        """设置预测数据"""
        if forecast_type == "price":
            self.price_forecast = data
        elif forecast_type == "inflow":
            self.inflow_forecast = data
        elif forecast_type == "load":
            self.load_forecast = data

    def optimize(self,
                 horizon: SchedulingHorizon,
                 objective: OptimizationObjective,
                 start_time: datetime,
                 duration_hours: int,
                 initial_state: Dict[str, Any] = None) -> SchedulingResult:
        """
        执行调度优化

        Args:
            horizon: 调度时域
            objective: 优化目标
            start_time: 开始时间
            duration_hours: 持续时间（小时）
            initial_state: 初始状态
        """
        # 确定时间步长
        if horizon == SchedulingHorizon.REALTIME:
            dt_minutes = 5
        elif horizon == SchedulingHorizon.INTRADAY:
            dt_minutes = 15
        else:
            dt_minutes = 60

        n_steps = int(duration_hours * 60 / dt_minutes)

        # 生成时间序列
        timestamps = [
            start_time + timedelta(minutes=i*dt_minutes)
            for i in range(n_steps)
        ]

        # 优化求解
        if objective == OptimizationObjective.MAX_GENERATION:
            schedule = self._optimize_max_generation(timestamps, initial_state)
        elif objective == OptimizationObjective.MAX_REVENUE:
            schedule = self._optimize_max_revenue(timestamps, initial_state)
        elif objective == OptimizationObjective.LOAD_FOLLOWING:
            schedule = self._optimize_load_following(timestamps, initial_state)
        elif objective == OptimizationObjective.MULTI_OBJECTIVE:
            schedule = self._optimize_multi_objective(timestamps, initial_state)
        else:
            schedule = self._optimize_max_generation(timestamps, initial_state)

        # 检查约束
        violations = self._check_constraints(schedule)

        # 计算目标值
        obj_value = self._calculate_objective(schedule, objective)

        return SchedulingResult(
            success=len(violations) == 0,
            schedule=schedule,
            objective_value=obj_value,
            constraint_violations=violations,
            solver_info={
                "horizon": horizon.value,
                "objective": objective.value,
                "n_steps": n_steps,
                "solve_time": 0.5,
            }
        )

    def _optimize_max_generation(self, timestamps: List[datetime],
                                  initial_state: Dict = None) -> CascadeSchedule:
        """最大发电量优化"""
        n_steps = len(timestamps)
        unit_schedules = {}

        for unit_id, unit_info in self.units.items():
            if unit_info["status"] != "available":
                continue

            # 简化：满负荷运行
            capacity = unit_info["capacity"]
            station_id = unit_info["station"]
            station = self.stations[station_id]

            power_setpoints = [capacity] * n_steps
            gv_positions = [85.0] * n_steps  # 导叶开度
            head_estimates = [station["design_head"]] * n_steps
            efficiency_estimates = [0.92] * n_steps
            status = ["running"] * n_steps

            unit_schedules[unit_id] = UnitSchedule(
                unit_id=unit_id,
                timestamps=timestamps,
                power_setpoints=power_setpoints,
                guide_vane_positions=gv_positions,
                head_estimates=head_estimates,
                efficiency_estimates=efficiency_estimates,
                status=status,
            )

        # 计算总功率
        total_power = [0.0] * n_steps
        for unit_schedule in unit_schedules.values():
            for i in range(n_steps):
                total_power[i] += unit_schedule.power_setpoints[i]

        return CascadeSchedule(
            schedule_id=f"SCH_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            horizon=SchedulingHorizon.DAY_AHEAD,
            start_time=timestamps[0],
            end_time=timestamps[-1],
            unit_schedules=unit_schedules,
            total_power=total_power,
            cascade_efficiency=[0.90] * n_steps,
            water_consumption=[1000.0] * n_steps,
        )

    def _optimize_max_revenue(self, timestamps: List[datetime],
                               initial_state: Dict = None) -> CascadeSchedule:
        """最大收益优化"""
        n_steps = len(timestamps)
        unit_schedules = {}

        # 获取价格预测
        prices = []
        for ts in timestamps:
            price = self.price_forecast.get(ts, 0.5)  # 默认0.5元/kWh
            prices.append(price)

        # 价格排序，高价时段满发
        price_sorted_idx = np.argsort(prices)[::-1]

        for unit_id, unit_info in self.units.items():
            if unit_info["status"] != "available":
                continue

            capacity = unit_info["capacity"]
            min_power = unit_info["min_power"]
            station_id = unit_info["station"]
            station = self.stations[station_id]

            power_setpoints = [0.0] * n_steps

            # 高价时段优先满发
            high_price_hours = n_steps // 2  # 前50%高价时段满发
            for rank, idx in enumerate(price_sorted_idx):
                if rank < high_price_hours:
                    power_setpoints[idx] = capacity
                else:
                    power_setpoints[idx] = min_power

            gv_positions = [p / capacity * 100 for p in power_setpoints]
            head_estimates = [station["design_head"]] * n_steps
            efficiency_estimates = [0.90] * n_steps
            status = ["running" if p > 0 else "standby" for p in power_setpoints]

            unit_schedules[unit_id] = UnitSchedule(
                unit_id=unit_id,
                timestamps=timestamps,
                power_setpoints=power_setpoints,
                guide_vane_positions=gv_positions,
                head_estimates=head_estimates,
                efficiency_estimates=efficiency_estimates,
                status=status,
            )

        # 计算总功率和收益
        total_power = [0.0] * n_steps
        revenue = 0.0
        for unit_schedule in unit_schedules.values():
            for i in range(n_steps):
                total_power[i] += unit_schedule.power_setpoints[i]
                revenue += unit_schedule.power_setpoints[i] * prices[i] / 4  # 15分钟

        schedule = CascadeSchedule(
            schedule_id=f"SCH_REV_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            horizon=SchedulingHorizon.DAY_AHEAD,
            start_time=timestamps[0],
            end_time=timestamps[-1],
            unit_schedules=unit_schedules,
            total_power=total_power,
            cascade_efficiency=[0.90] * n_steps,
            water_consumption=[800.0] * n_steps,
            revenue_estimate=revenue,
        )

        return schedule

    def _optimize_load_following(self, timestamps: List[datetime],
                                  initial_state: Dict = None) -> CascadeSchedule:
        """负荷跟踪优化"""
        n_steps = len(timestamps)

        # 获取负荷预测
        if len(self.load_forecast) >= n_steps:
            target_load = self.load_forecast[:n_steps]
        else:
            # 模拟负荷曲线
            target_load = []
            for ts in timestamps:
                hour = ts.hour
                # 日负荷曲线
                base = 4000
                if 8 <= hour <= 11 or 18 <= hour <= 21:
                    load = base + 1500  # 高峰
                elif 0 <= hour <= 6:
                    load = base - 1000  # 低谷
                else:
                    load = base
                target_load.append(load)

        unit_schedules = {}

        # 按容量排序机组
        sorted_units = sorted(
            [(uid, info) for uid, info in self.units.items() if info["status"] == "available"],
            key=lambda x: x[1]["capacity"],
            reverse=True
        )

        for unit_id, unit_info in sorted_units:
            capacity = unit_info["capacity"]
            min_power = unit_info["min_power"]
            station_id = unit_info["station"]
            station = self.stations[station_id]

            power_setpoints = []

            for i in range(n_steps):
                remaining = target_load[i] - sum(
                    us.power_setpoints[i] for us in unit_schedules.values()
                )

                if remaining <= 0:
                    power = 0
                elif remaining >= capacity:
                    power = capacity
                elif remaining >= min_power:
                    power = remaining
                else:
                    power = 0

                power_setpoints.append(power)
                target_load[i] = max(0, target_load[i] - power)

            gv_positions = [p / capacity * 100 if p > 0 else 0 for p in power_setpoints]
            head_estimates = [station["design_head"]] * n_steps
            efficiency_estimates = [0.88 + 0.04 * (p / capacity) if p > 0 else 0
                                   for p in power_setpoints]
            status = ["running" if p > 0 else "standby" for p in power_setpoints]

            unit_schedules[unit_id] = UnitSchedule(
                unit_id=unit_id,
                timestamps=timestamps,
                power_setpoints=power_setpoints,
                guide_vane_positions=gv_positions,
                head_estimates=head_estimates,
                efficiency_estimates=efficiency_estimates,
                status=status,
            )

        # 计算总功率
        total_power = [0.0] * n_steps
        for unit_schedule in unit_schedules.values():
            for i in range(n_steps):
                total_power[i] += unit_schedule.power_setpoints[i]

        return CascadeSchedule(
            schedule_id=f"SCH_LF_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            horizon=SchedulingHorizon.INTRADAY,
            start_time=timestamps[0],
            end_time=timestamps[-1],
            unit_schedules=unit_schedules,
            total_power=total_power,
            cascade_efficiency=[0.89] * n_steps,
            water_consumption=[900.0] * n_steps,
        )

    def _optimize_multi_objective(self, timestamps: List[datetime],
                                   initial_state: Dict = None) -> CascadeSchedule:
        """多目标优化（帕累托前沿）"""
        # 简化实现：加权组合
        weights = {
            "generation": 0.4,
            "revenue": 0.3,
            "efficiency": 0.2,
            "reserve": 0.1,
        }

        # 首先获取最大发电方案
        gen_schedule = self._optimize_max_generation(timestamps, initial_state)

        # 然后获取最大收益方案
        rev_schedule = self._optimize_max_revenue(timestamps, initial_state)

        # 加权组合
        n_steps = len(timestamps)
        unit_schedules = {}

        for unit_id in gen_schedule.unit_schedules:
            gen_powers = gen_schedule.unit_schedules[unit_id].power_setpoints
            rev_powers = rev_schedule.unit_schedules[unit_id].power_setpoints

            # 加权平均
            combined_powers = [
                weights["generation"] * gen_powers[i] + weights["revenue"] * rev_powers[i]
                for i in range(n_steps)
            ]

            unit_info = self.units[unit_id]
            station = self.stations[unit_info["station"]]
            capacity = unit_info["capacity"]

            gv_positions = [p / capacity * 100 for p in combined_powers]

            unit_schedules[unit_id] = UnitSchedule(
                unit_id=unit_id,
                timestamps=timestamps,
                power_setpoints=combined_powers,
                guide_vane_positions=gv_positions,
                head_estimates=[station["design_head"]] * n_steps,
                efficiency_estimates=[0.90] * n_steps,
                status=["running"] * n_steps,
            )

        total_power = [0.0] * n_steps
        for unit_schedule in unit_schedules.values():
            for i in range(n_steps):
                total_power[i] += unit_schedule.power_setpoints[i]

        return CascadeSchedule(
            schedule_id=f"SCH_MO_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            horizon=SchedulingHorizon.DAY_AHEAD,
            start_time=timestamps[0],
            end_time=timestamps[-1],
            unit_schedules=unit_schedules,
            total_power=total_power,
            cascade_efficiency=[0.89] * n_steps,
            water_consumption=[850.0] * n_steps,
        )

    def _check_constraints(self, schedule: CascadeSchedule) -> List[str]:
        """检查约束违反"""
        violations = []

        # 检查送出容量
        for i, power in enumerate(schedule.total_power):
            if power > 6000:
                violations.append(f"时段{i}: 超送出容量 {power:.0f}MW > 6000MW")

        # 检查备用
        total_capacity = sum(
            self.units[uid]["capacity"]
            for uid in schedule.unit_schedules
            if self.units[uid]["status"] == "available"
        )
        for i, power in enumerate(schedule.total_power):
            reserve = total_capacity - power
            if reserve < 300:
                violations.append(f"时段{i}: 备用不足 {reserve:.0f}MW < 300MW")

        return violations

    def _calculate_objective(self, schedule: CascadeSchedule,
                             objective: OptimizationObjective) -> float:
        """计算目标函数值"""
        if objective == OptimizationObjective.MAX_GENERATION:
            return sum(schedule.total_power) / 4  # MWh（15分钟时段）

        elif objective == OptimizationObjective.MAX_REVENUE:
            return schedule.revenue_estimate

        elif objective == OptimizationObjective.MAX_EFFICIENCY:
            return np.mean(schedule.cascade_efficiency)

        else:
            return sum(schedule.total_power) / 4


class AGCController:
    """
    自动发电控制（AGC）

    功能：
    - 区域控制误差（ACE）调节
    - 机组功率分配
    - 调节速率限制
    """

    def __init__(self, scheduler: OptimalScheduler):
        self.scheduler = scheduler

        # AGC参数
        self.params = {
            "ace_deadband": 5.0,        # ACE死区 (MW)
            "kp": 0.5,                   # 比例增益
            "ki": 0.1,                   # 积分增益
            "rate_limit": 50,            # 调节速率限制 (MW/min)
        }

        # 状态
        self.ace_integral = 0.0
        self.last_command = {}

    def calculate_ace(self, frequency_deviation: float,
                      tie_line_deviation: float,
                      bias: float = 200) -> float:
        """
        计算区域控制误差

        ACE = ΔP_tie + B × Δf
        """
        return tie_line_deviation + bias * frequency_deviation

    def dispatch(self, ace: float, available_units: List[str]) -> Dict[str, float]:
        """
        AGC调度分配

        Args:
            ace: 区域控制误差
            available_units: 可调机组列表

        Returns:
            各机组功率调整量
        """
        if abs(ace) < self.params["ace_deadband"]:
            return {}

        # PI控制
        self.ace_integral += ace * 0.5  # 假设0.5秒周期
        self.ace_integral = np.clip(self.ace_integral, -1000, 1000)

        regulation = -(self.params["kp"] * ace + self.params["ki"] * self.ace_integral)

        # 分配给机组（按容量比例）
        adjustments = {}
        total_capacity = sum(
            self.scheduler.units[uid]["capacity"]
            for uid in available_units
        )

        for unit_id in available_units:
            capacity = self.scheduler.units[unit_id]["capacity"]
            ratio = capacity / total_capacity
            adjustment = regulation * ratio

            # 速率限制
            last = self.last_command.get(unit_id, 0)
            max_change = self.params["rate_limit"] / 60 * 0.5  # 每周期最大变化
            adjustment = np.clip(adjustment - last, -max_change, max_change) + last

            adjustments[unit_id] = adjustment
            self.last_command[unit_id] = adjustment

        return adjustments


class AVCController:
    """
    自动电压控制（AVC）

    功能：
    - 无功优化
    - 电压调节
    - 功率因数控制
    """

    def __init__(self):
        # AVC参数
        self.params = {
            "voltage_deadband": 0.02,   # 电压死区 (p.u.)
            "target_pf": 0.95,          # 目标功率因数
            "q_limit_ratio": 0.5,       # 无功限制比例
        }

        self.voltage_setpoints: Dict[str, float] = {}

    def calculate_reactive_power(self, unit_id: str, active_power: float,
                                  voltage_deviation: float) -> float:
        """
        计算无功功率指令

        Args:
            unit_id: 机组ID
            active_power: 有功功率
            voltage_deviation: 电压偏差
        """
        if abs(voltage_deviation) < self.params["voltage_deadband"]:
            # 按功率因数运行
            q = active_power * np.tan(np.arccos(self.params["target_pf"]))
        else:
            # 电压调节
            q_adjustment = -voltage_deviation * active_power * 0.5
            base_q = active_power * np.tan(np.arccos(self.params["target_pf"]))
            q = base_q + q_adjustment

        # 无功限制
        q_max = active_power * self.params["q_limit_ratio"]
        q = np.clip(q, -q_max, q_max)

        return q

    def optimize_voltage_profile(self, bus_voltages: Dict[str, float],
                                  generators: Dict[str, Dict]) -> Dict[str, float]:
        """
        优化电压分布

        Args:
            bus_voltages: 母线电压
            generators: 发电机信息

        Returns:
            各发电机无功功率指令
        """
        q_commands = {}

        for gen_id, gen_info in generators.items():
            bus_id = gen_info.get("bus", gen_id)
            voltage = bus_voltages.get(bus_id, 1.0)
            deviation = voltage - 1.0

            active_power = gen_info.get("p", 0)
            q = self.calculate_reactive_power(gen_id, active_power, deviation)
            q_commands[gen_id] = q

        return q_commands

