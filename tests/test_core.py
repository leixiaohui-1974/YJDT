# -*- coding: utf-8 -*-
"""
核心模块集成测试
Core Module Integration Tests
"""

import pytest
import numpy as np
from typing import Dict, Any


class TestHydraulicSystem:
    """水力系统测试 / Hydraulic System Tests"""

    def test_pipeline_creation(self):
        """测试管道创建"""
        from yjdt.core.hydraulic import Pipeline

        pipeline = Pipeline(
            length=25000.0,
            diameter=12.0,
            wave_speed=1200.0,
            friction_factor=0.012,
            n_sections=100
        )

        assert pipeline.length == 25000.0
        assert pipeline.diameter == 12.0
        assert pipeline.n_sections == 100
        assert len(pipeline.H) == 101
        assert len(pipeline.Q) == 101

    def test_water_hammer_simulation(self):
        """测试水锤仿真"""
        from yjdt.core.hydraulic import Pipeline

        pipeline = Pipeline(
            length=5000.0,
            diameter=8.0,
            wave_speed=1000.0,
            friction_factor=0.015,
            n_sections=50
        )

        # 初始化
        pipeline.initialize(head=480.0, flow=200.0)

        # 执行一步仿真
        dt = pipeline.length / (pipeline.n_sections * pipeline.wave_speed)
        H_new, Q_new = pipeline.step(dt)

        assert len(H_new) == 51
        assert len(Q_new) == 51
        # 水头应保持在合理范围内
        assert np.all(H_new > 0)
        assert np.all(H_new < 1000)

    def test_surge_tank(self):
        """测试调压室"""
        from yjdt.core.hydraulic import SurgeTank

        surge_tank = SurgeTank(
            area=500.0,
            max_level=50.0,
            min_level=-30.0,
            orifice_area=20.0,
            orifice_coefficient=0.7
        )

        surge_tank.initialize(level=0.0)

        # 模拟流量变化
        level, outflow = surge_tank.step(
            inflow=180.0,
            outflow_demand=200.0,
            dt=0.1
        )

        assert surge_tank.min_level <= level <= surge_tank.max_level
        assert outflow > 0


class TestTurbineModels:
    """水轮机模型测试 / Turbine Model Tests"""

    def test_francis_turbine(self):
        """测试混流式水轮机"""
        from yjdt.core.turbine import FrancisTurbine

        turbine = FrancisTurbine(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0,
            rated_flow=230.0,
            efficiency_peak=0.94
        )

        # 测试额定工况
        power, efficiency = turbine.calculate_output(
            head=480.0,
            guide_vane_opening=0.8,
            speed=100.0
        )

        assert power > 0
        assert 0 < efficiency <= 1.0

    def test_pelton_turbine(self):
        """测试冲击式水轮机"""
        from yjdt.core.turbine import PeltonTurbine

        turbine = PeltonTurbine(
            rated_power=500.0,
            rated_head=2100.0,
            rated_speed=300.0,
            n_jets=6,
            jet_diameter=0.3,
            efficiency_peak=0.92
        )

        power, efficiency = turbine.calculate_output(
            head=2100.0,
            needle_position=0.8,
            speed=300.0
        )

        assert power > 0
        assert 0 < efficiency <= 1.0

    def test_turbine_characteristics(self):
        """测试水轮机特性曲线"""
        from yjdt.core.turbine import FrancisTurbine

        turbine = FrancisTurbine(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0,
            rated_flow=230.0
        )

        # 测试不同开度下的效率变化
        efficiencies = []
        for opening in [0.3, 0.5, 0.7, 0.9, 1.0]:
            _, eff = turbine.calculate_output(480.0, opening, 100.0)
            efficiencies.append(eff)

        # 效率应随开度变化
        assert len(set(efficiencies)) > 1


class TestGenerator:
    """发电机测试 / Generator Tests"""

    def test_synchronous_generator(self):
        """测试同步发电机"""
        from yjdt.core.generator import SynchronousGenerator

        generator = SynchronousGenerator(
            rated_power=1000.0,
            rated_voltage=20.0,
            rated_frequency=50.0,
            poles=60,
            inertia_constant=4.0
        )

        generator.initialize(
            mechanical_power=800.0,
            voltage=20.0
        )

        # 仿真一步
        state = generator.step(
            mechanical_power=810.0,
            field_voltage=1.0,
            dt=0.01
        )

        assert 'speed' in state
        assert 'angle' in state
        assert 'voltage' in state
        assert 'current' in state
        assert 'power' in state

    def test_swing_equation(self):
        """测试摇摆方程"""
        from yjdt.core.generator import SynchronousGenerator

        generator = SynchronousGenerator(
            rated_power=1000.0,
            rated_voltage=20.0,
            rated_frequency=50.0,
            poles=60,
            inertia_constant=4.0
        )

        generator.initialize(mechanical_power=800.0, voltage=20.0)

        # 施加机械功率阶跃
        initial_speed = generator.speed
        for _ in range(100):
            generator.step(
                mechanical_power=850.0,  # 增加功率
                field_voltage=1.0,
                dt=0.01
            )

        # 速度应该增加
        assert generator.speed > initial_speed


