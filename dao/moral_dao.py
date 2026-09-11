# -*- coding: utf-8 -*-
"""德育变动明细表 moral_record DAO。"""

from database.db_conn import execute_query, execute_update

_SCHEMA_READY = False

# moral_type 与 class_log.moral_type 一致
MORAL_NONE = 0
MORAL_ADD = 1
MORAL_DEDUCT = 2
MORAL_BOTH = 3  # 同时存在加分与扣分


def ensure_schema():
    """创建 moral_record（幂等）。"""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    tables = execute_query(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='moral_record'"
    )
    if not tables:
        execute_update(
            """
            CREATE TABLE moral_record (
                id            INT             NOT NULL AUTO_INCREMENT COMMENT '自增主键',
                student_id    INT             NOT NULL COMMENT '学生 id',
                score_change  INT             NOT NULL COMMENT '变动分数（加分为正，扣分为负）',
                change_time   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '变动时间',
                log_id        INT             DEFAULT NULL COMMENT '关联班级日志 id',
                reason        TEXT            DEFAULT NULL COMMENT '事由（复用日志内容）',
                PRIMARY KEY (id),
                KEY idx_moral_student (student_id),
                KEY idx_moral_log (log_id),
                KEY idx_moral_change_time (change_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='德育变动明细'
            """
        )
    _SCHEMA_READY = True


def delete_by_log_id(log_id):
    """删除某日志关联的全部德育明细。"""
    ensure_schema()
    if not log_id:
        return 0
    rowcount, _ = execute_update(
        "DELETE FROM moral_record WHERE log_id=%s", (log_id,)
    )
    return rowcount


def insert_records(log_id, student_ids, score_change, reason=None):
    """
    批量为学生写入德育明细。
    score_change: 已带符号（加分正、扣分负）。
    """
    ensure_schema()
    if not log_id or not student_ids:
        return 0
    reason = (reason or "").strip() or None
    n = 0
    for sid in student_ids:
        try:
            sid = int(sid)
        except (TypeError, ValueError):
            continue
        execute_update(
            "INSERT INTO moral_record "
            "(student_id, score_change, log_id, reason) "
            "VALUES (%s, %s, %s, %s)",
            (sid, int(score_change), log_id, reason),
        )
        n += 1
    return n


def list_by_log_id(log_id):
    """查询某日志的德育明细。"""
    ensure_schema()
    if not log_id:
        return []
    return execute_query(
        "SELECT * FROM moral_record WHERE log_id=%s ORDER BY id ASC",
        (log_id,),
    )


def affected_student_ids(log_id):
    """某日志受影响学生 id 列表。"""
    rows = list_by_log_id(log_id)
    ids = []
    for r in rows:
        sid = r.get("student_id")
        if sid is not None:
            try:
                ids.append(int(sid))
            except (TypeError, ValueError):
                pass
    return ids


def split_records_by_sign(log_id):
    """
    将某日志德育明细拆成加分 / 扣分两侧。
    返回: add_score, add_student_ids, deduct_score, deduct_student_ids
    """
    result = {
        "add_score": None,
        "add_student_ids": [],
        "deduct_score": None,
        "deduct_student_ids": [],
    }
    for r in list_by_log_id(log_id):
        try:
            sc = int(r.get("score_change") or 0)
            sid = int(r.get("student_id"))
        except (TypeError, ValueError):
            continue
        if sc > 0:
            result["add_student_ids"].append(sid)
            result["add_score"] = sc
        elif sc < 0:
            result["deduct_student_ids"].append(sid)
            result["deduct_score"] = abs(sc)
    return result


def list_by_student_id(student_id):
    """
    某学生全部德育明细（含关联日志类型）。
    按发生时间倒序。
    """
    ensure_schema()
    if not student_id:
        return []
    return execute_query(
        """
        SELECT
            mr.id,
            mr.student_id,
            mr.score_change,
            mr.change_time,
            mr.log_id,
            mr.reason,
            cl.log_type,
            cl.type_remark,
            cl.title AS log_title,
            cl.log_date
        FROM moral_record mr
        LEFT JOIN class_log cl ON cl.id = mr.log_id
        WHERE mr.student_id = %s
        ORDER BY mr.change_time DESC, mr.id DESC
        """,
        (student_id,),
    )


def list_student_scoreboard(order_by="student_no"):
    """
    全部学生德育总分榜。
    total = moral_base + SUM(score_change)
    order_by: student_no | score_desc
    """
    ensure_schema()
    from dao import settings_dao, student_dao
    student_dao.ensure_schema()
    settings_dao.ensure_schema()
    default_base = settings_dao.get_moral_base_default()
    default_class = settings_dao.get_default_class_name()

    if order_by == "score_desc":
        order_sql = "total_score DESC, s.student_no ASC"
    else:
        order_sql = "s.student_no ASC"

    rows = execute_query(
        f"""
        SELECT
            s.id,
            s.student_no,
            s.name,
            s.gender,
            s.phone,
            s.moral_base,
            s.class_name,
            COALESCE(SUM(mr.score_change), 0) AS change_sum,
            COALESCE(SUM(CASE WHEN mr.score_change > 0 THEN mr.score_change ELSE 0 END), 0)
                AS add_sum,
            COALESCE(SUM(CASE WHEN mr.score_change < 0 THEN -mr.score_change ELSE 0 END), 0)
                AS deduct_sum,
            (COALESCE(s.moral_base, %s) + COALESCE(SUM(mr.score_change), 0)) AS total_score
        FROM student s
        LEFT JOIN moral_record mr ON mr.student_id = s.id
        GROUP BY s.id, s.student_no, s.name, s.gender, s.phone,
                 s.moral_base, s.class_name
        ORDER BY {order_sql}
        """,
        (default_base,),
    )
    for row in rows:
        base = row.get("moral_base")
        if base is None:
            base = default_base
            row["moral_base"] = base
        try:
            row["total_score"] = int(row.get("total_score") if row.get("total_score") is not None else base)
        except (TypeError, ValueError):
            row["total_score"] = int(base)
        cls = (row.get("class_name") or "").strip()
        row["class_display"] = cls or default_class
    return rows
