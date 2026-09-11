# -*- coding: utf-8 -*-
"""个人模式外壳：首页 / 感触随笔。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from ui.personal.styles import PERSONAL_QSS, COLOR_BG
from ui.personal.leaf_button import LeafButton
from ui.personal.tab_widget import PersonalTabWidget
from ui.personal.home_widget import PersonalHomeWidget
from ui.personal.essay_widget import EssayWidget


class PersonalShellWidget(QWidget):
    """同等窗口尺寸的个人专属界面。"""

    exit_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    TAB_HOME = 0
    TAB_ESSAY = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("personalShell")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setStyleSheet(PERSONAL_QSS)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(COLOR_BG))
        self.setPalette(pal)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        brand = QLabel("个人模式")
        brand.setObjectName("pageTitle")
        top.addWidget(brand)
        top.addStretch()
        self.btn_quit = LeafButton("安全退出", tone="soft")
        self.btn_quit.setToolTip("确认后安全关闭程序，避免未落库数据丢失")
        self.btn_quit.clicked.connect(self.quit_requested.emit)
        top.addWidget(self.btn_quit)
        self.btn_exit = LeafButton("退出个人模式", tone="deep")
        self.btn_exit.clicked.connect(self.exit_requested.emit)
        top.addWidget(self.btn_exit)
        root.addLayout(top)

        self.tabs = PersonalTabWidget()
        self.home = PersonalHomeWidget()
        self.essay = EssayWidget()
        self.tabs.addTab(self.home, "首页")
        self.tabs.addTab(self.essay, "感触随笔")
        self.tabs.currentChanged.connect(self._on_tab)
        root.addWidget(self.tabs, 1)

    def _on_tab(self, index: int):
        if index == self.TAB_HOME:
            self.home.refresh()
        elif index == self.TAB_ESSAY:
            self.essay.reload()

    def on_enter(self):
        self.tabs.setCurrentIndex(self.TAB_HOME)
        self.home.refresh()
        self.essay.reload()
