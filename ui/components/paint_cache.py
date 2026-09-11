# -*- coding: utf-8 -*-
"""
绘制辅助：已禁用 setCacheMode / 多层离屏缓存。
自定义绘制一律在控件自身 paintEvent 内用局部 QPainter 完成。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget


def enable_scroll_friendly(widget: QWidget):
    """滚动容器用：不透明 + 样式背景。"""
    widget.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    # widget.setCacheMode(...)  # 已禁用：避免多层绘制缓存冲突


def try_set_widget_cache_mode(widget: QWidget):
    """
    兼容旧调用：仅保留样式背景提示。
    # setCacheMode / DeviceCoordinateCache / ItemCoordinateCache 全部禁用
    """
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    # if hasattr(widget, "setCacheMode"):
    #     widget.setCacheMode(...)  # 已注释：消除多层绘制缓存冲突
