# -*- coding: utf-8 -*-
"""日志图片无边框圆角预览窗：滚轮缩放、拖拽平移。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QPixmap, QWheelEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QWidget,
)

from utils.log_image_util import load_pixmap_limited, image_file_exists, normalize_image_path
from ui.styles import set_secondary_button


class _ZoomPanLabel(QLabel):
    """可缩放、拖拽的图片画布。"""

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
        self.setMouseTracking(True)

    def set_source(self, pix: QPixmap):
        self._source = pix
        self._scale = 1.0
        self._offset = QPoint(0, 0)
        self._fit_initial()
        self.update()

    def _fit_initial(self):
        if self._source.isNull() or self.width() < 10 or self.height() < 10:
            return
        sx = self.width() / max(1, self._source.width())
        sy = self.height() / max(1, self._source.height())
        self._scale = min(sx, sy, 1.0) * 0.92
        self._offset = QPoint(0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if abs(self._scale - 1.0) < 1e-6 and self._offset == QPoint(0, 0):
            self._fit_initial()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#f7fbff"))
        if self._source.isNull():
            painter.setPen(QColor("#6e675e"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "无法显示图片")
            return
        w = max(1, int(self._source.width() * self._scale))
        h = max(1, int(self._source.height() * self._scale))
        scaled = self._source.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2 + self._offset.x()
        y = (self.height() - scaled.height()) // 2 + self._offset.y()
        painter.drawPixmap(x, y, scaled)

    def wheelEvent(self, event: QWheelEvent):
        if self._source.isNull():
            return
        delta = event.angleDelta().y()
        factor = 1.12 if delta > 0 else (1 / 1.12)
        new_scale = max(0.08, min(8.0, self._scale * factor))
        self._scale = new_scale
        self.update()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            pos = event.position().toPoint()
            delta = pos - self._last_pos
            self._last_pos = pos
            self._offset += delta
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


class ImagePreviewDialog(QDialog):
    """独立无边框圆角预览窗口。"""

    def __init__(self, parent=None, image_path: str = ""):
        super().__init__(parent)
        self.setObjectName("imagePreviewDialog")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(720, 560)
        self.setMinimumSize(420, 320)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(0)

        self.panel = QFrame()
        self.panel.setObjectName("imagePreviewPanel")
        self.panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        shadow = QGraphicsDropShadowEffect(self.panel)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(64, 134, 214, 70))
        self.panel.setGraphicsEffect(shadow)

        lay = QVBoxLayout(self.panel)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("图片预览")
        title.setObjectName("imagePreviewTitle")
        head.addWidget(title, 1)
        btn_close = QPushButton("关闭")
        set_secondary_button(btn_close)
        btn_close.setFixedWidth(72)
        btn_close.clicked.connect(self.accept)
        head.addWidget(btn_close)
        lay.addLayout(head)

        hint = QLabel("滚轮缩放 · 拖拽移动 · 点击窗口空白处关闭")
        hint.setObjectName("imagePreviewHint")
        lay.addWidget(hint)

        self.canvas = _ZoomPanLabel()
        self.canvas.setObjectName("imagePreviewCanvas")
        lay.addWidget(self.canvas, 1)

        outer.addWidget(self.panel)

        rel = normalize_image_path(image_path)
        if not image_file_exists(rel):
            self.canvas.set_source(QPixmap())
        else:
            pix = load_pixmap_limited(rel, max_edge=2200)
            self.canvas.set_source(pix)

    def mousePressEvent(self, event: QMouseEvent):
        # 点击面板外空白关闭
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.panel.geometry().contains(event.pos()):
                self.accept()
                return
        super().mousePressEvent(event)


def open_log_image_preview(parent: QWidget | None, image_path: str) -> None:
    """打开预览；路径失效时由调用方提示，或此处返回 False。"""
    from PyQt6.QtWidgets import QMessageBox

    rel = normalize_image_path(image_path)
    if not rel or not image_file_exists(rel):
        QMessageBox.information(parent, "提示", "图片文件已丢失")
        return
    dlg = ImagePreviewDialog(parent, rel)
    dlg.exec()
