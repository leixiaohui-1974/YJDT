"""
设计优化器模块
Design Optimizer Module

面向可研阶段的设计方案对比与优化
对标无人驾驶汽车的V模型开发流程
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import json
import hashlib
from datetime import datetime


class DesignLevel(Enum):
    """设计层级（对标无人驾驶L0-L5）"""
    L0_MANUAL = 0           # 完全人工控制
    L1_ASSISTED = 1         # 辅助控制（单一功能自动化）
    L2_PARTIAL = 2          # 部分自动化（多功能协调）
    L3_CONDITIONAL = 3      # 有条件自动化（正常工况自动）
    L4_HIGH = 4             # 高度自动化（特定场景无人值守）
    L5_FULL = 5             # 完全自动化（全场景无人值守）


class OptimizationObjective(Enum):
    """优化目标"""
    COST = "cost"                    # 成本最小化
    RELIABILITY = "reliability"       # 可靠性最大化
    EFFICIENCY = "efficiency"         # 效率最大化
    SAFETY = "safety"                 # 安全性最大化
    FLEXIBILITY = "flexibility"       # 灵活性最大化
    LIFECYCLE = "lifecycle"           # 全生命周期效益最大化
    MULTI_OBJECTIVE = "multi"         # 多目标优化


@dataclass
class DesignParameter:
    """设计参数"""
    name: str
    value: float
    unit: str
    min_value: float
    max_value: float
    description: str = ""
    category: str = "general"
    is_optimizable: bool = True


@dataclass
class DesignScheme:
    """设计方案"""
    scheme_id: str
    name: str
    version: str = "1.0"
    description: str = ""
    design_level: DesignLevel = DesignLevel.L3_CONDITIONAL

    # 系统参数
    hydraulic_params: Dict[str, DesignParameter] = field(default_factory=dict)
    turbine_params: Dict[str, DesignParameter] = field(default_factory=dict)
    generator_params: Dict[str, DesignParameter] = field(default_factory=dict)
    control_params: Dict[str, DesignParameter] = field(default_factory=dict)

    # 传感器配置
    sensor_config: Dict[str, Any] = field(default_factory=dict)

    # 设备选型
    equipment_selection: Dict[str, Any] = field(default_factory=dict)

    # 成本估算
    capital_cost: float = 0.0           # 初始投资（亿元）
    annual_maintenance: float = 0.0     # 年维护费用（万元）
    expected_life: float = 50.0         # 设计寿命（年）

    # 性能指标
    expected_availability: float = 0.98  # 预期可用率
    expected_efficiency: float = 0.94    # 预期效率
    automation_level: float = 0.8        # 自动化程度

    # 元数据
    created_at: str = ""
    created_by: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def get_hash(self) -> str:
        """获取方案哈希值"""
        content = f"{self.name}{self.version}"
        for params in [self.hydraulic_params, self.turbine_params]:
            for k, v in params.items():
                content += f"{k}{v.value}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'scheme_id': self.scheme_id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'design_level': self.design_level.name,
            'capital_cost': self.capital_cost,
            'expected_availability': self.expected_availability,
            'expected_efficiency': self.expected_efficiency,
        }


@dataclass
class OptimizationResult:
    """优化结果"""
    scheme_id: str
    objective: OptimizationObjective
    optimal_value: float
    optimal_params: Dict[str, float]
    convergence_history: List[float] = field(default_factory=list)
    constraints_satisfied: bool = True
    computation_time: float = 0.0
    iterations: int = 0


@dataclass
class ComparisonResult:
    """方案对比结果"""
    schemes: List[str]               # 对比的方案ID列表
    metrics: Dict[str, Dict[str, float]]  # 各方案各指标得分
    ranking: List[str]               # 综合排名
    radar_data: Dict[str, List[float]]  # 雷达图数据
    recommendation: str              # 推荐方案
    analysis: str                    # 分析说明


class SchemeComparator:
    """
    方案对比器

    基于全场景在环测试进行方案优劣对比
    """

    def __init__(self):
        # 评价指标权重
        self.weights = {
            'safety': 0.25,           # 安全性
            'reliability': 0.20,       # 可靠性
            'efficiency': 0.15,        # 效率
            'economy': 0.15,          # 经济性
            'flexibility': 0.10,       # 灵活性
            'maintainability': 0.10,   # 可维护性
            'intelligence': 0.05,      # 智能化水平
        }

        # 指标评分标准
        self.scoring_criteria = {
            'safety': self._score_safety,
            'reliability': self._score_reliability,
            'efficiency': self._score_efficiency,
            'economy': self._score_economy,
            'flexibility': self._score_flexibility,
            'maintainability': self._score_maintainability,
            'intelligence': self._score_intelligence,
        }

        # 对比历史
        self.comparison_history: List[ComparisonResult] = []

    def compare(
        self,
        schemes: List[DesignScheme],
        test_results: Optional[Dict[str, Dict]] = None
    ) -> ComparisonResult:
        """
        对比多个设计方案

        Args:
            schemes: 待对比的设计方案列表
            test_results: 各方案的测试结果（来自全场景在环测试）

        Returns:
            对比结果
        """
        metrics = {}

        for scheme in schemes:
            scheme_metrics = {}

            # 获取该方案的测试结果
            scheme_test = test_results.get(scheme.scheme_id, {}) if test_results else {}

            # 计算各项指标得分
            for metric_name, scoring_func in self.scoring_criteria.items():
                score = scoring_func(scheme, scheme_test)
                scheme_metrics[metric_name] = score

            metrics[scheme.scheme_id] = scheme_metrics

        # 计算综合得分
        weighted_scores = {}
        for scheme_id, scheme_metrics in metrics.items():
            total = sum(
                score * self.weights[metric]
                for metric, score in scheme_metrics.items()
            )
            weighted_scores[scheme_id] = total

        # 排名
        ranking = sorted(
            weighted_scores.keys(),
            key=lambda x: weighted_scores[x],
            reverse=True
        )

        # 雷达图数据
        radar_data = {
            scheme_id: [metrics[scheme_id][m] for m in self.weights.keys()]
            for scheme_id in metrics
        }

        # 生成推荐和分析
        recommendation = ranking[0]
        analysis = self._generate_analysis(schemes, metrics, ranking)

        result = ComparisonResult(
            schemes=[s.scheme_id for s in schemes],
            metrics=metrics,
            ranking=ranking,
            radar_data=radar_data,
            recommendation=recommendation,
            analysis=analysis,
        )

        self.comparison_history.append(result)

        return result

    def _score_safety(self, scheme: DesignScheme, test_results: Dict) -> float:
        """安全性评分"""
        score = 80.0  # 基础分

        # 根据设计等级加分
        level_bonus = {
            DesignLevel.L0_MANUAL: 0,
            DesignLevel.L1_ASSISTED: 5,
            DesignLevel.L2_PARTIAL: 10,
            DesignLevel.L3_CONDITIONAL: 15,
            DesignLevel.L4_HIGH: 18,
            DesignLevel.L5_FULL: 20,
        }
        score += level_bonus.get(scheme.design_level, 0)

        # 根据测试结果调整
        if 'safety_tests' in test_results:
            pass_rate = test_results['safety_tests'].get('pass_rate', 1.0)
            score *= pass_rate

        return min(100, score)

    def _score_reliability(self, scheme: DesignScheme, test_results: Dict) -> float:
        """可靠性评分"""
        # 基于预期可用率
        availability = scheme.expected_availability
        score = availability * 100

        # 考虑冗余设计
        if scheme.sensor_config.get('redundancy', False):
            score += 5

        return min(100, score)

    def _score_efficiency(self, scheme: DesignScheme, test_results: Dict) -> float:
        """效率评分"""
        efficiency = scheme.expected_efficiency
        return efficiency * 100

    def _score_economy(self, scheme: DesignScheme, test_results: Dict) -> float:
        """经济性评分（成本越低得分越高）"""
        # 归一化成本（假设参考值为100亿）
        cost_ref = 100.0
        cost_ratio = scheme.capital_cost / cost_ref

        # 成本越低得分越高
        score = 100 * (1 - min(cost_ratio, 1))

        # 考虑运维成本
        maintenance_ratio = scheme.annual_maintenance / 10000  # 参考1亿/年
        score -= 20 * min(maintenance_ratio, 1)

        return max(0, min(100, score))

    def _score_flexibility(self, scheme: DesignScheme, test_results: Dict) -> float:
        """灵活性评分"""
        score = 70.0

        # 自动化程度高则灵活性高
        score += 20 * scheme.automation_level

        # 可优化参数越多越灵活
        optimizable_count = sum(
            1 for p in scheme.control_params.values()
            if p.is_optimizable
        )
        score += min(10, optimizable_count)

        return min(100, score)

    def _score_maintainability(self, scheme: DesignScheme, test_results: Dict) -> float:
        """可维护性评分"""
        score = 75.0

        # 标准化程度
        if 'standardization' in scheme.equipment_selection:
            score += scheme.equipment_selection['standardization'] * 15

        # 诊断能力
        if scheme.sensor_config.get('diagnostic_sensors', 0) > 10:
            score += 10

        return min(100, score)

    def _score_intelligence(self, scheme: DesignScheme, test_results: Dict) -> float:
        """智能化水平评分"""
        level_scores = {
            DesignLevel.L0_MANUAL: 20,
            DesignLevel.L1_ASSISTED: 40,
            DesignLevel.L2_PARTIAL: 60,
            DesignLevel.L3_CONDITIONAL: 75,
            DesignLevel.L4_HIGH: 90,
            DesignLevel.L5_FULL: 100,
        }
        return level_scores.get(scheme.design_level, 50)

    def _generate_analysis(
        self,
        schemes: List[DesignScheme],
        metrics: Dict[str, Dict[str, float]],
        ranking: List[str]
    ) -> str:
        """生成分析报告"""
        best_id = ranking[0]
        best_scheme = next(s for s in schemes if s.scheme_id == best_id)

        analysis = f"""
