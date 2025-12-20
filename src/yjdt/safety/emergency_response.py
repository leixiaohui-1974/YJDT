# -*- coding: utf-8 -*-
"""
应急响应决策支持系统
Emergency Response Decision Support System

功能：
1. 事故识别与分级
2. 应急预案自动匹配
3. 应急操作指导
4. 资源调度优化
5. 事故态势推演
6. 恢复策略建议

Author: YJDT Team
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import heapq


class EmergencyLevel(Enum):
    """应急响应等级"""
    LEVEL_IV = ("四级", "一般", "蓝色", 4)      # 一般事件
    LEVEL_III = ("三级", "较大", "黄色", 3)     # 较大事件
    LEVEL_II = ("二级", "重大", "橙色", 2)      # 重大事件
    LEVEL_I = ("一级", "特别重大", "红色", 1)   # 特别重大事件


class EventCategory(Enum):
    """事件类别"""
    EQUIPMENT_FAILURE = "设备故障"
    GRID_ACCIDENT = "电网事故"
    HYDRAULIC_ACCIDENT = "水力事故"
    NATURAL_DISASTER = "自然灾害"
    FIRE = "火灾"
    FLOOD = "水淹"
    PERSONNEL_INJURY = "人身伤害"
    ENVIRONMENTAL = "环境事件"
    SECURITY = "安保事件"
    CYBER = "网络安全"


class ResponsePhase(Enum):
    """响应阶段"""
    DETECTION = "检测识别"
    ASSESSMENT = "评估定级"
    ACTIVATION = "预案启动"
    RESPONSE = "应急处置"
    MITIGATION = "减缓控制"
    RECOVERY = "恢复重建"
    REVIEW = "总结评估"


@dataclass
class EmergencyEvent:
    """应急事件"""
    id: str
    name: str
    category: EventCategory
    level: EmergencyLevel
    start_time: datetime
    location: str
    description: str

    # 事件参数
    affected_units: List[str] = field(default_factory=list)
    affected_systems: List[str] = field(default_factory=list)
    casualties: int = 0
    economic_loss: float = 0.0

    # 状态
    current_phase: ResponsePhase = ResponsePhase.DETECTION
    is_active: bool = True
    escalation_risk: float = 0.0

    # 时间线
    timeline: List[Dict] = field(default_factory=list)


@dataclass
class ResponseAction:
    """响应动作"""
    id: str
    name: str
    description: str
    priority: int  # 1-最高，5-最低
    responsible: str  # 责任人/部门
    deadline_minutes: int
    prerequisites: List[str] = field(default_factory=list)
    resources_required: List[str] = field(default_factory=list)
    verification_method: str = ""

    # 执行状态
    status: str = "pending"  # pending, in_progress, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: str = ""


@dataclass
class EmergencyPlan:
    """应急预案"""
    id: str
    name: str
    category: EventCategory
    applicable_levels: List[EmergencyLevel]
    description: str

    # 响应动作
    immediate_actions: List[ResponseAction] = field(default_factory=list)
    short_term_actions: List[ResponseAction] = field(default_factory=list)
    long_term_actions: List[ResponseAction] = field(default_factory=list)

    # 资源需求
    personnel_required: Dict[str, int] = field(default_factory=dict)
    equipment_required: List[str] = field(default_factory=list)
    external_support: List[str] = field(default_factory=list)

    # 通知列表
    notification_list: List[Dict[str, str]] = field(default_factory=list)


class EmergencyPlanLibrary:
    """应急预案库"""

    def __init__(self):
        self.plans: Dict[str, EmergencyPlan] = {}
        self._init_standard_plans()

    def _init_standard_plans(self):
        """初始化标准应急预案"""

        # 1. 机组甩负荷应急预案
        self.plans['PLAN-LR'] = EmergencyPlan(
            id="PLAN-LR",
            name="机组甩负荷应急预案",
            category=EventCategory.EQUIPMENT_FAILURE,
            applicable_levels=[EmergencyLevel.LEVEL_IV, EmergencyLevel.LEVEL_III],
            description="机组发生甩负荷事件的应急处置",
            immediate_actions=[
                ResponseAction(
                    id="LR-01",
                    name="确认机组状态",
                    description="确认机组是否安全停机，检查转速、压力、振动等参数",
                    priority=1,
                    responsible="值班员",
                    deadline_minutes=1,
                    verification_method="参数确认，现场检查"
                ),
                ResponseAction(
                    id="LR-02",
                    name="检查保护动作",
                    description="确认各保护是否正确动作，检查信号和报警",
                    priority=1,
                    responsible="值班员",
                    deadline_minutes=2,
                    verification_method="保护信号确认"
                ),
                ResponseAction(
                    id="LR-03",
                    name="通知调度",
                    description="向电网调度报告事故情况",
                    priority=2,
                    responsible="值班长",
                    deadline_minutes=5,
                    verification_method="调度确认"
                ),
                ResponseAction(
                    id="LR-04",
                    name="组织分析原因",
                    description="分析甩负荷原因，判断是否可以重新启动",
                    priority=3,
                    responsible="技术人员",
                    deadline_minutes=30,
                    verification_method="分析报告"
                )
            ],
            short_term_actions=[
                ResponseAction(
                    id="LR-05",
                    name="设备检查",
                    description="全面检查机组设备状态",
                    priority=3,
                    responsible="检修人员",
                    deadline_minutes=120
                ),
                ResponseAction(
                    id="LR-06",
                    name="恢复运行评估",
                    description="评估机组是否具备恢复运行条件",
                    priority=4,
                    responsible="技术负责人",
                    deadline_minutes=240
                )
            ],
            personnel_required={"值班员": 2, "值班长": 1, "技术人员": 1, "检修人员": 2},
            notification_list=[
                {"role": "值班长", "method": "电话", "time": "立即"},
                {"role": "生产部门", "method": "电话", "time": "5分钟内"},
                {"role": "电网调度", "method": "调度电话", "time": "5分钟内"},
                {"role": "厂领导", "method": "电话", "time": "15分钟内"}
            ]
        )

        # 2. 全厂停电应急预案
        self.plans['PLAN-SBO'] = EmergencyPlan(
            id="PLAN-SBO",
            name="全厂停电应急预案",
            category=EventCategory.EQUIPMENT_FAILURE,
            applicable_levels=[EmergencyLevel.LEVEL_II, EmergencyLevel.LEVEL_I],
            description="全厂交直流电源丧失的应急处置",
            immediate_actions=[
                ResponseAction(
                    id="SBO-01",
                    name="启动应急照明",
                    description="确认应急照明自动投入，必要时手动投入",
                    priority=1,
                    responsible="值班员",
                    deadline_minutes=1
                ),
                ResponseAction(
                    id="SBO-02",
                    name="确认设备安全状态",
                    description="确认所有机组安全停机，闸门处于安全位置",
                    priority=1,
                    responsible="值班员",
                    deadline_minutes=2
                ),
                ResponseAction(
                    id="SBO-03",
                    name="启动柴油发电机",
                    description="手动或自动启动应急柴油发电机",
                    priority=1,
                    responsible="值班员",
                    deadline_minutes=5
                ),
                ResponseAction(
                    id="SBO-04",
                    name="通知相关人员",
                    description="通知生产、调度、安全部门及厂领导",
                    priority=2,
                    responsible="值班长",
                    deadline_minutes=5
                ),
                ResponseAction(
                    id="SBO-05",
                    name="确认直流电源",
                    description="检查蓄电池组状态，确认直流负荷供电",
                    priority=2,
                    responsible="值班员",
                    deadline_minutes=10
                )
            ],
            personnel_required={"值班员": 3, "值班长": 1, "电气人员": 2, "厂领导": 1},
            equipment_required=["应急柴油发电机", "应急照明", "通信设备", "蓄电池"],
            external_support=["电网调度支持", "外部电源支援"],
            notification_list=[
                {"role": "生产副总", "method": "电话", "time": "立即"},
                {"role": "电网调度", "method": "调度电话", "time": "立即"},
                {"role": "总经理", "method": "电话", "time": "5分钟内"},
                {"role": "上级公司", "method": "电话", "time": "15分钟内"}
            ]
        )

        # 3. 地震应急预案
        self.plans['PLAN-EARTHQUAKE'] = EmergencyPlan(
            id="PLAN-EARTHQUAKE",
            name="地震应急预案",
            category=EventCategory.NATURAL_DISASTER,
            applicable_levels=[EmergencyLevel.LEVEL_III, EmergencyLevel.LEVEL_II, EmergencyLevel.LEVEL_I],
            description="地震发生后的应急处置",
            immediate_actions=[
                ResponseAction(
                    id="EQ-01",
                    name="人员避险",
                    description="组织人员就近避险，远离危险区域",
                    priority=1,
                    responsible="现场负责人",
                    deadline_minutes=1
                ),
                ResponseAction(
                    id="EQ-02",
                    name="机组紧急停机",
                    description="执行地震停机程序，所有运行机组停机",
                    priority=1,
                    responsible="值班员",
                    deadline_minutes=2
                ),
                ResponseAction(
                    id="EQ-03",
                    name="关闭进水阀",
                    description="关闭所有进水阀门和闸门",
                    priority=1,
                    responsible="值班员",
                    deadline_minutes=5
                ),
                ResponseAction(
                    id="EQ-04",
                    name="大坝巡查",
                    description="震后立即进行大坝安全巡查",
                    priority=1,
                    responsible="大坝值班",
                    deadline_minutes=10
                ),
                ResponseAction(
                    id="EQ-05",
                    name="人员清点",
                    description="清点所有人员，确认无人员伤亡",
                    priority=2,
                    responsible="安全员",
                    deadline_minutes=15
                ),
                ResponseAction(
                    id="EQ-06",
                    name="设备巡检",
                    description="全面巡检所有设备设施",
                    priority=3,
                    responsible="各专业人员",
                    deadline_minutes=60
                )
            ],
            short_term_actions=[
                ResponseAction(
                    id="EQ-07",
                    name="大坝安全评估",
                    description="组织专家进行大坝安全评估",
                    priority=2,
                    responsible="技术负责人",
                    deadline_minutes=480
                ),
                ResponseAction(
                    id="EQ-08",
                    name="设备损伤评估",
                    description="评估设备损伤情况",
                    priority=3,
                    responsible="各专业负责人",
                    deadline_minutes=720
                )
            ],
            personnel_required={
                "现场负责人": 1,
                "值班员": 4,
                "安全员": 2,
                "大坝值班": 2,
                "各专业人员": 10,
                "医疗人员": 2
            },
            equipment_required=["通信设备", "应急照明", "急救箱", "检测仪器"],
            external_support=["地震部门", "应急管理部门", "专家组", "医疗救护"],
            notification_list=[
                {"role": "应急指挥中心", "method": "电话", "time": "立即"},
                {"role": "地方政府", "method": "电话", "time": "立即"},
                {"role": "上级公司", "method": "电话", "time": "5分钟内"},
                {"role": "下游政府", "method": "电话", "time": "10分钟内"}
            ]
        )

        # 4. 洪水应急预案
        self.plans['PLAN-FLOOD'] = EmergencyPlan(
            id="PLAN-FLOOD",
            name="洪水应急预案",
            category=EventCategory.NATURAL_DISASTER,
            applicable_levels=[EmergencyLevel.LEVEL_III, EmergencyLevel.LEVEL_II, EmergencyLevel.LEVEL_I],
            description="洪水来临及超标洪水的应急处置",
            immediate_actions=[
                ResponseAction(
                    id="FL-01",
                    name="监测水情",
                    description="加强水情监测，实时跟踪来水情况",
                    priority=1,
                    responsible="水工值班",
                    deadline_minutes=0
                ),
                ResponseAction(
                    id="FL-02",
                    name="预腾库容",
                    description="根据预报提前降低水库水位",
                    priority=1,
                    responsible="调度中心",
                    deadline_minutes=60
                ),
                ResponseAction(
                    id="FL-03",
                    name="通知下游",
                    description="向下游发布洪水预警信息",
                    priority=1,
                    responsible="调度中心",
                    deadline_minutes=30
                ),
                ResponseAction(
                    id="FL-04",
                    name="泄洪设施检查",
                    description="检查泄洪闸门、溢洪道等设施",
                    priority=2,
                    responsible="水工人员",
                    deadline_minutes=60
                )
            ],
            personnel_required={"调度人员": 3, "水工人员": 4, "闸门操作": 2},
            external_support=["水利部门", "气象部门", "下游政府"]
        )

        # 5. 火灾应急预案
        self.plans['PLAN-FIRE'] = EmergencyPlan(
            id="PLAN-FIRE",
            name="火灾应急预案",
            category=EventCategory.FIRE,
            applicable_levels=[EmergencyLevel.LEVEL_IV, EmergencyLevel.LEVEL_III, EmergencyLevel.LEVEL_II],
            description="电气或其他火灾的应急处置",
            immediate_actions=[
                ResponseAction(
                    id="FR-01",
                    name="报警疏散",
                    description="发现火情立即报警，组织人员疏散",
                    priority=1,
                    responsible="发现人",
                    deadline_minutes=1
                ),
                ResponseAction(
                    id="FR-02",
                    name="切断电源",
                    description="切断着火区域电源",
                    priority=1,
                    responsible="值班员",
                    deadline_minutes=2
                ),
                ResponseAction(
                    id="FR-03",
                    name="初期灭火",
                    description="使用灭火器进行初期灭火",
                    priority=1,
                    responsible="现场人员",
                    deadline_minutes=3
                ),
                ResponseAction(
                    id="FR-04",
                    name="启动消防系统",
                    description="启动消防水系统、气体灭火系统",
                    priority=2,
                    responsible="消防人员",
                    deadline_minutes=5
                ),
                ResponseAction(
                    id="FR-05",
                    name="呼叫消防队",
                    description="拨打119呼叫消防队",
                    priority=2,
                    responsible="值班长",
                    deadline_minutes=2
                )
            ],
            personnel_required={"消防人员": 4, "值班员": 2, "安全员": 2},
            equipment_required=["灭火器", "消防栓", "防烟面罩", "消防服"],
            external_support=["消防队", "医疗救护"]
        )

        # 6. 网络安全应急预案
        self.plans['PLAN-CYBER'] = EmergencyPlan(
            id="PLAN-CYBER",
            name="网络安全应急预案",
            category=EventCategory.CYBER,
            applicable_levels=[EmergencyLevel.LEVEL_III, EmergencyLevel.LEVEL_II],
            description="网络攻击或安全事件的应急处置",
            immediate_actions=[
                ResponseAction(
                    id="CY-01",
                    name="隔离受攻击系统",
                    description="立即隔离受攻击的网络和系统",
                    priority=1,
                    responsible="IT人员",
                    deadline_minutes=5
                ),
                ResponseAction(
                    id="CY-02",
                    name="切换本地控制",
                    description="将控制系统切换到本地模式",
                    priority=1,
                    responsible="值班员",
                    deadline_minutes=5
                ),
                ResponseAction(
                    id="CY-03",
                    name="保存证据",
                    description="保存攻击证据和日志",
                    priority=2,
                    responsible="IT人员",
                    deadline_minutes=30
                ),
                ResponseAction(
                    id="CY-04",
                    name="报告安全部门",
                    description="向公安网监部门报告",
                    priority=2,
                    responsible="安全负责人",
                    deadline_minutes=60
                )
            ],
            personnel_required={"IT人员": 3, "安全专家": 2, "值班员": 2},
            external_support=["网安部门", "安全服务商"]
        )

    def match_plan(self, event: EmergencyEvent) -> Optional[EmergencyPlan]:
        """匹配应急预案"""
        for plan in self.plans.values():
            if plan.category == event.category and event.level in plan.applicable_levels:
                return plan
        return None

    def get_all_plans(self) -> List[EmergencyPlan]:
        """获取所有预案"""
        return list(self.plans.values())


class EmergencyResponseCoordinator:
    """应急响应协调器"""

    def __init__(self):
        self.plan_library = EmergencyPlanLibrary()
        self.active_events: Dict[str, EmergencyEvent] = {}
        self.action_queue: List[Tuple[int, ResponseAction]] = []  # 优先队列

    def report_event(self, event: EmergencyEvent) -> Dict[str, Any]:
        """报告事件并启动响应"""
        self.active_events[event.id] = event

        # 匹配预案
        plan = self.plan_library.match_plan(event)

        if not plan:
            return {
                'success': False,
                'message': "未找到匹配的应急预案",
                'recommendation': "启动通用应急响应程序"
            }

        # 更新事件阶段
        event.current_phase = ResponsePhase.ACTIVATION
        event.timeline.append({
            'time': datetime.now(),
            'phase': ResponsePhase.ACTIVATION.value,
            'action': f"启动预案: {plan.name}"
        })

        # 加载响应动作到队列
        for action in plan.immediate_actions:
            heapq.heappush(self.action_queue, (action.priority, action))

        # 生成通知列表
        notifications = self._generate_notifications(event, plan)

        # 生成响应指导
        guidance = self._generate_response_guidance(event, plan)

        return {
            'success': True,
            'event_id': event.id,
            'matched_plan': plan.id,
            'plan_name': plan.name,
            'emergency_level': event.level.value[0],
            'notifications': notifications,
            'immediate_actions': [
                {
                    'id': a.id,
                    'name': a.name,
                    'responsible': a.responsible,
                    'deadline': f"{a.deadline_minutes}分钟"
                }
                for a in plan.immediate_actions
            ],
            'guidance': guidance
        }

    def _generate_notifications(self, event: EmergencyEvent,
                                plan: EmergencyPlan) -> List[Dict]:
        """生成通知列表"""
        notifications = []
        for notify in plan.notification_list:
            notifications.append({
                'role': notify['role'],
                'method': notify['method'],
                'time_requirement': notify['time'],
                'message': f"【{event.level.value[1]}事件】{event.name}，请立即响应"
            })
        return notifications

    def _generate_response_guidance(self, event: EmergencyEvent,
                                    plan: EmergencyPlan) -> List[str]:
        """生成响应指导"""
        guidance = []

        # 基于事件等级的指导
        if event.level == EmergencyLevel.LEVEL_I:
            guidance.extend([
                "⚠️ 特别重大事件，立即启动一级响应",
                "⚠️ 总指挥亲自到场指挥",
                "⚠️ 所有应急力量全部投入",
                "⚠️ 向上级和政府部门报告"
            ])
        elif event.level == EmergencyLevel.LEVEL_II:
            guidance.extend([
                "⚠️ 重大事件，启动二级响应",
                "⚠️ 分管领导到场指挥",
                "⚠️ 主要应急力量投入"
            ])
        elif event.level == EmergencyLevel.LEVEL_III:
            guidance.extend([
                "较大事件，启动三级响应",
                "部门负责人组织处置",
                "相关专业力量投入"
            ])
        else:
            guidance.extend([
                "一般事件，启动四级响应",
                "值班人员按规程处置"
            ])

        # 基于事件类型的特殊指导
        if event.category == EventCategory.NATURAL_DISASTER:
            guidance.append("关注气象/地质部门后续预警")
            guidance.append("做好次生灾害防范")

        if event.category == EventCategory.FIRE:
            guidance.append("确保逃生通道畅通")
            guidance.append("注意防止复燃")

        return guidance

    def get_next_action(self) -> Optional[ResponseAction]:
        """获取下一个待执行动作"""
        if self.action_queue:
            _, action = heapq.heappop(self.action_queue)
            action.status = "in_progress"
            action.start_time = datetime.now()
            return action
        return None

    def complete_action(self, action_id: str, success: bool, notes: str = ""):
        """完成动作"""
        # 在实际实现中需要追踪所有动作
        pass

    def assess_situation(self, event_id: str) -> Dict[str, Any]:
        """评估事态"""
        event = self.active_events.get(event_id)
        if not event:
            return {'error': '事件不存在'}

        # 评估升级风险
        escalation_factors = []

        if len(event.affected_units) > 2:
            escalation_factors.append("多机组受影响")
            event.escalation_risk += 0.2

        if event.casualties > 0:
            escalation_factors.append("有人员伤亡")
            event.escalation_risk += 0.3

        if event.economic_loss > 1000000:
            escalation_factors.append("经济损失较大")
            event.escalation_risk += 0.1

        return {
            'event_id': event_id,
            'current_level': event.level.value[0],
            'current_phase': event.current_phase.value,
            'escalation_risk': event.escalation_risk,
            'escalation_factors': escalation_factors,
            'recommendation': self._get_escalation_recommendation(event)
        }

    def _get_escalation_recommendation(self, event: EmergencyEvent) -> str:
        """获取升级建议"""
        if event.escalation_risk > 0.7:
            return "建议立即升级响应等级"
        elif event.escalation_risk > 0.4:
            return "密切关注态势发展，准备升级"
        else:
            return "维持当前响应等级"

    def predict_progression(self, event_id: str, hours: int = 24) -> List[Dict]:
        """预测事态发展"""
        event = self.active_events.get(event_id)
        if not event:
            return []

        predictions = []

        # 基于事件类型和当前状态预测
        if event.category == EventCategory.NATURAL_DISASTER:
            predictions.append({
                'time': '+2小时',
                'scenario': '余震或次生灾害可能',
                'probability': 0.3,
                'recommendation': '保持警戒，准备二次响应'
            })

        if event.category == EventCategory.EQUIPMENT_FAILURE:
            predictions.append({
                'time': '+4小时',
                'scenario': '设备检查完成，可评估恢复',
                'probability': 0.7,
                'recommendation': '准备恢复运行方案'
            })

        predictions.append({
            'time': f'+{hours}小时',
            'scenario': '事件基本控制',
            'probability': 0.8 - event.escalation_risk,
            'recommendation': '进入恢复阶段'
        })

        return predictions

    def generate_recovery_plan(self, event_id: str) -> Dict[str, Any]:
        """生成恢复计划"""
        event = self.active_events.get(event_id)
        if not event:
            return {'error': '事件不存在'}

        recovery_steps = []

        # 通用恢复步骤
        recovery_steps.append({
            'step': 1,
            'name': '安全确认',
            'description': '确认事故现场安全，无次生风险',
            'estimated_time': '1-2小时'
        })

        recovery_steps.append({
            'step': 2,
            'name': '损伤评估',
            'description': '全面评估设备和设施损伤情况',
            'estimated_time': '2-4小时'
        })

        recovery_steps.append({
            'step': 3,
            'name': '修复方案',
            'description': '制定详细修复方案',
            'estimated_time': '2-4小时'
        })

        recovery_steps.append({
            'step': 4,
            'name': '实施修复',
            'description': '按方案实施修复工作',
            'estimated_time': '视损伤程度'
        })

        recovery_steps.append({
            'step': 5,
            'name': '功能验证',
            'description': '验证修复后功能正常',
            'estimated_time': '1-2小时'
        })

        recovery_steps.append({
            'step': 6,
            'name': '恢复运行',
            'description': '按程序恢复正常运行',
            'estimated_time': '2-4小时'
        })

        recovery_steps.append({
            'step': 7,
            'name': '总结评估',
            'description': '事件总结和经验教训',
            'estimated_time': '1周内'
        })

        return {
            'event_id': event_id,
            'recovery_steps': recovery_steps,
            'estimated_total_time': '视损伤程度确定',
            'key_resources': ['检修人员', '备品备件', '专业工具'],
            'risk_points': ['二次损伤风险', '人员安全风险']
        }


def main():
    """演示应急响应系统"""
    print("=" * 70)
    print("应急响应决策支持系统演示")
    print("=" * 70)

    # 创建协调器
    coordinator = EmergencyResponseCoordinator()

    # 场景1: 机组甩负荷
    print("\n场景1: 机组甩负荷事件")
    print("-" * 50)

    event1 = EmergencyEvent(
        id="EV-001",
        name="1号机组全甩负荷",
        category=EventCategory.EQUIPMENT_FAILURE,
        level=EmergencyLevel.LEVEL_III,
        start_time=datetime.now(),
        location="1号机组",
        description="1号机组运行中突然甩负荷，机组跳闸",
        affected_units=["1号机组"],
        affected_systems=["发电系统", "调速系统"]
    )

    response1 = coordinator.report_event(event1)
    print(f"事件等级: {response1['emergency_level']}")
    print(f"匹配预案: {response1['plan_name']}")
    print("\n立即执行动作:")
    for action in response1['immediate_actions']:
        print(f"  [{action['id']}] {action['name']} - {action['responsible']} ({action['deadline']})")

    print("\n通知列表:")
    for notify in response1['notifications'][:4]:
        print(f"  {notify['role']}: {notify['method']} ({notify['time_requirement']})")

    # 场景2: 地震
    print("\n" + "=" * 50)
    print("场景2: 地震事件")
    print("-" * 50)

    event2 = EmergencyEvent(
        id="EV-002",
        name="VII度地震",
        category=EventCategory.NATURAL_DISASTER,
        level=EmergencyLevel.LEVEL_II,
        start_time=datetime.now(),
        location="全厂",
        description="监测到VII度地震，触发地震停机程序",
        affected_units=["1号机组", "2号机组", "3号机组", "4号机组"],
        affected_systems=["全部系统"]
    )

    response2 = coordinator.report_event(event2)
    print(f"事件等级: {response2['emergency_level']}")
    print(f"匹配预案: {response2['plan_name']}")

    print("\n响应指导:")
    for guide in response2['guidance']:
        print(f"  • {guide}")

    print("\n立即执行动作:")
    for action in response2['immediate_actions'][:5]:
        print(f"  [{action['id']}] {action['name']} ({action['deadline']})")

    # 态势评估
    print("\n态势评估:")
    assessment = coordinator.assess_situation("EV-002")
    print(f"  当前等级: {assessment['current_level']}")
    print(f"  升级风险: {assessment['escalation_risk']:.1%}")
    print(f"  建议: {assessment['recommendation']}")

    # 态势预测
    print("\n态势预测:")
    predictions = coordinator.predict_progression("EV-002")
    for pred in predictions:
        print(f"  {pred['time']}: {pred['scenario']} (概率{pred['probability']:.0%})")

    # 恢复计划
    print("\n恢复计划:")
    recovery = coordinator.generate_recovery_plan("EV-002")
    for step in recovery['recovery_steps'][:4]:
        print(f"  步骤{step['step']}: {step['name']} ({step['estimated_time']})")

    print("\n" + "=" * 70)
    print("应急响应系统演示完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
