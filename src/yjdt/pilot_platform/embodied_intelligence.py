# -*- coding: utf-8 -*-
"""
具身智能训练模块 - Embodied Intelligence Training Module

功能：
- 地下厂房机器人训练
- 视觉感知模拟
- 自主导航决策
- 紧急逃生训练
- 巡检任务规划

基于YX工程需求，支持：
- 2000m水头超高压环境
- 地下800m深度厂房
- 狭窄通道/竖井作业
- 高噪声/高温环境
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import threading
import time


class RobotType(Enum):
    """机器人类型"""
    INSPECTION = "inspection"          # 巡检机器人
    MAINTENANCE = "maintenance"        # 维护机器人
    EMERGENCY = "emergency"            # 应急机器人
    UNDERWATER = "underwater"          # 水下机器人
    CLIMBING = "climbing"              # 攀爬机器人


class SensorType(Enum):
    """传感器类型"""
    LIDAR = "lidar"                    # 激光雷达
    CAMERA_RGB = "camera_rgb"          # RGB相机
    CAMERA_THERMAL = "thermal"         # 热成像
    DEPTH = "depth"                    # 深度相机
    IMU = "imu"                        # 惯性测量
    GPS = "gps"                        # 定位（地下用UWB）
    ULTRASONIC = "ultrasonic"          # 超声波
    GAS = "gas"                        # 气体检测


class TaskType(Enum):
    """任务类型"""
    PATROL = "patrol"                  # 巡检
    INSPECTION = "inspection"          # 检测
    REPAIR = "repair"                  # 维修
    EMERGENCY_RESPONSE = "emergency"   # 应急
    ESCAPE = "escape"                  # 逃生
    MAPPING = "mapping"                # 建图


@dataclass
class RobotState:
    """机器人状态"""
    position: np.ndarray              # [x, y, z] 位置
    orientation: np.ndarray           # [roll, pitch, yaw] 姿态
    velocity: np.ndarray              # [vx, vy, vz] 速度
    angular_velocity: np.ndarray      # [wx, wy, wz] 角速度

    # 关节状态（多自由度）
    joint_positions: Dict[str, float] = field(default_factory=dict)
    joint_velocities: Dict[str, float] = field(default_factory=dict)

    # 电池/能源
    battery_level: float = 1.0

    # 状态标志
    is_moving: bool = False
    is_operational: bool = True
    emergency_stop: bool = False


@dataclass
class SensorReading:
    """传感器读数"""
    sensor_type: SensorType
    timestamp: datetime
    data: Any                         # 传感器数据（类型因传感器而异）
    quality: float = 1.0              # 数据质量 0-1


@dataclass
class Observation:
    """观测"""
    timestamp: datetime
    robot_state: RobotState
    sensor_readings: Dict[str, SensorReading] = field(default_factory=dict)

    # 感知结果
    detected_objects: List[Dict[str, Any]] = field(default_factory=list)
    detected_hazards: List[Dict[str, Any]] = field(default_factory=list)

    # 环境状态
    environment: Dict[str, float] = field(default_factory=dict)


@dataclass
class Action:
    """动作"""
    action_type: str                  # "move", "rotate", "manipulate", "stop"
    parameters: Dict[str, float] = field(default_factory=dict)
    priority: int = 0
    timeout: float = 10.0


@dataclass
class TrainingEpisode:
    """训练回合"""
    episode_id: str
    task_type: TaskType
    start_time: datetime
    end_time: Optional[datetime]

    # 轨迹
    observations: List[Observation] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    rewards: List[float] = field(default_factory=list)

    # 结果
    success: bool = False
    total_reward: float = 0.0
    steps: int = 0


class VisualPerceptionModule:
    """
    视觉感知模块

    功能：
    - 场景理解
    - 目标检测
    - 障碍识别
    - 设备状态识别
    """

    def __init__(self):
        # 检测模型（模拟）
        self.object_classes = [
            "pipe", "valve", "pump", "turbine", "generator",
            "cable", "panel", "person", "vehicle", "debris"
        ]

        self.hazard_classes = [
            "water_leak", "fire", "smoke", "crack", "corrosion",
            "oil_spill", "gas_leak", "electrical_arc"
        ]

        # 检测历史
        self.detection_history: List[Dict[str, Any]] = []

    def process_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        处理图像

        Args:
            image: 输入图像 [H, W, C]

        Returns:
            检测结果
        """
        h, w = image.shape[:2] if len(image.shape) >= 2 else (100, 100)

        # 模拟目标检测
        detections = []
        n_objects = np.random.randint(0, 5)

        for _ in range(n_objects):
            cls = np.random.choice(self.object_classes)
            x = np.random.randint(0, w - 50)
            y = np.random.randint(0, h - 50)
            box_w = np.random.randint(20, min(100, w - x))
            box_h = np.random.randint(20, min(100, h - y))

            detections.append({
                "class": cls,
                "confidence": np.random.uniform(0.7, 0.99),
                "bbox": [x, y, x + box_w, y + box_h],
            })

        # 模拟危险检测
        hazards = []
        if np.random.random() < 0.1:  # 10%概率检测到危险
            hazard_cls = np.random.choice(self.hazard_classes)
            hazards.append({
                "class": hazard_cls,
                "confidence": np.random.uniform(0.6, 0.95),
                "severity": np.random.choice(["low", "medium", "high"]),
                "location": [np.random.randint(0, w), np.random.randint(0, h)],
            })

        result = {
            "objects": detections,
            "hazards": hazards,
            "timestamp": datetime.now(),
        }

        self.detection_history.append(result)
        return result

    def process_thermal(self, thermal_image: np.ndarray) -> Dict[str, Any]:
        """
        处理热成像

        Args:
            thermal_image: 热成像数据

        Returns:
            热分析结果
        """
        # 模拟温度分布分析
        if thermal_image.size > 0:
            max_temp = np.max(thermal_image)
            min_temp = np.min(thermal_image)
            avg_temp = np.mean(thermal_image)
        else:
            max_temp = min_temp = avg_temp = 25.0

        # 热点检测
        hotspots = []
        if max_temp > 60:  # 高于60度为热点
            hotspots.append({
                "temperature": max_temp,
                "severity": "high" if max_temp > 80 else "medium",
            })

        return {
            "max_temperature": max_temp,
            "min_temperature": min_temp,
            "avg_temperature": avg_temp,
            "hotspots": hotspots,
            "thermal_anomaly": max_temp > 60,
        }

    def process_lidar(self, point_cloud: np.ndarray) -> Dict[str, Any]:
        """
        处理激光雷达数据

        Args:
            point_cloud: 点云 [N, 3+]

        Returns:
            环境分析结果
        """
        if len(point_cloud) == 0:
            return {"obstacles": [], "ground_plane": None}

        # 模拟障碍物聚类
        obstacles = []
        n_clusters = np.random.randint(0, 5)

        for i in range(n_clusters):
            center = np.random.uniform(-5, 5, size=3)
            size = np.random.uniform(0.5, 2.0, size=3)

            obstacles.append({
                "id": i,
                "center": center.tolist(),
                "size": size.tolist(),
                "distance": np.linalg.norm(center),
            })

        # 地面检测
        ground_plane = {
            "normal": [0, 0, 1],
            "height": 0.0,
        }

        return {
            "obstacles": obstacles,
            "ground_plane": ground_plane,
            "point_count": len(point_cloud),
        }

    def detect_equipment_status(self, observations: List[Observation]) -> Dict[str, Any]:
        """
        检测设备状态

        Args:
            observations: 观测序列

        Returns:
            设备状态分析
        """
        equipment_status = {}

        # 分析历史检测
        all_objects = []
        for obs in observations:
            all_objects.extend(obs.detected_objects)

        # 统计各类设备
        class_counts = {}
        for obj in all_objects:
            cls = obj.get("class", "unknown")
            class_counts[cls] = class_counts.get(cls, 0) + 1

        # 生成状态报告
        for cls, count in class_counts.items():
            equipment_status[cls] = {
                "detected_count": count,
                "status": "normal",  # 简化，实际需要深度分析
            }

        return equipment_status


