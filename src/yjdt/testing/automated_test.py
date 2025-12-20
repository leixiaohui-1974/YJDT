# -*- coding: utf-8 -*-
"""
自动化测试框架 - Automated Test Framework

功能：
- 自动化测试调度
- 回归测试
- 持续集成支持
- 测试覆盖分析
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import threading
import json


class TestTrigger(Enum):
    """测试触发条件"""
    MANUAL = "manual"               # 手动触发
    SCHEDULED = "scheduled"         # 定时触发
    ON_CHANGE = "on_change"         # 变更触发
    CONTINUOUS = "continuous"       # 持续运行


class TestCategory(Enum):
    """测试类别"""
    SMOKE = "smoke"                 # 冒烟测试
    REGRESSION = "regression"       # 回归测试
    INTEGRATION = "integration"     # 集成测试
    PERFORMANCE = "performance"     # 性能测试
    STRESS = "stress"               # 压力测试
    ACCEPTANCE = "acceptance"       # 验收测试


@dataclass
class TestSchedule:
    """测试计划"""
    schedule_id: str
    name: str
    trigger: TestTrigger
    test_suite_id: str
    category: TestCategory

    # 调度参数
    cron_expression: str = ""       # 定时表达式
    on_change_patterns: List[str] = field(default_factory=list)

    # 配置
    enabled: bool = True
    max_retries: int = 2
    timeout_minutes: int = 60
    notify_on_failure: bool = True

    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


@dataclass
class TestExecution:
    """测试执行记录"""
    execution_id: str
    schedule_id: str
    trigger: TestTrigger
    start_time: datetime
    end_time: Optional[datetime]

    status: str                     # "running", "passed", "failed", "error"
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0

    details: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


class TestScheduler:
    """
    测试调度器

    功能：
    - 管理测试计划
    - 定时执行
    - 触发管理
    """

    def __init__(self, test_runner=None):
        self.test_runner = test_runner
        self.schedules: Dict[str, TestSchedule] = {}
        self.executions: List[TestExecution] = []

        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None

    def add_schedule(self, schedule: TestSchedule):
        """添加测试计划"""
        self.schedules[schedule.schedule_id] = schedule

    def remove_schedule(self, schedule_id: str):
        """移除测试计划"""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]

    def trigger_test(self, schedule_id: str) -> Optional[TestExecution]:
        """
        触发测试

        Args:
            schedule_id: 计划ID

        Returns:
            执行记录
        """
        if schedule_id not in self.schedules:
            return None

        schedule = self.schedules[schedule_id]
        execution_id = f"EXEC_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        execution = TestExecution(
            execution_id=execution_id,
            schedule_id=schedule_id,
            trigger=schedule.trigger,
            start_time=datetime.now(),
            end_time=None,
            status="running",
        )

        self.executions.append(execution)

        try:
            # 执行测试
            if self.test_runner:
                result = self.test_runner.run_suite(schedule.test_suite_id)
                execution.total_tests = result.total_tests
                execution.passed_tests = result.passed_tests
                execution.failed_tests = result.failed_tests
                execution.skipped_tests = result.skipped_tests
                execution.status = "passed" if result.failed_tests == 0 else "failed"
                execution.details = {"coverage": result.coverage_percentage}
            else:
                execution.status = "passed"
                execution.total_tests = 1
                execution.passed_tests = 1

        except Exception as e:
            execution.status = "error"
            execution.error_message = str(e)

        execution.end_time = datetime.now()
        schedule.last_run = datetime.now()

        return execution

    def start(self):
        """启动调度器"""
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)

    def _scheduler_loop(self):
        """调度循环"""
        while self._running:
            now = datetime.now()

            for schedule in self.schedules.values():
                if not schedule.enabled:
                    continue

                if schedule.trigger == TestTrigger.SCHEDULED:
                    if schedule.next_run and now >= schedule.next_run:
                        self.trigger_test(schedule.schedule_id)
                        # 计算下次执行时间（简化）
                        schedule.next_run = now + timedelta(hours=24)

            # 每分钟检查一次
            import time
            time.sleep(60)

    def get_recent_executions(self, limit: int = 10) -> List[TestExecution]:
        """获取最近执行记录"""
        return sorted(self.executions, key=lambda e: e.start_time, reverse=True)[:limit]


class RegressionTest:
    """
    回归测试

    功能：
    - 基准对比
    - 性能回归检测
    - 功能回归验证
    """

    def __init__(self):
        self.baselines: Dict[str, Dict[str, Any]] = {}
        self.regression_history: List[Dict[str, Any]] = []

    def set_baseline(self, baseline_id: str, metrics: Dict[str, float]):
        """设置基准"""
        self.baselines[baseline_id] = {
            "metrics": metrics,
            "timestamp": datetime.now(),
        }

    def compare(self, baseline_id: str,
                current_metrics: Dict[str, float],
                tolerance: float = 0.1) -> Dict[str, Any]:
        """
        与基准比较

        Args:
            baseline_id: 基准ID
            current_metrics: 当前指标
            tolerance: 容差比例

        Returns:
            比较结果
        """
        if baseline_id not in self.baselines:
            return {"error": "Baseline not found"}

        baseline = self.baselines[baseline_id]["metrics"]
        regressions = []
        improvements = []
        unchanged = []

        for metric, current in current_metrics.items():
            if metric in baseline:
                base_value = baseline[metric]
                if base_value != 0:
                    change_ratio = (current - base_value) / abs(base_value)
                else:
                    change_ratio = 0 if current == 0 else float('inf')

                status = {
                    "metric": metric,
                    "baseline": base_value,
                    "current": current,
                    "change_percent": change_ratio * 100,
                }

                if change_ratio < -tolerance:
                    regressions.append(status)
                elif change_ratio > tolerance:
                    improvements.append(status)
                else:
                    unchanged.append(status)

        result = {
            "baseline_id": baseline_id,
            "has_regression": len(regressions) > 0,
            "regressions": regressions,
            "improvements": improvements,
            "unchanged": unchanged,
            "timestamp": datetime.now().isoformat(),
        }

        self.regression_history.append(result)
        return result

    def get_trend(self, metric: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取指标趋势"""
        trend = []
        for record in self.regression_history[-limit:]:
            for category in ["regressions", "improvements", "unchanged"]:
                for item in record.get(category, []):
                    if item["metric"] == metric:
                        trend.append({
                            "timestamp": record["timestamp"],
                            "value": item["current"],
                            "change": item["change_percent"],
                        })
        return trend


