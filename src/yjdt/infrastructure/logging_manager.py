# -*- coding: utf-8 -*-
"""
日志管理器 - Logging Manager

功能：
- 统一的日志配置初始化
- 文件日志（滚动）
- 控制台彩色输出
- 远程日志支持
- 性能日志
- 结构化日志

使用示例:
    from yjdt.infrastructure.logging_manager import configure_logging, get_logger

    # 初始化日志系统
    configure_logging(level="INFO", log_file="logs/yjdt.log")

    # 获取日志器
    logger = get_logger(__name__)
    logger.info("系统启动")
"""

import logging
import logging.handlers
import os
import sys
import time
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from functools import wraps
from pathlib import Path


# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


# ANSI颜色码
class Colors:
    """ANSI颜色码"""
    RESET = "\033[0m"
    BOLD = "\033[1m"

    # 前景色
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # 亮色
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # 背景色
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"


# 级别颜色映射
LEVEL_COLORS = {
    logging.DEBUG: Colors.CYAN,
    logging.INFO: Colors.GREEN,
    logging.WARNING: Colors.YELLOW,
    logging.ERROR: Colors.RED,
    logging.CRITICAL: Colors.BG_RED + Colors.WHITE,
}


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    def __init__(self, fmt: str = None, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and self._supports_color()

    def _supports_color(self) -> bool:
        """检查终端是否支持颜色"""
        # Windows命令行可能不支持
        if sys.platform == "win32":
            try:
                import colorama
                colorama.init()
                return True
            except ImportError:
                return os.environ.get("TERM") is not None
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 保存原始值
        original_msg = record.msg
        original_levelname = record.levelname

        if self.use_colors:
            # 添加颜色
            color = LEVEL_COLORS.get(record.levelno, Colors.RESET)
            record.levelname = f"{color}{record.levelname:8}{Colors.RESET}"

            # 对错误级别的消息也着色
            if record.levelno >= logging.ERROR:
                record.msg = f"{color}{record.msg}{Colors.RESET}"

        result = super().format(record)

        # 恢复原始值
        record.msg = original_msg
        record.levelname = original_levelname

        return result


class JsonFormatter(logging.Formatter):
    """JSON格式化器（用于结构化日志）"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化为JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加额外字段
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class PerformanceFilter(logging.Filter):
    """性能日志过滤器"""

    def __init__(self, min_duration_ms: float = 100):
        super().__init__()
        self.min_duration_ms = min_duration_ms

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤性能日志"""
        if hasattr(record, "duration_ms"):
            return record.duration_ms >= self.min_duration_ms
        return True


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

    # 文件日志
    file_enabled: bool = True
    file_path: str = "logs/yjdt.log"
    file_max_size_mb: int = 100
    file_backup_count: int = 10

    # 控制台
    console_enabled: bool = True
    console_colors: bool = True

    # JSON日志
    json_enabled: bool = False
    json_path: str = "logs/yjdt.json"

    # 性能日志
    performance_enabled: bool = False
    performance_threshold_ms: float = 100

    # 远程日志
    remote_enabled: bool = False
    remote_host: str = ""
    remote_port: int = 514


# 全局配置
_logging_configured = False
_root_logger_name = "yjdt"


def configure_logging(
    level: str = "INFO",
    log_file: str = None,
    console: bool = True,
    colors: bool = True,
    json_file: str = None,
    config: LoggingConfig = None,
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径
        console: 是否输出到控制台
        colors: 是否使用彩色输出
        json_file: JSON日志文件路径
        config: 完整配置对象
    """
    global _logging_configured

    if config is None:
        config = LoggingConfig(
            level=level,
            file_enabled=log_file is not None,
            file_path=log_file or "logs/yjdt.log",
            console_enabled=console,
            console_colors=colors,
            json_enabled=json_file is not None,
            json_path=json_file or "logs/yjdt.json",
        )

    # 获取或创建根日志器
    root_logger = logging.getLogger(_root_logger_name)
    root_logger.setLevel(LOG_LEVELS.get(config.level.upper(), logging.INFO))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    if config.console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(LOG_LEVELS.get(config.level.upper(), logging.INFO))

        if config.console_colors:
            formatter = ColoredFormatter(config.format, config.date_format)
        else:
            formatter = logging.Formatter(config.format, config.date_format)

        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 文件处理器
    if config.file_enabled:
        # 确保目录存在
        log_dir = Path(config.file_path).parent
        if log_dir and not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            config.file_path,
            maxBytes=config.file_max_size_mb * 1024 * 1024,
            backupCount=config.file_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(LOG_LEVELS.get(config.level.upper(), logging.INFO))
        file_handler.setFormatter(logging.Formatter(config.format, config.date_format))
        root_logger.addHandler(file_handler)

    # JSON日志处理器
    if config.json_enabled:
        json_dir = Path(config.json_path).parent
        if json_dir and not json_dir.exists():
            json_dir.mkdir(parents=True, exist_ok=True)

        json_handler = logging.handlers.RotatingFileHandler(
            config.json_path,
            maxBytes=config.file_max_size_mb * 1024 * 1024,
            backupCount=config.file_backup_count,
            encoding="utf-8",
        )
        json_handler.setLevel(LOG_LEVELS.get(config.level.upper(), logging.INFO))
        json_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(json_handler)

    # 性能日志过滤器
    if config.performance_enabled:
        perf_filter = PerformanceFilter(config.performance_threshold_ms)
        for handler in root_logger.handlers:
            handler.addFilter(perf_filter)

    _logging_configured = True

    root_logger.info(f"日志系统已初始化 - 级别: {config.level}")


def get_logger(name: str = None) -> logging.Logger:
    """
    获取日志器

    Args:
        name: 日志器名称（通常使用 __name__）

    Returns:
        日志器实例
    """
    global _logging_configured

    if not _logging_configured:
        # 使用默认配置
        configure_logging()

    if name:
        if not name.startswith(_root_logger_name):
            name = f"{_root_logger_name}.{name}"
        return logging.getLogger(name)
    else:
        return logging.getLogger(_root_logger_name)


def log_performance(func=None, threshold_ms: float = 100, level: str = "INFO"):
    """
    性能日志装饰器

    Args:
        func: 被装饰的函数
        threshold_ms: 记录阈值（毫秒）
        level: 日志级别

    Example:
        @log_performance(threshold_ms=50)
        def slow_function():
            time.sleep(0.1)
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            logger = get_logger(fn.__module__)
            start = time.perf_counter()

            try:
                result = fn(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000

                if elapsed_ms >= threshold_ms:
                    log_method = getattr(logger, level.lower(), logger.info)
                    log_method(
                        f"性能: {fn.__name__} 耗时 {elapsed_ms:.2f}ms",
                        extra={"duration_ms": elapsed_ms}
                    )

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


class LogContext:
    """
    日志上下文管理器

    Example:
        with LogContext(logger, "处理订单", order_id=12345):
            process_order()
    """

    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        self.logger.info(f"开始: {self.operation} [{context_str}]")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = (time.perf_counter() - self.start_time) * 1000

        if exc_type is not None:
            self.logger.error(
                f"失败: {self.operation} [{elapsed_ms:.2f}ms] - {exc_type.__name__}: {exc_val}"
            )
        else:
            self.logger.info(f"完成: {self.operation} [{elapsed_ms:.2f}ms]")

        return False


class StructuredLogger:
    """
    结构化日志器

    提供更丰富的日志记录方式

    Example:
        slog = StructuredLogger("my_module")
        slog.info("用户登录", user_id=123, ip="192.168.1.1")
    """

    def __init__(self, name: str):
        self.logger = get_logger(name)

    def _log(self, level: int, msg: str, **kwargs):
        """内部日志方法"""
        if kwargs:
            extra_str = " | " + " ".join(f"{k}={v}" for k, v in kwargs.items())
            msg = msg + extra_str
        self.logger.log(level, msg)

    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self._log(logging.CRITICAL, msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        """记录异常"""
        self.logger.exception(msg)


def create_audit_logger(name: str = "audit", log_file: str = "logs/audit.log") -> logging.Logger:
    """
    创建审计日志器

    用于记录安全相关的操作

    Args:
        name: 日志器名称
        log_file: 日志文件路径

    Returns:
        审计日志器
    """
    logger = logging.getLogger(f"{_root_logger_name}.{name}")
    logger.setLevel(logging.INFO)

    # 确保目录存在
    log_dir = Path(log_file).parent
    if log_dir and not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)

    # 文件处理器
    handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=90,  # 保留90天
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# 便捷函数
def debug(msg: str, *args, **kwargs):
    """记录DEBUG日志"""
    get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """记录INFO日志"""
    get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """记录WARNING日志"""
    get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """记录ERROR日志"""
    get_logger().error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """记录CRITICAL日志"""
    get_logger().critical(msg, *args, **kwargs)