class AutonomousNavigator:
    """
    自主导航模块

    功能：
    - 路径规划
    - 避障
    - SLAM定位
    - 多楼层导航
    """

    def __init__(self):
        # 地图
        self.occupancy_map: Optional[np.ndarray] = None
        self.map_resolution = 0.1  # 米/像素

        # 当前路径
        self.current_path: List[np.ndarray] = []
        self.path_index = 0

        # 导航参数
        self.max_velocity = 1.0        # m/s
        self.max_angular_velocity = 1.0  # rad/s
        self.safety_distance = 0.5     # m

        # 状态
        self.is_navigating = False
        self.goal: Optional[np.ndarray] = None

    def set_map(self, occupancy_map: np.ndarray, resolution: float = 0.1):
        """设置地图"""
        self.occupancy_map = occupancy_map
        self.map_resolution = resolution

    def plan_path(self, start: np.ndarray, goal: np.ndarray) -> List[np.ndarray]:
        """
        规划路径（A*算法简化实现）

        Args:
            start: 起点 [x, y]
            goal: 终点 [x, y]

        Returns:
            路径点列表
        """
        # 简化：直接生成平滑路径
        path = []
        n_points = int(np.linalg.norm(goal - start) / 0.5) + 2

        for i in range(n_points):
            t = i / (n_points - 1)
            point = start * (1 - t) + goal * t
            # 添加小随机偏移模拟避障
            point += np.random.normal(0, 0.1, size=2)
            path.append(point)

        self.current_path = path
        self.path_index = 0
        self.goal = goal

        return path

    def plan_3d_path(self, start: np.ndarray, goal: np.ndarray,
                     elevation_map: np.ndarray = None) -> List[np.ndarray]:
        """
        3D路径规划（用于多层厂房）

        Args:
            start: 起点 [x, y, z]
            goal: 终点 [x, y, z]
            elevation_map: 高程图

        Returns:
            3D路径
        """
        path_3d = []
        n_points = int(np.linalg.norm(goal - start) / 0.5) + 2

        for i in range(n_points):
            t = i / (n_points - 1)
            point = start * (1 - t) + goal * t
            path_3d.append(point)

        return path_3d

    def get_control_command(self, current_state: RobotState) -> Action:
        """
        获取控制指令

        Args:
            current_state: 当前机器人状态

        Returns:
            控制动作
        """
        if not self.current_path or self.path_index >= len(self.current_path):
            return Action(action_type="stop", parameters={})

        # 获取目标点
        target = self.current_path[self.path_index]
        current_pos = current_state.position[:2]

        # 计算误差
        error = target - current_pos
        distance = np.linalg.norm(error)

        # 到达当前航点
        if distance < 0.3:
            self.path_index += 1
            if self.path_index >= len(self.current_path):
                self.is_navigating = False
                return Action(action_type="stop", parameters={"reason": "goal_reached"})

        # 计算速度指令
        direction = error / max(distance, 0.01)
        velocity = min(self.max_velocity, distance)

        # 计算航向
        target_yaw = np.arctan2(direction[1], direction[0])
        current_yaw = current_state.orientation[2]
        yaw_error = target_yaw - current_yaw

        # 归一化角度
        while yaw_error > np.pi:
            yaw_error -= 2 * np.pi
        while yaw_error < -np.pi:
            yaw_error += 2 * np.pi

        return Action(
            action_type="move",
            parameters={
                "linear_velocity": velocity,
                "angular_velocity": np.clip(yaw_error, -self.max_angular_velocity,
                                            self.max_angular_velocity),
                "target_x": target[0],
                "target_y": target[1],
            }
        )

    def check_collision(self, position: np.ndarray) -> bool:
        """检查碰撞"""
        if self.occupancy_map is None:
            return False

        # 转换到地图坐标
        map_x = int(position[0] / self.map_resolution)
        map_y = int(position[1] / self.map_resolution)

        h, w = self.occupancy_map.shape
        if 0 <= map_x < w and 0 <= map_y < h:
            return self.occupancy_map[map_y, map_x] > 0.5

        return True  # 超出地图范围视为碰撞

    def get_navigation_status(self) -> Dict[str, Any]:
        """获取导航状态"""
        return {
            "is_navigating": self.is_navigating,
            "path_length": len(self.current_path),
            "current_waypoint": self.path_index,
            "goal": self.goal.tolist() if self.goal is not None else None,
            "progress": self.path_index / max(len(self.current_path), 1),
        }


