# -*- coding: utf-8 -*-
"""课程模式：笔记大类 / 笔记（与班级日志、个人日记、随笔隔离）。"""

from database.db_conn import execute_query, execute_one, execute_update

_SCHEMA_READY = False


def ensure_schema():
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS course_category (
            id          INT             NOT NULL AUTO_INCREMENT COMMENT '笔记大类ID',
            name        VARCHAR(100)    NOT NULL COMMENT '大类名称',
            sort_order  INT             NOT NULL DEFAULT 0 COMMENT '排序',
            create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_course_cat_sort (sort_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci COMMENT='课程模式笔记大类'
        """
    )
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS course_note (
            id            INT             NOT NULL AUTO_INCREMENT COMMENT '笔记ID',
            category_id   INT             NOT NULL COMMENT '归属大类ID',
            title         VARCHAR(200)    NOT NULL COMMENT '笔记标题',
            content_html  MEDIUMTEXT      DEFAULT NULL COMMENT '富文本内容（文字+图片引用）',
            outline_json  TEXT            DEFAULT NULL COMMENT '标题标记信息（纲要目录）',
            sort_order    INT             NOT NULL DEFAULT 0 COMMENT '排序',
            create_time   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            update_time   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_course_note_cat (category_id),
            CONSTRAINT fk_course_note_cat FOREIGN KEY (category_id)
                REFERENCES course_category (id)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci COMMENT='课程模式笔记'
        """
    )
    _SCHEMA_READY = True


def list_categories():
    ensure_schema()
    return execute_query(
        "SELECT * FROM course_category ORDER BY sort_order ASC, id ASC"
    )


def get_category(category_id):
    ensure_schema()
    return execute_one(
        "SELECT * FROM course_category WHERE id=%s", (category_id,)
    )


def next_category_sort():
    ensure_schema()
    row = execute_one(
        "SELECT COALESCE(MAX(sort_order), -1) AS m FROM course_category"
    )
    return int((row or {}).get("m") or -1) + 1


def insert_category(name, sort_order=0):
    ensure_schema()
    _, last_id = execute_update(
        "INSERT INTO course_category (name, sort_order) VALUES (%s, %s)",
        (name, sort_order),
    )
    return last_id


def update_category_name(category_id, name):
    ensure_schema()
    rowcount, _ = execute_update(
        "UPDATE course_category SET name=%s WHERE id=%s",
        (name, category_id),
    )
    return rowcount


def delete_category(category_id):
    ensure_schema()
    rowcount, _ = execute_update(
        "DELETE FROM course_category WHERE id=%s", (category_id,)
    )
    return rowcount


def list_notes(category_id):
    ensure_schema()
    return execute_query(
        "SELECT id, category_id, title, sort_order, create_time, update_time "
        "FROM course_note WHERE category_id=%s ORDER BY sort_order ASC, id ASC",
        (category_id,),
    )


def get_note(note_id):
    ensure_schema()
    return execute_one(
        "SELECT * FROM course_note WHERE id=%s", (note_id,)
    )


def next_note_sort(category_id):
    ensure_schema()
    row = execute_one(
        "SELECT COALESCE(MAX(sort_order), -1) AS m FROM course_note "
        "WHERE category_id=%s",
        (category_id,),
    )
    return int((row or {}).get("m") or -1) + 1


def insert_note(category_id, title, sort_order=0):
    ensure_schema()
    _, last_id = execute_update(
        "INSERT INTO course_note (category_id, title, content_html, outline_json, sort_order) "
        "VALUES (%s, %s, %s, %s, %s)",
        (category_id, title, "", "[]", sort_order),
    )
    return last_id


def update_note_title(note_id, title):
    ensure_schema()
    rowcount, _ = execute_update(
        "UPDATE course_note SET title=%s WHERE id=%s",
        (title, note_id),
    )
    return rowcount


def update_note_content(note_id, content_html, outline_json):
    ensure_schema()
    rowcount, _ = execute_update(
        "UPDATE course_note SET content_html=%s, outline_json=%s WHERE id=%s",
        (content_html, outline_json, note_id),
    )
    return rowcount


def delete_note(note_id):
    ensure_schema()
    rowcount, _ = execute_update(
        "DELETE FROM course_note WHERE id=%s", (note_id,)
    )
    return rowcount
