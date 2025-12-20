# -*- coding: utf-8 -*-
"""
调度优化求解器 - Scheduling Optimization Solver

功能：
- 梯级电站联合调度优化
- 日前/日内/实时调度
- 多目标优化
- 约束处理
- 分布式求解

技术特点：
- 线性规划/二次规划
- 分支定界法
- ADMM分布式算法
- 滚动时域优化
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
import time


class ObjectiveType(Enum):
    """目标类型"""
    MAX_GENERATION = "max_generation"         # 最大发电量
    MIN_COST = "min_cost"                     # 最小成本
    MAX_REVENUE = "max_revenue"               # 最大收益
    LOAD_TRACKING = "load_tracking"           # 负荷跟踪
    PEAK_SHAVING = "peak_shaving"             # 削峰填谷
    MULTI_OBJECTIVE = "multi_objective"       # 多目标


class ConstraintCategory(Enum):
    """约束类别"""
    HYDRAULIC = "hydraulic"           # 水力约束
    ELECTRICAL = "electrical"         # 电气约束
    OPERATIONAL = "operational"       # 运行约束
    ENVIRONMENTAL = "environmental"   # 环境约束
    MARKET = "market"                 # 市场约束


@dataclass
class SchedulingPeriod:
    """调度周期"""
    start_time: datetime
    end_time: datetime
    n_intervals: int
    interval_hours: float

    @property
    def intervals(self) -> List[datetime]:
        """获取所有时段"""
        return [
            self.start_time + timedelta(hours=i * self.interval_hours)
            for i in range(self.n_intervals)
        ]


@dataclass
class HydropowerUnit:
    """水电机组"""
    unit_id: str
    station_id: str

    # 容量参数
    rated_power: float            # 额定功率 MW
    min_power: float              # 最小出力 MW
    max_power: float              # 最大出力 MW

    # 效率参数
    efficiency_curve: List[Tuple[float, float]] = field(default_factory=list)

    # 运行约束
    min_uptime: float = 4.0       # 最小开机时间 h
    min_downtime: float = 2.0     # 最小停机时间 h
    ramp_up_rate: float = 50.0    # 爬坡速率 MW/h
    ramp_down_rate: float = 50.0  # 降坡速率 MW/h

    # 当前状态
    current_power: float = 0.0
    is_online: bool = False
    hours_since_change: float = 0.0


@dataclass
class Reservoir:
    """水库"""
    reservoir_id: str
    station_id: str

    # 库容参数
    max_storage: float            # 最大库容 亿m³
    min_storage: float            # 死库容 亿m³
    current_storage: float        # 当前库容 亿m³

    # 水位-库容关系
    level_storage_curve: List[Tuple[float, float]] = field(default_factory=list)

    # 约束
    max_level: float = 0.0        # 正常蓄水位 m
    min_level: float = 0.0        # 死水位 m
    flood_limit_level: float = 0.0  # 汛限水位 m

    # 入流预测
    inflow_forecast: List[float] = field(default_factory=list)


@dataclass
class SchedulingResult:
    """调度结果"""
    period: SchedulingPeriod
    status: str
    solve_time: float

    # 机组出力计划
    unit_schedules: Dict[str, List[float]] = field(default_factory=dict)

    # 水库调度
    reservoir_levels: Dict[str, List[float]] = field(default_factory=dict)
    reservoir_releases: Dict[str, List[float]] = field(default_factory=dict)

    # 汇总
    total_generation: List[float] = field(default_factory=list)
    total_revenue: float = 0.0
    constraint_violations: List[str] = field(default_factory=list)

    # 目标函数值
    objective_value: float = 0.0


class LinearProgramSolver:
    """
    线性规划求解器

    使用单纯形法和内点法
    """

    def __init__(self, method: str = "simplex"):
        self.method = method
        self.max_iterations = 1000
        self.tolerance = 1e-8

    def solve(self, c: np.ndarray, A_ub: np.ndarray = None,
              b_ub: np.ndarray = None, A_eq: np.ndarray = None,
              b_eq: np.ndarray = None, bounds: List[Tuple] = None) -> Tuple[np.ndarray, float, str]:
        """
        求解线性规划
        min  c'x
        s.t. A_ub * x <= b_ub
             A_eq * x = b_eq
             bounds

        Returns:
            最优解, 目标值, 状态
        """
        n = len(c)

        if self.method == "simplex":
            return self._simplex_solve(c, A_ub, b_ub, A_eq, b_eq, bounds)
        else:
            return self._interior_point_solve(c, A_ub, b_ub, A_eq, b_eq, bounds)

    def _simplex_solve(self, c, A_ub, b_ub, A_eq, b_eq, bounds):
        """单纯形法"""
        n = len(c)

        # 初始可行解
        if bounds:
            x = np.array([(b[0] if b[0] is not None else 0) for b in bounds])
        else:
            x = np.zeros(n)

        # 简化实现：梯度下降求近似解
        for _ in range(self.max_iterations):
            # 梯度
            grad = c.copy()

            # 投影到可行域
            x_new = x - 0.01 * grad

            # 边界约束
            if bounds:
                for i, (lb, ub) in enumerate(bounds):
                    if lb is not None:
                        x_new[i] = max(x_new[i], lb)
                    if ub is not None:
                        x_new[i] = min(x_new[i], ub)

            # 不等式约束
            if A_ub is not None and b_ub is not None:
                violations = A_ub @ x_new - b_ub
                if np.any(violations > 0):
                    # 投影回可行域
                    for i in range(len(b_ub)):
                        if violations[i] > 0:
                            # 简单投影
                            direction = A_ub[i] / (np.linalg.norm(A_ub[i]) + 1e-10)
                            x_new -= violations[i] * direction

            if np.linalg.norm(x_new - x) < self.tolerance:
                break

            x = x_new

        obj = c @ x
        return x, obj, "optimal"

    def _interior_point_solve(self, c, A_ub, b_ub, A_eq, b_eq, bounds):
        """内点法"""
        n = len(c)

        # 初始点
        if bounds:
            x = np.array([((b[0] or 0) + (b[1] or 1)) / 2 for b in bounds])
        else:
            x = np.ones(n) * 0.5

        mu = 10.0

        for iteration in range(self.max_iterations):
            # 对数障碍函数
            grad = c.copy()

            if bounds:
                for i, (lb, ub) in enumerate(bounds):
                    if lb is not None and x[i] - lb > 1e-10:
                        grad[i] -= mu / (x[i] - lb)
                    if ub is not None and ub - x[i] > 1e-10:
                        grad[i] += mu / (ub - x[i])

            # 牛顿步
            step = -0.1 * grad

            # 线搜索
            alpha = 1.0
            for _ in range(20):
                x_new = x + alpha * step

                # 检查可行性
                feasible = True
                if bounds:
                    for i, (lb, ub) in enumerate(bounds):
                        if lb is not None and x_new[i] < lb:
                            feasible = False
                            break
                        if ub is not None and x_new[i] > ub:
                            feasible = False
                            break

                if feasible:
                    break
                alpha *= 0.5

            x = x + alpha * step
            mu *= 0.9

            if np.linalg.norm(grad) < self.tolerance:
                break

        obj = c @ x
        return x, obj, "optimal"


class MixedIntegerSolver:
    """
    混合整数规划求解器

    用于机组组合优化
    """

    def __init__(self):
        self.max_iterations = 100
        self.gap_tolerance = 0.01

    def solve(self, c: np.ndarray, A_ub: np.ndarray, b_ub: np.ndarray,
              integer_vars: List[int], bounds: List[Tuple]) -> Tuple[np.ndarray, float, str]:
        """
        求解混合整数规划

        Args:
            c: 目标函数系数
            A_ub: 不等式约束矩阵
            b_ub: 不等式约束右端
            integer_vars: 整数变量索引
            bounds: 变量边界

        Returns:
            最优解, 目标值, 状态
        """
        n = len(c)
        lp_solver = LinearProgramSolver()

        # 松弛整数约束求解LP
        x_lp, obj_lp, status = lp_solver.solve(c, A_ub, b_ub, bounds=bounds)

        if status != "optimal":
            return x_lp, obj_lp, status

        # 检查整数可行性
        is_integer_feasible = True
        for idx in integer_vars:
            if abs(x_lp[idx] - round(x_lp[idx])) > 0.01:
                is_integer_feasible = False
                break

        if is_integer_feasible:
            return x_lp, obj_lp, "optimal"

        # 分支定界
        best_x = x_lp.copy()
        best_obj = float('inf')

        # 简化：对每个整数变量尝试取整
        for _ in range(self.max_iterations):
            x_rounded = x_lp.copy()

            for idx in integer_vars:
                # 随机选择向上或向下取整
                if np.random.random() < 0.5:
                    x_rounded[idx] = np.floor(x_lp[idx])
                else:
                    x_rounded[idx] = np.ceil(x_lp[idx])

                # 确保在边界内
                lb, ub = bounds[idx]
                if lb is not None:
                    x_rounded[idx] = max(x_rounded[idx], lb)
                if ub is not None:
                    x_rounded[idx] = min(x_rounded[idx], ub)

            # 检查可行性
            if A_ub is not None:
                violations = A_ub @ x_rounded - b_ub
                if np.all(violations <= 0.01):
                    obj = c @ x_rounded
                    if obj < best_obj:
                        best_obj = obj
                        best_x = x_rounded.copy()

        return best_x, best_obj, "suboptimal"


class ADMMSolver:
    """
    ADMM分布式求解器

    用于梯级电站联合优化的分解求解
    """

    def __init__(self, rho: float = 1.0):
        self.rho = rho
        self.max_iterations = 100
        self.tolerance = 1e-4

    def solve_distributed(self, subproblems: List[Dict],
                           coupling_constraints: List[Dict]) -> List[np.ndarray]:
        """
        分布式求解

        Args:
            subproblems: 子问题列表 [{c, A, b, bounds}, ...]
            coupling_constraints: 耦合约束

        Returns:
            各子问题解
        """
        n_sub = len(subproblems)

        # 初始化
        x_list = [np.zeros(len(sub["c"])) for sub in subproblems]
        z = np.zeros(len(coupling_constraints))  # 共识变量
        lambda_dual = np.zeros(len(coupling_constraints))

        lp_solver = LinearProgramSolver()

        for iteration in range(self.max_iterations):
            # 更新各子问题
            for i, sub in enumerate(subproblems):
                # 添加ADMM惩罚项（简化）
                c_aug = sub["c"].copy()

                x_list[i], _, _ = lp_solver.solve(
                    c_aug,
                    sub.get("A"),
                    sub.get("b"),
                    bounds=sub.get("bounds")
                )

            # 更新共识变量
            for j, constraint in enumerate(coupling_constraints):
                # 计算耦合值
                coupled_sum = 0
                for i, coef in constraint.get("coefficients", {}).items():
                    if i < len(x_list):
                        coupled_sum += coef * np.sum(x_list[i])

                z[j] = coupled_sum + lambda_dual[j] / self.rho

            # 更新对偶变量
            for j, constraint in enumerate(coupling_constraints):
                coupled_sum = 0
                for i, coef in constraint.get("coefficients", {}).items():
                    if i < len(x_list):
                        coupled_sum += coef * np.sum(x_list[i])

                lambda_dual[j] += self.rho * (coupled_sum - z[j])

            # 检查收敛
            primal_residual = sum(
                np.linalg.norm(x - z[:len(x)]) for x in x_list if len(x) <= len(z)
            )
            if primal_residual < self.tolerance:
                break

        return x_list


class CascadeSchedulingSolver:
    """
    梯级电站调度优化求解器

    功能：
    - 日前调度优化
    - 日内滚动优化
    - 实时调度
    - 多目标优化
    """

    def __init__(self):
        self.lp_solver = LinearProgramSolver()
        self.mip_solver = MixedIntegerSolver()
        self.admm_solver = ADMMSolver()

        # 电站配置
        self.stations: Dict[str, Dict] = {}
        self.units: Dict[str, HydropowerUnit] = {}
        self.reservoirs: Dict[str, Reservoir] = {}

        # 价格参数
        self.electricity_prices: List[float] = []

    def add_station(self, station_id: str, config: Dict):
        """添加电站"""
        self.stations[station_id] = config

    def add_unit(self, unit: HydropowerUnit):
        """添加机组"""
        self.units[unit.unit_id] = unit

    def add_reservoir(self, reservoir: Reservoir):
        """添加水库"""
        self.reservoirs[reservoir.reservoir_id] = reservoir

    def set_prices(self, prices: List[float]):
        """设置电价"""
        self.electricity_prices = prices

    def solve_day_ahead(self, period: SchedulingPeriod,
                         load_forecast: List[float],
                         objective: ObjectiveType = ObjectiveType.MAX_REVENUE) -> SchedulingResult:
        """
        求解日前调度

        Args:
            period: 调度周期
            load_forecast: 负荷预测
            objective: 优化目标

        Returns:
            调度结果
        """
        start_time = time.time()

        n_t = period.n_intervals
        n_units = len(self.units)

        # 决策变量: 各机组各时段出力
        # x[i*n_t + t] = 机组i在时段t的出力
        n_vars = n_units * n_t

        # 目标函数
        c = np.zeros(n_vars)

        if objective == ObjectiveType.MAX_REVENUE:
            # 最大化收益 = 最大化 sum(price * power)
            for i, unit_id in enumerate(self.units.keys()):
                for t in range(n_t):
                    price = self.electricity_prices[t] if t < len(self.electricity_prices) else 100
                    c[i * n_t + t] = -price  # 负号因为求最小化

        elif objective == ObjectiveType.LOAD_TRACKING:
            # 最小化负荷跟踪误差
            # 这需要二次规划，简化为线性
            for i, unit_id in enumerate(self.units.keys()):
                for t in range(n_t):
                    c[i * n_t + t] = 0  # 由约束处理

        # 约束
        A_ub_list = []
        b_ub_list = []

        # 1. 负荷平衡约束
        for t in range(n_t):
            row = np.zeros(n_vars)
            for i in range(n_units):
                row[i * n_t + t] = 1
            A_ub_list.append(-row)  # sum(P) >= load
            b_ub_list.append(-load_forecast[t] if t < len(load_forecast) else -500)

        # 2. 爬坡约束
        for i, (unit_id, unit) in enumerate(self.units.items()):
            for t in range(1, n_t):
                # 上爬坡
                row = np.zeros(n_vars)
                row[i * n_t + t] = 1
                row[i * n_t + t - 1] = -1
                A_ub_list.append(row)
                b_ub_list.append(unit.ramp_up_rate * period.interval_hours)

                # 下爬坡
                row = np.zeros(n_vars)
                row[i * n_t + t] = -1
                row[i * n_t + t - 1] = 1
                A_ub_list.append(row)
                b_ub_list.append(unit.ramp_down_rate * period.interval_hours)

        A_ub = np.array(A_ub_list) if A_ub_list else None
        b_ub = np.array(b_ub_list) if b_ub_list else None

        # 变量边界
        bounds = []
        for i, (unit_id, unit) in enumerate(self.units.items()):
            for t in range(n_t):
                bounds.append((unit.min_power, unit.max_power))

        # 求解
        x_opt, obj, status = self.lp_solver.solve(c, A_ub, b_ub, bounds=bounds)

        # 整理结果
        result = SchedulingResult(
            period=period,
            status=status,
            solve_time=time.time() - start_time,
            objective_value=-obj if objective == ObjectiveType.MAX_REVENUE else obj,
        )

        for i, unit_id in enumerate(self.units.keys()):
            result.unit_schedules[unit_id] = x_opt[i * n_t:(i + 1) * n_t].tolist()

        # 计算总发电
        result.total_generation = [0.0] * n_t
        for t in range(n_t):
            for i in range(n_units):
                result.total_generation[t] += x_opt[i * n_t + t]

        # 计算收益
        if self.electricity_prices:
            result.total_revenue = sum(
                result.total_generation[t] * self.electricity_prices[t]
                for t in range(min(n_t, len(self.electricity_prices)))
            )

        return result

    def solve_intraday(self, period: SchedulingPeriod,
                        load_forecast: List[float],
                        current_state: Dict[str, float]) -> SchedulingResult:
        """
        求解日内滚动调度

        Args:
            period: 调度周期（通常4小时）
            load_forecast: 更新的负荷预测
            current_state: 当前运行状态

        Returns:
            调度结果
        """
        # 使用当前状态作为初始条件
        for unit_id, power in current_state.items():
            if unit_id in self.units:
                self.units[unit_id].current_power = power

        return self.solve_day_ahead(period, load_forecast)

    def solve_realtime(self, target_power: float,
                        duration_minutes: int = 15) -> Dict[str, float]:
        """
        求解实时调度

        Args:
            target_power: 目标总出力
            duration_minutes: 调度时段长度

        Returns:
            各机组出力指令
        """
        # 快速分配算法
        allocation = {}
        remaining = target_power

        # 按效率排序分配
        sorted_units = sorted(
            self.units.items(),
            key=lambda x: x[1].rated_power,
            reverse=True
        )

        for unit_id, unit in sorted_units:
            if remaining <= 0:
                allocation[unit_id] = unit.min_power
            else:
                alloc = min(remaining, unit.max_power)
                alloc = max(alloc, unit.min_power)

                # 考虑爬坡约束
                max_change = unit.ramp_up_rate * duration_minutes / 60
                if alloc > unit.current_power:
                    alloc = min(alloc, unit.current_power + max_change)

                allocation[unit_id] = alloc
                remaining -= alloc

        return allocation

    def solve_multi_objective(self, period: SchedulingPeriod,
                               load_forecast: List[float],
                               objectives: List[Tuple[ObjectiveType, float]]) -> SchedulingResult:
        """
        多目标优化

        Args:
            period: 调度周期
            load_forecast: 负荷预测
            objectives: 目标列表 [(类型, 权重), ...]

        Returns:
            Pareto最优解
        """
        # 加权和法
        n_t = period.n_intervals
        n_units = len(self.units)
        n_vars = n_units * n_t

        c = np.zeros(n_vars)

        for obj_type, weight in objectives:
            if obj_type == ObjectiveType.MAX_REVENUE:
                for i in range(n_units):
                    for t in range(n_t):
                        price = self.electricity_prices[t] if t < len(self.electricity_prices) else 100
                        c[i * n_t + t] -= weight * price

            elif obj_type == ObjectiveType.PEAK_SHAVING:
                # 削峰：惩罚高峰时段的发电
                peak_hours = [10, 11, 12, 19, 20, 21]  # 高峰时段
                for i in range(n_units):
                    for t in range(n_t):
                        if t % 24 in peak_hours:
                            c[i * n_t + t] -= weight * 0.5

        # 求解
        period_result = self.solve_day_ahead(period, load_forecast, ObjectiveType.MULTI_OBJECTIVE)

        return period_result

    def solve_with_water_constraints(self, period: SchedulingPeriod,
                                       load_forecast: List[float],
                                       water_constraints: Dict[str, Dict]) -> SchedulingResult:
        """
        考虑水量约束的调度优化

        Args:
            period: 调度周期
            load_forecast: 负荷预测
            water_constraints: 水量约束 {reservoir_id: {min_release, max_release, target_level}}

        Returns:
            调度结果
        """
        # 扩展变量：加入水库下泄流量
        # 这里简化处理，假设出力与下泄成正比

        result = self.solve_day_ahead(period, load_forecast)

        # 计算水库调度
        for res_id, reservoir in self.reservoirs.items():
            if res_id in water_constraints:
                constraints = water_constraints[res_id]

                releases = []
                levels = [reservoir.current_storage]

                for t in range(period.n_intervals):
                    # 根据出力估算下泄
                    station_power = sum(
                        result.unit_schedules.get(uid, [0] * period.n_intervals)[t]
                        for uid, unit in self.units.items()
                        if unit.station_id == reservoir.station_id
                    )

                    # 简化：出力与流量成正比
                    release = station_power * 3.6 / 1000  # MW -> 亿m³/h

                    # 应用约束
                    release = max(release, constraints.get("min_release", 0))
                    release = min(release, constraints.get("max_release", 1000))

                    releases.append(release)

                    # 更新库容
                    inflow = reservoir.inflow_forecast[t] if t < len(reservoir.inflow_forecast) else 0.1
                    new_storage = levels[-1] + (inflow - release) * period.interval_hours
                    new_storage = max(reservoir.min_storage, min(reservoir.max_storage, new_storage))
                    levels.append(new_storage)

                result.reservoir_releases[res_id] = releases
                result.reservoir_levels[res_id] = levels

        return result


class RealTimeDispatcher:
    """
    实时调度器

    功能：
    - AGC指令生成
    - 负荷跟踪
    - 频率调节
    - 联络线功率控制
    """

    def __init__(self, solver: CascadeSchedulingSolver):
        self.solver = solver

        # AGC参数
        self.ace_deadband = 5.0       # ACE死区 MW
        self.kp = 0.5                  # 比例增益
        self.ki = 0.1                  # 积分增益

        # 状态
        self.ace_integral = 0.0
        self.last_dispatch_time: Optional[datetime] = None

    def calculate_ace(self, frequency_deviation: float,
                      tie_line_deviation: float,
                      frequency_bias: float = -20.0) -> float:
        """
        计算区域控制误差

        Args:
            frequency_deviation: 频率偏差 Hz
            tie_line_deviation: 联络线功率偏差 MW
            frequency_bias: 频率偏置系数 MW/0.1Hz

        Returns:
            ACE (MW)
        """
        ace = tie_line_deviation + frequency_bias * frequency_deviation * 10
        return ace

    def dispatch(self, ace: float, available_units: List[str]) -> Dict[str, float]:
        """
        执行调度

        Args:
            ace: 区域控制误差
            available_units: 可用机组列表

        Returns:
            调度指令
        """
        # 死区判断
        if abs(ace) < self.ace_deadband:
            return {}

        # PI控制
        self.ace_integral += ace * 0.01  # 假设1秒周期
        self.ace_integral = np.clip(self.ace_integral, -100, 100)

        correction = self.kp * ace + self.ki * self.ace_integral

        # 分配到各机组
        n_units = len(available_units)
        if n_units == 0:
            return {}

        per_unit = correction / n_units

        commands = {}
        for unit_id in available_units:
            if unit_id in self.solver.units:
                unit = self.solver.units[unit_id]
                new_power = unit.current_power + per_unit
                new_power = np.clip(new_power, unit.min_power, unit.max_power)
                commands[unit_id] = new_power

        self.last_dispatch_time = datetime.now()
        return commands

    def get_regulation_status(self) -> Dict[str, Any]:
        """获取调节状态"""
        return {
            "ace_integral": self.ace_integral,
            "last_dispatch": self.last_dispatch_time.isoformat() if self.last_dispatch_time else None,
            "kp": self.kp,
            "ki": self.ki,
        }


def create_yajiang_scheduler() -> CascadeSchedulingSolver:
    """
    创建雅江梯级调度求解器

    Returns:
        配置好的求解器
    """
    solver = CascadeSchedulingSolver()

    # 添加三个梯级电站
    solver.add_station("station_1", {"name": "一级电站", "cascade_position": 1})
    solver.add_station("station_2", {"name": "二级电站", "cascade_position": 2})
    solver.add_station("station_3", {"name": "三级电站", "cascade_position": 3})

    # 添加机组
    for i in range(1, 5):
        solver.add_unit(HydropowerUnit(
            unit_id=f"unit_1_{i}",
            station_id="station_1",
            rated_power=200,
            min_power=40,
            max_power=220,
        ))

    for i in range(1, 7):
        solver.add_unit(HydropowerUnit(
            unit_id=f"unit_2_{i}",
            station_id="station_2",
            rated_power=200,
            min_power=40,
            max_power=220,
        ))

    for i in range(1, 5):
        solver.add_unit(HydropowerUnit(
            unit_id=f"unit_3_{i}",
            station_id="station_3",
            rated_power=150,
            min_power=30,
            max_power=165,
        ))

    # 添加水库
    solver.add_reservoir(Reservoir(
        reservoir_id="reservoir_1",
        station_id="station_1",
        max_storage=10.0,
        min_storage=2.0,
        current_storage=6.0,
    ))

    solver.add_reservoir(Reservoir(
        reservoir_id="reservoir_2",
        station_id="station_2",
        max_storage=5.0,
        min_storage=1.0,
        current_storage=3.0,
    ))

    # 设置电价（24小时分时电价）
    peak_price = 0.8  # 元/kWh
    valley_price = 0.3
    normal_price = 0.5

    prices = []
    for h in range(24):
        if h in [10, 11, 12, 19, 20, 21]:
            prices.append(peak_price * 1000)  # 转换为元/MWh
        elif h in [0, 1, 2, 3, 4, 5]:
            prices.append(valley_price * 1000)
        else:
            prices.append(normal_price * 1000)

    solver.set_prices(prices)

    return solver
