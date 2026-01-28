# -*- coding: utf-8 -*-
"""
五梯级级联耦合仿真 - Cascade Coupled Simulation

基于YX工程（雅鲁藏布江大拐弯截弯取直引水梯级发电工程）的级联仿真

核心功能：
- 有压引水系统水力耦合
- 五梯级电站协同运行
- 压力波传播与叠加
- 级联效应仿真
- 与ODD/MAS/SIL/HIL集成

物理模型：
- 水力域：MOC水锤计算、调压室动态、超长隧洞流动
- 机电域：水轮机特性、发电机暂态、调速器响应
- 系统域：级联耦合、压力波传播

参考：YX工程面向运行能力的设计评估与运行逻辑验证关键技术研究
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from enum import Enum
import logging
import copy

logger = logging.getLogger(__name__)


class CascadePosition(Enum):
    """梯级位置"""
    FIRST = 1       # 第一级（最上游）
    MIDDLE = 2      # 中间级
    LAST = 3        # 最后一级（最下游）


class CouplingType(Enum):
    """耦合类型"""
    HYDRAULIC = "hydraulic"             # 水力耦合
    ELECTRICAL = "electrical"           # 电气耦合
    CONTROL = "control"                 # 控制耦合


@dataclass
class StationState:
    """电站状态"""
    station_id: str
    timestamp: float

    # 水力状态
    upstream_level: float               # 上游水位 (m)
    downstream_level: float             # 下游水位 (m)
    head: float                         # 净水头 (m)
    flow: float                         # 流量 (m³/s)
    pressure: float                     # 压力 (MPa)
    surge_level: float                  # 调压室水位 (m)

    # 机电状态
    power: float                        # 功率 (MW)
    speed: float                        # 转速 (rpm)
    guide_vane: float                   # 导叶开度 (pu)
    frequency: float                    # 频率 (Hz)
    voltage: float                      # 电压 (kV)

    # 温度
    bearing_temp: float = 55.0          # 轴承温度 (℃)
    stator_temp: float = 85.0           # 定子温度 (℃)


@dataclass
class CascadeState:
    """梯级系统状态"""
    timestamp: float
    stations: Dict[str, StationState]

    # 系统级指标
    total_power: float = 0.0
    total_flow: float = 0.0
    system_frequency: float = 50.0

    # 耦合状态
    hydraulic_coupling_active: bool = True
    pressure_wave_active: bool = False


@dataclass
class StationConfig:
    """电站配置"""
    station_id: str
    name: str
    position: CascadePosition

    # 水力参数
    rated_head: float                   # 额定水头 (m)
    rated_flow: float                   # 额定流量 (m³/s)
    tunnel_length: float                # 引水隧洞长度 (m)
    tunnel_diameter: float              # 隧洞直径 (m)
    wave_speed: float                   # 压力波速 (m/s)
    friction_factor: float              # 摩阻系数

    # 调压设施
    surge_tank_area: float              # 调压室面积 (m²)
    surge_tank_height: float            # 调压室高度 (m)

    # 机组参数
    num_units: int                      # 机组数量
    rated_power: float                  # 单机额定功率 (MW)
    rated_speed: float                  # 额定转速 (rpm)
    inertia: float                      # 惯性时间常数 (s)
    turbine_efficiency: float           # 水轮机效率

    # 调速器参数
    governor_kp: float = 2.5
    governor_ki: float = 0.15
    governor_kd: float = 4.0
    guide_vane_rate_limit: float = 0.1  # pu/s


class HydraulicCouplingModel:
    """
    水力耦合模型

    计算有压系统中各电站间的水力耦合效应
    """

    def __init__(self):
        self.stations: Dict[str, StationConfig] = {}
        self.coupling_matrix: Optional[np.ndarray] = None

    def add_station(self, config: StationConfig):
        """添加电站"""
        self.stations[config.station_id] = config

    def build_coupling_matrix(self):
        """构建耦合矩阵"""
        n = len(self.stations)
        self.coupling_matrix = np.zeros((n, n))

        station_ids = list(self.stations.keys())

        for i, id_i in enumerate(station_ids):
            for j, id_j in enumerate(station_ids):
                if i == j:
                    self.coupling_matrix[i, j] = 1.0
                elif abs(i - j) == 1:
                    # 相邻电站有耦合
                    self.coupling_matrix[i, j] = 0.3

    def calculate_coupling_effect(self, states: Dict[str, StationState],
                                   dt: float) -> Dict[str, Dict[str, float]]:
        """
        计算耦合效应

        Args:
            states: 各站状态
            dt: 时间步长

        Returns:
            各站的耦合影响
        """
        effects = {}

        station_ids = list(self.stations.keys())

        for i, station_id in enumerate(station_ids):
            effect = {
                "pressure_effect": 0.0,
                "flow_effect": 0.0,
            }

            # 考虑相邻电站的影响
            for j, other_id in enumerate(station_ids):
                if i != j and abs(i - j) == 1:
                    if other_id in states and station_id in states:
                        # 压力波传播效应
                        pressure_diff = states[other_id].pressure - states[station_id].pressure
                        effect["pressure_effect"] += pressure_diff * 0.1

                        # 流量耦合效应
                        if i < j:  # 上游电站
                            flow_upstream = states[other_id].flow
                            effect["flow_effect"] += (flow_upstream - states[station_id].flow) * 0.05
                        else:  # 下游电站
                            flow_downstream = states[other_id].flow
                            effect["flow_effect"] += (states[station_id].flow - flow_downstream) * 0.05

            effects[station_id] = effect

        return effects


class PressureWaveModel:
    """
    压力波传播模型

    使用特征线法(MOC)计算水锤效应
    """

    def __init__(self, tunnel_length: float, wave_speed: float,
                 diameter: float, num_segments: int = 100):
        self.length = tunnel_length
        self.wave_speed = wave_speed
        self.diameter = diameter
        self.num_segments = num_segments

        self.dx = tunnel_length / num_segments
        self.dt = self.dx / wave_speed  # Courant条件

        # 管道状态
        self.pressure = np.zeros(num_segments + 1)
        self.velocity = np.zeros(num_segments + 1)

    def initialize(self, steady_pressure: float, steady_velocity: float):
        """初始化稳态"""
        self.pressure[:] = steady_pressure
        self.velocity[:] = steady_velocity

    def step(self, boundary_upstream: float, boundary_downstream: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        MOC单步计算

        Args:
            boundary_upstream: 上游边界条件
            boundary_downstream: 下游边界条件

        Returns:
            新的压力场和速度场
        """
        new_pressure = np.zeros_like(self.pressure)
        new_velocity = np.zeros_like(self.velocity)

        # 特征线法内部节点
        for i in range(1, self.num_segments):
            # C+ 特征线 (从 i-1 到 i)
            Cp = self.pressure[i-1] + self.wave_speed / 9.81 * self.velocity[i-1]

            # C- 特征线 (从 i+1 到 i)
            Cm = self.pressure[i+1] - self.wave_speed / 9.81 * self.velocity[i+1]

            # 求解
            new_pressure[i] = (Cp + Cm) / 2
            new_velocity[i] = (Cp - Cm) * 9.81 / (2 * self.wave_speed)

        # 边界条件
        new_pressure[0] = boundary_upstream
        new_pressure[-1] = boundary_downstream

        # 从边界推算速度
        Cm_0 = self.pressure[1] - self.wave_speed / 9.81 * self.velocity[1]
        new_velocity[0] = (new_pressure[0] - Cm_0) * 9.81 / self.wave_speed

        Cp_n = self.pressure[-2] + self.wave_speed / 9.81 * self.velocity[-2]
        new_velocity[-1] = (Cp_n - new_pressure[-1]) * 9.81 / self.wave_speed

        self.pressure = new_pressure
        self.velocity = new_velocity

        return self.pressure.copy(), self.velocity.copy()

    def get_max_pressure(self) -> float:
        """获取最大压力"""
        return np.max(self.pressure)

    def get_min_pressure(self) -> float:
        """获取最小压力"""
        return np.min(self.pressure)


