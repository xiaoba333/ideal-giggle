# -*- coding: utf-8 -*-
"""
首页纸质日历独立控件（API 对齐 PySide6 Signal，本项目使用 PyQt6）。

- 米白纸张风格，复用 LogCalendarWidget 绘制
- 日志日期 → 左上角浅蓝 #；待办截止 → 日期下红色下划线（最多 3 层）
- 数据在子线程加载，点击日期向外发出选中信号
"""

from __future__ import annotations

from PyQt6.QtCore import QDate, QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy

from service import classlog_service, todo_service
from ui.components.log_calendar import LogCalendarWidget
from ui.components.text_label_util import ElideLabel, configure_wrap_label


class _HomeCalendarDataWorker(QThread):
    """子线程拉取当月日志日期 + 待办截止计数。"""

    finished_ok = pyqtSignal(int, int, list, dict)  # year, month, log_dates, todo_counts
    failed = pyqtSignal(str)

    def __init__(self, year: int, month: int, token: int, parent=None):
        super().__init__(parent)
        self.year = year
        self.month = month
        self.token = token

    def run(self):
        try:
            start = QDate(self.year, self.month, 1).addDays(-7)
            end = QDate(self.year, self.month, 1)
            end = QDate(self.year, self.month, end.daysInMonth()).addDays(14)
            start_s = start.toString("yyyy-MM-dd")
            end_s = end.toString("yyyy-MM-dd")

            log_dates = classlog_service.list_log_dates(start_s, end_s)
            todo_counts = todo_service.deadline_counts_in_range(start_s, end_s)
            self.finished_ok.emit(self.year, self.month, log_dates, todo_counts)
        except Exception as e:
            self.failed.emit(str(e))


class HomePaperCalendarWidget(QWidget):
    """
    首页纸质日历。

    Signals:
        date_selected(QDate): 点击日期
        month_changed(int, int): 翻页完成（已同步刷新标记）
        add_log_requested(QDate): 右键新增日志
        add_todo_requested(QDate): 右键新增待办
    """

    date_selected = pyqtSignal(object)
    month_changed = pyqtSignal(int, int)
    add_log_requested = pyqtSignal(object)
    add_todo_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homePaperCalendar")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(380)

        self._token = 0
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        caption = ElideLabel("月历总览")
        caption.setObjectName("pageTitle")
        caption.setMinimumHeight(22)
        root.addWidget(caption)

        tip = QLabel("左键点击日期可跳转；右键格子可新增日志或待办；＃=日志，红线=待办截止")
        tip.setObjectName("hintLabel")
        configure_wrap_label(tip)
        tip.setMaximumWidth(1100)
        root.addWidget(tip)

        self.calendar = LogCalendarWidget(self)
        self.calendar.set_show_todo_legend(True)
        self.calendar.setMinimumHeight(320)
        self.calendar.date_selected.connect(self.date_selected.emit)
        self.calendar.month_changed.connect(self._on_month_changed)
        self.calendar.add_log_requested.connect(self.add_log_requested.emit)
        self.calendar.add_todo_requested.connect(self.add_todo_requested.emit)
        root.addWidget(self.calendar)

        self.reload_marks()

    def year_shown(self) -> int:
        return self.calendar.year_shown()

    def month_shown(self) -> int:
        return self.calendar.month_shown()

    def log_dates(self):
        return self.calendar.log_dates()

    def todo_deadlines(self) -> dict:
        return self.calendar.todo_deadlines()

    def set_log_dates(self, dates):
        """外部直接灌入日志日期集合。"""
        self.calendar.set_log_dates(dates)

    def set_todo_deadlines(self, counts: dict):
        """外部直接灌入待办截止日期字典。"""
        self.calendar.set_todo_deadlines(counts)

    def reload_marks(self):
        """子线程重新加载当前页标记数据。"""
        self._load_async(self.calendar.year_shown(), self.calendar.month_shown())

    def refresh(self):
        self.reload_marks()

    def _on_month_changed(self, year: int, month: int):
        self.month_changed.emit(year, month)
        self._load_async(year, month)

    def _load_async(self, year: int, month: int):
        self._token += 1
        token = self._token
        worker = _HomeCalendarDataWorker(year, month, token, self)

        def _ok(y, m, log_dates, todo_counts, tok=token):
            if tok != self._token:
                return
            if y != self.calendar.year_shown() or m != self.calendar.month_shown():
                return
            self.calendar.set_log_dates(log_dates)
            self.calendar.set_todo_deadlines(todo_counts)

        def _fail(msg, tok=token):
            if tok != self._token:
                return
            print(f"[首页纸质日历] 加载标记失败: {msg}")

        worker.finished_ok.connect(_ok)
        worker.failed.connect(_fail)
        self._worker = worker
        worker.start()
