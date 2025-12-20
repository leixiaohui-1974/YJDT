"""
分层分布式控制器模块
Hierarchical Distributed Controller Module

实现水电站的四层控制架构：
- 现场级（Field Level）：直接控制回路，PID控制
- 单元级（Unit Level）：机组协调，MPC控制
- 厂站级（Plant Level）：厂内优化调度
- 梯级调度级（Cascade Level）：多电站协调
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import threading
import queue
import time


class ControlLevel(Enum):
    """控制层级"""
    FIELD = 1           # 现场级
    UNIT = 2            # 单元级
    PLANT = 3           # 厂站级
    CASCADE = 4         # 梯级调度级


class ControllerStatus(Enum):
    """控制器状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FAULT = "fault"
    MANUAL = "manual"


@dataclass
class ControlCommand:
    """控制指令"""
    target_id: str              # 目标设备/控制器ID
    command_type: str           # 指令类型
    value: float               # 指令值
    priority: int = 0          # 优先级
    timestamp: float = 0.0     # 时间戳
    source: str = ""           # 来源


@dataclass
class ControllerConfig:
    """控制器配置"""
    controller_id: str
    level: ControlLevel
    cycle_time: float = 0.02    # 控制周期 (s)
    timeout: float = 1.0        # 超时时间 (s)
    enable_redundancy: bool = False  # 冗余使能


class ControllerBase(ABC):
    """控制器基类"""

    def __init__(self, config: ControllerConfig):
        self.config = config
        self.status = ControllerStatus.IDLE

        # 输入输出
        self.inputs: Dict[str, float] = {}
        self.outputs: Dict[str, float] = {}
        self.setpoints: Dict[str, float] = {}

        # 通信
        self.command_queue: queue.Queue = queue.Queue()
        self.response_queue: queue.Queue = queue.Queue()

        # 子控制器
        self.sub_controllers: Dict[str, 'ControllerBase'] = {}

        # 父控制器引用
        self.parent: Optional['ControllerBase'] = None

        # 历史记录
        self.history: Dict[str, List[float]] = {
            'time': [],
            'inputs': [],
            'outputs': [],
        }

        # 诊断信息
        self.diagnostics: Dict[str, Any] = {}

    @abstractmethod
    def compute(self, dt: float) -> Dict[str, float]:
        """
        计算控制输出

        Args:
            dt: 时间步长 (s)

        Returns:
            控制输出字典
        """
        pass

    def update(self, inputs: Dict[str, float], dt: float) -> Dict[str, float]:
        """
        更新控制器

        Args:
            inputs: 输入信号字典
            dt: 时间步长 (s)

        Returns:
            输出信号字典
        """
        self.inputs = inputs

        # 处理接收的指令
        self._process_commands()

        # 执行控制计算
        if self.status == ControllerStatus.RUNNING:
            self.outputs = self.compute(dt)

        return self.outputs

    def _process_commands(self):
        """处理指令队列"""
        while not self.command_queue.empty():
            try:
                cmd = self.command_queue.get_nowait()
                self._handle_command(cmd)
            except queue.Empty:
                break

    def _handle_command(self, cmd: ControlCommand):
        """处理单个指令"""
        if cmd.command_type == "setpoint":
            self.setpoints[cmd.target_id] = cmd.value
        elif cmd.command_type == "start":
            self.start()
        elif cmd.command_type == "stop":
            self.stop()
        elif cmd.command_type == "mode":
            pass  # 模式切换

    def send_command(self, cmd: ControlCommand):
        """发送指令给子控制器"""
        if cmd.target_id in self.sub_controllers:
            self.sub_controllers[cmd.target_id].command_queue.put(cmd)

    def add_sub_controller(self, controller_id: str, controller: 'ControllerBase'):
        """添加子控制器"""
        self.sub_controllers[controller_id] = controller
        controller.parent = self

    def start(self):
        """启动控制器"""
        self.status = ControllerStatus.RUNNING

    def stop(self):
        """停止控制器"""
        self.status = ControllerStatus.IDLE

    def get_diagnostics(self) -> Dict[str, Any]:
        """获取诊断信息"""
        self.diagnostics = {
            'controller_id': self.config.controller_id,
            'level': self.config.level.name,
            'status': self.status.value,
            'num_inputs': len(self.inputs),
            'num_outputs': len(self.outputs),
            'num_sub_controllers': len(self.sub_controllers),
        }
        return self.diagnostics


