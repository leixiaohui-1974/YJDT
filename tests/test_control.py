# -*- coding: utf-8 -*-
"""
控制系统模块测试
Control System Module Tests
"""

import pytest
import numpy as np


class TestFieldLevelController:
    """现场级控制器测试"""

    def test_field_controller_creation(self):
        """测试现场级控制器创建"""
        from yjdt.control.distributed import FieldLevelController

        controller = FieldLevelController(
            controller_id="FLC001",
            control_cycle=0.02,
            control_type="pid"
        )

        assert controller.controller_id == "FLC001"
        assert controller.control_cycle == 0.02

    def test_pid_control_output(self):
        """测试PID控制输出"""
        from yjdt.control.distributed import FieldLevelController

        controller = FieldLevelController(
            controller_id="FLC002",
            control_cycle=0.02,
            control_type="pid",
            kp=2.0,
            ki=0.5,
            kd=0.1
        )

        controller.initialize(setpoint=100.0)

        # 模拟过程值偏离设定值
        output = controller.compute(
            process_value=98.0,
            dt=0.02
        )

        # 输出应该是正的（增加控制量）
        assert output > 0


class TestUnitLevelController:
    """机组级控制器测试"""

    def test_unit_controller_creation(self):
        """测试机组级控制器创建"""
        from yjdt.control.distributed import UnitLevelController

        controller = UnitLevelController(
            controller_id="ULC001",
            control_cycle=0.1,
            prediction_horizon=20
        )

        assert controller.controller_id == "ULC001"
        assert controller.control_cycle == 0.1

    def test_mpc_optimization(self):
        """测试MPC优化"""
        from yjdt.control.distributed import UnitLevelController

        controller = UnitLevelController(
            controller_id="ULC002",
            control_cycle=0.1,
            prediction_horizon=20,
            control_horizon=5
        )

        controller.initialize(
            power_setpoint=800.0,
            frequency_setpoint=50.0
        )

        # 模拟系统状态
        system_state = {
            'power': 780.0,
            'frequency': 49.95,
            'head': 480.0,
            'guide_vane_opening': 0.75,
            'speed': 100.0
        }

        control_output = controller.compute(
            system_state=system_state,
            dt=0.1
        )

        assert 'guide_vane_command' in control_output
        assert 0 <= control_output['guide_vane_command'] <= 1.0


class TestPlantLevelController:
    """厂站级控制器测试"""

    def test_plant_controller_creation(self):
        """测试厂站级控制器创建"""
        from yjdt.control.distributed import PlantLevelController

        controller = PlantLevelController(
            controller_id="PLC001",
            n_units=4,
            control_cycle=1.0
        )

        assert controller.n_units == 4

    def test_load_dispatch(self):
        """测试负荷分配"""
        from yjdt.control.distributed import PlantLevelController

        controller = PlantLevelController(
            controller_id="PLC002",
            n_units=4,
            control_cycle=1.0,
            optimization_method="equal_margin"
        )

        controller.initialize(total_load=3000.0)

        # 模拟各机组状态
        unit_states = [
            {'power': 750.0, 'efficiency': 0.92, 'available': True},
            {'power': 750.0, 'efficiency': 0.91, 'available': True},
            {'power': 750.0, 'efficiency': 0.93, 'available': True},
            {'power': 750.0, 'efficiency': 0.90, 'available': True}
        ]

        dispatch = controller.dispatch(
            total_load_command=3200.0,
            unit_states=unit_states
        )

        # 检查分配结果
        assert len(dispatch) == 4
        assert sum(dispatch) == pytest.approx(3200.0, rel=0.01)

    def test_vibration_zone_avoidance(self):
        """测试振动区规避"""
        from yjdt.control.distributed import PlantLevelController

        controller = PlantLevelController(
            controller_id="PLC003",
            n_units=2,
            control_cycle=1.0,
            vibration_zones=[(350, 450), (550, 650)]  # 振动区
        )

        controller.initialize(total_load=1000.0)

        unit_states = [
            {'power': 500.0, 'efficiency': 0.92, 'available': True},
            {'power': 500.0, 'efficiency': 0.91, 'available': True}
        ]

        # 请求的负荷在振动区
        dispatch = controller.dispatch(
            total_load_command=800.0,  # 每台400MW在振动区
            unit_states=unit_states
        )

        # 分配应该避开振动区
        for power in dispatch:
            assert power < 350 or power > 450


