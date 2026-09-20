# -*- coding: utf-8 -*-
"""课程模式独立黑白极简样式（不污染班级主界面 / 个人模式）。"""

COLOR_BG = "#ffffff"
COLOR_TEXT = "#222222"
COLOR_TEXT_SECONDARY = "#666666"
COLOR_BORDER = "#e8e8e8"
COLOR_SELECTED = "#f0f0f0"

COURSE_QSS = f"""
QWidget#courseShell {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
}}

QWidget#courseShell QLabel {{
    color: {COLOR_TEXT};
    background: transparent;
    border: none;
}}

QWidget#courseShell QLabel#courseTitle {{
    color: {COLOR_TEXT};
    font-size: 13pt;
    font-weight: 700;
}}

QWidget#courseShell QLabel#courseSection {{
    color: {COLOR_TEXT};
    font-size: 10pt;
    font-weight: 600;
}}

QWidget#courseShell QLabel#courseHint {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 9pt;
}}

QWidget#courseShell QWidget#courseOutlinePanel {{
    background-color: {COLOR_BG};
}}

QWidget#courseShell QPushButton#courseFoldBtn {{
    min-width: 32px;
    padding: 4px 6px;
}}

QWidget#courseShell QToolButton#courseOutlineArrow {{
    background: transparent;
    border: none;
    padding: 0;
    min-width: 22px;
    min-height: 22px;
    color: {COLOR_TEXT};
}}

QWidget#courseShell QToolButton#courseOutlineArrow:hover {{
    background-color: {COLOR_SELECTED};
}}

QWidget#courseShell QToolTip {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    padding: 4px 8px;
}}

QWidget#courseShell QFrame#courseSplit {{
    background-color: {COLOR_BORDER};
    border: none;
    max-width: 1px;
    min-width: 1px;
}}

QWidget#courseShell QListWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: none;
    border-radius: 0px;
    padding: 2px 0;
    outline: none;
}}

QWidget#courseShell QListWidget#courseOutline {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 0px;
}}

QWidget#courseShell QListWidget::item {{
    padding: 8px 10px;
    border: none;
    border-radius: 0px;
    color: {COLOR_TEXT};
}}

QWidget#courseShell QListWidget::item:hover {{
    background-color: {COLOR_SELECTED};
}}

QWidget#courseShell QListWidget::item:selected {{
    background-color: {COLOR_SELECTED};
    color: {COLOR_TEXT};
}}

QWidget#courseShell QPushButton {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 4px 12px;
    min-width: 64px;
    min-height: 28px;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 10pt;
    font-weight: 500;
}}

QWidget#courseShell QPushButton:hover {{
    background-color: {COLOR_SELECTED};
    color: {COLOR_TEXT};
    border-color: #d0d0d0;
}}

QWidget#courseShell QPushButton:pressed {{
    background-color: #e6e6e6;
    color: {COLOR_TEXT};
}}

QWidget#courseShell QPushButton:disabled {{
    color: #aaaaaa;
    background-color: {COLOR_BG};
    border-color: {COLOR_BORDER};
}}

QWidget#courseShell QPushButton#courseExitBtn {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 4px 14px;
    min-width: 96px;
}}

QWidget#courseShell QComboBox {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 2px 8px;
    min-height: 26px;
}}

QWidget#courseShell QComboBox:hover {{
    background-color: {COLOR_SELECTED};
}}

QWidget#courseShell QComboBox::drop-down {{
    border: none;
    width: 18px;
}}

QWidget#courseShell QComboBox QAbstractItemView {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_SELECTED};
    selection-color: {COLOR_TEXT};
}}

QWidget#courseShell QTextEdit {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 0px;
    padding: 8px;
    selection-background-color: {COLOR_SELECTED};
    selection-color: {COLOR_TEXT};
}}

QWidget#courseShell QMenu {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    padding: 4px 0;
}}

QWidget#courseShell QMenu::item {{
    padding: 6px 24px;
}}

QWidget#courseShell QMenu::item:selected {{
    background-color: {COLOR_SELECTED};
    color: {COLOR_TEXT};
}}

QWidget#courseShell QScrollBar:vertical {{
    background: {COLOR_BG};
    width: 8px;
    margin: 0;
    border: none;
}}

QWidget#courseShell QScrollBar::handle:vertical {{
    background: #d8d8d8;
    min-height: 24px;
    border-radius: 4px;
}}

QWidget#courseShell QScrollBar::add-line:vertical,
QWidget#courseShell QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
