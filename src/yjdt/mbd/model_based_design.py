# -*- coding: utf-8 -*-
"""
模型驱动设计 - Model-Based Design (MBD)

基于YX工程（雅鲁藏布江大拐弯截弯取直引水梯级发电工程）的MBD实现

核心功能：
- 建立系统级运行行为的仿真基础
- 设计参数反向优化
- 运行能力评估
- 设计方案对比验证
- 与ODD/MAS/SIL/HIL集成

参考：YX工程面向运行能力的设计评估与运行逻辑验证关键技术研究
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import logging
from scipy.optimize import minimize, differential_evolution
import copy

logger = logging.getLogger(__name__)


class DesignObjective(Enum):
    """设计目标"""
    SAFETY = "safety"                   # 安全性
    STABILITY = "stability"             # 稳定性
    ECONOMY = "economy"                 # 经济性
    RELIABILITY = "reliability"         # 可靠性
    CONTROLLABILITY = "controllability" # 可控性
    MAINTAINABILITY = "maintainability" # 可维护性


class ParameterType(Enum):
    """参数类型"""
    HYDRAULIC = "hydraulic"             # 水力参数
    MECHANICAL = "mechanical"           # 机械参数
    ELECTRICAL = "electrical"           # 电气参数
    CONTROL = "control"                 # 控制参数
    PROTECTION = "protection"           # 保护参数
    COORDINATION = "coordination"       # 协调参数


class OptimizationMethod(Enum):
    """优化方法"""
    GRADIENT = "gradient"               # 梯度下降
    GENETIC = "genetic"                 # 遗传算法
    PARTICLE_SWARM = "particle_swarm"   # 粒子群
    DIFFERENTIAL_EVOLUTION = "de"       # 差分进化
    BAYESIAN = "bayesian"               # 贝叶斯优化


@dataclass
class DesignParameter:
    """设计参数"""
    name: str
    description: str
    param_type: ParameterType
    unit: str

    # 取值范围
    nominal_value: float                 # 标称值
    min_value: float                     # 最小值
    max_value: float                     # 最大值

    # 敏感性
    sensitivity: float = 1.0             # 参数敏感度
    is_critical: bool = False            # 是否关键参数

    # 约束
    constraints: List[str] = field(default_factory=list)

    # 当前值
    current_value: float = None

    def __post_init__(self):
        if self.current_value is None:
            self.current_value = self.nominal_value


@dataclass
class DesignScheme:
    """设计方案"""
    scheme_id: str
    name: str
    description: str
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)

    # 参数集
    parameters: Dict[str, DesignParameter] = field(default_factory=dict)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 评估结果
    evaluation_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """优化结果"""
    success: bool
    optimal_parameters: Dict[str, float]
    optimal_value: float
    iterations: int
    convergence_history: List[float]
    constraints_satisfied: bool
    message: str


@dataclass
class SensitivityResult:
    """敏感性分析结果"""
    parameter: str
    sensitivity_index: float
    influence_on: Dict[str, float]      # 对各指标的影响
    critical_range: Tuple[float, float]  # 临界范围
    recommendation: str


class SystemModel(ABC):
    """系统模型基类"""

    @abstractmethod
    def simulate(self, parameters: Dict[str, float],
                 scenario: Dict[str, Any],
                 duration: float) -> Dict[str, Any]:
        """运行仿真"""
        pass

    @abstractmethod
    def evaluate(self, simulation_result: Dict[str, Any],
                 objectives: List[DesignObjective]) -> Dict[str, float]:
        """评估仿真结果"""
        pass


class CascadeHydropowerModel(SystemModel):
    """
    梯级水电站系统模型

    用于MBD的系统级仿真
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stations: List[Dict[str, Any]] = []
        self.hydraulic_coupling = True  # 水力耦合

    def add_station(self, station_config: Dict[str, Any]):
        """添加电站配置"""
        self.stations.append(station_config)

    def simulate(self, parameters: Dict[str, float],
                 scenario: Dict[str, Any],
                 duration: float) -> Dict[str, Any]:
        """
        运行梯级系统仿真

        Args:
            parameters: 设计参数
            scenario: 运行场景
            duration: 仿真时长

        Returns:
            仿真结果
        """
        dt = parameters.get("simulation_dt", 0.01)
        steps = int(duration / dt)

        results = {
            "time": np.arange(0, duration, dt),
            "stations": {},
            "system": {
                "pressure": [],
                "flow": [],
                "power": [],
                "frequency": [],
            },
        }

        # 初始化各站状态
        for i, station in enumerate(self.stations):
            station_id = station.get("id", f"station_{i}")
            results["stations"][station_id] = {
                "pressure": [],
                "flow": [],
                "power": [],
                "speed": [],
                "guide_vane": [],
            }

        # 获取场景参数
        scenario_type = scenario.get("type", "normal")
        event_time = scenario.get("event_time", duration / 2)
        event_magnitude = scenario.get("magnitude", 0.3)

        # 仿真循环
        system_state = self._init_state(parameters)

        for step in range(steps):
            t = step * dt

            # 场景事件
            if scenario_type == "load_rejection" and t >= event_time:
                # 甩负荷
                system_state = self._apply_load_rejection(
                    system_state, parameters, event_magnitude
                )
            elif scenario_type == "load_increase" and t >= event_time:
                # 加负荷
                system_state = self._apply_load_increase(
                    system_state, parameters, event_magnitude
                )

            # 系统动态计算
            system_state = self._step(system_state, parameters, dt)

            # 记录结果
            results["system"]["pressure"].append(system_state["system_pressure"])
            results["system"]["flow"].append(system_state["system_flow"])
            results["system"]["power"].append(system_state["system_power"])
            results["system"]["frequency"].append(system_state["frequency"])

            for station_id in results["stations"]:
                if station_id in system_state["stations"]:
                    s = system_state["stations"][station_id]
                    results["stations"][station_id]["pressure"].append(s.get("pressure", 0))
                    results["stations"][station_id]["flow"].append(s.get("flow", 0))
                    results["stations"][station_id]["power"].append(s.get("power", 0))
                    results["stations"][station_id]["speed"].append(s.get("speed", 0))
                    results["stations"][station_id]["guide_vane"].append(s.get("guide_vane", 0))

        # 转换为numpy数组
        for key in results["system"]:
            results["system"][key] = np.array(results["system"][key])

        for station_id in results["stations"]:
            for key in results["stations"][station_id]:
                results["stations"][station_id][key] = np.array(
                    results["stations"][station_id][key]
                )

        return results

    def _init_state(self, parameters: Dict[str, float]) -> Dict[str, Any]:
        """初始化系统状态"""
        state = {
            "system_pressure": parameters.get("rated_pressure", 5.0),
            "system_flow": parameters.get("rated_flow", 1000),
            "system_power": parameters.get("rated_power", 5000),
            "frequency": 50.0,
            "stations": {},
        }

        for i, station in enumerate(self.stations):
            station_id = station.get("id", f"station_{i}")
            state["stations"][station_id] = {
                "pressure": station.get("rated_pressure", 5.0),
                "flow": station.get("rated_flow", 200),
                "power": station.get("rated_power", 1000),
                "speed": station.get("rated_speed", 166.7),
                "guide_vane": 0.8,
            }

        return state

    def _step(self, state: Dict[str, Any],
              parameters: Dict[str, float], dt: float) -> Dict[str, Any]:
        """仿真单步"""
        new_state = copy.deepcopy(state)

        # 调速器参数
        Kp = parameters.get("governor_kp", 2.5)
        Ki = parameters.get("governor_ki", 0.15)
        Kd = parameters.get("governor_kd", 4.0)

        # 水力时间常数
        Tw = parameters.get("water_inertia_time", 12.0)

        # 机械时间常数
        Tm = parameters.get("mechanical_time_constant", 8.0)

        # 各站动态
        total_power = 0
        total_flow = 0

        for station_id, s in state["stations"].items():
            # 频率偏差
            freq_error = 50.0 - state["frequency"]

            # 调速器响应
            guide_vane_cmd = s["guide_vane"] + Kp * freq_error * dt

            # 导叶动作速率限制
            max_rate = parameters.get("max_guide_vane_rate", 0.1)
            guide_vane_change = np.clip(
                guide_vane_cmd - s["guide_vane"],
                -max_rate * dt,
                max_rate * dt
            )
            new_guide_vane = np.clip(s["guide_vane"] + guide_vane_change, 0, 1)

            # 流量响应
            target_flow = new_guide_vane * state["stations"][station_id].get("max_flow", 250)
            new_flow = s["flow"] + (target_flow - s["flow"]) * dt / Tw

            # 压力响应（水锤效应简化）
            flow_change_rate = (new_flow - s["flow"]) / dt if dt > 0 else 0
            pressure_change = -Tw * flow_change_rate / 100
            new_pressure = s["pressure"] + pressure_change * dt

            # 功率计算
            eta = parameters.get("turbine_efficiency", 0.94)
            new_power = 9.81 * new_flow * new_pressure * 100 * eta / 1000  # MW

            # 转速响应
            power_unbalance = (new_power - s.get("load", s["power"])) / s["power"] if s["power"] > 0 else 0
            speed_change = power_unbalance / Tm
            new_speed = s["speed"] * (1 + speed_change * dt)

            new_state["stations"][station_id] = {
                "pressure": new_pressure,
                "flow": new_flow,
                "power": new_power,
                "speed": new_speed,
                "guide_vane": new_guide_vane,
                "load": s.get("load", s["power"]),
            }

            total_power += new_power
            total_flow += new_flow

        # 系统级状态更新
        new_state["system_power"] = total_power
        new_state["system_flow"] = total_flow
        new_state["system_pressure"] = np.mean([
            s["pressure"] for s in new_state["stations"].values()
        ])

        # 系统频率
        total_inertia = sum(
            station.get("inertia", 4.0) for station in self.stations
        )
        load = parameters.get("system_load", total_power)
        power_unbalance = (total_power - load) / load if load > 0 else 0
        new_state["frequency"] = state["frequency"] + power_unbalance * dt / total_inertia * 50

        return new_state

    def _apply_load_rejection(self, state: Dict[str, Any],
                              parameters: Dict[str, float],
                              magnitude: float) -> Dict[str, Any]:
        """应用甩负荷"""
        new_state = copy.deepcopy(state)

        # 减少负荷
        for station_id in new_state["stations"]:
            new_state["stations"][station_id]["load"] = (
                new_state["stations"][station_id]["power"] * (1 - magnitude)
            )

        return new_state

    def _apply_load_increase(self, state: Dict[str, Any],
                             parameters: Dict[str, float],
                             magnitude: float) -> Dict[str, Any]:
        """应用加负荷"""
        new_state = copy.deepcopy(state)

        for station_id in new_state["stations"]:
            current_power = new_state["stations"][station_id]["power"]
            new_state["stations"][station_id]["load"] = current_power * (1 + magnitude)

        return new_state

    def evaluate(self, simulation_result: Dict[str, Any],
                 objectives: List[DesignObjective]) -> Dict[str, float]:
        """
        评估仿真结果

        Args:
            simulation_result: 仿真结果
            objectives: 评估目标

        Returns:
            各目标的评分
        """
        scores = {}

        system = simulation_result.get("system", {})
        pressure = system.get("pressure", np.array([]))
        flow = system.get("flow", np.array([]))
        power = system.get("power", np.array([]))
        frequency = system.get("frequency", np.array([]))

        if DesignObjective.SAFETY in objectives:
            # 安全性评估
            safety_score = 100.0

            # 压力安全
            if len(pressure) > 0:
                max_pressure = np.max(pressure)
                min_pressure = np.min(pressure)
                if max_pressure > 6.5 or min_pressure < 0:
                    safety_score -= 50
                elif max_pressure > 6.0 or min_pressure < 0.5:
                    safety_score -= 20

            # 频率安全
            if len(frequency) > 0:
                max_freq = np.max(frequency)
                min_freq = np.min(frequency)
                if max_freq > 52 or min_freq < 48:
                    safety_score -= 30
                elif max_freq > 51 or min_freq < 49:
                    safety_score -= 10

            scores[DesignObjective.SAFETY.value] = max(0, safety_score)

        if DesignObjective.STABILITY in objectives:
            # 稳定性评估
            stability_score = 100.0

            if len(frequency) > 100:
                # 频率波动
                freq_std = np.std(frequency[-100:])
                if freq_std > 0.5:
                    stability_score -= 30
                elif freq_std > 0.2:
                    stability_score -= 10

                # 是否收敛
                final_freq = np.mean(frequency[-10:])
                if abs(final_freq - 50) > 0.5:
                    stability_score -= 20

            if len(power) > 100:
                # 功率波动
                power_std = np.std(power[-100:]) / np.mean(power[-100:]) * 100 if np.mean(power[-100:]) > 0 else 0
                if power_std > 5:
                    stability_score -= 20

            scores[DesignObjective.STABILITY.value] = max(0, stability_score)

        if DesignObjective.CONTROLLABILITY in objectives:
            # 可控性评估
            control_score = 100.0

            if len(frequency) > 0:
                # 调节时间
                target = 50.0
                tolerance = 0.02 * target
                settled = np.abs(frequency - target) < tolerance

                if np.any(settled):
                    settle_indices = np.where(settled)[0]
                    if len(settle_indices) > 0:
                        first_settle = settle_indices[0]
                        time = simulation_result.get("time", np.array([]))
                        if len(time) > first_settle:
                            settling_time = time[first_settle]
                            if settling_time > 60:
                                control_score -= 30
                            elif settling_time > 30:
                                control_score -= 10
                else:
                    control_score -= 40

                # 超调量
                max_deviation = np.max(np.abs(frequency - target))
                overshoot = max_deviation / target * 100
                if overshoot > 10:
                    control_score -= 20
                elif overshoot > 5:
                    control_score -= 10

            scores[DesignObjective.CONTROLLABILITY.value] = max(0, control_score)

        return scores


