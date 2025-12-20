# -*- coding: utf-8 -*-
"""
L4级自主运行中试平台 - L4 Autonomous Operation Pilot Platform

基于YX工程建设方案，实现"设计即验证、建设即演练"范式

核心模块：
1. 对抗性场景生成引擎 - 自动搜索系统崩溃点
2. 硬件在环测试框架 - HIL验证控制器
3. 具身智能体训练场 - 机器人自主决策
4. 设计方案验证风洞 - 多方案比选优化
5. 极限工况推演引擎 - 冰崩/地震/溃决模拟
"""

from yjdt.pilot_platform.adversarial_generator import (
    AdversarialScenarioGenerator,
    CornerCaseSearcher,
    FailureModeSynthesizer,
    ScenarioDiffusionModel,
)

from yjdt.pilot_platform.hil_framework import (
    HILTestBench,
    ControllerInterface,
    RealTimeSimulator,
    PowerLevelInterface,
    HILTestCase,
)

from yjdt.pilot_platform.embodied_intelligence import (
    EmbodiedAgent,
    RobotTrainer,
    VisualPerceptionModule,
    AutonomousNavigator,
    EmergencyEscapeAgent,
)

from yjdt.pilot_platform.design_verification import (
    DesignVerificationWindTunnel,
    MultiSchemeComparator,
    SurgeTankOptimizer,
    WaterHammerAnalyzer,
)

__all__ = [
    # 对抗性场景生成
    "AdversarialScenarioGenerator",
    "CornerCaseSearcher",
    "FailureModeSynthesizer",
    "ScenarioDiffusionModel",
    # 硬件在环测试
    "HILTestBench",
    "ControllerInterface",
    "RealTimeSimulator",
    "PowerLevelInterface",
    "HILTestCase",
    # 具身智能
    "EmbodiedAgent",
    "RobotTrainer",
    "VisualPerceptionModule",
    "AutonomousNavigator",
    "EmergencyEscapeAgent",
    # 设计验证
    "DesignVerificationWindTunnel",
    "MultiSchemeComparator",
    "SurgeTankOptimizer",
    "WaterHammerAnalyzer",
]
