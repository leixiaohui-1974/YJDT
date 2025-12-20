# -*- coding: utf-8 -*-
"""
性能分析管理器 - Profiling Manager

功能：
- CPU性能分析 (cProfile)
- 内存分析
- 函数执行时间跟踪
- 性能指标收集
- 性能报告生成

使用示例:
    from yjdt.infrastructure.profiling_manager import (
        profile_function,
        PerformanceMonitor,
        start_profiling,
        stop_profiling,
    )

    # 装饰器方式
    @profile_function
    def my_function():
        ...

    # 上下文管理器方式
    with PerformanceMonitor("模块名称") as pm:
        ...
        pm.checkpoint("步骤1")
        ...
"""

import cProfile
import pstats
import io
import time
import sys
import tracemalloc
import threading
import functools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path
import json


@dataclass
class PerformanceMetrics:
    """性能指标"""
    name: str
    start_time: float = 0
    end_time: float = 0
    duration_ms: float = 0
    cpu_time_ms: float = 0
    memory_start_mb: float = 0
    memory_end_mb: float = 0
    memory_peak_mb: float = 0
    memory_delta_mb: float = 0
    call_count: int = 0
    checkpoints: List[Tuple[str, float]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "cpu_time_ms": self.cpu_time_ms,
            "memory_start_mb": self.memory_start_mb,
            "memory_end_mb": self.memory_end_mb,
            "memory_peak_mb": self.memory_peak_mb,
            "memory_delta_mb": self.memory_delta_mb,
            "call_count": self.call_count,
            "checkpoints": self.checkpoints,
            "metadata": self.metadata,
        }


class PerformanceMonitor:
    """
    性能监控器

    用于监控代码块的执行性能

    Example:
        with PerformanceMonitor("数据处理") as pm:
            load_data()
            pm.checkpoint("数据加载完成")
            process_data()
            pm.checkpoint("数据处理完成")
        print(pm.metrics.duration_ms)
    """

    def __init__(self, name: str, track_memory: bool = True):
        self.name = name
        self.track_memory = track_memory
        self.metrics = PerformanceMetrics(name=name)
        self._start_cpu_time = 0
        self._checkpoint_time = 0

    def __enter__(self) -> 'PerformanceMonitor':
        # 记录开始时间
        self.metrics.start_time = time.perf_counter()
        self._start_cpu_time = time.process_time()
        self._checkpoint_time = self.metrics.start_time

        # 内存跟踪
        if self.track_memory:
            tracemalloc.start()
            snapshot = tracemalloc.take_snapshot()
            stats = snapshot.statistics("filename")
            self.metrics.memory_start_mb = sum(s.size for s in stats) / (1024 * 1024)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 记录结束时间
        self.metrics.end_time = time.perf_counter()
        self.metrics.duration_ms = (self.metrics.end_time - self.metrics.start_time) * 1000
        self.metrics.cpu_time_ms = (time.process_time() - self._start_cpu_time) * 1000

        # 内存统计
        if self.track_memory:
            snapshot = tracemalloc.take_snapshot()
            stats = snapshot.statistics("filename")
            self.metrics.memory_end_mb = sum(s.size for s in stats) / (1024 * 1024)

            current, peak = tracemalloc.get_traced_memory()
            self.metrics.memory_peak_mb = peak / (1024 * 1024)
            self.metrics.memory_delta_mb = self.metrics.memory_end_mb - self.metrics.memory_start_mb

            tracemalloc.stop()

        return False

    def checkpoint(self, name: str):
        """记录检查点"""
        current_time = time.perf_counter()
        elapsed = (current_time - self._checkpoint_time) * 1000
        self.metrics.checkpoints.append((name, elapsed))
        self._checkpoint_time = current_time


