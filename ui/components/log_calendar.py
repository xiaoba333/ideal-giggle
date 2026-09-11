# -*- coding: utf-8 -*-
"""
班级日志纸质风格日历（API 对齐 PySide6 Signal，本项目使用 PyQt6）。

- 米黄纸张悬浮立体：外阴影 + 内阴影 + 格子浮雕纹理
- 有日志：左上角浅蓝手写 #（外发光）；待办：红线下带淡影（最多3层）
- 邻月凹陷降亮；今日/选中内侧发光
- 月份上下滑动翻页；对外 set_log_dates / set_todo_deadlines / date_selected / month_changed
"""

from __future__ import annotations

from calendar import Calendar
from datetime import timedelta
from typing import Iterable, Optional, Set

from PyQt6.QtCore import (
    Qt, QDate, QPoint, QRect, QSize, pyqtSignal, QEvent, QTimer,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QAbstractAnimation,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics, QFontDatabase,
    QLinearGradient, QBrush, QAction, QRegion,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QMenu,
)

WEEKDAY_LABELS = ("一", "二", "三", "四", "五", "六", "日")
ANIM_MS = 320

# 纸质色板（统一米色 #f2ebe0 系 · 低亮度护眼）
_PAPER_CELL = QColor("#efe8dc")          # 格内略深
_PAPER_CELL_HI = QColor("#f5f0e8")       # 格内极淡亮
_PAPER_CELL_DEEP = QColor("#e8e0d4")
_PAPER_OUT = QColor("#e6ddd0")           # 邻月凹陷
_PAPER_OUT_DEEP = QColor("#dcd3c6")
_BORDER = QColor("#d4cbc0")              # 柔和浅棕灰边框（弱化生硬线）
_LINE_HI = QColor(245, 240, 230, 90)     # 浮雕高光
_LINE_LO = QColor(150, 138, 118, 55)     # 浮雕暗边
_INK = QColor("#2e2e2e")                 # 本月数字
_INK_MUTED = QColor("#7a7268")           # 邻月灰
_INK_SELECTED = QColor("#3d6a9e")        # 选中数字
_HASH_BLUE = QColor("#5a8fc4")           # 日志 #
_HASH_GLOW = QColor(90, 143, 196, 45)
_TODAY_BORDER = QColor("#6a92c0")
_SELECTED_BG = QColor(106, 146, 192, 32)
_TODO_RED = QColor("#b54a4a")
_TODO_SHADOW = QColor(140, 80, 70, 50)
_PAGE_BG = QColor("#f2ebe0")

# 复用画笔（避免 paintEvent 内反复构造）
_PEN_NONE = QPen(Qt.PenStyle.NoPen)
_PEN_BORDER = QPen(_BORDER, 1)
_PEN_LINE_HI = QPen(_LINE_HI, 1)
_PEN_LINE_LO = QPen(_LINE_LO, 1)
_PEN_TODAY = QPen(_TODAY_BORDER, 1)
_PEN_TODAY_SEL = QPen(_TODAY_BORDER, 2)
_PEN_TODO_SHADOW = QPen(_TODO_SHADOW, 2)
_PEN_TODO_RED = QPen(_TODO_RED, 2)
_PEN_HASH = QPen(_HASH_BLUE, 1)
_PEN_HASH_EDGE = QPen(QColor(90, 143, 196, 180), 1)
_PEN_STRIPE_IN = QPen(QColor(140, 125, 100, 8), 1)
_PEN_STRIPE_OUT = QPen(QColor(140, 125, 100, 14), 1)
_BRUSH_SELECTED = QBrush(_SELECTED_BG)
_BRUSH_CELL = QBrush(_PAPER_CELL)
_BRUSH_CELL_OUT = QBrush(_PAPER_OUT)

