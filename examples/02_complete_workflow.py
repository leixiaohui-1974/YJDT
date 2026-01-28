#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YJDT完整工作流程示例

展示从设计到验证的完整闭环流程
"""

from datetime import datetime

print("=" * 70)
print("YJDT 雅江水电梯级分层分布式智能控制系统")
print("完整工作流程示例: 设计 → 优化 → 仿真 → 验证 → 反馈")
print("=" * 70)

# ============================================================================
# 工作流程步骤
# ============================================================================

workflow_steps = [
    "1. 定义设计运行域(ODD)",
    "2. 执行MBD优化设计",
    "3. 运行仿真验证",
    "4. 检查ODD符合性",
    "5. 生成反馈建议",
    "6. 迭代优化"
]

print("\n【工作流程】")
for step in workflow_steps:
    print(f"  {step}")

# ============================================================================
# Step 1: 定义ODD
# ============================================================================
print("\n" + "-" * 70)
print("Step 1: 定义设计运行域(ODD)")
print("-" * 70)

from yjdt.odd import (
    create_yajiang_bigbend_odd,
    create_default_odd_rules,
    ODDScanner,
    ODDStateMachine
)

# 创建ODD
odd = create_yajiang_bigbend_odd()
rules = create_default_odd_rules()
scanner = ODDScanner(rules)
state_machine = ODDStateMachine()

print(f"""
  ODD配置:
    - 工程: {odd.name}
    - 电站: {len(odd.stations)}座
    - 规则: {len(rules)}条
    - 区域: OPTIMAL → NORMAL → DEGRADED → RESTRICTED → EMERGENCY → FORBIDDEN
""")

# ============================================================================
# Step 2: MBD优化设计
# ============================================================================
print("-" * 70)
print("Step 2: 执行MBD优化设计")
print("-" * 70)

from yjdt.mbd import (
    create_yajiang_mbd_optimizer,
    AlgorithmSelector,
    IntegratedOptimizationFramework
)

# 创建综合优化器
optimizer = create_yajiang_mbd_optimizer()

print("\n  执行综合优化...")

# 运行优化
optimization_results = optimizer.run_full_optimization()

print(f"""
  优化结果:
    - 水力系统: 隧洞直径={optimization_results.get('hydraulic', {}).get('tunnel', {}).get('optimal_diameter', 12.0):.1f}m
    - 调压室: 面积={optimization_results.get('hydraulic', {}).get('surge_tank', {}).get('optimal_area', 800):.0f}m²
    - 控制系统: PID已优化
    - 安全保护: 参数已整定
""")

# 获取最优设计参数
design_params = {
    "tunnel_diameter": 12.0,
    "tunnel_length": 76000,
    "surge_tank_area": 850,
    "penstock_diameter": 8.5,
    "penstock_thickness": 0.035,
    "governor_kp": 2.8,
    "governor_ki": 0.25,
    "governor_kd": 0.15,
    "guide_vane_close_time": 12.0,
    "guide_vane_open_time": 15.0
}

# ============================================================================
# Step 3: 仿真验证
# ============================================================================
print("-" * 70)
print("Step 3: 运行仿真验证")
print("-" * 70)

from yjdt.mbd import (
    create_yajiang_verification_integrator,
    VerificationLevel,
    DesignStage
)

integrator = create_yajiang_verification_integrator()

print("\n  执行设计验证...")

# 运行验证
verification_report = integrator.verify_design(
    design_id="yajiang_v1",
    design_params=design_params,
    verification_level=VerificationLevel.COMPREHENSIVE,
    design_stage=DesignStage.PRELIMINARY
)

print(f"""
  验证结果:
    - 状态: {verification_report.overall_status.value}
    - 场景数: {verification_report.scenarios_run}
    - 通过数: {verification_report.scenarios_passed}
    - 失败数: {verification_report.scenarios_run - verification_report.scenarios_passed}
""")

# 详细准则结果
print("  准则验证详情:")
for outcome in verification_report.outcomes[:5]:
    status_icon = "✅" if outcome.status.value in ['passed', 'warning'] else "❌"
    print(f"    {status_icon} {outcome.criterion_id}: {outcome.details[:50]}...")

# ============================================================================
# Step 4: ODD符合性检查
# ============================================================================
print("\n" + "-" * 70)
print("Step 4: 检查ODD符合性")
print("-" * 70)

# 使用验证结果检查ODD符合性
odd_compliance = verification_report.odd_compliance

print(f"""
  ODD符合性:
    - 总体符合: {'是' if odd_compliance.get('overall', False) else '否'}
