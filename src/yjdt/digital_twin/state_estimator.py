# -*- coding: utf-8 -*-
"""
状态估计器 - 基于观测数据的最优状态估计
State Estimator - Optimal State Estimation from Observations

功能：
- 卡尔曼滤波
- 粒子滤波
- 扩展卡尔曼滤波
- 无迹卡尔曼滤波
- 多传感器融合
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime


@dataclass
class EstimationResult:
    """估计结果"""
    state: np.ndarray                       # 状态向量
    covariance: np.ndarray                  # 协方差矩阵
    innovation: np.ndarray                  # 新息
    likelihood: float                       # 似然
    timestamp: datetime = field(default_factory=datetime.now)

    def get_confidence_interval(self, index: int, confidence: float = 0.95) -> tuple:
        """获取置信区间"""
        std = np.sqrt(self.covariance[index, index])
        z = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%
        return (self.state[index] - z * std, self.state[index] + z * std)


class KalmanFilter:
    """
    卡尔曼滤波器

    用于线性系统的最优状态估计
    x(k+1) = A*x(k) + B*u(k) + w(k)
    y(k) = C*x(k) + v(k)
    """

    def __init__(self, n_states: int, n_measurements: int, n_inputs: int = 0):
        self.n_states = n_states
        self.n_measurements = n_measurements
        self.n_inputs = n_inputs

        # 状态转移矩阵
        self.A = np.eye(n_states)
        # 输入矩阵
        self.B = np.zeros((n_states, max(n_inputs, 1)))
        # 观测矩阵
        self.C = np.zeros((n_measurements, n_states))
        # 过程噪声协方差
        self.Q = np.eye(n_states) * 0.01
        # 测量噪声协方差
        self.R = np.eye(n_measurements) * 0.1

        # 状态估计
        self.x = np.zeros(n_states)
        # 估计协方差
        self.P = np.eye(n_states)

    def configure(self, A: Optional[np.ndarray] = None,
                  B: Optional[np.ndarray] = None,
                  C: Optional[np.ndarray] = None,
                  Q: Optional[np.ndarray] = None,
                  R: Optional[np.ndarray] = None):
        """配置滤波器矩阵"""
        if A is not None:
            self.A = np.array(A)
        if B is not None:
            self.B = np.array(B)
        if C is not None:
            self.C = np.array(C)
        if Q is not None:
            self.Q = np.array(Q)
        if R is not None:
            self.R = np.array(R)

    def predict(self, u: Optional[np.ndarray] = None) -> np.ndarray:
        """
        预测步骤

        Args:
            u: 控制输入

        Returns:
            预测状态
        """
        if u is None:
            u = np.zeros(self.n_inputs) if self.n_inputs > 0 else np.zeros(1)

        # 状态预测
        self.x = self.A @ self.x + self.B @ u

        # 协方差预测
        self.P = self.A @ self.P @ self.A.T + self.Q

        return self.x.copy()

    def update(self, y: np.ndarray) -> EstimationResult:
        """
        更新步骤

        Args:
            y: 测量值

        Returns:
            估计结果
        """
        y = np.array(y).flatten()

        # 新息
        innovation = y - self.C @ self.x

        # 新息协方差
        S = self.C @ self.P @ self.C.T + self.R

        # 卡尔曼增益
        K = self.P @ self.C.T @ np.linalg.inv(S)

        # 状态更新
        self.x = self.x + K @ innovation

        # 协方差更新 (Joseph form for numerical stability)
        I = np.eye(self.n_states)
        self.P = (I - K @ self.C) @ self.P @ (I - K @ self.C).T + K @ self.R @ K.T

        # 计算似然
        likelihood = self._compute_likelihood(innovation, S)

        return EstimationResult(
            state=self.x.copy(),
            covariance=self.P.copy(),
            innovation=innovation,
            likelihood=likelihood
        )

    def _compute_likelihood(self, innovation: np.ndarray, S: np.ndarray) -> float:
        """计算测量似然"""
        n = len(innovation)
        det_S = np.linalg.det(S)
        if det_S <= 0:
            return 0.0

        exp_term = -0.5 * innovation.T @ np.linalg.inv(S) @ innovation
        likelihood = (1.0 / np.sqrt((2 * np.pi) ** n * det_S)) * np.exp(exp_term)
        return float(likelihood)

    def reset(self, x0: Optional[np.ndarray] = None, P0: Optional[np.ndarray] = None):
        """重置滤波器"""
        if x0 is not None:
            self.x = np.array(x0)
        else:
            self.x = np.zeros(self.n_states)

        if P0 is not None:
            self.P = np.array(P0)
        else:
            self.P = np.eye(self.n_states)


class ExtendedKalmanFilter:
    """
    扩展卡尔曼滤波器

    用于非线性系统
    x(k+1) = f(x(k), u(k)) + w(k)
    y(k) = h(x(k)) + v(k)
    """

    def __init__(self, n_states: int, n_measurements: int):
        self.n_states = n_states
        self.n_measurements = n_measurements

        # 状态转移函数和雅可比
        self.f: Callable = lambda x, u: x
        self.F: Callable = lambda x, u: np.eye(n_states)

        # 观测函数和雅可比
        self.h: Callable = lambda x: x[:n_measurements]
        self.H: Callable = lambda x: np.eye(n_measurements, n_states)

        # 噪声协方差
        self.Q = np.eye(n_states) * 0.01
        self.R = np.eye(n_measurements) * 0.1

        # 状态估计
        self.x = np.zeros(n_states)
        self.P = np.eye(n_states)

    def set_dynamics(self, f: Callable, F: Callable):
        """设置状态转移函数"""
        self.f = f
        self.F = F

    def set_observation(self, h: Callable, H: Callable):
        """设置观测函数"""
        self.h = h
        self.H = H

    def predict(self, u: Optional[np.ndarray] = None) -> np.ndarray:
        """预测步骤"""
        u = u if u is not None else np.zeros(1)

        # 非线性状态预测
        self.x = self.f(self.x, u)

        # 雅可比矩阵
        F = self.F(self.x, u)

        # 协方差预测
        self.P = F @ self.P @ F.T + self.Q

        return self.x.copy()

    def update(self, y: np.ndarray) -> EstimationResult:
        """更新步骤"""
        y = np.array(y).flatten()

        # 非线性观测
        y_pred = self.h(self.x)
        innovation = y - y_pred

        # 雅可比矩阵
        H = self.H(self.x)

        # 新息协方差
        S = H @ self.P @ H.T + self.R

        # 卡尔曼增益
        K = self.P @ H.T @ np.linalg.inv(S)

        # 状态更新
        self.x = self.x + K @ innovation

        # 协方差更新
        I = np.eye(self.n_states)
        self.P = (I - K @ H) @ self.P

        # 计算似然
        det_S = np.linalg.det(S)
        likelihood = 0.0
        if det_S > 0:
            exp_term = -0.5 * innovation.T @ np.linalg.inv(S) @ innovation
            likelihood = np.exp(exp_term) / np.sqrt((2 * np.pi) ** len(innovation) * det_S)

        return EstimationResult(
            state=self.x.copy(),
            covariance=self.P.copy(),
            innovation=innovation,
            likelihood=float(likelihood)
        )


class ParticleFilter:
    """
    粒子滤波器

    用于高度非线性/非高斯系统
    """

    def __init__(self, n_states: int, n_particles: int = 1000):
        self.n_states = n_states
        self.n_particles = n_particles

        # 粒子和权重
        self.particles = np.random.randn(n_particles, n_states)
        self.weights = np.ones(n_particles) / n_particles

        # 动态模型
        self.f: Callable = lambda x, u: x + np.random.randn(*x.shape) * 0.1
        self.likelihood_fn: Callable = lambda y, x: np.exp(-0.5 * np.sum((y - x[:len(y)])**2))

        # 重采样阈值
        self.resample_threshold = n_particles / 2

    def set_dynamics(self, f: Callable):
        """设置动态模型"""
        self.f = f

    def set_likelihood(self, likelihood_fn: Callable):
        """设置似然函数"""
        self.likelihood_fn = likelihood_fn

    def predict(self, u: Optional[np.ndarray] = None) -> np.ndarray:
        """预测步骤"""
        u = u if u is not None else np.zeros(1)

        # 传播所有粒子
        for i in range(self.n_particles):
            self.particles[i] = self.f(self.particles[i], u)

        return self.get_estimate()

    def update(self, y: np.ndarray) -> EstimationResult:
        """更新步骤"""
        y = np.array(y).flatten()

        # 计算权重
        for i in range(self.n_particles):
            self.weights[i] *= self.likelihood_fn(y, self.particles[i])

        # 归一化
        weight_sum = np.sum(self.weights)
        if weight_sum > 0:
            self.weights /= weight_sum
        else:
            self.weights = np.ones(self.n_particles) / self.n_particles

        # 重采样
        n_eff = 1.0 / np.sum(self.weights ** 2)
        if n_eff < self.resample_threshold:
            self._resample()

        # 计算估计
        x_est = self.get_estimate()
        P_est = self.get_covariance()

        return EstimationResult(
            state=x_est,
            covariance=P_est,
            innovation=y - x_est[:len(y)],
            likelihood=float(weight_sum)
        )

    def _resample(self):
        """系统重采样"""
        cumsum = np.cumsum(self.weights)
        cumsum[-1] = 1.0  # 确保最后一个为1

        # 系统重采样
        positions = (np.arange(self.n_particles) + np.random.uniform()) / self.n_particles
        indices = np.searchsorted(cumsum, positions)

        # 重采样粒子
        self.particles = self.particles[indices].copy()
        self.weights = np.ones(self.n_particles) / self.n_particles

    def get_estimate(self) -> np.ndarray:
        """获取加权平均估计"""
        return np.average(self.particles, axis=0, weights=self.weights)

    def get_covariance(self) -> np.ndarray:
        """获取加权协方差"""
        x_mean = self.get_estimate()
        diff = self.particles - x_mean
        return np.cov(diff.T, aweights=self.weights)

    def reset(self, x0: Optional[np.ndarray] = None, spread: float = 1.0):
        """重置粒子"""
        if x0 is not None:
            self.particles = x0 + np.random.randn(self.n_particles, self.n_states) * spread
        else:
            self.particles = np.random.randn(self.n_particles, self.n_states)
        self.weights = np.ones(self.n_particles) / self.n_particles


class StateEstimator:
    """
    综合状态估计器

    集成多种滤波方法，提供统一接口
    """

    def __init__(self, method: str = "kalman"):
        self.method = method
        self.filter = None
        self.state_names: List[str] = []
        self.measurement_names: List[str] = []

        # 历史记录
        self.history: List[EstimationResult] = []

    def configure(self, n_states: int, n_measurements: int,
                  state_names: Optional[List[str]] = None,
                  measurement_names: Optional[List[str]] = None,
                  **kwargs):
        """配置估计器"""
        self.state_names = state_names or [f"x{i}" for i in range(n_states)]
        self.measurement_names = measurement_names or [f"y{i}" for i in range(n_measurements)]

        if self.method == "kalman":
            self.filter = KalmanFilter(n_states, n_measurements)
            if "A" in kwargs:
                self.filter.configure(**kwargs)
        elif self.method == "ekf":
            self.filter = ExtendedKalmanFilter(n_states, n_measurements)
        elif self.method == "particle":
            n_particles = kwargs.get("n_particles", 1000)
            self.filter = ParticleFilter(n_states, n_particles)

    def estimate(self, measurements: Dict[str, float],
                 inputs: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        执行状态估计

        Args:
            measurements: 测量值字典
            inputs: 控制输入字典

        Returns:
            估计结果字典
        """
        if self.filter is None:
            return {"error": "Filter not configured"}

        # 转换为向量
        y = np.array([measurements.get(name, 0.0) for name in self.measurement_names])

        u = None
        if inputs:
            u = np.array(list(inputs.values()))

        # 预测
        self.filter.predict(u)

        # 更新
        result = self.filter.update(y)

        # 保存历史
        self.history.append(result)
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

        # 转换为字典
        state_dict = {name: result.state[i] for i, name in enumerate(self.state_names)}
        confidence = {
            name: result.get_confidence_interval(i)
            for i, name in enumerate(self.state_names)
        }

        return {
            "states": state_dict,
            "confidence_intervals": confidence,
            "likelihood": result.likelihood,
            "timestamp": result.timestamp.isoformat(),
        }

    def get_state(self, name: str) -> Optional[float]:
        """获取单个状态值"""
        if not self.history:
            return None
        result = self.history[-1]
        if name in self.state_names:
            idx = self.state_names.index(name)
            return float(result.state[idx])
        return None

    def reset(self, initial_state: Optional[Dict[str, float]] = None):
        """重置估计器"""
        if self.filter is None:
            return

        x0 = None
        if initial_state:
            x0 = np.array([initial_state.get(name, 0.0) for name in self.state_names])

        if hasattr(self.filter, 'reset'):
            self.filter.reset(x0)

        self.history = []
