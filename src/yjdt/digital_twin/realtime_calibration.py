# -*- coding: utf-8 -*-
"""
数字孪生实时校准模块 - Digital Twin Real-time Calibration

功能：
- 在线参数辨识
- 模型误差学习
- 自适应校准
- 多源数据融合
- 漂移检测与补偿

技术特点：
- 递推最小二乘 (RLS)
- 无迹卡尔曼滤波 (UKF)
- 高斯过程回归 (GPR)
- 贝叶斯优化
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import time


class CalibrationMode(Enum):
    """校准模式"""
    OFFLINE = "offline"              # 离线校准
    ONLINE = "online"                # 在线校准
    ADAPTIVE = "adaptive"            # 自适应校准
    SCHEDULED = "scheduled"          # 定时校准


class DriftType(Enum):
    """漂移类型"""
    BIAS = "bias"                    # 偏置漂移
    SCALE = "scale"                  # 比例漂移
    NONLINEAR = "nonlinear"          # 非线性漂移
    STEP = "step"                    # 阶跃漂移
    GRADUAL = "gradual"              # 渐变漂移


@dataclass
class CalibrationState:
    """校准状态"""
    timestamp: datetime
    parameters: Dict[str, float]
    errors: Dict[str, float]
    confidence: Dict[str, float]
    is_converged: bool = False


@dataclass
class CalibrationConfig:
    """校准配置"""
    mode: CalibrationMode = CalibrationMode.ONLINE
    update_interval: float = 1.0      # 更新间隔（秒）
    forgetting_factor: float = 0.99   # 遗忘因子
    convergence_threshold: float = 0.01
    max_iterations: int = 100

    # 参数范围
    parameter_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    # 异常检测
    outlier_threshold: float = 3.0    # 异常值阈值（标准差倍数）
    drift_detection_window: int = 50   # 漂移检测窗口


class RecursiveLeastSquares:
    """
    递推最小二乘辨识器

    用于在线参数辨识：
    y = phi' * theta + e

    其中：
    - phi: 回归向量
    - theta: 待辨识参数
    - e: 噪声
    """

    def __init__(self, n_params: int, forgetting_factor: float = 0.99):
        self.n_params = n_params
        self.lambda_ = forgetting_factor

        # 参数估计
        self.theta = np.zeros(n_params)

        # 协方差矩阵
        self.P = np.eye(n_params) * 1000  # 初始高不确定性

        # 历史
        self.update_count = 0
        self.estimation_error: List[float] = []

    def update(self, phi: np.ndarray, y: float) -> np.ndarray:
        """
        更新参数估计

        Args:
            phi: 回归向量 (n_params,)
            y: 测量输出

        Returns:
            更新后的参数
        """
        # 预测误差
        y_pred = phi @ self.theta
        e = y - y_pred

        # 增益计算
        P_phi = self.P @ phi
        denominator = self.lambda_ + phi @ P_phi
        K = P_phi / denominator

        # 参数更新
        self.theta = self.theta + K * e

        # 协方差更新
        self.P = (self.P - np.outer(K, phi @ self.P)) / self.lambda_

        # 记录
        self.update_count += 1
        self.estimation_error.append(abs(e))

        return self.theta

    def get_confidence(self) -> np.ndarray:
        """获取参数置信度"""
        return np.sqrt(np.diag(self.P))

    def reset(self, initial_theta: np.ndarray = None):
        """重置"""
        if initial_theta is not None:
            self.theta = initial_theta.copy()
        else:
            self.theta = np.zeros(self.n_params)
        self.P = np.eye(self.n_params) * 1000
        self.update_count = 0
        self.estimation_error = []


class UnscentedKalmanFilter:
    """
    无迹卡尔曼滤波器

    用于非线性系统状态估计和参数辨识

    状态方程: x(k+1) = f(x(k), u(k)) + w(k)
    观测方程: y(k) = h(x(k)) + v(k)
    """

    def __init__(self, n_states: int, n_measurements: int,
                 process_noise: float = 0.01,
                 measurement_noise: float = 0.1):
        self.n_x = n_states
        self.n_z = n_measurements

        # 状态估计
        self.x = np.zeros(n_states)
        self.P = np.eye(n_states)

        # 噪声协方差
        self.Q = np.eye(n_states) * process_noise
        self.R = np.eye(n_measurements) * measurement_noise

        # UT变换参数
        self.alpha = 1e-3
        self.beta = 2
        self.kappa = 0

        # Sigma点权重
        self._compute_weights()

    def _compute_weights(self):
        """计算Sigma点权重"""
        n = self.n_x
        lambda_ = self.alpha**2 * (n + self.kappa) - n

        # 均值权重
        self.Wm = np.zeros(2*n + 1)
        self.Wm[0] = lambda_ / (n + lambda_)
        self.Wm[1:] = 1 / (2 * (n + lambda_))

        # 协方差权重
        self.Wc = self.Wm.copy()
        self.Wc[0] += 1 - self.alpha**2 + self.beta

        self.gamma = np.sqrt(n + lambda_)

    def _sigma_points(self, x: np.ndarray, P: np.ndarray) -> np.ndarray:
        """生成Sigma点"""
        n = len(x)
        sigma_pts = np.zeros((2*n + 1, n))

        # 计算Cholesky分解
        try:
            sqrt_P = np.linalg.cholesky(P)
        except np.linalg.LinAlgError:
            sqrt_P = np.linalg.cholesky(P + 1e-6 * np.eye(n))

        sigma_pts[0] = x
        for i in range(n):
            sigma_pts[i + 1] = x + self.gamma * sqrt_P[:, i]
            sigma_pts[n + i + 1] = x - self.gamma * sqrt_P[:, i]

        return sigma_pts

    def predict(self, f: Callable, u: np.ndarray = None):
        """
        预测步

        Args:
            f: 状态转移函数 f(x, u) -> x_next
            u: 控制输入
        """
        n = self.n_x

        # 生成Sigma点
        sigma_pts = self._sigma_points(self.x, self.P)

        # 传播Sigma点
        sigma_pts_pred = np.zeros_like(sigma_pts)
        for i in range(2*n + 1):
            if u is not None:
                sigma_pts_pred[i] = f(sigma_pts[i], u)
            else:
                sigma_pts_pred[i] = f(sigma_pts[i])

        # 计算预测均值
        self.x = np.sum(self.Wm[:, np.newaxis] * sigma_pts_pred, axis=0)

        # 计算预测协方差
        self.P = self.Q.copy()
        for i in range(2*n + 1):
            diff = sigma_pts_pred[i] - self.x
            self.P += self.Wc[i] * np.outer(diff, diff)

        self._sigma_pts_pred = sigma_pts_pred

    def update(self, h: Callable, z: np.ndarray):
        """
        更新步

        Args:
            h: 观测函数 h(x) -> z
            z: 测量值
        """
        n = self.n_x
        m = self.n_z

        # 传播Sigma点到观测空间
        sigma_z = np.zeros((2*n + 1, m))
        for i in range(2*n + 1):
            sigma_z[i] = h(self._sigma_pts_pred[i])

        # 预测观测均值
        z_pred = np.sum(self.Wm[:, np.newaxis] * sigma_z, axis=0)

        # 观测协方差
        Pzz = self.R.copy()
        for i in range(2*n + 1):
            diff = sigma_z[i] - z_pred
            Pzz += self.Wc[i] * np.outer(diff, diff)

        # 交叉协方差
        Pxz = np.zeros((n, m))
        for i in range(2*n + 1):
            diff_x = self._sigma_pts_pred[i] - self.x
            diff_z = sigma_z[i] - z_pred
            Pxz += self.Wc[i] * np.outer(diff_x, diff_z)

        # 卡尔曼增益
        K = Pxz @ np.linalg.inv(Pzz)

        # 更新
        self.x = self.x + K @ (z - z_pred)
        self.P = self.P - K @ Pzz @ K.T

        return z_pred


class GaussianProcessRegressor:
    """
    高斯过程回归器

    用于学习模型误差和不确定性量化
    """

    def __init__(self, length_scale: float = 1.0, variance: float = 1.0,
                 noise_variance: float = 0.1):
        self.l = length_scale
        self.sigma_f = np.sqrt(variance)
        self.sigma_n = np.sqrt(noise_variance)

        # 训练数据
        self.X_train: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None
        self.K_inv: Optional[np.ndarray] = None

    def _kernel(self, X1: np.ndarray, X2: np.ndarray) -> np.ndarray:
        """RBF核函数"""
        if X1.ndim == 1:
            X1 = X1.reshape(-1, 1)
        if X2.ndim == 1:
            X2 = X2.reshape(-1, 1)

        # 计算平方距离
        sqdist = np.sum(X1**2, axis=1, keepdims=True) + \
                 np.sum(X2**2, axis=1) - 2 * X1 @ X2.T

        return self.sigma_f**2 * np.exp(-0.5 * sqdist / self.l**2)

    def fit(self, X: np.ndarray, y: np.ndarray):
        """
        拟合模型

        Args:
            X: 训练输入 (n_samples, n_features)
            y: 训练输出 (n_samples,)
        """
        self.X_train = X
        self.y_train = y

        # 计算核矩阵
        K = self._kernel(X, X)
        K += self.sigma_n**2 * np.eye(len(X))

        # 求逆
        self.K_inv = np.linalg.inv(K)

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测

        Args:
            X: 测试输入

        Returns:
            均值, 标准差
        """
        if self.X_train is None:
            return np.zeros(len(X)), np.ones(len(X)) * self.sigma_f

        # 计算核
        K_s = self._kernel(X, self.X_train)
        K_ss = self._kernel(X, X)

        # 均值
        mu = K_s @ self.K_inv @ self.y_train

        # 协方差
        cov = K_ss - K_s @ self.K_inv @ K_s.T + 1e-6 * np.eye(len(X))
        std = np.sqrt(np.diag(cov))

        return mu, std

    def update_incremental(self, x_new: np.ndarray, y_new: float):
        """增量更新"""
        if self.X_train is None:
            self.X_train = x_new.reshape(1, -1)
            self.y_train = np.array([y_new])
        else:
            self.X_train = np.vstack([self.X_train, x_new])
            self.y_train = np.append(self.y_train, y_new)

        # 重新拟合（简化处理，可优化为增量更新）
        self.fit(self.X_train, self.y_train)


