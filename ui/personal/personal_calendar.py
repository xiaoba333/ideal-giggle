# -*- coding: utf-8 -*-
"""个人模式森系日历：大单元格 + 石碑里程碑 + 手绘心情表情。"""

from __future__ import annotations

from calendar import Calendar
from typing import Iterable, Optional, Dict, Set

from PyQt6.QtCore import Qt, QDate, QRect, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QPainterPath,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QSizePolicy,
)

from ui.personal.leaf_button import LeafButton
from ui.personal.styles import (
    COLOR_SOFT, COLOR_PRIMARY, COLOR_ASSIST, COLOR_TEXT,
    COLOR_TEXT_SECONDARY, COLOR_SELECTED, COLOR_CARD,
)
from dao.personal_dao import MOOD_HAPPY, MOOD_NORMAL, MOOD_TIRED, MOOD_SAD

WEEKDAY_LABELS = ("一", "二", "三", "四", "五", "六", "日")


class PersonalDayCell(QWidget):
    clicked = pyqtSignal(object)  # QDate

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date: Optional[QDate] = None
        self._in_month = True
        self._has_milestone = False
        self._mood: Optional[str] = None
        self._has_diary = False
        self._is_today = False
        self._is_selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(72, 68)

    def sizeHint(self):
        return QSize(88, 82)

    def set_day(self, date: Optional[QDate], in_month: bool):
        self._date = date
        self._in_month = in_month
        self.setEnabled(bool(date and date.isValid()))
        self.update()

    def set_milestone(self, has: bool):
        self._has_milestone = bool(has)
        self.update()

    def set_mood(self, mood: Optional[str]):
        self._mood = mood
        self.update()

    def set_has_diary(self, has: bool):
        self._has_diary = bool(has)
        self.update()

    def set_today(self, is_today: bool):
        self._is_today = bool(is_today)
        self.update()

    def set_selected(self, selected: bool):
        self._is_selected = bool(selected)
        self.update()

    def date(self) -> Optional[QDate]:
        return self._date

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._date and self._date.isValid():
            self.clicked.emit(self._date)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        rect = QRect(0, 0, w, h)
        inner = rect.adjusted(2, 2, -2, -2)

        bg = QColor(COLOR_CARD) if self._in_month else QColor(COLOR_SOFT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(inner, 8, 8)

        if self._is_selected and self._in_month:
            painter.setBrush(QColor(COLOR_SELECTED))
            painter.drawRoundedRect(inner.adjusted(1, 1, -1, -1), 7, 7)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(COLOR_ASSIST), 1))
        painter.drawRoundedRect(inner, 8, 8)

        if self._is_today and self._in_month:
            painter.setPen(QPen(QColor(COLOR_PRIMARY), 2))
            painter.drawRoundedRect(inner.adjusted(1, 1, -1, -1), 7, 7)

        if not self._date or not self._date.isValid():
            return

        # 日期数字居中偏上，下方留给羊皮纸；角落留给石碑/表情
        ink = QColor(COLOR_TEXT) if self._in_month else QColor(COLOR_TEXT_SECONDARY)
        if self._is_selected:
            ink = QColor(COLOR_PRIMARY)
        font = QFont("Courier New", 13)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(ink)
        # 有日记时数字略上移，腾出羊皮纸位置
        num_top = inner.y() + (6 if self._has_diary and self._in_month else 10)
        num_rect = QRect(inner.x(), num_top, inner.width(), 22)
        painter.drawText(num_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                         str(self._date.day()))

        if self._in_month and self._has_diary:
            self._paint_parchment(painter, inner, num_rect.bottom())
        if self._in_month and self._has_milestone:
            self._paint_stone(painter, inner)
        if self._in_month and self._mood:
            self._paint_mood(painter, inner, self._mood)

    def _paint_parchment(self, painter: QPainter, cell: QRect, below_y: int):
        """日期数字下方：手绘羊皮纸卷。"""
        painter.save()
        pw, ph = 28, 18
        cx = cell.center().x()
        # 紧贴数字下方，并避开底部表情
        top = min(below_y + 1, cell.bottom() - ph - 14)
        left = cx - pw // 2
        x, y = float(left), float(top)

        # 轻微卷边轮廓
        path = QPainterPath()
        path.moveTo(x + 2, y + 2)
        path.cubicTo(x - 1, y + ph * 0.35, x - 1, y + ph * 0.65, x + 2, y + ph - 2)
        path.lineTo(x + pw - 2, y + ph - 2)
        path.cubicTo(x + pw + 1, y + ph * 0.65, x + pw + 1, y + ph * 0.35, x + pw - 2, y + 2)
        path.closeSubpath()

        # 羊皮纸底色（米黄）
        painter.setPen(QPen(QColor("#8a7355"), 1.3))
        painter.setBrush(QColor("#e8d5b0"))
        painter.drawPath(path)

        # 纸面纹理细线
        painter.setPen(QPen(QColor(160, 130, 90, 70), 1))
        for i in range(3):
            yy = int(y + 5 + i * 4)
            painter.drawLine(int(x + 5), yy, int(x + pw - 5), yy)

        # 左上角小卷曲高光
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 248, 230, 120))
        painter.drawEllipse(QPointF(x + 5, y + 4), 3.2, 2.4)
        painter.restore()

    def _paint_stone(self, painter: QPainter, cell: QRect):
        """左上角较大石碑：灰石底色 + 手绘轮廓。"""
        painter.save()
        ox, oy = cell.left() + 4, cell.top() + 4
        # 碑身：圆顶石板，约 22×26
        path = QPainterPath()
        path.moveTo(ox + 11, oy)
        path.quadTo(ox + 20, oy + 2, ox + 20, oy + 8)
        path.lineTo(ox + 20, oy + 24)
        path.quadTo(ox + 20, oy + 26, ox + 18, oy + 26)
        path.lineTo(ox + 4, oy + 26)
        path.quadTo(ox + 2, oy + 26, ox + 2, oy + 24)
        path.lineTo(ox + 2, oy + 8)
        path.quadTo(ox + 2, oy + 2, ox + 11, oy)
        path.closeSubpath()

        # 石头底色（暖灰）+ 轻微立体
        painter.setPen(QPen(QColor("#5a5348"), 1.6))
        painter.setBrush(QColor("#9a9184"))
        painter.drawPath(path)
        # 高光面
        hi = QPainterPath()
        hi.moveTo(ox + 5, oy + 8)
        hi.lineTo(ox + 5, oy + 22)
        hi.lineTo(ox + 10, oy + 22)
        hi.lineTo(ox + 10, oy + 9)
        hi.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 45))
        painter.drawPath(hi)
        # 铭文横线
        painter.setPen(QPen(QColor("#3e3a34"), 1.2))
        painter.drawLine(int(ox + 6), int(oy + 12), int(ox + 16), int(oy + 12))
        painter.drawLine(int(ox + 6), int(oy + 17), int(ox + 16), int(oy + 17))
        painter.restore()

    def _paint_mood(self, painter: QPainter, cell: QRect, mood: str):
        """右下角手绘表情（按心情着色）。"""
        painter.save()
        cx = cell.right() - 17
        cy = cell.bottom() - 17
        r = 11
        # 开心亮绿 / 一般蓝 / 疲惫黄 / 沮丧灰
        if mood == MOOD_HAPPY:
            stroke = QColor("#2e9b4a")
            fill = QColor("#7dce6a")
            face = QColor("#1f5c30")
        elif mood == MOOD_NORMAL:
            stroke = QColor("#3a7ab8")
            fill = QColor("#7eb6e8")
            face = QColor("#1f4a70")
        elif mood == MOOD_TIRED:
            stroke = QColor("#c9a028")
            fill = QColor("#e8d06a")
            face = QColor("#6b5a12")
        else:  # sad
            stroke = QColor("#6e6e6e")
            fill = QColor("#b0b0b0")
            face = QColor("#3a3a3a")

        painter.setPen(QPen(stroke, 1.6))
        painter.setBrush(fill)
        painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.setPen(QPen(face, 1.5))
        # 眼睛
        painter.drawPoint(QPointF(cx - 3.8, cy - 2.8))
        painter.drawPoint(QPointF(cx + 3.8, cy - 2.8))
        if mood == MOOD_HAPPY:
            path = QPainterPath()
            path.moveTo(cx - 4.5, cy + 2)
            path.quadTo(cx, cy + 7, cx + 4.5, cy + 2)
            painter.drawPath(path)
        elif mood == MOOD_NORMAL:
            painter.drawLine(QPointF(cx - 4, cy + 3.5), QPointF(cx + 4, cy + 3.5))
        elif mood == MOOD_TIRED:
            painter.drawLine(QPointF(cx - 5, cy - 1.5), QPointF(cx - 1.5, cy - 3.2))
            painter.drawLine(QPointF(cx + 1.5, cy - 3.2), QPointF(cx + 5, cy - 1.5))
            painter.drawLine(QPointF(cx - 3.5, cy + 3.5), QPointF(cx + 3.5, cy + 3.5))
        else:  # sad
            path = QPainterPath()
            path.moveTo(cx - 4.5, cy + 5.5)
            path.quadTo(cx, cy + 1.5, cx + 4.5, cy + 5.5)
            painter.drawPath(path)
        painter.restore()


