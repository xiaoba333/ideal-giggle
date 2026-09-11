# -*- coding: utf-8 -*-
"""
班级管理系统 - 程序入口。
启动前请确认：
1. Docker MySQL 已启动，Navicat 已执行 database/init_table.sql
2. database/db_conn.py 中 DB_CONFIG 账号密码正确
"""

import os
import sys

# 保证以项目根目录为模块搜索路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import apply_app_style, styled_critical


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("班级管理系统")
    apply_app_style(app)

    try:
        from utils.log_image_util import ensure_log_images_dir
        ensure_log_images_dir()
    except Exception as e:
        print(f"[启动] 创建 log_images 目录失败: {e}")

    try:
        # 启动时探测数据库连接，并补齐班级日志新字段
        from database.db_conn import execute_query
        from dao.classlog_dao import ensure_schema as ensure_log_schema
        from dao.student_dao import ensure_schema as ensure_student_schema
        from dao.settings_dao import ensure_schema as ensure_settings_schema
        from dao.moral_dao import ensure_schema as ensure_moral_schema
        from dao.todo_dao import ensure_schema as ensure_todo_schema
        from dao.personal_dao import ensure_schema as ensure_personal_schema
        from dao.essay_dao import ensure_schema as ensure_essay_schema
        from utils.personal_image_util import ensure_personal_images_dir
        execute_query("SELECT 1 AS ok")
        ensure_settings_schema()
        ensure_student_schema()
        ensure_log_schema()
        ensure_moral_schema()
        ensure_todo_schema()
        ensure_personal_schema()
        ensure_essay_schema()
        ensure_personal_images_dir()
    except Exception as e:
        styled_critical(
            None,
            "数据库连接失败",
            f"无法连接 MySQL，请检查 Docker 与 database/db_conn.py 配置。\n\n{e}",
        )
        return 1

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
