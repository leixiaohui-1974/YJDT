# -*- coding: utf-8 -*-
"""
场景数据适配器 - Scenario Data Adapter

功能：
- 运行数据采集与场景匹配
- 基于历史数据的场景生成
- 场景库与实际运行数据对接
- 数据驱动的场景参数优化
- 场景验证与校准

设计目标：
- 将真实运行数据转化为仿真场景
- 验证场景库的真实性
- 持续优化场景参数
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
import threading
import time
import logging
from collections import deque

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """数据源类型"""
    SCADA = "scada"
    HISTORIAN = "historian"
    FILE = "file"
    SIMULATION = "simulation"
    MANUAL = "manual"


class ScenarioCategory(Enum):
    """场景类别"""
    NORMAL_OPERATION = "normal_operation"       # 正常运行
    LOAD_CHANGE = "load_change"                 # 负荷变化
    FAULT = "fault"                             # 故障
    EXTREME_WEATHER = "extreme_weather"         # 极端天气
    EMERGENCY = "emergency"                     # 紧急情况
    STARTUP_SHUTDOWN = "startup_shutdown"       # 启停机
    MAINTENANCE = "maintenance"                 # 维护工况
    GLACIER_MELT = "glacier_melt"               # 冰川融水
    SEISMIC = "seismic"                         # 地震
    FLOOD = "flood"                             # 洪水


@dataclass
class OperationalRecord:
    """运行记录"""
    timestamp: datetime
    duration: float  # 持续时间（秒）

    # 水力参数
    upstream_level: float = 0.0      # 上游水位 m
    downstream_level: float = 0.0    # 下游水位 m
    head: float = 0.0                # 水头 m
    flow_rate: float = 0.0           # 流量 m³/s
    inflow: float = 0.0              # 入流 m³/s

    # 电气参数
    power: float = 0.0               # 功率 MW
    frequency: float = 50.0          # 频率 Hz
    voltage: float = 0.0             # 电压 kV

    # 机械参数
    guide_vane_opening: float = 0.0  # 导叶开度 %
    rotation_speed: float = 0.0      # 转速 rpm
    vibration: float = 0.0           # 振动 mm/s

    # 环境参数
    temperature: float = 0.0         # 温度 ℃
    pressure: float = 0.0            # 压力 bar

    # 元数据
    source: DataSourceType = DataSourceType.SCADA
    quality: float = 1.0             # 数据质量 0-1
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioMatch:
    """场景匹配结果"""
    scenario_id: str
    scenario_name: str
    category: ScenarioCategory
    confidence: float              # 匹配置信度 0-1
    matched_features: List[str]    # 匹配的特征
    parameter_deviation: Dict[str, float]  # 参数偏差
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GeneratedScenario:
    """生成的场景"""
    scenario_id: str
    name: str
    category: ScenarioCategory
    source_records: List[str]      # 源记录ID

    # 场景参数
    initial_conditions: Dict[str, float]
    boundary_conditions: Dict[str, List[float]]
    duration: float                # 持续时间
    time_series: Dict[str, List[float]]  # 时间序列数据

    # 元信息
    generation_method: str
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)
    validated: bool = False


class OperationalDataCollector:
    """
    运行数据采集器

    从各种数据源采集运行数据，进行预处理和存储
    """

    def __init__(self, buffer_size: int = 100000):
        self._buffer_size = buffer_size
        self._data_buffer: deque = deque(maxlen=buffer_size)
        self._lock = threading.Lock()

        # 数据源
        self._data_sources: Dict[str, Any] = {}

        # 采集配置
        self._sampling_interval = 1.0  # 秒
        self._running = False
        self._collect_thread: Optional[threading.Thread] = None

        # 数据处理
        self._preprocessors: List[Callable] = []
        self._filters: List[Callable] = []

        # 统计
        self._stats = {
            'total_records': 0,
            'dropped_records': 0,
            'last_collect_time': None,
        }

    def add_data_source(self, name: str, source: Any):
        """添加数据源"""
        self._data_sources[name] = source

    def add_preprocessor(self, func: Callable[[OperationalRecord], OperationalRecord]):
        """添加预处理器"""
        self._preprocessors.append(func)

    def add_filter(self, func: Callable[[OperationalRecord], bool]):
        """添加过滤器"""
        self._filters.append(func)

    def start_collection(self, interval: float = 1.0):
        """启动采集"""
        self._sampling_interval = interval
        self._running = True

        self._collect_thread = threading.Thread(
            target=self._collection_loop,
            name="DataCollector"
        )
        self._collect_thread.daemon = True
        self._collect_thread.start()

        logger.info(f"Data collection started, interval={interval}s")

    def stop_collection(self):
        """停止采集"""
        self._running = False
        if self._collect_thread:
            self._collect_thread.join(timeout=5.0)
        logger.info("Data collection stopped")

    def _collection_loop(self):
        """采集循环"""
        while self._running:
            try:
                # 从各数据源采集
                for source_name, source in self._data_sources.items():
                    record = self._collect_from_source(source_name, source)
                    if record:
                        self._process_and_store(record)

                self._stats['last_collect_time'] = datetime.now()
            except Exception as e:
                logger.error(f"Collection error: {e}")

            time.sleep(self._sampling_interval)

    def _collect_from_source(self, name: str, source: Any) -> Optional[OperationalRecord]:
        """从单个数据源采集"""
        try:
            # 根据数据源类型采集
            if hasattr(source, 'read_multiple'):
                # 使用DataConnector
                tags = [
                    'upstream_level', 'downstream_level', 'flow_rate',
                    'power', 'frequency', 'guide_vane_opening',
                ]
                data = source.read_multiple(tags)

                return OperationalRecord(
                    timestamp=datetime.now(),
                    duration=self._sampling_interval,
                    upstream_level=data.get('upstream_level', {}).value if 'upstream_level' in data else 0,
                    downstream_level=data.get('downstream_level', {}).value if 'downstream_level' in data else 0,
                    flow_rate=data.get('flow_rate', {}).value if 'flow_rate' in data else 0,
                    power=data.get('power', {}).value if 'power' in data else 0,
                    frequency=data.get('frequency', {}).value if 'frequency' in data else 50.0,
                    guide_vane_opening=data.get('guide_vane_opening', {}).value if 'guide_vane_opening' in data else 0,
                    source=DataSourceType.SCADA,
                )

            elif hasattr(source, 'get_current_state'):
                # 使用仿真引擎
                state = source.get_current_state()
                return OperationalRecord(
                    timestamp=datetime.now(),
                    duration=self._sampling_interval,
                    source=DataSourceType.SIMULATION,
                    **state
                )

        except Exception as e:
            logger.error(f"Error collecting from {name}: {e}")

        return None

    def _process_and_store(self, record: OperationalRecord):
        """处理并存储记录"""
        # 应用过滤器
        for filter_func in self._filters:
            if not filter_func(record):
                self._stats['dropped_records'] += 1
                return

        # 应用预处理器
        for preprocessor in self._preprocessors:
            record = preprocessor(record)

        # 存储
        with self._lock:
            self._data_buffer.append(record)
            self._stats['total_records'] += 1

    def add_record(self, record: OperationalRecord):
        """手动添加记录"""
        self._process_and_store(record)

    def get_records(self, start_time: datetime = None,
                    end_time: datetime = None,
                    limit: int = None) -> List[OperationalRecord]:
        """获取记录"""
        with self._lock:
            records = list(self._data_buffer)

        if start_time:
            records = [r for r in records if r.timestamp >= start_time]
        if end_time:
            records = [r for r in records if r.timestamp <= end_time]
        if limit:
            records = records[-limit:]

        return records

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            'buffer_size': len(self._data_buffer),
            'sources': list(self._data_sources.keys()),
        }

    def export_to_csv(self, filepath: str, records: List[OperationalRecord] = None):
        """导出到CSV"""
        import csv

        if records is None:
            records = self.get_records()

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # 写入头部
            headers = [
                'timestamp', 'upstream_level', 'downstream_level', 'head',
                'flow_rate', 'inflow', 'power', 'frequency', 'voltage',
                'guide_vane_opening', 'rotation_speed', 'vibration',
                'temperature', 'quality'
            ]
            writer.writerow(headers)

            # 写入数据
            for record in records:
                row = [
                    record.timestamp.isoformat(),
                    record.upstream_level,
                    record.downstream_level,
                    record.head,
                    record.flow_rate,
                    record.inflow,
                    record.power,
                    record.frequency,
                    record.voltage,
                    record.guide_vane_opening,
                    record.rotation_speed,
                    record.vibration,
                    record.temperature,
                    record.quality,
                ]
                writer.writerow(row)


class ScenarioMatcher:
    """
    场景匹配器

    将运行数据与场景库中的场景进行匹配
    """

    def __init__(self):
        # 场景库
        self._scenario_library: Dict[str, Dict] = {}

        # 特征提取器
        self._feature_extractors: Dict[str, Callable] = {}

        # 匹配阈值
        self._confidence_threshold = 0.7

        # 注册默认特征提取器
        self._register_default_extractors()

    def _register_default_extractors(self):
        """注册默认特征提取器"""

        def extract_load_level(records: List[OperationalRecord]) -> str:
            avg_power = np.mean([r.power for r in records])
            if avg_power < 50:
                return "low"
            elif avg_power < 150:
                return "medium"
            else:
                return "high"

        def extract_flow_pattern(records: List[OperationalRecord]) -> str:
            flows = [r.flow_rate for r in records]
            if len(flows) < 2:
                return "stable"

            change_rate = (max(flows) - min(flows)) / (np.mean(flows) + 1e-6)
            if change_rate < 0.1:
                return "stable"
            elif change_rate < 0.3:
                return "varying"
            else:
                return "rapid_change"

        def extract_frequency_deviation(records: List[OperationalRecord]) -> str:
            freqs = [r.frequency for r in records]
            deviation = np.std(freqs)
            if deviation < 0.01:
                return "normal"
            elif deviation < 0.05:
                return "slight_deviation"
            else:
                return "significant_deviation"

        self._feature_extractors['load_level'] = extract_load_level
        self._feature_extractors['flow_pattern'] = extract_flow_pattern
        self._feature_extractors['frequency_deviation'] = extract_frequency_deviation

    def register_scenario(self, scenario_id: str, scenario_def: Dict):
        """
        注册场景

        Args:
            scenario_id: 场景ID
            scenario_def: 场景定义，包含特征和参数范围
        """
        self._scenario_library[scenario_id] = scenario_def

    def load_scenario_library(self, library_path: str = None):
        """加载场景库"""
        # 加载雅江场景库
        try:
            from yjdt.scenarios.yajiang_scenarios import YajiangScenarioLibrary
            yajiang_lib = YajiangScenarioLibrary()

            for category in ['normal', 'extreme', 'emergency']:
                scenarios = yajiang_lib.get_scenarios_by_category(category)
                for scenario in scenarios:
                    self._scenario_library[scenario.scenario_id] = {
                        'name': scenario.name,
                        'category': category,
                        'description': scenario.description,
                        'parameters': scenario.parameters,
                        'features': scenario.features if hasattr(scenario, 'features') else {},
                    }

            logger.info(f"Loaded {len(self._scenario_library)} scenarios")
        except Exception as e:
            logger.warning(f"Could not load scenario library: {e}")

        # 注册一些默认场景
        self._register_default_scenarios()

    def _register_default_scenarios(self):
        """注册默认场景"""
        default_scenarios = {
            'normal_steady': {
                'name': '稳态运行',
                'category': ScenarioCategory.NORMAL_OPERATION,
                'features': {
                    'load_level': ['low', 'medium', 'high'],
                    'flow_pattern': ['stable'],
                    'frequency_deviation': ['normal'],
                },
                'parameters': {
                    'power_range': (50, 200),
                    'frequency_range': (49.95, 50.05),
                }
            },
            'load_increase': {
                'name': '负荷增加',
                'category': ScenarioCategory.LOAD_CHANGE,
                'features': {
                    'flow_pattern': ['varying', 'rapid_change'],
                },
                'parameters': {
                    'power_change_rate': (0.1, 1.0),  # MW/s
                }
            },
            'load_decrease': {
                'name': '负荷减少',
                'category': ScenarioCategory.LOAD_CHANGE,
                'features': {
                    'flow_pattern': ['varying', 'rapid_change'],
                },
                'parameters': {
                    'power_change_rate': (-1.0, -0.1),
                }
            },
            'frequency_disturbance': {
                'name': '频率扰动',
                'category': ScenarioCategory.FAULT,
                'features': {
                    'frequency_deviation': ['slight_deviation', 'significant_deviation'],
                },
                'parameters': {
                    'frequency_range': (49.5, 50.5),
                }
            },
            'glacier_melt_surge': {
                'name': '冰川融水涌浪',
                'category': ScenarioCategory.GLACIER_MELT,
                'features': {
                    'flow_pattern': ['rapid_change'],
                },
                'parameters': {
                    'flow_surge_ratio': (1.5, 3.0),
                }
            },
        }

        for scenario_id, scenario_def in default_scenarios.items():
            if scenario_id not in self._scenario_library:
                self._scenario_library[scenario_id] = scenario_def

    def add_feature_extractor(self, name: str, extractor: Callable):
        """添加特征提取器"""
        self._feature_extractors[name] = extractor

    def extract_features(self, records: List[OperationalRecord]) -> Dict[str, Any]:
        """提取特征"""
        features = {}
        for name, extractor in self._feature_extractors.items():
            try:
                features[name] = extractor(records)
            except Exception as e:
                logger.error(f"Feature extraction error for {name}: {e}")
        return features

    def match(self, records: List[OperationalRecord]) -> List[ScenarioMatch]:
        """
        匹配场景

        Args:
            records: 运行记录

        Returns:
            匹配结果列表（按置信度排序）
        """
        if not records:
            return []

        # 提取特征
        extracted_features = self.extract_features(records)

        matches = []

        for scenario_id, scenario_def in self._scenario_library.items():
            confidence, matched_features = self._calculate_match_score(
                extracted_features, scenario_def.get('features', {})
            )

            if confidence >= self._confidence_threshold:
                # 计算参数偏差
                param_deviation = self._calculate_parameter_deviation(
                    records, scenario_def.get('parameters', {})
                )

                category = scenario_def.get('category', ScenarioCategory.NORMAL_OPERATION)
                if isinstance(category, str):
                    try:
                        category = ScenarioCategory(category)
                    except:
                        category = ScenarioCategory.NORMAL_OPERATION

                matches.append(ScenarioMatch(
                    scenario_id=scenario_id,
                    scenario_name=scenario_def.get('name', scenario_id),
                    category=category,
                    confidence=confidence,
                    matched_features=matched_features,
                    parameter_deviation=param_deviation,
                ))

        # 按置信度排序
        matches.sort(key=lambda x: x.confidence, reverse=True)

        return matches

    def _calculate_match_score(self, extracted: Dict[str, Any],
                               expected: Dict[str, Any]) -> Tuple[float, List[str]]:
        """计算匹配分数"""
        if not expected:
            return 0.5, []

        matched = []
        total_features = len(expected)

        for feature_name, expected_values in expected.items():
            if feature_name in extracted:
                actual = extracted[feature_name]
                if isinstance(expected_values, list):
                    if actual in expected_values:
                        matched.append(feature_name)
                elif actual == expected_values:
                    matched.append(feature_name)

        if total_features == 0:
            return 0.5, []

        confidence = len(matched) / total_features
        return confidence, matched

    def _calculate_parameter_deviation(self, records: List[OperationalRecord],
                                        parameters: Dict[str, Tuple]) -> Dict[str, float]:
        """计算参数偏差"""
        deviation = {}

        # 获取记录的统计值
        powers = [r.power for r in records]
        freqs = [r.frequency for r in records]
        flows = [r.flow_rate for r in records]

        if 'power_range' in parameters:
            expected_min, expected_max = parameters['power_range']
            actual = np.mean(powers)
            if actual < expected_min:
                deviation['power'] = (expected_min - actual) / expected_min
            elif actual > expected_max:
                deviation['power'] = (actual - expected_max) / expected_max
            else:
                deviation['power'] = 0.0

        if 'frequency_range' in parameters:
            expected_min, expected_max = parameters['frequency_range']
            actual = np.mean(freqs)
            if actual < expected_min:
                deviation['frequency'] = (expected_min - actual) / expected_min
            elif actual > expected_max:
                deviation['frequency'] = (actual - expected_max) / expected_max
            else:
                deviation['frequency'] = 0.0

        return deviation

    def get_scenario(self, scenario_id: str) -> Optional[Dict]:
        """获取场景定义"""
        return self._scenario_library.get(scenario_id)


class DataDrivenScenarioGenerator:
    """
    数据驱动场景生成器

    基于历史运行数据自动生成仿真场景
    """

    def __init__(self, collector: OperationalDataCollector = None):
        self._collector = collector or OperationalDataCollector()
        self._generated_scenarios: Dict[str, GeneratedScenario] = {}

        # 场景检测参数
        self._event_detection_window = 60  # 秒
        self._anomaly_threshold = 2.0      # 标准差倍数

        # 生成计数
        self._generation_count = 0

    def detect_events(self, records: List[OperationalRecord]) -> List[Dict]:
        """
        检测事件

        从运行数据中检测显著事件

        Args:
            records: 运行记录

        Returns:
            检测到的事件列表
        """
        if len(records) < 10:
            return []

        events = []

        # 分析各参数
        powers = np.array([r.power for r in records])
        flows = np.array([r.flow_rate for r in records])
        freqs = np.array([r.frequency for r in records])

        # 检测功率突变
        power_diff = np.diff(powers)
        power_std = np.std(power_diff)
        power_anomalies = np.where(np.abs(power_diff) > self._anomaly_threshold * power_std)[0]

        for idx in power_anomalies:
            events.append({
                'type': 'power_change',
                'timestamp': records[idx + 1].timestamp,
                'magnitude': power_diff[idx],
                'duration': self._event_detection_window,
                'indices': (idx, min(idx + 10, len(records) - 1)),
            })

        # 检测流量突变
        flow_diff = np.diff(flows)
        flow_std = np.std(flow_diff)
        flow_anomalies = np.where(np.abs(flow_diff) > self._anomaly_threshold * flow_std)[0]

        for idx in flow_anomalies:
            events.append({
                'type': 'flow_change',
                'timestamp': records[idx + 1].timestamp,
                'magnitude': flow_diff[idx],
                'indices': (idx, min(idx + 10, len(records) - 1)),
            })

        # 检测频率偏差
        freq_deviation = np.abs(freqs - 50.0)
        freq_anomalies = np.where(freq_deviation > 0.1)[0]

        if len(freq_anomalies) > 0:
            # 合并连续的偏差
            start_idx = freq_anomalies[0]
            events.append({
                'type': 'frequency_deviation',
                'timestamp': records[start_idx].timestamp,
                'magnitude': float(np.max(freq_deviation[freq_anomalies])),
                'indices': (start_idx, min(freq_anomalies[-1] + 1, len(records) - 1)),
            })

        return events

    def generate_scenario_from_event(self, records: List[OperationalRecord],
                                      event: Dict) -> GeneratedScenario:
        """
        从事件生成场景

        Args:
            records: 运行记录
            event: 检测到的事件

        Returns:
            生成的场景
        """
        self._generation_count += 1

        start_idx, end_idx = event.get('indices', (0, len(records) - 1))
        event_records = records[start_idx:end_idx + 1]

        # 确定场景类别
        event_type = event.get('type', 'unknown')
        if event_type == 'power_change':
            if event.get('magnitude', 0) > 0:
                category = ScenarioCategory.LOAD_CHANGE
                name = f"负荷增加场景_{self._generation_count}"
            else:
                category = ScenarioCategory.LOAD_CHANGE
                name = f"负荷减少场景_{self._generation_count}"
        elif event_type == 'flow_change':
            category = ScenarioCategory.GLACIER_MELT
            name = f"流量变化场景_{self._generation_count}"
        elif event_type == 'frequency_deviation':
            category = ScenarioCategory.FAULT
            name = f"频率扰动场景_{self._generation_count}"
        else:
            category = ScenarioCategory.NORMAL_OPERATION
            name = f"运行场景_{self._generation_count}"

        # 提取初始条件
        first_record = event_records[0]
        initial_conditions = {
            'upstream_level': first_record.upstream_level,
            'downstream_level': first_record.downstream_level,
            'head': first_record.head,
            'flow_rate': first_record.flow_rate,
            'power': first_record.power,
            'frequency': first_record.frequency,
            'guide_vane_opening': first_record.guide_vane_opening,
        }

        # 提取时间序列
        time_series = {
            'power': [r.power for r in event_records],
            'flow_rate': [r.flow_rate for r in event_records],
            'frequency': [r.frequency for r in event_records],
            'guide_vane_opening': [r.guide_vane_opening for r in event_records],
        }

        # 计算持续时间
        if len(event_records) > 1:
            duration = (event_records[-1].timestamp - event_records[0].timestamp).total_seconds()
        else:
            duration = event_records[0].duration

        # 提取边界条件
        boundary_conditions = {
            'inflow': [r.inflow for r in event_records],
        }

        scenario = GeneratedScenario(
            scenario_id=f"gen_{self._generation_count:06d}",
            name=name,
            category=category,
            source_records=[str(r.timestamp) for r in event_records],
            initial_conditions=initial_conditions,
            boundary_conditions=boundary_conditions,
            duration=duration,
            time_series=time_series,
            generation_method='event_detection',
            confidence=0.8,
        )

        self._generated_scenarios[scenario.scenario_id] = scenario
        return scenario

    def generate_from_data(self, records: List[OperationalRecord] = None,
                           min_duration: float = 60.0) -> List[GeneratedScenario]:
        """
        从数据生成场景

        Args:
            records: 运行记录（如果为None则从collector获取）
            min_duration: 最小场景持续时间

        Returns:
            生成的场景列表
        """
        if records is None:
            records = self._collector.get_records()

        if not records:
            return []

        # 检测事件
        events = self.detect_events(records)

        scenarios = []
        for event in events:
            scenario = self.generate_scenario_from_event(records, event)
            if scenario.duration >= min_duration:
                scenarios.append(scenario)

        logger.info(f"Generated {len(scenarios)} scenarios from {len(records)} records")
        return scenarios

    def generate_typical_scenarios(self, records: List[OperationalRecord],
                                    n_clusters: int = 5) -> List[GeneratedScenario]:
        """
        生成典型运行场景

        使用聚类方法识别典型运行工况

        Args:
            records: 运行记录
            n_clusters: 聚类数量

        Returns:
            典型场景列表
        """
        if len(records) < n_clusters:
            return []

        # 提取特征向量
        features = np.array([
            [r.power, r.flow_rate, r.frequency, r.guide_vane_opening]
            for r in records
        ])

        # 标准化
        mean = np.mean(features, axis=0)
        std = np.std(features, axis=0) + 1e-6
        normalized = (features - mean) / std

        # K-means聚类
        from yjdt.ai.deep_diagnosis import IsolationForest  # 复用现有模块
        centroids = self._kmeans_clustering(normalized, n_clusters)

        # 为每个聚类中心生成典型场景
        scenarios = []
        for i, centroid in enumerate(centroids):
            # 反标准化
            params = centroid * std + mean

            self._generation_count += 1
            scenario = GeneratedScenario(
                scenario_id=f"typical_{i+1:03d}",
                name=f"典型工况{i+1}",
                category=ScenarioCategory.NORMAL_OPERATION,
                source_records=[],
                initial_conditions={
                    'power': float(params[0]),
                    'flow_rate': float(params[1]),
                    'frequency': float(params[2]),
                    'guide_vane_opening': float(params[3]),
                },
                boundary_conditions={},
                duration=3600,  # 1小时
                time_series={},
                generation_method='clustering',
                confidence=0.7,
            )
            scenarios.append(scenario)
            self._generated_scenarios[scenario.scenario_id] = scenario

        return scenarios

    def _kmeans_clustering(self, data: np.ndarray, k: int,
                            max_iter: int = 100) -> np.ndarray:
        """简单K-means实现"""
        n_samples = len(data)

        # 随机初始化中心
        indices = np.random.choice(n_samples, k, replace=False)
        centroids = data[indices].copy()

        for _ in range(max_iter):
            # 分配样本到最近的中心
            distances = np.zeros((n_samples, k))
            for i, centroid in enumerate(centroids):
                distances[:, i] = np.linalg.norm(data - centroid, axis=1)

            labels = np.argmin(distances, axis=1)

            # 更新中心
            new_centroids = np.zeros_like(centroids)
            for i in range(k):
                mask = labels == i
                if np.sum(mask) > 0:
                    new_centroids[i] = np.mean(data[mask], axis=0)
                else:
                    new_centroids[i] = centroids[i]

            # 检查收敛
            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids

        return centroids

    def get_generated_scenarios(self) -> List[GeneratedScenario]:
        """获取所有生成的场景"""
        return list(self._generated_scenarios.values())

    def export_scenario(self, scenario_id: str, format: str = 'yaml') -> str:
        """
        导出场景

        Args:
            scenario_id: 场景ID
            format: 导出格式（yaml, json）

        Returns:
            导出内容
        """
        scenario = self._generated_scenarios.get(scenario_id)
        if not scenario:
            return ""

        scenario_dict = {
            'scenario_id': scenario.scenario_id,
            'name': scenario.name,
            'category': scenario.category.value,
            'initial_conditions': scenario.initial_conditions,
            'boundary_conditions': scenario.boundary_conditions,
            'duration': scenario.duration,
            'time_series': scenario.time_series,
            'generation_method': scenario.generation_method,
            'confidence': scenario.confidence,
            'created_at': scenario.created_at.isoformat(),
        }

        if format == 'yaml':
            import yaml
            return yaml.dump(scenario_dict, allow_unicode=True, default_flow_style=False)
        else:
            import json
            return json.dumps(scenario_dict, ensure_ascii=False, indent=2)


class ScenarioDataAdapter:
    """
    场景数据适配器

    综合管理运行数据采集、场景匹配和场景生成
    """

    def __init__(self):
        self.collector = OperationalDataCollector()
        self.matcher = ScenarioMatcher()
        self.generator = DataDrivenScenarioGenerator(self.collector)

        # 自动匹配配置
        self._auto_match_enabled = False
        self._auto_match_interval = 60  # 秒
        self._match_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 匹配历史
        self._match_history: List[ScenarioMatch] = []

    def initialize(self, data_sources: Dict[str, Any] = None):
        """初始化适配器"""
        # 加载场景库
        self.matcher.load_scenario_library()

        # 配置数据源
        if data_sources:
            for name, source in data_sources.items():
                self.collector.add_data_source(name, source)

        logger.info("Scenario data adapter initialized")

    def start(self, auto_match: bool = True, collect_interval: float = 1.0):
        """
        启动适配器

        Args:
            auto_match: 是否启用自动场景匹配
            collect_interval: 数据采集间隔
        """
        # 启动数据采集
        self.collector.start_collection(collect_interval)

        # 启动自动匹配
        if auto_match:
            self._start_auto_matching()

    def stop(self):
        """停止适配器"""
        self.collector.stop_collection()
        self._stop_auto_matching()

    def _start_auto_matching(self):
        """启动自动匹配"""
        self._auto_match_enabled = True
        self._stop_event.clear()

        self._match_thread = threading.Thread(
            target=self._auto_match_loop,
            name="ScenarioMatcher"
        )
        self._match_thread.daemon = True
        self._match_thread.start()

    def _stop_auto_matching(self):
        """停止自动匹配"""
        self._auto_match_enabled = False
        self._stop_event.set()
        if self._match_thread:
            self._match_thread.join(timeout=5.0)

    def _auto_match_loop(self):
        """自动匹配循环"""
        while not self._stop_event.is_set():
            try:
                # 获取最近的记录
                records = self.collector.get_records(limit=100)

                if records:
                    # 匹配场景
                    matches = self.matcher.match(records)

                    if matches:
                        best_match = matches[0]
                        self._match_history.append(best_match)

                        if best_match.confidence > 0.9:
                            logger.info(
                                f"High confidence match: {best_match.scenario_name} "
                                f"({best_match.confidence:.2f})"
                            )

            except Exception as e:
                logger.error(f"Auto-match error: {e}")

            self._stop_event.wait(self._auto_match_interval)

    def match_current_operation(self) -> List[ScenarioMatch]:
        """匹配当前运行状态"""
        records = self.collector.get_records(limit=100)
        return self.matcher.match(records)

    def generate_scenarios_from_history(self,
                                         start_time: datetime = None,
                                         end_time: datetime = None) -> List[GeneratedScenario]:
        """从历史数据生成场景"""
        records = self.collector.get_records(start_time, end_time)
        return self.generator.generate_from_data(records)

    def get_match_history(self, limit: int = 100) -> List[ScenarioMatch]:
        """获取匹配历史"""
        return self._match_history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            'collector': self.collector.get_stats(),
            'scenarios_loaded': len(self.matcher._scenario_library),
            'scenarios_generated': len(self.generator._generated_scenarios),
            'match_history_count': len(self._match_history),
            'auto_match_enabled': self._auto_match_enabled,
        }

    def add_manual_record(self, record: OperationalRecord):
        """添加手动记录"""
        self.collector.add_record(record)

    def validate_scenario(self, scenario_id: str,
                          validation_records: List[OperationalRecord]) -> Dict[str, Any]:
        """
        验证场景

        使用实际运行数据验证场景的真实性

        Args:
            scenario_id: 场景ID
            validation_records: 验证数据

        Returns:
            验证结果
        """
        scenario = self.generator._generated_scenarios.get(scenario_id)
        if not scenario:
            return {'valid': False, 'error': 'Scenario not found'}

        # 计算参数偏差
        if not validation_records:
            return {'valid': False, 'error': 'No validation data'}

        # 比较初始条件
        first_record = validation_records[0]
        initial_deviation = {}

        for param, expected in scenario.initial_conditions.items():
            if hasattr(first_record, param):
                actual = getattr(first_record, param)
                if expected != 0:
                    deviation = abs(actual - expected) / abs(expected)
                else:
                    deviation = abs(actual)
                initial_deviation[param] = deviation

        # 计算平均偏差
        avg_deviation = np.mean(list(initial_deviation.values())) if initial_deviation else 1.0

        return {
            'valid': avg_deviation < 0.2,  # 20%以内认为有效
            'scenario_id': scenario_id,
            'average_deviation': avg_deviation,
            'parameter_deviations': initial_deviation,
            'validation_records': len(validation_records),
        }


def create_yajiang_data_adapter() -> ScenarioDataAdapter:
    """
    创建雅江梯级数据适配器

    Returns:
        配置好的适配器
    """
    adapter = ScenarioDataAdapter()

    # 添加特定的特征提取器
    def extract_altitude_effect(records: List[OperationalRecord]) -> str:
        """提取高海拔效应"""
        # 根据温度和气压判断
        avg_temp = np.mean([r.temperature for r in records])
        if avg_temp < 5:
            return "severe"
        elif avg_temp < 15:
            return "moderate"
        else:
            return "mild"

    adapter.matcher.add_feature_extractor('altitude_effect', extract_altitude_effect)

    # 添加数据质量过滤器
    def quality_filter(record: OperationalRecord) -> bool:
        return record.quality >= 0.8

    adapter.collector.add_filter(quality_filter)

    return adapter
