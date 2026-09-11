# -*- coding: utf-8 -*-
"""个人日记图片预览（独立加载器，不依赖班级 log_images）。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QPixmap, QWheelEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QWidget, QMessageBox,
)

from utils import personal_image_util
from ui.personal.leaf_button import LeafButton
from ui.personal.styles import PERSONAL_QSS


class _ZoomPanLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 160)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._source = QPixmap()
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self._dragging = False
        self._last_pos = QPoint()

    def set_source(self, pix: QPixmap):
        self._source = pix
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self._fit_initial()
        self.update()

    def _fit_initial(self):
        if self._source.isNull() or self.width() <= 0 or self.height() <= 0:
            return
        sx = self.width() / max(1, self._source.width())
        sy = self.height() / max(1, self._source.height())
        self._scale = min(sx, sy, 1.0) * 0.92

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e6f1ea"))
        if self._source.isNull():
            painter.setPen(QColor("#63806c"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "无图片")
            return
        w = int(self._source.width() * self._scale)
        h = int(self._source.height() * self._scale)
        x = (self.width() - w) // 2 + self._offset.x()
        y = (self.height() - h) // 2 + self._offset.y()
        painter.drawPixmap(x, y, w, h, self._source)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        self._scale = max(0.15, min(6.0, self._scale * factor))
        self.update()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            delta = event.pos() - self._last_pos
            self._offset += delta
            self._last_pos = event.pos()
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PersonalImagePreviewDialog(QDialog):
    def __init__(self, parent=None, image_path: str = "", absolute: bool = False):
        super().__init__(parent)
        self.setObjectName("personalDialog")
        self.setStyleSheet(PERSONAL_QSS)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(720, 560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)

        self.panel = QFrame()
        self.panel.setObjectName("personalCard")
        self.panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        shadow = QGraphicsDropShadowEffect(self.panel)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(87, 150, 105, 70))
        self.panel.setGraphicsEffect(shadow)

        lay = QVBoxLayout(self.panel)
        lay.setContentsMargins(14, 12, 14, 14)
        head = QHBoxLayout()
        title = QLabel("图片预览")
        title.setObjectName("pageTitle")
        head.addWidget(title, 1)
        btn_close = LeafButton("关闭", tone="soft")
        btn_close.clicked.connect(self.accept)
        head.addWidget(btn_close)
        lay.addLayout(head)

        self.canvas = _ZoomPanLabel()
        lay.addWidget(self.canvas, 1)
        outer.addWidget(self.panel)

        if absolute:
            pix = personal_image_util.load_pixmap_limited(image_path, 2200)
        else:
            if not personal_image_util.image_file_exists(image_path):
                pix = QPixmap()
            else:
                pix = personal_image_util.load_pixmap_limited(image_path, 2200)
        self.canvas.set_source(pix)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.panel.geometry().contains(event.pos()):
                self.accept()
                return
        super().mousePressEvent(event)


def open_personal_image_preview(parent: QWidget | None, image_path: str,
                                absolute: bool = False) -> None:
    if not image_path:
        QMessageBox.information(parent, "提示", "图片文件已丢失")
        return
    if not absolute and not personal_image_util.image_file_exists(image_path):
        QMessageBox.information(parent, "提示", "图片文件已丢失")
        return
    dlg = PersonalImagePreviewDialog(parent, image_path, absolute=absolute)
    dlg.exec()
