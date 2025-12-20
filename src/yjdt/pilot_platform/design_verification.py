# -*- coding: utf-8 -*-
"""
设计验证风洞模块 - Design Verification Wind Tunnel

功能：
- 多方案比选优化
- 调压室参数优化
- 水锤分析
- 过渡过程仿真
- 设计方案验证

基于YX工程特殊需求：
- 2000m超高水头
- 45km超长隧洞
- 多级调压室系统
- 极端工况验证
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import threading


class DesignObjective(Enum):
    """设计目标"""
    MIN_WATERHAMMER = "min_waterhammer"        # 最小水锤压力
    MIN_SURGE = "min_surge"                    # 最小涌浪
    MIN_COST = "min_cost"                      # 最小成本
    MAX_STABILITY = "max_stability"            # 最大稳定性
    BALANCED = "balanced"                      # 平衡优化


class OptimizationMethod(Enum):
    """优化方法"""
    GRID_SEARCH = "grid_search"
    GENETIC_ALGORITHM = "genetic"
    PARTICLE_SWARM = "pso"
    DIFFERENTIAL_EVOLUTION = "de"
    BAYESIAN = "bayesian"


@dataclass
class DesignScheme:
    """设计方案"""
    scheme_id: str
    name: str
    description: str

    # 几何参数
    parameters: Dict[str, float] = field(default_factory=dict)

    # 性能指标
    metrics: Dict[str, float] = field(default_factory=dict)

    # 成本估算
    cost: float = 0.0

    # 评分
    score: float = 0.0
    ranking: int = 0


@dataclass
class SurgeTankConfig:
    """调压室配置"""
    tank_type: str = "simple"          # "simple", "throttled", "differential", "air_cushion"

    # 尺寸参数
    diameter: float = 10.0             # 直径 m
    height: float = 50.0               # 高度 m
    area: float = 78.5                 # 面积 m²

    # 阻抗孔参数（阻抗式）
    orifice_diameter: float = 2.0      # 阻抗孔直径 m
    orifice_coefficient: float = 0.6   # 流量系数

    # 差动式参数
    riser_diameter: float = 3.0        # 升管直径 m
    riser_area: float = 7.07           # 升管面积 m²

    # 气垫式参数
    air_volume: float = 1000.0         # 初始气体体积 m³
    air_pressure: float = 2e6          # 初始气压 Pa

    # 位置
    distance_from_turbine: float = 1000.0  # 距水轮机距离 m

    @property
    def thoma_coefficient(self) -> float:
        """托马系数"""
        # 简化计算，实际需要更复杂的分析
        return self.area / 100  # 归一化


@dataclass
class WaterHammerResult:
    """水锤分析结果"""
    max_pressure: float               # 最大压力 Pa
    min_pressure: float               # 最小压力 Pa
    pressure_rise: float              # 压力升高 %
    pressure_drop: float              # 压力下降 %

    # 时序数据
    time_series: List[float] = field(default_factory=list)
    pressure_at_turbine: List[float] = field(default_factory=list)
    pressure_at_surge_tank: List[float] = field(default_factory=list)
    flow_rate: List[float] = field(default_factory=list)

    # 特征值
    wave_period: float = 0.0          # 波动周期 s
    damping_ratio: float = 0.0        # 阻尼比
    settling_time: float = 0.0        # 稳定时间 s


@dataclass
class TransientResult:
    """过渡过程结果"""
    scenario: str                     # 场景名称
    duration: float                   # 持续时间 s

    # 关键指标
    max_speed_rise: float = 0.0       # 最大转速上升 %
    max_speed_drop: float = 0.0       # 最大转速下降 %
    max_pressure_rise: float = 0.0    # 最大压力上升 %
    max_surge_height: float = 0.0     # 最大涌浪高度 m

    # 时序数据
    time: List[float] = field(default_factory=list)
    speed: List[float] = field(default_factory=list)
    power: List[float] = field(default_factory=list)
    pressure: List[float] = field(default_factory=list)
    surge_level: List[float] = field(default_factory=list)

    # 安全评估
    is_safe: bool = True
    violations: List[str] = field(default_factory=list)


class WaterHammerAnalyzer:
    """
    水锤分析器

    功能：
    - 水锤压力计算
    - MOC特征线法求解
    - 压力波传播分析
    - 阀门关闭优化
    """

    def __init__(self):
        # 系统参数
        self.pipe_length = 45000.0     # 管道长度 m（45km）
        self.pipe_diameter = 10.0      # 管道直径 m
        self.pipe_area = 78.5          # 管道面积 m²
        self.wave_speed = 1000.0       # 波速 m/s

        # 边界条件
        self.upstream_head = 2000.0    # 上游水头 m（2000m水头）
        self.downstream_head = 0.0     # 下游水头 m

        # 初始状态
        self.initial_flow = 100.0      # 初始流量 m³/s

        # 数值参数
        self.n_segments = 100          # 管段数
        self.courant_number = 0.95     # 库朗数

    def analyze_valve_closure(self, closure_time: float,
                               closure_pattern: str = "linear") -> WaterHammerResult:
        """
        分析阀门关闭水锤

        Args:
            closure_time: 关闭时间 s
            closure_pattern: 关闭规律 ("linear", "parabolic", "optimized")

        Returns:
            水锤分析结果
        """
        # 计算时间步长
        dx = self.pipe_length / self.n_segments
        dt = self.courant_number * dx / self.wave_speed

        # 计算总仿真时间（水锤波往返几个周期）
        wave_period = 2 * self.pipe_length / self.wave_speed
        total_time = max(closure_time * 2, wave_period * 5)
        n_steps = int(total_time / dt) + 1

        # 初始化
        H = np.ones(self.n_segments + 1) * self.upstream_head  # 水头
        V = np.ones(self.n_segments + 1) * self.initial_flow / self.pipe_area  # 流速

        # 记录
        time_series = []
        pressure_turbine = []
        pressure_surge = []
        flow_rate = []

        # MOC求解
        for step in range(n_steps):
            t = step * dt
            time_series.append(t)

            # 阀门开度
            if t < closure_time:
                if closure_pattern == "linear":
                    tau = 1 - t / closure_time
                elif closure_pattern == "parabolic":
                    tau = (1 - t / closure_time) ** 2
                elif closure_pattern == "optimized":
                    # 两段式关闭：快关-慢关
                    if t < closure_time * 0.7:
                        tau = 1 - 0.8 * (t / (closure_time * 0.7))
                    else:
                        tau = 0.2 - 0.2 * ((t - closure_time * 0.7) / (closure_time * 0.3))
                else:
                    tau = 1 - t / closure_time
            else:
                tau = 0

            # 更新边界条件（简化处理）
            V_new = V.copy()
            H_new = H.copy()

            # 上游边界（恒定水头）
            H_new[0] = self.upstream_head

            # 内部节点（特征线法简化）
            for i in range(1, self.n_segments):
                # C+特征线
                Cp = H[i-1] + self.wave_speed / 9.81 * V[i-1]
                # C-特征线
                Cm = H[i+1] - self.wave_speed / 9.81 * V[i+1]

                H_new[i] = (Cp + Cm) / 2
                V_new[i] = (Cp - Cm) / 2 * 9.81 / self.wave_speed

            # 下游边界（阀门）
            V_new[-1] = tau * self.initial_flow / self.pipe_area
            H_new[-1] = H[-2] + self.wave_speed / 9.81 * (V[-2] - V_new[-1])

            # 更新
            H = H_new
            V = V_new

            # 记录
            pressure_turbine.append(H[-1] * 9810)  # Pa
            pressure_surge.append(H[self.n_segments // 2] * 9810)
            flow_rate.append(V[-1] * self.pipe_area)

        # 计算结果
        p_initial = self.upstream_head * 9810
        max_pressure = max(pressure_turbine)
        min_pressure = min(pressure_turbine)

        result = WaterHammerResult(
            max_pressure=max_pressure,
            min_pressure=min_pressure,
            pressure_rise=(max_pressure - p_initial) / p_initial * 100,
            pressure_drop=(p_initial - min_pressure) / p_initial * 100,
            time_series=time_series,
            pressure_at_turbine=pressure_turbine,
            pressure_at_surge_tank=pressure_surge,
            flow_rate=flow_rate,
            wave_period=wave_period,
        )

        # 计算阻尼比和稳定时间
        self._analyze_damping(result)

        return result

    def _analyze_damping(self, result: WaterHammerResult):
        """分析阻尼特性"""
        if not result.pressure_at_turbine:
            return

        pressure = np.array(result.pressure_at_turbine)
        p_final = pressure[-1]

        # 找峰值
        peaks = []
        for i in range(1, len(pressure) - 1):
            if pressure[i] > pressure[i-1] and pressure[i] > pressure[i+1]:
                if abs(pressure[i] - p_final) > 0.01 * p_final:
                    peaks.append(pressure[i] - p_final)

        if len(peaks) >= 2:
            # 计算对数衰减率
            decay = np.log(abs(peaks[0]) / abs(peaks[-1])) / len(peaks)
            result.damping_ratio = decay / (2 * np.pi)

        # 估算稳定时间（振幅小于2%）
        threshold = 0.02 * abs(pressure.max() - p_final)
        for i, t in enumerate(result.time_series):
            if abs(pressure[i] - p_final) < threshold:
                result.settling_time = t
                break

    def analyze_load_rejection(self, rejection_percent: float = 100.0,
                                rejection_time: float = 0.1) -> WaterHammerResult:
        """
        分析甩负荷水锤

        Args:
            rejection_percent: 甩负荷比例 %
            rejection_time: 甩负荷时间 s

        Returns:
            水锤结果
        """
        # 甩负荷相当于快速关闭阀门
        return self.analyze_valve_closure(
            closure_time=rejection_time,
            closure_pattern="linear"
        )

    def optimize_closure_time(self, max_pressure_limit: float = 1.3,
                               min_time: float = 5.0,
                               max_time: float = 60.0) -> Tuple[float, WaterHammerResult]:
        """
        优化阀门关闭时间

        Args:
            max_pressure_limit: 最大允许压力升高比
            min_time: 最小关闭时间 s
            max_time: 最大关闭时间 s

        Returns:
            最优关闭时间和结果
        """
        p_initial = self.upstream_head * 9810

        # 二分搜索
        low, high = min_time, max_time

        while high - low > 0.5:
            mid = (low + high) / 2
            result = self.analyze_valve_closure(mid, "optimized")

            if result.max_pressure < p_initial * max_pressure_limit:
                high = mid
            else:
                low = mid

        # 返回最优结果
        optimal_time = high
        optimal_result = self.analyze_valve_closure(optimal_time, "optimized")

        return optimal_time, optimal_result


class SurgeTankOptimizer:
    """
    调压室优化器

    功能：
    - 调压室尺寸优化
    - 托马稳定性分析
    - 涌浪高度计算
    - 多调压室系统优化
    """

    def __init__(self):
        # 系统参数
        self.pipe_length = 45000.0     # 隧洞长度 m
        self.pipe_area = 78.5          # 隧洞面积 m²
        self.pipe_friction = 0.015     # 摩阻系数

        self.head = 2000.0             # 水头 m
        self.rated_flow = 100.0        # 额定流量 m³/s

        # 水轮机参数
        self.turbine_inertia = 1e6     # 转动惯量 kg·m²
        self.rated_power = 1000e6      # 额定功率 W

        # 安全限制
        self.max_surge_rise = 0.3      # 最大涌浪上升比
        self.max_surge_drop = 0.2      # 最大涌浪下降比

    def calculate_thoma_coefficient(self, config: SurgeTankConfig) -> float:
        """
        计算托马稳定系数

        Args:
            config: 调压室配置

        Returns:
            托马系数
        """
        # 水头损失
        h_loss = self.pipe_friction * self.pipe_length / (2 * 9.81 * self.pipe_area**2) * self.rated_flow**2

        # 临界面积
        Ac = self.pipe_length * self.pipe_area / h_loss

        # 托马系数
        sigma = config.area / Ac

        return sigma

    def analyze_surge(self, config: SurgeTankConfig,
                      scenario: str = "load_rejection") -> Dict[str, Any]:
        """
        分析涌浪

        Args:
            config: 调压室配置
            scenario: 场景 ("load_rejection", "load_acceptance", "load_oscillation")

        Returns:
            涌浪分析结果
        """
        # 托马系数
        sigma = self.calculate_thoma_coefficient(config)

        # 稳定性判断
        is_stable = sigma > 1.0

        # 涌浪幅度估算
        if config.tank_type == "simple":
            # 简单调压室
            surge_amplitude = self.rated_flow * np.sqrt(
                self.pipe_length / (9.81 * config.area)
            )
        elif config.tank_type == "throttled":
            # 阻抗式调压室
            k = 0.5 * (1 / config.orifice_coefficient - 1)
            surge_amplitude = self.rated_flow * np.sqrt(
                self.pipe_length / (9.81 * config.area)
            ) / (1 + k)
        elif config.tank_type == "differential":
            # 差动式调压室
            surge_amplitude = self.rated_flow * np.sqrt(
                self.pipe_length / (9.81 * (config.area + config.riser_area))
            )
        else:
            surge_amplitude = self.rated_flow * np.sqrt(
                self.pipe_length / (9.81 * config.area)
            )

        # 涌浪周期
        period = 2 * np.pi * np.sqrt(
            self.pipe_length * config.area / (9.81 * self.pipe_area)
        )

        # 阻尼时间
        damping_time = 2 * config.area * self.head / (
            self.pipe_friction * self.pipe_length * self.rated_flow
        )

        return {
            "thoma_coefficient": sigma,
            "is_stable": is_stable,
            "surge_amplitude": surge_amplitude,
            "surge_period": period,
            "damping_time": damping_time,
            "max_rise_percent": surge_amplitude / self.head * 100,
            "safety_check": surge_amplitude / self.head < self.max_surge_rise,
        }

    def optimize_dimensions(self, tank_type: str = "throttled",
                            method: OptimizationMethod = OptimizationMethod.GENETIC_ALGORITHM,
                            n_iterations: int = 100) -> SurgeTankConfig:
        """
        优化调压室尺寸

        Args:
            tank_type: 调压室类型
            method: 优化方法
            n_iterations: 迭代次数

        Returns:
            最优配置
        """
        best_config = None
        best_score = float('inf')

        # 参数范围
        diameter_range = (8, 20)       # m
        height_range = (30, 100)       # m

        if tank_type == "throttled":
            orifice_range = (1, 5)     # m

        for _ in range(n_iterations):
            # 随机生成参数
            diameter = np.random.uniform(*diameter_range)
            height = np.random.uniform(*height_range)
            area = np.pi * (diameter / 2) ** 2

            config = SurgeTankConfig(
                tank_type=tank_type,
                diameter=diameter,
                height=height,
                area=area,
            )

            if tank_type == "throttled":
                config.orifice_diameter = np.random.uniform(*orifice_range)

            # 评估
            result = self.analyze_surge(config)

            # 目标函数：最小化成本，满足约束
            if result["is_stable"] and result["safety_check"]:
                # 成本函数（简化）
                cost = area * height * 1000  # 体积×单位成本

                if cost < best_score:
                    best_score = cost
                    best_config = config

        return best_config or SurgeTankConfig()

    def design_multi_surge_tank_system(self, n_tanks: int = 2) -> List[SurgeTankConfig]:
        """
        设计多调压室系统

        Args:
            n_tanks: 调压室数量

        Returns:
            调压室配置列表
        """
        tanks = []

        # 分配位置
        positions = np.linspace(10000, self.pipe_length - 5000, n_tanks)

        for i, pos in enumerate(positions):
            # 根据位置调整尺寸
            size_factor = 1.0 - 0.3 * i / n_tanks  # 靠近水轮机的较大

            config = SurgeTankConfig(
                tank_type="throttled" if i < n_tanks - 1 else "differential",
                diameter=12 * size_factor,
                height=60,
                area=np.pi * (12 * size_factor / 2) ** 2,
                distance_from_turbine=self.pipe_length - pos,
            )

            tanks.append(config)

        return tanks


class MultiSchemeComparator:
    """
    多方案比较器

    功能：
    - 方案生成
    - 性能评估
    - 综合比选
    - 敏感性分析
    """

    def __init__(self):
        self.schemes: List[DesignScheme] = []
        self.evaluation_weights = {
            "safety": 0.3,
            "economy": 0.3,
            "reliability": 0.2,
            "constructability": 0.2,
        }

    def add_scheme(self, scheme: DesignScheme):
        """添加方案"""
        self.schemes.append(scheme)

    def generate_scheme_variants(self, base_scheme: DesignScheme,
                                  n_variants: int = 10) -> List[DesignScheme]:
        """
        生成方案变体

        Args:
            base_scheme: 基础方案
            n_variants: 变体数量

        Returns:
            方案列表
        """
        variants = []

        for i in range(n_variants):
            variant = DesignScheme(
                scheme_id=f"{base_scheme.scheme_id}_v{i+1}",
                name=f"{base_scheme.name} - 变体{i+1}",
                description=f"基于{base_scheme.name}的参数变体",
            )

            # 扰动参数
            for param, value in base_scheme.parameters.items():
                perturbation = np.random.uniform(0.8, 1.2)
                variant.parameters[param] = value * perturbation

            variants.append(variant)

        return variants

    def evaluate_scheme(self, scheme: DesignScheme,
                        water_hammer_analyzer: WaterHammerAnalyzer,
                        surge_optimizer: SurgeTankOptimizer) -> Dict[str, float]:
        """
        评估方案

        Args:
            scheme: 设计方案
            water_hammer_analyzer: 水锤分析器
            surge_optimizer: 调压室优化器

        Returns:
            评估指标
        """
        metrics = {}

        # 水锤分析
        wh_result = water_hammer_analyzer.analyze_valve_closure(
            closure_time=scheme.parameters.get("closure_time", 30),
        )
        metrics["max_pressure_rise"] = wh_result.pressure_rise
        metrics["settling_time"] = wh_result.settling_time

        # 调压室分析
        surge_config = SurgeTankConfig(
            diameter=scheme.parameters.get("surge_diameter", 12),
            height=scheme.parameters.get("surge_height", 60),
            area=np.pi * (scheme.parameters.get("surge_diameter", 12) / 2) ** 2,
        )
        surge_result = surge_optimizer.analyze_surge(surge_config)
        metrics["thoma_coefficient"] = surge_result["thoma_coefficient"]
        metrics["surge_amplitude"] = surge_result["surge_amplitude"]

        # 安全评分
        safety_score = 100
        if wh_result.pressure_rise > 30:  # 超过30%
            safety_score -= (wh_result.pressure_rise - 30) * 2
        if not surge_result["is_stable"]:
            safety_score -= 30
        metrics["safety_score"] = max(0, safety_score)

        # 经济评分
        cost = (surge_config.area * surge_config.height * 1000 +
                scheme.parameters.get("closure_time", 30) * 10000)
        metrics["cost"] = cost
        metrics["economy_score"] = max(0, 100 - cost / 1e6)

        # 可靠性评分
        reliability_score = 100
        if surge_result["thoma_coefficient"] < 1.2:
            reliability_score -= (1.2 - surge_result["thoma_coefficient"]) * 50
        metrics["reliability_score"] = max(0, reliability_score)

        # 施工性评分（简化）
        constructability_score = 100
        if surge_config.diameter > 15:
            constructability_score -= (surge_config.diameter - 15) * 5
        if surge_config.height > 80:
            constructability_score -= (surge_config.height - 80) * 2
        metrics["constructability_score"] = max(0, constructability_score)

        scheme.metrics = metrics
        return metrics

    def compare_schemes(self) -> List[DesignScheme]:
        """
        比较所有方案

        Returns:
            排序后的方案列表
        """
        for scheme in self.schemes:
            # 计算综合评分
            total_score = 0
            for criterion, weight in self.evaluation_weights.items():
                score_key = f"{criterion}_score"
                if score_key in scheme.metrics:
                    total_score += scheme.metrics[score_key] * weight

            scheme.score = total_score

        # 排序
        sorted_schemes = sorted(self.schemes, key=lambda s: s.score, reverse=True)

        for i, scheme in enumerate(sorted_schemes):
            scheme.ranking = i + 1

        return sorted_schemes

    def sensitivity_analysis(self, scheme: DesignScheme,
                              parameter: str,
                              range_percent: float = 20,
                              n_points: int = 10) -> Dict[str, List[float]]:
        """
        敏感性分析

        Args:
            scheme: 基础方案
            parameter: 分析参数
            range_percent: 变化范围 %
            n_points: 分析点数

        Returns:
            敏感性数据
        """
        if parameter not in scheme.parameters:
            return {}

        base_value = scheme.parameters[parameter]
        values = np.linspace(
            base_value * (1 - range_percent / 100),
            base_value * (1 + range_percent / 100),
            n_points
        )

        results = {
            "parameter_values": values.tolist(),
            "scores": [],
            "safety_scores": [],
            "economy_scores": [],
        }

        wh_analyzer = WaterHammerAnalyzer()
        surge_opt = SurgeTankOptimizer()

        for val in values:
            # 创建变体
            variant = DesignScheme(
                scheme_id=f"{scheme.scheme_id}_sens",
                name=f"敏感性分析 - {parameter}={val:.2f}",
                description="敏感性分析变体",
                parameters=scheme.parameters.copy(),
            )
            variant.parameters[parameter] = val

            # 评估
            metrics = self.evaluate_scheme(variant, wh_analyzer, surge_opt)

            results["scores"].append(variant.score)
            results["safety_scores"].append(metrics.get("safety_score", 0))
            results["economy_scores"].append(metrics.get("economy_score", 0))

        return results

    def generate_report(self) -> Dict[str, Any]:
        """生成比选报告"""
        sorted_schemes = self.compare_schemes()

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_schemes": len(self.schemes),
            "evaluation_weights": self.evaluation_weights,
            "rankings": [],
            "recommended_scheme": None,
        }

        for scheme in sorted_schemes:
            report["rankings"].append({
                "rank": scheme.ranking,
                "scheme_id": scheme.scheme_id,
                "name": scheme.name,
                "score": scheme.score,
                "metrics": scheme.metrics,
                "parameters": scheme.parameters,
            })

        if sorted_schemes:
            report["recommended_scheme"] = sorted_schemes[0].scheme_id

        return report


class DesignVerificationWindTunnel:
    """
    设计验证风洞

    功能：
    - 综合设计验证
    - 多工况测试
    - 极限推演
    - 优化建议

    实现"设计即验证"范式
    """

    def __init__(self):
        self.water_hammer = WaterHammerAnalyzer()
        self.surge_optimizer = SurgeTankOptimizer()
        self.comparator = MultiSchemeComparator()

        # 验证场景
        self.verification_scenarios = [
            {"name": "正常启动", "type": "startup", "load_rate": 0.1},
            {"name": "正常停机", "type": "shutdown", "closure_time": 60},
            {"name": "紧急停机", "type": "emergency_stop", "closure_time": 10},
            {"name": "甩50%负荷", "type": "load_rejection", "rejection": 50},
            {"name": "甩100%负荷", "type": "load_rejection", "rejection": 100},
            {"name": "电网故障", "type": "grid_fault", "duration": 0.5},
            {"name": "满负荷突增", "type": "load_acceptance", "load": 100},
        ]

        # 极限工况
        self.extreme_scenarios = [
            {"name": "两机同时甩负荷", "machines": 2, "rejection": 100},
            {"name": "上游水库泄洪叠加", "flood": True, "head_change": 50},
            {"name": "地震工况", "seismic": True, "intensity": 8},
            {"name": "冰崩堵塞", "ice_jam": True, "blockage": 0.3},
        ]

        # 验证结果
        self.verification_results: List[Dict[str, Any]] = []

    def verify_design(self, scheme: DesignScheme) -> Dict[str, Any]:
        """
        验证设计方案

        Args:
            scheme: 设计方案

        Returns:
            验证结果
        """
        results = {
            "scheme_id": scheme.scheme_id,
            "timestamp": datetime.now().isoformat(),
            "scenarios": [],
            "extreme_tests": [],
            "overall_pass": True,
            "issues": [],
            "recommendations": [],
        }

        # 正常工况验证
        for scenario in self.verification_scenarios:
            scenario_result = self._verify_scenario(scheme, scenario)
            results["scenarios"].append(scenario_result)

            if not scenario_result["passed"]:
                results["overall_pass"] = False
                results["issues"].append(f"{scenario['name']}: {scenario_result['issue']}")

        # 极限工况测试
        for extreme in self.extreme_scenarios:
            extreme_result = self._verify_extreme(scheme, extreme)
            results["extreme_tests"].append(extreme_result)

            if extreme_result["severity"] == "critical":
                results["issues"].append(f"极限工况 {extreme['name']}: {extreme_result['description']}")

        # 生成建议
        results["recommendations"] = self._generate_recommendations(results)

        self.verification_results.append(results)
        return results

    def _verify_scenario(self, scheme: DesignScheme, scenario: Dict) -> Dict[str, Any]:
        """验证单个场景"""
        result = {
            "scenario": scenario["name"],
            "type": scenario["type"],
            "passed": True,
            "metrics": {},
            "issue": None,
        }

        if scenario["type"] == "shutdown" or scenario["type"] == "emergency_stop":
            # 停机水锤分析
            wh = self.water_hammer.analyze_valve_closure(
                closure_time=scenario.get("closure_time", 30)
            )
            result["metrics"]["max_pressure_rise"] = wh.pressure_rise
            result["metrics"]["settling_time"] = wh.settling_time

            if wh.pressure_rise > 30:
                result["passed"] = False
                result["issue"] = f"压力升高{wh.pressure_rise:.1f}%超过限值30%"

        elif scenario["type"] == "load_rejection":
            # 甩负荷分析
            rejection = scenario.get("rejection", 100)
            wh = self.water_hammer.analyze_load_rejection(rejection)
            result["metrics"]["max_pressure_rise"] = wh.pressure_rise

            # 涌浪分析
            surge_config = SurgeTankConfig(
                diameter=scheme.parameters.get("surge_diameter", 12),
                area=np.pi * (scheme.parameters.get("surge_diameter", 12) / 2) ** 2,
            )
            surge = self.surge_optimizer.analyze_surge(surge_config)
            result["metrics"]["surge_amplitude"] = surge["surge_amplitude"]

            if not surge["is_stable"]:
                result["passed"] = False
                result["issue"] = "涌浪不稳定"

        elif scenario["type"] == "load_acceptance":
            # 增负荷分析
            surge_config = SurgeTankConfig(
                diameter=scheme.parameters.get("surge_diameter", 12),
                area=np.pi * (scheme.parameters.get("surge_diameter", 12) / 2) ** 2,
            )
            surge = self.surge_optimizer.analyze_surge(surge_config, "load_acceptance")
            result["metrics"]["surge_drop"] = surge["surge_amplitude"]

            if surge["surge_amplitude"] / self.surge_optimizer.head > 0.2:
                result["passed"] = False
                result["issue"] = "涌浪下降过大"

        return result

    def _verify_extreme(self, scheme: DesignScheme, extreme: Dict) -> Dict[str, Any]:
        """验证极限工况"""
        result = {
            "scenario": extreme["name"],
            "severity": "normal",
            "description": "",
            "metrics": {},
        }

        if extreme.get("machines", 1) > 1:
            # 多机同时甩负荷
            wh = self.water_hammer.analyze_load_rejection(100)
            amplified_pressure = wh.max_pressure * (1 + 0.3 * (extreme["machines"] - 1))
            result["metrics"]["amplified_pressure"] = amplified_pressure

            if amplified_pressure > wh.max_pressure * 1.5:
                result["severity"] = "critical"
                result["description"] = "多机叠加效应导致压力超限"

        elif extreme.get("seismic"):
            # 地震工况
            intensity = extreme.get("intensity", 7)
            # 简化：地震可能导致控制失灵，考虑快速停机
            wh = self.water_hammer.analyze_valve_closure(5)  # 5秒紧急停机
            result["metrics"]["emergency_pressure"] = wh.max_pressure

            if intensity >= 8 and wh.pressure_rise > 40:
                result["severity"] = "warning"
                result["description"] = "强震下紧急停机压力较高"

        elif extreme.get("ice_jam"):
            # 冰崩堵塞
            blockage = extreme.get("blockage", 0.3)
            result["metrics"]["flow_reduction"] = blockage * 100
            result["severity"] = "warning"
            result["description"] = f"冰崩可能导致{blockage*100:.0f}%流量损失"

        return result

    def _generate_recommendations(self, results: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 分析问题
        for issue in results["issues"]:
            if "压力" in issue:
                recommendations.append("建议延长阀门关闭时间或优化关闭规律")
            if "涌浪" in issue:
                recommendations.append("建议增大调压室面积或采用阻抗式调压室")

        # 极限工况建议
        for extreme in results["extreme_tests"]:
            if extreme["severity"] == "critical":
                recommendations.append(f"极限工况{extreme['scenario']}需要专项研究")

        if not recommendations:
            recommendations.append("设计方案满足各项验证要求")

        return recommendations

    def run_full_verification(self, schemes: List[DesignScheme]) -> Dict[str, Any]:
        """
        运行完整验证

        Args:
            schemes: 方案列表

        Returns:
            综合验证报告
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_schemes": len(schemes),
            "verification_results": [],
            "comparison": {},
            "final_recommendation": None,
        }

        # 验证每个方案
        for scheme in schemes:
            # 评估性能
            self.comparator.add_scheme(scheme)
            self.comparator.evaluate_scheme(scheme, self.water_hammer, self.surge_optimizer)

            # 验证设计
            verification = self.verify_design(scheme)
            report["verification_results"].append(verification)

        # 比选
        sorted_schemes = self.comparator.compare_schemes()
        report["comparison"] = self.comparator.generate_report()

        # 最终建议
        passed_schemes = [s for s in sorted_schemes
                          if any(v["overall_pass"] for v in report["verification_results"]
                                 if v["scheme_id"] == s.scheme_id)]

        if passed_schemes:
            report["final_recommendation"] = {
                "scheme_id": passed_schemes[0].scheme_id,
                "name": passed_schemes[0].name,
                "score": passed_schemes[0].score,
                "reason": "综合评分最高且通过所有验证",
            }

        return report

    def export_report(self, filepath: str):
        """导出验证报告"""
        import json

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.verification_results, f, ensure_ascii=False, indent=2, default=str)
