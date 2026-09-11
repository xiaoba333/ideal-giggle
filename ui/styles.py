# -*- coding: utf-8 -*-
"""
全局 UI 样式常量与 QSS（羊皮纸暖色 · 复古印刷风）。
各窗口通过 apply_app_style / apply_widget_style 统一加载，勿在业务 widget 内散写样式。
"""

from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton

# ---------- 色板（羊皮纸暖色底 · 复古护眼） ----------
COLOR_PRIMARY = "#4086d6"
COLOR_PRIMARY_HOVER = "#3574c0"
COLOR_PRIMARY_PRESSED = "#2f66a8"
COLOR_ASSIST = "#e6ddd0"          # 浅褐辅助底
COLOR_BG = "#f2ebe0"              # 统一米色主底
COLOR_TEXT = "#2e2a24"
COLOR_TEXT_SECONDARY = "#6e675e"
COLOR_BORDER = "#c9bfb0"
COLOR_BORDER_FOCUS = "#8b5e3c"
COLOR_DIVIDER = "#d8d0c4"
COLOR_DANGER = "#b54a4a"
COLOR_DANGER_BG = "#f0e0d8"
COLOR_TABLE_HEADER = "#b89c88"        # 柔和浅棕表头
COLOR_TABLE_HEADER_TEXT = "#ffffff"
COLOR_TABLE_ROW_ODD = "#ffffff"       # 奇数行
COLOR_TABLE_ROW_EVEN = "#f8f3ed"      # 偶数行 · 极浅米杏
COLOR_TABLE_HOVER = "#e9dcd0"         # 悬浮行
COLOR_TABLE_SELECT = "#d9c8b8"        # 选中行
COLOR_TABLE_ALT = COLOR_TABLE_ROW_EVEN  # 兼容旧引用
COLOR_DISABLED = "#a89888"

# QColor 供表格行着色等程序内使用
QCOLOR_PRIMARY = QColor(COLOR_PRIMARY)
QCOLOR_DANGER = QColor(COLOR_DANGER)
QCOLOR_DANGER_BG = QColor(COLOR_DANGER_BG)
QCOLOR_ASSIST = QColor(COLOR_ASSIST)

FONT_FAMILY = '"Microsoft YaHei", "Segoe UI", sans-serif'
FONT_SIZE_PT = 10
BUTTON_FONT_SIZE_PT = FONT_SIZE_PT + 1  # 比默认大一号

# ---------- 棕色 Q 版按钮 ----------
COLOR_BTN = "#967259"
COLOR_BTN_BORDER = "#725342"
COLOR_BTN_HOVER = "#a8856b"
COLOR_BTN_HOVER_BORDER = "#7d5e4a"
COLOR_BTN_PRESSED = "#805e48"
COLOR_BTN_PRESSED_BORDER = "#5f4436"
COLOR_BTN_DISABLED = "#cbb8a8"
COLOR_BTN_DISABLED_BORDER = "#b5a594"
COLOR_BTN_DISABLED_TEXT = "#8a827a"

# 圆润可爱字体候选（系统无则回退微软雅黑）
BUTTON_FONT_CANDIDATES = [
    "微软雅黑圆润粗体",
    "Microsoft YaHei Rounded",
    "站酷快乐体",
    "HappyZcool-2016",
    "ZCOOL KuaiLe",
    "汉仪粗圆简",
    "HYCuYuanJ",
    "汉仪粗圆",
    "幼圆",
    "YouYuan",
    "Microsoft YaHei UI",
    "微软雅黑",
    "Microsoft YaHei",
]

_BTN_FONT_TOKEN = "@@BUTTON_FONT_FAMILY@@"
_resolved_button_font = None


def resolve_button_font_family() -> str:
    """解析按钮艺术字体；缺失时回退微软雅黑。"""
    global _resolved_button_font
    if _resolved_button_font is not None:
        return _resolved_button_font
    try:
        from PyQt6.QtGui import QFontDatabase
        available = set(QFontDatabase.families())
    except Exception:
        _resolved_button_font = "Microsoft YaHei"
        return _resolved_button_font
    for name in BUTTON_FONT_CANDIDATES:
        if name in available:
            _resolved_button_font = name
            return _resolved_button_font
    _resolved_button_font = "Microsoft YaHei"
    return _resolved_button_font


