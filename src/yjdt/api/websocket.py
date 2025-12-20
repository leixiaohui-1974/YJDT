# -*- coding: utf-8 -*-
"""
WebSocket实时数据推送 - WebSocket Real-time Data Streaming

功能：
- 实时数据推送
- 多频道订阅
- 连接管理
- 心跳检测
- 数据过滤
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    DATA = "data"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    INFO = "info"
    ALARM = "alarm"
    EVENT = "event"


class Channel(Enum):
    """数据频道"""
    REALTIME = "realtime"           # 实时数据
    SIMULATION = "simulation"       # 仿真数据
    ALARMS = "alarms"               # 告警
    EVENTS = "events"               # 事件
    CONTROL = "control"             # 控制指令
    DIAGNOSIS = "diagnosis"         # 诊断结果


@dataclass
class WebSocketConnection:
    """WebSocket连接"""
    connection_id: str
    websocket: Any
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_alive(self, timeout: float = 60.0) -> bool:
        """检查连接是否存活"""
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < timeout


class WebSocketManager:
    """
    WebSocket连接管理器

    管理所有WebSocket连接，处理订阅和消息广播
    """

    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._channel_subscribers: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

        # 心跳配置
        self._heartbeat_interval = 30  # 秒
        self._connection_timeout = 60  # 秒

        # 后台任务
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: Any, metadata: Dict = None) -> str:
        """
        处理新连接

        Args:
            websocket: WebSocket连接对象
            metadata: 连接元数据

        Returns:
            连接ID
        """
        connection_id = f"ws_{uuid.uuid4().hex[:12]}"

        connection = WebSocketConnection(
            connection_id=connection_id,
            websocket=websocket,
            metadata=metadata or {},
        )

        async with self._lock:
            self._connections[connection_id] = connection

        logger.info(f"WebSocket connected: {connection_id}")

        # 发送欢迎消息
        await self._send_to_connection(connection_id, {
            "type": MessageType.INFO.value,
            "message": "Connected to YJDT WebSocket Server",
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat(),
        })

        return connection_id

    async def disconnect(self, connection_id: str):
        """
        处理断开连接

        Args:
            connection_id: 连接ID
        """
        async with self._lock:
            if connection_id in self._connections:
                connection = self._connections[connection_id]

                # 从所有频道取消订阅
                for channel in connection.subscriptions:
                    if channel in self._channel_subscribers:
                        self._channel_subscribers[channel].discard(connection_id)

                del self._connections[connection_id]
                logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe(self, connection_id: str, channel: str) -> bool:
        """
        订阅频道

        Args:
            connection_id: 连接ID
            channel: 频道名

        Returns:
            是否成功
        """
        async with self._lock:
            if connection_id not in self._connections:
                return False

            connection = self._connections[connection_id]
            connection.subscriptions.add(channel)

            if channel not in self._channel_subscribers:
                self._channel_subscribers[channel] = set()
            self._channel_subscribers[channel].add(connection_id)

        logger.debug(f"Connection {connection_id} subscribed to {channel}")
        return True

    async def unsubscribe(self, connection_id: str, channel: str) -> bool:
        """
        取消订阅

        Args:
            connection_id: 连接ID
            channel: 频道名

        Returns:
            是否成功
        """
        async with self._lock:
            if connection_id not in self._connections:
                return False

            connection = self._connections[connection_id]
            connection.subscriptions.discard(channel)

            if channel in self._channel_subscribers:
                self._channel_subscribers[channel].discard(connection_id)

        return True

    async def broadcast(self, channel: str, data: Any):
        """
        广播消息到频道

        Args:
            channel: 频道名
            data: 消息数据
        """
        message = {
            "type": MessageType.DATA.value,
            "channel": channel,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        subscribers = self._channel_subscribers.get(channel, set())
        tasks = [
            self._send_to_connection(conn_id, message)
            for conn_id in subscribers
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_connection(self, connection_id: str, data: Any):
        """发送消息到指定连接"""
        await self._send_to_connection(connection_id, data)

    async def _send_to_connection(self, connection_id: str, data: Any):
        """内部发送方法"""
        connection = self._connections.get(connection_id)
        if not connection:
            return

        try:
            if hasattr(connection.websocket, 'send_json'):
                await connection.websocket.send_json(data)
            elif hasattr(connection.websocket, 'send_text'):
                await connection.websocket.send_text(json.dumps(data))
            elif hasattr(connection.websocket, 'send'):
                await connection.websocket.send(json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to send to {connection_id}: {e}")
            await self.disconnect(connection_id)

    async def handle_message(self, connection_id: str, message: Dict):
        """
        处理收到的消息

        Args:
            connection_id: 连接ID
            message: 消息内容
        """
        msg_type = message.get("type", "")

        if msg_type == "subscribe":
            channel = message.get("channel", "")
            await self.subscribe(connection_id, channel)
            await self._send_to_connection(connection_id, {
                "type": MessageType.INFO.value,
                "message": f"Subscribed to {channel}",
            })

        elif msg_type == "unsubscribe":
            channel = message.get("channel", "")
            await self.unsubscribe(connection_id, channel)
            await self._send_to_connection(connection_id, {
                "type": MessageType.INFO.value,
                "message": f"Unsubscribed from {channel}",
            })

        elif msg_type == "heartbeat":
            if connection_id in self._connections:
                self._connections[connection_id].last_heartbeat = datetime.now()
            await self._send_to_connection(connection_id, {
                "type": MessageType.HEARTBEAT.value,
                "timestamp": datetime.now().isoformat(),
            })

    async def start_heartbeat(self):
        """启动心跳检测"""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self):
        """停止心跳检测"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                # 检查超时连接
                dead_connections = []
                async with self._lock:
                    for conn_id, conn in self._connections.items():
                        if not conn.is_alive(self._connection_timeout):
                            dead_connections.append(conn_id)

                # 断开超时连接
                for conn_id in dead_connections:
                    logger.warning(f"Connection {conn_id} timed out")
                    await self.disconnect(conn_id)

                # 发送心跳
                for conn_id in list(self._connections.keys()):
                    await self._send_to_connection(conn_id, {
                        "type": MessageType.HEARTBEAT.value,
                        "timestamp": datetime.now().isoformat(),
                    })

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            await asyncio.sleep(self._heartbeat_interval)

    def get_connection_count(self) -> int:
        """获取连接数"""
        return len(self._connections)

    def get_channel_subscribers(self, channel: str) -> int:
        """获取频道订阅数"""
        return len(self._channel_subscribers.get(channel, set()))

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "total_connections": len(self._connections),
            "channels": {
                channel: len(subscribers)
                for channel, subscribers in self._channel_subscribers.items()
            },
        }


