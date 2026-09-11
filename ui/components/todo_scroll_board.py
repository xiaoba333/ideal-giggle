# -*- coding: utf-8 -*-
"""待办事项电子滚动显示屏（个人 / 班级左右分栏）。"""

from PyQt6.QtCore import Qt, QTimer, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QSlider, QSizePolicy,
)

from service import todo_service
from service.todo_service import SCOPE_PERSONAL, SCOPE_CLASS
from utils.date_util import format_date
from ui.components.home_styles import make_art_font
from ui.styles import COLOR_DANGER


class TodoScrollViewport(QWidget):
    """内部绘制区：纵向循环滚动；单击条目发出 item_clicked(todo_id)。"""

    item_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("todoScrollViewport")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._todos = []
        self._lines = []
        self._offset = 0
        self._line_height = 28
        self._paused = False
        self._speed = 1
        self._content_height = 0

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._on_tick)

        self._font = make_art_font(12, bold=False)

    def set_speed(self, pixels_per_tick):
        self._speed = max(1, int(pixels_per_tick))

    def set_interval_ms(self, ms):
        self._timer.setInterval(max(16, int(ms)))

    def set_todos(self, todos):
        self._todos = list(todos or [])
        self._lines = []
        if not self._todos:
            self._lines = [("暂无待办事项", QColor("#8eb8e0"))]
        else:
            for row in self._todos:
                urgency = int(row.get("urgency") or 0)
                status = todo_service.status_display(row)
                deadline = format_date(row.get("deadline")) or "无截止"
                title = row.get("title") or ""
                flag = "【紧急】" if urgency == 1 else "【普通】"
                text = f"{flag} {title}  ·  {deadline}  ·  {status}"
                color = QColor(COLOR_DANGER) if urgency == 1 else QColor("#7ec8ff")
                if todo_service.is_overdue(row):
                    color = QColor("#ff8a80")
                    text = f"⚠逾期  {text}"
                self._lines.append((text, color))

        self._line_height = max(26, self._font.pointSize() + 16)
        self._content_height = len(self._lines) * self._line_height
        self._offset = 0
        self.update()

    def start_scroll(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop_scroll(self):
        self._timer.stop()

    def enterEvent(self, event):
        self._paused = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._paused = False
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._todos:
            idx = self._hit_index(event.position().y())
            if idx is not None and 0 <= idx < len(self._todos):
                todo_id = self._todos[idx].get("id")
                if todo_id is not None:
                    self.item_clicked.emit(int(todo_id))
        super().mousePressEvent(event)

    def _hit_index(self, y):
        if not self._todos or self._line_height <= 0:
            return None
        loop_h = max(self._content_height, self.height())
        for cycle in (0, 1):
            base_y = -self._offset + cycle * (loop_h + self._line_height)
            for i in range(len(self._todos)):
                top = base_y + i * self._line_height
                if top <= y < top + self._line_height:
                    return i
        return None

    def _on_tick(self):
        if self._paused or self._content_height <= 0:
            return
        loop_h = max(self._content_height, self.height())
        self._offset = (self._offset + self._speed) % (loop_h + self._line_height)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        painter.fillRect(self.rect(), QColor("#0f2740"))

        painter.setPen(QPen(QColor(64, 134, 214, 40), 1))
        for y in range(0, self.height(), 4):
            painter.drawLine(0, y, self.width(), y)

        painter.setFont(self._font)
        if self._lines:
            loop_h = max(self._content_height, self.height())
            for cycle in (0, 1):
                base_y = -self._offset + cycle * (loop_h + self._line_height)
                for i, (text, color) in enumerate(self._lines):
                    y = int(base_y + i * self._line_height)
                    if y + self._line_height < 0 or y > self.height():
                        continue
                    painter.setPen(color)
                    rect = QRect(12, y, self.width() - 24, self._line_height)
                    painter.drawText(
                        rect,
                        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                        text,
                    )

        painter.fillRect(0, 0, self.width(), 3, QColor(64, 134, 214, 120))


class TodoScrollBoard(QWidget):
    """带外框与速度控制的待办滚动显示屏：左个人 / 右班级。"""

    item_clicked = pyqtSignal(int)

    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self._compact = compact
        self._build_ui()
        self.reload()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4 if self._compact else 8)

        head = QHBoxLayout()
        caption = QLabel("待办事项")
        caption.setObjectName("todoScrollCaption")
        head.addWidget(caption)
        head.addStretch()

        tip = QLabel("单击编辑 · 悬停暂停")
        tip.setObjectName("todoScrollHint")
        head.addWidget(tip)

        speed_lbl = QLabel("速度")
        speed_lbl.setObjectName("todoScrollHint")
        head.addWidget(speed_lbl)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 5)
        self.speed_slider.setValue(2)
        self.speed_slider.setFixedWidth(72 if self._compact else 100)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        head.addWidget(self.speed_slider)
        root.addLayout(head)

        shell = QFrame()
        shell.setObjectName("todoScrollShell")
        shell_lay = QHBoxLayout(shell)
        shell_lay.setContentsMargins(6 if self._compact else 8, 6, 6, 6)
        shell_lay.setSpacing(8 if self._compact else 10)

        self.viewport_personal = self._make_column(
            shell_lay, "个人", compact=self._compact
        )
        self.viewport_class = self._make_column(
            shell_lay, "班级", compact=self._compact
        )
        root.addWidget(shell)
        self.setMinimumHeight(160 if self._compact else 260)

        self._on_speed_changed(self.speed_slider.value())

    def _make_column(self, parent_lay, title, compact=False):
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("todoScrollColumnTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(title_lbl)

        bezel = QFrame()
        bezel.setObjectName("todoScrollBezel")
        bezel_lay = QVBoxLayout(bezel)
        bezel_lay.setContentsMargins(4, 4, 4, 4)

        viewport = TodoScrollViewport()
        viewport.item_clicked.connect(self.item_clicked.emit)
        if compact:
            viewport.setFixedHeight(120)
            viewport.setMinimumHeight(100)
        else:
            viewport.setMinimumHeight(160)
            viewport.setFixedHeight(200)
        bezel_lay.addWidget(viewport)
        col.addWidget(bezel, 1)
        parent_lay.addLayout(col, 1)
        return viewport

    def _viewports(self):
        return (self.viewport_personal, self.viewport_class)

    def _on_speed_changed(self, value):
        for vp in self._viewports():
            vp.set_speed(value)
            vp.set_interval_ms(48 - value * 4)

    def reload(self):
        try:
            personal = list(todo_service.list_todos(status=0, scope=SCOPE_PERSONAL))
            class_rows = list(todo_service.list_todos(status=0, scope=SCOPE_CLASS))
        except Exception as e:
            personal, class_rows = [], []
            print(f"[待办滚动屏] 加载失败: {e}")
        self.viewport_personal.set_todos(personal)
        self.viewport_class.set_todos(class_rows)
        for vp in self._viewports():
            vp.start_scroll()

    def showEvent(self, event):
        super().showEvent(event)
        for vp in self._viewports():
            vp.start_scroll()

    def hideEvent(self, event):
        for vp in self._viewports():
            vp.stop_scroll()
        super().hideEvent(event)