class PersonalCalendar(QWidget):
    """填满剩余区域的大格日历；无页面滚动依赖。"""

    date_selected = pyqtSignal(object)  # QDate
    month_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("personalCalendar")
        self._year = QDate.currentDate().year()
        self._month = QDate.currentDate().month()
        self._selected: Optional[QDate] = QDate.currentDate()
        self._milestone_dates: Set[str] = set()
        self._diary_dates: Set[str] = set()
        self._moods: Dict[str, str] = {}
        self._cells: list[PersonalDayCell] = []
        self._build()
        self._fill()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        head = QHBoxLayout()
        self.btn_prev = LeafButton("上月", tone="soft")
        self.btn_next = LeafButton("下月", tone="soft")
        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_next.clicked.connect(self._on_next)
        self.lbl_title = QLabel()
        self.lbl_title.setObjectName("pageTitle")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        head.addWidget(self.btn_prev)
        head.addWidget(self.lbl_title, 1)
        head.addWidget(self.btn_next)
        root.addLayout(head)

        shell = QFrame()
        shell.setObjectName("personalCard")
        shell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        shell_lay = QVBoxLayout(shell)
        shell_lay.setContentsMargins(10, 10, 10, 10)
        shell_lay.setSpacing(6)

        week_row = QHBoxLayout()
        for name in WEEKDAY_LABELS:
            lab = QLabel(name)
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-weight: bold;")
            week_row.addWidget(lab, 1)
        shell_lay.addLayout(week_row)

        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        self.grid.setContentsMargins(0, 0, 0, 0)
        for r in range(6):
            for c in range(7):
                cell = PersonalDayCell()
                cell.clicked.connect(self._on_cell_clicked)
                self._cells.append(cell)
                self.grid.addWidget(cell, r, c)
                self.grid.setRowStretch(r, 1)
                self.grid.setColumnStretch(c, 1)
        shell_lay.addLayout(self.grid, 1)
        root.addWidget(shell, 1)

    def _on_prev(self):
        d = QDate(self._year, self._month, 1).addMonths(-1)
        self.set_month(d.year(), d.month())

    def _on_next(self):
        d = QDate(self._year, self._month, 1).addMonths(1)
        self.set_month(d.year(), d.month())

    def set_month(self, year: int, month: int):
        self._year, self._month = year, month
        self._fill()
        self.month_changed.emit(year, month)

    def year(self):
        return self._year

    def month(self):
        return self._month

    def selected_date(self) -> Optional[QDate]:
        return self._selected

    def set_selected_date(self, qd: QDate, emit_signal: bool = False):
        if not qd or not qd.isValid():
            return
        self._selected = QDate(qd)
        if qd.year() != self._year or qd.month() != self._month:
            self.set_month(qd.year(), qd.month())
        else:
            self._refresh_selection()
        if emit_signal:
            self.date_selected.emit(QDate(qd))

    def set_marks(self, milestone_dates: Iterable[str] = (),
                  diary_dates: Iterable[str] = (),
                  moods: Optional[Dict[str, str]] = None):
        self._milestone_dates = {str(d) for d in milestone_dates if d}
        self._diary_dates = {str(d) for d in diary_dates if d}
        self._moods = dict(moods or {})
        self._refresh_marks()

    def _fill(self):
        self.lbl_title.setText(f"{self._year} 年 {self._month} 月")
        cal = Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(self._year, self._month)
        today = QDate.currentDate()
        while len(weeks) < 6:
            weeks.append([None] * 7)
        idx = 0
        for week in weeks[:6]:
            for day in week:
                cell = self._cells[idx]
                idx += 1
                if day is None:
                    cell.set_day(None, False)
                    continue
                qd = QDate(day.year, day.month, day.day)
                in_month = day.month == self._month
                cell.set_day(qd, in_month)
                cell.set_today(qd == today)
                selected = bool(
                    self._selected and self._selected.isValid()
                    and qd == self._selected and in_month
                )
                cell.set_selected(selected)
                key = qd.toString("yyyy-MM-dd")
                cell.set_milestone(key in self._milestone_dates)
                cell.set_has_diary(key in self._diary_dates)
                cell.set_mood(self._moods.get(key))

    def _refresh_selection(self):
        for cell in self._cells:
            d = cell.date()
            selected = bool(
                d and self._selected and d == self._selected
                and d.month() == self._month
            )
            cell.set_selected(selected)

    def _refresh_marks(self):
        for cell in self._cells:
            d = cell.date()
            if not d or not d.isValid():
                continue
            key = d.toString("yyyy-MM-dd")
            cell.set_milestone(key in self._milestone_dates)
            cell.set_has_diary(key in self._diary_dates)
            cell.set_mood(self._moods.get(key))

    def _on_cell_clicked(self, qd: QDate):
        if not qd or not qd.isValid():
            return
        if qd.month() != self._month or qd.year() != self._year:
            self.set_month(qd.year(), qd.month())
        self._selected = QDate(qd)
        self._refresh_selection()
        self.date_selected.emit(QDate(qd))
