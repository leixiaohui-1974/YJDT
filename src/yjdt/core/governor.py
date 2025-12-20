"""
调速器仿真模块
Governor Simulation Module

实现水轮机调速器的多种控制策略：
- 传统PID调速器
- 模型预测控制(MPC)调速器
- 自适应控制调速器
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from scipy.optimize import minimize
from enum import Enum


class GovernorMode(Enum):
    """调速器运行模式"""
    SPEED_CONTROL = "speed"           # 转速控制
    POWER_CONTROL = "power"           # 功率控制
    OPENING_CONTROL = "opening"       # 开度控制
    FREQUENCY_REGULATION = "frequency"  # 一次调频
    AGC = "agc"                       # 自动发电控制


@dataclass
class GovernorParams:
    """调速器参数"""
    # PID参数
    kp: float = 2.5               # 比例增益
    ki: float = 0.15              # 积分增益
    kd: float = 4.0               # 微分增益

    # 执行器参数
    servo_gain: float = 5.0       # 伺服增益
    servo_time: float = 0.5       # 执行器时间常数 (s)

    # 限幅参数
    opening_max: float = 1.0      # 开度上限
    opening_min: float = 0.0      # 开度下限
    rate_limit_open: float = 0.1  # 开启速率限制 (pu/s)
    rate_limit_close: float = 0.15  # 关闭速率限制 (pu/s)

    # 死区参数
    dead_band: float = 0.0004     # 死区 (pu)
    backlash: float = 0.002       # 回差 (pu)

    # 永态转差系数
    bp: float = 0.04              # 永态转差系数 (调差率)

    # 调节系统时间常数
    Ty: float = 0.5               # 主配压阀时间常数 (s)
    Tw: float = 12.0              # 水流惯性时间常数 (s)
    Ta: float = 10.0              # 机组惯性时间常数 (s)


class GovernorBase(ABC):
    """调速器基类"""

    def __init__(self, params: GovernorParams):
        self.params = params

        # 状态变量
        self.mode = GovernorMode.SPEED_CONTROL
        self.speed_ref = 1.0      # 转速参考值 (pu)
        self.power_ref = 0.0      # 功率参考值 (pu)
        self.opening_ref = 0.0    # 开度参考值 (pu)

        # 输出变量
        self.opening = 0.0        # 当前开度 (pu)
        self.opening_rate = 0.0   # 开度变化率 (pu/s)

        # 内部状态
        self.error = 0.0          # 误差
        self.error_integral = 0.0  # 误差积分
        self.error_prev = 0.0     # 上一步误差

        # 历史记录
        self.history: Dict[str, List[float]] = {
            'time': [],
            'opening': [],
            'opening_rate': [],
            'error': [],
            'speed_ref': [],
            'power_ref': [],
        }

    @abstractmethod
    def compute_control(
        self,
        speed: float,
        power: float,
        frequency: float,
        dt: float
    ) -> float:
        """
        计算控制输出

        Args:
            speed: 当前转速 (pu)
            power: 当前功率 (pu)
            frequency: 电网频率 (Hz)
            dt: 时间步长 (s)

        Returns:
            导叶开度指令 (pu)
        """
        pass

    def update(
        self,
        speed: float,
        power: float,
        frequency: float = 50.0,
        dt: float = 0.01,
        current_time: float = 0.0
    ) -> float:
        """
        更新调速器状态

        Args:
            speed: 当前转速 (pu)
            power: 当前功率 (pu)
            frequency: 电网频率 (Hz)
            dt: 时间步长 (s)
            current_time: 当前时间 (s)

        Returns:
            导叶开度 (pu)
        """
        # 计算控制输出
        opening_cmd = self.compute_control(speed, power, frequency, dt)

        # 执行器动态
        self._update_servo(opening_cmd, dt)

        # 记录历史
        self._record_state(current_time)

        return self.opening

    def _update_servo(self, opening_cmd: float, dt: float):
        """更新伺服执行器"""
        # 计算期望开度变化率
        rate = (opening_cmd - self.opening) * self.params.servo_gain

        # 速率限制
        if rate > 0:
            rate = min(rate, self.params.rate_limit_open)
        else:
            rate = max(rate, -self.params.rate_limit_close)

        self.opening_rate = rate

        # 更新开度
        self.opening += rate * dt

        # 位置限制
        self.opening = np.clip(
            self.opening,
            self.params.opening_min,
            self.params.opening_max
        )

    def _apply_dead_band(self, error: float) -> float:
        """应用死区"""
        if abs(error) < self.params.dead_band:
            return 0.0
        elif error > 0:
            return error - self.params.dead_band
        else:
            return error + self.params.dead_band

    def _record_state(self, current_time: float):
        """记录当前状态"""
        self.history['time'].append(current_time)
        self.history['opening'].append(self.opening)
        self.history['opening_rate'].append(self.opening_rate)
        self.history['error'].append(self.error)
        self.history['speed_ref'].append(self.speed_ref)
        self.history['power_ref'].append(self.power_ref)

    def set_mode(self, mode: GovernorMode):
        """设置调速器模式"""
        self.mode = mode

    def set_speed_reference(self, ref: float):
        """设置转速参考值"""
        self.speed_ref = ref

    def set_power_reference(self, ref: float):
        """设置功率参考值"""
        self.power_ref = ref

    def set_opening_reference(self, ref: float):
        """设置开度参考值"""
        self.opening_ref = np.clip(ref, self.params.opening_min, self.params.opening_max)


class PIDGovernor(GovernorBase):
    """
    PID调速器

    实现传统的比例-积分-微分控制策略
    包含并联PID和抗积分饱和
    """

    def __init__(self, params: GovernorParams):
        super().__init__(params)

        # 滤波器状态
        self.derivative_filter = 0.0
        self.filter_time = 0.1  # 微分滤波时间常数

        # 抗积分饱和
        self.anti_windup = True
        self.integral_limit = 0.5

    def compute_control(
        self,
        speed: float,
        power: float,
        frequency: float,
        dt: float
    ) -> float:
        """计算PID控制输出"""
        # 计算误差
        if self.mode == GovernorMode.SPEED_CONTROL:
            self.error = self.speed_ref - speed
        elif self.mode == GovernorMode.POWER_CONTROL:
            self.error = self.power_ref - power
        elif self.mode == GovernorMode.FREQUENCY_REGULATION:
            # 一次调频：考虑永态转差
            freq_error = (50.0 - frequency) / 50.0
            self.error = freq_error / self.params.bp
        else:
            self.error = self.opening_ref - self.opening

        # 应用死区
        error_db = self._apply_dead_band(self.error)

        # 比例项
        P = self.params.kp * error_db

        # 积分项（带抗饱和）
        if self.anti_windup:
            # 只在输出未饱和时积分
            if self.params.opening_min < self.opening < self.params.opening_max:
                self.error_integral += error_db * dt
            # 限制积分值
            self.error_integral = np.clip(
                self.error_integral,
                -self.integral_limit,
                self.integral_limit
            )
        else:
            self.error_integral += error_db * dt

        I = self.params.ki * self.error_integral

        # 微分项（带滤波）
        derivative = (error_db - self.error_prev) / dt if dt > 0 else 0
        self.derivative_filter = (
            self.derivative_filter +
            (derivative - self.derivative_filter) * dt / self.filter_time
        )
        D = self.params.kd * self.derivative_filter

        self.error_prev = error_db

        # PID输出
        output = P + I + D

        # 转换为开度指令
        opening_cmd = self.opening + output

        return opening_cmd


class MPCGovernor(GovernorBase):
    """
    模型预测控制(MPC)调速器

    适用于长隧洞高惯性系统
    能够预测水锤效应并提前动作
    """

    def __init__(
        self,
        params: GovernorParams,
        prediction_horizon: int = 30,
        control_horizon: int = 10,
        sample_time: float = 0.1
    ):
        super().__init__(params)

        # MPC参数
        self.Np = prediction_horizon  # 预测时域
        self.Nc = control_horizon     # 控制时域
        self.Ts = sample_time         # 采样时间

        # 系统模型参数 (离散化的水轮机-调节系统模型)
        self._build_prediction_model()

        # 权重矩阵
        self.Q = np.eye(self.Np) * 1.0     # 输出误差权重
        self.R = np.eye(self.Nc) * 0.1     # 控制增量权重
        self.S = np.eye(self.Nc) * 0.01    # 控制量权重

        # 约束
        self.u_min = params.opening_min
        self.u_max = params.opening_max
        self.du_max = params.rate_limit_open * sample_time

        # 优化历史
        self.optimal_sequence: List[float] = []

    def _build_prediction_model(self):
        """
        建立预测模型

        使用简化的水轮机传递函数模型:
        G(s) = (1 - Tw*s) / (1 + 0.5*Tw*s) * 1/(Ta*s)
        """
        Tw = self.params.Tw  # 水流惯性时间常数
        Ta = self.params.Ta  # 机组惯性时间常数
        Ts = self.Ts

        # 离散化状态空间模型
        # 简化为二阶系统
        a1 = -2 * (1/Ta + 1/Tw)
        a2 = 1 / (Ta * Tw)
        b1 = 1 / Ta - 2 / (Ta * Tw)
        b2 = 1 / (Ta * Tw)

        # 离散化 (欧拉法)
        self.Ad = np.array([
            [1 + a1 * Ts, Ts],
            [a2 * Ts, 1]
        ])

        self.Bd = np.array([
            [b1 * Ts],
            [b2 * Ts]
        ])

        self.Cd = np.array([[1, 0]])

        # 状态初始化
        self.x_state = np.zeros((2, 1))

    def compute_control(
        self,
        speed: float,
        power: float,
        frequency: float,
        dt: float
    ) -> float:
        """计算MPC控制输出"""
        # 目标值
        if self.mode == GovernorMode.SPEED_CONTROL:
            ref = self.speed_ref
            current = speed
        elif self.mode == GovernorMode.POWER_CONTROL:
            ref = self.power_ref
            current = power
        else:
            ref = self.speed_ref
            current = speed

        # 参考轨迹
        r = np.ones((self.Np, 1)) * ref

        # 更新状态估计
        self.x_state[0, 0] = current - ref

        # 构建预测矩阵
        F, Phi = self._build_prediction_matrices()

        # 求解QP问题
        du_optimal = self._solve_qp(F, Phi, r)

        # 应用第一个控制增量
        if len(du_optimal) > 0:
            delta_u = du_optimal[0]
        else:
            delta_u = 0.0

        # 限制控制增量
        delta_u = np.clip(delta_u, -self.du_max, self.du_max)

        # 计算新的控制量
        opening_cmd = self.opening + delta_u

        return opening_cmd

    def _build_prediction_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        """构建预测矩阵 F 和 Phi"""
        Np = self.Np
        Nc = self.Nc

        # F矩阵：自由响应
        F = np.zeros((Np, 2))
        A_power = np.eye(2)
        for i in range(Np):
            A_power = A_power @ self.Ad
            F[i, :] = (self.Cd @ A_power).flatten()

        # Phi矩阵：强制响应
        Phi = np.zeros((Np, Nc))
        for i in range(Np):
            for j in range(min(i + 1, Nc)):
                A_power = np.eye(2)
                for k in range(i - j):
                    A_power = A_power @ self.Ad
                Phi[i, j] = (self.Cd @ A_power @ self.Bd)[0, 0]

        return F, Phi

    def _solve_qp(
        self,
        F: np.ndarray,
        Phi: np.ndarray,
        r: np.ndarray
    ) -> np.ndarray:
        """
        求解二次规划问题

        min J = (y - r)' Q (y - r) + du' R du
        s.t. u_min <= u <= u_max
             |du| <= du_max
        """
        # 预测输出
        # y = F * x + Phi * du
        # 优化目标转换为: min du' H du + f' du
        H = Phi.T @ self.Q @ Phi + self.R
        f = Phi.T @ self.Q @ (F @ self.x_state - r)

        # 简化求解：使用解析解（无约束情况）
        try:
            du = -np.linalg.solve(H, f.flatten())
        except np.linalg.LinAlgError:
            du = np.zeros(self.Nc)

        # 应用约束
        for i in range(self.Nc):
            du[i] = np.clip(du[i], -self.du_max, self.du_max)

        return du

    def get_prediction(self) -> np.ndarray:
        """获取预测轨迹"""
        if len(self.optimal_sequence) > 0:
            return np.array(self.optimal_sequence)
        return np.array([self.opening])


class AdaptiveGovernor(GovernorBase):
    """
    自适应调速器

    根据系统工况自动调整控制参数
    适用于变工况运行
    """

    def __init__(self, params: GovernorParams):
        super().__init__(params)

        # 基础PID控制器
        self.pid = PIDGovernor(params)

        # 自适应参数
        self.adaptation_rate = 0.01
        self.parameter_history: List[Dict[str, float]] = []

        # 性能指标
        self.performance_index = 0.0
        self.settling_time_estimate = 0.0

    def compute_control(
        self,
        speed: float,
        power: float,
        frequency: float,
        dt: float
    ) -> float:
        """计算自适应控制输出"""
        # 同步状态
        self.pid.mode = self.mode
        self.pid.speed_ref = self.speed_ref
        self.pid.power_ref = self.power_ref

        # 获取PID输出
        output = self.pid.compute_control(speed, power, frequency, dt)

        # 自适应调整
        self._adapt_parameters(speed, power, dt)

        return output

    def _adapt_parameters(self, speed: float, power: float, dt: float):
        """自适应调整PID参数"""
        # 计算误差能量
        error_energy = self.pid.error ** 2

        # 基于MIT规则的参数调整
        # dKp/dt = -γ * e * de/dt
        gamma = self.adaptation_rate

        # 调整比例增益
        if abs(self.pid.error) > 0.01:
            dKp = -gamma * self.pid.error * (self.pid.error - self.pid.error_prev) / dt
            self.params.kp += dKp * dt
            self.params.kp = np.clip(self.params.kp, 0.5, 10.0)

        # 更新到PID控制器
        self.pid.params.kp = self.params.kp

        # 记录参数历史
        self.parameter_history.append({
            'kp': self.params.kp,
            'ki': self.params.ki,
            'kd': self.params.kd,
        })

    def reset_adaptation(self):
        """重置自适应参数"""
        self.params.kp = 2.5
        self.params.ki = 0.15
        self.params.kd = 4.0
        self.pid.params = self.params


def create_governor(governor_type: str, params: GovernorParams) -> GovernorBase:
    """
    调速器工厂函数

    Args:
        governor_type: 调速器类型 ("pid", "mpc", "adaptive")
        params: 调速器参数

    Returns:
        调速器实例
    """
    governor_map = {
        "pid": PIDGovernor,
        "mpc": MPCGovernor,
        "adaptive": AdaptiveGovernor,
    }

    governor_class = governor_map.get(governor_type.lower())
    if governor_class is None:
        raise ValueError(f"不支持的调速器类型: {governor_type}")

    return governor_class(params)
