# -*- coding: utf-8 -*-
"""文本标签溢出策略工具：换行 / 单行省略，防止穿模。"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QLabel, QSizePolicy


def configure_wrap_label(label: QLabel, min_height=None):
    """多行文本：自动换行，禁止水平无限扩张导致穿模。"""
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    label.setMinimumWidth(40)
    if min_height is not None:
        label.setMinimumHeight(min_height)
    return label


def configure_elide_label(label: QLabel):
    """
    单行文本：超长省略号。
    使用 ElideLabel 行为：将 label 替换逻辑挂到属性上。
    """
    if not isinstance(label, ElideLabel):
        # 普通 QLabel：尽量限制并不换行
        label.setWordWrap(False)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        label.setMinimumWidth(40)
    return label


class ElideLabel(QLabel):
    """单行省略号标签：宽度不足时显示 …"""

    def __init__(self, text="", parent=None, elide_mode=Qt.TextElideMode.ElideRight):
        super().__init__(parent)
        self._full_text = text or ""
        self._elide_mode = elide_mode
        self.setWordWrap(False)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(40)
        self.setMinimumHeight(22)
        super().setText(self._full_text)

    def setText(self, text):
        self._full_text = text or ""
        self._apply_elide()

    def fullText(self):
        return self._full_text

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_elide()

    def _apply_elide(self):
        metrics = QFontMetrics(self.font())
        width = max(10, self.width() - 4)
        elided = metrics.elidedText(self._full_text, self._elide_mode, width)
        # 避免递归：直接调用父类 setText
        super().setText(elided)
        if self._full_text and elided != self._full_text:
            self.setToolTip(self._full_text)
        else:
            self.setToolTip("")
