# -*- coding: utf-8 -*-
"""
YJDT数据导出器

支持多种数据格式的导出功能
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import json
import csv
import io


class ExportFormat(Enum):
    """导出格式"""
    CSV = "csv"
    JSON = "json"
    YAML = "yaml"
    EXCEL = "xlsx"
    HDF5 = "hdf5"
    PARQUET = "parquet"
    MARKDOWN = "md"


@dataclass
class ExportConfig:
    """导出配置"""
    format: ExportFormat = ExportFormat.CSV
    output_dir: str = "./exports"
    filename_prefix: str = "yjdt"
    include_timestamp: bool = True
    compression: Optional[str] = None  # gzip, zip, etc.
    encoding: str = "utf-8"


@dataclass
class ExportResult:
    """导出结果"""
    success: bool
    filepath: str
    format: ExportFormat
    records: int
    size_bytes: int
    timestamp: datetime
    error: Optional[str] = None


class DataExporter:
    """数据导出器基类"""

    def __init__(self, config: ExportConfig = None):
        self.config = config or ExportConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, name: str, ext: str) -> str:
        """生成文件名"""
        parts = [self.config.filename_prefix, name]
        if self.config.include_timestamp:
            parts.append(datetime.now().strftime("%Y%m%d_%H%M%S"))
        return "_".join(parts) + f".{ext}"

    def export_to_csv(self, data: List[Dict], filename: str) -> ExportResult:
        """导出为CSV"""
        if not data:
            return ExportResult(
                success=False, filepath="", format=ExportFormat.CSV,
                records=0, size_bytes=0, timestamp=datetime.now(),
                error="空数据"
            )

        filepath = self.output_dir / self._generate_filename(filename, "csv")

        try:
            with open(filepath, 'w', newline='', encoding=self.config.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            size = filepath.stat().st_size
            return ExportResult(
                success=True, filepath=str(filepath), format=ExportFormat.CSV,
                records=len(data), size_bytes=size, timestamp=datetime.now()
            )

        except Exception as e:
            return ExportResult(
                success=False, filepath=str(filepath), format=ExportFormat.CSV,
                records=0, size_bytes=0, timestamp=datetime.now(), error=str(e)
            )

    def export_to_json(self, data: Any, filename: str, indent: int = 2) -> ExportResult:
        """导出为JSON"""
        filepath = self.output_dir / self._generate_filename(filename, "json")

        try:
            with open(filepath, 'w', encoding=self.config.encoding) as f:
                json.dump(data, f, indent=indent, ensure_ascii=False, default=str)

            size = filepath.stat().st_size
            records = len(data) if isinstance(data, list) else 1

            return ExportResult(
                success=True, filepath=str(filepath), format=ExportFormat.JSON,
                records=records, size_bytes=size, timestamp=datetime.now()
            )

        except Exception as e:
            return ExportResult(
                success=False, filepath=str(filepath), format=ExportFormat.JSON,
                records=0, size_bytes=0, timestamp=datetime.now(), error=str(e)
            )

    def export_to_yaml(self, data: Any, filename: str) -> ExportResult:
        """导出为YAML"""
        filepath = self.output_dir / self._generate_filename(filename, "yaml")

        try:
            import yaml

            with open(filepath, 'w', encoding=self.config.encoding) as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

            size = filepath.stat().st_size
            records = len(data) if isinstance(data, list) else 1

            return ExportResult(
                success=True, filepath=str(filepath), format=ExportFormat.YAML,
                records=records, size_bytes=size, timestamp=datetime.now()
            )

        except ImportError:
            return ExportResult(
                success=False, filepath=str(filepath), format=ExportFormat.YAML,
                records=0, size_bytes=0, timestamp=datetime.now(),
                error="需要安装pyyaml: pip install pyyaml"
            )
        except Exception as e:
            return ExportResult(
                success=False, filepath=str(filepath), format=ExportFormat.YAML,
                records=0, size_bytes=0, timestamp=datetime.now(), error=str(e)
            )

    def export_to_markdown(self, data: List[Dict], filename: str, title: str = "") -> ExportResult:
        """导出为Markdown表格"""
        if not data:
            return ExportResult(
                success=False, filepath="", format=ExportFormat.MARKDOWN,
                records=0, size_bytes=0, timestamp=datetime.now(),
                error="空数据"
            )

        filepath = self.output_dir / self._generate_filename(filename, "md")

        try:
            headers = list(data[0].keys())

            lines = []
            if title:
                lines.append(f"# {title}\n")
                lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            # 表头
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

            # 数据行
            for row in data:
                values = [str(row.get(h, "")) for h in headers]
                lines.append("| " + " | ".join(values) + " |")

            content = "\n".join(lines)

            with open(filepath, 'w', encoding=self.config.encoding) as f:
                f.write(content)

            size = filepath.stat().st_size
            return ExportResult(
                success=True, filepath=str(filepath), format=ExportFormat.MARKDOWN,
                records=len(data), size_bytes=size, timestamp=datetime.now()
            )

        except Exception as e:
            return ExportResult(
                success=False, filepath=str(filepath), format=ExportFormat.MARKDOWN,
                records=0, size_bytes=0, timestamp=datetime.now(), error=str(e)
            )

    def export(
        self,
        data: Any,
        filename: str,
        format: ExportFormat = None
    ) -> ExportResult:
        """统一导出接口"""
        fmt = format or self.config.format

        if fmt == ExportFormat.CSV:
            if isinstance(data, list):
                return self.export_to_csv(data, filename)
            else:
                return self.export_to_csv([data], filename)

        elif fmt == ExportFormat.JSON:
            return self.export_to_json(data, filename)

        elif fmt == ExportFormat.YAML:
            return self.export_to_yaml(data, filename)

        elif fmt == ExportFormat.MARKDOWN:
            if isinstance(data, list):
                return self.export_to_markdown(data, filename)
            else:
                return self.export_to_markdown([data], filename)

        else:
            return ExportResult(
                success=False, filepath="", format=fmt,
                records=0, size_bytes=0, timestamp=datetime.now(),
                error=f"不支持的格式: {fmt}"
            )


class SimulationDataExporter(DataExporter):
    """仿真数据导出器"""

    def export_time_series(
        self,
        time_data: List[float],
        variables: Dict[str, List[float]],
        filename: str = "simulation_data"
    ) -> ExportResult:
        """导出时间序列数据"""
        data = []
        for i, t in enumerate(time_data):
            row = {"time": t}
            for var_name, values in variables.items():
                if i < len(values):
                    row[var_name] = values[i]
            data.append(row)

        return self.export_to_csv(data, filename)

    def export_scenario_results(
        self,
        scenario_id: str,
        metrics: Dict[str, float],
        status: str,
        filename: str = "scenario_results"
    ) -> ExportResult:
        """导出场景结果"""
        data = {
            "scenario_id": scenario_id,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "metrics": metrics
        }
        return self.export_to_json(data, filename)

    def export_batch_results(
        self,
        results: List[Dict],
        filename: str = "batch_results"
    ) -> ExportResult:
        """导出批量仿真结果"""
        # 展平嵌套结构
        flat_results = []
        for r in results:
            flat = {"scenario_id": r.get("scenario_id", "")}
            if "metrics" in r:
                for k, v in r["metrics"].items():
                    flat[f"metric_{k}"] = v
            flat["status"] = r.get("status", "")
            flat_results.append(flat)

        return self.export_to_csv(flat_results, filename)


class OptimizationDataExporter(DataExporter):
    """优化数据导出器"""

    def export_optimization_result(
        self,
        optimization_id: str,
        parameters: Dict[str, float],
        objective_value: float,
        iterations: int,
        filename: str = "optimization_result"
    ) -> ExportResult:
        """导出优化结果"""
        data = {
            "optimization_id": optimization_id,
            "timestamp": datetime.now().isoformat(),
            "objective_value": objective_value,
            "iterations": iterations,
            "optimal_parameters": parameters
        }
        return self.export_to_json(data, filename)

    def export_convergence_history(
        self,
        history: List[Dict],
        filename: str = "convergence_history"
    ) -> ExportResult:
        """导出收敛历史"""
        return self.export_to_csv(history, filename)

    def export_pareto_front(
        self,
        solutions: List[Dict],
        filename: str = "pareto_front"
    ) -> ExportResult:
        """导出Pareto前沿"""
        return self.export_to_csv(solutions, filename)

    def export_sensitivity_analysis(
        self,
        sensitivities: Dict[str, Dict],
        filename: str = "sensitivity"
    ) -> ExportResult:
        """导出敏感性分析结果"""
        # 转换为表格格式
        data = []
        for param, results in sensitivities.items():
            row = {"parameter": param}
            row.update(results)
            data.append(row)

        return self.export_to_csv(data, filename)


class SystemStateExporter(DataExporter):
    """系统状态导出器"""

    def export_odd_state(
        self,
        current_zone: str,
        parameters: Dict[str, float],
        violations: List[Dict],
        filename: str = "odd_state"
    ) -> ExportResult:
        """导出ODD状态"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "current_zone": current_zone,
            "parameters": parameters,
            "violations": violations
        }
        return self.export_to_json(data, filename)

    def export_station_status(
        self,
        stations: List[Dict],
        filename: str = "station_status"
    ) -> ExportResult:
        """导出电站状态"""
        return self.export_to_csv(stations, filename)

    def export_alarm_history(
        self,
        alarms: List[Dict],
        filename: str = "alarm_history"
    ) -> ExportResult:
        """导出告警历史"""
        return self.export_to_csv(alarms, filename)

    def export_full_snapshot(
        self,
        snapshot: Dict,
        filename: str = "system_snapshot"
    ) -> ExportResult:
        """导出完整系统快照"""
        return self.export_to_json(snapshot, filename)


