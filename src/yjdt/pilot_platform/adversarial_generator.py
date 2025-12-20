# -*- coding: utf-8 -*-
"""
对抗性场景生成引擎 - Adversarial Scenario Generation Engine

功能：
- 利用GAN/扩散模型自动搜索系统崩溃点
- 生成"物理上可能发生，但人类专家想不到"的长尾场景
- 千万级全谱系测试用例生成
- 极限组合场景合成

核心理念：为智能体提供"魔鬼试卷"
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
from enum import Enum
import random


class ScenarioDimension(Enum):
    """场景维度"""
    NATURAL = "natural"             # 自然环境
    HYDRAULIC = "hydraulic"         # 水力工况
    EQUIPMENT = "equipment"         # 设备故障
    HUMAN = "human"                 # 人为因素
    CYBER = "cyber"                 # 网络攻击
    COMBINED = "combined"           # 组合叠加


class SeverityLevel(Enum):
    """严重等级"""
    NORMAL = 0                      # 正常
    MINOR = 1                       # 轻微
    MODERATE = 2                    # 中等
    SEVERE = 3                      # 严重
    CATASTROPHIC = 4                # 灾难性
    BEYOND_DESIGN = 5               # 超设计基准


@dataclass
class CornerCase:
    """长尾极端场景"""
    case_id: str
    name: str
    description: str
    dimensions: List[ScenarioDimension]
    severity: SeverityLevel
    probability: float              # 发生概率

    # 场景参数
    parameters: Dict[str, Any]

    # 时序事件链
    event_chain: List[Dict[str, Any]]

    # 预期系统响应
    expected_response: Dict[str, Any]

    # 失效模式
    failure_modes: List[str]

    # 元数据
    generated_by: str = "adversarial_generator"
    generation_time: datetime = field(default_factory=datetime.now)
    verified: bool = False


@dataclass
class GenerationResult:
    """生成结果"""
    total_generated: int
    corner_cases: List[CornerCase]
    failure_distribution: Dict[str, int]
    coverage_matrix: Dict[str, float]
    generation_time_seconds: float


class CornerCaseSearcher:
    """
    长尾场景搜索器

    使用梯度引导搜索寻找系统崩溃边界
    """

    def __init__(self, system_model: Any = None):
        self.system_model = system_model

        # 搜索空间定义
        self.parameter_ranges = {}

        # 已发现的崩溃点
        self.crash_points: List[Dict] = []

        # 搜索历史
        self.search_history: List[Dict] = []

    def define_search_space(self, parameter_ranges: Dict[str, Tuple[float, float]]):
        """
        定义搜索空间

        Args:
            parameter_ranges: 参数范围字典 {参数名: (最小值, 最大值)}
        """
        self.parameter_ranges = parameter_ranges

    def search(self, n_iterations: int = 1000,
               fitness_function: Callable = None) -> List[Dict]:
        """
        搜索崩溃边界

        使用遗传算法+梯度引导

        Args:
            n_iterations: 迭代次数
            fitness_function: 适应度函数（值越大越接近崩溃）

        Returns:
            崩溃点列表
        """
        if not self.parameter_ranges:
            raise ValueError("搜索空间未定义")

        # 初始化种群
        population_size = 50
        population = self._initialize_population(population_size)

        for iteration in range(n_iterations):
            # 评估适应度
            fitness_scores = []
            for individual in population:
                if fitness_function:
                    score = fitness_function(individual)
                else:
                    score = self._default_fitness(individual)
                fitness_scores.append(score)

            # 记录高适应度个体（接近崩溃点）
            max_idx = np.argmax(fitness_scores)
            if fitness_scores[max_idx] > 0.9:
                self.crash_points.append({
                    "parameters": population[max_idx].copy(),
                    "fitness": fitness_scores[max_idx],
                    "iteration": iteration,
                })

            # 选择
            selected = self._selection(population, fitness_scores)

            # 交叉
            offspring = self._crossover(selected)

            # 变异
            offspring = self._mutation(offspring)

            # 更新种群
            population = offspring

            self.search_history.append({
                "iteration": iteration,
                "best_fitness": max(fitness_scores),
                "avg_fitness": np.mean(fitness_scores),
            })

        return self.crash_points

    def _initialize_population(self, size: int) -> List[Dict]:
        """初始化种群"""
        population = []
        for _ in range(size):
            individual = {}
            for param, (low, high) in self.parameter_ranges.items():
                individual[param] = np.random.uniform(low, high)
            population.append(individual)
        return population

    def _default_fitness(self, individual: Dict) -> float:
        """默认适应度函数"""
        # 距离边界越近，适应度越高
        score = 0
        for param, value in individual.items():
            low, high = self.parameter_ranges[param]
            range_size = high - low
            # 偏离中心的程度
            center = (low + high) / 2
            deviation = abs(value - center) / (range_size / 2)
            score += deviation

        return score / len(individual)

    def _selection(self, population: List[Dict],
                   fitness: List[float]) -> List[Dict]:
        """轮盘赌选择"""
        total = sum(fitness) + 1e-6
        probs = [f / total for f in fitness]

        selected_indices = np.random.choice(
            len(population),
            size=len(population),
            p=probs,
            replace=True
        )

        return [population[i].copy() for i in selected_indices]

    def _crossover(self, population: List[Dict],
                   rate: float = 0.8) -> List[Dict]:
        """交叉"""
        offspring = []

        for i in range(0, len(population), 2):
            p1 = population[i]
            p2 = population[i + 1] if i + 1 < len(population) else population[0]

            if np.random.random() < rate:
                child1, child2 = {}, {}
                for param in p1:
                    if np.random.random() < 0.5:
                        child1[param] = p1[param]
                        child2[param] = p2[param]
                    else:
                        child1[param] = p2[param]
                        child2[param] = p1[param]
                offspring.extend([child1, child2])
            else:
                offspring.extend([p1.copy(), p2.copy()])

        return offspring[:len(population)]

    def _mutation(self, population: List[Dict],
                  rate: float = 0.1) -> List[Dict]:
        """变异"""
        for individual in population:
            for param in individual:
                if np.random.random() < rate:
                    low, high = self.parameter_ranges[param]
                    individual[param] = np.random.uniform(low, high)

        return population


class FailureModeSynthesizer:
    """
    失效模式合成器

    合成复杂的多重故障叠加场景
    """

    def __init__(self):
        # 基础失效模式库
        self.failure_modes = self._initialize_failure_modes()

        # 组合规则
        self.combination_rules = self._initialize_combination_rules()

    def _initialize_failure_modes(self) -> Dict[str, Dict]:
        """初始化失效模式库"""
        return {
            # 自然灾害
            "earthquake_viii": {
                "dimension": ScenarioDimension.NATURAL,
                "severity": SeverityLevel.SEVERE,
                "probability": 1e-3,
                "effects": ["structure_damage", "equipment_shift", "comm_interrupt"],
            },
            "earthquake_xi": {
                "dimension": ScenarioDimension.NATURAL,
                "severity": SeverityLevel.BEYOND_DESIGN,
                "probability": 1e-5,
                "effects": ["structure_collapse", "dam_crack", "total_blackout"],
            },
            "glacier_outburst": {
                "dimension": ScenarioDimension.NATURAL,
                "severity": SeverityLevel.CATASTROPHIC,
                "probability": 1e-4,
                "effects": ["sudden_flood", "debris_flow", "dam_overtopping"],
            },
            "ice_dam_formation": {
                "dimension": ScenarioDimension.NATURAL,
                "severity": SeverityLevel.SEVERE,
                "probability": 5e-3,
                "effects": ["flow_blockage", "water_level_drop", "sudden_release"],
            },
            "extreme_cold": {
                "dimension": ScenarioDimension.NATURAL,
                "severity": SeverityLevel.MODERATE,
                "probability": 1e-2,
                "effects": ["ice_formation", "equipment_malfunction", "oil_viscosity"],
            },

            # 水力工况
            "load_rejection_full": {
                "dimension": ScenarioDimension.HYDRAULIC,
                "severity": SeverityLevel.SEVERE,
                "probability": 1e-4,
                "effects": ["water_hammer", "surge_tank_overflow", "speed_rise"],
            },
            "black_start": {
                "dimension": ScenarioDimension.HYDRAULIC,
                "severity": SeverityLevel.MODERATE,
                "probability": 1e-3,
                "effects": ["islanding", "frequency_instability", "voltage_variation"],
            },
            "cavitation_severe": {
                "dimension": ScenarioDimension.HYDRAULIC,
                "severity": SeverityLevel.MODERATE,
                "probability": 5e-3,
                "effects": ["vibration_increase", "efficiency_drop", "blade_damage"],
            },

            # 设备故障
            "governor_failure": {
                "dimension": ScenarioDimension.EQUIPMENT,
                "severity": SeverityLevel.SEVERE,
                "probability": 1e-4,
                "effects": ["speed_uncontrolled", "guide_vane_stuck", "emergency_close"],
            },
            "exciter_failure": {
                "dimension": ScenarioDimension.EQUIPMENT,
                "severity": SeverityLevel.SEVERE,
                "probability": 1e-4,
                "effects": ["loss_of_field", "reactive_deficit", "out_of_step"],
            },
            "sensor_drift": {
                "dimension": ScenarioDimension.EQUIPMENT,
                "severity": SeverityLevel.MINOR,
                "probability": 1e-2,
                "effects": ["wrong_measurement", "control_deviation", "false_alarm"],
            },
            "valve_stuck": {
                "dimension": ScenarioDimension.EQUIPMENT,
                "severity": SeverityLevel.MODERATE,
                "probability": 5e-3,
                "effects": ["flow_uncontrolled", "manual_intervention", "emergency_drain"],
            },

            # 通信故障
            "comm_total_loss": {
                "dimension": ScenarioDimension.CYBER,
                "severity": SeverityLevel.SEVERE,
                "probability": 1e-4,
                "effects": ["island_mode", "local_control", "no_remote_monitor"],
            },
            "satellite_outage": {
                "dimension": ScenarioDimension.CYBER,
                "severity": SeverityLevel.MODERATE,
                "probability": 1e-3,
                "effects": ["backup_comm", "delayed_data", "no_weather_update"],
            },
            "cyber_attack": {
                "dimension": ScenarioDimension.CYBER,
                "severity": SeverityLevel.CATASTROPHIC,
                "probability": 1e-5,
                "effects": ["false_commands", "data_corruption", "system_takeover"],
            },

            # 人为因素
            "operator_error": {
                "dimension": ScenarioDimension.HUMAN,
                "severity": SeverityLevel.MODERATE,
                "probability": 1e-2,
                "effects": ["wrong_operation", "procedure_violation", "delayed_response"],
            },
            "maintenance_incomplete": {
                "dimension": ScenarioDimension.HUMAN,
                "severity": SeverityLevel.MINOR,
                "probability": 5e-2,
                "effects": ["latent_defect", "unexpected_failure", "reduced_reliability"],
            },
        }

    def _initialize_combination_rules(self) -> List[Dict]:
        """初始化组合规则"""
        return [
            # 灾害链规则
            {
                "name": "地震灾害链",
                "trigger": "earthquake_viii",
                "followup": ["comm_total_loss", "sensor_drift", "valve_stuck"],
                "probability_multiplier": 0.3,
            },
            {
                "name": "冰川灾害链",
                "trigger": "glacier_outburst",
                "followup": ["load_rejection_full", "comm_total_loss"],
                "probability_multiplier": 0.5,
            },
            {
                "name": "极寒连锁",
                "trigger": "extreme_cold",
                "followup": ["sensor_drift", "valve_stuck", "satellite_outage"],
                "probability_multiplier": 0.4,
            },
        ]

    def synthesize(self, n_scenarios: int = 100,
                   max_combination: int = 4) -> List[CornerCase]:
        """
        合成复杂场景

        Args:
            n_scenarios: 生成数量
            max_combination: 最大叠加故障数

        Returns:
            极端场景列表
        """
        scenarios = []
        mode_names = list(self.failure_modes.keys())

        for i in range(n_scenarios):
            # 随机选择叠加数量
            n_combine = np.random.randint(1, max_combination + 1)

            # 选择失效模式
            selected_modes = random.sample(mode_names, min(n_combine, len(mode_names)))

            # 合并效应
            combined_effects = []
            combined_severity = SeverityLevel.NORMAL
            combined_probability = 1.0
            dimensions = set()

            for mode_name in selected_modes:
                mode = self.failure_modes[mode_name]
                combined_effects.extend(mode["effects"])
                dimensions.add(mode["dimension"])
                combined_probability *= mode["probability"]

                if mode["severity"].value > combined_severity.value:
                    combined_severity = mode["severity"]

            # 检查是否触发灾害链
            for rule in self.combination_rules:
                if rule["trigger"] in selected_modes:
                    for followup in rule["followup"]:
                        if followup not in selected_modes:
                            selected_modes.append(followup)
                            mode = self.failure_modes[followup]
                            combined_effects.extend(mode["effects"])
                            dimensions.add(mode["dimension"])
                    combined_probability *= rule["probability_multiplier"]

            # 生成时序事件链
            event_chain = self._generate_event_chain(selected_modes)

            # 创建场景
            scenario = CornerCase(
                case_id=f"ADV_{i+1:06d}",
                name=f"组合场景_{'+'.join(selected_modes[:3])}",
                description=f"包含{len(selected_modes)}个失效模式的复杂场景",
                dimensions=list(dimensions),
                severity=combined_severity,
                probability=combined_probability,
                parameters={"modes": selected_modes},
                event_chain=event_chain,
                expected_response=self._generate_expected_response(combined_severity),
                failure_modes=list(set(combined_effects)),
            )

            scenarios.append(scenario)

        return scenarios

    def _generate_event_chain(self, modes: List[str]) -> List[Dict]:
        """生成时序事件链"""
        events = []
        time = 0

        for mode in modes:
            events.append({
                "time": time,
                "event": mode,
                "description": f"触发{mode}",
            })
            time += np.random.randint(1, 60)  # 1-60秒间隔

        return sorted(events, key=lambda x: x["time"])

    def _generate_expected_response(self, severity: SeverityLevel) -> Dict:
        """生成预期响应"""
        if severity == SeverityLevel.BEYOND_DESIGN:
            return {
                "action": "emergency_shutdown",
                "max_response_time_s": 5,
                "safety_systems": ["dam_protection", "flood_gate", "emergency_drain"],
            }
        elif severity == SeverityLevel.CATASTROPHIC:
            return {
                "action": "controlled_shutdown",
                "max_response_time_s": 30,
                "safety_systems": ["unit_trip", "spillway_open"],
            }
        elif severity == SeverityLevel.SEVERE:
            return {
                "action": "load_reduction",
                "max_response_time_s": 60,
                "safety_systems": ["backup_systems"],
            }
        else:
            return {
                "action": "alarm_and_monitor",
                "max_response_time_s": 300,
                "safety_systems": [],
            }


class ScenarioDiffusionModel:
    """
    场景扩散模型

    基于扩散模型生成新颖的极端场景
    (简化实现，实际应用需要深度学习框架)
    """

    def __init__(self, latent_dim: int = 32):
        self.latent_dim = latent_dim

        # 场景嵌入
        self.scenario_embeddings: List[np.ndarray] = []

        # 生成器参数
        self.noise_schedule = np.linspace(1e-4, 0.02, 1000)

    def fit(self, scenarios: List[CornerCase]):
        """
        学习场景分布

        Args:
            scenarios: 训练场景列表
        """
        for scenario in scenarios:
            embedding = self._embed_scenario(scenario)
            self.scenario_embeddings.append(embedding)

    def _embed_scenario(self, scenario: CornerCase) -> np.ndarray:
        """场景嵌入"""
        embedding = np.zeros(self.latent_dim)

        # 维度编码
        for i, dim in enumerate(ScenarioDimension):
            if dim in scenario.dimensions:
                embedding[i] = 1

        # 严重等级编码
        embedding[10] = scenario.severity.value / 5

        # 概率编码
        embedding[11] = -np.log10(scenario.probability + 1e-10) / 10

        # 事件链长度
        embedding[12] = len(scenario.event_chain) / 10

        # 失效模式数量
        embedding[13] = len(scenario.failure_modes) / 20

        # 随机特征
        embedding[14:] = np.random.randn(self.latent_dim - 14) * 0.1

        return embedding

    def generate(self, n_samples: int = 10,
                 temperature: float = 1.0) -> List[CornerCase]:
        """
        生成新场景

        Args:
            n_samples: 生成数量
            temperature: 采样温度（越高越多样）

        Returns:
            生成的场景列表
        """
        if len(self.scenario_embeddings) == 0:
            # 从头生成
            return self._generate_from_prior(n_samples, temperature)

        generated = []

        for i in range(n_samples):
            # 从现有嵌入插值
            if len(self.scenario_embeddings) >= 2:
                idx1, idx2 = np.random.choice(len(self.scenario_embeddings), 2, replace=False)
                alpha = np.random.beta(0.5, 0.5)  # 偏向极端值
                embedding = (1 - alpha) * self.scenario_embeddings[idx1] + \
                           alpha * self.scenario_embeddings[idx2]
            else:
                embedding = self.scenario_embeddings[0] + np.random.randn(self.latent_dim) * temperature

            # 添加噪声
            embedding += np.random.randn(self.latent_dim) * temperature * 0.1

            # 解码为场景
            scenario = self._decode_embedding(embedding, i)
            generated.append(scenario)

        return generated

    def _generate_from_prior(self, n_samples: int,
                             temperature: float) -> List[CornerCase]:
        """从先验分布生成"""
        synthesizer = FailureModeSynthesizer()
        return synthesizer.synthesize(n_samples)

    def _decode_embedding(self, embedding: np.ndarray,
                          idx: int) -> CornerCase:
        """解码嵌入为场景"""
        # 解码维度
        dimensions = []
        for i, dim in enumerate(ScenarioDimension):
            if i < 6 and embedding[i] > 0.5:
                dimensions.append(dim)

        if not dimensions:
            dimensions = [ScenarioDimension.EQUIPMENT]

        # 解码严重等级
        severity_val = int(np.clip(embedding[10] * 5, 0, 5))
        severity = SeverityLevel(severity_val)

        # 解码概率
        probability = 10 ** (-embedding[11] * 10)

        return CornerCase(
            case_id=f"DIFF_{idx:06d}",
            name=f"扩散生成场景_{idx}",
            description="基于扩散模型生成的新颖场景",
            dimensions=dimensions,
            severity=severity,
            probability=probability,
            parameters={"embedding": embedding.tolist()},
            event_chain=[{"time": 0, "event": "scenario_start"}],
            expected_response={"action": "evaluate_and_respond"},
            failure_modes=["generated_mode"],
            generated_by="diffusion_model",
        )


class AdversarialScenarioGenerator:
    """
    对抗性场景生成引擎

    整合多种生成方法，构建千万级全谱系测试用例库
    """

    def __init__(self):
        self.corner_case_searcher = CornerCaseSearcher()
        self.failure_synthesizer = FailureModeSynthesizer()
        self.diffusion_model = ScenarioDiffusionModel()

        # 场景库
        self.scenario_library: Dict[str, CornerCase] = {}

        # 统计
        self.generation_stats = {
            "total_generated": 0,
            "by_method": {},
            "by_severity": {},
            "by_dimension": {},
        }

    def generate_full_spectrum(self, n_scenarios: int = 10000,
                               methods: List[str] = None) -> GenerationResult:
        """
        生成全谱系场景库

        Args:
            n_scenarios: 目标场景数量
            methods: 使用的方法列表

        Returns:
            生成结果
        """
        start_time = datetime.now()

        if methods is None:
            methods = ["synthesis", "search", "diffusion"]

        all_scenarios = []

        # 方法1：故障模式合成
        if "synthesis" in methods:
            n_synth = n_scenarios // 3
            synth_scenarios = self.failure_synthesizer.synthesize(n_synth)
            all_scenarios.extend(synth_scenarios)
            self.generation_stats["by_method"]["synthesis"] = len(synth_scenarios)

        # 方法2：崩溃边界搜索
        if "search" in methods:
            self._setup_search_space()
            crash_points = self.corner_case_searcher.search(n_iterations=500)
            search_scenarios = self._crash_points_to_scenarios(crash_points)
            all_scenarios.extend(search_scenarios)
            self.generation_stats["by_method"]["search"] = len(search_scenarios)

        # 方法3：扩散模型生成
        if "diffusion" in methods:
            # 用已有场景训练
            if all_scenarios:
                self.diffusion_model.fit(all_scenarios[:100])

            n_diff = n_scenarios - len(all_scenarios)
            diff_scenarios = self.diffusion_model.generate(max(0, n_diff))
            all_scenarios.extend(diff_scenarios)
            self.generation_stats["by_method"]["diffusion"] = len(diff_scenarios)

        # 统计分布
        failure_distribution = {}
        coverage_matrix = {}

        for scenario in all_scenarios:
            self.scenario_library[scenario.case_id] = scenario

            # 严重等级分布
            sev = scenario.severity.name
            self.generation_stats["by_severity"][sev] = \
                self.generation_stats["by_severity"].get(sev, 0) + 1

            # 维度分布
            for dim in scenario.dimensions:
                dim_name = dim.name
                self.generation_stats["by_dimension"][dim_name] = \
                    self.generation_stats["by_dimension"].get(dim_name, 0) + 1

            # 失效模式分布
            for mode in scenario.failure_modes:
                failure_distribution[mode] = failure_distribution.get(mode, 0) + 1

        self.generation_stats["total_generated"] = len(all_scenarios)

        # 计算覆盖矩阵
        for dim in ScenarioDimension:
            for sev in SeverityLevel:
                key = f"{dim.name}_{sev.name}"
                count = sum(1 for s in all_scenarios
                           if dim in s.dimensions and s.severity == sev)
                coverage_matrix[key] = count / max(1, len(all_scenarios))

        end_time = datetime.now()

        return GenerationResult(
            total_generated=len(all_scenarios),
            corner_cases=all_scenarios,
            failure_distribution=failure_distribution,
            coverage_matrix=coverage_matrix,
            generation_time_seconds=(end_time - start_time).total_seconds(),
        )

    def _setup_search_space(self):
        """设置搜索空间"""
        self.corner_case_searcher.define_search_space({
            "water_head": (100, 2000),
            "flow_rate": (0, 500),
            "temperature": (-40, 40),
            "earthquake_intensity": (0, 12),
            "wind_speed": (0, 50),
            "sediment_concentration": (0, 100),
            "grid_frequency_deviation": (-5, 5),
            "communication_delay": (0, 10),
        })

    def _crash_points_to_scenarios(self,
                                    crash_points: List[Dict]) -> List[CornerCase]:
        """将崩溃点转换为场景"""
        scenarios = []

        for i, point in enumerate(crash_points):
            params = point.get("parameters", {})

            # 判断维度
            dimensions = []
            if params.get("earthquake_intensity", 0) > 6:
                dimensions.append(ScenarioDimension.NATURAL)
            if params.get("water_head", 0) > 1500:
                dimensions.append(ScenarioDimension.HYDRAULIC)
            if params.get("communication_delay", 0) > 5:
                dimensions.append(ScenarioDimension.CYBER)

            if not dimensions:
                dimensions = [ScenarioDimension.COMBINED]

            # 判断严重等级
            fitness = point.get("fitness", 0)
            if fitness > 0.95:
                severity = SeverityLevel.BEYOND_DESIGN
            elif fitness > 0.85:
                severity = SeverityLevel.CATASTROPHIC
            elif fitness > 0.7:
                severity = SeverityLevel.SEVERE
            else:
                severity = SeverityLevel.MODERATE

            scenario = CornerCase(
                case_id=f"SEARCH_{i:06d}",
                name=f"搜索发现崩溃点_{i}",
                description=f"通过遗传算法搜索发现，适应度{fitness:.3f}",
                dimensions=dimensions,
                severity=severity,
                probability=1e-6,  # 极端场景
                parameters=params,
                event_chain=[{"time": 0, "event": "boundary_condition"}],
                expected_response={"action": "emergency_shutdown"},
                failure_modes=["system_crash"],
                generated_by="corner_case_search",
            )

            scenarios.append(scenario)

        return scenarios

    def get_scenario_by_id(self, case_id: str) -> Optional[CornerCase]:
        """按ID获取场景"""
        return self.scenario_library.get(case_id)

    def filter_scenarios(self, severity: SeverityLevel = None,
                         dimension: ScenarioDimension = None,
                         min_probability: float = None) -> List[CornerCase]:
        """过滤场景"""
        results = list(self.scenario_library.values())

        if severity:
            results = [s for s in results if s.severity == severity]

        if dimension:
            results = [s for s in results if dimension in s.dimensions]

        if min_probability:
            results = [s for s in results if s.probability >= min_probability]

        return results

    def export_library(self, filepath: str):
        """导出场景库"""
        import json

        data = {
            "metadata": {
                "total_scenarios": len(self.scenario_library),
                "generation_stats": self.generation_stats,
                "export_time": datetime.now().isoformat(),
            },
            "scenarios": [
                {
                    "case_id": s.case_id,
                    "name": s.name,
                    "description": s.description,
                    "dimensions": [d.value for d in s.dimensions],
                    "severity": s.severity.value,
                    "probability": s.probability,
                    "parameters": s.parameters,
                    "event_chain": s.event_chain,
                    "failure_modes": s.failure_modes,
                }
                for s in self.scenario_library.values()
            ],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

