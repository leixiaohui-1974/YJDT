# -*- coding: utf-8 -*-
"""
高级优化设计模块 - Advanced Optimization for MBD

扩展MBD功能，提供：
- 多目标优化设计
- 约束驱动的设计空间探索
- 鲁棒性优化
- 基于ODD的设计参数反演
- 设计验证闭环

参考：YX工程面向运行能力的设计评估与运行逻辑验证关键技术研究
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable, Set
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import logging
from scipy.optimize import minimize, differential_evolution, NonlinearConstraint
from scipy.stats import qmc
import copy

logger = logging.getLogger(__name__)


class OptimizationObjective(Enum):
    """优化目标类型"""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    TARGET = "target"           # 目标值


class DesignSpaceType(Enum):
    """设计空间类型"""
    CONTINUOUS = "continuous"   # 连续空间
    DISCRETE = "discrete"       # 离散空间
    MIXED = "mixed"             # 混合空间
    CATEGORICAL = "categorical" # 分类变量


class RobustnessLevel(Enum):
    """鲁棒性等级"""
    NOMINAL = "nominal"         # 标称设计
    ROBUST = "robust"           # 鲁棒设计
    ULTRA_ROBUST = "ultra_robust"  # 超鲁棒设计


@dataclass
class DesignVariable:
    """设计变量"""
    name: str
    description: str
    space_type: DesignSpaceType

    # 连续变量边界
    lower_bound: float = 0.0
    upper_bound: float = 1.0

    # 离散变量选项
    discrete_values: List[Any] = field(default_factory=list)

    # 约束关系
    linked_variables: List[str] = field(default_factory=list)
    constraint_expression: str = ""

    # 敏感性标记
    is_sensitive: bool = False
    sensitivity_index: float = 0.0


@dataclass
class ObjectiveFunction:
    """目标函数"""
    name: str
    description: str
    objective_type: OptimizationObjective

    # 目标函数定义
    function: Callable = None
    target_value: float = None

    # 权重
    weight: float = 1.0

    # 优先级
    priority: int = 1

    # 容差
    tolerance: float = 0.01


@dataclass
class DesignConstraint:
    """设计约束"""
    name: str
    description: str
    constraint_type: str  # "eq", "ineq"

    # 约束函数 g(x) <= 0 或 h(x) = 0
    function: Callable = None

    # 边界约束
    lower_bound: float = None
    upper_bound: float = None

    # 是否硬约束
    is_hard: bool = True

    # 违反惩罚系数
    penalty_coefficient: float = 1000.0


@dataclass
class ParetoSolution:
    """Pareto最优解"""
    solution_id: str
    parameters: Dict[str, float]
    objectives: Dict[str, float]
    constraints_satisfied: bool
    dominated_by: List[str] = field(default_factory=list)
    dominates: List[str] = field(default_factory=list)
    crowding_distance: float = 0.0


@dataclass
class OptimizationResult:
    """优化结果"""
    success: bool
    method: str
    iterations: int
    function_evaluations: int

    # 最优解
    optimal_parameters: Dict[str, float]
    optimal_objectives: Dict[str, float]

    # Pareto前沿（多目标优化）
    pareto_front: List[ParetoSolution] = field(default_factory=list)

    # 约束满足情况
    constraints_satisfied: bool = True
    constraint_violations: List[Dict] = field(default_factory=list)

    # 收敛历史
    convergence_history: List[Dict] = field(default_factory=list)

    # 鲁棒性评估
    robustness_score: float = 0.0
    sensitivity_analysis: Dict[str, float] = field(default_factory=dict)


class MultiObjectiveOptimizer:
    """
    多目标优化器

    支持：
    - 加权和法
    - ε-约束法
    - NSGA-II
    - Pareto前沿生成
    """

    def __init__(self):
        self.variables: List[DesignVariable] = []
        self.objectives: List[ObjectiveFunction] = []
        self.constraints: List[DesignConstraint] = []
        self.history: List[OptimizationResult] = []

    def add_variable(self, variable: DesignVariable):
        """添加设计变量"""
        self.variables.append(variable)

    def add_objective(self, objective: ObjectiveFunction):
        """添加目标函数"""
        self.objectives.append(objective)

    def add_constraint(self, constraint: DesignConstraint):
        """添加约束"""
        self.constraints.append(constraint)

    def optimize_weighted_sum(self,
                             weights: Dict[str, float] = None,
                             max_iterations: int = 100) -> OptimizationResult:
        """
        加权和法多目标优化

        将多目标转化为单目标: f(x) = Σ w_i * f_i(x)
        """
        if weights is None:
            # 使用目标函数自带权重
            weights = {obj.name: obj.weight for obj in self.objectives}

        # 归一化权重
        total_weight = sum(weights.values())
        weights = {k: v/total_weight for k, v in weights.items()}

        # 构建综合目标函数
        def combined_objective(x):
            params = self._decode_variables(x)
            total = 0
            for obj in self.objectives:
                value = obj.function(params) if obj.function else 0
                if obj.objective_type == OptimizationObjective.MAXIMIZE:
                    value = -value
                elif obj.objective_type == OptimizationObjective.TARGET:
                    value = abs(value - obj.target_value)
                total += weights.get(obj.name, 1.0) * value
            return total

        # 构建约束
        scipy_constraints = self._build_scipy_constraints()

        # 变量边界
        bounds = [(v.lower_bound, v.upper_bound) for v in self.variables
                  if v.space_type == DesignSpaceType.CONTINUOUS]

        # 初始点
        x0 = np.array([(v.lower_bound + v.upper_bound) / 2 for v in self.variables
                       if v.space_type == DesignSpaceType.CONTINUOUS])

        # 执行优化
        convergence = []

        def callback(xk, convergence=convergence):
            convergence.append({
                "iteration": len(convergence),
                "objective": combined_objective(xk),
                "parameters": xk.tolist(),
            })

        result = minimize(
            combined_objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=scipy_constraints,
            options={'maxiter': max_iterations, 'disp': True},
            callback=callback
        )

        # 计算各目标值
        optimal_params = self._decode_variables(result.x)
        objectives_values = {}
        for obj in self.objectives:
            if obj.function:
                objectives_values[obj.name] = obj.function(optimal_params)

        opt_result = OptimizationResult(
            success=result.success,
            method="weighted_sum",
            iterations=result.nit if hasattr(result, 'nit') else len(convergence),
            function_evaluations=result.nfev if hasattr(result, 'nfev') else 0,
            optimal_parameters=optimal_params,
            optimal_objectives=objectives_values,
            constraints_satisfied=self._check_constraints(optimal_params),
            convergence_history=convergence,
        )

        self.history.append(opt_result)
        return opt_result

    def optimize_epsilon_constraint(self,
                                   primary_objective: str,
                                   epsilon_values: Dict[str, List[float]] = None,
                                   n_points: int = 20) -> OptimizationResult:
        """
        ε-约束法多目标优化

        选择一个主目标进行优化，其他目标转化为约束
        """
        # 找到主目标
        primary_obj = None
        secondary_objs = []
        for obj in self.objectives:
            if obj.name == primary_objective:
                primary_obj = obj
            else:
                secondary_objs.append(obj)

        if primary_obj is None:
            raise ValueError(f"未找到主目标: {primary_objective}")

        # 如果没有指定ε值，自动生成
        if epsilon_values is None:
            epsilon_values = self._generate_epsilon_values(secondary_objs, n_points)

        pareto_solutions = []

        # 对每组ε值进行优化
        for i, eps_combo in enumerate(self._epsilon_combinations(epsilon_values)):
            # 添加ε约束
            eps_constraints = []
            for obj in secondary_objs:
                if obj.name in eps_combo:
                    eps_val = eps_combo[obj.name]
                    eps_constraints.append(DesignConstraint(
                        name=f"epsilon_{obj.name}",
                        description=f"ε-约束: {obj.name} <= {eps_val}",
                        constraint_type="ineq",
                        function=lambda p, o=obj, e=eps_val: e - o.function(p),
                        is_hard=True,
                    ))

            # 临时添加约束
            original_constraints = self.constraints.copy()
            self.constraints.extend(eps_constraints)

            try:
                # 优化主目标
                result = self._single_objective_optimize(primary_obj)

                if result.success and result.constraints_satisfied:
                    sol = ParetoSolution(
                        solution_id=f"pareto_{i}",
                        parameters=result.optimal_parameters,
                        objectives=result.optimal_objectives,
                        constraints_satisfied=True,
                    )
                    pareto_solutions.append(sol)
            except Exception as e:
                logger.warning(f"ε-约束优化失败: {e}")
            finally:
                # 恢复原始约束
                self.constraints = original_constraints

        # 计算Pareto支配关系和拥挤距离
        self._compute_pareto_relations(pareto_solutions)
        self._compute_crowding_distance(pareto_solutions)

        # 选择最佳折中解
        best_solution = self._select_best_compromise(pareto_solutions)

        result = OptimizationResult(
            success=len(pareto_solutions) > 0,
            method="epsilon_constraint",
            iterations=len(pareto_solutions),
            function_evaluations=len(pareto_solutions) * 100,
            optimal_parameters=best_solution.parameters if best_solution else {},
            optimal_objectives=best_solution.objectives if best_solution else {},
            pareto_front=pareto_solutions,
            constraints_satisfied=True,
        )

        self.history.append(result)
        return result

    def optimize_nsga2(self,
                       population_size: int = 50,
                       generations: int = 100) -> OptimizationResult:
        """
        NSGA-II多目标优化

        非支配排序遗传算法
        """
        # 初始化种群
        population = self._initialize_population(population_size)

        convergence_history = []

        for gen in range(generations):
            # 评估适应度
            fitness = self._evaluate_population(population)

            # 非支配排序
            fronts = self._non_dominated_sort(population, fitness)

            # 计算拥挤距离
            for front in fronts:
                self._compute_crowding_distance_for_front(front, fitness)

            # 选择
            selected = self._tournament_selection(population, fronts, fitness)

            # 交叉
            offspring = self._crossover(selected)

            # 变异
            offspring = self._mutate(offspring)

            # 合并种群
            combined = np.vstack([population, offspring])
            combined_fitness = self._evaluate_population(combined)

            # 环境选择
            population = self._environmental_selection(
                combined, combined_fitness, population_size
            )

            # 记录收敛历史
            best_front = fronts[0] if fronts else []
            if best_front:
                avg_objectives = {}
                for obj in self.objectives:
                    values = [fitness[i][obj.name] for i in best_front]
                    avg_objectives[obj.name] = np.mean(values)
                convergence_history.append({
                    "generation": gen,
                    "front_size": len(best_front),
                    "objectives": avg_objectives,
                })

        # 提取Pareto前沿
        final_fitness = self._evaluate_population(population)
        final_fronts = self._non_dominated_sort(population, final_fitness)

        pareto_solutions = []
        if final_fronts:
            for idx in final_fronts[0]:
                params = self._decode_variables(population[idx])
                sol = ParetoSolution(
                    solution_id=f"nsga2_{idx}",
                    parameters=params,
                    objectives=final_fitness[idx],
                    constraints_satisfied=self._check_constraints(params),
                )
                pareto_solutions.append(sol)

        self._compute_pareto_relations(pareto_solutions)
        self._compute_crowding_distance(pareto_solutions)

        best_solution = self._select_best_compromise(pareto_solutions)

        result = OptimizationResult(
            success=len(pareto_solutions) > 0,
            method="nsga2",
            iterations=generations,
            function_evaluations=generations * population_size * 2,
            optimal_parameters=best_solution.parameters if best_solution else {},
            optimal_objectives=best_solution.objectives if best_solution else {},
            pareto_front=pareto_solutions,
            constraints_satisfied=True,
            convergence_history=convergence_history,
        )

        self.history.append(result)
        return result

    def _decode_variables(self, x: np.ndarray) -> Dict[str, float]:
        """解码设计变量"""
        params = {}
        idx = 0
        for var in self.variables:
            if var.space_type == DesignSpaceType.CONTINUOUS:
                params[var.name] = float(x[idx])
                idx += 1
            elif var.space_type == DesignSpaceType.DISCRETE:
                # 四舍五入到最近的离散值
                discrete_idx = int(np.round(x[idx]))
                discrete_idx = np.clip(discrete_idx, 0, len(var.discrete_values) - 1)
                params[var.name] = var.discrete_values[discrete_idx]
                idx += 1
        return params

    def _build_scipy_constraints(self) -> List[Dict]:
        """构建SciPy约束格式"""
        scipy_constraints = []
        for constr in self.constraints:
            if constr.constraint_type == "eq":
                scipy_constraints.append({
                    'type': 'eq',
                    'fun': lambda x, c=constr: c.function(self._decode_variables(x)),
                })
            else:
                scipy_constraints.append({
                    'type': 'ineq',
                    'fun': lambda x, c=constr: c.function(self._decode_variables(x)),
                })
        return scipy_constraints

    def _check_constraints(self, params: Dict[str, float]) -> bool:
        """检查约束是否满足"""
        for constr in self.constraints:
            if constr.function:
                value = constr.function(params)
                if constr.constraint_type == "eq" and abs(value) > 1e-6:
                    return False
                if constr.constraint_type == "ineq" and value < -1e-6:
                    return False
        return True

    def _single_objective_optimize(self, objective: ObjectiveFunction) -> OptimizationResult:
        """单目标优化"""
        def obj_func(x):
            params = self._decode_variables(x)
            value = objective.function(params) if objective.function else 0
            if objective.objective_type == OptimizationObjective.MAXIMIZE:
                value = -value
            return value

        bounds = [(v.lower_bound, v.upper_bound) for v in self.variables
                  if v.space_type == DesignSpaceType.CONTINUOUS]

        x0 = np.array([(v.lower_bound + v.upper_bound) / 2 for v in self.variables
                       if v.space_type == DesignSpaceType.CONTINUOUS])

        scipy_constraints = self._build_scipy_constraints()

        result = minimize(
            obj_func, x0, method='SLSQP', bounds=bounds,
            constraints=scipy_constraints, options={'maxiter': 100}
        )

        optimal_params = self._decode_variables(result.x)
        objectives_values = {}
        for obj in self.objectives:
            if obj.function:
                objectives_values[obj.name] = obj.function(optimal_params)

        return OptimizationResult(
            success=result.success,
            method="single_objective",
            iterations=result.nit if hasattr(result, 'nit') else 0,
            function_evaluations=result.nfev if hasattr(result, 'nfev') else 0,
            optimal_parameters=optimal_params,
            optimal_objectives=objectives_values,
            constraints_satisfied=self._check_constraints(optimal_params),
        )

    def _generate_epsilon_values(self,
                                 objectives: List[ObjectiveFunction],
                                 n_points: int) -> Dict[str, List[float]]:
        """生成ε值网格"""
        epsilon_values = {}
        for obj in objectives:
            # 通过极值优化确定范围
            min_result = self._single_objective_optimize(
                ObjectiveFunction(
                    name=obj.name,
                    description=obj.description,
                    objective_type=OptimizationObjective.MINIMIZE,
                    function=obj.function,
                )
            )
            max_result = self._single_objective_optimize(
                ObjectiveFunction(
                    name=obj.name,
                    description=obj.description,
                    objective_type=OptimizationObjective.MAXIMIZE,
                    function=obj.function,
                )
            )

            min_val = min_result.optimal_objectives.get(obj.name, 0)
            max_val = max_result.optimal_objectives.get(obj.name, 1)

            epsilon_values[obj.name] = np.linspace(min_val, max_val, n_points).tolist()

        return epsilon_values

    def _epsilon_combinations(self,
                              epsilon_values: Dict[str, List[float]]) -> List[Dict[str, float]]:
        """生成ε值组合"""
        import itertools

        keys = list(epsilon_values.keys())
        values = [epsilon_values[k] for k in keys]

        combinations = []
        for combo in itertools.product(*values):
            combinations.append({k: v for k, v in zip(keys, combo)})

        return combinations

    def _initialize_population(self, size: int) -> np.ndarray:
        """初始化种群"""
        n_vars = len([v for v in self.variables
                      if v.space_type == DesignSpaceType.CONTINUOUS])

        # 使用拉丁超立方采样
        sampler = qmc.LatinHypercube(d=n_vars)
        sample = sampler.random(n=size)

        # 缩放到变量边界
        l_bounds = np.array([v.lower_bound for v in self.variables
                            if v.space_type == DesignSpaceType.CONTINUOUS])
        u_bounds = np.array([v.upper_bound for v in self.variables
                            if v.space_type == DesignSpaceType.CONTINUOUS])

        population = qmc.scale(sample, l_bounds, u_bounds)

        return population

    def _evaluate_population(self, population: np.ndarray) -> List[Dict[str, float]]:
        """评估种群适应度"""
        fitness = []
        for individual in population:
            params = self._decode_variables(individual)
            obj_values = {}
            for obj in self.objectives:
                if obj.function:
                    obj_values[obj.name] = obj.function(params)
            fitness.append(obj_values)
        return fitness

    def _non_dominated_sort(self,
                            population: np.ndarray,
                            fitness: List[Dict[str, float]]) -> List[List[int]]:
        """非支配排序"""
        n = len(population)

        # 初始化
        domination_count = [0] * n
        dominated_solutions = [[] for _ in range(n)]
        fronts = [[]]

        # 计算支配关系
        for i in range(n):
            for j in range(i + 1, n):
                if self._dominates(fitness[i], fitness[j]):
                    dominated_solutions[i].append(j)
                    domination_count[j] += 1
                elif self._dominates(fitness[j], fitness[i]):
                    dominated_solutions[j].append(i)
                    domination_count[i] += 1

        # 第一前沿
        for i in range(n):
            if domination_count[i] == 0:
                fronts[0].append(i)

        # 构建后续前沿
        current_front = 0
        while fronts[current_front]:
            next_front = []
            for i in fronts[current_front]:
                for j in dominated_solutions[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            current_front += 1
            if next_front:
                fronts.append(next_front)
            else:
                break

        return fronts

    def _dominates(self,
                   fitness_a: Dict[str, float],
                   fitness_b: Dict[str, float]) -> bool:
        """判断a是否支配b"""
        better_in_any = False
        for obj in self.objectives:
            val_a = fitness_a.get(obj.name, 0)
            val_b = fitness_b.get(obj.name, 0)

            if obj.objective_type == OptimizationObjective.MINIMIZE:
                if val_a > val_b:
                    return False
                if val_a < val_b:
                    better_in_any = True
            else:
                if val_a < val_b:
                    return False
                if val_a > val_b:
                    better_in_any = True

        return better_in_any

    def _compute_crowding_distance_for_front(self,
                                             front: List[int],
                                             fitness: List[Dict[str, float]]):
        """计算前沿拥挤距离"""
        n = len(front)
        if n <= 2:
            return

        distances = {i: 0.0 for i in front}

        for obj in self.objectives:
            # 按目标值排序
            sorted_front = sorted(front, key=lambda i: fitness[i].get(obj.name, 0))

            # 边界解
            distances[sorted_front[0]] = float('inf')
            distances[sorted_front[-1]] = float('inf')

            # 计算拥挤距离
            obj_range = (fitness[sorted_front[-1]].get(obj.name, 1) -
                        fitness[sorted_front[0]].get(obj.name, 0))
            if obj_range > 0:
                for i in range(1, n - 1):
                    distances[sorted_front[i]] += (
                        fitness[sorted_front[i+1]].get(obj.name, 0) -
                        fitness[sorted_front[i-1]].get(obj.name, 0)
                    ) / obj_range

    def _tournament_selection(self,
                              population: np.ndarray,
                              fronts: List[List[int]],
                              fitness: List[Dict[str, float]]) -> np.ndarray:
        """锦标赛选择"""
        n = len(population)
        selected = []

        # 为每个个体分配rank
        ranks = {}
        for rank, front in enumerate(fronts):
            for i in front:
                ranks[i] = rank

        for _ in range(n):
            # 随机选择两个个体
            i, j = np.random.choice(n, 2, replace=False)

            # 基于rank和拥挤距离选择
            if ranks.get(i, n) < ranks.get(j, n):
                selected.append(population[i].copy())
            elif ranks.get(i, n) > ranks.get(j, n):
                selected.append(population[j].copy())
            else:
                # 同rank，选择拥挤距离大的
                selected.append(population[i].copy())

        return np.array(selected)

    def _crossover(self, population: np.ndarray, crossover_rate: float = 0.9) -> np.ndarray:
        """模拟二进制交叉"""
        n, d = population.shape
        offspring = population.copy()

        for i in range(0, n - 1, 2):
            if np.random.random() < crossover_rate:
                # SBX交叉
                eta = 20
                u = np.random.random(d)
                beta = np.where(u <= 0.5,
                               (2 * u) ** (1 / (eta + 1)),
                               (1 / (2 * (1 - u))) ** (1 / (eta + 1)))

                offspring[i] = 0.5 * ((1 + beta) * population[i] + (1 - beta) * population[i + 1])
                offspring[i + 1] = 0.5 * ((1 - beta) * population[i] + (1 + beta) * population[i + 1])

        # 边界处理
        for i, var in enumerate(self.variables):
            if var.space_type == DesignSpaceType.CONTINUOUS:
                offspring[:, i] = np.clip(offspring[:, i], var.lower_bound, var.upper_bound)

        return offspring

    def _mutate(self, population: np.ndarray, mutation_rate: float = 0.1) -> np.ndarray:
        """多项式变异"""
        n, d = population.shape
        mutated = population.copy()

        for i in range(n):
            for j in range(d):
                if np.random.random() < mutation_rate:
                    var = self.variables[j]
                    if var.space_type == DesignSpaceType.CONTINUOUS:
                        eta = 20
                        delta = (mutated[i, j] - var.lower_bound) / (var.upper_bound - var.lower_bound)
                        u = np.random.random()

                        if u < 0.5:
                            delta_q = (2 * u) ** (1 / (eta + 1)) - 1
                        else:
                            delta_q = 1 - (2 * (1 - u)) ** (1 / (eta + 1))

                        mutated[i, j] += delta_q * (var.upper_bound - var.lower_bound)
                        mutated[i, j] = np.clip(mutated[i, j], var.lower_bound, var.upper_bound)

        return mutated

    def _environmental_selection(self,
                                 population: np.ndarray,
                                 fitness: List[Dict[str, float]],
                                 size: int) -> np.ndarray:
        """环境选择"""
        fronts = self._non_dominated_sort(population, fitness)

        selected_indices = []
        for front in fronts:
            if len(selected_indices) + len(front) <= size:
                selected_indices.extend(front)
            else:
                # 需要部分选择，基于拥挤距离
                remaining = size - len(selected_indices)
                self._compute_crowding_distance_for_front(front, fitness)
                # 选择拥挤距离最大的
                sorted_front = sorted(front, key=lambda i: -fitness[i].get('crowding', 0))
                selected_indices.extend(sorted_front[:remaining])
                break

        return population[selected_indices]

    def _compute_pareto_relations(self, solutions: List[ParetoSolution]):
        """计算Pareto支配关系"""
        for i, sol_i in enumerate(solutions):
            for j, sol_j in enumerate(solutions):
                if i != j:
                    if self._solution_dominates(sol_i, sol_j):
                        sol_i.dominates.append(sol_j.solution_id)
                        sol_j.dominated_by.append(sol_i.solution_id)

    def _solution_dominates(self, sol_a: ParetoSolution, sol_b: ParetoSolution) -> bool:
        """判断解a是否支配解b"""
        better_in_any = False
        for obj in self.objectives:
            val_a = sol_a.objectives.get(obj.name, 0)
            val_b = sol_b.objectives.get(obj.name, 0)

            if obj.objective_type == OptimizationObjective.MINIMIZE:
                if val_a > val_b:
                    return False
                if val_a < val_b:
                    better_in_any = True
            else:
                if val_a < val_b:
                    return False
                if val_a > val_b:
                    better_in_any = True

        return better_in_any

    def _compute_crowding_distance(self, solutions: List[ParetoSolution]):
        """计算拥挤距离"""
        n = len(solutions)
        if n <= 2:
            for sol in solutions:
                sol.crowding_distance = float('inf')
            return

        for obj in self.objectives:
            # 按目标值排序
            sorted_sols = sorted(solutions, key=lambda s: s.objectives.get(obj.name, 0))

            # 边界
            sorted_sols[0].crowding_distance = float('inf')
            sorted_sols[-1].crowding_distance = float('inf')

            # 计算距离
            obj_range = (sorted_sols[-1].objectives.get(obj.name, 1) -
                        sorted_sols[0].objectives.get(obj.name, 0))
            if obj_range > 0:
                for i in range(1, n - 1):
                    sorted_sols[i].crowding_distance += (
                        sorted_sols[i+1].objectives.get(obj.name, 0) -
                        sorted_sols[i-1].objectives.get(obj.name, 0)
                    ) / obj_range

    def _select_best_compromise(self, solutions: List[ParetoSolution]) -> Optional[ParetoSolution]:
        """选择最佳折中解"""
        if not solutions:
            return None

        # 选择非支配的、拥挤距离最大的解
        non_dominated = [s for s in solutions if not s.dominated_by]

        if not non_dominated:
            non_dominated = solutions

        # 按拥挤距离排序
        sorted_sols = sorted(non_dominated, key=lambda s: -s.crowding_distance)

        return sorted_sols[0]


class RobustnessOptimizer:
    """
    鲁棒性优化器

    考虑参数不确定性的鲁棒设计
    """

    def __init__(self, base_optimizer: MultiObjectiveOptimizer):
        self.base_optimizer = base_optimizer
        self.uncertainty_model: Dict[str, Dict] = {}

    def set_uncertainty(self,
                        variable_name: str,
                        distribution: str = "uniform",
                        parameters: Dict[str, float] = None):
        """设置变量不确定性"""
        self.uncertainty_model[variable_name] = {
            "distribution": distribution,
            "parameters": parameters or {},
        }

    def optimize_robust(self,
                       n_samples: int = 100,
                       robustness_level: RobustnessLevel = RobustnessLevel.ROBUST) -> OptimizationResult:
        """
        鲁棒优化

        使用蒙特卡洛方法评估鲁棒性
        """
        # 定义鲁棒目标函数
        original_objectives = self.base_optimizer.objectives.copy()

        robust_objectives = []
        for obj in original_objectives:
            # 创建鲁棒版本
            robust_obj = ObjectiveFunction(
                name=f"robust_{obj.name}",
                description=f"鲁棒版本: {obj.description}",
                objective_type=obj.objective_type,
                function=self._create_robust_function(obj.function, n_samples),
                weight=obj.weight,
            )
            robust_objectives.append(robust_obj)

            # 添加方差目标（需要最小化）
            variance_obj = ObjectiveFunction(
                name=f"variance_{obj.name}",
                description=f"方差: {obj.description}",
                objective_type=OptimizationObjective.MINIMIZE,
                function=self._create_variance_function(obj.function, n_samples),
                weight=self._get_variance_weight(robustness_level),
            )
            robust_objectives.append(variance_obj)

        # 设置鲁棒目标
        self.base_optimizer.objectives = robust_objectives

        # 执行优化
        result = self.base_optimizer.optimize_weighted_sum()

        # 恢复原始目标
        self.base_optimizer.objectives = original_objectives

        # 评估鲁棒性得分
        result.robustness_score = self._evaluate_robustness(
            result.optimal_parameters, n_samples
        )

        return result

    def _create_robust_function(self,
                                original_func: Callable,
                                n_samples: int) -> Callable:
        """创建鲁棒目标函数（期望值）"""
        def robust_func(params):
            samples = self._generate_samples(params, n_samples)
            values = [original_func(s) for s in samples]
            return np.mean(values)
        return robust_func

    def _create_variance_function(self,
                                  original_func: Callable,
                                  n_samples: int) -> Callable:
        """创建方差函数"""
        def variance_func(params):
            samples = self._generate_samples(params, n_samples)
            values = [original_func(s) for s in samples]
            return np.var(values)
        return variance_func

    def _generate_samples(self,
                          params: Dict[str, float],
                          n_samples: int) -> List[Dict[str, float]]:
        """生成考虑不确定性的样本"""
        samples = []
        for _ in range(n_samples):
            sample = params.copy()
            for var_name, uncertainty in self.uncertainty_model.items():
                if var_name in sample:
                    nominal = sample[var_name]
                    dist = uncertainty["distribution"]
                    params_unc = uncertainty["parameters"]

                    if dist == "uniform":
                        delta = params_unc.get("delta", 0.1)
                        sample[var_name] = np.random.uniform(
                            nominal * (1 - delta),
                            nominal * (1 + delta)
                        )
                    elif dist == "normal":
                        std = params_unc.get("std", 0.05)
                        sample[var_name] = np.random.normal(nominal, nominal * std)
            samples.append(sample)
        return samples

    def _get_variance_weight(self, level: RobustnessLevel) -> float:
        """获取方差权重"""
        weights = {
            RobustnessLevel.NOMINAL: 0.0,
            RobustnessLevel.ROBUST: 0.3,
            RobustnessLevel.ULTRA_ROBUST: 0.6,
        }
        return weights.get(level, 0.3)

    def _evaluate_robustness(self,
                            params: Dict[str, float],
                            n_samples: int) -> float:
        """评估鲁棒性得分"""
        samples = self._generate_samples(params, n_samples)

        # 检查每个样本是否满足约束
        satisfied = sum(
            1 for s in samples if self.base_optimizer._check_constraints(s)
        )

        return satisfied / n_samples


class ODDConstrainedDesigner:
    """
    ODD约束设计器

    在ODD边界约束下进行设计优化
    """

    def __init__(self, optimizer: MultiObjectiveOptimizer, odd=None):
        self.optimizer = optimizer
        self.odd = odd
        self.odd_constraints: List[DesignConstraint] = []

    def set_odd(self, odd):
        """设置ODD"""
        self.odd = odd
        self._extract_odd_constraints()

    def _extract_odd_constraints(self):
        """从ODD提取设计约束"""
        if self.odd is None:
            return

        # 从系统边界提取
        for name, boundary in self.odd.system_boundaries.items():
            # 最大值约束
            max_constraint = DesignConstraint(
                name=f"odd_max_{name}",
                description=f"ODD上限约束: {name}",
                constraint_type="ineq",
                function=lambda p, n=name, b=boundary: b.normal_max - p.get(n, 0),
                is_hard=True,
            )
            self.odd_constraints.append(max_constraint)

            # 最小值约束
            min_constraint = DesignConstraint(
                name=f"odd_min_{name}",
                description=f"ODD下限约束: {name}",
                constraint_type="ineq",
                function=lambda p, n=name, b=boundary: p.get(n, 0) - b.normal_min,
                is_hard=True,
            )
            self.odd_constraints.append(min_constraint)

    def optimize_within_odd(self, **kwargs) -> OptimizationResult:
        """在ODD约束下优化"""
        # 添加ODD约束
        original_constraints = self.optimizer.constraints.copy()
        self.optimizer.constraints.extend(self.odd_constraints)

        try:
            result = self.optimizer.optimize_weighted_sum(**kwargs)
        finally:
            self.optimizer.constraints = original_constraints

        return result

    def verify_design_in_odd(self, params: Dict[str, float]) -> Dict[str, Any]:
        """验证设计是否在ODD内"""
        if self.odd is None:
            return {"valid": True, "message": "未设置ODD"}

        violations = []
        for constraint in self.odd_constraints:
            if constraint.function:
                value = constraint.function(params)
                if value < 0:
                    violations.append({
                        "constraint": constraint.name,
                        "value": value,
                        "description": constraint.description,
                    })

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "message": "设计在ODD内" if not violations else f"发现{len(violations)}个违规",
        }


class DesignSpaceExplorer:
    """
    设计空间探索器

    系统性探索设计空间，识别可行区域和敏感区域
    """

    def __init__(self, optimizer: MultiObjectiveOptimizer):
        self.optimizer = optimizer
        self.exploration_results: List[Dict] = []

    def explore_latin_hypercube(self, n_samples: int = 100) -> Dict[str, Any]:
        """拉丁超立方采样探索"""
        n_vars = len([v for v in self.optimizer.variables
                      if v.space_type == DesignSpaceType.CONTINUOUS])

        # 生成样本
        sampler = qmc.LatinHypercube(d=n_vars)
        sample = sampler.random(n=n_samples)

        # 缩放
        l_bounds = np.array([v.lower_bound for v in self.optimizer.variables
                            if v.space_type == DesignSpaceType.CONTINUOUS])
        u_bounds = np.array([v.upper_bound for v in self.optimizer.variables
                            if v.space_type == DesignSpaceType.CONTINUOUS])

        samples = qmc.scale(sample, l_bounds, u_bounds)

        # 评估
        results = []
        feasible_count = 0

        for s in samples:
            params = self.optimizer._decode_variables(s)

            # 检查约束
            feasible = self.optimizer._check_constraints(params)
            if feasible:
                feasible_count += 1

            # 评估目标
            objectives = {}
            for obj in self.optimizer.objectives:
                if obj.function:
                    objectives[obj.name] = obj.function(params)

            results.append({
                "parameters": params,
                "objectives": objectives,
                "feasible": feasible,
            })

        exploration = {
            "method": "latin_hypercube",
            "n_samples": n_samples,
            "feasibility_rate": feasible_count / n_samples,
            "results": results,
        }

        self.exploration_results.append(exploration)
        return exploration

    def identify_sensitive_regions(self, threshold: float = 0.1) -> List[Dict]:
        """识别敏感区域"""
        if not self.exploration_results:
            self.explore_latin_hypercube()

        latest = self.exploration_results[-1]
        results = latest["results"]

        sensitive_regions = []

        # 对每个变量进行分析
        for var in self.optimizer.variables:
            if var.space_type != DesignSpaceType.CONTINUOUS:
                continue

            # 收集该变量的值和目标值
            var_values = [r["parameters"].get(var.name, 0) for r in results]

            for obj in self.optimizer.objectives:
                obj_values = [r["objectives"].get(obj.name, 0) for r in results]

                # 计算局部梯度
                for i in range(len(var_values) - 1):
                    if var_values[i+1] != var_values[i]:
                        gradient = abs(
                            (obj_values[i+1] - obj_values[i]) /
                            (var_values[i+1] - var_values[i])
                        )

                        if gradient > threshold:
                            sensitive_regions.append({
                                "variable": var.name,
                                "objective": obj.name,
                                "location": (var_values[i] + var_values[i+1]) / 2,
                                "gradient": gradient,
                            })

        return sensitive_regions


def create_cascade_optimization_problem():
    """创建梯级水电优化问题"""
    optimizer = MultiObjectiveOptimizer()

    # 添加设计变量
    optimizer.add_variable(DesignVariable(
        name="guide_vane_rate",
        description="导叶动作速率",
        space_type=DesignSpaceType.CONTINUOUS,
        lower_bound=0.01,
        upper_bound=0.2,
        is_sensitive=True,
    ))

    optimizer.add_variable(DesignVariable(
        name="action_interval",
        description="多站动作间隔",
        space_type=DesignSpaceType.CONTINUOUS,
        lower_bound=5.0,
        upper_bound=30.0,
    ))

    optimizer.add_variable(DesignVariable(
        name="governor_kp",
        description="调速器比例增益",
        space_type=DesignSpaceType.CONTINUOUS,
        lower_bound=1.0,
        upper_bound=5.0,
        is_sensitive=True,
    ))

    optimizer.add_variable(DesignVariable(
        name="governor_ki",
        description="调速器积分增益",
        space_type=DesignSpaceType.CONTINUOUS,
        lower_bound=0.05,
        upper_bound=0.5,
        is_sensitive=True,
    ))

    # 添加目标函数
    optimizer.add_objective(ObjectiveFunction(
        name="pressure_stability",
        description="压力稳定性",
        objective_type=OptimizationObjective.MAXIMIZE,
        function=lambda p: 100 - 10 * p.get("guide_vane_rate", 0.1),
        weight=0.4,
    ))

    optimizer.add_objective(ObjectiveFunction(
        name="response_speed",
        description="响应速度",
        objective_type=OptimizationObjective.MAXIMIZE,
        function=lambda p: 100 - 5 * p.get("action_interval", 10),
        weight=0.3,
    ))

    optimizer.add_objective(ObjectiveFunction(
        name="oscillation_damping",
        description="振荡阻尼",
        objective_type=OptimizationObjective.MAXIMIZE,
        function=lambda p: 100 - 20 * abs(p.get("governor_kp", 2.5) - 2.5),
        weight=0.3,
    ))

    # 添加约束
    optimizer.add_constraint(DesignConstraint(
        name="pressure_limit",
        description="压力波幅值限制",
        constraint_type="ineq",
        function=lambda p: 0.3 - 2 * p.get("guide_vane_rate", 0.1),
    ))

    return optimizer