class TestCascadeLevelController:
    """梯级控制器测试"""

    def test_cascade_controller_creation(self):
        """测试梯级控制器创建"""
        from yjdt.control.distributed import CascadeLevelController

        controller = CascadeLevelController(
            controller_id="CLC001",
            n_stations=3,
            control_cycle=60.0
        )

        assert controller.n_stations == 3

    def test_cascade_coordination(self):
        """测试梯级协调"""
        from yjdt.control.distributed import CascadeLevelController

        controller = CascadeLevelController(
            controller_id="CLC002",
            n_stations=3,
            control_cycle=60.0
        )

        controller.initialize(
            total_load=5000.0,
            water_level_targets=[450.0, 420.0, 380.0]
        )

        # 模拟各电站状态
        station_states = [
            {'power': 2000.0, 'water_level': 448.0, 'inflow': 500.0},
            {'power': 1800.0, 'water_level': 418.0, 'inflow': 520.0},
            {'power': 1200.0, 'water_level': 382.0, 'inflow': 530.0}
        ]

        commands = controller.coordinate(
            total_load_command=5200.0,
            station_states=station_states
        )

        assert len(commands) == 3
        for cmd in commands:
            assert 'power_setpoint' in cmd


class TestDistributedController:
    """分布式控制器系统测试"""

    def test_distributed_controller_hierarchy(self):
        """测试分布式控制器层次结构"""
        from yjdt.control.distributed import DistributedController

        controller = DistributedController(
            system_id="YJDT001",
            n_stations=2,
            units_per_station=[4, 3]
        )

        controller.initialize()

        # 验证层次结构
        assert controller.cascade_controller is not None
        assert len(controller.plant_controllers) == 2
        assert len(controller.unit_controllers) == 7  # 4 + 3

    def test_hierarchical_control_loop(self):
        """测试分层控制回路"""
        from yjdt.control.distributed import DistributedController

        controller = DistributedController(
            system_id="YJDT002",
            n_stations=1,
            units_per_station=[2]
        )

        controller.initialize()

        # 模拟系统状态
        system_state = {
            'stations': [
                {
                    'power': 1500.0,
                    'water_level': 450.0,
                    'units': [
                        {'power': 750.0, 'frequency': 50.0, 'guide_vane': 0.8},
                        {'power': 750.0, 'frequency': 50.0, 'guide_vane': 0.8}
                    ]
                }
            ]
        }

        commands = controller.step(
            system_state=system_state,
            load_command=1600.0,
            dt=1.0
        )

        assert 'unit_commands' in commands


class TestCoordinationController:
    """协调控制器测试"""

    def test_agc_response(self):
        """测试AGC响应"""
        from yjdt.control.coordination import LoadDispatcher

        dispatcher = LoadDispatcher(
            n_units=4,
            participation_factors=[0.3, 0.3, 0.2, 0.2]
        )

        # AGC指令
        agc_command = 100.0  # 增加100MW

        unit_commands = dispatcher.dispatch_agc(
            agc_command=agc_command,
            unit_states=[
                {'power': 700.0, 'max_power': 1000.0, 'available': True},
                {'power': 700.0, 'max_power': 1000.0, 'available': True},
                {'power': 500.0, 'max_power': 800.0, 'available': True},
                {'power': 500.0, 'max_power': 800.0, 'available': True}
            ]
        )

        # 检查分配是否按参与因子分配
        assert unit_commands[0] == pytest.approx(30.0, rel=0.01)
        assert unit_commands[1] == pytest.approx(30.0, rel=0.01)

    def test_frequency_regulation(self):
        """测试频率调节"""
        from yjdt.control.coordination import FrequencyRegulator

        regulator = FrequencyRegulator(
            droop=0.05,
            dead_band=0.02
        )

        # 频率下降
        power_change = regulator.calculate_response(
            frequency=49.9,
            rated_frequency=50.0,
            rated_power=1000.0
        )

        # 功率应该增加
        assert power_change > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
