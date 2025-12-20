# -*- coding: utf-8 -*-
"""
场景覆盖评价 - 全场景智能化覆盖度评估
Scenario Coverage Evaluation - Full-scenario Intelligence Coverage Assessment

功能：
- 场景分类体系
- 覆盖度计算
- 缺口识别
- 优先级排序
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum


class ScenarioCategory(Enum):
    """场景类别"""
    # 正常运行场景
    NORMAL_STEADY = "normal_steady"             # 稳态运行
    NORMAL_TRANSIENT = "normal_transient"       # 正常过渡

    # 调节场景
    LOAD_CHANGE = "load_change"                 # 负荷调节
    FREQUENCY_REGULATION = "frequency_reg"      # 频率调节
    VOLTAGE_REGULATION = "voltage_reg"          # 电压调节
    START_STOP = "start_stop"                   # 启停操作

    # 异常场景
    EQUIPMENT_FAULT = "equipment_fault"         # 设备故障
    GRID_DISTURBANCE = "grid_disturbance"       # 电网扰动
    HYDRAULIC_ANOMALY = "hydraulic_anomaly"     # 水力异常

    # 极端场景
    NATURAL_DISASTER = "natural_disaster"       # 自然灾害
    CASCADING_FAILURE = "cascading_failure"     # 级联故障
    CYBER_ATTACK = "cyber_attack"               # 网络攻击
    BLACK_START = "black_start"                 # 黑启动

    # 特殊场景
    MAINTENANCE = "maintenance"                 # 检修维护
    TESTING = "testing"                         # 试验测试
    EMERGENCY_DRILL = "emergency_drill"         # 应急演练


class CoverageLevel(Enum):
    """覆盖等级"""
    NOT_COVERED = 0         # 未覆盖
    PARTIAL = 1             # 部分覆盖
    BASIC = 2               # 基本覆盖
    COMPLETE = 3            # 完全覆盖
    OPTIMIZED = 4           # 优化覆盖


@dataclass
class ScenarioDefinition:
    """场景定义"""
    scenario_id: str
    name: str
    category: ScenarioCategory
    description: str
    probability: float              # 发生概率
    severity: int                   # 严重程度 1-5
    priority: int                   # 优先级
    sub_scenarios: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)


@dataclass
class ScenarioCoverage:
    """场景覆盖状态"""
    scenario_id: str
    coverage_level: CoverageLevel
    score: float                    # 0-100
    implemented_functions: List[str]
    missing_functions: List[str]
    test_results: Dict[str, Any] = field(default_factory=dict)
    last_validated: Optional[datetime] = None


@dataclass
class CoverageResult:
    """覆盖评价结果"""
    evaluation_id: str
    timestamp: datetime
    overall_coverage: float         # 总体覆盖率 %
    category_coverage: Dict[ScenarioCategory, float]
    scenario_details: Dict[str, ScenarioCoverage]
    coverage_gaps: List[str]
    priority_improvements: List[str]


class ScenarioCoverageEvaluator:
    """
    场景覆盖评价器

    功能：
    - 场景库管理
    - 覆盖度评估
    - 缺口分析
    - 提升建议
    """

    def __init__(self):
        # 场景库
        self.scenarios: Dict[str, ScenarioDefinition] = {}

        # 覆盖状态
        self.coverage_status: Dict[str, ScenarioCoverage] = {}

        # 类别权重
        self.category_weights = {
            ScenarioCategory.NORMAL_STEADY: 1.0,
            ScenarioCategory.NORMAL_TRANSIENT: 1.0,
            ScenarioCategory.LOAD_CHANGE: 0.9,
            ScenarioCategory.FREQUENCY_REGULATION: 0.9,
            ScenarioCategory.VOLTAGE_REGULATION: 0.9,
            ScenarioCategory.START_STOP: 0.9,
            ScenarioCategory.EQUIPMENT_FAULT: 1.0,
            ScenarioCategory.GRID_DISTURBANCE: 0.9,
            ScenarioCategory.HYDRAULIC_ANOMALY: 1.0,
            ScenarioCategory.NATURAL_DISASTER: 0.8,
            ScenarioCategory.CASCADING_FAILURE: 0.8,
            ScenarioCategory.CYBER_ATTACK: 0.7,
            ScenarioCategory.BLACK_START: 0.6,
            ScenarioCategory.MAINTENANCE: 0.7,
            ScenarioCategory.TESTING: 0.5,
            ScenarioCategory.EMERGENCY_DRILL: 0.6,
        }

        # 初始化场景库
        self._initialize_scenarios()

    def _initialize_scenarios(self):
        """初始化场景库"""
        # 正常运行场景
        self._add_scenario(
            "S001", "额定工况稳态运行", ScenarioCategory.NORMAL_STEADY,
            "机组在额定出力下稳定运行", 0.7, 1, 1,
            sub_scenarios=["S001_1", "S001_2"],
            required_capabilities=["状态监测", "趋势分析"]
        )
        self._add_scenario(
            "S002", "部分负荷稳态运行", ScenarioCategory.NORMAL_STEADY,
            "机组在30%-90%负荷稳定运行", 0.2, 1, 2,
            required_capabilities=["效率优化", "振动监测"]
        )

        # 负荷调节场景
        self._add_scenario(
            "S101", "正常升负荷", ScenarioCategory.LOAD_CHANGE,
            "按正常速率升负荷", 0.3, 2, 1,
            required_capabilities=["负荷控制", "过程监测", "安全联锁"]
        )
        self._add_scenario(
            "S102", "正常降负荷", ScenarioCategory.LOAD_CHANGE,
            "按正常速率降负荷", 0.3, 2, 1,
            required_capabilities=["负荷控制", "水力过渡", "安全联锁"]
        )
        self._add_scenario(
            "S103", "快速负荷响应", ScenarioCategory.LOAD_CHANGE,
            "响应电网调度快速调节", 0.1, 3, 2,
            required_capabilities=["AGC", "快速响应", "稳定控制"]
        )

        # 频率调节场景
        self._add_scenario(
            "S201", "一次调频", ScenarioCategory.FREQUENCY_REGULATION,
            "响应频率偏差自动调节", 0.4, 2, 1,
            required_capabilities=["调速器控制", "死区设置", "出力限制"]
        )
        self._add_scenario(
            "S202", "二次调频AGC", ScenarioCategory.FREQUENCY_REGULATION,
            "接受AGC指令调节", 0.3, 2, 1,
            required_capabilities=["AGC接口", "负荷分配", "调节速率"]
        )

        # 启停场景
        self._add_scenario(
            "S301", "机组冷态启动", ScenarioCategory.START_STOP,
            "机组从停机状态启动", 0.05, 3, 1,
            required_capabilities=["启动控制", "同期并网", "保护投入"]
        )
        self._add_scenario(
            "S302", "机组正常停机", ScenarioCategory.START_STOP,
            "机组正常停机", 0.05, 2, 1,
            required_capabilities=["停机控制", "解列保护", "辅助系统"]
        )
        self._add_scenario(
            "S303", "机组热态启动", ScenarioCategory.START_STOP,
            "机组从备用状态快速启动", 0.03, 2, 2,
            required_capabilities=["快速启动", "同期并网"]
        )

        # 设备故障场景
        self._add_scenario(
            "S401", "轴承故障", ScenarioCategory.EQUIPMENT_FAULT,
            "导轴承/推力轴承异常", 0.02, 4, 1,
            sub_scenarios=["S401_1", "S401_2", "S401_3"],
            required_capabilities=["振动诊断", "温度监测", "保护动作"]
        )
        self._add_scenario(
            "S402", "定子故障", ScenarioCategory.EQUIPMENT_FAULT,
            "定子绕组/铁芯故障", 0.01, 5, 1,
            required_capabilities=["电气保护", "温度监测", "绝缘监测"]
        )
        self._add_scenario(
            "S403", "调速系统故障", ScenarioCategory.EQUIPMENT_FAULT,
            "调速器/油压系统故障", 0.02, 4, 1,
            required_capabilities=["调速诊断", "备用切换", "安全停机"]
        )
        self._add_scenario(
            "S404", "励磁系统故障", ScenarioCategory.EQUIPMENT_FAULT,
            "励磁调节器/可控硅故障", 0.02, 4, 1,
            required_capabilities=["励磁保护", "备用励磁", "失磁处理"]
        )

        # 水力异常场景
        self._add_scenario(
            "S501", "水锤冲击", ScenarioCategory.HYDRAULIC_ANOMALY,
            "导叶快关引发水锤", 0.01, 5, 1,
            required_capabilities=["压力监测", "关闭规律优化", "泄压保护"]
        )
        self._add_scenario(
            "S502", "空化振动", ScenarioCategory.HYDRAULIC_ANOMALY,
            "不良工况区运行引发空化", 0.03, 3, 2,
            required_capabilities=["振动监测", "工况优化", "运行限制"]
        )
        self._add_scenario(
            "S503", "水位异常", ScenarioCategory.HYDRAULIC_ANOMALY,
            "上游/下游水位异常变化", 0.02, 4, 1,
            required_capabilities=["水位监测", "出力调整", "安全保护"]
        )

        # 电网扰动场景
        self._add_scenario(
            "S601", "电网短路故障", ScenarioCategory.GRID_DISTURBANCE,
            "外部电网短路", 0.05, 4, 1,
            required_capabilities=["故障穿越", "保护配合", "稳定控制"]
        )
        self._add_scenario(
            "S602", "电网振荡", ScenarioCategory.GRID_DISTURBANCE,
            "电力系统低频振荡", 0.02, 4, 2,
            required_capabilities=["振荡检测", "PSS调节", "紧急控制"]
        )
        self._add_scenario(
            "S603", "系统解列", ScenarioCategory.GRID_DISTURBANCE,
            "与主网解列孤网运行", 0.01, 5, 1,
            required_capabilities=["解列检测", "孤网控制", "负荷平衡"]
        )

        # 自然灾害场景
        self._add_scenario(
            "S701", "地震", ScenarioCategory.NATURAL_DISASTER,
            "地震灾害", 0.001, 5, 1,
            required_capabilities=["地震监测", "紧急停机", "结构评估"]
        )
        self._add_scenario(
            "S702", "洪水", ScenarioCategory.NATURAL_DISASTER,
            "上游来水异常增大", 0.01, 5, 1,
            required_capabilities=["洪水预报", "泄洪调度", "安全撤离"]
        )
        self._add_scenario(
            "S703", "泥石流/滑坡", ScenarioCategory.NATURAL_DISASTER,
            "库区地质灾害", 0.005, 5, 1,
            required_capabilities=["监测预警", "库区管理", "应急响应"]
        )

        # 级联故障场景
        self._add_scenario(
            "S801", "多机组同时故障", ScenarioCategory.CASCADING_FAILURE,
            "多台机组同时跳闸", 0.001, 5, 1,
            required_capabilities=["故障隔离", "负荷转移", "系统稳定"]
        )
        self._add_scenario(
            "S802", "主变-线路连锁故障", ScenarioCategory.CASCADING_FAILURE,
            "主变故障引发线路跳闸", 0.002, 5, 1,
            required_capabilities=["保护配合", "备用投入", "负荷控制"]
        )

        # 网络安全场景
        self._add_scenario(
            "S901", "网络入侵检测", ScenarioCategory.CYBER_ATTACK,
            "外部网络攻击尝试", 0.02, 4, 1,
            required_capabilities=["入侵检测", "访问控制", "隔离措施"]
        )
        self._add_scenario(
            "S902", "恶意指令识别", ScenarioCategory.CYBER_ATTACK,
            "识别异常控制指令", 0.01, 5, 1,
            required_capabilities=["指令校验", "行为分析", "安全联锁"]
        )

        # 黑启动场景
        self._add_scenario(
            "S1001", "独立黑启动", ScenarioCategory.BLACK_START,
            "电网全黑后独立启动", 0.001, 5, 1,
            required_capabilities=["自启动能力", "小网控制", "负荷恢复"]
        )

        # 检修场景
        self._add_scenario(
            "S1101", "在线检修", ScenarioCategory.MAINTENANCE,
            "机组在线状态下辅助设备检修", 0.1, 2, 2,
            required_capabilities=["状态评估", "风险分析", "在线监测"]
        )
        self._add_scenario(
            "S1102", "大修后投运", ScenarioCategory.MAINTENANCE,
            "机组大修后重新投入运行", 0.02, 3, 1,
            required_capabilities=["试验验证", "性能评估", "保护整定"]
        )

    def _add_scenario(self, scenario_id: str, name: str,
                      category: ScenarioCategory,
                      description: str, probability: float,
                      severity: int, priority: int,
                      sub_scenarios: List[str] = None,
                      required_capabilities: List[str] = None):
        """添加场景"""
        self.scenarios[scenario_id] = ScenarioDefinition(
            scenario_id=scenario_id,
            name=name,
            category=category,
            description=description,
            probability=probability,
            severity=severity,
            priority=priority,
            sub_scenarios=sub_scenarios or [],
            required_capabilities=required_capabilities or [],
        )

    def update_coverage(self, scenario_id: str,
                        implemented_functions: List[str],
                        test_results: Dict[str, Any] = None):
        """
        更新场景覆盖状态

        Args:
            scenario_id: 场景ID
            implemented_functions: 已实现功能列表
            test_results: 测试结果
        """
        if scenario_id not in self.scenarios:
            return

        scenario = self.scenarios[scenario_id]
        required = set(scenario.required_capabilities)
        implemented = set(implemented_functions)

        # 计算覆盖程度
        if not required:
            coverage_ratio = 1.0
        else:
            coverage_ratio = len(required & implemented) / len(required)

        # 确定覆盖等级
        if coverage_ratio == 0:
            level = CoverageLevel.NOT_COVERED
        elif coverage_ratio < 0.5:
            level = CoverageLevel.PARTIAL
        elif coverage_ratio < 0.8:
            level = CoverageLevel.BASIC
        elif coverage_ratio < 1.0:
            level = CoverageLevel.COMPLETE
        else:
            # 检查是否有优化
            if test_results and test_results.get("optimized", False):
                level = CoverageLevel.OPTIMIZED
            else:
                level = CoverageLevel.COMPLETE

        # 计算得分
        score = coverage_ratio * 100
        if test_results:
            test_score = test_results.get("score", 100)
            score = score * 0.7 + test_score * 0.3

        self.coverage_status[scenario_id] = ScenarioCoverage(
            scenario_id=scenario_id,
            coverage_level=level,
            score=score,
            implemented_functions=list(implemented),
            missing_functions=list(required - implemented),
            test_results=test_results or {},
            last_validated=datetime.now() if test_results else None,
        )

    def evaluate(self) -> CoverageResult:
        """执行覆盖度评价"""
        evaluation_id = f"COV_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 按类别统计
        category_scores: Dict[ScenarioCategory, List[float]] = {}
        for scenario in self.scenarios.values():
            cat = scenario.category
            if cat not in category_scores:
                category_scores[cat] = []

            coverage = self.coverage_status.get(scenario.scenario_id)
            score = coverage.score if coverage else 0
            category_scores[cat].append(score)

        # 计算类别覆盖率
        category_coverage = {}
        for cat, scores in category_scores.items():
            category_coverage[cat] = np.mean(scores) if scores else 0

        # 加权总体覆盖率
        total_weight = 0
        weighted_sum = 0
        for cat, cov in category_coverage.items():
            weight = self.category_weights.get(cat, 1.0)
            weighted_sum += cov * weight
            total_weight += weight

        overall_coverage = weighted_sum / total_weight if total_weight > 0 else 0

        # 识别覆盖缺口
        gaps = []
        priority_improvements = []

        for scenario_id, scenario in self.scenarios.items():
            coverage = self.coverage_status.get(scenario_id)
            if not coverage or coverage.coverage_level in [CoverageLevel.NOT_COVERED, CoverageLevel.PARTIAL]:
                gap_desc = f"{scenario.name}（{scenario.category.value}）"
                if coverage and coverage.missing_functions:
                    gap_desc += f"：缺少{', '.join(coverage.missing_functions[:3])}"
                gaps.append(gap_desc)

                if scenario.priority == 1:
                    priority_improvements.append(f"优先实现{scenario.name}场景覆盖")

        # 按优先级排序
        gaps.sort(key=lambda x: next(
            (s.priority for s in self.scenarios.values() if s.name in x), 99
        ))

        return CoverageResult(
            evaluation_id=evaluation_id,
            timestamp=datetime.now(),
            overall_coverage=overall_coverage,
            category_coverage=category_coverage,
            scenario_details=self.coverage_status.copy(),
            coverage_gaps=gaps[:20],
            priority_improvements=priority_improvements[:10],
        )

    def get_uncovered_scenarios(self, priority: int = None) -> List[ScenarioDefinition]:
        """获取未覆盖场景列表"""
        uncovered = []

        for scenario_id, scenario in self.scenarios.items():
            coverage = self.coverage_status.get(scenario_id)
            if not coverage or coverage.coverage_level == CoverageLevel.NOT_COVERED:
                if priority is None or scenario.priority <= priority:
                    uncovered.append(scenario)

        return sorted(uncovered, key=lambda s: (s.priority, -s.severity))

    def get_coverage_by_category(self) -> Dict[str, Dict[str, Any]]:
        """按类别获取覆盖情况"""
        result = {}

        for cat in ScenarioCategory:
            cat_scenarios = [s for s in self.scenarios.values() if s.category == cat]
            covered = sum(
                1 for s in cat_scenarios
                if s.scenario_id in self.coverage_status
                and self.coverage_status[s.scenario_id].coverage_level.value >= CoverageLevel.BASIC.value
            )

            result[cat.value] = {
                "total": len(cat_scenarios),
                "covered": covered,
                "coverage_rate": covered / len(cat_scenarios) * 100 if cat_scenarios else 0,
            }

        return result

