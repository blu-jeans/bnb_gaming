# -*- coding: utf-8 -*-
"""
@author hyq
@version 2026-07-13
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator

class DBManager:
    """
    SQLite 数据库连接管理器
    """
    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def connection(self, write: bool = False) -> Generator[sqlite3.Connection, None, None]:
        """
        连接上下文管理器，自动处理提交、回滚与关闭，强制启用外键约束，并配置自定义 Row Factory
        """
        conn = sqlite3.connect(self.db_path)
        try:
            # 强制启用外键约束
            conn.execute("PRAGMA foreign_keys = ON;")
            # 配置行映射为 dict-like 属性
            conn.row_factory = self.dict_like_row_factory
            if write:
                conn.isolation_level = None
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def dict_like_row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
        """
        Row Factory，将查询列映射为支持 dict 键、索引和属性访问的对象
        """
        class Row(dict):
            """
            自定义 Row 类，继承自 dict，支持属性访问、键访问和索引访问
            """
            def __init__(self, keys: list[str], values: tuple):
                super().__init__()
                object.__setattr__(self, '_keys', keys)
                object.__setattr__(self, '_values', values)
                for k, v in zip(keys, values):
                    self[k] = v

            def __getitem__(self, item):
                if isinstance(item, int):
                    return self._values[item]
                return super().__getitem__(item)

            def __getattr__(self, name: str):
                try:
                    return self[name]
                except KeyError:
                    raise AttributeError(f"'Row' object has no attribute '{name}'")

            def __setattr__(self, name: str, value):
                if name.startswith('_'):
                    super().__setattr__(name, value)
                else:
                    self[name] = value

        keys = [col[0] for col in cursor.description]
        return Row(keys, row)
