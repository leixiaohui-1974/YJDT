"""
仿真引擎模块
Simulation Engine Module

实现完整的水电站仿真引擎：
- 单机组仿真
- 梯级电站仿真
- 实时仿真
- 快速仿真
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import time as time_module
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


class SimulationMode(Enum):
    """仿真模式"""
    REALTIME = "realtime"          # 实时仿真
    FAST = "fast"                  # 快速仿真
    STEP = "step"                  # 单步仿真
    BATCH = "batch"                # 批量仿真


class SimulationStatus(Enum):
    """仿真状态"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SimulationConfig:
    """仿真配置"""
    # 时间参数
    start_time: float = 0.0
    end_time: float = 300.0
    time_step: float = 0.01
    output_interval: float = 0.1

    # 仿真模式
    mode: SimulationMode = SimulationMode.FAST
    realtime_factor: float = 1.0

    # 求解器配置
    solver: str = "euler"  # euler, rk4, adaptive
    tolerance: float = 1e-6
    max_iterations: int = 100

    # 并行配置
    parallel: bool = False
    num_workers: int = 4

    # 日志配置
    log_level: str = "info"
    save_history: bool = True


@dataclass
class SimulationResult:
    """仿真结果"""
    config: SimulationConfig
    status: SimulationStatus

    # 时间序列数据
    time: np.ndarray = field(default_factory=lambda: np.array([]))
    data: Dict[str, np.ndarray] = field(default_factory=dict)

    # 统计信息
    computation_time: float = 0.0
    num_steps: int = 0
    max_error: float = 0.0

    # 事件日志
    events: List[Dict[str, Any]] = field(default_factory=list)

    def get_signal(self, name: str) -> np.ndarray:
        """获取指定信号"""
        return self.data.get(name, np.array([]))

    def get_statistics(self, name: str) -> Dict[str, float]:
        """获取信号统计"""
        signal = self.get_signal(name)
        if len(signal) == 0:
            return {}
        return {
            'min': float(np.min(signal)),
            'max': float(np.max(signal)),
            'mean': float(np.mean(signal)),
            'std': float(np.std(signal)),
        }