# 预创建选中光晕 / 邻月内阴影画笔
_PENS_FOCUS_OUTER = [QPen(QColor(106, 146, 192, a), 1) for a in (18, 10, 4)]
_PENS_FOCUS_INNER = [QPen(QColor(106, 146, 192, a), 1) for a in (36, 18, 8)]
_PENS_OUT_INSET = [QPen(QColor(110, 95, 75, a), 1) for a in (24, 14, 6)]
_PENS_INNER_SHADE = [QPen(QColor(150, 130, 100, a), 1) for a in (14, 8, 3)]
_PENS_HASH_GLOW = [
    QPen(QColor(90, 143, 196, 30), 1),
    QPen(QColor(90, 143, 196, 30), 1),
    QPen(QColor(90, 143, 196, 34), 1),
    QPen(QColor(90, 143, 196, 38), 1),
    QPen(_HASH_GLOW, 1),
    QPen(QColor(70, 120, 170, 32), 1),
]
_HASH_GLOW_PTS = (
    QPoint(-2, 0), QPoint(2, 0), QPoint(0, -1),
    QPoint(0, 2), QPoint(1, 1), QPoint(-1, 1),
)
_PENS_TODO_LAYER = [
    QPen(QColor(181, 74, 74, 255), 2),
    QPen(QColor(181, 74, 74, 230), 2),
    QPen(QColor(181, 74, 74, 205), 2),
]

_FONT_DAY = None
_FONT_DAY_HEAVY = None
_FONT_HASH = None


def _cached_day_fonts():
    global _FONT_DAY, _FONT_DAY_HEAVY
    if _FONT_DAY is None:
        _FONT_DAY = _day_font(12, heavier=False)
        _FONT_DAY_HEAVY = _day_font(12, heavier=True)
    return _FONT_DAY, _FONT_DAY_HEAVY


def _cached_hash_font():
    global _FONT_HASH
    if _FONT_HASH is None:
        font = QFont("Segoe Script")
        if not QFontMetrics(font).inFont("#"):
            font = QFont("Comic Sans MS")
        if font.family() not in ("Segoe Script", "Comic Sans MS"):
            font = QFont("Microsoft YaHei")
        font.setPointSize(10)
        font.setItalic(True)
        font.setWeight(QFont.Weight.DemiBold)
        _FONT_HASH = font
    return _FONT_HASH

# 年月标题：松弛印刷宋体 / 仿宋（按本机可用字体回退）
_TITLE_FONT_CANDIDATES = (
    "Source Han Serif SC",
    "Noto Serif CJK SC",
    "思源宋体",
    "Source Han Serif CN",
    "方正仿宋",
    "方正仿宋_GBK",
    "FZFangSong-Z02",
    "FangSong",
    "STFangsong",
    "华文仿宋",
    "SimSun",
    "宋体",
)
_resolved_title_family: Optional[str] = None


def _resolve_title_family() -> str:
    global _resolved_title_family
    if _resolved_title_family is not None:
        return _resolved_title_family
    try:
        available = set(QFontDatabase.families())
    except Exception:
        _resolved_title_family = "SimSun"
        return _resolved_title_family
    for name in _TITLE_FONT_CANDIDATES:
        if name in available:
            _resolved_title_family = name
            return _resolved_title_family
    _resolved_title_family = "SimSun"
    return _resolved_title_family


def _day_font(point_size: int = 12, heavier: bool = False) -> QFont:
    """日期数字：Courier New 等宽打字机，setBold 加粗（禁止原生 Courier）。"""
    font = QFont("Courier New")
    font.setPointSize(point_size)
    font.setFixedPitch(True)
    font.setBold(True)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def _title_font(point_size: int = 17) -> QFont:
    """年月标题：思源宋体 Medium / 方正仿宋，松弛印刷感。"""
    font = QFont(_resolve_title_family())
    font.setPointSize(point_size)
    font.setWeight(QFont.Weight.Medium)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


