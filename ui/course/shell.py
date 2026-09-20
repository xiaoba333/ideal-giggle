# -*- coding: utf-8 -*-
"""课程模式外壳：黑白极简，与主界面木纹样式隔离。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.course.page import CoursePage
from ui.course.styles import COLOR_BG, COURSE_QSS


class CourseShellWidget(QWidget):
    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("courseShell")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setStyleSheet(COURSE_QSS)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(COLOR_BG))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#222222"))
        self.setPalette(pal)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("课程模式")
        title.setObjectName("courseTitle")
        top.addWidget(title)
        top.addStretch()
        self.btn_exit = QPushButton("退出课程模式")
        self.btn_exit.setObjectName("courseExitBtn")
        self.btn_exit.clicked.connect(self._on_exit)
        top.addWidget(self.btn_exit)
        root.addLayout(top)

        self.page = CoursePage()
        root.addWidget(self.page, 1)

    def on_enter(self):
        self.page.reload()

    def flush(self):
        self.page.flush()

    def _on_exit(self):
        self.flush()
        self.exit_requested.emit()
