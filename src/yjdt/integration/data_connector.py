# -*- coding: utf-8 -*-
"""
数据连接器 - Data Connector

功能：
- SCADA系统对接
- OPC-UA客户端
- 历史数据库连接
- 实时数据桥接
- 协议转换

支持的协议：
- OPC-UA
- Modbus TCP/RTU
- IEC 61850
- DNP3
- MQTT
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
import threading
import queue
import time
import logging
import struct
import socket

logger = logging.getLogger(__name__)


class ProtocolType(Enum):
    """通信协议类型"""
    OPC_UA = "opc_ua"
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    IEC61850 = "iec61850"
    DNP3 = "dnp3"
    MQTT = "mqtt"
    HTTP_REST = "http_rest"
    INTERNAL = "internal"


class DataQuality(Enum):
    """数据质量"""
    GOOD = "good"
    UNCERTAIN = "uncertain"
    BAD = "bad"
    NOT_AVAILABLE = "not_available"


@dataclass
class DataPoint:
    """数据点"""
    tag_name: str
    value: Any
    timestamp: datetime
    quality: DataQuality = DataQuality.GOOD
    unit: str = ""
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionConfig:
    """连接配置"""
    protocol: ProtocolType
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: float = 30.0
    retry_count: int = 3
    retry_interval: float = 5.0
    options: Dict[str, Any] = field(default_factory=dict)


class DataConnector:
    """
    数据连接器基类

    提供工业数据源的统一访问接口
    """

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._connected = False
        self._lock = threading.Lock()

        # 数据缓存
        self._cache: Dict[str, DataPoint] = {}
        self._cache_ttl = 5.0  # 缓存有效期（秒）

        # 订阅管理
        self._subscriptions: Dict[str, List[Callable]] = {}

        # 统计
        self._stats = {
            'read_count': 0,
            'write_count': 0,
            'error_count': 0,
            'last_error': None,
        }

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    def connect(self) -> bool:
        """建立连接"""
        raise NotImplementedError

    def disconnect(self):
        """断开连接"""
        self._connected = False

    def read(self, tag_name: str, use_cache: bool = True) -> Optional[DataPoint]:
        """
        读取数据点

        Args:
            tag_name: 标签名
            use_cache: 是否使用缓存

        Returns:
            数据点
        """
        if use_cache and tag_name in self._cache:
            cached = self._cache[tag_name]
            age = (datetime.now() - cached.timestamp).total_seconds()
            if age < self._cache_ttl:
                return cached

        data = self._read_impl(tag_name)
        if data:
            self._cache[tag_name] = data
            self._stats['read_count'] += 1
        return data

    def _read_impl(self, tag_name: str) -> Optional[DataPoint]:
        """读取实现（子类覆盖）"""
        raise NotImplementedError

    def read_multiple(self, tag_names: List[str]) -> Dict[str, DataPoint]:
        """批量读取"""
        results = {}
        for tag in tag_names:
            data = self.read(tag)
            if data:
                results[tag] = data
        return results

    def write(self, tag_name: str, value: Any) -> bool:
        """
        写入数据点

        Args:
            tag_name: 标签名
            value: 值

        Returns:
            是否成功
        """
        success = self._write_impl(tag_name, value)
        if success:
            self._stats['write_count'] += 1
        else:
            self._stats['error_count'] += 1
        return success

    def _write_impl(self, tag_name: str, value: Any) -> bool:
        """写入实现（子类覆盖）"""
        raise NotImplementedError

    def subscribe(self, tag_name: str, callback: Callable[[DataPoint], None],
                  interval: float = 1.0):
        """
        订阅数据变化

        Args:
            tag_name: 标签名
            callback: 回调函数
            interval: 采样间隔（秒）
        """
        if tag_name not in self._subscriptions:
            self._subscriptions[tag_name] = []
        self._subscriptions[tag_name].append(callback)

    def unsubscribe(self, tag_name: str, callback: Callable = None):
        """取消订阅"""
        if tag_name in self._subscriptions:
            if callback:
                self._subscriptions[tag_name].remove(callback)
            else:
                del self._subscriptions[tag_name]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()


class SCADAConnector(DataConnector):
    """
    SCADA系统连接器

    连接到水电站SCADA系统，获取实时运行数据
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)

        # 标签映射
        self._tag_mapping: Dict[str, str] = {}

        # 数据点定义
        self._point_definitions: Dict[str, Dict] = {}

        # 轮询线程
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_interval = 1.0
        self._stop_event = threading.Event()

    def set_tag_mapping(self, mapping: Dict[str, str]):
        """
        设置标签映射

        Args:
            mapping: {内部标签: SCADA标签}
        """
        self._tag_mapping = mapping

    def add_point_definition(self, internal_tag: str, scada_tag: str,
                             data_type: str, unit: str = "",
                             scale: float = 1.0, offset: float = 0.0):
        """添加数据点定义"""
        self._point_definitions[internal_tag] = {
            'scada_tag': scada_tag,
            'data_type': data_type,
            'unit': unit,
            'scale': scale,
            'offset': offset,
        }
        self._tag_mapping[internal_tag] = scada_tag

    def connect(self) -> bool:
        """连接到SCADA"""
        try:
            # 这里是模拟连接
            # 实际实现需要根据具体SCADA系统的API
            logger.info(f"Connecting to SCADA at {self.config.host}:{self.config.port}")

            # 模拟连接延迟
            time.sleep(0.5)

            self._connected = True
            logger.info("SCADA connection established")

            # 启动轮询线程
            self._start_polling()

            return True
        except Exception as e:
            logger.error(f"SCADA connection failed: {e}")
            self._stats['last_error'] = str(e)
            return False

    def disconnect(self):
        """断开SCADA连接"""
        self._stop_event.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=5.0)
        self._connected = False
        logger.info("SCADA disconnected")

    def _read_impl(self, tag_name: str) -> Optional[DataPoint]:
        """从SCADA读取数据"""
        if not self._connected:
            return None

        scada_tag = self._tag_mapping.get(tag_name, tag_name)
        definition = self._point_definitions.get(tag_name, {})

        try:
            # 模拟数据读取
            # 实际实现需要调用SCADA API
            raw_value = self._simulate_read(scada_tag)

            # 应用缩放
            scale = definition.get('scale', 1.0)
            offset = definition.get('offset', 0.0)
            value = raw_value * scale + offset

            return DataPoint(
                tag_name=tag_name,
                value=value,
                timestamp=datetime.now(),
                quality=DataQuality.GOOD,
                unit=definition.get('unit', ''),
                source='scada',
            )
        except Exception as e:
            logger.error(f"Read error for {tag_name}: {e}")
            self._stats['error_count'] += 1
            return None

    def _write_impl(self, tag_name: str, value: Any) -> bool:
        """写入SCADA"""
        if not self._connected:
            return False

        scada_tag = self._tag_mapping.get(tag_name, tag_name)
        definition = self._point_definitions.get(tag_name, {})

        try:
            # 反向缩放
            scale = definition.get('scale', 1.0)
            offset = definition.get('offset', 0.0)
            raw_value = (value - offset) / scale

            # 模拟写入
            logger.info(f"Write to SCADA: {scada_tag} = {raw_value}")
            return True
        except Exception as e:
            logger.error(f"Write error for {tag_name}: {e}")
            return False

    def _simulate_read(self, scada_tag: str) -> float:
        """模拟SCADA数据读取"""
        # 生成模拟数据
        base_values = {
            'water_level': 1850.0,
            'flow_rate': 150.0,
            'power': 180.0,
            'frequency': 50.0,
            'voltage': 15.75,
            'temperature': 45.0,
        }

        for key, base in base_values.items():
            if key in scada_tag.lower():
                noise = np.random.normal(0, base * 0.01)
                return base + noise

        return np.random.uniform(0, 100)

    def _start_polling(self):
        """启动轮询"""
        self._stop_event.clear()
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            name="SCADA-Poll"
        )
        self._poll_thread.daemon = True
        self._poll_thread.start()

    def _poll_loop(self):
        """轮询循环"""
        while not self._stop_event.is_set():
            for tag_name, callbacks in self._subscriptions.items():
                data = self.read(tag_name, use_cache=False)
                if data:
                    for callback in callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"Subscription callback error: {e}")

            self._stop_event.wait(self._poll_interval)


