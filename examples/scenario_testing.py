#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全场景测试示例 - 场景生成、识别与SIL测试
Full Scenario Testing Example - Generation, Recognition and SIL Testing

本示例展示如何使用YJDT进行：
1. 全场景自动生成
2. 场景特征识别（AI）
3. 软件在环测试与评估

对标无人驾驶汽车测试验证方法
Benchmarking autonomous vehicle testing and validation methodology

Author: YJDT Team
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class ScenarioType(Enum):
    """场景类型枚举"""
    STEADY_STATE = "稳态运行"
    LOAD_REJECTION = "甩负荷"
    STARTUP = "启动"
    SHUTDOWN = "停机"
    FAULT = "故障"
    EXTREME = "极端工况"
    COMBINED = "组合场景"


@dataclass
class Scenario:
    """场景定义"""
    id: str
    name: str
    type: ScenarioType
    description: str
    parameters: Dict
    events: List[Dict]
    duration: float
    acceptance_criteria: Dict


class ScenarioGenerator:
    """全场景生成器"""

    def __init__(self, rated_power: float, rated_head: float, rated_speed: float):
        self.rated_power = rated_power
        self.rated_head = rated_head
        self.rated_speed = rated_speed

    def generate_load_rejection(self, initial_power: float, rejection_ratio: float) -> Scenario:
        """生成甩负荷场景"""
        return Scenario(
            id=f"LR_{int(rejection_ratio*100)}",
            name=f"{int(rejection_ratio*100)}%甩负荷",
            type=ScenarioType.LOAD_REJECTION,
            description=f"初始功率{initial_power}MW，甩负荷{rejection_ratio*100}%",
            parameters={
                'initial_power': initial_power,
                'rejection_ratio': rejection_ratio,
                'initial_head': self.rated_head
            },
            events=[
                {'time': 5.0, 'type': 'load_rejection', 'value': rejection_ratio}
            ],
            duration=120.0,
            acceptance_criteria={
                'max_overspeed': 1.45,
                'max_pressure_rise': 1.50,
                'settling_time': 60.0
            }
        )

    def generate_startup(self, target_power: float, mode: str = 'normal') -> Scenario:
        """生成启动场景"""
        return Scenario(
            id=f"SU_{mode}",
            name=f"{mode}启动至{target_power}MW",
            type=ScenarioType.STARTUP,
            description=f"从停机状态启动至{target_power}MW",
            parameters={
                'target_power': target_power,
                'startup_mode': mode
            },
            events=[
                {'time': 0.0, 'type': 'open_inlet_valve', 'duration': 30.0},
                {'time': 30.0, 'type': 'speed_no_load', 'target_speed': self.rated_speed},
                {'time': 120.0, 'type': 'synchronize', 'duration': 10.0},
                {'time': 130.0, 'type': 'load_up', 'target': target_power, 'rate': 50.0}
            ],
            duration=300.0,
            acceptance_criteria={
                'startup_time': 300.0,
                'sync_accuracy': 0.1,
                'vibration_limit': 0.1
            }
        )

    def generate_fault(self, fault_type: str, location: str, severity: float) -> Scenario:
        """生成故障场景"""
        return Scenario(
            id=f"FT_{fault_type[:2].upper()}",
            name=f"{location}{fault_type}故障",
            type=ScenarioType.FAULT,
            description=f"{location}发生{fault_type}故障，严重程度{severity*100}%",
            parameters={
                'fault_type': fault_type,
                'fault_location': location,
                'fault_severity': severity
            },
            events=[
                {'time': 10.0, 'type': 'inject_fault', 'fault': fault_type,
                 'location': location, 'severity': severity}
            ],
            duration=60.0,
            acceptance_criteria={
                'detection_time': 1.0,
                'isolation_time': 5.0,
                'safe_operation': True
            }
        )

    def generate_extreme(self, extreme_type: str, conditions: Dict) -> Scenario:
        """生成极端工况场景"""
        return Scenario(
            id=f"EX_{extreme_type[:2].upper()}",
            name=f"极端{extreme_type}工况",
            type=ScenarioType.EXTREME,
            description=f"极端{extreme_type}条件下运行",
            parameters={
                'extreme_type': extreme_type,
                **conditions
            },
            events=[
                {'time': 0.0, 'type': 'set_conditions', **conditions}
            ],
            duration=60.0,
            acceptance_criteria={
                'stability': True,
                'within_limits': True
            }
        )

    def generate_combined(self, base_type: str, overlays: List[Dict]) -> Scenario:
        """生成组合场景"""
        events = [{'time': 0.0, 'type': base_type}]
        events.extend(overlays)

        return Scenario(
            id=f"CB_{len(overlays)}",
            name=f"组合场景-{len(overlays)}事件",
            type=ScenarioType.COMBINED,
            description=f"基于{base_type}叠加{len(overlays)}个事件",
            parameters={
                'base_type': base_type,
                'n_overlays': len(overlays)
            },
            events=sorted(events, key=lambda x: x['time']),
            duration=120.0,
            acceptance_criteria={
                'safe_operation': True,
                'recovery': True
            }
        )


