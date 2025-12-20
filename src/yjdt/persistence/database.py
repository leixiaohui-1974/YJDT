# -*- coding: utf-8 -*-
"""
数据库连接管理 - Database Connection Management

功能：
- SQLite数据库连接
- 连接池管理
- 事务管理
- 数据库迁移
"""

import sqlite3
import threading
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from yjdt.persistence.models import TABLES, INDEXES

logger = logging.getLogger(__name__)


class Database(ABC):
    """数据库抽象基类"""

    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    def execute(self, sql: str, params: Tuple = None) -> Any:
        """执行SQL"""
        pass

    @abstractmethod
    def execute_many(self, sql: str, params_list: List[Tuple]) -> int:
        """批量执行SQL"""
        pass

    @abstractmethod
    def fetch_one(self, sql: str, params: Tuple = None) -> Optional[Dict]:
        """获取单条记录"""
        pass

    @abstractmethod
    def fetch_all(self, sql: str, params: Tuple = None) -> List[Dict]:
        """获取所有记录"""
        pass

    @abstractmethod
    def begin_transaction(self):
        """开始事务"""
        pass

    @abstractmethod
    def commit(self):
        """提交事务"""
        pass

    @abstractmethod
    def rollback(self):
        """回滚事务"""
        pass


class SQLiteDatabase(Database):
    """
    SQLite数据库实现

    特点：
    - 线程安全
    - 连接池（单连接）
    - 自动重连
    - WAL模式支持
    """

    def __init__(self, db_path: str = "yjdt_data.db", wal_mode: bool = True):
        self.db_path = db_path
        self.wal_mode = wal_mode

        self._connection: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()
        self._in_transaction = False

        # 统计
        self._stats = {
            "queries": 0,
            "inserts": 0,
            "updates": 0,
            "errors": 0,
        }

    def connect(self) -> bool:
        """建立连接"""
        try:
            with self._lock:
                if self._connection is not None:
                    return True

                # 确保目录存在
                db_dir = Path(self.db_path).parent
                if db_dir and not db_dir.exists():
                    db_dir.mkdir(parents=True, exist_ok=True)

                # 创建连接
                self._connection = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0,
                )

                # 配置连接
                self._connection.row_factory = sqlite3.Row
                self._connection.execute("PRAGMA foreign_keys = ON")

                if self.wal_mode:
                    self._connection.execute("PRAGMA journal_mode = WAL")
                    self._connection.execute("PRAGMA synchronous = NORMAL")

                logger.info(f"SQLite connected: {self.db_path}")
                return True

        except Exception as e:
            logger.error(f"SQLite connection failed: {e}")
            self._stats["errors"] += 1
            return False

    def disconnect(self):
        """断开连接"""
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
                logger.info("SQLite disconnected")

    def _ensure_connected(self):
        """确保已连接"""
        if self._connection is None:
            self.connect()

    def execute(self, sql: str, params: Tuple = None) -> Any:
        """执行SQL"""
        with self._lock:
            self._ensure_connected()

            try:
                cursor = self._connection.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                self._stats["queries"] += 1

                if not self._in_transaction:
                    self._connection.commit()

                return cursor

            except Exception as e:
                logger.error(f"SQL execute error: {e}, SQL: {sql}")
                self._stats["errors"] += 1
                if not self._in_transaction:
                    self._connection.rollback()
                raise

    def execute_many(self, sql: str, params_list: List[Tuple]) -> int:
        """批量执行SQL"""
        with self._lock:
            self._ensure_connected()

            try:
                cursor = self._connection.cursor()
                cursor.executemany(sql, params_list)

                self._stats["queries"] += len(params_list)

                if not self._in_transaction:
                    self._connection.commit()

                return cursor.rowcount

            except Exception as e:
                logger.error(f"SQL execute_many error: {e}")
                self._stats["errors"] += 1
                if not self._in_transaction:
                    self._connection.rollback()
                raise

    def fetch_one(self, sql: str, params: Tuple = None) -> Optional[Dict]:
        """获取单条记录"""
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def fetch_all(self, sql: str, params: Tuple = None) -> List[Dict]:
        """获取所有记录"""
        cursor = self.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def begin_transaction(self):
        """开始事务"""
        with self._lock:
            self._ensure_connected()
            self._in_transaction = True

    def commit(self):
        """提交事务"""
        with self._lock:
            if self._connection and self._in_transaction:
                self._connection.commit()
                self._in_transaction = False

    def rollback(self):
        """回滚事务"""
        with self._lock:
            if self._connection and self._in_transaction:
                self._connection.rollback()
                self._in_transaction = False

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        self.begin_transaction()
        try:
            yield
            self.commit()
        except Exception:
            self.rollback()
            raise

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self._stats.copy()

    def vacuum(self):
        """压缩数据库"""
        with self._lock:
            self._ensure_connected()
            self._connection.execute("VACUUM")

    def get_table_info(self, table_name: str) -> List[Dict]:
        """获取表信息"""
        return self.fetch_all(f"PRAGMA table_info({table_name})")

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        result = self.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return result is not None


