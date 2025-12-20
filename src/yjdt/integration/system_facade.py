# -*- coding: utf-8 -*-
"""
系统外观模式 - System Facade

功能：
- 统一系统入口
- 组件编排与生命周期管理
- 配置驱动的系统构建
- 运行时监控与管理
- 模块间协调

设计模式：
- Facade: 简化复杂子系统的接口
- Builder: 灵活构建系统配置
- Registry: 组件注册与发现
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Type, Union
from datetime import datetime, timedelta
from enum import Enum
import threading
import time
import logging

logger = logging.getLogger(__name__)


class ComponentState(Enum):
    """组件状态"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class SystemMode(Enum):
    """系统运行模式"""
    SIMULATION = "simulation"       # 纯仿真模式
    HIL = "hil"                     # 硬件在环
    SIL = "sil"                     # 软件在环
    ONLINE = "online"               # 在线运行
    REPLAY = "replay"               # 数据回放
    TRAINING = "training"           # AI训练模式


@dataclass
class ComponentConfig:
    """组件配置"""
    name: str
    component_type: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 100


@dataclass
class SystemConfig:
    """系统配置"""
    name: str = "YJDT雅江水电梯级智能控制系统"
    mode: SystemMode = SystemMode.SIMULATION

    # 组件配置
    components: Dict[str, ComponentConfig] = field(default_factory=dict)

    # 时间配置
    simulation_step: float = 0.01  # 仿真步长 s
    realtime_factor: float = 1.0   # 实时因子

    # 通信配置
    data_bus_type: str = "internal"
    message_queue_size: int = 10000

    # 日志配置
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "logs/yjdt.log"


@dataclass
class IntegrationContext:
    """集成上下文 - 组件间共享的上下文信息"""
    system_time: datetime = field(default_factory=datetime.now)
    simulation_time: float = 0.0
    is_running: bool = False
    mode: SystemMode = SystemMode.SIMULATION

    # 共享数据
    shared_data: Dict[str, Any] = field(default_factory=dict)

    # 事件队列
    pending_events: List[Dict[str, Any]] = field(default_factory=list)

    # 诊断信息
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class ComponentRegistry:
    """
    组件注册中心

    管理所有可用组件的注册、发现和实例化
    """

    def __init__(self):
        self._registered_types: Dict[str, Type] = {}
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._metadata: Dict[str, Dict] = {}

    def register_type(self, name: str, component_type: Type,
                      metadata: Optional[Dict] = None):
        """注册组件类型"""
        self._registered_types[name] = component_type
        self._metadata[name] = metadata or {}
        logger.info(f"Registered component type: {name}")

    def register_factory(self, name: str, factory: Callable,
                         metadata: Optional[Dict] = None):
        """注册组件工厂"""
        self._factories[name] = factory
        self._metadata[name] = metadata or {}
        logger.info(f"Registered component factory: {name}")

    def register_instance(self, name: str, instance: Any):
        """注册组件实例"""
        self._instances[name] = instance
        logger.info(f"Registered component instance: {name}")

    def get_instance(self, name: str) -> Optional[Any]:
        """获取组件实例"""
        return self._instances.get(name)

    def create_instance(self, type_name: str, config: Dict[str, Any] = None) -> Any:
        """创建组件实例"""
        config = config or {}

        if type_name in self._factories:
            return self._factories[type_name](**config)
        elif type_name in self._registered_types:
            return self._registered_types[type_name](**config)
        else:
            raise ValueError(f"Unknown component type: {type_name}")

    def list_types(self) -> List[str]:
        """列出所有注册的类型"""
        return list(set(list(self._registered_types.keys()) +
                       list(self._factories.keys())))

    def list_instances(self) -> List[str]:
        """列出所有实例"""
        return list(self._instances.keys())

    def get_metadata(self, name: str) -> Dict:
        """获取组件元数据"""
        return self._metadata.get(name, {})


