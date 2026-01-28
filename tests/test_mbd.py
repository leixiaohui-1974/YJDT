# -*- coding: utf-8 -*-
"""
MBD模块单元测试
"""

import pytest
import numpy as np


# 默认工程参数
DEFAULT_PROJECT_PARAMS = {
    "tunnel_length": 76000,
    "design_flow": 2000,
    "static_head": 2000,
    "num_stations": 5,
    "tunnel_diameter": 12.0,
}

DEFAULT_SYSTEM_PARAMS = {
    "Tw": 12.0,  # 水流惯性时间常数
    "Tm": 8.0,   # 机械惯性时间常数
    "sigma": 0.04,
    "rated_power": 1000,
    "rated_speed": 166.7,
}


class TestHydraulicOptimizer:
    """水力系统优化器测试"""

    def test_optimizer_creation(self):
        """测试优化器创建"""
        from yjdt.mbd import HydraulicSystemOptimizer

        optimizer = HydraulicSystemOptimizer(DEFAULT_PROJECT_PARAMS)
        assert optimizer is not None

    def test_tunnel_optimization(self):
        """测试隧洞优化"""
        from yjdt.mbd import HydraulicSystemOptimizer

        optimizer = HydraulicSystemOptimizer(DEFAULT_PROJECT_PARAMS)
        result = optimizer.optimize_tunnel_section(
            design_flow=2000,
            tunnel_length=76000
        )

        assert 'optimal_diameter' in result
        assert result['optimal_diameter'] > 0
        # API返回的是flow_velocity而不是economic_velocity
        assert 'flow_velocity' in result or 'economic_velocity' in result

    def test_surge_tank_optimization(self):
        """测试调压室优化"""
        from yjdt.mbd import HydraulicSystemOptimizer

        optimizer = HydraulicSystemOptimizer(DEFAULT_PROJECT_PARAMS)
        result = optimizer.optimize_surge_tank(
            design_flow=2000,
            tunnel_length=76000,
            tunnel_area=120,
            static_head=2000
        )

        assert 'optimal_area' in result
        assert result['optimal_area'] > 0


class TestControlSystemOptimizer:
    """控制系统优化器测试"""

    def test_governor_pid_optimization(self):
        """测试调速器PID优化"""
        from yjdt.mbd import ControlSystemOptimizer

        optimizer = ControlSystemOptimizer(DEFAULT_SYSTEM_PARAMS)
        result = optimizer.optimize_governor_pid(
            Tw=12.0,
            Tm=8.0,
            sigma=0.04
        )

        # API返回的key使用大写Kp/Ki/Kd
        assert 'Kp' in result or 'kp' in result
        assert 'Ki' in result or 'ki' in result
        assert 'Kd' in result or 'kd' in result
        # PID参数应为正值
        kp = result.get('Kp', result.get('kp', 0))
        assert kp > 0


class TestFlexibilityOptimizer:
    """灵活性优化器测试"""

    def test_flexibility_score(self):
        """测试灵活性评分"""
        from yjdt.mbd import FlexibilityOptimizer

        optimizer = FlexibilityOptimizer()
        # 使用实际API的参数名
        scores = optimizer.calculate_flexibility_score({
            "settling_time": 20,
            "min_load": 0.4,
            "ramping_rate": 5,
            "startup_time": 300
        })

        assert isinstance(scores, dict)
        assert "total" in scores
        assert 0 <= scores["total"] <= 100

    def test_flexibility_score_boundaries(self):
        """测试灵活性评分边界"""
        from yjdt.mbd import FlexibilityOptimizer

        optimizer = FlexibilityOptimizer()

        # 极佳参数
        high_scores = optimizer.calculate_flexibility_score({
            "settling_time": 10,
            "min_load": 0.3,
            "ramping_rate": 8,
            "startup_time": 180
        })

        # 较差参数
        low_scores = optimizer.calculate_flexibility_score({
            "settling_time": 40,
            "min_load": 0.7,
            "ramping_rate": 2,
            "startup_time": 900
        })

        assert high_scores["total"] > low_scores["total"]


class TestSafetyOptimizer:
    """安全性优化器测试"""

    def test_safety_score(self):
        """测试安全性评分"""
        from yjdt.mbd import SafetyOptimizer

        optimizer = SafetyOptimizer()
        # 使用实际API的参数名
        scores = optimizer.calculate_safety_score({
            "pressure_margin": 0.25,
            "speed_margin": 0.3,
            "phase_margin": 35,
            "protection_reliability": 0.999
        })

        assert isinstance(scores, dict)
        assert "total" in scores
        assert 0 <= scores["total"] <= 100

    def test_safety_score_high_reliability(self):
        """测试高可靠性安全评分"""
        from yjdt.mbd import SafetyOptimizer

        optimizer = SafetyOptimizer()
        scores = optimizer.calculate_safety_score({
            "pressure_margin": 0.35,
            "speed_margin": 0.4,
            "phase_margin": 45,
            "protection_reliability": 0.9999
        })

        assert scores["total"] >= 80  # 高可靠性应该得高分


