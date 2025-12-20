# -*- coding: utf-8 -*-
"""
行为分析系统 - 操作员与系统行为建模
Behavior Analysis System - Operator and System Behavior Modeling

功能：
- 操作员行为画像
- 异常行为检测
- 操作序列分析
- 内部威胁检测
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum


class BehaviorType(Enum):
    """行为类型"""
    LOGIN = "login"
    LOGOUT = "logout"
    READ = "read"
    WRITE = "write"
    COMMAND = "command"
    ACKNOWLEDGE = "acknowledge"
    OVERRIDE = "override"
    CONFIG_CHANGE = "config_change"


@dataclass
class OperatorBehavior:
    """操作员行为记录"""
    user_id: str
    behavior_type: BehaviorType
    target: str                             # 操作目标
    value: Optional[Any] = None             # 操作值
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    source_ip: Optional[str] = None
    success: bool = True


@dataclass
class BehaviorProfile:
    """行为画像"""
    user_id: str

    # 时间模式
    typical_login_hours: List[int] = field(default_factory=list)  # 常用登录时段
    avg_session_duration: float = 0.0       # 平均会话时长(分钟)
    typical_days: List[int] = field(default_factory=list)  # 常用工作日

    # 操作模式
    frequent_operations: Dict[str, int] = field(default_factory=dict)
    frequent_targets: Dict[str, int] = field(default_factory=dict)
    avg_operations_per_session: float = 0.0

    # 风险指标
    failed_attempts: int = 0
    override_count: int = 0
    after_hours_access: int = 0

    # 学习参数
    sample_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class AnomalyScore:
    """异常评分"""
    user_id: str
    score: float                            # 0-1，越大越异常
    factors: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class BehaviorAnalyzer:
    """
    行为分析器

    功能：
    - 建立用户行为基线
    - 实时异常检测
    - 内部威胁识别
    """

    def __init__(self):
        self.profiles: Dict[str, BehaviorProfile] = {}
        self.behavior_history: Dict[str, List[OperatorBehavior]] = defaultdict(list)
        self.anomaly_history: List[AnomalyScore] = []

        # 分析参数
        self.params = {
            "learning_period": 30,          # 学习期(天)
            "history_limit": 10000,         # 历史记录限制
            "anomaly_threshold": 0.7,       # 异常阈值
            "time_decay": 0.95,             # 时间衰减因子
        }

        # 工作时间定义
        self.work_hours = {
            "start": 8,                     # 工作开始时间
            "end": 18,                      # 工作结束时间
            "days": [0, 1, 2, 3, 4],        # 工作日(周一到周五)
        }

    def record_behavior(self, behavior: OperatorBehavior) -> Optional[AnomalyScore]:
        """
        记录行为并检测异常

        Args:
            behavior: 操作员行为

        Returns:
            如果检测到异常则返回异常评分
        """
        user_id = behavior.user_id

        # 记录历史
        self.behavior_history[user_id].append(behavior)

        # 限制历史长度
        if len(self.behavior_history[user_id]) > self.params["history_limit"]:
            self.behavior_history[user_id] = self.behavior_history[user_id][-self.params["history_limit"]:]

        # 更新画像
        self._update_profile(user_id, behavior)

        # 检测异常
        anomaly = self._detect_anomaly(user_id, behavior)

        if anomaly and anomaly.score > self.params["anomaly_threshold"]:
            self.anomaly_history.append(anomaly)
            return anomaly

        return None

    def _update_profile(self, user_id: str, behavior: OperatorBehavior):
        """更新用户画像"""
        if user_id not in self.profiles:
            self.profiles[user_id] = BehaviorProfile(user_id=user_id)

        profile = self.profiles[user_id]
        profile.sample_count += 1
        profile.last_updated = datetime.now()

        # 更新登录时间模式
        if behavior.behavior_type == BehaviorType.LOGIN:
            hour = behavior.timestamp.hour
            if hour not in profile.typical_login_hours:
                profile.typical_login_hours.append(hour)
                profile.typical_login_hours = profile.typical_login_hours[-10:]  # 保留最近10个

            day = behavior.timestamp.weekday()
            if day not in profile.typical_days:
                profile.typical_days.append(day)

        # 更新操作模式
        op_key = behavior.behavior_type.value
        profile.frequent_operations[op_key] = profile.frequent_operations.get(op_key, 0) + 1

        target_key = behavior.target
        profile.frequent_targets[target_key] = profile.frequent_targets.get(target_key, 0) + 1

        # 更新风险指标
        if not behavior.success:
            profile.failed_attempts += 1

        if behavior.behavior_type == BehaviorType.OVERRIDE:
            profile.override_count += 1

        hour = behavior.timestamp.hour
        if hour < self.work_hours["start"] or hour >= self.work_hours["end"]:
            profile.after_hours_access += 1

    def _detect_anomaly(self, user_id: str, behavior: OperatorBehavior) -> AnomalyScore:
        """检测行为异常"""
        factors = {}
        total_score = 0.0

        profile = self.profiles.get(user_id)
        if not profile or profile.sample_count < 10:
            # 新用户，暂不评估
            return AnomalyScore(user_id=user_id, score=0.0, description="新用户")

        # 1. 时间异常
        hour = behavior.timestamp.hour
        if hour not in profile.typical_login_hours:
            time_score = 0.3
            if hour < 6 or hour > 22:  # 深夜
                time_score = 0.6
            factors["unusual_time"] = time_score
            total_score += time_score * 0.2

        # 2. 操作类型异常
        op_key = behavior.behavior_type.value
        total_ops = sum(profile.frequent_operations.values())
        op_freq = profile.frequent_operations.get(op_key, 0) / max(total_ops, 1)
        if op_freq < 0.05:  # 罕见操作
            op_score = 0.5
            factors["rare_operation"] = op_score
            total_score += op_score * 0.2

        # 3. 目标异常
        target = behavior.target
        total_targets = sum(profile.frequent_targets.values())
        target_freq = profile.frequent_targets.get(target, 0) / max(total_targets, 1)
        if target_freq < 0.01:  # 罕见目标
            target_score = 0.4
            factors["unusual_target"] = target_score
            total_score += target_score * 0.2

        # 4. 敏感操作
        if behavior.behavior_type in [BehaviorType.OVERRIDE, BehaviorType.CONFIG_CHANGE]:
            sensitive_score = 0.3
            factors["sensitive_operation"] = sensitive_score
            total_score += sensitive_score * 0.2

        # 5. 失败尝试
        if not behavior.success:
            fail_rate = profile.failed_attempts / max(profile.sample_count, 1)
            if fail_rate > 0.1:  # 高失败率
                fail_score = min(fail_rate * 5, 1.0)
                factors["high_failure_rate"] = fail_score
                total_score += fail_score * 0.2

        description = self._generate_description(factors)

        return AnomalyScore(
            user_id=user_id,
            score=min(total_score, 1.0),
            factors=factors,
            description=description,
        )

    def _generate_description(self, factors: Dict[str, float]) -> str:
        """生成异常描述"""
        descriptions = []

        if "unusual_time" in factors:
            descriptions.append("非常规时间操作")
        if "rare_operation" in factors:
            descriptions.append("罕见操作类型")
        if "unusual_target" in factors:
            descriptions.append("非常规操作目标")
        if "sensitive_operation" in factors:
            descriptions.append("敏感操作")
        if "high_failure_rate" in factors:
            descriptions.append("高失败率")

        return "；".join(descriptions) if descriptions else "正常行为"

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户画像"""
        if user_id not in self.profiles:
            return None

        profile = self.profiles[user_id]

        return {
            "user_id": user_id,
            "sample_count": profile.sample_count,
            "typical_login_hours": profile.typical_login_hours,
            "typical_days": profile.typical_days,
            "top_operations": dict(sorted(
                profile.frequent_operations.items(),
                key=lambda x: x[1], reverse=True
            )[:5]),
            "top_targets": dict(sorted(
                profile.frequent_targets.items(),
                key=lambda x: x[1], reverse=True
            )[:5]),
            "risk_indicators": {
                "failed_attempts": profile.failed_attempts,
                "override_count": profile.override_count,
                "after_hours_access": profile.after_hours_access,
            },
            "last_updated": profile.last_updated.isoformat(),
        }

    def get_anomalies(self, time_range: Optional[timedelta] = None,
                      min_score: float = 0.5) -> List[AnomalyScore]:
        """获取异常记录"""
        anomalies = self.anomaly_history

        if time_range:
            cutoff = datetime.now() - time_range
            anomalies = [a for a in anomalies if a.timestamp >= cutoff]

        anomalies = [a for a in anomalies if a.score >= min_score]

        return sorted(anomalies, key=lambda a: a.score, reverse=True)

    def get_high_risk_users(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """获取高风险用户"""
        user_scores = {}

        for anomaly in self.anomaly_history:
            user_id = anomaly.user_id
            if user_id not in user_scores:
                user_scores[user_id] = {
                    "anomaly_count": 0,
                    "total_score": 0,
                    "max_score": 0,
                }

            user_scores[user_id]["anomaly_count"] += 1
            user_scores[user_id]["total_score"] += anomaly.score
            user_scores[user_id]["max_score"] = max(
                user_scores[user_id]["max_score"],
                anomaly.score
            )

        # 计算综合风险
        risk_list = []
        for user_id, scores in user_scores.items():
            risk = (scores["total_score"] / max(scores["anomaly_count"], 1) +
                    scores["max_score"]) / 2
            risk_list.append({
                "user_id": user_id,
                "risk_score": risk,
                **scores
            })

        return sorted(risk_list, key=lambda x: x["risk_score"], reverse=True)[:top_n]

    def analyze_operation_sequence(self, user_id: str,
                                   lookback: int = 20) -> Dict[str, Any]:
        """分析操作序列"""
        history = self.behavior_history.get(user_id, [])[-lookback:]

        if len(history) < 3:
            return {"error": "Insufficient data"}

        # 操作间隔分析
        intervals = []
        for i in range(1, len(history)):
            interval = (history[i].timestamp - history[i-1].timestamp).total_seconds()
            intervals.append(interval)

        # 操作序列模式
        sequence = [b.behavior_type.value for b in history]

        # 常见序列检测
        common_patterns = [
            ["login", "read", "read", "logout"],  # 正常查看
            ["login", "write", "acknowledge", "logout"],  # 正常操作
        ]

        pattern_match = None
        for pattern in common_patterns:
            if self._sequence_contains(sequence, pattern):
                pattern_match = pattern

        return {
            "user_id": user_id,
            "sequence_length": len(history),
            "avg_interval": np.mean(intervals) if intervals else 0,
            "min_interval": np.min(intervals) if intervals else 0,
            "max_interval": np.max(intervals) if intervals else 0,
            "sequence": sequence,
            "pattern_match": pattern_match,
            "is_suspicious": np.min(intervals) < 1.0 if intervals else False,  # 操作过快
        }

    def _sequence_contains(self, sequence: List[str], pattern: List[str]) -> bool:
        """检查序列是否包含模式"""
        if len(pattern) > len(sequence):
            return False

        for i in range(len(sequence) - len(pattern) + 1):
            if sequence[i:i+len(pattern)] == pattern:
                return True
        return False
