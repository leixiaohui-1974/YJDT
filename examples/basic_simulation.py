#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础仿真示例 - 单机组水轮发电机仿真
Basic Simulation Example - Single Hydropower Unit Simulation

本示例展示如何使用YJDT进行单机组水轮发电机组的稳态和暂态仿真。
This example demonstrates how to use YJDT for steady-state and transient
simulation of a single hydropower unit.

Author: YJDT Team
"""

import numpy as np
import matplotlib.pyplot as plt

# 导入核心模块
from yjdt.core.hydraulic import Pipeline, SurgeTank, HydraulicSystem
from yjdt.core.turbine import FrancisTurbine
from yjdt.core.generator import SynchronousGenerator
from yjdt.core.governor import PIDGovernor


def create_hydraulic_system():
    """创建水力系统模型"""
    # 引水隧洞
    tunnel = Pipeline(
        length=25000.0,      # 25km隧洞
        diameter=12.0,       # 12m直径
        wave_speed=1200.0,   # 压力波速
        friction_factor=0.012,
        n_sections=100
    )

    # 调压室
    surge_tank = SurgeTank(
        area=500.0,          # 500m²面积
        max_level=50.0,      # 最高涌浪
        min_level=-30.0,     # 最低涌浪
        orifice_area=20.0,
        orifice_coefficient=0.7
    )

    # 压力钢管
    penstock = Pipeline(
        length=1500.0,       # 1.5km压力钢管
        diameter=8.0,        # 8m直径
        wave_speed=1000.0,
        friction_factor=0.015,
        n_sections=30
    )

    return HydraulicSystem(
        pipelines=[tunnel, penstock],
        surge_tank=surge_tank
    )


def create_turbine():
    """创建水轮机模型 - 混流式"""
    return FrancisTurbine(
        rated_power=1000.0,    # 额定功率 1000MW
        rated_head=480.0,      # 额定水头 480m
        rated_speed=100.0,     # 额定转速 100rpm
        rated_flow=230.0,      # 额定流量 230m³/s
        efficiency_peak=0.94   # 峰值效率 94%
    )


def create_generator():
    """创建发电机模型 - 同步发电机"""
    return SynchronousGenerator(
        rated_power=1000.0,    # 额定功率 1000MW
        rated_voltage=20.0,    # 额定电压 20kV
        rated_frequency=50.0,  # 额定频率 50Hz
        poles=60,              # 极对数
        inertia_constant=4.0   # 惯性时间常数 4s
    )


def create_governor():
    """创建调速器 - PID调速器"""
    return PIDGovernor(
        kp=3.0,       # 比例增益
        ki=0.5,       # 积分增益
        kd=0.1,       # 微分增益
        bt=0.04,      # 暂态调差系数
        bp=0.05       # 永态调差系数
    )


def run_steady_state_simulation():
    """稳态仿真示例"""
    print("=" * 60)
    print("稳态仿真示例 - Steady State Simulation Example")
    print("=" * 60)

    # 创建模型
    turbine = create_turbine()
    generator = create_generator()
    governor = create_governor()

    # 初始化
    initial_power = 800.0  # 初始功率 800MW
    initial_head = 480.0   # 水头 480m
    initial_opening = 0.8  # 导叶开度 80%

    generator.initialize(mechanical_power=initial_power, voltage=20.0)
    governor.initialize(initial_output=initial_opening)

    print(f"\n初始条件 / Initial Conditions:")
    print(f"  功率 Power: {initial_power} MW")
    print(f"  水头 Head: {initial_head} m")
    print(f"  导叶开度 Guide Vane Opening: {initial_opening * 100}%")

    # 计算稳态工况点
    power, efficiency = turbine.calculate_output(
        head=initial_head,
        guide_vane_opening=initial_opening,
        speed=100.0
    )

    print(f"\n稳态运行点 / Steady State Operating Point:")
    print(f"  输出功率 Output Power: {power:.2f} MW")
    print(f"  效率 Efficiency: {efficiency * 100:.2f}%")
    print(f"  发电机转速 Generator Speed: {generator.speed:.2f} rpm")
    print(f"  发电机频率 Generator Frequency: {generator.speed * 60 / 60:.2f} Hz")


def run_load_change_simulation():
    """负荷变化仿真示例"""
    print("\n" + "=" * 60)
    print("负荷变化仿真示例 - Load Change Simulation Example")
    print("=" * 60)

    # 创建模型
    turbine = create_turbine()
    generator = create_generator()
    governor = create_governor()

    # 初始化
    generator.initialize(mechanical_power=800.0, voltage=20.0)
    governor.initialize(initial_output=0.8)

    # 仿真参数
    dt = 0.02  # 时间步长 20ms
    t_end = 60.0  # 仿真时长 60s
    n_steps = int(t_end / dt)

    # 负荷变化事件：10s时负荷增加50MW
    load_change_time = 10.0
    load_change_amount = 50.0

    # 记录数据
    time = []
    power = []
    frequency = []
    guide_vane = []

    current_power = 800.0

    for i in range(n_steps):
        t = i * dt
        time.append(t)

        # 电网负荷（模拟电网频率响应）
        grid_load = 800.0
        if t >= load_change_time:
            grid_load += load_change_amount

        # 调速器响应
        opening = governor.step(
            frequency=generator.speed,
            reference_frequency=100.0,  # 额定转速作为参考
            dt=dt
        )
        guide_vane.append(opening)

        # 水轮机输出
        mech_power, _ = turbine.calculate_output(
            head=480.0,
            guide_vane_opening=opening,
            speed=generator.speed
        )

        # 发电机响应
        # 简化的频率-功率动态
        power_imbalance = mech_power - grid_load
        generator.speed += power_imbalance / (2 * generator.inertia_constant * generator.rated_power) * dt
        generator.speed = np.clip(generator.speed, 90.0, 110.0)

        power.append(mech_power)
        frequency.append(generator.speed)

    # 绘图
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    axes[0].plot(time, power, 'b-', linewidth=1.5)
    axes[0].axhline(y=800, color='r', linestyle='--', label='初始功率')
    axes[0].axhline(y=850, color='g', linestyle='--', label='目标功率')
    axes[0].axvline(x=load_change_time, color='k', linestyle=':', label='负荷变化时刻')
    axes[0].set_ylabel('功率 Power (MW)')
    axes[0].set_title('机组功率响应 / Unit Power Response')
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(time, [f for f in frequency], 'b-', linewidth=1.5)
    axes[1].axhline(y=100.0, color='r', linestyle='--', label='额定转速')
    axes[1].set_ylabel('转速 Speed (rpm)')
    axes[1].set_title('机组转速响应 / Unit Speed Response')
    axes[1].legend()
    axes[1].grid(True)

    axes[2].plot(time, [g * 100 for g in guide_vane], 'b-', linewidth=1.5)
    axes[2].set_xlabel('时间 Time (s)')
    axes[2].set_ylabel('导叶开度 Opening (%)')
    axes[2].set_title('导叶开度响应 / Guide Vane Response')
    axes[2].grid(True)

    plt.tight_layout()
    plt.savefig('load_change_simulation.png', dpi=150)
    print(f"\n仿真结果已保存到 load_change_simulation.png")

    # 打印关键指标
    print(f"\n仿真结果 / Simulation Results:")
    print(f"  最大频率偏差 Max Frequency Deviation: {abs(min(frequency) - 100.0):.3f} rpm")
    print(f"  稳态功率 Final Power: {power[-1]:.2f} MW")
    print(f"  稳态导叶开度 Final Guide Vane: {guide_vane[-1] * 100:.2f}%")


def run_load_rejection_simulation():
    """甩负荷仿真示例"""
    print("\n" + "=" * 60)
    print("甩负荷仿真示例 - Load Rejection Simulation Example")
    print("=" * 60)

    # 创建模型
    turbine = create_turbine()
    generator = create_generator()
    governor = create_governor()

    # 初始化 - 满载运行
    generator.initialize(mechanical_power=1000.0, voltage=20.0)
    governor.initialize(initial_output=1.0)

    # 仿真参数
    dt = 0.02
    t_end = 120.0
    n_steps = int(t_end / dt)

    # 甩负荷时刻
    rejection_time = 5.0

    # 记录数据
    time = []
    speed = []
    guide_vane = []
    mech_power = []

    for i in range(n_steps):
        t = i * dt
        time.append(t)

        # 电负荷
        if t < rejection_time:
            elec_load = 1000.0
        else:
            elec_load = 0.0  # 全甩

        # 调速器响应
        opening = governor.step(
            frequency=generator.speed,
            reference_frequency=100.0,
            dt=dt
        )
        guide_vane.append(opening)

        # 水轮机输出
        power, _ = turbine.calculate_output(
            head=480.0,
            guide_vane_opening=opening,
            speed=generator.speed
        )
        mech_power.append(power)

        # 发电机动态 (简化的摇摆方程)
        power_imbalance = power - elec_load
        acceleration = power_imbalance / (2 * generator.inertia_constant * generator.rated_power)
        generator.speed += acceleration * dt

        speed.append(generator.speed)

    # 计算关键指标
    max_speed = max(speed)
    overspeed_ratio = max_speed / 100.0

    # 找稳定时间（速度恢复到±2%）
    settling_time = t_end
    for i in range(len(speed)):
        if time[i] > rejection_time:
            if all(abs(s - 100.0) < 2.0 for s in speed[i:min(i+100, len(speed))]):
                settling_time = time[i] - rejection_time
                break

    print(f"\n甩负荷仿真结果 / Load Rejection Results:")
    print(f"  最大转速 Max Speed: {max_speed:.2f} rpm")
    print(f"  飞逸比 Overspeed Ratio: {overspeed_ratio:.3f}")
    print(f"  调节时间 Settling Time: {settling_time:.1f} s")

    # 安全判断
    if overspeed_ratio < 1.45:
        print(f"  ✓ 飞逸比满足安全要求 (< 1.45)")
    else:
        print(f"  ✗ 飞逸比超出安全限制!")

    # 绘图
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    axes[0].plot(time, speed, 'b-', linewidth=1.5)
    axes[0].axhline(y=100.0, color='g', linestyle='--', label='额定转速')
    axes[0].axhline(y=145.0, color='r', linestyle='--', label='飞逸限制')
    axes[0].axvline(x=rejection_time, color='k', linestyle=':', label='甩负荷时刻')
    axes[0].set_ylabel('转速 Speed (rpm)')
    axes[0].set_title('甩负荷转速响应 / Load Rejection Speed Response')
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(time, [g * 100 for g in guide_vane], 'b-', linewidth=1.5)
    axes[1].axvline(x=rejection_time, color='k', linestyle=':', label='甩负荷时刻')
    axes[1].set_ylabel('导叶开度 Opening (%)')
    axes[1].set_title('导叶关闭响应 / Guide Vane Closing Response')
    axes[1].grid(True)

    axes[2].plot(time, mech_power, 'b-', linewidth=1.5)
    axes[2].axvline(x=rejection_time, color='k', linestyle=':', label='甩负荷时刻')
    axes[2].set_xlabel('时间 Time (s)')
    axes[2].set_ylabel('机械功率 Mech Power (MW)')
    axes[2].set_title('机械功率响应 / Mechanical Power Response')
    axes[2].grid(True)

    plt.tight_layout()
    plt.savefig('load_rejection_simulation.png', dpi=150)
    print(f"\n仿真结果已保存到 load_rejection_simulation.png")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("雅江水电梯级智能系统 - 基础仿真示例")
    print("Yajiang Hydropower Cascade Intelligent System - Basic Examples")
    print("=" * 60)

    # 运行稳态仿真
    run_steady_state_simulation()

    # 运行负荷变化仿真
    run_load_change_simulation()

    # 运行甩负荷仿真
    run_load_rejection_simulation()

    print("\n" + "=" * 60)
    print("所有仿真完成 / All simulations completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