class FunctionProfiler:
    """
    函数性能分析器

    跟踪函数调用的性能统计
    """

    def __init__(self):
        self._stats: Dict[str, PerformanceMetrics] = {}
        self._lock = threading.Lock()

    def record(self, func_name: str, duration_ms: float, memory_delta_mb: float = 0):
        """记录函数执行"""
        with self._lock:
            if func_name not in self._stats:
                self._stats[func_name] = PerformanceMetrics(name=func_name)

            metrics = self._stats[func_name]
            metrics.call_count += 1
            metrics.duration_ms += duration_ms
            metrics.memory_delta_mb += memory_delta_mb

    def get_stats(self) -> Dict[str, Dict]:
        """获取统计"""
        with self._lock:
            return {
                name: {
                    "call_count": m.call_count,
                    "total_duration_ms": m.duration_ms,
                    "avg_duration_ms": m.duration_ms / m.call_count if m.call_count > 0 else 0,
                    "memory_delta_mb": m.memory_delta_mb,
                }
                for name, m in self._stats.items()
            }

    def get_top_functions(self, n: int = 10, sort_by: str = "total_duration_ms") -> List[Dict]:
        """获取耗时最长的函数"""
        stats = self.get_stats()
        sorted_funcs = sorted(
            stats.items(),
            key=lambda x: x[1].get(sort_by, 0),
            reverse=True
        )
        return [{"name": name, **data} for name, data in sorted_funcs[:n]]

    def reset(self):
        """重置统计"""
        with self._lock:
            self._stats.clear()


# 全局分析器实例
_function_profiler = FunctionProfiler()
_active_profile: Optional[cProfile.Profile] = None
_profile_enabled = False


