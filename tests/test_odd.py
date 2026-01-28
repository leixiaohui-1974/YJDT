# -*- coding: utf-8 -*-
"""
ODD模块单元测试
"""

import pytest
from datetime import datetime


class TestODDZones:
    """ODD区域测试"""

    def test_odd_zone_enum(self):
        """测试ODD区域枚举"""
        from yjdt.odd.operational_design_domain import ODDZone

        assert ODDZone.OPTIMAL.value == "optimal"
        assert ODDZone.NORMAL.value == "normal"
        assert ODDZone.DEGRADED.value == "degraded"
        assert ODDZone.RESTRICTED.value == "restricted"
        assert ODDZone.EMERGENCY.value == "emergency"
        assert ODDZone.FORBIDDEN.value == "forbidden"

    def test_degradation_level(self):
        """测试降级等级"""
        from yjdt.odd.operational_design_domain import DegradationLevel

        assert DegradationLevel.L0_OPTIMAL.value == 0
        assert DegradationLevel.L5_SHUTDOWN.value == 5


class TestODDRules:
    """ODD规则测试"""

    def test_rule_types(self):
        """测试规则类型"""
        from yjdt.odd.odd_identification import ODDRuleType

        assert ODDRuleType.BOUNDARY.value == "boundary"
        assert ODDRuleType.RATE.value == "rate"
        assert ODDRuleType.DURATION.value == "duration"


class TestODDStateMachine:
    """ODD状态机测试"""

    def test_state_machine_creation(self):
        """测试状态机创建"""
        from yjdt.odd.odd_identification import ODDStateMachine

        sm = ODDStateMachine()
        assert sm is not None


class TestYajiangODD:
    """雅江工程ODD测试"""

    def test_create_yajiang_odd(self):
        """测试创建雅江ODD"""
        from yjdt.odd.operational_design_domain import create_yajiang_bigbend_odd

        odd = create_yajiang_bigbend_odd()
        assert odd is not None
        # stations 是一个字典
        assert len(odd.stations) == 5
        # 检查电站ID
        assert "YJ01" in odd.stations
        assert "YJ05" in odd.stations

    def test_station_odd_boundaries(self):
        """测试电站ODD边界"""
        from yjdt.odd.operational_design_domain import create_yajiang_bigbend_odd

        odd = create_yajiang_bigbend_odd()
        for station_id, station in odd.stations.items():
            # 检查电站有边界定义
            assert hasattr(station, 'pressure_boundary')
            assert hasattr(station, 'flow_boundary')

    def test_yajiang_system_boundaries(self):
        """测试雅江系统边界"""
        from yjdt.odd.operational_design_domain import create_yajiang_bigbend_odd

        odd = create_yajiang_bigbend_odd()
        # 检查系统级边界
        assert "system_pressure" in odd.system_boundaries
        assert "system_flow" in odd.system_boundaries
        assert "system_frequency" in odd.system_boundaries


class TestODDValidator:
    """ODD验证器测试"""

    def test_validator_creation(self):
        """测试验证器创建"""
        from yjdt.odd.operational_design_domain import (
            ODDValidator,
            create_yajiang_bigbend_odd
        )

        odd = create_yajiang_bigbend_odd()
        validator = ODDValidator(odd)
        assert validator is not None


class TestBoundaryLimit:
    """边界限值测试"""

    def test_boundary_zone_detection(self):
        """测试边界区域检测"""
        from yjdt.odd.operational_design_domain import (
            BoundaryLimit,
            ODDBoundaryType,
            ODDZone
        )

        boundary = BoundaryLimit(
            name="测试边界",
            boundary_type=ODDBoundaryType.PRESSURE,
            unit="MPa",
            optimal_min=4.5,
            optimal_max=5.0,
            normal_min=4.0,
            normal_max=5.5,
            degraded_min=3.5,
            degraded_max=6.0,
            emergency_min=3.0,
            emergency_max=6.5,
            absolute_min=0.0,
            absolute_max=7.0
        )

        # 测试各区域判定
        assert boundary.get_zone(4.75) == ODDZone.OPTIMAL
        assert boundary.get_zone(4.25) == ODDZone.NORMAL
        assert boundary.get_zone(3.75) == ODDZone.DEGRADED
        assert boundary.get_zone(6.25) == ODDZone.RESTRICTED
        assert boundary.get_zone(2.5) == ODDZone.EMERGENCY
        assert boundary.get_zone(8.0) == ODDZone.FORBIDDEN