class ParameterOptimizer:
    """
    设计参数优化器

    实现设计参数反向优化功能
    """

    def __init__(self, model: SystemModel):
        self.model = model
        self.optimization_history: List[Dict[str, Any]] = []

    def optimize(self, parameters: List[DesignParameter],
                 objectives: List[DesignObjective],
                 scenarios: List[Dict[str, Any]],
                 method: OptimizationMethod = OptimizationMethod.DIFFERENTIAL_EVOLUTION,
                 max_iterations: int = 100) -> OptimizationResult:
        """
        优化设计参数

        Args:
            parameters: 待优化参数列表
            objectives: 优化目标
            scenarios: 测试场景列表
            method: 优化方法
            max_iterations: 最大迭代次数

        Returns:
            优化结果
        """
        # 构建参数边界
        bounds = [(p.min_value, p.max_value) for p in parameters]
        param_names = [p.name for p in parameters]

        # 目标函数
        def objective_func(x):
            params_dict = {name: val for name, val in zip(param_names, x)}

            total_score = 0
            for scenario in scenarios:
                result = self.model.simulate(params_dict, scenario, duration=60)
                scores = self.model.evaluate(result, objectives)
                # 最大化得分 -> 最小化负得分
                total_score -= sum(scores.values()) / len(scores)

            return total_score

        # 执行优化
        convergence_history = []

        if method == OptimizationMethod.DIFFERENTIAL_EVOLUTION:
            result = differential_evolution(
                objective_func,
                bounds,
                maxiter=max_iterations,
                disp=True,
                callback=lambda xk, convergence: convergence_history.append(-convergence)
            )
        else:
            # 使用scipy.optimize.minimize
            x0 = [p.current_value for p in parameters]
            result = minimize(
                objective_func,
                x0,
                method='L-BFGS-B',
                bounds=bounds,
                options={'maxiter': max_iterations}
            )

        # 构建结果
        optimal_params = {name: val for name, val in zip(param_names, result.x)}

        opt_result = OptimizationResult(
            success=result.success,
            optimal_parameters=optimal_params,
            optimal_value=-result.fun,  # 转回正得分
            iterations=result.nit if hasattr(result, 'nit') else max_iterations,
            convergence_history=convergence_history,
            constraints_satisfied=self._check_constraints(optimal_params, parameters),
            message=result.message if hasattr(result, 'message') else "Optimization completed"
        )

        self.optimization_history.append({
            "timestamp": datetime.now().isoformat(),
            "parameters": param_names,
            "result": opt_result
        })

        return opt_result

    def _check_constraints(self, params: Dict[str, float],
                           param_defs: List[DesignParameter]) -> bool:
        """检查约束是否满足"""
        for param_def in param_defs:
            value = params.get(param_def.name, param_def.nominal_value)
            if value < param_def.min_value or value > param_def.max_value:
                return False
        return True


