# -*- coding: utf-8 -*-
"""
高级水力仿真 - Advanced Hydraulic Simulation

功能：
- 非线性管道特性（空气夹杂、温度效应、管道伸缩）
- 多支管并联流量分配
- 设备老化劣化模型
- 高精度MOC算法
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


class PipelineType(Enum):
    """管道类型"""
    STEEL = "steel"
    CONCRETE = "concrete"
    CAST_IRON = "cast_iron"
    PVC = "pvc"
    HDPE = "hdpe"


class FluidType(Enum):
    """流体类型"""
    WATER = "water"
    WATER_AIR_MIX = "water_air_mix"
    SEDIMENT_WATER = "sediment_water"


@dataclass
class FluidProperties:
    """流体属性"""
    density: float = 1000.0           # kg/m³
    bulk_modulus: float = 2.2e9       # Pa
    viscosity: float = 1.0e-3         # Pa·s
    temperature: float = 20.0         # °C
    air_content: float = 0.0          # 体积分数 (0-1)
    sediment_content: float = 0.0     # kg/m³


@dataclass
class PipeProperties:
    """管道属性"""
    length: float                     # m
    diameter: float                   # m
    wall_thickness: float             # m
    roughness: float = 0.001          # m
    material: PipelineType = PipelineType.STEEL
    young_modulus: float = 210e9      # Pa
    poisson_ratio: float = 0.3
    thermal_expansion: float = 12e-6  # 1/°C


@dataclass
class AgingModel:
    """老化模型"""
    installation_date: datetime
    design_life_years: float = 50
    roughness_growth_rate: float = 0.01   # mm/年
    thickness_reduction_rate: float = 0.1  # mm/年
    fatigue_cycles: int = 0
    fatigue_limit: int = 1e7
    condition_factor: float = 1.0         # 0-1, 1为全新


class NonlinearPipeline:
    """
    非线性管道模型

    考虑：
    - 空气夹杂对波速的影响
    - 温度对流体性质的影响
    - 管道弹性变形
    - 沉积物对摩擦的影响
    - 老化劣化
    """

    def __init__(self, properties: PipeProperties,
                 n_nodes: int = 100):
        self.props = properties
        self.n_nodes = n_nodes
        self.dx = properties.length / (n_nodes - 1)

        # 状态变量
        self.head = np.zeros(n_nodes)           # 压力水头 (m)
        self.flow = np.zeros(n_nodes)           # 流量 (m³/s)
        self.velocity = np.zeros(n_nodes)       # 流速 (m/s)

        # 流体属性
        self.fluid = FluidProperties()

        # 老化模型
        self.aging = AgingModel(installation_date=datetime.now())

        # 计算截面积
        self.area = np.pi * (properties.diameter / 2) ** 2

        # 波速（初始值）
        self.wave_speed = self._calculate_wave_speed()

    def _calculate_wave_speed(self) -> float:
        """
        计算压力波速

        考虑：
        - 流体压缩性
        - 管壁弹性
        - 空气含量
        """
        K = self.fluid.bulk_modulus  # 流体体积模量
        rho = self.fluid.density     # 流体密度
        E = self.props.young_modulus  # 管壁弹性模量
        D = self.props.diameter
        e = self.props.wall_thickness
        c1 = self.props.poisson_ratio * 2 if self.props.material != PipelineType.CONCRETE else 1

        # 基础波速（不考虑空气）
        a_base = np.sqrt(K / rho / (1 + K * D * c1 / (E * e)))

        # 空气含量影响
        alpha = self.fluid.air_content
        if alpha > 0:
            # 混合流体体积模量
            K_air = 1.4e5  # 空气绝热体积模量
            K_mix = 1 / ((1 - alpha) / K + alpha / K_air)
            rho_mix = rho * (1 - alpha) + 1.2 * alpha

            a = np.sqrt(K_mix / rho_mix / (1 + K_mix * D * c1 / (E * e)))
        else:
            a = a_base

        return a

    def _calculate_friction_factor(self, velocity: float) -> float:
        """
        计算摩擦系数（考虑老化）

        使用Swamee-Jain公式
        """
        # 考虑老化的粗糙度
        age_years = (datetime.now() - self.aging.installation_date).days / 365.25
        roughness = self.props.roughness + self.aging.roughness_growth_rate * age_years / 1000

        D = self.props.diameter
        nu = self.fluid.viscosity / self.fluid.density

        if abs(velocity) < 1e-6:
            return 0.02  # 默认值

        Re = abs(velocity) * D / nu

        if Re < 2300:
            # 层流
            f = 64 / Re
        else:
            # 湍流 - Swamee-Jain公式
            f = 0.25 / (np.log10(roughness / (3.7 * D) + 5.74 / Re ** 0.9)) ** 2

        # 沉积物影响
        if self.fluid.sediment_content > 0:
            f *= (1 + 0.1 * self.fluid.sediment_content / 100)

        return f

    def _calculate_friction_loss(self, velocity: float, dx: float) -> float:
        """计算摩擦损失"""
        f = self._calculate_friction_factor(velocity)
        D = self.props.diameter
        g = 9.81

        return f * dx * velocity * abs(velocity) / (2 * g * D)

    def update_fluid_properties(self, temperature: float = None,
                                air_content: float = None,
                                sediment: float = None):
        """更新流体属性"""
        if temperature is not None:
            self.fluid.temperature = temperature
            # 温度影响密度和粘度
            T = temperature
            self.fluid.density = 1000 * (1 - 0.0002 * (T - 4) ** 2)
            self.fluid.viscosity = 0.00179 / (1 + 0.0337 * T + 0.000221 * T ** 2)

        if air_content is not None:
            self.fluid.air_content = np.clip(air_content, 0, 0.1)

        if sediment is not None:
            self.fluid.sediment_content = sediment

        # 重新计算波速
        self.wave_speed = self._calculate_wave_speed()

    def step_moc(self, dt: float, h_upstream: float, h_downstream: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        MOC方法求解（特征线法）

        Args:
            dt: 时间步长
            h_upstream: 上游边界水头
            h_downstream: 下游边界水头

        Returns:
            (水头数组, 流量数组)
        """
        a = self.wave_speed
        g = 9.81
        A = self.area

        # 检查Courant条件
        courant = a * dt / self.dx
        if courant > 1:
            raise ValueError(f"Courant数 {courant:.2f} > 1，请减小时间步长")

        # 复制当前状态
        H = self.head.copy()
        Q = self.flow.copy()

        H_new = np.zeros_like(H)
        Q_new = np.zeros_like(Q)

        # 边界条件
        H_new[0] = h_upstream
        H_new[-1] = h_downstream

        # 内部节点
        for i in range(1, self.n_nodes - 1):
            # 插值计算特征线上的值
            # C+特征线
            x_plus = i * self.dx - a * dt
            j_plus = int(x_plus / self.dx)
            j_plus = max(0, min(j_plus, self.n_nodes - 2))
            frac = (x_plus - j_plus * self.dx) / self.dx

            H_p = H[j_plus] + frac * (H[j_plus + 1] - H[j_plus])
            Q_p = Q[j_plus] + frac * (Q[j_plus + 1] - Q[j_plus])
            V_p = Q_p / A

            # C-特征线
            x_minus = i * self.dx + a * dt
            j_minus = int(x_minus / self.dx)
            j_minus = max(0, min(j_minus, self.n_nodes - 2))
            frac = (x_minus - j_minus * self.dx) / self.dx

            H_m = H[j_minus] + frac * (H[j_minus + 1] - H[j_minus])
            Q_m = Q[j_minus] + frac * (Q[j_minus + 1] - Q[j_minus])
            V_m = Q_m / A

            # 摩擦项
            R_p = self._calculate_friction_loss(V_p, a * dt)
            R_m = self._calculate_friction_loss(V_m, a * dt)

            # 特征线方程
            B = a / (g * A)
            Cp = H_p + B * Q_p - R_p
            Cm = H_m - B * Q_m - R_m

            # 求解
            H_new[i] = (Cp + Cm) / 2
            Q_new[i] = (Cp - Cm) / (2 * B)

        # 边界流量
        B = a / (g * A)
        V_0 = Q[0] / A
        R_0 = self._calculate_friction_loss(V_0, a * dt)
        Cm_0 = H[1] - B * Q[1] - R_0
        Q_new[0] = (H_new[0] - Cm_0) / B

        V_n = Q[-1] / A
        R_n = self._calculate_friction_loss(V_n, a * dt)
        Cp_n = H[-2] + B * Q[-2] - R_n
        Q_new[-1] = (Cp_n - H_new[-1]) / B

        # 更新状态
        self.head = H_new
        self.flow = Q_new
        self.velocity = Q_new / A

        return H_new, Q_new

    def get_aging_factor(self) -> float:
        """获取老化因子"""
        age_years = (datetime.now() - self.aging.installation_date).days / 365.25

        # 时间老化
        time_factor = 1 - 0.3 * (age_years / self.aging.design_life_years)

        # 疲劳老化
        fatigue_factor = 1 - 0.2 * (self.aging.fatigue_cycles / self.aging.fatigue_limit)

        return max(0.5, min(1.0, time_factor * fatigue_factor * self.aging.condition_factor))

    def record_fatigue_cycle(self, pressure_amplitude: float):
        """记录疲劳循环"""
        if pressure_amplitude > 0.1 * self.props.young_modulus:  # 显著压力波动
            self.aging.fatigue_cycles += 1