class BulkExporter:
    """批量导出器"""

    def __init__(self, output_dir: str = "./exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sim_exporter = SimulationDataExporter(ExportConfig(output_dir=output_dir))
        self.opt_exporter = OptimizationDataExporter(ExportConfig(output_dir=output_dir))
        self.state_exporter = SystemStateExporter(ExportConfig(output_dir=output_dir))

    def export_all(
        self,
        simulation_data: Dict = None,
        optimization_data: Dict = None,
        system_state: Dict = None,
        formats: List[ExportFormat] = None
    ) -> Dict[str, List[ExportResult]]:
        """批量导出所有数据"""
        formats = formats or [ExportFormat.CSV, ExportFormat.JSON]
        results = {"simulation": [], "optimization": [], "system": []}

        # 仿真数据
        if simulation_data:
            for fmt in formats:
                result = self.sim_exporter.export(simulation_data, "simulation", fmt)
                results["simulation"].append(result)

        # 优化数据
        if optimization_data:
            for fmt in formats:
                result = self.opt_exporter.export(optimization_data, "optimization", fmt)
                results["optimization"].append(result)

        # 系统状态
        if system_state:
            for fmt in formats:
                result = self.state_exporter.export(system_state, "system_state", fmt)
                results["system"].append(result)

        return results

    def create_export_package(self, name: str = "yjdt_export") -> str:
        """创建导出压缩包"""
        import shutil

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        package_name = f"{name}_{timestamp}"
        package_path = self.output_dir / package_name

        # 创建临时目录
        package_path.mkdir(exist_ok=True)

        # 复制所有导出文件
        for f in self.output_dir.glob("*.*"):
            if f.is_file() and f.suffix in ['.csv', '.json', '.yaml', '.md']:
                shutil.copy(f, package_path / f.name)

        # 创建压缩包
        zip_path = shutil.make_archive(
            str(self.output_dir / package_name),
            'zip',
            package_path
        )

        # 清理临时目录
        shutil.rmtree(package_path)

        return zip_path


def create_exporter(
    export_type: str = "general",
    output_dir: str = "./exports"
) -> DataExporter:
    """创建数据导出器"""
    config = ExportConfig(output_dir=output_dir)

    if export_type == "simulation":
        return SimulationDataExporter(config)
    elif export_type == "optimization":
        return OptimizationDataExporter(config)
    elif export_type == "system":
        return SystemStateExporter(config)
    else:
        return DataExporter(config)
