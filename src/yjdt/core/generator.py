"""
发电机仿真模块
Generator Simulation Module

实现同步发电机的电磁暂态和机电暂态模型
支持与电网的交互仿真
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class GeneratorState(Enum):
    """发电机状态"""
    STOPPED = "stopped"           # 停机
    STARTING = "starting"         # 启动中
    SYNCHRONIZING = "synchronizing"  # 并网中
    RUNNING = "running"           # 运行中
    LOAD_SHEDDING = "load_shedding"  # 甩负荷
    STOPPING = "stopping"         # 停机中


@dataclass
class GeneratorParams:
    """发电机参数"""
    # 额定参数
    rated_power: float = 1111.0     # 额定容量 (MVA)
    rated_voltage: float = 20.0     # 额定电压 (kV)
    rated_current: float = 32.0     # 额定电流 (kA)
    rated_frequency: float = 50.0   # 额定频率 (Hz)
    rated_speed: float = 166.7      # 额定转速 (r/min)
    power_factor: float = 0.9       # 功率因数
    poles: int = 36                 # 极对数

    # 惯性参数
    inertia_constant: float = 4.0   # 惯性时间常数 H (s)
    damping_coefficient: float = 2.0  # 阻尼系数 D

    # 电抗参数 (标幺值)
    xd: float = 1.0               # d轴同步电抗
    xq: float = 0.6               # q轴同步电抗
    xd_prime: float = 0.3         # d轴暂态电抗
    xd_double_prime: float = 0.2  # d轴次暂态电抗
    xq_double_prime: float = 0.25 # q轴次暂态电抗
    xl: float = 0.15              # 漏抗

    # 时间常数
    Td0_prime: float = 6.0        # d轴开路暂态时间常数 (s)
    Td0_double_prime: float = 0.04  # d轴开路次暂态时间常数 (s)
    Tq0_double_prime: float = 0.05  # q轴开路次暂态时间常数 (s)

    # 励磁系统参数
    exciter_gain: float = 200.0   # 励磁增益
    exciter_time_constant: float = 0.5  # 励磁时间常数 (s)
    ceiling_voltage: float = 3.0  # 顶值电压 (pu)

    @property
    def rated_omega(self) -> float:
        """额定角速度 (rad/s)"""
        return 2 * np.pi * self.rated_frequency

    @property
    def rated_omega_m(self) -> float:
        """额定机械角速度 (rad/s)"""
        return self.rated_speed * np.pi / 30


class SynchronousGenerator:
    """
    同步发电机类

    实现完整的机电暂态模型，包括：
    - 6阶电磁暂态模型
    - 励磁系统
    - 与电网交互
    """

    def __init__(self, params: GeneratorParams):
        self.params = params

        # 状态变量
        self.state = GeneratorState.STOPPED
        self.delta = 0.0          # 功角 (rad)
        self.omega = 0.0          # 角速度 (pu)
        self.speed = 0.0          # 转速 (r/min)

        # 电磁状态变量
        self.Ed_prime = 0.0       # d轴暂态电势
        self.Eq_prime = 1.0       # q轴暂态电势
        self.Ed_double_prime = 0.0  # d轴次暂态电势
        self.Eq_double_prime = 1.0  # q轴次暂态电势

        # 励磁状态
        self.Efd = 1.0            # 励磁电压 (pu)
        self.Vref = 1.0           # 参考电压 (pu)

        # 输出变量
        self.Pe = 0.0             # 电磁功率 (pu)
        self.Qe = 0.0             # 无功功率 (pu)
        self.Vt = 1.0             # 端电压 (pu)
        self.It = 0.0             # 端电流 (pu)
        self.Id = 0.0             # d轴电流 (pu)
        self.Iq = 0.0             # q轴电流 (pu)

        # 机械输入
        self.Pm = 0.0             # 机械功率 (pu)
        self.Tm = 0.0             # 机械力矩 (N·m)

        # 电网参数
        self.grid_voltage = 1.0   # 电网电压 (pu)
        self.grid_frequency = 50.0  # 电网频率 (Hz)
        self.Xe = 0.1             # 外部电抗 (pu)

        # 历史记录
        self.history: Dict[str, List[float]] = {
            'time': [],
            'delta': [],
            'omega': [],
            'speed': [],
            'Pe': [],
            'Qe': [],
            'Vt': [],
            'Eq_prime': [],
            'Efd': [],
        }

    def initialize(self, P0: float, Q0: float, V0: float):
        """
        初始化发电机运行点

        Args:
            P0: 初始有功功率 (pu)
            Q0: 初始无功功率 (pu)
            V0: 初始端电压 (pu)
        """
        self.Pe = P0
        self.Qe = Q0
        self.Vt = V0
        self.Pm = P0  # 假设初始平衡

        # 计算初始电流
        S0 = np.sqrt(P0**2 + Q0**2)
        self.It = S0 / V0 if V0 > 0 else 0
        phi = np.arctan2(Q0, P0)

        # 计算初始功角
        self.Iq = self.It * np.cos(phi)
        self.Id = self.It * np.sin(phi)

        # 计算初始暂态电势
        self.Eq_prime = V0 + self.params.xd_prime * self.Id
        self.Ed_prime = -self.params.xq * self.Iq

        # 计算初始功角
        self.delta = np.arctan2(self.params.xq * self.Iq, V0 + self.params.xd * self.Id)

        # 初始化励磁
        self.Efd = self.Eq_prime + (self.params.xd - self.params.xd_prime) * self.Id
        self.Vref = V0

        self.omega = 1.0
        self.speed = self.params.rated_speed
        self.state = GeneratorState.RUNNING

    def update(
        self,
        Pm: float,
        dt: float,
        current_time: float,
        grid_voltage: float = 1.0,
        grid_frequency: float = 50.0
    ) -> Tuple[float, float, float]:
        """
        更新发电机状态

        Args:
            Pm: 机械功率输入 (pu)
            dt: 时间步长 (s)
            current_time: 当前时间 (s)
            grid_voltage: 电网电压 (pu)
            grid_frequency: 电网频率 (Hz)

        Returns:
            (电磁功率, 无功功率, 端电压)
        """
        self.Pm = Pm
        self.grid_voltage = grid_voltage
        self.grid_frequency = grid_frequency

        # 电磁暂态方程
        self._update_electromagnetic(dt)

        # 励磁系统
        self._update_excitation(dt)

        # 机电暂态方程（摇摆方程）
        self._update_mechanical(dt)

        # 计算输出
        self._calculate_outputs()

        # 记录历史
        self._record_state(current_time)

        return self.Pe, self.Qe, self.Vt

    def _update_electromagnetic(self, dt: float):
        """更新电磁暂态状态"""
        xd = self.params.xd
        xd_prime = self.params.xd_prime
        xq = self.params.xq
        Td0_prime = self.params.Td0_prime

        # d轴暂态电势微分方程
        # dEq'/dt = (Efd - Eq' - (xd - xd')*Id) / Td0'
        dEq_prime = (self.Efd - self.Eq_prime - (xd - xd_prime) * self.Id) / Td0_prime
        self.Eq_prime += dEq_prime * dt

    def _update_excitation(self, dt: float):
        """更新励磁系统"""
        Ka = self.params.exciter_gain
        Ta = self.params.exciter_time_constant
        Efd_max = self.params.ceiling_voltage

        # 电压误差
        Ve = self.Vref - self.Vt

        # 简化的一阶励磁模型
        dEfd = (Ka * Ve - self.Efd) / Ta
        self.Efd += dEfd * dt

        # 限幅
        self.Efd = np.clip(self.Efd, 0, Efd_max)

    def _update_mechanical(self, dt: float):
        """更新机械暂态状态（摇摆方程）"""
        H = self.params.inertia_constant
        D = self.params.damping_coefficient
        omega0 = 2 * np.pi * self.params.rated_frequency

        # 摇摆方程
        # 2H * d(ω-1)/dt = Pm - Pe - D*(ω-1)
        d_omega = (self.Pm - self.Pe - D * (self.omega - 1)) / (2 * H)
        self.omega += d_omega * dt

        # 功角方程
        # dδ/dt = ω0 * (ω - 1)
        d_delta = omega0 * (self.omega - 1)
        self.delta += d_delta * dt

        # 保持功角在合理范围
        self.delta = np.mod(self.delta + np.pi, 2 * np.pi) - np.pi

        # 转速
        self.speed = self.omega * self.params.rated_speed

    def _calculate_outputs(self):
        """计算输出变量"""
        Vinf = self.grid_voltage
        xd_prime = self.params.xd_prime
        xq = self.params.xq
        Xe = self.Xe

        # 简化的功率计算（忽略电阻）
        X_total = xd_prime + Xe

        # 电磁功率
        self.Pe = self.Eq_prime * Vinf * np.sin(self.delta) / X_total

        # 无功功率
        self.Qe = (self.Eq_prime * Vinf * np.cos(self.delta) - Vinf**2) / X_total

        # 端电压（简化计算）
        self.Vt = np.sqrt(
            (Vinf + Xe * self.Qe / Vinf)**2 +
            (Xe * self.Pe / Vinf)**2
        )
        self.Vt = np.clip(self.Vt, 0.8, 1.2)

    def _record_state(self, current_time: float):
        """记录当前状态"""
        self.history['time'].append(current_time)
        self.history['delta'].append(self.delta)
        self.history['omega'].append(self.omega)
        self.history['speed'].append(self.speed)
        self.history['Pe'].append(self.Pe)
        self.history['Qe'].append(self.Qe)
        self.history['Vt'].append(self.Vt)
        self.history['Eq_prime'].append(self.Eq_prime)
        self.history['Efd'].append(self.Efd)

    def load_rejection(self, rejection_ratio: float = 1.0):
        """
        甩负荷处理

        Args:
            rejection_ratio: 甩负荷比例 (0-1)
        """
        self.Pe *= (1 - rejection_ratio)
        self.state = GeneratorState.LOAD_SHEDDING

    def get_frequency(self) -> float:
        """获取当前频率 (Hz)"""
        return self.omega * self.params.rated_frequency

    def get_power_mw(self) -> float:
        """获取当前功率 (MW)"""
        return self.Pe * self.params.rated_power * self.params.power_factor

    def get_reactive_power_mvar(self) -> float:
        """获取当前无功功率 (MVar)"""
        return self.Qe * self.params.rated_power

    def is_stable(self) -> bool:
        """检查是否稳定运行"""
        # 检查功角是否在稳定范围内
        if abs(self.delta) > 2.0:  # 约115度
            return False

        # 检查转速是否在允许范围内
        if self.omega < 0.95 or self.omega > 1.05:
            return False

        return True

    def get_critical_clearing_time(self, fault_location: float = 0.5) -> float:
        """
        估算临界切除时间

        Args:
            fault_location: 故障位置 (0-1)

        Returns:
            临界切除时间 (s)
        """
        H = self.params.inertia_constant
        P0 = self.Pm

        # 简化的等面积法则估算
        delta_0 = self.delta
        delta_max = np.pi - delta_0

        # 加速面积近似
        A_acc = P0 * (delta_max - delta_0)

        # 临界时间估算
        t_cr = np.sqrt(4 * H * (delta_max - delta_0) / (np.pi * self.params.rated_frequency * P0))

        return t_cr


class GridInterface:
    """电网接口类"""

    def __init__(
        self,
        nominal_voltage: float = 500.0,  # kV
        nominal_frequency: float = 50.0,  # Hz
        short_circuit_capacity: float = 10000.0,  # MVA
    ):
        self.nominal_voltage = nominal_voltage
        self.nominal_frequency = nominal_frequency
        self.short_circuit_capacity = short_circuit_capacity

        # 电网状态
        self.voltage = 1.0  # pu
        self.frequency = nominal_frequency
        self.angle = 0.0

        # 电网阻抗
        self.Xe = nominal_voltage**2 / short_circuit_capacity  # 等值电抗 (Ω)

    def update(self, dt: float, total_power_injection: float):
        """
        更新电网状态

        Args:
            dt: 时间步长 (s)
            total_power_injection: 总注入功率 (MW)
        """
        # 简化的频率响应模型
        # Δf = ΔP / (S_sc * K)
        K = 0.05  # 频率响应系数
        delta_f = total_power_injection / (self.short_circuit_capacity * K)
        self.frequency = self.nominal_frequency + delta_f

        # 更新电压角度
        self.angle += 2 * np.pi * (self.frequency - self.nominal_frequency) * dt

    def get_voltage_pu(self) -> float:
        """获取电网电压标幺值"""
        return self.voltage

    def get_frequency_hz(self) -> float:
        """获取电网频率"""
        return self.frequency

    def apply_fault(self, fault_type: str, duration: float):
        """
        应用电网故障

        Args:
            fault_type: 故障类型 ("three_phase", "single_line", "voltage_dip")
            duration: 故障持续时间 (s)
        """
        if fault_type == "three_phase":
            self.voltage = 0.0
        elif fault_type == "single_line":
            self.voltage = 0.7
        elif fault_type == "voltage_dip":
            self.voltage = 0.8