class DayCell(QWidget):
    """日期格：纸片立体感、数字、红线与左上角手写 #（仅在 paintEvent 内绘制）。"""

    clicked = pyqtSignal(object)  # QDate

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date: Optional[QDate] = None
        self._in_month = True
        self._has_log = False
        self._todo_count = 0
        self._is_today = False
        self._is_selected = False
        self.setObjectName("logCalDayCell")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 固定最小尺寸，网格缩放时保持规整、不挤压错位
        self.setMinimumSize(42, 40)

    def sizeHint(self):
        return QSize(48, 44)

    def minimumSizeHint(self):
        return QSize(42, 40)

    def _mark_dirty(self, schedule_update: bool = True):
        if schedule_update:
            self.update()

    def set_day(self, date: Optional[QDate], in_month: bool, schedule_update: bool = True):
        self._date = date
        self._in_month = in_month
        self.setEnabled(bool(date and date.isValid()))
        self._mark_dirty(schedule_update)

    def set_has_log(self, has_log: bool, schedule_update: bool = True):
        self._has_log = bool(has_log)
        self._mark_dirty(schedule_update)

    def set_todo_count(self, count: int, schedule_update: bool = True):
        """当天待办截止数量；下划线最多画 3 条。"""
        try:
            self._todo_count = max(0, int(count))
        except (TypeError, ValueError):
            self._todo_count = 0
        self._mark_dirty(schedule_update)

    def set_today(self, is_today: bool, schedule_update: bool = True):
        self._is_today = bool(is_today)
        self._mark_dirty(schedule_update)

    def set_selected(self, selected: bool, schedule_update: bool = True):
        self._is_selected = bool(selected)
        self._mark_dirty(schedule_update)

    def date(self) -> Optional[QDate]:
        return self._date

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._date and self._date.isValid():
            self.clicked.emit(self._date)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 所有绘制、translate、坐标变换代码写在这里
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        cell_rect = QRect(0, 0, w, h)
        self._paint_cell_background(painter, cell_rect)
        if not self._date or not self._date.isValid():
            return
        self._paint_day_number(painter, cell_rect)
        self._paint_todo_underline(painter, cell_rect)
        if self._has_log and self._in_month:
            self._paint_hash_mark(painter, cell_rect)

    def _paint_cell_background(self, painter: QPainter, cell_rect: QRect):
        w = cell_rect.width()
        h = cell_rect.height()
        inner = cell_rect.adjusted(1, 1, -1, -1)

        # 固定色填充（视觉接近原渐变，避免滚动时重复算渐变；缓存后只建一次）
        painter.setPen(_PEN_NONE)
        if self._in_month:
            painter.setBrush(_BRUSH_CELL)
        else:
            painter.setBrush(_BRUSH_CELL_OUT)
        painter.drawRoundedRect(inner, 3, 3)

        # 竖纹（步长加大，减轻绘制量）
        stripe = _PEN_STRIPE_IN if self._in_month else _PEN_STRIPE_OUT
        painter.setPen(stripe)
        for x in range(inner.left() + 2, inner.right(), 4):
            painter.drawLine(QPoint(x, inner.top() + 1), QPoint(x, inner.bottom() - 1))

        if self._is_selected and self._date and self._date.isValid() and self._in_month:
            painter.setPen(_PEN_NONE)
            painter.setBrush(_BRUSH_SELECTED)
            painter.drawRoundedRect(inner.adjusted(1, 1, -1, -1), 3, 3)

        if self._in_month:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(_PEN_BORDER)
            painter.drawRoundedRect(inner, 3, 3)
            painter.setPen(_PEN_LINE_HI)
            painter.drawLine(QPoint(inner.left() + 1, inner.top() + 1),
                             QPoint(inner.right() - 1, inner.top() + 1))
            painter.drawLine(QPoint(inner.left() + 1, inner.top() + 1),
                             QPoint(inner.left() + 1, inner.bottom() - 1))
            painter.setPen(_PEN_LINE_LO)
            painter.drawLine(QPoint(inner.left() + 1, inner.bottom() - 1),
                             QPoint(inner.right() - 1, inner.bottom() - 1))
            painter.drawLine(QPoint(inner.right() - 1, inner.top() + 1),
                             QPoint(inner.right() - 1, inner.bottom() - 1))
            for i, pen in enumerate(_PENS_INNER_SHADE):
                y = inner.bottom() - 1 - i
                painter.setPen(pen)
                painter.drawLine(QPoint(inner.left() + 2, y), QPoint(inner.right() - 2, y))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(_PEN_BORDER)
            painter.drawRoundedRect(inner, 3, 3)
            for i, pen in enumerate(_PENS_OUT_INSET):
                painter.setPen(pen)
                painter.drawRoundedRect(inner.adjusted(i, i, -i, -i), 3, 3)

        if self._date and self._date.isValid() and (self._is_today or self._is_selected):
            focus = cell_rect.adjusted(2, 2, -2, -2)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i, pen in enumerate(_PENS_FOCUS_OUTER):
                painter.setPen(pen)
                painter.drawRoundedRect(focus.adjusted(-i, -i + 1, i, i + 1), 5, 5)
            painter.setPen(
                _PEN_TODAY if (self._is_today and not self._is_selected) else _PEN_TODAY_SEL
            )
            painter.drawRoundedRect(focus, 5, 5)
            for i, pen in enumerate(_PENS_FOCUS_INNER):
                painter.setPen(pen)
                painter.drawRoundedRect(
                    focus.adjusted(1 + i, 1 + i, -1 - i, -1 - i), 4, 4
                )

    def _paint_day_number(self, painter: QPainter, cell_rect: QRect):
        if self._in_month:
            ink = _INK_SELECTED if self._is_selected else _INK
        else:
            ink = _INK_MUTED
        font_n, font_h = _cached_day_fonts()
        painter.setFont(font_h if (self._is_today or self._is_selected) else font_n)
        day_rect = QRect(
            cell_rect.x(),
            cell_rect.y() + 6,
            cell_rect.width(),
            cell_rect.height() - 6,
        )
        text = str(self._date.day())
        if not self._in_month:
            painter.setPen(QColor(255, 255, 255, 35))
            painter.drawText(
                day_rect.adjusted(0, 1, 0, 1),
                Qt.AlignmentFlag.AlignCenter,
                text,
            )
        painter.setPen(ink)
        painter.drawText(day_rect, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_todo_underline(self, painter: QPainter, cell_rect: QRect):
        if not self._in_month:
            return
        n = min(int(self._todo_count or 0), 3)
        if n <= 0:
            return

        cx = int(cell_rect.x()) + int(cell_rect.width()) // 2
        base_y = int(cell_rect.y()) + int(cell_rect.height()) // 2 + 10
        half = 8
        gap = 3
        for i in range(n):
            y = base_y + i * gap
            painter.setPen(_PEN_TODO_SHADOW)
            painter.drawLine(QPoint(cx - half, y + 1), QPoint(cx + half, y + 1))
            painter.setPen(_PENS_TODO_LAYER[i])
            painter.drawLine(QPoint(cx - half, y), QPoint(cx + half, y))

    def _paint_hash_mark(self, painter: QPainter, cell_rect: QRect):
        painter.save()
        try:
            painter.translate(int(cell_rect.x()) + 5, int(cell_rect.y()) + 13)
            painter.rotate(-8)
            painter.setFont(_cached_hash_font())
            for pt, pen in zip(_HASH_GLOW_PTS, _PENS_HASH_GLOW):
                painter.setPen(pen)
                painter.drawText(pt, "#")
            painter.setPen(_PEN_HASH)
            painter.drawText(QPoint(0, 0), "#")
            painter.setPen(_PEN_HASH_EDGE)
            painter.drawText(QPoint(1, 0), "#")
        finally:
            painter.restore()


class MonthPanel(QFrame):
    """单月纸页（周标题 + 6×7 日期格）。"""

    date_clicked = pyqtSignal(object)  # QDate

    def __init__(self, year: int, month: int, parent=None):
        super().__init__(parent)
        self.setObjectName("logCalMonthPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        # try_set_widget_cache_mode(self)  # setCacheMode 已禁用
        self._year = year
        self._month = month
        self._log_dates: Set[str] = set()
        self._todo_counts: dict = {}
        self._selected: Optional[QDate] = None
        self._cells: list[DayCell] = []
        self._repaint_pending = False
        self._build()
        self._fill()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(0, 0, -1, -1)
        grad = QLinearGradient(0, 0, 0, max(1, r.height()))
        grad.setColorAt(0.0, QColor("#f5f0e8"))
        grad.setColorAt(1.0, _PAGE_BG)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(r, 10, 10)
        # 极淡描边，避免生硬外框
        painter.setPen(QPen(QColor(212, 203, 192, 90), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), 9, 9)

    def date_at(self, pos: QPoint) -> Optional[QDate]:
        """根据面板内坐标命中日期格；点在空白/非格子上返回 None。"""
        child = self.childAt(pos)
        while child is not None and child is not self:
            if isinstance(child, DayCell):
                d = child.date()
                if d is not None and d.isValid():
                    return QDate(d)
                return None
            child = child.parentWidget()
        return None

    def year(self) -> int:
        return self._year

    def month(self) -> int:
        return self._month

    def set_month(self, year: int, month: int):
        self._year = year
        self._month = month
        self._fill()

    def set_log_dates(self, dates: Iterable[str]):
        self._log_dates = {str(d) for d in dates if d}
        self._refresh_marks()

    def set_todo_deadlines(self, counts: dict):
        """key=YYYY-MM-DD, value=当天待办数量。"""
        self._todo_counts = {}
        for k, v in (counts or {}).items():
            key = str(k)
            try:
                self._todo_counts[key] = max(0, int(v))
            except (TypeError, ValueError):
                continue
        self._refresh_marks()

    def set_selected(self, date: Optional[QDate]):
        self._selected = date
        self._refresh_marks()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(6)

        week = QHBoxLayout()
        week.setSpacing(4)
        week.setContentsMargins(2, 0, 2, 2)
        for name in WEEKDAY_LABELS:
            lab = QLabel(name)
            lab.setObjectName("logCalWeekday")
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setMinimumHeight(22)
            week.addWidget(lab, 1)
        root.addLayout(week)

        # 网格布局规整 6×7，禁止像素绝对定位单元格
        grid_host = QFrame()
        grid_host.setObjectName("logCalGridHost")
        grid_host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setHorizontalSpacing(3)
        grid.setVerticalSpacing(3)
        for c in range(7):
            grid.setColumnStretch(c, 1)
            grid.setColumnMinimumWidth(c, 42)
        for r in range(6):
            grid.setRowStretch(r, 1)
            grid.setRowMinimumHeight(r, 40)
        for r in range(6):
            for c in range(7):
                cell = DayCell(grid_host)
                cell.clicked.connect(self.date_clicked.emit)
                grid.addWidget(cell, r, c)
                self._cells.append(cell)
        root.addWidget(grid_host, 1)

    def _fill(self):
        today = QDate.currentDate()
        cal = Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(self._year, self._month)
        days = [d for week in weeks for d in week]
        while len(days) < 42:
            days.append(days[-1] + timedelta(days=1))

        for idx, d in enumerate(days[:42]):
            cell = self._cells[idx]
            qd = QDate(d.year, d.month, d.day)
            in_month = d.month == self._month
            cell.set_day(qd, in_month, schedule_update=False)
            cell.set_today(qd == today, schedule_update=False)
            key = qd.toString("yyyy-MM-dd")
            cell.set_has_log(key in self._log_dates, schedule_update=False)
            cell.set_todo_count(self._todo_counts.get(key, 0), schedule_update=False)
            cell.set_selected(
                self._selected is not None
                and self._selected.isValid()
                and qd == self._selected,
                schedule_update=False,
            )
        self._schedule_cells_repaint()

    def _refresh_marks(self):
        today = QDate.currentDate()
        for cell in self._cells:
            qd = cell.date()
            if not qd or not qd.isValid():
                continue
            key = qd.toString("yyyy-MM-dd")
            cell.set_has_log(key in self._log_dates, schedule_update=False)
            cell.set_todo_count(self._todo_counts.get(key, 0), schedule_update=False)
            cell.set_today(qd == today, schedule_update=False)
            cell.set_selected(
                self._selected is not None
                and self._selected.isValid()
                and qd == self._selected,
                schedule_update=False,
            )
        self._schedule_cells_repaint()

    def _schedule_cells_repaint(self):
        """合并到下一事件循环再刷一次，避免瞬间 42 次 update 争抢。"""
        if self._repaint_pending:
            return
        self._repaint_pending = True
        QTimer.singleShot(0, self._flush_cells_repaint)

    def _flush_cells_repaint(self):
        self._repaint_pending = False
        for cell in self._cells:
            cell.update()


class LogCalendarWidget(QWidget):
    """
    纸质风格班级日志日历。

    Signals:
        date_selected(QDate)
        month_changed(int year, int month)  — 翻页动画结束后
        add_log_requested(QDate)   — 右键「新增班级日志」
        add_todo_requested(QDate)  — 右键「新增待办事项」
    """

    date_selected = pyqtSignal(object)
    month_changed = pyqtSignal(int, int)
    add_log_requested = pyqtSignal(object)
    add_todo_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("logCalendar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        # try_set_widget_cache_mode(self)  # setCacheMode 已禁用
        today = QDate.currentDate()
        self._year = today.year()
        self._month = today.month()
        self._selected = today
        self._log_dates: Set[str] = set()
        self._todo_deadlines: dict = {}
        self._show_todo_legend = False
        self._anim_group: Optional[QParallelAnimationGroup] = None
        self._outgoing: Optional[MonthPanel] = None
        self._pending_select: Optional[QDate] = None

        self._build_ui()
        self._update_title()
        self._update_legend()

    def paintEvent(self, event):
        """米色纸张底 + 柔和投影（无生硬黑边）。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        face = self.rect().adjusted(2, 1, -4, -6)

        for i, a in enumerate((28, 18, 10, 5)):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(120, 100, 75, a))
            painter.drawRoundedRect(face.adjusted(1 + i, 2 + i, 1 + i, 3 + i), 12, 12)

        r = face
        grad = QLinearGradient(0, 0, 0, max(1, r.height()))
        grad.setColorAt(0.0, QColor("#f7f2ea"))
        grad.setColorAt(0.5, _PAGE_BG)
        grad.setColorAt(1.0, QColor("#ebe3d6"))
        painter.setPen(QPen(QColor(212, 203, 192, 120), 1))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(r, 12, 12)

        painter.setPen(QPen(QColor(245, 240, 230, 70), 1))
        painter.drawLine(
            QPoint(r.left() + 14, r.top() + 2),
            QPoint(r.right() - 14, r.top() + 2),
        )

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(8)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        self.btn_prev = QPushButton("上月")
        self.btn_next = QPushButton("下月")
        self.btn_prev.setObjectName("logCalNavBtn")
        self.btn_next.setObjectName("logCalNavBtn")
        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_next.clicked.connect(self._on_next)

        self.lbl_title = QLabel()
        self.lbl_title.setObjectName("logCalTitle")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setFont(_title_font(17))

        nav.addWidget(self.btn_prev)
        nav.addWidget(self.lbl_title, 1)
        nav.addWidget(self.btn_next)
        root.addLayout(nav)

        legend = QLabel()
        legend.setObjectName("logCalLegend")
        self.lbl_legend = legend
        root.addWidget(legend)

        self.viewport = QFrame()
        self.viewport.setObjectName("logCalViewport")
        self.viewport.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.viewport.setMinimumHeight(280)
        self.viewport.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.viewport.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._panel = MonthPanel(self._year, self._month, self.viewport)
        self._panel.date_clicked.connect(self._on_cell_clicked)
        self._panel.set_selected(self._selected)
        root.addWidget(self.viewport, 1)

        self.viewport.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.viewport:
            et = event.type()
            if et == QEvent.Type.Resize:
                self._clip_viewport()
                if self._anim_group is None:
                    self._layout_panel(self._panel, 0)
                else:
                    # 动画中同步宽高，保持纵向偏移比例
                    h = self.viewport.height()
                    for p in (self._panel, self._outgoing):
                        if p is not None:
                            p.setFixedSize(self.viewport.size())
            # 滚轮不再翻月，交给外层页面滚动；翻月仅用「上月/下月」按钮
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._clip_viewport()
        if self._anim_group is None:
            self._layout_panel(self._panel, 0)

    def _clip_viewport(self):
        """裁剪翻页时滑出视口的面板。"""
        r = self.viewport.rect()
        if r.width() > 0 and r.height() > 0:
            self.viewport.setMask(QRegion(r))

    def _layout_panel(self, panel: MonthPanel, y: int = 0):
        size = self.viewport.size()
        if size.width() < 10 or size.height() < 10:
            return
        panel.setFixedSize(size)
        panel.move(0, y)
        panel.show()
        panel.raise_()

    def _update_title(self):
        self.lbl_title.setText(f"{self._year} 年 {self._month} 月")

    def _update_legend(self):
        if self._show_todo_legend:
            self.lbl_legend.setText("＃ 班级日志　　红色下划线 待办截止（最多3层）")
        else:
            self.lbl_legend.setText("左上角 ＃ 表示该日有班级日志")

    def set_show_todo_legend(self, enabled: bool):
        self._show_todo_legend = bool(enabled)
        self._update_legend()

    def _set_nav_enabled(self, enabled: bool):
        self.btn_prev.setEnabled(enabled)
        self.btn_next.setEnabled(enabled)

    def _apply_marks_to_panel(self, panel: MonthPanel):
        panel.set_log_dates(self._log_dates)
        panel.set_todo_deadlines(self._todo_deadlines)
        panel.set_selected(self._selected)

    # ---------- 对外 API ----------
    def set_log_dates(self, dates: Iterable[str]):
        """外部传入有日志的日期（YYYY-MM-DD），自动渲染 # 标记。"""
        self._log_dates = {str(d) for d in dates if d}
        self._panel.set_log_dates(self._log_dates)

    def set_todo_deadlines(self, counts: dict):
        """
        外部传入待办截止日期字典：
        key=YYYY-MM-DD，value=当天待办数量（下划线最多 3 条）。
        """
        self._todo_deadlines = {}
        for k, v in (counts or {}).items():
            try:
                self._todo_deadlines[str(k)] = max(0, int(v))
            except (TypeError, ValueError):
                continue
        self._panel.set_todo_deadlines(self._todo_deadlines)

    def log_dates(self) -> Set[str]:
        return set(self._log_dates)

    def todo_deadlines(self) -> dict:
        return dict(self._todo_deadlines)

    def selected_date(self) -> QDate:
        return QDate(self._selected)

    def set_selected_date(self, date: QDate, emit_signal: bool = False):
        if not date or not date.isValid():
            return
        self._selected = date
        need_page = date.year() != self._year or date.month() != self._month
        if need_page:
            self.set_current_page(date.year(), date.month(), animate=False)
        self._panel.set_selected(self._selected)
        if emit_signal:
            self.date_selected.emit(QDate(self._selected))

    def year_shown(self) -> int:
        return self._year

    def month_shown(self) -> int:
        return self._month

    def set_current_page(self, year: int, month: int, animate: bool = False):
        """翻到指定年月；animate=False 时即刻切换（程序定位日期用）。"""
        if year == self._year and month == self._month:
            return
        self._go_to_month(year, month, animate=animate)

    # ---------- 交互 ----------
    def contextMenuEvent(self, event):
        """仅在日期格子上弹出右键菜单；空白背景不弹出。"""
        qd = self._date_at_global(event.globalPos())
        if qd is None:
            event.ignore()
            return

        menu = QMenu(self)
        menu.setObjectName("logCalContextMenu")
        act_log = QAction("新增班级日志", menu)
        act_todo = QAction("新增待办事项", menu)
        menu.addAction(act_log)
        menu.addAction(act_todo)

        chosen = menu.exec(event.globalPos())
        if chosen is act_log:
            self._selected = qd
            self._panel.set_selected(self._selected)
            self.add_log_requested.emit(QDate(qd))
        elif chosen is act_todo:
            self._selected = qd
            self._panel.set_selected(self._selected)
            self.add_todo_requested.emit(QDate(qd))
        event.accept()

    def _date_at_global(self, global_pos: QPoint) -> Optional[QDate]:
        if self._panel is None:
            return None
        local = self._panel.mapFromGlobal(global_pos)
        if not self._panel.rect().contains(local):
            return None
        return self._panel.date_at(local)

    def _on_cell_clicked(self, date: QDate):
        if not date or not date.isValid():
            return
        self._selected = date
        if date.year() != self._year or date.month() != self._month:
            self._go_to_month(
                date.year(), date.month(), select_after=date, animate=True
            )
            return
        self._panel.set_selected(self._selected)
        self.date_selected.emit(QDate(date))

    def _on_prev(self):
        if self._anim_group is not None:
            return
        d = QDate(self._year, self._month, 1).addMonths(-1)
        self._go_to_month(d.year(), d.month(), animate=True)

    def _on_next(self):
        if self._anim_group is not None:
            return
        d = QDate(self._year, self._month, 1).addMonths(1)
        self._go_to_month(d.year(), d.month(), animate=True)

    def _stop_anim_now(self):
        """中断进行中的翻页，定格到目标月。"""
        group = self._anim_group
        if group is None:
            return
        self._anim_group = None
        try:
            group.finished.disconnect(self._on_anim_finished)
        except TypeError:
            pass
        group.stop()
        if self._outgoing is not None:
            try:
                self._outgoing.date_clicked.disconnect(self._on_cell_clicked)
            except TypeError:
                pass
            self._outgoing.hide()
            self._outgoing.deleteLater()
            self._outgoing = None
        self._layout_panel(self._panel, 0)
        self._set_nav_enabled(True)

    def _go_to_month(
        self,
        year: int,
        month: int,
        select_after: Optional[QDate] = None,
        animate: bool = True,
    ):
        """切换月份；上月↑新页从上滑入，下月↓新页从下滑入。"""
        if year == self._year and month == self._month:
            if select_after and select_after.isValid():
                self._selected = select_after
                self._panel.set_selected(self._selected)
                self.date_selected.emit(QDate(select_after))
            return

        going_next = QDate(year, month, 1) > QDate(self._year, self._month, 1)
        self._year = year
        self._month = month
        if select_after and select_after.isValid():
            self._selected = select_after
        self._pending_select = (
            QDate(select_after) if select_after and select_after.isValid() else None
        )
        self._update_title()

        h = self.viewport.height()
        can_anim = (
            animate
            and h >= 40
            and self.viewport.width() >= 40
            and self.isVisible()
        )

        if not can_anim:
            self._stop_anim_now()
            self._panel.set_month(year, month)
            self._apply_marks_to_panel(self._panel)
            self._layout_panel(self._panel, 0)
            self._set_nav_enabled(True)
            self.month_changed.emit(self._year, self._month)
            if self._pending_select is not None:
                self.date_selected.emit(self._pending_select)
                self._pending_select = None
            return

        self._stop_anim_now()

        old = self._panel
        new = MonthPanel(year, month, self.viewport)
        new.date_clicked.connect(self._on_cell_clicked)
        self._apply_marks_to_panel(new)

        self._outgoing = old
        self._panel = new

        # 下月：旧页上移、新页自下进入；上月相反
        if going_next:
            self._layout_panel(old, 0)
            self._layout_panel(new, h)
            old_end_y, new_end_y = -h, 0
        else:
            self._layout_panel(old, 0)
            self._layout_panel(new, -h)
            old_end_y, new_end_y = h, 0

        self._set_nav_enabled(False)

        anim_old = QPropertyAnimation(old, b"pos", self)
        anim_old.setDuration(ANIM_MS)
        anim_old.setStartValue(QPoint(0, old.y()))
        anim_old.setEndValue(QPoint(0, old_end_y))
        anim_old.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim_new = QPropertyAnimation(new, b"pos", self)
        anim_new.setDuration(ANIM_MS)
        anim_new.setStartValue(QPoint(0, new.y()))
        anim_new.setEndValue(QPoint(0, new_end_y))
        anim_new.setEasingCurve(QEasingCurve.Type.InOutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_old)
        group.addAnimation(anim_new)
        self._anim_group = group
        group.finished.connect(self._on_anim_finished)
        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_anim_finished(self):
        self._anim_group = None
        if self._outgoing is not None:
            try:
                self._outgoing.date_clicked.disconnect(self._on_cell_clicked)
            except TypeError:
                pass
            self._outgoing.hide()
            self._outgoing.deleteLater()
            self._outgoing = None
        self._layout_panel(self._panel, 0)
        self._set_nav_enabled(True)
        self.month_changed.emit(self._year, self._month)
        if self._pending_select is not None:
            self.date_selected.emit(self._pending_select)
            self._pending_select = None