方案对比分析报告
================

1. 综合评估结果
   推荐方案: {best_scheme.name} (ID: {best_id})
   设计等级: {best_scheme.design_level.name}

2. 各方案排名
"""
        for i, scheme_id in enumerate(ranking, 1):
            scheme = next(s for s in schemes if s.scheme_id == scheme_id)
            total_score = sum(
                metrics[scheme_id][m] * self.weights[m]
                for m in self.weights
            )
            analysis += f"   第{i}名: {scheme.name} (综合得分: {total_score:.1f})\n"

        analysis += "\n3. 关键指标对比\n"
        for metric in self.weights:
            analysis += f"   {metric}:\n"
            for scheme_id in ranking:
                score = metrics[scheme_id][metric]
                analysis += f"      {scheme_id}: {score:.1f}\n"

        return analysis

    def set_weights(self, weights: Dict[str, float]):
        """设置评价权重"""
        total = sum(weights.values())
        self.weights = {k: v/total for k, v in weights.items()}


class DesignOptimizer:
    """
    设计优化器

    对标无人驾驶汽车的开发模式，实现：
    - 基于仿真的设计迭代
    - 全场景验证
    - 多目标优化
    """

    def __init__(self):
        self.schemes: Dict[str, DesignScheme] = {}
        self.comparator = SchemeComparator()

        # 优化算法配置
        self.optimization_config = {
            'algorithm': 'genetic',  # genetic, pso, bayesian
            'population_size': 50,
            'max_generations': 100,
            'crossover_rate': 0.8,
            'mutation_rate': 0.1,
        }

        # 约束条件
        self.constraints: List[Callable[[DesignScheme], bool]] = []

        # 优化历史
        self.optimization_history: List[OptimizationResult] = []

    def create_baseline_scheme(self) -> DesignScheme:
        """创建基准设计方案（方案一：工程现实版）"""
        scheme = DesignScheme(
            scheme_id="YJ_BASELINE_01",
            name="雅江梯级基准方案-多级开发",
            version="1.0",
            description="高水头Francis机组 + 超长隧洞，工程现实版",
            design_level=DesignLevel.L3_CONDITIONAL,
        )

        # 水力参数
        scheme.hydraulic_params = {
            'rated_head': DesignParameter(
                name="额定水头", value=480.0, unit="m",
                min_value=400.0, max_value=550.0,
                category="hydraulic"
            ),
            'rated_flow': DesignParameter(
                name="额定流量", value=210.0, unit="m³/s",
                min_value=180.0, max_value=250.0,
                category="hydraulic"
            ),
            'tunnel_length': DesignParameter(
                name="隧洞长度", value=25000.0, unit="m",
                min_value=20000.0, max_value=30000.0,
                category="hydraulic", is_optimizable=False
            ),
            'tunnel_diameter': DesignParameter(
                name="隧洞直径", value=11.0, unit="m",
                min_value=9.0, max_value=13.0,
                category="hydraulic"
            ),
            'wave_speed': DesignParameter(
                name="压力波速", value=1350.0, unit="m/s",
                min_value=1200.0, max_value=1400.0,
                category="hydraulic", is_optimizable=False
            ),
            'surge_tank_diameter': DesignParameter(
                name="调压室直径", value=45.0, unit="m",
                min_value=35.0, max_value=55.0,
                category="hydraulic"
            ),
        }

        # 水轮机参数
        scheme.turbine_params = {
            'rated_power': DesignParameter(
                name="额定功率", value=1000.0, unit="MW",
                min_value=800.0, max_value=1200.0,
                category="turbine"
            ),
            'rated_speed': DesignParameter(
                name="额定转速", value=166.7, unit="r/min",
                min_value=150.0, max_value=200.0,
                category="turbine"
            ),
            'inertia_gd2': DesignParameter(
                name="飞轮惯量", value=130000.0, unit="t·m²",
                min_value=100000.0, max_value=160000.0,
                category="turbine"
            ),
            'guide_vane_close_time': DesignParameter(
                name="导叶关闭时间", value=8.0, unit="s",
                min_value=6.0, max_value=15.0,
                category="turbine"
            ),
        }

        # 控制参数
        scheme.control_params = {
            'kp': DesignParameter(
                name="比例增益", value=2.5, unit="",
                min_value=1.0, max_value=5.0,
                category="control"
            ),
            'ki': DesignParameter(
                name="积分增益", value=0.15, unit="",
                min_value=0.05, max_value=0.5,
                category="control"
            ),
            'kd': DesignParameter(
                name="微分增益", value=4.0, unit="",
                min_value=1.0, max_value=8.0,
                category="control"
            ),
            'servo_time': DesignParameter(
                name="伺服时间常数", value=0.5, unit="s",
                min_value=0.2, max_value=1.0,
                category="control"
            ),
        }

        # 成本估算
        scheme.capital_cost = 60.0  # 亿元
        scheme.annual_maintenance = 5000.0  # 万元
        scheme.expected_life = 50.0  # 年
        scheme.expected_availability = 0.98
        scheme.expected_efficiency = 0.94

        # 传感器配置
        scheme.sensor_config = {
            'redundancy': True,
            'diagnostic_sensors': 50,
            'smart_sensors': 30,
            'total_sensors': 200,
        }

        self.schemes[scheme.scheme_id] = scheme
        return scheme

    def create_extreme_scheme(self) -> DesignScheme:
        """创建极限设计方案（方案二：理论极限版）"""
        scheme = DesignScheme(
            scheme_id="YJ_EXTREME_01",
            name="雅江一级开发方案-理论极限",
            version="1.0",
            description="2000m超高水头开发，Pelton机组",
            design_level=DesignLevel.L4_HIGH,
        )

        # 水力参数
        scheme.hydraulic_params = {
            'rated_head': DesignParameter(
                name="额定水头", value=2100.0, unit="m",
                min_value=1800.0, max_value=2400.0,
                category="hydraulic"
            ),
            'rated_flow': DesignParameter(
                name="额定流量", value=40.0, unit="m³/s",
                min_value=30.0, max_value=50.0,
                category="hydraulic"
            ),
            'tunnel_length': DesignParameter(
                name="隧洞长度", value=45000.0, unit="m",
                min_value=40000.0, max_value=50000.0,
                category="hydraulic", is_optimizable=False
            ),
            'tunnel_diameter': DesignParameter(
                name="隧洞直径", value=6.0, unit="m",
                min_value=5.0, max_value=8.0,
                category="hydraulic"
            ),
        }

        # 水轮机参数（Pelton）
        scheme.turbine_params = {
            'rated_power': DesignParameter(
                name="额定功率", value=800.0, unit="MW",
                min_value=600.0, max_value=1000.0,
                category="turbine"
            ),
            'rated_speed': DesignParameter(
                name="额定转速", value=300.0, unit="r/min",
                min_value=250.0, max_value=375.0,
                category="turbine"
            ),
            'num_nozzles': DesignParameter(
                name="喷嘴数量", value=6.0, unit="",
                min_value=4.0, max_value=8.0,
                category="turbine"
            ),
        }

        # 成本（极限方案成本更高）
        scheme.capital_cost = 120.0  # 亿元
        scheme.annual_maintenance = 8000.0  # 万元
        scheme.expected_availability = 0.95  # 挑战更大
        scheme.expected_efficiency = 0.92

        scheme.sensor_config = {
            'redundancy': True,
            'diagnostic_sensors': 80,
            'smart_sensors': 60,
            'total_sensors': 350,
        }

        self.schemes[scheme.scheme_id] = scheme
        return scheme

    def create_intelligent_scheme(self) -> DesignScheme:
        """创建智能化设计方案（面向L5自动化）"""
        scheme = DesignScheme(
            scheme_id="YJ_INTELLIGENT_01",
            name="雅江智能化方案-无人值守",
            version="1.0",
            description="面向L5级别全自动化运行的设计方案",
            design_level=DesignLevel.L5_FULL,
        )

        # 基于基准方案的水力参数
        scheme.hydraulic_params = {
            'rated_head': DesignParameter(
                name="额定水头", value=480.0, unit="m",
                min_value=400.0, max_value=550.0,
                category="hydraulic"
            ),
            'rated_flow': DesignParameter(
                name="额定流量", value=210.0, unit="m³/s",
                min_value=180.0, max_value=250.0,
                category="hydraulic"
            ),
            'surge_tank_diameter': DesignParameter(
                name="调压室直径", value=50.0, unit="m",  # 更大的调压室
                min_value=40.0, max_value=60.0,
                category="hydraulic"
            ),
        }

        # 增强的控制参数（MPC为主）
        scheme.control_params = {
            'control_type': DesignParameter(
                name="控制类型", value=2.0, unit="",  # 2=MPC
                min_value=1.0, max_value=3.0,
                category="control"
            ),
            'prediction_horizon': DesignParameter(
                name="预测时域", value=30.0, unit="步",
                min_value=10.0, max_value=50.0,
                category="control"
            ),
            'ai_enabled': DesignParameter(
                name="AI使能", value=1.0, unit="",
                min_value=0.0, max_value=1.0,
                category="control"
            ),
        }

        # 更高的投资但更高的自动化
        scheme.capital_cost = 80.0  # 亿元（增加智能化投入）
        scheme.annual_maintenance = 3000.0  # 无人值守降低维护成本
        scheme.expected_availability = 0.995  # 更高可用率
        scheme.expected_efficiency = 0.95
        scheme.automation_level = 1.0

        # 强化的传感器配置
        scheme.sensor_config = {
            'redundancy': True,
            'triple_redundancy': True,
            'diagnostic_sensors': 100,
            'smart_sensors': 80,
            'ai_sensors': 50,
            'total_sensors': 400,
        }

        self.schemes[scheme.scheme_id] = scheme
        return scheme

    def optimize_scheme(
        self,
        scheme: DesignScheme,
        objective: OptimizationObjective,
        simulation_func: Optional[Callable] = None
    ) -> OptimizationResult:
        """
        优化设计方案

        Args:
            scheme: 待优化的设计方案
            objective: 优化目标
            simulation_func: 仿真评估函数

        Returns:
            优化结果
        """
        import time
        start_time = time.time()

        # 获取可优化参数
        optimizable_params = []
        param_bounds = []

        for category in [scheme.hydraulic_params, scheme.turbine_params,
                        scheme.control_params]:
            for name, param in category.items():
                if param.is_optimizable:
                    optimizable_params.append((category, name))
                    param_bounds.append((param.min_value, param.max_value))

        if not optimizable_params:
            return OptimizationResult(
                scheme_id=scheme.scheme_id,
                objective=objective,
                optimal_value=0,
                optimal_params={},
            )

        # 遗传算法优化
        population = self._initialize_population(param_bounds)
        convergence_history = []

        for gen in range(self.optimization_config['max_generations']):
            # 评估适应度
            fitness = []
            for individual in population:
                # 更新参数
                for i, (category, name) in enumerate(optimizable_params):
                    category[name].value = individual[i]

                # 评估（使用仿真或简化模型）
                if simulation_func:
                    score = simulation_func(scheme)
                else:
                    score = self._evaluate_objective(scheme, objective)

                fitness.append(score)

            # 记录最优值
            best_fitness = max(fitness) if objective != OptimizationObjective.COST else min(fitness)
            convergence_history.append(best_fitness)

            # 选择、交叉、变异
            population = self._evolve_population(population, fitness, param_bounds)

        # 获取最优解
        best_idx = np.argmax(fitness) if objective != OptimizationObjective.COST else np.argmin(fitness)
        optimal_params = {
            f"{name}": population[best_idx][i]
            for i, (_, name) in enumerate(optimizable_params)
        }

        computation_time = time.time() - start_time

        result = OptimizationResult(
            scheme_id=scheme.scheme_id,
            objective=objective,
            optimal_value=fitness[best_idx],
            optimal_params=optimal_params,
            convergence_history=convergence_history,
            computation_time=computation_time,
            iterations=self.optimization_config['max_generations'],
        )

        self.optimization_history.append(result)

        return result

    def _initialize_population(self, bounds: List[Tuple[float, float]]) -> np.ndarray:
        """初始化种群"""
        pop_size = self.optimization_config['population_size']
        n_params = len(bounds)

        population = np.zeros((pop_size, n_params))
        for i, (low, high) in enumerate(bounds):
            population[:, i] = np.random.uniform(low, high, pop_size)

        return population

    def _evolve_population(
        self,
        population: np.ndarray,
        fitness: List[float],
        bounds: List[Tuple[float, float]]
    ) -> np.ndarray:
        """进化种群"""
        pop_size = len(population)
        n_params = population.shape[1]
        new_population = np.zeros_like(population)

        # 精英保留
        elite_size = max(2, pop_size // 10)
        elite_indices = np.argsort(fitness)[-elite_size:]
        new_population[:elite_size] = population[elite_indices]

        # 选择、交叉、变异
        for i in range(elite_size, pop_size):
            # 锦标赛选择
            p1, p2 = self._tournament_select(population, fitness, 2)

            # 交叉
            if np.random.random() < self.optimization_config['crossover_rate']:
                child = self._crossover(p1, p2)
            else:
                child = p1.copy()

            # 变异
            if np.random.random() < self.optimization_config['mutation_rate']:
                child = self._mutate(child, bounds)

            new_population[i] = child

        return new_population

    def _tournament_select(
        self,
        population: np.ndarray,
        fitness: List[float],
        k: int = 3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """锦标赛选择"""
        selected = []
        for _ in range(2):
            candidates = np.random.choice(len(population), k, replace=False)
            winner = candidates[np.argmax([fitness[c] for c in candidates])]
            selected.append(population[winner])
        return selected[0], selected[1]

    def _crossover(self, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
        """交叉操作"""
        alpha = np.random.random(len(p1))
        return alpha * p1 + (1 - alpha) * p2

    def _mutate(
        self,
        individual: np.ndarray,
        bounds: List[Tuple[float, float]]
    ) -> np.ndarray:
        """变异操作"""
        for i in range(len(individual)):
            if np.random.random() < 0.2:
                low, high = bounds[i]
                individual[i] = np.random.uniform(low, high)
        return individual

    def _evaluate_objective(
        self,
        scheme: DesignScheme,
        objective: OptimizationObjective
    ) -> float:
        """评估目标函数"""
        if objective == OptimizationObjective.COST:
            return -scheme.capital_cost  # 负号用于最小化

        elif objective == OptimizationObjective.EFFICIENCY:
            return scheme.expected_efficiency

        elif objective == OptimizationObjective.RELIABILITY:
            return scheme.expected_availability

        elif objective == OptimizationObjective.SAFETY:
            # 安全裕度评估
            Tw = 12.0  # 水流惯性时间常数
            if 'surge_tank_diameter' in scheme.hydraulic_params:
                D = scheme.hydraulic_params['surge_tank_diameter'].value
                safety_margin = D / 45.0  # 相对于基准的裕度
            else:
                safety_margin = 1.0
            return safety_margin

        elif objective == OptimizationObjective.LIFECYCLE:
            # 全生命周期效益
            annual_revenue = scheme.expected_efficiency * 1000 * 0.5 * 8760 * 0.3  # 简化收益模型
            total_cost = scheme.capital_cost * 1e8 + scheme.annual_maintenance * 1e4 * scheme.expected_life
            total_revenue = annual_revenue * 1e4 * scheme.expected_life
            npv = total_revenue - total_cost
            return npv / 1e10  # 归一化

        return 0.0

    def compare_all_schemes(self) -> ComparisonResult:
        """对比所有已创建的方案"""
        schemes = list(self.schemes.values())
        return self.comparator.compare(schemes)

    def export_schemes(self, filepath: str):
        """导出所有方案"""
        data = {
            scheme_id: scheme.to_dict()
            for scheme_id, scheme in self.schemes.items()
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def generate_design_report(self) -> str:
        """生成设计报告"""
        report = """
雅江水电梯级设计优化报告
========================

1. 设计方案概述
"""
        for scheme_id, scheme in self.schemes.items():
            report += f"""
   方案: {scheme.name}
   - ID: {scheme_id}
   - 设计等级: {scheme.design_level.name}
   - 投资: {scheme.capital_cost}亿元
   - 预期效率: {scheme.expected_efficiency*100:.1f}%
   - 预期可用率: {scheme.expected_availability*100:.1f}%
"""

        if self.optimization_history:
            report += "\n2. 优化历史\n"
            for result in self.optimization_history[-5:]:
                report += f"""
   - 方案: {result.scheme_id}
   - 目标: {result.objective.name}
   - 最优值: {result.optimal_value:.4f}
   - 迭代次数: {result.iterations}
"""

        return report