class SensitivityAnalyzer:
    """
    参数敏感性分析器

    识别系统级敏感参数区间
    """

    def __init__(self, model: SystemModel):
        self.model = model

    def analyze(self, parameters: List[DesignParameter],
                objectives: List[DesignObjective],
                scenarios: List[Dict[str, Any]],
                perturbation: float = 0.1) -> List[SensitivityResult]:
        """
        进行敏感性分析

        Args:
            parameters: 参数列表
            objectives: 评估目标
            scenarios: 测试场景
            perturbation: 扰动比例

        Returns:
            敏感性分析结果列表
        """
        results = []

        # 基准仿真
        base_params = {p.name: p.current_value for p in parameters}
        base_scores = self._evaluate_scenarios(base_params, objectives, scenarios)

        for param in parameters:
            # 正向扰动
            plus_params = base_params.copy()
            plus_params[param.name] = param.current_value * (1 + perturbation)
            plus_params[param.name] = min(plus_params[param.name], param.max_value)
            plus_scores = self._evaluate_scenarios(plus_params, objectives, scenarios)

            # 负向扰动
            minus_params = base_params.copy()
            minus_params[param.name] = param.current_value * (1 - perturbation)
            minus_params[param.name] = max(minus_params[param.name], param.min_value)
            minus_scores = self._evaluate_scenarios(minus_params, objectives, scenarios)

            # 计算敏感度
            influence_on = {}
            total_sensitivity = 0

            for obj in objectives:
                obj_name = obj.value
                if obj_name in base_scores and obj_name in plus_scores and obj_name in minus_scores:
                    delta_plus = plus_scores[obj_name] - base_scores[obj_name]
                    delta_minus = minus_scores[obj_name] - base_scores[obj_name]
                    sensitivity = (abs(delta_plus) + abs(delta_minus)) / (2 * perturbation * 100)
                    influence_on[obj_name] = sensitivity
                    total_sensitivity += sensitivity

            # 确定临界范围
            critical_range = self._find_critical_range(param, objectives, scenarios)

            # 生成建议
            recommendation = self._generate_recommendation(
                param, total_sensitivity, influence_on
            )

            results.append(SensitivityResult(
                parameter=param.name,
                sensitivity_index=total_sensitivity / len(objectives) if objectives else 0,
                influence_on=influence_on,
                critical_range=critical_range,
                recommendation=recommendation
            ))

        return results

    def _evaluate_scenarios(self, params: Dict[str, float],
                            objectives: List[DesignObjective],
                            scenarios: List[Dict[str, Any]]) -> Dict[str, float]:
        """评估多场景下的得分"""
        total_scores = {obj.value: 0 for obj in objectives}

        for scenario in scenarios:
            result = self.model.simulate(params, scenario, duration=60)
            scores = self.model.evaluate(result, objectives)

            for key, value in scores.items():
                total_scores[key] += value

        # 平均
        for key in total_scores:
            total_scores[key] /= len(scenarios) if scenarios else 1

        return total_scores

    def _find_critical_range(self, param: DesignParameter,
                             objectives: List[DesignObjective],
                             scenarios: List[Dict[str, Any]]) -> Tuple[float, float]:
        """找到参数的临界范围"""
        # 简化实现：基于边界
        margin = 0.1
        return (
            param.nominal_value * (1 - margin),
            param.nominal_value * (1 + margin)
        )

    def _generate_recommendation(self, param: DesignParameter,
                                 sensitivity: float,
                                 influence: Dict[str, float]) -> str:
        """生成参数调整建议"""
        if sensitivity > 0.5:
            return f"高敏感参数，建议在{param.nominal_value:.2f}±5%范围内取值"
        elif sensitivity > 0.2:
            return f"中等敏感参数，建议在{param.nominal_value:.2f}±10%范围内取值"
        else:
            return f"低敏感参数，可在允许范围内自由取值"