class HistorianConnector(DataConnector):
    """
    历史数据库连接器

    连接到历史数据服务器，查询历史运行数据
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)

        # 历史数据存储（模拟）
        self._historical_data: Dict[str, List[Tuple[datetime, float]]] = {}

    def connect(self) -> bool:
        """连接到历史数据库"""
        try:
            logger.info(f"Connecting to Historian at {self.config.host}:{self.config.port}")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Historian connection failed: {e}")
            return False

    def _read_impl(self, tag_name: str) -> Optional[DataPoint]:
        """读取最新值"""
        if tag_name in self._historical_data:
            data = self._historical_data[tag_name]
            if data:
                ts, value = data[-1]
                return DataPoint(
                    tag_name=tag_name,
                    value=value,
                    timestamp=ts,
                    quality=DataQuality.GOOD,
                    source='historian',
                )
        return None

    def _write_impl(self, tag_name: str, value: Any) -> bool:
        """写入历史数据"""
        if tag_name not in self._historical_data:
            self._historical_data[tag_name] = []
        self._historical_data[tag_name].append((datetime.now(), value))
        return True

    def query_history(self, tag_name: str, start_time: datetime,
                      end_time: datetime, interval: timedelta = None) -> List[DataPoint]:
        """
        查询历史数据

        Args:
            tag_name: 标签名
            start_time: 开始时间
            end_time: 结束时间
            interval: 采样间隔

        Returns:
            历史数据点列表
        """
        results = []

        if tag_name in self._historical_data:
            for ts, value in self._historical_data[tag_name]:
                if start_time <= ts <= end_time:
                    results.append(DataPoint(
                        tag_name=tag_name,
                        value=value,
                        timestamp=ts,
                        quality=DataQuality.GOOD,
                        source='historian',
                    ))

        # 如果需要重采样
        if interval and results:
            results = self._resample(results, interval)

        return results

    def _resample(self, data: List[DataPoint], interval: timedelta) -> List[DataPoint]:
        """重采样"""
        if not data:
            return []

        resampled = []
        current_time = data[0].timestamp
        end_time = data[-1].timestamp

        while current_time <= end_time:
            # 找最近的点
            closest = min(data, key=lambda x: abs((x.timestamp - current_time).total_seconds()))

            resampled.append(DataPoint(
                tag_name=closest.tag_name,
                value=closest.value,
                timestamp=current_time,
                quality=closest.quality,
                source=closest.source,
            ))

            current_time += interval

        return resampled

    def query_aggregated(self, tag_name: str, start_time: datetime,
                         end_time: datetime, aggregation: str = "avg") -> Dict[str, float]:
        """
        聚合查询

        Args:
            tag_name: 标签名
            start_time: 开始时间
            end_time: 结束时间
            aggregation: 聚合方式（avg, min, max, sum, count）

        Returns:
            聚合结果
        """
        data = self.query_history(tag_name, start_time, end_time)
        values = [d.value for d in data if isinstance(d.value, (int, float))]

        if not values:
            return {}

        result = {
            'tag': tag_name,
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'count': len(values),
        }

        if aggregation == "avg":
            result['value'] = np.mean(values)
        elif aggregation == "min":
            result['value'] = np.min(values)
        elif aggregation == "max":
            result['value'] = np.max(values)
        elif aggregation == "sum":
            result['value'] = np.sum(values)
        elif aggregation == "std":
            result['value'] = np.std(values)

        return result


class OPCUAClient(DataConnector):
    """
    OPC-UA客户端

    连接到OPC-UA服务器，读写过程数据
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)

        # 节点映射
        self._node_mapping: Dict[str, str] = {}

        # 安全配置
        self._security_mode = config.options.get('security_mode', 'None')
        self._security_policy = config.options.get('security_policy', 'None')

        # 会话
        self._session_id: Optional[str] = None

    def connect(self) -> bool:
        """连接到OPC-UA服务器"""
        try:
            endpoint = f"opc.tcp://{self.config.host}:{self.config.port}"
            logger.info(f"Connecting to OPC-UA server: {endpoint}")

            # 模拟连接过程
            # 实际实现需要使用 python-opcua 或 asyncua 库

            # 1. 发现端点
            # 2. 选择安全策略
            # 3. 建立安全通道
            # 4. 创建会话
            # 5. 激活会话

            self._session_id = f"session_{int(time.time())}"
            self._connected = True

            logger.info("OPC-UA connection established")
            return True
        except Exception as e:
            logger.error(f"OPC-UA connection failed: {e}")
            return False

    def set_node_mapping(self, mapping: Dict[str, str]):
        """
        设置节点映射

        Args:
            mapping: {标签名: OPC-UA NodeId}
        """
        self._node_mapping = mapping

    def _read_impl(self, tag_name: str) -> Optional[DataPoint]:
        """读取OPC-UA节点"""
        if not self._connected:
            return None

        node_id = self._node_mapping.get(tag_name, tag_name)

        try:
            # 模拟读取
            value = self._simulate_read_node(node_id)

            return DataPoint(
                tag_name=tag_name,
                value=value,
                timestamp=datetime.now(),
                quality=DataQuality.GOOD,
                source='opc-ua',
                metadata={'node_id': node_id},
            )
        except Exception as e:
            logger.error(f"OPC-UA read error: {e}")
            return None

    def _write_impl(self, tag_name: str, value: Any) -> bool:
        """写入OPC-UA节点"""
        if not self._connected:
            return False

        node_id = self._node_mapping.get(tag_name, tag_name)

        try:
            logger.info(f"Write to OPC-UA node {node_id}: {value}")
            return True
        except Exception as e:
            logger.error(f"OPC-UA write error: {e}")
            return False

    def _simulate_read_node(self, node_id: str) -> float:
        """模拟读取节点值"""
        return np.random.uniform(0, 100)

    def browse(self, parent_node: str = "i=85") -> List[Dict]:
        """
        浏览节点

        Args:
            parent_node: 父节点ID

        Returns:
            子节点列表
        """
        # 模拟节点浏览
        return [
            {'node_id': 'ns=2;i=1', 'name': 'WaterLevel', 'type': 'Float'},
            {'node_id': 'ns=2;i=2', 'name': 'FlowRate', 'type': 'Float'},
            {'node_id': 'ns=2;i=3', 'name': 'Power', 'type': 'Float'},
        ]

    def call_method(self, object_node: str, method_node: str,
                    arguments: List[Any] = None) -> Any:
        """
        调用方法

        Args:
            object_node: 对象节点ID
            method_node: 方法节点ID
            arguments: 参数列表

        Returns:
            方法返回值
        """
        logger.info(f"Call OPC-UA method: {method_node} on {object_node}")
        return None


