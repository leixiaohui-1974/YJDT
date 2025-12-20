# -*- coding: utf-8 -*-
"""
雅江流域特色场景库 - 基于雅鲁藏布江大峡谷特殊环境
Yajiang Basin Specific Scenario Library

雅江特殊条件：
- 高海拔（3000-4500m）：空气稀薄、设备降容、人员高反
- 极端落差（2000m+）：世界最高水头、超长引水隧洞
- 地震高发（地震带）：雅鲁藏布江断裂带、频繁地震
- 冰川融水：季节性流量变化大、冰湖溃决风险
- 极端气候：高寒、大温差、强紫外线
- 地质灾害：滑坡、泥石流、崩塌频发
- 生态敏感：世界级生态保护区
- 交通困难：运输限制、应急响应延迟
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


class YajiangHazardType(Enum):
    """雅江特有灾害类型"""
    # 地质灾害
    EARTHQUAKE = "earthquake"                    # 地震
    LANDSLIDE = "landslide"                     # 滑坡
    DEBRIS_FLOW = "debris_flow"                 # 泥石流
    ROCKFALL = "rockfall"                       # 崩塌
    GLACIAL_LAKE_OUTBURST = "glof"              # 冰湖溃决

    # 气象灾害
    EXTREME_COLD = "extreme_cold"               # 极寒
    BLIZZARD = "blizzard"                       # 暴风雪
    THUNDERSTORM = "thunderstorm"               # 雷暴
    HAIL = "hail"                               # 冰雹
    DROUGHT = "drought"                         # 干旱

    # 水文灾害
    GLACIAL_FLOOD = "glacial_flood"             # 冰川洪水
    ICE_DAM = "ice_dam"                         # 冰坝
    SEDIMENT_SURGE = "sediment_surge"           # 泥沙骤增

    # 高原特有
    ALTITUDE_SICKNESS = "altitude_sickness"     # 高原反应
    EQUIPMENT_DERATING = "equipment_derating"   # 设备降容
    OXYGEN_DEFICIENCY = "oxygen_deficiency"     # 缺氧环境


@dataclass
class YajiangSiteCondition:
    """雅江站址条件"""
    # 地理参数
    elevation: float = 3500.0           # 海拔高度 (m)
    latitude: float = 29.5              # 纬度
    longitude: float = 95.0             # 经度

    # 水力参数
    design_head: float = 2000.0         # 设计水头 (m)
    rated_flow: float = 200.0           # 额定流量 (m³/s)
    tunnel_length: float = 45000.0      # 引水隧洞长度 (m)
    reservoir_capacity: float = 5e9     # 库容 (m³)

    # 气候参数
    avg_temperature: float = 5.0        # 年均温度 (℃)
    min_temperature: float = -30.0      # 极端低温 (℃)
    max_temperature: float = 30.0       # 极端高温 (℃)
    annual_precipitation: float = 800.0 # 年降水量 (mm)

    # 地质参数
    seismic_intensity: int = 8          # 抗震设防烈度
    pga: float = 0.3                    # 峰值地面加速度 (g)
    fault_distance: float = 5.0         # 距活动断层距离 (km)

    # 高原修正系数
    air_density_ratio: float = 0.65     # 空气密度比（相对海平面）
    equipment_derating: float = 0.85    # 设备降容系数
    human_efficiency: float = 0.70      # 人员效率系数


@dataclass
class YajiangScenario:
    """雅江特色场景"""
    scenario_id: str
    name: str
    category: str
    hazard_type: Optional[YajiangHazardType]
    description: str

    # 概率与影响
    annual_probability: float           # 年发生概率
    severity: str                       # low/medium/high/extreme
    duration_hours: float               # 持续时间

    # 触发条件
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)

    # 影响评估
    impact_on_generation: float = 0.0   # 发电影响 (MW)
    impact_on_equipment: List[str] = field(default_factory=list)
    cascade_effects: List[str] = field(default_factory=list)

    # 应对措施
    response_actions: List[str] = field(default_factory=list)
    required_response_time: float = 3600  # 要求响应时间 (秒)

    # 仿真参数
    simulation_params: Dict[str, Any] = field(default_factory=dict)


class YajiangScenarioLibrary:
    """
    雅江流域场景库

    覆盖雅鲁藏布江大峡谷水电开发全部特殊场景
    """

    def __init__(self):
        self.site_condition = YajiangSiteCondition()
        self.scenarios: Dict[str, YajiangScenario] = {}
        self.scenario_categories = {}

        # 初始化所有场景
        self._init_geological_scenarios()
        self._init_meteorological_scenarios()
        self._init_hydrological_scenarios()
        self._init_equipment_scenarios()
        self._init_operational_scenarios()
        self._init_extreme_combination_scenarios()
        self._init_cascade_failure_scenarios()

    def _init_geological_scenarios(self):
        """初始化地质灾害场景"""
        geological_scenarios = [
            # 地震场景序列
            YajiangScenario(
                scenario_id="GEO_EQ_001",
                name="设计基准地震(DBE)",
                category="geological",
                hazard_type=YajiangHazardType.EARTHQUAKE,
                description="抗震设防烈度VIII度地震，PGA=0.2g",
                annual_probability=0.01,
                severity="high",
                duration_hours=0.1,
                trigger_conditions={"pga": 0.2, "intensity": 8},
                impact_on_generation=-1000,
                impact_on_equipment=["penstock", "dam", "powerhouse"],
                cascade_effects=["landslide_trigger", "tunnel_damage"],
                response_actions=[
                    "紧急停机",
                    "关闭进水口闸门",
                    "启动地震应急预案",
                    "检查大坝安全",
                    "检查隧洞衬砌",
                ],
                required_response_time=60,
                simulation_params={
                    "ground_motion_duration": 30,
                    "aftershock_probability": 0.8,
                    "structural_response": True,
                }
            ),
            YajiangScenario(
                scenario_id="GEO_EQ_002",
                name="超设计基准地震(BDBE)",
                category="geological",
                hazard_type=YajiangHazardType.EARTHQUAKE,
                description="超抗震设防烈度IX度地震，PGA=0.4g",
                annual_probability=0.001,
                severity="extreme",
                duration_hours=0.1,
                trigger_conditions={"pga": 0.4, "intensity": 9},
                impact_on_generation=-1000,
                impact_on_equipment=["all_systems"],
                cascade_effects=["massive_landslide", "dam_breach_risk", "tunnel_collapse"],
                response_actions=[
                    "全厂紧急停机",
                    "大坝应急泄洪",
                    "人员紧急撤离",
                    "启动最高级应急响应",
                ],
                required_response_time=30,
                simulation_params={
                    "ground_motion_duration": 60,
                    "liquefaction_risk": True,
                    "dam_safety_check": True,
                }
            ),
            YajiangScenario(
                scenario_id="GEO_EQ_003",
                name="极端罕遇地震(万年一遇)",
                category="geological",
                hazard_type=YajiangHazardType.EARTHQUAKE,
                description="超设计XI度极端地震，PGA=0.6g",
                annual_probability=0.0001,
                severity="extreme",
                duration_hours=0.2,
                trigger_conditions={"pga": 0.6, "intensity": 11},
                impact_on_generation=-1000,
                cascade_effects=["catastrophic_landslide", "dam_failure", "tunnel_total_collapse"],
                response_actions=[
                    "确保大坝不溃决",
                    "最大限度保护人员安全",
                    "启动灾后恢复预案",
                ],
                required_response_time=10,
                simulation_params={
                    "consider_dam_breach": True,
                    "downstream_flood_routing": True,
                }
            ),

            # 滑坡场景
            YajiangScenario(
                scenario_id="GEO_LS_001",
                name="库区滑坡入库",
                category="geological",
                hazard_type=YajiangHazardType.LANDSLIDE,
                description="大型滑坡体滑入水库，引发涌浪",
                annual_probability=0.02,
                severity="high",
                duration_hours=0.5,
                trigger_conditions={"rainfall_intensity": 50, "slope_saturation": 0.9},
                impact_on_generation=-500,
                cascade_effects=["surge_wave", "dam_overtopping_risk", "sediment_increase"],
                response_actions=[
                    "降低库水位",
                    "加强大坝监测",
                    "下游预警",
                    "准备应急泄洪",
                ],
                required_response_time=300,
                simulation_params={
                    "slide_volume": 1e7,  # 1000万方
                    "surge_height": 30,
                    "wave_propagation": True,
                }
            ),
            YajiangScenario(
                scenario_id="GEO_LS_002",
                name="引水隧洞洞口滑坡",
                category="geological",
                hazard_type=YajiangHazardType.LANDSLIDE,
                description="隧洞进口区域滑坡堵塞进水口",
                annual_probability=0.01,
                severity="high",
                duration_hours=24,
                trigger_conditions={"rainfall_72h": 200},
                impact_on_generation=-1000,
                cascade_effects=["intake_blocked", "forced_shutdown"],
                response_actions=[
                    "紧急停机",
                    "评估清障可行性",
                    "启动备用取水方案",
                ],
                required_response_time=1800,
            ),
            YajiangScenario(
                scenario_id="GEO_LS_003",
                name="厂房边坡失稳",
                category="geological",
                hazard_type=YajiangHazardType.LANDSLIDE,
                description="地下厂房上方边坡变形加剧",
                annual_probability=0.005,
                severity="extreme",
                duration_hours=168,
                trigger_conditions={"displacement_rate": 5},  # mm/day
                impact_on_generation=-1000,
                cascade_effects=["powerhouse_damage", "personnel_risk"],
                response_actions=[
                    "人员撤离",
                    "紧急加固",
                    "持续监测",
                ],
            ),

            # 泥石流场景
            YajiangScenario(
                scenario_id="GEO_DF_001",
                name="沟道泥石流",
                category="geological",
                hazard_type=YajiangHazardType.DEBRIS_FLOW,
                description="暴雨引发支沟泥石流冲入库区",
                annual_probability=0.05,
                severity="medium",
                duration_hours=2,
                trigger_conditions={"rainfall_1h": 40},
                impact_on_generation=-200,
                cascade_effects=["sediment_surge", "intake_clogging"],
                response_actions=[
                    "启动拦沙设施",
                    "调整取水深度",
                    "加强水质监测",
                ],
            ),

            # 冰湖溃决
            YajiangScenario(
                scenario_id="GEO_GLOF_001",
                name="上游冰湖溃决洪水",
                category="geological",
                hazard_type=YajiangHazardType.GLACIAL_LAKE_OUTBURST,
                description="上游冰川湖突然溃决，形成特大洪水",
                annual_probability=0.01,
                severity="extreme",
                duration_hours=6,
                trigger_conditions={"glacier_melt_rate": "extreme", "moraine_dam_unstable": True},
                impact_on_generation=-1000,
                cascade_effects=["extreme_flood", "sediment_surge", "dam_safety_threat"],
                response_actions=[
                    "紧急停机",
                    "最大能力泄洪",
                    "下游紧急预警",
                    "人员撤离",
                ],
                required_response_time=1800,
                simulation_params={
                    "peak_discharge": 10000,  # m³/s
                    "flood_volume": 1e8,  # 1亿方
                    "sediment_concentration": 0.3,
                }
            ),
        ]

        for scenario in geological_scenarios:
            self.scenarios[scenario.scenario_id] = scenario

    def _init_meteorological_scenarios(self):
        """初始化气象灾害场景"""
        meteorological_scenarios = [
            # 极寒场景
            YajiangScenario(
                scenario_id="MET_COLD_001",
                name="极端低温冻害",
                category="meteorological",
                hazard_type=YajiangHazardType.EXTREME_COLD,
                description="气温骤降至-35℃以下，设备冻结风险",
                annual_probability=0.02,
                severity="high",
                duration_hours=72,
                trigger_conditions={"temperature": -35, "wind_speed": 15},
                impact_on_generation=-300,
                impact_on_equipment=["cooling_system", "hydraulic_system", "instrumentation"],
                cascade_effects=["ice_formation", "valve_stuck", "sensor_failure"],
                response_actions=[
                    "启动防冻加热系统",
                    "降低负荷运行",
                    "加强巡检",
                    "备用设备预热",
                ],
                simulation_params={
                    "freezing_rate": 0.1,  # m/hour
                    "equipment_failure_prob": 0.05,
                }
            ),
            YajiangScenario(
                scenario_id="MET_COLD_002",
                name="引水隧洞结冰",
                category="meteorological",
                hazard_type=YajiangHazardType.EXTREME_COLD,
                description="隧洞进口段结冰影响过流能力",
                annual_probability=0.01,
                severity="medium",
                duration_hours=168,
                trigger_conditions={"temperature": -25, "duration_days": 7},
                impact_on_generation=-500,
                response_actions=[
                    "调整运行水位",
                    "间歇运行融冰",
                    "机械除冰",
                ],
            ),

            # 暴风雪场景
            YajiangScenario(
                scenario_id="MET_SNOW_001",
                name="高原暴风雪",
                category="meteorological",
                hazard_type=YajiangHazardType.BLIZZARD,
                description="强暴风雪导致交通中断、通信受阻",
                annual_probability=0.1,
                severity="medium",
                duration_hours=48,
                trigger_conditions={"snowfall": 50, "visibility": 50},  # cm, m
                impact_on_generation=-100,
                cascade_effects=["road_blocked", "personnel_trapped", "supply_shortage"],
                response_actions=[
                    "启动孤岛运行模式",
                    "储备物资检查",
                    "值班人员就地待命",
                ],
            ),

            # 雷暴场景
            YajiangScenario(
                scenario_id="MET_THUNDER_001",
                name="强雷暴天气",
                category="meteorological",
                hazard_type=YajiangHazardType.THUNDERSTORM,
                description="高原强雷暴引发电力系统故障",
                annual_probability=0.2,
                severity="medium",
                duration_hours=4,
                trigger_conditions={"lightning_density": 10},  # 次/km²/hour
                impact_on_generation=-200,
                impact_on_equipment=["transformer", "transmission_line", "control_system"],
                cascade_effects=["grid_fault", "protection_action", "communication_loss"],
                response_actions=[
                    "加强避雷措施",
                    "准备黑启动",
                    "备用通信启用",
                ],
            ),

            # 冰雹场景
            YajiangScenario(
                scenario_id="MET_HAIL_001",
                name="大冰雹灾害",
                category="meteorological",
                hazard_type=YajiangHazardType.HAIL,
                description="大冰雹损坏户外设备和建筑",
                annual_probability=0.05,
                severity="medium",
                duration_hours=1,
                trigger_conditions={"hail_diameter": 30},  # mm
                impact_on_equipment=["outdoor_equipment", "solar_panels", "vehicles"],
                response_actions=[
                    "人员进入室内",
                    "保护敏感设备",
                    "灾后检查",
                ],
            ),
        ]

        for scenario in meteorological_scenarios:
            self.scenarios[scenario.scenario_id] = scenario

    def _init_hydrological_scenarios(self):
        """初始化水文灾害场景"""
        hydrological_scenarios = [
            # 冰川洪水
            YajiangScenario(
                scenario_id="HYD_GF_001",
                name="夏季冰川融水洪峰",
                category="hydrological",
                hazard_type=YajiangHazardType.GLACIAL_FLOOD,
                description="高温导致冰川加速融化，形成超标洪水",
                annual_probability=0.1,
                severity="high",
                duration_hours=72,
                trigger_conditions={"temperature": 25, "glacier_melt_rate": 2},
                impact_on_generation=200,  # 短期可增发
                cascade_effects=["reservoir_rapid_rise", "spillway_operation"],
                response_actions=[
                    "增大泄洪流量",
                    "协调下游预警",
                    "调整发电计划",
                ],
                simulation_params={
                    "peak_inflow": 5000,
                    "duration": 72,
                    "sediment_load": 5000,  # kg/s
                }
            ),

            # 枯水期
            YajiangScenario(
                scenario_id="HYD_DRY_001",
                name="极端枯水年",
                category="hydrological",
                hazard_type=YajiangHazardType.DROUGHT,
                description="来水严重偏枯，发电受限",
                annual_probability=0.05,
                severity="medium",
                duration_hours=2160,  # 90天
                trigger_conditions={"inflow_ratio": 0.5},  # 多年平均的50%
                impact_on_generation=-500,
                response_actions=[
                    "优化水库调度",
                    "限制发电出力",
                    "协调梯级调度",
                ],
            ),

            # 泥沙问题
            YajiangScenario(
                scenario_id="HYD_SED_001",
                name="汛期泥沙骤增",
                category="hydrological",
                hazard_type=YajiangHazardType.SEDIMENT_SURGE,
                description="洪水携带大量泥沙，影响取水和机组",
                annual_probability=0.15,
                severity="medium",
                duration_hours=24,
                trigger_conditions={"sediment_concentration": 50},  # kg/m³
                impact_on_generation=-400,
                impact_on_equipment=["turbine_runner", "guide_vanes", "seals"],
                response_actions=[
                    "降低负荷运行",
                    "调整取水层位",
                    "加强排沙运行",
                    "监测机组磨损",
                ],
            ),

            # 冰坝
            YajiangScenario(
                scenario_id="HYD_ICE_001",
                name="河道冰坝形成",
                category="hydrological",
                hazard_type=YajiangHazardType.ICE_DAM,
                description="冬季河道冰凌堵塞形成冰坝",
                annual_probability=0.02,
                severity="high",
                duration_hours=48,
                trigger_conditions={"ice_coverage": 0.8, "flow_velocity": 0.5},
                cascade_effects=["upstream_flooding", "sudden_release"],
                response_actions=[
                    "监测冰坝稳定性",
                    "准备破冰措施",
                    "下游预警",
                ],
            ),
        ]

        for scenario in hydrological_scenarios:
            self.scenarios[scenario.scenario_id] = scenario

    def _init_equipment_scenarios(self):
        """初始化高原设备特殊场景"""
        equipment_scenarios = [
            # 高海拔降容
            YajiangScenario(
                scenario_id="EQP_DER_001",
                name="高海拔发电机降容运行",
                category="equipment",
                hazard_type=YajiangHazardType.EQUIPMENT_DERATING,
                description="高海拔空气稀薄，发电机冷却能力下降",
                annual_probability=1.0,  # 常态
                severity="low",
                duration_hours=8760,  # 全年
                trigger_conditions={"elevation": 3500},
                impact_on_generation=-150,  # 15%降容
                response_actions=[
                    "按降容曲线运行",
                    "加强温度监测",
                    "优化冷却系统",
                ],
                simulation_params={
                    "derating_factor": 0.85,
                    "cooling_efficiency": 0.75,
                }
            ),
            YajiangScenario(
                scenario_id="EQP_DER_002",
                name="高海拔变压器降容",
                category="equipment",
                hazard_type=YajiangHazardType.EQUIPMENT_DERATING,
                description="变压器冷却效率降低，需降容运行",
                annual_probability=1.0,
                severity="low",
                duration_hours=8760,
                impact_on_generation=-100,
                simulation_params={
                    "derating_factor": 0.88,
                }
            ),

            # 极端水头场景
            YajiangScenario(
                scenario_id="EQP_HEAD_001",
                name="超高水头水锤",
                category="equipment",
                hazard_type=None,
                description="2000m级超高水头紧急关机水锤",
                annual_probability=0.01,
                severity="extreme",
                duration_hours=0.01,
                trigger_conditions={"emergency_shutdown": True, "head": 2000},
                impact_on_equipment=["penstock", "spiral_case", "guide_vanes"],
                cascade_effects=["pressure_surge", "structural_stress"],
                response_actions=[
                    "按紧急停机程序",
                    "启动调压室",
                    "监测压力变化",
                ],
                simulation_params={
                    "max_pressure_rise": 0.4,  # 40%超压
                    "closure_time": 60,
                    "surge_tank_response": True,
                }
            ),
            YajiangScenario(
                scenario_id="EQP_HEAD_002",
                name="超高水头甩负荷",
                category="equipment",
                hazard_type=None,
                description="满负荷运行时突然甩负荷",
                annual_probability=0.02,
                severity="high",
                duration_hours=0.1,
                trigger_conditions={"load_rejection": 1.0, "head": 2000},
                cascade_effects=["overspeed", "pressure_rise", "surge"],
                response_actions=[
                    "调速器快速响应",
                    "泄压阀动作",
                    "监测转速飞升",
                ],
                simulation_params={
                    "max_overspeed": 1.45,
                    "governor_response": True,
                }
            ),

            # 超长隧洞场景
            YajiangScenario(
                scenario_id="EQP_TUN_001",
                name="45km隧洞水力过渡过程",
                category="equipment",
                hazard_type=None,
                description="超长引水隧洞水力惯性影响",
                annual_probability=0.5,
                severity="medium",
                duration_hours=0.5,
                trigger_conditions={"tunnel_length": 45000},
                cascade_effects=["slow_response", "extended_transient"],
                response_actions=[
                    "预测性调度",
                    "多级调压室协调",
                    "限制负荷变化率",
                ],
                simulation_params={
                    "water_time_constant": 25,
                    "tunnel_friction_loss": 50,
                }
            ),
        ]

        for scenario in equipment_scenarios:
            self.scenarios[scenario.scenario_id] = scenario

    def _init_operational_scenarios(self):
        """初始化运行场景"""
        operational_scenarios = [
            # 高原人员因素
            YajiangScenario(
                scenario_id="OPR_ALT_001",
                name="运维人员高原反应",
                category="operational",
                hazard_type=YajiangHazardType.ALTITUDE_SICKNESS,
                description="运维人员高原反应导致工作效率下降",
                annual_probability=0.3,
                severity="low",
                duration_hours=72,
                trigger_conditions={"new_personnel": True, "elevation": 3500},
                cascade_effects=["response_delay", "error_rate_increase"],
                response_actions=[
                    "适应性训练",
                    "备用人员待命",
                    "医疗保障",
                ],
                simulation_params={
                    "efficiency_factor": 0.7,
                    "error_probability": 1.5,
                }
            ),

            # 应急响应延迟
            YajiangScenario(
                scenario_id="OPR_RES_001",
                name="应急响应交通受阻",
                category="operational",
                hazard_type=None,
                description="恶劣天气或灾害导致应急响应延迟",
                annual_probability=0.1,
                severity="medium",
                duration_hours=48,
                trigger_conditions={"road_blocked": True},
                cascade_effects=["delayed_repair", "extended_outage"],
                response_actions=[
                    "直升机备用",
                    "就地备件储备",
                    "远程技术支持",
                ],
            ),

            # 孤网运行
            YajiangScenario(
                scenario_id="OPR_ISO_001",
                name="孤网独立运行",
                category="operational",
                hazard_type=None,
                description="与主网断开后孤网独立运行",
                annual_probability=0.05,
                severity="high",
                duration_hours=24,
                trigger_conditions={"grid_disconnected": True},
                impact_on_generation=-800,  # 限制出力
                response_actions=[
                    "切换孤网控制模式",
                    "负荷平衡控制",
                    "频率电压独立调节",
                ],
            ),
        ]

        for scenario in operational_scenarios:
            self.scenarios[scenario.scenario_id] = scenario

    def _init_extreme_combination_scenarios(self):
        """初始化极端组合场景"""
        combination_scenarios = [
            # 地震+滑坡+洪水
            YajiangScenario(
                scenario_id="COMB_001",
                name="地震-滑坡-堰塞湖链式灾害",
                category="combination",
                hazard_type=YajiangHazardType.EARTHQUAKE,
                description="强震触发滑坡形成堰塞湖，溃决后形成特大洪水",
                annual_probability=0.001,
                severity="extreme",
                duration_hours=168,
                trigger_conditions={
                    "earthquake_intensity": 8,
                    "landslide_triggered": True,
                    "dam_formed": True,
                },
                cascade_effects=[
                    "seismic_damage",
                    "landslide_dam",
                    "barrier_lake",
                    "outburst_flood",
                    "downstream_devastation",
                ],
                response_actions=[
                    "多级应急响应",
                    "下游大规模疏散",
                    "协调军队救援",
                    "国家级应急启动",
                ],
                required_response_time=600,
            ),

            # 极寒+暴雪+冰坝
            YajiangScenario(
                scenario_id="COMB_002",
                name="极寒-暴雪-冰坝复合灾害",
                category="combination",
                hazard_type=YajiangHazardType.EXTREME_COLD,
                description="极端寒潮叠加暴雪导致冰坝和设备冻害",
                annual_probability=0.005,
                severity="high",
                duration_hours=120,
                cascade_effects=[
                    "equipment_freeze",
                    "road_impassable",
                    "ice_dam_risk",
                    "power_outage",
                ],
                response_actions=[
                    "启动极端天气预案",
                    "保证最小安全运行",
                    "储备物资分配",
                ],
            ),

            # 洪水+泥沙+地震
            YajiangScenario(
                scenario_id="COMB_003",
                name="汛期洪水+高泥沙+地震",
                category="combination",
                hazard_type=None,
                description="主汛期遭遇高泥沙洪水同时发生地震",
                annual_probability=0.0005,
                severity="extreme",
                duration_hours=24,
                cascade_effects=[
                    "dam_safety_crisis",
                    "spillway_damage",
                    "sediment_abrasion",
                    "structural_failure",
                ],
                response_actions=[
                    "确保大坝安全第一",
                    "全面停机检查",
                    "启动最高级应急",
                ],
            ),
        ]

        for scenario in combination_scenarios:
            self.scenarios[scenario.scenario_id] = scenario

    def _init_cascade_failure_scenarios(self):
        """初始化梯级联动失效场景"""
        cascade_scenarios = [
            YajiangScenario(
                scenario_id="CASC_001",
                name="上游电站溃坝洪水",
                category="cascade",
                hazard_type=None,
                description="上游梯级电站溃坝形成叠加洪水",
                annual_probability=0.0001,
                severity="extreme",
                duration_hours=24,
                cascade_effects=[
                    "upstream_dam_breach",
                    "flood_superposition",
                    "domino_failure_risk",
                ],
                response_actions=[
                    "接收上游预警",
                    "紧急泄洪腾库",
                    "下游紧急疏散",
                ],
                simulation_params={
                    "breach_discharge": 50000,
                    "wave_arrival_time": 3600,
                }
            ),
            YajiangScenario(
                scenario_id="CASC_002",
                name="梯级电站连锁甩负荷",
                category="cascade",
                hazard_type=None,
                description="电网故障导致梯级电站连锁甩负荷",
                annual_probability=0.01,
                severity="high",
                duration_hours=1,
                cascade_effects=[
                    "multi_station_rejection",
                    "coordinated_surge",
                    "grid_instability",
                ],
                response_actions=[
                    "梯级协调控制",
                    "水位联合调节",
                    "防止连锁事故",
                ],
            ),
        ]

        for scenario in cascade_scenarios:
            self.scenarios[scenario.scenario_id] = scenario

    def get_all_scenarios(self) -> List[YajiangScenario]:
        """获取所有场景"""
        return list(self.scenarios.values())

    def get_scenarios_by_category(self, category: str) -> List[YajiangScenario]:
        """按类别获取场景"""
        return [s for s in self.scenarios.values() if s.category == category]

    def get_scenarios_by_severity(self, severity: str) -> List[YajiangScenario]:
        """按严重程度获取场景"""
        return [s for s in self.scenarios.values() if s.severity == severity]

    def get_scenario_statistics(self) -> Dict[str, Any]:
        """获取场景统计"""
        all_scenarios = self.get_all_scenarios()

        by_category = {}
        by_severity = {}
        by_hazard = {}

        for s in all_scenarios:
            by_category[s.category] = by_category.get(s.category, 0) + 1
            by_severity[s.severity] = by_severity.get(s.severity, 0) + 1
            if s.hazard_type:
                by_hazard[s.hazard_type.value] = by_hazard.get(s.hazard_type.value, 0) + 1

        return {
            "total_scenarios": len(all_scenarios),
            "by_category": by_category,
            "by_severity": by_severity,
            "by_hazard_type": by_hazard,
            "site_condition": {
                "elevation": self.site_condition.elevation,
                "design_head": self.site_condition.design_head,
                "seismic_intensity": self.site_condition.seismic_intensity,
            }
        }

    def generate_scenario_matrix(self) -> np.ndarray:
        """生成场景概率-影响矩阵"""
        scenarios = self.get_all_scenarios()
        n = len(scenarios)

        matrix = np.zeros((n, 4))  # probability, severity, duration, response_time
        severity_map = {"low": 1, "medium": 2, "high": 3, "extreme": 4}

        for i, s in enumerate(scenarios):
            matrix[i, 0] = s.annual_probability
            matrix[i, 1] = severity_map.get(s.severity, 2)
            matrix[i, 2] = s.duration_hours
            matrix[i, 3] = s.required_response_time / 3600  # 转换为小时

        return matrix
