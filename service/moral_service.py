# -*- coding: utf-8 -*-
"""德育分统计业务层。"""

from dao import moral_dao, settings_dao, student_dao
from dao.classlog_dao import display_log_type


def list_scoreboard(order_by="student_no"):
    """order_by: student_no | score_desc"""
    if order_by not in ("student_no", "score_desc"):
        order_by = "student_no"
    return moral_dao.list_student_scoreboard(order_by=order_by)


def list_student_history(student_id):
    """某学生德育明细，附带展示字段。"""
    rows = moral_dao.list_by_student_id(student_id)
    result = []
    for row in rows:
        change = int(row.get("score_change") or 0)
        item = dict(row)
        item["score_display"] = f"+{change}" if change > 0 else str(change)
        item["log_type_display"] = display_log_type(
            row.get("log_type") or row.get("log_title"),
            row.get("type_remark"),
        ) or "—"
        item["reason_display"] = (row.get("reason") or "").strip() or "—"
        result.append(item)
    return result


def get_moral_base_default():
    return settings_dao.get_moral_base_default()


def set_moral_base_default(value, apply_to_all=False):
    """
    设置全体默认初始德育分。
    apply_to_all=True 时同步更新所有学生 moral_base。
    """
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError("初始德育分须为整数")
    if value < 0 or value > 9999:
        raise ValueError("初始德育分范围应为 0～9999")
    settings_dao.set_moral_base_default(value)
    if apply_to_all:
        student_dao.apply_moral_base_to_all(value)
    return value


def get_default_class_name():
    return settings_dao.get_default_class_name()


def set_default_class_name(name):
    return settings_dao.set_default_class_name(name)
