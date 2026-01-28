# -*- coding: utf-8 -*-
"""
ODD识别体系 - ODD Identification System

完整的ODD扫描、识别与管理体系：
- 规则驱动的ODD边界扫描
- 自动ODD识别与分类
- ODD状态机管理
- ODD覆盖率分析
- ODD违规检测与预警

参考：YX工程面向运行能力的设计评估与运行逻辑验证关键技术研究
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable, Set, Union
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import logging
import json
import re

logger = logging.getLogger(__name__)


class ODDRuleType(Enum):
    """ODD规则类型"""
    BOUNDARY = "boundary"           # 边界规则
    RATE = "rate"                   # 变化率规则
    DURATION = "duration"           # 持续时间规则
    COMBINATION = "combination"     # 组合规则
    SEQUENCE = "sequence"           # 序列规则
    CORRELATION = "correlation"     # 相关性规则
    PROTECTION = "protection"       # 保护规则


class ODDScanMode(Enum):
    """ODD扫描模式"""
    REAL_TIME = "real_time"         # 实时扫描
    BATCH = "batch"                 # 批量扫描
    RETROSPECTIVE = "retrospective" # 回溯扫描
    PREDICTIVE = "predictive"       # 预测扫描


class ODDViolationSeverity(Enum):
    """ODD违规严重程度"""
    INFO = 0                        # 信息
    WARNING = 1                     # 警告
    MINOR = 2                       # 轻微违规
    MAJOR = 3                       # 主要违规
    CRITICAL = 4                    # 严重违规
    EMERGENCY = 5                   # 紧急违规


class ODDStateTransition(Enum):
    """ODD状态转换"""
    UPGRADE = "upgrade"             # 升级（恢复）
    MAINTAIN = "maintain"           # 维持
    DEGRADE = "degrade"             # 降级
    EMERGENCY_STOP = "emergency_stop"  # 紧急停止


@dataclass
class ODDRule:
    """ODD规则定义"""
    rule_id: str
    name: str
    description: str
    rule_type: ODDRuleType

    # 规则表达式
    condition: str                  # 条件表达式
    threshold: float = None         # 阈值
    lower_bound: float = None       # 下限
    upper_bound: float = None       # 上限

    # 规则参数
    parameters: Dict[str, Any] = field(default_factory=dict)

    # 关联变量
    variables: List[str] = field(default_factory=list)

    # 违规处理
    severity: ODDViolationSeverity = ODDViolationSeverity.WARNING
    action: str = ""                # 建议动作

    # 启用状态
    enabled: bool = True

    # 优先级
    priority: int = 1


@dataclass
class ODDViolation:
    """ODD违规记录"""
    violation_id: str
    timestamp: datetime
    rule: ODDRule
    severity: ODDViolationSeverity

    # 违规详情
    actual_value: float
    expected_range: Tuple[float, float]
    deviation: float

    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)

    # 状态
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: datetime = None


@dataclass
class ODDScanResult:
    """ODD扫描结果"""
    scan_id: str
    timestamp: datetime
    scan_mode: ODDScanMode
    duration_ms: float

    # 结果统计
    total_rules_checked: int
    violations_found: int
    warnings_found: int

    # 详细结果
    violations: List[ODDViolation] = field(default_factory=list)
    zone_distribution: Dict[str, float] = field(default_factory=dict)

    # 覆盖率
    coverage: float = 0.0

    # 建议
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ODDState:
    """ODD状态"""
    state_id: str
    zone: str                       # 当前区域
    degradation_level: int          # 降级等级

    # 时间信息
    entered_at: datetime
    duration: timedelta = field(default_factory=lambda: timedelta())

    # 边界距离
    distance_to_boundary: Dict[str, float] = field(default_factory=dict)

    # 活跃违规
    active_violations: List[str] = field(default_factory=list)

    # 趋势
    trend: str = "stable"           # rising, falling, stable


class ODDRuleEngine:
    """
    ODD规则引擎

    基于规则的ODD边界扫描和识别
    """

    def __init__(self):
        self.rules: Dict[str, ODDRule] = {}
        self.rule_groups: Dict[str, List[str]] = {}
        self.evaluation_cache: Dict[str, Any] = {}

    def add_rule(self, rule: ODDRule):
        """添加规则"""
        self.rules[rule.rule_id] = rule
        logger.info(f"添加ODD规则: {rule.name}")

    def add_rule_group(self, group_name: str, rule_ids: List[str]):
        """添加规则组"""
        self.rule_groups[group_name] = rule_ids

    def evaluate_rule(self, rule: ODDRule,
                      state: Dict[str, float]) -> Tuple[bool, Dict[str, Any]]:
        """
        评估单条规则

        Args:
            rule: ODD规则
            state: 当前状态

        Returns:
            (是否满足, 评估详情)
        """
        if not rule.enabled:
            return True, {"status": "disabled"}

        result = {"rule_id": rule.rule_id, "rule_name": rule.name}

        try:
            if rule.rule_type == ODDRuleType.BOUNDARY:
                satisfied, details = self._evaluate_boundary_rule(rule, state)
            elif rule.rule_type == ODDRuleType.RATE:
                satisfied, details = self._evaluate_rate_rule(rule, state)
            elif rule.rule_type == ODDRuleType.DURATION:
                satisfied, details = self._evaluate_duration_rule(rule, state)
            elif rule.rule_type == ODDRuleType.COMBINATION:
                satisfied, details = self._evaluate_combination_rule(rule, state)
            elif rule.rule_type == ODDRuleType.CORRELATION:
                satisfied, details = self._evaluate_correlation_rule(rule, state)
            elif rule.rule_type == ODDRuleType.PROTECTION:
                satisfied, details = self._evaluate_protection_rule(rule, state)
            else:
                satisfied = True
                details = {"status": "unknown_rule_type"}

            result.update(details)
            result["satisfied"] = satisfied

        except Exception as e:
            logger.error(f"规则评估失败 {rule.rule_id}: {e}")
            result["satisfied"] = False
            result["error"] = str(e)
            satisfied = False

        return satisfied, result

    def _evaluate_boundary_rule(self, rule: ODDRule,
                                 state: Dict[str, float]) -> Tuple[bool, Dict]:
        """评估边界规则"""
        details = {"type": "boundary"}

        for var in rule.variables:
            value = state.get(var)
            if value is None:
                continue

            lower = rule.lower_bound
            upper = rule.upper_bound

            details[var] = {
                "value": value,
                "lower_bound": lower,
                "upper_bound": upper,
            }

            if lower is not None and value < lower:
                details[var]["violation"] = "below_lower"
                details[var]["deviation"] = lower - value
                return False, details

            if upper is not None and value > upper:
                details[var]["violation"] = "above_upper"
                details[var]["deviation"] = value - upper
                return False, details

        return True, details

    def _evaluate_rate_rule(self, rule: ODDRule,
                            state: Dict[str, float]) -> Tuple[bool, Dict]:
        """评估变化率规则"""
        details = {"type": "rate"}

        for var in rule.variables:
            rate_var = f"{var}_rate"
            rate = state.get(rate_var, 0)

            max_rate = rule.parameters.get("max_rate", float('inf'))
            min_rate = rule.parameters.get("min_rate", -float('inf'))

            details[var] = {
                "rate": rate,
                "max_rate": max_rate,
                "min_rate": min_rate,
            }

            if rate > max_rate:
                details[var]["violation"] = "rate_too_high"
                return False, details

            if rate < min_rate:
                details[var]["violation"] = "rate_too_low"
                return False, details

        return True, details

    def _evaluate_duration_rule(self, rule: ODDRule,
                                state: Dict[str, float]) -> Tuple[bool, Dict]:
        """评估持续时间规则"""
        details = {"type": "duration"}

        zone = state.get("current_zone", "normal")
        zone_duration = state.get("zone_duration", 0)

        max_duration = rule.parameters.get(f"max_duration_{zone}", float('inf'))

        details["zone"] = zone
        details["duration"] = zone_duration
        details["max_duration"] = max_duration

        if zone_duration > max_duration:
            details["violation"] = "duration_exceeded"
            return False, details

        return True, details

    def _evaluate_combination_rule(self, rule: ODDRule,
                                   state: Dict[str, float]) -> Tuple[bool, Dict]:
        """评估组合规则"""
        details = {"type": "combination"}

        # 解析组合条件
        condition = rule.condition
        sub_conditions = rule.parameters.get("sub_conditions", [])

        results = []
        for i, sub in enumerate(sub_conditions):
            var = sub.get("variable")
            op = sub.get("operator", "<=")
            threshold = sub.get("threshold")

            value = state.get(var)
            if value is None:
                continue

            if op == "<=":
                result = value <= threshold
            elif op == ">=":
                result = value >= threshold
            elif op == "<":
                result = value < threshold
            elif op == ">":
                result = value > threshold
            elif op == "==":
                result = abs(value - threshold) < 1e-6
            else:
                result = True

            results.append(result)
            details[f"condition_{i}"] = {
                "variable": var,
                "operator": op,
                "threshold": threshold,
                "value": value,
                "result": result,
            }

        # 组合逻辑
        logic = rule.parameters.get("logic", "AND")
        if logic == "AND":
            satisfied = all(results) if results else True
        elif logic == "OR":
            satisfied = any(results) if results else True
        else:
            satisfied = all(results) if results else True

        details["logic"] = logic
        details["satisfied"] = satisfied

        return satisfied, details

    def _evaluate_correlation_rule(self, rule: ODDRule,
                                   state: Dict[str, float]) -> Tuple[bool, Dict]:
        """评估相关性规则"""
        details = {"type": "correlation"}

        if len(rule.variables) < 2:
            return True, details

        var1, var2 = rule.variables[0], rule.variables[1]
        value1 = state.get(var1)
        value2 = state.get(var2)

        if value1 is None or value2 is None:
            return True, details

        # 计算相关系数或差值
        correlation_type = rule.parameters.get("correlation_type", "ratio")
        max_deviation = rule.parameters.get("max_deviation", 0.1)

        if correlation_type == "ratio":
            if value2 != 0:
                ratio = value1 / value2
                expected_ratio = rule.parameters.get("expected_ratio", 1.0)
                deviation = abs(ratio - expected_ratio) / expected_ratio
            else:
                deviation = float('inf')

            details["ratio"] = ratio if value2 != 0 else None
            details["expected_ratio"] = rule.parameters.get("expected_ratio", 1.0)
            details["deviation"] = deviation

        elif correlation_type == "difference":
            diff = abs(value1 - value2)
            max_diff = rule.parameters.get("max_difference", 10)
            deviation = diff / max_diff if max_diff > 0 else 0

            details["difference"] = diff
            details["max_difference"] = max_diff
            details["deviation"] = deviation

        if deviation > max_deviation:
            details["violation"] = "correlation_exceeded"
            return False, details

        return True, details

    def _evaluate_protection_rule(self, rule: ODDRule,
                                  state: Dict[str, float]) -> Tuple[bool, Dict]:
        """评估保护规则"""
        details = {"type": "protection"}

        protection_var = rule.parameters.get("protection_variable")
        trigger_threshold = rule.parameters.get("trigger_threshold")
        protection_action = rule.parameters.get("protection_action", "shutdown")

        value = state.get(protection_var)
        if value is None:
            return True, details

        details["protection_variable"] = protection_var
        details["value"] = value
        details["trigger_threshold"] = trigger_threshold

        triggered = False
        trigger_type = rule.parameters.get("trigger_type", "above")

        if trigger_type == "above" and value > trigger_threshold:
            triggered = True
        elif trigger_type == "below" and value < trigger_threshold:
            triggered = True

        if triggered:
            details["protection_triggered"] = True
            details["action"] = protection_action
            return False, details

        return True, details

    def evaluate_all_rules(self, state: Dict[str, float]) -> List[Tuple[bool, Dict]]:
        """评估所有规则"""
        results = []
        for rule in self.rules.values():
            result = self.evaluate_rule(rule, state)
            results.append(result)
        return results

    def evaluate_rule_group(self, group_name: str,
                           state: Dict[str, float]) -> List[Tuple[bool, Dict]]:
        """评估规则组"""
        results = []
        rule_ids = self.rule_groups.get(group_name, [])
        for rule_id in rule_ids:
            if rule_id in self.rules:
                result = self.evaluate_rule(self.rules[rule_id], state)
                results.append(result)
        return results


class ODDScanner:
    """
    ODD扫描器

    执行ODD边界扫描和状态识别
    """

    def __init__(self, rule_engine: ODDRuleEngine):
        self.rule_engine = rule_engine
        self.scan_history: List[ODDScanResult] = []
        self.violation_history: List[ODDViolation] = []

    def scan(self, state: Dict[str, float],
             mode: ODDScanMode = ODDScanMode.REAL_TIME) -> ODDScanResult:
        """
        执行ODD扫描

        Args:
            state: 当前状态
            mode: 扫描模式

        Returns:
            扫描结果
        """
        start_time = datetime.now()

        # 评估所有规则
        results = self.rule_engine.evaluate_all_rules(state)

        # 统计
        total_rules = len(results)
        violations = []
        warnings = []

        for satisfied, details in results:
            if not satisfied:
                rule_id = details.get("rule_id")
                rule = self.rule_engine.rules.get(rule_id)
                if rule:
                    severity = rule.severity
                    if severity.value >= ODDViolationSeverity.MINOR.value:
                        violation = self._create_violation(rule, details, state)
                        violations.append(violation)
                    else:
                        warnings.append(details)

        # 计算区域分布
        zone_distribution = self._calculate_zone_distribution(state)

        # 计算覆盖率
        coverage = self._calculate_coverage(results)

        # 生成建议
        recommendations = self._generate_recommendations(violations, state)

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        scan_result = ODDScanResult(
            scan_id=f"scan_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            timestamp=datetime.now(),
            scan_mode=mode,
            duration_ms=duration_ms,
            total_rules_checked=total_rules,
            violations_found=len(violations),
            warnings_found=len(warnings),
            violations=violations,
            zone_distribution=zone_distribution,
            coverage=coverage,
            recommendations=recommendations,
        )

        self.scan_history.append(scan_result)
        self.violation_history.extend(violations)

        return scan_result

    def scan_batch(self, states: List[Dict[str, float]],
                   timestamps: List[datetime] = None) -> List[ODDScanResult]:
        """批量扫描"""
        results = []
        for i, state in enumerate(states):
            result = self.scan(state, ODDScanMode.BATCH)
            if timestamps and i < len(timestamps):
                result.timestamp = timestamps[i]
            results.append(result)
        return results

    def scan_predictive(self, current_state: Dict[str, float],
                        prediction_horizon: int = 10,
                        dt: float = 1.0) -> ODDScanResult:
        """
        预测性扫描

        基于当前状态和变化率预测未来ODD状态
        """
        predicted_violations = []

        for step in range(1, prediction_horizon + 1):
            t = step * dt
            predicted_state = self._predict_state(current_state, t)

            results = self.rule_engine.evaluate_all_rules(predicted_state)

            for satisfied, details in results:
                if not satisfied:
                    rule_id = details.get("rule_id")
                    rule = self.rule_engine.rules.get(rule_id)
                    if rule and rule.severity.value >= ODDViolationSeverity.WARNING.value:
                        violation = self._create_violation(rule, details, predicted_state)
                        violation.context["predicted_time"] = t
                        predicted_violations.append(violation)

        scan_result = ODDScanResult(
            scan_id=f"pred_scan_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            timestamp=datetime.now(),
            scan_mode=ODDScanMode.PREDICTIVE,
            duration_ms=0,
            total_rules_checked=len(self.rule_engine.rules) * prediction_horizon,
            violations_found=len(predicted_violations),
            warnings_found=0,
            violations=predicted_violations,
            coverage=0,
            recommendations=self._generate_predictive_recommendations(predicted_violations),
        )

        return scan_result

    def _predict_state(self, current_state: Dict[str, float],
                       t: float) -> Dict[str, float]:
        """基于变化率预测状态"""
        predicted = current_state.copy()

        for var, value in current_state.items():
            if var.endswith("_rate"):
                continue
            rate_var = f"{var}_rate"
            rate = current_state.get(rate_var, 0)
            predicted[var] = value + rate * t

        return predicted

    def _create_violation(self, rule: ODDRule,
                          details: Dict[str, Any],
                          state: Dict[str, float]) -> ODDViolation:
        """创建违规记录"""
        # 提取违规值和范围
        actual_value = 0
        expected_range = (rule.lower_bound or 0, rule.upper_bound or 0)
        deviation = 0

        for var in rule.variables:
            if var in details:
                var_details = details[var]
                if isinstance(var_details, dict):
                    actual_value = var_details.get("value", 0)
                    deviation = var_details.get("deviation", 0)
                    if "lower_bound" in var_details:
                        expected_range = (
                            var_details.get("lower_bound", 0),
                            var_details.get("upper_bound", 0)
                        )

        return ODDViolation(
            violation_id=f"v_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            timestamp=datetime.now(),
            rule=rule,
            severity=rule.severity,
            actual_value=actual_value,
            expected_range=expected_range,
            deviation=deviation,
            context={"state": state, "details": details},
        )

    def _calculate_zone_distribution(self,
                                     state: Dict[str, float]) -> Dict[str, float]:
        """计算区域分布"""
        zones = {
            "optimal": 0.0,
            "normal": 0.0,
            "degraded": 0.0,
            "restricted": 0.0,
            "emergency": 0.0,
            "forbidden": 0.0,
        }

        # 基于边界规则评估各变量所在区域
        boundary_rules = [r for r in self.rule_engine.rules.values()
                         if r.rule_type == ODDRuleType.BOUNDARY]

        for rule in boundary_rules:
            for var in rule.variables:
                value = state.get(var)
                if value is None:
                    continue

                zone = self._determine_zone(value, rule)
                zones[zone] = zones.get(zone, 0) + 1

        # 归一化
        total = sum(zones.values())
        if total > 0:
            zones = {k: v / total * 100 for k, v in zones.items()}

        return zones

    def _determine_zone(self, value: float, rule: ODDRule) -> str:
        """确定值所在区域"""
        params = rule.parameters

        # 从规则参数中获取各区域边界
        optimal_range = params.get("optimal_range", (rule.lower_bound, rule.upper_bound))
        normal_range = params.get("normal_range", optimal_range)
        degraded_range = params.get("degraded_range", normal_range)
        emergency_range = params.get("emergency_range", degraded_range)

        if optimal_range[0] <= value <= optimal_range[1]:
            return "optimal"
        elif normal_range[0] <= value <= normal_range[1]:
            return "normal"
        elif degraded_range[0] <= value <= degraded_range[1]:
            return "degraded"
        elif emergency_range[0] <= value <= emergency_range[1]:
            return "emergency"
        else:
            return "forbidden"

    def _calculate_coverage(self,
                           results: List[Tuple[bool, Dict]]) -> float:
        """计算ODD覆盖率"""
        if not results:
            return 0.0

        satisfied = sum(1 for sat, _ in results if sat)
        return satisfied / len(results) * 100

    def _generate_recommendations(self,
                                  violations: List[ODDViolation],
                                  state: Dict[str, float]) -> List[str]:
        """生成建议"""
        recommendations = []

        severity_counts = {}
        for v in violations:
            severity_counts[v.severity.name] = severity_counts.get(v.severity.name, 0) + 1

        if ODDViolationSeverity.EMERGENCY.name in severity_counts:
            recommendations.append("紧急：存在紧急违规，建议立即采取保护措施")

        if ODDViolationSeverity.CRITICAL.name in severity_counts:
            recommendations.append("严重：存在严重违规，建议启动降级策略")

        if len(violations) > 5:
            recommendations.append("多项违规：建议全面检查系统状态")

        # 根据具体违规生成建议
        for v in violations[:3]:  # 只处理前3个
            if v.rule.action:
                recommendations.append(f"{v.rule.name}: {v.rule.action}")

        return recommendations

    def _generate_predictive_recommendations(self,
                                            violations: List[ODDViolation]) -> List[str]:
        """生成预测性建议"""
        recommendations = []

        if violations:
            first_violation_time = min(
                v.context.get("predicted_time", 0) for v in violations
            )
            recommendations.append(
                f"预警：预计{first_violation_time:.1f}秒后可能发生ODD违规"
            )

            # 按时间排序
            sorted_violations = sorted(
                violations,
                key=lambda v: v.context.get("predicted_time", 0)
            )

            for v in sorted_violations[:3]:
                t = v.context.get("predicted_time", 0)
                recommendations.append(
                    f"预计{t:.1f}秒后: {v.rule.name} 可能违规"
                )

        return recommendations


class ODDStateMachine:
    """
    ODD状态机

    管理ODD状态转换和降级策略
    """

    def __init__(self):
        self.current_state: ODDState = None
        self.state_history: List[ODDState] = []
        self.transition_rules: Dict[str, Dict] = {}

        self._init_default_transitions()

    def _init_default_transitions(self):
        """初始化默认状态转换规则"""
        self.transition_rules = {
            "optimal": {
                "normal": {"trigger": "boundary_approach", "delay": 0},
                "degraded": {"trigger": "boundary_violation", "delay": 5},
                "emergency": {"trigger": "critical_violation", "delay": 0},
            },
            "normal": {
                "optimal": {"trigger": "return_to_optimal", "delay": 60},
                "degraded": {"trigger": "boundary_violation", "delay": 10},
                "emergency": {"trigger": "critical_violation", "delay": 0},
            },
            "degraded": {
                "normal": {"trigger": "return_to_normal", "delay": 120},
                "restricted": {"trigger": "continued_violation", "delay": 30},
                "emergency": {"trigger": "critical_violation", "delay": 0},
            },
            "restricted": {
                "degraded": {"trigger": "partial_recovery", "delay": 180},
                "emergency": {"trigger": "critical_violation", "delay": 0},
                "forbidden": {"trigger": "protection_trigger", "delay": 0},
            },
            "emergency": {
                "restricted": {"trigger": "emergency_stabilized", "delay": 300},
                "forbidden": {"trigger": "protection_trigger", "delay": 0},
            },
            "forbidden": {
                "emergency": {"trigger": "manual_recovery", "delay": 600},
            },
        }

    def initialize(self, initial_zone: str = "normal"):
        """初始化状态"""
        self.current_state = ODDState(
            state_id=f"state_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            zone=initial_zone,
            degradation_level=self._zone_to_level(initial_zone),
            entered_at=datetime.now(),
        )

    def update(self, scan_result: ODDScanResult) -> ODDStateTransition:
        """
        根据扫描结果更新状态

        Returns:
            状态转换类型
        """
        if self.current_state is None:
            self.initialize()

        old_zone = self.current_state.zone
        new_zone = self._determine_zone(scan_result)

        # 更新时间
        self.current_state.duration = datetime.now() - self.current_state.entered_at

        # 更新活跃违规
        self.current_state.active_violations = [
            v.violation_id for v in scan_result.violations
        ]

        # 更新趋势
        self.current_state.trend = self._determine_trend(scan_result)

        # 确定转换类型
        transition = self._determine_transition(old_zone, new_zone)

        # 执行转换
        if transition != ODDStateTransition.MAINTAIN:
            self._execute_transition(new_zone)

        return transition

    def _determine_zone(self, scan_result: ODDScanResult) -> str:
        """根据扫描结果确定区域"""
        if scan_result.violations_found == 0:
            return "optimal"

        max_severity = max(
            (v.severity.value for v in scan_result.violations),
            default=0
        )

        if max_severity >= ODDViolationSeverity.EMERGENCY.value:
            return "forbidden"
        elif max_severity >= ODDViolationSeverity.CRITICAL.value:
            return "emergency"
        elif max_severity >= ODDViolationSeverity.MAJOR.value:
            return "restricted"
        elif max_severity >= ODDViolationSeverity.MINOR.value:
            return "degraded"
        else:
            return "normal"

    def _determine_transition(self, old_zone: str,
                              new_zone: str) -> ODDStateTransition:
        """确定状态转换类型"""
        zone_order = ["optimal", "normal", "degraded", "restricted", "emergency", "forbidden"]

        try:
            old_idx = zone_order.index(old_zone)
            new_idx = zone_order.index(new_zone)
        except ValueError:
            return ODDStateTransition.MAINTAIN

        if new_idx > old_idx:
            if new_zone == "forbidden":
                return ODDStateTransition.EMERGENCY_STOP
            return ODDStateTransition.DEGRADE
        elif new_idx < old_idx:
            return ODDStateTransition.UPGRADE
        else:
            return ODDStateTransition.MAINTAIN

    def _execute_transition(self, new_zone: str):
        """执行状态转换"""
        # 保存历史
        self.state_history.append(self.current_state)

        # 创建新状态
        self.current_state = ODDState(
            state_id=f"state_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            zone=new_zone,
            degradation_level=self._zone_to_level(new_zone),
            entered_at=datetime.now(),
        )

        logger.info(f"ODD状态转换: {self.state_history[-1].zone} -> {new_zone}")

    def _zone_to_level(self, zone: str) -> int:
        """区域到降级等级"""
        mapping = {
            "optimal": 0,
            "normal": 1,
            "degraded": 2,
            "restricted": 3,
            "emergency": 4,
            "forbidden": 5,
        }
        return mapping.get(zone, 1)

    def _determine_trend(self, scan_result: ODDScanResult) -> str:
        """确定趋势"""
        if len(self.state_history) < 2:
            return "stable"

        recent_violations = [
            len(self.state_history[-1].active_violations),
            len(self.current_state.active_violations),
        ]

        if recent_violations[-1] > recent_violations[-2]:
            return "deteriorating"
        elif recent_violations[-1] < recent_violations[-2]:
            return "improving"
        else:
            return "stable"

    def get_allowed_actions(self) -> List[str]:
        """获取当前状态允许的动作"""
        zone = self.current_state.zone if self.current_state else "normal"

        actions = {
            "optimal": [
                "full_capacity_operation",
                "economic_optimization",
                "all_adjustments_allowed",
            ],
            "normal": [
                "normal_operation",
                "standard_adjustments",
                "moderate_optimization",
            ],
            "degraded": [
                "reduced_capacity",
                "conservative_control",
                "limited_adjustments",
            ],
            "restricted": [
                "minimum_adjustments",
                "safety_priority",
                "prepare_emergency_shutdown",
            ],
            "emergency": [
                "emergency_protocol",
                "protect_equipment",
                "controlled_shutdown",
            ],
            "forbidden": [
                "emergency_shutdown",
                "isolate_affected_units",
                "await_manual_intervention",
            ],
        }

        return actions.get(zone, [])


class ODDCoverageAnalyzer:
    """
    ODD覆盖率分析器

    分析ODD覆盖率和边界距离
    """

    def __init__(self, scanner: ODDScanner):
        self.scanner = scanner

    def analyze_coverage(self,
                        scan_results: List[ODDScanResult] = None) -> Dict[str, Any]:
        """分析ODD覆盖率"""
        if scan_results is None:
            scan_results = self.scanner.scan_history

        if not scan_results:
            return {"coverage": 0, "message": "无扫描数据"}

        # 计算平均覆盖率
        coverages = [r.coverage for r in scan_results]
        avg_coverage = np.mean(coverages)

        # 分析区域分布
        zone_totals = {}
        for result in scan_results:
            for zone, pct in result.zone_distribution.items():
                zone_totals[zone] = zone_totals.get(zone, 0) + pct

        n = len(scan_results)
        zone_avg = {k: v / n for k, v in zone_totals.items()}

        # 分析违规趋势
        violation_counts = [r.violations_found for r in scan_results]
        violation_trend = "stable"
        if len(violation_counts) >= 3:
            recent = np.mean(violation_counts[-3:])
            earlier = np.mean(violation_counts[:3])
            if recent > earlier * 1.2:
                violation_trend = "increasing"
            elif recent < earlier * 0.8:
                violation_trend = "decreasing"

        return {
            "coverage": {
                "average": avg_coverage,
                "min": min(coverages) if coverages else 0,
                "max": max(coverages) if coverages else 0,
            },
            "zone_distribution": zone_avg,
            "violation_analysis": {
                "total_violations": sum(violation_counts),
                "average_per_scan": np.mean(violation_counts) if violation_counts else 0,
                "trend": violation_trend,
            },
            "recommendation": self._generate_coverage_recommendation(
                avg_coverage, zone_avg, violation_trend
            ),
        }

    def analyze_boundary_distance(self,
                                  state: Dict[str, float]) -> Dict[str, float]:
        """分析边界距离"""
        distances = {}

        for rule in self.scanner.rule_engine.rules.values():
            if rule.rule_type != ODDRuleType.BOUNDARY:
                continue

            for var in rule.variables:
                value = state.get(var)
                if value is None:
                    continue

                # 计算到各边界的距离
                if rule.lower_bound is not None:
                    dist_lower = value - rule.lower_bound
                    distances[f"{var}_to_lower"] = dist_lower

                if rule.upper_bound is not None:
                    dist_upper = rule.upper_bound - value
                    distances[f"{var}_to_upper"] = dist_upper

                # 计算归一化距离
                if rule.lower_bound is not None and rule.upper_bound is not None:
                    range_size = rule.upper_bound - rule.lower_bound
                    if range_size > 0:
                        normalized = min(dist_lower, dist_upper) / range_size
                        distances[f"{var}_normalized"] = normalized

        return distances

    def _generate_coverage_recommendation(self,
                                         coverage: float,
                                         zone_dist: Dict[str, float],
                                         trend: str) -> str:
        """生成覆盖率建议"""
        if coverage < 80:
            return "ODD覆盖率不足，建议检查系统运行参数"
        elif coverage < 90:
            return "ODD覆盖率良好，建议持续监控"
        elif trend == "increasing":
            return "虽然覆盖率高，但违规趋势上升，建议加强监控"
        else:
            return "ODD覆盖率优秀，系统运行正常"


def create_default_odd_rules() -> ODDRuleEngine:
    """创建默认ODD规则引擎"""
    engine = ODDRuleEngine()

    # 压力边界规则
    engine.add_rule(ODDRule(
        rule_id="pressure_boundary",
        name="系统压力边界",
        description="有压系统压力边界限制",
        rule_type=ODDRuleType.BOUNDARY,
        variables=["system_pressure"],
        lower_bound=3.0,
        upper_bound=7.0,
        parameters={
            "optimal_range": (4.5, 5.0),
            "normal_range": (4.0, 5.5),
            "degraded_range": (3.5, 6.0),
            "emergency_range": (3.0, 6.5),
        },
        severity=ODDViolationSeverity.CRITICAL,
        action="检查压力调节系统",
    ))

    # 压力变化率规则
    engine.add_rule(ODDRule(
        rule_id="pressure_rate",
        name="压力变化率限制",
        description="压力变化率不能过快",
        rule_type=ODDRuleType.RATE,
        variables=["system_pressure"],
        parameters={
            "max_rate": 0.5,  # MPa/s
            "min_rate": -0.5,
        },
        severity=ODDViolationSeverity.MAJOR,
        action="减缓导叶动作速率",
    ))

    # 流量边界规则
    engine.add_rule(ODDRule(
        rule_id="flow_boundary",
        name="系统流量边界",
        description="系统流量边界限制",
        rule_type=ODDRuleType.BOUNDARY,
        variables=["system_flow"],
        lower_bound=200,
        upper_bound=1500,
        parameters={
            "optimal_range": (800, 1000),
            "normal_range": (600, 1100),
            "degraded_range": (400, 1200),
            "emergency_range": (200, 1300),
        },
        severity=ODDViolationSeverity.MAJOR,
        action="调整机组出力",
    ))

    # 频率边界规则
    engine.add_rule(ODDRule(
        rule_id="frequency_boundary",
        name="系统频率边界",
        description="电网频率边界限制",
        rule_type=ODDRuleType.BOUNDARY,
        variables=["frequency"],
        lower_bound=48.0,
        upper_bound=52.0,
        parameters={
            "optimal_range": (49.95, 50.05),
            "normal_range": (49.8, 50.2),
            "degraded_range": (49.5, 50.5),
            "emergency_range": (48.0, 52.0),
        },
        severity=ODDViolationSeverity.CRITICAL,
        action="启动频率调节",
    ))

    # 多站协同动作规则
    engine.add_rule(ODDRule(
        rule_id="simultaneous_action",
        name="多站同步动作限制",
        description="限制同时动作的电站数量",
        rule_type=ODDRuleType.COMBINATION,
        variables=["station_action_count"],
        parameters={
            "sub_conditions": [
                {"variable": "station_action_count", "operator": "<=", "threshold": 2},
            ],
            "logic": "AND",
        },
        severity=ODDViolationSeverity.MAJOR,
        action="错开动作时间",
    ))

    # 级联保护规则
    engine.add_rule(ODDRule(
        rule_id="cascade_protection",
        name="级联保护触发",
        description="级联效应保护",
        rule_type=ODDRuleType.PROTECTION,
        variables=["cascade_depth"],
        parameters={
            "protection_variable": "cascade_depth",
            "trigger_threshold": 3,
            "trigger_type": "above",
            "protection_action": "cascade_isolation",
        },
        severity=ODDViolationSeverity.EMERGENCY,
        action="隔离级联影响",
    ))

    # 降级持续时间规则
    engine.add_rule(ODDRule(
        rule_id="degraded_duration",
        name="降级持续时间限制",
        description="降级运行不能持续过长",
        rule_type=ODDRuleType.DURATION,
        variables=["current_zone"],
        parameters={
            "max_duration_degraded": 3600,    # 1小时
            "max_duration_emergency": 300,    # 5分钟
        },
        severity=ODDViolationSeverity.MAJOR,
        action="制定恢复计划",
    ))

    # 创建规则组
    engine.add_rule_group("pressure_rules", ["pressure_boundary", "pressure_rate"])
    engine.add_rule_group("safety_rules", ["frequency_boundary", "cascade_protection"])
    engine.add_rule_group("coordination_rules", ["simultaneous_action"])

    return engine
