# -*- coding: utf-8 -*-
"""
MBD模块单元测试
"""

import pytest
import numpy as np


class TestHydraulicOptimizer:
    """水力系统优化器测试"""

    def test_optimizer_creation(self):
        """测试优化器创建"""
        from yjdt.mbd import HydraulicSystemOptimizer

        optimizer = HydraulicSystemOptimizer()
        assert optimizer is not None

    def test_tunnel_optimization(self):
        """测试隧洞优化"""
        from yjdt.mbd import HydraulicSystemOptimizer

        optimizer = HydraulicSystemOptimizer()
        result = optimizer.optimize_tunnel_section(
            design_flow=2000,
            tunnel_length=76000
        )

        assert 'optimal_diameter' in result
        assert result['optimal_diameter'] > 0
        assert 'economic_velocity' in result
        assert 2.0 <= result['economic_velocity'] <= 5.0  # 合理流速范围

    def test_surge_tank_optimization(self):
        """测试调压室优化"""
        from yjdt.mbd import HydraulicSystemOptimizer

        optimizer = HydraulicSystemOptimizer()
        result = optimizer.optimize_surge_tank(
            design_flow=2000,
            tunnel_length=76000,
            tunnel_area=120,
            static_head=2000
        )

        assert 'optimal_area' in result
        assert result['optimal_area'] > 0
        assert 'thoma_ratio' in result
        assert result['thoma_ratio'] > 1.0  # 需要满足Thoma稳定条件


class TestControlSystemOptimizer:
    """控制系统优化器测试"""

    def test_governor_pid_optimization(self):
        """测试调速器PID优化"""
        from yjdt.mbd import ControlSystemOptimizer

        optimizer = ControlSystemOptimizer()
        result = optimizer.optimize_governor_pid(
            Tw=12.0,
            Tm=8.0,
            sigma=0.04
        )

        assert 'kp' in result
        assert 'ki' in result
        assert 'kd' in result
        # PID参数应为正值
        assert result['kp'] > 0
        assert result['ki'] >= 0
        assert result['kd'] >= 0


class TestFlexibilityOptimizer:
    """灵活性优化器测试"""

    def test_flexibility_score(self):
        """测试灵活性评分"""
        from yjdt.mbd import FlexibilityOptimizer

        optimizer = FlexibilityOptimizer()
        score = optimizer.calculate_flexibility_score({
            "response_time": 8,
            "ramp_rate": 3,
            "operating_range": [0.4, 1.0]
        })

        assert 0 <= score <= 100

    def test_flexibility_score_boundaries(self):
        """测试灵活性评分边界"""
        from yjdt.mbd import FlexibilityOptimizer

        optimizer = FlexibilityOptimizer()

        # 极佳参数
        high_score = optimizer.calculate_flexibility_score({
            "response_time": 5,
            "ramp_rate": 5,
            "operating_range": [0.3, 1.0]
        })

        # 较差参数
        low_score = optimizer.calculate_flexibility_score({
            "response_time": 30,
            "ramp_rate": 1,
            "operating_range": [0.7, 1.0]
        })

        assert high_score > low_score


class TestSafetyOptimizer:
    """安全性优化器测试"""

    def test_safety_score(self):
        """测试安全性评分"""
        from yjdt.mbd import SafetyOptimizer

        optimizer = SafetyOptimizer()
        score = optimizer.calculate_safety_score({
            "pressure_margin": 25,
            "stability_margin": 15,
            "protection_reliability": 0.999
        })

        assert 0 <= score <= 100

    def test_safety_score_high_reliability(self):
        """测试高可靠性安全评分"""
        from yjdt.mbd import SafetyOptimizer

        optimizer = SafetyOptimizer()
        score = optimizer.calculate_safety_score({
            "pressure_margin": 40,
            "stability_margin": 30,
            "protection_reliability": 0.9999
        })

        assert score >= 80  # 高可靠性应该得高分


class TestAlgorithmSelector:
    """算法选择器测试"""

    def test_algorithm_selection(self):
        """测试算法选择"""
        from yjdt.mbd import AlgorithmSelector, OptimizationProblem, ProblemType

        selector = AlgorithmSelector()

        # 单目标问题
        problem = OptimizationProblem(
            name="test",
            problem_type=ProblemType.SINGLE_OBJECTIVE,
            n_variables=5,
            n_objectives=1,
            n_constraints=2
        )

        config = selector.select(problem)
        assert config is not None
        assert config.algorithm is not None


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
