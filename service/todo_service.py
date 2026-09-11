# -*- coding: utf-8 -*-
"""待办事项业务逻辑层。"""

from datetime import date

from dao import todo_dao
from dao.todo_dao import SCOPE_PERSONAL, SCOPE_CLASS
from utils.date_util import format_date, parse_date, today_str

__all__ = [
    "SCOPE_PERSONAL",
    "SCOPE_CLASS",
    "is_overdue",
    "status_display",
    "urgency_display",
    "scope_display",
    "add_todo",
    "change_status",
    "edit_todo",
    "remove_todo",
    "get_todo",
    "deadline_counts_in_range",
    "list_todos",
]


def _normalize_urgency(urgency):
    urgency = int(urgency) if urgency is not None else 0
    if urgency not in (0, 1):
        raise ValueError("紧急度只能是 0（普通）或 1（紧急）")
    return urgency


def _normalize_scope(scope):
    scope = int(scope) if scope is not None else SCOPE_PERSONAL
    if scope not in (SCOPE_PERSONAL, SCOPE_CLASS):
        raise ValueError("范围只能是 0（个人）或 1（班级）")
    return scope


def _resolve_complete_date(status, old_todo=None):
    """
    根据状态解析完成日期：
    - 未完成 → None
    - 新完成 → 今天
    - 本就已完成 → 保留原完成日期（无则今天）
    """
    status = int(status) if status is not None else 0
    if status != 1:
        return None
    if old_todo is not None and int(old_todo.get("status") or 0) == 1:
        kept = format_date(old_todo.get("complete_date"))
        return kept or today_str()
    return today_str()


def is_overdue(todo):
    """
    是否逾期：未完成且截止日期早于今天。
    已完成不算逾期。
    """
    if int(todo.get("status") or 0) == 1:
        return False
    deadline = parse_date(todo.get("deadline"))
    if not deadline:
        return False
    return deadline < date.today()


def status_display(todo):
    """状态展示文案：已完成 / 逾期 / 未完成。"""
    if int(todo.get("status") or 0) == 1:
        return "已完成"
    if is_overdue(todo):
        return "逾期"
    return "未完成"


def urgency_display(urgency):
    """紧急度展示文案。"""
    return "紧急" if int(urgency or 0) == 1 else "普通"


def scope_display(scope):
    """范围展示文案。"""
    return "班级" if int(scope or 0) == SCOPE_CLASS else "个人"


def add_todo(title, content=None, deadline=None, status=0, urgency=0,
             scope=SCOPE_PERSONAL):
    """新增待办。"""
    title = (title or "").strip()
    if not title:
        raise ValueError("标题不能为空")
    deadline_str = format_date(deadline) if deadline else None
    if deadline and not parse_date(deadline_str):
        raise ValueError("截止日期格式错误，应为 YYYY-MM-DD")
    if deadline_str == "":
        deadline_str = None
    status = int(status) if status is not None else 0
    if status not in (0, 1):
        raise ValueError("状态只能是 0（未完成）或 1（已完成）")
    urgency = _normalize_urgency(urgency)
    scope = _normalize_scope(scope)
    complete_date = _resolve_complete_date(status)
    return todo_dao.insert_todo(
        title, content, deadline_str, status, urgency, scope, complete_date
    )


def change_status(todo_id, status):
    """勾选/取消完成：同步写入或清空完成日期。"""
    if not todo_id:
        raise ValueError("待办 id 无效")
    status = int(status)
    if status not in (0, 1):
        raise ValueError("状态只能是 0（未完成）或 1（已完成）")
    old = todo_dao.get_todo_by_id(todo_id)
    complete_date = _resolve_complete_date(status, old)
    return todo_dao.update_todo_status(todo_id, status, complete_date)


def edit_todo(todo_id, title, content=None, deadline=None, status=0,
              urgency=0, scope=SCOPE_PERSONAL):
    """编辑待办（状态变更时同步完成日期）。"""
    if not todo_id:
        raise ValueError("待办 id 无效")
    title = (title or "").strip()
    if not title:
        raise ValueError("标题不能为空")
    deadline_str = format_date(deadline) if deadline else None
    if deadline and deadline_str and not parse_date(deadline_str):
        raise ValueError("截止日期格式错误，应为 YYYY-MM-DD")
    if deadline_str == "":
        deadline_str = None
    status = int(status) if status is not None else 0
    if status not in (0, 1):
        raise ValueError("状态只能是 0（未完成）或 1（已完成）")
    urgency = _normalize_urgency(urgency)
    scope = _normalize_scope(scope)
    old = todo_dao.get_todo_by_id(todo_id)
    complete_date = _resolve_complete_date(status, old)
    return todo_dao.update_todo(
        todo_id, title, content, deadline_str, status, urgency, scope,
        complete_date,
    )


def remove_todo(todo_id):
    """删除待办。"""
    if not todo_id:
        raise ValueError("待办 id 无效")
    return todo_dao.delete_todo(todo_id)


def get_todo(todo_id):
    """获取单条待办。"""
    return todo_dao.get_todo_by_id(todo_id)


def deadline_counts_in_range(start_date, end_date):
    """
    统计日期区间内各日待办截止数量。
    :return: dict[str, int]  key=YYYY-MM-DD
    """
    start_str = format_date(start_date) if start_date else None
    end_str = format_date(end_date) if end_date else None
    if start_str == "":
        start_str = None
    if end_str == "":
        end_str = None
    rows = todo_dao.list_todos_by_deadline_range(start_str, end_str)
    counts = {}
    for row in rows:
        key = format_date(row.get("deadline"))
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return counts


def list_todos(status=None, urgency=None, start_date=None, end_date=None,
               scope=None):
    """
    按状态、紧急度、范围、截止日期区间筛选。
    status: None/0/1
    urgency: None/0/1
    scope: None/0个人/1班级
    """
    start_str = format_date(start_date) if start_date else None
    end_str = format_date(end_date) if end_date else None
    if start_str == "":
        start_str = None
    if end_str == "":
        end_str = None

    if start_str or end_str:
        return todo_dao.list_todos_by_deadline_range(
            start_str, end_str, status, urgency, scope
        )

    return todo_dao.list_todos(
        status=status, urgency=urgency, scope=scope, order_by_deadline=True
    )
