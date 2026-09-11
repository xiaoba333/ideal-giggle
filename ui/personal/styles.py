# -*- coding: utf-8 -*-
"""个人模式绿色森系配色与 QSS（仅作用于 personalShell 子树，不串色到主界面）。"""

COLOR_BG = "#f2f8f3"
COLOR_CARD = "#ffffff"
COLOR_PRIMARY = "#579669"
COLOR_ASSIST = "#b2d8bc"
COLOR_SOFT = "#e6f1ea"
COLOR_TEXT = "#274430"
COLOR_TEXT_SECONDARY = "#63806c"
COLOR_SELECTED = "#d0e8d9"
COLOR_BORDER = "#b2d8bc"
COLOR_BTN = "#579669"
COLOR_BTN_HOVER = "#6aad7c"
COLOR_BTN_PRESSED = "#3f7550"

COLOR_TABLE_HEADER = "#579669"
COLOR_TABLE_ODD = "#ffffff"
COLOR_TABLE_EVEN = "#eef6f1"
COLOR_TABLE_HOVER = "#d0e8d9"
COLOR_TABLE_SELECT = "#b2d8bc"

PERSONAL_QSS = f"""
QWidget#personalShell {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
}}

QWidget#personalShell QLabel {{
    color: {COLOR_TEXT};
    background: transparent;
}}

QWidget#personalShell QLabel#hintLabel {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 9pt;
}}

QWidget#personalShell QLabel#pageTitle {{
    color: {COLOR_PRIMARY};
    font-weight: bold;
    font-size: 13pt;
}}

QWidget#personalShell QLineEdit,
QWidget#personalShell QTextEdit,
QWidget#personalShell QPlainTextEdit,
QWidget#personalShell QDateEdit,
QWidget#personalShell QComboBox {{
    background-color: {COLOR_CARD};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 4px 8px;
    selection-background-color: {COLOR_SELECTED};
}}

QWidget#personalShell QLineEdit:focus,
QWidget#personalShell QTextEdit:focus,
QWidget#personalShell QDateEdit:focus,
QWidget#personalShell QComboBox:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}

QWidget#personalTabWidget {{
    background-color: {COLOR_BG};
}}

QWidget#personalTabPane {{
    background-color: {COLOR_BG};
}}

QStackedWidget#personalTabStack {{
    background-color: {COLOR_BG};
}}

QTabBar#personalNavTabBar {{
    background-color: {COLOR_BG};
    qproperty-drawBase: 0;
}}

QTabBar#personalNavTabBar::tab {{
    background-color: {COLOR_SOFT};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_ASSIST};
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    min-width: 96px;
    min-height: 34px;
    padding: 6px 18px;
    margin-right: 4px;
}}

QTabBar#personalNavTabBar::tab:selected {{
    background-color: {COLOR_CARD};
    color: {COLOR_PRIMARY};
    font-weight: bold;
    border-color: {COLOR_PRIMARY};
}}

QTabBar#personalNavTabBar::tab:hover:!selected {{
    background-color: {COLOR_SELECTED};
}}

QFrame#personalCard {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_ASSIST};
    border-radius: 12px;
}}

QFrame#personalTablePanel {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_ASSIST};
    border-radius: 12px;
}}

QTableWidget#personalTable {{
    background-color: {COLOR_CARD};
    alternate-background-color: {COLOR_TABLE_EVEN};
    gridline-color: {COLOR_SOFT};
    border: none;
    selection-background-color: {COLOR_TABLE_SELECT};
    selection-color: {COLOR_TEXT};
}}

QHeaderView::section {{
    background-color: {COLOR_TABLE_HEADER};
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}}

QDialog#personalDialog {{
    background-color: {COLOR_BG};
}}

QDialog#personalPinDialog {{
    background-color: #f2ebe0;
}}
"""
