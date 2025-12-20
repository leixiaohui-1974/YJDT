# -*- coding: utf-8 -*-
"""
数据记录与回放系统 - 全生命周期数据管理
Data Recording and Playback System

功能：
- 多级存储策略（实时/短期/长期/归档）
- 数据压缩与去重
- 快速查询与回放
- 事件触发记录
- 数据导出与备份
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Iterator, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json
import gzip
import struct
import threading


class RecordingMode(Enum):
    """记录模式"""
    CONTINUOUS = "continuous"       # 连续记录
    PERIODIC = "periodic"           # 周期记录
    ON_CHANGE = "on_change"         # 变化记录
    EVENT_TRIGGERED = "event"       # 事件触发


class CompressionLevel(Enum):
    """压缩级别"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class StorageTier(Enum):
    """存储层级"""
    REALTIME = "realtime"           # 实时层（内存，毫秒级）
    SHORT_TERM = "short_term"       # 短期层（1天，秒级）
    MEDIUM_TERM = "medium_term"     # 中期层（30天，分钟级）
    LONG_TERM = "long_term"         # 长期层（1年，小时级）
    ARCHIVE = "archive"             # 归档层（永久，日级）


@dataclass
class DataPoint:
    """数据点"""
    source_id: str
    value: float
    timestamp: datetime
    quality: int = 100              # 质量 0-100


@dataclass
class DataBlock:
    """数据块（压缩存储单元）"""
    source_id: str
    start_time: datetime
    end_time: datetime
    sample_count: int
    min_value: float
    max_value: float
    avg_value: float
    compressed_data: bytes = b""
    compression_level: CompressionLevel = CompressionLevel.NONE


@dataclass
class HistoricalQuery:
    """历史查询"""
    source_ids: List[str]
    start_time: datetime
    end_time: datetime
    aggregation: str = "none"       # none/avg/min/max/sum
    interval: Optional[float] = None  # 聚合间隔(秒)
    limit: Optional[int] = None


