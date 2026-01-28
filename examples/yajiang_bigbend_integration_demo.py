# -*- coding: utf-8 -*-
"""
雅鲁藏布江大拐弯截弯取直引水梯级发电工程 - 集成演示

本示例演示完整的运行能力设计与验证工作流程：
1. ODD (运行设计域) - 定义系统级运行边界
2. MBD (基于模型的设计) - 逆向设计优化
3. MAS (多智能体系统) - ODD约束下的智能调度
4. SIL/HIL 验证 - 软件在环/硬件在环测试
5. 本体仿真 - 5级级联耦合仿真

工程概况:
- 引水隧洞总长度: 约76km
- 设计流量: 2000 m³/s
- 总装机容量: 约60GW
- 级联电站: 墨脱(P1)→多雄藏布(P2)→达木(P3)→巴玉(P4)→通德(P5)
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any

# 导入YJDT各模块
from yjdt.odd import (
    create_yajiang_bigbend_odd,
    ODDZone,
    ODDValidator,
)
from yjdt.mbd import (
    create_yajiang_cascade_model,
    ParameterOptimizer,
    SensitivityAnalyzer,
    ReverseDesignOptimizer,
)
from yjdt.mas import (
    create_yajiang_mas_system,
    ODDScenarioGenerator,
    AdaptiveObjectiveManager,
    MultiSourceIndicatorAggregator,
)
from yjdt.verification import (
    SILVerificationFramework,
    HILVerificationFramework,
    IntegratedVerificationSystem,
    ODDBoundaryVerifier,
    VerificationLevel,
)
from yjdt.simulation import (
    create_yajiang_cascade_simulator,
    CascadeSimulator,
)


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def demo_odd_module():
    """演示ODD模块功能"""
    print_section("1. ODD (运行设计域) 模块演示")

    # 创建雅江大拐弯工程ODD
    odd = create_yajiang_bigbend_odd()
    print(f"\n[创建ODD] 工程: {odd.project_name}")
    print(f"  - 级联电站数量: {len(odd.boundaries)}")
    print(f"  - 过渡态边界数量: {len(odd.transient_boundaries)}")
    print(f"  - 级联边界数量: {len(odd.cascade_boundaries)}")

    # 验证稳态边界
    print("\n[稳态边界验证]")
    test_states = [
        {"station": "motuo", "H": 500, "Q": 1800, "P": 10000},  # 正常范围
        {"station": "motuo", "H": 580, "Q": 2200, "P": 13000},  # 超出范围
    ]

    for state in test_states:
        station = state["station"]
        result = odd.validate_state(station, state)
        zone = result.get("zone", "unknown")
        print(f"  电站: {station}, H={state['H']}m, Q={state['Q']}m³/s, P={state['P']}MW")
        print(f"    → 运行区域: {zone}")
        if result.get("violations"):
            print(f"    → 违规项: {result['violations']}")

    # 验证过渡态边界
    print("\n[过渡态边界验证]")
    transient_state = {
        "H": 520,
        "dH_dt": 15,  # 水头变化率
        "Q": 1900,
        "dQ_dt": 100,  # 流量变化率
        "P": 11000,
        "dP_dt": 500,  # 功率变化率
    }
    result = odd.validate_transient("motuo", transient_state)
    print(f"  墨脱电站过渡态: dH/dt={transient_state['dH_dt']}m/s, dQ/dt={transient_state['dQ_dt']}m³/s²")
    print(f"    → 验证结果: {result}")

    # 级联耦合验证
    print("\n[级联耦合验证]")
    cascade_state = {
        "upstream_Q": 1950,
        "downstream_Q": 1850,
        "pressure_wave_amplitude": 25,
        "cascade_delay": 180,
    }
    result = odd.validate_cascade("motuo_duoxiong", cascade_state)
    print(f"  墨脱→多雄藏布 级联: 流量差={cascade_state['upstream_Q']-cascade_state['downstream_Q']}m³/s")
    print(f"    → 验证结果: {result}")

    return odd


def demo_mbd_module(odd):
    """演示MBD模块功能"""
    print_section("2. MBD (基于模型的设计) 模块演示")

    # 创建级联水电模型
    model = create_yajiang_cascade_model()
    print(f"\n[创建模型] 级联电站数量: {len(model.stations)}")

    for station_id, station in model.stations.items():
        print(f"  - {station_id}: 装机={station.installed_capacity}MW, "
              f"机组数={station.n_units}, 水头={station.design_head}m")

    # 灵敏度分析
    print("\n[灵敏度分析]")
    analyzer = SensitivityAnalyzer(model)

    # 分析水头对功率的灵敏度
    sensitivity_results = analyzer.analyze_parameter_sensitivity(
        parameter_name="head",
        parameter_range=(480, 560),
        output_metric="power",
        station_id="motuo"
    )
    print(f"  墨脱电站水头灵敏度分析:")
    print(f"    → 水头范围: 480m ~ 560m")
    print(f"    → 功率变化率: {sensitivity_results.get('sensitivity', 0):.2f} MW/m")

    # 逆向设计优化
    print("\n[逆向设计优化]")
    optimizer = ReverseDesignOptimizer(model, odd)

    # 优化导叶协调策略
    print("  1) 导叶协调优化 (抑制水锤叠加):")
    guide_vane_result = optimizer.optimize_guide_vane_coordination(
        target_pressure_limit=50,  # 目标压力波幅值限制
        cascade_stations=["motuo", "duoxiong", "damu"],
    )
    print(f"     → 优化结果: {guide_vane_result}")

    # 优化级联降级策略
    print("  2) 级联降级优化 (保护触发下的级联响应):")
    degradation_result = optimizer.optimize_cascade_degradation(
        trigger_event="overspeed_protection",
        affected_stations=["motuo", "duoxiong"],
    )
    print(f"     → 优化结果: {degradation_result}")

    # 优化调速器参数
    print("  3) 调速器参数优化 (低频振荡风险):")
    governor_result = optimizer.optimize_governor_parameters(
        target_damping_ratio=0.1,
        frequency_range=(0.1, 2.0),
    )
    print(f"     → 优化结果: {governor_result}")

    return model


def demo_mas_module(odd, model):
    """演示MAS模块功能"""
    print_section("3. MAS (多智能体系统) 模块演示")

    # 创建ODD感知的MAS系统
    mas = create_yajiang_mas_system(odd, model)
    print(f"\n[创建MAS系统]")
    print(f"  - 中心协调智能体: 1")
    print(f"  - 电站控制智能体: {len(mas.station_agents)}")
    print(f"  - 机组控制智能体: {sum(len(sa.unit_agents) for sa in mas.station_agents.values())}")

    # ODD边界内场景生成
    print("\n[ODD边界内场景生成]")
    scenario_generator = ODDScenarioGenerator(odd)

    scenarios = scenario_generator.generate_scenarios(
        n_scenarios=5,
        scenario_types=["normal", "peak_load", "low_load", "transient", "emergency"]
    )

    for i, scenario in enumerate(scenarios):
        print(f"  场景{i+1}: {scenario.scenario_type}")
        print(f"    → 负荷水平: {scenario.load_level:.1%}")
        print(f"    → ODD区域: {scenario.odd_zone}")
        print(f"    → 约束满足: {scenario.constraints_satisfied}")

    # 多源指标聚合
    print("\n[多源指标聚合]")
    indicator_aggregator = MultiSourceIndicatorAggregator()

    # 模拟多源数据
    scada_data = {
        "motuo_power": 10500,
        "motuo_head": 512,
        "motuo_flow": 1850,
        "duoxiong_power": 9800,
    }
    pmu_data = {
        "frequency": 49.98,
        "voltage_a": 525.2,
        "phase_angle": 32.5,
    }
    prediction_data = {
        "load_forecast_1h": 52000,
        "load_forecast_4h": 48000,
        "inflow_forecast": 1920,
    }
    simulation_data = {
        "pressure_wave_peak": 28,
        "cascade_delay": 165,
        "efficiency": 0.892,
    }

    aggregated = indicator_aggregator.aggregate(
        scada=scada_data,
        pmu=pmu_data,
        prediction=prediction_data,
        simulation=simulation_data,
    )
    print(f"  聚合指标:")
    for key, value in list(aggregated.items())[:5]:
        print(f"    - {key}: {value}")

    # 自适应目标函数更新
    print("\n[自适应目标函数更新]")
    objective_manager = AdaptiveObjectiveManager(mas.central_agent)

    # 基于场景更新
    print("  1) 基于场景更新目标函数权重:")
    old_weights = objective_manager.get_current_weights()
    objective_manager.update_from_scenario(scenarios[0])
    new_weights = objective_manager.get_current_weights()
    print(f"     → 经济性权重: {old_weights.get('economy', 0):.2f} → {new_weights.get('economy', 0):.2f}")
    print(f"     → 安全性权重: {old_weights.get('safety', 0):.2f} → {new_weights.get('safety', 0):.2f}")

    # 基于ODD状态更新
    print("  2) 基于ODD状态更新目标函数:")
    odd_state = odd.get_system_state()
    objective_manager.update_from_odd_state(odd_state)
    print(f"     → 当前ODD区域: {odd_state.current_zone}")
    print(f"     → 降级等级: {odd_state.degradation_level}")

    # 执行调度决策
    print("\n[执行调度决策]")
    system_state = {
        "total_load_demand": 50000,
        "frequency": 49.98,
        "reserve_requirement": 3000,
        "stations": {
            "motuo": {"available_capacity": 12000, "current_output": 10500},
            "duoxiong": {"available_capacity": 11000, "current_output": 9800},
            "damu": {"available_capacity": 10000, "current_output": 9000},
            "bayu": {"available_capacity": 9000, "current_output": 8200},
            "tongde": {"available_capacity": 8000, "current_output": 7500},
        }
    }

    dispatch_result = mas.execute_dispatch(system_state, scenarios[0])
    print(f"  调度结果:")
    print(f"    → 总出力: {dispatch_result.get('total_output', 0):.0f} MW")
    print(f"    → 备用容量: {dispatch_result.get('reserve', 0):.0f} MW")
    print(f"    → ODD合规: {dispatch_result.get('odd_compliant', False)}")

    return mas


def demo_verification_module(odd, model, mas):
    """演示SIL/HIL验证模块"""
    print_section("4. SIL/HIL 验证模块演示")

    # 创建ODD边界验证器
    print("\n[ODD边界验证]")
    odd_verifier = ODDBoundaryVerifier(odd)

    # 验证用例
    test_cases = [
        {
            "name": "正常运行边界",
            "state": {"H": 520, "Q": 1800, "P": 10000},
            "expected_zone": ODDZone.NORMAL,
        },
        {
            "name": "最优运行区域",
            "state": {"H": 510, "Q": 1750, "P": 9500},
            "expected_zone": ODDZone.OPTIMAL,
        },
        {
            "name": "降级运行边界",
            "state": {"H": 550, "Q": 2000, "P": 11500},
            "expected_zone": ODDZone.DEGRADED,
        },
    ]

    for case in test_cases:
        result = odd_verifier.verify_boundary(case["state"], case["expected_zone"])
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status} {case['name']}: 期望={case['expected_zone'].value}, 实际={result.actual_zone.value}")

    # SIL验证框架
    print("\n[SIL (软件在环) 验证]")
    sil_framework = SILVerificationFramework(model, odd)

    # 运行SIL测试套件
    sil_results = sil_framework.run_test_suite(
        test_categories=["functional", "boundary", "stress"],
        coverage_target=0.9,
    )
    print(f"  测试套件执行结果:")
    print(f"    → 总测试数: {sil_results.total_tests}")
    print(f"    → 通过数: {sil_results.passed}")
    print(f"    → 失败数: {sil_results.failed}")
    print(f"    → 覆盖率: {sil_results.coverage:.1%}")

    # HIL验证框架
    print("\n[HIL (硬件在环) 验证]")
    hil_framework = HILVerificationFramework(model, odd)

    # 配置HIL测试
    hil_config = {
        "realtime_target": "PXI",
        "timing_requirement_ms": 10,
        "io_channels": 64,
        "safety_interlocks": True,
    }
    hil_framework.configure(hil_config)

    # 运行HIL测试
    hil_results = hil_framework.run_verification(
        test_scenarios=["load_rejection", "load_acceptance", "islanding"],
        deterministic_timing=True,
    )
    print(f"  HIL验证结果:")
    print(f"    → 实时性能: {hil_results.timing_compliance:.1%}")
    print(f"    → 确定性裕度: {hil_results.deterministic_margin_ms:.2f}ms")
    print(f"    → 安全连锁状态: {hil_results.safety_status}")

    # 集成验证系统
    print("\n[集成验证系统]")
    integrated_system = IntegratedVerificationSystem(
        sil_framework=sil_framework,
        hil_framework=hil_framework,
        odd_verifier=odd_verifier,
    )

    # 执行完整验证流程
    verification_report = integrated_system.execute_full_verification(
        level=VerificationLevel.SYSTEM,
        include_odd_boundary=True,
        include_transient=True,
        include_cascade=True,
    )

    print(f"  综合验证报告:")
    print(f"    → 验证级别: {verification_report.level.value}")
    print(f"    → 总体结果: {verification_report.overall_result}")
    print(f"    → SIL通过率: {verification_report.sil_pass_rate:.1%}")
    print(f"    → HIL通过率: {verification_report.hil_pass_rate:.1%}")
    print(f"    → ODD合规率: {verification_report.odd_compliance_rate:.1%}")

    return verification_report


def demo_cascade_simulation(odd, model):
    """演示级联本体仿真"""
    print_section("5. 级联本体仿真演示")

    # 创建级联仿真器
    simulator = create_yajiang_cascade_simulator(odd, model)
    print(f"\n[创建级联仿真器]")
    print(f"  - 仿真电站: {list(simulator.stations.keys())}")
    print(f"  - 耦合模型: 水力耦合 + 压力波传播")

    # 设置初始条件
    print("\n[设置初始条件]")
    initial_conditions = {
        "motuo": {"H": 520, "Q": 1800, "P": 10000, "n": 125},
        "duoxiong": {"H": 480, "Q": 1750, "P": 9500, "n": 150},
        "damu": {"H": 420, "Q": 1700, "P": 8500, "n": 166.7},
        "bayu": {"H": 380, "Q": 1680, "P": 7800, "n": 187.5},
        "tongde": {"H": 350, "Q": 1650, "P": 7200, "n": 200},
    }
    simulator.set_initial_conditions(initial_conditions)
    print(f"  初始条件已设置")

    # 定义仿真场景: 墨脱电站甩负荷
    print("\n[仿真场景: 墨脱电站甩负荷]")
    scenario = {
        "type": "load_rejection",
        "station": "motuo",
        "load_change": -5000,  # MW
        "trigger_time": 1.0,  # s
    }
    print(f"  事件: {scenario['station']}电站 {scenario['load_change']}MW 负荷突变")
    print(f"  触发时间: {scenario['trigger_time']}s")

    # 执行仿真
    print("\n[执行仿真]")
    simulation_params = {
        "duration": 60.0,  # s
        "time_step": 0.01,  # s
        "output_interval": 1.0,  # s
    }

    results = simulator.run_simulation(
        scenario=scenario,
        params=simulation_params,
        include_pressure_wave=True,
        include_cascade_coupling=True,
    )

    print(f"  仿真完成, 时长: {simulation_params['duration']}s")
    print(f"  时间步长: {simulation_params['time_step']}s")
    print(f"  输出点数: {len(results.time_series)}")

    # 分析结果
    print("\n[仿真结果分析]")

    # 压力波传播
    print("  1) 压力波传播:")
    for station_id in ["motuo", "duoxiong", "damu"]:
        peak_pressure = results.get_peak_pressure(station_id)
        arrival_time = results.get_wave_arrival_time(station_id)
        print(f"     {station_id}: 峰值压力={peak_pressure:.1f}m, 到达时间={arrival_time:.2f}s")

    # 频率响应
    print("  2) 系统频率响应:")
    freq_nadir = results.get_frequency_nadir()
    freq_recovery_time = results.get_frequency_recovery_time()
    print(f"     频率最低点: {freq_nadir:.3f}Hz")
    print(f"     频率恢复时间: {freq_recovery_time:.2f}s")

    # 级联响应
    print("  3) 级联电站响应:")
    for station_id in simulator.stations.keys():
        response = results.get_station_response(station_id)
        print(f"     {station_id}: ΔP={response['delta_P']:.0f}MW, "
              f"响应时间={response['response_time']:.2f}s")

    # ODD边界检查
    print("\n[ODD边界检查]")
    odd_violations = results.check_odd_boundaries(odd)
    if odd_violations:
        print(f"  发现 {len(odd_violations)} 个ODD边界违规:")
        for v in odd_violations[:3]:
            print(f"    - {v['station']} @ {v['time']:.2f}s: {v['parameter']}={v['value']:.1f} "
                  f"(限值: {v['limit']:.1f})")
    else:
        print(f"  ✓ 所有运行点均在ODD边界内")

    return results


def demo_full_workflow():
    """演示完整工作流程"""
    print_section("完整工作流程演示")
    print("\n雅鲁藏布江大拐弯截弯取直引水梯级发电工程")
    print("运行能力设计与验证系统 v2.0.0")
    print("-" * 40)

    # 1. ODD模块
    odd = demo_odd_module()

    # 2. MBD模块
    model = demo_mbd_module(odd)

    # 3. MAS模块
    mas = demo_mas_module(odd, model)

    # 4. 验证模块
    verification_report = demo_verification_module(odd, model, mas)

    # 5. 级联仿真
    simulation_results = demo_cascade_simulation(odd, model)

    # 总结
    print_section("工作流程总结")
    print("""
