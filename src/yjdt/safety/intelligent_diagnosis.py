# -*- coding: utf-8 -*-
"""
智能故障诊断与预测维护系统
Intelligent Fault Diagnosis and Predictive Maintenance System

功能：
1. 实时故障检测与诊断
2. 故障根因分析
3. 剩余寿命预测 (RUL)
4. 预测性维护建议
5. 健康状态评估

Author: YJDT Team
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
import warnings


class HealthStatus(Enum):
    """健康状态等级"""
    EXCELLENT = ("优秀", 0.9, "🟢")
    GOOD = ("良好", 0.7, "🟢")
    FAIR = ("一般", 0.5, "🟡")
    POOR = ("较差", 0.3, "🟠")
    CRITICAL = ("危险", 0.1, "🔴")
    FAILED = ("故障", 0.0, "⚫")


class FaultSeverity(Enum):
    """故障严重程度"""
    INFO = ("信息", 1)
    WARNING = ("警告", 2)
    ALARM = ("报警", 3)
    CRITICAL = ("严重", 4)
    EMERGENCY = ("紧急", 5)


class FaultCategory(Enum):
    """故障类别"""
    MECHANICAL = "机械故障"
    ELECTRICAL = "电气故障"
    HYDRAULIC = "水力故障"
    CONTROL = "控制故障"
    SENSOR = "传感器故障"
    ACTUATOR = "执行器故障"
    THERMAL = "热力故障"
    STRUCTURAL = "结构故障"


@dataclass
class DiagnosisResult:
    """诊断结果"""
    timestamp: datetime
    fault_detected: bool
    fault_type: Optional[str]
    fault_category: Optional[FaultCategory]
    severity: FaultSeverity
    confidence: float
    root_causes: List[str]
    affected_components: List[str]
    recommended_actions: List[str]
    time_to_failure: Optional[float]  # 小时
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthIndicator:
    """健康指标"""
    name: str
    current_value: float
    baseline_value: float
    threshold_warning: float
    threshold_alarm: float
    threshold_critical: float
    unit: str
    trend: str  # increasing, decreasing, stable
    degradation_rate: float  # 退化速率


class SignalProcessor:
    """信号处理器"""

    def __init__(self, sampling_rate: float = 1000.0):
        self.fs = sampling_rate

    def extract_features(self, signal: np.ndarray) -> Dict[str, float]:
        """提取信号特征"""
        features = {}

        # 时域特征
        features['mean'] = np.mean(signal)
        features['std'] = np.std(signal)
        features['rms'] = np.sqrt(np.mean(signal ** 2))
        features['peak'] = np.max(np.abs(signal))
        features['peak_to_peak'] = np.max(signal) - np.min(signal)
        features['crest_factor'] = features['peak'] / features['rms'] if features['rms'] > 0 else 0
        features['kurtosis'] = self._kurtosis(signal)
        features['skewness'] = self._skewness(signal)

        # 频域特征
        fft_result = np.fft.fft(signal)
        freq = np.fft.fftfreq(len(signal), 1 / self.fs)
        magnitude = np.abs(fft_result[:len(signal) // 2])
        freq_positive = freq[:len(signal) // 2]

        if len(magnitude) > 0:
            features['dominant_freq'] = freq_positive[np.argmax(magnitude)]
            features['spectral_centroid'] = np.sum(freq_positive * magnitude) / np.sum(magnitude) if np.sum(
                magnitude) > 0 else 0
            features['spectral_bandwidth'] = np.sqrt(
                np.sum(((freq_positive - features['spectral_centroid']) ** 2) * magnitude) / np.sum(
                    magnitude)) if np.sum(magnitude) > 0 else 0

        return features

    def _kurtosis(self, x: np.ndarray) -> float:
        n = len(x)
        mean = np.mean(x)
        std = np.std(x)
        if std == 0:
            return 0
        return np.sum((x - mean) ** 4) / (n * std ** 4) - 3

    def _skewness(self, x: np.ndarray) -> float:
        n = len(x)
        mean = np.mean(x)
        std = np.std(x)
        if std == 0:
            return 0
        return np.sum((x - mean) ** 3) / (n * std ** 3)

    def detect_anomaly(self, signal: np.ndarray, baseline: np.ndarray,
                       threshold: float = 3.0) -> Tuple[bool, float]:
        """检测信号异常"""
        features_current = self.extract_features(signal)
        features_baseline = self.extract_features(baseline)

        # 计算马氏距离
        deviations = []
        for key in features_current:
            if key in features_baseline and features_baseline[key] != 0:
                deviation = abs(features_current[key] - features_baseline[key]) / abs(features_baseline[key])
                deviations.append(deviation)

        if deviations:
            anomaly_score = np.mean(deviations)
            is_anomaly = anomaly_score > threshold
            return is_anomaly, anomaly_score

        return False, 0.0


class FaultDiagnoser:
    """故障诊断器"""

    def __init__(self):
        # 故障知识库
        self.fault_signatures = self._init_fault_signatures()

        # 历史数据缓存
        self.history = {
            'vibration': deque(maxlen=1000),
            'temperature': deque(maxlen=1000),
            'pressure': deque(maxlen=1000),
            'power': deque(maxlen=1000),
            'speed': deque(maxlen=1000)
        }

        # 信号处理器
        self.signal_processor = SignalProcessor()

    def _init_fault_signatures(self) -> Dict[str, Dict]:
        """初始化故障特征库"""
        return {
            # 机械故障
            'bearing_wear': {
                'category': FaultCategory.MECHANICAL,
                'indicators': {
                    'vibration_rms': {'threshold': 0.15, 'weight': 0.4},
                    'temperature_rise': {'threshold': 15, 'weight': 0.3},
                    'kurtosis': {'threshold': 4.0, 'weight': 0.3}
                },
                'severity_map': {0.3: FaultSeverity.WARNING, 0.6: FaultSeverity.ALARM, 0.8: FaultSeverity.CRITICAL}
            },
            'shaft_misalignment': {
                'category': FaultCategory.MECHANICAL,
                'indicators': {
                    'vibration_2x': {'threshold': 0.1, 'weight': 0.5},
                    'axial_vibration': {'threshold': 0.08, 'weight': 0.3},
                    'coupling_temperature': {'threshold': 10, 'weight': 0.2}
                },
                'severity_map': {0.3: FaultSeverity.WARNING, 0.5: FaultSeverity.ALARM, 0.7: FaultSeverity.CRITICAL}
            },
            'rotor_unbalance': {
                'category': FaultCategory.MECHANICAL,
                'indicators': {
                    'vibration_1x': {'threshold': 0.12, 'weight': 0.6},
                    'phase_stability': {'threshold': 10, 'weight': 0.4}
                },
                'severity_map': {0.4: FaultSeverity.WARNING, 0.6: FaultSeverity.ALARM, 0.8: FaultSeverity.CRITICAL}
            },

            # 水力故障
            'cavitation': {
                'category': FaultCategory.HYDRAULIC,
                'indicators': {
                    'high_freq_vibration': {'threshold': 0.05, 'weight': 0.4},
                    'noise_level': {'threshold': 95, 'weight': 0.3},
                    'pressure_fluctuation': {'threshold': 0.1, 'weight': 0.3}
                },
                'severity_map': {0.3: FaultSeverity.WARNING, 0.5: FaultSeverity.ALARM, 0.7: FaultSeverity.CRITICAL}
            },
            'draft_tube_vortex': {
                'category': FaultCategory.HYDRAULIC,
                'indicators': {
                    'low_freq_pressure': {'threshold': 0.15, 'weight': 0.5},
                    'power_swing': {'threshold': 0.05, 'weight': 0.3},
                    'partial_load': {'threshold': 0.5, 'weight': 0.2}
                },
                'severity_map': {0.4: FaultSeverity.WARNING, 0.6: FaultSeverity.ALARM}
            },

            # 电气故障
            'excitation_fault': {
                'category': FaultCategory.ELECTRICAL,
                'indicators': {
                    'voltage_fluctuation': {'threshold': 0.03, 'weight': 0.4},
                    'field_current_ripple': {'threshold': 0.05, 'weight': 0.3},
                    'reactive_power_swing': {'threshold': 0.1, 'weight': 0.3}
                },
                'severity_map': {0.3: FaultSeverity.WARNING, 0.5: FaultSeverity.ALARM, 0.8: FaultSeverity.CRITICAL}
            },
            'stator_winding_fault': {
                'category': FaultCategory.ELECTRICAL,
                'indicators': {
                    'partial_discharge': {'threshold': 100, 'weight': 0.4},
                    'winding_temperature': {'threshold': 20, 'weight': 0.3},
                    'current_unbalance': {'threshold': 0.05, 'weight': 0.3}
                },
                'severity_map': {0.4: FaultSeverity.WARNING, 0.6: FaultSeverity.ALARM, 0.8: FaultSeverity.CRITICAL}
            },

            # 控制故障
            'governor_instability': {
                'category': FaultCategory.CONTROL,
                'indicators': {
                    'power_oscillation': {'threshold': 0.03, 'weight': 0.4},
                    'guide_vane_hunting': {'threshold': 0.02, 'weight': 0.4},
                    'frequency_deviation': {'threshold': 0.1, 'weight': 0.2}
                },
                'severity_map': {0.3: FaultSeverity.WARNING, 0.5: FaultSeverity.ALARM}
            },
            'sensor_drift': {
                'category': FaultCategory.SENSOR,
                'indicators': {
                    'measurement_deviation': {'threshold': 0.05, 'weight': 0.5},
                    'noise_increase': {'threshold': 2.0, 'weight': 0.3},
                    'response_delay': {'threshold': 0.5, 'weight': 0.2}
                },
                'severity_map': {0.3: FaultSeverity.WARNING, 0.5: FaultSeverity.ALARM}
            }
        }

    def diagnose(self, measurements: Dict[str, float],
                 signals: Optional[Dict[str, np.ndarray]] = None) -> DiagnosisResult:
        """执行故障诊断"""
        detected_faults = []
        max_severity = FaultSeverity.INFO
        confidence = 0.0

        # 检查每种故障类型
        for fault_type, signature in self.fault_signatures.items():
            fault_score = 0.0
            total_weight = 0.0

            for indicator, config in signature['indicators'].items():
                if indicator in measurements:
                    value = measurements[indicator]
                    threshold = config['threshold']
                    weight = config['weight']

                    # 计算偏离程度
                    deviation = value / threshold if threshold != 0 else 0
                    fault_score += min(1.0, deviation) * weight
                    total_weight += weight

            if total_weight > 0:
                normalized_score = fault_score / total_weight

                # 确定严重程度
                severity = FaultSeverity.INFO
                for score_threshold, sev in sorted(signature['severity_map'].items()):
                    if normalized_score >= score_threshold:
                        severity = sev

                if normalized_score > 0.3:  # 故障检测阈值
                    detected_faults.append({
                        'type': fault_type,
                        'category': signature['category'],
                        'score': normalized_score,
                        'severity': severity
                    })

                    if severity.value[1] > max_severity.value[1]:
                        max_severity = severity
                        confidence = normalized_score

        # 构建诊断结果
        if detected_faults:
            # 按严重程度排序
            detected_faults.sort(key=lambda x: x['score'], reverse=True)
            primary_fault = detected_faults[0]

            root_causes = self._analyze_root_cause(primary_fault['type'], measurements)
            recommended_actions = self._get_recommendations(primary_fault['type'], primary_fault['severity'])
            affected = self._get_affected_components(primary_fault['type'])

            return DiagnosisResult(
                timestamp=datetime.now(),
                fault_detected=True,
                fault_type=primary_fault['type'],
                fault_category=primary_fault['category'],
                severity=primary_fault['severity'],
                confidence=primary_fault['score'],
                root_causes=root_causes,
                affected_components=affected,
                recommended_actions=recommended_actions,
                time_to_failure=self._estimate_ttf(primary_fault['type'], primary_fault['score']),
                details={'all_faults': detected_faults}
            )

        return DiagnosisResult(
            timestamp=datetime.now(),
            fault_detected=False,
            fault_type=None,
            fault_category=None,
            severity=FaultSeverity.INFO,
            confidence=1.0,
            root_causes=[],
            affected_components=[],
            recommended_actions=["继续正常运行", "保持常规监测"],
            time_to_failure=None
        )

    def _analyze_root_cause(self, fault_type: str, measurements: Dict) -> List[str]:
        """分析故障根因"""
        root_causes = {
            'bearing_wear': [
                "轴承润滑不良",
                "轴承疲劳磨损",
                "轴承安装不当",
                "过载运行导致"
            ],
            'shaft_misalignment': [
                "联轴器对中不良",
                "基础沉降",
                "热膨胀变形",
                "安装精度不足"
            ],
            'cavitation': [
                "运行水头过低",
                "吸出高度不足",
                "部分负荷运行",
                "进水条件恶化"
            ],
            'draft_tube_vortex': [
                "部分负荷运行(30-60%)",
                "水轮机设计不匹配",
                "尾水管形状不佳"
            ],
            'governor_instability': [
                "调速器参数整定不当",
                "水力系统惯性时间过大",
                "执行机构响应滞后",
                "反馈信号干扰"
            ]
        }
        return root_causes.get(fault_type, ["原因待分析"])

    def _get_recommendations(self, fault_type: str, severity: FaultSeverity) -> List[str]:
        """获取处理建议"""
        base_recommendations = {
            'bearing_wear': [
                "检查润滑油质量和油位",
                "分析振动频谱确认故障模式",
                "安排轴承检修更换",
                "调整运行工况降低负荷"
            ],
            'shaft_misalignment': [
                "进行激光对中检测",
                "检查联轴器状态",
                "检查基础沉降情况",
                "安排停机对中调整"
            ],
            'cavitation': [
                "提高运行水头或降低出力",
                "检查补气系统是否正常",
                "避开空化严重区域运行",
                "检查转轮空蚀情况"
            ],
            'governor_instability': [
                "检查调速器参数设置",
                "验证传感器工作正常",
                "检查执行机构响应",
                "必要时切换备用调速器"
            ]
        }

        recommendations = base_recommendations.get(fault_type, ["联系技术人员分析处理"])

        # 根据严重程度添加紧急建议
        if severity == FaultSeverity.CRITICAL:
            recommendations.insert(0, "⚠️ 立即降低负荷运行")
            recommendations.insert(1, "⚠️ 准备停机检修")
        elif severity == FaultSeverity.EMERGENCY:
            recommendations.insert(0, "🚨 立即执行紧急停机")
            recommendations.insert(1, "🚨 通知值班人员和领导")

        return recommendations

    def _get_affected_components(self, fault_type: str) -> List[str]:
        """获取受影响的组件"""
        affected_map = {
            'bearing_wear': ["推力轴承", "导轴承", "轴承座", "润滑系统"],
            'shaft_misalignment': ["主轴", "联轴器", "轴承", "密封"],
            'cavitation': ["转轮叶片", "尾水管", "底环", "顶盖"],
            'governor_instability': ["调速器", "导叶接力器", "主配压阀", "反馈机构"],
            'excitation_fault': ["励磁机", "灭磁开关", "励磁变", "AVR"]
        }
        return affected_map.get(fault_type, [])

    def _estimate_ttf(self, fault_type: str, severity_score: float) -> Optional[float]:
        """估算距离故障的时间（小时）"""
        # 基础估算（简化模型）
        base_ttf = {
            'bearing_wear': 2000,
            'shaft_misalignment': 5000,
            'cavitation': 1000,
            'governor_instability': 500
        }

        base = base_ttf.get(fault_type, 1000)

        # 根据严重程度调整
        ttf = base * (1 - severity_score) ** 2

        return max(1, ttf)


class PredictiveMaintenance:
    """预测性维护系统"""

    def __init__(self):
        self.health_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.degradation_models: Dict[str, Dict] = {}

    def update_health(self, component: str, health_value: float):
        """更新组件健康状态"""
        if component not in self.health_history:
            self.health_history[component] = []

        self.health_history[component].append((datetime.now(), health_value))

        # 保留最近1000个数据点
        if len(self.health_history[component]) > 1000:
            self.health_history[component] = self.health_history[component][-1000:]

    def predict_rul(self, component: str) -> Dict[str, Any]:
        """预测剩余使用寿命 (Remaining Useful Life)"""
        if component not in self.health_history or len(self.health_history[component]) < 10:
            return {
                'rul_hours': None,
                'confidence': 0,
                'message': "数据不足，无法预测"
            }

        # 提取健康值序列
        history = self.health_history[component]
        times = np.array([(t - history[0][0]).total_seconds() / 3600 for t, _ in history])
        healths = np.array([h for _, h in history])

        # 线性退化模型拟合
        if len(times) >= 3:
            coeffs = np.polyfit(times, healths, 1)
            degradation_rate = coeffs[0]  # 斜率

            if degradation_rate < 0:
                # 预测到达故障阈值(0.3)的时间
                current_health = healths[-1]
                failure_threshold = 0.3

                rul = (current_health - failure_threshold) / abs(degradation_rate)
                rul = max(0, rul)

                # 置信度基于数据量和拟合优度
                r_squared = self._calculate_r_squared(times, healths, coeffs)
                confidence = min(0.95, 0.5 + 0.4 * r_squared + 0.05 * min(1, len(times) / 100))

                return {
                    'rul_hours': rul,
                    'rul_days': rul / 24,
                    'confidence': confidence,
                    'degradation_rate': degradation_rate,
                    'current_health': current_health,
                    'maintenance_window': self._calculate_maintenance_window(rul)
                }

        return {
            'rul_hours': None,
            'confidence': 0,
            'message': "健康状态稳定，暂无退化趋势"
        }

    def _calculate_r_squared(self, x: np.ndarray, y: np.ndarray, coeffs: np.ndarray) -> float:
        """计算R²"""
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        return 1 - ss_res / ss_tot if ss_tot > 0 else 0

    def _calculate_maintenance_window(self, rul_hours: float) -> Dict[str, Any]:
        """计算维护窗口"""
        now = datetime.now()

        if rul_hours < 24:
            return {
                'urgency': 'IMMEDIATE',
                'recommended_date': now,
                'latest_date': now + timedelta(hours=rul_hours * 0.8),
                'message': "立即安排维护"
            }
        elif rul_hours < 168:  # 1周
            return {
                'urgency': 'HIGH',
                'recommended_date': now + timedelta(hours=rul_hours * 0.5),
                'latest_date': now + timedelta(hours=rul_hours * 0.8),
                'message': "本周内安排维护"
            }
        elif rul_hours < 720:  # 1月
            return {
                'urgency': 'MEDIUM',
                'recommended_date': now + timedelta(hours=rul_hours * 0.6),
                'latest_date': now + timedelta(hours=rul_hours * 0.9),
                'message': "本月内安排维护"
            }
        else:
            return {
                'urgency': 'LOW',
                'recommended_date': now + timedelta(hours=rul_hours * 0.7),
                'latest_date': now + timedelta(hours=rul_hours * 0.95),
                'message': "按计划安排维护"
            }

    def get_maintenance_plan(self) -> List[Dict[str, Any]]:
        """生成维护计划"""
        plan = []

        for component in self.health_history:
            rul_result = self.predict_rul(component)

            if rul_result.get('rul_hours'):
                window = rul_result.get('maintenance_window', {})
                plan.append({
                    'component': component,
                    'rul_hours': rul_result['rul_hours'],
                    'urgency': window.get('urgency', 'UNKNOWN'),
                    'recommended_date': window.get('recommended_date'),
                    'confidence': rul_result.get('confidence', 0)
                })

        # 按紧急程度排序
        urgency_order = {'IMMEDIATE': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'UNKNOWN': 4}
        plan.sort(key=lambda x: urgency_order.get(x['urgency'], 5))

        return plan


class HealthAssessment:
    """健康状态评估系统"""

    def __init__(self):
        self.component_weights = {
            'turbine': 0.25,
            'generator': 0.25,
            'governor': 0.15,
            'excitation': 0.10,
            'bearing': 0.10,
            'cooling': 0.05,
            'auxiliary': 0.05,
            'protection': 0.05
        }

    def assess_unit_health(self, component_health: Dict[str, float]) -> Dict[str, Any]:
        """评估机组整体健康状态"""
        total_score = 0.0
        total_weight = 0.0
        component_details = []

        for component, weight in self.component_weights.items():
            if component in component_health:
                health = component_health[component]
                total_score += health * weight
                total_weight += weight

                # 确定状态
                status = self._health_to_status(health)
                component_details.append({
                    'component': component,
                    'health': health,
                    'status': status,
                    'weight': weight
                })

        overall_health = total_score / total_weight if total_weight > 0 else 0
        overall_status = self._health_to_status(overall_health)

        # 识别薄弱环节
        weak_components = [c for c in component_details if c['health'] < 0.5]
        weak_components.sort(key=lambda x: x['health'])

        return {
            'overall_health': overall_health,
            'overall_status': overall_status,
            'component_details': component_details,
            'weak_components': weak_components[:3],
            'recommendations': self._generate_health_recommendations(overall_health, weak_components)
        }

    def _health_to_status(self, health: float) -> HealthStatus:
        """健康值转换为状态"""
        if health >= 0.9:
            return HealthStatus.EXCELLENT
        elif health >= 0.7:
            return HealthStatus.GOOD
        elif health >= 0.5:
            return HealthStatus.FAIR
        elif health >= 0.3:
            return HealthStatus.POOR
        elif health > 0:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.FAILED

    def _generate_health_recommendations(self, overall: float,
                                         weak: List[Dict]) -> List[str]:
        """生成健康改善建议"""
        recommendations = []

        if overall >= 0.8:
            recommendations.append("设备状态良好，保持当前维护策略")
        elif overall >= 0.6:
            recommendations.append("设备状态一般，建议加强巡检频率")
        else:
            recommendations.append("设备状态较差，建议安排全面检修")

        for comp in weak[:3]:
            recommendations.append(
                f"重点关注{comp['component']}，健康度仅{comp['health']*100:.1f}%"
            )

        return recommendations


def main():
    """演示智能诊断系统"""
    print("=" * 70)
    print("智能故障诊断与预测维护系统演示")
    print("=" * 70)

    # 创建诊断器
    diagnoser = FaultDiagnoser()

    # 模拟测量数据 - 正常情况
    print("\n场景1: 正常运行")
    measurements_normal = {
        'vibration_rms': 0.05,
        'temperature_rise': 5,
        'kurtosis': 2.5,
        'power_oscillation': 0.01
    }
    result = diagnoser.diagnose(measurements_normal)
    print(f"  故障检测: {'是' if result.fault_detected else '否'}")
    print(f"  严重程度: {result.severity.value[0]}")
    print(f"  建议: {result.recommended_actions[0]}")

    # 模拟测量数据 - 轴承磨损
    print("\n场景2: 轴承磨损预警")
    measurements_bearing = {
        'vibration_rms': 0.18,
        'temperature_rise': 18,
        'kurtosis': 5.2,
        'power_oscillation': 0.02
    }
    result = diagnoser.diagnose(measurements_bearing)
    print(f"  故障检测: {'是' if result.fault_detected else '否'}")
    if result.fault_detected:
        print(f"  故障类型: {result.fault_type}")
        print(f"  严重程度: {result.severity.value[0]}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  预计失效时间: {result.time_to_failure:.0f}小时")
        print(f"  根本原因:")
        for cause in result.root_causes[:3]:
            print(f"    - {cause}")
        print(f"  处理建议:")
        for action in result.recommended_actions[:3]:
            print(f"    - {action}")

    # 预测性维护演示
    print("\n预测性维护演示:")
    print("-" * 50)
    pm = PredictiveMaintenance()

    # 模拟健康退化
    for i in range(50):
        health = 1.0 - 0.005 * i + np.random.normal(0, 0.02)
        pm.update_health('thrust_bearing', max(0, min(1, health)))

    rul = pm.predict_rul('thrust_bearing')
    if rul['rul_hours']:
        print(f"  推力轴承剩余寿命: {rul['rul_hours']:.0f}小时 ({rul['rul_days']:.1f}天)")
        print(f"  预测置信度: {rul['confidence']*100:.1f}%")
        print(f"  维护建议: {rul['maintenance_window']['message']}")

    # 健康评估
    print("\n机组健康评估:")
    print("-" * 50)
    health_assessor = HealthAssessment()
    component_health = {
        'turbine': 0.85,
        'generator': 0.90,
        'governor': 0.75,
        'excitation': 0.95,
        'bearing': 0.60,
        'cooling': 0.88,
        'auxiliary': 0.92,
        'protection': 0.98
    }

    assessment = health_assessor.assess_unit_health(component_health)
    print(f"  整体健康度: {assessment['overall_health']*100:.1f}%")
    print(f"  整体状态: {assessment['overall_status'].value[0]} {assessment['overall_status'].value[2]}")

    print("  薄弱环节:")
    for weak in assessment['weak_components']:
        status = weak['status']
        print(f"    - {weak['component']}: {weak['health']*100:.1f}% {status.value[2]}")

    print("  改善建议:")
    for rec in assessment['recommendations']:
        print(f"    - {rec}")

    print("\n" + "=" * 70)
    print("智能诊断系统演示完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
