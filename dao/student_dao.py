# -*- coding: utf-8 -*-
"""学生表 DAO：增删改查、模糊搜索、德育基础分 / 班级。"""

from database.db_conn import execute_query, execute_one, execute_update
from dao import settings_dao

_SCHEMA_READY = False


def ensure_schema():
    """补齐 moral_base / class_name（幂等）。"""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    settings_dao.ensure_schema()
    cols = execute_query(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='student'"
    )
    names = {c["COLUMN_NAME"] for c in cols}
    if "moral_base" not in names:
        default_base = settings_dao.get_moral_base_default()
        execute_update(
            f"ALTER TABLE student ADD COLUMN moral_base INT NOT NULL "
            f"DEFAULT {int(default_base)} COMMENT '个人初始德育分'"
        )
    if "class_name" not in names:
        execute_update(
            "ALTER TABLE student ADD COLUMN class_name VARCHAR(50) "
            "DEFAULT NULL COMMENT '班级名称'"
        )
    _SCHEMA_READY = True


def insert_student(
    student_no,
    name,
    gender=None,
    phone=None,
    student_id=None,
    moral_base=None,
    class_name=None,
):
    """新增学生，返回新记录 id。"""
    ensure_schema()
    if moral_base is None:
        moral_base = settings_dao.get_moral_base_default()
    else:
        moral_base = int(moral_base)
    class_name = (class_name or "").strip() or None
    if student_id is not None:
        sql = (
            "INSERT INTO student "
            "(id, student_no, name, gender, phone, moral_base, class_name) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        )
        params = (
            student_id, student_no, name, gender, phone, moral_base, class_name,
        )
        execute_update(sql, params)
        return student_id
    sql = (
        "INSERT INTO student "
        "(student_no, name, gender, phone, moral_base, class_name) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )
    params = (student_no, name, gender, phone, moral_base, class_name)
    _, last_id = execute_update(sql, params)
    return last_id


def update_student(
    student_id,
    student_no,
    name,
    gender=None,
    phone=None,
    moral_base=None,
    class_name=None,
):
    """按 id 更新学生信息，返回受影响行数。"""
    ensure_schema()
    # 保留未传入的德育/班级字段
    current = get_student_by_id(student_id) or {}
    if moral_base is None:
        moral_base = current.get("moral_base")
        if moral_base is None:
            moral_base = settings_dao.get_moral_base_default()
    else:
        moral_base = int(moral_base)
    if class_name is None:
        class_name = current.get("class_name")
    else:
        class_name = (class_name or "").strip() or None
    sql = (
        "UPDATE student SET student_no=%s, name=%s, gender=%s, phone=%s, "
        "moral_base=%s, class_name=%s WHERE id=%s"
    )
    params = (
        student_no, name, gender, phone, moral_base, class_name, student_id,
    )
    rowcount, _ = execute_update(sql, params)
    return rowcount


def update_moral_base(student_id, moral_base: int):
    ensure_schema()
    rowcount, _ = execute_update(
        "UPDATE student SET moral_base=%s WHERE id=%s",
        (int(moral_base), student_id),
    )
    return rowcount


def apply_moral_base_to_all(moral_base: int):
    """将全体学生初始德育分设为同一值。"""
    ensure_schema()
    rowcount, _ = execute_update(
        "UPDATE student SET moral_base=%s", (int(moral_base),)
    )
    return rowcount


def delete_student(student_id):
    """按 id 删除学生，返回受影响行数。"""
    ensure_schema()
    sql = "DELETE FROM student WHERE id=%s"
    rowcount, _ = execute_update(sql, (student_id,))
    return rowcount


def get_student_by_id(student_id):
    ensure_schema()
    return execute_one("SELECT * FROM student WHERE id=%s", (student_id,))


def get_student_by_no(student_no):
    ensure_schema()
    return execute_one("SELECT * FROM student WHERE student_no=%s", (student_no,))


def list_all_students():
    ensure_schema()
    return execute_query("SELECT * FROM student ORDER BY student_no ASC")


def search_students(keyword):
    ensure_schema()
    like = f"%{keyword}%"
    return execute_query(
        "SELECT * FROM student "
        "WHERE name LIKE %s OR student_no LIKE %s "
        "ORDER BY student_no ASC",
        (like, like),
    )
