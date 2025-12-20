# -*- coding: utf-8 -*-
"""
配置管理器 - Configuration Manager

功能：
- 统一配置管理
- Schema验证
- 配置版本管理
- 热更新支持
- 配置变更审计
"""

import os
import json
import yaml
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Type, TypeVar
from datetime import datetime
from enum import Enum
from pathlib import Path
import copy


class ValidationError(Exception):
    """配置验证错误"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(f"{field}: {message}" if field else message)


class ConfigSection(Enum):
    """配置节"""
    SYSTEM = "system"
    SIMULATION = "simulation"
    CONTROL = "control"
    MONITORING = "monitoring"
    SAFETY = "safety"
    SECURITY = "security"
    NETWORK = "network"
    LOGGING = "logging"


@dataclass
class SystemConfig:
    """系统配置"""
    name: str = "YJDT"
    version: str = "1.3.0"
    environment: str = "development"  # development, testing, production

    # 时间配置
    timezone: str = "Asia/Shanghai"
    time_sync_enabled: bool = True
    time_sync_interval: int = 60  # 秒

    # 性能配置
    max_threads: int = 8
    max_memory_mb: int = 4096
    gc_interval: int = 300  # 秒

    # 调试配置
    debug_mode: bool = False
    profiling_enabled: bool = False

    def validate(self):
        """验证配置"""
        if not self.name:
            raise ValidationError("系统名称不能为空", "name")
        if self.max_threads < 1:
            raise ValidationError("线程数必须大于0", "max_threads", self.max_threads)
        if self.max_memory_mb < 256:
            raise ValidationError("内存至少256MB", "max_memory_mb", self.max_memory_mb)


@dataclass
class SimulationConfig:
    """仿真配置"""
    # 时间步长
    dt: float = 0.01  # 秒
    max_simulation_time: float = 3600  # 秒

    # 求解器配置
    solver: str = "rk4"  # euler, rk4, adaptive
    tolerance: float = 1e-6
    max_iterations: int = 100

    # MOC水锤计算
    moc_courant_number: float = 1.0
    moc_wave_speed: float = 1200  # m/s

    # 并行配置
    parallel_enabled: bool = False
    num_workers: int = 4

    def validate(self):
        if self.dt <= 0:
            raise ValidationError("时间步长必须为正", "dt", self.dt)
        if self.moc_courant_number > 1:
            raise ValidationError("Courant数不能大于1", "moc_courant_number")


@dataclass
class ControlConfig:
    """控制配置"""
    # 控制周期
    control_cycle_ms: int = 100
    agc_cycle_ms: int = 4000
    avc_cycle_ms: int = 1000

    # PID默认参数
    default_kp: float = 2.0
    default_ki: float = 0.5
    default_kd: float = 0.1

    # MPC配置
    mpc_horizon: int = 20
    mpc_control_horizon: int = 5

    # 安全限制
    rate_limit_enabled: bool = True
    max_rate_change: float = 10.0  # %/s

    def validate(self):
        if self.control_cycle_ms < 10:
            raise ValidationError("控制周期至少10ms", "control_cycle_ms")
        if self.mpc_horizon < self.mpc_control_horizon:
            raise ValidationError("预测域不能小于控制域", "mpc_horizon")


@dataclass
class MonitoringConfig:
    """监控配置"""
    # 采样配置
    sample_rate_hz: float = 100
    buffer_size: int = 10000

    # 告警配置
    alarm_delay_ms: int = 1000
    alarm_debounce_count: int = 3
    alarm_history_size: int = 10000

    # 趋势配置
    trend_window_size: int = 1000
    trend_detection_sensitivity: float = 0.8

    # 数据记录
    data_retention_days: int = 90
    archive_enabled: bool = True
    archive_interval_hours: int = 24

    def validate(self):
        if self.sample_rate_hz <= 0:
            raise ValidationError("采样率必须为正", "sample_rate_hz")


@dataclass
class SafetyConfig:
    """安全配置"""
    # 保护延时
    trip_delay_ms: int = 0
    alarm_delay_ms: int = 500

    # 联锁配置
    interlock_enabled: bool = True
    interlock_bypass_password: str = ""

    # 应急停机
    emergency_stop_enabled: bool = True
    emergency_response_timeout: int = 30  # 秒

    # 冗余配置
    redundancy_level: int = 2  # 2oo3
    voting_scheme: str = "2oo3"

    def validate(self):
        if self.redundancy_level < 1:
            raise ValidationError("冗余级别至少为1", "redundancy_level")


@dataclass
class SecurityConfig:
    """安全配置"""
    # 认证配置
    auth_enabled: bool = True
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    # 加密配置
    encryption_enabled: bool = True
    encryption_algorithm: str = "AES-256"

    # 审计配置
    audit_enabled: bool = True
    audit_retention_days: int = 365

    # 访问控制
    rbac_enabled: bool = True
    default_role: str = "operator"

    def validate(self):
        if self.session_timeout_minutes < 1:
            raise ValidationError("会话超时至少1分钟", "session_timeout_minutes")


@dataclass
class LoggingConfig:
    """日志配置"""
    # 日志级别
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # 文件配置
    file_enabled: bool = True
    file_path: str = "logs/yjdt.log"
    max_file_size_mb: int = 100
    backup_count: int = 10

    # 控制台配置
    console_enabled: bool = True
    console_color: bool = True

    # 远程日志
    remote_enabled: bool = False
    remote_host: str = ""
    remote_port: int = 514

    def validate(self):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ValidationError(f"日志级别必须是{valid_levels}之一", "level")


@dataclass
class ModuleConfig:
    """模块配置"""
    module_id: str
    module_type: str
    enabled: bool = True
    priority: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    def validate(self):
        if not self.module_id:
            raise ValidationError("模块ID不能为空", "module_id")


@dataclass
class ConfigChange:
    """配置变更记录"""
    change_id: str
    timestamp: datetime
    section: str
    field: str
    old_value: Any
    new_value: Any
    changed_by: str
    reason: str = ""


T = TypeVar('T')


class ConfigManager:
    """
    配置管理器

    提供统一的配置管理接口
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path

        # 各节配置
        self.system = SystemConfig()
        self.simulation = SimulationConfig()
        self.control = ControlConfig()
        self.monitoring = MonitoringConfig()
        self.safety = SafetyConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()

        # 模块配置
        self.modules: Dict[str, ModuleConfig] = {}

        # 变更历史
        self.change_history: List[ConfigChange] = []
        self._change_counter = 0

        # 观察者
        self._observers: Dict[str, List[callable]] = {}

        # 加载配置
        if config_path and os.path.exists(config_path):
            self.load(config_path)

    def load(self, path: str):
        """
        加载配置文件

        Args:
            path: 配置文件路径（支持JSON和YAML）
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        self._apply_config(data)
        self.config_path = str(path)

    def _apply_config(self, data: Dict[str, Any]):
        """应用配置数据"""
        if "system" in data:
            self._update_dataclass(self.system, data["system"])

        if "simulation" in data:
            self._update_dataclass(self.simulation, data["simulation"])

        if "control" in data:
            self._update_dataclass(self.control, data["control"])

        if "monitoring" in data:
            self._update_dataclass(self.monitoring, data["monitoring"])

        if "safety" in data:
            self._update_dataclass(self.safety, data["safety"])

        if "security" in data:
            self._update_dataclass(self.security, data["security"])

        if "logging" in data:
            self._update_dataclass(self.logging, data["logging"])

        if "modules" in data:
            for module_data in data["modules"]:
                module = ModuleConfig(**module_data)
                self.modules[module.module_id] = module

    def _update_dataclass(self, obj: Any, data: Dict[str, Any]):
        """更新dataclass对象"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

    def save(self, path: str = None):
        """
        保存配置

        Args:
            path: 保存路径（默认使用加载路径）
        """
        path = Path(path or self.config_path)

        data = self.to_dict()

        with open(path, 'w', encoding='utf-8') as f:
            if path.suffix in ['.yaml', '.yml']:
                yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "system": asdict(self.system),
            "simulation": asdict(self.simulation),
            "control": asdict(self.control),
            "monitoring": asdict(self.monitoring),
            "safety": asdict(self.safety),
            "security": asdict(self.security),
            "logging": asdict(self.logging),
            "modules": [asdict(m) for m in self.modules.values()],
        }

    def validate(self) -> List[ValidationError]:
        """
        验证所有配置

        Returns:
            验证错误列表
        """
        errors = []

        configs = [
            self.system, self.simulation, self.control,
            self.monitoring, self.safety, self.security, self.logging
        ]

        for config in configs:
            try:
                config.validate()
            except ValidationError as e:
                errors.append(e)

        for module in self.modules.values():
            try:
                module.validate()
            except ValidationError as e:
                errors.append(e)

        return errors

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            section: 配置节
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        config_map = {
            "system": self.system,
            "simulation": self.simulation,
            "control": self.control,
            "monitoring": self.monitoring,
            "safety": self.safety,
            "security": self.security,
            "logging": self.logging,
        }

        config = config_map.get(section)
        if config and hasattr(config, key):
            return getattr(config, key)

        return default

    def set(self, section: str, key: str, value: Any,
            changed_by: str = "system", reason: str = ""):
        """
        设置配置值

        Args:
            section: 配置节
            key: 配置键
            value: 新值
            changed_by: 修改者
            reason: 修改原因
        """
        config_map = {
            "system": self.system,
            "simulation": self.simulation,
            "control": self.control,
            "monitoring": self.monitoring,
            "safety": self.safety,
            "security": self.security,
            "logging": self.logging,
        }

        config = config_map.get(section)
        if not config:
            raise ValueError(f"未知的配置节: {section}")

        if not hasattr(config, key):
            raise ValueError(f"未知的配置键: {section}.{key}")

        # 记录变更
        old_value = getattr(config, key)

        self._change_counter += 1
        change = ConfigChange(
            change_id=f"CHG_{self._change_counter:06d}",
            timestamp=datetime.now(),
            section=section,
            field=key,
            old_value=old_value,
            new_value=value,
            changed_by=changed_by,
            reason=reason,
        )
        self.change_history.append(change)

        # 应用变更
        setattr(config, key, value)

        # 通知观察者
        self._notify_observers(section, key, old_value, value)

    def register_observer(self, section: str, callback: callable):
        """注册配置变更观察者"""
        if section not in self._observers:
            self._observers[section] = []
        self._observers[section].append(callback)

    def _notify_observers(self, section: str, key: str,
                          old_value: Any, new_value: Any):
        """通知观察者"""
        observers = self._observers.get(section, [])
        for callback in observers:
            try:
                callback(key, old_value, new_value)
            except Exception:
                pass

    def get_module_config(self, module_id: str) -> Optional[ModuleConfig]:
        """获取模块配置"""
        return self.modules.get(module_id)

    def set_module_config(self, config: ModuleConfig):
        """设置模块配置"""
        self.modules[config.module_id] = config

    def get_change_history(self, section: str = None,
                           limit: int = 100) -> List[ConfigChange]:
        """获取变更历史"""
        history = self.change_history

        if section:
            history = [c for c in history if c.section == section]

        return history[-limit:]

    def create_backup(self) -> Dict[str, Any]:
        """创建配置备份"""
        return {
            "timestamp": datetime.now().isoformat(),
            "config": copy.deepcopy(self.to_dict()),
        }

    def restore_backup(self, backup: Dict[str, Any]):
        """恢复配置备份"""
        if "config" in backup:
            self._apply_config(backup["config"])

    def diff(self, other: 'ConfigManager') -> Dict[str, Any]:
        """比较两个配置"""
        self_dict = self.to_dict()
        other_dict = other.to_dict()

        differences = {}

        for section in self_dict:
            if section not in other_dict:
                differences[section] = {"status": "removed"}
                continue

            if self_dict[section] != other_dict[section]:
                differences[section] = {
                    "self": self_dict[section],
                    "other": other_dict[section],
                }

        for section in other_dict:
            if section not in self_dict:
                differences[section] = {"status": "added"}

        return differences

    def export_documentation(self) -> str:
        """导出配置文档"""
        doc = ["# YJDT配置文档\n"]

        sections = [
            ("system", "系统配置", self.system),
            ("simulation", "仿真配置", self.simulation),
            ("control", "控制配置", self.control),
            ("monitoring", "监控配置", self.monitoring),
            ("safety", "安全配置", self.safety),
            ("security", "安全认证配置", self.security),
            ("logging", "日志配置", self.logging),
        ]

        for section_id, section_name, config in sections:
            doc.append(f"\n## {section_name}\n")
            doc.append(f"配置节: `{section_id}`\n")

            for field_name, field_value in asdict(config).items():
                doc.append(f"- **{field_name}**: `{field_value}`")

        return "\n".join(doc)

