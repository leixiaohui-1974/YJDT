"""
雅江水电梯级分层分布式智能控制系统
Yajiang Hydropower Cascade Distributed Intelligent Control System (YJDT)

本系统实现了完整的水电站仿真与控制功能，包括：
- 水力系统MOC水锤计算
- 水轮机/发电机全要素仿真
- 传感器和执行器仿真
- 分层分布式控制（PID/MPC）
- 全场景生成与识别
- 软件在环测试
- 可视化界面
"""

__version__ = "1.0.0"
__author__ = "Hydropower Research Team"

from yjdt.core.hydraulic import HydraulicSystem, Pipeline, SurgeTank
from yjdt.core.turbine import FrancisTurbine, PeltonTurbine
from yjdt.core.generator import SynchronousGenerator
from yjdt.core.governor import PIDGovernor, MPCGovernor
from yjdt.simulation.engine import SimulationEngine
from yjdt.control.distributed import DistributedController
from yjdt.scenarios.generator import ScenarioGenerator
from yjdt.scenarios.recognizer import ScenarioRecognizer

__all__ = [
    "HydraulicSystem",
    "Pipeline",
    "SurgeTank",
    "FrancisTurbine",
    "PeltonTurbine",
    "SynchronousGenerator",
    "PIDGovernor",
    "MPCGovernor",
    "SimulationEngine",
    "DistributedController",
    "ScenarioGenerator",
    "ScenarioRecognizer",
]