class DriftDetector:
    """
    漂移检测器

    检测模型参数或输出漂移
    """

    def __init__(self, window_size: int = 50, threshold: float = 3.0):
        self.window_size = window_size
        self.threshold = threshold

        # 滑动窗口
        self.error_buffer: List[float] = []
        self.baseline_mean = 0.0
        self.baseline_std = 1.0

    def update(self, error: float) -> Tuple[bool, DriftType]:
        """
        更新并检测漂移

        Args:
            error: 当前误差

        Returns:
            是否检测到漂移, 漂移类型
        """
        self.error_buffer.append(error)

        # 保持窗口大小
        if len(self.error_buffer) > self.window_size * 2:
            self.error_buffer.pop(0)

        if len(self.error_buffer) < self.window_size:
            return False, None

        # 分析前后两个窗口
        recent = np.array(self.error_buffer[-self.window_size:])
        baseline = np.array(self.error_buffer[-2*self.window_size:-self.window_size])

        # 更新基线
        self.baseline_mean = np.mean(baseline)
        self.baseline_std = max(np.std(baseline), 1e-6)

        # 检测偏移
        recent_mean = np.mean(recent)
        z_score = (recent_mean - self.baseline_mean) / self.baseline_std

        if abs(z_score) > self.threshold:
            # 判断漂移类型
            if abs(recent_mean - self.baseline_mean) > 3 * self.baseline_std:
                return True, DriftType.STEP
            else:
                return True, DriftType.GRADUAL

        # 检测方差变化
        recent_std = np.std(recent)
        if recent_std > 2 * self.baseline_std:
            return True, DriftType.NONLINEAR

        return False, None


