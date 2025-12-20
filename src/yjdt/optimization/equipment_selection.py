"""
设备选型优化模块
Equipment Selection Optimization Module

实现水电站关键设备的选型优化：
- 水轮机选型
- 发电机选型
- 调速器选型
- 励磁系统选型
- 辅助设备选型
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class EquipmentCategory(Enum):
    """设备类别"""
    TURBINE = "turbine"
    GENERATOR = "generator"
    GOVERNOR = "governor"
    EXCITER = "exciter"
    TRANSFORMER = "transformer"
    VALVE = "valve"
    BEARING = "bearing"
    COOLING = "cooling"
    PROTECTION = "protection"
    CONTROL = "control"


class VendorLevel(Enum):
    """供应商级别"""
    TOP_TIER = "top_tier"           # 顶级供应商
    PREMIUM = "premium"             # 优质供应商
    STANDARD = "standard"           # 标准供应商
    ECONOMY = "economy"             # 经济型供应商


@dataclass
class EquipmentSpec:
    """设备规格"""
    equipment_id: str
    name: str
    category: EquipmentCategory
    manufacturer: str
    vendor_level: VendorLevel

    # 技术参数
    rated_capacity: float = 0.0     # 额定容量
    rated_efficiency: float = 0.95  # 额定效率
    operating_range: Tuple[float, float] = (0.3, 1.1)  # 运行范围

    # 经济参数
    capital_cost: float = 0.0       # 采购成本（万元）
    installation_cost: float = 0.0  # 安装成本（万元）
    maintenance_cost: float = 0.0   # 年维护成本（万元）

    # 可靠性参数
    design_life: float = 40.0       # 设计寿命（年）
    mtbf: float = 50000.0           # 平均故障间隔时间（小时）
    mttr: float = 24.0              # 平均修复时间（小时）
    availability: float = 0.99      # 可用率

    # 环境适应性
    altitude_limit: float = 4000.0  # 最高海拔（m）
    temp_range: Tuple[float, float] = (-20, 50)  # 工作温度范围

    # 技术成熟度
    technology_readiness: float = 9.0  # 技术成熟度（1-9级）
    domestic_rate: float = 0.0       # 国产化率

    # 标签
    features: List[str] = field(default_factory=list)


@dataclass
class SelectionCriteria:
    """选型准则"""
    # 权重
    weights: Dict[str, float] = field(default_factory=lambda: {
        'performance': 0.25,
        'reliability': 0.25,
        'economy': 0.20,
        'technology': 0.15,
        'adaptability': 0.15,
    })

    # 约束
    max_budget: float = float('inf')
    min_efficiency: float = 0.90
    min_availability: float = 0.98
    min_domestic_rate: float = 0.0
    altitude_requirement: float = 3500.0
    temp_requirement: Tuple[float, float] = (-10, 40)


class EquipmentDatabase:
    """
    设备数据库

    存储可选设备的规格信息
    """

    def __init__(self):
        self.equipment: Dict[str, EquipmentSpec] = {}
        self._init_database()

    def _init_database(self):
        """初始化设备数据库"""
        # 水轮机选项
        self._add_turbine_options()
        # 发电机选项
        self._add_generator_options()
        # 调速器选项
        self._add_governor_options()
        # 励磁系统选项
        self._add_exciter_options()

    def _add_turbine_options(self):
        """添加水轮机选项"""
        # 哈尔滨电机 - 国内顶级
        self.add_equipment(EquipmentSpec(
            equipment_id="TUR_HEC_F1000",
            name="HEC-F1000型混流式水轮机",
            category=EquipmentCategory.TURBINE,
            manufacturer="哈尔滨电机厂",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1000.0,
            rated_efficiency=0.945,
            operating_range=(0.3, 1.05),
            capital_cost=50000.0,
            installation_cost=5000.0,
            maintenance_cost=500.0,
            design_life=50.0,
            mtbf=80000.0,
            availability=0.995,
            altitude_limit=4500.0,
            technology_readiness=9.0,
            domestic_rate=0.95,
            features=['高水头', '大容量', '白鹤滩技术'],
        ))

        # 东方电机
        self.add_equipment(EquipmentSpec(
            equipment_id="TUR_DEC_F1000",
            name="DEC-F1000型混流式水轮机",
            category=EquipmentCategory.TURBINE,
            manufacturer="东方电机",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1000.0,
            rated_efficiency=0.940,
            operating_range=(0.35, 1.05),
            capital_cost=48000.0,
            installation_cost=4800.0,
            maintenance_cost=480.0,
            design_life=50.0,
            mtbf=75000.0,
            availability=0.994,
            altitude_limit=4000.0,
            technology_readiness=9.0,
            domestic_rate=0.90,
            features=['高水头', '溪洛渡技术'],
        ))

        # 阿尔斯通（现GE）
        self.add_equipment(EquipmentSpec(
            equipment_id="TUR_GEH_F1000",
            name="GE Hydro Francis 1000",
            category=EquipmentCategory.TURBINE,
            manufacturer="GE Hydro",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1000.0,
            rated_efficiency=0.948,
            operating_range=(0.25, 1.08),
            capital_cost=70000.0,
            installation_cost=8000.0,
            maintenance_cost=800.0,
            design_life=50.0,
            mtbf=90000.0,
            availability=0.997,
            altitude_limit=5000.0,
            technology_readiness=9.0,
            domestic_rate=0.30,
            features=['全球领先', '宽运行范围', '进口'],
        ))

        # 福伊特（Voith）
        self.add_equipment(EquipmentSpec(
            equipment_id="TUR_VOI_F1000",
            name="Voith Francis 1000",
            category=EquipmentCategory.TURBINE,
            manufacturer="Voith Hydro",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1000.0,
            rated_efficiency=0.946,
            operating_range=(0.28, 1.06),
            capital_cost=68000.0,
            installation_cost=7500.0,
            maintenance_cost=750.0,
            design_life=50.0,
            mtbf=85000.0,
            availability=0.996,
            altitude_limit=4500.0,
            technology_readiness=9.0,
            domestic_rate=0.35,
            features=['德国技术', '高可靠性', '进口'],
        ))

    def _add_generator_options(self):
        """添加发电机选项"""
        self.add_equipment(EquipmentSpec(
            equipment_id="GEN_HEC_S1000",
            name="HEC同步发电机 1000MW",
            category=EquipmentCategory.GENERATOR,
            manufacturer="哈尔滨电机厂",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1111.0,  # MVA
            rated_efficiency=0.988,
            capital_cost=30000.0,
            installation_cost=3000.0,
            maintenance_cost=300.0,
            design_life=50.0,
            mtbf=100000.0,
            availability=0.998,
            technology_readiness=9.0,
            domestic_rate=0.98,
            features=['大容量', '高效率', '国产'],
        ))

        self.add_equipment(EquipmentSpec(
            equipment_id="GEN_DEC_S1000",
            name="DEC同步发电机 1000MW",
            category=EquipmentCategory.GENERATOR,
            manufacturer="东方电机",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1111.0,
            rated_efficiency=0.987,
            capital_cost=29000.0,
            installation_cost=2900.0,
            maintenance_cost=290.0,
            design_life=50.0,
            mtbf=95000.0,
            availability=0.997,
            technology_readiness=9.0,
            domestic_rate=0.96,
            features=['大容量', '国产'],
        ))

        self.add_equipment(EquipmentSpec(
            equipment_id="GEN_ABB_S1000",
            name="ABB同步发电机 1000MW",
            category=EquipmentCategory.GENERATOR,
            manufacturer="ABB",
            vendor_level=VendorLevel.PREMIUM,
            rated_capacity=1111.0,
            rated_efficiency=0.990,
            capital_cost=45000.0,
            installation_cost=5000.0,
            maintenance_cost=500.0,
            design_life=50.0,
            mtbf=120000.0,
            availability=0.999,
            technology_readiness=9.0,
            domestic_rate=0.40,
            features=['高效率', '高可靠性', '进口'],
        ))

    def _add_governor_options(self):
        """添加调速器选项"""
        self.add_equipment(EquipmentSpec(
            equipment_id="GOV_NARI_MPC",
            name="南瑞MPC调速器",
            category=EquipmentCategory.GOVERNOR,
            manufacturer="南瑞集团",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1000.0,
            capital_cost=800.0,
            installation_cost=50.0,
            maintenance_cost=20.0,
            design_life=25.0,
            mtbf=50000.0,
            availability=0.995,
            technology_readiness=9.0,
            domestic_rate=1.0,
            features=['MPC控制', '自适应', '国产'],
        ))

        self.add_equipment(EquipmentSpec(
            equipment_id="GOV_ABB_UNITROL",
            name="ABB Unitrol调速器",
            category=EquipmentCategory.GOVERNOR,
            manufacturer="ABB",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1200.0,
            capital_cost=1500.0,
            installation_cost=100.0,
            maintenance_cost=50.0,
            design_life=25.0,
            mtbf=80000.0,
            availability=0.998,
            technology_readiness=9.0,
            domestic_rate=0.20,
            features=['先进算法', '高可靠性', '进口'],
        ))

        self.add_equipment(EquipmentSpec(
            equipment_id="GOV_SIEMENS_TELEPERM",
            name="西门子Teleperm调速器",
            category=EquipmentCategory.GOVERNOR,
            manufacturer="Siemens",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1200.0,
            capital_cost=1400.0,
            installation_cost=90.0,
            maintenance_cost=45.0,
            design_life=25.0,
            mtbf=75000.0,
            availability=0.997,
            technology_readiness=9.0,
            domestic_rate=0.25,
            features=['模块化', '冗余设计', '进口'],
        ))

    def _add_exciter_options(self):
        """添加励磁系统选项"""
        self.add_equipment(EquipmentSpec(
            equipment_id="EXC_NARI_THYRI",
            name="南瑞可控硅励磁系统",
            category=EquipmentCategory.EXCITER,
            manufacturer="南瑞集团",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1000.0,
            capital_cost=500.0,
            installation_cost=30.0,
            maintenance_cost=15.0,
            design_life=25.0,
            mtbf=60000.0,
            availability=0.996,
            technology_readiness=9.0,
            domestic_rate=1.0,
            features=['静止励磁', '响应快', '国产'],
        ))

        self.add_equipment(EquipmentSpec(
            equipment_id="EXC_ABB_UNITROL",
            name="ABB Unitrol励磁系统",
            category=EquipmentCategory.EXCITER,
            manufacturer="ABB",
            vendor_level=VendorLevel.TOP_TIER,
            rated_capacity=1200.0,
            capital_cost=1000.0,
            installation_cost=60.0,
            maintenance_cost=30.0,
            design_life=30.0,
            mtbf=100000.0,
            availability=0.999,
            technology_readiness=9.0,
            domestic_rate=0.30,
            features=['高性能', '高可靠性', '进口'],
        ))

    def add_equipment(self, equipment: EquipmentSpec):
        """添加设备"""
        self.equipment[equipment.equipment_id] = equipment

    def get_by_category(self, category: EquipmentCategory) -> List[EquipmentSpec]:
        """按类别获取设备"""
        return [e for e in self.equipment.values() if e.category == category]

    def get_by_capacity_range(
        self,
        category: EquipmentCategory,
        min_capacity: float,
        max_capacity: float
    ) -> List[EquipmentSpec]:
        """按容量范围获取设备"""
        return [
            e for e in self.equipment.values()
            if e.category == category and min_capacity <= e.rated_capacity <= max_capacity
        ]


class EquipmentSelector:
    """
    设备选型优化器

    基于多目标优化进行设备选型
    """

    def __init__(self):
        self.database = EquipmentDatabase()
        self.criteria = SelectionCriteria()

        # 选型结果
        self.selections: Dict[EquipmentCategory, EquipmentSpec] = {}
        self.evaluation_results: Dict[str, Dict] = {}

    def set_criteria(self, criteria: SelectionCriteria):
        """设置选型准则"""
        self.criteria = criteria

    def evaluate_equipment(self, equipment: EquipmentSpec) -> Dict:
        """
        评估单个设备

        Args:
            equipment: 设备规格

        Returns:
            评估结果
        """
        scores = {}

        # 性能得分
        scores['performance'] = self._score_performance(equipment)

        # 可靠性得分
        scores['reliability'] = self._score_reliability(equipment)

        # 经济性得分
        scores['economy'] = self._score_economy(equipment)

        # 技术成熟度得分
        scores['technology'] = self._score_technology(equipment)

        # 环境适应性得分
        scores['adaptability'] = self._score_adaptability(equipment)

        # 综合得分
        total_score = sum(
            scores[k] * self.criteria.weights[k]
            for k in self.criteria.weights
        )

        # 检查约束
        constraints_satisfied = self._check_constraints(equipment)

        return {
            'equipment_id': equipment.equipment_id,
            'scores': scores,
            'total_score': total_score,
            'constraints_satisfied': constraints_satisfied,
        }

    def _score_performance(self, equipment: EquipmentSpec) -> float:
        """性能评分"""
        # 基于效率
        efficiency_score = equipment.rated_efficiency * 100

        # 基于运行范围
        range_width = equipment.operating_range[1] - equipment.operating_range[0]
        range_score = min(range_width * 100, 100)

        return 0.7 * efficiency_score + 0.3 * range_score

    def _score_reliability(self, equipment: EquipmentSpec) -> float:
        """可靠性评分"""
        # 基于可用率
        availability_score = equipment.availability * 100

        # 基于MTBF
        mtbf_score = min(equipment.mtbf / 1000, 100)

        # 基于设计寿命
        life_score = min(equipment.design_life / 0.5, 100)

        return 0.5 * availability_score + 0.3 * mtbf_score + 0.2 * life_score

    def _score_economy(self, equipment: EquipmentSpec) -> float:
        """经济性评分"""
        # 总拥有成本（简化计算）
        tco = (
            equipment.capital_cost +
            equipment.installation_cost +
            equipment.maintenance_cost * equipment.design_life
        )

        # 归一化（假设参考成本为10万/MW容量）
        ref_tco = equipment.rated_capacity * 100

        if ref_tco > 0:
            cost_ratio = tco / ref_tco
            score = max(0, 100 * (2 - cost_ratio))
        else:
            score = 50

        return min(100, score)

    def _score_technology(self, equipment: EquipmentSpec) -> float:
        """技术成熟度评分"""
        # TRL得分
        trl_score = equipment.technology_readiness / 9 * 100

        # 国产化率加分
        domestic_bonus = equipment.domestic_rate * 10

        return min(100, trl_score + domestic_bonus)

    def _score_adaptability(self, equipment: EquipmentSpec) -> float:
        """环境适应性评分"""
        score = 80.0

        # 海拔适应性
        if equipment.altitude_limit >= self.criteria.altitude_requirement:
            score += 10
        else:
            score -= 20

        # 温度适应性
        temp_low, temp_high = equipment.temp_range
        req_low, req_high = self.criteria.temp_requirement
        if temp_low <= req_low and temp_high >= req_high:
            score += 10

        return min(100, max(0, score))

    def _check_constraints(self, equipment: EquipmentSpec) -> bool:
        """检查约束条件"""
        # 预算约束
        total_cost = equipment.capital_cost + equipment.installation_cost
        if total_cost > self.criteria.max_budget:
            return False

        # 效率约束
        if equipment.rated_efficiency < self.criteria.min_efficiency:
            return False

        # 可用率约束
        if equipment.availability < self.criteria.min_availability:
            return False

        # 国产化率约束
        if equipment.domestic_rate < self.criteria.min_domestic_rate:
            return False

        # 海拔约束
        if equipment.altitude_limit < self.criteria.altitude_requirement:
            return False

        return True

    def select_best(
        self,
        category: EquipmentCategory,
        required_capacity: float = 1000.0
    ) -> Optional[EquipmentSpec]:
        """
        选择最佳设备

        Args:
            category: 设备类别
            required_capacity: 所需容量

        Returns:
            最佳设备规格
        """
        # 获取候选设备
        candidates = self.database.get_by_category(category)

        # 筛选容量匹配的
        candidates = [
            c for c in candidates
            if c.rated_capacity >= required_capacity * 0.9
        ]

        if not candidates:
            return None

        # 评估所有候选
        best_equipment = None
        best_score = 0

        for equipment in candidates:
            result = self.evaluate_equipment(equipment)
            self.evaluation_results[equipment.equipment_id] = result

            if result['constraints_satisfied'] and result['total_score'] > best_score:
                best_score = result['total_score']
                best_equipment = equipment

        if best_equipment:
            self.selections[category] = best_equipment

        return best_equipment

    def select_complete_set(
        self,
        required_capacity: float = 1000.0
    ) -> Dict[EquipmentCategory, EquipmentSpec]:
        """
        选择完整设备组合

        Args:
            required_capacity: 所需容量（MW）

        Returns:
            完整设备选型结果
        """
        categories = [
            EquipmentCategory.TURBINE,
            EquipmentCategory.GENERATOR,
            EquipmentCategory.GOVERNOR,
            EquipmentCategory.EXCITER,
        ]

        for category in categories:
            self.select_best(category, required_capacity)

        return self.selections

    def compare_options(
        self,
        category: EquipmentCategory
    ) -> List[Dict]:
        """
        对比同类设备

        Args:
            category: 设备类别

        Returns:
            对比结果列表
        """
        candidates = self.database.get_by_category(category)
        results = []

        for equipment in candidates:
            result = self.evaluate_equipment(equipment)
            result['equipment'] = equipment
            results.append(result)

        # 按综合得分排序
        results.sort(key=lambda x: x['total_score'], reverse=True)

        return results

    def generate_selection_report(self) -> str:
        """生成选型报告"""
        report = """
