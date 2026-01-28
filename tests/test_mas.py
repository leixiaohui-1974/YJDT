# -*- coding: utf-8 -*-
"""
MAS模块单元测试
"""

import pytest


class TestAutonomyLevel:
    """自主等级测试"""

    def test_autonomy_levels(self):
        """测试自主等级枚举"""
        from yjdt.mas import AutonomyLevel

        assert AutonomyLevel.FULL_AUTONOMOUS.value == 5
        assert AutonomyLevel.HIGH_AUTONOMOUS.value == 4
        assert AutonomyLevel.SUPERVISED_AUTONOMOUS.value == 3
        assert AutonomyLevel.ASSISTED.value == 2
        assert AutonomyLevel.MANUAL.value == 1
        assert AutonomyLevel.LOCKDOWN.value == 0

    def test_autonomy_level_ordering(self):
        """测试自主等级排序"""
        from yjdt.mas import AutonomyLevel

        levels = [
            AutonomyLevel.LOCKDOWN,
            AutonomyLevel.MANUAL,
            AutonomyLevel.ASSISTED,
            AutonomyLevel.SUPERVISED_AUTONOMOUS,
            AutonomyLevel.HIGH_AUTONOMOUS,
            AutonomyLevel.FULL_AUTONOMOUS,
        ]

        for i in range(len(levels) - 1):
            assert levels[i].value < levels[i + 1].value


class TestODDAwareMAS:
    """ODD感知MAS测试"""

    def test_mas_creation(self):
        """测试MAS创建"""
        from yjdt.mas import create_yajiang_mas_system

        mas = create_yajiang_mas_system()
        assert mas is not None

    def test_agent_types(self):
        """测试智能体类型"""
        from yjdt.mas import AgentType

        assert AgentType.CENTRAL_COORDINATOR.value == "central_coordinator"
        assert AgentType.STATION_CONTROLLER.value == "station_controller"
        assert AgentType.UNIT_CONTROLLER.value == "unit_controller"


class TestFullAutonomousMAS:
    """全自主MAS测试"""

    def test_autonomous_mas_creation(self):
        """测试全自主MAS创建"""
        from yjdt.mas import create_yajiang_autonomous_mas

        mas = create_yajiang_autonomous_mas()
        assert mas is not None
        assert hasattr(mas, 'autonomy_level')

    def test_zone_controller(self):
        """测试区域控制器"""
        from yjdt.mas import ZoneController

        controller = ZoneController()
        assert controller is not None

    def test_degradation_controller(self):
        """测试降级控制器"""
        from yjdt.mas import DegradationController

        controller = DegradationController()
        assert controller is not None


class TestODDBoundaryGuard:
    """ODD边界守护测试"""

    def test_boundary_guard_creation(self):
        """测试边界守护创建"""
        from yjdt.mas import ODDBoundaryGuard

        guard = ODDBoundaryGuard()
        assert guard is not None


class TestControlAction:
    """控制动作测试"""

    def test_control_action_creation(self):
        """测试控制动作创建"""
        from yjdt.mas import ControlAction

        action = ControlAction(
            action_type="power_adjustment",
            target="unit_1",
            value=0.9,
            priority=1
        )

        assert action.action_type == "power_adjustment"
        assert action.target == "unit_1"
        assert action.value == 0.9


class TestAutonomousDecision:
    """自主决策测试"""

    def test_decision_creation(self):
        """测试决策创建"""
        from yjdt.mas import AutonomousDecision

        decision = AutonomousDecision(
            decision_id="DEC001",
            timestamp="2024-01-01T00:00:00",
            autonomy_level=4,
            actions=[],
            confidence=0.95
        )

        assert decision.decision_id == "DEC001"
        assert decision.autonomy_level == 4
        assert decision.confidence == 0.95
