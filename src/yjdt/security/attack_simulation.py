# -*- coding: utf-8 -*-
"""
网络攻击仿真模块 - Cyber Attack Simulation

功能：
- 攻击场景模拟
- 协议级攻击
- 数据注入攻击
- 拒绝服务攻击
- 攻击链仿真
- 防护效果验证

用于安全评估和应急演练
注意：仅用于授权的安全测试和研究
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
import random
import time


class AttackCategory(Enum):
    """攻击类别"""
    RECONNAISSANCE = "reconnaissance"       # 侦察
    INITIAL_ACCESS = "initial_access"       # 初始访问
    EXECUTION = "execution"                 # 执行
    PERSISTENCE = "persistence"             # 持久化
    PRIVILEGE_ESCALATION = "privilege_escalation"  # 权限提升
    DEFENSE_EVASION = "defense_evasion"     # 防御规避
    CREDENTIAL_ACCESS = "credential_access" # 凭证获取
    LATERAL_MOVEMENT = "lateral_movement"   # 横向移动
    COLLECTION = "collection"               # 信息收集
    COMMAND_CONTROL = "command_control"     # 命令控制
    IMPACT = "impact"                       # 影响


class AttackType(Enum):
    """攻击类型"""
    # 数据层攻击
    DATA_INJECTION = "data_injection"       # 数据注入
    DATA_MANIPULATION = "data_manipulation" # 数据篡改
    DATA_REPLAY = "data_replay"             # 数据重放

    # 协议层攻击
    MODBUS_ATTACK = "modbus_attack"         # Modbus攻击
    DNP3_ATTACK = "dnp3_attack"             # DNP3攻击
    IEC104_ATTACK = "iec104_attack"         # IEC 104攻击

    # 网络层攻击
    DOS = "denial_of_service"               # 拒绝服务
    MITM = "man_in_the_middle"              # 中间人
    ARP_SPOOFING = "arp_spoofing"           # ARP欺骗

    # 控制层攻击
    SETPOINT_ATTACK = "setpoint_attack"     # 设定值攻击
    LOGIC_BOMB = "logic_bomb"               # 逻辑炸弹
    FIRMWARE_ATTACK = "firmware_attack"     # 固件攻击


class AttackSeverity(Enum):
    """攻击严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AttackVector:
    """攻击向量"""
    vector_id: str
    name: str
    attack_type: AttackType
    category: AttackCategory
    severity: AttackSeverity

    # 攻击参数
    target: str                             # 目标系统/变量
    parameters: Dict[str, Any] = field(default_factory=dict)

    # 攻击条件
    preconditions: List[str] = field(default_factory=list)
    success_probability: float = 0.8

    # 影响
    expected_impact: Dict[str, float] = field(default_factory=dict)


@dataclass
class AttackScenario:
    """攻击场景"""
    scenario_id: str
    name: str
    description: str

    # 攻击链
    attack_chain: List[AttackVector] = field(default_factory=list)

    # 时间参数
    start_time: Optional[datetime] = None
    duration: float = 3600                  # 秒

    # 目标
    primary_target: str = ""
    secondary_targets: List[str] = field(default_factory=list)

    # 攻击者能力
    attacker_capability: str = "intermediate"  # "novice", "intermediate", "advanced", "apt"


@dataclass
class AttackResult:
    """攻击结果"""
    scenario_id: str
    start_time: datetime
    end_time: datetime

    # 成功情况
    success: bool
    stages_completed: int
    stages_total: int

    # 影响评估
    impact: Dict[str, Any] = field(default_factory=dict)
    affected_systems: List[str] = field(default_factory=list)
    data_compromised: List[str] = field(default_factory=list)

    # 检测情况
    detected: bool = False
    detection_time: Optional[datetime] = None
    detection_method: str = ""

    # 时间线
    timeline: List[Dict[str, Any]] = field(default_factory=list)


