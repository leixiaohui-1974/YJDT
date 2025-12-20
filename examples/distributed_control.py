#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分层分布式控制示例 - 梯级水电站协调控制
Distributed Hierarchical Control Example - Cascade Hydropower Coordination

本示例展示雅江梯级水电站的四级分层分布式控制系统：
- 现场级（Field Level）: 20ms周期，PID控制
- 机组级（Unit Level）: 100ms周期，MPC优化
- 厂站级（Plant Level）: 1s周期，负荷分配
- 梯级级（Cascade Level）: 60s周期，水库调度

Author: YJDT Team
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any
import time


class FieldLevelController:
    """现场级控制器 - 执行层"""

    def __init__(self, controller_id: str, kp: float = 3.0, ki: float = 0.5, kd: float = 0.1):
        self.controller_id = controller_id
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.control_cycle = 0.02  # 20ms

        self.integral = 0.0
        self.last_error = 0.0
        self.output = 0.0

    def compute(self, setpoint: float, process_value: float, dt: float) -> float:
        """计算PID控制输出"""
        error = setpoint - process_value

        # PID计算
        self.integral += error * dt
        self.integral = np.clip(self.integral, -10.0, 10.0)  # 抗积分饱和

        derivative = (error - self.last_error) / dt if dt > 0 else 0.0

        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        output = np.clip(output, -1.0, 1.0)

        self.last_error = error
        self.output = output

        return output


class UnitLevelController:
    """机组级控制器 - 优化层"""

    def __init__(self, unit_id: str, prediction_horizon: int = 20):
        self.unit_id = unit_id
        self.prediction_horizon = prediction_horizon
        self.control_cycle = 0.1  # 100ms

        self.power_setpoint = 0.0
        self.frequency_setpoint = 50.0

    def optimize(self, current_state: Dict, constraints: Dict) -> Dict:
        """MPC优化计算"""
        # 简化的MPC：预测未来状态并优化控制序列

        current_power = current_state.get('power', 0.0)
        current_freq = current_state.get('frequency', 50.0)

        # 目标：最小化功率偏差和频率偏差
        power_error = self.power_setpoint - current_power
        freq_error = self.frequency_setpoint - current_freq

        # 简化的优化输出
        guide_vane_delta = 0.01 * power_error + 0.5 * freq_error

        return {
            'guide_vane_command': np.clip(
                current_state.get('guide_vane', 0.5) + guide_vane_delta,
                constraints.get('gv_min', 0.0),
                constraints.get('gv_max', 1.0)
            ),
            'excitation_command': 1.0 + 0.1 * freq_error
        }


class PlantLevelController:
    """厂站级控制器 - 调度层"""

    def __init__(self, plant_id: str, n_units: int):
        self.plant_id = plant_id
        self.n_units = n_units
        self.control_cycle = 1.0  # 1s

        self.total_load_setpoint = 0.0
        self.vibration_zones = [(350, 450), (550, 650)]  # MW

    def dispatch(self, total_load: float, unit_states: List[Dict]) -> List[float]:
        """负荷优化分配"""
        available_units = [i for i, s in enumerate(unit_states) if s.get('available', True)]
        n_available = len(available_units)

        if n_available == 0:
            return [0.0] * self.n_units

        # 初始等分
        base_load = total_load / n_available

        # 避开振动区
        unit_loads = [0.0] * self.n_units
        for i in available_units:
            load = base_load

            for zone_min, zone_max in self.vibration_zones:
                if zone_min < load < zone_max:
                    # 移出振动区
                    if load - zone_min < zone_max - load:
                        load = zone_min - 10
                    else:
                        load = zone_max + 10

            unit_loads[i] = max(0, min(load, unit_states[i].get('max_power', 1000)))

        return unit_loads


