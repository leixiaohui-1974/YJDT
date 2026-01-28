# -*- coding: utf-8 -*-
"""
YJDT Web仪表板

提供可视化监控界面：
- 系统状态总览
- ODD实时监控
- 仿真结果展示
- 优化分析面板
"""

from .dashboard_app import create_dashboard_app, DashboardServer

__all__ = ["create_dashboard_app", "DashboardServer"]
