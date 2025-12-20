# -*- coding: utf-8 -*-
"""
传感器和执行器模块测试
Sensors and Actuators Module Tests
"""

import pytest
import numpy as np


class TestSensors:
    """传感器测试 / Sensor Tests"""

    def test_pressure_sensor(self):
        """测试压力传感器"""
        from yjdt.sensors.sensors import PressureSensor

        sensor = PressureSensor(
            sensor_id="PT001",
            location="penstock_inlet",
            range_min=0.0,
            range_max=600.0,
            accuracy=0.1,
            response_time=0.01
        )

        # 测试正常测量
        measurement = sensor.measure(true_value=480.0, dt=0.01)

        assert measurement is not None
        assert 'value' in measurement
        assert 'timestamp' in measurement
        assert 'quality' in measurement

        # 测量值应在合理范围内（考虑噪声）
        assert 450.0 < measurement['value'] < 510.0

    def test_flow_sensor(self):
        """测试流量传感器"""
        from yjdt.sensors.sensors import FlowSensor

        sensor = FlowSensor(
            sensor_id="FT001",
            location="penstock",
            range_min=0.0,
            range_max=300.0,
            accuracy=0.5
        )

        measurement = sensor.measure(true_value=200.0, dt=0.01)

        assert 190.0 < measurement['value'] < 210.0

    def test_speed_sensor(self):
        """测试转速传感器"""
        from yjdt.sensors.sensors import SpeedSensor

        sensor = SpeedSensor(
            sensor_id="ST001",
            location="turbine_shaft",
            pulses_per_revolution=60,
            accuracy=0.01
        )

        measurement = sensor.measure(true_value=100.0, dt=0.01)

        assert 99.0 < measurement['value'] < 101.0

    def test_sensor_fault_injection(self):
        """测试传感器故障注入"""
        from yjdt.sensors.sensors import PressureSensor, FaultType

        sensor = PressureSensor(
            sensor_id="PT002",
            location="test",
            range_min=0.0,
            range_max=600.0,
            accuracy=0.1
        )

        # 注入偏置故障
        sensor.inject_fault(FaultType.BIAS, magnitude=50.0)

        measurement = sensor.measure(true_value=480.0, dt=0.01)

        # 测量值应该有明显偏置
        assert measurement['value'] > 520.0 or measurement['value'] < 440.0
        assert measurement['quality'] < 1.0

    def test_sensor_stuck_fault(self):
        """测试传感器卡死故障"""
        from yjdt.sensors.sensors import PressureSensor, FaultType

        sensor = PressureSensor(
            sensor_id="PT003",
            location="test",
            range_min=0.0,
            range_max=600.0,
            accuracy=0.1
        )

        # 先进行一次正常测量
        sensor.measure(true_value=400.0, dt=0.01)

        # 注入卡死故障
        sensor.inject_fault(FaultType.STUCK)

        # 多次测量应该返回相同值
        values = []
        for true_val in [420.0, 450.0, 480.0]:
            m = sensor.measure(true_value=true_val, dt=0.01)
            values.append(m['value'])

        # 所有值应该相同（卡死）
        assert len(set([round(v, 1) for v in values])) == 1

    def test_vibration_sensor(self):
        """测试振动传感器"""
        from yjdt.sensors.sensors import VibrationSensor

        sensor = VibrationSensor(
            sensor_id="VT001",
            location="bearing",
            frequency_range=(0.1, 1000.0),
            sensitivity=100.0  # mV/g
        )

        measurement = sensor.measure(true_value=0.5, dt=0.001)

        assert 'value' in measurement
        assert 'spectrum' in measurement or measurement['value'] > 0


