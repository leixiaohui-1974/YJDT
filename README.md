# 雅江水电梯级分层分布式智能系统 (YJDT)

**Yajiang Hydropower Cascade Hierarchical Distributed Intelligent System**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 概述 / Overview

YJDT是面向雅鲁藏布江水电开发的智能控制系统仿真平台，对标无人驾驶汽车L0-L5开发模式，提供从设计优化到运行测试的全流程支持。

YJDT is an intelligent control system simulation platform for the Yarlung Tsangpo River hydropower development, benchmarking the L0-L5 autonomous vehicle development approach, providing full-process support from design optimization to operational testing.

## 核心特性 / Key Features

### 🌊 全要素仿真模型 / Full-Element Simulation Models
- **水力系统**: 特征线法(MOC)水锤计算、调压室仿真
- **水轮机**: 混流式(Francis)、冲击式(Pelton)完整特性
- **发电机**: 六阶同步发电机电磁暂态模型
- **调速器**: PID/MPC/自适应多种控制策略

### 📡 传感器与执行器仿真 / Sensor & Actuator Simulation
- 压力、流量、水位、转速、功率、温度、振动等传感器
- 导叶、阀门、励磁、断路器等执行器
- 完整的故障注入功能（偏置、漂移、卡死、噪声等）

### 🎛️ 分层分布式控制 / Hierarchical Distributed Control
| 层级 | 周期 | 功能 |
|------|------|------|
| 梯级级 | 60s | 水库调度、梯级协调 |
| 厂站级 | 1s | 负荷分配、经济调度 |
| 机组级 | 100ms | MPC优化、约束处理 |
| 现场级 | 20ms | PID执行、闭环控制 |

### 🎬 全场景生成与识别 / Full Scenario Generation & Recognition
- **场景生成**: 正常运行、甩负荷、启停机、故障、极端工况、组合场景
- **场景识别**: 基于AI的实时场景识别与异常检测
- **场景库**: 标准场景库管理与扩展，157+标准场景，500+极端场景
- **100%覆盖**: 7级概率等级（常态→年级→偶发→罕见→极罕见→万年一遇→超设计基准）
- **极端场景**: 超设计地震(XI度)、PMF洪水、巨型滑坡、网络攻击等

### 🛡️ 核电站级安全分析 / Nuclear-Grade Safety Analysis
- **概率安全分析(PSA)**: 故障树(FTA)、事件树(ETA)、共因失效(CCF)分析
- **重要度分析**: Fussell-Vesely、Birnbaum、RAW、RRW四大指标
- **MOCUS算法**: 自动识别最小割集，量化系统失效概率
- **智能故障诊断**: 信号处理、故障特征识别、根因分析
- **预测性维护**: RUL(剩余使用寿命)预测、健康评估
- **应急响应**: I-IV级应急预案库、行动协调、恢复规划

### 🧪 软件在环测试 (SIL) / Software-in-the-Loop Testing
- 自动化测试用例执行
- 验收标准自动评估
- 多方案对比分析
- 测试报告自动生成

### 📊 设计优化 / Design Optimization
- 多方案对比评估
- 传感器布设优化（可观测性/可诊断性分析）
- 设备选型优化（总拥有成本TCO分析）
- 全生命周期效益分析（NPV/IRR/LCOE）

### 🖥️ 可视化界面 / Visualization GUI
- Streamlit交互式界面
- 实时仿真监控
- 参数配置与调整
- 结果分析与导出

## 安装 / Installation

```bash
# 克隆仓库
git clone https://github.com/your-org/YJDT.git
cd YJDT

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

## 快速开始 / Quick Start

### 命令行使用

```bash
# 显示帮助
python -m yjdt help

# 启动可视化界面
python -m yjdt gui

# 运行基础仿真
python -m yjdt simulate

# 运行方案对比
python -m yjdt compare

# 运行全场景测试
python -m yjdt scenario
```

### Python API使用

```python
# 创建水轮机模型
from yjdt.core.turbine import FrancisTurbine

turbine = FrancisTurbine(
    rated_power=1000.0,    # MW
    rated_head=480.0,      # m
    rated_speed=100.0,     # rpm
    rated_flow=230.0       # m³/s
)

# 计算工况点
power, efficiency = turbine.calculate_output(
    head=480.0,
    guide_vane_opening=0.8,
    speed=100.0
)

