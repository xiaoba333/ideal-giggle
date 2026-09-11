# -*- coding: utf-8 -*-
"""应用设置表 DAO（键值对）。"""

from database.db_conn import execute_one, execute_update, execute_query

_SCHEMA_READY = False

KEY_MORAL_BASE_DEFAULT = "moral_base_default"
KEY_DEFAULT_CLASS_NAME = "default_class_name"

DEFAULT_MORAL_BASE = 100
DEFAULT_CLASS_NAME = "软件工程2506班"


def ensure_schema():
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    tables = execute_query(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='app_settings'"
    )
    if not tables:
        execute_update(
            """
            CREATE TABLE app_settings (
                setting_key   VARCHAR(64)  NOT NULL COMMENT '配置键',
                setting_value VARCHAR(255) DEFAULT NULL COMMENT '配置值',
                PRIMARY KEY (setting_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='应用配置'
            """
        )
    # 写入缺省项
    if get_raw(KEY_MORAL_BASE_DEFAULT) is None:
        set_value(KEY_MORAL_BASE_DEFAULT, str(DEFAULT_MORAL_BASE))
    if get_raw(KEY_DEFAULT_CLASS_NAME) is None:
        set_value(KEY_DEFAULT_CLASS_NAME, DEFAULT_CLASS_NAME)
    _SCHEMA_READY = True


def get_raw(key):
    row = execute_one(
        "SELECT setting_value FROM app_settings WHERE setting_key=%s", (key,)
    )
    if not row:
        return None
    return row.get("setting_value")


def set_value(key, value):
    execute_update(
        "INSERT INTO app_settings (setting_key, setting_value) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)",
        (key, None if value is None else str(value)),
    )


def get_moral_base_default():
    ensure_schema()
    raw = get_raw(KEY_MORAL_BASE_DEFAULT)
    try:
        return int(raw) if raw is not None else DEFAULT_MORAL_BASE
    except (TypeError, ValueError):
        return DEFAULT_MORAL_BASE


def set_moral_base_default(value: int):
    ensure_schema()
    value = int(value)
    set_value(KEY_MORAL_BASE_DEFAULT, str(value))
    return value


def get_default_class_name():
    ensure_schema()
    raw = get_raw(KEY_DEFAULT_CLASS_NAME)
    text = (raw or "").strip()
    return text or DEFAULT_CLASS_NAME


def set_default_class_name(name: str):
    ensure_schema()
    name = (name or "").strip() or DEFAULT_CLASS_NAME
    set_value(KEY_DEFAULT_CLASS_NAME, name)
    return name
