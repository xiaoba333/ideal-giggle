# -*- coding: utf-8 -*-
"""右侧错落便利贴堆：点击新建便签。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtWidgets import QWidget, QSizePolicy, QVBoxLayout

from ui.personal.handwriting_font import handwriting_font


class StickyStackWidget(QWidget):
    """视觉便签堆，点击弹出新建。"""

    create_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("essayStickyStack")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(170)
        self.setMaximumWidth(210)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 12)
        lay.addStretch(1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.create_requested.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 错落堆叠 4 张空白便签
        layers = (
            (18, 40, -8, "#e8d9b5"),
            (28, 55, 6, "#f0e0bd"),
            (22, 72, -4, "#f3e6c8"),
            (30, 90, 3, "#f7edd4"),
        )
        w, h = 118, 100
        for ox, oy, rot_hint, color in layers:
            # rot_hint 仅作视觉偏移，不真旋转以保持简单
            r = QRect(ox + abs(rot_hint), oy, w, h)
            # 阴影
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(60, 70, 50, 40))
            p.drawRoundedRect(r.adjusted(3, 4, 3, 4), 8, 8)
            p.setBrush(QColor(color))
            p.setPen(QPen(QColor("#c9b896"), 1))
            p.drawRoundedRect(r, 8, 8)
            p.setPen(QPen(QColor("#d4c4a0"), 1))
            p.drawLine(r.left() + 10, r.top() + 14, r.right() - 10, r.top() + 14)

        # 顶部标签
        p.setFont(handwriting_font(12, bold=True))
        p.setPen(QColor("#5c4030"))
        p.drawText(
            QRect(20, 8, self.width() - 40, 28),
            Qt.AlignmentFlag.AlignCenter,
            "便利贴",
        )
