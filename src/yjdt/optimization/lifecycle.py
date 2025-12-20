"""
全生命周期评价模块
Lifecycle Analysis Module

实现水电站的全生命周期效益分析：
- 投资成本分析
- 运营收益预测
- 维护成本估算
- 净现值(NPV)计算
- 内部收益率(IRR)计算
- 可靠性评估
- 环境影响评价
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from scipy.optimize import brentq


class LifecyclePhase(Enum):
    """生命周期阶段"""
    PLANNING = "planning"           # 规划阶段
    CONSTRUCTION = "construction"   # 建设阶段
    COMMISSIONING = "commissioning" # 调试阶段
    OPERATION = "operation"         # 运营阶段
    MAINTENANCE = "maintenance"     # 检修阶段
    UPGRADE = "upgrade"             # 改造升级
    DECOMMISSION = "decommission"   # 退役阶段


@dataclass
class InvestmentCost:
    """投资成本"""
    # 工程投资（亿元）
    civil_works: float = 0.0            # 土建工程
    hydraulic_structures: float = 0.0   # 水工结构
    equipment_procurement: float = 0.0   # 设备采购
    equipment_installation: float = 0.0  # 设备安装
    electrical_works: float = 0.0        # 电气工程
    control_systems: float = 0.0         # 控制系统
    auxiliary_systems: float = 0.0       # 辅助系统
    transmission_lines: float = 0.0      # 输电线路
    environmental: float = 0.0           # 环保工程
    resettlement: float = 0.0           # 移民安置

    # 其他费用
    design_consulting: float = 0.0       # 设计咨询
    supervision: float = 0.0             # 监理费
    contingency: float = 0.0             # 预备费
    financing: float = 0.0               # 建设期利息

    @property
    def total(self) -> float:
        """总投资"""
        return sum([
            self.civil_works, self.hydraulic_structures,
            self.equipment_procurement, self.equipment_installation,
            self.electrical_works, self.control_systems,
            self.auxiliary_systems, self.transmission_lines,
            self.environmental, self.resettlement,
            self.design_consulting, self.supervision,
            self.contingency, self.financing,
        ])


@dataclass
class OperatingCost:
    """运营成本（万元/年）"""
    labor: float = 0.0                  # 人工成本
    maintenance: float = 0.0            # 维护检修
    spare_parts: float = 0.0            # 备品备件
    insurance: float = 0.0              # 保险
    management: float = 0.0             # 管理费
    water_fees: float = 0.0             # 水资源费
    other: float = 0.0                  # 其他

    @property
    def total(self) -> float:
        """年总运营成本"""
        return sum([
            self.labor, self.maintenance, self.spare_parts,
            self.insurance, self.management, self.water_fees, self.other,
        ])


@dataclass
class RevenueModel:
    """收益模型"""
    installed_capacity: float = 6000.0   # 装机容量（MW）
    annual_utilization: float = 4500.0   # 年利用小时数
    on_grid_price: float = 0.30          # 上网电价（元/kWh）
    capacity_price: float = 0.0          # 容量电价（元/kW/年）
    ancillary_revenue: float = 0.0       # 辅助服务收入（万元/年）
    carbon_credit_price: float = 50.0    # 碳价（元/吨）
    carbon_factor: float = 0.8           # 减排因子（tCO2/MWh）

    @property
    def annual_generation(self) -> float:
        """年发电量（亿kWh）"""
        return self.installed_capacity * self.annual_utilization / 1e5

    @property
    def electricity_revenue(self) -> float:
        """电量收入（亿元/年）"""
        return self.annual_generation * self.on_grid_price

    @property
    def capacity_revenue(self) -> float:
        """容量收入（亿元/年）"""
        return self.installed_capacity * self.capacity_price / 1e4

    @property
    def carbon_revenue(self) -> float:
        """碳减排收入（亿元/年）"""
        emission_reduction = self.annual_generation * 1e5 * self.carbon_factor / 1e4  # 万吨
        return emission_reduction * self.carbon_credit_price / 1e4

    @property
    def total_revenue(self) -> float:
        """总收入（亿元/年）"""
        return (
            self.electricity_revenue +
            self.capacity_revenue +
            self.carbon_revenue +
            self.ancillary_revenue / 1e4
        )


@dataclass
class LifecycleParameters:
    """生命周期参数"""
    project_life: int = 50              # 项目寿命（年）
    construction_period: int = 8         # 建设期（年）
    discount_rate: float = 0.08          # 折现率
    tax_rate: float = 0.25               # 所得税率
    depreciation_period: int = 20        # 折旧年限
    residual_value_rate: float = 0.05    # 残值率

    # 增长率假设
    price_escalation: float = 0.02       # 电价年增长率
    cost_escalation: float = 0.03        # 成本年增长率

    # 融资结构
    equity_ratio: float = 0.30           # 资本金比例
    loan_rate: float = 0.045             # 贷款利率
    loan_period: int = 20                # 贷款期限


class CostBenefitAnalysis:
    """
    成本效益分析

    计算NPV、IRR、投资回收期等指标
    """

    def __init__(self, params: LifecycleParameters):
        self.params = params

    def calculate_npv(
        self,
        investment: InvestmentCost,
        operating_cost: OperatingCost,
        revenue: RevenueModel
    ) -> float:
        """
        计算净现值(NPV)

        Args:
            investment: 投资成本
            operating_cost: 运营成本
            revenue: 收益模型

        Returns:
            净现值（亿元）
        """
        cash_flows = self._generate_cash_flows(investment, operating_cost, revenue)

        npv = 0.0
        for year, cf in enumerate(cash_flows):
            npv += cf / (1 + self.params.discount_rate) ** year

        return npv

    def calculate_irr(
        self,
        investment: InvestmentCost,
        operating_cost: OperatingCost,
        revenue: RevenueModel
    ) -> float:
        """
        计算内部收益率(IRR)

        Returns:
            内部收益率
        """
        cash_flows = self._generate_cash_flows(investment, operating_cost, revenue)

        def npv_at_rate(r):
            return sum(cf / (1 + r) ** t for t, cf in enumerate(cash_flows))

        try:
            irr = brentq(npv_at_rate, -0.5, 0.5)
        except ValueError:
            irr = 0.0

        return irr

    def calculate_payback_period(
        self,
        investment: InvestmentCost,
        operating_cost: OperatingCost,
        revenue: RevenueModel
    ) -> float:
        """
        计算投资回收期

        Returns:
            回收期（年）
        """
        cash_flows = self._generate_cash_flows(investment, operating_cost, revenue)

        cumulative = 0.0
        for year, cf in enumerate(cash_flows):
            cumulative += cf
            if cumulative >= 0:
                # 插值计算精确回收期
                if year > 0 and cash_flows[year] > 0:
                    fraction = -cash_flows[year-1] / cash_flows[year] if year > 0 else 0
                    return year - 1 + fraction
                return float(year)

        return float('inf')

    def calculate_lcoe(
        self,
        investment: InvestmentCost,
        operating_cost: OperatingCost,
        revenue: RevenueModel
    ) -> float:
        """
        计算平准化发电成本(LCOE)

        Returns:
            LCOE (元/kWh)
        """
        total_years = self.params.project_life

        # 折现后的总成本
        total_cost = investment.total

        for year in range(1, total_years + 1):
            annual_op_cost = operating_cost.total / 1e4  # 转为亿元
            annual_op_cost *= (1 + self.params.cost_escalation) ** year
            total_cost += annual_op_cost / (1 + self.params.discount_rate) ** year

        # 折现后的总发电量
        total_generation = 0.0
        for year in range(1, total_years + 1):
            annual_gen = revenue.annual_generation  # 亿kWh
            total_generation += annual_gen / (1 + self.params.discount_rate) ** year

        # LCOE = 总成本 / 总发电量
        if total_generation > 0:
            lcoe = total_cost / total_generation  # 元/kWh
        else:
            lcoe = 0.0

        return lcoe

    def _generate_cash_flows(
        self,
        investment: InvestmentCost,
        operating_cost: OperatingCost,
        revenue: RevenueModel
    ) -> List[float]:
        """生成现金流序列"""
        construction = self.params.construction_period
        operation = self.params.project_life
        total_years = construction + operation

        cash_flows = []

        # 建设期
        annual_investment = investment.total / construction
        for year in range(construction):
            cash_flows.append(-annual_investment)

        # 运营期
        for year in range(1, operation + 1):
            # 收入
            rev = revenue.total_revenue * (1 + self.params.price_escalation) ** year

            # 成本
            op_cost = operating_cost.total / 1e4  # 转为亿元
            op_cost *= (1 + self.params.cost_escalation) ** year

            # 折旧
            depreciation = investment.total * (1 - self.params.residual_value_rate) / self.params.depreciation_period
            if year > self.params.depreciation_period:
                depreciation = 0

            # 税前利润
            ebit = rev - op_cost - depreciation

            # 税后利润
            tax = max(0, ebit * self.params.tax_rate)
            net_profit = ebit - tax

            # 现金流
            cash_flow = net_profit + depreciation
            cash_flows.append(cash_flow)

        return cash_flows

    def sensitivity_analysis(
        self,
        investment: InvestmentCost,
        operating_cost: OperatingCost,
        revenue: RevenueModel,
        variable: str,
        range_pct: float = 0.3
    ) -> Dict[str, List[Tuple[float, float]]]:
        """
        敏感性分析

        Args:
            variable: 分析变量 ('investment', 'price', 'utilization', 'cost')
            range_pct: 变化范围百分比

        Returns:
            敏感性分析结果
        """
        results = {
            'variable_values': [],
            'npv_values': [],
            'irr_values': [],
        }

        for pct in np.linspace(-range_pct, range_pct, 11):
            # 创建修改后的参数
            if variable == 'investment':
                modified_inv = InvestmentCost(**{
                    k: v * (1 + pct) for k, v in investment.__dict__.items()
                })
                npv = self.calculate_npv(modified_inv, operating_cost, revenue)
                irr = self.calculate_irr(modified_inv, operating_cost, revenue)
            elif variable == 'price':
                modified_rev = RevenueModel(**revenue.__dict__)
                modified_rev.on_grid_price *= (1 + pct)
                npv = self.calculate_npv(investment, operating_cost, modified_rev)
                irr = self.calculate_irr(investment, operating_cost, modified_rev)
            elif variable == 'utilization':
                modified_rev = RevenueModel(**revenue.__dict__)
                modified_rev.annual_utilization *= (1 + pct)
                npv = self.calculate_npv(investment, operating_cost, modified_rev)
                irr = self.calculate_irr(investment, operating_cost, modified_rev)
            elif variable == 'cost':
                modified_op = OperatingCost(**{
                    k: v * (1 + pct) for k, v in operating_cost.__dict__.items()
                })
                npv = self.calculate_npv(investment, modified_op, revenue)
                irr = self.calculate_irr(investment, modified_op, revenue)
            else:
                continue

            results['variable_values'].append(pct)
            results['npv_values'].append(npv)
            results['irr_values'].append(irr)

        return results


class ReliabilityAnalysis:
    """
    可靠性分析

    评估系统全生命周期的可靠性
    """

    def __init__(self):
        # 组件可靠性参数
        self.component_reliability = {
            'turbine': {'mtbf': 80000, 'mttr': 720, 'failure_rate': 0.000012},
            'generator': {'mtbf': 100000, 'mttr': 480, 'failure_rate': 0.00001},
            'governor': {'mtbf': 50000, 'mttr': 24, 'failure_rate': 0.00002},
            'exciter': {'mtbf': 60000, 'mttr': 48, 'failure_rate': 0.000017},
            'transformer': {'mtbf': 200000, 'mttr': 168, 'failure_rate': 0.000005},
            'protection': {'mtbf': 100000, 'mttr': 8, 'failure_rate': 0.00001},
        }

    def calculate_system_availability(
        self,
        num_units: int = 6,
        min_units_required: int = 4
    ) -> float:
        """
        计算系统可用率

        Args:
            num_units: 机组数量
            min_units_required: 最少运行机组数

        Returns:
            系统可用率
        """
        # 单机可用率
        unit_availability = self._calculate_unit_availability()

        # k/n系统可用率（至少k个可用）
        system_availability = 0.0

        for k in range(min_units_required, num_units + 1):
            # C(n,k) * A^k * (1-A)^(n-k)
            comb = np.math.comb(num_units, k)
            prob = comb * (unit_availability ** k) * ((1 - unit_availability) ** (num_units - k))
            system_availability += prob

        return system_availability

    def _calculate_unit_availability(self) -> float:
        """计算单机可用率"""
        # 串联系统
        total_failure_rate = sum(
            comp['failure_rate'] for comp in self.component_reliability.values()
        )
        total_mttr = np.mean([
            comp['mttr'] for comp in self.component_reliability.values()
        ])

        mtbf = 1 / total_failure_rate
        availability = mtbf / (mtbf + total_mttr)

        return availability

    def predict_failures(
        self,
        years: int = 50
    ) -> Dict[str, List[float]]:
        """
        预测故障次数

        Args:
            years: 预测年数

        Returns:
            各年预测故障次数
        """
        hours_per_year = 8760

        predictions = {comp: [] for comp in self.component_reliability}

        for year in range(1, years + 1):
            for comp, params in self.component_reliability.items():
                # 考虑老化因素
                aging_factor = 1 + 0.02 * (year - 1)  # 每年增加2%故障率
                expected_failures = hours_per_year * params['failure_rate'] * aging_factor
                predictions[comp].append(expected_failures)

        return predictions

    def calculate_ram_metrics(self) -> Dict:
        """计算RAM指标（可靠性、可用性、可维护性）"""
        availability = self._calculate_unit_availability()

        # MTBF
        total_mtbf = 1 / sum(
            comp['failure_rate'] for comp in self.component_reliability.values()
        )

        # MTTR
        total_mttr = np.mean([
            comp['mttr'] for comp in self.component_reliability.values()
        ])

        return {
            'availability': availability,
            'mtbf_hours': total_mtbf,
            'mttr_hours': total_mttr,
            'failure_rate': 1 / total_mtbf,
        }


class LifecycleAnalyzer:
    """
    全生命周期分析器

    综合成本效益和可靠性分析
    """

    def __init__(self):
        self.params = LifecycleParameters()
        self.cost_benefit = CostBenefitAnalysis(self.params)
        self.reliability = ReliabilityAnalysis()

    def analyze_scheme(
        self,
        scheme_name: str,
        investment: InvestmentCost,
        operating_cost: OperatingCost,
        revenue: RevenueModel,
        num_units: int = 6
    ) -> Dict:
        """
        分析设计方案的全生命周期效益

        Returns:
            综合分析结果
        """
        # 经济分析
        npv = self.cost_benefit.calculate_npv(investment, operating_cost, revenue)
        irr = self.cost_benefit.calculate_irr(investment, operating_cost, revenue)
        payback = self.cost_benefit.calculate_payback_period(investment, operating_cost, revenue)
        lcoe = self.cost_benefit.calculate_lcoe(investment, operating_cost, revenue)

        # 可靠性分析
        system_availability = self.reliability.calculate_system_availability(num_units)
        ram_metrics = self.reliability.calculate_ram_metrics()

        # 综合得分
        economic_score = self._score_economics(npv, irr, payback)
        reliability_score = system_availability * 100

        total_score = 0.6 * economic_score + 0.4 * reliability_score

        return {
            'scheme_name': scheme_name,
            'economics': {
                'npv': npv,
                'irr': irr,
                'payback_period': payback,
                'lcoe': lcoe,
                'total_investment': investment.total,
                'annual_revenue': revenue.total_revenue,
                'annual_cost': operating_cost.total / 1e4,
            },
            'reliability': {
                'system_availability': system_availability,
                **ram_metrics,
            },
            'scores': {
                'economic_score': economic_score,
                'reliability_score': reliability_score,
                'total_score': total_score,
            },
        }

    def _score_economics(self, npv: float, irr: float, payback: float) -> float:
        """经济性评分"""
        # NPV得分
        npv_score = min(100, max(0, npv / 10 + 50))

        # IRR得分
        irr_score = min(100, max(0, irr * 1000))

        # 回收期得分
        if payback < 10:
            payback_score = 100
        elif payback < 20:
            payback_score = 80
        elif payback < 30:
            payback_score = 60
        else:
            payback_score = 40

        return 0.4 * npv_score + 0.3 * irr_score + 0.3 * payback_score

    def generate_lifecycle_report(self, analysis_result: Dict) -> str:
        """生成生命周期分析报告"""
        eco = analysis_result['economics']
        rel = analysis_result['reliability']
        scores = analysis_result['scores']

        report = f"""
