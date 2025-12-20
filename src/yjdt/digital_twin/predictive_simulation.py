# -*- coding: utf-8 -*-
"""
预测仿真 - 前瞻性决策支持
Predictive Simulation - Forward-looking Decision Support

功能：
- What-If场景分析
- 最优控制搜索
- 风险预评估
- 操作建议生成
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import copy


class OptimizationObjective(Enum):
    """优化目标"""
    MAX_POWER = "max_power"                 # 最大功率
    MAX_EFFICIENCY = "max_efficiency"       # 最大效率
    MIN_VIBRATION = "min_vibration"         # 最小振动
    MIN_WEAR = "min_wear"                   # 最小磨损
    BALANCED = "balanced"                   # 综合最优


@dataclass
class WhatIfScenario:
    """假设场景"""
    name: str
    description: str
    duration: float = 600.0                 # 仿真时长(秒)
    dt: float = 1.0                         # 时间步长(秒)

    # 初始条件修改
    initial_conditions: Dict[str, float] = field(default_factory=dict)

    # 控制序列 [{time: float, inputs: Dict[str, float]}, ...]
    control_sequence: List[Dict[str, Any]] = field(default_factory=list)

    # 扰动 [{time: float, variable: str, magnitude: float}, ...]
    disturbances: List[Dict[str, Any]] = field(default_factory=list)

    # 约束
    constraints: Dict[str, Tuple[float, float]] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """仿真结果"""
    scenario_name: str
    success: bool
    duration: float
    final_state: Dict[str, float]
    time_series: Dict[str, List[float]]
    violations: List[Dict[str, Any]]
    metrics: Dict[str, float]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


class PredictiveSimulator:
    """
    预测仿真器

    功能：
    - 快速前向仿真
    - 场景对比分析
    - 最优策略搜索
    - 风险评估
    """

    def __init__(self):
        # 模型参数
        self.params = {
            "rated_power": 1000.0,
            "rated_speed": 100.0,
            "rated_head": 480.0,
            "water_time_constant": 12.0,
            "mechanical_time_constant": 8.0,
            "thermal_time_constant": 300.0,
        }

        # 约束限值
        self.limits = {
            "speed": (80, 120),
            "power": (0, 1100),
            "guide_vane": (0, 1.0),
            "vibration": (0, 350),
            "bearing_temp": (20, 85),
            "stator_temp": (20, 135),
        }

        # 当前状态
        self.state = {
            "speed": 100.0,
            "power": 800.0,
            "guide_vane": 0.8,
            "flow": 200.0,
            "head": 480.0,
            "vibration": 100.0,
            "bearing_temp": 55.0,
            "stator_temp": 85.0,
        }

    def run_scenario(self, scenario: WhatIfScenario) -> SimulationResult:
        """
        运行假设场景

        Args:
            scenario: 场景定义

        Returns:
            仿真结果
        """
        # 初始化状态
        state = self.state.copy()
        for key, value in scenario.initial_conditions.items():
            if key in state:
                state[key] = value

        # 仿真参数
        duration = scenario.duration
        dt = scenario.dt
        steps = int(duration / dt)

        # 时间序列记录
        time_series = {key: [] for key in state}
        time_series["time"] = []

        # 违约记录
        violations = []

        # 控制序列索引
        ctrl_idx = 0
        ctrl_sequence = sorted(scenario.control_sequence, key=lambda x: x.get("time", 0))

        # 扰动索引
        dist_idx = 0
        disturbances = sorted(scenario.disturbances, key=lambda x: x.get("time", 0))

        # 仿真循环
        for step in range(steps):
            t = step * dt

            # 应用控制
            while ctrl_idx < len(ctrl_sequence) and ctrl_sequence[ctrl_idx].get("time", 0) <= t:
                ctrl = ctrl_sequence[ctrl_idx]
                for key, value in ctrl.get("inputs", {}).items():
                    if key in state:
                        state[key] = value
                ctrl_idx += 1

            # 应用扰动
            while dist_idx < len(disturbances) and disturbances[dist_idx].get("time", 0) <= t:
                dist = disturbances[dist_idx]
                var = dist.get("variable")
                if var in state:
                    state[var] += dist.get("magnitude", 0)
                dist_idx += 1

            # 模型更新
            state = self._step_model(state, dt)

            # 检查约束
            for var, (low, high) in scenario.constraints.items():
                if var in state:
                    if state[var] < low or state[var] > high:
                        violations.append({
                            "time": t,
                            "variable": var,
                            "value": state[var],
                            "limit": (low, high),
                        })

            # 记录时间序列
            time_series["time"].append(t)
            for key, value in state.items():
                time_series[key].append(value)

        # 计算指标
        metrics = self._calculate_metrics(time_series, violations)

        # 生成建议
        recommendations = self._generate_recommendations(scenario, metrics, violations)

        return SimulationResult(
            scenario_name=scenario.name,
            success=len(violations) == 0,
            duration=duration,
            final_state=state.copy(),
            time_series=time_series,
            violations=violations,
            metrics=metrics,
            recommendations=recommendations,
        )

    def _step_model(self, state: Dict[str, float], dt: float) -> Dict[str, float]:
        """单步模型更新"""
        new_state = state.copy()
        params = self.params

        # 水力模型
        # dQ/dt = (Q_target - Q) / Tw
        q_target = state["guide_vane"] * 250  # 简化：开度与流量线性
        tau_w = params["water_time_constant"]
        new_state["flow"] += (q_target - state["flow"]) * dt / tau_w

        # 功率模型
        # P = ρgQHη
        efficiency = 0.92 - 0.1 * (state["guide_vane"] - 0.8)**2
        power = 1000 * 9.81 * new_state["flow"] * state["head"] * efficiency / 1e6
        new_state["power"] = power

        # 转速模型
        # dω/dt = (Pm - Pe) / (2H)
        pm = power * 1.02  # 机械功率略大于电功率
        pe = power
        inertia = params["mechanical_time_constant"]
        speed_change = (pm - pe) / (2 * inertia) * dt
        new_state["speed"] = state["speed"] + speed_change * 100 / params["rated_speed"]

        # 振动模型（简化）
        base_vibration = 50 + 100 * abs(state["guide_vane"] - 0.75)
        new_state["vibration"] += (base_vibration - state["vibration"]) * dt / 10

        # 温度模型
        tau_t = params["thermal_time_constant"]
        steady_bearing = 45 + 20 * power / 1000
        new_state["bearing_temp"] += (steady_bearing - state["bearing_temp"]) * dt / tau_t

        steady_stator = 60 + 40 * power / 1000
        new_state["stator_temp"] += (steady_stator - state["stator_temp"]) * dt / tau_t

        return new_state

    def _calculate_metrics(self, time_series: Dict[str, List[float]],
                           violations: List[Dict]) -> Dict[str, float]:
        """计算性能指标"""
        power = time_series.get("power", [0])
        vibration = time_series.get("vibration", [0])
        temp = time_series.get("bearing_temp", [0])

        return {
            "avg_power": np.mean(power),
            "max_power": np.max(power),
            "min_power": np.min(power),
            "power_variation": np.std(power),
            "max_vibration": np.max(vibration),
            "avg_vibration": np.mean(vibration),
            "max_temp": np.max(temp),
            "violation_count": len(violations),
            "efficiency_score": np.mean(power) / 1000 * 100,  # 简化效率评分
        }

    def _generate_recommendations(self, scenario: WhatIfScenario,
                                   metrics: Dict[str, float],
                                   violations: List[Dict]) -> List[str]:
        """生成操作建议"""
        recommendations = []

        # 基于违约情况
        if violations:
            var_counts = {}
            for v in violations:
                var = v["variable"]
                var_counts[var] = var_counts.get(var, 0) + 1

            for var, count in var_counts.items():
                if var == "speed":
                    recommendations.append(f"转速越限{count}次，建议调整调速器参数")
                elif var == "power":
                    recommendations.append(f"功率越限{count}次，建议限制导叶开度变化率")
                elif var == "vibration":
                    recommendations.append(f"振动越限{count}次，建议避免振动区运行")
                elif var == "bearing_temp":
                    recommendations.append(f"轴承温度越限{count}次，建议检查冷却系统")

        # 基于指标
        if metrics.get("power_variation", 0) > 50:
            recommendations.append("功率波动较大，建议平滑控制策略")

        if metrics.get("max_vibration", 0) > 200:
            recommendations.append("振动偏高，建议优化运行工况点")

        if not recommendations:
            recommendations.append("该场景运行正常，无需特别调整")

        return recommendations

    def compare_scenarios(self, scenarios: List[WhatIfScenario]) -> Dict[str, Any]:
        """对比多个场景"""
        results = []
        for scenario in scenarios:
            result = self.run_scenario(scenario)
            results.append(result)

        # 对比表
        comparison = {
            "scenarios": [r.scenario_name for r in results],
            "success": [r.success for r in results],
            "avg_power": [r.metrics.get("avg_power", 0) for r in results],
            "max_vibration": [r.metrics.get("max_vibration", 0) for r in results],
            "violations": [r.metrics.get("violation_count", 0) for r in results],
        }

        # 推荐最优场景
        best_idx = 0
        best_score = float('-inf')
        for i, r in enumerate(results):
            score = r.metrics.get("avg_power", 0) - r.metrics.get("violation_count", 0) * 100
            if score > best_score:
                best_score = score
                best_idx = i

        comparison["recommended"] = scenarios[best_idx].name
        comparison["results"] = results

        return comparison

    def find_optimal_setpoint(self, objective: OptimizationObjective,
                              constraints: Dict[str, Tuple[float, float]],
                              search_range: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
        """
        搜索最优设定点

        Args:
            objective: 优化目标
            constraints: 约束条件
            search_range: 搜索范围

        Returns:
            最优设定点和预期性能
        """
        best_setpoint = {}
        best_score = float('-inf')
        best_result = None

        # 网格搜索
        resolution = 10
        ranges = []
        var_names = list(search_range.keys())

        for var in var_names:
            low, high = search_range[var]
            ranges.append(np.linspace(low, high, resolution))

        # 生成所有组合
        grid = np.meshgrid(*ranges)
        combinations = np.array([g.flatten() for g in grid]).T

        for combo in combinations:
            setpoint = {var: combo[i] for i, var in enumerate(var_names)}

            # 创建测试场景
            scenario = WhatIfScenario(
                name="optimization_test",
                description="Optimization search",
                duration=60,
                dt=1.0,
                initial_conditions=setpoint,
                constraints=constraints,
            )

            result = self.run_scenario(scenario)

            # 计算得分
            score = self._calculate_objective_score(result, objective)

            if score > best_score and result.success:
                best_score = score
                best_setpoint = setpoint.copy()
                best_result = result

        return {
            "objective": objective.value,
            "optimal_setpoint": best_setpoint,
            "expected_score": best_score,
            "expected_metrics": best_result.metrics if best_result else {},
            "recommendations": best_result.recommendations if best_result else [],
        }

    def _calculate_objective_score(self, result: SimulationResult,
                                   objective: OptimizationObjective) -> float:
        """计算目标函数值"""
        metrics = result.metrics

        if objective == OptimizationObjective.MAX_POWER:
            return metrics.get("avg_power", 0)

        elif objective == OptimizationObjective.MAX_EFFICIENCY:
            return metrics.get("efficiency_score", 0)

        elif objective == OptimizationObjective.MIN_VIBRATION:
            return -metrics.get("max_vibration", 0)

        elif objective == OptimizationObjective.MIN_WEAR:
            # 综合振动和温度
            return -(metrics.get("max_vibration", 0) + metrics.get("max_temp", 0))

        elif objective == OptimizationObjective.BALANCED:
            # 综合评分
            power_score = metrics.get("avg_power", 0) / 1000 * 100
            vibration_penalty = max(0, metrics.get("max_vibration", 0) - 150) / 10
            temp_penalty = max(0, metrics.get("max_temp", 0) - 70) / 10
            return power_score - vibration_penalty - temp_penalty

        return 0.0

    def predict_risk(self, horizon: float = 3600,
                     current_state: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        预测运行风险

        Args:
            horizon: 预测时长(秒)
            current_state: 当前状态

        Returns:
            风险评估结果
        """
        if current_state:
            self.state = current_state.copy()

        # 创建趋势延续场景
        scenario = WhatIfScenario(
            name="risk_prediction",
            description="Risk prediction based on current trends",
            duration=horizon,
            dt=10.0,
            initial_conditions=self.state.copy(),
            constraints=self.limits.copy(),
        )

        result = self.run_scenario(scenario)

        # 分析风险
        risks = []
        time_series = result.time_series

        # 检查各变量趋势
        for var in ["speed", "vibration", "bearing_temp", "stator_temp"]:
            if var in time_series and len(time_series[var]) > 10:
                values = time_series[var]
                trend = np.polyfit(range(len(values)), values, 1)[0]

                low, high = self.limits.get(var, (0, float('inf')))

                if trend > 0 and values[-1] > high * 0.9:
                    time_to_limit = (high - values[-1]) / trend if trend > 0 else float('inf')
                    risks.append({
                        "variable": var,
                        "type": "increasing_toward_limit",
                        "current_value": values[-1],
                        "limit": high,
                        "trend": trend,
                        "time_to_limit": time_to_limit,
                        "severity": "high" if time_to_limit < 300 else "medium",
                    })

                elif trend < 0 and values[-1] < low * 1.1:
                    time_to_limit = (values[-1] - low) / abs(trend) if trend < 0 else float('inf')
                    risks.append({
                        "variable": var,
                        "type": "decreasing_toward_limit",
                        "current_value": values[-1],
                        "limit": low,
                        "trend": trend,
                        "time_to_limit": time_to_limit,
                        "severity": "high" if time_to_limit < 300 else "medium",
                    })

        # 综合风险等级
        if any(r["severity"] == "high" for r in risks):
            overall_risk = "high"
        elif any(r["severity"] == "medium" for r in risks):
            overall_risk = "medium"
        else:
            overall_risk = "low"

        return {
            "horizon": horizon,
            "overall_risk": overall_risk,
            "specific_risks": risks,
            "violations_predicted": len(result.violations),
            "recommendations": result.recommendations,
        }