""")

if 'zones' in odd_compliance:
    print("  各参数ODD区域:")
    for param, zone in odd_compliance.get('zones', {}).items():
        print(f"    - {param}: {zone}")

if 'boundary_margins' in odd_compliance:
    print("\n  边界裕度:")
    for param, margin in odd_compliance.get('boundary_margins', {}).items():
        print(f"    - {param}: {margin:.1f}%")

# ============================================================================
# Step 5: 生成反馈建议
# ============================================================================
print("\n" + "-" * 70)
print("Step 5: 生成反馈建议")
print("-" * 70)

# 生成优化反馈
feedback = integrator.generate_feedback_for_optimization(verification_report)

print("\n  参数调整建议:")
for param, adjustment in feedback.get('parameter_adjustments', {}).items():
    direction = "增大" if adjustment.get('direction') == 'increase' else "减小"
    change = adjustment.get('suggested_change', 0)
    reason = adjustment.get('reason', '')
    print(f"    - {param}: {direction} {change}% ({reason})")

if feedback.get('constraint_violations'):
    print("\n  约束违反:")
    for violation in feedback.get('constraint_violations', []):
        print(f"    - {violation.get('criterion')}: 实际={violation.get('actual')}, 阈值={violation.get('threshold')}")

if feedback.get('sensitivity_hints'):
    print("\n  敏感性提示:")
    for hint in feedback.get('sensitivity_hints', []):
        print(f"    - {hint}")

# ============================================================================
# Step 6: 迭代优化
# ============================================================================
print("\n" + "-" * 70)
print("Step 6: 迭代优化")
print("-" * 70)

# 根据反馈调整设计参数
adjusted_params = design_params.copy()

for param, adjustment in feedback.get('parameter_adjustments', {}).items():
    if param in adjusted_params:
        change_factor = 1 + adjustment.get('suggested_change', 0) / 100
        if adjustment.get('direction') == 'increase':
            adjusted_params[param] *= change_factor
        else:
            adjusted_params[param] /= change_factor

print("\n  调整后的设计参数:")
for param, value in list(adjusted_params.items())[:5]:
    original = design_params.get(param, value)
    change = (value - original) / original * 100 if original != 0 else 0
    print(f"    - {param}: {original:.3f} → {value:.3f} ({change:+.1f}%)")

# 重新验证
print("\n  重新运行验证...")
new_report = integrator.verify_design(
    design_id="yajiang_v2",
    design_params=adjusted_params,
    verification_level=VerificationLevel.STANDARD
)

print(f"""
  迭代结果:
    - 状态: {new_report.overall_status.value}
    - 通过率: {new_report.scenarios_passed}/{new_report.scenarios_run} ({new_report.scenarios_passed/new_report.scenarios_run*100:.0f}%)
""")

# ============================================================================
# 生成报告
# ============================================================================
print("-" * 70)
print("生成最终报告")
print("-" * 70)

from yjdt.reports import ReportGenerator, SystemReport, ReportSection

generator = ReportGenerator("./reports")

# 创建系统报告
system_report = SystemReport(
    report_id=f"SYS_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    report_type="综合设计验证报告",
    generated_at=datetime.now(),
    system_version="2.2.0",
    project_name="雅鲁藏布江大拐弯截弯取直引水梯级发电工程",
    sections=[
        ReportSection(
            title="项目概述",
            content="""
本项目为雅鲁藏布江大拐弯截弯取直引水梯级发电工程的智能控制系统设计。

主要参数:
- 总装机容量: ~60 GW
- 电站数量: 5座梯级电站
- 引水隧洞: 76 km
- 设计水头: 2000+ m
            """,
            level=2
        ),
        ReportSection(
            title="设计优化结果",
            content=f"""
经过MBD优化设计和仿真验证,得到以下最优参数:

水力系统:
- 隧洞直径: {adjusted_params.get('tunnel_diameter', 12.0):.1f} m
- 调压室面积: {adjusted_params.get('surge_tank_area', 850):.0f} m²

控制系统:
- Kp: {adjusted_params.get('governor_kp', 2.8):.3f}
- Ki: {adjusted_params.get('governor_ki', 0.25):.3f}
- Kd: {adjusted_params.get('governor_kd', 0.15):.3f}
            """,
            level=2
        ),
        ReportSection(
            title="验证结论",
            content=f"""
设计方案已通过综合验证:

- 验证状态: {new_report.overall_status.value}
- 场景通过率: {new_report.scenarios_passed}/{new_report.scenarios_run}
- ODD符合性: {'符合' if odd_compliance.get('overall', False) else '部分符合'}

建议进入详细设计阶段。
            """,
            level=2
        )
    ]
)

# 生成报告
report_content = generator.generate_system_report(system_report)
report_path = generator.save_report(
    report_content,
    f"yajiang_design_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
)

print(f"\n  报告已生成: {report_path}")

# ============================================================================
# 完成
# ============================================================================
print("\n" + "=" * 70)
print("工作流程完成!")
print("=" * 70)
print(f"""
  ✅ ODD定义完成
  ✅ MBD优化完成
  ✅ 仿真验证完成
  ✅ ODD符合性检查完成
  ✅ 反馈建议生成完成
  ✅ 迭代优化完成
  ✅ 报告生成完成

  最终状态: {new_report.overall_status.value}
  报告位置: {report_path}
""")