class DataInjectionAttack:
    """
    数据注入攻击

    向控制系统注入虚假数据

    攻击模式：
    - 偏置注入
    - 比例攻击
    - 随机噪声
    - 阶跃攻击
    - 斜坡攻击
    """

    def __init__(self):
        self.injection_modes = {
            "bias": self._bias_injection,
            "scaling": self._scaling_injection,
            "random": self._random_injection,
            "step": self._step_injection,
            "ramp": self._ramp_injection,
            "replay": self._replay_injection,
        }

        self.active = False
        self.start_time: Optional[float] = None
        self.recorded_data: List[float] = []

    def inject(self, original_value: float, mode: str,
               params: Dict[str, float] = None) -> float:
        """
        注入攻击

        Args:
            original_value: 原始值
            mode: 注入模式
            params: 攻击参数

        Returns:
            篡改后的值
        """
        params = params or {}

        if mode in self.injection_modes:
            return self.injection_modes[mode](original_value, params)

        return original_value

    def _bias_injection(self, value: float, params: Dict) -> float:
        """偏置注入"""
        bias = params.get("bias", 10.0)
        return value + bias

    def _scaling_injection(self, value: float, params: Dict) -> float:
        """比例攻击"""
        scale = params.get("scale", 1.2)
        return value * scale

    def _random_injection(self, value: float, params: Dict) -> float:
        """随机噪声"""
        std = params.get("std", 5.0)
        return value + np.random.normal(0, std)

    def _step_injection(self, value: float, params: Dict) -> float:
        """阶跃攻击"""
        step_value = params.get("step_value", 50.0)
        return step_value

    def _ramp_injection(self, value: float, params: Dict) -> float:
        """斜坡攻击"""
        rate = params.get("rate", 1.0)
        if self.start_time is None:
            self.start_time = time.time()

        elapsed = time.time() - self.start_time
        return value + rate * elapsed

    def _replay_injection(self, value: float, params: Dict) -> float:
        """重放攻击"""
        if not self.active:
            # 记录阶段
            self.recorded_data.append(value)
            if len(self.recorded_data) > params.get("record_length", 100):
                self.active = True
            return value
        else:
            # 重放阶段
            idx = len(self.recorded_data) % max(len(self.recorded_data), 1)
            return self.recorded_data[idx] if self.recorded_data else value


class ProtocolAttack:
    """
    工控协议攻击

    针对Modbus/DNP3/IEC104等协议的攻击
    """

    def __init__(self, protocol: str = "modbus"):
        self.protocol = protocol
        self.active_attacks: List[Dict] = []

    def create_malicious_packet(self, attack_type: str,
                                 target_address: int,
                                 params: Dict = None) -> Dict:
        """
        创建恶意数据包

        Args:
            attack_type: 攻击类型
            target_address: 目标地址
            params: 攻击参数

        Returns:
            恶意数据包描述
        """
        params = params or {}

        if self.protocol == "modbus":
            return self._modbus_attack(attack_type, target_address, params)
        elif self.protocol == "dnp3":
            return self._dnp3_attack(attack_type, target_address, params)
        elif self.protocol == "iec104":
            return self._iec104_attack(attack_type, target_address, params)

        return {}

    def _modbus_attack(self, attack_type: str, address: int,
                       params: Dict) -> Dict:
        """Modbus攻击"""
        packet = {
            "protocol": "modbus",
            "attack_type": attack_type,
            "target_address": address,
        }

        if attack_type == "coil_write":
            # 强制线圈写入
            packet["function_code"] = 0x05  # Write Single Coil
            packet["value"] = params.get("value", 0xFF00)

        elif attack_type == "register_write":
            # 寄存器写入
            packet["function_code"] = 0x06  # Write Single Register
            packet["value"] = params.get("value", 0xFFFF)

        elif attack_type == "broadcast":
            # 广播攻击
            packet["slave_id"] = 0  # Broadcast address
            packet["function_code"] = 0x06

        elif attack_type == "exception":
            # 异常响应
            packet["function_code"] = 0x81  # Exception response
            packet["exception_code"] = params.get("exception", 0x02)

        return packet

    def _dnp3_attack(self, attack_type: str, address: int,
                     params: Dict) -> Dict:
        """DNP3攻击"""
        packet = {
            "protocol": "dnp3",
            "attack_type": attack_type,
            "destination": address,
        }

        if attack_type == "direct_operate":
            # 直接操作
            packet["function"] = "DIRECT_OPERATE"
            packet["object_group"] = 12  # CROB
            packet["control_code"] = params.get("control", "LATCH_ON")

        elif attack_type == "cold_restart":
            # 冷重启
            packet["function"] = "COLD_RESTART"

        elif attack_type == "clear_objects":
            # 清除对象
            packet["function"] = "CLEAR_OBJECTS"

        return packet

    def _iec104_attack(self, attack_type: str, address: int,
                       params: Dict) -> Dict:
        """IEC 104攻击"""
        packet = {
            "protocol": "iec104",
            "attack_type": attack_type,
            "asdu_address": address,
        }

        if attack_type == "single_command":
            # 单命令
            packet["type_id"] = 45  # C_SC_NA_1
            packet["value"] = params.get("value", 1)

        elif attack_type == "setpoint":
            # 设定值命令
            packet["type_id"] = 48  # C_SE_NA_1
            packet["value"] = params.get("value", 100.0)

        elif attack_type == "reset":
            # 复位进程
            packet["type_id"] = 105  # C_RP_NA_1

        return packet

    def simulate_effect(self, packet: Dict,
                        current_state: Dict[str, float]) -> Dict[str, float]:
        """
        模拟攻击效果

        Args:
            packet: 恶意数据包
            current_state: 当前系统状态

        Returns:
            攻击后状态
        """
        new_state = current_state.copy()

        if packet.get("function_code") == 0x06:  # Register write
            target = f"register_{packet.get('target_address', 0)}"
            new_state[target] = packet.get("value", 0)

        elif packet.get("function") == "DIRECT_OPERATE":
            # 直接操作效果
            control = packet.get("control_code", "LATCH_ON")
            if control == "LATCH_ON":
                new_state["breaker_status"] = 1
            elif control == "LATCH_OFF":
                new_state["breaker_status"] = 0

        return new_state