class ScenarioLibrary:
    """场景库管理"""

    def __init__(self):
        self.scenarios: List[Scenario] = []

    def add(self, scenario: Scenario):
        self.scenarios.append(scenario)

    def generate_standard_library(self, generator: ScenarioGenerator) -> None:
        """生成标准场景库"""
        print("生成标准场景库...")

        # 甩负荷场景族
        for ratio in [0.25, 0.50, 0.75, 1.0]:
            self.add(generator.generate_load_rejection(1000.0, ratio))

        # 启动场景
        self.add(generator.generate_startup(800.0, 'normal'))
        self.add(generator.generate_startup(1000.0, 'fast'))

        # 故障场景
        fault_types = ['sensor_bias', 'sensor_stuck', 'actuator_stuck', 'communication_loss']
        locations = ['pressure_sensor', 'flow_sensor', 'guide_vane', 'governor']
        for ft, loc in zip(fault_types, locations):
            self.add(generator.generate_fault(ft, loc, 0.8))

        # 极端工况
        self.add(generator.generate_extreme('low_head', {'head': 400.0}))
        self.add(generator.generate_extreme('high_head', {'head': 550.0}))
        self.add(generator.generate_extreme('low_frequency', {'frequency': 49.0}))

        # 组合场景
        self.add(generator.generate_combined('load_change', [
            {'time': 30.0, 'type': 'sensor_fault'},
            {'time': 60.0, 'type': 'head_change', 'delta': -20.0}
        ]))

        print(f"已生成 {len(self.scenarios)} 个标准场景")

    def query(self, scenario_type: ScenarioType = None) -> List[Scenario]:
        if scenario_type is None:
            return self.scenarios
        return [s for s in self.scenarios if s.type == scenario_type]


class ScenarioRecognizer:
    """场景识别器 - 基于AI"""

    def __init__(self):
        self.trained = False
        self.feature_names = [
            'power_mean', 'power_std', 'power_trend',
            'freq_mean', 'freq_std', 'freq_trend',
            'head_mean', 'head_std',
            'gv_mean', 'gv_rate'
        ]

    def extract_features(self, time_series: Dict) -> np.ndarray:
        """提取时序特征"""
        features = []

        for key in ['power', 'frequency', 'head', 'guide_vane']:
            if key in time_series:
                data = np.array(time_series[key])
                features.append(np.mean(data))
                features.append(np.std(data))
                if len(data) > 1:
                    features.append((data[-1] - data[0]) / len(data))

        return np.array(features[:10])  # 确保10个特征

    def train(self, labeled_data: List[Dict]):
        """训练识别模型"""
        print("训练场景识别模型...")
        self.trained = True
        print("模型训练完成")

    def recognize(self, time_series: Dict) -> Dict:
        """识别当前场景"""
        features = self.extract_features(time_series)

        # 简化的规则识别（实际系统使用机器学习）
        power_std = features[1] if len(features) > 1 else 0
        freq_std = features[4] if len(features) > 4 else 0

        if power_std > 100:
            scenario = ScenarioType.LOAD_REJECTION
            confidence = min(0.95, 0.5 + power_std / 500)
        elif freq_std > 0.5:
            scenario = ScenarioType.FAULT
            confidence = min(0.90, 0.5 + freq_std)
        elif power_std < 10 and freq_std < 0.1:
            scenario = ScenarioType.STEADY_STATE
            confidence = 0.95
        else:
            scenario = ScenarioType.COMBINED
            confidence = 0.70

        return {
            'scenario_type': scenario,
            'confidence': confidence,
            'features': features.tolist()
        }


