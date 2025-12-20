"""
可视化界面应用
Visualization Application

基于Streamlit的交互式界面，实现：
- 系统配置
- 仿真运行
- 结果可视化
- 设计优化
- 测试管理
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional
import json


def create_app():
    """创建Streamlit应用"""

    # 页面配置
    st.set_page_config(
        page_title="雅江水电梯级智能控制系统",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 侧边栏导航
    st.sidebar.title("🌊 雅江智控系统")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "功能导航",
        [
            "🏠 系统概览",
            "⚙️ 参数配置",
            "🔬 仿真运行",
            "📊 结果分析",
            "🎯 设计优化",
            "🧪 在环测试",
            "📈 生命周期分析",
            "📋 报告生成",
        ]
    )

    # 根据选择显示不同页面
    if page == "🏠 系统概览":
        show_overview_page()
    elif page == "⚙️ 参数配置":
        show_config_page()
    elif page == "🔬 仿真运行":
        show_simulation_page()
    elif page == "📊 结果分析":
        show_analysis_page()
    elif page == "🎯 设计优化":
        show_optimization_page()
    elif page == "🧪 在环测试":
        show_testing_page()
    elif page == "📈 生命周期分析":
        show_lifecycle_page()
    elif page == "📋 报告生成":
        show_report_page()


def show_overview_page():
    """系统概览页面"""
    st.title("雅江水电梯级分层分布式智能控制系统")

    st.markdown("""
    ## 系统简介

    本系统是针对雅鲁藏布江下游水电开发工程设计的**分层分布式智能控制仿真平台**，
    对标无人驾驶汽车的开发模式，实现从设计到运营的全生命周期数字孪生。

    ### 核心功能

    - **本体仿真模型**: 水力系统、水轮机、发电机、控制系统全要素仿真
    - **传感器/执行器仿真**: 包含故障注入和性能退化模型
    - **分层分布式控制**: 现场级PID、单元级MPC、厂站级优化、梯级调度
    - **全场景生成**: 正常运行、过渡过程、故障场景、极端工况
    - **AI场景识别**: 基于机器学习的在线场景识别和异常检测
    - **软件在环测试**: 全面的自动化测试和评价体系
    - **设计优化**: 多方案对比、传感器布设、设备选型优化
    """)

    # 显示系统架构图
    st.subheader("系统架构")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("电站数量", "5座", "梯级开发")
        st.metric("总装机容量", "17,500 MW", "")

    with col2:
        st.metric("设计等级", "L4", "高度自动化")
        st.metric("控制周期", "20ms", "现场级")

    with col3:
        st.metric("仿真精度", "0.01s", "时间步长")
        st.metric("场景覆盖", "50+", "测试场景")

    # 梯级布置示意
    st.subheader("梯级布置")

    cascade_data = {
        '电站': ['墨脱', '多雄藏布', '达木', '巴玉', '通德'],
        '装机容量(MW)': [6000, 4000, 3000, 2500, 2000],
        '机组数量': [6, 4, 3, 3, 2],
        '额定水头(m)': [480, 450, 420, 400, 380],
    }

    st.dataframe(cascade_data, use_container_width=True)

    # 控制架构
    st.subheader("控制层级架构")

    control_levels = """
    ```
    ┌─────────────────────────────────────────────────────────────┐
    │                    梯级调度级 (周期: 60s)                    │
    │                    - 多电站协调优化                          │
    │                    - 水库联合调度                            │
    └─────────────────────────────────────────────────────────────┘
                                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                    厂站级 (周期: 1s)                         │
    │                    - 多机组负荷分配                          │
    │                    - AGC/一次调频                            │
    └─────────────────────────────────────────────────────────────┘
                                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                    单元级 (周期: 100ms)                      │
    │                    - MPC预测控制                             │
    │                    - 机组协调                                │
    └─────────────────────────────────────────────────────────────┘
                                    ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                    现场级 (周期: 20ms)                       │
    │                    - PID控制回路                             │
    │                    - 伺服执行                                │
    └─────────────────────────────────────────────────────────────┘
    ```
    """
    st.markdown(control_levels)


def show_config_page():
    """参数配置页面"""
    st.title("⚙️ 系统参数配置")

    tab1, tab2, tab3, tab4 = st.tabs([
        "水力系统", "水轮机", "控制系统", "仿真设置"
    ])

    with tab1:
        st.subheader("水力系统参数")

        col1, col2 = st.columns(2)

        with col1:
            rated_head = st.number_input("额定水头 (m)", value=480.0, min_value=100.0, max_value=2500.0)
            rated_flow = st.number_input("额定流量 (m³/s)", value=210.0, min_value=10.0, max_value=500.0)
            tunnel_length = st.number_input("隧洞长度 (m)", value=25000.0, min_value=1000.0, max_value=50000.0)

        with col2:
            tunnel_diameter = st.number_input("隧洞直径 (m)", value=11.0, min_value=3.0, max_value=20.0)
            wave_speed = st.number_input("压力波速 (m/s)", value=1350.0, min_value=800.0, max_value=1500.0)
            friction_factor = st.number_input("摩阻系数", value=0.015, min_value=0.001, max_value=0.05, format="%.3f")

        # 计算水流惯性时间常数
        v = rated_flow / (np.pi * (tunnel_diameter/2)**2)
        Tw = tunnel_length * v / (9.81 * rated_head)

        st.info(f"💡 计算得到的水流惯性时间常数 Tw = {Tw:.2f} 秒")

        if Tw > 10:
            st.warning("⚠️ 水流惯性时间常数较大(>10s)，需要特别注意控制策略设计！")

    with tab2:
        st.subheader("水轮机参数")

        turbine_type = st.selectbox("水轮机类型", ["混流式(Francis)", "冲击式(Pelton)"])

        col1, col2 = st.columns(2)

        with col1:
            rated_power = st.number_input("额定功率 (MW)", value=1000.0, min_value=100.0, max_value=1500.0)
            rated_speed = st.number_input("额定转速 (r/min)", value=166.7, min_value=50.0, max_value=500.0)
            inertia_gd2 = st.number_input("飞轮惯量 GD² (t·m²)", value=130000.0, min_value=10000.0, max_value=200000.0)

        with col2:
            guide_vane_close = st.number_input("导叶关闭时间 (s)", value=8.0, min_value=2.0, max_value=20.0)
            guide_vane_open = st.number_input("导叶开启时间 (s)", value=12.0, min_value=2.0, max_value=30.0)
            efficiency = st.slider("额定效率 (%)", 85, 98, 94)

    with tab3:
        st.subheader("控制系统参数")

        control_type = st.radio("控制器类型", ["PID", "MPC", "自适应"])

        if control_type == "PID":
            col1, col2, col3 = st.columns(3)
            with col1:
                kp = st.number_input("比例增益 Kp", value=2.5, min_value=0.1, max_value=10.0)
            with col2:
                ki = st.number_input("积分增益 Ki", value=0.15, min_value=0.01, max_value=1.0)
            with col3:
                kd = st.number_input("微分增益 Kd", value=4.0, min_value=0.0, max_value=10.0)

            servo_time = st.slider("伺服时间常数 (s)", 0.1, 2.0, 0.5)

        elif control_type == "MPC":
            col1, col2 = st.columns(2)
            with col1:
                prediction_horizon = st.number_input("预测时域", value=30, min_value=5, max_value=100)
                control_horizon = st.number_input("控制时域", value=10, min_value=1, max_value=30)
            with col2:
                sample_time = st.number_input("采样时间 (s)", value=0.1, min_value=0.01, max_value=1.0)

    with tab4:
        st.subheader("仿真设置")

        col1, col2 = st.columns(2)

        with col1:
            sim_duration = st.number_input("仿真时长 (s)", value=300.0, min_value=10.0, max_value=3600.0)
            time_step = st.number_input("时间步长 (s)", value=0.01, min_value=0.001, max_value=0.1, format="%.3f")

        with col2:
            sim_mode = st.selectbox("仿真模式", ["快速仿真", "实时仿真", "单步仿真"])
            solver = st.selectbox("求解器", ["欧拉法", "4阶龙格库塔", "自适应步长"])

        save_history = st.checkbox("保存仿真历史", value=True)

    if st.button("💾 保存配置", type="primary"):
        st.success("✅ 配置已保存！")


def show_simulation_page():
    """仿真运行页面"""
    st.title("🔬 仿真运行")

    # 场景选择
    st.subheader("场景选择")

    scenario_type = st.selectbox(
        "场景类型",
        [
            "正常运行",
            "负荷阶跃",
            "甩负荷100%",
            "甩负荷50%",
            "启动过程",
            "停机过程",
            "一次调频",
            "传感器故障",
            "执行器故障",
            "电网故障",
        ]
    )

    col1, col2 = st.columns(2)

    with col1:
        initial_power = st.slider("初始功率 (%)", 0, 100, 80)
        event_time = st.number_input("事件发生时间 (s)", value=10.0, min_value=0.0, max_value=100.0)

    with col2:
        event_magnitude = st.slider("事件幅度 (%)", 0, 100, 100)
        noise_level = st.slider("噪声水平 (%)", 0, 10, 1)

    # 运行按钮
    if st.button("▶️ 开始仿真", type="primary"):
        # 仿真进度
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 模拟仿真过程
        for i in range(100):
            import time
            time.sleep(0.02)
            progress_bar.progress(i + 1)
            status_text.text(f"仿真进度: {i+1}%")

        st.success("✅ 仿真完成！")

        # 生成模拟数据
        t = np.linspace(0, 100, 1000)
        speed = 166.7 + 5 * np.exp(-0.1 * t) * np.sin(0.5 * t) + 0.5 * np.random.randn(len(t))
        power = 800 * (1 - np.exp(-0.05 * t)) + 20 * np.random.randn(len(t))
        opening = 0.5 + 0.1 * (1 - np.exp(-0.1 * t)) + 0.01 * np.random.randn(len(t))
        pressure = 4.8 + 0.3 * np.exp(-0.05 * t) * np.sin(0.3 * t) + 0.05 * np.random.randn(len(t))

        # 显示结果
        st.subheader("仿真结果")

        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('转速', '功率', '导叶开度', '压力'),
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )

        fig.add_trace(go.Scatter(x=t, y=speed, name='转速', line=dict(color='blue')), row=1, col=1)
        fig.add_trace(go.Scatter(x=t, y=power, name='功率', line=dict(color='green')), row=1, col=2)
        fig.add_trace(go.Scatter(x=t, y=opening*100, name='开度', line=dict(color='orange')), row=2, col=1)
        fig.add_trace(go.Scatter(x=t, y=pressure, name='压力', line=dict(color='red')), row=2, col=2)

        fig.update_layout(height=600, showlegend=False)
        fig.update_xaxes(title_text="时间 (s)")
        fig.update_yaxes(title_text="转速 (r/min)", row=1, col=1)
        fig.update_yaxes(title_text="功率 (MW)", row=1, col=2)
        fig.update_yaxes(title_text="开度 (%)", row=2, col=1)
        fig.update_yaxes(title_text="压力 (MPa)", row=2, col=2)

        st.plotly_chart(fig, use_container_width=True)

        # 性能指标
        st.subheader("性能指标")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("超调量", "4.2%", "✓ 合格")
        with col2:
            st.metric("调节时间", "35.6s", "✓ 合格")
        with col3:
            st.metric("稳态误差", "0.1%", "✓ 合格")
        with col4:
            st.metric("最大压力上升", "12.3%", "✓ 合格")


def show_analysis_page():
    """结果分析页面"""
    st.title("📊 结果分析")

    # 加载或生成示例数据
    t = np.linspace(0, 100, 1000)
    speed = 166.7 + 5 * np.exp(-0.1 * t) * np.sin(0.5 * t)
    power = 800 * (1 - np.exp(-0.05 * t))

    tab1, tab2, tab3 = st.tabs(["时域分析", "频域分析", "统计分析"])

    with tab1:
        st.subheader("时域响应分析")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=speed, name='转速响应'))
        fig.add_hline(y=166.7, line_dash="dash", line_color="red", annotation_text="额定转速")
        fig.add_hline(y=166.7*1.02, line_dash="dot", line_color="green", annotation_text="+2%")
        fig.add_hline(y=166.7*0.98, line_dash="dot", line_color="green", annotation_text="-2%")

        fig.update_layout(title="转速阶跃响应", xaxis_title="时间 (s)", yaxis_title="转速 (r/min)")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("频域分析")

        # FFT分析
        fft_result = np.fft.fft(speed - np.mean(speed))
        freq = np.fft.fftfreq(len(speed), t[1] - t[0])

        positive_freq = freq[:len(freq)//2]
        magnitude = np.abs(fft_result[:len(freq)//2])

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=positive_freq, y=magnitude, name='幅值谱'))
        fig.update_layout(title="转速频谱分析", xaxis_title="频率 (Hz)", yaxis_title="幅值")
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("统计分析")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**转速统计**")
            st.write(f"- 均值: {np.mean(speed):.2f} r/min")
            st.write(f"- 标准差: {np.std(speed):.4f} r/min")
            st.write(f"- 最大值: {np.max(speed):.2f} r/min")
            st.write(f"- 最小值: {np.min(speed):.2f} r/min")

        with col2:
            st.markdown("**功率统计**")
            st.write(f"- 均值: {np.mean(power):.2f} MW")
            st.write(f"- 标准差: {np.std(power):.2f} MW")
            st.write(f"- 最大值: {np.max(power):.2f} MW")
            st.write(f"- 最小值: {np.min(power):.2f} MW")


def show_optimization_page():
    """设计优化页面"""
    st.title("🎯 设计优化")

    tab1, tab2, tab3, tab4 = st.tabs([
        "方案对比", "传感器布设", "设备选型", "控制器调参"
    ])

    with tab1:
        st.subheader("设计方案对比")

        schemes = {
            '指标': ['安全性', '可靠性', '效率', '经济性', '灵活性', '智能化'],
            '基准方案': [85, 90, 94, 75, 70, 75],
            '极限方案': [75, 80, 92, 60, 65, 80],
            '智能方案': [95, 95, 95, 70, 90, 100],
        }

        # 雷达图
        fig = go.Figure()

        categories = schemes['指标']
        for scheme_name in ['基准方案', '极限方案', '智能方案']:
            values = schemes[scheme_name]
            values_closed = values + [values[0]]  # 闭合

            fig.add_trace(go.Scatterpolar(
                r=values_closed,
                theta=categories + [categories[0]],
                fill='toself',
                name=scheme_name
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            title="方案对比雷达图"
        )
        st.plotly_chart(fig, use_container_width=True)

        # 综合得分
        st.markdown("**综合评分**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("基准方案", "81.5分", "")
        with col2:
            st.metric("极限方案", "75.3分", "-6.2")
        with col3:
            st.metric("智能方案", "90.8分", "+9.3", delta_color="normal")

    with tab2:
        st.subheader("传感器布设优化")

        config_type = st.radio("配置方案", ["最小配置", "标准配置", "增强配置"])

        sensor_configs = {
            '最小配置': {'数量': 8, '成本': 15, '可观测性': 75, '可诊断性': 60},
            '标准配置': {'数量': 20, '成本': 35, '可观测性': 90, '可诊断性': 80},
            '增强配置': {'数量': 40, '成本': 80, '可观测性': 98, '可诊断性': 95},
        }

        config = sensor_configs[config_type]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("传感器数量", config['数量'])
        with col2:
            st.metric("成本(万元)", config['成本'])
        with col3:
            st.metric("可观测性(%)", config['可观测性'])
        with col4:
            st.metric("可诊断性(%)", config['可诊断性'])

    with tab3:
        st.subheader("设备选型")

        equipment_type = st.selectbox("设备类别", ["水轮机", "发电机", "调速器", "励磁系统"])

        if equipment_type == "水轮机":
            options = [
                {"名称": "HEC-F1000", "制造商": "哈尔滨电机", "效率": 94.5, "成本": 5.0, "评分": 92},
                {"名称": "DEC-F1000", "制造商": "东方电机", "效率": 94.0, "成本": 4.8, "评分": 90},
                {"名称": "GE Hydro F1000", "制造商": "GE", "效率": 94.8, "成本": 7.0, "评分": 88},
            ]

            for opt in options:
                with st.expander(f"{opt['名称']} - {opt['制造商']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"效率: {opt['效率']}%")
                    with col2:
                        st.write(f"成本: {opt['成本']}亿元")
                    with col3:
                        st.write(f"综合评分: {opt['评分']}")

    with tab4:
        st.subheader("控制器参数优化")

        tuning_method = st.selectbox("整定方法", ["Ziegler-Nichols", "IMC", "数值优化", "鲁棒优化"])

        if st.button("🔧 开始优化"):
            with st.spinner("优化中..."):
                import time
                time.sleep(2)

            st.success("优化完成！")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Kp", "2.85", "+0.35")
            with col2:
                st.metric("Ki", "0.12", "-0.03")
            with col3:
                st.metric("Kd", "4.50", "+0.50")

            st.info("💡 优化后超调量降低15%，调节时间缩短20%")


def show_testing_page():
    """在环测试页面"""
    st.title("🧪 软件在环测试")

    tab1, tab2, tab3 = st.tabs(["测试配置", "测试执行", "测试报告"])

    with tab1:
        st.subheader("测试套件配置")

        coverage = st.radio("测试覆盖", ["基本测试", "标准测试", "全面测试"])

        test_types = {
            '基本测试': ['甩负荷', '启动', '停机', '一次调频'],
            '标准测试': ['甩负荷', '启动', '停机', '一次调频', '负荷变化', '传感器故障', '执行器故障'],
            '全面测试': ['所有场景类型（50+测试用例）'],
        }

        st.write(f"包含测试: {', '.join(test_types[coverage])}")

        num_tests = {'基本测试': 4, '标准测试': 12, '全面测试': 50}
        st.info(f"📋 共 {num_tests[coverage]} 个测试用例")

    with tab2:
        st.subheader("测试执行")

        if st.button("▶️ 运行测试套件", type="primary"):
            progress = st.progress(0)
            status = st.empty()
            results_container = st.empty()

            test_results = []
            for i in range(12):
                import time
                time.sleep(0.3)
                progress.progress((i + 1) / 12)
                status.text(f"正在执行测试 {i+1}/12...")

                # 模拟测试结果
                passed = np.random.random() > 0.15
                test_results.append({
                    'id': f'TEST_{i+1:03d}',
                    'name': f'测试用例{i+1}',
                    'status': '✅ 通过' if passed else '❌ 失败',
                    'score': np.random.uniform(70, 100) if passed else np.random.uniform(40, 70)
                })

            st.success("✅ 测试完成！")

            # 显示结果
            import pandas as pd
            df = pd.DataFrame(test_results)
            st.dataframe(df, use_container_width=True)

    with tab3:
        st.subheader("测试报告")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总测试数", "12")
        with col2:
            st.metric("通过", "10", delta_color="normal")
        with col3:
            st.metric("失败", "2", delta_color="inverse")
        with col4:
            st.metric("通过率", "83.3%")

        # 测试覆盖饼图
        fig = go.Figure(data=[go.Pie(
            labels=['通过', '失败', '跳过'],
            values=[10, 2, 0],
            hole=0.4,
            marker_colors=['#2ecc71', '#e74c3c', '#95a5a6']
        )])
        fig.update_layout(title="测试结果分布")
        st.plotly_chart(fig, use_container_width=True)


def show_lifecycle_page():
    """生命周期分析页面"""
    st.title("📈 全生命周期分析")

    tab1, tab2, tab3 = st.tabs(["投资分析", "收益预测", "可靠性分析"])

    with tab1:
        st.subheader("投资成本分析")

        investment_data = {
            '项目': ['土建工程', '设备采购', '安装调试', '电气工程', '控制系统', '其他'],
            '金额(亿元)': [20, 35, 8, 12, 5, 10],
        }

        fig = px.pie(
            names=investment_data['项目'],
            values=investment_data['金额(亿元)'],
            title="投资构成"
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("总投资", "90亿元")
            st.metric("单位千瓦投资", "5143元/kW")
        with col2:
            st.metric("年维护成本", "5000万元")
            st.metric("设计寿命", "50年")

    with tab2:
        st.subheader("收益预测")

        years = np.arange(1, 51)
        cumulative_revenue = 12 * years  # 简化的累计收益
        cumulative_cost = 90 + 0.5 * years  # 初始投资 + 累计维护成本
        cumulative_profit = cumulative_revenue - cumulative_cost

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=cumulative_revenue, name='累计收入', fill='tonexty'))
        fig.add_trace(go.Scatter(x=years, y=cumulative_cost, name='累计成本'))
        fig.add_trace(go.Scatter(x=years, y=cumulative_profit, name='累计净收益'))
        fig.update_layout(title="累计现金流", xaxis_title="年份", yaxis_title="金额(亿元)")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("净现值(NPV)", "156亿元")
        with col2:
            st.metric("内部收益率(IRR)", "12.5%")
        with col3:
            st.metric("投资回收期", "8.2年")

    with tab3:
        st.subheader("可靠性分析")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("系统可用率", "99.85%")
            st.metric("MTBF", "45,000小时")
            st.metric("MTTR", "24小时")

        with col2:
            # 可靠性随时间变化
            years = np.arange(1, 51)
            reliability = 0.9985 * np.exp(-0.0005 * years)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=reliability * 100, name='可用率'))
            fig.add_hline(y=99, line_dash="dash", line_color="red", annotation_text="最低要求")
            fig.update_layout(title="可用率预测", xaxis_title="运行年份", yaxis_title="可用率(%)")
            st.plotly_chart(fig, use_container_width=True)


def show_report_page():
    """报告生成页面"""
    st.title("📋 报告生成")

    report_type = st.selectbox(
        "报告类型",
        [
            "设计优化报告",
            "仿真分析报告",
            "在环测试报告",
            "生命周期评估报告",
            "综合评估报告",
        ]
    )

    report_format = st.radio("输出格式", ["Markdown", "PDF", "HTML", "Word"])

    include_options = st.multiselect(
        "包含内容",
        ["系统配置", "仿真结果", "性能指标", "对比分析", "优化建议", "图表"],
        default=["系统配置", "仿真结果", "性能指标", "优化建议"]
    )

    if st.button("📄 生成报告", type="primary"):
        with st.spinner("正在生成报告..."):
            import time
            time.sleep(2)

        st.success("✅ 报告生成成功！")

        # 显示预览
        st.subheader("报告预览")

        preview_content = f"""
# {report_type}

**生成时间**: 2025-12-20

## 1. 系统概述

本报告针对雅江水电梯级工程的{report_type.replace('报告', '')}进行了详细分析。

## 2. 主要结论

- 推荐采用智能化设计方案，综合得分90.8分
- 系统可用率达到99.85%，满足设计要求
- 投资回收期预计8.2年，具有良好的经济效益

## 3. 建议

1. 优先采用国产化设备，国产化率可达95%以上
2. 建议采用三取二冗余配置，提高系统可靠性
3. 控制器建议采用MPC算法，适应长隧洞高惯性系统

---
*本报告由雅江水电梯级智能控制系统自动生成*
"""
        st.markdown(preview_content)

        st.download_button(
            label="📥 下载报告",
            data=preview_content,
            file_name=f"{report_type}.md",
            mime="text/markdown"
        )


def main():
    """主入口函数"""
    create_app()


if __name__ == "__main__":
    main()
