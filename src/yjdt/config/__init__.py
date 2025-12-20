"""配置管理模块"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

CONFIG_DIR = Path(__file__).parent


@dataclass
class HydraulicConfig:
    """水力系统配置"""
    rated_head: float = 480.0
    rated_flow: float = 210.0
    tunnel_length: float = 25000.0
    tunnel_diameter: float = 11.0
    wave_speed: float = 1350.0
    friction_factor: float = 0.015
    water_inertia_time: float = 12.0
    gravity: float = 9.81
    water_density: float = 1000.0
    bulk_modulus: float = 2.2e9


@dataclass
class SurgeTankConfig:
    """调压设施配置"""
    type: str = "impedance"
    distance_from_plant: float = 800.0
    main_diameter: float = 45.0
    orifice_diameter: float = 6.5
    height: float = 120.0
    initial_level: float = 60.0


@dataclass
class TurbineConfig:
    """水轮机配置"""
    type: str = "francis"
    rated_power: float = 1000.0
    rated_speed: float = 166.7
    rated_head: float = 480.0
    rated_flow: float = 210.0
    efficiency: float = 0.94
    runaway_speed_ratio: float = 1.8
    inertia_gd2: float = 130000.0
    guide_vane_close_time: float = 8.0
    guide_vane_open_time: float = 12.0


@dataclass
class GeneratorConfig:
    """发电机配置"""
    type: str = "synchronous"
    rated_power: float = 1111.0
    rated_voltage: float = 20.0
    rated_frequency: float = 50.0
    power_factor: float = 0.9
    poles: int = 36
    inertia_constant: float = 4.0


@dataclass
class GovernorConfig:
    """调速器配置"""
    type: str = "PID"
    kp: float = 2.5
    ki: float = 0.15
    kd: float = 4.0
    servo_time: float = 0.5
    dead_band: float = 0.0004
    rate_limit: float = 0.1


@dataclass
class SimulationConfig:
    """仿真配置"""
    courant_number: float = 1.0
    num_segments: int = 100
    time_step: float = 0.01
    total_time: float = 300.0


@dataclass
class SystemConfig:
    """系统总配置"""
    hydraulic: HydraulicConfig = field(default_factory=HydraulicConfig)
    surge_tank: SurgeTankConfig = field(default_factory=SurgeTankConfig)
    turbine: TurbineConfig = field(default_factory=TurbineConfig)
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    governor: GovernorConfig = field(default_factory=GovernorConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)


def load_config(config_file: str = "yajiang_params.yaml") -> Dict[str, Any]:
    """加载配置文件"""
    config_path = CONFIG_DIR / config_file
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_scheme_config(scheme: str = "scheme_realistic") -> SystemConfig:
    """获取特定方案的配置"""
    config = load_config()
    scheme_data = config.get(scheme, {})

    return SystemConfig(
        hydraulic=HydraulicConfig(**scheme_data.get('hydraulic', {})),
        surge_tank=SurgeTankConfig(**scheme_data.get('surge_tank', {})),
        turbine=TurbineConfig(**scheme_data.get('turbine', {})),
        generator=GeneratorConfig(**scheme_data.get('generator', {})),
        governor=GovernorConfig(**scheme_data.get('governor', {})),
        simulation=SimulationConfig(**config.get('simulation', {}).get('moc', {})),
    )


def get_cascade_config() -> Dict[str, Any]:
    """获取梯级配置"""
    config = load_config()
    return config.get('cascade_config', {})


def get_control_hierarchy() -> Dict[str, Any]:
    """获取控制层级配置"""
    config = load_config()
    return config.get('control_hierarchy', {})
