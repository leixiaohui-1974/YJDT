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


# ==============================================================================
# 扩展配置管理
# ==============================================================================

@dataclass
class ODDConfig:
    """ODD配置"""
    zones: list = field(default_factory=lambda: [
        "OPTIMAL", "NORMAL", "DEGRADED", "RESTRICTED", "EMERGENCY", "FORBIDDEN"
    ])
    default_zone: str = "NORMAL"
    scan_interval: float = 1.0
    boundary_margins: Dict = field(default_factory=lambda: {
        "frequency": {"optimal": 0.1, "normal": 0.2, "restricted": 0.5},
        "pressure": {"optimal": 10, "normal": 20, "restricted": 35},
        "power": {"optimal": 0.95, "normal": 0.9, "restricted": 0.8}
    })


@dataclass
class MBDConfig:
    """MBD优化配置"""
    default_algorithm: str = "auto"
    max_iterations: int = 1000
    convergence_tolerance: float = 1e-6
    population_size: int = 50
    parallel_evaluations: int = 4


@dataclass
class MASConfig:
    """MAS配置"""
    autonomy_level: int = 4
    decision_interval: float = 0.1
    consensus_iterations: int = 10
    degradation_threshold: float = 0.8


@dataclass
class VerificationConfig:
    """验证配置"""
    default_level: str = "standard"
    scenario_timeout: float = 600.0
    parallel_scenarios: int = 4
    report_format: str = "markdown"


@dataclass
class YJDTConfig:
    """YJDT完整配置"""
    project_name: str = "YJDT"
    version: str = "2.2.0"
    system: SystemConfig = field(default_factory=SystemConfig)
    odd: ODDConfig = field(default_factory=ODDConfig)
    mbd: MBDConfig = field(default_factory=MBDConfig)
    mas: MASConfig = field(default_factory=MASConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or CONFIG_DIR
        self._config_cache: Dict[str, Any] = {}

    def load(self, filename: str) -> Dict[str, Any]:
        """加载配置文件"""
        if filename in self._config_cache:
            return self._config_cache[filename]

        config_path = self.config_dir / filename
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                config = yaml.safe_load(f)
            elif filename.endswith('.json'):
                import json
                config = json.load(f)
            else:
                raise ValueError(f"不支持的配置格式: {filename}")

        self._config_cache[filename] = config
        return config

    def save(self, filename: str, config: Dict[str, Any]):
        """保存配置文件"""
        config_path = self.config_dir / filename

        with open(config_path, 'w', encoding='utf-8') as f:
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            elif filename.endswith('.json'):
                import json
                json.dump(config, f, indent=2, ensure_ascii=False)

        # 清除缓存
        if filename in self._config_cache:
            del self._config_cache[filename]

    def reload(self, filename: str) -> Dict[str, Any]:
        """重新加载配置"""
        if filename in self._config_cache:
            del self._config_cache[filename]
        return self.load(filename)


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate_hydraulic(config: HydraulicConfig) -> list:
        """验证水力配置"""
        errors = []
        if config.rated_head <= 0:
            errors.append("额定水头必须大于0")
        if config.rated_flow <= 0:
            errors.append("额定流量必须大于0")
        if config.tunnel_length <= 0:
            errors.append("隧洞长度必须大于0")
        if config.tunnel_diameter <= 0:
            errors.append("隧洞直径必须大于0")
        if config.wave_speed <= 0:
            errors.append("波速必须大于0")
        return errors

    @staticmethod
    def validate_turbine(config: TurbineConfig) -> list:
        """验证水轮机配置"""
        errors = []
        if config.rated_power <= 0:
            errors.append("额定功率必须大于0")
        if config.efficiency <= 0 or config.efficiency > 1:
            errors.append("效率必须在0-1之间")
        if config.guide_vane_close_time <= 0:
            errors.append("导叶关闭时间必须大于0")
        return errors

    @staticmethod
    def validate_odd(config: ODDConfig) -> list:
        """验证ODD配置"""
        errors = []
        if not config.zones:
            errors.append("ODD区域列表不能为空")
        if config.default_zone not in config.zones:
            errors.append(f"默认区域{config.default_zone}不在区域列表中")
        if config.scan_interval <= 0:
            errors.append("扫描间隔必须大于0")
        return errors

    @staticmethod
    def validate_all(config: YJDTConfig) -> Dict[str, list]:
        """验证所有配置"""
        return {
            "hydraulic": ConfigValidator.validate_hydraulic(config.system.hydraulic),
            "turbine": ConfigValidator.validate_turbine(config.system.turbine),
            "odd": ConfigValidator.validate_odd(config.odd)
        }


# 全局配置实例
_global_config: Optional[YJDTConfig] = None


def get_config() -> YJDTConfig:
    """获取全局配置"""
    global _global_config
    if _global_config is None:
        _global_config = YJDTConfig()
    return _global_config


def save_config(config: YJDTConfig, filepath: str):
    """保存配置到文件"""
    import json
    from dataclasses import asdict

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(asdict(config), f, indent=2, ensure_ascii=False)


__all__ = [
    # 数据类
    "HydraulicConfig",
    "SurgeTankConfig",
    "TurbineConfig",
    "GeneratorConfig",
    "GovernorConfig",
    "SimulationConfig",
    "SystemConfig",
    "ODDConfig",
    "MBDConfig",
    "MASConfig",
    "VerificationConfig",
    "YJDTConfig",
    # 工具类
    "ConfigLoader",
    "ConfigValidator",
    # 函数
    "load_config",
    "get_scheme_config",
    "get_cascade_config",
    "get_control_hierarchy",
    "get_config",
    "save_config",
]
