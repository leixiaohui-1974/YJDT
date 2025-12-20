# -*- coding: utf-8 -*-
"""
持久化数据模型 - Persistence Data Models

定义数据库表结构和数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import json


class RecordStatus(Enum):
    """记录状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class BaseRecord:
    """基础记录"""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: RecordStatus = RecordStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseRecord':
        """从字典创建"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = RecordStatus(data['status'])
        return cls(**data)


@dataclass
class SimulationRecord(BaseRecord):
    """仿真记录"""
    simulation_id: str = ""
    name: str = ""
    description: str = ""

    # 配置
    config_json: str = "{}"

    # 状态
    simulation_status: str = "pending"
    progress: float = 0.0
    current_time: float = 0.0

    # 时间
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    computation_time: float = 0.0

    # 结果
    result_json: str = "{}"
    statistics_json: str = "{}"

    # 错误信息
    error_message: str = ""

    @property
    def config(self) -> Dict:
        """获取配置"""
        return json.loads(self.config_json)

    @config.setter
    def config(self, value: Dict):
        """设置配置"""
        self.config_json = json.dumps(value, ensure_ascii=False)

    @property
    def result(self) -> Dict:
        """获取结果"""
        return json.loads(self.result_json)

    @result.setter
    def result(self, value: Dict):
        """设置结果"""
        self.result_json = json.dumps(value, ensure_ascii=False)

    @property
    def statistics(self) -> Dict:
        """获取统计"""
        return json.loads(self.statistics_json)

    @statistics.setter
    def statistics(self, value: Dict):
        """设置统计"""
        self.statistics_json = json.dumps(value, ensure_ascii=False)


@dataclass
class ScenarioRecord(BaseRecord):
    """场景记录"""
    scenario_id: str = ""
    name: str = ""
    category: str = ""
    description: str = ""

    # 场景定义
    initial_conditions_json: str = "{}"
    boundary_conditions_json: str = "{}"
    parameters_json: str = "{}"

    # 元数据
    duration: float = 3600
    severity: str = "normal"
    probability: float = 1.0
    tags_json: str = "[]"

    # 验证状态
    validated: bool = False
    validation_result_json: str = "{}"

    @property
    def initial_conditions(self) -> Dict:
        return json.loads(self.initial_conditions_json)

    @initial_conditions.setter
    def initial_conditions(self, value: Dict):
        self.initial_conditions_json = json.dumps(value, ensure_ascii=False)

    @property
    def boundary_conditions(self) -> Dict:
        return json.loads(self.boundary_conditions_json)

    @boundary_conditions.setter
    def boundary_conditions(self, value: Dict):
        self.boundary_conditions_json = json.dumps(value, ensure_ascii=False)

    @property
    def parameters(self) -> Dict:
        return json.loads(self.parameters_json)

    @parameters.setter
    def parameters(self, value: Dict):
        self.parameters_json = json.dumps(value, ensure_ascii=False)

    @property
    def tags(self) -> List[str]:
        return json.loads(self.tags_json)

    @tags.setter
    def tags(self, value: List[str]):
        self.tags_json = json.dumps(value, ensure_ascii=False)


@dataclass
class TimeSeriesRecord(BaseRecord):
    """时间序列记录"""
    tag_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    value: float = 0.0
    quality: str = "good"
    unit: str = ""
    source: str = ""

    # 分层存储级别
    storage_tier: str = "realtime"

    # 元数据
    metadata_json: str = "{}"

    @property
    def metadata(self) -> Dict:
        return json.loads(self.metadata_json)

    @metadata.setter
    def metadata(self, value: Dict):
        self.metadata_json = json.dumps(value, ensure_ascii=False)


@dataclass
class AlarmRecord(BaseRecord):
    """告警记录"""
    alarm_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    severity: str = "warning"
    source: str = ""
    message: str = ""

    # 状态
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: Optional[datetime] = None

    cleared: bool = False
    cleared_at: Optional[datetime] = None

    # 关联
    related_tags: str = "[]"
    related_events: str = "[]"

    # 处理
    notes: str = ""
    resolution: str = ""


@dataclass
class ConfigRecord(BaseRecord):
    """配置记录"""
    config_key: str = ""
    config_value: str = ""
    config_type: str = "string"  # string, int, float, bool, json
    category: str = "general"
    description: str = ""

    # 版本控制
    version: int = 1
    previous_value: str = ""

    def get_typed_value(self) -> Any:
        """获取类型化的值"""
        if self.config_type == "int":
            return int(self.config_value)
        elif self.config_type == "float":
            return float(self.config_value)
        elif self.config_type == "bool":
            return self.config_value.lower() in ("true", "1", "yes")
        elif self.config_type == "json":
            return json.loads(self.config_value)
        else:
            return self.config_value

    def set_typed_value(self, value: Any):
        """设置类型化的值"""
        self.previous_value = self.config_value
        if isinstance(value, bool):
            self.config_type = "bool"
            self.config_value = str(value).lower()
        elif isinstance(value, int):
            self.config_type = "int"
            self.config_value = str(value)
        elif isinstance(value, float):
            self.config_type = "float"
            self.config_value = str(value)
        elif isinstance(value, (dict, list)):
            self.config_type = "json"
            self.config_value = json.dumps(value, ensure_ascii=False)
        else:
            self.config_type = "string"
            self.config_value = str(value)
        self.version += 1


@dataclass
class EventRecord(BaseRecord):
    """事件记录"""
    event_id: str = ""
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    description: str = ""
    data_json: str = "{}"
    severity: str = "info"

    @property
    def data(self) -> Dict:
        return json.loads(self.data_json)

    @data.setter
    def data(self, value: Dict):
        self.data_json = json.dumps(value, ensure_ascii=False)


# SQL表定义
TABLES = {
    "simulations": """
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simulation_id TEXT UNIQUE NOT NULL,
            name TEXT,
            description TEXT,
            config_json TEXT,
            simulation_status TEXT DEFAULT 'pending',
            progress REAL DEFAULT 0,
            current_time REAL DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            computation_time REAL DEFAULT 0,
            result_json TEXT,
            statistics_json TEXT,
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """,
    "scenarios": """
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id TEXT UNIQUE NOT NULL,
            name TEXT,
            category TEXT,
            description TEXT,
            initial_conditions_json TEXT,
            boundary_conditions_json TEXT,
            parameters_json TEXT,
            duration REAL DEFAULT 3600,
            severity TEXT DEFAULT 'normal',
            probability REAL DEFAULT 1.0,
            tags_json TEXT,
            validated INTEGER DEFAULT 0,
            validation_result_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """,
    "time_series": """
        CREATE TABLE IF NOT EXISTS time_series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            value REAL,
            quality TEXT DEFAULT 'good',
            unit TEXT,
            source TEXT,
            storage_tier TEXT DEFAULT 'realtime',
            metadata_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "alarms": """
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alarm_id TEXT UNIQUE NOT NULL,
            timestamp TEXT NOT NULL,
            severity TEXT DEFAULT 'warning',
            source TEXT,
            message TEXT,
            acknowledged INTEGER DEFAULT 0,
            acknowledged_by TEXT,
            acknowledged_at TEXT,
            cleared INTEGER DEFAULT 0,
            cleared_at TEXT,
            related_tags TEXT,
            related_events TEXT,
            notes TEXT,
            resolution TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """,
    "configs": """
        CREATE TABLE IF NOT EXISTS configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT,
            config_type TEXT DEFAULT 'string',
            category TEXT DEFAULT 'general',
            description TEXT,
            version INTEGER DEFAULT 1,
            previous_value TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """,
    "events": """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT,
            timestamp TEXT NOT NULL,
            source TEXT,
            description TEXT,
            data_json TEXT,
            severity TEXT DEFAULT 'info',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """,
}

# 索引定义
INDEXES = {
    "idx_time_series_tag_timestamp": """
        CREATE INDEX IF NOT EXISTS idx_time_series_tag_timestamp
        ON time_series(tag_name, timestamp)
    """,
    "idx_time_series_storage_tier": """
        CREATE INDEX IF NOT EXISTS idx_time_series_storage_tier
        ON time_series(storage_tier)
    """,
    "idx_alarms_timestamp": """
        CREATE INDEX IF NOT EXISTS idx_alarms_timestamp
        ON alarms(timestamp)
    """,
    "idx_alarms_severity": """
        CREATE INDEX IF NOT EXISTS idx_alarms_severity
        ON alarms(severity)
    """,
    "idx_simulations_status": """
        CREATE INDEX IF NOT EXISTS idx_simulations_status
        ON simulations(simulation_status)
    """,
    "idx_scenarios_category": """
        CREATE INDEX IF NOT EXISTS idx_scenarios_category
        ON scenarios(category)
    """,
    "idx_events_type_timestamp": """
        CREATE INDEX IF NOT EXISTS idx_events_type_timestamp
        ON events(event_type, timestamp)
    """,
}