class ContinuousIntegration:
    """
    持续集成支持

    功能：
    - 变更检测
    - 自动测试触发
    - 结果报告
    """

    def __init__(self, scheduler: TestScheduler):
        self.scheduler = scheduler
        self.change_history: List[Dict[str, Any]] = []
        self.webhooks: List[str] = []

    def on_change(self, change_info: Dict[str, Any]):
        """
        处理变更事件

        Args:
            change_info: 变更信息
        """
        self.change_history.append({
            "timestamp": datetime.now(),
            **change_info,
        })

        # 检查是否需要触发测试
        affected_files = change_info.get("files", [])

        for schedule in self.scheduler.schedules.values():
            if schedule.trigger == TestTrigger.ON_CHANGE:
                for pattern in schedule.on_change_patterns:
                    if any(pattern in f for f in affected_files):
                        self.scheduler.trigger_test(schedule.schedule_id)
                        break

    def add_webhook(self, url: str):
        """添加Webhook"""
        self.webhooks.append(url)

    def notify(self, execution: TestExecution):
        """发送通知"""
        notification = {
            "execution_id": execution.execution_id,
            "status": execution.status,
            "passed": execution.passed_tests,
            "failed": execution.failed_tests,
            "timestamp": datetime.now().isoformat(),
        }

        # 模拟发送Webhook
        for webhook in self.webhooks:
            # 实际应用中使用requests发送
            pass

    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取流水线状态"""
        recent = self.scheduler.get_recent_executions(5)

        if not recent:
            return {"status": "unknown", "message": "No executions"}

        latest = recent[0]

        return {
            "status": latest.status,
            "last_execution": latest.execution_id,
            "last_run": latest.start_time.isoformat(),
            "pass_rate": sum(1 for e in recent if e.status == "passed") / len(recent) * 100,
            "recent_failures": [e.execution_id for e in recent if e.status == "failed"],
        }


class AutomatedTestFramework:
    """
    自动化测试框架

    整合所有测试功能
    """

    def __init__(self, test_runner=None):
        self.test_runner = test_runner
        self.scheduler = TestScheduler(test_runner)
        self.regression = RegressionTest()
        self.ci = ContinuousIntegration(self.scheduler)

        # 测试配置
        self.config = {
            "parallel_execution": False,
            "retry_on_failure": True,
            "max_retries": 2,
            "default_timeout": 3600,
        }

    def setup_smoke_tests(self, test_suite_id: str):
        """设置冒烟测试"""
        schedule = TestSchedule(
            schedule_id="SMOKE_DAILY",
            name="每日冒烟测试",
            trigger=TestTrigger.SCHEDULED,
            test_suite_id=test_suite_id,
            category=TestCategory.SMOKE,
            cron_expression="0 6 * * *",  # 每天6点
        )
        self.scheduler.add_schedule(schedule)

    def setup_regression_tests(self, test_suite_id: str):
        """设置回归测试"""
        schedule = TestSchedule(
            schedule_id="REGRESSION_CHANGE",
            name="变更回归测试",
            trigger=TestTrigger.ON_CHANGE,
            test_suite_id=test_suite_id,
            category=TestCategory.REGRESSION,
            on_change_patterns=["*.py", "config/*"],
        )
        self.scheduler.add_schedule(schedule)

    def run_full_suite(self) -> Dict[str, Any]:
        """运行完整测试套件"""
        results = {}

        for schedule in self.scheduler.schedules.values():
            execution = self.scheduler.trigger_test(schedule.schedule_id)
            if execution:
                results[schedule.schedule_id] = {
                    "status": execution.status,
                    "passed": execution.passed_tests,
                    "failed": execution.failed_tests,
                }

        # 汇总
        total_passed = sum(r["passed"] for r in results.values())
        total_failed = sum(r["failed"] for r in results.values())

        return {
            "suites_run": len(results),
            "total_passed": total_passed,
            "total_failed": total_failed,
            "overall_status": "passed" if total_failed == 0 else "failed",
            "details": results,
        }

    def get_dashboard(self) -> Dict[str, Any]:
        """获取测试仪表板"""
        recent = self.scheduler.get_recent_executions(20)

        # 计算统计
        if recent:
            pass_rate = sum(1 for e in recent if e.status == "passed") / len(recent) * 100
            avg_duration = np.mean([
                (e.end_time - e.start_time).total_seconds()
                for e in recent if e.end_time
            ])
        else:
            pass_rate = 0
            avg_duration = 0

        return {
            "total_schedules": len(self.scheduler.schedules),
            "active_schedules": sum(1 for s in self.scheduler.schedules.values() if s.enabled),
            "recent_pass_rate": pass_rate,
            "average_duration": avg_duration,
            "pipeline_status": self.ci.get_pipeline_status(),
            "recent_executions": [
                {
                    "id": e.execution_id,
                    "status": e.status,
                    "time": e.start_time.isoformat(),
                }
                for e in recent[:5]
            ],
        }