class SingleStationSimulator:
    """
    单电站仿真器

    完整的单机组/单站仿真
    """

    def __init__(self, config: StationConfig):
        self.config = config

        # 状态
        self.state: Optional[StationState] = None

        # 压力波模型
        self.pressure_wave = PressureWaveModel(
            config.tunnel_length,
            config.wave_speed,
            config.tunnel_diameter
        )

        # 控制器状态
        self.integral_error = 0.0
        self.last_error = 0.0

        # 初始化
        self._initialize()

    def _initialize(self):
        """初始化"""
        # 计算稳态
        rated_pressure = self.config.rated_head * 9.81 * 1000 / 1e6  # MPa

        self.state = StationState(
            station_id=self.config.station_id,
            timestamp=0.0,
            upstream_level=self.config.rated_head + 100,
            downstream_level=100,
            head=self.config.rated_head,
            flow=self.config.rated_flow * self.config.num_units,
            pressure=rated_pressure,
            surge_level=self.config.surge_tank_height * 0.5,
            power=self.config.rated_power * self.config.num_units * 0.8,
            speed=self.config.rated_speed,
            guide_vane=0.8,
            frequency=50.0,
            voltage=20.0,
        )

        # 初始化压力波
        steady_velocity = self.state.flow / (np.pi * (self.config.tunnel_diameter/2)**2)
        self.pressure_wave.initialize(self.state.pressure, steady_velocity)

    def step(self, dt: float, external_inputs: Dict[str, float] = None,
             coupling_effects: Dict[str, float] = None) -> StationState:
        """
        单步仿真

        Args:
            dt: 时间步长
            external_inputs: 外部输入（负荷指令等）
            coupling_effects: 耦合效应

        Returns:
            新状态
        """
        external_inputs = external_inputs or {}
        coupling_effects = coupling_effects or {}

        # 获取目标值
        power_target = external_inputs.get("power_target", self.state.power)
        frequency_target = external_inputs.get("frequency_target", 50.0)

        # 调速器控制
        guide_vane_cmd = self._governor_control(
            self.state.speed,
            self.config.rated_speed,
            self.state.power,
            power_target,
            dt
        )

        # 导叶动作（带速率限制）
        gv_change = guide_vane_cmd - self.state.guide_vane
        gv_change = np.clip(
            gv_change,
            -self.config.guide_vane_rate_limit * dt,
            self.config.guide_vane_rate_limit * dt
        )
        new_guide_vane = np.clip(self.state.guide_vane + gv_change, 0.05, 1.0)

        # 水力计算
        # 流量响应
        max_flow = self.config.rated_flow * self.config.num_units * 1.1
        target_flow = new_guide_vane * max_flow * np.sqrt(self.state.head / self.config.rated_head)

        # 水惯性
        Tw = self.config.tunnel_length / (9.81 * self.state.flow / max_flow + 1e-6)
        Tw = min(Tw, 30)  # 限制最大水惯性时间

        new_flow = self.state.flow + (target_flow - self.state.flow) * dt / Tw

        # 调压室动态
        surge_inflow = new_flow - self.state.flow
        new_surge_level = self.state.surge_level + surge_inflow * dt / self.config.surge_tank_area

        # 水头计算
        new_head = self.state.upstream_level - self.state.downstream_level - \
                   (new_flow / max_flow)**2 * self.config.rated_head * 0.1

        # 应用耦合效应
        new_head += coupling_effects.get("pressure_effect", 0) * 10  # 转换为水头
        new_flow += coupling_effects.get("flow_effect", 0)

        # 压力计算
        new_pressure = new_head * 9.81 * 1000 / 1e6

        # 水锤效应（简化）
        flow_rate = (new_flow - self.state.flow) / dt if dt > 0 else 0
        water_hammer = self.config.wave_speed * abs(flow_rate) / 1000 * 0.01
        new_pressure += water_hammer

        # 机械功率
        eta = self.config.turbine_efficiency
        mech_power = 9.81 * new_flow * new_head * eta / 1000  # MW

        # 电气功率响应
        tau_e = 0.5
        new_power = self.state.power + (mech_power - self.state.power) * dt / tau_e

        # 转速响应
        load_power = external_inputs.get("load", new_power)
        power_unbalance = (mech_power - load_power) / self.config.rated_power
        speed_change = power_unbalance / self.config.inertia
        new_speed = self.state.speed * (1 + speed_change * dt)

        # 频率
        new_frequency = new_speed / self.config.rated_speed * 50

        # 更新状态
        self.state = StationState(
            station_id=self.config.station_id,
            timestamp=self.state.timestamp + dt,
            upstream_level=self.state.upstream_level,
            downstream_level=self.state.downstream_level,
            head=new_head,
            flow=new_flow,
            pressure=new_pressure,
            surge_level=new_surge_level,
            power=new_power,
            speed=new_speed,
            guide_vane=new_guide_vane,
            frequency=new_frequency,
            voltage=self.state.voltage,
        )

        return self.state

    def _governor_control(self, speed: float, rated_speed: float,
                          power: float, power_target: float, dt: float) -> float:
        """调速器控制"""
        # 频率偏差
        speed_error = (rated_speed - speed) / rated_speed

        # 功率偏差
        power_error = (power_target - power) / self.config.rated_power if self.config.rated_power > 0 else 0

        # 综合误差
        error = speed_error * 0.7 + power_error * 0.3

        # PID控制
        self.integral_error += error * dt
        self.integral_error = np.clip(self.integral_error, -1, 1)

        derivative = (error - self.last_error) / dt if dt > 0 else 0
        self.last_error = error

        output = (
            self.config.governor_kp * error +
            self.config.governor_ki * self.integral_error +
            self.config.governor_kd * derivative
        )

        # 转换为导叶开度指令
        guide_vane_cmd = self.state.guide_vane + output * 0.01

        return np.clip(guide_vane_cmd, 0.05, 1.0)


