"""
水轮机仿真模块
Turbine Simulation Module

支持混流式(Francis)和冲击式(Pelton)水轮机建模
包含全特性曲线和Suter变换
"""

import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from scipy.interpolate import interp2d, RectBivariateSpline
from enum import Enum


class TurbineType(Enum):
    """水轮机类型"""
    FRANCIS = "francis"
    PELTON = "pelton"
    KAPLAN = "kaplan"
    BULB = "bulb"


@dataclass
class TurbineParams:
    """水轮机参数"""
    turbine_type: TurbineType = TurbineType.FRANCIS
    rated_power: float = 1000.0      # 额定功率 (MW)
    rated_head: float = 480.0        # 额定水头 (m)
    rated_flow: float = 210.0        # 额定流量 (m³/s)
    rated_speed: float = 166.7       # 额定转速 (r/min)
    rated_efficiency: float = 0.94   # 额定效率
    runaway_speed_ratio: float = 1.8 # 飞逸转速比
    inertia_gd2: float = 130000.0    # 机组惯性矩 GD² (t·m²)

    # 导叶/喷嘴参数
    num_guide_vanes: int = 24        # 导叶数量
    guide_vane_close_time: float = 8.0   # 导叶关闭时间 (s)
    guide_vane_open_time: float = 12.0   # 导叶开启时间 (s)
    max_opening: float = 1.0         # 最大开度
    min_opening: float = 0.0         # 最小开度

    # Pelton特有参数
    num_nozzles: int = 6             # 喷嘴数量
    deflector_time: float = 0.3      # 折向器动作时间 (s)

    @property
    def rated_omega(self) -> float:
        """额定角速度 (rad/s)"""
        return self.rated_speed * np.pi / 30

    @property
    def inertia_J(self) -> float:
        """转动惯量 J (kg·m²)"""
        return self.inertia_gd2 * 1000 / 4  # GD² 转 J

    @property
    def mechanical_time_constant(self) -> float:
        """机械时间常数 Ta (s)"""
        return self.inertia_J * self.rated_omega**2 / (self.rated_power * 1e6)


class TurbineBase(ABC):
    """水轮机基类"""

    def __init__(self, params: TurbineParams):
        self.params = params

        # 状态变量
        self.speed = params.rated_speed      # 当前转速 (r/min)
        self.omega = params.rated_omega      # 当前角速度 (rad/s)
        self.guide_vane_opening = 0.8        # 当前导叶开度 (pu)
        self.flow = 0.0                      # 当前流量 (m³/s)
        self.head = params.rated_head        # 当前水头 (m)
        self.power = 0.0                     # 当前功率 (MW)
        self.torque = 0.0                    # 当前力矩 (N·m)
        self.efficiency = 0.0                # 当前效率

        # 历史记录
        self.history: Dict[str, List[float]] = {
            'time': [],
            'speed': [],
            'flow': [],
            'head': [],
            'power': [],
            'torque': [],
            'efficiency': [],
            'opening': [],
        }

        # 初始化特性曲线
        self._init_characteristics()

    @abstractmethod
    def _init_characteristics(self):
        """初始化水轮机特性曲线"""
        pass

    @abstractmethod
    def calculate_flow(self, head: float, opening: float, speed: float) -> float:
        """计算流量"""
        pass

    @abstractmethod
    def calculate_torque(self, head: float, flow: float, speed: float) -> float:
        """计算力矩"""
        pass

    def update(
        self,
        head: float,
        opening: float,
        load_torque: float,
        dt: float,
        current_time: float
    ) -> Tuple[float, float, float]:
        """
        更新水轮机状态

        Args:
            head: 工作水头 (m)
            opening: 导叶开度 (pu)
            load_torque: 负载力矩 (N·m)
            dt: 时间步长 (s)
            current_time: 当前时间 (s)

        Returns:
            (流量, 功率, 转速)
        """
        self.head = head
        self.guide_vane_opening = np.clip(opening, self.params.min_opening, self.params.max_opening)

        # 计算水轮机出力特性
        self.flow = self.calculate_flow(head, self.guide_vane_opening, self.speed)
        self.torque = self.calculate_torque(head, self.flow, self.speed)

        # 计算功率
        self.power = self.torque * self.omega / 1e6  # MW

        # 转动方程 J * dω/dt = M_turbine - M_load
        d_omega = (self.torque - load_torque) / self.params.inertia_J * dt
        self.omega += d_omega
        self.speed = self.omega * 30 / np.pi

        # 计算效率
        if self.head > 0 and self.flow > 0:
            hydraulic_power = 9.81 * 1000 * self.flow * self.head / 1e6  # MW
            self.efficiency = self.power / hydraulic_power if hydraulic_power > 0 else 0
        else:
            self.efficiency = 0

        # 记录历史
        self._record_state(current_time)

        return self.flow, self.power, self.speed

    def _record_state(self, current_time: float):
        """记录当前状态"""
        self.history['time'].append(current_time)
        self.history['speed'].append(self.speed)
        self.history['flow'].append(self.flow)
        self.history['head'].append(self.head)
        self.history['power'].append(self.power)
        self.history['torque'].append(self.torque)
        self.history['efficiency'].append(self.efficiency)
        self.history['opening'].append(self.guide_vane_opening)

    def get_boundary_condition(self) -> callable:
        """获取水力边界条件函数"""
        def turbine_bc(t: float, Cp: float, B: float) -> Tuple[float, float]:
            """
            水轮机边界条件

            Args:
                t: 时间
                Cp: C+特征线常数
                B: 管道阻抗

            Returns:
                (水头, 流量)
            """
            # 简化模型：假设流量与开度成正比
            # 实际应结合特性曲线迭代求解
            Q = self.flow
            H = Cp - B * Q
            return H, Q

        return turbine_bc