class FieldLevelController(ControllerBase):
    """
    现场级控制器

    实现直接的PID控制回路
    控制周期：20ms
    """

    def __init__(self, controller_id: str):
        config = ControllerConfig(
            controller_id=controller_id,
            level=ControlLevel.FIELD,
            cycle_time=0.02,
        )
        super().__init__(config)

        # PID参数
        self.kp = 2.5
        self.ki = 0.15
        self.kd = 4.0

        # 内部状态
        self.integral = 0.0
        self.prev_error = 0.0

        # 限幅
        self.output_min = 0.0
        self.output_max = 1.0
        self.integral_limit = 0.5

    def compute(self, dt: float) -> Dict[str, float]:
        """PID控制计算"""
        # 获取输入
        pv = self.inputs.get('process_value', 0.0)
        sp = self.setpoints.get('setpoint', self.inputs.get('setpoint', 0.0))

        # 计算误差
        error = sp - pv

        # 比例项
        P = self.kp * error

        # 积分项（带抗饱和）
        self.integral += error * dt
        self.integral = np.clip(self.integral, -self.integral_limit, self.integral_limit)
        I = self.ki * self.integral

        # 微分项
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        D = self.kd * derivative
        self.prev_error = error

        # 输出
        output = P + I + D
        output = np.clip(output, self.output_min, self.output_max)

        return {
            'control_output': output,
            'error': error,
            'P': P,
            'I': I,
            'D': D,
        }

    def set_pid_params(self, kp: float, ki: float, kd: float):
        """设置PID参数"""
        self.kp = kp
        self.ki = ki
        self.kd = kd

    def reset_integral(self):
        """重置积分项"""
        self.integral = 0.0


class UnitLevelController(ControllerBase):
    """
    单元级控制器

    实现单台机组的协调控制
    控制周期：100ms
    使用MPC进行预测控制
    """

    def __init__(self, controller_id: str, unit_id: str):
        config = ControllerConfig(
            controller_id=controller_id,
            level=ControlLevel.UNIT,
            cycle_time=0.1,
        )
        super().__init__(config)

        self.unit_id = unit_id

        # MPC参数
        self.prediction_horizon = 30
        self.control_horizon = 10
        self.sample_time = 0.1

        # 约束
        self.power_max = 1000.0   # MW
        self.power_min = 0.0
        self.ramp_rate = 50.0     # MW/s

        # 状态
        self.power_target = 0.0
        self.opening_target = 0.0
        self.mode = "power"  # power, speed, opening

    def compute(self, dt: float) -> Dict[str, float]:
        """单元级控制计算"""
        # 获取输入
        current_power = self.inputs.get('power', 0.0)
        current_speed = self.inputs.get('speed', 1.0)
        current_opening = self.inputs.get('opening', 0.0)
        grid_frequency = self.inputs.get('frequency', 50.0)

        # 获取设定值
        target_power = self.setpoints.get('power', self.power_target)

        if self.mode == "power":
            # 功率控制模式
            output = self._power_control(current_power, target_power, dt)
        elif self.mode == "speed":
            # 转速控制模式
            target_speed = self.setpoints.get('speed', 1.0)
            output = self._speed_control(current_speed, target_speed, dt)
        else:
            # 开度控制模式
            target_opening = self.setpoints.get('opening', 0.0)
            output = {'opening_command': target_opening}

        # 添加调频响应
        freq_deviation = 50.0 - grid_frequency
        freq_response = freq_deviation * 20.0  # MW/Hz
        output['freq_response'] = freq_response

        return output

    def _power_control(
        self,
        current_power: float,
        target_power: float,
        dt: float
    ) -> Dict[str, float]:
        """功率控制"""
        # 限制功率变化率
        delta_power = target_power - current_power
        max_delta = self.ramp_rate * dt
        delta_power = np.clip(delta_power, -max_delta, max_delta)

        power_command = current_power + delta_power

        # 功率-开度转换（简化模型）
        opening_command = power_command / self.power_max

        return {
            'power_command': power_command,
            'opening_command': opening_command,
        }

    def _speed_control(
        self,
        current_speed: float,
        target_speed: float,
        dt: float
    ) -> Dict[str, float]:
        """转速控制"""
        error = target_speed - current_speed

        # 简单比例控制
        opening_adjustment = error * 10.0

        return {
            'opening_adjustment': opening_adjustment,
            'speed_error': error,
        }

    def set_mode(self, mode: str):
        """设置控制模式"""
        self.mode = mode


