# -*- coding: utf-8 -*-
"""
标签页容器：QTabBar + QStackedWidget，原生即刻切换（无过渡动画）。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabBar, QSizePolicy, QFrame, QStackedWidget,
)

from ui.styles import COLOR_BG


class DissolveTabWidget(QWidget):
    """
    近似 QTabWidget API：addTab / setCurrentIndex / currentIndex / count。
    用 QStackedWidget 切换，保证旧页完全隐藏，不会叠在新页下面。
    """

    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dissolveTabWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._pages: list[QWidget] = []
        self._current = -1

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bg = QColor(COLOR_BG)

        self.tabBar = QTabBar(self)
        self.tabBar.setObjectName("mainNavTabBar")
        self.tabBar.setExpanding(False)
        self.tabBar.setDrawBase(False)
        self.tabBar.setDocumentMode(True)
        self.tabBar.setUsesScrollButtons(True)
        self.tabBar.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabBar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.tabBar.setAutoFillBackground(True)
        pal = self.tabBar.palette()
        pal.setColor(QPalette.ColorRole.Window, bg)
        pal.setColor(QPalette.ColorRole.Base, bg)
        pal.setColor(QPalette.ColorRole.Button, bg)
        self.tabBar.setPalette(pal)
        tab_font = QFont("Microsoft YaHei", 10)
        tab_font.setBold(False)
        self.tabBar.setFont(tab_font)
        self.tabBar.currentChanged.connect(self._on_tab_bar_changed)
        root.addWidget(self.tabBar)

        self._pane = QFrame(self)
        self._pane.setObjectName("dissolveTabPane")
        self._pane.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._pane.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._pane.setAutoFillBackground(True)
        self._pane.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        pane_pal = self._pane.palette()
        pane_pal.setColor(QPalette.ColorRole.Window, bg)
        pane_pal.setColor(QPalette.ColorRole.Base, bg)
        self._pane.setPalette(pane_pal)

        pane_lay = QVBoxLayout(self._pane)
        pane_lay.setContentsMargins(0, 0, 0, 0)
        pane_lay.setSpacing(0)

        self._stack = QStackedWidget(self._pane)
        self._stack.setObjectName("dissolveTabStack")
        self._stack.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._stack.setAutoFillBackground(True)
        self._stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        stack_pal = self._stack.palette()
        stack_pal.setColor(QPalette.ColorRole.Window, bg)
        stack_pal.setColor(QPalette.ColorRole.Base, bg)
        self._stack.setPalette(stack_pal)
        pane_lay.addWidget(self._stack, 1)

        root.addWidget(self._pane, 1)

    def addTab(self, widget: QWidget, label: str) -> int:
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        widget.setAutoFillBackground(True)
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._pages.append(widget)
        self._stack.addWidget(widget)
        idx = self.tabBar.addTab(label)

        if self._current < 0:
            self._show_page(0)
        return idx

    def count(self) -> int:
        return len(self._pages)

    def currentIndex(self) -> int:
        return self._current

    def widget(self, index: int) -> QWidget | None:
        if 0 <= index < len(self._pages):
            return self._pages[index]
        return None

    def setCurrentIndex(self, index: int):
        if index < 0 or index >= len(self._pages):
            return
        if index == self.tabBar.currentIndex():
            if index != self._current:
                self._show_page(index)
            return
        self.tabBar.setCurrentIndex(index)

    def _on_tab_bar_changed(self, index: int):
        if index < 0 or index >= len(self._pages):
            return
        self._show_page(index)

    def _show_page(self, new_index: int):
        if new_index < 0 or new_index >= len(self._pages):
            return
        old = self._current
        if old == new_index:
            self._stack.setCurrentIndex(new_index)
            return
        self._current = new_index
        self._stack.setCurrentIndex(new_index)
        self._pages[new_index].update()
        self._pane.update()
        self.currentChanged.emit(new_index)
