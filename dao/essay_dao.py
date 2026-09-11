# -*- coding: utf-8 -*-
"""感触随笔：黑板 / 便签独立表（与日记日历隔离）。"""

from database.db_conn import execute_query, execute_one, execute_update

_SCHEMA_READY = False

DEFAULT_NOTE_BG = "#f3e6c8"


def ensure_schema():
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS personal_blackboard (
            id          INT             NOT NULL AUTO_INCREMENT COMMENT '黑板ID',
            title       VARCHAR(100)    NOT NULL DEFAULT '黑板' COMMENT '标题',
            sort_order  INT             NOT NULL DEFAULT 0 COMMENT '排序',
            create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_board_sort (sort_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci COMMENT='感触随笔黑板'
        """
    )
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS personal_sticky_note (
            id          INT             NOT NULL AUTO_INCREMENT COMMENT '便签ID',
            board_id    INT             NOT NULL COMMENT '归属黑板ID',
            pos_x       INT             NOT NULL DEFAULT 40 COMMENT 'X坐标',
            pos_y       INT             NOT NULL DEFAULT 40 COMMENT 'Y坐标',
            width       INT             NOT NULL DEFAULT 118 COMMENT '宽度',
            height      INT             NOT NULL DEFAULT 108 COMMENT '高度',
            rotation    DOUBLE          NOT NULL DEFAULT 0 COMMENT '倾斜角度',
            content     TEXT            DEFAULT NULL COMMENT '完整文本',
            bg_color    VARCHAR(16)     NOT NULL DEFAULT '#f3e6c8' COMMENT '底色',
            z_order     INT             NOT NULL DEFAULT 0 COMMENT '叠放层级',
            create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            update_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_note_board (board_id),
            CONSTRAINT fk_note_board FOREIGN KEY (board_id)
                REFERENCES personal_blackboard (id)
                ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci COMMENT='感触随笔便签'
        """
    )
    # 若尚无黑板，建一块空白命名的默认板
    rows = execute_query("SELECT COUNT(*) AS c FROM personal_blackboard")
    if rows and int(rows[0].get("c") or 0) == 0:
        execute_update(
            "INSERT INTO personal_blackboard (title, sort_order) VALUES (%s, %s)",
            ("未命名", 0),
        )
    # 便签宽高（可缩放）
    cols = execute_query(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='personal_sticky_note'"
    )
    names = {c["COLUMN_NAME"] for c in (cols or [])}
    if names and "width" not in names:
        execute_update(
            "ALTER TABLE personal_sticky_note "
            "ADD COLUMN width INT NOT NULL DEFAULT 118 COMMENT '宽度' AFTER pos_y, "
            "ADD COLUMN height INT NOT NULL DEFAULT 108 COMMENT '高度' AFTER width"
        )
    # 重新读列（可能刚加了 width/height）
    cols = execute_query(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='personal_sticky_note'"
    )
    names = {c["COLUMN_NAME"] for c in (cols or [])}
    if names and "rotation" not in names:
        execute_update(
            "ALTER TABLE personal_sticky_note "
            "ADD COLUMN rotation DOUBLE NOT NULL DEFAULT 0 "
            "COMMENT '倾斜角度' AFTER height"
        )
    _SCHEMA_READY = True


def list_boards():
    ensure_schema()
    return execute_query(
        "SELECT * FROM personal_blackboard ORDER BY sort_order ASC, id ASC"
    )


def get_board(board_id):
    ensure_schema()
    return execute_one(
        "SELECT * FROM personal_blackboard WHERE id=%s", (board_id,)
    )


def insert_board(title="黑板", sort_order=0):
    ensure_schema()
    _, last_id = execute_update(
        "INSERT INTO personal_blackboard (title, sort_order) VALUES (%s, %s)",
        (title, sort_order),
    )
    return last_id


def update_board_title(board_id, title):
    ensure_schema()
    rowcount, _ = execute_update(
        "UPDATE personal_blackboard SET title=%s WHERE id=%s",
        (title, board_id),
    )
    return rowcount


def delete_board(board_id):
    ensure_schema()
    rowcount, _ = execute_update(
        "DELETE FROM personal_blackboard WHERE id=%s", (board_id,)
    )
    return rowcount


def next_board_sort():
    ensure_schema()
    row = execute_one("SELECT COALESCE(MAX(sort_order), -1) AS m FROM personal_blackboard")
    return int((row or {}).get("m") or -1) + 1


def list_notes_by_board(board_id):
    ensure_schema()
    return execute_query(
        "SELECT * FROM personal_sticky_note WHERE board_id=%s "
        "ORDER BY z_order ASC, id ASC",
        (board_id,),
    )


def get_note(note_id):
    ensure_schema()
    return execute_one(
        "SELECT * FROM personal_sticky_note WHERE id=%s", (note_id,)
    )


def insert_note(board_id, pos_x=40, pos_y=40, content="", bg_color=DEFAULT_NOTE_BG,
                z_order=0, width=118, height=108, rotation=0):
    ensure_schema()
    _, last_id = execute_update(
        "INSERT INTO personal_sticky_note "
        "(board_id, pos_x, pos_y, width, height, rotation, content, bg_color, z_order) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (board_id, pos_x, pos_y, width, height, rotation, content, bg_color, z_order),
    )
    return last_id


def update_note(note_id, content=None, pos_x=None, pos_y=None, bg_color=None,
                z_order=None, width=None, height=None, rotation=None, board_id=None):
    ensure_schema()
    old = get_note(note_id)
    if not old:
        return 0
    content = old["content"] if content is None else content
    pos_x = old["pos_x"] if pos_x is None else pos_x
    pos_y = old["pos_y"] if pos_y is None else pos_y
    bg_color = old["bg_color"] if bg_color is None else bg_color
    z_order = old["z_order"] if z_order is None else z_order
    width = old.get("width") if width is None else width
    height = old.get("height") if height is None else height
    rotation = old.get("rotation") if rotation is None else rotation
    board_id = old["board_id"] if board_id is None else board_id
    if width is None:
        width = 118
    if height is None:
        height = 108
    if rotation is None:
        rotation = 0
    rowcount, _ = execute_update(
        "UPDATE personal_sticky_note SET board_id=%s, content=%s, pos_x=%s, pos_y=%s, "
        "width=%s, height=%s, rotation=%s, bg_color=%s, z_order=%s WHERE id=%s",
        (board_id, content, pos_x, pos_y, width, height, rotation, bg_color, z_order, note_id),
    )
    return rowcount


def delete_note(note_id):
    ensure_schema()
    rowcount, _ = execute_update(
        "DELETE FROM personal_sticky_note WHERE id=%s", (note_id,)
    )
    return rowcount


def max_z_order(board_id):
    ensure_schema()
    row = execute_one(
        "SELECT COALESCE(MAX(z_order), 0) AS m FROM personal_sticky_note "
        "WHERE board_id=%s",
        (board_id,),
    )
    return int((row or {}).get("m") or 0)