class PlantLevelController(ControllerBase):
    """
    厂站级控制器

    实现厂内多机组的优化调度
    控制周期：1s
    """

    def __init__(self, controller_id: str, plant_id: str, num_units: int):
        config = ControllerConfig(
            controller_id=controller_id,
            level=ControlLevel.PLANT,
            cycle_time=1.0,
        )
        super().__init__(config)

        self.plant_id = plant_id
        self.num_units = num_units

        # 电站参数
        self.total_capacity = 0.0    # 总装机容量 (MW)
        self.available_capacity = 0.0  # 可用容量 (MW)

        # 负荷分配
        self.load_allocation: Dict[str, float] = {}

        # 优化目标
        self.optimization_mode = "efficiency"  # efficiency, equal, stability

        # 约束
        self.min_units_online = 1
        self.max_units_online = num_units

        # 机组状态
        self.unit_status: Dict[str, str] = {}
        self.unit_efficiency: Dict[str, float] = {}

    def compute(self, dt: float) -> Dict[str, float]:
        """厂站级控制计算"""
        # 获取输入
        total_power_demand = self.inputs.get('power_demand', 0.0)
        grid_frequency = self.inputs.get('frequency', 50.0)
        agc_command = self.inputs.get('agc_command', 0.0)

        # 考虑AGC指令
        if agc_command != 0:
            total_power_demand = agc_command

        # 获取各机组状态
        for unit_id in range(self.num_units):
            unit_key = f"unit_{unit_id}"
            status = self.inputs.get(f"{unit_key}_status", "running")
            power = self.inputs.get(f"{unit_key}_power", 0.0)
            self.unit_status[unit_key] = status

        # 执行负荷分配优化
        self.load_allocation = self._optimize_load_distribution(total_power_demand)

        # 生成机组控制指令
        outputs = {}
        for unit_id, power in self.load_allocation.items():
            outputs[f"{unit_id}_power_command"] = power

        # 添加厂站总体信息
        outputs['total_power_command'] = total_power_demand
        outputs['num_units_online'] = sum(1 for s in self.unit_status.values() if s == "running")

        return outputs

    def _optimize_load_distribution(
        self,
        total_demand: float
    ) -> Dict[str, float]:
        """优化负荷分配"""
        allocation = {}

        # 获取在线机组
        online_units = [uid for uid, status in self.unit_status.items()
                       if status == "running"]

        if not online_units:
            return allocation

        if self.optimization_mode == "equal":
            # 平均分配
            per_unit = total_demand / len(online_units)
            for unit_id in online_units:
                allocation[unit_id] = per_unit

        elif self.optimization_mode == "efficiency":
            # 按效率分配（简化：优先高效机组）
            remaining = total_demand
            sorted_units = sorted(
                online_units,
                key=lambda u: self.unit_efficiency.get(u, 0.9),
                reverse=True
            )
            for unit_id in sorted_units:
                unit_capacity = self.inputs.get(f"{unit_id}_capacity", 1000.0)
                allocated = min(remaining, unit_capacity * 0.9)  # 90%负荷率
                allocation[unit_id] = allocated
                remaining -= allocated

        else:
            # 稳定性优先（均匀分配，留有裕度）
            margin = 0.8  # 80%负荷率上限
            per_unit = total_demand / len(online_units)
            for unit_id in online_units:
                unit_capacity = self.inputs.get(f"{unit_id}_capacity", 1000.0)
                allocation[unit_id] = min(per_unit, unit_capacity * margin)

        return allocation

    def request_unit_start(self, unit_id: str):
        """请求启动机组"""
        cmd = ControlCommand(
            target_id=unit_id,
            command_type="start",
            value=1.0,
            timestamp=time.time(),
            source=self.config.controller_id,
        )
        self.send_command(cmd)

    def request_unit_stop(self, unit_id: str):
        """请求停止机组"""
        cmd = ControlCommand(
            target_id=unit_id,
            command_type="stop",
            value=0.0,
            timestamp=time.time(),
            source=self.config.controller_id,
        )
        self.send_command(cmd)


