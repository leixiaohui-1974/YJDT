# -*- coding: utf-8 -*-
"""
硬件在环测试框架 - Hardware-in-Loop Test Framework

功能：
- 控制器硬件接入
- 实时仿真运行
- 功率级接口测试
- 信号注入与采集
- 控制器时序验证

基于YX工程HIL测试需求，支持：
- 10ms确定性时序
- 多控制器并行测试
- 故障注入与响应验证
- 完整控制回路闭合
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
import threading
import time
import struct


class HILMode(Enum):
    """HIL测试模式"""
    CONTROLLER_HIL = "controller_hil"      # 控制器在环（真实控制器+虚拟对象）
    PLANT_HIL = "plant_hil"                # 对象在环（虚拟控制器+真实对象）
    FULL_HIL = "full_hil"                  # 全系统在环
    RAPID_PROTOTYPING = "rapid_proto"      # 快速原型


class SignalType(Enum):
    """信号类型"""
    ANALOG_IN = "analog_in"
    ANALOG_OUT = "analog_out"
    DIGITAL_IN = "digital_in"
    DIGITAL_OUT = "digital_out"
    PWM = "pwm"
    ENCODER = "encoder"
    CAN = "can"
    MODBUS = "modbus"


class TestStatus(Enum):
    """测试状态"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class SignalChannel:
    """信号通道"""
    channel_id: str
    name: str
    signal_type: SignalType
    unit: str = ""

    # 量程
    min_value: float = -float('inf')
    max_value: float = float('inf')

    # 校准
    gain: float = 1.0
    offset: float = 0.0

    # 滤波
    filter_type: str = "none"  # "none", "lowpass", "average"
    filter_param: float = 0.0

    # 当前值
    current_value: float = 0.0
    timestamp: Optional[datetime] = None


@dataclass
class HILConfiguration:
    """HIL配置"""
    mode: HILMode = HILMode.CONTROLLER_HIL
    sample_rate: float = 1000.0          # 采样率 Hz
    control_rate: float = 100.0          # 控制率 Hz
    simulation_step: float = 0.001       # 仿真步长 秒

    # 实时性
    deterministic_mode: bool = True
    max_latency_ms: float = 10.0         # 最大延迟 ms
    jitter_tolerance_ms: float = 1.0     # 抖动容忍 ms

    # 接口
    controller_interface: str = "ethernet"  # ethernet, serial, can
    plant_interface: str = "simulation"

    # 数据记录
    logging_enabled: bool = True
    log_buffer_size: int = 100000


@dataclass
class HILTestCase:
    """HIL测试用例"""
    test_id: str
    name: str
    description: str

    # 测试配置
    duration: float                       # 测试时长（秒）
    initial_conditions: Dict[str, float] = field(default_factory=dict)

    # 输入序列
    input_profiles: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)

    # 故障注入
    fault_injections: List[Dict[str, Any]] = field(default_factory=list)

    # 验证准则
    pass_criteria: List[Dict[str, Any]] = field(default_factory=list)

    # 安全限制
    safety_limits: Dict[str, Tuple[float, float]] = field(default_factory=dict)


