# -*- coding: utf-8 -*-
"""
闭环测试框架 - Closed-loop Test Harness

功能：
- 闭环测试环境
- 场景注入
- 响应验证
- 性能评估
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import threading
import time


class TestMode(Enum):
    """测试模式"""
    SIL = "software_in_loop"        # 软件在环
    HIL = "hardware_in_loop"        # 硬件在环
    MIL = "model_in_loop"           # 模型在环


class InjectionType(Enum):
    """注入类型"""
    STEP = "step"                   # 阶跃
    RAMP = "ramp"                   # 斜坡
    SINE = "sine"                   # 正弦
    PULSE = "pulse"                 # 脉冲
    RANDOM = "random"               # 随机
    PROFILE = "profile"             # 曲线


@dataclass
class HarnessConfiguration:
    """测试台配置"""
    mode: TestMode = TestMode.SIL
    simulation_step: float = 0.01       # 仿真步长（秒）
    real_time_factor: float = 1.0       # 实时因子
    max_duration: float = 3600          # 最大测试时长（秒）
    logging_enabled: bool = True
    auto_save_results: bool = True


@dataclass
class InjectionProfile:
    """注入曲线"""
    variable: str
    injection_type: InjectionType
    start_time: float                   # 开始时间（秒）
    duration: float                     # 持续时间（秒）
    parameters: Dict[str, float]        # 类型参数


@dataclass
class ValidationCriteria:
    """验证准则"""
    variable: str
    criterion_type: str                 # "range", "settling", "overshoot", "response_time"
    parameters: Dict[str, float]
    weight: float = 1.0


@dataclass
class TestScenarioConfig:
    """测试场景配置"""
    scenario_id: str
    name: str
    description: str
    initial_state: Dict[str, float]
    injections: List[InjectionProfile]
    validations: List[ValidationCriteria]
    duration: float                     # 测试时长（秒）


class TestScenarioInjector:
    """
    场景注入器

    功能：
    - 信号注入
    - 故障模拟
    - 扰动生成
    """

    def __init__(self):
        self.profiles: List[InjectionProfile] = []
        self.current_time = 0.0

    def add_profile(self, profile: InjectionProfile):
        """添加注入曲线"""
        self.profiles.append(profile)

    def get_injection(self, time: float) -> Dict[str, float]:
        """
        获取指定时刻的注入值

        Args:
            time: 当前时间（秒）

        Returns:
            各变量的注入值
        """
        self.current_time = time
        injections = {}

        for profile in self.profiles:
            if profile.start_time <= time < profile.start_time + profile.duration:
                t_rel = time - profile.start_time  # 相对时间
                value = self._calculate_injection(profile, t_rel)
                injections[profile.variable] = value

        return injections

    def _calculate_injection(self, profile: InjectionProfile,
                             t_rel: float) -> float:
        """计算注入值"""
        params = profile.parameters

        if profile.injection_type == InjectionType.STEP:
            magnitude = params.get("magnitude", 0)
            return magnitude

        elif profile.injection_type == InjectionType.RAMP:
            rate = params.get("rate", 0)
            magnitude = params.get("magnitude", float('inf'))
            return min(rate * t_rel, magnitude)

        elif profile.injection_type == InjectionType.SINE:
            amplitude = params.get("amplitude", 0)
            frequency = params.get("frequency", 1)
            offset = params.get("offset", 0)
            return offset + amplitude * np.sin(2 * np.pi * frequency * t_rel)

        elif profile.injection_type == InjectionType.PULSE:
            magnitude = params.get("magnitude", 0)
            pulse_width = params.get("width", 1)
            return magnitude if t_rel < pulse_width else 0

        elif profile.injection_type == InjectionType.RANDOM:
            mean = params.get("mean", 0)
            std = params.get("std", 1)
            return np.random.normal(mean, std)

        elif profile.injection_type == InjectionType.PROFILE:
            # 从预定义曲线插值
            times = params.get("times", [0])
            values = params.get("values", [0])
            return np.interp(t_rel, times, values)

        return 0.0

    def reset(self):
        """重置注入器"""
        self.current_time = 0.0


class ResponseValidator:
    """
    响应验证器

    功能：
    - 验证系统响应
    - 计算性能指标
    - 判定通过/失败
    """

    def __init__(self):
        self.criteria: List[ValidationCriteria] = []
        self.data_buffer: Dict[str, List[tuple]] = {}  # 变量 -> [(时间, 值)]

    def add_criteria(self, criteria: ValidationCriteria):
        """添加验证准则"""
        self.criteria.append(criteria)

    def record_data(self, time: float, data: Dict[str, float]):
        """记录数据"""
        for var, value in data.items():
            if var not in self.data_buffer:
                self.data_buffer[var] = []
            self.data_buffer[var].append((time, value))

    def validate(self) -> Dict[str, Any]:
        """
        执行验证

        Returns:
            验证结果
        """
        results = {
            "passed": True,
            "details": {},
            "metrics": {},
        }

        total_weight = sum(c.weight for c in self.criteria)

        for criteria in self.criteria:
            result = self._validate_criteria(criteria)
            results["details"][criteria.variable] = result

            if not result["passed"]:
                results["passed"] = False

            # 加权分数
            if "score" in result:
                weight = criteria.weight / total_weight
                results["metrics"][f"{criteria.variable}_{criteria.criterion_type}"] = result["score"]

        # 计算总体分数
        if results["metrics"]:
            results["overall_score"] = np.mean(list(results["metrics"].values()))
        else:
            results["overall_score"] = 100 if results["passed"] else 0

        return results

    def _validate_criteria(self, criteria: ValidationCriteria) -> Dict[str, Any]:
        """验证单个准则"""
        var = criteria.variable
        params = criteria.parameters

        if var not in self.data_buffer:
            return {"passed": False, "error": "No data", "score": 0}

        data = self.data_buffer[var]
        times = [d[0] for d in data]
        values = [d[1] for d in data]

        if criteria.criterion_type == "range":
            # 范围验证
            min_val = params.get("min", float('-inf'))
            max_val = params.get("max", float('inf'))
            in_range = all(min_val <= v <= max_val for v in values)
            return {
                "passed": in_range,
                "min_actual": min(values),
                "max_actual": max(values),
                "score": 100 if in_range else 0,
            }

        elif criteria.criterion_type == "settling":
            # 稳定时间验证
            target = params.get("target", values[-1])
            tolerance = params.get("tolerance", 0.02)
            max_time = params.get("max_time", float('inf'))

            # 找稳定点
            settle_time = None
            for i, (t, v) in enumerate(zip(times, values)):
                if abs(v - target) / max(abs(target), 1e-6) <= tolerance:
                    settle_time = t
                    break

            if settle_time is not None and settle_time <= max_time:
                score = max(0, 100 - (settle_time / max_time) * 50)
                return {"passed": True, "settle_time": settle_time, "score": score}
            else:
                return {"passed": False, "settle_time": settle_time, "score": 0}

        elif criteria.criterion_type == "overshoot":
            # 超调验证
            target = params.get("target", values[-1])
            max_overshoot = params.get("max_percent", 10)

            if target != 0:
                peak = max(values) if target > values[0] else min(values)
                overshoot = abs(peak - target) / abs(target) * 100
            else:
                overshoot = 0

            passed = overshoot <= max_overshoot
            score = max(0, 100 - overshoot / max_overshoot * 100) if passed else 0
            return {"passed": passed, "overshoot_percent": overshoot, "score": score}

        elif criteria.criterion_type == "response_time":
            # 响应时间验证
            threshold = params.get("threshold_percent", 63.2)  # 时间常数
            target = params.get("target", values[-1])
            max_time = params.get("max_time", float('inf'))

            initial = values[0]
            threshold_value = initial + (target - initial) * threshold / 100

            response_time = None
            for t, v in zip(times, values):
                if (target > initial and v >= threshold_value) or \
                   (target < initial and v <= threshold_value):
                    response_time = t
                    break

            if response_time is not None and response_time <= max_time:
                score = max(0, 100 - (response_time / max_time) * 50)
                return {"passed": True, "response_time": response_time, "score": score}
            else:
                return {"passed": False, "response_time": response_time, "score": 0}

        return {"passed": False, "error": "Unknown criterion type", "score": 0}

    def reset(self):
        """重置验证器"""
        self.data_buffer.clear()


class ClosedLoopTestHarness:
    """
    闭环测试台

    功能：
    - 闭环测试环境
    - 场景执行
    - 结果收集
    - 性能评估
    """

    def __init__(self, config: HarnessConfiguration = None,
                 closed_loop_coordinator=None):
        self.config = config or HarnessConfiguration()
        self.coordinator = closed_loop_coordinator

        self.injector = TestScenarioInjector()
        self.validator = ResponseValidator()

        # 测试状态
        self.current_time = 0.0
        self.running = False
        self.results: Dict[str, Any] = {}

        # 数据记录
        self.time_series: List[float] = []
        self.state_history: List[Dict[str, float]] = []
        self.input_history: List[Dict[str, float]] = []

    def configure_scenario(self, scenario: TestScenarioConfig):
        """配置测试场景"""
        # 设置注入
        self.injector = TestScenarioInjector()
        for profile in scenario.injections:
            self.injector.add_profile(profile)

        # 设置验证
        self.validator = ResponseValidator()
        for criteria in scenario.validations:
            self.validator.add_criteria(criteria)

        self.scenario = scenario

    def run(self, scenario: TestScenarioConfig = None) -> Dict[str, Any]:
        """
        执行测试

        Args:
            scenario: 测试场景（可选，如已配置则使用已配置的）

        Returns:
            测试结果
        """
        if scenario:
            self.configure_scenario(scenario)

        if not hasattr(self, 'scenario'):
            raise ValueError("No scenario configured")

        # 初始化
        self.current_time = 0.0
        self.time_series = []
        self.state_history = []
        self.input_history = []
        self.running = True

        start_time = datetime.now()

        # 设置初始状态
        current_state = self.scenario.initial_state.copy()

        # 仿真循环
        dt = self.config.simulation_step
        duration = self.scenario.duration

        while self.current_time < duration and self.running:
            # 获取注入
            injections = self.injector.get_injection(self.current_time)

            # 合并输入
            inputs = current_state.copy()
            inputs.update(injections)

            # 执行仿真步
            if self.coordinator:
                result = self.coordinator.run_single_cycle(
                    external_inputs=injections
                )
                new_state = result.simulation_state
            else:
                # 简化仿真
                new_state = self._simple_simulation(current_state, injections, dt)

            # 记录数据
            self.time_series.append(self.current_time)
            self.state_history.append(new_state.copy())
            self.input_history.append(injections.copy())

            # 验证器记录
            self.validator.record_data(self.current_time, new_state)

            # 更新状态
            current_state = new_state
            self.current_time += dt

            # 实时因子控制
            if self.config.real_time_factor > 0:
                time.sleep(dt / self.config.real_time_factor)

        self.running = False
        end_time = datetime.now()

        # 执行验证
        validation_results = self.validator.validate()

        # 汇总结果
        self.results = {
            "scenario_id": self.scenario.scenario_id,
            "scenario_name": self.scenario.name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "simulation_time": self.current_time,
            "samples": len(self.time_series),
            "validation": validation_results,
            "passed": validation_results["passed"],
            "overall_score": validation_results["overall_score"],
        }

        return self.results

    def _simple_simulation(self, state: Dict[str, float],
                           inputs: Dict[str, float],
                           dt: float) -> Dict[str, float]:
        """简化仿真（用于SIL测试）"""
        new_state = state.copy()

        # 简单一阶响应
        for var, target in inputs.items():
            if var in state:
                current = state[var]
                tau = 1.0  # 时间常数
                new_state[var] = current + (target - current) * (1 - np.exp(-dt / tau))
            else:
                new_state[var] = target

        return new_state

    def stop(self):
        """停止测试"""
        self.running = False

    def get_time_series(self, variable: str) -> tuple:
        """获取时间序列数据"""
        times = self.time_series
        values = [s.get(variable, 0) for s in self.state_history]
        return times, values

    def export_results(self, filepath: str):
        """导出结果"""
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "results": self.results,
                "time_series": self.time_series,
                "state_history": self.state_history,
                "input_history": self.input_history,
            }, f, ensure_ascii=False, indent=2, default=str)


class BatchTestRunner:
    """
    批量测试运行器

    功能：
    - 批量执行测试
    - 并行处理
    - 结果汇总
    """

    def __init__(self, harness: ClosedLoopTestHarness):
        self.harness = harness
        self.scenarios: List[TestScenarioConfig] = []
        self.results: List[Dict[str, Any]] = []

    def add_scenario(self, scenario: TestScenarioConfig):
        """添加场景"""
        self.scenarios.append(scenario)

    def run_all(self, parallel: bool = False) -> Dict[str, Any]:
        """
        运行所有场景

        Args:
            parallel: 是否并行执行

        Returns:
            汇总结果
        """
        self.results = []
        start_time = datetime.now()

        for scenario in self.scenarios:
            result = self.harness.run(scenario)
            self.results.append(result)

        end_time = datetime.now()

        # 汇总
        passed = sum(1 for r in self.results if r["passed"])
        failed = len(self.results) - passed
        avg_score = np.mean([r["overall_score"] for r in self.results])

        return {
            "total_scenarios": len(self.scenarios),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(self.scenarios) * 100 if self.scenarios else 0,
            "average_score": avg_score,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_duration": (end_time - start_time).total_seconds(),
            "results": self.results,
        }

