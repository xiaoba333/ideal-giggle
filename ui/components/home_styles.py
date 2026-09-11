# -*- coding: utf-8 -*-
"""首页模块 QSS 与艺术字体兼容工具。"""

from PyQt6.QtGui import QFont, QFontDatabase

from ui.styles import (
    COLOR_PRIMARY, COLOR_ASSIST, COLOR_BG, COLOR_TEXT,
    COLOR_TEXT_SECONDARY, COLOR_DIVIDER, COLOR_DANGER,
)

# 艺术字体候选（Windows 常见 / 开源中文字体），按优先级
ART_FONT_CANDIDATES = [
    "Source Han Sans SC",
    "思源黑体",
    "Noto Sans CJK SC",
    "HYXinRenWenSongJ",
    "汉仪细圆简",
    "汉仪细圆",
    "YouYuan",
    "幼圆",
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "Segoe UI",
]

_resolved_art_font = None


def resolve_art_font_family():
    """查找可用艺术字体，缺失时回退系统默认无衬线字体。"""
    global _resolved_art_font
    if _resolved_art_font is not None:
        return _resolved_art_font

    try:
        available = set(QFontDatabase.families())
    except Exception:
        _resolved_art_font = "Microsoft YaHei"
        return _resolved_art_font

    for name in ART_FONT_CANDIDATES:
        if name in available:
            _resolved_art_font = name
            return _resolved_art_font

    _resolved_art_font = "Microsoft YaHei"
    return _resolved_art_font


def make_art_font(point_size=12, bold=False):
    """生成滚动屏用艺术字体。"""
    font = QFont(resolve_art_font_family(), point_size)
    font.setBold(bold)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


