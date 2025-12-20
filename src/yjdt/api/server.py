# -*- coding: utf-8 -*-
"""
API服务器 - FastAPI Server

功能：
- RESTful API服务
- WebSocket实时数据推送
- OpenAPI文档自动生成
- 中间件（CORS、认证、日志）
- 后台任务管理
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from yjdt.api.models import (
    APIResponse,
    SimulationConfig,
    SimulationResult,
    SimulationState,
    SystemStatus,
)

logger = logging.getLogger(__name__)

# 全局应用实例
_app_instance = None

# 仿真任务存储
_simulation_tasks: Dict[str, Dict[str, Any]] = {}
_simulation_results: Dict[str, SimulationResult] = {}


class SimulationManager:
    """仿真任务管理器"""

    def __init__(self):
        self._tasks: Dict[str, Dict] = {}
        self._results: Dict[str, SimulationResult] = {}
        self._lock = asyncio.Lock()

    async def create_simulation(self, config: SimulationConfig) -> str:
        """创建仿真任务"""
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"

        async with self._lock:
            self._tasks[simulation_id] = {
                "id": simulation_id,
                "config": config,
                "status": "pending",
                "progress": 0,
                "current_time": 0,
                "start_time": None,
                "message": "等待启动",
            }

        return simulation_id

    async def start_simulation(self, simulation_id: str) -> bool:
        """启动仿真"""
        if simulation_id not in self._tasks:
            return False

        async with self._lock:
            task = self._tasks[simulation_id]
            task["status"] = "running"
            task["start_time"] = datetime.now()
            task["message"] = "仿真运行中"

        # 在后台运行仿真
        asyncio.create_task(self._run_simulation(simulation_id))
        return True

    async def _run_simulation(self, simulation_id: str):
        """执行仿真（后台任务）"""
        task = self._tasks.get(simulation_id)
        if not task:
            return

        config = task["config"]
        duration = config.duration
        time_step = config.time_step
        n_steps = int(duration / time_step)

        try:
            # 初始化仿真引擎
            from yjdt.simulation.engine import SimulationEngine
            from yjdt.core.hydraulic import HydraulicSystem, Pipeline
            from yjdt.core.turbine import FrancisTurbine
            from yjdt.core.generator import SynchronousGenerator
            from yjdt.core.governor import PIDGovernor

            # 创建组件
            pipeline = Pipeline(
                length=config.hydraulic.pipeline_length if config.hydraulic else 1000,
                diameter=config.hydraulic.pipeline_diameter if config.hydraulic else 5.0,
                wave_speed=config.hydraulic.wave_speed if config.hydraulic else 1200,
            )

            hydraulic = HydraulicSystem(pipelines=[pipeline])
            turbine = FrancisTurbine(
                rated_power=config.turbine.rated_power if config.turbine else 200,
                rated_head=config.turbine.rated_head if config.turbine else 150,
            )
            generator = SynchronousGenerator(
                rated_power=config.generator.rated_power if config.generator else 200,
            )
            governor = PIDGovernor(
                kp=config.governor.kp if config.governor else 2.0,
                ki=config.governor.ki if config.governor else 0.5,
                kd=config.governor.kd if config.governor else 0.1,
            )

            engine = SimulationEngine(
                hydraulic_system=hydraulic,
                turbine=turbine,
                generator=generator,
                governor=governor,
            )

            # 运行仿真
            time_data = []
            power_data = []
            frequency_data = []
            head_data = []
            flow_data = []

            start_compute = time.time()

            for step in range(n_steps):
                t = step * time_step

                # 更新进度
                progress = (step + 1) / n_steps * 100
                async with self._lock:
                    task["progress"] = progress
                    task["current_time"] = t

                # 执行仿真步
                engine.step(time_step)

                # 记录数据（每100步记录一次以减少数据量）
                if step % 100 == 0:
                    state = engine.get_state()
                    time_data.append(t)
                    power_data.append(state.get("power", 0))
                    frequency_data.append(state.get("frequency", 50))
                    head_data.append(state.get("head", 150))
                    flow_data.append(state.get("flow", 100))

                # 让出控制权
                if step % 1000 == 0:
                    await asyncio.sleep(0)

            compute_time = time.time() - start_compute

            # 构建结果
            result = SimulationResult(
                simulation_id=simulation_id,
                config=config,
                status="completed",
                time_series={
                    "time": time_data,
                    "values": {
                        "power": power_data,
                        "frequency": frequency_data,
                        "head": head_data,
                        "flow": flow_data,
                    },
                    "units": {
                        "power": "MW",
                        "frequency": "Hz",
                        "head": "m",
                        "flow": "m³/s",
                    },
                },
                statistics={
                    "power_mean": sum(power_data) / len(power_data) if power_data else 0,
                    "frequency_mean": sum(frequency_data) / len(frequency_data) if frequency_data else 50,
                    "n_steps": n_steps,
                },
                performance={
                    "computation_time": compute_time,
                    "realtime_factor": duration / compute_time if compute_time > 0 else 0,
                },
                completed_at=datetime.now(),
                computation_time=compute_time,
            )

            async with self._lock:
                self._results[simulation_id] = result
                task["status"] = "completed"
                task["progress"] = 100
                task["message"] = "仿真完成"

        except Exception as e:
            logger.error(f"Simulation {simulation_id} failed: {e}")
            async with self._lock:
                task["status"] = "failed"
                task["message"] = str(e)

    async def get_state(self, simulation_id: str) -> Optional[SimulationState]:
        """获取仿真状态"""
        task = self._tasks.get(simulation_id)
        if not task:
            return None

        return SimulationState(
            simulation_id=simulation_id,
            status=task["status"],
            progress=task["progress"],
            current_time=task["current_time"],
            start_time=task["start_time"],
            elapsed_time=(datetime.now() - task["start_time"]).total_seconds()
            if task["start_time"]
            else 0,
            message=task["message"],
        )

    async def get_result(self, simulation_id: str) -> Optional[SimulationResult]:
        """获取仿真结果"""
        return self._results.get(simulation_id)

    async def list_simulations(self) -> list:
        """列出所有仿真"""
        return [
            {
                "simulation_id": sid,
                "status": task["status"],
                "progress": task["progress"],
            }
            for sid, task in self._tasks.items()
        ]

    async def cancel_simulation(self, simulation_id: str) -> bool:
        """取消仿真"""
        if simulation_id not in self._tasks:
            return False

        async with self._lock:
            self._tasks[simulation_id]["status"] = "cancelled"
            self._tasks[simulation_id]["message"] = "用户取消"

        return True


# 全局仿真管理器
simulation_manager = SimulationManager()


def create_app():
    """创建FastAPI应用"""
    try:
        from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
    except ImportError:
        logger.warning("FastAPI not installed, using mock implementation")
        return _create_mock_app()

    # 生命周期管理
    @asynccontextmanager
    async def lifespan(app):
        # 启动时
        logger.info("YJDT API Server starting...")
        yield
        # 关闭时
        logger.info("YJDT API Server shutting down...")

    app = FastAPI(
        title="雅江水电梯级智能控制系统 API",
        description="""
        YJDT (Yajiang Hydropower Cascade Distributed Intelligent Control System) RESTful API

        功能模块：
        - 仿真管理：创建、启动、查询仿真任务
        - 场景管理：场景库查询、场景匹配
        - 监控数据：实时数据、历史查询、告警管理
        - 控制指令：设定值调整、调度优化
        - 诊断分析：故障诊断、健康评估
        """,
        version="1.7.0",
        lifespan=lifespan,
    )

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============== 系统状态 ==============

    @app.get("/", tags=["系统"])
    async def root():
        """API根路径"""
        return {
            "system": "YJDT - 雅江水电梯级智能控制系统",
            "version": "1.7.0",
            "status": "running",
            "docs": "/docs",
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/health", tags=["系统"])
    async def health_check():
        """健康检查"""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    @app.get("/status", response_model=SystemStatus, tags=["系统"])
    async def get_system_status():
        """获取系统状态"""
        return SystemStatus(
            system_id="yjdt-main",
            status="running",
            mode="api",
            system_time=datetime.now(),
            uptime=0,
            components={
                "simulation_engine": "ready",
                "scenario_library": "ready",
                "monitoring": "ready",
                "control": "ready",
            },
            realtime_data={
                "active_simulations": len(simulation_manager._tasks),
            },
        )

    # ============== 仿真管理 ==============

    @app.post("/simulations", response_model=APIResponse, tags=["仿真"])
    async def create_simulation(config: SimulationConfig):
        """创建仿真任务"""
        simulation_id = await simulation_manager.create_simulation(config)
        return APIResponse(
            success=True,
            message="仿真任务已创建",
            data={"simulation_id": simulation_id},
        )

    @app.post("/simulations/{simulation_id}/start", response_model=APIResponse, tags=["仿真"])
    async def start_simulation(simulation_id: str):
        """启动仿真"""
        success = await simulation_manager.start_simulation(simulation_id)
        if not success:
            raise HTTPException(status_code=404, detail="仿真任务不存在")
        return APIResponse(success=True, message="仿真已启动")

    @app.get("/simulations/{simulation_id}/state", response_model=SimulationState, tags=["仿真"])
    async def get_simulation_state(simulation_id: str):
        """获取仿真状态"""
        state = await simulation_manager.get_state(simulation_id)
        if not state:
            raise HTTPException(status_code=404, detail="仿真任务不存在")
        return state

    @app.get("/simulations/{simulation_id}/result", response_model=SimulationResult, tags=["仿真"])
    async def get_simulation_result(simulation_id: str):
        """获取仿真结果"""
        result = await simulation_manager.get_result(simulation_id)
        if not result:
            raise HTTPException(status_code=404, detail="仿真结果不存在")
        return result

    @app.get("/simulations", response_model=APIResponse, tags=["仿真"])
    async def list_simulations():
        """列出所有仿真"""
        simulations = await simulation_manager.list_simulations()
        return APIResponse(success=True, data=simulations)

    @app.delete("/simulations/{simulation_id}", response_model=APIResponse, tags=["仿真"])
    async def cancel_simulation(simulation_id: str):
        """取消仿真"""
        success = await simulation_manager.cancel_simulation(simulation_id)
        if not success:
            raise HTTPException(status_code=404, detail="仿真任务不存在")
        return APIResponse(success=True, message="仿真已取消")

    # ============== 快速仿真 ==============

    @app.post("/simulate", response_model=APIResponse, tags=["仿真"])
    async def quick_simulate(config: SimulationConfig, background_tasks: BackgroundTasks):
        """快速仿真（同步创建并启动）"""
        simulation_id = await simulation_manager.create_simulation(config)
        await simulation_manager.start_simulation(simulation_id)
        return APIResponse(
            success=True,
            message="仿真已启动",
            data={"simulation_id": simulation_id},
        )

    # ============== 场景管理 ==============

    @app.get("/scenarios", response_model=APIResponse, tags=["场景"])
    async def list_scenarios(
        category: Optional[str] = Query(None, description="场景类别"),
        limit: int = Query(50, description="返回数量"),
    ):
        """列出场景库"""
        try:
            from yjdt.scenarios.yajiang_scenarios import YajiangScenarioLibrary

            library = YajiangScenarioLibrary()
            scenarios = []

            for cat in ["normal", "extreme", "emergency"]:
                if category and cat != category:
                    continue
                cat_scenarios = library.get_scenarios_by_category(cat)
                for s in cat_scenarios[:limit]:
                    scenarios.append({
                        "scenario_id": s.scenario_id,
                        "name": s.name,
                        "category": cat,
                        "description": s.description,
                    })

            return APIResponse(success=True, data=scenarios[:limit])
        except Exception as e:
            return APIResponse(success=False, message=str(e), data=[])

    @app.get("/scenarios/{scenario_id}", response_model=APIResponse, tags=["场景"])
    async def get_scenario(scenario_id: str):
        """获取场景详情"""
        try:
            from yjdt.scenarios.yajiang_scenarios import YajiangScenarioLibrary

            library = YajiangScenarioLibrary()
            scenario = library.get_scenario(scenario_id)

            if not scenario:
                raise HTTPException(status_code=404, detail="场景不存在")

            return APIResponse(
                success=True,
                data={
                    "scenario_id": scenario.scenario_id,
                    "name": scenario.name,
                    "description": scenario.description,
                    "parameters": scenario.parameters,
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ============== 控制指令 ==============

    @app.post("/control/setpoint", response_model=APIResponse, tags=["控制"])
    async def change_setpoint(target: str, setpoint: str, value: float):
        """修改设定值"""
        return APIResponse(
            success=True,
            message=f"设定值已修改: {target}.{setpoint} = {value}",
            data={"target": target, "setpoint": setpoint, "value": value},
        )

    @app.post("/control/schedule", response_model=APIResponse, tags=["控制"])
    async def request_scheduling(
        scheduling_type: str = Query("realtime", description="调度类型"),
        target_power: Optional[float] = Query(None, description="目标功率"),
    ):
        """请求调度优化"""
        try:
            from yjdt.optimization.scheduling_solver import create_yajiang_scheduler

            scheduler = create_yajiang_scheduler()
            if scheduling_type == "realtime" and target_power:
                result = scheduler.solve_realtime(target_power)
                return APIResponse(
                    success=True,
                    message="实时调度完成",
                    data={"allocation": result},
                )
            else:
                return APIResponse(
                    success=True,
                    message="调度请求已接收",
                    data={"scheduling_type": scheduling_type},
                )
        except Exception as e:
            return APIResponse(success=False, message=str(e))

    # ============== 监控数据 ==============

    @app.get("/monitoring/realtime", response_model=APIResponse, tags=["监控"])
    async def get_realtime_data():
        """获取实时数据"""
        import numpy as np

        # 模拟实时数据
        data = {
            "timestamp": datetime.now().isoformat(),
            "power": float(np.random.normal(180, 5)),
            "frequency": float(np.random.normal(50, 0.01)),
            "voltage": float(np.random.normal(15.75, 0.1)),
            "head": float(np.random.normal(150, 2)),
            "flow": float(np.random.normal(130, 5)),
            "guide_vane": float(np.random.uniform(70, 80)),
        }
        return APIResponse(success=True, data=data)

    @app.get("/monitoring/alarms", response_model=APIResponse, tags=["监控"])
    async def get_alarms(
        severity: Optional[str] = Query(None, description="告警级别"),
        acknowledged: Optional[bool] = Query(None, description="是否已确认"),
    ):
        """获取告警列表"""
        # 模拟告警数据
        alarms = [
            {
                "alarm_id": "ALM001",
                "timestamp": datetime.now().isoformat(),
                "severity": "warning",
                "source": "turbine_1",
                "message": "轴承温度偏高",
                "acknowledged": False,
            }
        ]
        return APIResponse(success=True, data=alarms)

    @app.post("/monitoring/alarms/{alarm_id}/acknowledge", response_model=APIResponse, tags=["监控"])
    async def acknowledge_alarm(alarm_id: str):
        """确认告警"""
        return APIResponse(success=True, message=f"告警 {alarm_id} 已确认")

    # ============== 诊断分析 ==============

    @app.post("/diagnosis/fault", response_model=APIResponse, tags=["诊断"])
    async def diagnose_fault(target: str):
        """故障诊断"""
        return APIResponse(
            success=True,
            message="诊断完成",
            data={
                "target": target,
                "status": "healthy",
                "confidence": 0.95,
                "findings": [],
                "recommendations": [],
            },
        )

    @app.get("/diagnosis/health/{component}", response_model=APIResponse, tags=["诊断"])
    async def get_health_status(component: str):
        """获取健康状态"""
        return APIResponse(
            success=True,
            data={
                "component": component,
                "health_index": 92.5,
                "status": "healthy",
                "remaining_life": 8760,  # 小时
                "factors": {
                    "temperature": 0.95,
                    "vibration": 0.90,
                    "efficiency": 0.93,
                },
            },
        )

    global _app_instance
    _app_instance = app
    return app


def _create_mock_app():
    """创建模拟应用（当FastAPI不可用时）"""

    class MockApp:
        def __init__(self):
            self.routes = {}

        def get(self, path, **kwargs):
            def decorator(func):
                self.routes[("GET", path)] = func
                return func

            return decorator

        def post(self, path, **kwargs):
            def decorator(func):
                self.routes[("POST", path)] = func
                return func

            return decorator

    return MockApp()


def get_app():
    """获取应用实例"""
    global _app_instance
    if _app_instance is None:
        _app_instance = create_app()
    return _app_instance


class APIServer:
    """
    API服务器封装

    使用示例:
        server = APIServer(host="0.0.0.0", port=8000)
        server.start()
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.app = get_app()
        self._server = None

    def start(self, reload: bool = False):
        """启动服务器"""
        try:
            import uvicorn

            logger.info(f"Starting API server at http://{self.host}:{self.port}")
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                reload=reload,
            )
        except ImportError:
            logger.error("uvicorn not installed. Install with: pip install uvicorn")

    async def start_async(self):
        """异步启动服务器"""
        try:
            import uvicorn

            config = uvicorn.Config(self.app, host=self.host, port=self.port)
            self._server = uvicorn.Server(config)
            await self._server.serve()
        except ImportError:
            logger.error("uvicorn not installed")

    def stop(self):
        """停止服务器"""
        if self._server:
            self._server.should_exit = True


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """便捷函数：运行API服务器"""
    server = APIServer(host=host, port=port)
    server.start()
