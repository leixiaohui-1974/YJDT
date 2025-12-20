# -*- coding: utf-8 -*-
"""
优化模块测试
Optimization Module Tests
"""

import pytest
import numpy as np


class TestDesignOptimizer:
    """设计优化测试"""

    def test_design_scheme_creation(self):
        """测试设计方案创建"""
        from yjdt.optimization.design_optimizer import DesignScheme

        scheme = DesignScheme(
            name="方案一",
            description="多级开发方案",
            parameters={
                'rated_head': 480.0,
                'rated_power': 1000.0,
                'tunnel_length': 25000.0,
                'turbine_type': 'francis'
            }
        )

        assert scheme.name == "方案一"
        assert scheme.parameters['rated_head'] == 480.0

    def test_scheme_comparison(self):
        """测试方案对比"""
        from yjdt.optimization.design_optimizer import DesignScheme, SchemeComparator

        scheme1 = DesignScheme(
            name="方案一",
            parameters={
                'rated_head': 480.0,
                'rated_power': 1000.0,
                'efficiency': 0.92,
                'cost': 5000.0  # 百万元
            }
        )

        scheme2 = DesignScheme(
            name="方案二",
            parameters={
                'rated_head': 2100.0,
                'rated_power': 500.0,
                'efficiency': 0.90,
                'cost': 8000.0
            }
        )

        comparator = SchemeComparator(
            criteria=['efficiency', 'cost', 'rated_power'],
            weights=[0.4, 0.3, 0.3]
        )

        scores = comparator.compare([scheme1, scheme2])

        assert len(scores) == 2
        assert all(0 <= s <= 1 for s in scores.values())

    def test_multi_criteria_optimization(self):
        """测试多目标优化"""
        from yjdt.optimization.design_optimizer import DesignOptimizer

        optimizer = DesignOptimizer(
            objectives=['maximize_efficiency', 'minimize_cost', 'maximize_reliability'],
            constraints={
                'rated_power': (800.0, 1200.0),
                'rated_head': (400.0, 600.0)
            }
        )

        # 定义设计变量范围
        bounds = {
            'guide_vane_opening_rate': (0.05, 0.15),
            'surge_tank_area': (300.0, 800.0),
            'governor_kp': (1.0, 5.0)
        }

        result = optimizer.optimize(bounds=bounds, n_iterations=20)

        assert 'optimal_parameters' in result
        assert 'pareto_front' in result


class TestSensorPlacement:
    """传感器布设优化测试"""

    def test_observability_analysis(self):
        """测试可观测性分析"""
        from yjdt.optimization.sensor_placement import ObservabilityAnalyzer

        analyzer = ObservabilityAnalyzer(n_states=10)

        # 定义观测矩阵
        C = np.zeros((5, 10))
        C[0, 0] = 1  # 传感器1观测状态1
        C[1, 2] = 1  # 传感器2观测状态3
        C[2, 4] = 1
        C[3, 6] = 1
        C[4, 8] = 1

        # 分析可观测性
        result = analyzer.analyze(C)

        assert 'rank' in result
        assert 'observability_index' in result
        assert result['rank'] <= 10

    def test_diagnosability_analysis(self):
        """测试可诊断性分析"""
        from yjdt.optimization.sensor_placement import DiagnosabilityAnalyzer

        analyzer = DiagnosabilityAnalyzer()

        # 故障签名矩阵
        fault_signature = np.array([
            [1, 0, 1, 0, 0],  # 传感器1可检测故障1、3
            [0, 1, 0, 1, 0],  # 传感器2可检测故障2、4
            [1, 1, 0, 0, 1],  # 传感器3可检测故障1、2、5
            [0, 0, 1, 1, 1]   # 传感器4可检测故障3、4、5
        ])

        result = analyzer.analyze(fault_signature)

        assert 'detectability' in result
        assert 'isolability' in result
        assert 0 <= result['detectability'] <= 1

    def test_sensor_placement_optimization(self):
        """测试传感器布设优化"""
        from yjdt.optimization.sensor_placement import SensorPlacementOptimizer

        optimizer = SensorPlacementOptimizer(
            n_candidate_locations=20,
            max_sensors=10,
            objectives=['observability', 'diagnosability', 'cost']
        )

        # 候选位置
        candidate_locations = [
            {'id': f'LOC{i:02d}', 'type': 'pressure' if i < 10 else 'flow',
             'cost': 1000 + i * 100}
            for i in range(20)
        ]

        # 模拟系统矩阵
        A = np.random.randn(10, 10) * 0.1
        C_candidates = np.random.randn(20, 10)

        result = optimizer.optimize(
            candidate_locations=candidate_locations,
            system_matrix=A,
            observation_candidates=C_candidates
        )

        assert 'selected_locations' in result
        assert len(result['selected_locations']) <= 10