@dataclass
class HILTestResult:
    """HIL测试结果"""
    test_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: TestStatus

    # 时序性能
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    jitter_ms: float = 0.0
    missed_cycles: int = 0

    # 测试结果
    passed: bool = False
    pass_rate: float = 0.0

    # 详细数据
    time_series: List[float] = field(default_factory=list)
    signals: Dict[str, List[float]] = field(default_factory=list)

    # 异常记录
    violations: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ControllerInterface:
    """
    控制器接口

    功能：
    - 连接真实控制器硬件
    - 信号读写
    - 协议转换
    - 时序同步
    """

    def __init__(self, interface_type: str = "ethernet"):
        self.interface_type = interface_type
        self.connected = False

        # 通道配置
        self.input_channels: Dict[str, SignalChannel] = {}
        self.output_channels: Dict[str, SignalChannel] = {}

        # 通信状态
        self.tx_count = 0
        self.rx_count = 0
        self.error_count = 0
        self.last_comm_time: Optional[datetime] = None

        # 模拟模式（无真实硬件时）
        self.simulation_mode = True
        self._simulated_controller: Optional[Callable] = None

    def add_input_channel(self, channel: SignalChannel):
        """添加输入通道（控制器->仿真）"""
        self.input_channels[channel.channel_id] = channel

    def add_output_channel(self, channel: SignalChannel):
        """添加输出通道（仿真->控制器）"""
        self.output_channels[channel.channel_id] = channel

    def connect(self, address: str = "localhost", port: int = 5000) -> bool:
        """
        连接控制器

        Args:
            address: 控制器地址
            port: 端口

        Returns:
            是否连接成功
        """
        try:
            if self.interface_type == "ethernet":
                # 模拟以太网连接
                self.connected = True
                self.last_comm_time = datetime.now()
                return True
            elif self.interface_type == "serial":
                # 模拟串口连接
                self.connected = True
                return True
            elif self.interface_type == "can":
                # 模拟CAN连接
                self.connected = True
                return True
            else:
                return False
        except Exception as e:
            self.error_count += 1
            return False

    def disconnect(self):
        """断开连接"""
        self.connected = False

    def read_inputs(self) -> Dict[str, float]:
        """
        读取控制器输出（作为仿真输入）

        Returns:
            通道值字典
        """
        if not self.connected:
            return {}

        values = {}

        if self.simulation_mode and self._simulated_controller:
            # 使用模拟控制器
            outputs = self.output_channels
            ctrl_outputs = self._simulated_controller({
                ch.channel_id: ch.current_value
                for ch in outputs.values()
            })

            for ch_id, channel in self.input_channels.items():
                if ch_id in ctrl_outputs:
                    raw = ctrl_outputs[ch_id]
                    channel.current_value = raw * channel.gain + channel.offset
                    channel.timestamp = datetime.now()
                    values[ch_id] = channel.current_value
        else:
            # 从真实硬件读取
            for ch_id, channel in self.input_channels.items():
                # 模拟读取
                channel.current_value = np.random.normal(0, 0.01)
                channel.timestamp = datetime.now()
                values[ch_id] = channel.current_value

        self.rx_count += 1
        self.last_comm_time = datetime.now()
        return values

    def write_outputs(self, values: Dict[str, float]) -> bool:
        """
        写入仿真输出（作为控制器输入）

        Args:
            values: 通道值字典

        Returns:
            是否写入成功
        """
        if not self.connected:
            return False

        try:
            for ch_id, value in values.items():
                if ch_id in self.output_channels:
                    channel = self.output_channels[ch_id]
                    # 应用限幅
                    clamped = np.clip(value, channel.min_value, channel.max_value)
                    # 应用校准逆变换
                    raw = (clamped - channel.offset) / channel.gain
                    channel.current_value = clamped
                    channel.timestamp = datetime.now()

            self.tx_count += 1
            self.last_comm_time = datetime.now()
            return True

        except Exception as e:
            self.error_count += 1
            return False

    def set_simulated_controller(self, controller_func: Callable):
        """设置模拟控制器函数"""
        self._simulated_controller = controller_func

    def get_statistics(self) -> Dict[str, Any]:
        """获取通信统计"""
        return {
            "connected": self.connected,
            "tx_count": self.tx_count,
            "rx_count": self.rx_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.tx_count + self.rx_count, 1),
            "last_comm": self.last_comm_time.isoformat() if self.last_comm_time else None,
        }