class BranchPipelineNetwork:
    """
    支管并联管网模型

    用于多条管道并联时的流量分配计算
    """

    def __init__(self):
        self.pipelines: Dict[str, NonlinearPipeline] = {}
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.connections: List[Tuple[str, str, str]] = []  # (管道ID, 起点, 终点)

    def add_pipeline(self, pipe_id: str, pipeline: NonlinearPipeline,
                     start_node: str, end_node: str):
        """添加管道"""
        self.pipelines[pipe_id] = pipeline
        self.connections.append((pipe_id, start_node, end_node))

        # 注册节点
        if start_node not in self.nodes:
            self.nodes[start_node] = {"type": "junction", "head": 0, "demand": 0}
        if end_node not in self.nodes:
            self.nodes[end_node] = {"type": "junction", "head": 0, "demand": 0}

    def set_boundary(self, node_id: str, head: float = None, demand: float = None):
        """设置边界条件"""
        if node_id not in self.nodes:
            self.nodes[node_id] = {}

        if head is not None:
            self.nodes[node_id]["type"] = "reservoir"
            self.nodes[node_id]["head"] = head
        if demand is not None:
            self.nodes[node_id]["demand"] = demand

    def solve_steady_state(self, max_iter: int = 100,
                           tolerance: float = 1e-6) -> Dict[str, float]:
        """
        求解稳态流量分配

        使用Hardy-Cross迭代法

        Returns:
            各管道流量字典
        """
        # 初始化流量估计
        flows = {pipe_id: 1.0 for pipe_id in self.pipelines}

        for iteration in range(max_iter):
            max_correction = 0

            # 遍历所有回路（简化：处理并联管道）
            for node_id, node in self.nodes.items():
                if node.get("type") == "reservoir":
                    continue

                # 找到连接到此节点的管道
                connected = []
                for pipe_id, start, end in self.connections:
                    if start == node_id or end == node_id:
                        sign = 1 if start == node_id else -1
                        connected.append((pipe_id, sign))

                if len(connected) < 2:
                    continue

                # 节点流量平衡
                net_flow = node.get("demand", 0)
                for pipe_id, sign in connected:
                    net_flow += sign * flows[pipe_id]

                # 分配校正
                if abs(net_flow) > tolerance:
                    correction = net_flow / len(connected)
                    for pipe_id, sign in connected:
                        flows[pipe_id] -= sign * correction * 0.5

                    max_correction = max(max_correction, abs(correction))

            if max_correction < tolerance:
                break

        return flows

    def step(self, dt: float) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """
        时步推进

        Returns:
            各管道的(水头, 流量)字典
        """
        results = {}

        for pipe_id, pipeline in self.pipelines.items():
            # 找到边界条件
            for conn_pipe, start, end in self.connections:
                if conn_pipe == pipe_id:
                    h_up = self.nodes[start].get("head", 0)
                    h_down = self.nodes[end].get("head", 0)
                    break

            # MOC求解
            H, Q = pipeline.step_moc(dt, h_up, h_down)
            results[pipe_id] = (H, Q)

            # 更新节点水头
            self.nodes[start]["head"] = H[0]
            self.nodes[end]["head"] = H[-1]

        return results