class CascadeSimulator:
    """
    梯级级联仿真器

    五梯级电站协同仿真
    """

    def __init__(self):
        # 电站配置
        self.station_configs: Dict[str, StationConfig] = {}

        # 单站仿真器
        self.station_simulators: Dict[str, SingleStationSimulator] = {}

        # 水力耦合模型
        self.hydraulic_coupling = HydraulicCouplingModel()

        # 梯级状态
        self.cascade_state: Optional[CascadeState] = None

        # 仿真参数
        self.dt = 0.01  # 10ms
        self.time = 0.0

        # 历史记录
        self.history: List[CascadeState] = []

    def add_station(self, config: StationConfig):
        """添加电站"""
        self.station_configs[config.station_id] = config
        self.station_simulators[config.station_id] = SingleStationSimulator(config)
        self.hydraulic_coupling.add_station(config)

    def initialize(self):
        """初始化"""
        self.hydraulic_coupling.build_coupling_matrix()

        # 收集各站状态
        stations = {}
        for station_id, sim in self.station_simulators.items():
            stations[station_id] = sim.state

        # 计算系统级指标
        total_power = sum(s.power for s in stations.values())
        total_flow = sum(s.flow for s in stations.values())

        self.cascade_state = CascadeState(
            timestamp=0.0,
            stations=stations,
            total_power=total_power,
            total_flow=total_flow,
            system_frequency=50.0,
        )

        self.time = 0.0
        self.history = []

    def step(self, system_inputs: Dict[str, Any] = None) -> CascadeState:
        """
        级联仿真单步

        Args:
            system_inputs: 系统级输入
                - station_targets: 各站目标
                - system_load: 系统总负荷

        Returns:
            新的级联状态
        """
        system_inputs = system_inputs or {}

        # 获取各站目标
        station_targets = system_inputs.get("station_targets", {})
        system_load = system_inputs.get("system_load", self.cascade_state.total_power)

        # 计算耦合效应
        coupling_effects = self.hydraulic_coupling.calculate_coupling_effect(
            self.cascade_state.stations,
            self.dt
        )

        # 分配系统负荷
        if not station_targets:
            station_targets = self._allocate_load(system_load)

        # 各站仿真
        new_stations = {}
        for station_id, simulator in self.station_simulators.items():
            external_inputs = station_targets.get(station_id, {})
            effects = coupling_effects.get(station_id, {})

            new_state = simulator.step(self.dt, external_inputs, effects)
            new_stations[station_id] = new_state

        # 更新系统级状态
        total_power = sum(s.power for s in new_stations.values())
        total_flow = sum(s.flow for s in new_stations.values())

        # 系统频率（加权平均）
        total_inertia = sum(
            self.station_configs[sid].inertia * self.station_configs[sid].num_units
            for sid in new_stations
        )
        weighted_freq = sum(
            new_stations[sid].frequency *
            self.station_configs[sid].inertia *
            self.station_configs[sid].num_units
            for sid in new_stations
        )
        system_frequency = weighted_freq / total_inertia if total_inertia > 0 else 50.0

        self.time += self.dt

        self.cascade_state = CascadeState(
            timestamp=self.time,
            stations=new_stations,
            total_power=total_power,
            total_flow=total_flow,
            system_frequency=system_frequency,
            hydraulic_coupling_active=True,
        )

        self.history.append(copy.deepcopy(self.cascade_state))

        return self.cascade_state

    def _allocate_load(self, total_load: float) -> Dict[str, Dict[str, float]]:
        """分配负荷"""
        targets = {}

        # 计算总容量
        total_capacity = sum(
            config.rated_power * config.num_units
            for config in self.station_configs.values()
        )

        # 按比例分配
        for station_id, config in self.station_configs.items():
            station_capacity = config.rated_power * config.num_units
            ratio = station_capacity / total_capacity if total_capacity > 0 else 0
            targets[station_id] = {
                "power_target": total_load * ratio,
                "frequency_target": 50.0,
            }

        return targets

    def run(self, duration: float, system_inputs_sequence: List[Dict[str, Any]] = None) -> List[CascadeState]:
        """
        运行仿真

        Args:
            duration: 仿真时长
            system_inputs_sequence: 输入序列

        Returns:
            状态历史
        """
        steps = int(duration / self.dt)

        for i in range(steps):
            inputs = {}
            if system_inputs_sequence and i < len(system_inputs_sequence):
                inputs = system_inputs_sequence[i]

            self.step(inputs)

        return self.history

    def apply_event(self, event: Dict[str, Any]):
        """
        应用事件

        Args:
            event: 事件描述
        """
        event_type = event.get("type", "")

        if event_type == "station_trip":
            # 电站跳闸
            station_id = event.get("station", "")
            if station_id in self.station_simulators:
                sim = self.station_simulators[station_id]
                sim.state.power = 0
                sim.state.guide_vane = 0

        elif event_type == "load_rejection":
            # 甩负荷
            magnitude = event.get("magnitude", 0.3)
            station_id = event.get("station", "")
            if station_id in self.station_simulators:
                sim = self.station_simulators[station_id]
                # 负荷突然减少
                pass

        elif event_type == "guide_vane_fast_close":
            # 导叶快关
            station_id = event.get("station", "")
            if station_id in self.station_simulators:
                sim = self.station_simulators[station_id]
                sim.state.guide_vane = event.get("target", 0.1)

    def get_results(self) -> Dict[str, Any]:
        """获取仿真结果"""
        if not self.history:
            return {}

        results = {
            "time": [s.timestamp for s in self.history],
            "system": {
                "total_power": [s.total_power for s in self.history],
                "total_flow": [s.total_flow for s in self.history],
                "frequency": [s.system_frequency for s in self.history],
            },
            "stations": {},
        }

        # 各站数据
        for station_id in self.station_configs:
            results["stations"][station_id] = {
                "power": [s.stations[station_id].power for s in self.history],
                "flow": [s.stations[station_id].flow for s in self.history],
                "pressure": [s.stations[station_id].pressure for s in self.history],
                "speed": [s.stations[station_id].speed for s in self.history],
                "guide_vane": [s.stations[station_id].guide_vane for s in self.history],
                "surge_level": [s.stations[station_id].surge_level for s in self.history],
            }

        return results


