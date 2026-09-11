# -*- coding: utf-8 -*-
"""个人模式数据表 DAO：日记 / 里程碑 / 心情（与班级业务表隔离）。"""

from database.db_conn import execute_query, execute_one, execute_update

_SCHEMA_READY = False

# 心情：happy / normal / tired / sad
MOOD_HAPPY = "happy"
MOOD_NORMAL = "normal"
MOOD_TIRED = "tired"
MOOD_SAD = "sad"
MOOD_VALUES = (MOOD_HAPPY, MOOD_NORMAL, MOOD_TIRED, MOOD_SAD)


def ensure_schema():
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS personal_diary (
            id          INT             NOT NULL AUTO_INCREMENT COMMENT '自增主键',
            diary_date  DATE            NOT NULL COMMENT '日记日期',
            content     TEXT            DEFAULT NULL COMMENT '正文摘要',
            canvas_data MEDIUMTEXT      DEFAULT NULL COMMENT '混合画布JSON(文字+手绘)',
            image_path  VARCHAR(255)    DEFAULT NULL COMMENT '配图相对路径',
            create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            update_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_personal_diary_date (diary_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci COMMENT='个人日记'
        """
    )
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS personal_milestone (
            id          INT             NOT NULL AUTO_INCREMENT COMMENT '自增主键',
            mark_date   DATE            NOT NULL COMMENT '里程碑日期',
            title       VARCHAR(100)    NOT NULL COMMENT '标题',
            content     TEXT            DEFAULT NULL COMMENT '详情',
            create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_personal_ms_date (mark_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci COMMENT='个人里程碑'
        """
    )
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS personal_mood (
            mark_date   DATE            NOT NULL COMMENT '日期',
            mood        VARCHAR(16)     NOT NULL COMMENT '心情标签',
            update_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (mark_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci COMMENT='个人心情'
        """
    )
    # 旧库补齐 canvas_data
    cols = execute_query(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='personal_diary'"
    )
    names = {c["COLUMN_NAME"] for c in (cols or [])}
    if names and "canvas_data" not in names:
        execute_update(
            "ALTER TABLE personal_diary ADD COLUMN canvas_data MEDIUMTEXT "
            "DEFAULT NULL COMMENT '混合画布JSON(文字+手绘)' AFTER content"
        )
    _SCHEMA_READY = True


# ----- diary -----

def insert_diary(diary_date, content=None, image_path=None, canvas_data=None):
    ensure_schema()
    sql = (
        "INSERT INTO personal_diary (diary_date, content, canvas_data, image_path) "
        "VALUES (%s, %s, %s, %s)"
    )
    _, last_id = execute_update(
        sql, (diary_date, content, canvas_data, image_path)
    )
    return last_id


def update_diary(diary_id, content=None, image_path=None, canvas_data=None):
    ensure_schema()
    sql = (
        "UPDATE personal_diary SET content=%s, canvas_data=%s, image_path=%s "
        "WHERE id=%s"
    )
    rowcount, _ = execute_update(
        sql, (content, canvas_data, image_path, diary_id)
    )
    return rowcount


def delete_diary(diary_id):
    ensure_schema()
    rowcount, _ = execute_update(
        "DELETE FROM personal_diary WHERE id=%s", (diary_id,)
    )
    return rowcount


def get_diary_by_id(diary_id):
    ensure_schema()
    return execute_one("SELECT * FROM personal_diary WHERE id=%s", (diary_id,))


def list_diaries_by_date(diary_date):
    ensure_schema()
    return execute_query(
        "SELECT * FROM personal_diary WHERE diary_date=%s ORDER BY id DESC",
        (diary_date,),
    )


def list_diary_dates(start_date=None, end_date=None):
    ensure_schema()
    conditions, params = [], []
    if start_date:
        conditions.append("diary_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("diary_date <= %s")
        params.append(end_date)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = execute_query(
        f"SELECT DISTINCT diary_date FROM personal_diary {where} ORDER BY diary_date",
        tuple(params) if params else None,
    )
    return [r["diary_date"] for r in (rows or [])]


def list_all_diaries():
    ensure_schema()
    return execute_query(
        "SELECT * FROM personal_diary ORDER BY diary_date DESC, id DESC"
    )


# ----- milestone -----

def insert_milestone(mark_date, title, content=None):
    ensure_schema()
    sql = (
        "INSERT INTO personal_milestone (mark_date, title, content) "
        "VALUES (%s, %s, %s)"
    )
    _, last_id = execute_update(sql, (mark_date, title, content))
    return last_id


def update_milestone(ms_id, title, content=None):
    ensure_schema()
    sql = "UPDATE personal_milestone SET title=%s, content=%s WHERE id=%s"
    rowcount, _ = execute_update(sql, (title, content, ms_id))
    return rowcount


def delete_milestone(ms_id):
    ensure_schema()
    rowcount, _ = execute_update(
        "DELETE FROM personal_milestone WHERE id=%s", (ms_id,)
    )
    return rowcount


def get_milestone_by_id(ms_id):
    ensure_schema()
    return execute_one("SELECT * FROM personal_milestone WHERE id=%s", (ms_id,))


def list_milestones_by_date(mark_date):
    ensure_schema()
    return execute_query(
        "SELECT * FROM personal_milestone WHERE mark_date=%s ORDER BY id DESC",
        (mark_date,),
    )


def list_milestone_dates(start_date=None, end_date=None):
    ensure_schema()
    conditions, params = [], []
    if start_date:
        conditions.append("mark_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("mark_date <= %s")
        params.append(end_date)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = execute_query(
        f"SELECT DISTINCT mark_date FROM personal_milestone {where}",
        tuple(params) if params else None,
    )
    return [r["mark_date"] for r in (rows or [])]


# ----- mood -----

def upsert_mood(mark_date, mood):
    ensure_schema()
    sql = (
        "INSERT INTO personal_mood (mark_date, mood) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE mood=VALUES(mood)"
    )
    rowcount, _ = execute_update(sql, (mark_date, mood))
    return rowcount


def delete_mood(mark_date):
    ensure_schema()
    rowcount, _ = execute_update(
        "DELETE FROM personal_mood WHERE mark_date=%s", (mark_date,)
    )
    return rowcount


def get_mood(mark_date):
    ensure_schema()
    return execute_one(
        "SELECT * FROM personal_mood WHERE mark_date=%s", (mark_date,)
    )


def list_moods_in_range(start_date=None, end_date=None):
    ensure_schema()
    conditions, params = [], []
    if start_date:
        conditions.append("mark_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("mark_date <= %s")
        params.append(end_date)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return execute_query(
        f"SELECT * FROM personal_mood {where}",
        tuple(params) if params else None,
    )


def wipe_all_personal_data():
    """重置 PIN 时清空全部个人数据。"""
    ensure_schema()
    # 先取图片路径再删表
    rows = execute_query("SELECT image_path FROM personal_diary") or []
    execute_update("DELETE FROM personal_diary")
    execute_update("DELETE FROM personal_milestone")
    execute_update("DELETE FROM personal_mood")
    return [r.get("image_path") for r in rows if r.get("image_path")]