class DataRecorder:
    """
    数据记录器

    功能：
    - 多层级存储管理
    - 智能压缩与聚合
    - 高效查询接口
    - 事件触发记录
    """

    def __init__(self, base_path: str = "./data"):
        self.base_path = base_path
        self._lock = threading.Lock()

        # 多层存储
        self.storage = {
            StorageTier.REALTIME: {},      # 实时数据（内存）
            StorageTier.SHORT_TERM: {},    # 短期数据
            StorageTier.MEDIUM_TERM: {},   # 中期数据
            StorageTier.LONG_TERM: {},     # 长期数据
            StorageTier.ARCHIVE: {},       # 归档数据
        }

        # 存储配置
        self.tier_config = {
            StorageTier.REALTIME: {
                "max_duration": 3600,       # 1小时
                "sample_rate": 0.1,         # 100ms
                "compression": CompressionLevel.NONE,
            },
            StorageTier.SHORT_TERM: {
                "max_duration": 86400,      # 1天
                "sample_rate": 1.0,         # 1s
                "compression": CompressionLevel.LOW,
            },
            StorageTier.MEDIUM_TERM: {
                "max_duration": 2592000,    # 30天
                "sample_rate": 60.0,        # 1分钟
                "compression": CompressionLevel.MEDIUM,
            },
            StorageTier.LONG_TERM: {
                "max_duration": 31536000,   # 1年
                "sample_rate": 3600.0,      # 1小时
                "compression": CompressionLevel.HIGH,
            },
            StorageTier.ARCHIVE: {
                "max_duration": float('inf'),
                "sample_rate": 86400.0,     # 1天
                "compression": CompressionLevel.HIGH,
            },
        }

        # 记录配置
        self.recording_config: Dict[str, Dict[str, Any]] = {}
        self.event_triggers: List[Dict[str, Any]] = []

        # 统计信息
        self.stats = {
            "total_points": 0,
            "total_bytes": 0,
            "compression_ratio": 1.0,
            "by_tier": defaultdict(int),
        }

    def configure_source(self, source_id: str,
                         mode: RecordingMode = RecordingMode.CONTINUOUS,
                         deadband: float = 0.0,
                         sample_rate: Optional[float] = None):
        """配置数据源记录参数"""
        self.recording_config[source_id] = {
            "mode": mode,
            "deadband": deadband,
            "sample_rate": sample_rate,
            "last_value": None,
            "last_time": None,
        }

    def record(self, source_id: str, value: float,
               timestamp: Optional[datetime] = None,
               quality: int = 100) -> bool:
        """记录数据点"""
        timestamp = timestamp or datetime.now()

        # 检查记录条件
        if source_id in self.recording_config:
            config = self.recording_config[source_id]

            # 变化记录模式
            if config["mode"] == RecordingMode.ON_CHANGE:
                if config["last_value"] is not None:
                    if abs(value - config["last_value"]) <= config["deadband"]:
                        return False

            # 周期记录模式
            if config["mode"] == RecordingMode.PERIODIC:
                if config["last_time"] is not None and config["sample_rate"]:
                    elapsed = (timestamp - config["last_time"]).total_seconds()
                    if elapsed < config["sample_rate"]:
                        return False

            config["last_value"] = value
            config["last_time"] = timestamp

        # 写入实时层
        with self._lock:
            if source_id not in self.storage[StorageTier.REALTIME]:
                self.storage[StorageTier.REALTIME][source_id] = []

            self.storage[StorageTier.REALTIME][source_id].append(
                DataPoint(source_id, value, timestamp, quality)
            )

            self.stats["total_points"] += 1
            self.stats["by_tier"][StorageTier.REALTIME.value] += 1

        # 检查事件触发
        self._check_event_triggers(source_id, value, timestamp)

        return True

    def batch_record(self, records: List[Tuple[str, float, Optional[datetime]]]) -> int:
        """批量记录"""
        count = 0
        for source_id, value, timestamp in records:
            if self.record(source_id, value, timestamp):
                count += 1
        return count

    def _check_event_triggers(self, source_id: str, value: float, timestamp: datetime):
        """检查事件触发条件"""
        for trigger in self.event_triggers:
            if trigger.get("source_id") != source_id:
                continue

            condition = trigger.get("condition", "")
            threshold = trigger.get("threshold", 0)

            triggered = False
            if condition == "above" and value > threshold:
                triggered = True
            elif condition == "below" and value < threshold:
                triggered = True
            elif condition == "equal" and abs(value - threshold) < 1e-6:
                triggered = True

            if triggered:
                self._trigger_event_recording(trigger, value, timestamp)

    def _trigger_event_recording(self, trigger: Dict, value: float, timestamp: datetime):
        """触发事件记录"""
        # 记录事件前后的高频数据
        duration = trigger.get("duration", 60)  # 默认记录60秒
        sample_rate = trigger.get("sample_rate", 0.01)  # 默认10ms

        event_record = {
            "trigger_id": trigger.get("id", "unknown"),
            "source_id": trigger.get("source_id"),
            "trigger_time": timestamp,
            "trigger_value": value,
            "duration": duration,
            "sample_rate": sample_rate,
        }

        # 这里可以启动高频记录
        # 实际实现中会有独立的事件记录线程

    def add_event_trigger(self, source_id: str, condition: str,
                          threshold: float, duration: float = 60,
                          sample_rate: float = 0.01):
        """添加事件触发器"""
        trigger_id = f"TRG_{len(self.event_triggers):04d}"
        self.event_triggers.append({
            "id": trigger_id,
            "source_id": source_id,
            "condition": condition,
            "threshold": threshold,
            "duration": duration,
            "sample_rate": sample_rate,
        })
        return trigger_id

    def tier_transition(self, source_id: Optional[str] = None):
        """执行层级转换（数据压缩下沉）"""
        now = datetime.now()

        with self._lock:
            # 从实时层到短期层
            self._transition_tier(
                StorageTier.REALTIME,
                StorageTier.SHORT_TERM,
                source_id,
                now
            )

            # 其他层级转换类似...

    def _transition_tier(self, from_tier: StorageTier, to_tier: StorageTier,
                         source_id: Optional[str], now: datetime):
        """执行单个层级转换"""
        config = self.tier_config[from_tier]
        max_age = timedelta(seconds=config["max_duration"])
        cutoff = now - max_age

        sources = [source_id] if source_id else list(self.storage[from_tier].keys())

        for sid in sources:
            if sid not in self.storage[from_tier]:
                continue

            data = self.storage[from_tier][sid]
            if not data:
                continue

            # 找出需要转换的数据
            old_data = [d for d in data if d.timestamp < cutoff]
            if not old_data:
                continue

            # 聚合数据
            to_config = self.tier_config[to_tier]
            aggregated = self._aggregate_data(old_data, to_config["sample_rate"])

            # 压缩并存储到目标层
            if sid not in self.storage[to_tier]:
                self.storage[to_tier][sid] = []
            self.storage[to_tier][sid].extend(aggregated)

            # 从源层移除
            self.storage[from_tier][sid] = [d for d in data if d.timestamp >= cutoff]

    def _aggregate_data(self, data: List[DataPoint],
                        interval: float) -> List[DataPoint]:
        """聚合数据"""
        if not data or interval <= 0:
            return data

        aggregated = []
        current_bucket = []
        bucket_start = data[0].timestamp

        for point in data:
            bucket_end = bucket_start + timedelta(seconds=interval)
            if point.timestamp < bucket_end:
                current_bucket.append(point)
            else:
                # 完成当前桶
                if current_bucket:
                    agg_point = self._aggregate_bucket(current_bucket)
                    aggregated.append(agg_point)

                # 开始新桶
                bucket_start = point.timestamp
                current_bucket = [point]

        # 最后一个桶
        if current_bucket:
            agg_point = self._aggregate_bucket(current_bucket)
            aggregated.append(agg_point)

        return aggregated

    def _aggregate_bucket(self, bucket: List[DataPoint]) -> DataPoint:
        """聚合单个桶"""
        values = [p.value for p in bucket]
        qualities = [p.quality for p in bucket]

        return DataPoint(
            source_id=bucket[0].source_id,
            value=np.mean(values),
            timestamp=bucket[len(bucket)//2].timestamp,  # 取中点时间
            quality=int(np.mean(qualities))
        )

    def query(self, query: HistoricalQuery) -> Dict[str, List[Dict[str, Any]]]:
        """执行历史查询"""
        results = {}

        for source_id in query.source_ids:
            data = self._query_source(source_id, query.start_time, query.end_time)

            # 聚合处理
            if query.aggregation != "none" and query.interval:
                data = self._apply_aggregation(data, query.aggregation, query.interval)

            # 限制数量
            if query.limit:
                data = data[:query.limit]

            results[source_id] = [
                {
                    "timestamp": d.timestamp.isoformat(),
                    "value": d.value,
                    "quality": d.quality
                }
                for d in data
            ]

        return results

    def _query_source(self, source_id: str,
                      start_time: datetime,
                      end_time: datetime) -> List[DataPoint]:
        """查询单个数据源"""
        all_data = []

        # 从所有层级收集数据
        for tier in StorageTier:
            if source_id in self.storage[tier]:
                tier_data = self.storage[tier][source_id]
                filtered = [
                    d for d in tier_data
                    if start_time <= d.timestamp <= end_time
                ]
                all_data.extend(filtered)

        # 按时间排序
        all_data.sort(key=lambda d: d.timestamp)

        return all_data

    def _apply_aggregation(self, data: List[DataPoint],
                           aggregation: str,
                           interval: float) -> List[DataPoint]:
        """应用聚合"""
        if not data:
            return data

        buckets = defaultdict(list)
        start = data[0].timestamp

        for point in data:
            bucket_idx = int((point.timestamp - start).total_seconds() / interval)
            buckets[bucket_idx].append(point)

        aggregated = []
        for bucket_idx in sorted(buckets.keys()):
            bucket = buckets[bucket_idx]
            values = [p.value for p in bucket]

            if aggregation == "avg":
                agg_value = np.mean(values)
            elif aggregation == "min":
                agg_value = np.min(values)
            elif aggregation == "max":
                agg_value = np.max(values)
            elif aggregation == "sum":
                agg_value = np.sum(values)
            else:
                agg_value = np.mean(values)

            aggregated.append(DataPoint(
                source_id=bucket[0].source_id,
                value=agg_value,
                timestamp=start + timedelta(seconds=bucket_idx * interval),
                quality=int(np.mean([p.quality for p in bucket]))
            ))

        return aggregated

    def get_statistics(self, source_id: str,
                       start_time: datetime,
                       end_time: datetime) -> Dict[str, Any]:
        """获取统计信息"""
        data = self._query_source(source_id, start_time, end_time)

        if not data:
            return {"error": "No data"}

        values = [d.value for d in data]

        return {
            "source_id": source_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "count": len(values),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "median": float(np.median(values)),
            "percentile_5": float(np.percentile(values, 5)),
            "percentile_95": float(np.percentile(values, 95)),
        }

    def export(self, source_ids: List[str],
               start_time: datetime,
               end_time: datetime,
               format: str = "json") -> bytes:
        """导出数据"""
        query = HistoricalQuery(
            source_ids=source_ids,
            start_time=start_time,
            end_time=end_time
        )
        results = self.query(query)

        if format == "json":
            return json.dumps(results, indent=2).encode('utf-8')
        elif format == "csv":
            lines = ["timestamp,source_id,value,quality"]
            for source_id, data in results.items():
                for point in data:
                    lines.append(f"{point['timestamp']},{source_id},{point['value']},{point['quality']}")
            return "\n".join(lines).encode('utf-8')
        else:
            return json.dumps(results).encode('utf-8')


@dataclass
class DataPlayback:
    """数据回放器"""
    recorder: DataRecorder
    source_ids: List[str]
    start_time: datetime
    end_time: datetime
    speed: float = 1.0              # 回放速度
    current_time: datetime = None
    is_playing: bool = False
    _data_cache: Dict[str, List[DataPoint]] = field(default_factory=dict)

    def __post_init__(self):
        self.current_time = self.start_time
        self._load_data()

    def _load_data(self):
        """加载回放数据"""
        for source_id in self.source_ids:
            self._data_cache[source_id] = self.recorder._query_source(
                source_id, self.start_time, self.end_time
            )

    def play(self) -> Iterator[Dict[str, Any]]:
        """回放数据（生成器）"""
        self.is_playing = True

        # 合并所有数据并排序
        all_points = []
        for source_id, data in self._data_cache.items():
            all_points.extend(data)
        all_points.sort(key=lambda d: d.timestamp)

        for point in all_points:
            if not self.is_playing:
                break

            self.current_time = point.timestamp

            yield {
                "source_id": point.source_id,
                "value": point.value,
                "timestamp": point.timestamp.isoformat(),
                "quality": point.quality,
                "playback_position": (
                    (point.timestamp - self.start_time).total_seconds() /
                    (self.end_time - self.start_time).total_seconds()
                )
            }

    def pause(self):
        """暂停回放"""
        self.is_playing = False

    def seek(self, position: float):
        """跳转到指定位置（0-1）"""
        duration = (self.end_time - self.start_time).total_seconds()
        self.current_time = self.start_time + timedelta(seconds=duration * position)

    def set_speed(self, speed: float):
        """设置回放速度"""
        self.speed = max(0.1, min(speed, 100.0))
