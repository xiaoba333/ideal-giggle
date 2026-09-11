# -*- coding: utf-8 -*-
"""
首页：模块化布局（整体可纵向滚动）。
日期水滴卡 + 天气水滴卡 + 待办滚动屏 + 班级日志卡片流。
"""

from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QAbstractScrollArea,
)

from ui.components.date_module import DateModule
from ui.components.weather_module import WeatherModule
from ui.components.todo_scroll_board import TodoScrollBoard
from ui.components.class_log_flow import ClassLogFlow
from ui.components.home_paper_calendar import HomePaperCalendarWidget
from ui.components.home_styles import HOME_MODULE_QSS
from ui.components.text_label_util import ElideLabel
from ui.components.paint_cache import enable_scroll_friendly
from ui.styles import set_secondary_button
from service import todo_service


class HomeWidget(QWidget):
    """首页面板（完整大屏 · QScrollArea 包裹）。"""

    jump_to_log = pyqtSignal(str)
    jump_to_todo = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeRoot")
        self.setStyleSheet(HOME_MODULE_QSS)
        self._scrolling = False
        self._scroll_end_timer = QTimer(self)
        self._scroll_end_timer.setSingleShot(True)
        self._scroll_end_timer.setInterval(120)
        self._scroll_end_timer.timeout.connect(self._on_scroll_settled)
        self._build_ui()
        self.refresh()

    def is_scrolling(self) -> bool:
        return self._scrolling

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("homeScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scroll.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored
        )
        # 不透明视口，降低滚动时底层擦除开销（QScrollArea 无 ScrollPerPixel API）
        vp = self.scroll.viewport()
        enable_scroll_friendly(vp)
        vp.setAutoFillBackground(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.inner = QWidget()
        self.inner.setObjectName("homeScrollInner")
        enable_scroll_friendly(self.inner)
        self.inner.setAutoFillBackground(True)
        layout = QVBoxLayout(self.inner)
        layout.setContentsMargins(16, 16, 16, 20)
        layout.setSpacing(16)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        title = ElideLabel("首页")
        title.setObjectName("pageTitle")
        title.setMinimumHeight(28)
        top_bar.addWidget(title, 1)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setMinimumSize(72, 32)
        set_secondary_button(self.btn_refresh)
        self.btn_refresh.clicked.connect(self.refresh)
        top_bar.addWidget(self.btn_refresh, 0)
        layout.addLayout(top_bar)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.date_module = DateModule()
        self.weather_module = WeatherModule()
        self.date_module.setMinimumHeight(300)
        self.weather_module.setMinimumHeight(300)
        cards.addWidget(self.date_module, 1)
        cards.addWidget(self.weather_module, 1)
        layout.addLayout(cards)

        self.paper_calendar = HomePaperCalendarWidget()
        self.paper_calendar.setMinimumHeight(400)
        self.paper_calendar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.paper_calendar.date_selected.connect(self._on_calendar_date)
        self.paper_calendar.add_log_requested.connect(self._on_calendar_add_log)
        self.paper_calendar.add_todo_requested.connect(self._on_calendar_add_todo)
        layout.addWidget(self.paper_calendar)

        self.todo_board = TodoScrollBoard(compact=False)
        self.todo_board.setMinimumHeight(260)
        self.todo_board.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.todo_board.item_clicked.connect(self._on_todo_clicked)
        layout.addWidget(self.todo_board)

        self.log_flow = ClassLogFlow(nested_scroll=False)
        self.log_flow.setMinimumHeight(180)
        self.log_flow.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.log_flow)

        layout.addStretch(1)

        self.scroll.setWidget(self.inner)
        outer.addWidget(self.scroll)

        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_moved)

    def _on_scroll_moved(self, _value: int):
        if not self._scrolling:
            self._scrolling = True
            self._set_heavy_effects_enabled(False)
        self._scroll_end_timer.start()

    def _on_scroll_settled(self):
        self._scrolling = False
        self._set_heavy_effects_enabled(True)
        if hasattr(self.date_module, "refresh"):
            self.date_module.refresh(force=True)

    def _set_heavy_effects_enabled(self, enabled: bool):
        """滚动中可关闭手绘阴影减负（无 QGraphicsEffect）。"""
        for w in (self.date_module, self.weather_module):
            if hasattr(w, "set_shadow_enabled"):
                w.set_shadow_enabled(enabled)

    def reset_scroll(self):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(0)
        self.scroll.horizontalScrollBar().setValue(0)

    def pause_weather_network(self):
        """切迷你：不停定时器，仅暂停 UI 刷新。"""
        if hasattr(self.weather_module, "pause_ui"):
            self.weather_module.pause_ui()
        else:
            self.weather_module.stop_network()

    def resume_weather_network(self, reload=True):
        if hasattr(self.weather_module, "resume_ui"):
            self.weather_module.resume_ui(reload=reload)
        else:
            self.weather_module.start_network(reload=reload)

    def set_modules_visible_for_full(self):
        self.date_module.show()
        self.weather_module.show()
        self.paper_calendar.show()
        self.todo_board.show()
        self.log_flow.show()
        self.btn_refresh.show()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._scrolling:
            self.refresh()

    def refresh(self):
        if self._scrolling:
            return
        self.date_module.refresh(force=True)
        self.weather_module.refresh()
        self.paper_calendar.refresh()
        self.todo_board.reload()
        self.log_flow.reload()

    def _on_calendar_date(self, qdate):
        """首页点击日期仅高亮选中，不跳转到班级日志 / 待办页。"""
        return

    def _on_calendar_add_log(self, qdate):
        from PyQt6.QtWidgets import QMessageBox, QDialog
        from ui.log_widget import LogFormDialog
        from service import classlog_service

        if not qdate or not qdate.isValid():
            return
        date_str = qdate.toString("yyyy-MM-dd")
        dialog = LogFormDialog(self, default_date=date_str, lock_date=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        try:
            classlog_service.add_log(**data)
            QMessageBox.information(self, "成功", "日志已新增")
            self.paper_calendar.refresh()
            self.log_flow.reload()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_calendar_add_todo(self, qdate):
        from PyQt6.QtWidgets import QMessageBox, QDialog
        from ui.todo_widget import TodoFormDialog

        if not qdate or not qdate.isValid():
            return
        date_str = qdate.toString("yyyy-MM-dd")
        dialog = TodoFormDialog(self, default_deadline=date_str)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            todo_service.add_todo(**dialog.get_data())
            QMessageBox.information(self, "成功", "待办已新增")
            self.todo_board.reload()
            self.paper_calendar.refresh()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_todo_clicked(self, todo_id):
        from PyQt6.QtWidgets import QMessageBox, QDialog
        from ui.todo_widget import TodoFormDialog

        try:
            todo = todo_service.get_todo(todo_id)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取待办失败：\n{e}")
            return
        if not todo:
            QMessageBox.information(self, "提示", "该待办不存在或已删除")
            self.todo_board.reload()
            return

        dialog = TodoFormDialog(self, todo)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.deleted:
            try:
                todo_service.remove_todo(todo_id)
                QMessageBox.information(self, "成功", "已删除")
                self.todo_board.reload()
                self.paper_calendar.refresh()
            except Exception as e:
                QMessageBox.warning(self, "失败", str(e))
            return
        if not dialog.is_changed():
            return
        try:
            todo_service.edit_todo(todo_id, **dialog.get_data())
            QMessageBox.information(self, "成功", "待办已更新")
            self.todo_board.reload()
            self.paper_calendar.refresh()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
