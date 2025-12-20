"""
传感器布设优化模块
Sensor Placement Optimization Module

实现传感器最优布设：
- 可观测性分析
- 故障可诊断性
- 冗余配置优化
- 成本效益分析
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from scipy.optimize import minimize, differential_evolution
from scipy.linalg import matrix_rank


class SensorType(Enum):
    """传感器类型"""
    PRESSURE = "pressure"
    FLOW = "flow"
    LEVEL = "level"
    SPEED = "speed"
    POWER = "power"
    TEMPERATURE = "temperature"
    VIBRATION = "vibration"
    POSITION = "position"
    VOLTAGE = "voltage"
    CURRENT = "current"
    STRAIN = "strain"
    ACCELERATION = "acceleration"


class MeasurementLocation(Enum):
    """测量位置"""
    # 水力系统
    PENSTOCK_INLET = "penstock_inlet"
    PENSTOCK_OUTLET = "penstock_outlet"
    SURGE_TANK = "surge_tank"
    SPIRAL_CASE = "spiral_case"
    DRAFT_TUBE = "draft_tube"

    # 水轮机
    GUIDE_VANE = "guide_vane"
    RUNNER = "runner"
    MAIN_SHAFT = "main_shaft"
    THRUST_BEARING = "thrust_bearing"
    GUIDE_BEARING = "guide_bearing"

    # 发电机
    STATOR = "stator"
    ROTOR = "rotor"
    EXCITER = "exciter"
    TERMINAL = "terminal"

    # 辅助系统
    COOLING_WATER = "cooling_water"
    OIL_SYSTEM = "oil_system"
    GOVERNOR = "governor"


@dataclass
class SensorSpec:
    """传感器规格"""
    sensor_type: SensorType
    location: MeasurementLocation
    name: str
    accuracy: float = 0.01
    range_min: float = 0.0
    range_max: float = 100.0
    cost: float = 1000.0  # 元
    mtbf: float = 50000.0  # 平均故障间隔时间(小时)
    is_critical: bool = False
    redundancy_level: int = 1  # 冗余度


@dataclass
class SensorConfiguration:
    """传感器配置方案"""
    config_id: str
    name: str
    sensors: List[SensorSpec] = field(default_factory=list)

    # 评价指标
    total_cost: float = 0.0
    observability_score: float = 0.0
    diagnosability_score: float = 0.0
    reliability_score: float = 0.0

    def add_sensor(self, sensor: SensorSpec):
        """添加传感器"""
        self.sensors.append(sensor)
        self._update_metrics()

    def _update_metrics(self):
        """更新评价指标"""
        self.total_cost = sum(s.cost * s.redundancy_level for s in self.sensors)

    def get_sensors_by_location(self, location: MeasurementLocation) -> List[SensorSpec]:
        """按位置获取传感器"""
        return [s for s in self.sensors if s.location == location]

    def get_sensors_by_type(self, sensor_type: SensorType) -> List[SensorSpec]:
        """按类型获取传感器"""
        return [s for s in self.sensors if s.sensor_type == sensor_type]


class ObservabilityAnalyzer:
    """
    可观测性分析器

    基于系统状态空间模型分析可观测性
    """

    def __init__(self, system_order: int = 10):
        self.system_order = system_order

        # 状态变量定义
        self.state_variables = [
            'pipeline_pressure',
            'pipeline_flow',
            'surge_tank_level',
            'turbine_speed',
            'turbine_torque',
            'generator_power',
            'generator_voltage',
            'generator_current',
            'guide_vane_position',
            'excitation_voltage',
        ]

        # 测量矩阵（传感器与状态的映射）
        self.C_matrix: Optional[np.ndarray] = None

    def build_measurement_matrix(
        self,
        config: SensorConfiguration
    ) -> np.ndarray:
        """
        构建测量矩阵

        Args:
            config: 传感器配置

        Returns:
            测量矩阵 C
        """
        n_sensors = len(config.sensors)
        n_states = len(self.state_variables)

        C = np.zeros((n_sensors, n_states))

        # 传感器-状态映射规则
        sensor_state_map = {
            (SensorType.PRESSURE, MeasurementLocation.PENSTOCK_OUTLET): 'pipeline_pressure',
            (SensorType.FLOW, MeasurementLocation.PENSTOCK_INLET): 'pipeline_flow',
            (SensorType.LEVEL, MeasurementLocation.SURGE_TANK): 'surge_tank_level',
            (SensorType.SPEED, MeasurementLocation.MAIN_SHAFT): 'turbine_speed',
            (SensorType.POWER, MeasurementLocation.TERMINAL): 'generator_power',
            (SensorType.VOLTAGE, MeasurementLocation.TERMINAL): 'generator_voltage',
            (SensorType.CURRENT, MeasurementLocation.TERMINAL): 'generator_current',
            (SensorType.POSITION, MeasurementLocation.GUIDE_VANE): 'guide_vane_position',
            (SensorType.VOLTAGE, MeasurementLocation.EXCITER): 'excitation_voltage',
        }

        for i, sensor in enumerate(config.sensors):
            key = (sensor.sensor_type, sensor.location)
            if key in sensor_state_map:
                state_name = sensor_state_map[key]
                if state_name in self.state_variables:
                    j = self.state_variables.index(state_name)
                    C[i, j] = 1.0 / sensor.accuracy  # 加权

        self.C_matrix = C
        return C

    def compute_observability_gramian(
        self,
        A: np.ndarray,
        C: np.ndarray
    ) -> np.ndarray:
        """
        计算可观测性Gramian矩阵

        Wo = sum(A'^i C' C A^i)
        """
        n = A.shape[0]
        Wo = np.zeros((n, n))

        Ai = np.eye(n)
        for i in range(n):
            Wo += Ai.T @ C.T @ C @ Ai
            Ai = Ai @ A

        return Wo

    def analyze_observability(
        self,
        config: SensorConfiguration,
        A_matrix: Optional[np.ndarray] = None
    ) -> Dict:
        """
        分析可观测性

        Args:
            config: 传感器配置
            A_matrix: 系统矩阵（可选）

        Returns:
            可观测性分析结果
        """
        C = self.build_measurement_matrix(config)

        # 如果未提供A矩阵，使用单位矩阵
        n = len(self.state_variables)
        if A_matrix is None:
            A = np.eye(n) * 0.95  # 假设稳定系统

        # 构建可观测性矩阵 O = [C; CA; CA^2; ...]
        O = C.copy()
        Ai = A.copy()
        for i in range(1, n):
            O = np.vstack([O, C @ Ai])
            Ai = Ai @ A

        # 计算秩
        obs_rank = matrix_rank(O)
        full_observable = obs_rank == n

        # 计算可观测性Gramian
        Wo = self.compute_observability_gramian(A, C)

        # 计算条件数（数值稳定性指标）
        eigenvalues = np.linalg.eigvalsh(Wo)
        eigenvalues = eigenvalues[eigenvalues > 1e-10]
        if len(eigenvalues) > 0:
            condition_number = np.max(eigenvalues) / np.min(eigenvalues)
        else:
            condition_number = np.inf

        # 可观测性得分
        observability_score = obs_rank / n

        # 更新配置的得分
        config.observability_score = observability_score

        return {
            'rank': obs_rank,
            'full_observable': full_observable,
            'unobservable_states': [
                self.state_variables[i]
                for i in range(n)
                if i >= obs_rank
            ],
            'condition_number': condition_number,
            'observability_score': observability_score,
            'gramian_eigenvalues': eigenvalues.tolist(),
        }


class DiagnosabilityAnalyzer:
    """
    故障可诊断性分析器

    分析传感器配置对故障的检测和隔离能力
    """

    def __init__(self):
        # 定义可能的故障模式
        self.fault_modes = [
            'sensor_bias',
            'sensor_drift',
            'sensor_stuck',
            'actuator_stuck',
            'actuator_slow',
            'pipeline_leak',
            'cavitation',
            'governor_fault',
            'exciter_fault',
            'bearing_wear',
        ]

        # 故障-传感器影响矩阵
        self.fault_signature_matrix: Optional[np.ndarray] = None

    def build_fault_signature_matrix(
        self,
        config: SensorConfiguration
    ) -> np.ndarray:
        """
        构建故障特征矩阵

        每行代表一个故障，每列代表一个传感器
        元素值表示该故障对该传感器测量的影响程度
        """
        n_faults = len(self.fault_modes)
        n_sensors = len(config.sensors)

        FSM = np.zeros((n_faults, n_sensors))

        # 定义故障影响规则
        for j, sensor in enumerate(config.sensors):
            for i, fault in enumerate(self.fault_modes):
                influence = self._get_fault_influence(fault, sensor)
                FSM[i, j] = influence

        self.fault_signature_matrix = FSM
        return FSM

    def _get_fault_influence(self, fault: str, sensor: SensorSpec) -> float:
        """获取故障对传感器的影响程度"""
        influence_rules = {
            ('sensor_bias', SensorType.PRESSURE): 1.0,
            ('sensor_bias', SensorType.FLOW): 1.0,
            ('sensor_drift', SensorType.TEMPERATURE): 0.8,
            ('actuator_stuck', SensorType.POSITION): 1.0,
            ('pipeline_leak', SensorType.PRESSURE): 0.9,
            ('pipeline_leak', SensorType.FLOW): 0.7,
            ('cavitation', SensorType.VIBRATION): 1.0,
            ('cavitation', SensorType.PRESSURE): 0.5,
            ('governor_fault', SensorType.SPEED): 0.8,
            ('governor_fault', SensorType.POSITION): 0.9,
            ('exciter_fault', SensorType.VOLTAGE): 1.0,
            ('bearing_wear', SensorType.VIBRATION): 1.0,
            ('bearing_wear', SensorType.TEMPERATURE): 0.6,
        }

        key = (fault, sensor.sensor_type)
        return influence_rules.get(key, 0.0)

    def analyze_diagnosability(
        self,
        config: SensorConfiguration
    ) -> Dict:
        """
        分析故障可诊断性

        Args:
            config: 传感器配置

        Returns:
            可诊断性分析结果
        """
        FSM = self.build_fault_signature_matrix(config)

        # 检测能力：每个故障至少被一个传感器检测到
        detectable = []
        for i, fault in enumerate(self.fault_modes):
            if np.any(FSM[i, :] > 0):
                detectable.append(fault)

        detection_rate = len(detectable) / len(self.fault_modes)

        # 隔离能力：不同故障有不同的特征向量
        isolable = []
        for i in range(len(self.fault_modes)):
            is_isolable = True
            for j in range(i + 1, len(self.fault_modes)):
                if np.allclose(FSM[i, :], FSM[j, :]):
                    is_isolable = False
                    break
            if is_isolable:
                isolable.append(self.fault_modes[i])

        isolation_rate = len(isolable) / len(self.fault_modes)

        # 综合可诊断性得分
        diagnosability_score = 0.6 * detection_rate + 0.4 * isolation_rate

        config.diagnosability_score = diagnosability_score

        return {
            'detection_rate': detection_rate,
            'isolation_rate': isolation_rate,
            'diagnosability_score': diagnosability_score,
            'detectable_faults': detectable,
            'isolable_faults': isolable,
            'undetectable_faults': [
                f for f in self.fault_modes if f not in detectable
            ],
        }


class SensorPlacementOptimizer:
    """
    传感器布设优化器

    优化传感器的数量、位置和冗余配置
    """

    def __init__(self):
        self.observability_analyzer = ObservabilityAnalyzer()
        self.diagnosability_analyzer = DiagnosabilityAnalyzer()

        # 优化目标权重
        self.weights = {
            'observability': 0.30,
            'diagnosability': 0.25,
            'reliability': 0.25,
            'cost': 0.20,
        }

        # 可选传感器库
        self.sensor_library: List[SensorSpec] = []
        self._init_sensor_library()

        # 优化结果
        self.optimization_results: List[SensorConfiguration] = []

    def _init_sensor_library(self):
        """初始化传感器库"""
        # 压力传感器
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.PRESSURE,
            location=MeasurementLocation.PENSTOCK_INLET,
            name="进水口压力",
            accuracy=0.005, cost=5000, is_critical=True
        ))
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.PRESSURE,
            location=MeasurementLocation.PENSTOCK_OUTLET,
            name="蜗壳进口压力",
            accuracy=0.005, cost=8000, is_critical=True
        ))
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.PRESSURE,
            location=MeasurementLocation.SPIRAL_CASE,
            name="蜗壳压力",
            accuracy=0.01, cost=6000
        ))
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.PRESSURE,
            location=MeasurementLocation.DRAFT_TUBE,
            name="尾水管压力",
            accuracy=0.01, cost=5000
        ))

        # 流量传感器
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.FLOW,
            location=MeasurementLocation.PENSTOCK_INLET,
            name="进水流量",
            accuracy=0.01, cost=50000, is_critical=True
        ))

        # 水位传感器
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.LEVEL,
            location=MeasurementLocation.SURGE_TANK,
            name="调压室水位",
            accuracy=0.001, cost=10000, is_critical=True
        ))

        # 转速传感器
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.SPEED,
            location=MeasurementLocation.MAIN_SHAFT,
            name="主轴转速",
            accuracy=0.001, cost=15000, is_critical=True
        ))

        # 功率传感器
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.POWER,
            location=MeasurementLocation.TERMINAL,
            name="有功功率",
            accuracy=0.005, cost=20000, is_critical=True
        ))

        # 电压电流传感器
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.VOLTAGE,
            location=MeasurementLocation.TERMINAL,
            name="端电压",
            accuracy=0.002, cost=8000
        ))
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.CURRENT,
            location=MeasurementLocation.TERMINAL,
            name="定子电流",
            accuracy=0.002, cost=8000
        ))

        # 位置传感器
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.POSITION,
            location=MeasurementLocation.GUIDE_VANE,
            name="导叶开度",
            accuracy=0.005, cost=5000, is_critical=True
        ))

        # 振动传感器
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.VIBRATION,
            location=MeasurementLocation.THRUST_BEARING,
            name="推力轴承振动",
            accuracy=0.02, cost=12000
        ))
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.VIBRATION,
            location=MeasurementLocation.GUIDE_BEARING,
            name="导轴承振动",
            accuracy=0.02, cost=12000
        ))

        # 温度传感器
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.TEMPERATURE,
            location=MeasurementLocation.THRUST_BEARING,
            name="推力瓦温",
            accuracy=0.01, cost=2000
        ))
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.TEMPERATURE,
            location=MeasurementLocation.STATOR,
            name="定子铁芯温度",
            accuracy=0.01, cost=2000
        ))
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.TEMPERATURE,
            location=MeasurementLocation.COOLING_WATER,
            name="冷却水温度",
            accuracy=0.01, cost=1500
        ))

        # 励磁系统
        self.sensor_library.append(SensorSpec(
            sensor_type=SensorType.VOLTAGE,
            location=MeasurementLocation.EXCITER,
            name="励磁电压",
            accuracy=0.005, cost=5000
        ))

    def create_minimal_config(self) -> SensorConfiguration:
        """创建最小配置（仅关键传感器）"""
        config = SensorConfiguration(
            config_id="MIN_CONFIG",
            name="最小传感器配置"
        )

        for sensor in self.sensor_library:
            if sensor.is_critical:
                config.add_sensor(sensor)

        return config

    def create_standard_config(self) -> SensorConfiguration:
        """创建标准配置"""
        config = SensorConfiguration(
            config_id="STD_CONFIG",
            name="标准传感器配置"
        )

        for sensor in self.sensor_library:
            new_sensor = SensorSpec(
                sensor_type=sensor.sensor_type,
                location=sensor.location,
                name=sensor.name,
                accuracy=sensor.accuracy,
                cost=sensor.cost,
                is_critical=sensor.is_critical,
                redundancy_level=2 if sensor.is_critical else 1
            )
            config.add_sensor(new_sensor)

        return config

    def create_enhanced_config(self) -> SensorConfiguration:
        """创建增强配置（高可靠性）"""
        config = SensorConfiguration(
            config_id="ENH_CONFIG",
            name="增强传感器配置"
        )

        for sensor in self.sensor_library:
            new_sensor = SensorSpec(
                sensor_type=sensor.sensor_type,
                location=sensor.location,
                name=sensor.name,
                accuracy=sensor.accuracy * 0.5,  # 更高精度
                cost=sensor.cost * 1.5,
                is_critical=sensor.is_critical,
                redundancy_level=3 if sensor.is_critical else 2
            )
            config.add_sensor(new_sensor)

        return config

    def evaluate_config(self, config: SensorConfiguration) -> Dict:
        """
        评估传感器配置

        Args:
            config: 传感器配置

        Returns:
            评估结果
        """
        # 可观测性分析
        obs_result = self.observability_analyzer.analyze_observability(config)

        # 可诊断性分析
        diag_result = self.diagnosability_analyzer.analyze_diagnosability(config)

        # 可靠性计算
        reliability = self._calculate_reliability(config)

        # 成本得分（越低越好，归一化）
        cost_ref = 500000  # 参考成本
        cost_score = 1 - min(config.total_cost / cost_ref, 1)

        # 综合得分
        total_score = (
            self.weights['observability'] * obs_result['observability_score'] +
            self.weights['diagnosability'] * diag_result['diagnosability_score'] +
            self.weights['reliability'] * reliability +
            self.weights['cost'] * cost_score
        )

        config.reliability_score = reliability

        return {
            'config_id': config.config_id,
            'total_cost': config.total_cost,
            'num_sensors': len(config.sensors),
            'observability': obs_result,
            'diagnosability': diag_result,
            'reliability': reliability,
            'cost_score': cost_score,
            'total_score': total_score,
        }

    def _calculate_reliability(self, config: SensorConfiguration) -> float:
        """计算系统可靠性"""
        if not config.sensors:
            return 0.0

        # 关键传感器的可靠性（考虑冗余）
        critical_reliabilities = []

        for sensor in config.sensors:
            if sensor.is_critical:
                # 单个传感器可靠性（1年）
                hours_per_year = 8760
                single_reliability = np.exp(-hours_per_year / sensor.mtbf)

                # k/n冗余可靠性（至少1个工作）
                n = sensor.redundancy_level
                # P(至少1个工作) = 1 - P(全部失效)
                redundant_reliability = 1 - (1 - single_reliability) ** n

                critical_reliabilities.append(redundant_reliability)

        if not critical_reliabilities:
            return 0.9

        # 串联系统可靠性
        system_reliability = np.prod(critical_reliabilities)

        return system_reliability

    def optimize(
        self,
        budget: float = 500000,
        min_observability: float = 0.8,
        min_diagnosability: float = 0.7
    ) -> SensorConfiguration:
        """
        优化传感器配置

        Args:
            budget: 预算约束（元）
            min_observability: 最小可观测性要求
            min_diagnosability: 最小可诊断性要求

        Returns:
            优化后的配置
        """
        best_config = None
        best_score = 0

        # 生成候选配置
        candidates = [
            self.create_minimal_config(),
            self.create_standard_config(),
            self.create_enhanced_config(),
        ]

        for config in candidates:
            if config.total_cost > budget:
                continue

            result = self.evaluate_config(config)

            if (result['observability']['observability_score'] >= min_observability and
                result['diagnosability']['diagnosability_score'] >= min_diagnosability):

                if result['total_score'] > best_score:
                    best_score = result['total_score']
                    best_config = config

        if best_config is None:
            # 如果没有满足约束的配置，返回最小配置
            best_config = self.create_minimal_config()

        self.optimization_results.append(best_config)

        return best_config

    def compare_configs(
        self,
        configs: List[SensorConfiguration]
    ) -> Dict:
        """对比多个配置"""
        results = []
        for config in configs:
            result = self.evaluate_config(config)
            results.append(result)

        # 排名
        ranking = sorted(
            range(len(results)),
            key=lambda i: results[i]['total_score'],
            reverse=True
        )

        return {
            'results': results,
            'ranking': [configs[i].config_id for i in ranking],
            'best_config': configs[ranking[0]].config_id,
        }

    def generate_placement_report(
        self,
        config: SensorConfiguration
    ) -> str:
        """生成布设报告"""
        result = self.evaluate_config(config)

        report = f"""
