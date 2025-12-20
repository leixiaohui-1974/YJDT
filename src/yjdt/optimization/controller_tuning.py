"""
控制器调参优化模块
Controller Tuning Optimization Module

实现控制器参数的自动优化：
- PID参数整定
- MPC参数优化
- 性能指标评估
- 鲁棒性分析
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from scipy.optimize import minimize, differential_evolution
from scipy.signal import lti, step, impulse


class TuningMethod(Enum):
    """调参方法"""
    ZIEGLER_NICHOLS = "zn"           # Ziegler-Nichols
    COHEN_COON = "cc"                 # Cohen-Coon
    IMC = "imc"                       # 内模控制
    RELAY_FEEDBACK = "relay"          # 继电反馈
    OPTIMIZATION = "optimization"     # 数值优化
    GENETIC_ALGORITHM = "ga"          # 遗传算法
    PARTICLE_SWARM = "pso"            # 粒子群算法
    BAYESIAN = "bayesian"             # 贝叶斯优化


class PerformanceIndex(Enum):
    """性能指标"""
    IAE = "iae"      # 积分绝对误差
    ISE = "ise"      # 积分平方误差
    ITAE = "itae"    # 积分时间绝对误差
    ITSE = "itse"    # 积分时间平方误差
    OVERSHOOT = "overshoot"     # 超调量
    SETTLING_TIME = "settling"   # 调节时间
    RISE_TIME = "rise"          # 上升时间
    COMPOSITE = "composite"      # 综合指标


@dataclass
class TuningResult:
    """调参结果"""
    method: TuningMethod
    kp: float
    ki: float
    kd: float
    performance: Dict[str, float]
    stability_margin: Dict[str, float]
    robustness: float
    iterations: int = 0
    convergence: List[float] = field(default_factory=list)


@dataclass
class SystemModel:
    """系统模型"""
    # 传递函数参数
    num: List[float] = field(default_factory=lambda: [1.0])
    den: List[float] = field(default_factory=lambda: [1.0, 1.0])

    # 时域参数
    time_constant: float = 1.0
    dead_time: float = 0.0
    gain: float = 1.0

    # 水轮机调节系统特有参数
    water_inertia_time: float = 12.0  # Tw
    mechanical_time_constant: float = 10.0  # Ta
    servo_time: float = 0.5  # Ty


class PerformanceEvaluator:
    """性能评估器"""

    def __init__(self, simulation_time: float = 100.0, dt: float = 0.01):
        self.simulation_time = simulation_time
        self.dt = dt
        self.time = np.arange(0, simulation_time, dt)

    def evaluate(
        self,
        response: np.ndarray,
        setpoint: float = 1.0
    ) -> Dict[str, float]:
        """
        评估阶跃响应性能

        Args:
            response: 响应曲线
            setpoint: 设定值

        Returns:
            性能指标字典
        """
        error = setpoint - response

        # 积分指标
        iae = np.sum(np.abs(error)) * self.dt
        ise = np.sum(error ** 2) * self.dt
        itae = np.sum(self.time * np.abs(error)) * self.dt
        itse = np.sum(self.time * error ** 2) * self.dt

        # 超调量
        if setpoint > 0:
            overshoot = (np.max(response) - setpoint) / setpoint * 100
        else:
            overshoot = 0.0
        overshoot = max(0, overshoot)

        # 调节时间（2%误差带）
        tolerance = 0.02 * setpoint
        settling_idx = np.where(np.abs(error) > tolerance)[0]
        if len(settling_idx) > 0:
            settling_time = self.time[settling_idx[-1]]
        else:
            settling_time = 0.0

        # 上升时间（10%-90%）
        threshold_10 = 0.1 * setpoint
        threshold_90 = 0.9 * setpoint
        rise_start = np.where(response >= threshold_10)[0]
        rise_end = np.where(response >= threshold_90)[0]
        if len(rise_start) > 0 and len(rise_end) > 0:
            rise_time = self.time[rise_end[0]] - self.time[rise_start[0]]
        else:
            rise_time = self.simulation_time

        # 稳态误差
        steady_state = np.mean(response[-100:]) if len(response) > 100 else response[-1]
        steady_error = abs(setpoint - steady_state)

        return {
            'iae': iae,
            'ise': ise,
            'itae': itae,
            'itse': itse,
            'overshoot': overshoot,
            'settling_time': settling_time,
            'rise_time': rise_time,
            'steady_error': steady_error,
        }

    def calculate_composite_index(
        self,
        metrics: Dict[str, float],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """计算综合性能指标"""
        if weights is None:
            weights = {
                'iae': 0.15,
                'ise': 0.10,
                'itae': 0.15,
                'overshoot': 0.25,
                'settling_time': 0.25,
                'steady_error': 0.10,
            }

        # 归一化各指标
        normalized = {
            'iae': min(metrics['iae'] / 10, 1),
            'ise': min(metrics['ise'] / 10, 1),
            'itae': min(metrics['itae'] / 100, 1),
            'overshoot': min(metrics['overshoot'] / 50, 1),
            'settling_time': min(metrics['settling_time'] / 50, 1),
            'steady_error': min(metrics['steady_error'] / 0.1, 1),
        }

        composite = sum(
            normalized.get(k, 0) * w
            for k, w in weights.items()
        )

        return 1 - composite  # 转换为越大越好


class HydropowerSystemSimulator:
    """
    水电调节系统仿真器

    实现水轮机调节系统的时域仿真
    """

    def __init__(self, model: SystemModel):
        self.model = model
        self.dt = 0.01

    def simulate_step_response(
        self,
        kp: float,
        ki: float,
        kd: float,
        simulation_time: float = 100.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        仿真阶跃响应

        使用简化的水轮机调节系统模型

        Returns:
            (时间数组, 响应数组)
        """
        Tw = self.model.water_inertia_time
        Ta = self.model.mechanical_time_constant
        Ty = self.model.servo_time
        dt = self.dt

        time = np.arange(0, simulation_time, dt)
        n_steps = len(time)

        # 状态变量
        x = 0.0       # 转速偏差
        y = 0.0       # 导叶开度
        q = 0.0       # 流量偏差
        h = 0.0       # 水头偏差

        # PID状态
        integral = 0.0
        prev_error = 0.0

        response = np.zeros(n_steps)
        setpoint = 1.0  # 阶跃输入

        for i, t in enumerate(time):
            # 误差
            error = setpoint - x

            # PID控制
            integral += error * dt
            integral = np.clip(integral, -1, 1)  # 抗饱和

            derivative = (error - prev_error) / dt if dt > 0 else 0
            prev_error = error

            u = kp * error + ki * integral + kd * derivative

            # 伺服机构动态
            dy = (u - y) / Ty
            y += dy * dt
            y = np.clip(y, 0, 1)

            # 水锤效应（简化模型）
            # dq/dt = (y - q - Tw*dh/dt) / (0.5*Tw)
            dh = (y - q) / (0.5 * Tw)
            dq = (y - q - Tw * dh) / (0.5 * Tw)
            q += dq * dt
            h += dh * dt

            # 转子运动方程
            # Ta * dx/dt = Pm - Pe
            # 简化：Pm ≈ (h + q), Pe = 负荷
            Pm = h + q
            Pe = 0.0  # 甩负荷后为0
            dx = (Pm - Pe - 0.05 * x) / Ta  # 加入阻尼
            x += dx * dt

            response[i] = x

        return time, response


