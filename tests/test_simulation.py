# -*- coding: utf-8 -*-
"""
仿真引擎和SIL测试模块测试
Simulation Engine and SIL Testing Module Tests
"""

import pytest
import numpy as np


class TestSimulationEngine:
    """仿真引擎测试"""

    def test_engine_creation(self):
        """测试仿真引擎创建"""
        from yjdt.simulation.engine import SimulationEngine

        engine = SimulationEngine(
            dt=0.01,
            t_end=10.0
        )

        assert engine.dt == 0.01
        assert engine.t_end == 10.0

    def test_unit_simulation(self):
        """测试单机仿真"""
        from yjdt.simulation.engine import HydropowerUnitSimulator

        simulator = HydropowerUnitSimulator(
            unit_id="UNIT001",
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        simulator.initialize(
            power=800.0,
            head=480.0,
            guide_vane_opening=0.8
        )

        # 仿真10步
        results = []
        for _ in range(10):
            state = simulator.step(dt=0.01)
            results.append(state)

        assert len(results) == 10
        assert all('power' in r for r in results)
        assert all('frequency' in r for r in results)

    def test_load_change_simulation(self):
        """测试负荷变化仿真"""
        from yjdt.simulation.engine import HydropowerUnitSimulator

        simulator = HydropowerUnitSimulator(
            unit_id="UNIT002",
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        simulator.initialize(power=800.0, head=480.0, guide_vane_opening=0.8)

        # 施加负荷阶跃
        simulator.set_power_setpoint(850.0)

        # 仿真响应
        power_history = []
        for i in range(500):
            state = simulator.step(dt=0.02)
            power_history.append(state['power'])

        # 功率应该从800变化到接近850
        assert power_history[-1] != power_history[0]

    def test_cascade_simulation(self):
        """测试梯级仿真"""
        from yjdt.simulation.engine import CascadeSimulator

        simulator = CascadeSimulator(
            n_stations=2,
            units_per_station=[2, 2]
        )

        simulator.initialize(
            station_powers=[1500.0, 1200.0],
            water_levels=[450.0, 420.0]
        )

        # 仿真
        for _ in range(100):
            state = simulator.step(dt=1.0)

        assert 'stations' in state
        assert len(state['stations']) == 2

    def test_water_hammer_simulation(self):
        """测试水锤仿真"""
        from yjdt.simulation.engine import SimulationEngine

        engine = SimulationEngine(
            dt=0.001,
            t_end=5.0
        )

        # 配置水锤仿真
        config = {
            'pipeline': {
                'length': 5000.0,
                'diameter': 8.0,
                'wave_speed': 1000.0
            },
            'initial_conditions': {
                'head': 480.0,
                'flow': 200.0
            },
            'events': [
                {'time': 1.0, 'type': 'valve_closure', 'duration': 2.0}
            ]
        }

        results = engine.run_water_hammer(config)

        assert 'time' in results
        assert 'head' in results
        assert 'flow' in results

        # 水锤应该导致压力波动
        head_max = max(results['head'])
        head_min = min(results['head'])
        assert head_max > 480.0
        assert head_min < 480.0


class TestSILTestFramework:
    """SIL测试框架测试"""

    def test_test_case_creation(self):
        """测试用例创建"""
        from yjdt.simulation.sil_testing import TestCase

        test_case = TestCase(
            name="TC001_LoadRejection",
            description="100%甩负荷测试",
            scenario={
                'type': 'load_rejection',
                'initial_power': 1000.0,
                'rejection_ratio': 1.0
            },
            acceptance_criteria={
                'max_overspeed': 1.45,
                'settling_time': 60.0
            }
        )

        assert test_case.name == "TC001_LoadRejection"
        assert test_case.scenario['type'] == 'load_rejection'

    def test_test_suite_creation(self):
        """测试套件创建"""
        from yjdt.simulation.sil_testing import TestCase, TestSuite

        test_cases = [
            TestCase(
                name="TC001",
                description="测试1",
                scenario={'type': 'test1'},
                acceptance_criteria={}
            ),
            TestCase(
                name="TC002",
                description="测试2",
                scenario={'type': 'test2'},
                acceptance_criteria={}
            )
        ]

        suite = TestSuite(
            name="基础测试套件",
            test_cases=test_cases
        )

        assert len(suite.test_cases) == 2

    def test_sil_test_execution(self):
        """测试SIL测试执行"""
        from yjdt.simulation.sil_testing import SILTestFramework, TestCase

        framework = SILTestFramework()

        test_case = TestCase(
            name="TC_SimpleTest",
            description="简单测试",
            scenario={
                'type': 'steady_state',
                'power': 800.0,
                'duration': 10.0
            },
            acceptance_criteria={
                'frequency_deviation_max': 0.1
            }
        )

        result = framework.run_test(test_case)

        assert 'passed' in result
        assert 'metrics' in result
        assert 'execution_time' in result

    def test_test_evaluation(self):
        """测试结果评估"""
        from yjdt.simulation.sil_testing import TestEvaluator

        evaluator = TestEvaluator()

        # 仿真结果
        simulation_results = {
            'max_overspeed': 1.35,
            'settling_time': 45.0,
            'max_pressure': 520.0,
            'frequency_deviation': 0.05
        }

        # 验收标准
        criteria = {
            'max_overspeed': 1.45,
            'settling_time': 60.0,
            'max_pressure': 600.0,
            'frequency_deviation': 0.1
        }

        evaluation = evaluator.evaluate(simulation_results, criteria)

        assert evaluation['overall_pass'] == True
        assert all(c['passed'] for c in evaluation['criteria_results'].values())

    def test_scheme_comparison(self):
        """测试方案对比"""
        from yjdt.simulation.sil_testing import SILTestFramework

        framework = SILTestFramework()

        # 两个设计方案
        scheme1 = {
            'name': '方案一',
            'parameters': {
                'rated_head': 480.0,
                'tunnel_length': 25000.0
            }
        }

        scheme2 = {
            'name': '方案二',
            'parameters': {
                'rated_head': 2100.0,
                'tunnel_length': 45000.0
            }
        }

        comparison = framework.compare_schemes(
            schemes=[scheme1, scheme2],
            test_scenarios=['load_rejection', 'startup', 'fault']
        )

        assert len(comparison) == 2
        assert all('score' in c for c in comparison)


class TestTestReport:
    """测试报告测试"""

    def test_report_generation(self):
        """测试报告生成"""
        from yjdt.simulation.sil_testing import TestReport, TestResult

        results = [
            TestResult(
                test_name="TC001",
                passed=True,
                metrics={'overspeed': 1.30},
                execution_time=5.2
            ),
            TestResult(
                test_name="TC002",
                passed=True,
                metrics={'settling_time': 40.0},
                execution_time=8.5
            ),
            TestResult(
                test_name="TC003",
                passed=False,
                metrics={'max_pressure': 650.0},
                execution_time=3.1,
                failure_reason="超过允许压力"
            )
        ]

        report = TestReport(results=results)
        summary = report.generate_summary()

        assert summary['total_tests'] == 3
        assert summary['passed'] == 2
        assert summary['failed'] == 1
        assert summary['pass_rate'] == pytest.approx(2/3, rel=0.01)

    def test_report_export(self):
        """测试报告导出"""
        from yjdt.simulation.sil_testing import TestReport, TestResult
        import tempfile
        import os

        results = [
            TestResult(
                test_name="TC001",
                passed=True,
                metrics={'overspeed': 1.30},
                execution_time=5.2
            )
        ]

        report = TestReport(results=results)

        # 导出为字典格式
        report_dict = report.to_dict()

        assert 'summary' in report_dict
        assert 'results' in report_dict


class TestPerformanceMetrics:
    """性能指标测试"""

    def test_stability_metrics(self):
        """测试稳定性指标"""
        from yjdt.simulation.sil_testing import TestEvaluator

        evaluator = TestEvaluator()

        # 模拟时间序列数据
        time = np.linspace(0, 60, 6000)
        frequency = 50.0 + 0.2 * np.exp(-time / 10) * np.sin(2 * np.pi * 0.5 * time)

        metrics = evaluator.calculate_stability_metrics(time, frequency)

        assert 'settling_time' in metrics
        assert 'overshoot' in metrics
        assert 'damping_ratio' in metrics

    def test_safety_metrics(self):
        """测试安全性指标"""
        from yjdt.simulation.sil_testing import TestEvaluator

        evaluator = TestEvaluator()

        # 模拟数据
        data = {
            'speed': np.ones(1000) * 100.0 + np.random.randn(1000) * 0.5,
            'pressure': np.ones(1000) * 480.0 + np.random.randn(1000) * 5,
            'temperature': np.ones(1000) * 60.0 + np.random.randn(1000) * 2
        }

        limits = {
            'speed': (90.0, 110.0),
            'pressure': (400.0, 600.0),
            'temperature': (40.0, 80.0)
        }

        metrics = evaluator.calculate_safety_metrics(data, limits)

        assert 'speed_margin' in metrics
        assert 'pressure_margin' in metrics
        assert all(m > 0 for m in metrics.values())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