class CascadeLevelController:
    """梯级级控制器 - 协调层"""

    def __init__(self, cascade_id: str, n_stations: int):
        self.cascade_id = cascade_id
        self.n_stations = n_stations
        self.control_cycle = 60.0  # 60s

        self.water_level_targets = []
        self.station_capacities = []

    def coordinate(self, total_load: float, station_states: List[Dict]) -> List[Dict]:
        """梯级协调控制"""
        commands = []

        # 考虑水位和发电效益的优化分配
        total_capacity = sum(s.get('capacity', 1000) for s in station_states)

        for i, state in enumerate(station_states):
            capacity = state.get('capacity', 1000)
            water_level = state.get('water_level', 450)
            target_level = self.water_level_targets[i] if i < len(self.water_level_targets) else 450

            # 基础分配比例
            base_ratio = capacity / total_capacity if total_capacity > 0 else 1 / self.n_stations

            # 水位调节因子
            level_error = water_level - target_level
            level_factor = 1.0 + 0.01 * level_error  # 水位高则多发

            power_setpoint = total_load * base_ratio * level_factor
            power_setpoint = max(0, min(power_setpoint, capacity))

            commands.append({
                'station_id': i,
                'power_setpoint': power_setpoint,
                'water_level_target': target_level
            })

        return commands


class DistributedControlSystem:
    """分层分布式控制系统"""

    def __init__(self, n_stations: int, units_per_station: List[int]):
        self.n_stations = n_stations
        self.units_per_station = units_per_station

        # 创建控制器层次
        self.cascade_controller = CascadeLevelController("YJDT", n_stations)

        self.plant_controllers = []
        self.unit_controllers = []
        self.field_controllers = []

        for i in range(n_stations):
            self.plant_controllers.append(
                PlantLevelController(f"PLANT_{i+1}", units_per_station[i])
            )

            for j in range(units_per_station[i]):
                unit_id = f"UNIT_{i+1}_{j+1}"
                self.unit_controllers.append(UnitLevelController(unit_id))
                self.field_controllers.append(FieldLevelController(f"FIELD_{unit_id}"))

        # 初始化水位目标
        self.cascade_controller.water_level_targets = [450.0, 420.0, 380.0][:n_stations]

    def step(self, system_state: Dict, grid_command: float, dt: float) -> Dict:
        """执行一步分层控制"""

        # 梯级级控制 (每60s)
        station_states = []
        for i in range(self.n_stations):
            station_states.append({
                'capacity': sum(self.units_per_station) * 250,  # 简化
                'water_level': system_state.get('water_levels', [450])[i] if i < len(system_state.get('water_levels', [])) else 450
            })

        cascade_commands = self.cascade_controller.coordinate(grid_command, station_states)

        # 厂站级控制 (每1s)
        all_unit_setpoints = []
        unit_idx = 0
        for i, plant_ctrl in enumerate(self.plant_controllers):
            n_units = self.units_per_station[i]
            unit_states = []

            for j in range(n_units):
                if unit_idx < len(system_state.get('units', [])):
                    unit_states.append(system_state['units'][unit_idx])
                else:
                    unit_states.append({'available': True, 'max_power': 1000})
                unit_idx += 1

            station_load = cascade_commands[i]['power_setpoint'] if i < len(cascade_commands) else 0
            unit_loads = plant_ctrl.dispatch(station_load, unit_states)
            all_unit_setpoints.extend(unit_loads)

        # 机组级控制 (每100ms) 和 现场级控制 (每20ms)
        unit_commands = []
        for i, (unit_ctrl, field_ctrl) in enumerate(zip(self.unit_controllers, self.field_controllers)):
            unit_ctrl.power_setpoint = all_unit_setpoints[i] if i < len(all_unit_setpoints) else 0

            if i < len(system_state.get('units', [])):
                current_state = system_state['units'][i]
            else:
                current_state = {'power': 0, 'frequency': 50, 'guide_vane': 0.5}

            # MPC优化
            mpc_output = unit_ctrl.optimize(current_state, {'gv_min': 0, 'gv_max': 1})

            # PID执行
            pid_output = field_ctrl.compute(
                setpoint=mpc_output['guide_vane_command'],
                process_value=current_state.get('guide_vane', 0.5),
                dt=dt
            )

            unit_commands.append({
                'unit_id': i,
                'power_setpoint': all_unit_setpoints[i] if i < len(all_unit_setpoints) else 0,
                'guide_vane_command': mpc_output['guide_vane_command'],
                'pid_output': pid_output
            })

        return {
            'cascade_commands': cascade_commands,
            'unit_commands': unit_commands
        }