class ReverseDesignOptimizer:
    """
    反向设计优化器

    基于在环验证结果反向驱动设计参数优化

    典型应用场景：
    1. 导叶/阀门动作速率与压力波叠加优化
    2. 保护触发后的级联降级参数优化
    3. 调速参数与系统低频振荡风险规避
    """

    def __init__(self, model: SystemModel):
        self.model = model
        self.optimizer = ParameterOptimizer(model)
        self.analyzer = SensitivityAnalyzer(model)
        self.optimization_results: List[Dict[str, Any]] = []

    def optimize_guide_vane_coordination(self,
                                         multi_station_scenario: Dict[str, Any],
                                         current_params: Dict[str, float]) -> Dict[str, Any]:
        """
        优化导叶/阀门动作时间窗

        针对多站近同步动作→压力波叠加的问题

        Args:
            multi_station_scenario: 多站协同动作场景
            current_params: 当前参数

        Returns:
            优化建议
        """
        result = {
            "issue": "多站导叶同步动作导致压力波叠加",
            "analysis": {},
            "recommendations": [],
        }

        # 分析不同时间窗配置
        time_windows = [5, 10, 15, 20, 30]  # 秒
        best_window = None
        best_score = -float('inf')

        for window in time_windows:
            test_params = current_params.copy()
            test_params["action_time_window"] = window

            sim_result = self.model.simulate(
                test_params,
                multi_station_scenario,
                duration=120
            )

            # 评估压力波动
            pressure = sim_result.get("system", {}).get("pressure", [])
            if len(pressure) > 0:
                max_pressure = np.max(pressure)
                min_pressure = np.min(pressure)
                pressure_range = max_pressure - min_pressure

                score = 100 - pressure_range * 20  # 压力范围越小越好

                result["analysis"][f"window_{window}s"] = {
                    "max_pressure": max_pressure,
                    "min_pressure": min_pressure,
                    "pressure_range": pressure_range,
                    "score": score,
                }

                if score > best_score:
                    best_score = score
                    best_window = window

        if best_window:
            result["recommendations"].append({
                "parameter": "action_time_window",
                "optimal_value": best_window,
                "description": f"建议多站动作时间窗设置为{best_window}秒",
            })

        # 动作速率优化
        rates = [0.02, 0.05, 0.08, 0.10, 0.15]
        best_rate = None
        best_rate_score = -float('inf')

        for rate in rates:
            test_params = current_params.copy()
            test_params["max_guide_vane_rate"] = rate

            sim_result = self.model.simulate(
                test_params,
                multi_station_scenario,
                duration=120
            )

            pressure = sim_result.get("system", {}).get("pressure", [])
            if len(pressure) > 0:
                pressure_gradient = np.max(np.abs(np.diff(pressure))) / 0.01  # MPa/s
                score = 100 - pressure_gradient * 50

                if score > best_rate_score:
                    best_rate_score = score
                    best_rate = rate

        if best_rate:
            result["recommendations"].append({
                "parameter": "max_guide_vane_rate",
                "optimal_value": best_rate,
                "description": f"建议导叶动作速率限制为{best_rate} pu/s",
            })

        self.optimization_results.append(result)
        return result

    def optimize_cascade_degradation(self,
                                     cascade_scenario: Dict[str, Any],
                                     current_params: Dict[str, float]) -> Dict[str, Any]:
        """
        优化级联降级参数

        针对保护触发后的级联效应

        Args:
            cascade_scenario: 级联场景
            current_params: 当前参数

        Returns:
            优化建议
        """
        result = {
            "issue": "保护触发后的级联降级优化",
            "analysis": {},
            "recommendations": [],
        }

        # 测试不同降级序列
        priorities = [
            ["maintain_pressure", "maintain_frequency"],
            ["maintain_frequency", "maintain_pressure"],
            ["minimize_cascade", "maintain_pressure", "maintain_frequency"],
        ]

        best_priority = None
        best_score = -float('inf')

        for i, priority in enumerate(priorities):
            test_params = current_params.copy()
            test_params["degradation_priority"] = priority

            sim_result = self.model.simulate(
                test_params,
                cascade_scenario,
                duration=180
            )

            # 评估恢复质量
            scores = self.model.evaluate(
                sim_result,
                [DesignObjective.SAFETY, DesignObjective.STABILITY]
            )

            total_score = sum(scores.values())

            result["analysis"][f"priority_{i}"] = {
                "priority": priority,
                "scores": scores,
                "total": total_score,
            }

            if total_score > best_score:
                best_score = total_score
                best_priority = priority

        if best_priority:
            result["recommendations"].append({
                "parameter": "degradation_priority",
                "optimal_value": best_priority,
                "description": f"建议降级优先级序列: {' -> '.join(best_priority)}",
            })

        # 稳压力优先的参数优化
        result["recommendations"].append({
            "parameter": "pressure_priority_weight",
            "optimal_value": 0.7,
            "description": "建议压力稳定权重设置为0.7，优先保障有压系统安全",
        })

        self.optimization_results.append(result)
        return result

    def optimize_governor_parameters(self,
                                     oscillation_scenario: Dict[str, Any],
                                     current_params: Dict[str, float]) -> Dict[str, Any]:
        """
        优化调速参数避免系统振荡

        针对系统级低频振荡风险

        Args:
            oscillation_scenario: 振荡风险场景
            current_params: 当前参数

        Returns:
            优化建议
        """
        result = {
            "issue": "调速参数与系统低频振荡风险",
            "analysis": {},
            "recommendations": [],
            "sensitive_regions": [],
        }

        # 参数扫描
        kp_range = np.linspace(1.0, 5.0, 10)
        ki_range = np.linspace(0.05, 0.5, 10)

        stability_map = np.zeros((len(kp_range), len(ki_range)))

        for i, kp in enumerate(kp_range):
            for j, ki in enumerate(ki_range):
                test_params = current_params.copy()
                test_params["governor_kp"] = kp
                test_params["governor_ki"] = ki

                sim_result = self.model.simulate(
                    test_params,
                    oscillation_scenario,
                    duration=120
                )

                # 检测振荡
                frequency = sim_result.get("system", {}).get("frequency", [])
                if len(frequency) > 100:
                    # 计算频谱
                    freq_fft = np.fft.fft(frequency - np.mean(frequency))
                    power = np.abs(freq_fft[:len(freq_fft)//2])**2

                    # 低频能量占比（0.1-1Hz）
                    dt = 0.01
                    freqs = np.fft.fftfreq(len(frequency), dt)[:len(frequency)//2]
                    low_freq_mask = (freqs > 0.1) & (freqs < 1.0)
                    low_freq_energy = np.sum(power[low_freq_mask])
                    total_energy = np.sum(power) + 1e-10

                    oscillation_ratio = low_freq_energy / total_energy

                    # 稳定性得分（振荡越小越好）
                    stability_map[i, j] = 1 - oscillation_ratio
                else:
                    stability_map[i, j] = 0.5

        # 找到最佳参数区域
        best_idx = np.unravel_index(np.argmax(stability_map), stability_map.shape)
        best_kp = kp_range[best_idx[0]]
        best_ki = ki_range[best_idx[1]]

        result["analysis"]["stability_map"] = stability_map.tolist()
        result["analysis"]["kp_range"] = kp_range.tolist()
        result["analysis"]["ki_range"] = ki_range.tolist()

        result["recommendations"].append({
            "parameter": "governor_kp",
            "optimal_value": best_kp,
            "recommended_range": (max(1.0, best_kp - 0.5), min(5.0, best_kp + 0.5)),
            "description": f"建议Kp取值{best_kp:.2f}，范围{best_kp-0.5:.2f}~{best_kp+0.5:.2f}",
        })

        result["recommendations"].append({
            "parameter": "governor_ki",
            "optimal_value": best_ki,
            "recommended_range": (max(0.05, best_ki - 0.1), min(0.5, best_ki + 0.1)),
            "description": f"建议Ki取值{best_ki:.2f}，范围{best_ki-0.1:.2f}~{best_ki+0.1:.2f}",
        })

        # 识别敏感区域（振荡风险高的区域）
        unstable_mask = stability_map < 0.5
        if np.any(unstable_mask):
            unstable_indices = np.where(unstable_mask)
            for idx in range(min(5, len(unstable_indices[0]))):
                i, j = unstable_indices[0][idx], unstable_indices[1][idx]
                result["sensitive_regions"].append({
                    "kp": kp_range[i],
                    "ki": ki_range[j],
                    "risk": "high_oscillation",
                    "description": f"Kp={kp_range[i]:.2f}, Ki={ki_range[j]:.2f}区域存在振荡风险",
                })

        self.optimization_results.append(result)
        return result

    def generate_design_feedback_report(self) -> str:
        """生成设计反馈报告"""
        report = """
# 反向设计优化报告

## 1. 优化概要

本报告基于在环验证结果，对以下关键设计参数提出优化建议：

"""
        for i, result in enumerate(self.optimization_results):
            report += f"### 1.{i+1} {result['issue']}\n\n"

            if result.get("recommendations"):
                report += "**优化建议:**\n\n"
                for rec in result["recommendations"]:
                    report += f"- **{rec['parameter']}**: {rec['description']}\n"
                    if "optimal_value" in rec:
                        report += f"  - 建议值: {rec['optimal_value']}\n"
                    if "recommended_range" in rec:
                        report += f"  - 建议范围: {rec['recommended_range']}\n"
                report += "\n"

            if result.get("sensitive_regions"):
                report += "**敏感区域警示:**\n\n"
                for region in result["sensitive_regions"]:
                    report += f"- {region['description']}\n"
                report += "\n"

        report += """
## 2. 实施建议

1. 优先实施压力安全相关的参数优化
2. 在仿真环境中验证参数调整效果
3. 分阶段实施，每阶段进行HIL验证
4. 保留参数调整回退机制

## 3. 验证要求

- 所有参数调整需通过SIL测试
- 关键参数需通过HIL验证
- 验证覆盖率需达到ODD规定的100%场景
"""

        return report


def create_yajiang_mbd_model() -> CascadeHydropowerModel:
    """创建雅鲁藏布江大拐弯工程MBD模型"""
    model = CascadeHydropowerModel()

    # 添加五个梯级电站
    stations = [
        {"id": "YJ01", "name": "墨脱", "rated_pressure": 4.7, "rated_flow": 210, "rated_power": 1000, "rated_speed": 166.7, "max_flow": 250, "inertia": 4.0},
        {"id": "YJ02", "name": "多雄藏布", "rated_pressure": 4.4, "rated_flow": 200, "rated_power": 800, "rated_speed": 166.7, "max_flow": 240, "inertia": 4.0},
        {"id": "YJ03", "name": "达木", "rated_pressure": 3.9, "rated_flow": 180, "rated_power": 600, "rated_speed": 150, "max_flow": 220, "inertia": 3.5},
        {"id": "YJ04", "name": "巴玉", "rated_pressure": 3.4, "rated_flow": 160, "rated_power": 500, "rated_speed": 150, "max_flow": 200, "inertia": 3.5},
        {"id": "YJ05", "name": "通德", "rated_pressure": 2.9, "rated_flow": 150, "rated_power": 400, "rated_speed": 125, "max_flow": 180, "inertia": 3.0},
    ]

    for station in stations:
        model.add_station(station)

    return model