class SimulationEngine:
    """
    仿真引擎

    管理和协调整个仿真过程
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.status = SimulationStatus.IDLE

        # 仿真组件
        self.models: Dict[str, Any] = {}
        self.controllers: Dict[str, Any] = {}
        self.sensors: Dict[str, Any] = {}
        self.actuators: Dict[str, Any] = {}

        # 状态变量
        self.current_time = 0.0
        self.step_count = 0

        # 数据记录
        self.history: Dict[str, List[float]] = {}
        self.time_history: List[float] = []

        # 回调函数
        self.callbacks: Dict[str, List[Callable]] = {
            'pre_step': [],
            'post_step': [],
            'on_event': [],
            'on_complete': [],
        }

        # 事件队列
        self.event_queue: List[Dict] = []

    def add_model(self, model_id: str, model: Any):
        """添加仿真模型"""
        self.models[model_id] = model

    def add_controller(self, controller_id: str, controller: Any):
        """添加控制器"""
        self.controllers[controller_id] = controller

    def add_sensor(self, sensor_id: str, sensor: Any):
        """添加传感器"""
        self.sensors[sensor_id] = sensor

    def add_actuator(self, actuator_id: str, actuator: Any):
        """添加执行器"""
        self.actuators[actuator_id] = actuator

    def register_callback(self, event: str, callback: Callable):
        """注册回调函数"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def schedule_event(self, time: float, event_type: str, data: Dict = None):
        """调度事件"""
        self.event_queue.append({
            'time': time,
            'type': event_type,
            'data': data or {},
        })
        self.event_queue.sort(key=lambda x: x['time'])

    def initialize(self):
        """初始化仿真"""
        self.status = SimulationStatus.INITIALIZING

        self.current_time = self.config.start_time
        self.step_count = 0
        self.history = {}
        self.time_history = []

        # 初始化各组件
        for model in self.models.values():
            if hasattr(model, 'initialize'):
                model.initialize()

        for controller in self.controllers.values():
            if hasattr(controller, 'start'):
                controller.start()

        self.status = SimulationStatus.IDLE

    def step(self) -> Dict[str, float]:
        """执行单步仿真"""
        dt = self.config.time_step

        # 预处理回调
        for callback in self.callbacks['pre_step']:
            callback(self.current_time, dt)

        # 处理事件
        self._process_events()

        # 收集传感器数据
        sensor_data = self._collect_sensor_data()

        # 控制器计算
        control_outputs = self._compute_control(sensor_data)

        # 执行器动作
        self._apply_actuator_commands(control_outputs)

        # 模型更新
        model_outputs = self._update_models(dt)

        # 合并输出
        outputs = {**sensor_data, **control_outputs, **model_outputs}

        # 记录历史
        if self.config.save_history:
            self._record_history(outputs)

        # 更新时间
        self.current_time += dt
        self.step_count += 1

        # 后处理回调
        for callback in self.callbacks['post_step']:
            callback(self.current_time, outputs)

        return outputs

    def _process_events(self):
        """处理事件队列"""
        while self.event_queue and self.event_queue[0]['time'] <= self.current_time:
            event = self.event_queue.pop(0)
            for callback in self.callbacks['on_event']:
                callback(event)

    def _collect_sensor_data(self) -> Dict[str, float]:
        """收集传感器数据"""
        data = {}
        for sensor_id, sensor in self.sensors.items():
            if hasattr(sensor, 'measured_value'):
                data[sensor_id] = sensor.measured_value
        return data

    def _compute_control(self, inputs: Dict[str, float]) -> Dict[str, float]:
        """计算控制输出"""
        outputs = {}
        dt = self.config.time_step

        for ctrl_id, controller in self.controllers.items():
            if hasattr(controller, 'update'):
                result = controller.update(inputs, dt)
                if isinstance(result, dict):
                    outputs.update(result)
                else:
                    outputs[f"{ctrl_id}_output"] = result

        return outputs

    def _apply_actuator_commands(self, commands: Dict[str, float]):
        """应用执行器命令"""
        dt = self.config.time_step

        for actuator_id, actuator in self.actuators.items():
            if actuator_id in commands:
                if hasattr(actuator, 'set_command'):
                    actuator.set_command(commands[actuator_id])
            if hasattr(actuator, 'update'):
                actuator.update(dt, self.current_time)

    def _update_models(self, dt: float) -> Dict[str, float]:
        """更新仿真模型"""
        outputs = {}

        for model_id, model in self.models.items():
            if hasattr(model, 'step'):
                result = model.step(dt)
                if isinstance(result, dict):
                    for k, v in result.items():
                        outputs[f"{model_id}_{k}"] = v

        return outputs

    def _record_history(self, data: Dict[str, float]):
        """记录历史数据"""
        self.time_history.append(self.current_time)

        for key, value in data.items():
            if key not in self.history:
                self.history[key] = []
            self.history[key].append(value)

    def run(self) -> SimulationResult:
        """运行仿真"""
        self.initialize()
        self.status = SimulationStatus.RUNNING

        start_time = time_module.time()

        while self.current_time < self.config.end_time:
            if self.status != SimulationStatus.RUNNING:
                break

            self.step()

            # 实时仿真控制
            if self.config.mode == SimulationMode.REALTIME:
                elapsed = time_module.time() - start_time
                target = self.current_time / self.config.realtime_factor
                if elapsed < target:
                    time_module.sleep(target - elapsed)

        computation_time = time_module.time() - start_time
        self.status = SimulationStatus.COMPLETED

        # 完成回调
        for callback in self.callbacks['on_complete']:
            callback()

        return SimulationResult(
            config=self.config,
            status=self.status,
            time=np.array(self.time_history),
            data={k: np.array(v) for k, v in self.history.items()},
            computation_time=computation_time,
            num_steps=self.step_count,
        )

    def pause(self):
        """暂停仿真"""
        self.status = SimulationStatus.PAUSED

    def resume(self):
        """恢复仿真"""
        if self.status == SimulationStatus.PAUSED:
            self.status = SimulationStatus.RUNNING

    def stop(self):
        """停止仿真"""
        self.status = SimulationStatus.IDLE


