# -*- coding: utf-8 -*-
"""将 class_log 主键按时间顺序重排为从 1 开始，并重置自增。"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from database.db_conn import execute_query, execute_update


def reindex_class_log():
    rows = execute_query(
        "SELECT id FROM class_log ORDER BY log_date ASC, create_time ASC, id ASC"
    )
    print("before:", [r["id"] for r in rows])
    if not rows:
        execute_update("ALTER TABLE class_log AUTO_INCREMENT = 1")
        print("empty table, auto_increment reset to 1")
        return

    # 临时偏移，避免主键冲突
    execute_update("UPDATE class_log SET id = id + 100000")
    rows = execute_query(
        "SELECT id FROM class_log ORDER BY log_date ASC, create_time ASC, id ASC"
    )
    for new_id, row in enumerate(rows, start=1):
        execute_update(
            "UPDATE class_log SET id=%s WHERE id=%s",
            (new_id, row["id"]),
        )
    next_id = len(rows) + 1
    execute_update(f"ALTER TABLE class_log AUTO_INCREMENT = {next_id}")
    after = execute_query(
        "SELECT id, log_type, title FROM class_log ORDER BY id"
    )
    print("after:", after)
    print("auto_increment next:", next_id)


if __name__ == "__main__":
    reindex_class_log()