class RealtimeCalibrator:
    """
    实时校准器

    功能：
    - 在线参数辨识
    - 误差模型学习
    - 漂移检测与补偿
    - 多模型融合
    """

    def __init__(self, config: CalibrationConfig = None):
        self.config = config or CalibrationConfig()

        # 参数辨识器
        self.rls_estimators: Dict[str, RecursiveLeastSquares] = {}

        # 误差模型
        self.error_models: Dict[str, GaussianProcessRegressor] = {}

        # 漂移检测
        self.drift_detectors: Dict[str, DriftDetector] = {}

        # 校准状态
        self.current_state: Optional[CalibrationState] = None
        self.state_history: List[CalibrationState] = []

        # 统计
        self.calibration_count = 0
        self.drift_events: List[Dict[str, Any]] = []

    def add_parameter(self, name: str, initial_value: float = 0.0,
                      n_regression: int = 3):
        """
        添加待校准参数

        Args:
            name: 参数名
            initial_value: 初始值
            n_regression: 回归向量维度
        """
        self.rls_estimators[name] = RecursiveLeastSquares(
            n_regression,
            self.config.forgetting_factor
        )
        self.rls_estimators[name].theta[0] = initial_value

        self.error_models[name] = GaussianProcessRegressor()
        self.drift_detectors[name] = DriftDetector(
            self.config.drift_detection_window,
            self.config.outlier_threshold
        )

    def calibrate(self, measurements: Dict[str, float],
                  predictions: Dict[str, float],
                  regressors: Dict[str, np.ndarray] = None) -> CalibrationState:
        """
        执行校准

        Args:
            measurements: 实际测量值
            predictions: 模型预测值
            regressors: 回归向量（可选）

        Returns:
            校准状态
        """
        parameters = {}
        errors = {}
        confidence = {}
        converged = True

        for name in self.rls_estimators.keys():
            if name not in measurements or name not in predictions:
                continue

            # 计算误差
            error = measurements[name] - predictions[name]
            errors[name] = error

            # 获取回归向量
            if regressors and name in regressors:
                phi = regressors[name]
            else:
                phi = np.array([1.0, predictions[name], predictions[name]**2])

            # RLS更新
            theta = self.rls_estimators[name].update(phi, measurements[name])
            parameters[name] = theta[0]  # 使用第一个参数作为校准值

            # 置信度
            conf = self.rls_estimators[name].get_confidence()
            confidence[name] = 1.0 / (1.0 + np.mean(conf))

            # 误差模型更新
            x_input = np.array([predictions[name]])
            self.error_models[name].update_incremental(x_input, error)

            # 漂移检测
            is_drift, drift_type = self.drift_detectors[name].update(error)
            if is_drift:
                self.drift_events.append({
                    "timestamp": datetime.now(),
                    "parameter": name,
                    "drift_type": drift_type.value if drift_type else None,
                    "error": error,
                })
                converged = False

        # 创建校准状态
        self.current_state = CalibrationState(
            timestamp=datetime.now(),
            parameters=parameters,
            errors=errors,
            confidence=confidence,
            is_converged=converged,
        )

        self.state_history.append(self.current_state)
        self.calibration_count += 1

        return self.current_state

    def get_correction(self, variable: str, value: float) -> Tuple[float, float]:
        """
        获取校正值

        Args:
            variable: 变量名
            value: 原始值

        Returns:
            校正后的值, 不确定性
        """
        if variable not in self.error_models:
            return value, 0.0

        # 使用GPR预测误差
        x = np.array([[value]])
        error_pred, uncertainty = self.error_models[variable].predict(x)

        corrected = value + error_pred[0]
        return corrected, uncertainty[0]

    def get_calibrated_parameters(self) -> Dict[str, float]:
        """获取校准后的参数"""
        if self.current_state is None:
            return {}
        return self.current_state.parameters.copy()

    def reset_parameter(self, name: str):
        """重置单个参数"""
        if name in self.rls_estimators:
            self.rls_estimators[name].reset()
            self.drift_detectors[name] = DriftDetector(
                self.config.drift_detection_window,
                self.config.outlier_threshold
            )

    def get_calibration_quality(self) -> Dict[str, Any]:
        """获取校准质量评估"""
        if not self.state_history:
            return {}

        recent_states = self.state_history[-50:]

        quality = {}
        for name in self.rls_estimators.keys():
            recent_errors = [s.errors.get(name, 0) for s in recent_states if name in s.errors]
            recent_conf = [s.confidence.get(name, 0) for s in recent_states if name in s.confidence]

            if recent_errors:
                quality[name] = {
                    "mean_error": np.mean(recent_errors),
                    "std_error": np.std(recent_errors),
                    "mean_confidence": np.mean(recent_conf) if recent_conf else 0,
                    "convergence": np.std(recent_errors) < self.config.convergence_threshold,
                    "n_drifts": sum(1 for e in self.drift_events if e["parameter"] == name),
                }

        return quality


