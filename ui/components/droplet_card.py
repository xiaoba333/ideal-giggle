# -*- coding: utf-8 -*-
"""水滴外凸立体卡片基类：阴影由 paintEvent 手绘，无 QGraphicsEffect。"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QSizePolicy

from ui.styles import COLOR_BG, COLOR_BORDER


class DropletCard(QFrame):
    """
    水滴凸起卡片：大圆角 + 浅蓝描边 + QPainter 柔和投影。
    内部自带内边距，子控件不得贴边。
    """

    def __init__(self, parent=None, min_width=220, min_height=200):
        super().__init__(parent)
        self.setObjectName("dropletCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setMinimumSize(min_width, min_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # 不再挂载 QGraphicsDropShadowEffect；投影在 paintEvent 内绘制
        # self.setCacheMode(...)  # 已禁用

        self._shadow_enabled = True

        outer = QVBoxLayout(self)
        # 底部/右侧留出投影绘制空间
        outer.setContentsMargins(6, 4, 10, 12)
        outer.setSpacing(0)

        self.inner = QFrame()
        self.inner.setObjectName("dropletInner")
        self.inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.content_layout = QVBoxLayout(self.inner)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(10)
        outer.addWidget(self.inner)

    def content(self):
        """返回内容区布局，供子类填充控件。"""
        return self.content_layout

    def set_shadow_enabled(self, enabled: bool):
        """滚动期间可临时关闭手绘阴影以减负。"""
        enabled = bool(enabled)
        if self._shadow_enabled == enabled:
            return
        self._shadow_enabled = enabled
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 所有绘制、translate、坐标变换代码写在这里
        face = self.rect().adjusted(2, 1, -8, -8)

        if self._shadow_enabled:
            for i, alpha in enumerate((28, 18, 10, 5)):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(64, 134, 214, alpha))
                painter.drawRoundedRect(
                    face.adjusted(2 + i, 3 + i, 2 + i, 3 + i), 28, 28
                )

        painter.setPen(QPen(QColor(COLOR_BORDER), 2))
        painter.setBrush(QBrush(QColor(COLOR_BG)))
        painter.drawRoundedRect(face, 28, 28)
