# -*- coding: utf-8 -*-
"""
概率安全分析模块 - PSA/FTA/ETA
Probabilistic Safety Analysis Module

对标核电站安全分析方法，实现：
1. 概率安全分析 (PSA - Probabilistic Safety Analysis)
2. 故障树分析 (FTA - Fault Tree Analysis)
3. 事件树分析 (ETA - Event Tree Analysis)
4. 共因故障分析 (CCF - Common Cause Failure)
5. 重要度分析 (Importance Analysis)

Author: YJDT Team
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import itertools
from collections import defaultdict


class GateType(Enum):
    """逻辑门类型"""
    AND = "与门"
    OR = "或门"
    VOTE = "表决门"  # K/N门
    NOT = "非门"
    XOR = "异或门"
    INHIBIT = "禁止门"
    PRIORITY_AND = "优先与门"


class EventType(Enum):
    """事件类型"""
    BASIC = "基本事件"
    UNDEVELOPED = "未展开事件"
    CONDITIONING = "条件事件"
    EXTERNAL = "外部事件"
    HOUSE = "房屋事件"
    INTERMEDIATE = "中间事件"
    TOP = "顶事件"


@dataclass
class BasicEvent:
    """基本事件定义"""
    id: str
    name: str
    description: str
    probability: float  # 失效概率
    failure_rate: float = 0.0  # 失效率 (1/h)
    repair_rate: float = 0.0  # 修复率 (1/h)
    mission_time: float = 8760.0  # 任务时间 (h)
    event_type: EventType = EventType.BASIC

    # 共因故障参数
    ccf_group: Optional[str] = None
    beta_factor: float = 0.0  # β因子

    # 不确定性参数
    error_factor: float = 3.0  # 误差因子(对数正态分布)

    def get_unavailability(self) -> float:
        """计算不可用度"""
        if self.failure_rate > 0 and self.repair_rate > 0:
            # 可修复设备
            return self.failure_rate / (self.failure_rate + self.repair_rate)
        elif self.failure_rate > 0:
            # 不可修复设备
            return 1 - np.exp(-self.failure_rate * self.mission_time)
        else:
            return self.probability


@dataclass
class FaultTreeGate:
    """故障树逻辑门"""
    id: str
    name: str
    gate_type: GateType
    inputs: List[str]  # 输入事件/门的ID列表
    k_value: int = 0  # 表决门的K值
    description: str = ""


@dataclass
class FaultTree:
    """故障树结构"""
    id: str
    name: str
    description: str
    top_event: str  # 顶事件ID

    gates: Dict[str, FaultTreeGate] = field(default_factory=dict)
    basic_events: Dict[str, BasicEvent] = field(default_factory=dict)

    def add_gate(self, gate: FaultTreeGate):
        self.gates[gate.id] = gate

    def add_basic_event(self, event: BasicEvent):
        self.basic_events[event.id] = event


class FaultTreeAnalyzer:
    """故障树分析器"""

    def __init__(self, fault_tree: FaultTree):
        self.ft = fault_tree
        self.minimal_cut_sets: List[Set[str]] = []
        self.top_probability: float = 0.0

    def find_minimal_cut_sets(self) -> List[Set[str]]:
        """求取最小割集 (MOCUS算法)"""
        self.minimal_cut_sets = []

        # 从顶事件开始展开
        cut_sets = self._expand_gate(self.ft.top_event)

        # 最小化
        self.minimal_cut_sets = self._minimize_cut_sets(cut_sets)

        return self.minimal_cut_sets

    def _expand_gate(self, gate_id: str) -> List[Set[str]]:
        """展开逻辑门"""
        if gate_id in self.ft.basic_events:
            return [{gate_id}]

        gate = self.ft.gates.get(gate_id)
        if not gate:
            return []

        # 递归展开所有输入
        input_cut_sets = []
        for input_id in gate.inputs:
            input_cut_sets.append(self._expand_gate(input_id))

        # 根据门类型组合
        if gate.gate_type == GateType.OR:
            # 或门：并集
            result = []
            for cs_list in input_cut_sets:
                result.extend(cs_list)
            return result

        elif gate.gate_type == GateType.AND:
            # 与门：笛卡尔积
            if not input_cut_sets:
                return []

            result = input_cut_sets[0]
            for cs_list in input_cut_sets[1:]:
                new_result = []
                for cs1 in result:
                    for cs2 in cs_list:
                        new_result.append(cs1 | cs2)
                result = new_result
            return result

        elif gate.gate_type == GateType.VOTE:
            # K/N表决门
            n = len(gate.inputs)
            k = gate.k_value
            result = []

            # 生成所有K个输入的组合
            for combo in itertools.combinations(range(n), k):
                combo_sets = [input_cut_sets[i] for i in combo]
                # 对选中的输入做与门操作
                if combo_sets:
                    combined = combo_sets[0]
                    for cs_list in combo_sets[1:]:
                        new_combined = []
                        for cs1 in combined:
                            for cs2 in cs_list:
                                new_combined.append(cs1 | cs2)
                        combined = new_combined
                    result.extend(combined)
            return result

        return []

    def _minimize_cut_sets(self, cut_sets: List[Set[str]]) -> List[Set[str]]:
        """最小化割集（去除超集）"""
        if not cut_sets:
            return []

        # 按长度排序
        sorted_sets = sorted(cut_sets, key=len)
        minimal = []

        for cs in sorted_sets:
            # 检查是否是已有最小割集的超集
            is_superset = False
            for mcs in minimal:
                if mcs <= cs:
                    is_superset = True
                    break
            if not is_superset:
                minimal.append(cs)

        return minimal

    def calculate_top_probability(self, method: str = "rare_event") -> float:
        """计算顶事件概率"""
        if not self.minimal_cut_sets:
            self.find_minimal_cut_sets()

        if method == "rare_event":
            # 稀有事件近似（上界）
            prob = 0.0
            for mcs in self.minimal_cut_sets:
                mcs_prob = 1.0
                for event_id in mcs:
                    event = self.ft.basic_events.get(event_id)
                    if event:
                        mcs_prob *= event.get_unavailability()
                prob += mcs_prob
            self.top_probability = min(1.0, prob)

        elif method == "min_cut_upper":
            # 最小割集上界
            prob = 1.0
            for mcs in self.minimal_cut_sets:
                mcs_prob = 1.0
                for event_id in mcs:
                    event = self.ft.basic_events.get(event_id)
                    if event:
                        mcs_prob *= event.get_unavailability()
                prob *= (1 - mcs_prob)
            self.top_probability = 1 - prob

        elif method == "exact":
            # 精确计算（包含-排斥原理）
            n = len(self.minimal_cut_sets)
            prob = 0.0

            for r in range(1, n + 1):
                sign = (-1) ** (r + 1)
                for combo in itertools.combinations(range(n), r):
                    # 计算组合割集的交集概率
                    union_set = set()
                    for i in combo:
                        union_set |= self.minimal_cut_sets[i]

                    intersection_prob = 1.0
                    for event_id in union_set:
                        event = self.ft.basic_events.get(event_id)
                        if event:
                            intersection_prob *= event.get_unavailability()

                    prob += sign * intersection_prob

            self.top_probability = prob

        return self.top_probability

    def calculate_importance(self) -> Dict[str, Dict[str, float]]:
        """计算重要度指标"""
        importance = {}

        top_prob = self.calculate_top_probability()

        for event_id, event in self.ft.basic_events.items():
            q = event.get_unavailability()

            # Fussell-Vesely重要度
            fv = 0.0
            for mcs in self.minimal_cut_sets:
                if event_id in mcs:
                    mcs_prob = 1.0
                    for eid in mcs:
                        e = self.ft.basic_events.get(eid)
                        if e:
                            mcs_prob *= e.get_unavailability()
                    fv += mcs_prob
            fv = fv / top_prob if top_prob > 0 else 0

            # Birnbaum重要度
            # Q(1) - Q(0)，即设备必然失效与必然可用的概率差
            original_prob = event.probability
            event.probability = 1.0
            q1 = self.calculate_top_probability("rare_event")
            event.probability = 0.0
            q0 = self.calculate_top_probability("rare_event")
            event.probability = original_prob
            birnbaum = q1 - q0

            # Risk Achievement Worth (RAW)
            raw = q1 / top_prob if top_prob > 0 else 0

            # Risk Reduction Worth (RRW)
            rrw = top_prob / q0 if q0 > 0 else float('inf')

            importance[event_id] = {
                'fussell_vesely': fv,
                'birnbaum': birnbaum,
                'raw': raw,
                'rrw': rrw,
                'unavailability': q
            }

        return importance


@dataclass
class EventTreeBranch:
    """事件树分支"""
    heading_id: str
    success_probability: float
    success_next: Optional[str] = None
    failure_next: Optional[str] = None
    success_sequence: Optional[str] = None
    failure_sequence: Optional[str] = None


@dataclass
class EventTreeHeading:
    """事件树标题（功能事件）"""
    id: str
    name: str
    description: str
    success_probability: float
    failure_probability: float
    fault_tree: Optional[str] = None  # 关联的故障树ID


@dataclass
class AccidentSequence:
    """事故序列"""
    id: str
    name: str
    path: List[Tuple[str, bool]]  # (标题ID, 是否成功)
    frequency: float
    consequence_category: str  # 后果类别
    description: str = ""


class EventTree:
    """事件树结构"""

    def __init__(self, id: str, name: str, initiating_event: str,
                 ie_frequency: float):
        self.id = id
        self.name = name
        self.initiating_event = initiating_event
        self.ie_frequency = ie_frequency

        self.headings: List[EventTreeHeading] = []
        self.sequences: List[AccidentSequence] = []

    def add_heading(self, heading: EventTreeHeading):
        self.headings.append(heading)

    def quantify(self) -> List[AccidentSequence]:
        """量化事件树"""
        self.sequences = []

        # 生成所有可能的路径
        n = len(self.headings)
        for i in range(2 ** n):
            path = []
            freq = self.ie_frequency

            for j, heading in enumerate(self.headings):
                success = (i >> j) & 1 == 0

                if success:
                    freq *= heading.success_probability
                    path.append((heading.id, True))
                else:
                    freq *= heading.failure_probability
                    path.append((heading.id, False))

            # 确定后果类别
            failures = sum(1 for _, s in path if not s)
            if failures == 0:
                category = "OK"
            elif failures == 1:
                category = "CD1"  # 受控降级1
            elif failures == 2:
                category = "CD2"
            else:
                category = "CD3" if failures < n else "CORE_DAMAGE"

            seq = AccidentSequence(
                id=f"SEQ-{i:03d}",
                name=f"序列{i}",
                path=path,
                frequency=freq,
                consequence_category=category
            )
            self.sequences.append(seq)

        return self.sequences


class CommonCauseFailureAnalyzer:
    """共因故障分析器"""

    def __init__(self, method: str = "beta_factor"):
        """
        method: beta_factor, mgl (Multiple Greek Letter), alpha_factor
        """
        self.method = method

    def calculate_ccf_probability(self, basic_events: List[BasicEvent],
                                  ccf_parameters: Dict) -> Dict[str, float]:
        """计算共因故障概率"""
        results = {}

        if self.method == "beta_factor":
            # β因子法
            beta = ccf_parameters.get('beta', 0.1)

            # 独立失效概率
            for event in basic_events:
                q_ind = event.get_unavailability() * (1 - beta)
                results[f"{event.id}_ind"] = q_ind

            # 共因失效概率
            if basic_events:
                q_ccf = basic_events[0].get_unavailability() * beta
                results["ccf"] = q_ccf

        elif self.method == "alpha_factor":
            # α因子法
            n = len(basic_events)
            alphas = ccf_parameters.get('alphas', {})

            q_total = sum(e.get_unavailability() for e in basic_events) / n

            for k in range(1, n + 1):
                alpha_k = alphas.get(k, 0)
                # k个设备同时失效的概率
                from math import comb
                q_k = (comb(n, k) * alpha_k * q_total) / sum(
                    j * comb(n, j) * alphas.get(j, 0) for j in range(1, n + 1)
                ) if sum(alphas.values()) > 0 else 0
                results[f"ccf_{k}of{n}"] = q_k

        return results


class PSAAnalyzer:
    """概率安全分析器"""

    def __init__(self):
        self.fault_trees: Dict[str, FaultTree] = {}
        self.event_trees: Dict[str, EventTree] = {}
        self.initiating_events: Dict[str, float] = {}

        # 结果
        self.cdf: float = 0.0  # 堆芯损伤频率（对应大坝失事频率）
        self.sequence_results: List[Dict] = []

    def add_fault_tree(self, ft: FaultTree):
        self.fault_trees[ft.id] = ft

    def add_event_tree(self, et: EventTree):
        self.event_trees[et.id] = et

    def add_initiating_event(self, ie_id: str, frequency: float):
        self.initiating_events[ie_id] = frequency

    def perform_level1_psa(self) -> Dict[str, Any]:
        """执行第一级PSA（系统分析）"""
        results = {
            'initiating_events': {},
            'fault_tree_results': {},
            'event_tree_results': {},
            'accident_sequences': [],
            'total_cdf': 0.0,
            'dominant_sequences': [],
            'importance_analysis': {}
        }

        # 1. 分析各故障树
        for ft_id, ft in self.fault_trees.items():
            analyzer = FaultTreeAnalyzer(ft)
            mcs = analyzer.find_minimal_cut_sets()
            prob = analyzer.calculate_top_probability()
            importance = analyzer.calculate_importance()

            results['fault_tree_results'][ft_id] = {
                'minimal_cut_sets': [list(cs) for cs in mcs],
                'top_probability': prob,
                'importance': importance
            }

        # 2. 量化各事件树
        all_sequences = []
        for et_id, et in self.event_trees.items():
            sequences = et.quantify()
            results['event_tree_results'][et_id] = {
                'sequences': len(sequences),
                'ie_frequency': et.ie_frequency
            }

            for seq in sequences:
                all_sequences.append({
                    'event_tree': et_id,
                    'sequence_id': seq.id,
                    'path': seq.path,
                    'frequency': seq.frequency,
                    'category': seq.consequence_category
                })

        # 3. 计算总CDF
        for seq in all_sequences:
            if seq['category'] in ['CORE_DAMAGE', 'CD3']:
                results['total_cdf'] += seq['frequency']

        self.cdf = results['total_cdf']

        # 4. 识别主要事故序列
        all_sequences.sort(key=lambda x: x['frequency'], reverse=True)
        results['dominant_sequences'] = all_sequences[:20]
        results['accident_sequences'] = all_sequences

        return results

    def perform_uncertainty_analysis(self, n_samples: int = 10000) -> Dict[str, Any]:
        """执行不确定性分析（蒙特卡洛）"""
        cdf_samples = []

        for _ in range(n_samples):
            # 对每个基本事件采样
            for ft in self.fault_trees.values():
                for event in ft.basic_events.values():
                    # 对数正态分布采样
                    median = event.probability
                    ef = event.error_factor
                    sigma = np.log(ef) / 1.645
                    sampled = np.random.lognormal(np.log(median), sigma)
                    event.probability = min(1.0, sampled)

            # 重新计算CDF
            total_cdf = 0.0
            for ft in self.fault_trees.values():
                analyzer = FaultTreeAnalyzer(ft)
                analyzer.find_minimal_cut_sets()
                total_cdf += analyzer.calculate_top_probability()

            cdf_samples.append(total_cdf)

        # 统计分析
        cdf_array = np.array(cdf_samples)
        results = {
            'mean': np.mean(cdf_array),
            'median': np.median(cdf_array),
            'std': np.std(cdf_array),
            'percentile_5': np.percentile(cdf_array, 5),
            'percentile_95': np.percentile(cdf_array, 95),
            'error_factor': np.percentile(cdf_array, 95) / np.percentile(cdf_array, 50)
        }

        return results


def create_hydropower_psa_model() -> PSAAnalyzer:
    """创建水电站PSA模型示例"""

    psa = PSAAnalyzer()

    # ========================================
    # 1. 创建故障树：调速系统失效
    # ========================================
    ft_governor = FaultTree(
        id="FT-GOV",
        name="调速系统失效",
        description="调速系统无法正常调节导叶",
        top_event="GOV_FAIL"
    )

    # 基本事件
    ft_governor.add_basic_event(BasicEvent(
        id="GOV_CTRL_FAIL",
        name="调速器控制器故障",
        description="调速器PLC/DCS失效",
        probability=1e-4,
        failure_rate=1e-5,
        repair_rate=0.1
    ))

    ft_governor.add_basic_event(BasicEvent(
        id="GOV_OIL_FAIL",
        name="油压系统失效",
        description="调速器液压油系统失效",
        probability=1e-4,
        failure_rate=1e-5,
        repair_rate=0.05
    ))

    ft_governor.add_basic_event(BasicEvent(
        id="GV_ACT_FAIL",
        name="导叶执行器故障",
        description="导叶接力器失效",
        probability=5e-5,
        failure_rate=5e-6,
        repair_rate=0.02,
        ccf_group="GV_ACT",
        beta_factor=0.05
    ))

    ft_governor.add_basic_event(BasicEvent(
        id="SENSOR_FAIL",
        name="传感器故障",
        description="转速/功率传感器失效",
        probability=1e-4,
        failure_rate=1e-5,
        repair_rate=0.2
    ))

    # 逻辑门
    ft_governor.add_gate(FaultTreeGate(
        id="GOV_FAIL",
        name="调速系统失效",
        gate_type=GateType.OR,
        inputs=["CTRL_OR_OIL", "GV_ACT_FAIL", "SENSOR_FAIL"]
    ))

    ft_governor.add_gate(FaultTreeGate(
        id="CTRL_OR_OIL",
        name="控制或油压失效",
        gate_type=GateType.OR,
        inputs=["GOV_CTRL_FAIL", "GOV_OIL_FAIL"]
    ))

    psa.add_fault_tree(ft_governor)

    # ========================================
    # 2. 创建故障树：事故闸门失效
    # ========================================
    ft_gate = FaultTree(
        id="FT-GATE",
        name="事故闸门失效",
        description="事故闸门无法关闭",
        top_event="GATE_FAIL"
    )

    ft_gate.add_basic_event(BasicEvent(
        id="GATE_MECH_FAIL",
        name="闸门机械故障",
        description="闸门卡死或变形",
        probability=1e-5,
        failure_rate=1e-6
    ))

    ft_gate.add_basic_event(BasicEvent(
        id="GATE_CTRL_FAIL",
        name="闸门控制故障",
        description="闸门控制系统失效",
        probability=5e-5,
        failure_rate=5e-6
    ))

    ft_gate.add_basic_event(BasicEvent(
        id="GATE_POWER_FAIL",
        name="闸门电源故障",
        description="闸门操作电源失效",
        probability=1e-4,
        failure_rate=1e-5
    ))

    ft_gate.add_gate(FaultTreeGate(
        id="GATE_FAIL",
        name="事故闸门失效",
        gate_type=GateType.OR,
        inputs=["GATE_MECH_FAIL", "GATE_CTRL_AND_POWER"]
    ))

    ft_gate.add_gate(FaultTreeGate(
        id="GATE_CTRL_AND_POWER",
        name="控制和电源同时失效",
        gate_type=GateType.AND,
        inputs=["GATE_CTRL_FAIL", "GATE_POWER_FAIL"]
    ))

    psa.add_fault_tree(ft_gate)

    # ========================================
    # 3. 创建事件树：甩负荷事件
    # ========================================
    et_rejection = EventTree(
        id="ET-LR",
        name="甩负荷事件树",
        initiating_event="LOAD_REJECTION",
        ie_frequency=0.1  # 每年0.1次
    )

    et_rejection.add_heading(EventTreeHeading(
        id="GOV_WORKS",
        name="调速器动作",
        description="调速器正常关闭导叶",
        success_probability=0.9999,
        failure_probability=0.0001,
        fault_tree="FT-GOV"
    ))

    et_rejection.add_heading(EventTreeHeading(
        id="GATE_WORKS",
        name="事故闸门动作",
        description="事故闸门成功关闭",
        success_probability=0.99999,
        failure_probability=0.00001,
        fault_tree="FT-GATE"
    ))

    et_rejection.add_heading(EventTreeHeading(
        id="MECH_PROT",
        name="机械过速保护",
        description="机械过速保护装置动作",
        success_probability=0.999,
        failure_probability=0.001
    ))

    psa.add_event_tree(et_rejection)

    # ========================================
    # 4. 创建事件树：地震事件
    # ========================================
    et_seismic = EventTree(
        id="ET-SEISMIC",
        name="地震事件树",
        initiating_event="EARTHQUAKE",
        ie_frequency=0.01  # 每年0.01次（VII度以上）
    )

    et_seismic.add_heading(EventTreeHeading(
        id="STRUCT_OK",
        name="结构完好",
        description="主体结构未损坏",
        success_probability=0.999,
        failure_probability=0.001
    ))

    et_seismic.add_heading(EventTreeHeading(
        id="EQUIP_OK",
        name="设备可用",
        description="关键设备可正常运行",
        success_probability=0.99,
        failure_probability=0.01
    ))

    et_seismic.add_heading(EventTreeHeading(
        id="POWER_OK",
        name="电源可用",
        description="厂用电和直流电源可用",
        success_probability=0.95,
        failure_probability=0.05
    ))

    et_seismic.add_heading(EventTreeHeading(
        id="SAFE_SHUTDOWN",
        name="安全停机",
        description="机组安全停机",
        success_probability=0.999,
        failure_probability=0.001
    ))

    psa.add_event_tree(et_seismic)

    return psa


def main():
    """演示PSA分析"""
    print("=" * 70)
    print("概率安全分析 (PSA) 演示")
    print("=" * 70)

    # 创建PSA模型
    psa = create_hydropower_psa_model()

    # 执行Level 1 PSA
    print("\n执行第一级PSA分析...")
    results = psa.perform_level1_psa()

    # 故障树分析结果
    print("\n故障树分析结果:")
    print("-" * 50)
    for ft_id, ft_result in results['fault_tree_results'].items():
        print(f"\n{ft_id}:")
        print(f"  顶事件概率: {ft_result['top_probability']:.2e}")
        print(f"  最小割集数: {len(ft_result['minimal_cut_sets'])}")

        # 重要度分析
        print("  重要基本事件:")
        imp = ft_result['importance']
        sorted_imp = sorted(imp.items(), key=lambda x: x[1]['fussell_vesely'], reverse=True)
        for event_id, values in sorted_imp[:5]:
            print(f"    {event_id}: FV={values['fussell_vesely']:.3f}, "
                  f"RAW={values['raw']:.1f}, RRW={values['rrw']:.1f}")

    # 事件树分析结果
    print("\n事件树分析结果:")
    print("-" * 50)
    for et_id, et_result in results['event_tree_results'].items():
        print(f"  {et_id}: {et_result['sequences']}个序列, "
              f"起因事件频率={et_result['ie_frequency']:.2e}/年")

    # 主要事故序列
    print("\n主要事故序列（前10）:")
    print("-" * 50)
    for seq in results['dominant_sequences'][:10]:
        print(f"  {seq['sequence_id']}: {seq['frequency']:.2e}/年 "
              f"[{seq['category']}]")

    # 总CDF
    print(f"\n总CDF (严重事故频率): {results['total_cdf']:.2e}/年")

    # 安全目标评估
    safety_goal = 1e-5  # 安全目标：10^-5/年
    if results['total_cdf'] < safety_goal:
        print(f"✓ 满足安全目标 (< {safety_goal:.0e}/年)")
    else:
        print(f"✗ 不满足安全目标 (目标: {safety_goal:.0e}/年)")

    print("\n" + "=" * 70)
    print("PSA分析完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
