# -*- coding: utf-8 -*-
"""
闭环协调器 - 本体仿真-数据同化-诊断-预测-调度-控制闭环
Closed-Loop Coordinator - Physical Simulation-Data Assimilation-Diagnosis-Prediction-Scheduling-Control Loop

功能：
- 闭环流程协调
- 多模块信息融合
- 自适应调整
- 性能监控
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import threading
import time

from .physical_simulation import PhysicalSimulator, MultiPhysicsModel
from .data_assimilation import DataAssimilator, ObservationOperator
from .evaluation_diagnosis import StateEvaluator, FaultDiagnosisEngine
from .prediction_engine import PredictionEngine
from .optimal_scheduling import OptimalScheduler, SchedulingHorizon, OptimizationObjective
from .control_executor import ControlExecutor, ControlMode, CommandPriority


class LoopState(Enum):
    """闭环状态"""
    IDLE = "idle"                   # 空闲
    SIMULATING = "simulating"       # 仿真中
    ASSIMILATING = "assimilating"   # 同化中
    DIAGNOSING = "diagnosing"       # 诊断中
    PREDICTING = "predicting"       # 预测中
    SCHEDULING = "scheduling"       # 调度中
    CONTROLLING = "controlling"     # 控制中
    ERROR = "error"                 # 错误


@dataclass
class LoopCycleResult:
    """闭环周期结果"""
    cycle_id: int
    start_time: datetime
    end_time: datetime
    duration_ms: float

    # 各阶段结果
    simulation_state: Dict[str, float]
    assimilation_state: Dict[str, float]
    diagnosis_result: Dict[str, Any]
    prediction_result: Dict[str, Any]
    schedule_result: Dict[str, Any]
    control_commands: List[Dict[str, Any]]

    # 性能指标
    metrics: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class LoopConfiguration:
    """闭环配置"""
    cycle_period: float = 1.0           # 闭环周期（秒）
    simulation_dt: float = 0.01         # 仿真步长（秒）
    assimilation_interval: int = 10     # 同化间隔（周期数）
    diagnosis_interval: int = 60        # 诊断间隔（周期数）
    prediction_interval: int = 30       # 预测间隔（周期数）
    scheduling_interval: int = 300      # 调度间隔（周期数）

    enable_simulation: bool = True
    enable_assimilation: bool = True
    enable_diagnosis: bool = True
    enable_prediction: bool = True
    enable_scheduling: bool = True
    enable_control: bool = True


class ClosedLoopCoordinator:
    """
    闭环协调器

    实现本体仿真→数据同化→评价诊断→预测→调度→控制的完整闭环

    架构：
    ┌─────────────────────────────────────────────────────┐
    │                  ClosedLoopCoordinator               │
    │  ┌─────────┐   ┌─────────┐   ┌─────────┐            │
    │  │Physical │──▶│  Data   │──▶│Evaluate │            │
    │  │Simulator│   │Assimilat│   │Diagnose │            │
    │  └─────────┘   └─────────┘   └────┬────┘            │
    │       ▲                           │                  │
    │       │                           ▼                  │
    │  ┌─────────┐   ┌─────────┐   ┌─────────┐            │
    │  │Control  │◀──│Optimal  │◀──│Predict  │            │
    │  │Executor │   │Scheduler│   │ Engine  │            │
    │  └─────────┘   └─────────┘   └─────────┘            │
    └─────────────────────────────────────────────────────┘
    """

    def __init__(self, config: LoopConfiguration = None):
        self.config = config or LoopConfiguration()

        # 初始化各模块
        self.simulator = PhysicalSimulator()
        self.assimilator = DataAssimilator()
        self.evaluator = StateEvaluator()
        self.diagnoser = FaultDiagnosisEngine()
        self.predictor = PredictionEngine()
        self.scheduler = OptimalScheduler()
        self.executor = ControlExecutor()

        # 状态管理
        self.state = LoopState.IDLE
        self.cycle_count = 0
        self.cycle_history: List[LoopCycleResult] = []

        # 当前状态
        self.current_state: Dict[str, float] = {}
        self.estimated_state: Dict[str, float] = {}
        self.observations: Dict[str, float] = {}

        # 运行控制
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 性能监控
        self.performance_metrics = {
            "avg_cycle_time": 0.0,
            "max_cycle_time": 0.0,
            "cycle_overruns": 0,
            "total_cycles": 0,
        }

    def initialize(self, initial_state: Dict[str, float] = None):
        """
        初始化闭环系统

        Args:
            initial_state: 初始状态
        """
        if initial_state:
            self.current_state = initial_state.copy()
            self.estimated_state = initial_state.copy()

        # 初始化仿真器
        self.simulator.initialize()

        # 初始化同化器
        state_dim = len(self.current_state)
        self.assimilator.initialize_ensemble(
            state_dim=max(state_dim, 10),
            ensemble_size=50
        )

        self.state = LoopState.IDLE

    def run_single_cycle(self, external_inputs: Dict[str, float] = None,
                         observations: Dict[str, float] = None) -> LoopCycleResult:
        """
        执行单个闭环周期

        Args:
            external_inputs: 外部输入
            observations: 观测数据

        Returns:
            周期执行结果
        """
        cycle_start = datetime.now()
        self.cycle_count += 1
        errors = []

        # 保存观测
        if observations:
            self.observations = observations

        # 1. 本体仿真
        simulation_state = {}
        if self.config.enable_simulation:
            try:
                self.state = LoopState.SIMULATING
                simulation_state = self._run_simulation(external_inputs)
            except Exception as e:
                errors.append(f"Simulation error: {str(e)}")

        # 2. 数据同化
        assimilation_state = {}
        if self.config.enable_assimilation and self.cycle_count % self.config.assimilation_interval == 0:
            try:
                self.state = LoopState.ASSIMILATING
                assimilation_state = self._run_assimilation(simulation_state, observations)
            except Exception as e:
                errors.append(f"Assimilation error: {str(e)}")
        else:
            assimilation_state = simulation_state

        # 更新当前状态估计
        self.estimated_state = assimilation_state or simulation_state or self.current_state

        # 3. 评价诊断
        diagnosis_result = {}
        if self.config.enable_diagnosis and self.cycle_count % self.config.diagnosis_interval == 0:
            try:
                self.state = LoopState.DIAGNOSING
                diagnosis_result = self._run_diagnosis(self.estimated_state)
            except Exception as e:
                errors.append(f"Diagnosis error: {str(e)}")

        # 4. 预测
        prediction_result = {}
        if self.config.enable_prediction and self.cycle_count % self.config.prediction_interval == 0:
            try:
                self.state = LoopState.PREDICTING
                prediction_result = self._run_prediction(self.estimated_state)
            except Exception as e:
                errors.append(f"Prediction error: {str(e)}")

        # 5. 调度
        schedule_result = {}
        if self.config.enable_scheduling and self.cycle_count % self.config.scheduling_interval == 0:
            try:
                self.state = LoopState.SCHEDULING
                schedule_result = self._run_scheduling(prediction_result)
            except Exception as e:
                errors.append(f"Scheduling error: {str(e)}")

        # 6. 控制
        control_commands = []
        if self.config.enable_control:
            try:
                self.state = LoopState.CONTROLLING
                control_commands = self._run_control(schedule_result, self.estimated_state)
            except Exception as e:
                errors.append(f"Control error: {str(e)}")

        cycle_end = datetime.now()
        duration = (cycle_end - cycle_start).total_seconds() * 1000

        # 更新性能指标
        self._update_performance_metrics(duration)

        # 创建周期结果
        result = LoopCycleResult(
            cycle_id=self.cycle_count,
            start_time=cycle_start,
            end_time=cycle_end,
            duration_ms=duration,
            simulation_state=simulation_state,
            assimilation_state=assimilation_state,
            diagnosis_result=diagnosis_result,
            prediction_result=prediction_result,
            schedule_result=schedule_result,
            control_commands=control_commands,
            errors=errors,
        )

        # 保存历史
        self.cycle_history.append(result)
        if len(self.cycle_history) > 1000:
            self.cycle_history = self.cycle_history[-1000:]

        self.state = LoopState.IDLE
        return result

    def _run_simulation(self, external_inputs: Dict[str, float]) -> Dict[str, float]:
        """执行仿真"""
        inputs = external_inputs or {}

        # 多步仿真
        steps_per_cycle = int(self.config.cycle_period / self.config.simulation_dt)

        for _ in range(steps_per_cycle):
            self.simulator.step(self.config.simulation_dt, inputs)

        return self.simulator.get_state()

    def _run_assimilation(self, model_state: Dict[str, float],
                          observations: Dict[str, float]) -> Dict[str, float]:
        """执行数据同化"""
        if not observations:
            return model_state

        # 创建观测算子
        obs_operator = ObservationOperator()
        for var in observations:
            obs_operator.add_observation(var, observations[var], 0.1)

        # 执行同化
        obs_vector = np.array(list(observations.values()))
        result = self.assimilator.assimilate(obs_vector, obs_operator)

        # 转换为字典
        assimilated_state = {}
        state_vars = list(model_state.keys()) if model_state else list(observations.keys())
        for i, var in enumerate(state_vars):
            if i < len(result.posterior_mean):
                assimilated_state[var] = result.posterior_mean[i]
            elif var in model_state:
                assimilated_state[var] = model_state[var]

        return assimilated_state

    def _run_diagnosis(self, state: Dict[str, float]) -> Dict[str, Any]:
        """执行诊断"""
        # 状态评估
        evaluation = self.evaluator.evaluate_state(state)

        # 故障诊断
        faults = self.diagnoser.diagnose(state)

        # 健康评估
        health_index = self.evaluator.calculate_health_index(state)

        return {
            "evaluation": evaluation,
            "faults": faults,
            "health_index": health_index,
            "timestamp": datetime.now().isoformat(),
        }

    def _run_prediction(self, state: Dict[str, float]) -> Dict[str, Any]:
        """执行预测"""
        predictions = {}

        # 更新预测引擎
        self.predictor.update(state)

        # 短期预测
        for var in ["power", "head", "efficiency"]:
            if var in state:
                pred = self.predictor.predict_short_term(var, 60, 1.0)
                predictions[f"{var}_short"] = {
                    "values": pred.predicted_values.tolist()[:10],
                    "confidence": 0.95,
                }

        # 中期预测
        inflow_pred = self.predictor.predict_medium_term("inflow", 24)
        predictions["inflow_24h"] = {
            "values": inflow_pred.predicted_values.tolist(),
        }

        return predictions

    def _run_scheduling(self, predictions: Dict) -> Dict[str, Any]:
        """执行调度"""
        result = self.scheduler.optimize(
            horizon=SchedulingHorizon.INTRADAY,
            objective=OptimizationObjective.LOAD_FOLLOWING,
            start_time=datetime.now(),
            duration_hours=4,
        )

        if result.success and result.schedule:
            return {
                "schedule_id": result.schedule.schedule_id,
                "total_power": result.schedule.total_power[:10],
                "objective_value": result.objective_value,
            }

        return {"error": "Scheduling failed"}

    def _run_control(self, schedule: Dict, current_state: Dict) -> List[Dict]:
        """执行控制"""
        commands = []

        # 根据调度结果生成控制指令
        if "total_power" in schedule and schedule["total_power"]:
            target_power = schedule["total_power"][0]

            # 分配给各机组
            for unit_id in self.scheduler.units:
                cmd = self.executor.submit_command(
                    target=unit_id,
                    variable="power",
                    setpoint=target_power / len(self.scheduler.units),
                    priority=CommandPriority.NORMAL,
                    source="scheduler",
                    mode=ControlMode.AUTO,
                )
                commands.append({
                    "command_id": cmd.command_id,
                    "target": cmd.target,
                    "setpoint": cmd.setpoint,
                })

        # 处理指令队列
        self.executor.process_queue()

        return commands

    def _update_performance_metrics(self, duration_ms: float):
        """更新性能指标"""
        self.performance_metrics["total_cycles"] += 1

        # 更新平均周期时间
        n = self.performance_metrics["total_cycles"]
        old_avg = self.performance_metrics["avg_cycle_time"]
        self.performance_metrics["avg_cycle_time"] = old_avg + (duration_ms - old_avg) / n

        # 更新最大周期时间
        if duration_ms > self.performance_metrics["max_cycle_time"]:
            self.performance_metrics["max_cycle_time"] = duration_ms

        # 检查超时
        if duration_ms > self.config.cycle_period * 1000:
            self.performance_metrics["cycle_overruns"] += 1

    def start(self, external_input_provider: callable = None,
              observation_provider: callable = None):
        """
        启动闭环运行

        Args:
            external_input_provider: 外部输入提供函数
            observation_provider: 观测数据提供函数
        """
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(external_input_provider, observation_provider),
            daemon=True
        )
        self._thread.start()

    def _run_loop(self, external_input_provider, observation_provider):
        """闭环运行主循环"""
        while self._running:
            cycle_start = time.time()

            # 获取输入和观测
            inputs = external_input_provider() if external_input_provider else {}
            observations = observation_provider() if observation_provider else {}

            # 执行周期
            with self._lock:
                self.run_single_cycle(inputs, observations)

            # 等待下一周期
            elapsed = time.time() - cycle_start
            sleep_time = max(0, self.config.cycle_period - elapsed)
            time.sleep(sleep_time)

    def stop(self):
        """停止闭环运行"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def get_status(self) -> Dict[str, Any]:
        """获取闭环状态"""
        return {
            "state": self.state.value,
            "running": self._running,
            "cycle_count": self.cycle_count,
            "current_state": self.estimated_state,
            "performance": self.performance_metrics,
            "config": {
                "cycle_period": self.config.cycle_period,
                "simulation_dt": self.config.simulation_dt,
            },
        }

    def get_recent_results(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取最近的周期结果"""
        results = []
        for cycle in self.cycle_history[-n:]:
            results.append({
                "cycle_id": cycle.cycle_id,
                "duration_ms": cycle.duration_ms,
                "errors": cycle.errors,
                "simulation_state": cycle.simulation_state,
            })
        return results


class InLoopTester:
    """
    全场景在环测试器

    功能：
    - 场景注入
    - 闭环响应测试
    - 性能评估
    """

    def __init__(self, coordinator: ClosedLoopCoordinator):
        self.coordinator = coordinator
        self.test_results: List[Dict[str, Any]] = []

    def inject_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        注入测试场景

        Args:
            scenario: 场景定义

        Returns:
            测试结果
        """
        scenario_type = scenario.get("type", "normal")
        duration = scenario.get("duration", 60)
        disturbances = scenario.get("disturbances", {})

        # 记录初始状态
        initial_state = self.coordinator.estimated_state.copy()

        # 执行场景
        results = []
        for i in range(int(duration / self.coordinator.config.cycle_period)):
            # 注入扰动
            external_inputs = self._apply_disturbances(disturbances, i)

            # 执行周期
            cycle_result = self.coordinator.run_single_cycle(
                external_inputs=external_inputs
            )
            results.append(cycle_result)

        # 评估响应
        evaluation = self._evaluate_response(initial_state, results, scenario)

        test_result = {
            "scenario": scenario,
            "cycles": len(results),
            "evaluation": evaluation,
            "timestamp": datetime.now().isoformat(),
        }

        self.test_results.append(test_result)
        return test_result

    def _apply_disturbances(self, disturbances: Dict, step: int) -> Dict[str, float]:
        """应用扰动"""
        inputs = {}

        for var, disturbance in disturbances.items():
            dist_type = disturbance.get("type", "step")
            magnitude = disturbance.get("magnitude", 0)
            start_step = disturbance.get("start", 0)

            if step < start_step:
                continue

            if dist_type == "step":
                inputs[var] = magnitude
            elif dist_type == "ramp":
                rate = disturbance.get("rate", 1)
                inputs[var] = magnitude * min((step - start_step) * rate, 1.0)
            elif dist_type == "sine":
                frequency = disturbance.get("frequency", 1)
                inputs[var] = magnitude * np.sin(2 * np.pi * frequency * step)
            elif dist_type == "impulse":
                if step == start_step:
                    inputs[var] = magnitude
                else:
                    inputs[var] = 0

        return inputs

    def _evaluate_response(self, initial_state: Dict, results: List,
                           scenario: Dict) -> Dict[str, Any]:
        """评估响应性能"""
        # 提取状态轨迹
        trajectories = {}
        for var in initial_state:
            values = [r.simulation_state.get(var, 0) for r in results]
            trajectories[var] = values

        # 计算性能指标
        metrics = {}

        # 超调量
        for var, values in trajectories.items():
            initial = initial_state.get(var, 0)
            if initial != 0:
                overshoot = (max(values) - initial) / abs(initial) * 100
                metrics[f"{var}_overshoot"] = overshoot

        # 调节时间
        for var, values in trajectories.items():
            threshold = 0.02  # 2%误差带
            final_value = values[-1] if values else 0
            settle_idx = len(values)
            for i, v in enumerate(values):
                if abs(v - final_value) / max(abs(final_value), 1e-6) < threshold:
                    settle_idx = i
                    break
            metrics[f"{var}_settle_time"] = settle_idx * self.coordinator.config.cycle_period

        # 错误统计
        total_errors = sum(len(r.errors) for r in results)
        metrics["total_errors"] = total_errors

        # 周期时间统计
        cycle_times = [r.duration_ms for r in results]
        metrics["avg_cycle_time"] = np.mean(cycle_times)
        metrics["max_cycle_time"] = np.max(cycle_times)

        return metrics

    def run_test_suite(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        运行测试套件

        Args:
            scenarios: 场景列表

        Returns:
            测试套件结果
        """
        suite_results = []

        for i, scenario in enumerate(scenarios):
            print(f"Running scenario {i+1}/{len(scenarios)}: {scenario.get('name', 'unnamed')}")

            # 重置协调器
            self.coordinator.initialize()

            # 执行测试
            result = self.inject_scenario(scenario)
            suite_results.append(result)

        # 汇总结果
        passed = sum(1 for r in suite_results if r["evaluation"].get("total_errors", 0) == 0)

        return {
            "total_scenarios": len(scenarios),
            "passed": passed,
            "failed": len(scenarios) - passed,
            "pass_rate": passed / len(scenarios) * 100 if scenarios else 0,
            "results": suite_results,
        }