class EmergencyEscapeAgent:
    """
    紧急逃生智能体

    功能：
    - 危险感知
    - 逃生路径规划
    - 避险决策
    - 自主撤离

    针对YX工程特殊需求：
    - 地下800m深厂房逃生
    - 水淹/火灾/地震场景
    - 竖井/隧道撤离
    """

    def __init__(self, navigator: AutonomousNavigator):
        self.navigator = navigator

        # 紧急出口位置
        self.emergency_exits: List[np.ndarray] = []

        # 危险区域
        self.danger_zones: List[Dict[str, Any]] = []

        # 逃生状态
        self.in_emergency = False
        self.current_threat: Optional[str] = None
        self.escape_path: List[np.ndarray] = []

        # 决策参数
        self.threat_threshold = 0.7
        self.reaction_time = 0.5  # 秒

    def add_emergency_exit(self, position: np.ndarray, exit_type: str = "door"):
        """添加紧急出口"""
        self.emergency_exits.append({
            "position": position,
            "type": exit_type,
            "accessible": True,
        })

    def add_danger_zone(self, center: np.ndarray, radius: float,
                        danger_type: str, severity: float = 1.0):
        """添加危险区域"""
        self.danger_zones.append({
            "center": center,
            "radius": radius,
            "type": danger_type,
            "severity": severity,
            "timestamp": datetime.now(),
        })

    def assess_threat(self, observation: Observation) -> Dict[str, Any]:
        """
        评估威胁

        Args:
            observation: 当前观测

        Returns:
            威胁评估结果
        """
        threats = []

        # 检查感知到的危险
        for hazard in observation.detected_hazards:
            threat_level = hazard.get("confidence", 0.5)
            if hazard.get("severity") == "high":
                threat_level *= 1.5
            elif hazard.get("severity") == "medium":
                threat_level *= 1.2

            threats.append({
                "type": hazard.get("class", "unknown"),
                "level": min(threat_level, 1.0),
                "location": hazard.get("location"),
            })

        # 检查环境参数
        env = observation.environment

        # 温度威胁
        if env.get("temperature", 25) > 60:
            threats.append({
                "type": "high_temperature",
                "level": min((env["temperature"] - 60) / 40, 1.0),
            })

        # 水位威胁
        if env.get("water_level", 0) > 0.3:
            threats.append({
                "type": "flooding",
                "level": min(env["water_level"], 1.0),
            })

        # 气体威胁
        if env.get("toxic_gas_level", 0) > 0.1:
            threats.append({
                "type": "toxic_gas",
                "level": min(env["toxic_gas_level"] * 5, 1.0),
            })

        # 计算综合威胁等级
        if threats:
            max_threat = max(t["level"] for t in threats)
            primary_threat = max(threats, key=lambda t: t["level"])
        else:
            max_threat = 0
            primary_threat = None

        return {
            "threats": threats,
            "max_threat_level": max_threat,
            "primary_threat": primary_threat,
            "should_evacuate": max_threat >= self.threat_threshold,
        }

    def plan_escape(self, current_position: np.ndarray,
                    blocked_paths: List[np.ndarray] = None) -> List[np.ndarray]:
        """
        规划逃生路径

        Args:
            current_position: 当前位置
            blocked_paths: 被阻断的路径

        Returns:
            逃生路径
        """
        if not self.emergency_exits:
            return []

        blocked = blocked_paths or []

        # 找最近可达的出口
        best_exit = None
        best_distance = float('inf')

        for exit_info in self.emergency_exits:
            if not exit_info.get("accessible", True):
                continue

            exit_pos = exit_info["position"]

            # 检查是否被阻断
            is_blocked = False
            for blocked_zone in blocked:
                if np.linalg.norm(exit_pos - blocked_zone) < 2.0:
                    is_blocked = True
                    break

            # 检查是否在危险区
            for zone in self.danger_zones:
                if np.linalg.norm(exit_pos - zone["center"]) < zone["radius"]:
                    is_blocked = True
                    break

            if is_blocked:
                continue

            distance = np.linalg.norm(exit_pos - current_position)
            if distance < best_distance:
                best_distance = distance
                best_exit = exit_pos

        if best_exit is None:
            return []

        # 规划路径
        self.escape_path = self.navigator.plan_path(
            current_position[:2], best_exit[:2]
        )

        return self.escape_path

    def get_escape_action(self, current_state: RobotState,
                          observation: Observation) -> Action:
        """
        获取逃生动作

        Args:
            current_state: 当前状态
            observation: 当前观测

        Returns:
            逃生动作
        """
        # 评估威胁
        threat = self.assess_threat(observation)

        if threat["should_evacuate"] and not self.in_emergency:
            # 进入紧急状态
            self.in_emergency = True
            self.current_threat = threat["primary_threat"]["type"] if threat["primary_threat"] else "unknown"

            # 规划逃生路径
            self.plan_escape(current_state.position)

        if self.in_emergency:
            # 执行逃生
            if not self.escape_path:
                # 无路可逃，就地防护
                return Action(
                    action_type="shelter",
                    parameters={
                        "reason": "no_escape_path",
                        "threat": self.current_threat,
                    }
                )

            # 导航到出口
            nav_action = self.navigator.get_control_command(current_state)

            # 提高速度
            if nav_action.parameters.get("linear_velocity"):
                nav_action.parameters["linear_velocity"] *= 1.5
                nav_action.parameters["emergency"] = True

            return nav_action

        return Action(action_type="continue", parameters={})

    def reset(self):
        """重置状态"""
        self.in_emergency = False
        self.current_threat = None
        self.escape_path = []
        self.danger_zones = []


