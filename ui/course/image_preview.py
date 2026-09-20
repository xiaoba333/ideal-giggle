# -*- coding: utf-8 -*-
"""课程笔记图片预览：滚轮缩放，黑白极简。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QWheelEvent
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from ui.course.styles import COURSE_QSS


class CourseImagePreviewDialog(QDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setObjectName("courseShell")
        self.setWindowTitle("图片预览")
        self.setModal(True)
        self.resize(720, 520)
        self.setStyleSheet(COURSE_QSS)
        self._source = pixmap if pixmap is not None else QPixmap()
        self._scale = 1.0

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self.view = QLabel("无法显示图片")
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setMinimumSize(320, 240)
        self.view.setStyleSheet(
            "QLabel { background:#ffffff; color:#666666;"
            " border:1px solid #e8e8e8; }"
        )
        root.addWidget(self.view, 1)

        row = QHBoxLayout()
        row.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_close)
        root.addLayout(row)
        self._refresh()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta == 0 or self._source.isNull():
            return
        self._scale *= 1.12 if delta > 0 else 0.89
        self._scale = max(0.2, min(4.0, self._scale))
        self._refresh()
        event.accept()

    def _refresh(self):
        if self._source.isNull():
            self.view.setText("无法显示图片")
            self.view.setPixmap(QPixmap())
            return
        w = max(1, int(self._source.width() * self._scale))
        h = max(1, int(self._source.height() * self._scale))
        shown = self._source.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.view.setPixmap(shown)
        self.view.setText("")