class TestVerificationIntegrator:
    """验证集成器测试"""

    def test_integrator_creation(self):
        """测试集成器创建"""
        from yjdt.mbd import create_yajiang_verification_integrator

        integrator = create_yajiang_verification_integrator()
        assert integrator is not None

    def test_design_verification(self):
        """测试设计验证"""
        from yjdt.mbd import (
            create_yajiang_verification_integrator,
            VerificationLevel,
            VerificationStatus
        )

        integrator = create_yajiang_verification_integrator()

        design_params = {
            "tunnel_diameter": 12.0,
            "surge_tank_area": 800,
            "governor_kp": 2.5
        }

        report = integrator.verify_design(
            design_id="test_design",
            design_params=design_params,
            verification_level=VerificationLevel.QUICK
        )

        assert report is not None
        assert report.design_id == "test_design"
        assert report.overall_status in VerificationStatus
        assert report.scenarios_run > 0

    def test_verification_scenarios(self):
        """测试验证场景库"""
        from yjdt.mbd import create_yajiang_verification_integrator

        integrator = create_yajiang_verification_integrator()

        # 检查场景库
        scenarios = integrator.scenario_library.scenarios
        assert len(scenarios) > 0

        # 检查雅江特定场景
        assert "YJ001" in scenarios or "YJ002" in scenarios

    def test_verification_criteria(self):
        """测试验证准则"""
        from yjdt.mbd import create_yajiang_verification_integrator

        integrator = create_yajiang_verification_integrator()

        # 检查准则管理器
        criteria = integrator.criteria_manager.criteria
        assert len(criteria) > 0


class TestYajiangMBDOptimizer:
    """雅江MBD综合优化器测试"""

    def test_optimizer_creation(self):
        """测试优化器创建"""
        from yjdt.mbd import create_yajiang_mbd_optimizer

        optimizer = create_yajiang_mbd_optimizer()
        assert optimizer is not None

    def test_full_optimization(self):
        """测试完整优化"""
        from yjdt.mbd import create_yajiang_mbd_optimizer

        optimizer = create_yajiang_mbd_optimizer()
        results = optimizer.run_full_optimization()

        assert results is not None
        assert 'hydraulic' in results or len(results) > 0


class TestDesignParameterMapper:
    """设计参数映射器测试"""

    def test_mapper_creation(self):
        """测试映射器创建"""
        from yjdt.mbd import DesignParameterMapper

        mapper = DesignParameterMapper()
        assert mapper is not None
        assert len(mapper.mappings) > 0

    def test_parameter_mapping(self):
        """测试参数映射"""
        from yjdt.mbd import DesignParameterMapper

        mapper = DesignParameterMapper()

        design_params = {
            "tunnel_diameter": 12.0,
            "surge_tank_area": 800,
            "governor_kp": 2.5
        }

        sim_params = mapper.map_design_to_simulation(design_params)
        assert sim_params is not None
        # 检查映射后有对应的仿真参数
        assert len(sim_params) >= len(design_params)


class TestSimulationScenarioLibrary:
    """仿真场景库测试"""

    def test_library_creation(self):
        """测试场景库创建"""
        from yjdt.mbd import SimulationScenarioLibrary

        library = SimulationScenarioLibrary()
        assert library is not None
        assert len(library.scenarios) > 0

    def test_get_scenarios_by_type(self):
        """测试按类型获取场景"""
        from yjdt.mbd import SimulationScenarioLibrary

        library = SimulationScenarioLibrary()

        extreme_scenarios = library.get_scenarios_by_type("extreme")
        assert isinstance(extreme_scenarios, list)

    def test_get_scenarios_by_priority(self):
        """测试按优先级获取场景"""
        from yjdt.mbd import SimulationScenarioLibrary

        library = SimulationScenarioLibrary()

        high_priority = library.get_scenarios_by_priority(1)
        assert isinstance(high_priority, list)
        assert len(high_priority) > 0


class TestSimulationExecutor:
    """仿真执行器测试"""

    def test_executor_creation(self):
        """测试执行器创建"""
        from yjdt.mbd import SimulationExecutor

        executor = SimulationExecutor()
        assert executor is not None

    def test_execute_scenario(self):
        """测试场景执行"""
        from yjdt.mbd import SimulationExecutor, SimulationScenarioLibrary

        executor = SimulationExecutor()
        library = SimulationScenarioLibrary()

        # 获取一个场景执行
        scenario = list(library.scenarios.values())[0]
        design_params = {
            "tunnel_diameter": 12.0,
            "surge_tank_area": 800
        }

        result = executor.execute_scenario(scenario, design_params)

        assert result is not None
        assert result.scenario_id == scenario.scenario_id
        assert result.execution_time >= 0
        assert "time" in result.time_series
