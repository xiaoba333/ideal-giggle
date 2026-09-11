# -*- coding: utf-8 -*-
"""待办事项表 DAO。"""

from database.db_conn import execute_query, execute_one, execute_update

_SCHEMA_READY = False

# 范围：0个人 1班级
SCOPE_PERSONAL = 0
SCOPE_CLASS = 1


def ensure_schema():
    """补齐 complete_date / scope 等字段（幂等）。"""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    cols = execute_query(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='todo_list'"
    )
    names = {c["COLUMN_NAME"] for c in (cols or [])}
    if names and "complete_date" not in names:
        execute_update(
            "ALTER TABLE todo_list ADD COLUMN complete_date DATE "
            "DEFAULT NULL COMMENT '实际完成日期 YYYY-MM-DD' AFTER urgency"
        )
        execute_update(
            "UPDATE todo_list SET complete_date=DATE(create_time) "
            "WHERE status=1 AND complete_date IS NULL"
        )
    # 重新读列（可能刚加了 complete_date）
    cols = execute_query(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='todo_list'"
    )
    names = {c["COLUMN_NAME"] for c in (cols or [])}
    if names and "scope" not in names:
        # 插在 urgency 后；若已有 complete_date 则放其前
        after = "urgency"
        execute_update(
            f"ALTER TABLE todo_list ADD COLUMN scope TINYINT NOT NULL "
            f"DEFAULT 0 COMMENT '范围：0个人 1班级' AFTER {after}"
        )
        execute_update(
            "UPDATE todo_list SET scope=0 WHERE scope IS NULL"
        )
    _SCHEMA_READY = True


def insert_todo(title, content=None, deadline=None, status=0, urgency=0,
                scope=SCOPE_PERSONAL, complete_date=None):
    """新增待办，返回新记录 id。"""
    ensure_schema()
    sql = (
        "INSERT INTO todo_list "
        "(title, content, deadline, status, urgency, scope, complete_date) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    )
    params = (title, content, deadline, status, urgency, scope, complete_date)
    _, last_id = execute_update(sql, params)
    return last_id


def update_todo_status(todo_id, status, complete_date=None):
    """修改完成状态与完成日期，返回受影响行数。"""
    ensure_schema()
    sql = "UPDATE todo_list SET status=%s, complete_date=%s WHERE id=%s"
    rowcount, _ = execute_update(sql, (status, complete_date, todo_id))
    return rowcount


def update_todo(todo_id, title, content=None, deadline=None, status=0,
                urgency=0, scope=SCOPE_PERSONAL, complete_date=None):
    """更新待办全部字段，返回受影响行数。"""
    ensure_schema()
    sql = (
        "UPDATE todo_list SET title=%s, content=%s, deadline=%s, "
        "status=%s, urgency=%s, scope=%s, complete_date=%s WHERE id=%s"
    )
    params = (
        title, content, deadline, status, urgency, scope, complete_date, todo_id
    )
    rowcount, _ = execute_update(sql, params)
    return rowcount


def delete_todo(todo_id):
    """删除待办，返回受影响行数。"""
    ensure_schema()
    sql = "DELETE FROM todo_list WHERE id=%s"
    rowcount, _ = execute_update(sql, (todo_id,))
    return rowcount


def get_todo_by_id(todo_id):
    """按 id 查询单条待办。"""
    ensure_schema()
    sql = "SELECT * FROM todo_list WHERE id=%s"
    return execute_one(sql, (todo_id,))


def list_todos(status=None, urgency=None, scope=None, order_by_deadline=True):
    """
    查询待办列表。
    :param status: None=全部，0=未完成，1=已完成
    :param urgency: None=全部，0=普通，1=紧急
    :param scope: None=全部，0=个人，1=班级
    :param order_by_deadline: True 按截止日期升序（空日期靠后）
    """
    ensure_schema()
    conditions = []
    params = []
    if status is not None:
        conditions.append("status=%s")
        params.append(status)
    if urgency is not None:
        conditions.append("urgency=%s")
        params.append(urgency)
    if scope is not None:
        conditions.append("scope=%s")
        params.append(scope)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    if order_by_deadline:
        order = (
            "ORDER BY urgency DESC, (deadline IS NULL) ASC, "
            "deadline ASC, id DESC"
        )
    else:
        order = "ORDER BY create_time DESC"

    sql = f"SELECT * FROM todo_list {where} {order}"
    return execute_query(sql, tuple(params) if params else None)


def list_todos_by_deadline_range(start_date=None, end_date=None,
                                 status=None, urgency=None, scope=None):
    """按截止日期区间筛选（含边界）。"""
    ensure_schema()
    conditions = []
    params = []
    if start_date:
        conditions.append("deadline >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("deadline <= %s")
        params.append(end_date)
    if status is not None:
        conditions.append("status=%s")
        params.append(status)
    if urgency is not None:
        conditions.append("urgency=%s")
        params.append(urgency)
    if scope is not None:
        conditions.append("scope=%s")
        params.append(scope)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = (
        f"SELECT * FROM todo_list {where} "
        "ORDER BY urgency DESC, (deadline IS NULL) ASC, deadline ASC, id DESC"
    )
    return execute_query(sql, tuple(params) if params else None)
