# -*- coding: utf-8 -*-
"""
多智能体分布式协调框架 - Multi-Agent Distributed Coordination

功能：
- 梯级电站智能体
- 分散式决策
- 共识协议
- 协商机制
- 容错恢复

技术特点：
- 基于共识的分布式优化
- 多智能体强化学习接口
- 事件驱动通信
- 拜占庭容错
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from datetime import datetime
from enum import Enum
import threading
import queue
import time
import random


class AgentRole(Enum):
    """智能体角色"""
    LEADER = "leader"                 # 领导者
    FOLLOWER = "follower"             # 跟随者
    COORDINATOR = "coordinator"       # 协调者
    OBSERVER = "observer"             # 观察者


class MessageType(Enum):
    """消息类型"""
    PROPOSAL = "proposal"             # 提议
    VOTE = "vote"                     # 投票
    COMMIT = "commit"                 # 提交
    CONSENSUS = "consensus"           # 共识
    STATE_UPDATE = "state_update"     # 状态更新
    HEARTBEAT = "heartbeat"           # 心跳
    REQUEST = "request"               # 请求
    RESPONSE = "response"             # 响应


class CoordinationState(Enum):
    """协调状态"""
    IDLE = "idle"
    PROPOSING = "proposing"
    VOTING = "voting"
    COMMITTING = "committing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentMessage:
    """智能体消息"""
    msg_id: str
    msg_type: MessageType
    sender: str
    receiver: str                      # "*" 表示广播
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0


@dataclass
class AgentState:
    """智能体状态"""
    agent_id: str
    role: AgentRole
    local_state: Dict[str, float]
    neighbors: List[str]
    is_active: bool = True
    last_heartbeat: Optional[datetime] = None


@dataclass
class ConsensusProposal:
    """共识提议"""
    proposal_id: str
    proposer: str
    value: Dict[str, Any]
    votes: Dict[str, bool] = field(default_factory=dict)
    status: CoordinationState = CoordinationState.PROPOSING


class CommunicationChannel:
    """
    通信信道

    模拟智能体间通信
    """

    def __init__(self, latency_ms: float = 10, packet_loss: float = 0.01):
        self.latency_ms = latency_ms
        self.packet_loss = packet_loss

        # 消息队列（按接收者分）
        self.message_queues: Dict[str, queue.Queue] = {}

        # 统计
        self.total_messages = 0
        self.lost_messages = 0

        self._lock = threading.Lock()

    def register_agent(self, agent_id: str):
        """注册智能体"""
        with self._lock:
            self.message_queues[agent_id] = queue.Queue()

    def send(self, message: AgentMessage) -> bool:
        """
        发送消息

        Args:
            message: 消息

        Returns:
            是否发送成功
        """
        # 模拟丢包
        if random.random() < self.packet_loss:
            self.lost_messages += 1
            return False

        # 模拟延迟
        time.sleep(self.latency_ms / 1000)

        self.total_messages += 1

        with self._lock:
            if message.receiver == "*":
                # 广播
                for agent_id, q in self.message_queues.items():
                    if agent_id != message.sender:
                        q.put(message)
            else:
                # 单播
                if message.receiver in self.message_queues:
                    self.message_queues[message.receiver].put(message)
                else:
                    return False

        return True

    def receive(self, agent_id: str, timeout: float = 1.0) -> Optional[AgentMessage]:
        """
        接收消息

        Args:
            agent_id: 接收者ID
            timeout: 超时时间

        Returns:
            消息或None
        """
        if agent_id not in self.message_queues:
            return None

        try:
            return self.message_queues[agent_id].get(timeout=timeout)
        except queue.Empty:
            return None

    def get_statistics(self) -> Dict[str, float]:
        """获取统计"""
        return {
            "total_messages": self.total_messages,
            "lost_messages": self.lost_messages,
            "loss_rate": self.lost_messages / max(self.total_messages, 1),
        }


class BaseAgent:
    """
    基础智能体

    所有智能体的基类
    """

    def __init__(self, agent_id: str, channel: CommunicationChannel):
        self.agent_id = agent_id
        self.channel = channel

        self.state = AgentState(
            agent_id=agent_id,
            role=AgentRole.FOLLOWER,
            local_state={},
            neighbors=[],
        )

        # 注册到通信信道
        channel.register_agent(agent_id)

        # 消息处理器
        self.message_handlers: Dict[MessageType, Callable] = {}
        self._setup_handlers()

        # 运行状态
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def _setup_handlers(self):
        """设置消息处理器"""
        self.message_handlers[MessageType.HEARTBEAT] = self._handle_heartbeat
        self.message_handlers[MessageType.STATE_UPDATE] = self._handle_state_update

    def add_neighbor(self, neighbor_id: str):
        """添加邻居"""
        if neighbor_id not in self.state.neighbors:
            self.state.neighbors.append(neighbor_id)

    def send_message(self, receiver: str, msg_type: MessageType,
                     content: Dict[str, Any]) -> bool:
        """发送消息"""
        msg = AgentMessage(
            msg_id=f"{self.agent_id}_{time.time_ns()}",
            msg_type=msg_type,
            sender=self.agent_id,
            receiver=receiver,
            content=content,
        )
        return self.channel.send(msg)

    def broadcast(self, msg_type: MessageType, content: Dict[str, Any]):
        """广播消息"""
        self.send_message("*", msg_type, content)

    def _handle_heartbeat(self, msg: AgentMessage):
        """处理心跳"""
        self.state.last_heartbeat = datetime.now()

    def _handle_state_update(self, msg: AgentMessage):
        """处理状态更新"""
        # 子类实现
        pass

    def start(self):
        """启动智能体"""
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止智能体"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_loop(self):
        """运行循环"""
        while self.running:
            # 接收消息
            msg = self.channel.receive(self.agent_id, timeout=0.1)
            if msg:
                handler = self.message_handlers.get(msg.msg_type)
                if handler:
                    handler(msg)

            # 周期任务
            self._periodic_task()

    def _periodic_task(self):
        """周期任务（子类重写）"""
        pass


class HydropowerStationAgent(BaseAgent):
    """
    水电站智能体

    代表单个水电站的决策智能体

    功能：
    - 本地调度决策
    - 与邻居协商
    - 执行协调指令
    """

    def __init__(self, agent_id: str, channel: CommunicationChannel,
                 station_config: Dict[str, Any] = None):
        super().__init__(agent_id, channel)

        self.config = station_config or {}

        # 电站参数
        self.n_units = self.config.get("n_units", 4)
        self.max_power = self.config.get("max_power", 1000)  # MW
        self.min_power = self.config.get("min_power", 100)

        # 当前运行状态
        self.current_power = 0.0
        self.power_setpoint = 0.0
        self.available_capacity = self.max_power

        # 梯级位置
        self.cascade_position = self.config.get("cascade_position", 0)
        self.upstream_station: Optional[str] = None
        self.downstream_station: Optional[str] = None

        # 协调状态
        self.coordination_state = CoordinationState.IDLE
        self.pending_proposals: Dict[str, ConsensusProposal] = {}

        # 本地策略
        self.policy: Optional[Callable] = None

    def _setup_handlers(self):
        """设置消息处理器"""
        super()._setup_handlers()
        self.message_handlers[MessageType.PROPOSAL] = self._handle_proposal
        self.message_handlers[MessageType.VOTE] = self._handle_vote
        self.message_handlers[MessageType.COMMIT] = self._handle_commit
        self.message_handlers[MessageType.REQUEST] = self._handle_request

    def _handle_proposal(self, msg: AgentMessage):
        """处理提议"""
        proposal_id = msg.content.get("proposal_id")
        value = msg.content.get("value")

        # 评估提议
        accept = self._evaluate_proposal(value)

        # 发送投票
        self.send_message(
            msg.sender,
            MessageType.VOTE,
            {
                "proposal_id": proposal_id,
                "vote": accept,
                "reason": "local_evaluation",
            }
        )

    def _evaluate_proposal(self, value: Dict[str, Any]) -> bool:
        """评估提议"""
        # 检查是否在能力范围内
        requested_power = value.get("power", 0)

        if self.min_power <= requested_power <= self.available_capacity:
            return True

        return False

    def _handle_vote(self, msg: AgentMessage):
        """处理投票"""
        proposal_id = msg.content.get("proposal_id")
        vote = msg.content.get("vote")

        if proposal_id in self.pending_proposals:
            proposal = self.pending_proposals[proposal_id]
            proposal.votes[msg.sender] = vote

            # 检查是否达成共识
            self._check_consensus(proposal)

    def _check_consensus(self, proposal: ConsensusProposal):
        """检查共识"""
        if len(proposal.votes) >= len(self.state.neighbors):
            # 所有邻居都投票了
            approve_count = sum(1 for v in proposal.votes.values() if v)

            if approve_count >= len(self.state.neighbors) * 2 / 3:
                # 达成共识
                proposal.status = CoordinationState.COMMITTING
                self._commit_proposal(proposal)
            else:
                proposal.status = CoordinationState.FAILED

    def _commit_proposal(self, proposal: ConsensusProposal):
        """提交提议"""
        # 广播提交消息
        self.broadcast(MessageType.COMMIT, {
            "proposal_id": proposal.proposal_id,
            "value": proposal.value,
        })

        # 执行本地动作
        self._execute_action(proposal.value)
        proposal.status = CoordinationState.COMPLETED

    def _handle_commit(self, msg: AgentMessage):
        """处理提交"""
        value = msg.content.get("value")
        self._execute_action(value)

    def _handle_request(self, msg: AgentMessage):
        """处理请求"""
        request_type = msg.content.get("type")

        if request_type == "state_query":
            self.send_message(
                msg.sender,
                MessageType.RESPONSE,
                {
                    "current_power": self.current_power,
                    "available_capacity": self.available_capacity,
                    "station_id": self.agent_id,
                }
            )

    def _execute_action(self, action: Dict[str, Any]):
        """执行动作"""
        if "power" in action:
            self.power_setpoint = action["power"]

    def propose_power_adjustment(self, target_power: float) -> str:
        """
        发起功率调整提议

        Args:
            target_power: 目标功率

        Returns:
            提议ID
        """
        proposal_id = f"{self.agent_id}_prop_{time.time_ns()}"

        proposal = ConsensusProposal(
            proposal_id=proposal_id,
            proposer=self.agent_id,
            value={"power": target_power},
        )

        self.pending_proposals[proposal_id] = proposal

        # 广播提议
        self.broadcast(MessageType.PROPOSAL, {
            "proposal_id": proposal_id,
            "value": proposal.value,
        })

        return proposal_id

    def _periodic_task(self):
        """周期任务"""
        # 发送心跳
        self.broadcast(MessageType.HEARTBEAT, {
            "power": self.current_power,
            "capacity": self.available_capacity,
        })

        # 更新功率（简化的一阶响应）
        tau = 5.0  # 时间常数
        dt = 0.1
        self.current_power += (self.power_setpoint - self.current_power) * (1 - np.exp(-dt/tau))

        time.sleep(0.1)


class ConsensusProtocol:
    """
    共识协议

    实现分布式共识算法

    支持：
    - Raft共识
    - PBFT（简化）
    - 平均共识
    """

    def __init__(self, agents: List[BaseAgent]):
        self.agents = {a.agent_id: a for a in agents}
        self.n_agents = len(agents)

        # 共识状态
        self.current_term = 0
        self.leader_id: Optional[str] = None
        self.consensus_value: Optional[Dict] = None

    def elect_leader(self) -> str:
        """选举领导者（简化Raft）"""
        self.current_term += 1

        # 简化：选择ID最小的活跃节点
        active_agents = [
            aid for aid, agent in self.agents.items()
            if agent.state.is_active
        ]

        if active_agents:
            self.leader_id = min(active_agents)

        return self.leader_id

    def run_consensus(self, proposal: Dict[str, Any],
                      timeout: float = 5.0) -> Tuple[bool, Dict]:
        """
        运行共识

        Args:
            proposal: 提议值
            timeout: 超时时间

        Returns:
            是否达成共识, 最终值
        """
        if not self.leader_id or self.leader_id not in self.agents:
            self.elect_leader()

        if not self.leader_id:
            return False, {}

        # 领导者发起提议
        leader = self.agents[self.leader_id]
        leader.broadcast(MessageType.PROPOSAL, {
            "term": self.current_term,
            "value": proposal,
        })

        # 等待投票（简化：假设同步）
        votes = {}
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 收集投票
            for aid, agent in self.agents.items():
                if aid != self.leader_id:
                    msg = agent.channel.receive(aid, timeout=0.1)
                    if msg and msg.msg_type == MessageType.VOTE:
                        votes[aid] = msg.content.get("vote", False)

            # 检查是否足够
            if len(votes) >= self.n_agents - 1:
                break

        # 计算结果
        approve_count = sum(1 for v in votes.values() if v)
        if approve_count >= (self.n_agents - 1) * 2 / 3:
            self.consensus_value = proposal
            return True, proposal

        return False, {}


class AverageConsensus:
    """
    平均共识算法

    用于分布式参数协调

    迭代：x_i(k+1) = sum_j(w_ij * x_j(k))
    """

    def __init__(self, n_agents: int, adjacency_matrix: np.ndarray = None):
        self.n_agents = n_agents

        # 邻接矩阵
        if adjacency_matrix is not None:
            self.A = adjacency_matrix
        else:
            # 默认全连接
            self.A = np.ones((n_agents, n_agents)) - np.eye(n_agents)

        # 权重矩阵（Metropolis-Hastings）
        self.W = self._compute_weights()

        # 状态
        self.values = np.zeros(n_agents)

    def _compute_weights(self) -> np.ndarray:
        """计算权重矩阵"""
        W = np.zeros((self.n_agents, self.n_agents))
        degrees = np.sum(self.A, axis=1)

        for i in range(self.n_agents):
            for j in range(self.n_agents):
                if i != j and self.A[i, j] > 0:
                    W[i, j] = 1 / (1 + max(degrees[i], degrees[j]))

            W[i, i] = 1 - np.sum(W[i, :])

        return W

    def iterate(self, initial_values: np.ndarray, max_iter: int = 100,
                tolerance: float = 1e-6) -> Tuple[np.ndarray, int]:
        """
        迭代求解

        Args:
            initial_values: 初始值
            max_iter: 最大迭代次数
            tolerance: 收敛容差

        Returns:
            最终值, 迭代次数
        """
        self.values = initial_values.copy()

        for k in range(max_iter):
            new_values = self.W @ self.values

            # 收敛检查
            if np.max(np.abs(new_values - self.values)) < tolerance:
                self.values = new_values
                return self.values, k + 1

            self.values = new_values

        return self.values, max_iter

    def get_consensus_value(self) -> float:
        """获取共识值"""
        return np.mean(self.values)


class CascadeCoordinator:
    """
    梯级协调器

    协调多个水电站智能体

    功能：
    - 负荷分配
    - 水位协调
    - 应急响应
    """

    def __init__(self, channel: CommunicationChannel = None):
        self.channel = channel or CommunicationChannel()

        # 电站智能体
        self.stations: Dict[str, HydropowerStationAgent] = {}

        # 协调状态
        self.total_demand = 0.0
        self.total_capacity = 0.0
        self.allocation: Dict[str, float] = {}

        # 共识算法
        self.consensus: Optional[AverageConsensus] = None

    def add_station(self, station_id: str, config: Dict[str, Any]):
        """添加电站"""
        agent = HydropowerStationAgent(station_id, self.channel, config)
        self.stations[station_id] = agent

        # 更新共识
        n = len(self.stations)
        self.consensus = AverageConsensus(n)

    def setup_cascade_topology(self, topology: List[Tuple[str, str]]):
        """
        设置梯级拓扑

        Args:
            topology: 上下游关系列表 [(上游, 下游), ...]
        """
        for upstream, downstream in topology:
            if upstream in self.stations and downstream in self.stations:
                self.stations[upstream].downstream_station = downstream
                self.stations[downstream].upstream_station = upstream

                # 添加邻居
                self.stations[upstream].add_neighbor(downstream)
                self.stations[downstream].add_neighbor(upstream)

    def start_all(self):
        """启动所有智能体"""
        for agent in self.stations.values():
            agent.start()

    def stop_all(self):
        """停止所有智能体"""
        for agent in self.stations.values():
            agent.stop()

    def allocate_load(self, total_demand: float,
                       method: str = "proportional") -> Dict[str, float]:
        """
        负荷分配

        Args:
            total_demand: 总需求
            method: 分配方法 ("proportional", "equal", "consensus", "optimal")

        Returns:
            各电站分配
        """
        self.total_demand = total_demand

        # 计算总容量
        self.total_capacity = sum(s.available_capacity for s in self.stations.values())

        if method == "proportional":
            # 按容量比例分配
            for sid, station in self.stations.items():
                ratio = station.available_capacity / max(self.total_capacity, 1)
                self.allocation[sid] = total_demand * ratio

        elif method == "equal":
            # 均等分配
            n = len(self.stations)
            per_station = total_demand / n
            for sid in self.stations:
                self.allocation[sid] = per_station

        elif method == "consensus":
            # 共识分配
            initial = np.array([s.current_power for s in self.stations.values()])
            target_avg = total_demand / len(self.stations)
            adjusted = initial + (target_avg - np.mean(initial))

            final, _ = self.consensus.iterate(adjusted)
            for i, sid in enumerate(self.stations.keys()):
                self.allocation[sid] = final[i]

        elif method == "optimal":
            # 优化分配（简化：基于效率）
            # 按效率曲线分配，这里用容量作为代理
            self.allocation = self._optimal_allocation(total_demand)

        # 应用分配
        for sid, power in self.allocation.items():
            self.stations[sid].power_setpoint = power

        return self.allocation

    def _optimal_allocation(self, demand: float) -> Dict[str, float]:
        """优化分配"""
        allocation = {}
        remaining = demand

        # 按效率排序（简化：容量大效率高）
        sorted_stations = sorted(
            self.stations.items(),
            key=lambda x: x[1].max_power,
            reverse=True
        )

        for sid, station in sorted_stations:
            if remaining <= 0:
                allocation[sid] = station.min_power
            else:
                alloc = min(remaining, station.available_capacity)
                alloc = max(alloc, station.min_power)
                allocation[sid] = alloc
                remaining -= alloc

        return allocation

    def coordinate_water_level(self, target_levels: Dict[str, float]):
        """
        协调水位

        Args:
            target_levels: 各电站目标水位
        """
        for sid, level in target_levels.items():
            if sid in self.stations:
                self.stations[sid].broadcast(
                    MessageType.REQUEST,
                    {
                        "type": "water_level_adjustment",
                        "target": level,
                    }
                )

    def emergency_response(self, event: Dict[str, Any]):
        """
        应急响应

        Args:
            event: 事件信息
        """
        event_type = event.get("type")
        affected_station = event.get("station")

        if event_type == "trip":
            # 机组跳闸
            if affected_station in self.stations:
                lost_power = event.get("power", 0)

                # 重新分配负荷
                new_demand = self.total_demand
                remaining_stations = {
                    sid: s for sid, s in self.stations.items()
                    if sid != affected_station
                }

                for sid, station in remaining_stations.items():
                    extra = lost_power / len(remaining_stations)
                    station.power_setpoint += extra

        elif event_type == "flood":
            # 洪水
            for station in self.stations.values():
                station.broadcast(
                    MessageType.REQUEST,
                    {"type": "reduce_output", "percent": 20}
                )

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "total_demand": self.total_demand,
            "total_capacity": self.total_capacity,
            "allocation": self.allocation,
            "stations": {
                sid: {
                    "power": s.current_power,
                    "setpoint": s.power_setpoint,
                    "capacity": s.available_capacity,
                    "active": s.state.is_active,
                }
                for sid, s in self.stations.items()
            },
            "communication_stats": self.channel.get_statistics(),
        }


def create_yajiang_cascade() -> CascadeCoordinator:
    """
    创建雅江梯级电站群

    Returns:
        协调器实例
    """
    coordinator = CascadeCoordinator()

    # 添加三个梯级电站
    coordinator.add_station("station_1", {
        "n_units": 4,
        "max_power": 800,
        "min_power": 80,
        "cascade_position": 1,
        "name": "一级电站",
    })

    coordinator.add_station("station_2", {
        "n_units": 6,
        "max_power": 1200,
        "min_power": 120,
        "cascade_position": 2,
        "name": "二级电站",
    })

    coordinator.add_station("station_3", {
        "n_units": 4,
        "max_power": 600,
        "min_power": 60,
        "cascade_position": 3,
        "name": "三级电站",
    })

    # 设置梯级拓扑
    coordinator.setup_cascade_topology([
        ("station_1", "station_2"),
        ("station_2", "station_3"),
    ])

    return coordinator