HOME_MODULE_QSS = f"""
/* ----- 水滴凸起卡片外壳 ----- */
QFrame#dropletCard {{
    background-color: transparent;
    border: none;
    min-width: 200px;
}}

QFrame#dropletInner {{
    background-color: #f5efe4;
    border: 1px solid #c9bfb0;
    border-radius: 24px;
    padding: 4px;
}}

QLabel#dropletTitle {{
    color: {COLOR_PRIMARY};
    font-size: 11pt;
    font-weight: bold;
    background: transparent;
}}

QLabel#dropletMain {{
    color: {COLOR_TEXT};
    font-size: 20pt;
    font-weight: bold;
    background: transparent;
    padding: 2px 0;
}}

QLabel#dateYmd {{
    color: {COLOR_TEXT};
    font-family: "Courier New", monospace;
    font-size: 18pt;
    font-weight: bold;
    background: transparent;
    padding: 2px 0;
    qproperty-alignment: AlignCenter;
}}

QLabel#dropletSub {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 10pt;
    background: transparent;
    padding: 2px 0;
}}

QLabel#dateWeekday {{
    color: {COLOR_PRIMARY};
    font-size: 14pt;
    font-weight: bold;
    background: transparent;
    padding: 4px 0;
    qproperty-alignment: AlignCenter;
}}

QLabel#dateClock {{
    color: #8b5e3c;
    font-family: "Courier New", monospace;
    font-size: 60pt;
    font-weight: bold;
    background: transparent;
    padding: 12px 0 16px 0;
    qproperty-alignment: AlignCenter;
}}

QLabel#dateClockCompact {{
    color: #8b5e3c;
    font-family: "Courier New", monospace;
    font-size: 34pt;
    font-weight: bold;
    background: transparent;
    padding: 0;
    qproperty-alignment: AlignCenter;
}}

QLabel#weatherCondition {{
    color: {COLOR_PRIMARY};
    font-size: 16pt;
    font-weight: bold;
    background: transparent;
    padding: 2px 0;
}}

QLabel#weatherTemp {{
    color: {COLOR_TEXT};
    font-size: 26pt;
    font-weight: bold;
    background: transparent;
    padding: 2px 0 6px 0;
}}

QLabel#weatherBody {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11pt;
    background: transparent;
    line-height: 1.4;
    padding: 2px 0;
}}

QFrame#weatherDivider {{
    background-color: {COLOR_DIVIDER};
    border: none;
    max-height: 1px;
}}

QWidget#weatherIcon {{
    background: transparent;
}}

QLineEdit#weatherCityEdit {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid #c5d8ef;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 26px;
}}

QLineEdit#weatherCityEdit:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}

/* ----- 待办滚动显示屏外框 ----- */
QFrame#todoScrollShell {{
    background-color: #eef4fb;
    border: 3px solid {COLOR_PRIMARY};
    border-radius: 12px;
}}

QFrame#todoScrollBezel {{
    background-color: #1a3a5c;
    border: 2px solid #2c5a8a;
    border-radius: 8px;
}}

QWidget#todoScrollViewport {{
    background-color: #0f2740;
    border-radius: 4px;
}}

QLabel#todoScrollCaption {{
    color: {COLOR_PRIMARY};
    font-weight: bold;
    font-size: 11pt;
    background: transparent;
}}

QLabel#todoScrollHint {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 9pt;
    background: transparent;
}}

QLabel#todoScrollColumnTitle {{
    color: {COLOR_PRIMARY};
    font-weight: bold;
    font-size: 10pt;
    background: transparent;
}}

/* ----- 班级日志卡片流 ----- */
QFrame#logFlowCard {{
    background-color: {COLOR_BG};
    border: 1px solid {COLOR_DIVIDER};
    border-radius: 10px;
    padding: 4px;
    min-height: 64px;
}}

QLabel#logFlowDate {{
    color: {COLOR_PRIMARY};
    font-weight: bold;
    background: transparent;
}}

QLabel#logFlowTitle {{
    color: {COLOR_TEXT};
    font-size: 11pt;
    font-weight: bold;
    background: transparent;
}}

QLabel#logFlowContent {{
    color: {COLOR_TEXT_SECONDARY};
    background: transparent;
}}

QLabel#logFlowParticipants {{
    color: {COLOR_PRIMARY};
    font-size: 9pt;
    background: transparent;
}}

QLabel#logFlowThumb {{
    background-color: #f7fbff;
    border: 1px solid #d0e4f7;
    border-radius: 6px;
    color: {COLOR_PRIMARY};
    font-size: 8pt;
    max-width: 40px;
    max-height: 40px;
}}

QPushButton#logFlowViewImage {{
    min-height: 26px;
    padding: 3px 12px;
    font-size: 10pt;
    border-radius: 10px;
}}

QScrollArea#logFlowScroll {{
    background: transparent;
    border: none;
}}

QWidget#logFlowHost {{
    background: transparent;
}}

QWidget#homeRoot {{
    background-color: {COLOR_BG};
}}

QWidget#homeScrollInner, QWidget#miniScrollInner {{
    background-color: {COLOR_BG};
    padding: 4px;
}}

QScrollArea#homeScroll, QScrollArea#miniScroll {{
    background-color: {COLOR_BG};
    border: none;
    padding: 0px;
}}

QScrollArea#homeScroll > QWidget > QWidget,
QScrollArea#miniScroll > QWidget > QWidget {{
    background-color: {COLOR_BG};
}}

/* 蓝白主题滚动条 */
QScrollArea#homeScroll QScrollBar:vertical,
QScrollArea#miniScroll QScrollBar:vertical {{
    background: {COLOR_ASSIST};
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}}

QScrollArea#homeScroll QScrollBar::handle:vertical,
QScrollArea#miniScroll QScrollBar::handle:vertical {{
    background: #9bbfe8;
    border-radius: 5px;
    min-height: 28px;
}}

QScrollArea#homeScroll QScrollBar::handle:vertical:hover,
QScrollArea#miniScroll QScrollBar::handle:vertical:hover {{
    background: {COLOR_PRIMARY};
}}

QScrollArea#homeScroll QScrollBar::add-line:vertical,
QScrollArea#homeScroll QScrollBar::sub-line:vertical,
QScrollArea#miniScroll QScrollBar::add-line:vertical,
QScrollArea#miniScroll QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollArea#homeScroll QScrollBar::add-page:vertical,
QScrollArea#homeScroll QScrollBar::sub-page:vertical,
QScrollArea#miniScroll QScrollBar::add-page:vertical,
QScrollArea#miniScroll QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QLabel {{
    background: transparent;
}}

/* 迷你窗口：放大字号，便于横屏小窗阅读 */
QWidget#miniPanel {{
    font-size: 11pt;
    background-color: {COLOR_BG};
    border: 1px solid #c9bfb0;
    border-radius: 10px;
}}

QCheckBox#miniPinCheck {{
    font-size: 8pt;
    spacing: 2px;
    padding: 0;
    margin: 0;
    color: {COLOR_TEXT_SECONDARY};
    background: transparent;
}}

QCheckBox#miniPinCheck::indicator {{
    width: 11px;
    height: 11px;
}}

QPushButton#miniSwitchBtn {{
    font-size: 8pt;
    font-weight: 700;
    padding: 1px 6px;
    min-height: 16px;
    max-height: 18px;
    border-radius: 8px;
}}

QPushButton#miniSwitchBtn:pressed {{
    padding: 2px 4px 0px 8px;
}}

QWidget#miniPanel QLabel#pageTitle {{
    font-size: 13pt;
}}

QWidget#miniPanel QLabel#dropletTitle {{
    font-size: 13pt;
}}

QWidget#miniPanel QLabel#dropletMain {{
    font-size: 18pt;
    padding: 0;
}}

QWidget#miniPanel QLabel#dateYmd {{
    font-size: 18pt;
    padding: 0;
}}

QWidget#miniPanel QLabel#dateWeekday {{
    font-size: 14pt;
    padding: 0;
}}

QWidget#miniPanel QLabel#dateClock {{
    color: #8b5e3c;
    font-size: 32pt;
    padding: 0;
}}

QWidget#miniPanel QLabel#dateClockCompact {{
    color: #8b5e3c;
    font-size: 34pt;
    font-weight: 700;
    padding: 0;
    margin: 0;
    background: transparent;
    qproperty-alignment: AlignCenter;
}}

QWidget#miniPanel QLabel#weatherTemp {{
    color: #5c4033;
    font-size: 12pt;
    font-weight: 700;
    padding: 0;
    background: transparent;
}}

QWidget#miniPanel QLabel#dropletSub {{
    font-size: 11pt;
}}

QWidget#miniPanel QLabel#todoScrollCaption {{
    font-size: 12pt;
}}

QWidget#miniPanel QFrame#dropletCard {{
    border-radius: 14px;
    background: transparent;
}}

QWidget#miniPanel QFrame#dropletInner {{
    border-radius: 12px;
    background-color: {COLOR_BG};
}}

QWidget#miniPanel QLabel#weatherCondition {{
    color: {COLOR_TEXT};
    font-size: 14pt;
    font-weight: 700;
    padding: 0;
    background: transparent;
}}

QWidget#miniPanel QLabel#weatherBody {{
    font-size: 11pt;
}}

QWidget#miniPanel QCheckBox {{
    font-size: 8pt;
}}

QWidget#miniPanel QPushButton {{
    font-size: 8pt;
    font-weight: 700;
    padding: 1px 6px;
    min-height: 16px;
    border-radius: 8px;
}}
"""
