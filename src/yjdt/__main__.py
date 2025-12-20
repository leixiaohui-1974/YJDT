#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
雅江水电梯级分层分布式智能系统 - 主入口
Yajiang Hydropower Cascade Hierarchical Distributed Intelligent System - Main Entry

Usage:
    python -m yjdt                    # 显示帮助信息
    python -m yjdt gui                # 启动可视化界面
    python -m yjdt simulate           # 运行基础仿真
    python -m yjdt test               # 运行SIL测试
    python -m yjdt compare            # 运行方案对比
    python -m yjdt version            # 显示版本信息

Author: YJDT Team
"""

import sys
import argparse


def show_banner():
    """显示系统横幅"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║   ██╗   ██╗     ██╗██████╗ ████████╗                              ║
    ║   ╚██╗ ██╔╝     ██║██╔══██╗╚══██╔══╝                              ║
    ║    ╚████╔╝      ██║██║  ██║   ██║                                 ║
    ║     ╚██╔╝  ██   ██║██║  ██║   ██║                                 ║
    ║      ██║   ╚█████╔╝██████╔╝   ██║                                 ║
    ║      ╚═╝    ╚════╝ ╚═════╝    ╚═╝                                 ║
    ║                                                                   ║
    ║   雅江水电梯级分层分布式智能系统                                   ║
    ║   Yajiang Hydropower Cascade Hierarchical Distributed             ║
    ║   Intelligent System                                              ║
    ║                                                                   ║
    ║   Version: 1.0.0                                                  ║
    ║   Author: YJDT Team                                               ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def show_help():
    """显示帮助信息"""
    help_text = """
    可用命令 / Available Commands:
    ─────────────────────────────────────────────────────────────────

    gui         启动Streamlit可视化界面
                Launch Streamlit visualization interface

    simulate    运行基础仿真示例
                Run basic simulation example

    test        运行软件在环测试
                Run software-in-the-loop tests

    compare     运行设计方案对比分析
                Run design scheme comparison analysis

    control     运行分层分布式控制示例
                Run distributed control example

    scenario    运行全场景测试示例
                Run full scenario testing example

    version     显示版本信息
                Show version information

    help        显示此帮助信息
                Show this help message

    ─────────────────────────────────────────────────────────────────

    示例 / Examples:

        python -m yjdt gui
        python -m yjdt simulate
        python -m yjdt compare

    更多信息请参阅文档 / For more information, see documentation.
    """
    print(help_text)


def run_gui():
    """启动GUI"""
    print("正在启动可视化界面...")
    print("Starting visualization interface...")
    try:
        import subprocess
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "src/yjdt/gui/app.py",
            "--server.headless", "true"
        ])
    except Exception as e:
        print(f"启动失败: {e}")
        print("请确保已安装streamlit: pip install streamlit")


def run_simulate():
    """运行仿真"""
    print("运行基础仿真示例...")
    try:
        from examples.basic_simulation import main
        main()
    except ImportError:
        # 尝试直接执行
        import subprocess
        subprocess.run([sys.executable, "examples/basic_simulation.py"])


def run_test():
    """运行测试"""
    print("运行软件在环测试...")
    try:
        from examples.scenario_testing import main
        main()
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "examples/scenario_testing.py"])


def run_compare():
    """运行方案对比"""
    print("运行设计方案对比分析...")
    try:
        from examples.scheme_comparison import main
        main()
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "examples/scheme_comparison.py"])


def run_control():
    """运行控制示例"""
    print("运行分层分布式控制示例...")
    try:
        from examples.distributed_control import main
        main()
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "examples/distributed_control.py"])


def run_scenario():
    """运行场景测试"""
    print("运行全场景测试示例...")
    try:
        from examples.scenario_testing import main
        main()
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "examples/scenario_testing.py"])


def show_version():
    """显示版本信息"""
    version_info = """
    ─────────────────────────────────────────────────────────────────
    雅江水电梯级分层分布式智能系统 (YJDT)
    Yajiang Hydropower Cascade Hierarchical Distributed Intelligent System
    ─────────────────────────────────────────────────────────────────

    版本 Version:      1.0.0
    Python:            {python_version}
    平台 Platform:     {platform}

    核心模块 Core Modules:
      - 水力仿真 Hydraulic Simulation (MOC)
      - 水轮机模型 Turbine Models (Francis/Pelton)
      - 发电机模型 Generator Model (Synchronous)
      - 调速器模型 Governor Models (PID/MPC/Adaptive)
      - 传感器仿真 Sensor Simulation
      - 执行器仿真 Actuator Simulation
      - 分层控制 Hierarchical Control
      - 场景生成 Scenario Generation
      - 场景识别 Scenario Recognition
      - SIL测试 SIL Testing
      - 设计优化 Design Optimization
      - 生命周期分析 Lifecycle Analysis
      - 可视化界面 Visualization GUI

    ─────────────────────────────────────────────────────────────────
    """.format(
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=sys.platform
    )
    print(version_info)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="雅江水电梯级分层分布式智能系统 (YJDT)",
        add_help=False
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=["gui", "simulate", "test", "compare", "control", "scenario", "version", "help"],
        help="要执行的命令"
    )

    args = parser.parse_args()

    show_banner()

    commands = {
        "gui": run_gui,
        "simulate": run_simulate,
        "test": run_test,
        "compare": run_compare,
        "control": run_control,
        "scenario": run_scenario,
        "version": show_version,
        "help": show_help
    }

    if args.command in commands:
        commands[args.command]()
    else:
        show_help()


if __name__ == "__main__":
    main()
