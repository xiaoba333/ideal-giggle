# -*- coding: utf-8 -*-
"""迷你模式（横屏）：上方时间 + 下方缩小天气图标与温度（无轮播）。"""

from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QSizePolicy,
)

from ui.components.date_module import DateModule
from ui.components.mini_weather_widget import MiniWeatherWidget
from ui.components.home_styles import HOME_MODULE_QSS
from ui.styles import set_secondary_button


class MiniTodoWidget(QWidget):
    """迷你小窗：时间靠上，下方常驻天气图标+温度。"""

    request_full_mode = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("miniPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(HOME_MODULE_QSS)
        self._drag_pos: QPoint | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 0, 2, 2)
        root.setSpacing(0)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(2)
        title_row.addStretch(1)

        self.chk_pin = QCheckBox("置顶")
        self.chk_pin.setObjectName("miniPinCheck")
        self.chk_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        title_row.addWidget(self.chk_pin, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_switch = QPushButton("完整")
        self.btn_switch.setObjectName("miniSwitchBtn")
        self.btn_switch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_switch.setFixedHeight(18)
        self.btn_switch.setMaximumWidth(42)
        set_secondary_button(self.btn_switch)
        self.btn_switch.clicked.connect(self.request_full_mode.emit)
        title_row.addWidget(self.btn_switch, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(title_row, 0)

        # 时间靠上
        self.date_module = DateModule(compact=True)
        self.date_module.setMinimumHeight(0)
        self.date_module.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        root.addWidget(self.date_module, 1)

        # 时间下方：缩小天气图标 + 温度（常驻，不轮播）
        self.weather_module = MiniWeatherWidget(strip=True)
        self.weather_module.setMinimumHeight(36)
        self.weather_module.setMaximumHeight(44)
        self.weather_module.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.weather_module.pause_ui()
        root.addWidget(self.weather_module, 0)

    def reset_scroll(self):
        pass

    def showEvent(self, event):
        super().showEvent(event)
        self.date_module.refresh()

    def refresh(self):
        self.date_module.refresh()
        if hasattr(self.weather_module, "resume_ui"):
            if getattr(self.weather_module, "_ui_active", False):
                self.weather_module.refresh()
        elif getattr(self.weather_module, "_network_enabled", False):
            self.weather_module.refresh()

    # ---------- 无边框窗口拖拽 ----------
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            self._drag_pos = (
                event.globalPosition().toPoint() - win.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (
            self._drag_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
        super().mouseReleaseEvent(event)
