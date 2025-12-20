# -*- coding: utf-8 -*-
"""
数据同化模块 - 观测与模型融合
Data Assimilation Module - Observation-Model Fusion

功能：
- 集合卡尔曼滤波 (EnKF)
- 四维变分同化 (4D-Var)
- 粒子滤波 (PF)
- 模型误差估计
- 观测质量控制

实现模型预测与实测数据的最优融合
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod


class AssimilationMethod(Enum):
    """同化方法"""
    ENKF = "ensemble_kalman_filter"
    ETKF = "ensemble_transform_kalman_filter"
    FOUR_D_VAR = "four_dimensional_variational"
    PARTICLE_FILTER = "particle_filter"
    HYBRID = "hybrid"


@dataclass
class AssimilationResult:
    """同化结果"""
    analysis_state: np.ndarray              # 分析场（同化后状态）
    analysis_covariance: np.ndarray         # 分析误差协方差
    background_state: np.ndarray            # 背景场（模型预测）
    observations: np.ndarray                # 观测值
    innovation: np.ndarray                  # 新息（观测-预测）
    gain_matrix: Optional[np.ndarray]       # 增益矩阵
    chi_squared: float                      # 卡方统计量
    effective_observations: int             # 有效观测数
    timestamp: datetime = field(default_factory=datetime.now)

    def get_correction(self) -> np.ndarray:
        """获取同化校正量"""
        return self.analysis_state - self.background_state


class ObservationOperator:
    """观测算子"""

    def __init__(self, state_dim: int, obs_dim: int):
        self.state_dim = state_dim
        self.obs_dim = obs_dim
        self.H = np.zeros((obs_dim, state_dim))  # 线性观测矩阵

    def set_linear_operator(self, H: np.ndarray):
        """设置线性观测算子"""
        self.H = H

    def forward(self, state: np.ndarray) -> np.ndarray:
        """正向观测（状态→观测）"""
        return self.H @ state

    def tangent_linear(self, state: np.ndarray) -> np.ndarray:
        """切线性算子"""
        return self.H

    def adjoint(self, obs_perturbation: np.ndarray) -> np.ndarray:
        """伴随算子"""
        return self.H.T @ obs_perturbation


class EnsembleKalmanFilter:
    """
    集合卡尔曼滤波器 (EnKF)

    适用于大规模非线性系统
    """

    def __init__(self, state_dim: int, obs_dim: int, ensemble_size: int = 50):
        self.state_dim = state_dim
        self.obs_dim = obs_dim
        self.ensemble_size = ensemble_size

        # 集合成员
        self.ensemble = np.zeros((ensemble_size, state_dim))

        # 观测误差协方差
        self.R = np.eye(obs_dim) * 0.01

        # 模型误差协方差
        self.Q = np.eye(state_dim) * 0.001

        # 膨胀因子
        self.inflation_factor = 1.05

        # 局地化半径
        self.localization_radius = None

    def initialize_ensemble(self, mean: np.ndarray, covariance: np.ndarray):
        """初始化集合"""
        self.ensemble = np.random.multivariate_normal(
            mean, covariance, self.ensemble_size
        )

    def forecast(self, model_func: Callable, dt: float, inputs: Dict = None):
        """集合预报"""
        inputs = inputs or {}

        for i in range(self.ensemble_size):
            # 模型积分
            self.ensemble[i] = model_func(self.ensemble[i], dt, inputs)

            # 添加模型误差
            self.ensemble[i] += np.random.multivariate_normal(
                np.zeros(self.state_dim),
                self.Q
            )

    def analysis(self, observations: np.ndarray,
                 obs_operator: ObservationOperator) -> AssimilationResult:
        """集合分析（同化）"""
        n = self.ensemble_size
        m = self.obs_dim

        # 集合均值
        x_mean = np.mean(self.ensemble, axis=0)

        # 集合扰动
        X_prime = self.ensemble - x_mean

        # 背景误差协方差（采样估计）
        P_b = X_prime.T @ X_prime / (n - 1)

        # 协方差膨胀
        P_b *= self.inflation_factor

        # 观测集合
        Y = np.array([obs_operator.forward(x) for x in self.ensemble])
        y_mean = np.mean(Y, axis=0)
        Y_prime = Y - y_mean

        # 观测空间背景协方差
        HP_bH_T = Y_prime.T @ Y_prime / (n - 1)

        # 卡尔曼增益
        S = HP_bH_T + self.R
        K = P_b @ obs_operator.H.T @ np.linalg.inv(S)

        # 新息
        innovation = observations - obs_operator.forward(x_mean)

        # 分析更新
        for i in range(n):
            # 扰动观测
            obs_perturbed = observations + np.random.multivariate_normal(
                np.zeros(m), self.R
            )
            # 更新成员
            d = obs_perturbed - obs_operator.forward(self.ensemble[i])
            self.ensemble[i] += K @ d

        # 分析均值和协方差
        x_analysis = np.mean(self.ensemble, axis=0)
        X_a_prime = self.ensemble - x_analysis
        P_a = X_a_prime.T @ X_a_prime / (n - 1)

        # 卡方统计
        chi2 = innovation.T @ np.linalg.inv(S) @ innovation

        return AssimilationResult(
            analysis_state=x_analysis,
            analysis_covariance=P_a,
            background_state=x_mean,
            observations=observations,
            innovation=innovation,
            gain_matrix=K,
            chi_squared=chi2,
            effective_observations=m,
        )

    def get_ensemble_spread(self) -> np.ndarray:
        """获取集合离散度"""
        return np.std(self.ensemble, axis=0)

    def get_ensemble_mean(self) -> np.ndarray:
        """获取集合均值"""
        return np.mean(self.ensemble, axis=0)


class FourDVar:
    """
    四维变分同化 (4D-Var)

    在时间窗口内最小化目标函数
    """

    def __init__(self, state_dim: int, obs_dim: int, window_length: int = 10):
        self.state_dim = state_dim
        self.obs_dim = obs_dim
        self.window_length = window_length

        # 背景误差协方差
        self.B = np.eye(state_dim) * 0.01

        # 观测误差协方差
        self.R = np.eye(obs_dim) * 0.01

        # 优化参数
        self.max_iterations = 50
        self.tolerance = 1e-6

    def minimize(self, x_background: np.ndarray,
                 observations: List[np.ndarray],
                 obs_times: List[int],
                 model_func: Callable,
                 obs_operator: ObservationOperator,
                 dt: float) -> AssimilationResult:
        """
        最小化4D-Var目标函数

        J(x) = 0.5 * (x-xb)^T B^-1 (x-xb) + 0.5 * Σ (y-H(x))^T R^-1 (y-H(x))
        """
        x = x_background.copy()
        B_inv = np.linalg.inv(self.B)
        R_inv = np.linalg.inv(self.R)

        for iteration in range(self.max_iterations):
            # 计算目标函数和梯度
            J, grad = self._compute_cost_gradient(
                x, x_background, observations, obs_times,
                model_func, obs_operator, dt, B_inv, R_inv
            )

            # 简单梯度下降（实际应用中使用L-BFGS等）
            step_size = 0.1 / (1 + iteration * 0.1)
            x_new = x - step_size * grad

            # 收敛检查
            if np.linalg.norm(x_new - x) < self.tolerance:
                break

            x = x_new

        # 计算分析协方差（Hessian逆的近似）
        P_a = self.B  # 简化：使用背景协方差

        # 计算最终新息
        final_innovation = np.zeros(self.obs_dim)
        if observations:
            final_innovation = observations[-1] - obs_operator.forward(x)

        return AssimilationResult(
            analysis_state=x,
            analysis_covariance=P_a,
            background_state=x_background,
            observations=observations[-1] if observations else np.zeros(self.obs_dim),
            innovation=final_innovation,
            gain_matrix=None,
            chi_squared=self._compute_cost_gradient(
                x, x_background, observations, obs_times,
                model_func, obs_operator, dt, B_inv, R_inv
            )[0],
            effective_observations=len(observations) * self.obs_dim,
        )

    def _compute_cost_gradient(self, x: np.ndarray, x_b: np.ndarray,
                               observations: List[np.ndarray],
                               obs_times: List[int],
                               model_func: Callable,
                               obs_operator: ObservationOperator,
                               dt: float,
                               B_inv: np.ndarray,
                               R_inv: np.ndarray) -> Tuple[float, np.ndarray]:
        """计算目标函数和梯度"""
        # 背景项
        dx = x - x_b
        J_b = 0.5 * dx.T @ B_inv @ dx
        grad_b = B_inv @ dx

        # 观测项（需要正向积分和伴随积分）
        J_o = 0.0
        grad_o = np.zeros_like(x)

        # 正向积分
        trajectory = [x.copy()]
        x_current = x.copy()
        for t in range(self.window_length):
            x_current = model_func(x_current, dt, {})
            trajectory.append(x_current.copy())

        # 观测项贡献
        for obs, obs_t in zip(observations, obs_times):
            if 0 <= obs_t < len(trajectory):
                x_t = trajectory[obs_t]
                y_pred = obs_operator.forward(x_t)
                d = obs - y_pred
                J_o += 0.5 * d.T @ R_inv @ d

        return J_b + J_o, grad_b + grad_o


class ParticleFilter:
    """
    粒子滤波器

    适用于高度非线性非高斯系统
    """

    def __init__(self, state_dim: int, n_particles: int = 1000):
        self.state_dim = state_dim
        self.n_particles = n_particles

        self.particles = np.zeros((n_particles, state_dim))
        self.weights = np.ones(n_particles) / n_particles

        # 过程噪声
        self.process_noise_std = 0.01

        # 重采样阈值
        self.resample_threshold = n_particles / 2

    def initialize(self, mean: np.ndarray, std: np.ndarray):
        """初始化粒子"""
        for i in range(self.state_dim):
            self.particles[:, i] = np.random.normal(mean[i], std[i], self.n_particles)
        self.weights = np.ones(self.n_particles) / self.n_particles

    def predict(self, model_func: Callable, dt: float, inputs: Dict = None):
        """粒子预测"""
        inputs = inputs or {}

        for i in range(self.n_particles):
            # 模型传播
            self.particles[i] = model_func(self.particles[i], dt, inputs)

            # 添加过程噪声
            self.particles[i] += np.random.normal(0, self.process_noise_std, self.state_dim)

    def update(self, observation: np.ndarray,
               obs_operator: ObservationOperator,
               obs_noise_std: float) -> AssimilationResult:
        """粒子更新"""
        # 计算似然权重
        for i in range(self.n_particles):
            y_pred = obs_operator.forward(self.particles[i])
            residual = observation - y_pred
            likelihood = np.exp(-0.5 * np.sum(residual**2) / obs_noise_std**2)
            self.weights[i] *= likelihood

        # 归一化
        weight_sum = np.sum(self.weights)
        if weight_sum > 0:
            self.weights /= weight_sum
        else:
            self.weights = np.ones(self.n_particles) / self.n_particles

        # 有效样本数
        n_eff = 1.0 / np.sum(self.weights**2)

        # 重采样
        if n_eff < self.resample_threshold:
            self._resample()

        # 计算估计
        mean = np.average(self.particles, weights=self.weights, axis=0)
        # 加权协方差
        diff = self.particles - mean
        cov = np.zeros((self.state_dim, self.state_dim))
        for i in range(self.n_particles):
            cov += self.weights[i] * np.outer(diff[i], diff[i])

        return AssimilationResult(
            analysis_state=mean,
            analysis_covariance=cov,
            background_state=np.mean(self.particles, axis=0),
            observations=observation,
            innovation=observation - obs_operator.forward(mean),
            gain_matrix=None,
            chi_squared=0,
            effective_observations=len(observation),
        )

    def _resample(self):
        """系统重采样"""
        cumsum = np.cumsum(self.weights)
        cumsum[-1] = 1.0

        positions = (np.arange(self.n_particles) + np.random.uniform()) / self.n_particles
        indices = np.searchsorted(cumsum, positions)

        self.particles = self.particles[indices].copy()
        self.weights = np.ones(self.n_particles) / self.n_particles


class DataAssimilator:
    """
    数据同化器

    管理多种同化方法的统一接口
    """

    def __init__(self, state_dim: int, obs_dim: int,
                 method: AssimilationMethod = AssimilationMethod.ENKF):
        self.state_dim = state_dim
        self.obs_dim = obs_dim
        self.method = method

        # 初始化同化器
        if method == AssimilationMethod.ENKF:
            self.assimilator = EnsembleKalmanFilter(state_dim, obs_dim)
        elif method == AssimilationMethod.FOUR_D_VAR:
            self.assimilator = FourDVar(state_dim, obs_dim)
        elif method == AssimilationMethod.PARTICLE_FILTER:
            self.assimilator = ParticleFilter(state_dim)

        # 观测算子
        self.obs_operator = ObservationOperator(state_dim, obs_dim)

        # 历史记录
        self.history: List[AssimilationResult] = []

        # 质量控制参数
        self.qc_params = {
            "innovation_threshold": 3.0,  # 标准差倍数
            "chi_squared_threshold": 50,
        }

    def set_observation_operator(self, H: np.ndarray):
        """设置观测算子"""
        self.obs_operator.set_linear_operator(H)

    def assimilate(self, background: np.ndarray,
                   observations: np.ndarray,
                   model_func: Optional[Callable] = None,
                   dt: float = 1.0,
                   inputs: Dict = None) -> AssimilationResult:
        """
        执行数据同化

        Args:
            background: 背景场（模型预测）
            observations: 观测值
            model_func: 模型函数
            dt: 时间步长
            inputs: 模型输入

        Returns:
            同化结果
        """
        # 观测质量控制
        qc_passed, obs_filtered = self._quality_control(
            observations, self.obs_operator.forward(background)
        )

        if not qc_passed:
            # 质量控制失败，返回背景场
            return AssimilationResult(
                analysis_state=background,
                analysis_covariance=np.eye(self.state_dim) * 0.01,
                background_state=background,
                observations=observations,
                innovation=observations - self.obs_operator.forward(background),
                gain_matrix=None,
                chi_squared=float('inf'),
                effective_observations=0,
            )

        # 执行同化
        if self.method == AssimilationMethod.ENKF:
            result = self.assimilator.analysis(obs_filtered, self.obs_operator)

        elif self.method == AssimilationMethod.FOUR_D_VAR:
            result = self.assimilator.minimize(
                background, [obs_filtered], [0],
                model_func, self.obs_operator, dt
            )

        elif self.method == AssimilationMethod.PARTICLE_FILTER:
            result = self.assimilator.update(obs_filtered, self.obs_operator, 0.1)

        # 记录历史
        self.history.append(result)

        return result

    def _quality_control(self, observations: np.ndarray,
                         background_obs: np.ndarray) -> Tuple[bool, np.ndarray]:
        """观测质量控制"""
        innovation = observations - background_obs

        # 检查新息是否过大
        threshold = self.qc_params["innovation_threshold"]
        std = np.std(innovation) if len(innovation) > 1 else 1.0

        outliers = np.abs(innovation) > threshold * std
        if np.all(outliers):
            return False, observations

        # 剔除异常观测
        obs_filtered = observations.copy()
        obs_filtered[outliers] = background_obs[outliers]

        return True, obs_filtered

    def get_analysis_increment(self) -> Optional[np.ndarray]:
        """获取分析增量"""
        if not self.history:
            return None
        return self.history[-1].get_correction()

    def get_statistics(self) -> Dict[str, Any]:
        """获取同化统计"""
        if not self.history:
            return {}

        innovations = [r.innovation for r in self.history]
        chi2_values = [r.chi_squared for r in self.history]

        return {
            "total_cycles": len(self.history),
            "mean_innovation": np.mean([np.mean(np.abs(i)) for i in innovations]),
            "mean_chi_squared": np.mean(chi2_values),
            "method": self.method.value,
        }
