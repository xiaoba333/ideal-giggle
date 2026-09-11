# -*- coding: utf-8 -*-
"""
统一美化 QTableWidget：暖棕米色面板风。
业务页创建表格后调用 style_data_table(table) / wrap_table_panel(table)。
"""

from __future__ import annotations

from PyQt6 import sip
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QTableWidget, QHeaderView, QAbstractItemView, QFrame, QVBoxLayout, QWidget,
)

from ui.styles import COLOR_TABLE_HOVER

_ROW_HEIGHT = 40
_HEADER_HEIGHT = 42
_HOVER_COLOR = QColor(COLOR_TABLE_HOVER)
# 悬浮前缓存单元格背景（False=无自定义底色；QBrush=业务自定义底色）
_SAVED_BG_ROLE = Qt.ItemDataRole.UserRole + 90


def _qt_alive(obj) -> bool:
    """C++ 侧对象是否仍存在（关闭窗口/换页销毁表格时可能已删）。"""
    return obj is not None and not sip.isdeleted(obj)


class _RowHoverFilter(QObject):
    """整行悬浮高亮（弥补 QSS 只能高亮单格的不足）。"""

    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self._table = table
        self._hover_row = -1
        # 表格销毁时立刻清空，避免析构过程中仍收到 viewport 事件
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
            selected = False
            if sm is not None:
                selected = any(i.row() == row for i in sm.selectedRows())
            for c in range(table.columnCount()):
                item = table.item(row, c)
                if item is None:
                    continue
                if selected:
                    continue
                if hover:
                    if item.data(_SAVED_BG_ROLE) is None:
                        brush = item.background()
                        if brush.style() != Qt.BrushStyle.NoBrush:
                            item.setData(_SAVED_BG_ROLE, brush)
                        else:
                            item.setData(_SAVED_BG_ROLE, False)
                    item.setBackground(QBrush(_HOVER_COLOR))
                else:
                    saved = item.data(_SAVED_BG_ROLE)
                    item.setData(_SAVED_BG_ROLE, None)
                    if isinstance(saved, QBrush):
                        item.setBackground(saved)
                    else:
                        item.setData(Qt.ItemDataRole.BackgroundRole, None)
                        item.setBackground(QBrush())
        except RuntimeError:
            # 表格/单元格在绘制过程中被销毁
            return


def style_data_table(table: QTableWidget):
    """统一表格行为与外观属性（配合全局 QSS）。"""
    table.setObjectName("dataTable")
    table.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    table.setFrameShape(QFrame.Shape.NoFrame)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setMouseTracking(True)
    table.viewport().setMouseTracking(True)

    header = table.horizontalHeader()
    header.setObjectName("dataTableHeader")
    header.setHighlightSections(False)
    header.setStretchLastSection(True)
    header.setSectionsMovable(False)
    header.setSectionsClickable(False)
    header.setDefaultAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    header.setMinimumHeight(_HEADER_HEIGHT)
    header.setFixedHeight(_HEADER_HEIGHT)
    # Stretch：禁止拖拽改列宽，列均分填满
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    header.setCascadingSectionResizes(False)

    vheader = table.verticalHeader()
    vheader.setVisible(False)
    vheader.setDefaultSectionSize(_ROW_HEIGHT)
    vheader.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    vheader.setMinimumSectionSize(_ROW_HEIGHT)

    # 避免重复 style 时叠多个 filter
    old = getattr(table, "_row_hover_filter", None)
    if _qt_alive(old):
        try:
            table.viewport().removeEventFilter(old)
        except RuntimeError:
            pass
        old.deleteLater()

    filt = _RowHoverFilter(table)
    table.viewport().installEventFilter(filt)
    table._row_hover_filter = filt  # 防止被 GC


def wrap_table_panel(table: QTableWidget, parent: QWidget | None = None) -> QFrame:
    """
    外包一层大圆角面板（模拟微弱阴影），返回面板；调用方把 panel 加入布局。
    若 table 已有 parent，会改挂到 panel 下。
    """
    style_data_table(table)
    shadow = QFrame(parent)
    shadow.setObjectName("tablePanelShadow")
    shadow.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    outer = QVBoxLayout(shadow)
    outer.setContentsMargins(0, 0, 0, 3)
    outer.setSpacing(0)

    panel = QFrame(shadow)
    panel.setObjectName("tablePanel")
    panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    table.setParent(panel)
    lay.addWidget(table)
    outer.addWidget(panel)
    return shadow