class HydropowerUnitSimulator:
    """
    水电机组仿真器

    集成水力系统、水轮机、发电机、控制系统的完整仿真
    """

    def __init__(self, unit_config: Dict):
        self.config = unit_config
        self.engine = SimulationEngine()

        # 机组状态
        self.power = 0.0
        self.speed = 0.0
        self.opening = 0.0
        self.head = 0.0
        self.flow = 0.0
        self.voltage = 1.0
        self.frequency = 50.0

        # 初始化组件
        self._init_components()

    def _init_components(self):
        """初始化机组组件"""
        from yjdt.core.hydraulic import Pipeline, PipelineParams, HydraulicSystem
        from yjdt.core.turbine import FrancisTurbine, TurbineParams, TurbineType
        from yjdt.core.generator import SynchronousGenerator, GeneratorParams
        from yjdt.core.governor import PIDGovernor, GovernorParams
        from yjdt.sensors.sensors import (
            PressureSensor, FlowSensor, SpeedSensor, PowerSensor, PositionSensor
        )
        from yjdt.sensors.actuators import GuideVaneActuator

        # 水力系统
        pipeline_params = PipelineParams(
            length=self.config.get('tunnel_length', 25000),
            diameter=self.config.get('tunnel_diameter', 11),
            wave_speed=self.config.get('wave_speed', 1350),
            friction_factor=self.config.get('friction_factor', 0.015),
        )
        pipeline = Pipeline(pipeline_params)

        # 水轮机
        turbine_params = TurbineParams(
            turbine_type=TurbineType.FRANCIS,
            rated_power=self.config.get('rated_power', 1000),
            rated_head=self.config.get('rated_head', 480),
            rated_flow=self.config.get('rated_flow', 210),
            rated_speed=self.config.get('rated_speed', 166.7),
        )
        turbine = FrancisTurbine(turbine_params)

        # 发电机
        generator_params = GeneratorParams(
            rated_power=self.config.get('rated_power', 1000) * 1.111,
            rated_frequency=50.0,
        )
        generator = SynchronousGenerator(generator_params)

        # 调速器
        governor_params = GovernorParams(
            kp=self.config.get('kp', 2.5),
            ki=self.config.get('ki', 0.15),
            kd=self.config.get('kd', 4.0),
        )
        governor = PIDGovernor(governor_params)

        # 传感器
        pressure_sensor = PressureSensor("pressure")
        flow_sensor = FlowSensor("flow")
        speed_sensor = SpeedSensor("speed")
        power_sensor = PowerSensor("power")
        position_sensor = PositionSensor("opening")

        # 执行器
        guide_vane = GuideVaneActuator("guide_vane")

        # 添加到引擎
        self.engine.add_model('pipeline', pipeline)
        self.engine.add_model('turbine', turbine)
        self.engine.add_model('generator', generator)
        self.engine.add_controller('governor', governor)
        self.engine.add_sensor('pressure', pressure_sensor)
        self.engine.add_sensor('flow', flow_sensor)
        self.engine.add_sensor('speed', speed_sensor)
        self.engine.add_sensor('power', power_sensor)
        self.engine.add_sensor('opening', position_sensor)
        self.engine.add_actuator('guide_vane', guide_vane)

    def run_scenario(self, scenario: 'Scenario') -> SimulationResult:
        """
        运行指定场景

        Args:
            scenario: 场景对象

        Returns:
            仿真结果
        """
        # 设置仿真时间
        self.engine.config.end_time = scenario.duration

        # 设置初始条件
        self.power = scenario.initial_condition.initial_power
        self.speed = scenario.initial_condition.initial_speed
        self.opening = scenario.initial_condition.initial_opening
        self.head = scenario.initial_condition.upstream_level - scenario.initial_condition.downstream_level

        # 调度场景事件
        for event in scenario.events:
            self.engine.schedule_event(
                event.time,
                event.event_type,
                event.parameters
            )

        # 运行仿真
        return self.engine.run()


class CascadeSimulator:
    """
    梯级电站仿真器

    仿真多电站的协调运行
    """

    def __init__(self, cascade_config: Dict):
        self.config = cascade_config
        self.stations: Dict[str, HydropowerUnitSimulator] = {}

        # 水力联系
        self.hydraulic_connections: List[Tuple[str, str, float]] = []

        # 初始化各电站
        self._init_stations()

    def _init_stations(self):
        """初始化各电站"""
        for station in self.config.get('stations', []):
            station_id = station['id']
            unit_config = {
                'rated_power': station.get('installed_capacity', 1000) / station.get('num_units', 1),
                'rated_head': 480,
            }
            self.stations[station_id] = HydropowerUnitSimulator(unit_config)

    def add_hydraulic_connection(
        self,
        upstream: str,
        downstream: str,
        time_lag: float
    ):
        """添加水力联系"""
        self.hydraulic_connections.append((upstream, downstream, time_lag))

    def run_parallel(
        self,
        scenario: 'Scenario',
        num_workers: int = 4
    ) -> Dict[str, SimulationResult]:
        """并行运行各电站仿真"""
        results = {}

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                station_id: executor.submit(station.run_scenario, scenario)
                for station_id, station in self.stations.items()
            }

            for station_id, future in futures.items():
                results[station_id] = future.result()

        return results

    def get_cascade_summary(
        self,
        results: Dict[str, SimulationResult]
    ) -> Dict:
        """获取梯级汇总"""
        total_power = 0.0
        total_generation = 0.0

        for station_id, result in results.items():
            if 'power' in result.data:
                power_data = result.data['power']
                avg_power = np.mean(power_data) if len(power_data) > 0 else 0
                total_power += avg_power

                # 发电量 (MWh)
                duration_hours = (result.time[-1] - result.time[0]) / 3600 if len(result.time) > 1 else 0
                generation = avg_power * duration_hours
                total_generation += generation

        return {
            'total_power_mw': total_power,
            'total_generation_mwh': total_generation,
            'num_stations': len(results),
            'stations': list(results.keys()),
        }