def create_yajiang_cascade_simulator() -> CascadeSimulator:
    """
    创建雅鲁藏布江大拐弯工程级联仿真器

    配置五个梯级电站
    """
    simulator = CascadeSimulator()

    # 五个梯级电站配置
    stations = [
        StationConfig(
            station_id="YJ01",
            name="墨脱水电站",
            position=CascadePosition.FIRST,
            rated_head=480,
            rated_flow=210,
            tunnel_length=25000,
            tunnel_diameter=11,
            wave_speed=1350,
            friction_factor=0.015,
            surge_tank_area=1590,  # 45m直径
            surge_tank_height=120,
            num_units=6,
            rated_power=1000,
            rated_speed=166.7,
            inertia=4.0,
            turbine_efficiency=0.94,
        ),
        StationConfig(
            station_id="YJ02",
            name="多雄藏布水电站",
            position=CascadePosition.MIDDLE,
            rated_head=450,
            rated_flow=200,
            tunnel_length=20000,
            tunnel_diameter=10,
            wave_speed=1300,
            friction_factor=0.015,
            surge_tank_area=1260,
            surge_tank_height=100,
            num_units=4,
            rated_power=800,
            rated_speed=166.7,
            inertia=4.0,
            turbine_efficiency=0.93,
        ),
        StationConfig(
            station_id="YJ03",
            name="达木水电站",
            position=CascadePosition.MIDDLE,
            rated_head=400,
            rated_flow=180,
            tunnel_length=15000,
            tunnel_diameter=9,
            wave_speed=1250,
            friction_factor=0.014,
            surge_tank_area=1000,
            surge_tank_height=90,
            num_units=3,
            rated_power=600,
            rated_speed=150,
            inertia=3.5,
            turbine_efficiency=0.93,
        ),
        StationConfig(
            station_id="YJ04",
            name="巴玉水电站",
            position=CascadePosition.MIDDLE,
            rated_head=350,
            rated_flow=160,
            tunnel_length=12000,
            tunnel_diameter=8,
            wave_speed=1200,
            friction_factor=0.014,
            surge_tank_area=800,
            surge_tank_height=80,
            num_units=3,
            rated_power=500,
            rated_speed=150,
            inertia=3.5,
            turbine_efficiency=0.92,
        ),
        StationConfig(
            station_id="YJ05",
            name="通德水电站",
            position=CascadePosition.LAST,
            rated_head=300,
            rated_flow=150,
            tunnel_length=10000,
            tunnel_diameter=7,
            wave_speed=1150,
            friction_factor=0.013,
            surge_tank_area=600,
            surge_tank_height=70,
            num_units=2,
            rated_power=400,
            rated_speed=125,
            inertia=3.0,
            turbine_efficiency=0.92,
        ),
    ]

    for config in stations:
        simulator.add_station(config)

    simulator.initialize()

    return simulator
