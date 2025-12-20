#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
设计方案对比示例 - 多方案全场景测试与评估
Scheme Comparison Example - Multi-Scheme Full-Scenario Testing and Evaluation

本示例展示如何使用YJDT进行多个设计方案的全场景在环测试对比。
This example demonstrates how to use YJDT for comparing multiple design
schemes through full-scenario software-in-the-loop testing.

对标无人驾驶汽车L0-L5开发模式
Benchmarking autonomous vehicle L0-L5 development approach

Author: YJDT Team
"""

import numpy as np
from typing import Dict, List, Any

from yjdt.optimization.design_optimizer import DesignScheme, SchemeComparator
from yjdt.optimization.lifecycle import LifecycleAnalyzer, CostBenefitAnalysis
from yjdt.simulation.sil_testing import SILTestFramework, TestCase, TestSuite


def define_design_schemes() -> List[DesignScheme]:
    """定义待比较的设计方案"""

    # 方案一：多级开发方案（现实方案）
    scheme_realistic = DesignScheme(
        name="方案一：多级开发",
        description="""
        多级梯级开发方案，分3-4个梯级电站开发雅江水能资源。
        - 采用混流式水轮机
        - 单机容量1000MW
        - 额定水头480m
        - 引水隧洞长度25km
        - 水流惯性时间Tw=12s

        优势：技术成熟，风险可控，分期建设灵活
        劣势：总体效率略低，投资分散
        """,
        parameters={
            'development_type': 'multi_stage',
            'n_stages': 3,
            'rated_head': 480.0,          # m
            'rated_power': 1000.0,        # MW/台
            'n_units': 4,                 # 台/电站
            'turbine_type': 'francis',
            'tunnel_length': 25000.0,     # m
            'water_inertia_time': 12.0,   # s
            'peak_efficiency': 0.94,
            'capital_cost': 50000.0,      # 百万元
            'construction_period': 8,     # 年
            'design_level': 'L2'          # 对标无人驾驶L2
        }
    )

    # 方案二：单级极限开发方案
    scheme_extreme = DesignScheme(
        name="方案二：单级极限开发",
        description="""
        单级极限开发方案，利用雅江全落差一次开发。
        - 采用冲击式水轮机（Pelton）
        - 单机容量500MW
        - 额定水头2100m（世界最高）
        - 引水隧洞长度45km
        - 水流惯性时间Tw≈25s（极端）

        优势：资源利用效率最高，年发电量最大
        劣势：技术风险极高，世界首创，建设周期长
        """,
        parameters={
            'development_type': 'single_stage',
            'n_stages': 1,
            'rated_head': 2100.0,         # m（世界最高）
            'rated_power': 500.0,         # MW/台
            'n_units': 10,                # 台
            'turbine_type': 'pelton',
            'tunnel_length': 45000.0,     # m
            'water_inertia_time': 25.0,   # s（极端）
            'peak_efficiency': 0.92,
            'capital_cost': 80000.0,      # 百万元
            'construction_period': 12,    # 年
            'design_level': 'L0'          # 需从L0开始开发
        }
    )

    # 方案三：混合开发方案
    scheme_hybrid = DesignScheme(
        name="方案三：混合开发",
        description="""
        混合开发方案，高水头段采用冲击式，低水头段采用混流式。
        - 上级电站：冲击式，水头1200m
        - 下级电站：混流式，水头600m
        - 综合考虑技术风险和资源利用

        优势：平衡风险和效益
        劣势：系统复杂度增加
        """,
        parameters={
            'development_type': 'hybrid',
            'n_stages': 2,
            'rated_head': [1200.0, 600.0],
            'rated_power': [600.0, 800.0],
            'n_units': [6, 4],
            'turbine_type': ['pelton', 'francis'],
            'tunnel_length': [30000.0, 20000.0],
            'water_inertia_time': [18.0, 10.0],
            'peak_efficiency': 0.93,
            'capital_cost': 65000.0,
            'construction_period': 10,
            'design_level': 'L1'
        }
    )

    return [scheme_realistic, scheme_extreme, scheme_hybrid]


def create_test_scenarios() -> List[Dict[str, Any]]:
    """创建全场景测试用例"""

    scenarios = [
        # 正常运行场景
        {
            'name': 'S01_稳态运行',
            'type': 'steady_state',
            'weight': 0.15,
            'description': '额定工况稳态运行',
            'criteria': {
                'frequency_deviation': 0.02,  # ≤0.02Hz
                'power_deviation': 0.01,      # ≤1%
                'efficiency_min': 0.90
            }
        },
        {
            'name': 'S02_负荷跟踪',
            'type': 'load_following',
            'weight': 0.15,
            'description': 'AGC负荷跟踪性能',
            'criteria': {
                'response_time': 30.0,        # ≤30s
                'tracking_error': 0.02,       # ≤2%
                'ramp_rate': 20.0             # ≥20MW/min
            }
        },

        # 暂态过程场景
        {
            'name': 'S03_100%甩负荷',
            'type': 'load_rejection',
            'weight': 0.20,
            'description': '满载甩负荷暂态过程',
            'criteria': {
                'max_overspeed': 1.45,        # ≤145%额定转速
                'max_pressure_rise': 1.50,    # ≤150%额定压力
                'settling_time': 60.0         # ≤60s
            }
        },
        {
            'name': 'S04_紧急停机',
            'type': 'emergency_stop',
            'weight': 0.15,
            'description': '紧急停机响应',
            'criteria': {
                'stop_time': 45.0,            # ≤45s
                'max_water_hammer': 1.40,     # ≤140%
                'generator_protection': True
            }
        },

        # 故障场景
        {
            'name': 'S05_传感器故障',
            'type': 'sensor_fault',
            'weight': 0.10,
            'description': '关键传感器故障工况',
            'criteria': {
                'detection_time': 1.0,        # ≤1s
                'isolation_time': 5.0,        # ≤5s
                'safe_operation': True
            }
        },
        {
            'name': 'S06_执行器故障',
            'type': 'actuator_fault',
            'weight': 0.10,
            'description': '导叶执行器卡死故障',
            'criteria': {
                'backup_activation': 5.0,     # ≤5s
                'safe_shutdown': True
            }
        },

        # 极端工况场景
        {
            'name': 'S07_低水头运行',
            'type': 'low_head',
            'weight': 0.05,
            'description': '最低水头极限运行',
            'criteria': {
                'stability': True,
                'cavitation_free': True,
                'min_efficiency': 0.85
            }
        },
        {
            'name': 'S08_高水头运行',
            'type': 'high_head',
            'weight': 0.05,
            'description': '最高水头极限运行',
            'criteria': {
                'pressure_limit': True,
                'vibration_limit': 0.1,       # ≤0.1mm/s
                'max_efficiency': 0.94
            }
        },

        # 启停场景
        {
            'name': 'S09_正常启动',
            'type': 'startup',
            'weight': 0.05,
            'description': '正常启动并网过程',
            'criteria': {
                'startup_time': 300.0,        # ≤5min
                'synchronization_accuracy': 0.1,  # ≤0.1%
                'smooth_loading': True
            }
        }
    ]

    return scenarios


def run_sil_tests(scheme: DesignScheme, scenarios: List[Dict]) -> Dict[str, Any]:
    """运行软件在环测试"""

    print(f"\n  正在测试: {scheme.name}")
    print(f"  {'='*50}")

    results = {
        'scheme_name': scheme.name,
        'test_results': [],
        'overall_score': 0.0,
        'pass_rate': 0.0
    }

    total_weight = 0.0
    weighted_score = 0.0
    passed_count = 0

    for scenario in scenarios:
        # 模拟SIL测试（实际系统中会调用仿真引擎）
        test_result = simulate_test(scheme, scenario)

        results['test_results'].append({
            'scenario': scenario['name'],
            'passed': test_result['passed'],
            'score': test_result['score'],
            'metrics': test_result['metrics']
        })

        # 计算加权得分
        total_weight += scenario['weight']
        weighted_score += scenario['weight'] * test_result['score']

        if test_result['passed']:
            passed_count += 1
            status = "✓ 通过"
        else:
            status = "✗ 未通过"

        print(f"    {scenario['name']}: {status} (得分: {test_result['score']:.2f})")

    results['overall_score'] = weighted_score / total_weight if total_weight > 0 else 0
    results['pass_rate'] = passed_count / len(scenarios)

    print(f"\n  综合得分: {results['overall_score']:.3f}")
    print(f"  通过率: {results['pass_rate']*100:.1f}%")

    return results


def simulate_test(scheme: DesignScheme, scenario: Dict) -> Dict:
    """模拟单个测试（简化版本）"""

    # 根据方案参数和场景类型计算模拟结果
    params = scheme.parameters

    # 基础得分（根据方案特性）
    base_score = 0.8

    # 根据场景类型调整
    if scenario['type'] == 'load_rejection':
        # 甩负荷测试 - 水流惯性时间影响大
        tw = params.get('water_inertia_time', 10.0)
        if isinstance(tw, list):
            tw = max(tw)

        # Tw越大，控制越困难
        penalty = (tw - 10.0) / 20.0 * 0.3
        score = max(0.4, base_score - penalty)

        # 冲击式水轮机在甩负荷时响应更快
        if params.get('turbine_type') == 'pelton':
            score += 0.05

        metrics = {
            'max_overspeed': 1.20 + tw / 100.0,
            'settling_time': 30.0 + tw * 2
        }
        passed = metrics['max_overspeed'] < 1.45

    elif scenario['type'] == 'steady_state':
        # 稳态运行 - 效率影响大
        eff = params.get('peak_efficiency', 0.92)
        score = base_score + (eff - 0.90) * 2
        metrics = {
            'efficiency': eff,
            'frequency_deviation': 0.01
        }
        passed = True

    elif scenario['type'] == 'low_head' or scenario['type'] == 'high_head':
        # 极限水头 - 水头范围影响
        head = params.get('rated_head', 500.0)
        if isinstance(head, list):
            head = max(head)

        if head > 1500:
            score = base_score - 0.15  # 超高水头风险
        else:
            score = base_score + 0.05

        metrics = {'head_margin': 0.1}
        passed = True

    elif scenario['type'] == 'sensor_fault' or scenario['type'] == 'actuator_fault':
        # 故障场景 - 系统复杂度影响
        dev_type = params.get('development_type', 'multi_stage')
        if dev_type == 'hybrid':
            score = base_score - 0.1  # 混合系统故障诊断更复杂
        else:
            score = base_score

        metrics = {'detection_time': 0.5, 'recovery_success': True}
        passed = True

    else:
        # 其他场景
        score = base_score
        metrics = {}
        passed = True

    # 根据设计等级调整（对标无人驾驶L0-L5）
    design_level = params.get('design_level', 'L2')
    level_bonus = {'L0': -0.1, 'L1': 0.0, 'L2': 0.05, 'L3': 0.08, 'L4': 0.10, 'L5': 0.12}
    score += level_bonus.get(design_level, 0)

    score = min(1.0, max(0.0, score))

    return {
        'passed': passed,
        'score': score,
        'metrics': metrics
    }


def compare_lifecycle_benefits(schemes: List[DesignScheme]) -> Dict[str, Any]:
    """对比全生命周期效益"""

    print("\n" + "=" * 60)
    print("全生命周期效益分析")
    print("=" * 60)

    results = []

    for scheme in schemes:
        params = scheme.parameters

        # 计算年发电量
        rated_power = params.get('rated_power', 1000.0)
        n_units = params.get('n_units', 4)
        if isinstance(rated_power, list):
            total_capacity = sum([p * n for p, n in zip(rated_power, n_units)])
        else:
            total_capacity = rated_power * n_units

        annual_hours = 4500  # 年利用小时数
        annual_generation = total_capacity * annual_hours  # GWh

        # 计算收益
        electricity_price = 0.3  # 元/kWh
        annual_revenue = annual_generation * 1000 * electricity_price / 1e6  # 百万元

        # 运营成本
        annual_opex = params.get('capital_cost', 50000) * 0.01  # 1%资本成本

        # NPV计算（40年，8%折现率）
        capital_cost = params.get('capital_cost', 50000)
        construction_period = params.get('construction_period', 8)

        npv = -capital_cost
        for year in range(1, 41):
            if year > construction_period:
                net_cash = annual_revenue - annual_opex
            else:
                net_cash = -capital_cost / construction_period * 0.5
            npv += net_cash / (1.08 ** year)

        # LCOE计算
        total_generation = annual_generation * (40 - construction_period)
        total_cost = capital_cost + annual_opex * 40
        lcoe = total_cost * 1e6 / (total_generation * 1000) if total_generation > 0 else float('inf')

        result = {
            'scheme_name': scheme.name,
            'total_capacity': total_capacity,
            'annual_generation': annual_generation,
            'capital_cost': capital_cost,
            'npv': npv,
            'lcoe': lcoe,
            'construction_period': construction_period
        }
        results.append(result)

        print(f"\n{scheme.name}:")
        print(f"  总装机容量: {total_capacity:.0f} MW")
        print(f"  年发电量: {annual_generation:.0f} GWh")
        print(f"  资本投资: {capital_cost:.0f} 百万元")
        print(f"  净现值NPV: {npv:.0f} 百万元")
        print(f"  度电成本LCOE: {lcoe:.4f} 元/kWh")
        print(f"  建设周期: {construction_period} 年")

    return results


def generate_comparison_report(
    schemes: List[DesignScheme],
    test_results: List[Dict],
    lifecycle_results: List[Dict]
) -> None:
    """生成方案对比报告"""

    print("\n" + "=" * 60)
    print("方案综合对比报告")
    print("=" * 60)

    # 综合评分维度
    dimensions = ['安全性', '可靠性', '效率', '经济性', '技术风险', '综合得分']

    print("\n各方案评分对比:")
    print("-" * 60)
    header = f"{'评估维度':<12}"
    for scheme in schemes:
        header += f"{scheme.name:<15}"
    print(header)
    print("-" * 60)

    # 计算各维度得分
    for i, scheme in enumerate(schemes):
        test_result = test_results[i]
        lifecycle_result = lifecycle_results[i]

        params = scheme.parameters

        # 安全性得分（基于甩负荷等测试）
        safety_score = test_result['overall_score'] * 0.9 + 0.1

        # 可靠性得分
        reliability_score = 0.85 if params.get('turbine_type') == 'francis' else 0.80

        # 效率得分
        efficiency_score = params.get('peak_efficiency', 0.90) / 0.95

        # 经济性得分（基于NPV和LCOE）
        npv_normalized = (lifecycle_result['npv'] + 50000) / 100000
        economy_score = min(1.0, max(0.0, npv_normalized))

        # 技术风险（越低越好）
        head = params.get('rated_head', 500)
        if isinstance(head, list):
            head = max(head)
        risk_score = 1.0 - min(1.0, (head - 500) / 2000)

        # 综合得分
        weights = [0.25, 0.20, 0.15, 0.25, 0.15]
        overall = (safety_score * weights[0] +
                   reliability_score * weights[1] +
                   efficiency_score * weights[2] +
                   economy_score * weights[3] +
                   risk_score * weights[4])

        scores = [safety_score, reliability_score, efficiency_score,
                  economy_score, risk_score, overall]

        scheme.scores = scores  # 存储得分

    # 打印对比表格
    for dim_idx, dim in enumerate(dimensions):
        row = f"{dim:<12}"
        for scheme in schemes:
            row += f"{scheme.scores[dim_idx]:.3f}         "
        print(row)

    print("-" * 60)

    # 推荐方案
    best_scheme = max(schemes, key=lambda s: s.scores[-1])
    print(f"\n推荐方案: {best_scheme.name}")
    print(f"综合得分: {best_scheme.scores[-1]:.3f}")

    print("\n推荐理由:")
    params = best_scheme.parameters
    if params.get('development_type') == 'multi_stage':
        print("  1. 技术成熟度高，采用混流式水轮机，工程经验丰富")
        print("  2. 分级开发降低单点故障风险，运营灵活")
        print("  3. 水流惯性时间适中，调节品质有保障")
    elif params.get('development_type') == 'hybrid':
        print("  1. 平衡了资源利用效率和技术风险")
        print("  2. 分段采用最适合的机组类型")
        print("  3. 具有一定的技术创新性")

    print("\n后续开发建议（对标无人驾驶L0-L5）:")
    print(f"  当前设计等级: {params.get('design_level', 'L2')}")
    print("  建议路径:")
    print("    L0 -> L1: 完成基础控制系统设计与仿真验证")
    print("    L1 -> L2: 实现自动调节功能，通过SIL全场景测试")
    print("    L2 -> L3: 增加故障诊断与预测功能")
    print("    L3 -> L4: 实现自主决策与优化控制")
    print("    L4 -> L5: 达到完全自主智能运行")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("雅江水电梯级智能系统 - 设计方案对比示例")
    print("Yajiang Hydropower Cascade - Scheme Comparison Example")
    print("=" * 60)

    # 定义设计方案
    schemes = define_design_schemes()
    print(f"\n已加载 {len(schemes)} 个设计方案:")
    for scheme in schemes:
        print(f"  - {scheme.name}")

    # 创建测试场景
    scenarios = create_test_scenarios()
    print(f"\n已创建 {len(scenarios)} 个测试场景")

    # 运行SIL测试
    print("\n" + "=" * 60)
    print("软件在环(SIL)全场景测试")
    print("=" * 60)

    test_results = []
    for scheme in schemes:
        result = run_sil_tests(scheme, scenarios)
        test_results.append(result)

    # 生命周期效益分析
    lifecycle_results = compare_lifecycle_benefits(schemes)

    # 生成对比报告
    generate_comparison_report(schemes, test_results, lifecycle_results)

    print("\n" + "=" * 60)
    print("方案对比分析完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
