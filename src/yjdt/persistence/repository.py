# -*- coding: utf-8 -*-
"""
数据仓库模式 - Repository Pattern

提供数据访问的抽象层
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, TypeVar

from yjdt.persistence.database import Database, get_database_manager
from yjdt.persistence.models import (
    SimulationRecord,
    ScenarioRecord,
    TimeSeriesRecord,
    AlarmRecord,
    ConfigRecord,
)

import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(ABC):
    """仓库基类"""

    def __init__(self, database: Database = None):
        if database is None:
            self.db = get_database_manager().db
        else:
            self.db = database

    @abstractmethod
    def create(self, entity: T) -> T:
        """创建实体"""
        pass

    @abstractmethod
    def get_by_id(self, entity_id: Any) -> Optional[T]:
        """按ID获取"""
        pass

    @abstractmethod
    def update(self, entity: T) -> bool:
        """更新实体"""
        pass

    @abstractmethod
    def delete(self, entity_id: Any) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """列出所有"""
        pass


class SimulationRepository(BaseRepository):
    """仿真记录仓库"""

    def create(self, record: SimulationRecord) -> SimulationRecord:
        """创建仿真记录"""
        if not record.simulation_id:
            record.simulation_id = f"sim_{uuid.uuid4().hex[:12]}"

        self.db.execute(
            """
            INSERT INTO simulations (
                simulation_id, name, description, config_json,
                simulation_status, progress, current_time,
                started_at, completed_at, computation_time,
                result_json, statistics_json, error_message,
                created_at, updated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.simulation_id, record.name, record.description,
                record.config_json, record.simulation_status,
                record.progress, record.current_time,
                record.started_at.isoformat() if record.started_at else None,
                record.completed_at.isoformat() if record.completed_at else None,
                record.computation_time, record.result_json,
                record.statistics_json, record.error_message,
                record.created_at.isoformat(), record.updated_at.isoformat(),
                record.status.value,
            )
        )

        return record

    def get_by_id(self, simulation_id: str) -> Optional[SimulationRecord]:
        """获取仿真记录"""
        row = self.db.fetch_one(
            "SELECT * FROM simulations WHERE simulation_id = ?",
            (simulation_id,)
        )
        if row:
            return self._row_to_record(row)
        return None

    def update(self, record: SimulationRecord) -> bool:
        """更新仿真记录"""
        record.updated_at = datetime.now()

        cursor = self.db.execute(
            """
            UPDATE simulations SET
                name = ?, description = ?, config_json = ?,
                simulation_status = ?, progress = ?, current_time = ?,
                started_at = ?, completed_at = ?, computation_time = ?,
                result_json = ?, statistics_json = ?, error_message = ?,
                updated_at = ?, status = ?
            WHERE simulation_id = ?
            """,
            (
                record.name, record.description, record.config_json,
                record.simulation_status, record.progress, record.current_time,
                record.started_at.isoformat() if record.started_at else None,
                record.completed_at.isoformat() if record.completed_at else None,
                record.computation_time, record.result_json,
                record.statistics_json, record.error_message,
                record.updated_at.isoformat(), record.status.value,
                record.simulation_id,
            )
        )
        return cursor.rowcount > 0

    def delete(self, simulation_id: str) -> bool:
        """删除仿真记录"""
        cursor = self.db.execute(
            "DELETE FROM simulations WHERE simulation_id = ?",
            (simulation_id,)
        )
        return cursor.rowcount > 0

    def list_all(self, limit: int = 100, offset: int = 0) -> List[SimulationRecord]:
        """列出所有仿真"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM simulations
            WHERE status = 'active'
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        return [self._row_to_record(row) for row in rows]

    def find_by_status(self, status: str, limit: int = 100) -> List[SimulationRecord]:
        """按状态查找"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM simulations
            WHERE simulation_status = ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (status, limit)
        )
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: Dict) -> SimulationRecord:
        """行转记录"""
        record = SimulationRecord()
        record.id = row.get("id")
        record.simulation_id = row.get("simulation_id", "")
        record.name = row.get("name", "")
        record.description = row.get("description", "")
        record.config_json = row.get("config_json", "{}")
        record.simulation_status = row.get("simulation_status", "pending")
        record.progress = row.get("progress", 0)
        record.current_time = row.get("current_time", 0)
        record.result_json = row.get("result_json", "{}")
        record.statistics_json = row.get("statistics_json", "{}")
        record.error_message = row.get("error_message", "")
        record.computation_time = row.get("computation_time", 0)

        if row.get("started_at"):
            record.started_at = datetime.fromisoformat(row["started_at"])
        if row.get("completed_at"):
            record.completed_at = datetime.fromisoformat(row["completed_at"])
        if row.get("created_at"):
            record.created_at = datetime.fromisoformat(row["created_at"])
        if row.get("updated_at"):
            record.updated_at = datetime.fromisoformat(row["updated_at"])

        return record