def simulate_cascade_system():
    """仿真梯级水电站系统"""

    print("=" * 60)
    print("梯级水电站分层分布式控制仿真")
    print("=" * 60)

    # 系统配置：3个电站，每站4台机组
    n_stations = 3
    units_per_station = [4, 4, 2]  # 10台机组

    # 创建控制系统
    control_system = DistributedControlSystem(n_stations, units_per_station)

    # 仿真参数
    dt = 0.1  # 100ms步长
    t_end = 300.0  # 5分钟仿真
    n_steps = int(t_end / dt)

    # 电网负荷指令（模拟AGC）
    base_load = 8000.0  # 基础负荷 8000MW

    # 初始化系统状态
    system_state = {
        'water_levels': [450.0, 420.0, 385.0],
        'units': []
    }

    for i in range(sum(units_per_station)):
        system_state['units'].append({
            'power': base_load / sum(units_per_station),
            'frequency': 50.0,
            'guide_vane': 0.8,
            'available': True,
            'max_power': 1000.0
        })

    # 记录数据
    time_history = []
    total_power_history = []
    load_command_history = []
    unit_power_history = [[] for _ in range(sum(units_per_station))]

    print("\n开始仿真...")

    for step in range(n_steps):
        t = step * dt
        time_history.append(t)

        # 模拟AGC负荷变化
        if t < 60:
            grid_command = base_load
        elif t < 120:
            grid_command = base_load + 500  # 增加500MW
        elif t < 180:
            grid_command = base_load + 500 - 800  # 减少800MW
        elif t < 240:
            grid_command = base_load - 300 + 1000  # 增加1000MW
        else:
            grid_command = base_load

        load_command_history.append(grid_command)

        # 执行分层控制
        commands = control_system.step(system_state, grid_command, dt)

        # 更新系统状态（简化的物理模型）
        total_power = 0
        for i, cmd in enumerate(commands['unit_commands']):
            # 简化的功率响应
            current_power = system_state['units'][i]['power']
            target_power = cmd['power_setpoint']

            # 一阶惯性响应
            tau = 10.0  # 时间常数
            new_power = current_power + (target_power - current_power) * dt / tau
            new_power = max(0, min(new_power, 1000))

            system_state['units'][i]['power'] = new_power
            system_state['units'][i]['guide_vane'] = cmd['guide_vane_command']

            total_power += new_power
            unit_power_history[i].append(new_power)

        total_power_history.append(total_power)

        # 更新水位（简化模型）
        for i in range(n_stations):
            inflow = 500.0  # 入库流量
            outflow = total_power / n_stations / 10  # 出库流量与发电相关
            dh = (inflow - outflow) / 1000000 * dt  # 水位变化
            system_state['water_levels'][i] += dh

        # 打印进度
        if step % 100 == 0:
            print(f"  t = {t:.1f}s, 总功率 = {total_power:.1f} MW, 指令 = {grid_command:.1f} MW")

    print("\n仿真完成！")

    # 绘图
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    # 总功率响应
    axes[0].plot(time_history, total_power_history, 'b-', linewidth=1.5, label='实际功率')
    axes[0].plot(time_history, load_command_history, 'r--', linewidth=1.5, label='指令功率')
    axes[0].set_ylabel('功率 Power (MW)')
    axes[0].set_title('梯级总功率跟踪响应 / Cascade Total Power Response')
    axes[0].legend()
    axes[0].grid(True)

    # 各机组功率
    colors = plt.cm.tab10(np.linspace(0, 1, sum(units_per_station)))
    for i in range(min(6, sum(units_per_station))):  # 只显示前6台
        axes[1].plot(time_history, unit_power_history[i], color=colors[i],
                     linewidth=1, label=f'机组 {i+1}')
    axes[1].set_ylabel('功率 Power (MW)')
    axes[1].set_title('各机组功率分配 / Unit Power Distribution')
    axes[1].legend(loc='upper right', ncol=3)
    axes[1].grid(True)

    # 跟踪误差
    error = np.array(load_command_history) - np.array(total_power_history)
    axes[2].plot(time_history, error, 'g-', linewidth=1)
    axes[2].axhline(y=0, color='k', linestyle='--')
    axes[2].fill_between(time_history, -50, 50, alpha=0.2, color='green', label='±50MW容差')
    axes[2].set_xlabel('时间 Time (s)')
    axes[2].set_ylabel('跟踪误差 Error (MW)')
    axes[2].set_title('负荷跟踪误差 / Load Tracking Error')
    axes[2].legend()
    axes[2].grid(True)

    plt.tight_layout()
    plt.savefig('distributed_control_simulation.png', dpi=150)
    print("\n仿真结果已保存到 distributed_control_simulation.png")

    # 打印性能指标
    print("\n控制性能指标:")
    print(f"  最大跟踪误差: {max(abs(e) for e in error):.1f} MW")
    print(f"  平均跟踪误差: {np.mean(np.abs(error)):.1f} MW")
    print(f"  误差标准差: {np.std(error):.1f} MW")