class DoSAttack:
    """
    拒绝服务攻击

    模拟各种DoS攻击场景
    """

    def __init__(self):
        self.attack_active = False
        self.packet_count = 0
        self.target_latency = 0.0

    def start_attack(self, attack_type: str, intensity: float = 1.0):
        """
        启动DoS攻击

        Args:
            attack_type: 攻击类型
            intensity: 攻击强度 (0-1)
        """
        self.attack_active = True
        self.attack_type = attack_type
        self.intensity = intensity
        self.packet_count = 0

    def stop_attack(self):
        """停止攻击"""
        self.attack_active = False

    def affect_communication(self, original_latency: float) -> Tuple[float, bool]:
        """
        影响通信

        Args:
            original_latency: 原始延迟

        Returns:
            新延迟, 是否丢包
        """
        if not self.attack_active:
            return original_latency, False

        self.packet_count += 1

        if self.attack_type == "flood":
            # 洪泛攻击
            new_latency = original_latency * (1 + 10 * self.intensity)
            packet_loss = random.random() < 0.3 * self.intensity
            return new_latency, packet_loss

        elif self.attack_type == "slowloris":
            # 慢速攻击
            new_latency = original_latency + 5000 * self.intensity  # ms
            return new_latency, False

        elif self.attack_type == "amplification":
            # 放大攻击
            new_latency = original_latency * (1 + 100 * self.intensity)
            packet_loss = random.random() < 0.5 * self.intensity
            return new_latency, packet_loss

        return original_latency, False

    def get_statistics(self) -> Dict[str, Any]:
        """获取攻击统计"""
        return {
            "active": self.attack_active,
            "type": getattr(self, "attack_type", None),
            "intensity": getattr(self, "intensity", 0),
            "packets_sent": self.packet_count,
        }


