# -*- coding: utf-8 -*-
"""
深度学习诊断引擎 - AI-based Intelligent Diagnosis Engine

功能：
- 孤立森林异常检测 (Isolation Forest)
- LSTM时序预测与异常检测
- AutoEncoder重构异常检测
- 集成诊断决策
- 故障根因分析 (XAI可解释性)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from collections import deque


class DiagnosisMethod(Enum):
    """诊断方法"""
    ISOLATION_FOREST = "isolation_forest"
    LSTM_PREDICTOR = "lstm_predictor"
    AUTOENCODER = "autoencoder"
    ENSEMBLE = "ensemble"


class AnomalyLevel(Enum):
    """异常等级"""
    NORMAL = 0
    SLIGHT = 1
    MODERATE = 2
    SEVERE = 3
    CRITICAL = 4


@dataclass
class AnomalyResult:
    """异常检测结果"""
    timestamp: datetime
    method: DiagnosisMethod
    anomaly_score: float          # 0-1, 越高越异常
    anomaly_level: AnomalyLevel
    is_anomaly: bool
    confidence: float             # 置信度 0-1
    affected_variables: List[str]
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiagnosisReport:
    """诊断报告"""
    report_id: str
    timestamp: datetime
    overall_status: str           # "healthy", "warning", "fault"
    anomaly_results: List[AnomalyResult]
    fault_hypothesis: List[Dict[str, Any]]
    root_cause: Optional[str]
    recommendations: List[str]
    feature_importance: Dict[str, float] = field(default_factory=dict)


class IsolationForest:
    """
    孤立森林异常检测

    原理：异常点更容易被孤立，需要更少的分裂次数
    """

    def __init__(self, n_estimators: int = 100,
                 max_samples: int = 256,
                 contamination: float = 0.1):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination

        self.trees: List['IsolationTree'] = []
        self.threshold = 0.5
        self._is_fitted = False

    def fit(self, X: np.ndarray):
        """
        训练孤立森林

        Args:
            X: 训练数据 (n_samples, n_features)
        """
        n_samples = X.shape[0]
        sample_size = min(self.max_samples, n_samples)

        self.trees = []
        for _ in range(self.n_estimators):
            # 随机采样
            indices = np.random.choice(n_samples, sample_size, replace=False)
            sample = X[indices]

            # 构建孤立树
            tree = IsolationTree(max_depth=int(np.ceil(np.log2(sample_size))))
            tree.fit(sample)
            self.trees.append(tree)

        # 计算阈值
        scores = self.decision_function(X)
        self.threshold = np.percentile(scores, 100 * (1 - self.contamination))
        self._is_fitted = True

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """计算异常分数"""
        if not self.trees:
            return np.zeros(X.shape[0])

        # 平均路径长度
        avg_path_lengths = np.zeros(X.shape[0])
        for tree in self.trees:
            avg_path_lengths += tree.path_length(X)
        avg_path_lengths /= len(self.trees)

        # 归一化分数
        n = self.max_samples
        c_n = 2 * (np.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n
        scores = 2 ** (-avg_path_lengths / c_n)

        return scores

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测异常"""
        scores = self.decision_function(X)
        return (scores > self.threshold).astype(int)

    def detect(self, sample: np.ndarray) -> AnomalyResult:
        """检测单个样本"""
        if sample.ndim == 1:
            sample = sample.reshape(1, -1)

        score = self.decision_function(sample)[0]
        is_anomaly = score > self.threshold

        # 确定异常等级
        if score < 0.3:
            level = AnomalyLevel.NORMAL
        elif score < 0.5:
            level = AnomalyLevel.SLIGHT
        elif score < 0.7:
            level = AnomalyLevel.MODERATE
        elif score < 0.85:
            level = AnomalyLevel.SEVERE
        else:
            level = AnomalyLevel.CRITICAL

        return AnomalyResult(
            timestamp=datetime.now(),
            method=DiagnosisMethod.ISOLATION_FOREST,
            anomaly_score=float(score),
            anomaly_level=level,
            is_anomaly=is_anomaly,
            confidence=abs(score - 0.5) * 2,  # 距离0.5越远置信度越高
            affected_variables=[],
            details={"threshold": self.threshold},
        )