def _button_font_css() -> str:
    fam = resolve_button_font_family()
    return f'"{fam}", "Microsoft YaHei", "微软雅黑", "Segoe UI", sans-serif'


def _fabric_gradient(c_mid: str, c_hi: str, c_lo: str) -> str:
    """
    多层线性色标模拟布料/磨砂细纹（纯 QSS 渐变，无外部图片）。
    对角细条纹 + 明暗交替。
    """
    # 24 段微纹：hi/mid/lo 循环，形成细腻斜纹
    parts = []
    steps = 24
    palette = (c_hi, c_mid, c_lo, c_mid)
    for i in range(steps + 1):
        t = i / steps
        col = palette[i % len(palette)]
        parts.append(f"stop:{t:.4f} {col}")
    return (
        "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
        + ", ".join(parts)
        + ")"
    )


# 预生成各状态纹路（模块加载即可，不依赖 QApplication）
_BTN_BG = _fabric_gradient("#967259", "#a07e66", "#8a6750")
_BTN_BG_HOVER = _fabric_gradient("#a8856b", "#b49378", "#9a765c")
_BTN_BG_PRESSED = _fabric_gradient("#805e48", "#8c6a52", "#6f513c")
_BTN_BG_DISABLED = _fabric_gradient("#cbb8a8", "#d2c0b2", "#c0ad9c")


