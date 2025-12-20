"""
协调控制模块
Coordination Control Module

实现多机组、多电站之间的协调控制功能
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from scipy.optimize import minimize, linprog


class DispatchMode(Enum):
    """调度模式"""
    EQUAL_DISTRIBUTION = "equal"         # 均分负荷
    OPTIMAL_EFFICIENCY = "efficiency"     # 效率最优
    WATER_LEVEL = "water_level"          # 水位控制
    PEAK_REGULATION = "peak"             # 调峰
    FREQUENCY_REGULATION = "frequency"    # 调频
    RESERVE = "reserve"                  # 备用


@dataclass
class UnitState:
    """机组状态"""
    unit_id: str
    is_online: bool = False
    power: float = 0.0          # 当前功率 (MW)
    capacity: float = 1000.0    # 装机容量 (MW)
    min_power: float = 100.0    # 最小技术出力 (MW)
    max_power: float = 1000.0   # 最大出力 (MW)
    ramp_up: float = 50.0       # 上升速率 (MW/min)
    ramp_down: float = 60.0     # 下降速率 (MW/min)
    efficiency: float = 0.94    # 效率
    cost: float = 0.0           # 发电成本 (元/MWh)
    vibration_zone: List[Tuple[float, float]] = field(default_factory=list)  # 振动区


@dataclass
class ReservoirState:
    """水库状态"""
    reservoir_id: str
    level: float = 0.0          # 当前水位 (m)
    max_level: float = 100.0    # 最高水位 (m)
    min_level: float = 50.0     # 最低水位 (m)
    target_level: float = 80.0  # 目标水位 (m)
    inflow: float = 0.0         # 来水流量 (m³/s)
    outflow: float = 0.0        # 出库流量 (m³/s)
    volume: float = 0.0         # 库容 (亿m³)


class CoordinationController:
    """
    协调控制器

    实现多机组/多电站的协调优化
    """

    def __init__(self, name: str = "coordinator"):
        self.name = name

        # 机组状态
        self.units: Dict[str, UnitState] = {}

        # 水库状态
        self.reservoirs: Dict[str, ReservoirState] = {}

        # 调度模式
        self.mode = DispatchMode.OPTIMAL_EFFICIENCY

        # 优化参数
        self.optimization_weights = {
            'efficiency': 1.0,
            'stability': 0.5,
            'water_level': 0.3,
            'ramp': 0.2,
        }

        # 约束
        self.total_demand = 0.0
        self.reserve_requirement = 0.0

    def add_unit(self, unit: UnitState):
        """添加机组"""
        self.units[unit.unit_id] = unit

    def add_reservoir(self, reservoir: ReservoirState):
        """添加水库"""
        self.reservoirs[reservoir.reservoir_id] = reservoir

    def update_unit_state(self, unit_id: str, **kwargs):
        """更新机组状态"""
        if unit_id in self.units:
            for key, value in kwargs.items():
                if hasattr(self.units[unit_id], key):
                    setattr(self.units[unit_id], key, value)

    def dispatch(
        self,
        total_demand: float,
        reserve_requirement: float = 0.0
    ) -> Dict[str, float]:
        """
        执行负荷分配

        Args:
            total_demand: 总负荷需求 (MW)
            reserve_requirement: 备用需求 (MW)

        Returns:
            各机组功率分配
        """
        self.total_demand = total_demand
        self.reserve_requirement = reserve_requirement

        if self.mode == DispatchMode.EQUAL_DISTRIBUTION:
            return self._equal_dispatch(total_demand)

        elif self.mode == DispatchMode.OPTIMAL_EFFICIENCY:
            return self._efficiency_dispatch(total_demand)

        elif self.mode == DispatchMode.WATER_LEVEL:
            return self._water_level_dispatch(total_demand)

        elif self.mode == DispatchMode.PEAK_REGULATION:
            return self._peak_dispatch(total_demand)

        else:
            return self._equal_dispatch(total_demand)

    def _equal_dispatch(self, total_demand: float) -> Dict[str, float]:
        """均分负荷"""
        allocation = {}
        online_units = [u for u in self.units.values() if u.is_online]

        if not online_units:
            return allocation

        per_unit = total_demand / len(online_units)

        for unit in online_units:
            power = np.clip(per_unit, unit.min_power, unit.max_power)
            allocation[unit.unit_id] = power

        return allocation

    def _efficiency_dispatch(self, total_demand: float) -> Dict[str, float]:
        """
        效率最优分配

        使用等微增率原则
        """
        allocation = {}
        online_units = [u for u in self.units.values() if u.is_online]

        if not online_units:
            return allocation

        # 按效率排序
        sorted_units = sorted(online_units, key=lambda u: u.efficiency, reverse=True)

        remaining = total_demand

        for unit in sorted_units:
            if remaining <= 0:
                allocation[unit.unit_id] = unit.min_power if unit.min_power > 0 else 0
            else:
                # 优先分配给高效机组
                max_allocate = min(remaining, unit.max_power)
                power = max(max_allocate, unit.min_power)
                allocation[unit.unit_id] = power
                remaining -= power

        # 如果有剩余，按比例调整
        total_allocated = sum(allocation.values())
        if total_allocated > 0 and abs(total_allocated - total_demand) > 1:
            ratio = total_demand / total_allocated
            for unit_id in allocation:
                unit = self.units[unit_id]
                allocation[unit_id] = np.clip(
                    allocation[unit_id] * ratio,
                    unit.min_power,
                    unit.max_power
                )

        return allocation

    def _water_level_dispatch(self, total_demand: float) -> Dict[str, float]:
        """水位控制调度"""
        allocation = {}

        for unit in self.units.values():
            if not unit.is_online:
                continue

            # 获取关联水库
            reservoir_id = unit.unit_id.split('_')[0]  # 假设命名规则
            if reservoir_id in self.reservoirs:
                reservoir = self.reservoirs[reservoir_id]

                # 根据水位偏差调整出力
                level_error = reservoir.level - reservoir.target_level

                if level_error > 0:
                    # 水位偏高，增加出力
                    factor = 1 + 0.1 * level_error
                else:
                    # 水位偏低，减少出力
                    factor = 1 + 0.05 * level_error

                base_power = unit.capacity * 0.5
                power = np.clip(
                    base_power * factor,
                    unit.min_power,
                    unit.max_power
                )
                allocation[unit.unit_id] = power

        return allocation

    def _peak_dispatch(self, total_demand: float) -> Dict[str, float]:
        """调峰调度"""
        allocation = {}
        online_units = [u for u in self.units.values() if u.is_online]

        if not online_units:
            return allocation

        # 按变负荷能力排序
        sorted_units = sorted(
            online_units,
            key=lambda u: (u.ramp_up + u.ramp_down),
            reverse=True
        )

        # 基荷机组和调峰机组分配
        base_load_ratio = 0.6  # 60%作为基荷
        base_load = total_demand * base_load_ratio
        peak_load = total_demand - base_load

        # 分配基荷
        remaining_base = base_load
        for unit in sorted_units[len(sorted_units)//2:]:
            power = np.clip(remaining_base / (len(sorted_units) // 2 + 1),
                          unit.min_power, unit.max_power)
            allocation[unit.unit_id] = power
            remaining_base -= power

        # 分配调峰负荷
        remaining_peak = peak_load
        for unit in sorted_units[:len(sorted_units)//2]:
            if unit.unit_id in allocation:
                continue
            power = np.clip(remaining_peak, unit.min_power, unit.max_power)
            allocation[unit.unit_id] = power
            remaining_peak -= power

        return allocation

    def check_vibration_zones(
        self,
        allocation: Dict[str, float]
    ) -> Dict[str, float]:
        """
        检查并规避振动区

        Args:
            allocation: 功率分配

        Returns:
            调整后的功率分配
        """
        adjusted = allocation.copy()

        for unit_id, power in allocation.items():
            unit = self.units.get(unit_id)
            if unit is None:
                continue

            for zone_min, zone_max in unit.vibration_zone:
                if zone_min < power < zone_max:
                    # 在振动区内，调整到区域边界
                    to_min = power - zone_min
                    to_max = zone_max - power

                    if to_min < to_max:
                        adjusted[unit_id] = zone_min
                    else:
                        adjusted[unit_id] = zone_max

        return adjusted


class LoadDispatcher:
    """
    负荷调度器

    实现AGC功能和负荷预测
    """

    def __init__(self):
        self.coordinator = CoordinationController()

        # AGC参数
        self.agc_enabled = True
        self.agc_dead_band = 5.0      # MW
        self.agc_rate_limit = 50.0     # MW/min
        self.agc_bias = 10.0           # MW/0.1Hz

        # 负荷预测
        self.load_forecast: List[float] = []
        self.forecast_horizon = 24     # 小时

        # 历史数据
        self.load_history: List[float] = []
        self.frequency_history: List[float] = []

    def process_agc_signal(
        self,
        area_control_error: float,
        current_frequency: float,
        target_frequency: float = 50.0
    ) -> float:
        """
        处理AGC信号

        Args:
            area_control_error: 区域控制偏差 (MW)
            current_frequency: 当前频率 (Hz)
            target_frequency: 目标频率 (Hz)

        Returns:
            调节功率 (MW)
        """
        if not self.agc_enabled:
            return 0.0

        # 频率偏差
        freq_error = target_frequency - current_frequency

        # 计算ACE（区域控制偏差）
        ace = area_control_error + self.agc_bias * freq_error * 10

        # 应用死区
        if abs(ace) < self.agc_dead_band:
            return 0.0

        # 限制调节速率
        regulation = np.clip(ace, -self.agc_rate_limit, self.agc_rate_limit)

        return regulation

    def forecast_load(self, hours_ahead: int = 24) -> List[float]:
        """
        负荷预测

        Args:
            hours_ahead: 预测时长 (小时)

        Returns:
            预测负荷序列
        """
        if len(self.load_history) < 24:
            # 历史数据不足，返回当前负荷
            current = self.load_history[-1] if self.load_history else 0
            return [current] * hours_ahead

        # 简单的日周期模式预测
        daily_pattern = self.load_history[-24:]
        forecast = []

        for h in range(hours_ahead):
            # 基于昨日同时刻
            base = daily_pattern[h % 24]
            # 添加一些趋势
            trend = 0.01 * h  # 简单线性趋势
            forecast.append(base * (1 + trend))

        self.load_forecast = forecast
        return forecast

    def optimize_dispatch_schedule(
        self,
        load_forecast: List[float],
        time_step: float = 1.0  # 小时
    ) -> Dict[int, Dict[str, float]]:
        """
        优化调度计划

        Args:
            load_forecast: 负荷预测序列
            time_step: 时间步长 (小时)

        Returns:
            各时段的机组分配计划
        """
        schedule = {}

        for t, load in enumerate(load_forecast):
            allocation = self.coordinator.dispatch(load)
            # 规避振动区
            allocation = self.coordinator.check_vibration_zones(allocation)
            schedule[t] = allocation

        return schedule


class FrequencyRegulator:
    """
    频率调节器

    实现一次调频和二次调频
    """

    def __init__(self):
        # 一次调频参数
        self.primary_dead_band = 0.033    # Hz
        self.primary_droop = 0.04          # 调差率
        self.primary_response_time = 3.0   # 秒

        # 二次调频参数
        self.secondary_enabled = True
        self.secondary_gain = 20.0         # MW/Hz
        self.secondary_time_constant = 60.0  # 秒

        # 状态
        self.primary_reserve = 0.0         # 一次调频备用 (MW)
        self.secondary_reserve = 0.0       # 二次调频备用 (MW)
        self.frequency_deviation_integral = 0.0

    def primary_response(
        self,
        frequency: float,
        rated_power: float,
        current_power: float
    ) -> float:
        """
        一次调频响应

        Args:
            frequency: 当前频率 (Hz)
            rated_power: 额定功率 (MW)
            current_power: 当前功率 (MW)

        Returns:
            功率调节量 (MW)
        """
        freq_deviation = 50.0 - frequency

        # 死区
        if abs(freq_deviation) < self.primary_dead_band:
            return 0.0

        # 有效频差
        if freq_deviation > 0:
            effective_deviation = freq_deviation - self.primary_dead_band
        else:
            effective_deviation = freq_deviation + self.primary_dead_band

        # 一次调频出力
        # ΔP = -Pr / (bp * fn) * Δf
        delta_p = -rated_power / (self.primary_droop * 50.0) * effective_deviation

        return delta_p

    def secondary_response(
        self,
        area_control_error: float,
        dt: float
    ) -> float:
        """
        二次调频响应

        Args:
            area_control_error: ACE (MW)
            dt: 时间步长 (s)

        Returns:
            功率调节量 (MW)
        """
        if not self.secondary_enabled:
            return 0.0

        # PI控制
        # 积分项
        self.frequency_deviation_integral += area_control_error * dt

        # 限制积分
        max_integral = 500.0  # MW
        self.frequency_deviation_integral = np.clip(
            self.frequency_deviation_integral,
            -max_integral,
            max_integral
        )

        # 调节量
        delta_p = (
            self.secondary_gain * area_control_error +
            self.secondary_gain * 0.1 * self.frequency_deviation_integral
        )

        return delta_p

    def calculate_reserves(
        self,
        units: Dict[str, UnitState]
    ) -> Tuple[float, float]:
        """
        计算调频备用容量

        Args:
            units: 机组状态字典

        Returns:
            (一次调频备用, 二次调频备用)
        """
        primary_up = 0.0
        primary_down = 0.0
        secondary_up = 0.0
        secondary_down = 0.0

        for unit in units.values():
            if not unit.is_online:
                continue

            # 上调备用
            up_margin = unit.max_power - unit.power
            primary_up += min(up_margin, unit.ramp_up * self.primary_response_time / 60)
            secondary_up += up_margin

            # 下调备用
            down_margin = unit.power - unit.min_power
            primary_down += min(down_margin, unit.ramp_down * self.primary_response_time / 60)
            secondary_down += down_margin

        self.primary_reserve = min(primary_up, primary_down)
        self.secondary_reserve = min(secondary_up, secondary_down)

        return self.primary_reserve, self.secondary_reserve