class IsolationTree:
    """孤立树"""

    def __init__(self, max_depth: int = 10):
        self.max_depth = max_depth
        self.root = None
        self.n_features = 0

    def fit(self, X: np.ndarray):
        self.n_features = X.shape[1]
        self.root = self._build_tree(X, 0)

    def _build_tree(self, X: np.ndarray, depth: int) -> Dict:
        n_samples = X.shape[0]

        if depth >= self.max_depth or n_samples <= 1:
            return {"type": "leaf", "size": n_samples}

        # 随机选择特征和分裂点
        feature = np.random.randint(self.n_features)
        min_val, max_val = X[:, feature].min(), X[:, feature].max()

        if min_val == max_val:
            return {"type": "leaf", "size": n_samples}

        split_value = np.random.uniform(min_val, max_val)

        # 分裂
        left_mask = X[:, feature] < split_value
        right_mask = ~left_mask

        return {
            "type": "internal",
            "feature": feature,
            "split_value": split_value,
            "left": self._build_tree(X[left_mask], depth + 1),
            "right": self._build_tree(X[right_mask], depth + 1),
        }

    def path_length(self, X: np.ndarray) -> np.ndarray:
        """计算路径长度"""
        return np.array([self._path_length_single(x, self.root, 0) for x in X])

    def _path_length_single(self, x: np.ndarray, node: Dict, depth: int) -> float:
        if node["type"] == "leaf":
            # 使用调整因子
            size = node["size"]
            if size <= 1:
                return depth
            else:
                c = 2 * (np.log(size - 1) + 0.5772156649) - 2 * (size - 1) / size
                return depth + c

        if x[node["feature"]] < node["split_value"]:
            return self._path_length_single(x, node["left"], depth + 1)
        else:
            return self._path_length_single(x, node["right"], depth + 1)