class EmbodiedAgent:
    """
    具身智能体

    功能：
    - 集成感知/决策/执行
    - 强化学习训练
    - 任务执行
    - 自主决策
    """

    def __init__(self, robot_type: RobotType = RobotType.INSPECTION):
        self.robot_type = robot_type

        # 状态
        self.state = RobotState(
            position=np.zeros(3),
            orientation=np.zeros(3),
            velocity=np.zeros(3),
            angular_velocity=np.zeros(3),
        )

        # 模块
        self.perception = VisualPerceptionModule()
        self.navigator = AutonomousNavigator()
        self.escape_agent = EmergencyEscapeAgent(self.navigator)

        # 传感器
        self.sensors: Dict[str, SensorType] = {}

        # 任务
        self.current_task: Optional[TaskType] = None
        self.task_progress = 0.0

        # 决策策略（简化的策略网络模拟）
        self.policy_weights: Dict[str, np.ndarray] = {}

        # 历史
        self.episode_history: List[TrainingEpisode] = []

    def add_sensor(self, sensor_id: str, sensor_type: SensorType):
        """添加传感器"""
        self.sensors[sensor_id] = sensor_type

    def observe(self) -> Observation:
        """获取观测"""
        sensor_readings = {}

        for sensor_id, sensor_type in self.sensors.items():
            # 模拟传感器读数
            if sensor_type == SensorType.CAMERA_RGB:
                data = np.random.randint(0, 255, size=(480, 640, 3), dtype=np.uint8)
            elif sensor_type == SensorType.LIDAR:
                data = np.random.uniform(-10, 10, size=(1000, 3))
            elif sensor_type == SensorType.CAMERA_THERMAL:
                data = np.random.uniform(20, 50, size=(120, 160))
            elif sensor_type == SensorType.IMU:
                data = {
                    "acceleration": np.random.normal(0, 0.1, size=3),
                    "gyroscope": np.random.normal(0, 0.01, size=3),
                }
            else:
                data = {}

            sensor_readings[sensor_id] = SensorReading(
                sensor_type=sensor_type,
                timestamp=datetime.now(),
                data=data,
            )

        # 处理视觉数据
        detected_objects = []
        detected_hazards = []

        for reading in sensor_readings.values():
            if reading.sensor_type == SensorType.CAMERA_RGB:
                result = self.perception.process_image(reading.data)
                detected_objects.extend(result.get("objects", []))
                detected_hazards.extend(result.get("hazards", []))

        return Observation(
            timestamp=datetime.now(),
            robot_state=self.state,
            sensor_readings=sensor_readings,
            detected_objects=detected_objects,
            detected_hazards=detected_hazards,
            environment={
                "temperature": 25 + np.random.normal(0, 5),
                "humidity": 60 + np.random.normal(0, 10),
                "noise_level": 70 + np.random.normal(0, 10),
            }
        )

    def decide(self, observation: Observation) -> Action:
        """
        决策

        Args:
            observation: 当前观测

        Returns:
            决策动作
        """
        # 首先检查紧急情况
        escape_action = self.escape_agent.get_escape_action(self.state, observation)
        if escape_action.action_type not in ["continue", "stop"]:
            return escape_action

        # 根据任务类型决策
        if self.current_task == TaskType.PATROL:
            return self._patrol_policy(observation)
        elif self.current_task == TaskType.INSPECTION:
            return self._inspection_policy(observation)
        elif self.current_task == TaskType.EMERGENCY_RESPONSE:
            return self._emergency_policy(observation)
        else:
            return Action(action_type="idle", parameters={})

    def _patrol_policy(self, observation: Observation) -> Action:
        """巡检策略"""
        # 沿路径巡检
        if self.navigator.is_navigating:
            return self.navigator.get_control_command(self.state)
        else:
            return Action(action_type="wait", parameters={"reason": "patrol_complete"})

    def _inspection_policy(self, observation: Observation) -> Action:
        """检测策略"""
        # 检测到设备时停下来分析
        if observation.detected_objects:
            for obj in observation.detected_objects:
                if obj["class"] in ["valve", "pump", "turbine"]:
                    return Action(
                        action_type="inspect",
                        parameters={
                            "target": obj["class"],
                            "duration": 5.0,
                        }
                    )

        return self.navigator.get_control_command(self.state)

    def _emergency_policy(self, observation: Observation) -> Action:
        """应急策略"""
        # 直接使用逃生代理
        return self.escape_agent.get_escape_action(self.state, observation)

    def execute(self, action: Action, dt: float = 0.1) -> RobotState:
        """
        执行动作

        Args:
            action: 动作
            dt: 时间步长

        Returns:
            新状态
        """
        if action.action_type == "move":
            v = action.parameters.get("linear_velocity", 0)
            w = action.parameters.get("angular_velocity", 0)

            # 更新姿态
            self.state.orientation[2] += w * dt

            # 更新位置
            yaw = self.state.orientation[2]
            self.state.position[0] += v * np.cos(yaw) * dt
            self.state.position[1] += v * np.sin(yaw) * dt

            # 更新速度
            self.state.velocity = np.array([
                v * np.cos(yaw),
                v * np.sin(yaw),
                0,
            ])
            self.state.angular_velocity = np.array([0, 0, w])
            self.state.is_moving = True

        elif action.action_type == "stop":
            self.state.velocity = np.zeros(3)
            self.state.angular_velocity = np.zeros(3)
            self.state.is_moving = False

        elif action.action_type == "inspect":
            # 停下来检测
            self.state.is_moving = False

        # 电池消耗
        if self.state.is_moving:
            self.state.battery_level -= 0.0001 * dt

        return self.state

    def set_task(self, task_type: TaskType, parameters: Dict[str, Any] = None):
        """设置任务"""
        self.current_task = task_type
        self.task_progress = 0.0

        if task_type == TaskType.PATROL and parameters:
            # 设置巡检路径
            waypoints = parameters.get("waypoints", [])
            if len(waypoints) >= 2:
                self.navigator.current_path = waypoints
                self.navigator.path_index = 0
                self.navigator.is_navigating = True

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "robot_type": self.robot_type.value,
            "position": self.state.position.tolist(),
            "orientation": self.state.orientation.tolist(),
            "battery": self.state.battery_level,
            "is_moving": self.state.is_moving,
            "is_operational": self.state.is_operational,
            "current_task": self.current_task.value if self.current_task else None,
            "task_progress": self.task_progress,
            "in_emergency": self.escape_agent.in_emergency,
            "navigation": self.navigator.get_navigation_status(),
        }