class SystemBuilder:
    """
    系统构建器

    使用Builder模式灵活构建系统配置
    """

    def __init__(self):
        self._config = SystemConfig()
        self._registry = ComponentRegistry()
        self._custom_initializers: List[Callable] = []

    def set_name(self, name: str) -> 'SystemBuilder':
        """设置系统名称"""
        self._config.name = name
        return self

    def set_mode(self, mode: SystemMode) -> 'SystemBuilder':
        """设置运行模式"""
        self._config.mode = mode
        return self

    def set_simulation_step(self, step: float) -> 'SystemBuilder':
        """设置仿真步长"""
        self._config.simulation_step = step
        return self

    def set_realtime_factor(self, factor: float) -> 'SystemBuilder':
        """设置实时因子"""
        self._config.realtime_factor = factor
        return self

    def add_component(self, name: str, component_type: str,
                      config: Dict[str, Any] = None,
                      dependencies: List[str] = None,
                      priority: int = 100) -> 'SystemBuilder':
        """添加组件"""
        self._config.components[name] = ComponentConfig(
            name=name,
            component_type=component_type,
            config=config or {},
            dependencies=dependencies or [],
            priority=priority
        )
        return self

    def add_hydraulic_system(self, config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加水力系统"""
        return self.add_component(
            "hydraulic_system", "HydraulicSystem",
            config=config,
            priority=10
        )

    def add_turbine(self, turbine_id: str, turbine_type: str = "Francis",
                    config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加水轮机"""
        return self.add_component(
            f"turbine_{turbine_id}",
            f"{turbine_type}Turbine",
            config=config,
            dependencies=["hydraulic_system"],
            priority=20
        )

    def add_generator(self, generator_id: str,
                      config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加发电机"""
        return self.add_component(
            f"generator_{generator_id}",
            "SynchronousGenerator",
            config=config,
            priority=20
        )

    def add_governor(self, governor_id: str, governor_type: str = "PID",
                     config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加调速器"""
        return self.add_component(
            f"governor_{governor_id}",
            f"{governor_type}Governor",
            config=config,
            priority=30
        )

    def add_mpc_controller(self, config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加MPC控制器"""
        return self.add_component(
            "mpc_controller", "MPCSolver",
            config=config,
            priority=30
        )

    def add_digital_twin(self, config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加数字孪生"""
        return self.add_component(
            "digital_twin", "DigitalTwinEngine",
            config=config,
            dependencies=["hydraulic_system"],
            priority=40
        )

    def add_monitoring(self, config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加监控系统"""
        return self.add_component(
            "realtime_monitor", "RealtimeMonitor",
            config=config,
            priority=50
        )

    def add_safety_analysis(self, config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加安全分析"""
        return self.add_component(
            "psa_analyzer", "PSAAnalyzer",
            config=config,
            priority=60
        )

    def add_scheduler(self, config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加调度优化"""
        return self.add_component(
            "scheduler", "CascadeSchedulingSolver",
            config=config,
            priority=35
        )

    def add_security(self, config: Dict[str, Any] = None) -> 'SystemBuilder':
        """添加安全防护"""
        return self.add_component(
            "security", "SecuritySituationAwareness",
            config=config,
            priority=70
        )

    def add_custom_initializer(self, initializer: Callable) -> 'SystemBuilder':
        """添加自定义初始化器"""
        self._custom_initializers.append(initializer)
        return self

    def from_yaml(self, yaml_path: str) -> 'SystemBuilder':
        """从YAML配置文件加载"""
        import yaml

        with open(yaml_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)

        if 'name' in config_dict:
            self._config.name = config_dict['name']
        if 'mode' in config_dict:
            self._config.mode = SystemMode(config_dict['mode'])
        if 'simulation_step' in config_dict:
            self._config.simulation_step = config_dict['simulation_step']

        for name, comp_config in config_dict.get('components', {}).items():
            self.add_component(
                name=name,
                component_type=comp_config.get('type', 'Unknown'),
                config=comp_config.get('config', {}),
                dependencies=comp_config.get('dependencies', []),
                priority=comp_config.get('priority', 100)
            )

        return self

    def build(self) -> 'YJDTSystem':
        """构建系统"""
        system = YJDTSystem(self._config, self._registry)

        # 执行自定义初始化
        for initializer in self._custom_initializers:
            initializer(system)

        return system


class YJDTSystem:
    """
    雅江水电梯级智能控制系统 - 统一入口

    功能：
    - 系统生命周期管理
    - 组件协调与调度
    - 仿真循环控制
    - 状态监控与诊断
    - 事件处理

    使用示例:
        # 方式1: Builder模式
        system = (SystemBuilder()
            .set_name("雅江梯级控制系统")
            .set_mode(SystemMode.SIMULATION)
            .add_hydraulic_system()
            .add_turbine("1", "Francis")
            .add_generator("1")
            .add_mpc_controller()
            .add_digital_twin()
            .build())

        system.initialize()
        system.start()

        # 方式2: 快速创建
        system = YJDTSystem.create_standard_system()
        system.run_simulation(duration=3600)
    """

    def __init__(self, config: SystemConfig = None,
                 registry: ComponentRegistry = None):
        self.config = config or SystemConfig()
        self.registry = registry or ComponentRegistry()
        self.context = IntegrationContext(mode=self.config.mode)

        # 状态管理
        self._state = ComponentState.UNINITIALIZED
        self._lock = threading.RLock()

        # 组件实例
        self._components: Dict[str, Any] = {}
        self._component_states: Dict[str, ComponentState] = {}

        # 仿真控制
        self._simulation_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 事件处理
        self._event_handlers: Dict[str, List[Callable]] = {}

        # 性能统计
        self._stats = {
            'total_steps': 0,
            'total_time': 0.0,
            'avg_step_time': 0.0,
            'max_step_time': 0.0,
        }

        # 注册默认组件
        self._register_default_components()

    def _register_default_components(self):
        """注册默认组件类型"""
        from yjdt.core.hydraulic import HydraulicSystem
        from yjdt.core.turbine import FrancisTurbine, PeltonTurbine
        from yjdt.core.generator import SynchronousGenerator
        from yjdt.core.governor import PIDGovernor, MPCGovernor
        from yjdt.simulation.engine import SimulationEngine
        from yjdt.control.mpc_solver import MPCSolver
        from yjdt.digital_twin.twin_engine import DigitalTwinEngine
        from yjdt.monitoring.realtime_monitor import RealtimeMonitor
        from yjdt.safety.psa_analysis import PSAAnalyzer
        from yjdt.optimization.scheduling_solver import CascadeSchedulingSolver

        self.registry.register_type("HydraulicSystem", HydraulicSystem)
        self.registry.register_type("FrancisTurbine", FrancisTurbine)
        self.registry.register_type("PeltonTurbine", PeltonTurbine)
        self.registry.register_type("SynchronousGenerator", SynchronousGenerator)
        self.registry.register_type("PIDGovernor", PIDGovernor)
        self.registry.register_type("MPCGovernor", MPCGovernor)
        self.registry.register_type("SimulationEngine", SimulationEngine)
        self.registry.register_type("MPCSolver", MPCSolver)
        self.registry.register_type("DigitalTwinEngine", DigitalTwinEngine)
        self.registry.register_type("RealtimeMonitor", RealtimeMonitor)
        self.registry.register_type("PSAAnalyzer", PSAAnalyzer)
        self.registry.register_type("CascadeSchedulingSolver", CascadeSchedulingSolver)

    @property
    def state(self) -> ComponentState:
        """获取系统状态"""
        return self._state

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._state == ComponentState.RUNNING

    def initialize(self) -> bool:
        """
        初始化系统

        按依赖顺序初始化所有组件
        """
        with self._lock:
            if self._state != ComponentState.UNINITIALIZED:
                logger.warning(f"System already in state: {self._state}")
                return False

            self._state = ComponentState.INITIALIZING
            logger.info(f"Initializing system: {self.config.name}")

            try:
                # 按优先级排序组件
                sorted_components = sorted(
                    self.config.components.items(),
                    key=lambda x: x[1].priority
                )

                # 初始化各组件
                for name, comp_config in sorted_components:
                    if not comp_config.enabled:
                        continue

                    # 检查依赖
                    for dep in comp_config.dependencies:
                        if dep not in self._components:
                            logger.error(f"Dependency not satisfied: {dep} for {name}")
                            continue

                    # 创建组件实例
                    try:
                        instance = self.registry.create_instance(
                            comp_config.component_type,
                            comp_config.config
                        )
                        self._components[name] = instance
                        self._component_states[name] = ComponentState.READY
                        self.registry.register_instance(name, instance)
                        logger.info(f"Initialized component: {name}")
                    except Exception as e:
                        logger.error(f"Failed to initialize {name}: {e}")
                        self._component_states[name] = ComponentState.ERROR

                self._state = ComponentState.READY
                self.context.is_running = False

                self._emit_event('system_initialized', {
                    'components': list(self._components.keys())
                })

                return True

            except Exception as e:
                logger.error(f"System initialization failed: {e}")
                self._state = ComponentState.ERROR
                return False

    def start(self, async_mode: bool = True) -> bool:
        """
        启动系统

        Args:
            async_mode: 是否异步运行
        """
        with self._lock:
            if self._state != ComponentState.READY:
                logger.warning(f"Cannot start from state: {self._state}")
                return False

            self._state = ComponentState.RUNNING
            self.context.is_running = True
            self._stop_event.clear()

            logger.info("Starting system...")

            if async_mode:
                self._simulation_thread = threading.Thread(
                    target=self._simulation_loop,
                    name="YJDT-SimulationLoop"
                )
                self._simulation_thread.start()
            else:
                self._simulation_loop()

            return True

    def stop(self, timeout: float = 10.0) -> bool:
        """停止系统"""
        with self._lock:
            if self._state != ComponentState.RUNNING:
                return False

            self._state = ComponentState.STOPPING
            self.context.is_running = False
            self._stop_event.set()

            if self._simulation_thread and self._simulation_thread.is_alive():
                self._simulation_thread.join(timeout=timeout)

            self._state = ComponentState.STOPPED
            self._emit_event('system_stopped', {})

            logger.info("System stopped")
            return True

    def pause(self):
        """暂停系统"""
        if self._state == ComponentState.RUNNING:
            self._state = ComponentState.PAUSED
            logger.info("System paused")

    def resume(self):
        """恢复系统"""
        if self._state == ComponentState.PAUSED:
            self._state = ComponentState.RUNNING
            logger.info("System resumed")

    def step(self) -> Dict[str, Any]:
        """
        执行一个仿真步

        Returns:
            步骤结果
        """
        step_start = time.time()

        results = {}

        # 更新仿真时间
        self.context.simulation_time += self.config.simulation_step
        self.context.system_time = datetime.now()

        # 按优先级执行各组件
        sorted_components = sorted(
            self._components.items(),
            key=lambda x: self.config.components.get(x[0], ComponentConfig(x[0], "")).priority
        )

        for name, component in sorted_components:
            if self._component_states.get(name) == ComponentState.ERROR:
                continue

            try:
                if hasattr(component, 'step'):
                    result = component.step(self.config.simulation_step)
                    results[name] = result
                elif hasattr(component, 'update'):
                    result = component.update(self.config.simulation_step)
                    results[name] = result
            except Exception as e:
                logger.error(f"Component {name} step failed: {e}")
                self._component_states[name] = ComponentState.ERROR

        # 处理事件
        self._process_pending_events()

        # 更新统计
        step_time = time.time() - step_start
        self._stats['total_steps'] += 1
        self._stats['total_time'] += step_time
        self._stats['avg_step_time'] = self._stats['total_time'] / self._stats['total_steps']
        self._stats['max_step_time'] = max(self._stats['max_step_time'], step_time)

        return results

    def _simulation_loop(self):
        """仿真主循环"""
        logger.info("Simulation loop started")

        target_step_time = self.config.simulation_step / self.config.realtime_factor

        while not self._stop_event.is_set():
            if self._state == ComponentState.PAUSED:
                time.sleep(0.1)
                continue

            loop_start = time.time()

            self.step()

            # 实时同步
            elapsed = time.time() - loop_start
            if elapsed < target_step_time:
                time.sleep(target_step_time - elapsed)

        logger.info("Simulation loop ended")

    def run_simulation(self, duration: float, callback: Callable = None) -> Dict[str, Any]:
        """
        运行仿真

        Args:
            duration: 仿真时长（秒）
            callback: 每步回调函数

        Returns:
            仿真结果汇总
        """
        if self._state == ComponentState.UNINITIALIZED:
            self.initialize()

        if self._state != ComponentState.READY:
            logger.error(f"Cannot run simulation from state: {self._state}")
            return {}

        self._state = ComponentState.RUNNING
        self.context.is_running = True

        n_steps = int(duration / self.config.simulation_step)
        all_results = []

        logger.info(f"Running simulation: {duration}s, {n_steps} steps")

        for step_idx in range(n_steps):
            if self._stop_event.is_set():
                break

            results = self.step()
            all_results.append(results)

            if callback:
                callback(step_idx, self.context.simulation_time, results)

        self._state = ComponentState.READY
        self.context.is_running = False

        return {
            'n_steps': len(all_results),
            'duration': self.context.simulation_time,
            'stats': self._stats.copy(),
            'final_state': self.get_system_state(),
        }

    def get_component(self, name: str) -> Optional[Any]:
        """获取组件"""
        return self._components.get(name)

    def get_system_state(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'system_state': self._state.value,
            'mode': self.config.mode.value,
            'simulation_time': self.context.simulation_time,
            'components': {
                name: self._component_states.get(name, ComponentState.UNINITIALIZED).value
                for name in self._components
            },
            'stats': self._stats.copy(),
        }

    def get_diagnostics(self) -> Dict[str, Any]:
        """获取诊断信息"""
        diag = {
            'system': self.get_system_state(),
            'components': {},
        }

        for name, component in self._components.items():
            if hasattr(component, 'get_diagnostics'):
                diag['components'][name] = component.get_diagnostics()
            elif hasattr(component, 'get_status'):
                diag['components'][name] = component.get_status()

        return diag

    def on(self, event_name: str, handler: Callable):
        """注册事件处理器"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    def _emit_event(self, event_name: str, data: Dict[str, Any]):
        """发送事件"""
        handlers = self._event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def _process_pending_events(self):
        """处理待处理事件"""
        while self.context.pending_events:
            event = self.context.pending_events.pop(0)
            self._emit_event(event.get('type', 'unknown'), event)

    def set_parameter(self, component_name: str, param_name: str, value: Any):
        """设置组件参数"""
        component = self._components.get(component_name)
        if component and hasattr(component, 'set_parameter'):
            component.set_parameter(param_name, value)
        elif component:
            setattr(component, param_name, value)

    def get_parameter(self, component_name: str, param_name: str) -> Any:
        """获取组件参数"""
        component = self._components.get(component_name)
        if component and hasattr(component, 'get_parameter'):
            return component.get_parameter(param_name)
        elif component:
            return getattr(component, param_name, None)
        return None

    @classmethod
    def create_standard_system(cls, n_stations: int = 3) -> 'YJDTSystem':
        """
        创建标准系统配置

        Args:
            n_stations: 电站数量

        Returns:
            配置好的系统实例
        """
        builder = SystemBuilder()
        builder.set_name(f"雅江{n_stations}级梯级电站控制系统")
        builder.set_mode(SystemMode.SIMULATION)
        builder.set_simulation_step(0.01)

        # 添加水力系统
        builder.add_hydraulic_system({
            'n_pipelines': n_stations,
            'total_length': 5000,
        })

        # 为每个电站添加机组
        for i in range(1, n_stations + 1):
            builder.add_turbine(str(i), "Francis", {
                'rated_power': 200,
                'rated_head': 100 + i * 50,
            })
            builder.add_generator(str(i), {
                'rated_power': 200,
                'rated_voltage': 15.75,
            })
            builder.add_governor(str(i), "PID", {
                'kp': 2.0,
                'ki': 0.5,
                'kd': 0.1,
            })

        # 添加控制系统
        builder.add_mpc_controller({
            'prediction_horizon': 20,
            'control_horizon': 10,
        })

        # 添加数字孪生
        builder.add_digital_twin()

        # 添加监控
        builder.add_monitoring()

        # 添加安全分析
        builder.add_safety_analysis()

        # 添加调度优化
        builder.add_scheduler()

        return builder.build()

    @classmethod
    def create_minimal_system(cls) -> 'YJDTSystem':
        """创建最小系统（用于测试）"""
        builder = SystemBuilder()
        builder.set_name("最小测试系统")
        builder.set_mode(SystemMode.SIMULATION)
        builder.add_hydraulic_system()
        return builder.build()

    def export_config(self, path: str):
        """导出配置到YAML"""
        import yaml

        config_dict = {
            'name': self.config.name,
            'mode': self.config.mode.value,
            'simulation_step': self.config.simulation_step,
            'realtime_factor': self.config.realtime_factor,
            'components': {}
        }

        for name, comp_config in self.config.components.items():
            config_dict['components'][name] = {
                'type': comp_config.component_type,
                'enabled': comp_config.enabled,
                'config': comp_config.config,
                'dependencies': comp_config.dependencies,
                'priority': comp_config.priority,
            }

        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)

    def __enter__(self):
        """上下文管理器入口"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        if self.is_running:
            self.stop()
        return False

    def __repr__(self):
        return f"YJDTSystem(name='{self.config.name}', state={self._state.value}, components={len(self._components)})"
