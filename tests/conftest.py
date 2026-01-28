# -*- coding: utf-8 -*-
"""
YJDT测试配置

pytest配置和共享fixtures
"""

import pytest
import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_state():
    """示例系统状态"""
    return {
        "frequency": 50.0,
        "pressure": 1.0,
        "power": 0.85,
        "guide_vane": 0.8,
        "surge_level": 0.5
    }


@pytest.fixture
def design_params():
    """示例设计参数"""
    return {
        "tunnel_diameter": 12.0,
        "tunnel_length": 76000,
        "surge_tank_area": 800,
        "penstock_diameter": 8.0,
        "governor_kp": 2.5,
        "governor_ki": 0.3,
        "governor_kd": 0.1
    }


@pytest.fixture
def optimization_config():
    """优化配置"""
    return {
        "max_iterations": 100,
        "convergence_tolerance": 1e-4,
        "population_size": 20
    }


@pytest.fixture
def odd_rules():
    """ODD规则"""
    from yjdt.odd import create_default_odd_rules
    return create_default_odd_rules()


@pytest.fixture
def yajiang_odd():
    """雅江ODD"""
    from yjdt.odd import create_yajiang_bigbend_odd
    return create_yajiang_bigbend_odd()


@pytest.fixture
def yajiang_mas():
    """雅江MAS"""
    from yjdt.mas import create_yajiang_autonomous_mas
    return create_yajiang_autonomous_mas()


@pytest.fixture
def verification_integrator():
    """验证集成器"""
    from yjdt.mbd import create_yajiang_verification_integrator
    return create_yajiang_verification_integrator()


@pytest.fixture
def temp_output_dir(tmp_path):
    """临时输出目录"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
