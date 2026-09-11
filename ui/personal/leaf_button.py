# -*- coding: utf-8 -*-
"""树叶造型按钮：手绘叶片轮廓 + 纵向绿渐变 + 叶脉肌理。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient, QFont,
)
from PyQt6.QtWidgets import QPushButton, QSizePolicy

from ui.personal.styles import COLOR_BTN, COLOR_BTN_HOVER, COLOR_BTN_PRESSED


class LeafButton(QPushButton):
    """个人模式专用叶片按钮（不走主界面木纹 QSS）。"""

    def __init__(self, text="", parent=None, tone="normal"):
        super().__init__(text, parent)
        self._tone = tone  # normal / deep / soft
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(88, 36)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        font = QFont("Microsoft YaHei")
        font.setPointSize(10)
        font.setBold(True)
        self.setFont(font)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def _base_colors(self):
        if self._tone == "deep":
            return QColor("#3f7550"), QColor("#579669"), QColor("#2f5a3c")
        if self._tone == "soft":
            return QColor("#6aad7c"), QColor("#8bc49a"), QColor("#579669")
        return QColor(COLOR_BTN), QColor(COLOR_BTN_HOVER), QColor(COLOR_BTN_PRESSED)

    def _fill_color(self):
        base, hover, pressed = self._base_colors()
        if self.isDown():
            return pressed
        if self.underMouse() and self.isEnabled():
            return hover
        return base

    def _leaf_path(self, rect: QRectF) -> QPainterPath:
        path = QPainterPath()
        # 不规则波浪大圆角叶片轮廓
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        path.moveTo(x + w * 0.12, y + h * 0.55)
        path.cubicTo(
            x + w * 0.02, y + h * 0.18,
            x + w * 0.22, y + h * 0.02,
            x + w * 0.48, y + h * 0.08,
        )
        path.cubicTo(
            x + w * 0.72, y + h * 0.02,
            x + w * 0.98, y + h * 0.22,
            x + w * 0.92, y + h * 0.52,
        )
        path.cubicTo(
            x + w * 0.98, y + h * 0.78,
            x + w * 0.70, y + h * 0.98,
            x + w * 0.45, y + h * 0.92,
        )
        path.cubicTo(
            x + w * 0.20, y + h * 0.98,
            x + w * 0.00, y + h * 0.78,
            x + w * 0.12, y + h * 0.55,
        )
        path.closeSubpath()
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        margin = 2.0
        rect = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
        path = self._leaf_path(rect)

        fill = self._fill_color()
        if not self.isEnabled():
            fill = QColor("#a8b8ad")

        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        top = QColor(fill)
        top = top.lighter(118)
        bottom = QColor(fill).darker(112)
        grad.setColorAt(0.0, top)
        grad.setColorAt(1.0, bottom)

        painter.setPen(QPen(QColor(fill).darker(130), 1.4))
        painter.setBrush(QBrush(grad))
        painter.drawPath(path)

        # 细密叶脉
        painter.setClipPath(path)
        vein = QColor(255, 255, 255, 55)
        painter.setPen(QPen(vein, 1.0))
        cx = rect.center().x()
        cy = rect.center().y()
        painter.drawLine(QPointF(cx - rect.width() * 0.28, cy),
                         QPointF(cx + rect.width() * 0.30, cy - 1))
        for i, t in enumerate((0.25, 0.40, 0.55, 0.70)):
            bx = rect.left() + rect.width() * t
            painter.drawLine(
                QPointF(bx, cy),
                QPointF(bx + 6, cy - (8 if i % 2 == 0 else 10)),
            )
            painter.drawLine(
                QPointF(bx, cy),
                QPointF(bx + 5, cy + (8 if i % 2 == 0 else 9)),
            )
        painter.setClipping(False)

        painter.setPen(QColor("#ffffff"))
        painter.setFont(self.font())
        painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), self.text())

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)