GLOBAL_QSS = f"""
/* ===== 全局基础 ===== */
* {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_PT}pt;
}}

QMainWindow, QDialog, QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
}}

QLabel {{
    color: {COLOR_TEXT};
    background: transparent;
    border: none;
}}

QLabel#hintLabel {{
    color: {COLOR_TEXT_SECONDARY};
    border: none;
    padding: 2px 0;
}}

QLabel#legendLabel {{
    color: {COLOR_PRIMARY};
    font-weight: bold;
    border: none;
}}

QLabel#pageTitle {{
    color: {COLOR_TEXT};
    font-size: 12pt;
    font-weight: bold;
    border: none;
}}

QLabel#fieldLabel {{
    color: {COLOR_TEXT};
    border: none;
    padding: 0;
}}

QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {COLOR_DIVIDER};
    max-height: 1px;
}}

/* ===== 分组区域 ===== */
QWidget#groupPanel {{
    background-color: {COLOR_ASSIST};
    border: 1px solid {COLOR_DIVIDER};
    border-radius: 6px;
}}

/* ===== 按钮（暖棕纹路 · Q 版软糯 · 抗挤压） ===== */
QPushButton {{
    background-color: {COLOR_BTN};
    background: {_BTN_BG};
    color: #ffffff;
    border: 1px solid {COLOR_BTN_BORDER};
    border-radius: 12px;
    padding: 4px 12px;
    min-width: 80px;
    min-height: 32px;
    font-family: {_BTN_FONT_TOKEN};
    font-size: {BUTTON_FONT_SIZE_PT}pt;
    font-weight: 700;
}}

QPushButton:hover {{
    background-color: {COLOR_BTN_HOVER};
    background: {_BTN_BG_HOVER};
    border-color: {COLOR_BTN_HOVER_BORDER};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: {COLOR_BTN_PRESSED};
    background: {_BTN_BG_PRESSED};
    border-color: {COLOR_BTN_PRESSED_BORDER};
    color: #ffffff;
}}

QPushButton:disabled {{
    background-color: {COLOR_BTN_DISABLED};
    background: {_BTN_BG_DISABLED};
    color: {COLOR_BTN_DISABLED_TEXT};
    border-color: {COLOR_BTN_DISABLED_BORDER};
}}

/* secondary / danger：统一棕色纹路 Q 版（仅保留属性兼容，视觉一致） */
QPushButton[secondary="true"] {{
    background-color: {COLOR_BTN};
    background: {_BTN_BG};
    color: #ffffff;
    border: 1px solid {COLOR_BTN_BORDER};
    min-width: 80px;
    min-height: 32px;
}}

QPushButton[secondary="true"]:hover {{
    background-color: {COLOR_BTN_HOVER};
    background: {_BTN_BG_HOVER};
    border-color: {COLOR_BTN_HOVER_BORDER};
    color: #ffffff;
}}

QPushButton[secondary="true"]:pressed {{
    background-color: {COLOR_BTN_PRESSED};
    background: {_BTN_BG_PRESSED};
    border-color: {COLOR_BTN_PRESSED_BORDER};
    color: #ffffff;
}}

QPushButton[secondary="true"]:disabled {{
    background-color: {COLOR_BTN_DISABLED};
    background: {_BTN_BG_DISABLED};
    color: {COLOR_BTN_DISABLED_TEXT};
    border-color: {COLOR_BTN_DISABLED_BORDER};
}}

QPushButton[danger="true"] {{
    background-color: {COLOR_BTN};
    background: {_BTN_BG};
    color: #ffffff;
    border: 1px solid {COLOR_BTN_BORDER};
    min-width: 80px;
    min-height: 32px;
}}

QPushButton[danger="true"]:hover {{
    background-color: {COLOR_BTN_HOVER};
    background: {_BTN_BG_HOVER};
    border-color: {COLOR_BTN_HOVER_BORDER};
    color: #ffffff;
}}

QPushButton[danger="true"]:pressed {{
    background-color: {COLOR_BTN_PRESSED};
    background: {_BTN_BG_PRESSED};
    border-color: {COLOR_BTN_PRESSED_BORDER};
    color: #ffffff;
}}

QPushButton[danger="true"]:disabled {{
    background-color: {COLOR_BTN_DISABLED};
    background: {_BTN_BG_DISABLED};
    color: {COLOR_BTN_DISABLED_TEXT};
    border-color: {COLOR_BTN_DISABLED_BORDER};
}}

/* ===== 输入控件 ===== */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 26px;
    selection-background-color: {COLOR_TABLE_SELECT};
    selection-color: {COLOR_TEXT};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QComboBox:focus, QDateEdit:focus, QSpinBox:focus {{
    border: 1px solid {COLOR_BORDER_FOCUS};
}}

QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QDateEdit:disabled {{
    background-color: #e8dfd0;
    color: {COLOR_DISABLED};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}

QComboBox::down-arrow {{
    width: 8px;
    height: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_ASSIST};
    selection-color: {COLOR_TEXT};
    outline: none;
}}

QDateEdit::drop-down {{
    border: none;
    width: 22px;
}}

QTextEdit {{
    padding: 6px;
}}

QCheckBox {{
    color: {COLOR_TEXT};
    spacing: 6px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_BORDER};
    border-radius: 3px;
    background: {COLOR_BG};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_PRIMARY};
    border-color: {COLOR_PRIMARY};
}}

/* ===== 表格（暖棕米色 · 匹配按钮主色） ===== */
QFrame#tablePanelShadow {{
    background-color: rgba(184, 156, 136, 40);
    border: none;
    border-radius: 16px;
}}

QFrame#tablePanel {{
    background-color: {COLOR_TABLE_ROW_ODD};
    border: 1px solid #e0d4c8;
    border-radius: 14px;
}}

QTableWidget {{
    background-color: {COLOR_TABLE_ROW_ODD};
    alternate-background-color: {COLOR_TABLE_ROW_EVEN};
    border: 1px solid #e0d4c8;
    border-radius: 14px;
    gridline-color: transparent;
    outline: none;
    selection-background-color: {COLOR_TABLE_SELECT};
}}

/* 内嵌面板内的表格：由外层圆角/阴影承担边框 */
QTableWidget#dataTable {{
    background-color: {COLOR_TABLE_ROW_ODD};
    alternate-background-color: {COLOR_TABLE_ROW_EVEN};
    border: none;
    border-radius: 14px;
    gridline-color: transparent;
    outline: none;
    selection-background-color: {COLOR_TABLE_SELECT};
}}

QTableWidget::item, QTableWidget#dataTable::item {{
    padding: 8px 14px;
    border: none;
    /* 不写死 color，以便业务侧 setForeground（紧急红/普通蓝/完成绿）生效 */
}}

QTableWidget::item:selected, QTableWidget#dataTable::item:selected {{
    background-color: {COLOR_TABLE_SELECT};
}}

QTableWidget::item:hover, QTableWidget#dataTable::item:hover {{
    background-color: {COLOR_TABLE_HOVER};
}}

QHeaderView#dataTableHeader::section,
QTableWidget QHeaderView::section,
QTableWidget#dataTable QHeaderView::section {{
    background-color: {COLOR_TABLE_HEADER};
    color: {COLOR_TABLE_HEADER_TEXT};
    border: none;
    border-right: 1px solid rgba(255, 255, 255, 40);
    border-bottom: none;
    padding: 10px 14px;
    font-weight: 700;
}}

QHeaderView#dataTableHeader::section:first,
QTableWidget QHeaderView::section:first {{
    border-top-left-radius: 13px;
}}

QHeaderView#dataTableHeader::section:last,
QTableWidget QHeaderView::section:last {{
    border-top-right-radius: 13px;
    border-right: none;
}}

QTableCornerButton::section {{
    background-color: {COLOR_TABLE_HEADER};
    border: none;
}}

/* 表格内细款暖棕滚动条 */
QTableWidget QScrollBar:vertical,
QTableWidget#dataTable QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px 4px 0;
}}

QTableWidget QScrollBar::handle:vertical,
QTableWidget#dataTable QScrollBar::handle:vertical {{
    background: #c9b09c;
    border-radius: 4px;
    min-height: 28px;
}}

QTableWidget QScrollBar::handle:vertical:hover,
QTableWidget#dataTable QScrollBar::handle:vertical:hover {{
    background: {COLOR_TABLE_HEADER};
}}

QTableWidget QScrollBar::add-line:vertical,
QTableWidget QScrollBar::sub-line:vertical,
QTableWidget QScrollBar::add-page:vertical,
QTableWidget QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0;
    border: none;
}}

QTableWidget QScrollBar:horizontal,
QTableWidget#dataTable QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0 4px 2px 4px;
}}

QTableWidget QScrollBar::handle:horizontal,
QTableWidget#dataTable QScrollBar::handle:horizontal {{
    background: #c9b09c;
    border-radius: 4px;
    min-width: 28px;
}}

QTableWidget QScrollBar::handle:horizontal:hover {{
    background: {COLOR_TABLE_HEADER};
}}

QTableWidget QScrollBar::add-line:horizontal,
QTableWidget QScrollBar::sub-line:horizontal,
QTableWidget QScrollBar::add-page:horizontal,
QTableWidget QScrollBar::sub-page:horizontal {{
    background: transparent;
    width: 0;
    border: none;
}}

/* ===== 标签页（米色导航 · 白底选中 · 无黑色块） ===== */
QWidget#dissolveTabWidget {{
    background-color: {COLOR_BG};
}}

QFrame#dissolveTabPane {{
    border: none;
    background-color: {COLOR_BG};
}}

QTabWidget::pane {{
    border: none;
    background-color: {COLOR_BG};
    top: 0px;
}}

/* 主导航：整条米色底，杜绝透明透出系统黑底 */
QTabBar#mainNavTabBar {{
    background-color: {COLOR_BG};
    border: none;
    border-bottom: 1px solid {COLOR_DIVIDER};
    min-height: 40px;
}}

QTabBar#mainNavTabBar::tab {{
    background-color: {COLOR_BG};
    color: #4a453e;
    border: none;
    border-radius: 8px 8px 0 0;
    padding: 8px 18px;
    margin: 4px 4px 0 0;
    min-width: 88px;
    min-height: 28px;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 10pt;
    font-weight: 500;
}}

QTabBar#mainNavTabBar::tab:hover {{
    color: #3d3830;
    background-color: #ebe3d6;
}}

QTabBar#mainNavTabBar::tab:selected {{
    background-color: #ffffff;
    color: #2e2a24;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 10pt;
    font-weight: 700;
    border: 1px solid {COLOR_DIVIDER};
    border-bottom: 1px solid #ffffff;
    border-radius: 8px 8px 0 0;
    padding: 8px 18px;
    margin: 4px 4px 0 0;
}}

/* 仅作用于真正的 QTabWidget 内 TabBar，勿叠加到 #mainNavTabBar */
QTabWidget > QTabBar {{
    background-color: {COLOR_BG};
    border: none;
}}

QTabWidget > QTabBar::tab {{
    background-color: {COLOR_BG};
    color: #4a453e;
    border: none;
    border-radius: 8px 8px 0 0;
    padding: 8px 16px;
    margin-right: 4px;
    min-width: 88px;
}}

QTabWidget > QTabBar::tab:hover {{
    color: #3d3830;
    background-color: #ebe3d6;
}}

QTabWidget > QTabBar::tab:selected {{
    color: #2e2a24;
    font-weight: bold;
    background-color: #ffffff;
    border: 1px solid {COLOR_DIVIDER};
    border-bottom: 1px solid #ffffff;
}}

/* ===== 日历 ===== */
QCalendarWidget {{
    background-color: {COLOR_BG};
    border: 1px solid {COLOR_DIVIDER};
    border-radius: 4px;
}}

QCalendarWidget QWidget {{
    alternate-background-color: {COLOR_ASSIST};
}}

QCalendarWidget QAbstractItemView {{
    selection-background-color: {COLOR_PRIMARY};
    selection-color: #ffffff;
    outline: none;
}}

QCalendarWidget QToolButton {{
    background-color: {COLOR_BG};
    color: {COLOR_PRIMARY};
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: bold;
}}

QCalendarWidget QToolButton:hover {{
    background-color: {COLOR_ASSIST};
}}

QCalendarWidget QSpinBox {{
    background: {COLOR_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
}}

QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {COLOR_ASSIST};
    border-bottom: 1px solid {COLOR_DIVIDER};
}}

/* ===== 班级日志纸质日历（护眼浅米黄） ===== */
QWidget#logCalendar {{
    background-color: transparent;
    border: none;
}}

QLabel#logCalTitle {{
    color: #2e2e2e;
    font-family: "Source Han Serif SC", "Noto Serif CJK SC", "思源宋体",
                 "方正仿宋", "FangSong", "STFangsong", "SimSun", serif;
    font-size: 16pt;
    font-weight: 500;
    letter-spacing: 3px;
}}

QLabel#logCalWeekday {{
    color: #6e675e;
    font-family: "Microsoft YaHei", "SimHei", "黑体", "Segoe UI", sans-serif;
    font-size: 9pt;
    font-weight: 700;
    padding: 4px 0 2px 0;
}}

QLabel#logCalLegend {{
    color: #5a8fc4;
    font-size: 9pt;
    font-weight: 500;
    padding: 0 2px 2px 2px;
}}

QPushButton#logCalNavBtn {{
    background-color: {COLOR_BTN};
    background: {_BTN_BG};
    color: #ffffff;
    border: 1px solid {COLOR_BTN_BORDER};
    border-radius: 12px;
    padding: 4px 12px;
    font-family: {_BTN_FONT_TOKEN};
    font-size: {BUTTON_FONT_SIZE_PT}pt;
    font-weight: 700;
    min-width: 80px;
    min-height: 32px;
}}

QPushButton#logCalNavBtn:hover {{
    background-color: {COLOR_BTN_HOVER};
    background: {_BTN_BG_HOVER};
    border-color: {COLOR_BTN_HOVER_BORDER};
    color: #ffffff;
}}

QPushButton#logCalNavBtn:pressed {{
    background-color: {COLOR_BTN_PRESSED};
    background: {_BTN_BG_PRESSED};
    border-color: {COLOR_BTN_PRESSED_BORDER};
}}

QPushButton#logCalNavBtn:disabled {{
    background-color: {COLOR_BTN_DISABLED};
    background: {_BTN_BG_DISABLED};
    color: {COLOR_BTN_DISABLED_TEXT};
    border-color: {COLOR_BTN_DISABLED_BORDER};
}}

QFrame#logCalViewport {{
    background-color: transparent;
    border: none;
}}

QFrame#logCalMonthPanel {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
}}

QFrame#logCalGridHost {{
    background-color: {COLOR_BG};
    border: none;
    border-radius: 8px;
}}

QWidget#logCalDayCell {{
    background-color: transparent;
    border: none;
    min-width: 42px;
    min-height: 40px;
}}

/* ===== 状态栏 / 菜单 ===== */
QStatusBar {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_SECONDARY};
    border-top: 1px solid {COLOR_DIVIDER};
}}

QMenu {{
    background-color: {COLOR_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 6px 4px;
}}

QMenu::item {{
    padding: 8px 18px;
    border-radius: 6px;
    color: {COLOR_TEXT};
}}

QMenu::item:selected {{
    background-color: {COLOR_ASSIST};
    color: {COLOR_TEXT};
}}

QMenu#logCalContextMenu {{
    background-color: #faf8f4;
    border: 1px solid #e0d8cc;
    border-radius: 10px;
    padding: 6px 4px;
}}

QMenu#logCalContextMenu::item {{
    padding: 8px 20px;
    border-radius: 6px;
    min-width: 140px;
}}

QMenu#logCalContextMenu::item:selected {{
    background-color: #ddd2c0;
    color: #5c4033;
}}

/* ===== 滚动条 ===== */
QScrollBar:vertical {{
    background: {COLOR_BG};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: #c9bfb0;
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_PRIMARY};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {COLOR_BG};
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background: #c9bfb0;
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ===== 弹窗 QMessageBox ===== */
QMessageBox {{
    background-color: {COLOR_BG};
}}

QMessageBox QLabel {{
    color: {COLOR_TEXT};
    min-width: 280px;
}}

QMessageBox QPushButton {{
    background-color: {COLOR_BTN};
    background: {_BTN_BG};
    color: #ffffff;
    border: 1px solid {COLOR_BTN_BORDER};
    border-radius: 12px;
    padding: 4px 12px;
    min-width: 80px;
    min-height: 32px;
    font-family: {_BTN_FONT_TOKEN};
    font-size: {BUTTON_FONT_SIZE_PT}pt;
    font-weight: 700;
}}

QMessageBox QPushButton:hover {{
    background-color: {COLOR_BTN_HOVER};
    background: {_BTN_BG_HOVER};
    border-color: {COLOR_BTN_HOVER_BORDER};
}}

QMessageBox QPushButton:pressed {{
    background-color: {COLOR_BTN_PRESSED};
    background: {_BTN_BG_PRESSED};
    border-color: {COLOR_BTN_PRESSED_BORDER};
}}

QDialogButtonBox QPushButton {{
    min-width: 80px;
    min-height: 32px;
    padding: 4px 12px;
    border-radius: 12px;
}}

/* ===== 班级日志新增/编辑弹窗（纸质日历同系圆角卡片） ===== */
QDialog#logFormDialog {{
    background-color: {COLOR_BG};
}}

QFrame#logFormSection {{
    background-color: #f5efe4;
    border: 1px solid #c9bfb0;
    border-radius: 12px;
}}

QLabel#logFormSectionTitle {{
    color: #3d3a34;
    font-size: 11pt;
    font-weight: 700;
    background: transparent;
}}

QLabel#logImagePreview {{
    background-color: #f7fbff;
    border: 1px dashed #a8c8ea;
    border-radius: 10px;
    color: #6e8aab;
    font-size: 9pt;
}}

/* ===== 日志图片预览窗 ===== */
QDialog#imagePreviewDialog {{
    background: transparent;
}}

QFrame#imagePreviewPanel {{
    background-color: #ffffff;
    border: 1px solid #d0e4f7;
    border-radius: 16px;
}}

QLabel#imagePreviewTitle {{
    color: #4086d6;
    font-size: 12pt;
    font-weight: 700;
    background: transparent;
}}

QLabel#imagePreviewHint {{
    color: #6e8aab;
    font-size: 9pt;
    background: transparent;
}}

QLabel#imagePreviewCanvas {{
    background-color: #f7fbff;
    border: 1px solid #e2eef9;
    border-radius: 10px;
}}

QRadioButton#logTypeRadio {{
    spacing: 6px;
    color: {COLOR_TEXT};
    background: transparent;
}}

QRadioButton#logTypeRadio::indicator {{
    width: 16px;
    height: 16px;
}}

QScrollArea#logStudentScroll {{
    background-color: #faf8f4;
    border: none;
    border-radius: 8px;
}}

/* 班级日志整页纵向滚动（与首页一致） */
QScrollArea#logPageScroll {{
    background-color: {COLOR_BG};
    border: none;
    padding: 0px;
}}

QWidget#logPageScrollInner {{
    background-color: {COLOR_BG};
}}

QScrollArea {{
    border: none;
    background-color: {COLOR_BG};
}}

QScrollArea#logPageScroll QScrollBar:vertical {{
    background: {COLOR_ASSIST};
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}}

QScrollArea#logPageScroll QScrollBar::handle:vertical {{
    background: #c9bfb0;
    border-radius: 5px;
    min-height: 28px;
}}

QScrollArea#logPageScroll QScrollBar::handle:vertical:hover {{
    background: {COLOR_PRIMARY};
}}

QScrollArea#logPageScroll QScrollBar::add-line:vertical,
QScrollArea#logPageScroll QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollArea#logPageScroll QScrollBar::add-page:vertical,
QScrollArea#logPageScroll QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QWidget#logStudentHost {{
    background-color: #faf8f4;
}}

QCheckBox#logStudentCheck {{
    spacing: 8px;
    padding: 4px 2px;
    color: {COLOR_TEXT};
    background: transparent;
}}

QCheckBox#logStudentCheck::indicator {{
    width: 16px;
    height: 16px;
}}

/* 文件对话框尽量贴近主题 */
QFileDialog {{
    background-color: {COLOR_BG};
}}

/* ===== 迷你模式紧凑布局 ===== */
QWidget#miniPanel {{
    background-color: {COLOR_BG};
    border: 1px solid #c9bfb0;
    border-radius: 10px;
}}

QToolBar {{
    background-color: {COLOR_BG};
    border-bottom: 1px solid {COLOR_DIVIDER};
    spacing: 8px;
    padding: 4px 8px;
}}

QToolBar QToolButton {{
    background-color: {COLOR_BTN};
    background: {_BTN_BG};
    color: #ffffff;
    border: 1px solid {COLOR_BTN_BORDER};
    border-radius: 10px;
    padding: 4px 12px;
    font-family: {_BTN_FONT_TOKEN};
    font-size: {BUTTON_FONT_SIZE_PT}pt;
    font-weight: 700;
}}

QToolBar QToolButton:hover {{
    background-color: {COLOR_BTN_HOVER};
    background: {_BTN_BG_HOVER};
    border-color: {COLOR_BTN_HOVER_BORDER};
}}

QToolBar QToolButton:pressed {{
    background-color: {COLOR_BTN_PRESSED};
    background: {_BTN_BG_PRESSED};
    border-color: {COLOR_BTN_PRESSED_BORDER};
}}

QFrame#miniTodoItem {{
    background-color: {COLOR_BG};
    border: 1px solid {COLOR_DIVIDER};
    border-radius: 4px;
}}

/* 迷你窗口：保留紧凑尺寸（大屏规则不压扁迷你窗） */
QWidget#miniPanel QPushButton {{
    font-family: {_BTN_FONT_TOKEN};
    font-size: 9pt;
    font-weight: 700;
    padding: 2px 8px;
    min-width: 48px;
    min-height: 22px;
    border-radius: 10px;
}}

QWidget#miniPanel QPushButton:pressed {{
    padding: 2px 8px;
}}
"""