class CascadeLevelController(ControllerBase):
    """
    梯级调度级控制器

    实现多电站的协调优化
    控制周期：60s
    """

    def __init__(self, controller_id: str, cascade_name: str):
        config = ControllerConfig(
            controller_id=controller_id,
            level=ControlLevel.CASCADE,
            cycle_time=60.0,
        )
        super().__init__(config)

        self.cascade_name = cascade_name

        # 电站信息
        self.stations: Dict[str, Dict] = {}

        # 水库信息
        self.reservoirs: Dict[str, Dict] = {}

        # 调度目标
        self.dispatch_mode = "total_power"  # total_power, water_level, peak_shaving

        # 约束
        self.total_power_max = 0.0
        self.water_level_limits: Dict[str, Tuple[float, float]] = {}

        # 水力联系
        self.hydraulic_connections: List[Tuple[str, str, float]] = []  # (上游, 下游, 时滞)

    def compute(self, dt: float) -> Dict[str, float]:
        """梯级调度计算"""
        # 获取输入
        grid_demand = self.inputs.get('grid_demand', 0.0)
        grid_frequency = self.inputs.get('frequency', 50.0)

        # 获取各电站状态
        for station_id in self.stations.keys():
            power = self.inputs.get(f"{station_id}_power", 0.0)
            level = self.inputs.get(f"{station_id}_level", 0.0)
            inflow = self.inputs.get(f"{station_id}_inflow", 0.0)

            self.stations[station_id].update({
                'current_power': power,
                'current_level': level,
                'inflow': inflow,
            })

        # 执行梯级优化
        station_commands = self._optimize_cascade(grid_demand)

        # 生成输出
        outputs = {}
        for station_id, command in station_commands.items():
            outputs[f"{station_id}_power_command"] = command['power']
            outputs[f"{station_id}_level_target"] = command.get('level_target', 0.0)

        # 梯级总体信息
        outputs['total_power'] = sum(s.get('current_power', 0) for s in self.stations.values())
        outputs['dispatch_mode'] = self.dispatch_mode

        return outputs

    def _optimize_cascade(self, total_demand: float) -> Dict[str, Dict]:
        """梯级优化"""
        commands = {}

        if self.dispatch_mode == "total_power":
            # 按装机容量比例分配
            total_capacity = sum(s.get('capacity', 0) for s in self.stations.values())
            if total_capacity > 0:
                for station_id, station in self.stations.items():
                    capacity = station.get('capacity', 0)
                    ratio = capacity / total_capacity
                    commands[station_id] = {
                        'power': total_demand * ratio,
                    }

        elif self.dispatch_mode == "water_level":
            # 水位控制优先
            for station_id, station in self.stations.items():
                current_level = station.get('current_level', 0)
                target_level = station.get('target_level', 0)
                level_error = target_level - current_level

                # 根据水位偏差调整出力
                base_power = station.get('base_power', 0)
                power_adjustment = level_error * 10.0  # MW/m
                commands[station_id] = {
                    'power': base_power + power_adjustment,
                    'level_target': target_level,
                }

        elif self.dispatch_mode == "peak_shaving":
            # 调峰模式
            # 简化：高峰时增出力，低谷时减出力
            hour = (time.time() / 3600) % 24
            if 8 <= hour <= 12 or 18 <= hour <= 22:
                # 高峰时段
                factor = 1.2
            elif 0 <= hour <= 6:
                # 低谷时段
                factor = 0.7
            else:
                factor = 1.0

            for station_id, station in self.stations.items():
                base_power = station.get('base_power', 0)
                commands[station_id] = {
                    'power': base_power * factor,
                }

        return commands

    def add_station(
        self,
        station_id: str,
        capacity: float,
        controller: PlantLevelController
    ):
        """添加电站"""
        self.stations[station_id] = {
            'capacity': capacity,
            'current_power': 0.0,
            'current_level': 0.0,
            'base_power': capacity * 0.5,
        }
        self.add_sub_controller(station_id, controller)
        self.total_power_max += capacity

    def add_hydraulic_connection(
        self,
        upstream_id: str,
        downstream_id: str,
        time_lag: float
    ):
        """添加水力联系"""
        self.hydraulic_connections.append((upstream_id, downstream_id, time_lag))