class EquipmentDegradation:
    """
    设备劣化模型

    用于模拟水轮机、发电机等设备的性能衰退
    """

    def __init__(self, equipment_type: str):
        self.equipment_type = equipment_type
        self.installation_date = datetime.now()

        # 劣化参数
        self.efficiency_degradation_rate = 0.001  # %/年
        self.vibration_increase_rate = 0.5        # %/年
        self.wear_rate = 0.02                     # mm/年

        # 当前状态
        self.operating_hours = 0
        self.start_stop_cycles = 0
        self.overload_events = 0
        self.cavitation_time = 0                  # 空化运行累计时间

        # 初始性能
        self.baseline_efficiency = 0.92
        self.baseline_vibration = 20.0            # μm

    def update_operating_time(self, hours: float, is_overload: bool = False,
                              is_cavitation: bool = False):
        """更新运行时间"""
        self.operating_hours += hours

        if is_overload:
            self.overload_events += 1

        if is_cavitation:
            self.cavitation_time += hours

    def record_start_stop(self):
        """记录启停"""
        self.start_stop_cycles += 1

    def get_current_efficiency(self) -> float:
        """获取当前效率"""
        age_years = self.operating_hours / 8760  # 年运行小时

        # 时间劣化
        time_degradation = self.efficiency_degradation_rate * age_years

        # 空化劣化
        cavitation_degradation = 0.05 * (self.cavitation_time / 1000)

        # 启停劣化
        start_stop_degradation = 0.001 * (self.start_stop_cycles / 1000)

        # 过载劣化
        overload_degradation = 0.005 * self.overload_events

        total_degradation = (time_degradation + cavitation_degradation +
                            start_stop_degradation + overload_degradation)

        return max(0.7, self.baseline_efficiency * (1 - total_degradation))

    def get_current_vibration(self) -> float:
        """获取当前振动水平"""
        age_years = self.operating_hours / 8760

        # 振动增长
        vibration_factor = 1 + self.vibration_increase_rate * age_years / 100

        # 启停影响
        start_stop_factor = 1 + 0.001 * self.start_stop_cycles

        return self.baseline_vibration * vibration_factor * start_stop_factor

    def get_remaining_life(self, design_life_hours: float = 200000) -> float:
        """估算剩余寿命（小时）"""
        # 等效运行时间
        equivalent_hours = (self.operating_hours +
                           self.cavitation_time * 2 +
                           self.start_stop_cycles * 10 +
                           self.overload_events * 50)

        remaining = design_life_hours - equivalent_hours
        return max(0, remaining)

    def get_condition_report(self) -> Dict[str, Any]:
        """获取状态报告"""
        return {
            "equipment_type": self.equipment_type,
            "operating_hours": self.operating_hours,
            "start_stop_cycles": self.start_stop_cycles,
            "current_efficiency": self.get_current_efficiency(),
            "current_vibration": self.get_current_vibration(),
            "remaining_life_hours": self.get_remaining_life(),
            "health_score": self._calculate_health_score(),
            "maintenance_recommendation": self._get_maintenance_recommendation(),
        }

    def _calculate_health_score(self) -> float:
        """计算健康分数 (0-100)"""
        eff_score = (self.get_current_efficiency() / self.baseline_efficiency) * 100
        vib_score = max(0, 100 - (self.get_current_vibration() / self.baseline_vibration - 1) * 50)
        life_score = (self.get_remaining_life() / 200000) * 100

        return (eff_score * 0.4 + vib_score * 0.3 + life_score * 0.3)

    def _get_maintenance_recommendation(self) -> str:
        """获取维护建议"""
        health = self._calculate_health_score()

        if health > 90:
            return "设备状态良好，继续正常维护"
        elif health > 70:
            return "建议加强监测，计划下次大修"
        elif health > 50:
            return "建议近期安排检修"
        else:
            return "设备劣化严重，建议立即检修或更换"