class TestActuators:
    """执行器测试 / Actuator Tests"""

    def test_guide_vane_actuator(self):
        """测试导叶执行器"""
        from yjdt.sensors.actuators import GuideVaneActuator

        actuator = GuideVaneActuator(
            actuator_id="GV001",
            opening_time=8.0,
            closing_time=12.0,
            max_opening=1.0,
            min_opening=0.0,
            dead_band=0.001
        )

        actuator.initialize(position=0.5)

        # 发送开启命令
        actuator.set_command(0.8)

        # 仿真执行器动作
        for _ in range(100):
            position = actuator.step(dt=0.1)

        # 位置应该接近目标
        assert 0.75 < position < 0.85

    def test_valve_actuator(self):
        """测试阀门执行器"""
        from yjdt.sensors.actuators import ValveActuator

        actuator = ValveActuator(
            actuator_id="BV001",
            stroke_time=30.0,
            valve_type="butterfly"
        )

        actuator.initialize(position=1.0)  # 全开

        # 发送关闭命令
        actuator.set_command(0.0)

        # 仿真执行器动作
        for _ in range(50):
            position = actuator.step(dt=1.0)

        # 位置应该在下降
        assert position < 1.0

    def test_actuator_rate_limiting(self):
        """测试执行器速率限制"""
        from yjdt.sensors.actuators import GuideVaneActuator

        actuator = GuideVaneActuator(
            actuator_id="GV002",
            opening_time=10.0,  # 10秒全开
            closing_time=15.0,  # 15秒全关
            max_opening=1.0,
            min_opening=0.0
        )

        actuator.initialize(position=0.5)

        # 发送快速变化命令
        actuator.set_command(1.0)  # 要求立即全开

        # 只仿真0.1秒
        position = actuator.step(dt=0.1)

        # 由于速率限制，位置变化应该有限
        # 最大开启速率 = 1.0 / 10.0 = 0.1 /s
        max_change = 0.1 * 0.1  # 0.01

        assert position <= 0.5 + max_change + 0.001

    def test_actuator_fault_injection(self):
        """测试执行器故障注入"""
        from yjdt.sensors.actuators import GuideVaneActuator, ActuatorFaultType

        actuator = GuideVaneActuator(
            actuator_id="GV003",
            opening_time=8.0,
            closing_time=12.0
        )

        actuator.initialize(position=0.5)

        # 注入卡死故障
        actuator.inject_fault(ActuatorFaultType.STUCK)

        actuator.set_command(0.8)

        # 仿真多步
        positions = []
        for _ in range(50):
            pos = actuator.step(dt=0.1)
            positions.append(pos)

        # 位置应该保持不变（卡死）
        assert all(abs(p - 0.5) < 0.01 for p in positions)

    def test_exciter_actuator(self):
        """测试励磁执行器"""
        from yjdt.sensors.actuators import ExciterActuator

        actuator = ExciterActuator(
            actuator_id="EX001",
            max_voltage=500.0,
            ceiling_voltage=750.0,
            response_time=0.02
        )

        actuator.initialize(voltage=250.0)

        actuator.set_command(300.0)

        voltage = actuator.step(dt=0.01)

        assert voltage > 250.0
        assert voltage <= actuator.ceiling_voltage

    def test_breaker_actuator(self):
        """测试断路器执行器"""
        from yjdt.sensors.actuators import BreakerActuator

        actuator = BreakerActuator(
            actuator_id="CB001",
            closing_time=0.06,
            opening_time=0.04,
            rated_current=30000.0
        )

        actuator.initialize(state=True)  # 初始闭合

        # 发送分闸命令
        actuator.set_command(False)

        # 等待动作完成
        for _ in range(10):
            state = actuator.step(dt=0.01)

        # 应该已经分闸
        assert state == False


class TestSensorActuatorIntegration:
    """传感器-执行器集成测试"""

    def test_position_feedback_loop(self):
        """测试位置反馈回路"""
        from yjdt.sensors.sensors import PositionSensor
        from yjdt.sensors.actuators import GuideVaneActuator

        actuator = GuideVaneActuator(
            actuator_id="GV004",
            opening_time=8.0,
            closing_time=12.0
        )

        sensor = PositionSensor(
            sensor_id="PS001",
            location="guide_vane",
            range_min=0.0,
            range_max=1.0,
            accuracy=0.001
        )

        actuator.initialize(position=0.3)
        target = 0.7

        # 简单位置控制回路
        for _ in range(200):
            # 读取位置
            measurement = sensor.measure(
                true_value=actuator.get_position(),
                dt=0.01
            )

            # 简单比例控制
            error = target - measurement['value']
            command = actuator.get_position() + 0.5 * error
            command = np.clip(command, 0.0, 1.0)

            actuator.set_command(command)
            actuator.step(dt=0.05)

        # 位置应该接近目标
        final_position = actuator.get_position()
        assert abs(final_position - target) < 0.05


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