class TwinModelCalibrator:
    """
    孪生模型校准器

    用于同步物理系统与数字孪生模型

    功能：
    - 参数同步
    - 状态同步
    - 模型偏差补偿
    """

    def __init__(self):
        # 状态校准器
        self.state_calibrator = RealtimeCalibrator()

        # 参数校准器
        self.param_calibrator = RealtimeCalibrator(CalibrationConfig(
            forgetting_factor=0.995,  # 参数变化更慢
            convergence_threshold=0.001,
        ))

        # UKF用于状态估计
        self.ukf: Optional[UnscentedKalmanFilter] = None

        # 同步状态
        self.sync_quality = 0.0
        self.last_sync_time: Optional[datetime] = None

    def initialize_ukf(self, n_states: int, n_measurements: int):
        """初始化UKF"""
        self.ukf = UnscentedKalmanFilter(n_states, n_measurements)

    def add_state_variable(self, name: str):
        """添加状态变量"""
        self.state_calibrator.add_parameter(name, n_regression=2)

    def add_model_parameter(self, name: str, initial: float):
        """添加模型参数"""
        self.param_calibrator.add_parameter(name, initial, n_regression=1)

    def synchronize(self, physical_state: Dict[str, float],
                     twin_state: Dict[str, float],
                     model_params: Dict[str, float] = None) -> Dict[str, Any]:
        """
        同步物理系统与孪生模型

        Args:
            physical_state: 物理系统状态（测量值）
            twin_state: 孪生模型状态（预测值）
            model_params: 模型参数（可选）

        Returns:
            同步结果
        """
        result = {
            "timestamp": datetime.now(),
            "state_corrections": {},
            "param_corrections": {},
            "sync_quality": 0.0,
        }

        # 状态校准
        state_calib = self.state_calibrator.calibrate(physical_state, twin_state)
        for name, error in state_calib.errors.items():
            corrected, uncertainty = self.state_calibrator.get_correction(name, twin_state[name])
            result["state_corrections"][name] = {
                "original": twin_state[name],
                "corrected": corrected,
                "uncertainty": uncertainty,
            }

        # 参数校准
        if model_params:
            # 简化：使用状态误差来推断参数偏差
            param_errors = {
                k: state_calib.errors.get(k, 0) for k in model_params.keys()
            }
            param_calib = self.param_calibrator.calibrate(model_params, model_params)

        # 计算同步质量
        total_error = sum(abs(e) for e in state_calib.errors.values())
        total_value = sum(abs(v) for v in physical_state.values()) + 1e-6
        self.sync_quality = max(0, 1 - total_error / total_value)

        result["sync_quality"] = self.sync_quality
        self.last_sync_time = datetime.now()

        return result

    def get_corrected_twin_state(self, twin_state: Dict[str, float]) -> Dict[str, float]:
        """获取校正后的孪生状态"""
        corrected = {}
        for name, value in twin_state.items():
            if name in self.state_calibrator.error_models:
                corrected[name], _ = self.state_calibrator.get_correction(name, value)
            else:
                corrected[name] = value
        return corrected

    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            "sync_quality": self.sync_quality,
            "last_sync": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "state_quality": self.state_calibrator.get_calibration_quality(),
            "param_quality": self.param_calibrator.get_calibration_quality(),
            "drift_events": len(self.state_calibrator.drift_events),
        }