全生命周期分析报告
==================

方案: {analysis_result['scheme_name']}

1. 经济效益分析

   投资规模
   - 总投资: {eco['total_investment']:.2f} 亿元

   收益预测
   - 年发电收入: {eco['annual_revenue']:.2f} 亿元
   - 年运营成本: {eco['annual_cost']:.2f} 亿元
   - 年净收益: {eco['annual_revenue'] - eco['annual_cost']:.2f} 亿元

   财务指标
   - 净现值(NPV): {eco['npv']:.2f} 亿元
   - 内部收益率(IRR): {eco['irr']*100:.2f}%
   - 投资回收期: {eco['payback_period']:.1f} 年
   - 平准化发电成本(LCOE): {eco['lcoe']*100:.2f} 分/kWh

2. 可靠性分析

   - 系统可用率: {rel['system_availability']*100:.3f}%
   - 平均故障间隔(MTBF): {rel['mtbf_hours']:.0f} 小时
   - 平均修复时间(MTTR): {rel['mttr_hours']:.1f} 小时
   - 故障率: {rel['failure_rate']*1e6:.2f} 次/百万小时

3. 综合评价

   - 经济性得分: {scores['economic_score']:.1f}
   - 可靠性得分: {scores['reliability_score']:.1f}
   - 综合得分: {scores['total_score']:.1f}

"""
        return report