class RealtimeDataBridge:
    """
    实时数据桥接器

    在仿真系统和实际设备之间桥接数据
    """

    def __init__(self):
        self._connectors: Dict[str, DataConnector] = {}
        self._data_queue = queue.Queue(maxsize=10000)

        # 数据映射
        self._input_mapping: Dict[str, Tuple[str, str]] = {}  # 仿真输入 -> (连接器, 标签)
        self._output_mapping: Dict[str, Tuple[str, str]] = {}  # 仿真输出 -> (连接器, 标签)

        # 数据处理
        self._input_filters: Dict[str, Callable] = {}
        self._output_filters: Dict[str, Callable] = {}

        # 状态
        self._running = False
        self._bridge_thread: Optional[threading.Thread] = None

    def add_connector(self, name: str, connector: DataConnector):
        """添加连接器"""
        self._connectors[name] = connector

    def map_input(self, sim_var: str, connector_name: str, tag_name: str,
                  filter_func: Callable = None):
        """
        映射输入（从外部到仿真）

        Args:
            sim_var: 仿真变量名
            connector_name: 连接器名
            tag_name: 标签名
            filter_func: 过滤/转换函数
        """
        self._input_mapping[sim_var] = (connector_name, tag_name)
        if filter_func:
            self._input_filters[sim_var] = filter_func

    def map_output(self, sim_var: str, connector_name: str, tag_name: str,
                   filter_func: Callable = None):
        """
        映射输出（从仿真到外部）

        Args:
            sim_var: 仿真变量名
            connector_name: 连接器名
            tag_name: 标签名
            filter_func: 过滤/转换函数
        """
        self._output_mapping[sim_var] = (connector_name, tag_name)
        if filter_func:
            self._output_filters[sim_var] = filter_func

    def start(self):
        """启动桥接"""
        self._running = True

        # 连接所有连接器
        for name, connector in self._connectors.items():
            if not connector.is_connected:
                connector.connect()

        self._bridge_thread = threading.Thread(
            target=self._bridge_loop,
            name="DataBridge"
        )
        self._bridge_thread.daemon = True
        self._bridge_thread.start()

        logger.info("Data bridge started")

    def stop(self):
        """停止桥接"""
        self._running = False
        if self._bridge_thread:
            self._bridge_thread.join(timeout=5.0)

        for connector in self._connectors.values():
            connector.disconnect()

        logger.info("Data bridge stopped")

    def _bridge_loop(self):
        """桥接循环"""
        while self._running:
            # 处理输入
            for sim_var, (conn_name, tag_name) in self._input_mapping.items():
                connector = self._connectors.get(conn_name)
                if connector and connector.is_connected:
                    data = connector.read(tag_name)
                    if data:
                        value = data.value
                        if sim_var in self._input_filters:
                            value = self._input_filters[sim_var](value)
                        self._data_queue.put(('input', sim_var, value))

            time.sleep(0.1)

    def get_input(self, sim_var: str) -> Optional[float]:
        """获取输入值"""
        connector_name, tag_name = self._input_mapping.get(sim_var, (None, None))
        if not connector_name:
            return None

        connector = self._connectors.get(connector_name)
        if connector and connector.is_connected:
            data = connector.read(tag_name)
            if data:
                value = data.value
                if sim_var in self._input_filters:
                    value = self._input_filters[sim_var](value)
                return value
        return None

    def set_output(self, sim_var: str, value: float) -> bool:
        """设置输出值"""
        connector_name, tag_name = self._output_mapping.get(sim_var, (None, None))
        if not connector_name:
            return False

        if sim_var in self._output_filters:
            value = self._output_filters[sim_var](value)

        connector = self._connectors.get(connector_name)
        if connector and connector.is_connected:
            return connector.write(tag_name, value)
        return False

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            'running': self._running,
            'connectors': {
                name: {'connected': conn.is_connected, 'stats': conn.get_stats()}
                for name, conn in self._connectors.items()
            },
            'input_count': len(self._input_mapping),
            'output_count': len(self._output_mapping),
        }