class SILTestRunner:
    """软件在环测试运行器"""

    def __init__(self):
        self.results = []

    def run_scenario(self, scenario: Scenario, system_params: Dict) -> Dict:
        """运行单个场景测试"""
        print(f"  测试: {scenario.name}", end="")

        # 模拟仿真执行
        dt = 0.02
        n_steps = int(scenario.duration / dt)

        # 初始化状态
        power = system_params.get('initial_power', 800.0)
        frequency = 50.0
        speed = system_params.get('rated_speed', 100.0)
        guide_vane = 0.8
        pressure = system_params.get('rated_head', 480.0)

        # 记录数据
        power_history = []
        freq_history = []
        speed_history = []
        pressure_history = []

        # 仿真主循环
        for step in range(n_steps):
            t = step * dt

            # 处理事件
            for event in scenario.events:
                if abs(t - event['time']) < dt:
                    if event['type'] == 'load_rejection':
                        power *= (1 - event['value'])

            # 简化的动态响应
            if scenario.type == ScenarioType.LOAD_REJECTION:
                # 甩负荷响应
                speed_target = 100.0 + (1000.0 - power) / 100.0
                speed += (speed_target - speed) * dt / 5.0
                pressure_surge = 480.0 + (speed - 100.0) * 5.0
                guide_vane = max(0, guide_vane - dt / 10.0)
            else:
                speed = 100.0 + np.random.randn() * 0.1
                pressure_surge = 480.0 + np.random.randn() * 2

            frequency = speed / 100.0 * 50.0

            power_history.append(power)
            freq_history.append(frequency)
            speed_history.append(speed)
            pressure_history.append(pressure_surge)

        # 计算性能指标
        metrics = {
            'max_speed': max(speed_history),
            'max_overspeed': max(speed_history) / 100.0,
            'max_pressure': max(pressure_history),
            'max_pressure_rise': max(pressure_history) / 480.0,
            'settling_time': self._calculate_settling_time(speed_history, dt),
            'power_deviation': np.std(power_history)
        }

        # 评估通过/失败
        passed = True
        failure_reasons = []

        for criterion, limit in scenario.acceptance_criteria.items():
            if criterion in metrics:
                if criterion.startswith('max_'):
                    if metrics[criterion] > limit:
                        passed = False
                        failure_reasons.append(f"{criterion}: {metrics[criterion]:.3f} > {limit}")

        status = "✓" if passed else "✗"
        print(f" {status}")

        result = {
            'scenario_id': scenario.id,
            'scenario_name': scenario.name,
            'passed': passed,
            'metrics': metrics,
            'failure_reasons': failure_reasons,
            'time_series': {
                'power': power_history[::50],  # 降采样
                'speed': speed_history[::50],
                'pressure': pressure_history[::50]
            }
        }

        self.results.append(result)
        return result

    def _calculate_settling_time(self, speed_history: List[float], dt: float) -> float:
        """计算调节时间"""
        target = 100.0
        tolerance = 2.0  # 2%容差

        for i in range(len(speed_history) - 1, 0, -1):
            if abs(speed_history[i] - target) > tolerance:
                return (i + 1) * dt

        return 0.0

    def run_all(self, scenarios: List[Scenario], system_params: Dict) -> Dict:
        """运行所有场景测试"""
        print(f"\n开始执行 {len(scenarios)} 个场景测试...")
        print("-" * 50)

        for scenario in scenarios:
            self.run_scenario(scenario, system_params)

        # 生成汇总
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)

        summary = {
            'total_tests': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': passed / total if total > 0 else 0,
            'results': self.results
        }

        print("-" * 50)
        print(f"测试完成: {passed}/{total} 通过 ({summary['pass_rate']*100:.1f}%)")

        return summary


def demonstrate_scenario_testing():
    """演示全场景测试流程"""

    print("=" * 60)
    print("全场景测试流程演示")
    print("=" * 60)

    # 1. 创建场景生成器
    generator = ScenarioGenerator(
        rated_power=1000.0,
        rated_head=480.0,
        rated_speed=100.0
    )

    # 2. 生成场景库
    library = ScenarioLibrary()
    library.generate_standard_library(generator)

    # 3. 显示场景统计
    print("\n场景库统计:")
    for stype in ScenarioType:
        count = len(library.query(stype))
        if count > 0:
            print(f"  {stype.value}: {count} 个")

    # 4. 创建场景识别器
    recognizer = ScenarioRecognizer()

    # 模拟训练数据
    training_data = [
        {'label': 'steady_state', 'features': np.random.randn(10)},
        {'label': 'load_rejection', 'features': np.random.randn(10) + [5, 0, 0, 0, 0, 0, 0, 0, 0, 0]}
    ]
    recognizer.train(training_data)

    # 5. 运行SIL测试
    runner = SILTestRunner()
    system_params = {
        'initial_power': 1000.0,
        'rated_head': 480.0,
        'rated_speed': 100.0
    }

    summary = runner.run_all(library.scenarios, system_params)

    # 6. 生成报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)

    print("\n按场景类型统计:")
    type_stats = {}
    for result in summary['results']:
        scenario = next((s for s in library.scenarios if s.id == result['scenario_id']), None)
        if scenario:
            stype = scenario.type.value
            if stype not in type_stats:
                type_stats[stype] = {'passed': 0, 'failed': 0}
            if result['passed']:
                type_stats[stype]['passed'] += 1
            else:
                type_stats[stype]['failed'] += 1

    for stype, stats in type_stats.items():
        total = stats['passed'] + stats['failed']
        rate = stats['passed'] / total * 100 if total > 0 else 0
        print(f"  {stype}: {stats['passed']}/{total} ({rate:.0f}%)")

    # 失败场景详情
    failed = [r for r in summary['results'] if not r['passed']]
    if failed:
        print("\n失败场景详情:")
        for f in failed:
            print(f"  {f['scenario_name']}:")
            for reason in f['failure_reasons']:
                print(f"    - {reason}")

    return summary