class RobotTrainer:
    """
    机器人训练器

    功能：
    - 强化学习训练
    - 模仿学习
    - 课程学习
    - 训练评估

    支持训练场景：
    - 日常巡检
    - 故障处置
    - 紧急逃生
    - 协同作业
    """

    def __init__(self, agent: EmbodiedAgent):
        self.agent = agent

        # 训练配置
        self.learning_rate = 0.001
        self.discount_factor = 0.99
        self.epsilon = 0.1            # 探索率

        # 经验回放
        self.replay_buffer: List[Tuple] = []
        self.buffer_size = 10000

        # 训练统计
        self.episode_rewards: List[float] = []
        self.episode_lengths: List[int] = []
        self.success_rate: List[float] = []

        # 课程学习
        self.curriculum_level = 0
        self.curriculum_stages = [
            {"name": "basic_navigation", "difficulty": 0.2},
            {"name": "obstacle_avoidance", "difficulty": 0.4},
            {"name": "emergency_response", "difficulty": 0.6},
            {"name": "multi_hazard", "difficulty": 0.8},
            {"name": "full_scenario", "difficulty": 1.0},
        ]

    def create_environment(self, scenario_type: str) -> Dict[str, Any]:
        """
        创建训练环境

        Args:
            scenario_type: 场景类型

        Returns:
            环境配置
        """
        env = {
            "size": (100, 100),
            "obstacles": [],
            "hazards": [],
            "exits": [],
            "start_position": np.array([10.0, 10.0, 0.0]),
            "goal_position": np.array([90.0, 90.0, 0.0]),
        }

        difficulty = self.curriculum_stages[self.curriculum_level]["difficulty"]

        # 根据难度添加障碍物
        n_obstacles = int(10 * difficulty)
        for _ in range(n_obstacles):
            env["obstacles"].append({
                "position": np.random.uniform(10, 90, size=2),
                "radius": np.random.uniform(1, 3),
            })

        # 添加危险区域
        n_hazards = int(3 * difficulty)
        hazard_types = ["fire", "water_leak", "toxic_gas"]
        for _ in range(n_hazards):
            env["hazards"].append({
                "position": np.random.uniform(20, 80, size=2),
                "radius": np.random.uniform(3, 8),
                "type": np.random.choice(hazard_types),
            })

        # 添加紧急出口
        env["exits"] = [
            np.array([5.0, 50.0, 0.0]),
            np.array([95.0, 50.0, 0.0]),
            np.array([50.0, 5.0, 0.0]),
            np.array([50.0, 95.0, 0.0]),
        ]

        return env

    def compute_reward(self, state: RobotState, action: Action,
                       next_state: RobotState, done: bool,
                       info: Dict[str, Any]) -> float:
        """
        计算奖励

        Args:
            state: 当前状态
            action: 动作
            next_state: 下一状态
            done: 是否结束
            info: 附加信息

        Returns:
            奖励值
        """
        reward = 0.0

        # 存活奖励
        reward += 0.1

        # 接近目标奖励
        goal = info.get("goal_position", np.zeros(3))
        dist_before = np.linalg.norm(state.position - goal)
        dist_after = np.linalg.norm(next_state.position - goal)
        reward += (dist_before - dist_after) * 0.5

        # 到达目标奖励
        if dist_after < 1.0:
            reward += 100.0

        # 碰撞惩罚
        if info.get("collision", False):
            reward -= 10.0

        # 进入危险区惩罚
        if info.get("in_danger_zone", False):
            reward -= 5.0

        # 电池耗尽惩罚
        if next_state.battery_level <= 0:
            reward -= 50.0

        # 动作平滑奖励
        if action.action_type == "move":
            v = action.parameters.get("linear_velocity", 0)
            w = action.parameters.get("angular_velocity", 0)
            # 惩罚急转弯
            reward -= abs(w) * 0.1

        return reward

    def train_episode(self, max_steps: int = 1000) -> TrainingEpisode:
        """
        训练一个回合

        Args:
            max_steps: 最大步数

        Returns:
            训练回合记录
        """
        # 创建环境
        env = self.create_environment("training")

        # 初始化
        self.agent.state.position = env["start_position"].copy()
        self.agent.state.orientation = np.zeros(3)
        self.agent.state.battery_level = 1.0

        # 设置紧急出口
        for exit_pos in env["exits"]:
            self.agent.escape_agent.add_emergency_exit(exit_pos)

        episode = TrainingEpisode(
            episode_id=f"EP_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            task_type=TaskType.PATROL,
            start_time=datetime.now(),
            end_time=None,
        )

        total_reward = 0.0
        done = False
        step = 0

        while not done and step < max_steps:
            # 观测
            observation = self.agent.observe()
            episode.observations.append(observation)

            # 决策（带探索）
            if np.random.random() < self.epsilon:
                # 随机动作
                action = Action(
                    action_type="move",
                    parameters={
                        "linear_velocity": np.random.uniform(0, 1),
                        "angular_velocity": np.random.uniform(-1, 1),
                    }
                )
            else:
                action = self.agent.decide(observation)

            episode.actions.append(action)

            # 执行
            prev_state = self.agent.state
            new_state = self.agent.execute(action)

            # 检查碰撞
            collision = False
            for obs in env["obstacles"]:
                if np.linalg.norm(new_state.position[:2] - obs["position"]) < obs["radius"]:
                    collision = True
                    break

            # 检查危险区
            in_danger = False
            for hazard in env["hazards"]:
                if np.linalg.norm(new_state.position[:2] - hazard["position"]) < hazard["radius"]:
                    in_danger = True
                    break

            # 检查是否到达目标
            goal_reached = np.linalg.norm(new_state.position - env["goal_position"]) < 1.0

            # 计算奖励
            info = {
                "goal_position": env["goal_position"],
                "collision": collision,
                "in_danger_zone": in_danger,
            }
            reward = self.compute_reward(prev_state, action, new_state, goal_reached, info)

            episode.rewards.append(reward)
            total_reward += reward

            # 存储经验
            self._store_experience(prev_state, action, reward, new_state, goal_reached)

            # 检查终止条件
            if goal_reached or collision or new_state.battery_level <= 0:
                done = True
                episode.success = goal_reached and not collision

            step += 1

        episode.end_time = datetime.now()
        episode.total_reward = total_reward
        episode.steps = step

        # 更新统计
        self.episode_rewards.append(total_reward)
        self.episode_lengths.append(step)
        self.success_rate.append(1.0 if episode.success else 0.0)

        # 检查是否升级课程
        if len(self.success_rate) >= 10:
            recent_success = np.mean(self.success_rate[-10:])
            if recent_success > 0.8 and self.curriculum_level < len(self.curriculum_stages) - 1:
                self.curriculum_level += 1

        # 学习
        self._learn()

        self.agent.episode_history.append(episode)
        return episode

    def _store_experience(self, state: RobotState, action: Action,
                          reward: float, next_state: RobotState, done: bool):
        """存储经验"""
        experience = (
            state.position.copy(),
            action.parameters.copy(),
            reward,
            next_state.position.copy(),
            done,
        )

        self.replay_buffer.append(experience)

        # 限制缓冲区大小
        if len(self.replay_buffer) > self.buffer_size:
            self.replay_buffer.pop(0)

    def _learn(self, batch_size: int = 32):
        """从经验中学习"""
        if len(self.replay_buffer) < batch_size:
            return

        # 采样批次
        indices = np.random.choice(len(self.replay_buffer), batch_size, replace=False)
        batch = [self.replay_buffer[i] for i in indices]

        # 简化的策略梯度更新（实际应用中使用PyTorch/TensorFlow）
        for state, action_params, reward, next_state, done in batch:
            # 更新策略权重（简化）
            if "move" not in self.agent.policy_weights:
                self.agent.policy_weights["move"] = np.zeros(6)

            # 梯度估计
            gradient = np.concatenate([state, next_state]) * reward * self.learning_rate
            gradient = np.clip(gradient, -1, 1)

            self.agent.policy_weights["move"] += gradient[:6]

    def get_training_stats(self) -> Dict[str, Any]:
        """获取训练统计"""
        if not self.episode_rewards:
            return {}

        return {
            "total_episodes": len(self.episode_rewards),
            "avg_reward": np.mean(self.episode_rewards[-100:]),
            "max_reward": max(self.episode_rewards),
            "avg_length": np.mean(self.episode_lengths[-100:]),
            "recent_success_rate": np.mean(self.success_rate[-100:]) if self.success_rate else 0,
            "curriculum_level": self.curriculum_level,
            "curriculum_stage": self.curriculum_stages[self.curriculum_level]["name"],
        }

    def save_model(self, filepath: str):
        """保存模型"""
        import json

        model_data = {
            "policy_weights": {k: v.tolist() for k, v in self.agent.policy_weights.items()},
            "curriculum_level": self.curriculum_level,
            "training_stats": self.get_training_stats(),
        }

        with open(filepath, 'w') as f:
            json.dump(model_data, f)

    def load_model(self, filepath: str):
        """加载模型"""
        import json

        with open(filepath, 'r') as f:
            model_data = json.load(f)

        self.agent.policy_weights = {
            k: np.array(v) for k, v in model_data["policy_weights"].items()
        }
        self.curriculum_level = model_data.get("curriculum_level", 0)
