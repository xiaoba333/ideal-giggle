# -*- coding: utf-8 -*-
"""个人模式绿色系表格包装（交互逻辑同主表，仅换色）。"""

from __future__ import annotations

from PyQt6 import sip
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QTableWidget, QAbstractItemView, QFrame, QVBoxLayout,
)

from ui.personal.styles import COLOR_TABLE_HOVER

_ROW_HEIGHT = 40
_HEADER_HEIGHT = 42
_HOVER_COLOR = QColor(COLOR_TABLE_HOVER)
_SAVED_BG_ROLE = Qt.ItemDataRole.UserRole + 90


def _qt_alive(obj) -> bool:
    return obj is not None and not sip.isdeleted(obj)


class _RowHoverFilter(QObject):
    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self._table = table
        self._hover_row = -1
        table.destroyed.connect(self._on_table_destroyed)

    def _on_table_destroyed(self, *_args):
        self._table = None
        self._hover_row = -1

    def eventFilter(self, obj, event):
        table = self._table
        if not _qt_alive(table):
            return False
        try:
            viewport = table.viewport()
        except RuntimeError:
            return False
        if obj is not viewport:
            return False
        et = event.type()
        if et == QEvent.Type.MouseMove:
            idx = table.indexAt(event.pos())
            row = idx.row() if idx.isValid() else -1
            self._set_hover(row)
        elif et in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
            self._set_hover(-1)
        return False

    def _set_hover(self, row: int):
        if row == self._hover_row:
            return
        old = self._hover_row
        self._hover_row = row
        if old >= 0:
            self._paint_row(old, False)
        if row >= 0:
            self._paint_row(row, True)

    def _paint_row(self, row: int, hover: bool):
        table = self._table
        if not _qt_alive(table):
            return
        try:
            if row < 0 or row >= table.rowCount():
                return
            sm = table.selectionModel()
            if sm and sm.isRowSelected(row):
                return
            cols = table.columnCount()
            for c in range(cols):
                item = table.item(row, c)
                if item is None:
                    continue
                if hover:
                    if item.data(_SAVED_BG_ROLE) is None:
                        bg = item.data(Qt.ItemDataRole.BackgroundRole)
                        item.setData(_SAVED_BG_ROLE, bg if bg is not None else False)
                    item.setBackground(_HOVER_COLOR)
                else:
                    saved = item.data(_SAVED_BG_ROLE)
                    if saved is False or saved is None:
                        item.setData(Qt.ItemDataRole.BackgroundRole, None)
                    elif saved is not None:
                        item.setBackground(saved if isinstance(saved, QBrush) else QBrush(saved))
                    item.setData(_SAVED_BG_ROLE, None)
        except RuntimeError:
            return


def style_personal_table(table: QTableWidget):
    table.setObjectName("personalTable")
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setShowGrid(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(_ROW_HEIGHT)
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header.setFixedHeight(_HEADER_HEIGHT)
    header.setHighlightSections(False)
    filt = _RowHoverFilter(table)
    table.viewport().installEventFilter(filt)
    table.setMouseTracking(True)
    table._personal_hover_filter = filt  # noqa: keep ref


def wrap_personal_table_panel(table: QTableWidget) -> QFrame:
    style_personal_table(table)
    panel = QFrame()
    panel.setObjectName("personalTablePanel")
    panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(8, 8, 8, 8)
    lay.setSpacing(0)
    lay.addWidget(table)
    return panel
