# -*- coding: utf-8 -*-
"""
系统集成模块
System Integration Module

提供统一的系统入口和组件编排
"""

from yjdt.integration.system_facade import (
    YJDTSystem,
    SystemBuilder,
    ComponentRegistry,
    IntegrationContext,
)
from yjdt.integration.data_connector import (
    DataConnector,
    SCADAConnector,
    HistorianConnector,
    OPCUAClient,
    RealtimeDataBridge,
)
from yjdt.integration.scenario_data_adapter import (
    ScenarioDataAdapter,
    OperationalDataCollector,
    ScenarioMatcher,
    DataDrivenScenarioGenerator,
)

__all__ = [
    "YJDTSystem",
    "SystemBuilder",
    "ComponentRegistry",
    "IntegrationContext",
    "DataConnector",
    "SCADAConnector",
    "HistorianConnector",
    "OPCUAClient",
    "RealtimeDataBridge",
    "ScenarioDataAdapter",
    "OperationalDataCollector",
    "ScenarioMatcher",
    "DataDrivenScenarioGenerator",
]
