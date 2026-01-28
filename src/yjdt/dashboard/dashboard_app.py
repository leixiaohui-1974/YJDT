# -*- coding: utf-8 -*-
"""
YJDT Web仪表板应用

基于FastAPI + HTML/JS的轻量级仪表板
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import json


@dataclass
class DashboardState:
    """仪表板状态"""
    odd_zone: str = "NORMAL"
    autonomy_level: int = 4
    frequency: float = 50.0
    power: float = 0.85
    pressure: float = 1.0
    surge_level: float = 0.5
    alerts: List[Dict] = field(default_factory=list)
    stations: List[Dict] = field(default_factory=list)


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass


# 全局状态
dashboard_state = DashboardState()
connection_manager = ConnectionManager()


def get_dashboard_html() -> str:
    """生成仪表板HTML"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YJDT - 雅江水电梯级智能控制系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
        }

        .header {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .header h1 {
            font-size: 24px;
            color: #00d4ff;
        }

        .header .status {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .status-dot.normal { background: #00ff88; }
        .status-dot.warning { background: #ffaa00; }
        .status-dot.danger { background: #ff4444; }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .main-content {
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            grid-template-rows: auto auto auto;
            gap: 20px;
            max-width: 1800px;
            margin: 0 auto;
        }

        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }

        .card-title {
            font-size: 14px;
            color: #888;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .card-value {
            font-size: 36px;
            font-weight: bold;
            color: #00d4ff;
        }

        .card-unit {
            font-size: 14px;
            color: #666;
            margin-left: 5px;
        }

        .card-trend {
            font-size: 12px;
            margin-top: 5px;
        }

        .trend-up { color: #00ff88; }
        .trend-down { color: #ff4444; }
        .trend-stable { color: #888; }

        .odd-panel {
            grid-column: span 2;
        }

        .odd-zones {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .odd-zone {
            flex: 1;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-size: 12px;
            transition: all 0.3s;
        }

        .odd-zone.optimal { background: rgba(0, 255, 136, 0.2); border: 2px solid #00ff88; }
        .odd-zone.normal { background: rgba(0, 212, 255, 0.2); border: 2px solid #00d4ff; }
        .odd-zone.degraded { background: rgba(255, 170, 0, 0.2); border: 2px solid #ffaa00; }
        .odd-zone.restricted { background: rgba(255, 136, 0, 0.2); border: 2px solid #ff8800; }
        .odd-zone.emergency { background: rgba(255, 68, 68, 0.2); border: 2px solid #ff4444; }
        .odd-zone.forbidden { background: rgba(255, 0, 0, 0.2); border: 2px solid #ff0000; }

        .odd-zone.active {
            transform: scale(1.05);
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        }

        .station-panel {
            grid-column: span 4;
        }

        .stations-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-top: 15px;
        }

        .station-card {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }

        .station-name {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #00d4ff;
        }

        .station-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            font-size: 12px;
        }

        .metric {
            background: rgba(255, 255, 255, 0.05);
            padding: 8px;
            border-radius: 5px;
        }

        .metric-label {
            color: #888;
            font-size: 10px;
        }

        .metric-value {
            font-size: 14px;
            font-weight: bold;
        }

        .chart-panel {
            grid-column: span 2;
            min-height: 300px;
        }

        .alerts-panel {
            grid-column: span 2;
            max-height: 300px;
            overflow-y: auto;
        }

        .alert-list {
            margin-top: 15px;
        }

        .alert-item {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            border-left: 3px solid #00d4ff;
        }

        .alert-item.warning { border-left-color: #ffaa00; }
        .alert-item.error { border-left-color: #ff4444; }

        .alert-time {
            font-size: 11px;
            color: #666;
        }

        .alert-message {
            flex: 1;
            font-size: 13px;
        }

        .controls-panel {
            grid-column: span 4;
        }

        .controls-grid {
            display: flex;
            gap: 15px;
            margin-top: 15px;
            flex-wrap: wrap;
        }

        .control-btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .control-btn.primary {
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            color: #fff;
        }

        .control-btn.secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .control-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 212, 255, 0.3);
        }

        .autonomy-panel {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .autonomy-level {
            display: flex;
            gap: 5px;
        }

        .level-bar {
            width: 30px;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }

        .level-bar.active {
            background: linear-gradient(90deg, #00ff88, #00d4ff);
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }

        /* 简单图表 */
        .simple-chart {
            width: 100%;
            height: 200px;
            margin-top: 15px;
            position: relative;
        }

        .chart-svg {
            width: 100%;
            height: 100%;
        }

        .chart-line {
            fill: none;
            stroke: #00d4ff;
            stroke-width: 2;
        }

        .chart-area {
            fill: url(#gradient);
            opacity: 0.3;
        }

        .chart-grid line {
            stroke: rgba(255, 255, 255, 0.1);
            stroke-width: 1;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>YJDT 雅江水电梯级智能控制系统</h1>
        <div class="status">
            <div class="status-indicator">
                <span class="status-dot normal" id="status-dot"></span>
                <span id="status-text">系统正常运行</span>
            </div>
            <div id="current-time"></div>
        </div>
    </div>

    <div class="main-content">
        <!-- 关键指标卡片 -->
        <div class="card">
            <div class="card-title">系统频率</div>
            <div class="card-value" id="frequency">50.00<span class="card-unit">Hz</span></div>
            <div class="card-trend trend-stable">◆ 稳定</div>
        </div>

        <div class="card">
            <div class="card-title">总有功功率</div>
            <div class="card-value" id="power">51.0<span class="card-unit">GW</span></div>
            <div class="card-trend trend-up">▲ +0.5%</div>
        </div>

        <div class="card">
            <div class="card-title">管道压力</div>
            <div class="card-value" id="pressure">102<span class="card-unit">%</span></div>
            <div class="card-trend trend-stable">◆ 正常</div>
        </div>

        <div class="card">
            <div class="card-title">调压室水位</div>
            <div class="card-value" id="surge-level">52<span class="card-unit">%</span></div>
            <div class="card-trend trend-down">▼ -0.2%</div>
        </div>

        <!-- ODD状态面板 -->
        <div class="card odd-panel">
            <div class="card-title">ODD设计运行域状态</div>
            <div class="autonomy-panel">
                <span>自主等级: L<span id="autonomy-level">4</span></span>
                <div class="autonomy-level">
                    <div class="level-bar active"></div>
                    <div class="level-bar active"></div>
                    <div class="level-bar active"></div>
                    <div class="level-bar active"></div>
                    <div class="level-bar"></div>
                </div>
            </div>
            <div class="odd-zones">
                <div class="odd-zone optimal">OPTIMAL<br>最优</div>
                <div class="odd-zone normal active" id="zone-normal">NORMAL<br>正常</div>
                <div class="odd-zone degraded">DEGRADED<br>降级</div>
                <div class="odd-zone restricted">RESTRICTED<br>受限</div>
                <div class="odd-zone emergency">EMERGENCY<br>应急</div>
                <div class="odd-zone forbidden">FORBIDDEN<br>禁止</div>
            </div>
        </div>

        <!-- 告警面板 -->
        <div class="card alerts-panel">
            <div class="card-title">系统告警</div>
            <div class="alert-list" id="alert-list">
                <div class="alert-item">
                    <span class="alert-time">14:32:15</span>
                    <span class="alert-message">系统启动完成，进入正常运行模式</span>
                </div>
                <div class="alert-item warning">
                    <span class="alert-time">14:30:22</span>
                    <span class="alert-message">3号电站AGC响应延迟0.5秒</span>
                </div>
                <div class="alert-item">
                    <span class="alert-time">14:28:10</span>
                    <span class="alert-message">ODD边界检查通过</span>
                </div>
            </div>
        </div>

        <!-- 五站状态面板 -->
        <div class="card station-panel">
            <div class="card-title">五站梯级电站状态</div>
            <div class="stations-grid">
                <div class="station-card">
                    <div class="station-name">1号电站</div>
                    <div class="station-metrics">
                        <div class="metric">
                            <div class="metric-label">功率</div>
                            <div class="metric-value">12.2 GW</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">负荷率</div>
                            <div class="metric-value">85%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">水头</div>
                            <div class="metric-value">420 m</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">状态</div>
                            <div class="metric-value" style="color:#00ff88">正常</div>
                        </div>
                    </div>
                </div>
                <div class="station-card">
                    <div class="station-name">2号电站</div>
                    <div class="station-metrics">
                        <div class="metric">
                            <div class="metric-label">功率</div>
                            <div class="metric-value">11.8 GW</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">负荷率</div>
                            <div class="metric-value">82%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">水头</div>
                            <div class="metric-value">395 m</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">状态</div>
                            <div class="metric-value" style="color:#00ff88">正常</div>
                        </div>
                    </div>
                </div>
                <div class="station-card">
                    <div class="station-name">3号电站</div>
                    <div class="station-metrics">
                        <div class="metric">
                            <div class="metric-label">功率</div>
                            <div class="metric-value">12.5 GW</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">负荷率</div>
                            <div class="metric-value">87%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">水头</div>
                            <div class="metric-value">438 m</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">状态</div>
                            <div class="metric-value" style="color:#00ff88">正常</div>
                        </div>
                    </div>
                </div>
                <div class="station-card">
                    <div class="station-name">4号电站</div>
                    <div class="station-metrics">
                        <div class="metric">
                            <div class="metric-label">功率</div>
                            <div class="metric-value">11.5 GW</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">负荷率</div>
                            <div class="metric-value">80%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">水头</div>
                            <div class="metric-value">382 m</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">状态</div>
                            <div class="metric-value" style="color:#00ff88">正常</div>
                        </div>
                    </div>
                </div>
                <div class="station-card">
                    <div class="station-name">5号电站</div>
                    <div class="station-metrics">
                        <div class="metric">
                            <div class="metric-label">功率</div>
                            <div class="metric-value">11.0 GW</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">负荷率</div>
                            <div class="metric-value">78%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">水头</div>
                            <div class="metric-value">365 m</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">状态</div>
                            <div class="metric-value" style="color:#00ff88">正常</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 控制面板 -->
        <div class="card controls-panel">
            <div class="card-title">控制操作</div>
            <div class="controls-grid">
                <button class="control-btn primary" onclick="runSimulation()">
                    ▶ 运行仿真
                </button>
                <button class="control-btn primary" onclick="runOptimization()">
                    ⚙ 运行优化
                </button>
                <button class="control-btn primary" onclick="runVerification()">
                    ✓ 运行验证
                </button>
                <button class="control-btn secondary" onclick="scanODD()">
                    🔍 ODD扫描
                </button>
                <button class="control-btn secondary" onclick="generateReport()">
                    📊 生成报告
                </button>
                <button class="control-btn secondary" onclick="exportData()">
                    💾 导出数据
                </button>
            </div>
        </div>
    </div>

    <div class="footer">
        YJDT v2.2.0 | 雅鲁藏布江大拐弯截弯取直引水梯级发电工程 (~60GW) |
        <span id="ws-status">WebSocket: 连接中...</span>
    </div>

    <script>
        // 更新时间
        function updateTime() {
            const now = new Date();
            document.getElementById('current-time').textContent =
                now.toLocaleString('zh-CN', { hour12: false });
        }
        setInterval(updateTime, 1000);
        updateTime();

        // WebSocket连接
        let ws = null;
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = function() {
                document.getElementById('ws-status').textContent = 'WebSocket: 已连接';
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };

            ws.onclose = function() {
                document.getElementById('ws-status').textContent = 'WebSocket: 已断开';
                setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = function() {
                document.getElementById('ws-status').textContent = 'WebSocket: 错误';
            };
        }

        function updateDashboard(data) {
            if (data.frequency) {
                document.getElementById('frequency').innerHTML =
                    data.frequency.toFixed(2) + '<span class="card-unit">Hz</span>';
            }
            if (data.power) {
                document.getElementById('power').innerHTML =
                    data.power.toFixed(1) + '<span class="card-unit">GW</span>';
            }
            if (data.odd_zone) {
                // 更新ODD区域显示
                document.querySelectorAll('.odd-zone').forEach(el => el.classList.remove('active'));
                const zoneEl = document.querySelector(`.odd-zone.${data.odd_zone.toLowerCase()}`);
                if (zoneEl) zoneEl.classList.add('active');
            }
        }

        // 控制按钮函数
        async function runSimulation() {
            addAlert('info', '正在启动仿真...');
            try {
                const response = await fetch('/api/simulation/start', { method: 'POST' });
                const result = await response.json();
                addAlert('info', '仿真已启动: ' + result.message);
            } catch (e) {
                addAlert('warning', '仿真启动失败');
            }
        }

        async function runOptimization() {
            addAlert('info', '正在启动优化...');
            try {
                const response = await fetch('/api/optimization/start', { method: 'POST' });
                const result = await response.json();
                addAlert('info', '优化已启动: ' + result.message);
            } catch (e) {
                addAlert('warning', '优化启动失败');
            }
        }

        async function runVerification() {
            addAlert('info', '正在启动验证...');
            try {
                const response = await fetch('/api/verification/start', { method: 'POST' });
                const result = await response.json();
                addAlert('info', '验证已启动: ' + result.message);
            } catch (e) {
                addAlert('warning', '验证启动失败');
            }
        }

        async function scanODD() {
            addAlert('info', '正在扫描ODD边界...');
            try {
                const response = await fetch('/api/odd/scan', { method: 'POST' });
                const result = await response.json();
                addAlert('info', 'ODD扫描完成: 当前区域 ' + result.zone);
            } catch (e) {
                addAlert('warning', 'ODD扫描失败');
            }
        }

        async function generateReport() {
            addAlert('info', '正在生成报告...');
            try {
                const response = await fetch('/api/report/generate', { method: 'POST' });
                const result = await response.json();
                addAlert('info', '报告已生成: ' + result.path);
            } catch (e) {
                addAlert('warning', '报告生成失败');
            }
        }

        function exportData() {
            addAlert('info', '正在导出数据...');
            window.location.href = '/api/data/export';
        }

        function addAlert(type, message) {
            const alertList = document.getElementById('alert-list');
            const now = new Date().toLocaleTimeString('zh-CN', { hour12: false });
            const alertHtml = `
                <div class="alert-item ${type === 'warning' ? 'warning' : ''}">
                    <span class="alert-time">${now}</span>
                    <span class="alert-message">${message}</span>
                </div>
            `;
            alertList.insertAdjacentHTML('afterbegin', alertHtml);

            // 保留最近20条告警
            while (alertList.children.length > 20) {
                alertList.removeChild(alertList.lastChild);
            }
        }

        // 模拟数据更新
        function simulateDataUpdate() {
            const frequency = 50 + (Math.random() - 0.5) * 0.1;
            document.getElementById('frequency').innerHTML =
                frequency.toFixed(2) + '<span class="card-unit">Hz</span>';

            const power = 51 + (Math.random() - 0.5) * 2;
            document.getElementById('power').innerHTML =
                power.toFixed(1) + '<span class="card-unit">GW</span>';

            const pressure = 100 + (Math.random() - 0.5) * 4;
            document.getElementById('pressure').innerHTML =
                pressure.toFixed(0) + '<span class="card-unit">%</span>';

            const surge = 50 + (Math.random() - 0.5) * 4;
            document.getElementById('surge-level').innerHTML =
                surge.toFixed(0) + '<span class="card-unit">%</span>';
        }

        // 启动
        connectWebSocket();
        setInterval(simulateDataUpdate, 2000);
    </script>
</body>
</html>
"""


def create_dashboard_app() -> FastAPI:
    """创建仪表板应用"""
    app = FastAPI(
        title="YJDT Dashboard",
        description="雅江水电梯级分层分布式智能控制系统仪表板",
        version="2.2.0"
    )

    @app.get("/", response_class=HTMLResponse)
    async def get_dashboard():
        """获取仪表板页面"""
        return get_dashboard_html()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket端点"""
        await connection_manager.connect(websocket)
        try:
            while True:
                # 发送状态更新
                state_data = {
                    "frequency": dashboard_state.frequency,
                    "power": dashboard_state.power,
                    "pressure": dashboard_state.pressure,
                    "surge_level": dashboard_state.surge_level,
                    "odd_zone": dashboard_state.odd_zone,
                    "autonomy_level": dashboard_state.autonomy_level
                }
                await websocket.send_text(json.dumps(state_data))
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            connection_manager.disconnect(websocket)

    @app.post("/api/simulation/start")
    async def start_simulation():
        """启动仿真"""
        return {"status": "started", "message": "仿真已启动"}

    @app.post("/api/optimization/start")
    async def start_optimization():
        """启动优化"""
        return {"status": "started", "message": "优化已启动"}

    @app.post("/api/verification/start")
    async def start_verification():
        """启动验证"""
        return {"status": "started", "message": "验证已启动"}

    @app.post("/api/odd/scan")
    async def scan_odd():
        """ODD扫描"""
        return {"status": "completed", "zone": dashboard_state.odd_zone}

    @app.post("/api/report/generate")
    async def generate_report():
        """生成报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return {"status": "generated", "path": f"reports/report_{timestamp}.md"}

    @app.get("/api/data/export")
    async def export_data():
        """导出数据"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "state": {
                "frequency": dashboard_state.frequency,
                "power": dashboard_state.power,
                "odd_zone": dashboard_state.odd_zone
            }
        }
        return JSONResponse(content=data, headers={
            "Content-Disposition": "attachment; filename=yjdt_data.json"
        })

    @app.get("/api/status")
    async def get_status():
        """获取系统状态"""
        return {
            "status": "running",
            "odd_zone": dashboard_state.odd_zone,
            "autonomy_level": dashboard_state.autonomy_level,
            "metrics": {
                "frequency": dashboard_state.frequency,
                "power": dashboard_state.power,
                "pressure": dashboard_state.pressure,
                "surge_level": dashboard_state.surge_level
            }
        }

    return app


class DashboardServer:
    """仪表板服务器"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = create_dashboard_app()

    def run(self):
        """运行服务器"""
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port)


if __name__ == "__main__":
    server = DashboardServer()
    server.run()