class TestEquipmentSelection:
    """设备选型优化测试"""

    def test_equipment_database(self):
        """测试设备数据库"""
        from yjdt.optimization.equipment_selection import EquipmentDatabase

        db = EquipmentDatabase()

        # 查询水轮机
        turbines = db.query(
            equipment_type='turbine',
            rated_power=(800.0, 1200.0),
            rated_head=(400.0, 600.0)
        )

        assert len(turbines) >= 0

    def test_equipment_matching(self):
        """测试设备匹配"""
        from yjdt.optimization.equipment_selection import EquipmentSelector

        selector = EquipmentSelector()

        requirements = {
            'rated_power': 1000.0,
            'rated_head': 480.0,
            'rated_speed': 100.0,
            'efficiency_min': 0.90
        }

        matches = selector.match_turbine(requirements)

        assert isinstance(matches, list)

    def test_tco_analysis(self):
        """测试总拥有成本分析"""
        from yjdt.optimization.equipment_selection import EquipmentSelector

        selector = EquipmentSelector()

        equipment = {
            'capital_cost': 50000000,  # 5000万元
            'annual_maintenance': 500000,  # 50万/年
            'efficiency': 0.92,
            'lifetime': 40  # 年
        }

        tco = selector.calculate_tco(
            equipment=equipment,
            discount_rate=0.08,
            annual_generation_hours=4500
        )

        assert tco > 0
        assert tco > equipment['capital_cost']  # TCO应大于初始投资


class TestLifecycleAnalysis:
    """全生命周期分析测试"""

    def test_cost_benefit_analysis(self):
        """测试成本效益分析"""
        from yjdt.optimization.lifecycle import CostBenefitAnalysis

        cba = CostBenefitAnalysis(
            project_lifetime=40,
            discount_rate=0.08
        )

        # 定义现金流
        cash_flows = {
            'capital_cost': 10000.0,  # 百万元
            'annual_revenue': 800.0,
            'annual_opex': 100.0
        }

        result = cba.analyze(cash_flows)

        assert 'npv' in result
        assert 'irr' in result
        assert 'payback_period' in result
        assert 'lcoe' in result

    def test_reliability_analysis(self):
        """测试可靠性分析"""
        from yjdt.optimization.lifecycle import ReliabilityAnalysis

        analysis = ReliabilityAnalysis()

        # 定义组件可靠性参数
        components = [
            {'name': 'turbine', 'mtbf': 50000, 'mttr': 168},
            {'name': 'generator', 'mtbf': 80000, 'mttr': 120},
            {'name': 'governor', 'mtbf': 30000, 'mttr': 24}
        ]

        result = analysis.analyze_system(components, configuration='series')

        assert 'system_mtbf' in result
        assert 'availability' in result
        assert result['availability'] < 1.0

    def test_lifecycle_comparison(self):
        """测试生命周期方案对比"""
        from yjdt.optimization.lifecycle import LifecycleAnalyzer

        analyzer = LifecycleAnalyzer(project_lifetime=40)

        scheme1 = {
            'name': '方案一',
            'capital_cost': 10000.0,
            'annual_revenue': 800.0,
            'annual_opex': 100.0,
            'availability': 0.95
        }

        scheme2 = {
            'name': '方案二',
            'capital_cost': 12000.0,
            'annual_revenue': 900.0,
            'annual_opex': 120.0,
            'availability': 0.97
        }

        result = analyzer.compare([scheme1, scheme2])

        assert len(result) == 2
        assert all('npv' in r for r in result)
        assert all('lcoe' in r for r in result)


class TestControllerTuning:
    """控制器整定测试"""

    def test_zn_tuning(self):
        """测试Ziegler-Nichols整定"""
        from yjdt.optimization.controller_tuning import ControllerOptimizer

        optimizer = ControllerOptimizer(method="ziegler-nichols")

        # 系统参数
        system_params = {
            'Ku': 4.0,  # 临界增益
            'Pu': 2.0   # 临界周期
        }

        pid_params = optimizer.tune_pid(system_params)

        assert 'kp' in pid_params
        assert 'ki' in pid_params
        assert 'kd' in pid_params

    def test_optimization_tuning(self):
        """测试优化整定"""
        from yjdt.optimization.controller_tuning import ControllerOptimizer

        optimizer = ControllerOptimizer(method="optimization")

        # 系统模型参数
        system = {
            'water_inertia_time': 12.0,
            'mechanical_time': 0.2,
            'rated_power': 1000.0
        }

        pid_params = optimizer.tune_pid(
            system,
            objective='itae',
            bounds={
                'kp': (1.0, 10.0),
                'ki': (0.1, 2.0),
                'kd': (0.0, 1.0)
            }
        )

        assert 'kp' in pid_params
        assert 1.0 <= pid_params['kp'] <= 10.0

    def test_robustness_analysis(self):
        """测试鲁棒性分析"""
        from yjdt.optimization.controller_tuning import ControllerOptimizer

        optimizer = ControllerOptimizer(method="optimization")

        pid_params = {
            'kp': 3.0,
            'ki': 0.5,
            'kd': 0.1
        }

        # 参数扰动分析
        robustness = optimizer.analyze_robustness(
            pid_params,
            parameter_variations={
                'water_inertia_time': (-0.2, 0.2),  # ±20%
                'head': (-0.1, 0.1)  # ±10%
            }
        )

        assert 'stability_margin' in robustness
        assert 'performance_variation' in robustness


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