class DatabaseManager:
    """
    数据库管理器

    功能：
    - 数据库初始化
    - 表创建和迁移
    - 数据备份和恢复
    - 数据清理
    """

    def __init__(self, database: Database = None):
        self.db = database or SQLiteDatabase()
        self._initialized = False

    def initialize(self) -> bool:
        """初始化数据库"""
        if self._initialized:
            return True

        try:
            # 连接数据库
            if not self.db.connect():
                return False

            # 创建表
            self._create_tables()

            # 创建索引
            self._create_indexes()

            self._initialized = True
            logger.info("Database initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    def _create_tables(self):
        """创建表"""
        for table_name, create_sql in TABLES.items():
            try:
                self.db.execute(create_sql)
                logger.debug(f"Table created/verified: {table_name}")
            except Exception as e:
                logger.error(f"Failed to create table {table_name}: {e}")
                raise

    def _create_indexes(self):
        """创建索引"""
        for index_name, create_sql in INDEXES.items():
            try:
                self.db.execute(create_sql)
                logger.debug(f"Index created/verified: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")

    def backup(self, backup_path: str) -> bool:
        """备份数据库"""
        if not isinstance(self.db, SQLiteDatabase):
            logger.warning("Backup only supported for SQLite")
            return False

        try:
            import shutil

            # 确保WAL检查点
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

            # 复制文件
            shutil.copy2(self.db.db_path, backup_path)

            logger.info(f"Database backed up to: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False

    def restore(self, backup_path: str) -> bool:
        """恢复数据库"""
        if not isinstance(self.db, SQLiteDatabase):
            logger.warning("Restore only supported for SQLite")
            return False

        try:
            import shutil

            # 断开连接
            self.db.disconnect()

            # 恢复文件
            shutil.copy2(backup_path, self.db.db_path)

            # 重新连接
            self.db.connect()

            logger.info(f"Database restored from: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        cutoff = datetime.now().isoformat()

        # 清理时间序列数据
        self.db.execute(
            """
            DELETE FROM time_series
            WHERE created_at < datetime('now', '-' || ? || ' days')
            AND storage_tier = 'realtime'
            """,
            (days,)
        )

        # 清理已确认的旧告警
        self.db.execute(
            """
            DELETE FROM alarms
            WHERE cleared = 1
            AND cleared_at < datetime('now', '-' || ? || ' days')
            """,
            (days,)
        )

        # 压缩数据库
        if isinstance(self.db, SQLiteDatabase):
            self.db.vacuum()

        logger.info(f"Cleaned up data older than {days} days")

    def get_database_stats(self) -> Dict:
        """获取数据库统计"""
        stats = {
            "tables": {},
            "total_records": 0,
        }

        tables = ["simulations", "scenarios", "time_series", "alarms", "configs", "events"]

        for table in tables:
            try:
                result = self.db.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                count = result["count"] if result else 0
                stats["tables"][table] = count
                stats["total_records"] += count
            except Exception:
                stats["tables"][table] = 0

        if isinstance(self.db, SQLiteDatabase):
            stats["db_stats"] = self.db.get_stats()

        return stats

    def shutdown(self):
        """关闭数据库"""
        if self.db:
            self.db.disconnect()
        self._initialized = False


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(db_path: str = "yjdt_data.db") -> DatabaseManager:
    """获取数据库管理器实例（单例）"""
    global _db_manager

    if _db_manager is None:
        db = SQLiteDatabase(db_path)
        _db_manager = DatabaseManager(db)
        _db_manager.initialize()

    return _db_manager


def close_database():
    """关闭数据库"""
    global _db_manager

    if _db_manager:
        _db_manager.shutdown()
        _db_manager = None