class ModbusTCPClient(DataConnector):
    """
    Modbus TCP客户端

    用于连接支持Modbus协议的设备
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._socket: Optional[socket.socket] = None
        self._transaction_id = 0
        self._unit_id = config.options.get('unit_id', 1)

    def connect(self) -> bool:
        """连接到Modbus设备"""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.config.timeout)
            self._socket.connect((self.config.host, self.config.port))
            self._connected = True
            logger.info(f"Modbus TCP connected to {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Modbus TCP connection failed: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self._socket:
            self._socket.close()
            self._socket = None
        self._connected = False

    def _read_impl(self, tag_name: str) -> Optional[DataPoint]:
        """读取寄存器"""
        # 解析标签格式：HR100（保持寄存器100）, IR200（输入寄存器200）
        try:
            if tag_name.startswith("HR"):
                address = int(tag_name[2:])
                value = self._read_holding_registers(address, 1)[0]
            elif tag_name.startswith("IR"):
                address = int(tag_name[2:])
                value = self._read_input_registers(address, 1)[0]
            elif tag_name.startswith("DI"):
                address = int(tag_name[2:])
                value = self._read_discrete_inputs(address, 1)[0]
            elif tag_name.startswith("CO"):
                address = int(tag_name[2:])
                value = self._read_coils(address, 1)[0]
            else:
                return None

            return DataPoint(
                tag_name=tag_name,
                value=value,
                timestamp=datetime.now(),
                quality=DataQuality.GOOD,
                source='modbus',
            )
        except Exception as e:
            logger.error(f"Modbus read error: {e}")
            return None

    def _write_impl(self, tag_name: str, value: Any) -> bool:
        """写入寄存器"""
        try:
            if tag_name.startswith("HR"):
                address = int(tag_name[2:])
                return self._write_single_register(address, int(value))
            elif tag_name.startswith("CO"):
                address = int(tag_name[2:])
                return self._write_single_coil(address, bool(value))
            return False
        except Exception as e:
            logger.error(f"Modbus write error: {e}")
            return False

    def _read_holding_registers(self, address: int, count: int) -> List[int]:
        """读取保持寄存器（功能码03）"""
        return self._read_registers(0x03, address, count)

    def _read_input_registers(self, address: int, count: int) -> List[int]:
        """读取输入寄存器（功能码04）"""
        return self._read_registers(0x04, address, count)

    def _read_discrete_inputs(self, address: int, count: int) -> List[bool]:
        """读取离散输入（功能码02）"""
        # 简化实现
        return [False] * count

    def _read_coils(self, address: int, count: int) -> List[bool]:
        """读取线圈（功能码01）"""
        # 简化实现
        return [False] * count

    def _read_registers(self, function_code: int, address: int, count: int) -> List[int]:
        """读取寄存器"""
        if not self._connected or not self._socket:
            return []

        self._transaction_id += 1

        # 构造Modbus TCP帧
        request = struct.pack(
            '>HHHBBHH',
            self._transaction_id,  # 事务标识
            0,                      # 协议标识（Modbus = 0）
            6,                      # 长度
            self._unit_id,          # 单元标识
            function_code,          # 功能码
            address,                # 起始地址
            count                   # 寄存器数量
        )

        try:
            self._socket.send(request)
            response = self._socket.recv(256)

            # 解析响应
            if len(response) >= 9:
                byte_count = response[8]
                values = []
                for i in range(count):
                    offset = 9 + i * 2
                    if offset + 2 <= len(response):
                        value = struct.unpack('>H', response[offset:offset+2])[0]
                        values.append(value)
                return values
        except Exception as e:
            logger.error(f"Modbus read registers error: {e}")

        return []

    def _write_single_register(self, address: int, value: int) -> bool:
        """写入单个寄存器（功能码06）"""
        if not self._connected or not self._socket:
            return False

        self._transaction_id += 1

        request = struct.pack(
            '>HHHBBHH',
            self._transaction_id,
            0,
            6,
            self._unit_id,
            0x06,
            address,
            value
        )

        try:
            self._socket.send(request)
            response = self._socket.recv(256)
            return len(response) >= 12
        except Exception as e:
            logger.error(f"Modbus write error: {e}")
            return False

    def _write_single_coil(self, address: int, value: bool) -> bool:
        """写入单个线圈（功能码05）"""
        # 简化实现
        return True


def create_hydropower_connectors(scada_host: str, historian_host: str,
                                   opc_host: str) -> Dict[str, DataConnector]:
    """
    创建水电站连接器套件

    Args:
        scada_host: SCADA服务器地址
        historian_host: 历史数据库地址
        opc_host: OPC-UA服务器地址

    Returns:
        连接器字典
    """
    connectors = {}

    # SCADA连接器
    scada_config = ConnectionConfig(
        protocol=ProtocolType.MODBUS_TCP,
        host=scada_host,
        port=502,
    )
    scada = SCADAConnector(scada_config)

    # 配置标签映射
    scada.add_point_definition('upstream_level', 'PLC1.AI001', 'float', 'm', 0.001, 0)
    scada.add_point_definition('downstream_level', 'PLC1.AI002', 'float', 'm', 0.001, 0)
    scada.add_point_definition('flow_rate', 'PLC1.AI003', 'float', 'm3/s', 0.01, 0)
    scada.add_point_definition('power_output', 'PLC1.AI004', 'float', 'MW', 0.1, 0)
    scada.add_point_definition('frequency', 'PLC1.AI005', 'float', 'Hz', 0.001, 0)

    connectors['scada'] = scada

    # 历史数据库连接器
    historian_config = ConnectionConfig(
        protocol=ProtocolType.HTTP_REST,
        host=historian_host,
        port=8080,
    )
    connectors['historian'] = HistorianConnector(historian_config)

    # OPC-UA连接器
    opc_config = ConnectionConfig(
        protocol=ProtocolType.OPC_UA,
        host=opc_host,
        port=4840,
        options={
            'security_mode': 'SignAndEncrypt',
            'security_policy': 'Basic256Sha256',
        }
    )
    connectors['opc'] = OPCUAClient(opc_config)

    return connectors