class LSTMPredictor:
    """
    LSTM时序预测器

    用于预测下一时刻值，通过预测误差检测异常
    """

    def __init__(self, input_dim: int, hidden_dim: int = 64,
                 sequence_length: int = 20):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.sequence_length = sequence_length

        # LSTM参数（简化实现）
        self.Wf = None  # forget gate
        self.Wi = None  # input gate
        self.Wc = None  # cell gate
        self.Wo = None  # output gate
        self.Wy = None  # output projection

        self.data_buffer = deque(maxlen=sequence_length)
        self.error_history = deque(maxlen=1000)
        self.error_threshold = 0.0
        self._is_fitted = False

    def _initialize_weights(self):
        """初始化权重"""
        total_input = self.input_dim + self.hidden_dim

        # Xavier初始化
        scale = np.sqrt(2.0 / (total_input + self.hidden_dim))
        self.Wf = np.random.randn(self.hidden_dim, total_input) * scale
        self.Wi = np.random.randn(self.hidden_dim, total_input) * scale
        self.Wc = np.random.randn(self.hidden_dim, total_input) * scale
        self.Wo = np.random.randn(self.hidden_dim, total_input) * scale

        self.bf = np.ones(self.hidden_dim)  # forget bias初始化为1
        self.bi = np.zeros(self.hidden_dim)
        self.bc = np.zeros(self.hidden_dim)
        self.bo = np.zeros(self.hidden_dim)

        self.Wy = np.random.randn(self.input_dim, self.hidden_dim) * scale
        self.by = np.zeros(self.input_dim)

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def _tanh(self, x: np.ndarray) -> np.ndarray:
        return np.tanh(np.clip(x, -500, 500))

    def _lstm_step(self, x: np.ndarray, h_prev: np.ndarray,
                   c_prev: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """单步LSTM"""
        combined = np.concatenate([x, h_prev])

        f = self._sigmoid(self.Wf @ combined + self.bf)
        i = self._sigmoid(self.Wi @ combined + self.bi)
        c_candidate = self._tanh(self.Wc @ combined + self.bc)
        o = self._sigmoid(self.Wo @ combined + self.bo)

        c = f * c_prev + i * c_candidate
        h = o * self._tanh(c)

        return h, c

    def fit(self, X: np.ndarray, epochs: int = 100, lr: float = 0.001):
        """
        训练LSTM

        Args:
            X: 时序数据 (n_samples, n_features)
            epochs: 训练轮数
            lr: 学习率
        """
        self._initialize_weights()

        n_samples = X.shape[0]
        errors = []

        for epoch in range(epochs):
            h = np.zeros(self.hidden_dim)
            c = np.zeros(self.hidden_dim)

            epoch_loss = 0
            for t in range(self.sequence_length, n_samples):
                # 前向传播
                for i in range(self.sequence_length):
                    x_t = X[t - self.sequence_length + i]
                    h, c = self._lstm_step(x_t, h, c)

                # 预测
                y_pred = self.Wy @ h + self.by
                y_true = X[t]

                # 误差
                error = y_pred - y_true
                epoch_loss += np.mean(error ** 2)

                # 简化的梯度更新（实际应用中需要BPTT）
                self.Wy -= lr * np.outer(error, h)
                self.by -= lr * error

            errors.append(epoch_loss / (n_samples - self.sequence_length))

        # 计算误差阈值
        self._compute_threshold(X)
        self._is_fitted = True

    def _compute_threshold(self, X: np.ndarray):
        """计算异常阈值"""
        errors = []
        h = np.zeros(self.hidden_dim)
        c = np.zeros(self.hidden_dim)

        for t in range(self.sequence_length, X.shape[0]):
            for i in range(self.sequence_length):
                x_t = X[t - self.sequence_length + i]
                h, c = self._lstm_step(x_t, h, c)

            y_pred = self.Wy @ h + self.by
            error = np.mean((y_pred - X[t]) ** 2)
            errors.append(error)

        self.error_threshold = np.percentile(errors, 95)

    def predict_next(self) -> Optional[np.ndarray]:
        """预测下一时刻"""
        if len(self.data_buffer) < self.sequence_length:
            return None

        h = np.zeros(self.hidden_dim)
        c = np.zeros(self.hidden_dim)

        for x in self.data_buffer:
            h, c = self._lstm_step(x, h, c)

        return self.Wy @ h + self.by

    def update(self, observation: np.ndarray):
        """更新数据缓冲区"""
        self.data_buffer.append(observation)

    def detect(self, observation: np.ndarray) -> AnomalyResult:
        """检测异常"""
        prediction = self.predict_next()
        self.update(observation)

        if prediction is None:
            return AnomalyResult(
                timestamp=datetime.now(),
                method=DiagnosisMethod.LSTM_PREDICTOR,
                anomaly_score=0.0,
                anomaly_level=AnomalyLevel.NORMAL,
                is_anomaly=False,
                confidence=0.0,
                affected_variables=[],
                details={"status": "warming_up"},
            )

        error = np.mean((prediction - observation) ** 2)
        self.error_history.append(error)

        # 归一化分数
        if self.error_threshold > 0:
            score = min(1.0, error / (self.error_threshold * 2))
        else:
            score = 0.0

        is_anomaly = error > self.error_threshold

        # 确定等级
        if score < 0.25:
            level = AnomalyLevel.NORMAL
        elif score < 0.5:
            level = AnomalyLevel.SLIGHT
        elif score < 0.75:
            level = AnomalyLevel.MODERATE
        elif score < 0.9:
            level = AnomalyLevel.SEVERE
        else:
            level = AnomalyLevel.CRITICAL

        # 找出偏差最大的变量
        var_errors = np.abs(prediction - observation)
        top_indices = np.argsort(var_errors)[-3:]
        affected = [f"var_{i}" for i in top_indices]

        return AnomalyResult(
            timestamp=datetime.now(),
            method=DiagnosisMethod.LSTM_PREDICTOR,
            anomaly_score=float(score),
            anomaly_level=level,
            is_anomaly=is_anomaly,
            confidence=min(1.0, len(self.error_history) / 100),
            affected_variables=affected,
            details={
                "prediction_error": float(error),
                "threshold": float(self.error_threshold),
                "prediction": prediction.tolist(),
            },
        )


class AutoEncoderDetector:
    """
    AutoEncoder异常检测

    原理：正常样本重构误差小，异常样本重构误差大
    """

    def __init__(self, input_dim: int, encoding_dim: int = 16):
        self.input_dim = input_dim
        self.encoding_dim = encoding_dim

        # 编码器权重
        self.W1 = None
        self.b1 = None

        # 解码器权重
        self.W2 = None
        self.b2 = None

        self.threshold = 0.0
        self._is_fitted = False

    def _initialize_weights(self):
        """初始化权重"""
        scale1 = np.sqrt(2.0 / self.input_dim)
        scale2 = np.sqrt(2.0 / self.encoding_dim)

        self.W1 = np.random.randn(self.encoding_dim, self.input_dim) * scale1
        self.b1 = np.zeros(self.encoding_dim)

        self.W2 = np.random.randn(self.input_dim, self.encoding_dim) * scale2
        self.b2 = np.zeros(self.input_dim)

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def _relu_grad(self, x: np.ndarray) -> np.ndarray:
        return (x > 0).astype(float)

    def encode(self, X: np.ndarray) -> np.ndarray:
        """编码"""
        return self._relu(X @ self.W1.T + self.b1)

    def decode(self, Z: np.ndarray) -> np.ndarray:
        """解码"""
        return Z @ self.W2.T + self.b2

    def reconstruct(self, X: np.ndarray) -> np.ndarray:
        """重构"""
        return self.decode(self.encode(X))

    def fit(self, X: np.ndarray, epochs: int = 100, lr: float = 0.01,
            batch_size: int = 32):
        """
        训练AutoEncoder

        Args:
            X: 训练数据 (n_samples, n_features)
            epochs: 训练轮数
            lr: 学习率
            batch_size: 批大小
        """
        self._initialize_weights()
        n_samples = X.shape[0]

        for epoch in range(epochs):
            # 打乱数据
            indices = np.random.permutation(n_samples)

            for start in range(0, n_samples, batch_size):
                end = min(start + batch_size, n_samples)
                batch = X[indices[start:end]]

                # 前向传播
                z = self.encode(batch)
                x_recon = self.decode(z)

                # 计算梯度
                recon_error = x_recon - batch  # (batch, input_dim)

                # 解码器梯度
                dW2 = z.T @ recon_error / len(batch)
                db2 = np.mean(recon_error, axis=0)

                # 编码器梯度
                dz = recon_error @ self.W2  # (batch, encoding_dim)
                dz *= self._relu_grad(z)

                dW1 = dz.T @ batch / len(batch)
                db1 = np.mean(dz, axis=0)

                # 更新权重
                self.W2 -= lr * dW2.T
                self.b2 -= lr * db2
                self.W1 -= lr * dW1
                self.b1 -= lr * db1

        # 计算阈值
        recon = self.reconstruct(X)
        errors = np.mean((X - recon) ** 2, axis=1)
        self.threshold = np.percentile(errors, 95)
        self._is_fitted = True

    def detect(self, sample: np.ndarray) -> AnomalyResult:
        """检测异常"""
        if sample.ndim == 1:
            sample = sample.reshape(1, -1)

        recon = self.reconstruct(sample)
        error = np.mean((sample - recon) ** 2)

        # 归一化分数
        score = min(1.0, error / (self.threshold * 2)) if self.threshold > 0 else 0.0
        is_anomaly = error > self.threshold

        # 确定等级
        if score < 0.25:
            level = AnomalyLevel.NORMAL
        elif score < 0.5:
            level = AnomalyLevel.SLIGHT
        elif score < 0.75:
            level = AnomalyLevel.MODERATE
        elif score < 0.9:
            level = AnomalyLevel.SEVERE
        else:
            level = AnomalyLevel.CRITICAL

        # 找出重构误差最大的变量
        var_errors = np.abs(sample[0] - recon[0])
        top_indices = np.argsort(var_errors)[-3:]
        affected = [f"var_{i}" for i in top_indices]

        return AnomalyResult(
            timestamp=datetime.now(),
            method=DiagnosisMethod.AUTOENCODER,
            anomaly_score=float(score),
            anomaly_level=level,
            is_anomaly=is_anomaly,
            confidence=0.85,
            affected_variables=affected,
            details={
                "reconstruction_error": float(error),
                "threshold": float(self.threshold),
            },
        )


class EnsembleDiagnosisEngine:
    """
    集成诊断引擎

    整合多种诊断方法，提供综合诊断结果
    """

    def __init__(self, input_dim: int):
        self.input_dim = input_dim

        # 初始化各诊断器
        self.isolation_forest = IsolationForest(n_estimators=100)
        self.lstm_predictor = LSTMPredictor(input_dim, hidden_dim=32)
        self.autoencoder = AutoEncoderDetector(input_dim, encoding_dim=max(4, input_dim // 4))

        # 方法权重
        self.weights = {
            DiagnosisMethod.ISOLATION_FOREST: 0.3,
            DiagnosisMethod.LSTM_PREDICTOR: 0.4,
            DiagnosisMethod.AUTOENCODER: 0.3,
        }

        # 历史数据
        self.training_data: List[np.ndarray] = []
        self.diagnosis_history: List[DiagnosisReport] = []

        # 故障模式知识库
        self.fault_patterns = self._initialize_fault_patterns()

        self._is_trained = False

    def _initialize_fault_patterns(self) -> Dict[str, Dict]:
        """初始化故障模式库"""
        return {
            "bearing_wear": {
                "description": "轴承磨损",
                "indicators": ["振动增大", "温度升高", "油液金属含量"],
                "affected_vars": ["vibration", "bearing_temp", "oil_quality"],
                "typical_score_range": (0.6, 0.9),
            },
            "cavitation": {
                "description": "空化",
                "indicators": ["振动异常", "效率下降", "噪声增大"],
                "affected_vars": ["vibration", "efficiency", "noise_level"],
                "typical_score_range": (0.5, 0.85),
            },
            "governor_instability": {
                "description": "调速器不稳定",
                "indicators": ["功率波动", "导叶振荡", "转速波动"],
                "affected_vars": ["power", "guide_vane", "speed"],
                "typical_score_range": (0.4, 0.7),
            },
            "excitation_fault": {
                "description": "励磁故障",
                "indicators": ["电压波动", "无功异常", "励磁电流"],
                "affected_vars": ["voltage", "reactive_power", "excitation_current"],
                "typical_score_range": (0.5, 0.8),
            },
            "water_hammer": {
                "description": "水锤冲击",
                "indicators": ["压力骤升", "振动突增", "流量波动"],
                "affected_vars": ["pressure", "vibration", "flow"],
                "typical_score_range": (0.7, 1.0),
            },
            "sensor_drift": {
                "description": "传感器漂移",
                "indicators": ["单一测点异常", "无关联变化", "缓慢偏移"],
                "affected_vars": [],  # 动态确定
                "typical_score_range": (0.3, 0.6),
            },
        }

    def train(self, X: np.ndarray, epochs: int = 50):
        """
        训练所有诊断器

        Args:
            X: 正常运行数据 (n_samples, n_features)
            epochs: 训练轮数
        """
        print("训练孤立森林...")
        self.isolation_forest.fit(X)

        print("训练LSTM预测器...")
        self.lstm_predictor.fit(X, epochs=epochs)

        print("训练AutoEncoder...")
        self.autoencoder.fit(X, epochs=epochs)

        self._is_trained = True
        print("训练完成")

    def diagnose(self, observation: np.ndarray,
                 variable_names: List[str] = None) -> DiagnosisReport:
        """
        执行综合诊断

        Args:
            observation: 当前观测值
            variable_names: 变量名列表

        Returns:
            诊断报告
        """
        report_id = f"DIAG_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if observation.ndim == 1:
            obs = observation.reshape(1, -1)
        else:
            obs = observation

        # 各方法诊断
        results = []

        # 孤立森林
        if self.isolation_forest._is_fitted:
            if_result = self.isolation_forest.detect(obs)
            if variable_names:
                if_result.affected_variables = self._identify_affected_vars(
                    obs[0], variable_names, if_result.anomaly_score
                )
            results.append(if_result)

        # LSTM预测器
        lstm_result = self.lstm_predictor.detect(obs[0])
        if variable_names:
            lstm_result.affected_variables = self._identify_affected_vars(
                obs[0], variable_names, lstm_result.anomaly_score
            )
        results.append(lstm_result)

        # AutoEncoder
        if self.autoencoder._is_fitted:
            ae_result = self.autoencoder.detect(obs)
            if variable_names:
                ae_result.affected_variables = self._identify_affected_vars(
                    obs[0], variable_names, ae_result.anomaly_score
                )
            results.append(ae_result)

        # 集成决策
        ensemble_score = self._ensemble_score(results)
        overall_level = self._determine_overall_level(ensemble_score)
        overall_status = self._determine_status(overall_level)

        # 故障假设
        fault_hypothesis = self._generate_fault_hypothesis(results, variable_names)

        # 根因分析
        root_cause = self._analyze_root_cause(fault_hypothesis)

        # 建议
        recommendations = self._generate_recommendations(overall_status, fault_hypothesis)

        # 特征重要性
        feature_importance = self._calculate_feature_importance(obs[0], variable_names)

        report = DiagnosisReport(
            report_id=report_id,
            timestamp=datetime.now(),
            overall_status=overall_status,
            anomaly_results=results,
            fault_hypothesis=fault_hypothesis,
            root_cause=root_cause,
            recommendations=recommendations,
            feature_importance=feature_importance,
        )

        self.diagnosis_history.append(report)
        return report

    def _identify_affected_vars(self, observation: np.ndarray,
                                variable_names: List[str],
                                score: float) -> List[str]:
        """识别受影响的变量"""
        if score < 0.3:
            return []

        # 基于偏差识别
        if len(self.training_data) > 0:
            mean_vals = np.mean(self.training_data, axis=0)
            std_vals = np.std(self.training_data, axis=0) + 1e-6
            z_scores = np.abs(observation - mean_vals) / std_vals

            # 选择z-score > 2的变量
            affected_indices = np.where(z_scores > 2)[0]
            affected = [variable_names[i] for i in affected_indices
                       if i < len(variable_names)]
            return affected[:5]

        return []

    def _ensemble_score(self, results: List[AnomalyResult]) -> float:
        """计算集成分数"""
        if not results:
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0

        for result in results:
            weight = self.weights.get(result.method, 0.33)
            weighted_sum += result.anomaly_score * weight * result.confidence
            total_weight += weight * result.confidence

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _determine_overall_level(self, score: float) -> AnomalyLevel:
        """确定整体异常等级"""
        if score < 0.2:
            return AnomalyLevel.NORMAL
        elif score < 0.4:
            return AnomalyLevel.SLIGHT
        elif score < 0.6:
            return AnomalyLevel.MODERATE
        elif score < 0.8:
            return AnomalyLevel.SEVERE
        else:
            return AnomalyLevel.CRITICAL

    def _determine_status(self, level: AnomalyLevel) -> str:
        """确定状态"""
        if level == AnomalyLevel.NORMAL:
            return "healthy"
        elif level in [AnomalyLevel.SLIGHT, AnomalyLevel.MODERATE]:
            return "warning"
        else:
            return "fault"

    def _generate_fault_hypothesis(self, results: List[AnomalyResult],
                                   variable_names: List[str]) -> List[Dict]:
        """生成故障假设"""
        hypotheses = []

        # 收集所有受影响的变量
        all_affected = set()
        for result in results:
            all_affected.update(result.affected_variables)

        avg_score = np.mean([r.anomaly_score for r in results]) if results else 0

        # 匹配故障模式
        for fault_type, pattern in self.fault_patterns.items():
            match_score = 0
            matched_vars = []

            for var in pattern["affected_vars"]:
                if any(var in av for av in all_affected):
                    match_score += 1
                    matched_vars.append(var)

            if match_score > 0 and pattern["typical_score_range"][0] <= avg_score <= pattern["typical_score_range"][1] + 0.2:
                confidence = match_score / max(len(pattern["affected_vars"]), 1)
                hypotheses.append({
                    "fault_type": fault_type,
                    "description": pattern["description"],
                    "confidence": confidence,
                    "matched_indicators": matched_vars,
                    "severity": avg_score,
                })

        # 按置信度排序
        hypotheses.sort(key=lambda x: x["confidence"], reverse=True)
        return hypotheses[:3]

    def _analyze_root_cause(self, hypotheses: List[Dict]) -> Optional[str]:
        """分析根本原因"""
        if not hypotheses:
            return None

        top = hypotheses[0]
        if top["confidence"] > 0.6:
            return f"{top['description']}（置信度{top['confidence']*100:.0f}%）"

        return None

    def _generate_recommendations(self, status: str,
                                   hypotheses: List[Dict]) -> List[str]:
        """生成建议"""
        recommendations = []

        if status == "healthy":
            recommendations.append("系统运行正常，继续监控")

        elif status == "warning":
            recommendations.append("发现异常趋势，建议加强监控")
            if hypotheses:
                recommendations.append(f"重点关注：{hypotheses[0]['description']}")

        else:  # fault
            recommendations.append("检测到故障，建议立即处理")
            if hypotheses:
                fault_type = hypotheses[0]['fault_type']
                if fault_type == "bearing_wear":
                    recommendations.append("检查轴承润滑和磨损情况")
                    recommendations.append("分析油液金属颗粒含量")
                elif fault_type == "cavitation":
                    recommendations.append("调整运行工况，避免空化区")
                    recommendations.append("检查转轮叶片是否受损")
                elif fault_type == "governor_instability":
                    recommendations.append("检查调速器PID参数")
                    recommendations.append("验证调速器油压系统")
                elif fault_type == "water_hammer":
                    recommendations.append("检查导叶关闭规律")
                    recommendations.append("检查压力管道和调压室")

        return recommendations

    def _calculate_feature_importance(self, observation: np.ndarray,
                                       variable_names: List[str]) -> Dict[str, float]:
        """计算特征重要性"""
        if not variable_names or len(self.training_data) == 0:
            return {}

        mean_vals = np.mean(self.training_data, axis=0)
        std_vals = np.std(self.training_data, axis=0) + 1e-6
        z_scores = np.abs(observation - mean_vals) / std_vals

        importance = {}
        for i, name in enumerate(variable_names):
            if i < len(z_scores):
                importance[name] = float(min(1.0, z_scores[i] / 5))

        return importance

    def add_training_sample(self, sample: np.ndarray):
        """添加训练样本"""
        self.training_data.append(sample)

    def get_diagnosis_summary(self, n_recent: int = 10) -> Dict[str, Any]:
        """获取诊断摘要"""
        recent = self.diagnosis_history[-n_recent:]

        if not recent:
            return {"status": "no_data"}

        status_counts = {"healthy": 0, "warning": 0, "fault": 0}
        for report in recent:
            status_counts[report.overall_status] += 1

        avg_score = np.mean([
            np.mean([r.anomaly_score for r in report.anomaly_results])
            for report in recent
        ])

        return {
            "total_diagnoses": len(recent),
            "status_distribution": status_counts,
            "average_anomaly_score": float(avg_score),
            "latest_status": recent[-1].overall_status,
            "latest_root_cause": recent[-1].root_cause,
        }

