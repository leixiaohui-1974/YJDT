# -*- coding: utf-8 -*-
"""
MBD优化设计框架 - Design Optimization Framework

完整的优化设计方法论：
1. 优化算法体系 - 针对不同问题选择合适算法
2. 设计-验证-反馈闭环 - 持续改进机制
3. 灵活性量化与优化 - 提升运行适应能力
4. 安全性量化与优化 - 保障系统可靠运行

设计理念：
- 基于ODD的约束优化
- 基于仿真的验证反馈
- 多目标Pareto优化
- 鲁棒性设计
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import logging
from scipy.optimize import (
    minimize, differential_evolution, dual_annealing,
    shgo, basinhopping, NonlinearConstraint
)
from scipy.stats import qmc
import copy

logger = logging.getLogger(__name__)


# ==============================================================================
# 优化算法体系
# ==============================================================================

class OptimizationAlgorithm(Enum):
    """优化算法类型"""
    # 梯度类算法
    GRADIENT_DESCENT = "gradient_descent"       # 简单问题
    BFGS = "bfgs"                               # 光滑凸问题
    L_BFGS_B = "l_bfgs_b"                       # 带边界约束
    SLSQP = "slsqp"                             # 带约束非线性规划
    TRUST_CONSTR = "trust_constr"               # 信赖域约束优化

    # 全局优化算法
    DIFFERENTIAL_EVOLUTION = "de"               # 差分进化
    GENETIC_ALGORITHM = "ga"                    # 遗传算法
    PARTICLE_SWARM = "pso"                      # 粒子群优化
    SIMULATED_ANNEALING = "sa"                  # 模拟退火
    BASIN_HOPPING = "basin_hopping"             # 盆地跳跃

    # 多目标优化
    NSGA_II = "nsga2"                           # 非支配排序遗传算法
    NSGA_III = "nsga3"                          # 参考点NSGA
    MOEAD = "moead"                             # 多目标分解进化

    # 代理模型优化
    BAYESIAN = "bayesian"                       # 贝叶斯优化
    SURROGATE = "surrogate"                     # 代理模型优化

    # 鲁棒优化
    ROBUST = "robust"                           # 鲁棒优化
    STOCHASTIC = "stochastic"                   # 随机优化


class ProblemType(Enum):
    """问题类型"""
    SINGLE_OBJECTIVE_UNCONSTRAINED = "single_unconstrained"
    SINGLE_OBJECTIVE_CONSTRAINED = "single_constrained"
    MULTI_OBJECTIVE = "multi_objective"
    ROBUST_OPTIMIZATION = "robust"
    DYNAMIC_OPTIMIZATION = "dynamic"
    MIXED_INTEGER = "mixed_integer"


@dataclass
class OptimizationProblem:
    """优化问题定义"""
    name: str
    problem_type: ProblemType

    # 设计变量
    variables: List[Dict[str, Any]]  # [{name, lb, ub, type}]

    # 目标函数
    objectives: List[Dict[str, Any]]  # [{name, func, weight, direction}]

    # 约束条件
    constraints: List[Dict[str, Any]] = field(default_factory=list)

    # ODD边界约束
    odd_constraints: Dict[str, Any] = field(default_factory=dict)

    # 仿真模型
    simulation_model: Callable = None


@dataclass
class AlgorithmConfig:
    """算法配置"""
    algorithm: OptimizationAlgorithm
    max_iterations: int = 100
    population_size: int = 50
    tolerance: float = 1e-6

    # 算法特定参数
    params: Dict[str, Any] = field(default_factory=dict)


class AlgorithmSelector:
    """
    算法选择器

    根据问题特征自动选择合适的优化算法
    """

    def __init__(self):
        self.selection_rules = self._init_selection_rules()

    def _init_selection_rules(self) -> Dict[str, List[OptimizationAlgorithm]]:
        """初始化选择规则"""
        return {
            "convex_smooth": [
                OptimizationAlgorithm.BFGS,
                OptimizationAlgorithm.L_BFGS_B,
            ],
            "constrained": [
                OptimizationAlgorithm.SLSQP,
                OptimizationAlgorithm.TRUST_CONSTR,
            ],
            "nonconvex": [
                OptimizationAlgorithm.DIFFERENTIAL_EVOLUTION,
                OptimizationAlgorithm.BASIN_HOPPING,
            ],
            "high_dimensional": [
                OptimizationAlgorithm.DIFFERENTIAL_EVOLUTION,
                OptimizationAlgorithm.PARTICLE_SWARM,
            ],
            "expensive_evaluation": [
                OptimizationAlgorithm.BAYESIAN,
                OptimizationAlgorithm.SURROGATE,
            ],
            "multi_objective": [
                OptimizationAlgorithm.NSGA_II,
                OptimizationAlgorithm.NSGA_III,
                OptimizationAlgorithm.MOEAD,
            ],
            "uncertain_parameters": [
                OptimizationAlgorithm.ROBUST,
                OptimizationAlgorithm.STOCHASTIC,
            ],
        }

    def select(self, problem: OptimizationProblem) -> AlgorithmConfig:
        """根据问题选择算法"""
        n_vars = len(problem.variables)
        n_obj = len(problem.objectives)
        n_constraints = len(problem.constraints)

        # 多目标问题
        if n_obj > 1 or problem.problem_type == ProblemType.MULTI_OBJECTIVE:
            if n_obj <= 3:
                return AlgorithmConfig(
                    algorithm=OptimizationAlgorithm.NSGA_II,
                    population_size=max(50, n_vars * 10),
                    max_iterations=200,
                    params={"crossover_prob": 0.9, "mutation_prob": 0.1}
                )
            else:
                return AlgorithmConfig(
                    algorithm=OptimizationAlgorithm.NSGA_III,
                    population_size=max(100, n_vars * 20),
                    max_iterations=300,
                )

        # 鲁棒优化
        if problem.problem_type == ProblemType.ROBUST_OPTIMIZATION:
            return AlgorithmConfig(
                algorithm=OptimizationAlgorithm.ROBUST,
                max_iterations=100,
                params={"n_samples": 100}
            )

        # 带约束问题
        if n_constraints > 0:
            if n_vars <= 20:
                return AlgorithmConfig(
                    algorithm=OptimizationAlgorithm.SLSQP,
                    max_iterations=200,
                )
            else:
                return AlgorithmConfig(
                    algorithm=OptimizationAlgorithm.DIFFERENTIAL_EVOLUTION,
                    population_size=min(100, n_vars * 5),
                    max_iterations=500,
                )

        # 高维问题
        if n_vars > 50:
            return AlgorithmConfig(
                algorithm=OptimizationAlgorithm.DIFFERENTIAL_EVOLUTION,
                population_size=min(200, n_vars * 3),
                max_iterations=1000,
            )

        # 默认
        return AlgorithmConfig(
            algorithm=OptimizationAlgorithm.L_BFGS_B,
            max_iterations=100,
        )


class UnifiedOptimizer:
    """
    统一优化器

    封装多种优化算法，提供统一接口
    """

    def __init__(self):
        self.algorithm_selector = AlgorithmSelector()
        self.history = []

    def optimize(self,
                 problem: OptimizationProblem,
                 config: AlgorithmConfig = None) -> Dict[str, Any]:
        """
        执行优化

        Args:
            problem: 优化问题定义
            config: 算法配置（可选，自动选择）

        Returns:
            优化结果
        """
        if config is None:
            config = self.algorithm_selector.select(problem)

        logger.info(f"使用算法: {config.algorithm.value}")

        # 构建边界
        bounds = [(v["lb"], v["ub"]) for v in problem.variables]

        # 构建目标函数
        def objective(x):
            params = {v["name"]: x[i] for i, v in enumerate(problem.variables)}
            total = 0
            for obj in problem.objectives:
                val = obj["func"](params)
                weight = obj.get("weight", 1.0)
                direction = obj.get("direction", "minimize")
                if direction == "maximize":
                    val = -val
                total += weight * val
            return total

        # 构建约束
        scipy_constraints = []
        for c in problem.constraints:
            if c["type"] == "eq":
                scipy_constraints.append({
                    'type': 'eq',
                    'fun': lambda x, cf=c: cf["func"]({
                        v["name"]: x[i] for i, v in enumerate(problem.variables)
                    })
                })
            else:
                scipy_constraints.append({
                    'type': 'ineq',
                    'fun': lambda x, cf=c: cf["func"]({
                        v["name"]: x[i] for i, v in enumerate(problem.variables)
                    })
                })

        # 执行优化
        result = self._run_algorithm(
            config, objective, bounds, scipy_constraints, problem
        )

        # 记录历史
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "problem": problem.name,
            "algorithm": config.algorithm.value,
            "result": result,
        })

        return result

    def _run_algorithm(self,
                      config: AlgorithmConfig,
                      objective: Callable,
                      bounds: List[Tuple],
                      constraints: List[Dict],
                      problem: OptimizationProblem) -> Dict[str, Any]:
        """运行指定算法"""
        algo = config.algorithm

        # 初始点
        x0 = np.array([(b[0] + b[1]) / 2 for b in bounds])

        if algo in [OptimizationAlgorithm.BFGS, OptimizationAlgorithm.L_BFGS_B]:
            result = minimize(
                objective, x0,
                method='L-BFGS-B',
                bounds=bounds,
                options={'maxiter': config.max_iterations}
            )

        elif algo == OptimizationAlgorithm.SLSQP:
            result = minimize(
                objective, x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': config.max_iterations}
            )

        elif algo == OptimizationAlgorithm.TRUST_CONSTR:
            result = minimize(
                objective, x0,
                method='trust-constr',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': config.max_iterations}
            )

        elif algo == OptimizationAlgorithm.DIFFERENTIAL_EVOLUTION:
            result = differential_evolution(
                objective,
                bounds,
                maxiter=config.max_iterations,
                popsize=config.population_size // len(bounds),
                seed=42
            )

        elif algo == OptimizationAlgorithm.SIMULATED_ANNEALING:
            result = dual_annealing(
                objective,
                bounds,
                maxiter=config.max_iterations,
            )

        elif algo == OptimizationAlgorithm.BASIN_HOPPING:
            result = basinhopping(
                objective, x0,
                minimizer_kwargs={"bounds": bounds},
                niter=config.max_iterations,
            )

        elif algo == OptimizationAlgorithm.NSGA_II:
            result = self._run_nsga2(problem, config)

        elif algo == OptimizationAlgorithm.ROBUST:
            result = self._run_robust_optimization(problem, config)

        else:
            # 默认使用差分进化
            result = differential_evolution(
                objective, bounds,
                maxiter=config.max_iterations,
            )

        # 格式化结果
        return self._format_result(result, problem)

    def _run_nsga2(self,
                   problem: OptimizationProblem,
                   config: AlgorithmConfig) -> Dict[str, Any]:
        """NSGA-II多目标优化"""
        n_vars = len(problem.variables)
        n_obj = len(problem.objectives)
        pop_size = config.population_size
        n_gen = config.max_iterations

        bounds = [(v["lb"], v["ub"]) for v in problem.variables]

        # 初始化种群
        sampler = qmc.LatinHypercube(d=n_vars)
        sample = sampler.random(n=pop_size)
        l_bounds = np.array([b[0] for b in bounds])
        u_bounds = np.array([b[1] for b in bounds])
        population = qmc.scale(sample, l_bounds, u_bounds)

        # 评估函数
        def evaluate(x):
            params = {v["name"]: x[i] for i, v in enumerate(problem.variables)}
            objectives = []
            for obj in problem.objectives:
                val = obj["func"](params)
                direction = obj.get("direction", "minimize")
                if direction == "maximize":
                    val = -val
                objectives.append(val)
            return objectives

        # 进化
        for gen in range(n_gen):
            # 评估
            fitness = np.array([evaluate(ind) for ind in population])

            # 非支配排序
            fronts = self._non_dominated_sort(fitness)

            # 拥挤距离
            for front in fronts:
                self._compute_crowding_distance(front, fitness)

            # 选择、交叉、变异
            offspring = self._create_offspring(population, fronts, fitness, bounds)

            # 合并
            combined = np.vstack([population, offspring])
            combined_fitness = np.array([evaluate(ind) for ind in combined])

            # 环境选择
            population = self._environmental_selection(
                combined, combined_fitness, pop_size
            )

        # 最终Pareto前沿
        final_fitness = np.array([evaluate(ind) for ind in population])
        fronts = self._non_dominated_sort(final_fitness)
        pareto_front = population[fronts[0]]
        pareto_objectives = final_fitness[fronts[0]]

        return {
            "success": True,
            "pareto_front": pareto_front.tolist(),
            "pareto_objectives": pareto_objectives.tolist(),
            "n_solutions": len(fronts[0]),
        }

    def _run_robust_optimization(self,
                                problem: OptimizationProblem,
                                config: AlgorithmConfig) -> Dict[str, Any]:
        """鲁棒优化"""
        n_samples = config.params.get("n_samples", 100)
        bounds = [(v["lb"], v["ub"]) for v in problem.variables]

        def robust_objective(x):
            params = {v["name"]: x[i] for i, v in enumerate(problem.variables)}

            # 生成不确定性样本
            samples = []
            for _ in range(n_samples):
                perturbed = params.copy()
                for v in problem.variables:
                    if v.get("uncertain", False):
                        delta = v.get("uncertainty", 0.05)
                        perturbed[v["name"]] *= (1 + np.random.uniform(-delta, delta))
                samples.append(perturbed)

            # 计算期望和方差
            objectives = []
            for sample in samples:
                val = 0
                for obj in problem.objectives:
                    val += obj["func"](sample)
                objectives.append(val)

            mean = np.mean(objectives)
            std = np.std(objectives)

            # 鲁棒目标 = 期望 + k*标准差
            k = config.params.get("robustness_factor", 2.0)
            return mean + k * std

        result = differential_evolution(
            robust_objective,
            bounds,
            maxiter=config.max_iterations,
        )

        return {
            "success": result.success,
            "x": result.x.tolist(),
            "fun": result.fun,
            "message": "Robust optimization completed"
        }

    def _non_dominated_sort(self, fitness: np.ndarray) -> List[List[int]]:
        """非支配排序"""
        n = len(fitness)
        domination_count = [0] * n
        dominated = [[] for _ in range(n)]
        fronts = [[]]

        for i in range(n):
            for j in range(i + 1, n):
                if self._dominates(fitness[i], fitness[j]):
                    dominated[i].append(j)
                    domination_count[j] += 1
                elif self._dominates(fitness[j], fitness[i]):
                    dominated[j].append(i)
                    domination_count[i] += 1

        for i in range(n):
            if domination_count[i] == 0:
                fronts[0].append(i)

        k = 0
        while fronts[k]:
            next_front = []
            for i in fronts[k]:
                for j in dominated[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            k += 1
            if next_front:
                fronts.append(next_front)
            else:
                break

        return fronts

    def _dominates(self, a: np.ndarray, b: np.ndarray) -> bool:
        """判断a是否支配b（所有目标都最小化）"""
        return np.all(a <= b) and np.any(a < b)

    def _compute_crowding_distance(self, front: List[int], fitness: np.ndarray):
        """计算拥挤距离"""
        pass  # 简化实现

    def _create_offspring(self, population, fronts, fitness, bounds):
        """创建子代"""
        n = len(population)
        offspring = np.zeros_like(population)

        for i in range(n):
            # 锦标赛选择
            p1, p2 = np.random.choice(n, 2, replace=False)
            parent1 = population[p1]
            parent2 = population[p2]

            # SBX交叉
            child = 0.5 * (parent1 + parent2)

            # 多项式变异
            for j in range(len(child)):
                if np.random.random() < 0.1:
                    delta = 0.1 * (bounds[j][1] - bounds[j][0])
                    child[j] += np.random.uniform(-delta, delta)
                    child[j] = np.clip(child[j], bounds[j][0], bounds[j][1])

            offspring[i] = child

        return offspring

    def _environmental_selection(self, population, fitness, size):
        """环境选择"""
        fronts = self._non_dominated_sort(fitness)
        selected = []

        for front in fronts:
            if len(selected) + len(front) <= size:
                selected.extend(front)
            else:
                remaining = size - len(selected)
                selected.extend(front[:remaining])
                break

        return population[selected]

    def _format_result(self,
                      result: Any,
                      problem: OptimizationProblem) -> Dict[str, Any]:
        """格式化结果"""
        if isinstance(result, dict):
            return result

        optimal_params = {}
        if hasattr(result, 'x'):
            for i, v in enumerate(problem.variables):
                optimal_params[v["name"]] = float(result.x[i])

        return {
            "success": result.success if hasattr(result, 'success') else True,
            "optimal_parameters": optimal_params,
            "optimal_value": float(result.fun) if hasattr(result, 'fun') else 0,
            "message": result.message if hasattr(result, 'message') else "",
            "iterations": result.nit if hasattr(result, 'nit') else 0,
        }


# ==============================================================================
# 设计-验证-反馈闭环
# ==============================================================================

@dataclass
class VerificationResult:
    """验证结果"""
    passed: bool
    metrics: Dict[str, float]
    violations: List[str]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DesignFeedback:
    """设计反馈"""
    parameter_adjustments: Dict[str, Dict[str, float]]  # {param: {direction, magnitude}}
    priority: int
    reason: str
    expected_improvement: Dict[str, float]


class DesignVerificationLoop:
    """
    设计-验证-反馈闭环

    流程：
    1. 设计参数优化
    2. 仿真验证
    3. ODD边界检查
    4. 性能评估
    5. 反馈生成
    6. 参数调整
    """

    def __init__(self, optimizer: UnifiedOptimizer, simulator=None, odd=None):
        self.optimizer = optimizer
        self.simulator = simulator
        self.odd = odd
        self.iteration_history = []

    def run_design_loop(self,
                        problem: OptimizationProblem,
                        max_iterations: int = 10,
                        convergence_threshold: float = 0.01) -> Dict[str, Any]:
        """
        运行设计闭环

        Args:
            problem: 优化问题
            max_iterations: 最大迭代次数
            convergence_threshold: 收敛阈值

        Returns:
            最终设计结果
        """
        current_design = None
        prev_performance = float('inf')

        for iteration in range(max_iterations):
            logger.info(f"设计闭环迭代 {iteration + 1}/{max_iterations}")

            # 1. 优化设计
            if current_design is None:
                opt_result = self.optimizer.optimize(problem)
            else:
                # 基于反馈调整问题
                adjusted_problem = self._apply_feedback(problem, feedback)
                opt_result = self.optimizer.optimize(adjusted_problem)

            current_design = opt_result.get("optimal_parameters", {})

            # 2. 仿真验证
            sim_result = self._run_simulation(current_design)

            # 3. ODD边界检查
            odd_check = self._check_odd_boundaries(current_design, sim_result)

            # 4. 性能评估
            performance = self._evaluate_performance(sim_result, odd_check)

            # 5. 生成反馈
            feedback = self._generate_feedback(
                current_design, sim_result, odd_check, performance
            )

            # 记录
            self.iteration_history.append({
                "iteration": iteration,
                "design": current_design.copy(),
                "performance": performance,
                "feedback": feedback,
            })

            # 6. 检查收敛
            improvement = (prev_performance - performance["total_score"]) / max(prev_performance, 1e-10)
            if abs(improvement) < convergence_threshold and iteration > 0:
                logger.info(f"设计收敛于迭代 {iteration + 1}")
                break

            prev_performance = performance["total_score"]

        return {
            "final_design": current_design,
            "final_performance": performance,
            "iterations": len(self.iteration_history),
            "convergence": improvement < convergence_threshold,
            "history": self.iteration_history,
        }

    def _run_simulation(self, design: Dict[str, float]) -> Dict[str, Any]:
        """运行仿真验证"""
        if self.simulator is None:
            # 简化仿真
            return self._simplified_simulation(design)

        return self.simulator.run(design)

    def _simplified_simulation(self, design: Dict[str, float]) -> Dict[str, Any]:
        """简化仿真"""
        # 模拟典型工况响应
        result = {
            "steady_state": {},
            "transient": {},
            "extreme": {},
        }

        # 稳态性能
        Kp = design.get("governor_kp", 2.5)
        Ki = design.get("governor_ki", 0.15)

        result["steady_state"]["frequency_deviation"] = 0.05 / Kp
        result["steady_state"]["power_accuracy"] = 0.98

        # 过渡过程
        Tw = design.get("water_inertia", 12.0)
        result["transient"]["settling_time"] = 10 + Tw
        result["transient"]["overshoot"] = 5 + 2 * Kp
        result["transient"]["pressure_rise"] = 1.2 + 0.05 * design.get("guide_vane_rate", 0.1) * 10

        # 极端工况
        result["extreme"]["max_speed_rise"] = 1.3 + 0.1 * Kp
        result["extreme"]["min_pressure"] = 0.7 - 0.01 * Tw

        return result

    def _check_odd_boundaries(self,
                             design: Dict[str, float],
                             sim_result: Dict[str, Any]) -> Dict[str, Any]:
        """ODD边界检查"""
        violations = []
        margins = {}

        # 定义ODD边界
        odd_limits = {
            "pressure_rise": {"max": 1.3, "warning": 1.2},
            "speed_rise": {"max": 1.4, "warning": 1.2},
            "settling_time": {"max": 60, "warning": 40},
            "overshoot": {"max": 20, "warning": 10},
        }

        # 检查
        transient = sim_result.get("transient", {})
        extreme = sim_result.get("extreme", {})

        # 压力升
        pressure_rise = transient.get("pressure_rise", 1.0)
        if pressure_rise > odd_limits["pressure_rise"]["max"]:
            violations.append(f"压力升{pressure_rise:.2f}超过ODD限值{odd_limits['pressure_rise']['max']}")
        margins["pressure_rise"] = odd_limits["pressure_rise"]["max"] - pressure_rise

        # 转速升
        speed_rise = extreme.get("max_speed_rise", 1.0)
        if speed_rise > odd_limits["speed_rise"]["max"]:
            violations.append(f"转速升{speed_rise:.2f}超过ODD限值")
        margins["speed_rise"] = odd_limits["speed_rise"]["max"] - speed_rise

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "margins": margins,
        }

    def _evaluate_performance(self,
                             sim_result: Dict[str, Any],
                             odd_check: Dict[str, Any]) -> Dict[str, float]:
        """性能评估"""
        scores = {}

        # 安全性评分
        safety_score = 100
        for violation in odd_check.get("violations", []):
            safety_score -= 20
        safety_score = max(0, safety_score)
        scores["safety"] = safety_score

        # 稳定性评分
        transient = sim_result.get("transient", {})
        settling = transient.get("settling_time", 60)
        overshoot = transient.get("overshoot", 20)
        stability_score = 100 - settling / 60 * 30 - overshoot / 20 * 20
        scores["stability"] = max(0, stability_score)

        # 灵活性评分（响应速度）
        flexibility_score = 100 - settling / 30 * 50
        scores["flexibility"] = max(0, flexibility_score)

        # 经济性评分（效率相关）
        steady = sim_result.get("steady_state", {})
        accuracy = steady.get("power_accuracy", 0.95)
        economy_score = accuracy * 100
        scores["economy"] = economy_score

        # 总分
        weights = {"safety": 0.4, "stability": 0.25, "flexibility": 0.2, "economy": 0.15}
        total = sum(scores[k] * weights[k] for k in weights)
        scores["total_score"] = total

        return scores

    def _generate_feedback(self,
                          design: Dict[str, float],
                          sim_result: Dict[str, Any],
                          odd_check: Dict[str, Any],
                          performance: Dict[str, float]) -> DesignFeedback:
        """生成设计反馈"""
        adjustments = {}
        reasons = []

        # 基于ODD违规生成反馈
        if odd_check.get("violations"):
            for violation in odd_check["violations"]:
                if "压力升" in violation:
                    adjustments["guide_vane_rate"] = {"direction": "decrease", "magnitude": 0.1}
                    reasons.append("降低导叶动作速率以减小压力升")
                if "转速升" in violation:
                    adjustments["governor_kp"] = {"direction": "decrease", "magnitude": 0.2}
                    reasons.append("降低调速器增益以减小转速升")

        # 基于性能评分生成反馈
        if performance["flexibility"] < 70:
            adjustments["governor_kp"] = {"direction": "increase", "magnitude": 0.1}
            reasons.append("提高调速器增益以改善响应速度")

        if performance["stability"] < 70:
            adjustments["governor_ki"] = {"direction": "decrease", "magnitude": 0.1}
            reasons.append("降低积分增益以改善稳定性")

        return DesignFeedback(
            parameter_adjustments=adjustments,
            priority=1 if odd_check.get("violations") else 2,
            reason="; ".join(reasons) if reasons else "性能满足要求",
            expected_improvement={
                "safety": 10 if adjustments else 0,
                "stability": 5 if "ki" in str(adjustments) else 0,
                "flexibility": 5 if "kp" in str(adjustments) else 0,
            }
        )

    def _apply_feedback(self,
                        problem: OptimizationProblem,
                        feedback: DesignFeedback) -> OptimizationProblem:
        """应用反馈调整问题"""
        adjusted = copy.deepcopy(problem)

        for param, adjustment in feedback.parameter_adjustments.items():
            for var in adjusted.variables:
                if var["name"] == param:
                    direction = adjustment["direction"]
                    magnitude = adjustment["magnitude"]

                    if direction == "increase":
                        # 收紧下界
                        var["lb"] = var["lb"] + (var["ub"] - var["lb"]) * magnitude
                    else:
                        # 收紧上界
                        var["ub"] = var["ub"] - (var["ub"] - var["lb"]) * magnitude

        return adjusted


# ==============================================================================
# 灵活性量化与优化
# ==============================================================================

class FlexibilityMetrics(Enum):
    """灵活性指标"""
    RESPONSE_SPEED = "response_speed"           # 响应速度
    REGULATION_RANGE = "regulation_range"       # 调节范围
    RAMPING_RATE = "ramping_rate"               # 爬坡速率
    OPERATING_RANGE = "operating_range"         # 运行范围
    STARTUP_TIME = "startup_time"               # 启动时间
    MINIMUM_LOAD = "minimum_load"               # 最小负荷
    COORDINATION_CAPABILITY = "coordination"    # 协调能力


class FlexibilityOptimizer:
    """
    灵活性优化器

    提升系统运行灵活性
    """

    def __init__(self):
        self.flexibility_targets = {}
        self.optimization_results = {}

    def set_flexibility_targets(self, targets: Dict[str, float]):
        """设置灵活性目标"""
        self.flexibility_targets = targets

    def optimize_response_speed(self,
                               current_settling_time: float = 30,
                               target_settling_time: float = 15) -> Dict[str, Any]:
        """
        优化响应速度

        通过调整控制参数提升响应速度
        """
        # 影响因素分析
        factors = {
            "governor_gain": {
                "sensitivity": 0.8,
                "adjustment_range": (1.5, 4.0),
                "current": 2.5,
            },
            "governor_derivative": {
                "sensitivity": 0.3,
                "adjustment_range": (0, 8),
                "current": 4.0,
            },
            "guide_vane_rate": {
                "sensitivity": 0.5,
                "adjustment_range": (0.03, 0.15),
                "current": 0.08,
            },
        }

        # 优化
        improvement_ratio = target_settling_time / current_settling_time

        recommendations = []
        for factor, info in factors.items():
            if info["sensitivity"] > 0.5:
                current = info["current"]
                adjustment = (1 / improvement_ratio - 1) * info["sensitivity"]
                new_value = current * (1 + adjustment)
                new_value = np.clip(new_value, *info["adjustment_range"])

                recommendations.append({
                    "parameter": factor,
                    "current_value": current,
                    "recommended_value": new_value,
                    "expected_improvement": f"{(1 - new_value/current) * 100:.1f}%",
                })

        return {
            "current_settling_time": current_settling_time,
            "target_settling_time": target_settling_time,
            "recommendations": recommendations,
            "constraints": ["压力升限制", "稳定性裕度"],
        }

    def optimize_ramping_rate(self,
                             current_rate: float = 5,
                             target_rate: float = 10) -> Dict[str, Any]:
        """
        优化爬坡速率

        提升负荷跟踪能力
        """
        # 限制因素
        limitations = {
            "water_hammer": {
                "current_limit": 8,  # %/min
                "relaxation_method": "增大调压室容积",
            },
            "cavitation": {
                "current_limit": 12,
                "relaxation_method": "优化运行水头范围",
            },
            "thermal_stress": {
                "current_limit": 15,
                "relaxation_method": "改进冷却系统",
            },
        }

        # 确定主要限制
        bottleneck = min(limitations.items(), key=lambda x: x[1]["current_limit"])

        recommendations = []
        if target_rate > bottleneck[1]["current_limit"]:
            recommendations.append({
                "bottleneck": bottleneck[0],
                "current_limit": bottleneck[1]["current_limit"],
                "required_relaxation": target_rate - bottleneck[1]["current_limit"],
                "method": bottleneck[1]["relaxation_method"],
            })

        achievable_rate = min(target_rate, min(v["current_limit"] for v in limitations.values()))

        return {
            "current_rate": current_rate,
            "target_rate": target_rate,
            "achievable_rate": achievable_rate,
            "limitations": limitations,
            "recommendations": recommendations,
        }

    def optimize_operating_range(self,
                                current_min_load: float = 0.4,
                                target_min_load: float = 0.25) -> Dict[str, Any]:
        """
        优化运行范围

        扩展低负荷运行能力
        """
        # 低负荷运行限制因素
        low_load_issues = {
            "efficiency_drop": {
                "threshold": 0.30,
                "impact": "效率降低10-15%",
                "mitigation": "优化导叶开度曲线",
            },
            "cavitation_risk": {
                "threshold": 0.35,
                "impact": "空化风险增加",
                "mitigation": "降低运行水头或增加吸出高度",
            },
            "vibration": {
                "threshold": 0.25,
                "impact": "振动增大",
                "mitigation": "避开振动区运行",
            },
            "flame_stability": {
                "threshold": 0.20,
                "impact": "不稳定运行",
                "mitigation": "增加稳定运行措施",
            },
        }

        # 优化建议
        recommendations = []
        for issue, info in low_load_issues.items():
            if target_min_load < info["threshold"]:
                recommendations.append({
                    "issue": issue,
                    "threshold": info["threshold"],
                    "impact": info["impact"],
                    "mitigation": info["mitigation"],
                })

        achievable_min_load = max(
            target_min_load,
            max(info["threshold"] for info in low_load_issues.values() if target_min_load < info["threshold"]) if any(target_min_load < info["threshold"] for info in low_load_issues.values()) else target_min_load
        )

        return {
            "current_min_load": current_min_load,
            "target_min_load": target_min_load,
            "achievable_min_load": achievable_min_load,
            "operating_range_expansion": (current_min_load - achievable_min_load) * 100,
            "recommendations": recommendations,
        }

    def calculate_flexibility_score(self,
                                   system_params: Dict[str, float]) -> Dict[str, float]:
        """计算灵活性综合评分"""
        scores = {}

        # 响应速度评分
        settling_time = system_params.get("settling_time", 30)
        scores["response_speed"] = max(0, 100 - settling_time * 2)

        # 调节范围评分
        min_load = system_params.get("min_load", 0.4)
        scores["operating_range"] = (1 - min_load) * 100

        # 爬坡速率评分
        ramping_rate = system_params.get("ramping_rate", 5)
        scores["ramping_capability"] = min(100, ramping_rate * 10)

        # 启动时间评分
        startup_time = system_params.get("startup_time", 600)
        scores["startup_speed"] = max(0, 100 - startup_time / 60 * 10)

        # 综合评分
        weights = {
            "response_speed": 0.3,
            "operating_range": 0.25,
            "ramping_capability": 0.25,
            "startup_speed": 0.2,
        }
        scores["total"] = sum(scores[k] * weights.get(k, 0.25) for k in scores if k != "total")

        return scores


# ==============================================================================
# 安全性量化与优化
# ==============================================================================

class SafetyMetrics(Enum):
    """安全性指标"""
    PRESSURE_MARGIN = "pressure_margin"         # 压力裕度
    SPEED_MARGIN = "speed_margin"               # 转速裕度
    STABILITY_MARGIN = "stability_margin"       # 稳定裕度
    PROTECTION_RELIABILITY = "protection"       # 保护可靠性
    FAILURE_PROBABILITY = "failure_prob"        # 失效概率
    MTBF = "mtbf"                               # 平均故障间隔


class SafetyOptimizer:
    """
    安全性优化器

    提升系统运行安全性
    """

    def __init__(self):
        self.safety_targets = {}
        self.optimization_results = {}

    def optimize_pressure_margin(self,
                                current_margin: float = 0.2,
                                target_margin: float = 0.3) -> Dict[str, Any]:
        """
        优化压力安全裕度

        减小水锤压力升，增加安全裕度
        """
        methods = [
            {
                "method": "降低导叶关闭速率",
                "effectiveness": 0.4,
                "side_effects": ["响应速度降低"],
                "implementation": "调整导叶伺服系统",
            },
            {
                "method": "优化两段关闭规律",
                "effectiveness": 0.3,
                "side_effects": ["控制复杂度增加"],
                "implementation": "重新整定关闭曲线",
            },
            {
                "method": "增大调压室容积",
                "effectiveness": 0.5,
                "side_effects": ["投资增加"],
                "implementation": "土建改造",
            },
            {
                "method": "增设泄压阀",
                "effectiveness": 0.2,
                "side_effects": ["维护成本"],
                "implementation": "增加设备",
            },
        ]

        # 计算所需改进
        improvement_needed = target_margin - current_margin
        total_effectiveness = sum(m["effectiveness"] for m in methods)

        selected_methods = []
        cumulative_improvement = 0
        for method in sorted(methods, key=lambda x: -x["effectiveness"]):
            if cumulative_improvement >= improvement_needed:
                break
            contribution = method["effectiveness"] * improvement_needed / total_effectiveness
            selected_methods.append({
                **method,
                "contribution": contribution,
            })
            cumulative_improvement += contribution

        return {
            "current_margin": current_margin,
            "target_margin": target_margin,
            "achievable_margin": current_margin + cumulative_improvement,
            "selected_methods": selected_methods,
        }

    def optimize_stability_margin(self,
                                 current_phase_margin: float = 30,
                                 target_phase_margin: float = 45) -> Dict[str, Any]:
        """
        优化稳定性裕度

        增加相位裕度和增益裕度
        """
        adjustments = []

        # 相位裕度不足
        if current_phase_margin < target_phase_margin:
            # 降低调速器增益
            gain_reduction = (target_phase_margin - current_phase_margin) / 15 * 0.3
            adjustments.append({
                "parameter": "governor_kp",
                "action": "decrease",
                "magnitude": gain_reduction,
                "expected_improvement": f"+{target_phase_margin - current_phase_margin:.0f}°相位裕度",
            })

            # 增加超前补偿
            adjustments.append({
                "parameter": "lead_compensator",
                "action": "add",
                "magnitude": (target_phase_margin - current_phase_margin) / 45,
                "expected_improvement": "改善相位特性",
            })

        return {
            "current_phase_margin": current_phase_margin,
            "target_phase_margin": target_phase_margin,
            "adjustments": adjustments,
            "stability_analysis_required": True,
        }

    def optimize_protection_reliability(self,
                                       current_reliability: float = 0.99,
                                       target_reliability: float = 0.9999) -> Dict[str, Any]:
        """
        优化保护系统可靠性
        """
        enhancement_measures = [
            {
                "measure": "增加保护冗余",
                "reliability_improvement": 0.1,
                "implementation": "双重化/三重化保护",
            },
            {
                "measure": "缩短自检周期",
                "reliability_improvement": 0.05,
                "implementation": "增加在线监测",
            },
            {
                "measure": "改进保护逻辑",
                "reliability_improvement": 0.03,
                "implementation": "优化判据",
            },
            {
                "measure": "提高元件可靠性",
                "reliability_improvement": 0.02,
                "implementation": "选用高可靠性元件",
            },
        ]

        # 可靠性计算
        current_unreliability = 1 - current_reliability
        target_unreliability = 1 - target_reliability
        required_improvement = np.log10(current_unreliability) - np.log10(target_unreliability)

        selected_measures = []
        cumulative_improvement = 0
        for measure in enhancement_measures:
            if 1 - current_reliability * (1 + cumulative_improvement) <= target_unreliability:
                break
            selected_measures.append(measure)
            cumulative_improvement += measure["reliability_improvement"]

        return {
            "current_reliability": current_reliability,
            "target_reliability": target_reliability,
            "required_improvement_orders": required_improvement,
            "selected_measures": selected_measures,
            "achievable_reliability": current_reliability * (1 + cumulative_improvement),
        }

    def calculate_safety_score(self,
                              system_params: Dict[str, float]) -> Dict[str, float]:
        """计算安全性综合评分"""
        scores = {}

        # 压力裕度评分
        pressure_margin = system_params.get("pressure_margin", 0.2)
        scores["pressure_safety"] = min(100, pressure_margin / 0.3 * 100)

        # 转速裕度评分
        speed_margin = system_params.get("speed_margin", 0.3)
        scores["speed_safety"] = min(100, speed_margin / 0.4 * 100)

        # 稳定裕度评分
        phase_margin = system_params.get("phase_margin", 30)
        scores["stability"] = min(100, phase_margin / 45 * 100)

        # 保护可靠性评分
        protection_reliability = system_params.get("protection_reliability", 0.99)
        scores["protection"] = protection_reliability * 100

        # 综合评分
        weights = {
            "pressure_safety": 0.3,
            "speed_safety": 0.25,
            "stability": 0.25,
            "protection": 0.2,
        }
        scores["total"] = sum(scores[k] * weights.get(k, 0.25) for k in scores if k != "total")

        return scores


# ==============================================================================
# 综合优化框架
# ==============================================================================

class IntegratedOptimizationFramework:
    """
    综合优化设计框架

    整合所有优化能力
    """

    def __init__(self):
        self.unified_optimizer = UnifiedOptimizer()
        self.design_loop = DesignVerificationLoop(self.unified_optimizer)
        self.flexibility_optimizer = FlexibilityOptimizer()
        self.safety_optimizer = SafetyOptimizer()

    def optimize_for_flexibility_and_safety(self,
                                           problem: OptimizationProblem,
                                           flexibility_weight: float = 0.5,
                                           safety_weight: float = 0.5) -> Dict[str, Any]:
        """
        灵活性与安全性联合优化

        平衡灵活性和安全性目标
        """
        # 构建多目标问题
        multi_obj_problem = copy.deepcopy(problem)

        # 添加灵活性目标
        multi_obj_problem.objectives.append({
            "name": "flexibility",
            "func": lambda p: -self._calc_flexibility(p),  # 最大化
            "weight": flexibility_weight,
            "direction": "maximize",
        })

        # 添加安全性目标
        multi_obj_problem.objectives.append({
            "name": "safety",
            "func": lambda p: -self._calc_safety(p),  # 最大化
            "weight": safety_weight,
            "direction": "maximize",
        })

        # 使用多目标优化
        config = AlgorithmConfig(
            algorithm=OptimizationAlgorithm.NSGA_II,
            population_size=100,
            max_iterations=200,
        )

        result = self.unified_optimizer.optimize(multi_obj_problem, config)

        return {
            "pareto_front": result.get("pareto_front", []),
            "recommended_solution": self._select_balanced_solution(result),
            "flexibility_range": self._analyze_flexibility_range(result),
            "safety_range": self._analyze_safety_range(result),
        }

    def _calc_flexibility(self, params: Dict[str, float]) -> float:
        """计算灵活性得分"""
        settling_time = 30 / (params.get("governor_kp", 2.5) / 2.5)
        ramping_rate = 5 * params.get("guide_vane_rate", 0.08) / 0.08

        return (100 - settling_time * 2) * 0.5 + ramping_rate * 10 * 0.5

    def _calc_safety(self, params: Dict[str, float]) -> float:
        """计算安全性得分"""
        # 压力裕度
        pressure_margin = 0.3 - params.get("guide_vane_rate", 0.08) * 2
        # 稳定裕度
        stability_margin = 45 - (params.get("governor_kp", 2.5) - 2) * 10

        return pressure_margin / 0.3 * 50 + stability_margin / 45 * 50

    def _select_balanced_solution(self, result: Dict) -> Dict:
        """选择平衡解"""
        pareto = result.get("pareto_front", [])
        if not pareto:
            return {}

        # 选择最接近理想点的解
        # 简化：选择中间解
        mid_idx = len(pareto) // 2
        return {"parameters": pareto[mid_idx]}

    def _analyze_flexibility_range(self, result: Dict) -> Dict:
        """分析灵活性范围"""
        return {"min": 50, "max": 90, "recommended": 70}

    def _analyze_safety_range(self, result: Dict) -> Dict:
        """分析安全性范围"""
        return {"min": 70, "max": 95, "recommended": 85}

    def generate_design_recommendations(self,
                                       current_design: Dict[str, float],
                                       target_improvements: Dict[str, float]) -> List[Dict]:
        """
        生成设计改进建议

        Args:
            current_design: 当前设计参数
            target_improvements: 目标改进 {metric: target_improvement}

        Returns:
            设计改进建议列表
        """
        recommendations = []

        for metric, target in target_improvements.items():
            if "flexibility" in metric.lower():
                flex_result = self.flexibility_optimizer.optimize_response_speed(
                    current_settling_time=current_design.get("settling_time", 30),
                    target_settling_time=current_design.get("settling_time", 30) * (1 - target)
                )
                recommendations.extend(flex_result.get("recommendations", []))

            elif "safety" in metric.lower():
                safety_result = self.safety_optimizer.optimize_pressure_margin(
                    current_margin=current_design.get("pressure_margin", 0.2),
                    target_margin=current_design.get("pressure_margin", 0.2) + target
                )
                recommendations.extend(safety_result.get("selected_methods", []))

        return recommendations