def app_font():
    """统一应用字体。"""
    font = QFont()
    font.setFamilies(["Microsoft YaHei", "Segoe UI", "sans-serif"])
    font.setPointSize(FONT_SIZE_PT)
    return font


def get_global_qss() -> str:
    """返回已注入按钮字体的全局 QSS（需在 QApplication 创建后调用）。"""
    return GLOBAL_QSS.replace(_BTN_FONT_TOKEN, _button_font_css())


def apply_app_style(app: QApplication):
    """
    在 QApplication 上加载全局 QSS（推荐入口处调用一次）。
    使用 Fusion 样式以便 QSS 在 Windows 上可靠生效（含 QMessageBox）。
    """
    app.setStyle("Fusion")
    app.setFont(app_font())
    app.setStyleSheet(get_global_qss())


def apply_widget_style(widget):
    """单个窗口/对话框补充应用全局样式（一般应用级已足够）。"""
    widget.setStyleSheet(get_global_qss())


def set_secondary_button(button: QPushButton):
    """标记为次要按钮（视觉已与主按钮统一为棕色 Q 版）。"""
    button.setProperty("secondary", True)
    button.style().unpolish(button)
    button.style().polish(button)


def set_danger_button(button: QPushButton):
    """标记为警示按钮（视觉已与主按钮统一为棕色 Q 版）。"""
    button.setProperty("danger", True)
    button.style().unpolish(button)
    button.style().polish(button)


def styled_information(parent, title, text):
    """主题化信息框。"""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStyleSheet(get_global_qss())
    return box.exec()


def styled_warning(parent, title, text):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStyleSheet(get_global_qss())
    return box.exec()


def styled_critical(parent, title, text):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStyleSheet(get_global_qss())
    return box.exec()


def styled_question(parent, title, text):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    box.setDefaultButton(QMessageBox.StandardButton.No)
    box.setStyleSheet(get_global_qss())
    return box.exec()