class PowerLevelInterface:
    """
    功率级接口

    功能：
    - 功率信号模拟
    - 电压/电流注入
    - 负载模拟
    - 功率测量

    用于测试：
    - 励磁系统
    - 变频器
    - 断路器
    """

    def __init__(self):
        # 功率通道
        self.voltage_channels: Dict[str, float] = {}
        self.current_channels: Dict[str, float] = {}

        # 负载模型
        self.loads: Dict[str, Dict[str, float]] = {}

        # 测量
        self.power_measurements: Dict[str, float] = {}

        # 安全限制
        self.voltage_limits = (0, 10000)  # V
        self.current_limits = (0, 5000)   # A

    def configure_voltage_source(self, channel: str,
                                  voltage: float,
                                  frequency: float = 50.0):
        """配置电压源"""
        self.voltage_channels[channel] = {
            "voltage": np.clip(voltage, *self.voltage_limits),
            "frequency": frequency,
            "phase": 0.0,
        }

    def configure_current_source(self, channel: str, current: float):
        """配置电流源"""
        self.current_channels[channel] = np.clip(current, *self.current_limits)

    def add_load(self, load_id: str, load_type: str, parameters: Dict[str, float]):
        """
        添加负载模型

        Args:
            load_id: 负载ID
            load_type: 类型 ("resistive", "inductive", "motor", "grid")
            parameters: 参数
        """
        self.loads[load_id] = {
            "type": load_type,
            "parameters": parameters,
            "power": 0.0,
        }

    def simulate_step(self, dt: float) -> Dict[str, float]:
        """
        仿真一步

        Args:
            dt: 时间步长

        Returns:
            功率测量结果
        """
        measurements = {}

        for load_id, load in self.loads.items():
            if load["type"] == "resistive":
                # 电阻负载
                r = load["parameters"].get("resistance", 1.0)
                for ch, v_data in self.voltage_channels.items():
                    v = v_data["voltage"] if isinstance(v_data, dict) else v_data
                    i = v / r
                    p = v * i
                    measurements[f"{load_id}_power"] = p
                    measurements[f"{load_id}_current"] = i

            elif load["type"] == "motor":
                # 电机负载
                pn = load["parameters"].get("rated_power", 1000)  # kW
                eta = load["parameters"].get("efficiency", 0.95)
                load_factor = load["parameters"].get("load_factor", 0.8)

                p_mech = pn * load_factor
                p_elec = p_mech / eta
                measurements[f"{load_id}_power"] = p_elec
                measurements[f"{load_id}_mechanical_power"] = p_mech

            elif load["type"] == "grid":
                # 电网模型
                grid_voltage = load["parameters"].get("voltage", 220000)
                grid_frequency = load["parameters"].get("frequency", 50.0)
                impedance = load["parameters"].get("impedance", 10.0)

                measurements[f"{load_id}_grid_voltage"] = grid_voltage
                measurements[f"{load_id}_grid_frequency"] = grid_frequency

        self.power_measurements = measurements
        return measurements

    def get_power_flow(self) -> Dict[str, float]:
        """获取功率潮流"""
        return self.power_measurements.copy()