class FrancisTurbine(TurbineBase):
    """
    混流式水轮机 (Francis Turbine)

    适用于中高水头水电站
    包含完整的全特性曲线和S形特性区处理
    """

    def __init__(self, params: TurbineParams):
        if params.turbine_type != TurbineType.FRANCIS:
            params.turbine_type = TurbineType.FRANCIS
        super().__init__(params)

    def _init_characteristics(self):
        """
        初始化Francis水轮机特性曲线

        使用Suter变换的全特性曲线(WH, WB曲线)
        """
        # 单位转速和单位流量范围
        self.n11_range = np.linspace(40, 180, 50)  # 单位转速
        self.Q11_range = np.linspace(0.2, 1.5, 50)  # 单位流量

        # 构建效率曲面 (简化模型，实际需要实验数据)
        n11_grid, Q11_grid = np.meshgrid(self.n11_range, self.Q11_range)

        # 最优工况点
        n11_opt = 80.0
        Q11_opt = 0.85
        eta_max = self.params.rated_efficiency

        # 高斯效率曲面
        self.eta_surface = eta_max * np.exp(
            -((n11_grid - n11_opt)**2 / (2 * 30**2) +
              (Q11_grid - Q11_opt)**2 / (2 * 0.3**2))
        )

        # Suter变换参数 (WH和WB曲线)
        # x = arctan(ω*/Q*), 其中ω*和Q*为相对值
        self._init_suter_curves()

    def _init_suter_curves(self):
        """初始化Suter变换曲线"""
        # 定义角度范围 (0到2π)
        self.suter_x = np.linspace(0, 2*np.pi, 360)

        # WH曲线 (水头特性) - 简化的余弦模型
        # 实际应使用白鹤滩等高水头电站的实测数据
        self.WH = 1.0 + 0.3 * np.cos(self.suter_x) + 0.1 * np.cos(2*self.suter_x)

        # WB曲线 (力矩特性)
        self.WB = 0.9 + 0.35 * np.sin(self.suter_x) + 0.1 * np.sin(2*self.suter_x)

        # S形特性区标记 (危险区域)
        self.s_region_start = 0.6 * np.pi
        self.s_region_end = 0.9 * np.pi

    def calculate_flow(self, head: float, opening: float, speed: float) -> float:
        """
        计算Francis水轮机流量

        使用导叶开度方程和相似律
        """
        if head <= 0 or opening <= 0:
            return 0.0

        # 基于相似律的流量计算
        # Q = Q_r * (y/y_r) * sqrt(H/H_r)
        Q_r = self.params.rated_flow
        H_r = self.params.rated_head
        y_r = 0.8  # 额定开度

        Q = Q_r * (opening / y_r) * np.sqrt(head / H_r)

        # 考虑转速影响 (简化模型)
        n_r = self.params.rated_speed
        n_ratio = speed / n_r
        Q *= (0.3 + 0.7 * n_ratio)  # 转速对流量的影响

        return max(0, Q)

    def calculate_torque(self, head: float, flow: float, speed: float) -> float:
        """
        计算Francis水轮机力矩

        使用效率曲线和水力功率
        """
        if head <= 0 or flow <= 0 or speed <= 0:
            return 0.0

        # 计算单位参数
        D = 5.0  # 假设转轮直径 (m)
        n11 = speed * D / np.sqrt(head)
        Q11 = flow / (D**2 * np.sqrt(head))

        # 查找效率
        n11_idx = np.searchsorted(self.n11_range, n11)
        Q11_idx = np.searchsorted(self.Q11_range, Q11)
        n11_idx = np.clip(n11_idx, 0, len(self.n11_range) - 1)
        Q11_idx = np.clip(Q11_idx, 0, len(self.Q11_range) - 1)
        eta = self.eta_surface[Q11_idx, n11_idx]

        # 水力功率
        P_hydraulic = 9.81 * 1000 * flow * head  # W

        # 机械功率
        P_mechanical = P_hydraulic * eta

        # 力矩
        omega = speed * np.pi / 30
        torque = P_mechanical / omega if omega > 0 else 0

        return torque

    def is_in_s_region(self) -> bool:
        """检查是否处于S形特性区"""
        if self.speed <= 0 or self.flow <= 0:
            return False

        # 计算Suter角度
        omega_star = self.speed / self.params.rated_speed
        Q_star = self.flow / self.params.rated_flow
        x = np.arctan2(omega_star, Q_star)

        return self.s_region_start <= x <= self.s_region_end