class RealtimeDataStreamer:
    """
    实时数据流推送器

    周期性推送实时运行数据
    """

    def __init__(self, ws_manager: WebSocketManager = None):
        self.ws_manager = ws_manager or WebSocketManager()

        # 数据源
        self._data_sources: Dict[str, Callable] = {}

        # 推送配置
        self._push_interval = 1.0  # 秒
        self._running = False
        self._push_task: Optional[asyncio.Task] = None

        # 注册默认数据源
        self._register_default_sources()

    def _register_default_sources(self):
        """注册默认数据源"""

        def generate_realtime_data() -> Dict:
            """生成实时运行数据"""
            return {
                "power": float(np.random.normal(180, 5)),
                "frequency": float(np.random.normal(50, 0.01)),
                "voltage": float(np.random.normal(15.75, 0.1)),
                "head": float(np.random.normal(150, 2)),
                "flow": float(np.random.normal(130, 5)),
                "guide_vane_opening": float(np.random.uniform(70, 80)),
                "turbine_speed": float(np.random.normal(150, 0.5)),
                "upstream_level": float(np.random.normal(1850, 0.5)),
                "downstream_level": float(np.random.normal(1700, 0.3)),
                "bearing_temperature": float(np.random.normal(45, 2)),
                "vibration_x": float(np.random.normal(0.5, 0.1)),
                "vibration_y": float(np.random.normal(0.4, 0.1)),
            }

        def generate_simulation_data() -> Dict:
            """生成仿真数据"""
            return {
                "simulation_time": time.time() % 1000,
                "step": int(time.time() * 100) % 100000,
                "hydraulic_pressure": float(np.random.normal(1500000, 10000)),
                "water_hammer_amplitude": float(np.random.exponential(0.1)),
                "governor_output": float(np.random.uniform(0.3, 0.8)),
            }

        self._data_sources[Channel.REALTIME.value] = generate_realtime_data
        self._data_sources[Channel.SIMULATION.value] = generate_simulation_data

    def register_data_source(self, channel: str, source: Callable):
        """注册数据源"""
        self._data_sources[channel] = source

    async def start(self, interval: float = 1.0):
        """
        启动数据推送

        Args:
            interval: 推送间隔（秒）
        """
        self._push_interval = interval
        self._running = True

        # 启动心跳
        await self.ws_manager.start_heartbeat()

        # 启动数据推送
        self._push_task = asyncio.create_task(self._push_loop())

        logger.info(f"Realtime data streamer started, interval={interval}s")

    async def stop(self):
        """停止数据推送"""
        self._running = False

        if self._push_task:
            self._push_task.cancel()

        await self.ws_manager.stop_heartbeat()

        logger.info("Realtime data streamer stopped")

    async def _push_loop(self):
        """数据推送循环"""
        while self._running:
            try:
                # 推送各频道数据
                for channel, source in self._data_sources.items():
                    subscribers = self.ws_manager.get_channel_subscribers(channel)
                    if subscribers > 0:
                        try:
                            data = source()
                            await self.ws_manager.broadcast(channel, data)
                        except Exception as e:
                            logger.error(f"Data source error for {channel}: {e}")

            except Exception as e:
                logger.error(f"Push loop error: {e}")

            await asyncio.sleep(self._push_interval)

    async def push_alarm(self, alarm: Dict):
        """推送告警"""
        await self.ws_manager.broadcast(Channel.ALARMS.value, alarm)

    async def push_event(self, event: Dict):
        """推送事件"""
        await self.ws_manager.broadcast(Channel.EVENTS.value, event)

    async def push_simulation_update(self, simulation_id: str, data: Dict):
        """推送仿真更新"""
        await self.ws_manager.broadcast(
            f"simulation_{simulation_id}",
            data
        )

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "running": self._running,
            "push_interval": self._push_interval,
            "data_sources": list(self._data_sources.keys()),
            "ws_manager": self.ws_manager.get_status(),
        }


def create_websocket_endpoint(app, ws_manager: WebSocketManager = None):
    """
    创建WebSocket端点

    Args:
        app: FastAPI应用
        ws_manager: WebSocket管理器
    """
    try:
        from fastapi import WebSocket, WebSocketDisconnect
    except ImportError:
        logger.warning("FastAPI not installed, WebSocket endpoint not created")
        return

    manager = ws_manager or WebSocketManager()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket端点"""
        await websocket.accept()
        connection_id = await manager.connect(websocket)

        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理消息
                await manager.handle_message(connection_id, message)

        except WebSocketDisconnect:
            await manager.disconnect(connection_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await manager.disconnect(connection_id)

    @app.websocket("/ws/{channel}")
    async def websocket_channel_endpoint(websocket: WebSocket, channel: str):
        """频道专用WebSocket端点"""
        await websocket.accept()
        connection_id = await manager.connect(websocket)

        # 自动订阅频道
        await manager.subscribe(connection_id, channel)

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                await manager.handle_message(connection_id, message)

        except WebSocketDisconnect:
            await manager.disconnect(connection_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await manager.disconnect(connection_id)

    return manager
