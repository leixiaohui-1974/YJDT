# -*- coding: utf-8 -*-
"""
API数据模型 - Pydantic Models

定义API请求和响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class SimulationMode(str, Enum):
    """仿真模式"""
    NORMAL = "normal"
    REALTIME = "realtime"
    FAST = "fast"
    STEP = "step"


class ScenarioType(str, Enum):
    """场景类型"""
    NORMAL_OPERATION = "normal_operation"
    LOAD_CHANGE = "load_change"
    FAULT = "fault"
    EXTREME_WEATHER = "extreme_weather"
    EMERGENCY = "emergency"
    GLACIER_MELT = "glacier_melt"
    SEISMIC = "seismic"


class ControllerType(str, Enum):
    """控制器类型"""
    PID = "pid"
    MPC = "mpc"
    DISTRIBUTED = "distributed"


class AlarmSeverity(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ============== 仿真相关模型 ==============

class HydraulicConfig(BaseModel):
    """水力系统配置"""
    pipeline_length: float = Field(1000, description="管道长度(m)")
    pipeline_diameter: float = Field(5.0, description="管道直径(m)")
    wave_speed: float = Field(1200, description="水锤波速(m/s)")
    friction_factor: float = Field(0.02, description="摩阻系数")
    surge_tank_area: float = Field(100, description="调压室面积(m²)")


class TurbineConfig(BaseModel):
    """水轮机配置"""
    turbine_type: str = Field("Francis", description="水轮机类型")
    rated_power: float = Field(200, description="额定功率(MW)")
    rated_head: float = Field(150, description="额定水头(m)")
    rated_flow: float = Field(150, description="额定流量(m³/s)")
    rated_speed: float = Field(150, description="额定转速(rpm)")
    efficiency: float = Field(0.92, description="效率")


class GeneratorConfig(BaseModel):
    """发电机配置"""
    rated_power: float = Field(200, description="额定功率(MW)")
    rated_voltage: float = Field(15.75, description="额定电压(kV)")
    rated_frequency: float = Field(50, description="额定频率(Hz)")
    inertia: float = Field(8.0, description="惯性时间常数(s)")
    poles: int = Field(40, description="极对数")


class GovernorConfig(BaseModel):
    """调速器配置"""
    controller_type: ControllerType = ControllerType.PID
    kp: float = Field(2.0, description="比例增益")
    ki: float = Field(0.5, description="积分增益")
    kd: float = Field(0.1, description="微分增益")
    deadband: float = Field(0.0006, description="死区")

    # MPC参数
    prediction_horizon: int = Field(20, description="预测时域")
    control_horizon: int = Field(10, description="控制时域")


class SimulationConfig(BaseModel):
    """仿真配置"""
    name: str = Field("默认仿真", description="仿真名称")
    mode: SimulationMode = SimulationMode.NORMAL
    duration: float = Field(100, description="仿真时长(s)")
    time_step: float = Field(0.01, description="仿真步长(s)")

    # 子系统配置
    hydraulic: Optional[HydraulicConfig] = None
    turbine: Optional[TurbineConfig] = None
    generator: Optional[GeneratorConfig] = None
    governor: Optional[GovernorConfig] = None

    # 场景配置
    scenario_id: Optional[str] = None
    initial_power: float = Field(100, description="初始功率(MW)")
    target_power: float = Field(150, description="目标功率(MW)")

    # 扰动配置
    disturbance_time: float = Field(10, description="扰动时刻(s)")
    disturbance_magnitude: float = Field(0.1, description="扰动幅值(pu)")


class SimulationState(BaseModel):
    """仿真状态"""
    simulation_id: str
    status: str = Field(description="状态: pending/running/completed/failed")
    progress: float = Field(0, description="进度百分比")
    current_time: float = Field(0, description="当前仿真时间(s)")
    start_time: Optional[datetime] = None
    elapsed_time: float = Field(0, description="已用时间(s)")
    message: str = ""


class TimeSeriesData(BaseModel):
    """时间序列数据"""
    time: List[float]
    values: Dict[str, List[float]]
    units: Dict[str, str] = {}


class SimulationResult(BaseModel):
    """仿真结果"""
    simulation_id: str
    config: SimulationConfig
    status: str

    # 时间序列结果
    time_series: Optional[TimeSeriesData] = None

    # 汇总统计
    statistics: Dict[str, Any] = {}

    # 性能指标
    performance: Dict[str, float] = {}

    # 告警和事件
    events: List[Dict[str, Any]] = []

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    computation_time: float = 0


# ============== 场景相关模型 ==============

class ScenarioDefinition(BaseModel):
    """场景定义"""
    scenario_id: str
    name: str
    scenario_type: ScenarioType
    description: str = ""

    # 初始条件
    initial_conditions: Dict[str, float] = {}

    # 边界条件
    boundary_conditions: Dict[str, List[float]] = {}

    # 参数
    parameters: Dict[str, Any] = {}

    # 持续时间
    duration: float = 3600

    # 元数据
    tags: List[str] = []
    severity: str = "normal"
    probability: float = 1.0


class ScenarioListItem(BaseModel):
    """场景列表项"""
    scenario_id: str
    name: str
    scenario_type: ScenarioType
    description: str = ""
    severity: str = "normal"


class ScenarioMatchResult(BaseModel):
    """场景匹配结果"""
    scenario_id: str
    scenario_name: str
    confidence: float
    matched_features: List[str]


# ============== 监控相关模型 ==============

class SensorReading(BaseModel):
    """传感器读数"""
    sensor_id: str
    value: float
    unit: str
    timestamp: datetime
    quality: str = "good"


class SystemStatus(BaseModel):
    """系统状态"""
    system_id: str = "yjdt-main"
    status: str = "running"
    mode: str = "simulation"

    # 时间信息
    system_time: datetime = Field(default_factory=datetime.now)
    uptime: float = 0

    # 组件状态
    components: Dict[str, str] = {}

    # 实时数据
    realtime_data: Dict[str, float] = {}

    # 统计信息
    statistics: Dict[str, Any] = {}


class AlarmInfo(BaseModel):
    """告警信息"""
    alarm_id: str
    timestamp: datetime
    severity: AlarmSeverity
    source: str
    message: str
    acknowledged: bool = False
    cleared: bool = False


class HistoricalDataRequest(BaseModel):
    """历史数据请求"""
    tags: List[str]
    start_time: datetime
    end_time: datetime
    interval: Optional[float] = None  # 重采样间隔(秒)
    aggregation: str = "mean"  # mean, max, min, sum


class HistoricalDataResponse(BaseModel):
    """历史数据响应"""
    tags: List[str]
    start_time: datetime
    end_time: datetime
    data: Dict[str, List[Dict[str, Any]]]
    statistics: Dict[str, Dict[str, float]] = {}


# ============== 控制相关模型 ==============

class ControlCommand(BaseModel):
    """控制指令"""
    command_id: str = ""
    target: str = Field(description="目标设备/控制器")
    action: str = Field(description="动作类型")
    parameters: Dict[str, Any] = {}
    priority: int = 5
    timeout: float = 30
    timestamp: datetime = Field(default_factory=datetime.now)


class ControlResponse(BaseModel):
    """控制响应"""
    command_id: str
    status: str  # pending, executing, completed, failed
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SetpointChange(BaseModel):
    """设定值变更"""
    target: str
    setpoint_name: str
    current_value: float
    new_value: float
    ramp_rate: Optional[float] = None  # 变化速率


class SchedulingRequest(BaseModel):
    """调度请求"""
    scheduling_type: str = "realtime"  # day_ahead, intraday, realtime
    target_power: Optional[float] = None
    load_forecast: Optional[List[float]] = None
    duration_hours: float = 24
    objective: str = "max_revenue"


class SchedulingResult(BaseModel):
    """调度结果"""
    request_id: str
    status: str
    unit_schedules: Dict[str, List[float]]
    total_generation: List[float]
    total_revenue: float
    solve_time: float


# ============== 诊断相关模型 ==============

class DiagnosisRequest(BaseModel):
    """诊断请求"""
    target: str
    diagnosis_type: str = "fault"  # fault, performance, health
    data_window: float = 3600  # 数据窗口(秒)


class DiagnosisResult(BaseModel):
    """诊断结果"""
    request_id: str
    target: str
    status: str
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthStatus(BaseModel):
    """健康状态"""
    component: str
    health_index: float  # 0-100
    status: str  # healthy, degraded, critical
    remaining_life: Optional[float] = None
    factors: Dict[str, float] = {}


# ============== 通用模型 ==============

class APIResponse(BaseModel):
    """通用API响应"""
    success: bool
    message: str = ""
    data: Optional[Any] = None
    errors: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    message_type: str
    channel: str = "default"
    data: Any
    timestamp: datetime = Field(default_factory=datetime.now)