完整的运行能力设计与验证流程:

1. ODD (运行设计域)
   ├─ 定义稳态运行边界 (OPTIMAL→NORMAL→DEGRADED→RESTRICTED→EMERGENCY→FORBIDDEN)
   ├─ 定义过渡态边界 (变化率限制)
   └─ 定义级联耦合边界 (压力波、流量差)

2. MBD (基于模型的设计)
   ├─ 建立系统级级联水电模型
   ├─ 灵敏度分析
   └─ 逆向设计优化 (导叶协调、降级策略、调速器参数)

3. MAS (多智能体系统)
   ├─ 三层智能体架构 (中心→电站→机组)
   ├─ ODD边界内场景生成
   ├─ 多源指标聚合 (SCADA+PMU+预测+仿真)
   └─ 自适应目标函数更新

4. SIL/HIL验证
   ├─ SIL: 高频次、低成本功能验证
   ├─ HIL: 10ms确定性实时验证
   └─ ODD边界全覆盖验证

5. 本体仿真
   ├─ 5级级联耦合仿真
   ├─ MOC水锤计算
   ├─ 压力波传播分析
   └─ 级联响应评估

工程红线:
  ✓ 不突破ODD边界
  ✓ 不旁路SCADA/保护
  ✓ 无单点失效可旁路
""")

    return {
        "odd": odd,
        "model": model,
        "mas": mas,
        "verification": verification_report,
        "simulation": simulation_results,
    }


if __name__ == "__main__":
    # 运行完整演示
    results = demo_full_workflow()
    print("\n" + "=" * 80)
    print("  演示完成")
    print("=" * 80)