传感器布设优化报告
==================

配置名称: {config.name}
配置ID: {config.config_id}

1. 基本统计
   - 传感器总数: {len(config.sensors)}
   - 总成本: {config.total_cost/10000:.1f} 万元
   - 关键传感器数: {sum(1 for s in config.sensors if s.is_critical)}

2. 可观测性分析
   - 可观测性得分: {result['observability']['observability_score']:.2f}
   - 系统秩: {result['observability']['rank']}/{len(self.observability_analyzer.state_variables)}
   - 不可观测状态: {', '.join(result['observability']['unobservable_states']) or '无'}

3. 可诊断性分析
   - 可诊断性得分: {result['diagnosability']['diagnosability_score']:.2f}
   - 故障检测率: {result['diagnosability']['detection_rate']:.1%}
   - 故障隔离率: {result['diagnosability']['isolation_rate']:.1%}

4. 可靠性分析
   - 系统可靠性: {result['reliability']:.4f}

5. 综合评分: {result['total_score']:.2f}

6. 传感器清单
"""
        for sensor in config.sensors:
            report += f"""
   - {sensor.name}
     类型: {sensor.sensor_type.value}
     位置: {sensor.location.value}
     精度: {sensor.accuracy:.3f}
     冗余度: {sensor.redundancy_level}
     成本: {sensor.cost} 元
"""

        return report
