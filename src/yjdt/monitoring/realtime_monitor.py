# -*- coding: utf-8 -*-
"""
实时监控系统 - 全要素运行态势感知
Real-time Monitoring System - Full-Element Operational Awareness

功能：
- 多源数据采集（传感器、PLC、DCS）
- 信号质量评估与坏点剔除
- 实时数据处理与特征提取
- 运行状态综合评估
- 多级别监控点管理
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime
import threading
import queue
from collections import deque


class SignalQuality(Enum):
    """信号质量等级"""
    EXCELLENT = "excellent"       # 优秀 (误差<0.1%)
    GOOD = "good"                 # 良好 (误差<0.5%)
    ACCEPTABLE = "acceptable"     # 可接受 (误差<1%)
    DEGRADED = "degraded"         # 降级 (误差<5%)
    BAD = "bad"                   # 坏点 (误差>5%或超时)
    UNKNOWN = "unknown"           # 未知


class MonitoringStatus(Enum):
    """监控状态"""
    NORMAL = "normal"             # 正常
    WARNING = "warning"           # 预警
    ALARM = "alarm"               # 报警
    CRITICAL = "critical"         # 危急
    FAULT = "fault"               # 故障
    MAINTENANCE = "maintenance"   # 维护中
    OFFLINE = "offline"           # 离线


@dataclass
class MonitoringPoint:
    """监控点定义"""
    point_id: str                           # 点位ID
    name: str                               # 名称
    description: str                        # 描述
    unit: str                               # 单位
    data_type: str = "float"                # 数据类型
    scan_rate: float = 1.0                  # 采集周期(秒)

    # 量程与限值
    range_min: float = 0.0                  # 量程下限
    range_max: float = 100.0                # 量程上限
    alarm_hh: Optional[float] = None        # 高高报警
    alarm_h: Optional[float] = None         # 高报警
    alarm_l: Optional[float] = None         # 低报警
    alarm_ll: Optional[float] = None        # 低低报警

    # 变化率限值
    rate_limit: Optional[float] = None      # 变化率限值
    rate_alarm: Optional[float] = None      # 变化率报警

    # 信号处理
    deadband: float = 0.1                   # 死区(%)
    filter_constant: float = 0.0            # 滤波常数
    bad_value_timeout: float = 10.0         # 坏点超时(秒)

    # 当前状态
    current_value: float = 0.0
    last_update: Optional[datetime] = None
    quality: SignalQuality = SignalQuality.UNKNOWN
    status: MonitoringStatus = MonitoringStatus.OFFLINE


@dataclass
class DataAcquisition:
    """数据采集配置"""
    source_type: str                        # 数据源类型
    connection_string: str                  # 连接字符串
    protocol: str = "modbus"                # 协议
    retry_count: int = 3                    # 重试次数
    timeout: float = 5.0                    # 超时时间(秒)
    buffer_size: int = 1000                 # 缓冲区大小
    compression: bool = True                # 启用压缩


class RealtimeMonitor:
    """
    实时监控系统

    功能：
    - 多源数据采集与同步
    - 信号质量实时评估
    - 多级报警触发
    - 趋势数据缓存
    - 状态综合评估
    """

    def __init__(self):
        self.monitoring_points: Dict[str, MonitoringPoint] = {}
        self.data_sources: Dict[str, DataAcquisition] = {}
        self.data_buffer: Dict[str, deque] = {}
        self.event_handlers: List[Callable] = []
        self.is_running = False
        self._lock = threading.Lock()
        self._data_queue = queue.Queue()

        # 统计信息
        self.stats = {
            "total_points": 0,
            "online_points": 0,
            "alarm_count": 0,
            "bad_quality_count": 0,
            "data_rate": 0.0,
            "last_scan_time": None,
        }

        # 初始化标准监控点
        self._initialize_standard_points()

    def _initialize_standard_points(self):
        """初始化水电站标准监控点"""
        standard_points = [
            # 水力系统监控点
            MonitoringPoint(
                point_id="HYD_001",
                name="上游水位",
                description="水库上游水位测量",
                unit="m",
                range_min=2000, range_max=2200,
                alarm_h=2180, alarm_hh=2190,
                alarm_l=2050, alarm_ll=2030,
                scan_rate=1.0
            ),
            MonitoringPoint(
                point_id="HYD_002",
                name="下游水位",
                description="尾水下游水位测量",
                unit="m",
                range_min=1500, range_max=1600,
                alarm_h=1580, alarm_hh=1590,
                scan_rate=1.0
            ),
            MonitoringPoint(
                point_id="HYD_003",
                name="引水流量",
                description="引水隧洞流量测量",
                unit="m³/s",
                range_min=0, range_max=300,
                alarm_h=280, alarm_hh=290,
                rate_limit=50, rate_alarm=100,
                scan_rate=0.5
            ),
            MonitoringPoint(
                point_id="HYD_004",
                name="蜗壳压力",
                description="水轮机蜗壳进口压力",
                unit="MPa",
                range_min=0, range_max=6.0,
                alarm_h=5.5, alarm_hh=5.8,
                alarm_l=3.0, alarm_ll=2.5,
                scan_rate=0.1
            ),
            MonitoringPoint(
                point_id="HYD_005",
                name="调压室水位",
                description="调压室水位波动",
                unit="m",
                range_min=2050, range_max=2150,
                alarm_h=2140, alarm_hh=2145,
                alarm_l=2060, alarm_ll=2055,
                rate_limit=5, rate_alarm=10,
                scan_rate=0.2
            ),

            # 水轮机监控点
            MonitoringPoint(
                point_id="TRB_001",
                name="机组转速",
                description="水轮发电机转速",
                unit="rpm",
                range_min=0, range_max=150,
                alarm_h=110, alarm_hh=120,
                alarm_l=90, alarm_ll=80,
                rate_limit=5, rate_alarm=20,
                scan_rate=0.02
            ),
            MonitoringPoint(
                point_id="TRB_002",
                name="导叶开度",
                description="导水叶开度反馈",
                unit="%",
                range_min=0, range_max=100,
                rate_limit=10, rate_alarm=30,
                scan_rate=0.02
            ),
            MonitoringPoint(
                point_id="TRB_003",
                name="水轮机功率",
                description="水轮机输出功率",
                unit="MW",
                range_min=0, range_max=1100,
                alarm_h=1050, alarm_hh=1080,
                scan_rate=0.1
            ),
            MonitoringPoint(
                point_id="TRB_004",
                name="推力轴承温度",
                description="推力轴承瓦温",
                unit="℃",
                range_min=20, range_max=100,
                alarm_h=75, alarm_hh=85,
                rate_limit=2, rate_alarm=5,
                scan_rate=1.0
            ),
            MonitoringPoint(
                point_id="TRB_005",
                name="上导轴承振动",
                description="上导轴承振动幅值",
                unit="μm",
                range_min=0, range_max=500,
                alarm_h=250, alarm_hh=350,
                scan_rate=0.01
            ),

            # 发电机监控点
            MonitoringPoint(
                point_id="GEN_001",
                name="有功功率",
                description="发电机有功功率输出",
                unit="MW",
                range_min=-100, range_max=1100,
                alarm_h=1050, alarm_hh=1080,
                scan_rate=0.1
            ),
            MonitoringPoint(
                point_id="GEN_002",
                name="无功功率",
                description="发电机无功功率输出",
                unit="Mvar",
                range_min=-500, range_max=500,
                alarm_h=400, alarm_hh=450,
                alarm_l=-400, alarm_ll=-450,
                scan_rate=0.1
            ),
            MonitoringPoint(
                point_id="GEN_003",
                name="定子电流",
                description="定子绕组电流",
                unit="kA",
                range_min=0, range_max=25,
                alarm_h=22, alarm_hh=24,
                scan_rate=0.1
            ),
            MonitoringPoint(
                point_id="GEN_004",
                name="定子电压",
                description="定子端电压",
                unit="kV",
                range_min=15, range_max=25,
                alarm_h=22, alarm_hh=23,
                alarm_l=18, alarm_ll=17,
                scan_rate=0.1
            ),
            MonitoringPoint(
                point_id="GEN_005",
                name="定子温度",
                description="定子绕组温度",
                unit="℃",
                range_min=20, range_max=150,
                alarm_h=120, alarm_hh=135,
                rate_limit=3, rate_alarm=10,
                scan_rate=1.0
            ),
            MonitoringPoint(
                point_id="GEN_006",
                name="励磁电流",
                description="励磁绕组电流",
                unit="A",
                range_min=0, range_max=5000,
                alarm_h=4500, alarm_hh=4800,
                scan_rate=0.1
            ),

            # 电网监控点
            MonitoringPoint(
                point_id="GRID_001",
                name="系统频率",
                description="电网系统频率",
                unit="Hz",
                range_min=49.0, range_max=51.0,
                alarm_h=50.2, alarm_hh=50.5,
                alarm_l=49.8, alarm_ll=49.5,
                rate_limit=0.5, rate_alarm=1.0,
                scan_rate=0.02
            ),
            MonitoringPoint(
                point_id="GRID_002",
                name="母线电压",
                description="500kV母线电压",
                unit="kV",
                range_min=475, range_max=525,
                alarm_h=515, alarm_hh=520,
                alarm_l=485, alarm_ll=480,
                scan_rate=0.1
            ),

            # 环境监控点
            MonitoringPoint(
                point_id="ENV_001",
                name="环境温度",
                description="厂房环境温度",
                unit="℃",
                range_min=-10, range_max=50,
                alarm_h=40, alarm_hh=45,
                alarm_l=5, alarm_ll=0,
                scan_rate=10.0
            ),
            MonitoringPoint(
                point_id="ENV_002",
                name="地震烈度",
                description="地震监测烈度",
                unit="度",
                range_min=0, range_max=12,
                alarm_h=5, alarm_hh=7,
                scan_rate=0.01
            ),
        ]

        for point in standard_points:
            self.add_monitoring_point(point)

    def add_monitoring_point(self, point: MonitoringPoint):
        """添加监控点"""
        with self._lock:
            self.monitoring_points[point.point_id] = point
            self.data_buffer[point.point_id] = deque(maxlen=3600)  # 1小时趋势
            self.stats["total_points"] = len(self.monitoring_points)

    def remove_monitoring_point(self, point_id: str):
        """移除监控点"""
        with self._lock:
            if point_id in self.monitoring_points:
                del self.monitoring_points[point_id]
                del self.data_buffer[point_id]
                self.stats["total_points"] = len(self.monitoring_points)

    def update_value(self, point_id: str, value: float,
                     timestamp: Optional[datetime] = None,
                     quality: SignalQuality = SignalQuality.GOOD) -> Dict[str, Any]:
        """
        更新监控点数值

        Returns:
            包含报警和状态变化的字典
        """
        if point_id not in self.monitoring_points:
            return {"error": f"Point {point_id} not found"}

        timestamp = timestamp or datetime.now()
        point = self.monitoring_points[point_id]
        old_value = point.current_value
        old_status = point.status

        # 更新数值
        point.current_value = value
        point.last_update = timestamp
        point.quality = quality

        # 记录趋势数据
        self.data_buffer[point_id].append({
            "timestamp": timestamp,
            "value": value,
            "quality": quality
        })

        # 评估状态
        events = []
        point.status = self._evaluate_status(point, old_value, events)

        # 触发事件
        if point.status != old_status:
            events.append({
                "type": "status_change",
                "point_id": point_id,
                "old_status": old_status.value,
                "new_status": point.status.value,
                "timestamp": timestamp
            })

        # 调用事件处理器
        for event in events:
            for handler in self.event_handlers:
                try:
                    handler(event)
                except Exception as e:
                    pass  # 忽略处理器错误

        return {
            "point_id": point_id,
            "value": value,
            "status": point.status.value,
            "quality": quality.value,
            "events": events
        }

    def _evaluate_status(self, point: MonitoringPoint,
                         old_value: float,
                         events: List[Dict]) -> MonitoringStatus:
        """评估监控点状态"""
        value = point.current_value

        # 检查信号质量
        if point.quality == SignalQuality.BAD:
            events.append({
                "type": "bad_quality",
                "point_id": point.point_id,
                "message": f"信号质量差: {point.name}"
            })
            return MonitoringStatus.FAULT

        # 检查高高报警
        if point.alarm_hh is not None and value >= point.alarm_hh:
            events.append({
                "type": "alarm",
                "level": "HH",
                "point_id": point.point_id,
                "value": value,
                "limit": point.alarm_hh,
                "message": f"{point.name} 高高报警: {value:.2f} >= {point.alarm_hh}"
            })
            return MonitoringStatus.CRITICAL

        # 检查低低报警
        if point.alarm_ll is not None and value <= point.alarm_ll:
            events.append({
                "type": "alarm",
                "level": "LL",
                "point_id": point.point_id,
                "value": value,
                "limit": point.alarm_ll,
                "message": f"{point.name} 低低报警: {value:.2f} <= {point.alarm_ll}"
            })
            return MonitoringStatus.CRITICAL

        # 检查高报警
        if point.alarm_h is not None and value >= point.alarm_h:
            events.append({
                "type": "alarm",
                "level": "H",
                "point_id": point.point_id,
                "value": value,
                "limit": point.alarm_h,
                "message": f"{point.name} 高报警: {value:.2f} >= {point.alarm_h}"
            })
            return MonitoringStatus.ALARM

        # 检查低报警
        if point.alarm_l is not None and value <= point.alarm_l:
            events.append({
                "type": "alarm",
                "level": "L",
                "point_id": point.point_id,
                "value": value,
                "limit": point.alarm_l,
                "message": f"{point.name} 低报警: {value:.2f} <= {point.alarm_l}"
            })
            return MonitoringStatus.ALARM

        # 检查变化率
        if point.rate_alarm is not None and old_value != 0:
            rate = abs(value - old_value)
            if rate >= point.rate_alarm:
                events.append({
                    "type": "rate_alarm",
                    "point_id": point.point_id,
                    "rate": rate,
                    "limit": point.rate_alarm,
                    "message": f"{point.name} 变化率报警: {rate:.2f} >= {point.rate_alarm}"
                })
                return MonitoringStatus.WARNING

        # 检查趋势预警
        if point.alarm_h is not None and value >= point.alarm_h * 0.9:
            events.append({
                "type": "trend_warning",
                "point_id": point.point_id,
                "value": value,
                "message": f"{point.name} 接近高限: {value:.2f}"
            })
            return MonitoringStatus.WARNING

        if point.alarm_l is not None and value <= point.alarm_l * 1.1:
            events.append({
                "type": "trend_warning",
                "point_id": point.point_id,
                "value": value,
                "message": f"{point.name} 接近低限: {value:.2f}"
            })
            return MonitoringStatus.WARNING

        return MonitoringStatus.NORMAL

    def batch_update(self, updates: Dict[str, Tuple[float, SignalQuality]]) -> Dict[str, Any]:
        """批量更新多个监控点"""
        results = {}
        timestamp = datetime.now()

        for point_id, (value, quality) in updates.items():
            results[point_id] = self.update_value(
                point_id, value, timestamp, quality
            )

        # 更新统计
        self._update_stats()

        return results

    def _update_stats(self):
        """更新统计信息"""
        online_count = 0
        alarm_count = 0
        bad_quality_count = 0

        for point in self.monitoring_points.values():
            if point.status != MonitoringStatus.OFFLINE:
                online_count += 1
            if point.status in [MonitoringStatus.ALARM, MonitoringStatus.CRITICAL]:
                alarm_count += 1
            if point.quality == SignalQuality.BAD:
                bad_quality_count += 1

        self.stats["online_points"] = online_count
        self.stats["alarm_count"] = alarm_count
        self.stats["bad_quality_count"] = bad_quality_count
        self.stats["last_scan_time"] = datetime.now()

    def get_point_status(self, point_id: str) -> Optional[Dict[str, Any]]:
        """获取监控点状态"""
        if point_id not in self.monitoring_points:
            return None

        point = self.monitoring_points[point_id]
        trend_data = list(self.data_buffer[point_id])

        return {
            "point_id": point.point_id,
            "name": point.name,
            "value": point.current_value,
            "unit": point.unit,
            "status": point.status.value,
            "quality": point.quality.value,
            "last_update": point.last_update.isoformat() if point.last_update else None,
            "limits": {
                "alarm_hh": point.alarm_hh,
                "alarm_h": point.alarm_h,
                "alarm_l": point.alarm_l,
                "alarm_ll": point.alarm_ll,
            },
            "trend_count": len(trend_data)
        }

    def get_all_status(self) -> Dict[str, Any]:
        """获取所有监控点状态"""
        return {
            "stats": self.stats.copy(),
            "points": {
                pid: self.get_point_status(pid)
                for pid in self.monitoring_points
            }
        }

    def get_alarms(self) -> List[Dict[str, Any]]:
        """获取当前所有报警"""
        alarms = []
        for point in self.monitoring_points.values():
            if point.status in [MonitoringStatus.ALARM, MonitoringStatus.CRITICAL,
                                MonitoringStatus.WARNING]:
                alarms.append({
                    "point_id": point.point_id,
                    "name": point.name,
                    "value": point.current_value,
                    "unit": point.unit,
                    "status": point.status.value,
                    "timestamp": point.last_update.isoformat() if point.last_update else None
                })
        return alarms

    def get_trend_data(self, point_id: str,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """获取趋势数据"""
        if point_id not in self.data_buffer:
            return []

        data = list(self.data_buffer[point_id])

        # 时间过滤
        if start_time:
            data = [d for d in data if d["timestamp"] >= start_time]
        if end_time:
            data = [d for d in data if d["timestamp"] <= end_time]

        return data

    def register_event_handler(self, handler: Callable):
        """注册事件处理器"""
        self.event_handlers.append(handler)

    def unregister_event_handler(self, handler: Callable):
        """注销事件处理器"""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)

    def simulate_normal_operation(self, duration: float = 10.0, dt: float = 0.1):
        """模拟正常运行数据"""
        np.random.seed(42)
        steps = int(duration / dt)

        # 基准值
        base_values = {
            "HYD_001": 2100,  # 上游水位
            "HYD_002": 1550,  # 下游水位
            "HYD_003": 220,   # 引水流量
            "HYD_004": 4.5,   # 蜗壳压力
            "HYD_005": 2100,  # 调压室水位
            "TRB_001": 100,   # 转速
            "TRB_002": 80,    # 导叶开度
            "TRB_003": 800,   # 水轮机功率
            "TRB_004": 55,    # 推力轴承温度
            "TRB_005": 100,   # 上导轴承振动
            "GEN_001": 800,   # 有功功率
            "GEN_002": 100,   # 无功功率
            "GEN_003": 15,    # 定子电流
            "GEN_004": 20,    # 定子电压
            "GEN_005": 85,    # 定子温度
            "GEN_006": 2500,  # 励磁电流
            "GRID_001": 50.0, # 系统频率
            "GRID_002": 500,  # 母线电压
            "ENV_001": 25,    # 环境温度
            "ENV_002": 0,     # 地震烈度
        }

        # 噪声幅度
        noise_levels = {
            "HYD_001": 0.5,
            "HYD_002": 0.3,
            "HYD_003": 5.0,
            "HYD_004": 0.1,
            "HYD_005": 2.0,
            "TRB_001": 0.2,
            "TRB_002": 0.5,
            "TRB_003": 10,
            "TRB_004": 1.0,
            "TRB_005": 20,
            "GEN_001": 10,
            "GEN_002": 5,
            "GEN_003": 0.5,
            "GEN_004": 0.2,
            "GEN_005": 1.0,
            "GEN_006": 50,
            "GRID_001": 0.02,
            "GRID_002": 2,
            "ENV_001": 0.5,
            "ENV_002": 0.1,
        }

        results = []
        for step in range(steps):
            updates = {}
            for point_id in base_values:
                if point_id in self.monitoring_points:
                    base = base_values[point_id]
                    noise = noise_levels.get(point_id, 1.0)
                    value = base + np.random.normal(0, noise)
                    updates[point_id] = (value, SignalQuality.GOOD)

            result = self.batch_update(updates)
            results.append(result)

        return results
