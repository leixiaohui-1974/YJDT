"""
场景识别模块
Scenario Recognition Module

基于机器学习的运行场景识别和异常检测
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
import warnings

# 抑制sklearn的警告
warnings.filterwarnings('ignore')


@dataclass
class RecognitionResult:
    """识别结果"""
    scenario_type: str          # 识别的场景类型
    confidence: float           # 置信度 (0-1)
    probabilities: Dict[str, float]  # 各场景类型的概率
    features_used: List[str]    # 使用的特征
    timestamp: float = 0.0      # 时间戳
    is_anomaly: bool = False    # 是否异常


class FeatureExtractor:
    """特征提取器"""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size

        # 特征名称
        self.feature_names = [
            'power_mean', 'power_std', 'power_trend',
            'speed_mean', 'speed_std', 'speed_deviation',
            'opening_mean', 'opening_std', 'opening_rate',
            'pressure_mean', 'pressure_std', 'pressure_max',
            'frequency_mean', 'frequency_std', 'frequency_deviation',
            'flow_mean', 'flow_std',
            'vibration_rms', 'vibration_peak',
        ]

    def extract(self, data: Dict[str, np.ndarray]) -> np.ndarray:
        """
        从时序数据中提取特征

        Args:
            data: 包含各信号时序数据的字典

        Returns:
            特征向量
        """
        features = []

        # 功率特征
        if 'power' in data:
            power = data['power'][-self.window_size:]
            features.extend([
                np.mean(power),
                np.std(power),
                self._calc_trend(power),
            ])
        else:
            features.extend([0, 0, 0])

        # 转速特征
        if 'speed' in data:
            speed = data['speed'][-self.window_size:]
            features.extend([
                np.mean(speed),
                np.std(speed),
                np.max(np.abs(speed - np.mean(speed))),
            ])
        else:
            features.extend([1, 0, 0])

        # 开度特征
        if 'opening' in data:
            opening = data['opening'][-self.window_size:]
            features.extend([
                np.mean(opening),
                np.std(opening),
                self._calc_rate(opening),
            ])
        else:
            features.extend([0.5, 0, 0])

        # 压力特征
        if 'pressure' in data:
            pressure = data['pressure'][-self.window_size:]
            features.extend([
                np.mean(pressure),
                np.std(pressure),
                np.max(pressure),
            ])
        else:
            features.extend([0, 0, 0])

        # 频率特征
        if 'frequency' in data:
            freq = data['frequency'][-self.window_size:]
            features.extend([
                np.mean(freq),
                np.std(freq),
                np.max(np.abs(freq - 50.0)),
            ])
        else:
            features.extend([50, 0, 0])

        # 流量特征
        if 'flow' in data:
            flow = data['flow'][-self.window_size:]
            features.extend([
                np.mean(flow),
                np.std(flow),
            ])
        else:
            features.extend([0, 0])

        # 振动特征
        if 'vibration' in data:
            vib = data['vibration'][-self.window_size:]
            features.extend([
                np.sqrt(np.mean(vib**2)),  # RMS
                np.max(vib),
            ])
        else:
            features.extend([0, 0])

        return np.array(features)

    def _calc_trend(self, data: np.ndarray) -> float:
        """计算趋势（线性拟合斜率）"""
        if len(data) < 2:
            return 0.0
        x = np.arange(len(data))
        slope = np.polyfit(x, data, 1)[0]
        return slope

    def _calc_rate(self, data: np.ndarray) -> float:
        """计算变化率"""
        if len(data) < 2:
            return 0.0
        return np.mean(np.abs(np.diff(data)))


class ScenarioClassifier(ABC):
    """场景分类器基类"""

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray):
        """训练分类器"""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """预测场景"""
        pass


class RandomForestScenarioClassifier(ScenarioClassifier):
    """随机森林场景分类器"""

    def __init__(self, n_estimators: int = 100):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=10,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.classes_: List[str] = []

    def train(self, X: np.ndarray, y: np.ndarray):
        """训练分类器"""
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.classes_ = list(self.model.classes_)
        self.is_trained = True

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """预测场景"""
        if not self.is_trained:
            raise RuntimeError("分类器未训练")

        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)

        return predictions, probabilities

    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if not self.is_trained:
            return {}
        return dict(zip(
            range(len(self.model.feature_importances_)),
            self.model.feature_importances_
        ))


class NeuralNetworkScenarioClassifier(ScenarioClassifier):
    """神经网络场景分类器"""

    def __init__(self, hidden_layers: Tuple[int, ...] = (64, 32)):
        self.model = MLPClassifier(
            hidden_layer_sizes=hidden_layers,
            activation='relu',
            solver='adam',
            max_iter=500,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.classes_: List[str] = []

    def train(self, X: np.ndarray, y: np.ndarray):
        """训练分类器"""
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.classes_ = list(self.model.classes_)
        self.is_trained = True

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """预测场景"""
        if not self.is_trained:
            raise RuntimeError("分类器未训练")

        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)

        return predictions, probabilities


class AnomalyDetector:
    """
    异常检测器

    使用隔离森林检测异常工况
    """

    def __init__(self, contamination: float = 0.1):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False

        # 阈值
        self.thresholds: Dict[str, Tuple[float, float]] = {}

    def train(self, X: np.ndarray):
        """训练异常检测模型"""
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True

        # 计算各特征的正常范围
        for i in range(X.shape[1]):
            mean = np.mean(X[:, i])
            std = np.std(X[:, i])
            self.thresholds[i] = (mean - 3*std, mean + 3*std)

    def detect(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        检测异常

        Args:
            X: 特征矩阵

        Returns:
            (异常标记数组, 异常分数数组)
        """
        if not self.is_trained:
            # 未训练时使用简单规则
            return np.zeros(len(X)), np.zeros(len(X))

        X_scaled = self.scaler.transform(X)

        # 隔离森林预测 (-1表示异常，1表示正常)
        predictions = self.model.predict(X_scaled)
        is_anomaly = predictions == -1

        # 异常分数 (越小越异常)
        scores = self.model.decision_function(X_scaled)

        return is_anomaly, scores

    def detect_threshold(self, sample: np.ndarray) -> Tuple[bool, List[str]]:
        """
        基于阈值的异常检测

        Args:
            sample: 单个样本的特征向量

        Returns:
            (是否异常, 异常特征列表)
        """
        anomaly_features = []

        for i, value in enumerate(sample):
            if i in self.thresholds:
                low, high = self.thresholds[i]
                if value < low or value > high:
                    anomaly_features.append(str(i))

        is_anomaly = len(anomaly_features) > 0
        return is_anomaly, anomaly_features