class PeltonTurbine(TurbineBase):
    """
    冲击式水轮机 (Pelton Turbine)

    适用于超高水头水电站
    特点：使用折向器控制，无直接水锤问题
    """

    def __init__(self, params: TurbineParams):
        if params.turbine_type != TurbineType.PELTON:
            params.turbine_type = TurbineType.PELTON
        super().__init__(params)

        # Pelton特有状态
        self.deflector_position = 0.0  # 折向器位置 (0=全偏,1=全开)
        self.nozzle_openings = [1.0] * params.num_nozzles

    def _init_characteristics(self):
        """初始化Pelton水轮机特性"""
        # 喷嘴流量系数
        self.nozzle_coefficient = 0.97

        # 最优速比
        self.optimal_speed_ratio = 0.46  # u/c_1 最优值

        # 斗叶效率曲线
        speed_ratios = np.linspace(0.2, 0.8, 50)
        self.bucket_efficiency = 0.96 - 2.5 * (speed_ratios - 0.46)**2

    def calculate_flow(self, head: float, opening: float, speed: float) -> float:
        """
        计算Pelton水轮机流量

        流量主要由喷嘴开度和水头决定
        """
        if head <= 0 or opening <= 0:
            return 0.0

        # 喷射流速
        c1 = self.nozzle_coefficient * np.sqrt(2 * 9.81 * head)

        # 单个喷嘴流量 (假设圆形喷嘴)
        nozzle_diameter = 0.3  # 假设值 (m)
        nozzle_area = np.pi * (nozzle_diameter * opening)**2 / 4

        # 总流量
        Q = self.params.num_nozzles * nozzle_area * c1

        # 折向器影响
        Q *= self.deflector_position

        return Q

    def calculate_torque(self, head: float, flow: float, speed: float) -> float:
        """
        计算Pelton水轮机力矩

        使用冲量动量定理
        """
        if head <= 0 or flow <= 0:
            return 0.0

        # 喷射流速
        c1 = self.nozzle_coefficient * np.sqrt(2 * 9.81 * head)

        # 圆周速度
        D = 4.0  # 假设节圆直径 (m)
        u = speed * np.pi / 30 * D / 2

        # 速比
        speed_ratio = u / c1 if c1 > 0 else 0

        # 斗叶效率
        eta_bucket = 0.96 - 2.5 * (speed_ratio - 0.46)**2
        eta_bucket = max(0, min(0.96, eta_bucket))

        # 力矩 (冲量定理)
        # M = ρ * Q * (c1 - u) * D/2 * k
        k = 1.8  # 斗叶系数
        rho = 1000
        torque = rho * flow * (c1 - u) * D / 2 * k * eta_bucket

        return max(0, torque)

    def set_deflector(self, position: float):
        """设置折向器位置 (0-1)"""
        self.deflector_position = np.clip(position, 0, 1)

    def emergency_deflect(self, dt: float):
        """紧急偏转 - 快速降低功率"""
        deflect_rate = 1.0 / self.params.deflector_time
        self.deflector_position = max(0, self.deflector_position - deflect_rate * dt)


@dataclass
class TurbineCharacteristics:
    """水轮机综合特性数据"""
    n11: np.ndarray        # 单位转速
    Q11: np.ndarray        # 单位流量
    eta: np.ndarray        # 效率曲面
    M11: np.ndarray        # 单位力矩
    Pmax: float            # 最大出力
    cavitation_sigma: float  # 空化系数


def create_turbine(turbine_type: str, params: TurbineParams) -> TurbineBase:
    """
    水轮机工厂函数

    Args:
        turbine_type: 水轮机类型 ("francis", "pelton", "kaplan")
        params: 水轮机参数

    Returns:
        水轮机实例
    """
    turbine_map = {
        "francis": FrancisTurbine,
        "pelton": PeltonTurbine,
    }

    turbine_class = turbine_map.get(turbine_type.lower())
    if turbine_class is None:
        raise ValueError(f"不支持的水轮机类型: {turbine_type}")

    return turbine_class(params)