def profile_function(func: Callable = None, *, track_memory: bool = False, threshold_ms: float = 0):
    """
    函数性能分析装饰器

    Args:
        func: 被装饰的函数
        track_memory: 是否跟踪内存
        threshold_ms: 只记录超过此阈值的调用

    Example:
        @profile_function
        def slow_function():
            time.sleep(0.1)

        @profile_function(track_memory=True, threshold_ms=50)
        def another_function():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            memory_start = 0

            if track_memory:
                tracemalloc.start()
                current, _ = tracemalloc.get_traced_memory()
                memory_start = current

            try:
                result = fn(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                memory_delta = 0

                if track_memory:
                    current, _ = tracemalloc.get_traced_memory()
                    memory_delta = (current - memory_start) / (1024 * 1024)
                    tracemalloc.stop()

                if duration_ms >= threshold_ms:
                    func_name = f"{fn.__module__}.{fn.__qualname__}"
                    _function_profiler.record(func_name, duration_ms, memory_delta)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def start_profiling():
    """开始CPU性能分析"""
    global _active_profile, _profile_enabled

    if _active_profile is None:
        _active_profile = cProfile.Profile()

    _active_profile.enable()
    _profile_enabled = True


def stop_profiling() -> str:
    """
    停止CPU性能分析

    Returns:
        性能分析报告字符串
    """
    global _active_profile, _profile_enabled

    if _active_profile is None or not _profile_enabled:
        return "No active profiling session"

    _active_profile.disable()
    _profile_enabled = False

    # 生成报告
    stream = io.StringIO()
    stats = pstats.Stats(_active_profile, stream=stream)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(30)

    return stream.getvalue()


def get_profile_stats() -> Optional[pstats.Stats]:
    """获取性能分析统计对象"""
    if _active_profile is None:
        return None
    return pstats.Stats(_active_profile)


def save_profile(filepath: str):
    """保存性能分析结果"""
    global _active_profile

    if _active_profile is None:
        return

    _active_profile.dump_stats(filepath)


class PerformanceCollector:
    """
    性能数据收集器

    持续收集系统性能指标
    """

    def __init__(self):
        self._metrics_history: List[Dict] = []
        self._start_time = time.time()
        self._lock = threading.Lock()

        # 采集配置
        self._collection_interval = 1.0  # 秒
        self._max_history = 3600  # 最多保存1小时的数据

    def collect_system_metrics(self) -> Dict:
        """收集系统指标"""
        import os

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self._start_time,
        }

        # 进程内存
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            metrics["memory_mb"] = usage.ru_maxrss / 1024  # macOS返回字节，Linux返回KB
            metrics["user_time_s"] = usage.ru_utime
            metrics["system_time_s"] = usage.ru_stime
        except ImportError:
            pass

        # Python内存
        try:
            import gc
            metrics["gc_objects"] = len(gc.get_objects())
            metrics["gc_collections"] = gc.get_stats()
        except Exception:
            pass

        # 线程数
        metrics["thread_count"] = threading.active_count()

        return metrics

    def record(self, metrics: Dict):
        """记录指标"""
        with self._lock:
            self._metrics_history.append(metrics)

            # 限制历史大小
            if len(self._metrics_history) > self._max_history:
                self._metrics_history = self._metrics_history[-self._max_history:]

    def get_history(self, limit: int = 100) -> List[Dict]:
        """获取历史指标"""
        with self._lock:
            return self._metrics_history[-limit:]

    def get_summary(self) -> Dict:
        """获取摘要统计"""
        with self._lock:
            if not self._metrics_history:
                return {}

            memory_values = [m.get("memory_mb", 0) for m in self._metrics_history if "memory_mb" in m]

            return {
                "total_records": len(self._metrics_history),
                "uptime_seconds": time.time() - self._start_time,
                "memory_avg_mb": sum(memory_values) / len(memory_values) if memory_values else 0,
                "memory_max_mb": max(memory_values) if memory_values else 0,
                "memory_min_mb": min(memory_values) if memory_values else 0,
            }


class PerformanceReport:
    """
    性能报告生成器
    """

    def __init__(self):
        self.function_profiler = _function_profiler
        self.collector = PerformanceCollector()

    def generate_report(self, format: str = "text") -> str:
        """
        生成性能报告

        Args:
            format: 报告格式 (text, json, html)

        Returns:
            报告内容
        """
        data = {
            "generated_at": datetime.now().isoformat(),
            "function_stats": self.function_profiler.get_stats(),
            "top_functions": self.function_profiler.get_top_functions(20),
            "system_summary": self.collector.get_summary(),
        }

        if format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)

        elif format == "html":
            return self._generate_html_report(data)

        else:
            return self._generate_text_report(data)

    def _generate_text_report(self, data: Dict) -> str:
        """生成文本报告"""
        lines = [
            "=" * 60,
            "YJDT 性能分析报告",
            f"生成时间: {data['generated_at']}",
            "=" * 60,
            "",
            "系统摘要:",
            "-" * 40,
        ]

        summary = data.get("system_summary", {})
        lines.append(f"  运行时间: {summary.get('uptime_seconds', 0):.2f} 秒")
        lines.append(f"  记录数量: {summary.get('total_records', 0)}")
        lines.append(f"  平均内存: {summary.get('memory_avg_mb', 0):.2f} MB")
        lines.append(f"  最大内存: {summary.get('memory_max_mb', 0):.2f} MB")

        lines.extend([
            "",
            "耗时最长的函数 (Top 20):",
            "-" * 40,
        ])

        for func in data.get("top_functions", []):
            lines.append(
                f"  {func['name']}: "
                f"{func['total_duration_ms']:.2f}ms 总计, "
                f"{func['avg_duration_ms']:.2f}ms 平均, "
                f"{func['call_count']} 次调用"
            )

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _generate_html_report(self, data: Dict) -> str:
        """生成HTML报告"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>YJDT 性能报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>YJDT 性能分析报告</h1>
    <p>生成时间: {generated_at}</p>

    <h2>系统摘要</h2>
    <table>
        <tr><th>指标</th><th>值</th></tr>
        <tr><td>运行时间</td><td>{uptime:.2f} 秒</td></tr>
        <tr><td>平均内存</td><td>{avg_mem:.2f} MB</td></tr>
        <tr><td>最大内存</td><td>{max_mem:.2f} MB</td></tr>
    </table>

    <h2>耗时最长的函数</h2>
    <table>
        <tr>
            <th>函数名</th>
            <th>总耗时 (ms)</th>
            <th>平均耗时 (ms)</th>
            <th>调用次数</th>
        </tr>
        {func_rows}
    </table>
</body>
</html>
        """

        summary = data.get("system_summary", {})
        func_rows = "\n".join(
            f"<tr><td>{f['name']}</td><td>{f['total_duration_ms']:.2f}</td>"
            f"<td>{f['avg_duration_ms']:.2f}</td><td>{f['call_count']}</td></tr>"
            for f in data.get("top_functions", [])
        )

        return html.format(
            generated_at=data["generated_at"],
            uptime=summary.get("uptime_seconds", 0),
            avg_mem=summary.get("memory_avg_mb", 0),
            max_mem=summary.get("memory_max_mb", 0),
            func_rows=func_rows,
        )

    def save_report(self, filepath: str, format: str = "text"):
        """保存报告到文件"""
        report = self.generate_report(format)

        # 确保目录存在
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)


# 便捷函数
def get_function_stats() -> Dict[str, Dict]:
    """获取函数性能统计"""
    return _function_profiler.get_stats()


def get_top_functions(n: int = 10) -> List[Dict]:
    """获取耗时最长的函数"""
    return _function_profiler.get_top_functions(n)


def reset_profiling():
    """重置所有性能统计"""
    global _active_profile
    _function_profiler.reset()
    _active_profile = None