class ScenarioRecognizer:
    """
    场景识别器

    综合使用分类和异常检测进行场景识别
    """

    def __init__(self, classifier_type: str = "random_forest"):
        # 特征提取器
        self.feature_extractor = FeatureExtractor()

        # 分类器
        if classifier_type == "random_forest":
            self.classifier = RandomForestScenarioClassifier()
        else:
            self.classifier = NeuralNetworkScenarioClassifier()

        # 异常检测器
        self.anomaly_detector = AnomalyDetector()

        # 场景类型映射
        self.scenario_types = [
            'normal_operation',
            'load_change',
            'load_rejection',
            'startup',
            'shutdown',
            'frequency_regulation',
            'sensor_fault',
            'actuator_fault',
            'grid_fault',
            'extreme_condition',
        ]

        # 训练状态
        self.is_trained = False

        # 历史数据缓冲
        self.data_buffer: Dict[str, List[float]] = {}
        self.buffer_size = 1000

        # 识别历史
        self.recognition_history: List[RecognitionResult] = []

    def train(
        self,
        training_data: List[Dict[str, np.ndarray]],
        labels: List[str]
    ):
        """
        训练识别器

        Args:
            training_data: 训练数据列表
            labels: 对应的场景标签
        """
        # 提取特征
        X = np.array([
            self.feature_extractor.extract(data)
            for data in training_data
        ])
        y = np.array(labels)

        # 训练分类器
        self.classifier.train(X, y)

        # 训练异常检测器（仅使用正常数据）
        normal_mask = y == 'normal_operation'
        if np.sum(normal_mask) > 10:
            X_normal = X[normal_mask]
            self.anomaly_detector.train(X_normal)

        self.is_trained = True

    def recognize(
        self,
        data: Dict[str, np.ndarray],
        timestamp: float = 0.0
    ) -> RecognitionResult:
        """
        识别当前场景

        Args:
            data: 当前数据
            timestamp: 时间戳

        Returns:
            识别结果
        """
        # 提取特征
        features = self.feature_extractor.extract(data)
        features = features.reshape(1, -1)

        # 异常检测
        is_anomaly, anomaly_score = self.anomaly_detector.detect(features)

        if self.is_trained:
            # 分类预测
            predictions, probabilities = self.classifier.predict(features)
            scenario_type = predictions[0]
            confidence = np.max(probabilities[0])

            # 构建概率字典
            prob_dict = dict(zip(
                self.classifier.classes_,
                probabilities[0]
            ))
        else:
            # 未训练时使用规则
            scenario_type, confidence = self._rule_based_recognition(data)
            prob_dict = {scenario_type: confidence}

        result = RecognitionResult(
            scenario_type=scenario_type,
            confidence=confidence,
            probabilities=prob_dict,
            features_used=self.feature_extractor.feature_names,
            timestamp=timestamp,
            is_anomaly=bool(is_anomaly[0]) if len(is_anomaly) > 0 else False,
        )

        self.recognition_history.append(result)

        return result

    def _rule_based_recognition(
        self,
        data: Dict[str, np.ndarray]
    ) -> Tuple[str, float]:
        """基于规则的场景识别"""
        # 获取最新数据
        power = data.get('power', np.array([0]))[-1]
        speed = data.get('speed', np.array([1]))[-1]
        opening = data.get('opening', np.array([0.5]))[-1]
        frequency = data.get('frequency', np.array([50]))[-1]

        # 计算变化率
        if 'power' in data and len(data['power']) > 10:
            power_rate = np.abs(np.mean(np.diff(data['power'][-10:])))
        else:
            power_rate = 0

        # 规则判断
        if power < 10 and speed < 10:
            return 'shutdown', 0.9

        if power < 10 and speed > 150:
            return 'startup', 0.8

        if power_rate > 100:  # 功率快速变化
            if power_rate > 500:
                return 'load_rejection', 0.85
            return 'load_change', 0.75

        if abs(frequency - 50) > 0.2:
            return 'frequency_regulation', 0.8

        if abs(speed - 166.7) / 166.7 > 0.05:
            return 'sensor_fault', 0.6

        return 'normal_operation', 0.9

    def update_buffer(self, signal_name: str, value: float):
        """更新数据缓冲"""
        if signal_name not in self.data_buffer:
            self.data_buffer[signal_name] = []

        self.data_buffer[signal_name].append(value)

        # 限制缓冲大小
        if len(self.data_buffer[signal_name]) > self.buffer_size:
            self.data_buffer[signal_name] = self.data_buffer[signal_name][-self.buffer_size:]

    def get_buffer_as_array(self) -> Dict[str, np.ndarray]:
        """获取缓冲数据为数组格式"""
        return {
            name: np.array(values)
            for name, values in self.data_buffer.items()
        }

    def get_recognition_statistics(self) -> Dict:
        """获取识别统计信息"""
        if not self.recognition_history:
            return {}

        recent = self.recognition_history[-100:]

        type_counts = {}
        for result in recent:
            stype = result.scenario_type
            type_counts[stype] = type_counts.get(stype, 0) + 1

        avg_confidence = np.mean([r.confidence for r in recent])
        anomaly_rate = np.mean([r.is_anomaly for r in recent])

        return {
            'total_recognitions': len(self.recognition_history),
            'recent_type_distribution': type_counts,
            'average_confidence': avg_confidence,
            'anomaly_rate': anomaly_rate,
        }

    def generate_training_data(
        self,
        num_samples: int = 1000
    ) -> Tuple[List[Dict[str, np.ndarray]], List[str]]:
        """
        生成合成训练数据

        Args:
            num_samples: 样本数量

        Returns:
            (训练数据, 标签)
        """
        training_data = []
        labels = []

        samples_per_class = num_samples // len(self.scenario_types)

        for scenario_type in self.scenario_types:
            for _ in range(samples_per_class):
                data = self._generate_synthetic_sample(scenario_type)
                training_data.append(data)
                labels.append(scenario_type)

        return training_data, labels

    def _generate_synthetic_sample(
        self,
        scenario_type: str,
        length: int = 100
    ) -> Dict[str, np.ndarray]:
        """生成合成样本"""
        t = np.linspace(0, 10, length)

        if scenario_type == 'normal_operation':
            power = 500 + 10 * np.random.randn(length)
            speed = 166.7 + 0.5 * np.random.randn(length)
            opening = 0.5 + 0.01 * np.random.randn(length)
            frequency = 50 + 0.05 * np.random.randn(length)

        elif scenario_type == 'load_rejection':
            power = np.concatenate([
                500 * np.ones(50),
                np.linspace(500, 50, 20),
                50 * np.ones(30),
            ])
            speed = np.concatenate([
                166.7 * np.ones(50),
                np.linspace(166.7, 200, 20),
                np.linspace(200, 170, 30),
            ])
            opening = np.concatenate([
                0.5 * np.ones(50),
                np.linspace(0.5, 0.1, 20),
                0.1 * np.ones(30),
            ])
            frequency = 50 + 0.1 * np.random.randn(length)

        elif scenario_type == 'startup':
            power = np.linspace(0, 500, length)
            speed = np.linspace(0, 166.7, length)
            opening = np.linspace(0, 0.5, length)
            frequency = 50 + 0.05 * np.random.randn(length)

        elif scenario_type == 'shutdown':
            power = np.linspace(500, 0, length)
            speed = np.linspace(166.7, 0, length)
            opening = np.linspace(0.5, 0, length)
            frequency = 50 + 0.05 * np.random.randn(length)

        elif scenario_type == 'load_change':
            power = 500 + 100 * np.sin(2 * np.pi * t / 10)
            speed = 166.7 + 2 * np.sin(2 * np.pi * t / 10)
            opening = 0.5 + 0.1 * np.sin(2 * np.pi * t / 10)
            frequency = 50 + 0.05 * np.random.randn(length)

        elif scenario_type == 'frequency_regulation':
            power = 500 + 50 * np.random.randn(length)
            speed = 166.7 + 0.5 * np.random.randn(length)
            opening = 0.5 + 0.05 * np.random.randn(length)
            frequency = 50 + 0.3 * np.sin(2 * np.pi * t / 5) + 0.1 * np.random.randn(length)

        elif scenario_type == 'sensor_fault':
            power = 500 + 10 * np.random.randn(length)
            # 传感器故障：突然跳变或漂移
            speed = 166.7 + 0.5 * np.random.randn(length)
            speed[50:] += 50  # 突变
            opening = 0.5 + 0.01 * np.random.randn(length)
            frequency = 50 + 0.05 * np.random.randn(length)

        elif scenario_type == 'actuator_fault':
            power = 500 + 10 * np.random.randn(length)
            speed = 166.7 + 2 * np.random.randn(length)  # 增大波动
            opening = 0.5 * np.ones(length)  # 卡死
            frequency = 50 + 0.1 * np.random.randn(length)

        elif scenario_type == 'grid_fault':
            power = 500 + 10 * np.random.randn(length)
            power[50:55] *= 0.1  # 短暂跌落
            speed = 166.7 + 5 * np.random.randn(length)
            opening = 0.5 + 0.05 * np.random.randn(length)
            frequency = 50 + 0.05 * np.random.randn(length)
            frequency[50:55] -= 1  # 频率跌落

        else:  # extreme_condition
            power = 800 + 20 * np.random.randn(length)  # 高负荷
            speed = 166.7 + 1 * np.random.randn(length)
            opening = 0.9 + 0.02 * np.random.randn(length)  # 大开度
            frequency = 50 + 0.1 * np.random.randn(length)

        # 添加噪声
        noise_level = 0.02
        power += noise_level * np.max(np.abs(power)) * np.random.randn(length)
        speed += noise_level * np.max(np.abs(speed)) * np.random.randn(length)

        return {
            'power': power,
            'speed': speed,
            'opening': opening,
            'frequency': frequency,
            'flow': power / 2.5,  # 简化关系
            'pressure': 4.8 + 0.1 * np.random.randn(length),
            'vibration': 20 + 5 * np.random.randn(length),
        }