print(f"功率: {power:.2f} MW, 效率: {efficiency*100:.2f}%")
```

## 项目结构 / Project Structure

```
YJDT/
├── src/yjdt/
│   ├── core/                 # 核心仿真模型
│   │   ├── hydraulic.py      # 水力系统 (MOC)
│   │   ├── turbine.py        # 水轮机模型
│   │   ├── generator.py      # 发电机模型
│   │   └── governor.py       # 调速器模型
│   ├── sensors/              # 传感器与执行器
│   │   ├── sensors.py        # 传感器仿真
│   │   └── actuators.py      # 执行器仿真
│   ├── control/              # 控制系统
│   │   ├── distributed.py    # 分层分布式控制
│   │   └── coordination.py   # 协调控制
│   ├── scenarios/            # 场景系统
│   │   ├── generator.py      # 场景生成
│   │   ├── recognizer.py     # 场景识别
│   │   ├── extreme_scenarios.py  # 极端场景生成(500+)
│   │   ├── coverage_analyzer.py  # 覆盖率分析
│   │   └── scenario_library.yaml # 场景库配置(157+)
│   ├── safety/               # 安全分析模块
│   │   ├── psa_analysis.py   # PSA/FTA/ETA分析
│   │   ├── intelligent_diagnosis.py  # 智能诊断
│   │   └── emergency_response.py     # 应急响应
│   ├── optimization/         # 优化模块
│   │   ├── design_optimizer.py   # 设计优化
│   │   ├── sensor_placement.py   # 传感器布设
│   │   ├── equipment_selection.py # 设备选型
│   │   ├── lifecycle.py          # 生命周期
│   │   └── controller_tuning.py  # 控制器整定
│   ├── simulation/           # 仿真引擎
│   │   ├── engine.py         # 仿真引擎
│   │   └── sil_testing.py    # SIL测试
│   ├── gui/                  # 可视化界面
│   │   └── app.py            # Streamlit应用
│   └── config/               # 配置文件
│       └── yajiang_params.yaml
├── examples/                 # 示例程序
│   ├── basic_simulation.py   # 基础仿真
│   ├── scheme_comparison.py  # 方案对比
│   ├── distributed_control.py # 分布式控制
│   └── scenario_testing.py   # 场景测试
├── tests/                    # 测试用例
├── pyproject.toml           # 项目配置
└── README.md                # 说明文档
```

## 设计方案 / Design Schemes

### 方案一：多级开发（现实方案）
- 分3-4个梯级开发
- 混流式水轮机，单机1000MW
- 额定水头480m，隧洞25km
- 水流惯性时间Tw=12s
- 设计等级：L2

### 方案二：单级极限开发
- 一次性全落差开发
- 冲击式水轮机（Pelton），单机500MW
- 额定水头2100m（世界最高），隧洞45km
- 水流惯性时间Tw≈25s（极端）
- 设计等级：L0

### 方案三：混合开发
- 上级：冲击式，水头1200m
- 下级：混流式，水头600m
- 平衡风险与效益
- 设计等级：L1

## 对标无人驾驶L0-L5 / Benchmarking Autonomous Vehicle L0-L5

| 等级 | 无人驾驶 | 智能水电站 |
|------|----------|------------|
| L0 | 无自动化 | 手动控制 |
| L1 | 驾驶辅助 | 单回路自动 |
| L2 | 部分自动 | 多回路协调 |
| L3 | 条件自动 | 智能诊断 |
| L4 | 高度自动 | 自主决策 |
| L5 | 完全自动 | 完全自主 |

## 安全设计原则 / Safety Design Principles

### 核电站级安全标准
- **深度防御**: 多层保护屏障，单一故障不导致系统失效
- **固有安全**: 依靠自然规律实现安全，无需外部干预
- **无悬崖效应**: 超设计基准事故不会导致灾难性后果
- **多样性冗余**: 不同原理、不同厂家的冗余设计

### 场景覆盖等级 / Scenario Coverage Levels

| 概率等级 | 年发生概率 | 典型场景 | 安全要求 |
|----------|------------|----------|----------|
| 常态 | 1.0 | 正常运行 | 高效稳定 |
| 年级 | 10⁻¹ | 负荷波动 | 自动调节 |
| 偶发 | 10⁻² | 设备故障 | 安全保护 |
| 罕见 | 10⁻³ | 甩满负荷 | 应急处置 |
| 极罕见 | 10⁻⁴ | 多重故障 | 深度防御 |
| 万年一遇 | 10⁻⁵ | 极端地震 | 确保安全 |
| 超设计基准 | <10⁻⁶ | 叠加灾害 | 无悬崖效应 |

## 贡献 / Contributing

欢迎贡献代码、报告问题或提出建议。

## 许可证 / License

MIT License

## 联系 / Contact

- 项目主页: https://github.com/your-org/YJDT
- 技术支持: support@yjdt.example.com
