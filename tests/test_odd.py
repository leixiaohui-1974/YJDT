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
        from yjdt.odd import ODDZone

        assert ODDZone.OPTIMAL.value == "optimal"
        assert ODDZone.NORMAL.value == "normal"
        assert ODDZone.DEGRADED.value == "degraded"
        assert ODDZone.RESTRICTED.value == "restricted"
        assert ODDZone.EMERGENCY.value == "emergency"
        assert ODDZone.FORBIDDEN.value == "forbidden"

    def test_degradation_level(self):
        """测试降级等级"""
        from yjdt.odd import DegradationLevel

        assert DegradationLevel.NONE.value == 0
        assert DegradationLevel.FULL.value == 5


class TestODDRules:
    """ODD规则测试"""

    def test_create_default_rules(self):
        """测试创建默认规则"""
        from yjdt.odd import create_default_odd_rules

        rules = create_default_odd_rules()
        assert len(rules) > 0
        assert all(hasattr(r, 'name') for r in rules)
        assert all(hasattr(r, 'rule_type') for r in rules)

    def test_rule_types(self):
        """测试规则类型"""
        from yjdt.odd import ODDRuleType

        assert ODDRuleType.BOUNDARY.value == "boundary"
        assert ODDRuleType.RATE.value == "rate"
        assert ODDRuleType.DURATION.value == "duration"


class TestODDScanner:
    """ODD扫描器测试"""

    def test_scanner_creation(self):
        """测试扫描器创建"""
        from yjdt.odd import ODDScanner, create_default_odd_rules

        rules = create_default_odd_rules()
        scanner = ODDScanner(rules)
        assert scanner is not None

    def test_scan_normal_state(self):
        """测试正常状态扫描"""
        from yjdt.odd import ODDScanner, create_default_odd_rules, ODDZone

        rules = create_default_odd_rules()
        scanner = ODDScanner(rules)

        # 正常状态
        state = {
            "frequency": 50.0,
            "pressure": 1.0,
            "power": 0.8,
            "guide_vane": 0.75
        }

        result = scanner.scan(state)
        assert result is not None
        assert result.current_zone in [ODDZone.OPTIMAL, ODDZone.NORMAL]

    def test_scan_violation_detection(self):
        """测试违规检测"""
        from yjdt.odd import ODDScanner, create_default_odd_rules

        rules = create_default_odd_rules()
        scanner = ODDScanner(rules)

        # 异常状态
        state = {
            "frequency": 45.0,  # 严重偏低
            "pressure": 1.5,   # 严重偏高
            "power": 0.3,
            "guide_vane": 0.2
        }

        result = scanner.scan(state)
        assert len(result.violations) > 0


class TestODDStateMachine:
    """ODD状态机测试"""

    def test_state_machine_creation(self):
        """测试状态机创建"""
        from yjdt.odd import ODDStateMachine

        sm = ODDStateMachine()
        assert sm is not None

    def test_state_transition(self):
        """测试状态转换"""
        from yjdt.odd import ODDStateMachine, ODDZone

        sm = ODDStateMachine()
        # 状态机应该从某个初始状态开始
        assert sm.current_zone is not None


class TestYajiangODD:
    """雅江工程ODD测试"""

    def test_create_yajiang_odd(self):
        """测试创建雅江ODD"""
        from yjdt.odd import create_yajiang_bigbend_odd

        odd = create_yajiang_bigbend_odd()
        assert odd is not None
        assert odd.name == "雅江大拐弯梯级"
        assert len(odd.stations) == 5

    def test_station_odd_boundaries(self):
        """测试电站ODD边界"""
        from yjdt.odd import create_yajiang_bigbend_odd

        odd = create_yajiang_bigbend_odd()
        for station in odd.stations:
            assert hasattr(station, 'frequency_limits')
            assert hasattr(station, 'pressure_limits')
