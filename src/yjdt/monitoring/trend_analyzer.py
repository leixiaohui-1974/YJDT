# -*- coding: utf-8 -*-
"""
趋势分析与预警系统 - 智能预测与异常检测
Trend Analysis and Early Warning System

功能：
- 多尺度趋势分析（秒/分/时/日）
- 智能异常检测（统计/机器学习）
- 预测性预警（趋势外推）
- 关联分析（多参数协同）
- 模式识别（周期/突变/漂移）
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import deque
import warnings


class TrendDirection(Enum):
    """趋势方向"""
    RISING = "rising"           # 上升
    FALLING = "falling"         # 下降
    STABLE = "stable"           # 稳定
    OSCILLATING = "oscillating" # 振荡
    UNKNOWN = "unknown"         # 未知


class AnomalyType(Enum):
    """异常类型"""
    SPIKE = "spike"             # 尖峰
    DROPOUT = "dropout"         # 跌落
    DRIFT = "drift"             # 漂移
    SHIFT = "shift"             # 阶跃
    NOISE = "noise"             # 噪声增大
    STUCK = "stuck"             # 卡死
    OSCILLATION = "oscillation" # 振荡
    CORRELATION = "correlation" # 相关性异常


@dataclass
class TrendAlert:
    """趋势预警"""
    alert_id: str
    source_id: str
    source_name: str
    direction: TrendDirection
    rate: float                             # 变化率
    predicted_value: float                  # 预测值
    predicted_time: datetime                # 预测时间
    limit_type: str                         # 限值类型
    limit_value: float                      # 限值
    confidence: float                       # 置信度
    message: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PredictiveAlert:
    """预测性预警"""
    alert_id: str
    source_id: str
    source_name: str
    current_value: float
    predicted_value: float
    prediction_horizon: float               # 预测时长(秒)
    limit_value: float
    time_to_limit: float                    # 到达限值时间(秒)
    confidence: float
    message: str
    recommended_action: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AnomalyScore:
    """异常评分"""
    source_id: str
    anomaly_type: AnomalyType
    score: float                            # 0-1，越大越异常
    severity: str                           # low/medium/high/critical
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class TrendAnalyzer:
    """
    趋势分析器

    功能：
    - 实时趋势检测与方向判断
    - 多时间尺度分析
    - 预测性预警生成
    - 异常模式检测
    - 关联性分析
    """

    def __init__(self, history_length: int = 3600):
        self.history_length = history_length
        self.data_history: Dict[str, deque] = {}
        self.trend_cache: Dict[str, Dict[str, Any]] = {}
        self.anomaly_baseline: Dict[str, Dict[str, float]] = {}
        self.alert_counter = 0

        # 分析参数
        self.params = {
            "min_samples": 10,              # 最小样本数
            "trend_window": 60,             # 趋势窗口(秒)
            "prediction_horizon": 300,      # 预测时长(秒)
            "anomaly_threshold": 3.0,       # 异常阈值(标准差倍数)
            "correlation_window": 300,      # 相关性窗口(秒)
            "oscillation_threshold": 0.3,   # 振荡阈值
        }

    def add_data(self, source_id: str, value: float,
                 timestamp: Optional[datetime] = None):
        """添加数据点"""
        timestamp = timestamp or datetime.now()

        if source_id not in self.data_history:
            self.data_history[source_id] = deque(maxlen=self.history_length)

        self.data_history[source_id].append({
            "timestamp": timestamp,
            "value": value
        })

    def analyze_trend(self, source_id: str,
                      window: Optional[float] = None) -> Dict[str, Any]:
        """
        分析趋势

        Returns:
            包含趋势方向、变化率、预测值等信息
        """
        if source_id not in self.data_history:
            return {"direction": TrendDirection.UNKNOWN, "error": "No data"}

        data = list(self.data_history[source_id])
        if len(data) < self.params["min_samples"]:
            return {"direction": TrendDirection.UNKNOWN, "error": "Insufficient data"}

        window = window or self.params["trend_window"]
        now = datetime.now()
        cutoff = now - timedelta(seconds=window)

        # 过滤窗口内数据
        window_data = [d for d in data if d["timestamp"] >= cutoff]
        if len(window_data) < 3:
            return {"direction": TrendDirection.UNKNOWN, "error": "Insufficient window data"}

        values = np.array([d["value"] for d in window_data])
        times = np.array([(d["timestamp"] - cutoff).total_seconds() for d in window_data])

        # 线性回归
        slope, intercept, r_squared = self._linear_regression(times, values)

        # 判断趋势方向
        direction = self._determine_direction(slope, values)

        # 计算振荡特性
        oscillation = self._analyze_oscillation(values)

        # 预测值
        prediction_time = window + self.params["prediction_horizon"]
        predicted_value = slope * prediction_time + intercept

        result = {
            "direction": direction,
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "current_value": values[-1],
            "mean": np.mean(values),
            "std": np.std(values),
            "min": np.min(values),
            "max": np.max(values),
            "predicted_value": predicted_value,
            "prediction_horizon": self.params["prediction_horizon"],
            "oscillation": oscillation,
            "sample_count": len(values),
            "timestamp": now,
        }

        # 缓存结果
        self.trend_cache[source_id] = result

        return result

    def _linear_regression(self, x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
        """简单线性回归"""
        n = len(x)
        if n < 2:
            return 0.0, y[0] if len(y) > 0 else 0.0, 0.0

        x_mean = np.mean(x)
        y_mean = np.mean(y)

        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            return 0.0, y_mean, 0.0

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # R²
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        return slope, intercept, r_squared

    def _determine_direction(self, slope: float, values: np.ndarray) -> TrendDirection:
        """判断趋势方向"""
        std = np.std(values)
        mean = np.mean(values)

        if std == 0:
            return TrendDirection.STABLE

        # 归一化斜率
        normalized_slope = slope * len(values) / (std + 1e-10)

        if abs(normalized_slope) < 0.1:
            return TrendDirection.STABLE
        elif normalized_slope > 0.5:
            return TrendDirection.RISING
        elif normalized_slope < -0.5:
            return TrendDirection.FALLING
        elif 0.1 <= abs(normalized_slope) < 0.5:
            # 检查振荡
            zero_crossings = np.sum(np.diff(np.sign(values - mean)) != 0)
            if zero_crossings > len(values) * 0.3:
                return TrendDirection.OSCILLATING
            return TrendDirection.RISING if normalized_slope > 0 else TrendDirection.FALLING

        return TrendDirection.UNKNOWN

    def _analyze_oscillation(self, values: np.ndarray) -> Dict[str, Any]:
        """分析振荡特性"""
        if len(values) < 10:
            return {"is_oscillating": False}

        mean = np.mean(values)
        centered = values - mean

        # 过零次数
        zero_crossings = np.sum(np.diff(np.sign(centered)) != 0)
        crossing_rate = zero_crossings / len(values)

        # 振幅
        amplitude = (np.max(values) - np.min(values)) / 2

        # FFT分析主频
        try:
            fft = np.fft.fft(centered)
            freqs = np.fft.fftfreq(len(centered))
            main_freq_idx = np.argmax(np.abs(fft[1:len(fft)//2])) + 1
            main_freq = abs(freqs[main_freq_idx])
            main_power = np.abs(fft[main_freq_idx])
        except Exception:
            main_freq = 0.0
            main_power = 0.0

        is_oscillating = crossing_rate > self.params["oscillation_threshold"]

        return {
            "is_oscillating": is_oscillating,
            "crossing_rate": crossing_rate,
            "amplitude": amplitude,
            "main_frequency": main_freq,
            "main_power": main_power,
        }

    def detect_anomaly(self, source_id: str) -> List[AnomalyScore]:
        """检测异常"""
        if source_id not in self.data_history:
            return []

        data = list(self.data_history[source_id])
        if len(data) < self.params["min_samples"]:
            return []

        values = np.array([d["value"] for d in data])
        anomalies = []

        # 建立基线（如果没有）
        if source_id not in self.anomaly_baseline:
            self._build_baseline(source_id, values)

        baseline = self.anomaly_baseline.get(source_id, {})

        # 1. 尖峰检测
        spike = self._detect_spike(values, baseline)
        if spike:
            anomalies.append(spike)

        # 2. 漂移检测
        drift = self._detect_drift(values, baseline)
        if drift:
            anomalies.append(drift)

        # 3. 卡死检测
        stuck = self._detect_stuck(values)
        if stuck:
            anomalies.append(stuck)

        # 4. 噪声异常检测
        noise = self._detect_noise_anomaly(values, baseline)
        if noise:
            anomalies.append(noise)

        return anomalies

    def _build_baseline(self, source_id: str, values: np.ndarray):
        """建立基线"""
        self.anomaly_baseline[source_id] = {
            "mean": np.mean(values),
            "std": np.std(values),
            "min": np.min(values),
            "max": np.max(values),
            "range": np.max(values) - np.min(values),
        }

    def _detect_spike(self, values: np.ndarray,
                      baseline: Dict[str, float]) -> Optional[AnomalyScore]:
        """检测尖峰"""
        if not baseline:
            return None

        current = values[-1]
        mean = baseline.get("mean", np.mean(values))
        std = baseline.get("std", np.std(values))

        if std == 0:
            return None

        z_score = abs(current - mean) / std

        if z_score > self.params["anomaly_threshold"]:
            severity = "low" if z_score < 4 else "medium" if z_score < 5 else "high"
            return AnomalyScore(
                source_id="",  # 调用者填充
                anomaly_type=AnomalyType.SPIKE,
                score=min(z_score / 10, 1.0),
                severity=severity,
                description=f"尖峰异常: 当前值{current:.2f}偏离均值{mean:.2f}达{z_score:.1f}倍标准差",
                evidence={"z_score": z_score, "current": current, "mean": mean, "std": std}
            )
        return None

    def _detect_drift(self, values: np.ndarray,
                      baseline: Dict[str, float]) -> Optional[AnomalyScore]:
        """检测漂移"""
        if len(values) < 100 or not baseline:
            return None

        # 比较最近10%与历史均值
        recent = values[-int(len(values)*0.1):]
        recent_mean = np.mean(recent)
        baseline_mean = baseline.get("mean", np.mean(values))
        baseline_std = baseline.get("std", np.std(values))

        if baseline_std == 0:
            return None

        drift = abs(recent_mean - baseline_mean) / baseline_std

        if drift > 1.5:
            severity = "low" if drift < 2 else "medium" if drift < 3 else "high"
            direction = "上升" if recent_mean > baseline_mean else "下降"
            return AnomalyScore(
                source_id="",
                anomaly_type=AnomalyType.DRIFT,
                score=min(drift / 5, 1.0),
                severity=severity,
                description=f"漂移异常: 均值{direction}，从{baseline_mean:.2f}变为{recent_mean:.2f}",
                evidence={"drift": drift, "recent_mean": recent_mean, "baseline_mean": baseline_mean}
            )
        return None

    def _detect_stuck(self, values: np.ndarray) -> Optional[AnomalyScore]:
        """检测卡死"""
        if len(values) < 20:
            return None

        recent = values[-20:]
        std = np.std(recent)

        # 标准差几乎为零表示卡死
        if std < 1e-6:
            return AnomalyScore(
                source_id="",
                anomaly_type=AnomalyType.STUCK,
                score=0.9,
                severity="high",
                description=f"卡死异常: 数值停滞在{recent[-1]:.4f}",
                evidence={"std": std, "value": recent[-1]}
            )
        return None

    def _detect_noise_anomaly(self, values: np.ndarray,
                              baseline: Dict[str, float]) -> Optional[AnomalyScore]:
        """检测噪声异常"""
        if len(values) < 50 or not baseline:
            return None

        recent_std = np.std(values[-50:])
        baseline_std = baseline.get("std", np.std(values))

        if baseline_std == 0:
            return None

        noise_ratio = recent_std / baseline_std

        if noise_ratio > 2.0:
            severity = "low" if noise_ratio < 3 else "medium" if noise_ratio < 5 else "high"
            return AnomalyScore(
                source_id="",
                anomaly_type=AnomalyType.NOISE,
                score=min((noise_ratio - 1) / 5, 1.0),
                severity=severity,
                description=f"噪声异常: 波动增大{noise_ratio:.1f}倍",
                evidence={"noise_ratio": noise_ratio, "recent_std": recent_std, "baseline_std": baseline_std}
            )
        return None

    def generate_predictive_alert(self, source_id: str, source_name: str,
                                  limit_value: float,
                                  limit_type: str = "high") -> Optional[PredictiveAlert]:
        """生成预测性预警"""
        trend = self.analyze_trend(source_id)

        if trend.get("direction") == TrendDirection.UNKNOWN:
            return None

        slope = trend.get("slope", 0)
        current = trend.get("current_value", 0)

        # 判断是否会触及限值
        if limit_type == "high":
            if slope <= 0 or current >= limit_value:
                return None
            time_to_limit = (limit_value - current) / slope
        else:
            if slope >= 0 or current <= limit_value:
                return None
            time_to_limit = (current - limit_value) / abs(slope)

        # 只对短期内会触及的情况报警
        horizon = self.params["prediction_horizon"]
        if time_to_limit > horizon:
            return None

        self.alert_counter += 1
        predicted_value = current + slope * time_to_limit

        return PredictiveAlert(
            alert_id=f"PRED_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.alert_counter:04d}",
            source_id=source_id,
            source_name=source_name,
            current_value=current,
            predicted_value=predicted_value,
            prediction_horizon=horizon,
            limit_value=limit_value,
            time_to_limit=time_to_limit,
            confidence=trend.get("r_squared", 0.5),
            message=f"{source_name}预计在{time_to_limit:.0f}秒后达到{limit_type}限值{limit_value}",
            recommended_action="建议提前调整运行参数",
        )

    def analyze_correlation(self, source_ids: List[str]) -> Dict[str, Any]:
        """分析多参数相关性"""
        if len(source_ids) < 2:
            return {"error": "Need at least 2 sources"}

        # 获取对齐的数据
        aligned_data = self._align_data(source_ids)
        if aligned_data is None:
            return {"error": "Failed to align data"}

        n = len(source_ids)
        correlation_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i == j:
                    correlation_matrix[i, j] = 1.0
                else:
                    corr = np.corrcoef(aligned_data[i], aligned_data[j])[0, 1]
                    correlation_matrix[i, j] = corr if not np.isnan(corr) else 0.0

        # 识别强相关对
        strong_correlations = []
        for i in range(n):
            for j in range(i+1, n):
                corr = correlation_matrix[i, j]
                if abs(corr) > 0.7:
                    strong_correlations.append({
                        "pair": (source_ids[i], source_ids[j]),
                        "correlation": corr,
                        "type": "positive" if corr > 0 else "negative"
                    })

        return {
            "source_ids": source_ids,
            "correlation_matrix": correlation_matrix.tolist(),
            "strong_correlations": strong_correlations,
        }

    def _align_data(self, source_ids: List[str]) -> Optional[np.ndarray]:
        """对齐多源数据"""
        # 简化实现：取最近N个共同时间点的数据
        min_len = min(
            len(self.data_history.get(sid, []))
            for sid in source_ids
        )

        if min_len < self.params["min_samples"]:
            return None

        aligned = []
        for sid in source_ids:
            data = list(self.data_history[sid])[-min_len:]
            values = [d["value"] for d in data]
            aligned.append(values)

        return np.array(aligned)