class RealTimeSimulator:
    """
    实时仿真器

    功能：
    - 确定性执行
    - 多速率调度
    - 模型求解
    - 时序监控
    """

    def __init__(self, config: HILConfiguration):
        self.config = config

        # 仿真状态
        self.running = False
        self.current_time = 0.0
        self.cycle_count = 0

        # 模型
        self.plant_model: Optional[Callable] = None
        self.state: Dict[str, float] = {}

        # 时序统计
        self.latencies: List[float] = []
        self.missed_deadlines = 0

        # 多速率任务
        self.tasks: List[Dict[str, Any]] = []

        # 线程
        self._sim_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def set_plant_model(self, model: Callable, initial_state: Dict[str, float]):
        """
        设置对象模型

        Args:
            model: 模型函数 (state, inputs, dt) -> new_state
            initial_state: 初始状态
        """
        self.plant_model = model
        self.state = initial_state.copy()

    def add_task(self, name: str, rate: float, callback: Callable):
        """
        添加周期任务

        Args:
            name: 任务名
            rate: 执行频率 Hz
            callback: 回调函数
        """
        self.tasks.append({
            "name": name,
            "rate": rate,
            "period": 1.0 / rate,
            "last_execution": 0.0,
            "callback": callback,
        })

    def start(self):
        """启动实时仿真"""
        self.running = True
        self.current_time = 0.0
        self.cycle_count = 0
        self.latencies = []
        self.missed_deadlines = 0

        self._sim_thread = threading.Thread(target=self._realtime_loop, daemon=True)
        self._sim_thread.start()

    def stop(self):
        """停止仿真"""
        self.running = False
        if self._sim_thread:
            self._sim_thread.join(timeout=2.0)

    def _realtime_loop(self):
        """实时仿真循环"""
        dt = self.config.simulation_step
        target_period = dt / self.config.control_rate * self.config.sample_rate

        while self.running:
            cycle_start = time.perf_counter()

            # 执行仿真步
            with self._lock:
                if self.plant_model:
                    inputs = {}  # 从控制器接口获取
                    self.state = self.plant_model(self.state, inputs, dt)

                # 执行到期任务
                for task in self.tasks:
                    if self.current_time - task["last_execution"] >= task["period"]:
                        try:
                            task["callback"](self.current_time, self.state)
                            task["last_execution"] = self.current_time
                        except Exception as e:
                            pass

                self.current_time += dt
                self.cycle_count += 1

            # 计算延迟
            cycle_end = time.perf_counter()
            cycle_time = (cycle_end - cycle_start) * 1000  # ms
            self.latencies.append(cycle_time)

            # 检查是否超时
            if cycle_time > self.config.max_latency_ms:
                self.missed_deadlines += 1

            # 等待到下一周期
            sleep_time = target_period - (cycle_end - cycle_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def step(self, inputs: Dict[str, float]) -> Dict[str, float]:
        """
        单步执行（同步模式）

        Args:
            inputs: 输入

        Returns:
            新状态
        """
        dt = self.config.simulation_step

        with self._lock:
            if self.plant_model:
                self.state = self.plant_model(self.state, inputs, dt)
            else:
                # 简单响应模型
                for key, value in inputs.items():
                    if key in self.state:
                        tau = 1.0
                        self.state[key] += (value - self.state[key]) * (1 - np.exp(-dt/tau))

            self.current_time += dt
            self.cycle_count += 1

        return self.state.copy()

    def get_state(self) -> Dict[str, float]:
        """获取当前状态"""
        with self._lock:
            return self.state.copy()

    def get_timing_stats(self) -> Dict[str, float]:
        """获取时序统计"""
        if not self.latencies:
            return {}

        return {
            "avg_latency_ms": np.mean(self.latencies),
            "max_latency_ms": np.max(self.latencies),
            "min_latency_ms": np.min(self.latencies),
            "jitter_ms": np.std(self.latencies),
            "missed_deadlines": self.missed_deadlines,
            "deadline_miss_rate": self.missed_deadlines / max(len(self.latencies), 1),
            "total_cycles": self.cycle_count,
        }


class HILTestBench:
    """
    HIL测试台

    功能：
    - 完整HIL测试环境
    - 测试用例执行
    - 故障注入
    - 结果分析

    支持测试场景：
    - 控制器响应验证
    - 故障穿越测试
    - 极限工况测试
    - 时序确定性验证
    """

    def __init__(self, config: HILConfiguration = None):
        self.config = config or HILConfiguration()

        # 组件
        self.controller = ControllerInterface(self.config.controller_interface)
        self.power_interface = PowerLevelInterface()
        self.simulator = RealTimeSimulator(self.config)

        # 测试状态
        self.status = TestStatus.IDLE
        self.current_test: Optional[HILTestCase] = None
        self.test_results: List[HILTestResult] = []

        # 数据记录
        self.data_log: Dict[str, List[Any]] = {
            "time": [],
            "inputs": [],
            "outputs": [],
            "states": [],
        }

        # 故障注入状态
        self.active_faults: List[Dict[str, Any]] = []

        # 安全监控
        self.safety_triggered = False
        self.safety_violations: List[Dict[str, Any]] = []

    def configure(self, plant_model: Callable,
                  initial_state: Dict[str, float],
                  controller_func: Callable = None):
        """
        配置测试台

        Args:
            plant_model: 对象模型
            initial_state: 初始状态
            controller_func: 模拟控制器（可选）
        """
        self.simulator.set_plant_model(plant_model, initial_state)
        if controller_func:
            self.controller.set_simulated_controller(controller_func)

    def load_test_case(self, test_case: HILTestCase):
        """加载测试用例"""
        self.current_test = test_case
        self.status = TestStatus.IDLE

    def run_test(self, test_case: HILTestCase = None) -> HILTestResult:
        """
        运行测试

        Args:
            test_case: 测试用例（可选，使用已加载的）

        Returns:
            测试结果
        """
        if test_case:
            self.load_test_case(test_case)

        if not self.current_test:
            raise ValueError("No test case loaded")

        # 初始化
        self.status = TestStatus.INITIALIZING
        self._reset_data_log()
        self.active_faults = []
        self.safety_triggered = False
        self.safety_violations = []

        result = HILTestResult(
            test_id=self.current_test.test_id,
            start_time=datetime.now(),
            end_time=None,
            status=TestStatus.RUNNING,
        )

        # 连接控制器
        if not self.controller.connected:
            self.controller.connect()

        # 设置初始条件
        self.simulator.state = self.current_test.initial_conditions.copy()

        # 开始测试
        self.status = TestStatus.RUNNING
        start_time = time.perf_counter()

        try:
            # 主测试循环
            dt = self.config.simulation_step
            t = 0.0

            while t < self.current_test.duration and not self.safety_triggered:
                cycle_start = time.perf_counter()

                # 获取输入（从曲线插值）
                inputs = self._interpolate_inputs(t)

                # 检查故障注入
                self._check_fault_injection(t)

                # 应用故障效果
                inputs = self._apply_faults(inputs, t)

                # 写入控制器
                self.controller.write_outputs(inputs)

                # 读取控制器输出
                ctrl_outputs = self.controller.read_inputs()

                # 仿真步进
                state = self.simulator.step(ctrl_outputs)

                # 功率级仿真
                power = self.power_interface.simulate_step(dt)

                # 检查安全限制
                self._check_safety_limits(state, t)

                # 记录数据
                self._log_data(t, inputs, ctrl_outputs, state)

                # 计算延迟
                cycle_time = (time.perf_counter() - cycle_start) * 1000
                result.time_series.append(t)

                t += dt

            # 测试完成
            self.status = TestStatus.COMPLETED

        except Exception as e:
            self.status = TestStatus.FAILED
            result.errors.append(str(e))

        # 生成结果
        result.end_time = datetime.now()
        result.status = self.status

        # 时序统计
        timing = self.simulator.get_timing_stats()
        result.avg_latency_ms = timing.get("avg_latency_ms", 0)
        result.max_latency_ms = timing.get("max_latency_ms", 0)
        result.jitter_ms = timing.get("jitter_ms", 0)
        result.missed_cycles = timing.get("missed_deadlines", 0)

        # 验证通过准则
        result.passed, result.pass_rate = self._validate_criteria()
        result.violations = self.safety_violations

        # 保存信号数据
        for key in self.data_log:
            if key != "time":
                result.signals[key] = self.data_log[key]

        self.test_results.append(result)
        return result

    def _reset_data_log(self):
        """重置数据记录"""
        self.data_log = {
            "time": [],
            "inputs": [],
            "outputs": [],
            "states": [],
        }

    def _interpolate_inputs(self, t: float) -> Dict[str, float]:
        """插值获取输入"""
        inputs = {}

        for var, profile in self.current_test.input_profiles.items():
            if not profile:
                continue

            times = [p[0] for p in profile]
            values = [p[1] for p in profile]
            inputs[var] = np.interp(t, times, values)

        return inputs

    def _check_fault_injection(self, t: float):
        """检查故障注入"""
        for fault in self.current_test.fault_injections:
            start = fault.get("start_time", 0)
            duration = fault.get("duration", float('inf'))

            if start <= t < start + duration:
                if fault not in self.active_faults:
                    self.active_faults.append(fault)
            else:
                if fault in self.active_faults:
                    self.active_faults.remove(fault)

    def _apply_faults(self, inputs: Dict[str, float], t: float) -> Dict[str, float]:
        """应用故障效果"""
        modified = inputs.copy()

        for fault in self.active_faults:
            fault_type = fault.get("type", "")
            target = fault.get("target", "")

            if fault_type == "stuck":
                # 信号卡死
                if target in modified:
                    modified[target] = fault.get("value", 0)

            elif fault_type == "bias":
                # 偏差
                if target in modified:
                    modified[target] += fault.get("bias", 0)

            elif fault_type == "noise":
                # 噪声
                if target in modified:
                    std = fault.get("std", 0.1)
                    modified[target] += np.random.normal(0, std)

            elif fault_type == "delay":
                # 延迟（简化处理）
                pass

            elif fault_type == "loss":
                # 信号丢失
                if target in modified:
                    modified[target] = 0.0

        return modified

    def _check_safety_limits(self, state: Dict[str, float], t: float):
        """检查安全限制"""
        for var, (low, high) in self.current_test.safety_limits.items():
            if var in state:
                value = state[var]
                if value < low or value > high:
                    violation = {
                        "time": t,
                        "variable": var,
                        "value": value,
                        "limit": (low, high),
                    }
                    self.safety_violations.append(violation)

                    # 严重超限时触发安全停止
                    if value < low * 0.5 or value > high * 1.5:
                        self.safety_triggered = True

    def _log_data(self, t: float, inputs: Dict, outputs: Dict, states: Dict):
        """记录数据"""
        if not self.config.logging_enabled:
            return

        self.data_log["time"].append(t)
        self.data_log["inputs"].append(inputs.copy())
        self.data_log["outputs"].append(outputs.copy())
        self.data_log["states"].append(states.copy())

    def _validate_criteria(self) -> Tuple[bool, float]:
        """验证通过准则"""
        if not self.current_test or not self.current_test.pass_criteria:
            return len(self.safety_violations) == 0, 100.0

        passed_count = 0
        total = len(self.current_test.pass_criteria)

        for criteria in self.current_test.pass_criteria:
            criterion_type = criteria.get("type", "")
            variable = criteria.get("variable", "")

            # 从记录数据中提取
            values = []
            for state in self.data_log["states"]:
                if variable in state:
                    values.append(state[variable])

            if not values:
                continue

            if criterion_type == "range":
                min_val = criteria.get("min", float('-inf'))
                max_val = criteria.get("max", float('inf'))
                if all(min_val <= v <= max_val for v in values):
                    passed_count += 1

            elif criterion_type == "settling":
                target = criteria.get("target", values[-1])
                tolerance = criteria.get("tolerance", 0.02)
                settle_time = criteria.get("max_time", float('inf'))

                # 检查最终值是否在容差内
                if abs(values[-1] - target) <= abs(target) * tolerance:
                    passed_count += 1

            elif criterion_type == "overshoot":
                target = criteria.get("target", values[-1])
                max_overshoot = criteria.get("max_percent", 10)

                if target != 0:
                    peak = max(values) if target > values[0] else min(values)
                    overshoot = abs(peak - target) / abs(target) * 100
                    if overshoot <= max_overshoot:
                        passed_count += 1
                else:
                    passed_count += 1

            elif criterion_type == "timing":
                max_latency = criteria.get("max_latency_ms", 10)
                if self.simulator.get_timing_stats().get("max_latency_ms", 0) <= max_latency:
                    passed_count += 1

        pass_rate = passed_count / total * 100 if total > 0 else 100
        return passed_count == total and len(self.safety_violations) == 0, pass_rate

    def inject_fault(self, fault_type: str, target: str,
                     parameters: Dict[str, Any], duration: float = None):
        """
        运行时故障注入

        Args:
            fault_type: 故障类型
            target: 目标信号
            parameters: 参数
            duration: 持续时间
        """
        fault = {
            "type": fault_type,
            "target": target,
            "start_time": self.simulator.current_time,
            "duration": duration or float('inf'),
            **parameters,
        }
        self.active_faults.append(fault)

    def clear_faults(self):
        """清除所有故障"""
        self.active_faults.clear()

    def abort_test(self):
        """终止测试"""
        self.status = TestStatus.ABORTED
        self.safety_triggered = True

    def get_test_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        if not self.test_results:
            return {"message": "No tests executed"}

        passed = sum(1 for r in self.test_results if r.passed)
        failed = len(self.test_results) - passed

        return {
            "total_tests": len(self.test_results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(self.test_results) * 100,
            "avg_latency_ms": np.mean([r.avg_latency_ms for r in self.test_results]),
            "max_latency_ms": max(r.max_latency_ms for r in self.test_results),
            "total_violations": sum(len(r.violations) for r in self.test_results),
        }

    def export_results(self, filepath: str):
        """导出测试结果"""
        import json

        results = []
        for r in self.test_results:
            results.append({
                "test_id": r.test_id,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "status": r.status.value,
                "passed": r.passed,
                "pass_rate": r.pass_rate,
                "timing": {
                    "avg_latency_ms": r.avg_latency_ms,
                    "max_latency_ms": r.max_latency_ms,
                    "jitter_ms": r.jitter_ms,
                    "missed_cycles": r.missed_cycles,
                },
                "violations": r.violations,
                "errors": r.errors,
            })

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)


# 预定义水电站控制器模型
def create_hydropower_controller(kp: float = 1.0, ki: float = 0.1, kd: float = 0.05):
    """
    创建水电站PID控制器

    Args:
        kp, ki, kd: PID参数
    """
    state = {"integral": 0.0, "last_error": 0.0}

    def controller(inputs: Dict[str, float]) -> Dict[str, float]:
        # 获取测量值和设定值
        power_meas = inputs.get("power_measurement", 0)
        power_ref = inputs.get("power_setpoint", 0)

        # PID计算
        error = power_ref - power_meas
        state["integral"] += error * 0.01  # dt = 0.01
        derivative = (error - state["last_error"]) / 0.01
        state["last_error"] = error

        output = kp * error + ki * state["integral"] + kd * derivative

        # 限幅
        output = np.clip(output, -1.0, 1.0)

        return {
            "guide_vane_command": 0.5 + output * 0.3,  # 导叶开度
            "excitation_command": 1.0 + output * 0.1,   # 励磁电压
        }

    return controller


def create_governor_model(Tw: float = 2.0, Tm: float = 8.0):
    """
    创建调速器模型

    Args:
        Tw: 水锤时间常数
        Tm: 机械时间常数
    """
    def model(state: Dict[str, float], inputs: Dict[str, float],
              dt: float) -> Dict[str, float]:
        new_state = state.copy()

        # 导叶位置
        y = state.get("guide_vane", 0.5)
        y_cmd = inputs.get("guide_vane_command", 0.5)

        # 一阶响应
        tau_y = 0.5  # 导叶时间常数
        y_new = y + (y_cmd - y) * (1 - np.exp(-dt / tau_y))
        new_state["guide_vane"] = np.clip(y_new, 0, 1)

        # 水头响应（简化水锤）
        h = state.get("head", 1.0)
        q = state.get("flow", 0.5)

        # 流量与导叶关系
        q_new = y_new * np.sqrt(h)

        # 水锤效应
        dh = -Tw * (q_new - q) / dt if dt > 0 else 0
        h_new = h + dh * dt
        new_state["head"] = np.clip(h_new, 0.5, 1.5)
        new_state["flow"] = q_new

        # 机械功率
        pm = q_new * h_new
        new_state["mechanical_power"] = pm

        # 转速
        omega = state.get("speed", 1.0)
        pe = state.get("electrical_power", 0.5)
        domega = (pm - pe) / Tm
        new_state["speed"] = omega + domega * dt

        return new_state

    return model