class ScenarioRepository(BaseRepository):
    """场景记录仓库"""

    def create(self, record: ScenarioRecord) -> ScenarioRecord:
        """创建场景记录"""
        if not record.scenario_id:
            record.scenario_id = f"scn_{uuid.uuid4().hex[:12]}"

        self.db.execute(
            """
            INSERT INTO scenarios (
                scenario_id, name, category, description,
                initial_conditions_json, boundary_conditions_json,
                parameters_json, duration, severity, probability,
                tags_json, validated, validation_result_json,
                created_at, updated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.scenario_id, record.name, record.category,
                record.description, record.initial_conditions_json,
                record.boundary_conditions_json, record.parameters_json,
                record.duration, record.severity, record.probability,
                record.tags_json, 1 if record.validated else 0,
                record.validation_result_json,
                record.created_at.isoformat(), record.updated_at.isoformat(),
                record.status.value,
            )
        )
        return record

    def get_by_id(self, scenario_id: str) -> Optional[ScenarioRecord]:
        """获取场景记录"""
        row = self.db.fetch_one(
            "SELECT * FROM scenarios WHERE scenario_id = ?",
            (scenario_id,)
        )
        if row:
            return self._row_to_record(row)
        return None

    def update(self, record: ScenarioRecord) -> bool:
        """更新场景记录"""
        record.updated_at = datetime.now()
        cursor = self.db.execute(
            """
            UPDATE scenarios SET
                name = ?, category = ?, description = ?,
                initial_conditions_json = ?, boundary_conditions_json = ?,
                parameters_json = ?, duration = ?, severity = ?,
                probability = ?, tags_json = ?, validated = ?,
                validation_result_json = ?, updated_at = ?, status = ?
            WHERE scenario_id = ?
            """,
            (
                record.name, record.category, record.description,
                record.initial_conditions_json, record.boundary_conditions_json,
                record.parameters_json, record.duration, record.severity,
                record.probability, record.tags_json,
                1 if record.validated else 0, record.validation_result_json,
                record.updated_at.isoformat(), record.status.value,
                record.scenario_id,
            )
        )
        return cursor.rowcount > 0

    def delete(self, scenario_id: str) -> bool:
        """删除场景记录"""
        cursor = self.db.execute(
            "DELETE FROM scenarios WHERE scenario_id = ?",
            (scenario_id,)
        )
        return cursor.rowcount > 0

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ScenarioRecord]:
        """列出所有场景"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM scenarios
            WHERE status = 'active'
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        return [self._row_to_record(row) for row in rows]

    def find_by_category(self, category: str, limit: int = 100) -> List[ScenarioRecord]:
        """按类别查找"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM scenarios
            WHERE category = ? AND status = 'active'
            ORDER BY name
            LIMIT ?
            """,
            (category, limit)
        )
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: Dict) -> ScenarioRecord:
        """行转记录"""
        record = ScenarioRecord()
        record.id = row.get("id")
        record.scenario_id = row.get("scenario_id", "")
        record.name = row.get("name", "")
        record.category = row.get("category", "")
        record.description = row.get("description", "")
        record.initial_conditions_json = row.get("initial_conditions_json", "{}")
        record.boundary_conditions_json = row.get("boundary_conditions_json", "{}")
        record.parameters_json = row.get("parameters_json", "{}")
        record.duration = row.get("duration", 3600)
        record.severity = row.get("severity", "normal")
        record.probability = row.get("probability", 1.0)
        record.tags_json = row.get("tags_json", "[]")
        record.validated = bool(row.get("validated", 0))
        record.validation_result_json = row.get("validation_result_json", "{}")

        if row.get("created_at"):
            record.created_at = datetime.fromisoformat(row["created_at"])
        if row.get("updated_at"):
            record.updated_at = datetime.fromisoformat(row["updated_at"])

        return record