class DistributedController:
    """
    分层分布式控制器总成

    管理完整的四层控制架构
    """

    def __init__(self, name: str = "yajiang_cascade"):
        self.name = name

        # 各层控制器
        self.cascade_controller: Optional[CascadeLevelController] = None
        self.plant_controllers: Dict[str, PlantLevelController] = {}
        self.unit_controllers: Dict[str, UnitLevelController] = {}
        self.field_controllers: Dict[str, FieldLevelController] = {}

        # 通信管理
        self.message_bus: queue.Queue = queue.Queue()

        # 状态
        self.is_running = False
        self.cycle_count = 0
        self.last_update_time = 0.0

    def build_hierarchy(self, cascade_config: Dict):
        """
        构建控制层级

        Args:
            cascade_config: 梯级配置字典
        """
        # 创建梯级控制器
        self.cascade_controller = CascadeLevelController(
            controller_id="cascade_ctrl",
            cascade_name=self.name
        )

        # 创建各电站控制器
        for station in cascade_config.get('stations', []):
            station_id = station['id']
            num_units = station['num_units']

            # 厂站级控制器
            plant_ctrl = PlantLevelController(
                controller_id=f"{station_id}_plant",
                plant_id=station_id,
                num_units=num_units
            )
            self.plant_controllers[station_id] = plant_ctrl

            # 添加到梯级控制器
            self.cascade_controller.add_station(
                station_id,
                station['installed_capacity'],
                plant_ctrl
            )

            # 创建机组级控制器
            for i in range(num_units):
                unit_id = f"{station_id}_unit_{i}"

                unit_ctrl = UnitLevelController(
                    controller_id=f"{unit_id}_ctrl",
                    unit_id=unit_id
                )
                self.unit_controllers[unit_id] = unit_ctrl
                plant_ctrl.add_sub_controller(unit_id, unit_ctrl)

                # 创建现场级控制器
                for control_loop in ['speed', 'opening', 'voltage']:
                    field_id = f"{unit_id}_{control_loop}"
                    field_ctrl = FieldLevelController(controller_id=field_id)
                    self.field_controllers[field_id] = field_ctrl
                    unit_ctrl.add_sub_controller(field_id, field_ctrl)

    def update(
        self,
        inputs: Dict[str, Dict[str, float]],
        dt: float
    ) -> Dict[str, Dict[str, float]]:
        """
        更新所有控制器

        Args:
            inputs: 各层输入信号
            dt: 时间步长

        Returns:
            各层输出信号
        """
        outputs = {}

        # 自底向上更新
        # 1. 现场级
        field_outputs = {}
        for ctrl_id, ctrl in self.field_controllers.items():
            field_inputs = inputs.get('field', {}).get(ctrl_id, {})
            field_outputs[ctrl_id] = ctrl.update(field_inputs, dt)
        outputs['field'] = field_outputs

        # 2. 单元级
        unit_outputs = {}
        for ctrl_id, ctrl in self.unit_controllers.items():
            unit_inputs = inputs.get('unit', {}).get(ctrl_id, {})
            # 合并现场级输出
            for sub_id in ctrl.sub_controllers.keys():
                if sub_id in field_outputs:
                    unit_inputs.update(field_outputs[sub_id])
            unit_outputs[ctrl_id] = ctrl.update(unit_inputs, dt)
        outputs['unit'] = unit_outputs

        # 3. 厂站级
        plant_outputs = {}
        for ctrl_id, ctrl in self.plant_controllers.items():
            plant_inputs = inputs.get('plant', {}).get(ctrl_id, {})
            plant_outputs[ctrl_id] = ctrl.update(plant_inputs, dt)
        outputs['plant'] = plant_outputs

        # 4. 梯级调度级
        if self.cascade_controller:
            cascade_inputs = inputs.get('cascade', {})
            outputs['cascade'] = self.cascade_controller.update(cascade_inputs, dt)

        self.cycle_count += 1

        return outputs

    def start(self):
        """启动所有控制器"""
        self.is_running = True

        if self.cascade_controller:
            self.cascade_controller.start()

        for ctrl in self.plant_controllers.values():
            ctrl.start()

        for ctrl in self.unit_controllers.values():
            ctrl.start()

        for ctrl in self.field_controllers.values():
            ctrl.start()

    def stop(self):
        """停止所有控制器"""
        self.is_running = False

        for ctrl in self.field_controllers.values():
            ctrl.stop()

        for ctrl in self.unit_controllers.values():
            ctrl.stop()

        for ctrl in self.plant_controllers.values():
            ctrl.stop()

        if self.cascade_controller:
            self.cascade_controller.stop()

    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            'name': self.name,
            'is_running': self.is_running,
            'cycle_count': self.cycle_count,
            'num_field_controllers': len(self.field_controllers),
            'num_unit_controllers': len(self.unit_controllers),
            'num_plant_controllers': len(self.plant_controllers),
            'cascade_controller': self.cascade_controller is not None,
        }

    def get_all_diagnostics(self) -> Dict[str, Dict]:
        """获取所有诊断信息"""
        diagnostics = {}

        if self.cascade_controller:
            diagnostics['cascade'] = self.cascade_controller.get_diagnostics()

        for ctrl_id, ctrl in self.plant_controllers.items():
            diagnostics[f'plant_{ctrl_id}'] = ctrl.get_diagnostics()

        for ctrl_id, ctrl in self.unit_controllers.items():
            diagnostics[f'unit_{ctrl_id}'] = ctrl.get_diagnostics()

        return diagnostics