class TestGovernor:
    """调速器测试 / Governor Tests"""

    def test_pid_governor(self):
        """测试PID调速器"""
        from yjdt.core.governor import PIDGovernor

        governor = PIDGovernor(
            kp=3.0,
            ki=0.5,
            kd=0.1,
            bt=0.04,
            bp=0.05
        )

        governor.initialize(initial_output=0.8)

        # 测试频率偏差响应
        output = governor.step(
            frequency=49.8,  # 频率下降
            reference_frequency=50.0,
            dt=0.02
        )

        # 输出应增加以恢复频率
        assert 0 <= output <= 1.0

    def test_mpc_governor(self):
        """测试MPC调速器"""
        from yjdt.core.governor import MPCGovernor

        governor = MPCGovernor(
            prediction_horizon=20,
            control_horizon=5,
            water_inertia_time=12.0,
            mechanical_time=0.2
        )

        governor.initialize(initial_output=0.75)

        # 创建预测参考轨迹
        reference_trajectory = np.ones(20) * 50.0

        output = governor.step(
            frequency=49.9,
            reference_frequency=50.0,
            power=800.0,
            reference_trajectory=reference_trajectory,
            dt=0.1
        )

        assert 0 <= output <= 1.0

    def test_adaptive_governor(self):
        """测试自适应调速器"""
        from yjdt.core.governor import AdaptiveGovernor

        governor = AdaptiveGovernor(
            initial_kp=2.5,
            initial_ki=0.4,
            adaptation_gain=0.01
        )

        governor.initialize(initial_output=0.8)

        # 仿真多步，测试参数自适应
        for _ in range(50):
            output = governor.step(
                frequency=49.95,
                reference_frequency=50.0,
                power=800.0,
                dt=0.02
            )

        assert 0 <= output <= 1.0


class TestIntegration:
    """集成测试 / Integration Tests"""

    def test_turbine_generator_coupling(self):
        """测试水轮机-发电机耦合"""
        from yjdt.core.turbine import FrancisTurbine
        from yjdt.core.generator import SynchronousGenerator

        turbine = FrancisTurbine(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0,
            rated_flow=230.0
        )

        generator = SynchronousGenerator(
            rated_power=1000.0,
            rated_voltage=20.0,
            rated_frequency=50.0,
            poles=60,
            inertia_constant=4.0
        )

        generator.initialize(mechanical_power=800.0, voltage=20.0)

        # 耦合仿真
        for _ in range(100):
            # 水轮机输出
            power, _ = turbine.calculate_output(
                head=480.0,
                guide_vane_opening=0.8,
                speed=generator.speed
            )

            # 发电机响应
            state = generator.step(
                mechanical_power=power,
                field_voltage=1.0,
                dt=0.01
            )

        assert state['speed'] > 0
        assert state['power'] > 0

    def test_governor_turbine_loop(self):
        """测试调速器-水轮机闭环"""
        from yjdt.core.turbine import FrancisTurbine
        from yjdt.core.governor import PIDGovernor

        turbine = FrancisTurbine(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0,
            rated_flow=230.0
        )

        governor = PIDGovernor(
            kp=3.0,
            ki=0.5,
            kd=0.1,
            bt=0.04,
            bp=0.05
        )

        governor.initialize(initial_output=0.8)

        frequency = 50.0

        # 闭环仿真
        for i in range(200):
            # 调速器计算
            opening = governor.step(
                frequency=frequency,
                reference_frequency=50.0,
                dt=0.02
            )

            # 水轮机响应
            power, _ = turbine.calculate_output(
                head=480.0,
                guide_vane_opening=opening,
                speed=100.0
            )

            # 简化的频率响应
            if i == 50:  # 在第50步施加负荷扰动
                frequency -= 0.2

            # 频率恢复
            frequency += (power - 750.0) / 1000.0 * 0.02

        # 频率应该恢复到接近50Hz
        assert abs(frequency - 50.0) < 0.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