class ControllerOptimizer:
    """
    控制器优化器

    实现多种PID参数整定方法
    """

    def __init__(self, model: SystemModel):
        self.model = model
        self.simulator = HydropowerSystemSimulator(model)
        self.evaluator = PerformanceEvaluator()

        # 参数范围
        self.param_bounds = {
            'kp': (0.5, 10.0),
            'ki': (0.01, 1.0),
            'kd': (0.0, 10.0),
        }

        # 调参历史
        self.tuning_history: List[TuningResult] = []

    def tune_ziegler_nichols(self) -> TuningResult:
        """
        Ziegler-Nichols整定法

        基于临界振荡法
        """
        # 寻找临界增益和临界周期
        Ku, Pu = self._find_critical_point()

        # ZN公式（经典PID）
        kp = 0.6 * Ku
        ki = 2 * kp / Pu
        kd = kp * Pu / 8

        # 对于水轮机系统，需要调整
        # 由于水锤效应，减小增益
        kp *= 0.8
        ki *= 0.5
        kd *= 1.2

        result = self._evaluate_parameters(kp, ki, kd, TuningMethod.ZIEGLER_NICHOLS)
        self.tuning_history.append(result)

        return result

    def _find_critical_point(self) -> Tuple[float, float]:
        """寻找临界增益和临界周期"""
        # 使用继电反馈法模拟
        # 简化处理：基于系统特性估算
        Tw = self.model.water_inertia_time
        Ta = self.model.mechanical_time_constant

        # 经验公式
        Ku = 2 * Ta / Tw
        Pu = 2 * np.pi * np.sqrt(Tw * Ta / 2)

        return Ku, Pu

    def tune_imc(self, lambda_factor: float = 0.5) -> TuningResult:
        """
        内模控制(IMC)整定法

        Args:
            lambda_factor: 滤波因子（越大越保守）
        """
        Tw = self.model.water_inertia_time
        Ta = self.model.mechanical_time_constant
        K = self.model.gain

        # IMC调参公式
        tau_c = lambda_factor * max(Tw, Ta)

        kp = Ta / (K * tau_c)
        ki = kp / Ta
        kd = 0.5 * kp * Tw  # 补偿水锤

        result = self._evaluate_parameters(kp, ki, kd, TuningMethod.IMC)
        self.tuning_history.append(result)

        return result

    def tune_optimization(
        self,
        index: PerformanceIndex = PerformanceIndex.ITAE,
        method: str = 'differential_evolution'
    ) -> TuningResult:
        """
        数值优化整定法

        Args:
            index: 优化目标（性能指标）
            method: 优化方法

        Returns:
            调参结果
        """
        bounds = [
            self.param_bounds['kp'],
            self.param_bounds['ki'],
            self.param_bounds['kd'],
        ]

        convergence = []

        def objective(params):
            kp, ki, kd = params
            time, response = self.simulator.simulate_step_response(kp, ki, kd)
            metrics = self.evaluator.evaluate(response)

            if index == PerformanceIndex.IAE:
                cost = metrics['iae']
            elif index == PerformanceIndex.ISE:
                cost = metrics['ise']
            elif index == PerformanceIndex.ITAE:
                cost = metrics['itae']
            elif index == PerformanceIndex.ITSE:
                cost = metrics['itse']
            elif index == PerformanceIndex.OVERSHOOT:
                cost = metrics['overshoot']
            elif index == PerformanceIndex.SETTLING_TIME:
                cost = metrics['settling_time']
            elif index == PerformanceIndex.COMPOSITE:
                cost = -self.evaluator.calculate_composite_index(metrics)
            else:
                cost = metrics['itae']

            convergence.append(cost)
            return cost

        if method == 'differential_evolution':
            result = differential_evolution(
                objective,
                bounds,
                maxiter=100,
                seed=42,
                polish=True
            )
        else:
            x0 = [2.5, 0.15, 4.0]
            result = minimize(objective, x0, bounds=bounds, method='L-BFGS-B')

        kp, ki, kd = result.x

        tuning_result = self._evaluate_parameters(
            kp, ki, kd, TuningMethod.OPTIMIZATION
        )
        tuning_result.iterations = len(convergence)
        tuning_result.convergence = convergence

        self.tuning_history.append(tuning_result)

        return tuning_result

    def tune_for_robustness(self) -> TuningResult:
        """
        鲁棒性优化

        考虑参数不确定性的调参
        """
        bounds = [
            self.param_bounds['kp'],
            self.param_bounds['ki'],
            self.param_bounds['kd'],
        ]

        def robust_objective(params):
            kp, ki, kd = params

            # 在多个工况下评估
            costs = []

            # 标称工况
            time, response = self.simulator.simulate_step_response(kp, ki, kd)
            metrics = self.evaluator.evaluate(response)
            costs.append(metrics['itae'])

            # 高水头工况（Tw增加20%）
            original_Tw = self.model.water_inertia_time
            self.model.water_inertia_time *= 1.2
            self.simulator = HydropowerSystemSimulator(self.model)
            time, response = self.simulator.simulate_step_response(kp, ki, kd)
            metrics = self.evaluator.evaluate(response)
            costs.append(metrics['itae'])

            # 低水头工况（Tw减少20%）
            self.model.water_inertia_time = original_Tw * 0.8
            self.simulator = HydropowerSystemSimulator(self.model)
            time, response = self.simulator.simulate_step_response(kp, ki, kd)
            metrics = self.evaluator.evaluate(response)
            costs.append(metrics['itae'])

            # 恢复
            self.model.water_inertia_time = original_Tw
            self.simulator = HydropowerSystemSimulator(self.model)

            # 最坏情况
            return max(costs)

        result = differential_evolution(
            robust_objective,
            bounds,
            maxiter=50,
            seed=42
        )

        kp, ki, kd = result.x

        tuning_result = self._evaluate_parameters(kp, ki, kd, TuningMethod.OPTIMIZATION)
        tuning_result.robustness = 1 - result.fun / 100  # 归一化

        self.tuning_history.append(tuning_result)

        return tuning_result

    def _evaluate_parameters(
        self,
        kp: float,
        ki: float,
        kd: float,
        method: TuningMethod
    ) -> TuningResult:
        """评估参数性能"""
        time, response = self.simulator.simulate_step_response(kp, ki, kd)
        metrics = self.evaluator.evaluate(response)

        # 稳定裕度（简化计算）
        stability = self._calculate_stability_margin(kp, ki, kd)

        # 鲁棒性评估
        robustness = self._evaluate_robustness(kp, ki, kd)

        return TuningResult(
            method=method,
            kp=kp,
            ki=ki,
            kd=kd,
            performance=metrics,
            stability_margin=stability,
            robustness=robustness,
        )

    def _calculate_stability_margin(
        self,
        kp: float,
        ki: float,
        kd: float
    ) -> Dict[str, float]:
        """计算稳定裕度"""
        # 简化计算
        Tw = self.model.water_inertia_time
        Ta = self.model.mechanical_time_constant

        # 估算增益裕度
        Ku, _ = self._find_critical_point()
        gain_margin = Ku / (kp + 1e-6)
        gain_margin_db = 20 * np.log10(gain_margin + 1e-6)

        # 估算相位裕度
        phase_margin = 45 * (1 - kp * Tw / (2 * Ta))
        phase_margin = max(0, min(90, phase_margin))

        return {
            'gain_margin': gain_margin,
            'gain_margin_db': gain_margin_db,
            'phase_margin': phase_margin,
        }

    def _evaluate_robustness(
        self,
        kp: float,
        ki: float,
        kd: float
    ) -> float:
        """评估鲁棒性"""
        # 在参数扰动下测试
        perturbations = [0.8, 0.9, 1.0, 1.1, 1.2]
        max_overshoot = 0

        original_Tw = self.model.water_inertia_time

        for factor in perturbations:
            self.model.water_inertia_time = original_Tw * factor
            self.simulator = HydropowerSystemSimulator(self.model)
            time, response = self.simulator.simulate_step_response(kp, ki, kd)
            metrics = self.evaluator.evaluate(response)
            max_overshoot = max(max_overshoot, metrics['overshoot'])

        # 恢复
        self.model.water_inertia_time = original_Tw
        self.simulator = HydropowerSystemSimulator(self.model)

        # 鲁棒性得分（越小越好）
        robustness = 1 - min(max_overshoot / 100, 1)

        return robustness

    def compare_methods(self) -> Dict[str, TuningResult]:
        """比较不同整定方法"""
        results = {}

        # ZN法
        results['zn'] = self.tune_ziegler_nichols()

        # IMC法
        results['imc'] = self.tune_imc()

        # 优化法
        results['optimization'] = self.tune_optimization()

        # 鲁棒优化
        results['robust'] = self.tune_for_robustness()

        return results

    def generate_tuning_report(self, result: TuningResult) -> str:
        """生成调参报告"""
        report = f"""
控制器调参报告
==============

整定方法: {result.method.value}

1. PID参数
   Kp = {result.kp:.4f}
   Ki = {result.ki:.4f}
   Kd = {result.kd:.4f}

2. 性能指标
   积分绝对误差(IAE): {result.performance['iae']:.4f}
   积分平方误差(ISE): {result.performance['ise']:.4f}
   积分时间绝对误差(ITAE): {result.performance['itae']:.4f}
   超调量: {result.performance['overshoot']:.2f}%
   调节时间: {result.performance['settling_time']:.2f}s
   上升时间: {result.performance['rise_time']:.2f}s
   稳态误差: {result.performance['steady_error']:.4f}

3. 稳定裕度
   增益裕度: {result.stability_margin['gain_margin']:.2f} ({result.stability_margin['gain_margin_db']:.1f}dB)
   相位裕度: {result.stability_margin['phase_margin']:.1f}°

4. 鲁棒性评估
   鲁棒性得分: {result.robustness:.2f}

"""
        return report
