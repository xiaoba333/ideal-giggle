# -*- coding: utf-8 -*-
"""个人模式标签容器（绿色森系，独立于主界面 DissolveTabWidget）。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabBar, QSizePolicy, QFrame, QStackedWidget,
)

from ui.personal.styles import COLOR_BG


class PersonalTabWidget(QWidget):
    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("personalTabWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._pages: list[QWidget] = []
        self._current = -1

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bg = QColor(COLOR_BG)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, bg)
        self.setPalette(pal)

        self.tabBar = QTabBar(self)
        self.tabBar.setObjectName("personalNavTabBar")
        self.tabBar.setExpanding(False)
        self.tabBar.setDrawBase(False)
        self.tabBar.setDocumentMode(True)
        self.tabBar.setFont(QFont("Microsoft YaHei", 10))
        self.tabBar.currentChanged.connect(self._on_tab_bar_changed)
        root.addWidget(self.tabBar)

        self._pane = QFrame(self)
        self._pane.setObjectName("personalTabPane")
        self._pane.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._pane.setAutoFillBackground(True)
        pane_pal = self._pane.palette()
        pane_pal.setColor(QPalette.ColorRole.Window, bg)
        self._pane.setPalette(pane_pal)

        pane_lay = QVBoxLayout(self._pane)
        pane_lay.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget(self._pane)
        self._stack.setObjectName("personalTabStack")
        pane_lay.addWidget(self._stack, 1)
        root.addWidget(self._pane, 1)

    def addTab(self, widget: QWidget, label: str) -> int:
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        widget.setAutoFillBackground(True)
        self._pages.append(widget)
        self._stack.addWidget(widget)
        idx = self.tabBar.addTab(label)
        if self._current < 0:
            self.setCurrentIndex(0)
        return idx

    def setCurrentIndex(self, index: int):
        if index < 0 or index >= len(self._pages):
            return
        self.tabBar.blockSignals(True)
        self.tabBar.setCurrentIndex(index)
        self.tabBar.blockSignals(False)
        self._show_page(index)

    def currentIndex(self) -> int:
        return self._current

    def count(self) -> int:
        return len(self._pages)

    def _on_tab_bar_changed(self, index: int):
        self._show_page(index)

    def _show_page(self, new_index: int):
        if new_index < 0 or new_index >= len(self._pages):
            return
        if new_index == self._current:
            return
        self._current = new_index
        self._stack.setCurrentIndex(new_index)
        self.currentChanged.emit(new_index)
