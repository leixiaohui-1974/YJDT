"""
水力系统仿真模块
Hydraulic System Simulation Module

实现MOC (Method of Characteristics) 水锤计算方法
支持管道、调压室等水力元件的瞬变仿真
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class BoundaryType(Enum):
    """边界类型枚举"""
    RESERVOIR = "reservoir"           # 水库
    VALVE = "valve"                   # 阀门
    TURBINE = "turbine"               # 水轮机
    SURGE_TANK = "surge_tank"         # 调压室
    JUNCTION = "junction"             # 管道连接点
    DEAD_END = "dead_end"             # 死端


@dataclass
class HydraulicState:
    """水力状态变量"""
    head: np.ndarray          # 水头分布 (m)
    velocity: np.ndarray      # 流速分布 (m/s)
    flow: np.ndarray          # 流量分布 (m³/s)
    pressure: np.ndarray      # 压力分布 (Pa)
    time: float = 0.0         # 当前时间 (s)


@dataclass
class PipelineParams:
    """管道参数"""
    length: float             # 管道长度 (m)
    diameter: float           # 管道直径 (m)
    wave_speed: float         # 波速 (m/s)
    friction_factor: float    # 达西摩擦系数
    roughness: float = 0.0    # 粗糙度 (m)
    wall_thickness: float = 0.05  # 管壁厚度 (m)
    elastic_modulus: float = 2.1e11  # 弹性模量 (Pa)

    @property
    def area(self) -> float:
        """管道横截面积"""
        return np.pi * self.diameter**2 / 4

    @property
    def hydraulic_radius(self) -> float:
        """水力半径"""
        return self.diameter / 4


class Pipeline:
    """
    管道类 - MOC水锤计算核心

    使用特征线法(Method of Characteristics)进行水锤瞬变计算
    """

    def __init__(
        self,
        params: PipelineParams,
        num_segments: int = 100,
        gravity: float = 9.81
    ):
        self.params = params
        self.num_segments = num_segments
        self.gravity = gravity

        # 计算空间步长和时间步长
        self.dx = params.length / num_segments
        self.dt = self.dx / params.wave_speed  # 满足Courant条件

        # 初始化网格
        self.x = np.linspace(0, params.length, num_segments + 1)
        self.num_nodes = num_segments + 1

        # 状态变量数组
        self.H = np.zeros(self.num_nodes)  # 水头
        self.V = np.zeros(self.num_nodes)  # 流速
        self.Q = np.zeros(self.num_nodes)  # 流量

        # 历史数据存储
        self.history: List[HydraulicState] = []

        # MOC特征线系数
        self._calculate_moc_coefficients()

    def _calculate_moc_coefficients(self):
        """计算MOC特征线方程系数"""
        a = self.params.wave_speed
        g = self.gravity
        D = self.params.diameter
        f = self.params.friction_factor
        A = self.params.area

        # 特征线系数
        self.B = a / (g * A)  # 阻抗
        self.R = f * self.dx / (2 * g * D * A**2)  # 阻力系数

    def initialize_steady_state(
        self,
        upstream_head: float,
        downstream_head: float,
        flow: float
    ):
        """
        初始化稳态条件

        Args:
            upstream_head: 上游水头 (m)
            downstream_head: 下游水头 (m)
            flow: 稳态流量 (m³/s)
        """
        # 线性插值初始水头分布
        self.H = np.linspace(upstream_head, downstream_head, self.num_nodes)

        # 稳态流量和流速
        self.Q = np.full(self.num_nodes, flow)
        self.V = self.Q / self.params.area

        # 计算水头损失
        self._apply_friction_losses()

        self.current_time = 0.0
        self._save_state()

    def _apply_friction_losses(self):
        """应用沿程水头损失"""
        f = self.params.friction_factor
        D = self.params.diameter
        g = self.gravity

        for i in range(1, self.num_nodes):
            v_avg = (self.V[i] + self.V[i-1]) / 2
            h_loss = f * self.dx / D * v_avg * abs(v_avg) / (2 * g)
            self.H[i] = self.H[i-1] - h_loss

    def step(
        self,
        upstream_bc: Callable[[float], float],
        downstream_bc: Callable[[float, float, float], Tuple[float, float]]
    ):
        """
        执行一个时间步的MOC计算

        Args:
            upstream_bc: 上游边界条件函数 f(t) -> H
            downstream_bc: 下游边界条件函数 f(t, Cp, Cm) -> (H, Q)
        """
        H_new = np.zeros(self.num_nodes)
        Q_new = np.zeros(self.num_nodes)

        # 内部节点计算 - 使用MOC特征线方程
        for i in range(1, self.num_nodes - 1):
            # C+特征线（从上游传来）
            Cp = self.H[i-1] + self.B * self.Q[i-1] - self.R * self.Q[i-1] * abs(self.Q[i-1])

            # C-特征线（从下游传来）
            Cm = self.H[i+1] - self.B * self.Q[i+1] + self.R * self.Q[i+1] * abs(self.Q[i+1])

            # 求解交点
            H_new[i] = (Cp + Cm) / 2
            Q_new[i] = (Cp - Cm) / (2 * self.B)

        # 上游边界
        H_new[0] = upstream_bc(self.current_time + self.dt)
        # 从C-特征线求Q
        Cm_0 = self.H[1] - self.B * self.Q[1] + self.R * self.Q[1] * abs(self.Q[1])
        Q_new[0] = (H_new[0] - Cm_0) / self.B

        # 下游边界
        Cp_n = self.H[-2] + self.B * self.Q[-2] - self.R * self.Q[-2] * abs(self.Q[-2])
        H_new[-1], Q_new[-1] = downstream_bc(self.current_time + self.dt, Cp_n, self.B)

        # 更新状态
        self.H = H_new
        self.Q = Q_new
        self.V = self.Q / self.params.area
        self.current_time += self.dt

        self._save_state()

    def _save_state(self):
        """保存当前状态"""
        state = HydraulicState(
            head=self.H.copy(),
            velocity=self.V.copy(),
            flow=self.Q.copy(),
            pressure=self.H * self.gravity * 1000,  # 简化压力计算
            time=self.current_time
        )
        self.history.append(state)

    def get_water_hammer_pressure(self, node_index: int = -1) -> np.ndarray:
        """获取指定节点的水锤压力历史"""
        return np.array([state.pressure[node_index] for state in self.history])

    def get_max_pressure(self) -> float:
        """获取最大水锤压力"""
        return max(np.max(state.pressure) for state in self.history)

    def get_min_pressure(self) -> float:
        """获取最小水锤压力（检查负压）"""
        return min(np.min(state.pressure) for state in self.history)


@dataclass
class SurgeTankParams:
    """调压室参数"""
    type: str = "simple"          # simple, impedance, differential
    diameter: float = 45.0        # 主井直径 (m)
    height: float = 120.0         # 调压室高度 (m)
    initial_level: float = 60.0   # 初始水位 (m)
    orifice_diameter: float = 6.5  # 阻抗孔口直径 (m)
    riser_diameter: float = 0.0   # 升管直径 (m) - 差动式
    loss_coefficient: float = 0.5  # 局部损失系数


class SurgeTank:
    """
    调压室类

    支持简单调压室、阻抗式调压室、差动式调压室
    """

    def __init__(
        self,
        params: SurgeTankParams,
        gravity: float = 9.81
    ):
        self.params = params
        self.gravity = gravity

        # 状态变量
        self.level = params.initial_level
        self.inflow = 0.0
        self.velocity = 0.0

        # 横截面积
        self.main_area = np.pi * params.diameter**2 / 4
        self.orifice_area = np.pi * params.orifice_diameter**2 / 4

        # 历史记录
        self.level_history: List[float] = [self.level]
        self.inflow_history: List[float] = [0.0]
        self.time_history: List[float] = [0.0]

    def update(
        self,
        pipeline_flow: float,
        turbine_flow: float,
        dt: float,
        current_time: float
    ) -> Tuple[float, float]:
        """
        更新调压室状态

        Args:
            pipeline_flow: 管道来流量 (m³/s)
            turbine_flow: 水轮机流量 (m³/s)
            dt: 时间步长 (s)
            current_time: 当前时间 (s)

        Returns:
            (调压室水位, 阻抗损失水头)
        """
        # 计算流入调压室的流量
        self.inflow = pipeline_flow - turbine_flow

        # 阻抗式调压室的阻力水头
        if self.params.type == "impedance" and self.orifice_area > 0:
            v_orifice = self.inflow / self.orifice_area
            head_loss = self.params.loss_coefficient * v_orifice * abs(v_orifice) / (2 * self.gravity)
        else:
            head_loss = 0.0

        # 水位变化
        d_level = self.inflow * dt / self.main_area
        self.level += d_level

        # 检查边界条件
        self.level = np.clip(self.level, 0, self.params.height)

        # 记录历史
        self.level_history.append(self.level)
        self.inflow_history.append(self.inflow)
        self.time_history.append(current_time)

        return self.level, head_loss

    def get_head(self, base_elevation: float = 0.0) -> float:
        """获取调压室提供的水头"""
        return base_elevation + self.level


class HydraulicSystem:
    """
    水力系统总成类

    集成管道、调压室等组件进行完整的水力瞬变仿真
    """

    def __init__(
        self,
        pipelines: List[Pipeline],
        surge_tanks: Optional[List[SurgeTank]] = None,
        upstream_reservoir_level: float = 500.0,
        gravity: float = 9.81
    ):
        self.pipelines = pipelines
        self.surge_tanks = surge_tanks or []
        self.upstream_level = upstream_reservoir_level
        self.gravity = gravity

        self.current_time = 0.0
        self.dt = min(p.dt for p in pipelines)  # 使用最小时间步长

        # 系统状态
        self.turbine_flow = 0.0
        self.turbine_head = 0.0

    def initialize(self, initial_flow: float, downstream_head: float):
        """初始化系统稳态"""
        for pipeline in self.pipelines:
            pipeline.initialize_steady_state(
                self.upstream_level,
                downstream_head,
                initial_flow
            )

        self.turbine_flow = initial_flow
        self.turbine_head = downstream_head

    def step(
        self,
        turbine_bc: Callable[[float, float, float], Tuple[float, float]]
    ):
        """
        执行一个时间步的系统仿真

        Args:
            turbine_bc: 水轮机边界条件函数
        """
        # 上游水库边界（恒定水头）
        def upstream_bc(t):
            return self.upstream_level

        # 考虑调压室的下游边界
        if self.surge_tanks:
            surge_tank = self.surge_tanks[0]  # 简化：只考虑一个调压室

            def downstream_bc(t, Cp, B):
                # 与水轮机边界耦合
                H, Q = turbine_bc(t, Cp, B)
                # 更新调压室
                pipeline_Q = self.pipelines[0].Q[-1]
                surge_tank.update(pipeline_Q, Q, self.dt, t)
                return H, Q
        else:
            downstream_bc = turbine_bc

        # 更新管道
        for pipeline in self.pipelines:
            pipeline.step(upstream_bc, downstream_bc)

        self.current_time += self.dt

    def simulate(
        self,
        total_time: float,
        turbine_bc: Callable[[float, float, float], Tuple[float, float]]
    ) -> Dict:
        """
        运行完整的瞬变仿真

        Args:
            total_time: 仿真总时间 (s)
            turbine_bc: 水轮机边界条件函数

        Returns:
            仿真结果字典
        """
        num_steps = int(total_time / self.dt)

        for _ in range(num_steps):
            self.step(turbine_bc)

        return self.get_results()

    def get_results(self) -> Dict:
        """获取仿真结果"""
        results = {
            "time": np.array([s.time for s in self.pipelines[0].history]),
            "pipelines": []
        }

        for i, pipeline in enumerate(self.pipelines):
            results["pipelines"].append({
                "head": np.array([s.head for s in pipeline.history]),
                "flow": np.array([s.flow for s in pipeline.history]),
                "pressure": np.array([s.pressure for s in pipeline.history]),
                "max_pressure": pipeline.get_max_pressure(),
                "min_pressure": pipeline.get_min_pressure(),
            })

        if self.surge_tanks:
            results["surge_tanks"] = []
            for surge_tank in self.surge_tanks:
                results["surge_tanks"].append({
                    "level": np.array(surge_tank.level_history),
                    "inflow": np.array(surge_tank.inflow_history),
                })

        return results


def calculate_water_inertia_time(
    length: float,
    velocity: float,
    head: float,
    gravity: float = 9.81
) -> float:
    """
    计算水流惯性时间常数 Tw

    Args:
        length: 管道长度 (m)
        velocity: 流速 (m/s)
        head: 水头 (m)
        gravity: 重力加速度 (m/s²)

    Returns:
        水流惯性时间常数 (s)
    """
    return length * velocity / (gravity * head)


def calculate_wave_speed(
    bulk_modulus: float,
    water_density: float,
    pipe_diameter: float,
    wall_thickness: float,
    elastic_modulus: float,
    constraint_factor: float = 1.0
) -> float:
    """
    计算压力波速

    Args:
        bulk_modulus: 水的体积弹性模量 (Pa)
        water_density: 水密度 (kg/m³)
        pipe_diameter: 管道直径 (m)
        wall_thickness: 管壁厚度 (m)
        elastic_modulus: 管材弹性模量 (Pa)
        constraint_factor: 约束系数

    Returns:
        压力波速 (m/s)
    """
    K = bulk_modulus
    rho = water_density
    D = pipe_diameter
    e = wall_thickness
    E = elastic_modulus
    c = constraint_factor

    # 经典波速公式
    a = np.sqrt(K / rho / (1 + K * D * c / (E * e)))
    return a
