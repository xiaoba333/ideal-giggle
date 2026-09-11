# -*- coding: utf-8 -*-
"""首页日期模块：本机系统时间实时刷新（只读展示）。"""

from datetime import datetime

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QSizePolicy

from ui.components.droplet_card import DropletCard
from ui.components.text_label_util import ElideLabel

WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


class DateModule(DropletCard):
    """
    读取本机本地时间，每秒刷新；只读展示。
    compact=True（迷你窗）：仅居中显示时分秒。
    """

    def __init__(self, parent=None, compact=False):
        self._compact = compact
        min_w = 40 if compact else 200
        min_h = 40 if compact else 240
        super().__init__(parent, min_width=min_w, min_height=min_h)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if compact:
            self.setProperty("compact", True)
            # 迷你窗：紧凑边距，时间在模块内居中放大显示
            self.layout().setContentsMargins(2, 2, 2, 4)
            self.content().setContentsMargins(0, 0, 0, 0)
            self.set_shadow_enabled(False)
        self._build_content()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def _build_content(self):
        lay = self.content()
        if self._compact:
            lay.setSpacing(0)
            lay.setContentsMargins(0, 0, 0, 0)
            self.lbl_date = None
            self.lbl_weekday = None

            # 上下弹性空白：时间在上方小模块内居中
            lay.addStretch(1)

            self.lbl_clock = QLabel()
            self.lbl_clock.setObjectName("dateClockCompact")
            self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_clock.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self.lbl_clock.setMinimumHeight(48)
            font_clock = QFont("Courier New")
            font_clock.setPointSize(34)
            font_clock.setFixedPitch(True)
            font_clock.setBold(True)
            self.lbl_clock.setFont(font_clock)
            lay.addWidget(
                self.lbl_clock,
                0,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            )

            lay.addStretch(1)
            return

        lay.setSpacing(12)
        lay.addStretch(1)

        self.lbl_date = ElideLabel()
        self.lbl_date.setObjectName("dateYmd")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date.setMinimumHeight(36)
        font_ymd = QFont("Courier New")
        font_ymd.setPointSize(18)
        font_ymd.setFixedPitch(True)
        font_ymd.setBold(True)
        self.lbl_date.setFont(font_ymd)
        lay.addWidget(self.lbl_date)

        self.lbl_weekday = ElideLabel()
        self.lbl_weekday.setObjectName("dateWeekday")
        self.lbl_weekday.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_weekday.setMinimumHeight(28)
        lay.addWidget(self.lbl_weekday)

        self.lbl_clock = ElideLabel()
        self.lbl_clock.setObjectName("dateClock")
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_clock.setMinimumHeight(88)
        font_clock = QFont("Courier New")
        font_clock.setPointSize(60)
        font_clock.setFixedPitch(True)
        font_clock.setBold(True)
        self.lbl_clock.setFont(font_clock)
        lay.addWidget(self.lbl_clock)

        lay.addStretch(2)

    def refresh(self, force: bool = False):
        """系统时钟刷新；首页滚动中跳过 UI 写入以减负。"""
        if not force:
            w = self.parent()
            while w is not None:
                if hasattr(w, "is_scrolling") and callable(w.is_scrolling):
                    if w.is_scrolling():
                        return
                    break
                w = w.parent()
        now = datetime.now()
        if self.lbl_date is not None:
            self.lbl_date.setText(now.strftime("%Y-%m-%d"))
        if self.lbl_weekday is not None:
            self.lbl_weekday.setText(WEEKDAY_CN[now.weekday()])
        self.lbl_clock.setText(now.strftime("%H:%M:%S"))

    def showEvent(self, event):
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start()
        self.refresh()

    def hideEvent(self, event):
        super().hideEvent(event)