class StealthyAttack:
    """
    隐蔽攻击

    难以检测的高级攻击
    """

    def __init__(self):
        self.attack_phase = 0
        self.reconnaissance_data: Dict = {}
        self.learned_patterns: List[np.ndarray] = []

    def learn_normal_behavior(self, data_stream: List[float],
                               window_size: int = 100):
        """
        学习正常行为模式

        Args:
            data_stream: 数据流
            window_size: 窗口大小
        """
        if len(data_stream) >= window_size:
            pattern = np.array(data_stream[-window_size:])
            self.learned_patterns.append(pattern)

            # 统计正常范围
            self.reconnaissance_data["mean"] = np.mean(pattern)
            self.reconnaissance_data["std"] = np.std(pattern)
            self.reconnaissance_data["min"] = np.min(pattern)
            self.reconnaissance_data["max"] = np.max(pattern)

    def stealthy_injection(self, original_value: float,
                           target_drift: float,
                           rate: float = 0.001) -> float:
        """
        隐蔽注入

        缓慢改变值以避免检测

        Args:
            original_value: 原始值
            target_drift: 目标偏移
            rate: 变化速率

        Returns:
            修改后的值
        """
        if "mean" not in self.reconnaissance_data:
            return original_value

        # 确保在正常范围内
        normal_range = self.reconnaissance_data["max"] - self.reconnaissance_data["min"]
        max_change = normal_range * rate

        # 缓慢逼近目标
        current_drift = original_value - self.reconnaissance_data["mean"]
        desired_change = target_drift - current_drift
        actual_change = np.clip(desired_change, -max_change, max_change)

        new_value = original_value + actual_change

        # 添加正常噪声
        noise = np.random.normal(0, self.reconnaissance_data["std"] * 0.1)
        new_value += noise

        return new_value

    def time_based_attack(self, value: float, trigger_time: datetime,
                           attack_value: float) -> float:
        """
        时间触发攻击

        Args:
            value: 原始值
            trigger_time: 触发时间
            attack_value: 攻击值

        Returns:
            可能被修改的值
        """
        if datetime.now() >= trigger_time:
            return attack_value
        return value


