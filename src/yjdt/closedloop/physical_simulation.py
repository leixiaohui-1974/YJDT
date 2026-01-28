# -*- coding: utf-8 -*-
"""
本体仿真模块 - 多物理场耦合仿真
Physical Simulation Module - Multi-Physics Coupled Simulation

功能：
- 水力域：管道流动、水锤、调压室
- 机械域：转子动力学、振动、磨损
- 电气域：发电机电磁暂态、励磁、并网
- 热力域：温度场、冷却、热应力

采用分域耦合求解策略
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod


class DomainType(Enum):
    """物理域类型"""
    HYDRAULIC = "hydraulic"
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    THERMAL = "thermal"


@dataclass
class DomainState:
    """域状态"""
    domain: DomainType
    variables: Dict[str, float]
    derivatives: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CouplingMatrix:
    """
    耦合矩阵 - 描述不同物理域之间的耦合关系

    用于多物理场耦合仿真中域间信息传递
    """
    from_domain: DomainType
    to_domain: DomainType
    coupling_coefficients: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def get_coefficient(self, from_var: str, to_var: str) -> float:
        """获取耦合系数"""
        if from_var in self.coupling_coefficients:
            return self.coupling_coefficients[from_var].get(to_var, 0.0)
        return 0.0

    def set_coefficient(self, from_var: str, to_var: str, value: float):
        """设置耦合系数"""
        if from_var not in self.coupling_coefficients:
            self.coupling_coefficients[from_var] = {}
        self.coupling_coefficients[from_var][to_var] = value


class PhysicsDomain(ABC):
    """物理域基类"""

    def __init__(self, name: str, domain_type: DomainType):
        self.name = name
        self.domain_type = domain_type
        self.state: Dict[str, float] = {}
        self.parameters: Dict[str, float] = {}
        self.inputs: Dict[str, float] = {}
        self.outputs: Dict[str, float] = {}

    @abstractmethod
    def initialize(self, params: Dict[str, float]):
        """初始化域"""
        pass

    @abstractmethod
    def step(self, dt: float, inputs: Dict[str, float]) -> Dict[str, float]:
        """推进一步"""
        pass

    @abstractmethod
    def get_coupling_variables(self) -> Dict[str, float]:
        """获取耦合变量"""
        pass


class HydraulicDomain(PhysicsDomain):
    """
    水力域仿真

    特征线法(MOC)求解水锤
    考虑超高水头(2000m)特殊条件
    """

    def __init__(self):
        super().__init__("Hydraulic", DomainType.HYDRAULIC)

        # 管道参数
        self.parameters = {
            "tunnel_length": 45000,     # m
            "tunnel_diameter": 10,      # m
            "tunnel_area": 78.5,        # m²
            "wave_speed": 1200,         # m/s
            "friction_factor": 0.012,
            "penstock_length": 2000,    # m
            "penstock_diameter": 6,     # m
            "gross_head": 2000,         # m
            "surge_tank_area": 500,     # m²
            "surge_tank_height": 200,   # m
        }

        # 状态变量
        self.state = {
            "upstream_level": 4500,     # m
            "downstream_level": 2500,   # m
            "tunnel_flow": 200,         # m³/s
            "penstock_pressure": 20,    # MPa
            "surge_tank_level": 4450,   # m
            "turbine_flow": 200,        # m³/s
        }

    def initialize(self, params: Dict[str, float]):
        """初始化水力域"""
        self.parameters.update(params)

        # 计算初始稳态
        head = self.parameters["gross_head"]
        self.state["penstock_pressure"] = head * 9.81 * 1000 / 1e6  # MPa

    def step(self, dt: float, inputs: Dict[str, float]) -> Dict[str, float]:
        """水力域推进一步"""
        # 获取输入
        guide_vane_opening = inputs.get("guide_vane_opening", 0.8)
        upstream_inflow = inputs.get("inflow", 200)

        # 简化水力计算
        # 隧洞流量响应（一阶惯性）
        Tw = self.parameters["tunnel_length"] / (
            9.81 * self.parameters["tunnel_area"] / self.state["tunnel_flow"]
        ) if self.state["tunnel_flow"] > 0 else 25

        target_flow = guide_vane_opening * 250
        self.state["tunnel_flow"] += (target_flow - self.state["tunnel_flow"]) * dt / Tw

        # 调压室水位变化
        surge_area = self.parameters["surge_tank_area"]
        surge_inflow = self.state["tunnel_flow"] - self.state["turbine_flow"]
        self.state["surge_tank_level"] += surge_inflow * dt / surge_area

        # 水轮机流量
        self.state["turbine_flow"] = guide_vane_opening * 250 * np.sqrt(
            (self.state["surge_tank_level"] - self.state["downstream_level"]) /
            self.parameters["gross_head"]
        )

        # 压力计算（包含水锤效应简化）
        head = self.state["surge_tank_level"] - self.state["downstream_level"]
        # 水锤压力波动
        flow_change_rate = inputs.get("flow_change_rate", 0)
        water_hammer = self.parameters["wave_speed"] * abs(flow_change_rate) / (
            9.81 * self.parameters["penstock_diameter"]**2 * np.pi / 4
        )

        self.state["penstock_pressure"] = head * 9.81 * 1000 / 1e6 + water_hammer * 0.001

        # 更新输出
        self.outputs = {
            "net_head": head,
            "turbine_flow": self.state["turbine_flow"],
            "penstock_pressure": self.state["penstock_pressure"],
            "surge_level": self.state["surge_tank_level"],
        }

        return self.outputs

    def get_coupling_variables(self) -> Dict[str, float]:
        """获取耦合到其他域的变量"""
        return {
            "hydraulic_power": 9.81 * 1000 * self.state["turbine_flow"] * (
                self.state["surge_tank_level"] - self.state["downstream_level"]
            ) / 1e6,  # MW
            "turbine_flow": self.state["turbine_flow"],
            "penstock_pressure": self.state["penstock_pressure"],
        }


class MechanicalDomain(PhysicsDomain):
    """
    机械域仿真

    转子动力学、振动、轴承
    """

    def __init__(self):
        super().__init__("Mechanical", DomainType.MECHANICAL)

        self.parameters = {
            "rated_speed": 100,         # rpm
            "inertia": 1e7,             # kg·m²
            "damping": 1e5,             # N·m·s/rad
            "rated_torque": 9.55e6,     # N·m (1000MW at 100rpm)
            "critical_speed_1": 50,     # rpm
            "critical_speed_2": 150,    # rpm
            "bearing_stiffness": 1e9,   # N/m
            "bearing_damping": 1e6,     # N·s/m
        }

        self.state = {
            "speed": 100,               # rpm
            "acceleration": 0,          # rpm/s
            "vibration_x": 50,          # μm
            "vibration_y": 50,          # μm
            "bearing_temperature": 55,  # ℃
            "shaft_displacement": 0,    # mm
        }

    def initialize(self, params: Dict[str, float]):
        self.parameters.update(params)
        self.state["speed"] = self.parameters["rated_speed"]

    def step(self, dt: float, inputs: Dict[str, float]) -> Dict[str, float]:
        """机械域推进一步"""
        # 获取输入
        hydraulic_torque = inputs.get("hydraulic_torque", self.parameters["rated_torque"])
        electrical_torque = inputs.get("electrical_torque", self.parameters["rated_torque"])

        # 转子动力学方程
        # J * dω/dt = Th - Te - D*ω
        omega = self.state["speed"] * 2 * np.pi / 60  # rad/s
        net_torque = hydraulic_torque - electrical_torque - self.parameters["damping"] * omega

        domega_dt = net_torque / self.parameters["inertia"]
        self.state["acceleration"] = domega_dt * 60 / (2 * np.pi)  # rpm/s

        # 更新转速
        self.state["speed"] += self.state["acceleration"] * dt

        # 振动计算（简化模型）
        # 基于不平衡力和临界转速
        speed_ratio = self.state["speed"] / self.parameters["critical_speed_1"]
        magnification = 1 / abs(1 - speed_ratio**2 + 0.1)  # 避免除零

        base_vibration = 30  # 基础振动 μm
        self.state["vibration_x"] = base_vibration * magnification * (1 + 0.1 * np.random.randn())
        self.state["vibration_y"] = base_vibration * magnification * (1 + 0.1 * np.random.randn())

        # 轴承温度（热平衡简化模型）
        friction_power = self.parameters["damping"] * omega**2 / 1000  # kW
        cooling_rate = 0.1  # kW/℃
        ambient_temp = 25

        dT_dt = (friction_power - cooling_rate * (self.state["bearing_temperature"] - ambient_temp)) / 10
        self.state["bearing_temperature"] += dT_dt * dt

        self.outputs = {
            "speed": self.state["speed"],
            "vibration": np.sqrt(self.state["vibration_x"]**2 + self.state["vibration_y"]**2),
            "bearing_temp": self.state["bearing_temperature"],
        }

        return self.outputs

    def get_coupling_variables(self) -> Dict[str, float]:
        return {
            "shaft_speed": self.state["speed"],
            "mechanical_torque": self.parameters["rated_torque"] * self.state["speed"] / self.parameters["rated_speed"],
        }


class ElectricalDomain(PhysicsDomain):
    """
    电气域仿真

    同步发电机电磁暂态模型
    """

    def __init__(self):
        super().__init__("Electrical", DomainType.ELECTRICAL)

        self.parameters = {
            "rated_power": 1000,        # MW
            "rated_voltage": 20,        # kV
            "rated_current": 28.87,     # kA
            "power_factor": 0.9,
            "synchronous_reactance": 2.0,  # p.u.
            "transient_reactance": 0.3,
            "subtransient_reactance": 0.2,
            "field_time_constant": 5.0,    # s
            "armature_time_constant": 0.15,
        }

        self.state = {
            "active_power": 800,        # MW
            "reactive_power": 100,      # Mvar
            "terminal_voltage": 20,     # kV
            "stator_current": 23,       # kA
            "field_current": 2500,      # A
            "power_angle": 30,          # deg
            "frequency": 50,            # Hz
        }

    def initialize(self, params: Dict[str, float]):
        self.parameters.update(params)

    def step(self, dt: float, inputs: Dict[str, float]) -> Dict[str, float]:
        """电气域推进一步"""
        # 获取输入
        shaft_speed = inputs.get("shaft_speed", 100)  # rpm
        mechanical_power = inputs.get("mechanical_power", 800)  # MW
        voltage_setpoint = inputs.get("voltage_setpoint", 20)
        power_setpoint = inputs.get("power_setpoint", 800)

        # 频率（基于转速）
        self.state["frequency"] = shaft_speed / 100 * 50

        # 功率响应（一阶惯性）
        tau_p = 0.5  # 功率响应时间常数
        self.state["active_power"] += (power_setpoint - self.state["active_power"]) * dt / tau_p

        # 电压调节
        tau_v = 1.0  # 电压响应时间常数
        self.state["terminal_voltage"] += (voltage_setpoint - self.state["terminal_voltage"]) * dt / tau_v

        # 定子电流计算
        apparent_power = np.sqrt(self.state["active_power"]**2 + self.state["reactive_power"]**2)
        self.state["stator_current"] = apparent_power / (np.sqrt(3) * self.state["terminal_voltage"])

        # 功率角估算
        self.state["power_angle"] = np.arcsin(
            self.state["active_power"] / self.parameters["rated_power"] *
            self.parameters["synchronous_reactance"]
        ) * 180 / np.pi

        # 励磁电流（简化AVR模型）
        voltage_error = voltage_setpoint - self.state["terminal_voltage"]
        self.state["field_current"] += voltage_error * 100 * dt

        # 计算电磁转矩
        electrical_torque = self.state["active_power"] * 1e6 / (shaft_speed * 2 * np.pi / 60)

        self.outputs = {
            "active_power": self.state["active_power"],
            "reactive_power": self.state["reactive_power"],
            "frequency": self.state["frequency"],
            "voltage": self.state["terminal_voltage"],
            "electrical_torque": electrical_torque,
        }

        return self.outputs

    def get_coupling_variables(self) -> Dict[str, float]:
        return {
            "electrical_torque": self.outputs.get("electrical_torque", 0),
            "active_power": self.state["active_power"],
        }


class ThermalDomain(PhysicsDomain):
    """
    热力域仿真

    温度场、冷却系统
    """

    def __init__(self):
        super().__init__("Thermal", DomainType.THERMAL)

        self.parameters = {
            "stator_thermal_capacity": 1e7,     # J/℃
            "rotor_thermal_capacity": 5e6,
            "cooling_capacity": 5e6,            # W
            "ambient_temperature": 25,
            "cooling_water_temp": 20,
            "heat_transfer_coeff": 1000,        # W/m²℃
        }

        self.state = {
            "stator_temperature": 85,
            "rotor_temperature": 75,
            "cooling_water_outlet": 30,
            "oil_temperature": 45,
        }

    def initialize(self, params: Dict[str, float]):
        self.parameters.update(params)

    def step(self, dt: float, inputs: Dict[str, float]) -> Dict[str, float]:
        """热力域推进一步"""
        # 获取输入
        stator_losses = inputs.get("stator_losses", 5e6)  # W
        rotor_losses = inputs.get("rotor_losses", 3e6)
        mechanical_losses = inputs.get("mechanical_losses", 2e6)

        # 定子温度
        cooling_power = self.parameters["cooling_capacity"] * (
            self.state["stator_temperature"] - self.parameters["cooling_water_temp"]
        ) / 100

        dT_stator = (stator_losses - cooling_power) / self.parameters["stator_thermal_capacity"]
        self.state["stator_temperature"] += dT_stator * dt

        # 转子温度
        rotor_cooling = self.parameters["cooling_capacity"] * 0.3 * (
            self.state["rotor_temperature"] - self.parameters["ambient_temperature"]
        ) / 50

        dT_rotor = (rotor_losses - rotor_cooling) / self.parameters["rotor_thermal_capacity"]
        self.state["rotor_temperature"] += dT_rotor * dt

        # 冷却水出口温度
        self.state["cooling_water_outlet"] = self.parameters["cooling_water_temp"] + (
            cooling_power / 4.18e6  # 假设流量1000 kg/s
        )

        self.outputs = {
            "stator_temp": self.state["stator_temperature"],
            "rotor_temp": self.state["rotor_temperature"],
            "cooling_outlet": self.state["cooling_water_outlet"],
        }

        return self.outputs

    def get_coupling_variables(self) -> Dict[str, float]:
        return {
            "stator_temperature": self.state["stator_temperature"],
            "rotor_temperature": self.state["rotor_temperature"],
        }


class MultiPhysicsModel:
    """
    多物理场耦合模型

    协调各物理域的耦合求解
    """

    def __init__(self):
        self.domains: Dict[DomainType, PhysicsDomain] = {}
        self.coupling_map: Dict[str, List[Tuple[DomainType, str]]] = {}

        # 初始化各域
        self._init_domains()
        self._setup_coupling()

    def _init_domains(self):
        """初始化各物理域"""
        self.domains[DomainType.HYDRAULIC] = HydraulicDomain()
        self.domains[DomainType.MECHANICAL] = MechanicalDomain()
        self.domains[DomainType.ELECTRICAL] = ElectricalDomain()
        self.domains[DomainType.THERMAL] = ThermalDomain()

    def _setup_coupling(self):
        """设置域间耦合关系"""
        # 水力→机械：水轮机力矩
        # 机械→电气：转速
        # 电气→机械：电磁力矩
        # 机械→热力：机械损耗
        # 电气→热力：电气损耗
        self.coupling_map = {
            "hydraulic_power": [(DomainType.MECHANICAL, "hydraulic_torque")],
            "shaft_speed": [(DomainType.ELECTRICAL, "shaft_speed"),
                           (DomainType.THERMAL, "shaft_speed")],
            "electrical_torque": [(DomainType.MECHANICAL, "electrical_torque")],
        }

    def initialize(self, params: Dict[DomainType, Dict[str, float]] = None):
        """初始化所有域"""
        params = params or {}
        for domain_type, domain in self.domains.items():
            domain_params = params.get(domain_type, {})
            domain.initialize(domain_params)

    def step(self, dt: float, external_inputs: Dict[str, float]) -> Dict[str, float]:
        """
        多物理场耦合推进一步

        使用顺序耦合策略：水力→机械→电气→热力
        """
        all_outputs = {}

        # 1. 水力域
        hydraulic_inputs = {
            "guide_vane_opening": external_inputs.get("guide_vane_opening", 0.8),
            "inflow": external_inputs.get("inflow", 200),
            "flow_change_rate": external_inputs.get("flow_change_rate", 0),
        }
        hydraulic_outputs = self.domains[DomainType.HYDRAULIC].step(dt, hydraulic_inputs)
        hydraulic_coupling = self.domains[DomainType.HYDRAULIC].get_coupling_variables()

        # 2. 机械域
        mechanical_inputs = {
            "hydraulic_torque": hydraulic_coupling["hydraulic_power"] * 1e6 / (
                self.domains[DomainType.MECHANICAL].state["speed"] * 2 * np.pi / 60
            ) if self.domains[DomainType.MECHANICAL].state["speed"] > 0 else 0,
            "electrical_torque": self.domains[DomainType.ELECTRICAL].outputs.get("electrical_torque", 0),
        }
        mechanical_outputs = self.domains[DomainType.MECHANICAL].step(dt, mechanical_inputs)
        mechanical_coupling = self.domains[DomainType.MECHANICAL].get_coupling_variables()

        # 3. 电气域
        electrical_inputs = {
            "shaft_speed": mechanical_coupling["shaft_speed"],
            "mechanical_power": hydraulic_coupling["hydraulic_power"] * 0.92,  # 水轮机效率
            "voltage_setpoint": external_inputs.get("voltage_setpoint", 20),
            "power_setpoint": external_inputs.get("power_setpoint", 800),
        }
        electrical_outputs = self.domains[DomainType.ELECTRICAL].step(dt, electrical_inputs)

        # 4. 热力域
        thermal_inputs = {
            "stator_losses": electrical_outputs["active_power"] * 0.005 * 1e6,  # 0.5%损耗
            "rotor_losses": electrical_outputs["active_power"] * 0.003 * 1e6,
            "mechanical_losses": mechanical_coupling["mechanical_torque"] *
                                 mechanical_coupling["shaft_speed"] * 2 * np.pi / 60 * 0.001,
        }
        thermal_outputs = self.domains[DomainType.THERMAL].step(dt, thermal_inputs)

        # 汇总输出
        all_outputs.update({f"hydraulic_{k}": v for k, v in hydraulic_outputs.items()})
        all_outputs.update({f"mechanical_{k}": v for k, v in mechanical_outputs.items()})
        all_outputs.update({f"electrical_{k}": v for k, v in electrical_outputs.items()})
        all_outputs.update({f"thermal_{k}": v for k, v in thermal_outputs.items()})

        return all_outputs

    def get_all_states(self) -> Dict[str, Dict[str, float]]:
        """获取所有域的状态"""
        return {
            domain_type.value: domain.state.copy()
            for domain_type, domain in self.domains.items()
        }


class PhysicalSimulator:
    """
    本体仿真器

    管理多物理场模型的仿真执行
    """

    def __init__(self):
        self.model = MultiPhysicsModel()
        self.time = 0.0
        self.dt = 0.01  # 10ms步长
        self.history: List[Dict[str, Any]] = []
        self.is_running = False

    def initialize(self, params: Dict[DomainType, Dict[str, float]] = None):
        """初始化仿真器"""
        self.model.initialize(params)
        self.time = 0.0
        self.history = []

    def step(self, inputs: Dict[str, float] = None) -> Dict[str, float]:
        """执行单步仿真"""
        inputs = inputs or {}
        outputs = self.model.step(self.dt, inputs)

        # 记录历史
        record = {
            "time": self.time,
            "inputs": inputs.copy(),
            "outputs": outputs.copy(),
            "states": self.model.get_all_states(),
        }
        self.history.append(record)

        self.time += self.dt
        return outputs

    def run(self, duration: float, inputs_sequence: List[Dict[str, float]] = None) -> List[Dict[str, float]]:
        """运行指定时长的仿真"""
        self.is_running = True
        steps = int(duration / self.dt)
        results = []

        for i in range(steps):
            if not self.is_running:
                break

            inputs = {}
            if inputs_sequence and i < len(inputs_sequence):
                inputs = inputs_sequence[i]

            outputs = self.step(inputs)
            results.append(outputs)

        return results

    def stop(self):
        """停止仿真"""
        self.is_running = False

    def get_history(self) -> List[Dict[str, Any]]:
        """获取仿真历史"""
        return self.history

    def get_state_trajectory(self, variable: str) -> Tuple[List[float], List[float]]:
        """获取变量时间序列"""
        times = []
        values = []

        for record in self.history:
            times.append(record["time"])
            if variable in record["outputs"]:
                values.append(record["outputs"][variable])
            else:
                values.append(0)

        return times, values