def demonstrate_control_hierarchy():
    """演示控制层次结构"""

    print("\n" + "=" * 60)
    print("分层分布式控制层次结构")
    print("=" * 60)

    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │                    梯级调度中心 (Cascade)                    │
    │               控制周期: 60s | 通信协议: IEC 61850            │
    │  功能: 水库调度、梯级协调、电网互动、来水预报               │
    └─────────────────────────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
    ┌───────────┐           ┌───────────┐           ┌───────────┐
    │ 电站1控制  │           │ 电站2控制  │           │ 电站3控制  │
    │ (Plant)   │           │ (Plant)   │           │ (Plant)   │
    │周期: 1s   │           │周期: 1s   │           │周期: 1s   │
    │负荷分配   │           │负荷分配   │           │负荷分配   │
    │振动区规避 │           │振动区规避 │           │振动区规避 │
    └───────────┘           └───────────┘           └───────────┘
          │                       │                       │
     ┌────┼────┐             ┌────┼────┐             ┌────┼────┐
     ▼    ▼    ▼             ▼    ▼    ▼             ▼    ▼    ▼
    ┌──┐ ┌──┐ ┌──┐         ┌──┐ ┌──┐ ┌──┐         ┌──┐ ┌──┐ ┌──┐
    │U1│ │U2│ │..│         │U1│ │U2│ │..│         │U1│ │U2│ │..│
    │  │ │  │ │  │         │  │ │  │ │  │         │  │ │  │ │  │
    │MPC│ │MPC│ │MPC│        │MPC│ │MPC│ │MPC│        │MPC│ │MPC│ │MPC│
    │100ms│100ms│100ms│      │100ms│100ms│100ms│      │100ms│100ms│100ms│
    └──┘ └──┘ └──┘         └──┘ └──┘ └──┘         └──┘ └──┘ └──┘
     │    │    │             │    │    │             │    │    │
    ┌──┐ ┌──┐ ┌──┐         ┌──┐ ┌──┐ ┌──┐         ┌──┐ ┌──┐ ┌──┐
    │PID│ │PID│ │PID│       │PID│ │PID│ │PID│       │PID│ │PID│ │PID│
    │20ms│ │20ms│ │20ms│      │20ms│ │20ms│ │20ms│      │20ms│ │20ms│ │20ms│
    └──┘ └──┘ └──┘         └──┘ └──┘ └──┘         └──┘ └──┘ └──┘
     │    │    │             │    │    │             │    │    │
    ┌──┐ ┌──┐ ┌──┐         ┌──┐ ┌──┐ ┌──┐         ┌──┐ ┌──┐ ┌──┐
    │执│ │执│ │执│         │执│ │执│ │执│         │执│ │执│ │执│
    │行│ │行│ │行│         │行│ │行│ │行│         │行│ │行│ │行│
    │器│ │器│ │器│         │器│ │器│ │器│         │器│ │器│ │器│
    └──┘ └──┘ └──┘         └──┘ └──┘ └──┘         └──┘ └──┘ └──┘

    控制层级说明:
    ─────────────────────────────────────────────────────────────
    层级      周期     功能                        通信
    ─────────────────────────────────────────────────────────────
    梯级级    60s      水库调度、梯级协调          IEC 61850
    厂站级    1s       负荷分配、经济调度          IEC 61850
    机组级    100ms    MPC优化、约束处理           工业以太网
    现场级    20ms     PID执行、闭环控制           现场总线
    ─────────────────────────────────────────────────────────────
    """)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("雅江水电梯级智能系统 - 分层分布式控制示例")
    print("Yajiang Cascade System - Distributed Control Example")
    print("=" * 60)

    # 演示控制层次
    demonstrate_control_hierarchy()

    # 运行仿真
    simulate_cascade_system()

    print("\n" + "=" * 60)
    print("分层分布式控制示例完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