def demonstrate_real_time_recognition():
    """演示实时场景识别"""

    print("\n" + "=" * 60)
    print("实时场景识别演示")
    print("=" * 60)

    recognizer = ScenarioRecognizer()

    # 模拟不同场景的实时数据
    scenarios_data = {
        '稳态运行': {
            'power': [800 + np.random.randn() * 5 for _ in range(100)],
            'frequency': [50 + np.random.randn() * 0.02 for _ in range(100)],
            'head': [480 + np.random.randn() * 1 for _ in range(100)],
            'guide_vane': [0.8 + np.random.randn() * 0.01 for _ in range(100)]
        },
        '甩负荷': {
            'power': [800 - i * 8 + np.random.randn() * 10 for i in range(100)],
            'frequency': [50 + i * 0.03 + np.random.randn() * 0.1 for i in range(100)],
            'head': [480 + i * 0.5 + np.random.randn() * 5 for i in range(100)],
            'guide_vane': [0.8 - i * 0.008 for i in range(100)]
        },
        '故障状态': {
            'power': [800 + np.random.randn() * 50 for _ in range(100)],
            'frequency': [50 + np.random.randn() * 0.5 for _ in range(100)],
            'head': [480 + np.random.randn() * 10 for _ in range(100)],
            'guide_vane': [0.8 + np.random.randn() * 0.05 for _ in range(100)]
        }
    }

    print("\n实时识别结果:")
    print("-" * 50)

    for scenario_name, data in scenarios_data.items():
        result = recognizer.recognize(data)
        print(f"\n场景: {scenario_name}")
        print(f"  识别结果: {result['scenario_type'].value}")
        print(f"  置信度: {result['confidence']:.2f}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("雅江水电梯级智能系统 - 全场景测试示例")
    print("Yajiang Cascade System - Full Scenario Testing Example")
    print("=" * 60)

    # 全场景测试演示
    summary = demonstrate_scenario_testing()

    # 实时识别演示
    demonstrate_real_time_recognition()

    # 对比无人驾驶测试方法
    print("\n" + "=" * 60)
    print("对标无人驾驶汽车测试验证方法")
    print("=" * 60)

    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │            无人驾驶 vs 智能水电站 测试验证对比              │
    ├─────────────────────────────────────────────────────────────┤
    │  维度        │ 无人驾驶汽车      │ 智能水电站              │
    ├─────────────────────────────────────────────────────────────┤
    │  场景数量    │ 数百万种          │ 数千种                  │
    │  场景生成    │ 仿真+道路采集     │ 工程经验+MOC计算       │
    │  测试里程    │ 数十亿公里        │ 数十年等效运行时间     │
    │  安全等级    │ ASIL-D            │ SIL-3                  │
    │  测试方法    │ MIL→SIL→HIL→VIL  │ MIL→SIL→HIL→现场      │
    │  验收标准    │ 接管率、碰撞率    │ 调节品质、保护动作     │
    ├─────────────────────────────────────────────────────────────┤
    │  本系统特点  │                                              │
    │  - 全场景覆盖: 正常/暂态/故障/极端/组合                     │
    │  - AI识别: 实时场景识别与预测                               │
    │  - 自动评估: 基于验收标准的自动化测试                       │
    │  - 方案对比: 多方案全场景对比分析                           │
    └─────────────────────────────────────────────────────────────┘
    """)

    print("\n" + "=" * 60)
    print("全场景测试示例完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