设备选型优化报告
================

1. 选型准则
"""
        for criterion, weight in self.criteria.weights.items():
            report += f"   - {criterion}: {weight*100:.0f}%\n"

        report += f"""
2. 约束条件
   - 最大预算: {self.criteria.max_budget}万元
   - 最低效率: {self.criteria.min_efficiency*100:.1f}%
   - 最低可用率: {self.criteria.min_availability*100:.1f}%
   - 最低国产化率: {self.criteria.min_domestic_rate*100:.0f}%
   - 海拔要求: {self.criteria.altitude_requirement}m

3. 选型结果
"""
        for category, equipment in self.selections.items():
            result = self.evaluation_results.get(equipment.equipment_id, {})
            report += f"""
   {category.value.upper()}
   - 选型: {equipment.name}
   - 制造商: {equipment.manufacturer}
   - 容量: {equipment.rated_capacity}
   - 效率: {equipment.rated_efficiency*100:.1f}%
   - 成本: {equipment.capital_cost}万元
   - 综合得分: {result.get('total_score', 0):.1f}
"""

        report += "\n4. 总投资估算\n"
        total_capital = sum(e.capital_cost for e in self.selections.values())
        total_install = sum(e.installation_cost for e in self.selections.values())
        report += f"   - 设备采购: {total_capital:.0f}万元\n"
        report += f"   - 安装调试: {total_install:.0f}万元\n"
        report += f"   - 合计: {total_capital + total_install:.0f}万元\n"

        return report