class TimeSeriesRepository(BaseRepository):
    """时间序列数据仓库"""

    def create(self, record: TimeSeriesRecord) -> TimeSeriesRecord:
        """创建时间序列记录"""
        self.db.execute(
            """
            INSERT INTO time_series (
                tag_name, timestamp, value, quality, unit,
                source, storage_tier, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.tag_name, record.timestamp.isoformat(),
                record.value, record.quality, record.unit,
                record.source, record.storage_tier, record.metadata_json,
                record.created_at.isoformat(),
            )
        )
        return record

    def create_batch(self, records: List[TimeSeriesRecord]) -> int:
        """批量创建"""
        params = [
            (
                r.tag_name, r.timestamp.isoformat(), r.value,
                r.quality, r.unit, r.source, r.storage_tier,
                r.metadata_json, r.created_at.isoformat()
            )
            for r in records
        ]
        return self.db.execute_many(
            """
            INSERT INTO time_series (
                tag_name, timestamp, value, quality, unit,
                source, storage_tier, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            params
        )

    def get_by_id(self, record_id: int) -> Optional[TimeSeriesRecord]:
        """按ID获取"""
        row = self.db.fetch_one(
            "SELECT * FROM time_series WHERE id = ?",
            (record_id,)
        )
        if row:
            return self._row_to_record(row)
        return None

    def update(self, record: TimeSeriesRecord) -> bool:
        """更新记录（通常不更新时间序列）"""
        return False

    def delete(self, record_id: int) -> bool:
        """删除记录"""
        cursor = self.db.execute(
            "DELETE FROM time_series WHERE id = ?",
            (record_id,)
        )
        return cursor.rowcount > 0

    def list_all(self, limit: int = 1000, offset: int = 0) -> List[TimeSeriesRecord]:
        """列出所有"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM time_series
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        return [self._row_to_record(row) for row in rows]

    def query_by_tag(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10000
    ) -> List[TimeSeriesRecord]:
        """按标签和时间范围查询"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM time_series
            WHERE tag_name = ?
            AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
            LIMIT ?
            """,
            (tag_name, start_time.isoformat(), end_time.isoformat(), limit)
        )
        return [self._row_to_record(row) for row in rows]

    def query_by_tags(
        self,
        tag_names: List[str],
        start_time: datetime,
        end_time: datetime,
        limit: int = 10000
    ) -> Dict[str, List[TimeSeriesRecord]]:
        """按多个标签查询"""
        result = {tag: [] for tag in tag_names}

        placeholders = ",".join("?" * len(tag_names))
        rows = self.db.fetch_all(
            f"""
            SELECT * FROM time_series
            WHERE tag_name IN ({placeholders})
            AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
            LIMIT ?
            """,
            tuple(tag_names) + (start_time.isoformat(), end_time.isoformat(), limit)
        )

        for row in rows:
            record = self._row_to_record(row)
            if record.tag_name in result:
                result[record.tag_name].append(record)

        return result

    def get_latest(self, tag_name: str) -> Optional[TimeSeriesRecord]:
        """获取最新值"""
        row = self.db.fetch_one(
            """
            SELECT * FROM time_series
            WHERE tag_name = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (tag_name,)
        )
        if row:
            return self._row_to_record(row)
        return None

    def aggregate(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime,
        aggregation: str = "avg"
    ) -> Dict[str, float]:
        """聚合查询"""
        agg_func = {
            "avg": "AVG",
            "min": "MIN",
            "max": "MAX",
            "sum": "SUM",
            "count": "COUNT",
        }.get(aggregation.lower(), "AVG")

        row = self.db.fetch_one(
            f"""
            SELECT
                {agg_func}(value) as agg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                COUNT(*) as count
            FROM time_series
            WHERE tag_name = ?
            AND timestamp >= ? AND timestamp <= ?
            """,
            (tag_name, start_time.isoformat(), end_time.isoformat())
        )

        if row:
            return {
                "value": row.get("agg_value", 0),
                "min": row.get("min_value", 0),
                "max": row.get("max_value", 0),
                "count": row.get("count", 0),
            }
        return {"value": 0, "min": 0, "max": 0, "count": 0}

    def cleanup_old_data(self, days: int = 7, tier: str = "realtime") -> int:
        """清理旧数据"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor = self.db.execute(
            """
            DELETE FROM time_series
            WHERE storage_tier = ?
            AND timestamp < ?
            """,
            (tier, cutoff)
        )
        return cursor.rowcount

    def _row_to_record(self, row: Dict) -> TimeSeriesRecord:
        """行转记录"""
        record = TimeSeriesRecord()
        record.id = row.get("id")
        record.tag_name = row.get("tag_name", "")
        record.value = row.get("value", 0)
        record.quality = row.get("quality", "good")
        record.unit = row.get("unit", "")
        record.source = row.get("source", "")
        record.storage_tier = row.get("storage_tier", "realtime")
        record.metadata_json = row.get("metadata_json", "{}")

        if row.get("timestamp"):
            record.timestamp = datetime.fromisoformat(row["timestamp"])
        if row.get("created_at"):
            record.created_at = datetime.fromisoformat(row["created_at"])

        return record


class AlarmRepository(BaseRepository):
    """告警记录仓库"""

    def create(self, record: AlarmRecord) -> AlarmRecord:
        """创建告警记录"""
        if not record.alarm_id:
            record.alarm_id = f"ALM{uuid.uuid4().hex[:8].upper()}"

        self.db.execute(
            """
            INSERT INTO alarms (
                alarm_id, timestamp, severity, source, message,
                acknowledged, acknowledged_by, acknowledged_at,
                cleared, cleared_at, related_tags, related_events,
                notes, resolution, created_at, updated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.alarm_id, record.timestamp.isoformat(),
                record.severity, record.source, record.message,
                1 if record.acknowledged else 0, record.acknowledged_by,
                record.acknowledged_at.isoformat() if record.acknowledged_at else None,
                1 if record.cleared else 0,
                record.cleared_at.isoformat() if record.cleared_at else None,
                record.related_tags, record.related_events,
                record.notes, record.resolution,
                record.created_at.isoformat(), record.updated_at.isoformat(),
                record.status.value,
            )
        )
        return record

    def get_by_id(self, alarm_id: str) -> Optional[AlarmRecord]:
        """获取告警记录"""
        row = self.db.fetch_one(
            "SELECT * FROM alarms WHERE alarm_id = ?",
            (alarm_id,)
        )
        if row:
            return self._row_to_record(row)
        return None

    def update(self, record: AlarmRecord) -> bool:
        """更新告警记录"""
        record.updated_at = datetime.now()
        cursor = self.db.execute(
            """
            UPDATE alarms SET
                severity = ?, source = ?, message = ?,
                acknowledged = ?, acknowledged_by = ?, acknowledged_at = ?,
                cleared = ?, cleared_at = ?,
                notes = ?, resolution = ?, updated_at = ?, status = ?
            WHERE alarm_id = ?
            """,
            (
                record.severity, record.source, record.message,
                1 if record.acknowledged else 0, record.acknowledged_by,
                record.acknowledged_at.isoformat() if record.acknowledged_at else None,
                1 if record.cleared else 0,
                record.cleared_at.isoformat() if record.cleared_at else None,
                record.notes, record.resolution,
                record.updated_at.isoformat(), record.status.value,
                record.alarm_id,
            )
        )
        return cursor.rowcount > 0

    def delete(self, alarm_id: str) -> bool:
        """删除告警记录"""
        cursor = self.db.execute(
            "DELETE FROM alarms WHERE alarm_id = ?",
            (alarm_id,)
        )
        return cursor.rowcount > 0

    def list_all(self, limit: int = 100, offset: int = 0) -> List[AlarmRecord]:
        """列出所有告警"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM alarms
            WHERE status = 'active'
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        return [self._row_to_record(row) for row in rows]

    def find_active(self, limit: int = 100) -> List[AlarmRecord]:
        """查找活跃告警"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM alarms
            WHERE cleared = 0 AND status = 'active'
            ORDER BY severity DESC, timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [self._row_to_record(row) for row in rows]

    def find_by_severity(self, severity: str, limit: int = 100) -> List[AlarmRecord]:
        """按严重度查找"""
        rows = self.db.fetch_all(
            """
            SELECT * FROM alarms
            WHERE severity = ? AND status = 'active'
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (severity, limit)
        )
        return [self._row_to_record(row) for row in rows]

    def acknowledge(self, alarm_id: str, acknowledged_by: str = "") -> bool:
        """确认告警"""
        cursor = self.db.execute(
            """
            UPDATE alarms SET
                acknowledged = 1,
                acknowledged_by = ?,
                acknowledged_at = ?,
                updated_at = ?
            WHERE alarm_id = ?
            """,
            (
                acknowledged_by, datetime.now().isoformat(),
                datetime.now().isoformat(), alarm_id
            )
        )
        return cursor.rowcount > 0

    def clear(self, alarm_id: str, resolution: str = "") -> bool:
        """清除告警"""
        cursor = self.db.execute(
            """
            UPDATE alarms SET
                cleared = 1,
                cleared_at = ?,
                resolution = ?,
                updated_at = ?
            WHERE alarm_id = ?
            """,
            (
                datetime.now().isoformat(), resolution,
                datetime.now().isoformat(), alarm_id
            )
        )
        return cursor.rowcount > 0

    def _row_to_record(self, row: Dict) -> AlarmRecord:
        """行转记录"""
        record = AlarmRecord()
        record.id = row.get("id")
        record.alarm_id = row.get("alarm_id", "")
        record.severity = row.get("severity", "warning")
        record.source = row.get("source", "")
        record.message = row.get("message", "")
        record.acknowledged = bool(row.get("acknowledged", 0))
        record.acknowledged_by = row.get("acknowledged_by", "")
        record.cleared = bool(row.get("cleared", 0))
        record.related_tags = row.get("related_tags", "[]")
        record.related_events = row.get("related_events", "[]")
        record.notes = row.get("notes", "")
        record.resolution = row.get("resolution", "")

        if row.get("timestamp"):
            record.timestamp = datetime.fromisoformat(row["timestamp"])
        if row.get("acknowledged_at"):
            record.acknowledged_at = datetime.fromisoformat(row["acknowledged_at"])
        if row.get("cleared_at"):
            record.cleared_at = datetime.fromisoformat(row["cleared_at"])
        if row.get("created_at"):
            record.created_at = datetime.fromisoformat(row["created_at"])
        if row.get("updated_at"):
            record.updated_at = datetime.fromisoformat(row["updated_at"])

        return record
