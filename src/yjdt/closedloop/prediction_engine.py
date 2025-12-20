# -*- coding: utf-8 -*-
"""
预测引擎 - 多时间尺度预测
Prediction Engine - Multi-scale Forecasting

功能：
- 短期预测（秒-分钟）：控制优化
- 中期预测（小时-天）：调度决策
- 长期预测（周-月）：维护规划
- 不确定性量化
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
from enum import Enum


class PredictionHorizon(Enum):
    """预测时域"""
    IMMEDIATE = "immediate"     # 即时 (<1分钟)
    SHORT_TERM = "short_term"   # 短期 (1分钟-1小时)
    MEDIUM_TERM = "medium_term" # 中期 (1小时-1天)
    LONG_TERM = "long_term"     # 长期 (1天-1月)


@dataclass
class PredictionResult:
    """预测结果"""
    variable: str
    horizon: PredictionHorizon
    predicted_values: np.ndarray
    timestamps: List[datetime]
    confidence_lower: np.ndarray        # 置信下限
    confidence_upper: np.ndarray        # 置信上限
    confidence_level: float = 0.95
    model_used: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class UncertaintyQuantification:
    """不确定性量化"""
    variable: str
    mean: float
    std: float
    percentiles: Dict[int, float]       # 5, 25, 50, 75, 95
    sources: Dict[str, float]           # 不确定性来源分解
    sensitivity: Dict[str, float]       # 敏感性分析


class ShortTermPredictor:
    """
    短期预测器

    用于控制优化的秒级-分钟级预测
    """

    def __init__(self):
        self.model_params = {
            "ar_order": 5,              # AR模型阶数
            "ma_order": 2,              # MA模型阶数
            "state_dim": 10,            # 状态空间维度
        }

        self.history: Dict[str, List[float]] = {}
        self.fitted_models: Dict[str, Any] = {}

    def add_observation(self, variable: str, value: float, timestamp: datetime = None):
        """添加观测值"""
        if variable not in self.history:
            self.history[variable] = []
        self.history[variable].append(value)

        # 保留最近1000个点
        if len(self.history[variable]) > 1000:
            self.history[variable] = self.history[variable][-1000:]

    def predict(self, variable: str, horizon_steps: int,
                dt: float = 1.0) -> PredictionResult:
        """
        执行短期预测

        Args:
            variable: 预测变量
            horizon_steps: 预测步数
            dt: 时间步长（秒）
        """
        if variable not in self.history or len(self.history[variable]) < 10:
            # 数据不足，返回持续预测
            last_value = self.history.get(variable, [0])[-1] if variable in self.history else 0
            predictions = np.full(horizon_steps, last_value)
            lower = predictions - np.abs(predictions) * 0.1
            upper = predictions + np.abs(predictions) * 0.1
        else:
            # AR模型预测
            predictions, lower, upper = self._ar_predict(
                self.history[variable], horizon_steps
            )

        # 生成时间戳
        now = datetime.now()
        timestamps = [now + timedelta(seconds=i*dt) for i in range(horizon_steps)]

        return PredictionResult(
            variable=variable,
            horizon=PredictionHorizon.SHORT_TERM,
            predicted_values=predictions,
            timestamps=timestamps,
            confidence_lower=lower,
            confidence_upper=upper,
            model_used="AR",
        )

    def _ar_predict(self, data: List[float], steps: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """AR模型预测"""
        data = np.array(data)
        n = len(data)
        order = min(self.model_params["ar_order"], n - 1)

        # 估计AR系数（Yule-Walker方程简化）
        if order > 0:
            # 自相关
            autocorr = np.correlate(data - np.mean(data), data - np.mean(data), mode='full')
            autocorr = autocorr[n-1:n+order] / autocorr[n-1]

            # 简化的系数估计
            coeffs = autocorr[1:order+1] * 0.8  # 衰减以保证稳定性
        else:
            coeffs = np.array([0.9])

        # 预测
        predictions = np.zeros(steps)
        buffer = data[-order:].copy() if order > 0 else np.array([data[-1]])

        for i in range(steps):
            pred = np.dot(coeffs[:len(buffer)], buffer[::-1][:len(coeffs)])
            predictions[i] = pred
            buffer = np.roll(buffer, -1)
            buffer[-1] = pred

        # 置信区间（基于历史标准差）
        std = np.std(data)
        confidence_factor = 1.96  # 95%置信
        lower = predictions - confidence_factor * std * np.sqrt(np.arange(1, steps+1) * 0.1)
        upper = predictions + confidence_factor * std * np.sqrt(np.arange(1, steps+1) * 0.1)

        return predictions, lower, upper


class MediumTermPredictor:
    """
    中期预测器

    用于调度决策的小时-天级预测
    """

    def __init__(self):
        self.inflow_patterns: Dict[str, np.ndarray] = {}
        self.load_patterns: Dict[str, np.ndarray] = {}

        # 初始化典型日模式
        self._init_patterns()

    def _init_patterns(self):
        """初始化典型模式"""
        # 入库流量日模式（雅江冰川融水特征）
        hours = np.arange(24)
        # 下午融雪高峰
        self.inflow_patterns["summer"] = 200 + 50 * np.sin((hours - 15) * np.pi / 12)
        self.inflow_patterns["winter"] = 100 + 10 * np.sin((hours - 12) * np.pi / 12)

        # 负荷日模式
        self.load_patterns["weekday"] = 700 + 200 * np.sin((hours - 12) * np.pi / 12)
        self.load_patterns["weekend"] = 600 + 150 * np.sin((hours - 13) * np.pi / 12)

    def predict_inflow(self, hours_ahead: int,
                       season: str = "summer") -> PredictionResult:
        """预测来水"""
        pattern = self.inflow_patterns.get(season, self.inflow_patterns["summer"])

        now = datetime.now()
        predictions = []
        timestamps = []

        for h in range(hours_ahead):
            future_time = now + timedelta(hours=h)
            hour_of_day = future_time.hour
            pred = pattern[hour_of_day]

            # 添加随机变异
            pred *= (1 + np.random.normal(0, 0.1))
            predictions.append(pred)
            timestamps.append(future_time)

        predictions = np.array(predictions)
        std = predictions * 0.15

        return PredictionResult(
            variable="inflow",
            horizon=PredictionHorizon.MEDIUM_TERM,
            predicted_values=predictions,
            timestamps=timestamps,
            confidence_lower=predictions - 1.96 * std,
            confidence_upper=predictions + 1.96 * std,
            model_used="pattern_based",
        )

    def predict_load_demand(self, hours_ahead: int,
                            day_type: str = "weekday") -> PredictionResult:
        """预测负荷需求"""
        pattern = self.load_patterns.get(day_type, self.load_patterns["weekday"])

        now = datetime.now()
        predictions = []
        timestamps = []

        for h in range(hours_ahead):
            future_time = now + timedelta(hours=h)
            hour_of_day = future_time.hour
            pred = pattern[hour_of_day]
            predictions.append(pred)
            timestamps.append(future_time)

        predictions = np.array(predictions)
        std = predictions * 0.1

        return PredictionResult(
            variable="load_demand",
            horizon=PredictionHorizon.MEDIUM_TERM,
            predicted_values=predictions,
            timestamps=timestamps,
            confidence_lower=predictions - 1.96 * std,
            confidence_upper=predictions + 1.96 * std,
            model_used="pattern_based",
        )


class LongTermPredictor:
    """
    长期预测器

    用于维护规划的周-月级预测
    """

    def __init__(self):
        self.degradation_models: Dict[str, Callable] = {}
        self.component_age: Dict[str, float] = {}  # 运行小时数

        # 初始化劣化模型
        self._init_degradation_models()

    def _init_degradation_models(self):
        """初始化劣化模型"""
        # 轴承寿命模型（指数衰减）
        self.degradation_models["bearing"] = lambda t: 100 * np.exp(-t / 50000)

        # 定子绝缘老化
        self.degradation_models["stator_insulation"] = lambda t: 100 - 0.001 * t

        # 转轮磨损
        self.degradation_models["runner"] = lambda t: 100 - 0.0005 * t

    def predict_remaining_life(self, component: str,
                               current_condition: float,
                               operating_hours: float) -> Dict[str, Any]:
        """预测剩余寿命"""
        if component not in self.degradation_models:
            return {"error": f"Unknown component: {component}"}

        model = self.degradation_models[component]

        # 当前状态校准
        calibration_factor = current_condition / model(operating_hours) if model(operating_hours) > 0 else 1

        # 预测未来状态
        future_hours = np.arange(0, 50000, 1000)
        future_condition = model(operating_hours + future_hours) * calibration_factor

        # 找到失效点（条件<60%）
        failure_threshold = 60
        failure_idx = np.where(future_condition < failure_threshold)[0]

        if len(failure_idx) > 0:
            remaining_hours = future_hours[failure_idx[0]]
        else:
            remaining_hours = 50000

        return {
            "component": component,
            "current_condition": current_condition,
            "operating_hours": operating_hours,
            "remaining_life_hours": remaining_hours,
            "failure_probability_1year": 1 - np.exp(-8760 / remaining_hours) if remaining_hours > 0 else 1.0,
            "recommended_inspection": operating_hours + remaining_hours * 0.7,
            "recommended_replacement": operating_hours + remaining_hours * 0.9,
        }

    def predict_maintenance_schedule(self, components: List[Dict]) -> List[Dict]:
        """预测维护计划"""
        schedule = []

        for comp in components:
            prediction = self.predict_remaining_life(
                comp["name"],
                comp.get("condition", 90),
                comp.get("hours", 10000)
            )

            if "remaining_life_hours" in prediction:
                schedule.append({
                    "component": comp["name"],
                    "action": "inspection",
                    "due_hours": prediction["recommended_inspection"],
                    "priority": "high" if prediction["remaining_life_hours"] < 5000 else "normal",
                })

        # 按时间排序
        schedule.sort(key=lambda x: x["due_hours"])

        return schedule


class PredictionEngine:
    """
    预测引擎

    统一管理多时间尺度预测
    """

    def __init__(self):
        self.short_term = ShortTermPredictor()
        self.medium_term = MediumTermPredictor()
        self.long_term = LongTermPredictor()

        # 预测性能监控
        self.metrics = {
            "mae": {},      # 平均绝对误差
            "rmse": {},     # 均方根误差
            "mape": {},     # 平均绝对百分比误差
        }

    def update(self, observations: Dict[str, float]):
        """更新观测值"""
        for var, value in observations.items():
            self.short_term.add_observation(var, value)

    def predict_short_term(self, variable: str, horizon_seconds: float,
                           dt: float = 1.0) -> PredictionResult:
        """短期预测"""
        steps = int(horizon_seconds / dt)
        return self.short_term.predict(variable, steps, dt)

    def predict_medium_term(self, variable: str, horizon_hours: int) -> PredictionResult:
        """中期预测"""
        if variable == "inflow":
            return self.medium_term.predict_inflow(horizon_hours)
        elif variable == "load":
            return self.medium_term.predict_load_demand(horizon_hours)
        else:
            # 通用预测
            return PredictionResult(
                variable=variable,
                horizon=PredictionHorizon.MEDIUM_TERM,
                predicted_values=np.zeros(horizon_hours),
                timestamps=[datetime.now() + timedelta(hours=i) for i in range(horizon_hours)],
                confidence_lower=np.zeros(horizon_hours),
                confidence_upper=np.zeros(horizon_hours),
            )

    def predict_long_term(self, component: str, condition: float,
                          hours: float) -> Dict[str, Any]:
        """长期预测（寿命预测）"""
        return self.long_term.predict_remaining_life(component, condition, hours)

    def quantify_uncertainty(self, variable: str,
                             predictions: np.ndarray) -> UncertaintyQuantification:
        """量化预测不确定性"""
        mean = np.mean(predictions)
        std = np.std(predictions)

        percentiles = {
            5: np.percentile(predictions, 5),
            25: np.percentile(predictions, 25),
            50: np.percentile(predictions, 50),
            75: np.percentile(predictions, 75),
            95: np.percentile(predictions, 95),
        }

        # 不确定性来源分解（简化）
        sources = {
            "model_uncertainty": std * 0.4,
            "parameter_uncertainty": std * 0.3,
            "input_uncertainty": std * 0.2,
            "measurement_uncertainty": std * 0.1,
        }

        return UncertaintyQuantification(
            variable=variable,
            mean=mean,
            std=std,
            percentiles=percentiles,
            sources=sources,
            sensitivity={},
        )

    def evaluate_accuracy(self, variable: str, predicted: float,
                          actual: float):
        """评估预测精度"""
        error = abs(predicted - actual)
        relative_error = error / abs(actual) if actual != 0 else 0

        if variable not in self.metrics["mae"]:
            self.metrics["mae"][variable] = []
            self.metrics["mape"][variable] = []

        self.metrics["mae"][variable].append(error)
        self.metrics["mape"][variable].append(relative_error * 100)

    def get_accuracy_report(self) -> Dict[str, Any]:
        """获取精度报告"""
        report = {}

        for variable in self.metrics["mae"]:
            mae_values = self.metrics["mae"][variable]
            mape_values = self.metrics["mape"][variable]

            if mae_values:
                report[variable] = {
                    "mae": np.mean(mae_values),
                    "mape": np.mean(mape_values),
                    "samples": len(mae_values),
                }

        return report
