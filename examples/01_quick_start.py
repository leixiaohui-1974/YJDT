#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YJDT快速入门示例

本示例展示YJDT系统的基本使用方法
"""

print("=" * 60)
print("YJDT 雅江水电梯级分层分布式智能控制系统")
print("快速入门示例")
print("=" * 60)

# ============================================================================
# 1. 导入模块
# ============================================================================
print("\n【1. 导入核心模块】")

try:
    # 导入ODD模块
    from yjdt.odd import (
        SystemODD,
        ODDValidator,
        ODDScanner,
        ODDStateMachine,
        create_yajiang_bigbend_odd,
        create_default_odd_rules,
    )
    print("  ✓ ODD模块导入成功")

    # 导入MBD模块
    from yjdt.mbd import (
        HydraulicSystemOptimizer,
        ControlSystemOptimizer,
        FlexibilityOptimizer,
        SafetyOptimizer,
        create_yajiang_mbd_optimizer,
    )
    print("  ✓ MBD模块导入成功")

    # 导入MAS模块
    from yjdt.mas import (
        FullAutonomousMAS,
        AutonomyLevel,
        create_yajiang_autonomous_mas,
    )
    print("  ✓ MAS模块导入成功")

    # 导入验证模块
    from yjdt.mbd import (
        MBDSimulationVerificationIntegrator,
        create_yajiang_verification_integrator,
    )
    print("  ✓ 验证模块导入成功")

except ImportError as e:
    print(f"  ⚠️ 导入失败: {e}")
    print("  请确保YJDT已正确安装: pip install -e .")
    exit(1)

# ============================================================================
# 2. ODD设计运行域
# ============================================================================
print("\n【2. ODD设计运行域】")

# 创建雅江大拐弯工程ODD
odd = create_yajiang_bigbend_odd()
print(f"  工程名称: {odd.name}")
print(f"  电站数量: {len(odd.stations)}座")

# 创建ODD规则
rules = create_default_odd_rules()
print(f"  ODD规则数量: {len(rules)}条")

# 创建ODD扫描器
scanner = ODDScanner(rules)

# 模拟当前状态
current_state = {
    "frequency": 50.02,
    "pressure": 1.05,
    "power": 0.85,
    "guide_vane": 0.8,
    "surge_level": 0.52
}

# 执行ODD扫描
scan_result = scanner.scan(current_state)
print(f"\n  ODD扫描结果:")
print(f"    当前区域: {scan_result.current_zone.value}")
print(f"    违规数量: {len(scan_result.violations)}")
print(f"    边界裕度: {scan_result.margin_to_boundary:.1f}%")

# ============================================================================
# 3. MBD优化设计
# ============================================================================
print("\n【3. MBD优化设计】")

# 水力系统优化
hydraulic_optimizer = HydraulicSystemOptimizer()

# 优化隧洞断面
print("\n  [水力系统优化]")
tunnel_result = hydraulic_optimizer.optimize_tunnel_section(
    design_flow=2000,  # m³/s
    tunnel_length=76000  # m
)
print(f"    推荐隧洞直径: {tunnel_result.get('optimal_diameter', 'N/A'):.1f} m")
print(f"    经济流速: {tunnel_result.get('economic_velocity', 'N/A'):.2f} m/s")

# 优化调压室
surge_result = hydraulic_optimizer.optimize_surge_tank(
    design_flow=2000,
    tunnel_length=76000,
    tunnel_area=120,
    static_head=2000
)
print(f"    调压室面积: {surge_result.get('optimal_area', 'N/A'):.0f} m²")
print(f"    Thoma稳定系数: {surge_result.get('thoma_ratio', 'N/A'):.2f}")

# 控制系统优化
control_optimizer = ControlSystemOptimizer()
print("\n  [控制系统优化]")

pid_result = control_optimizer.optimize_governor_pid(
    Tw=12.0,  # 水流惯性时间常数
    Tm=8.0,   # 机械惯性时间常数
    sigma=0.04  # 转差系数
)
print(f"    调速器PID: Kp={pid_result.get('kp', 'N/A'):.3f}, Ki={pid_result.get('ki', 'N/A'):.3f}, Kd={pid_result.get('kd', 'N/A'):.3f}")

# ============================================================================
# 4. 灵活性与安全性评估
# ============================================================================
print("\n【4. 灵活性与安全性评估】")

# 灵活性优化
flexibility_optimizer = FlexibilityOptimizer()
flexibility_score = flexibility_optimizer.calculate_flexibility_score({
    "response_time": 8,
    "ramp_rate": 3,
    "operating_range": [0.4, 1.0]
})
print(f"  灵活性评分: {flexibility_score:.1f}/100")

# 安全性优化
safety_optimizer = SafetyOptimizer()
safety_score = safety_optimizer.calculate_safety_score({
    "pressure_margin": 25,
    "stability_margin": 15,
    "protection_reliability": 0.999
})
print(f"  安全性评分: {safety_score:.1f}/100")

# ============================================================================
# 5. 设计验证
# ============================================================================
print("\n【5. 设计验证】")

# 创建验证集成器
integrator = create_yajiang_verification_integrator()

# 定义设计参数
design_params = {
    "tunnel_diameter": 12.0,
    "surge_tank_area": 800,
    "penstock_diameter": 8.0,
    "governor_kp": pid_result.get('kp', 2.5),
    "governor_ki": pid_result.get('ki', 0.3),
    "governor_kd": pid_result.get('kd', 0.1)
}

# 执行验证
from yjdt.mbd import VerificationLevel
report = integrator.verify_design(
    design_id="design_v1",
    design_params=design_params,
    verification_level=VerificationLevel.STANDARD
)

print(f"  验证状态: {report.overall_status.value}")
print(f"  场景通过率: {report.scenarios_passed}/{report.scenarios_run}")

if report.recommendations:
    print(f"  改进建议:")
    for rec in report.recommendations[:3]:
        print(f"    - {rec}")

# ============================================================================
# 6. MAS自主运行
# ============================================================================
print("\n【6. MAS自主运行】")

# 创建全自主MAS
mas = create_yajiang_autonomous_mas()

print(f"  MAS系统已创建")
print(f"  自主等级: L{mas.autonomy_level.value}")
print(f"  ODD区域: {mas.current_zone.value if hasattr(mas, 'current_zone') else 'NORMAL'}")

# ============================================================================
# 总结
# ============================================================================
print("\n" + "=" * 60)
print("【总结】")
print("=" * 60)
print(f"""
  工程: 雅鲁藏布江大拐弯截弯取直引水梯级发电工程
  装机: ~60 GW (5座电站)
  隧洞: 76 km

  ODD状态: {scan_result.current_zone.value}
  灵活性: {flexibility_score:.1f}/100
  安全性: {safety_score:.1f}/100
  验证状态: {report.overall_status.value}

  系统已准备就绪!
""")
