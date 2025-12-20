# -*- coding: utf-8 -*-
"""
入侵检测系统 - 工控网络威胁检测
Intrusion Detection System - ICS Network Threat Detection

功能：
- 基于规则的检测
- 基于异常的检测
- 协议深度解析
- 实时告警
- 攻击溯源

对标NIST SP 800-82工控系统安全指南
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict
import re
import hashlib


class ThreatLevel(Enum):
    """威胁级别"""
    INFO = 0              # 信息
    LOW = 1               # 低
    MEDIUM = 2            # 中
    HIGH = 3              # 高
    CRITICAL = 4          # 严重


class AttackType(Enum):
    """攻击类型"""
    # 网络层攻击
    PORT_SCAN = "port_scan"
    DOS = "denial_of_service"
    MITM = "man_in_the_middle"
    REPLAY = "replay_attack"

    # 协议层攻击
    MODBUS_INJECTION = "modbus_injection"
    PROTOCOL_FUZZING = "protocol_fuzzing"
    ILLEGAL_COMMAND = "illegal_command"

    # 应用层攻击
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"

    # 工控特定攻击
    SETPOINT_MANIPULATION = "setpoint_manipulation"
    LOGIC_BOMB = "logic_bomb"
    FIRMWARE_ATTACK = "firmware_attack"
    HMI_HIJACK = "hmi_hijack"

    # 其他
    UNKNOWN = "unknown"


@dataclass
class DetectionRule:
    """检测规则"""
    rule_id: str
    name: str
    description: str
    attack_type: AttackType
    threat_level: ThreatLevel

    # 匹配条件
    conditions: Dict[str, Any] = field(default_factory=dict)
    pattern: Optional[str] = None           # 正则模式

    # 响应
    response_actions: List[str] = field(default_factory=list)

    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


@dataclass
class ThreatAlert:
    """威胁告警"""
    alert_id: str
    rule_id: str
    attack_type: AttackType
    threat_level: ThreatLevel
    source_ip: str
    target_ip: str
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    response_status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "attack_type": self.attack_type.value,
            "threat_level": self.threat_level.name,
            "source_ip": self.source_ip,
            "target_ip": self.target_ip,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "response_status": self.response_status,
        }


class IntrusionDetectionSystem:
    """
    入侵检测系统

    功能：
    - 规则匹配检测
    - 统计异常检测
    - 协议合规检测
    - 行为基线检测
    """

    def __init__(self):
        self.rules: Dict[str, DetectionRule] = {}
        self.alerts: List[ThreatAlert] = []
        self.blocked_ips: Set[str] = set()

        # 统计数据
        self.connection_stats: Dict[str, Dict] = defaultdict(lambda: {
            "packet_count": 0,
            "byte_count": 0,
            "last_seen": None,
            "ports": set(),
        })

        # 基线数据
        self.normal_baseline = {
            "avg_packet_rate": 100,      # 正常包速率
            "avg_connection_count": 50,  # 正常连接数
            "allowed_ports": {502, 102, 44818, 20000},  # 允许端口
            "allowed_protocols": {"modbus", "s7", "ethernet_ip", "dnp3"},
        }

        # 初始化规则
        self._initialize_rules()
        self._alert_counter = 0

    def _initialize_rules(self):
        """初始化检测规则"""
        default_rules = [
            # 端口扫描检测
            DetectionRule(
                rule_id="IDS_001",
                name="端口扫描检测",
                description="检测到同一源IP在短时间内访问多个端口",
                attack_type=AttackType.PORT_SCAN,
                threat_level=ThreatLevel.MEDIUM,
                conditions={"port_count": 10, "time_window": 60},
                response_actions=["log", "alert", "block_temp"],
            ),

            # DoS攻击检测
            DetectionRule(
                rule_id="IDS_002",
                name="拒绝服务攻击检测",
                description="检测到异常高的网络流量",
                attack_type=AttackType.DOS,
                threat_level=ThreatLevel.HIGH,
                conditions={"packet_rate_threshold": 10000},
                response_actions=["log", "alert", "block", "rate_limit"],
            ),

            # 非法Modbus命令
            DetectionRule(
                rule_id="IDS_003",
                name="非法Modbus命令",
                description="检测到未授权的Modbus功能码",
                attack_type=AttackType.ILLEGAL_COMMAND,
                threat_level=ThreatLevel.HIGH,
                conditions={"illegal_function_codes": [8, 17, 43]},
                response_actions=["log", "alert", "block_command"],
            ),

            # 设定值篡改
            DetectionRule(
                rule_id="IDS_004",
                name="设定值异常篡改",
                description="检测到控制设定值被异常修改",
                attack_type=AttackType.SETPOINT_MANIPULATION,
                threat_level=ThreatLevel.CRITICAL,
                conditions={"max_change_rate": 10, "allowed_range": (0, 100)},
                response_actions=["log", "alert", "block", "rollback", "notify_operator"],
            ),

            # 未授权访问
            DetectionRule(
                rule_id="IDS_005",
                name="未授权访问尝试",
                description="检测到未经授权的系统访问",
                attack_type=AttackType.UNAUTHORIZED_ACCESS,
                threat_level=ThreatLevel.HIGH,
                conditions={"failed_attempts": 5, "time_window": 300},
                response_actions=["log", "alert", "lock_account"],
            ),

            # 重放攻击
            DetectionRule(
                rule_id="IDS_006",
                name="重放攻击检测",
                description="检测到可能的命令重放攻击",
                attack_type=AttackType.REPLAY,
                threat_level=ThreatLevel.MEDIUM,
                conditions={"duplicate_threshold": 10, "time_window": 60},
                response_actions=["log", "alert"],
            ),

            # HMI劫持
            DetectionRule(
                rule_id="IDS_007",
                name="HMI界面劫持",
                description="检测到HMI显示与实际状态不一致",
                attack_type=AttackType.HMI_HIJACK,
                threat_level=ThreatLevel.CRITICAL,
                conditions={"discrepancy_threshold": 5},
                response_actions=["log", "alert", "notify_operator", "switch_backup"],
            ),

            # 数据外泄
            DetectionRule(
                rule_id="IDS_008",
                name="敏感数据外泄",
                description="检测到大量数据向外部传输",
                attack_type=AttackType.DATA_EXFILTRATION,
                threat_level=ThreatLevel.HIGH,
                conditions={"outbound_threshold": 10000000},  # 10MB
                response_actions=["log", "alert", "block_outbound"],
            ),
        ]

        for rule in default_rules:
            self.rules[rule.rule_id] = rule

    def analyze_packet(self, packet: Dict[str, Any]) -> List[ThreatAlert]:
        """
        分析网络包

        Args:
            packet: 网络包信息

        Returns:
            触发的告警列表
        """
        alerts = []

        src_ip = packet.get("src_ip", "unknown")
        dst_ip = packet.get("dst_ip", "unknown")
        dst_port = packet.get("dst_port", 0)
        protocol = packet.get("protocol", "unknown")
        payload = packet.get("payload", b"")

        # 更新统计
        stats = self.connection_stats[src_ip]
        stats["packet_count"] += 1
        stats["byte_count"] += len(payload)
        stats["last_seen"] = datetime.now()
        stats["ports"].add(dst_port)

        # 检查是否已阻止
        if src_ip in self.blocked_ips:
            return []

        # 规则检测
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            triggered = self._check_rule(rule, packet, stats)
            if triggered:
                alert = self._create_alert(rule, src_ip, dst_ip, packet)
                alerts.append(alert)
                self.alerts.append(alert)
                rule.last_triggered = datetime.now()
                rule.trigger_count += 1

                # 执行响应动作
                self._execute_response(rule, alert)

        return alerts

    def _check_rule(self, rule: DetectionRule, packet: Dict,
                    stats: Dict) -> bool:
        """检查规则是否匹配"""
        conditions = rule.conditions

        if rule.attack_type == AttackType.PORT_SCAN:
            port_count = conditions.get("port_count", 10)
            if len(stats["ports"]) >= port_count:
                return True

        elif rule.attack_type == AttackType.DOS:
            threshold = conditions.get("packet_rate_threshold", 10000)
            # 简化：基于包计数
            if stats["packet_count"] > threshold:
                return True

        elif rule.attack_type == AttackType.ILLEGAL_COMMAND:
            if packet.get("protocol") == "modbus":
                func_code = packet.get("function_code", 0)
                illegal_codes = conditions.get("illegal_function_codes", [])
                if func_code in illegal_codes:
                    return True

        elif rule.attack_type == AttackType.SETPOINT_MANIPULATION:
            if "setpoint_change" in packet:
                change = packet["setpoint_change"]
                max_rate = conditions.get("max_change_rate", 10)
                allowed = conditions.get("allowed_range", (0, 100))
                if abs(change) > max_rate or not (allowed[0] <= packet.get("new_value", 0) <= allowed[1]):
                    return True

        elif rule.attack_type == AttackType.UNAUTHORIZED_ACCESS:
            if packet.get("auth_failed", False):
                # 简化：检测认证失败
                return True

        # 正则匹配
        if rule.pattern:
            payload = packet.get("payload", b"")
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8', errors='ignore')
            if re.search(rule.pattern, payload):
                return True

        return False

    def _create_alert(self, rule: DetectionRule, src_ip: str,
                      dst_ip: str, packet: Dict) -> ThreatAlert:
        """创建告警"""
        self._alert_counter += 1
        alert_id = f"ALERT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._alert_counter:04d}"

        return ThreatAlert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            attack_type=rule.attack_type,
            threat_level=rule.threat_level,
            source_ip=src_ip,
            target_ip=dst_ip,
            description=rule.description,
            evidence={
                "packet_info": {k: v for k, v in packet.items() if k != "payload"},
                "rule_conditions": rule.conditions,
            },
        )

    def _execute_response(self, rule: DetectionRule, alert: ThreatAlert):
        """执行响应动作"""
        for action in rule.response_actions:
            if action == "block":
                self.blocked_ips.add(alert.source_ip)
            elif action == "block_temp":
                # 临时阻止（实际应用中需要定时器）
                self.blocked_ips.add(alert.source_ip)
            elif action == "log":
                # 记录日志
                pass
            elif action == "alert":
                # 发送告警
                pass
            elif action == "notify_operator":
                # 通知操作员
                pass

        alert.response_status = "executed"

    def analyze_modbus_traffic(self, transaction: Dict[str, Any]) -> List[ThreatAlert]:
        """
        专门分析Modbus流量

        Args:
            transaction: Modbus事务

        Returns:
            告警列表
        """
        alerts = []

        func_code = transaction.get("function_code", 0)
        unit_id = transaction.get("unit_id", 0)
        registers = transaction.get("registers", [])

        # 功能码白名单检查
        allowed_functions = {1, 2, 3, 4, 5, 6, 15, 16}  # 常见读写功能
        if func_code not in allowed_functions:
            alert = ThreatAlert(
                alert_id=f"MODBUS_{datetime.now().strftime('%H%M%S')}",
                rule_id="IDS_003",
                attack_type=AttackType.ILLEGAL_COMMAND,
                threat_level=ThreatLevel.HIGH,
                source_ip=transaction.get("src_ip", "unknown"),
                target_ip=transaction.get("dst_ip", "unknown"),
                description=f"非法Modbus功能码: {func_code}",
            )
            alerts.append(alert)
            self.alerts.append(alert)

        # 写操作范围检查
        if func_code in {5, 6, 15, 16}:
            start_addr = transaction.get("start_address", 0)
            # 检查是否写入敏感寄存器
            sensitive_ranges = [(0, 10), (100, 110)]  # 示例敏感范围
            for low, high in sensitive_ranges:
                if low <= start_addr <= high:
                    alert = ThreatAlert(
                        alert_id=f"MODBUS_SENS_{datetime.now().strftime('%H%M%S')}",
                        rule_id="IDS_004",
                        attack_type=AttackType.SETPOINT_MANIPULATION,
                        threat_level=ThreatLevel.CRITICAL,
                        source_ip=transaction.get("src_ip", "unknown"),
                        target_ip=transaction.get("dst_ip", "unknown"),
                        description=f"敏感寄存器写入: 地址{start_addr}",
                    )
                    alerts.append(alert)
                    self.alerts.append(alert)

        return alerts

    def get_alerts(self, time_range: Optional[timedelta] = None,
                   threat_level: Optional[ThreatLevel] = None,
                   acknowledged: Optional[bool] = None) -> List[ThreatAlert]:
        """获取告警列表"""
        alerts = self.alerts

        if time_range:
            cutoff = datetime.now() - time_range
            alerts = [a for a in alerts if a.timestamp >= cutoff]

        if threat_level:
            alerts = [a for a in alerts if a.threat_level.value >= threat_level.value]

        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        return alerts

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """确认告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)

        recent_alerts = [a for a in self.alerts if a.timestamp >= hour_ago]

        by_type = defaultdict(int)
        by_level = defaultdict(int)
        for alert in recent_alerts:
            by_type[alert.attack_type.value] += 1
            by_level[alert.threat_level.name] += 1

        return {
            "total_alerts": len(self.alerts),
            "recent_alerts_1h": len(recent_alerts),
            "unacknowledged": sum(1 for a in self.alerts if not a.acknowledged),
            "blocked_ips": len(self.blocked_ips),
            "by_attack_type": dict(by_type),
            "by_threat_level": dict(by_level),
            "active_rules": sum(1 for r in self.rules.values() if r.enabled),
        }

    def add_rule(self, rule: DetectionRule):
        """添加检测规则"""
        self.rules[rule.rule_id] = rule

    def enable_rule(self, rule_id: str, enabled: bool = True):
        """启用/禁用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = enabled

    def unblock_ip(self, ip: str):
        """解除IP阻止"""
        self.blocked_ips.discard(ip)
