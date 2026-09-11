# -*- coding: utf-8 -*-
"""
MySQL 连接封装：连接池 + 通用查询执行。
使用 pymysql + DBUtils，统一异常处理与资源关闭。
"""

import pymysql
from dbutils.pooled_db import PooledDB
from pymysql.cursors import DictCursor

# ---------- 数据库配置（按本机 Docker MySQL 修改） ----------
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "xiaoba",
    "password": "333",
    "database": "class_manager",
    "charset": "utf8mb4",
}

_pool = None


def get_pool():
    """获取全局连接池（懒加载单例）。"""
    global _pool
    if _pool is None:
        try:
            _pool = PooledDB(
                creator=pymysql,
                maxconnections=10,
                mincached=2,
                maxcached=5,
                blocking=True,
                ping=1,
                cursorclass=DictCursor,
                **DB_CONFIG,
            )
        except Exception as e:
            print(f"[DB错误] 创建连接池失败: {e}")
            raise
    return _pool


def get_connection():
    """从连接池获取一条连接。"""
    try:
        return get_pool().connection()
    except Exception as e:
        print(f"[DB错误] 获取数据库连接失败: {e}")
        raise


def execute_query(sql, params=None):
    """
    执行查询 SQL，返回字典列表。
    :param sql: 参数化 SQL
    :param params: 参数元组/列表
    :return: list[dict]
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    except Exception as e:
        print(f"[DB错误] 查询失败: {e}\nSQL: {sql}\n参数: {params}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def execute_one(sql, params=None):
    """
    执行查询 SQL，返回单条记录（dict 或 None）。
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        return cursor.fetchone()
    except Exception as e:
        print(f"[DB错误] 单条查询失败: {e}\nSQL: {sql}\n参数: {params}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def execute_update(sql, params=None):
    """
    执行增删改 SQL，返回受影响行数。
    插入时可通过 lastrowid 获取自增 id（本函数返回 (rowcount, lastrowid)）。
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        rowcount = cursor.execute(sql, params or ())
        conn.commit()
        return rowcount, cursor.lastrowid
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB错误] 更新失败: {e}\nSQL: {sql}\n参数: {params}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def close_pool():
    """关闭全局连接池，安全退出前调用。"""
    global _pool
    if _pool is None:
        return
    try:
        _pool.close()
    except Exception as e:
        print(f"[DB错误] 关闭连接池失败: {e}")
    finally:
        _pool = None