class AttackSimulator:
    """
    攻击仿真器

    综合攻击仿真平台

    功能：
    - 攻击场景管理
    - 攻击执行
    - 效果评估
    - 检测验证
    """

    def __init__(self):
        # 攻击模块
        self.data_injector = DataInjectionAttack()
        self.protocol_attacker = ProtocolAttack()
        self.dos_attacker = DoSAttack()
        self.stealth_attacker = StealthyAttack()

        # 攻击场景库
        self.scenarios: Dict[str, AttackScenario] = {}

        # 执行记录
        self.execution_history: List[AttackResult] = []

        # 检测接口
        self.detection_callback: Optional[Callable] = None

    def register_scenario(self, scenario: AttackScenario):
        """注册攻击场景"""
        self.scenarios[scenario.scenario_id] = scenario

    def create_predefined_scenarios(self):
        """创建预定义攻击场景"""

        # 场景1：数据注入攻击
        self.scenarios["data_injection_1"] = AttackScenario(
            scenario_id="data_injection_1",
            name="水位传感器数据注入",
            description="攻击者篡改上游水库水位传感器数据",
            attack_chain=[
                AttackVector(
                    vector_id="v1",
                    name="水位数据偏置",
                    attack_type=AttackType.DATA_INJECTION,
                    category=AttackCategory.IMPACT,
                    severity=AttackSeverity.HIGH,
                    target="upstream_water_level",
                    parameters={"mode": "bias", "bias": -5.0},
                ),
            ],
            primary_target="sensor_system",
        )

        # 场景2：Modbus协议攻击
        self.scenarios["modbus_attack_1"] = AttackScenario(
            scenario_id="modbus_attack_1",
            name="导叶开度控制攻击",
            description="通过Modbus协议直接控制导叶开度",
            attack_chain=[
                AttackVector(
                    vector_id="v1",
                    name="网络扫描",
                    attack_type=AttackType.MODBUS_ATTACK,
                    category=AttackCategory.RECONNAISSANCE,
                    severity=AttackSeverity.LOW,
                    target="plc_network",
                ),
                AttackVector(
                    vector_id="v2",
                    name="寄存器写入",
                    attack_type=AttackType.MODBUS_ATTACK,
                    category=AttackCategory.IMPACT,
                    severity=AttackSeverity.CRITICAL,
                    target="guide_vane_register",
                    parameters={"function_code": 0x06, "value": 0},
                    preconditions=["v1"],
                ),
            ],
            primary_target="plc_system",
            attacker_capability="advanced",
        )

        # 场景3：拒绝服务攻击
        self.scenarios["dos_attack_1"] = AttackScenario(
            scenario_id="dos_attack_1",
            name="SCADA通信阻断",
            description="对SCADA通信链路进行洪泛攻击",
            attack_chain=[
                AttackVector(
                    vector_id="v1",
                    name="通信洪泛",
                    attack_type=AttackType.DOS,
                    category=AttackCategory.IMPACT,
                    severity=AttackSeverity.HIGH,
                    target="scada_network",
                    parameters={"type": "flood", "intensity": 0.8},
                ),
            ],
            primary_target="communication",
        )

        # 场景4：隐蔽攻击
        self.scenarios["stealth_attack_1"] = AttackScenario(
            scenario_id="stealth_attack_1",
            name="缓慢功率偏移攻击",
            description="长期缓慢改变功率设定值",
            attack_chain=[
                AttackVector(
                    vector_id="v1",
                    name="行为学习",
                    attack_type=AttackType.DATA_MANIPULATION,
                    category=AttackCategory.RECONNAISSANCE,
                    severity=AttackSeverity.LOW,
                    target="power_setpoint",
                    parameters={"phase": "learning", "duration": 3600},
                ),
                AttackVector(
                    vector_id="v2",
                    name="隐蔽偏移",
                    attack_type=AttackType.DATA_MANIPULATION,
                    category=AttackCategory.IMPACT,
                    severity=AttackSeverity.MEDIUM,
                    target="power_setpoint",
                    parameters={"mode": "stealthy", "target_drift": -50, "rate": 0.001},
                    preconditions=["v1"],
                ),
            ],
            primary_target="control_system",
            attacker_capability="apt",
            duration=86400,  # 24小时
        )

        # 场景5：级联攻击
        self.scenarios["cascade_attack_1"] = AttackScenario(
            scenario_id="cascade_attack_1",
            name="梯级电站协同攻击",
            description="同时攻击多个梯级电站造成连锁反应",
            attack_chain=[
                AttackVector(
                    vector_id="v1",
                    name="上游电站攻击",
                    attack_type=AttackType.SETPOINT_ATTACK,
                    category=AttackCategory.IMPACT,
                    severity=AttackSeverity.HIGH,
                    target="station_1_flow",
                ),
                AttackVector(
                    vector_id="v2",
                    name="下游电站攻击",
                    attack_type=AttackType.SETPOINT_ATTACK,
                    category=AttackCategory.IMPACT,
                    severity=AttackSeverity.HIGH,
                    target="station_2_gate",
                ),
            ],
            primary_target="cascade_system",
            attacker_capability="advanced",
        )

    def execute_scenario(self, scenario_id: str,
                         system_state: Dict[str, float]) -> AttackResult:
        """
        执行攻击场景

        Args:
            scenario_id: 场景ID
            system_state: 系统状态

        Returns:
            攻击结果
        """
        if scenario_id not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        scenario = self.scenarios[scenario_id]
        start_time = datetime.now()

        result = AttackResult(
            scenario_id=scenario_id,
            start_time=start_time,
            end_time=start_time,
            success=False,
            stages_completed=0,
            stages_total=len(scenario.attack_chain),
        )

        completed_vectors = set()
        current_state = system_state.copy()

        # 执行攻击链
        for vector in scenario.attack_chain:
            # 检查前置条件
            if not all(pre in completed_vectors for pre in vector.preconditions):
                result.timeline.append({
                    "time": datetime.now(),
                    "vector": vector.vector_id,
                    "status": "skipped",
                    "reason": "preconditions not met",
                })
                continue

            # 执行攻击
            success, impact = self._execute_vector(vector, current_state)

            result.timeline.append({
                "time": datetime.now(),
                "vector": vector.vector_id,
                "name": vector.name,
                "status": "success" if success else "failed",
                "impact": impact,
            })

            if success:
                completed_vectors.add(vector.vector_id)
                result.stages_completed += 1
                result.affected_systems.append(vector.target)

                # 更新状态
                current_state.update(impact)

            # 检测检查
            if self.detection_callback:
                detected = self.detection_callback(vector, current_state)
                if detected:
                    result.detected = True
                    result.detection_time = datetime.now()
                    break

        result.end_time = datetime.now()
        result.success = result.stages_completed == result.stages_total
        result.impact = {
            "state_changes": current_state,
            "severity": scenario.attack_chain[-1].severity.value if scenario.attack_chain else "none",
        }

        self.execution_history.append(result)
        return result

    def _execute_vector(self, vector: AttackVector,
                        state: Dict[str, float]) -> Tuple[bool, Dict]:
        """执行单个攻击向量"""
        impact = {}

        # 模拟成功概率
        if random.random() > vector.success_probability:
            return False, {}

        if vector.attack_type == AttackType.DATA_INJECTION:
            mode = vector.parameters.get("mode", "bias")
            if vector.target in state:
                original = state[vector.target]
                modified = self.data_injector.inject(original, mode, vector.parameters)
                impact[vector.target] = modified

        elif vector.attack_type == AttackType.MODBUS_ATTACK:
            packet = self.protocol_attacker.create_malicious_packet(
                "register_write",
                vector.parameters.get("address", 0),
                vector.parameters
            )
            impact = self.protocol_attacker.simulate_effect(packet, state)

        elif vector.attack_type == AttackType.DOS:
            self.dos_attacker.start_attack(
                vector.parameters.get("type", "flood"),
                vector.parameters.get("intensity", 1.0)
            )
            impact["network_latency"] = 1000  # ms
            impact["packet_loss_rate"] = 0.3

        elif vector.attack_type == AttackType.SETPOINT_ATTACK:
            if vector.target in state:
                # 设定值攻击
                impact[vector.target] = vector.parameters.get("value", 0)

        elif vector.attack_type == AttackType.DATA_MANIPULATION:
            if vector.parameters.get("mode") == "stealthy":
                if vector.target in state:
                    modified = self.stealth_attacker.stealthy_injection(
                        state[vector.target],
                        vector.parameters.get("target_drift", 0),
                        vector.parameters.get("rate", 0.001)
                    )
                    impact[vector.target] = modified

        return True, impact

    def set_detection_callback(self, callback: Callable):
        """设置检测回调"""
        self.detection_callback = callback

    def get_attack_statistics(self) -> Dict[str, Any]:
        """获取攻击统计"""
        if not self.execution_history:
            return {}

        successful = sum(1 for r in self.execution_history if r.success)
        detected = sum(1 for r in self.execution_history if r.detected)

        return {
            "total_attacks": len(self.execution_history),
            "successful": successful,
            "failed": len(self.execution_history) - successful,
            "detected": detected,
            "detection_rate": detected / len(self.execution_history),
            "success_rate": successful / len(self.execution_history),
        }

    def evaluate_defense(self, defense_system: Any) -> Dict[str, Any]:
        """
        评估防御效果

        Args:
            defense_system: 防御系统实例

        Returns:
            评估结果
        """
        results = {
            "scenarios_tested": 0,
            "attacks_blocked": 0,
            "attacks_detected": 0,
            "detection_times": [],
            "false_positives": 0,
        }

        # 对每个场景进行测试
        for scenario_id in self.scenarios:
            results["scenarios_tested"] += 1

            # 设置检测回调
            def detection_check(vector, state):
                # 简化：使用防御系统的检测方法
                if hasattr(defense_system, "detect"):
                    return defense_system.detect(vector, state)
                return False

            self.set_detection_callback(detection_check)

            # 执行攻击
            result = self.execute_scenario(
                scenario_id,
                {"power": 500, "water_level": 100, "frequency": 50}
            )

            if result.detected:
                results["attacks_detected"] += 1
                if result.detection_time:
                    dt = (result.detection_time - result.start_time).total_seconds()
                    results["detection_times"].append(dt)

            if not result.success:
                results["attacks_blocked"] += 1

        # 计算平均检测时间
        if results["detection_times"]:
            results["avg_detection_time"] = np.mean(results["detection_times"])

        return results

    def export_results(self, filepath: str):
        """导出结果"""
        import json

        export_data = []
        for result in self.execution_history:
            export_data.append({
                "scenario_id": result.scenario_id,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat(),
                "success": result.success,
                "detected": result.detected,
                "stages_completed": result.stages_completed,
                "stages_total": result.stages_total,
                "affected_systems": result.affected_systems,
                "timeline": [
                    {
                        "time": t["time"].isoformat() if isinstance(t["time"], datetime) else str(t["time"]),
                        **{k: v for k, v in t.items() if k != "time"}
                    }
                    for t in result.timeline
                ],
            })

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
