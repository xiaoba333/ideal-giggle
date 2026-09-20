# -*- coding: utf-8 -*-
"""
主窗口：完整大屏 / 迷你小窗双固定模式。
以 is_mini_mode 统一控制模块显隐；setFixedSize 锁定尺寸。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow, QStatusBar, QVBoxLayout, QWidget,
    QToolBar, QStackedWidget, QMessageBox, QApplication, QDialog,
)

from ui.home_widget import HomeWidget
from ui.student_widget import StudentWidget
from ui.todo_widget import TodoWidget
from ui.log_widget import LogWidget
from ui.moral_widget import MoralStatsWidget
from ui.mini_todo_widget import MiniTodoWidget
from ui.components.dissolve_tab_widget import DissolveTabWidget
from ui.personal import PersonalShellWidget, run_personal_pin_gate
from ui.course import CourseShellWidget
from ui.styles import apply_widget_style
from ui import window_mode


class MainWindow(QMainWindow):
    TAB_HOME = 0
    TAB_STUDENT = 1
    TAB_TODO = 2
    TAB_LOG = 3
    TAB_MORAL = 4

    STACK_FULL = 0
    STACK_MINI = 1
    STACK_PERSONAL = 2
    STACK_COURSE = 3

    def __init__(self):
        super().__init__()
        self.setWindowTitle("班级管理系统")
        self.is_mini_mode = False
        self.is_personal_mode = False
        self.is_course_mode = False
        self._force_close = False
        apply_widget_style(self)
        self._build_ui()
        self._apply_layout_by_mode(is_mini_mode=False, initial=True)

    def _build_ui(self):
        self.toolbar = QToolBar("窗口模式")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.addToolBar(self.toolbar)

        self.action_toggle = QAction("切换迷你模式", self)
        self.action_toggle.triggered.connect(self.toggle_window_mode)
        self.toolbar.addAction(self.action_toggle)

        self.action_personal = QAction("进入个人模式", self)
        self.action_personal.triggered.connect(self.enter_personal_mode)
        self.toolbar.addAction(self.action_personal)

        self.action_course = QAction("课程模式", self)
        self.action_course.triggered.connect(self.enter_course_mode)
        self.toolbar.addAction(self.action_course)

        self.toolbar.addSeparator()
        self.action_safe_exit = QAction("安全退出", self)
        self.action_safe_exit.setToolTip("确认后安全关闭程序，避免数据丢失")
        self.action_safe_exit.triggered.connect(self.safe_exit)
        self.toolbar.addAction(self.action_safe_exit)

        self.stack = QStackedWidget()

        # —— 完整大屏面板（预实例化，不销毁）——
        self.full_panel = QWidget()
        full_layout = QVBoxLayout(self.full_panel)
        full_layout.setContentsMargins(12, 12, 12, 12)
        full_layout.setSpacing(10)

        self.tabs = DissolveTabWidget()
        self.home_widget = HomeWidget()
        self.student_widget = StudentWidget()
        self.todo_widget = TodoWidget()
        self.log_widget = LogWidget()
        self.moral_widget = MoralStatsWidget()

        self.tabs.addTab(self.home_widget, "首页")
        self.tabs.addTab(self.student_widget, "学生信息管理")
        self.tabs.addTab(self.todo_widget, "待办事项")
        self.tabs.addTab(self.log_widget, "班级日志")
        self.tabs.addTab(self.moral_widget, "德育分统计")

        self.home_widget.jump_to_log.connect(self._goto_log_day)
        self.home_widget.jump_to_todo.connect(self._goto_todo)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        full_layout.addWidget(self.tabs)
        self.stack.addWidget(self.full_panel)

        # —— 迷你面板（预实例化：仅日期+待办）——
        self.mini_widget = MiniTodoWidget()
        self.mini_widget.request_full_mode.connect(self.switch_to_full_mode)
        self.mini_widget.chk_pin.toggled.connect(self._on_pin_toggled)
        self.stack.addWidget(self.mini_widget)

        # —— 个人模式面板（预实例化，与班级主界面隔离）——
        self.personal_widget = PersonalShellWidget()
        self.personal_widget.exit_requested.connect(self.exit_personal_mode)
        self.personal_widget.quit_requested.connect(self.safe_exit)
        self.stack.addWidget(self.personal_widget)

        # —— 课程模式面板（独立页面，不与个人 / 迷你共用控件）——
        self.course_widget = CourseShellWidget()
        self.course_widget.exit_requested.connect(self.exit_course_mode)
        self.stack.addWidget(self.course_widget)

        self.setCentralWidget(self.stack)

        status = QStatusBar()
        status.showMessage("就绪 · 完整大屏模式")
        self.setStatusBar(status)

    def toggle_window_mode(self):
        if self.is_personal_mode or self.is_course_mode:
            return
        self._apply_layout_by_mode(is_mini_mode=not self.is_mini_mode, initial=False)

    def switch_to_full_mode(self):
        if self.is_personal_mode:
            self.exit_personal_mode()
            return
        if self.is_course_mode:
            self.exit_course_mode()
            return
        self._apply_layout_by_mode(is_mini_mode=False, initial=False)

    def switch_to_mini_mode(self):
        if self.is_personal_mode or self.is_course_mode:
            return
        self._apply_layout_by_mode(is_mini_mode=True, initial=False)

    def enter_personal_mode(self):
        """PIN 校验通过后隐藏班级控件，加载个人界面（同尺寸）。"""
        if self.is_personal_mode or self.is_course_mode:
            return
        if self.is_mini_mode:
            self.switch_to_full_mode()
        if not run_personal_pin_gate(self):
            return
        self.setUpdatesEnabled(False)
        try:
            self.is_personal_mode = True
            self.home_widget.pause_weather_network()
            self.full_panel.hide()
            self.tabs.hide()
            self.mini_widget.hide()
            self.course_widget.hide()
            self.toolbar.hide()
            self.statusBar().hide()
            self.personal_widget.show()
            self.stack.setCurrentIndex(self.STACK_PERSONAL)
            self.setFixedSize(window_mode.FULL_WIDTH, window_mode.FULL_HEIGHT)
            self.setWindowTitle("个人模式")
            self.personal_widget.on_enter()
            self.show()
        finally:
            self.setUpdatesEnabled(True)

    def exit_personal_mode(self):
        """退出个人模式，恢复班级主界面。"""
        if not self.is_personal_mode:
            return
        self.setUpdatesEnabled(False)
        try:
            self.is_personal_mode = False
            self.personal_widget.hide()
            self.course_widget.hide()
            self.setWindowTitle("班级管理系统")
            # 回到完整大屏班级界面
            self._apply_layout_by_mode(is_mini_mode=False, initial=False)
            self.statusBar().showMessage("已退出个人模式", 3000)
        finally:
            self.setUpdatesEnabled(True)

    def enter_course_mode(self):
        """进入课程模式：独立页面，窗口尺寸与主界面一致。"""
        if self.is_course_mode or self.is_personal_mode or self.is_mini_mode:
            return
        self.setUpdatesEnabled(False)
        try:
            self.is_course_mode = True
            self.home_widget.pause_weather_network()
            self.full_panel.hide()
            self.tabs.hide()
            self.mini_widget.hide()
            self.personal_widget.hide()
            self.toolbar.hide()
            self.statusBar().hide()
            self.course_widget.show()
            self.stack.setCurrentIndex(self.STACK_COURSE)
            self.setFixedSize(window_mode.FULL_WIDTH, window_mode.FULL_HEIGHT)
            self.setWindowTitle("课程模式")
            self.course_widget.on_enter()
            self.show()
        finally:
            self.setUpdatesEnabled(True)

    def exit_course_mode(self):
        """退出课程模式，先落库再回到班级主界面。"""
        if not self.is_course_mode:
            return
        try:
            self.course_widget.flush()
        except Exception:
            pass
        self.setUpdatesEnabled(False)
        try:
            self.is_course_mode = False
            self.course_widget.hide()
            self.setWindowTitle("班级管理系统")
            self._apply_layout_by_mode(is_mini_mode=False, initial=False)
            self.statusBar().showMessage("已退出课程模式", 3000)
        finally:
            self.setUpdatesEnabled(True)

    def _apply_layout_by_mode(self, is_mini_mode, initial=False):
        """
        根据 is_mini_mode 统一控制显隐、尺寸与网络任务。
        两套界面 show()/hide()，不销毁组件。
        """
        self.setUpdatesEnabled(False)
        try:
            self.is_mini_mode = bool(is_mini_mode)
            window_mode.set_mode(
                window_mode.MODE_MINI if self.is_mini_mode else window_mode.MODE_FULL
            )

            if self.is_mini_mode:
                self._enter_mini_mode(initial=initial)
            else:
                self._enter_full_mode(initial=initial)
        finally:
            self.setUpdatesEnabled(True)

    def _enter_full_mode(self, initial=False):
        if self.isMaximized():
            self.showNormal()

        self._apply_window_flags(mini=False, stay_on_top=False)

        # 停迷你天气 UI，大屏天气恢复（定时器全程不停）
        if hasattr(self.mini_widget.weather_module, "pause_ui"):
            self.mini_widget.weather_module.pause_ui()
        else:
            self.mini_widget.weather_module.stop_network()

        self.mini_widget.hide()
        self.personal_widget.hide()
        self.course_widget.hide()
        self.full_panel.show()
        self.stack.setCurrentIndex(self.STACK_FULL)

        self.tabs.show()
        self.home_widget.set_modules_visible_for_full()
        self.home_widget.resume_weather_network(reload=not initial)

        self.toolbar.show()
        self.statusBar().show()
        self.action_toggle.setText("切换迷你模式")
        self.action_personal.setVisible(True)
        self.action_course.setVisible(True)

        self.setFixedSize(window_mode.FULL_WIDTH, window_mode.FULL_HEIGHT)
        self.setMaximumSize(16777215, 16777215)
        self.setMinimumSize(window_mode.FULL_WIDTH, window_mode.FULL_HEIGHT)
        self.resize(window_mode.FULL_WIDTH, window_mode.FULL_HEIGHT)

        self.show()
        self.home_widget.reset_scroll()
        if not initial:
            self.todo_widget.refresh_table()
            self.home_widget.todo_board.reload()
            self.home_widget.log_flow.reload()
            self.home_widget.paper_calendar.refresh()
            self.home_widget.date_module.refresh()
            self.statusBar().showMessage("已切换到完整大屏模式", 3000)
        else:
            self.statusBar().showMessage("就绪 · 完整大屏模式")

    def _enter_mini_mode(self, initial=False):
        if self.isMaximized():
            self.showNormal()

        # 大屏天气仅暂停 UI；迷你先灌入大屏快照再刷新（同城），避免图标不一致
        self.home_widget.pause_weather_network()
        home_weather = self.home_widget.weather_module
        mini_weather = self.mini_widget.weather_module
        if hasattr(mini_weather, "seed_from"):
            mini_weather.seed_from(
                home_weather.last_weather() if hasattr(home_weather, "last_weather") else None,
                home_weather.session_city() if hasattr(home_weather, "session_city") else None,
            )

        pin = self.mini_widget.chk_pin.isChecked()
        self._apply_window_flags(mini=True, stay_on_top=pin)

        self.full_panel.hide()
        self.tabs.hide()
        self.toolbar.hide()
        self.statusBar().hide()
        self.personal_widget.hide()
        self.course_widget.hide()

        self.mini_widget.show()
        self.stack.setCurrentIndex(self.STACK_MINI)
        if hasattr(mini_weather, "resume_ui"):
            # reload 用共享城市，不再另起 IP 定位
            mini_weather.resume_ui(reload=True)
        else:
            mini_weather.start_network(reload=True)

        self.action_toggle.setText("切换完整模式")

        self.setFixedSize(window_mode.MINI_WIDTH, window_mode.MINI_HEIGHT)

        self.show()
        self.mini_widget.reset_scroll()
        self.mini_widget.refresh()

    def _apply_window_flags(self, mini, stay_on_top):
        if mini:
            # 无边框：去掉系统标题栏（深色主题下呈黑色顶栏）
            flags = (
                Qt.WindowType.Window
                | Qt.WindowType.FramelessWindowHint
            )
        else:
            flags = (
                Qt.WindowType.Window
                | Qt.WindowType.WindowTitleHint
                | Qt.WindowType.WindowSystemMenuHint
                | Qt.WindowType.WindowMinimizeButtonHint
                | Qt.WindowType.WindowMaximizeButtonHint
                | Qt.WindowType.WindowCloseButtonHint
            )
        if stay_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        # 仅在标志变化时设置，减少闪烁
        if self.windowFlags() != flags:
            self.setWindowFlags(flags)

    def _on_pin_toggled(self, checked):
        if not self.is_mini_mode:
            return
        self.setUpdatesEnabled(False)
        try:
            self._apply_window_flags(mini=True, stay_on_top=checked)
            self.show()
        finally:
            self.setUpdatesEnabled(True)

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        super().changeEvent(event)
        if event.type() != QEvent.Type.WindowStateChange:
            return
        if self.is_mini_mode or self.is_personal_mode or self.is_course_mode:
            return
        # 大屏还原时锁回固定尺寸
        if not self.isMaximized():
            self.setMinimumSize(window_mode.FULL_WIDTH, window_mode.FULL_HEIGHT)
            self.resize(window_mode.FULL_WIDTH, window_mode.FULL_HEIGHT)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.is_personal_mode or self.is_course_mode:
            if self.width() != window_mode.FULL_WIDTH or self.height() != window_mode.FULL_HEIGHT:
                self.setFixedSize(window_mode.FULL_WIDTH, window_mode.FULL_HEIGHT)
            return
        if self.is_mini_mode:
            if self.width() != window_mode.MINI_WIDTH or self.height() != window_mode.MINI_HEIGHT:
                self.setFixedSize(window_mode.MINI_WIDTH, window_mode.MINI_HEIGHT)
        elif not self.isMaximized():
            if self.width() != window_mode.FULL_WIDTH or self.height() != window_mode.FULL_HEIGHT:
                self.resize(window_mode.FULL_WIDTH, window_mode.FULL_HEIGHT)

    def safe_exit(self):
        """工具栏 / 个人模式「安全退出」：确认后规范关闭，防止误关丢数据。"""
        if not self._confirm_quit():
            return
        self._force_close = True
        self.close()

    def _confirm_quit(self) -> bool:
        modal = QApplication.activeModalWidget()
        if isinstance(modal, QDialog) and modal.isVisible():
            QMessageBox.warning(
                self,
                "请先保存",
                "当前还有编辑窗口未关闭。\n"
                "请先在该窗口点击「保存」或「取消」，再安全退出，以免内容丢失。",
            )
            try:
                modal.raise_()
                modal.activateWindow()
            except Exception:
                pass
            return False

        reply = QMessageBox.question(
            self,
            "安全退出",
            "确定要退出班级管理系统吗？\n\n"
            "已保存到数据库的内容不会丢失。\n"
            "若还有日记等编辑窗口未点「保存」，请先取消退出并保存。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _shutdown_resources(self):
        try:
            if hasattr(self.home_widget.weather_module, "shutdown"):
                self.home_widget.weather_module.shutdown()
            else:
                self.home_widget.pause_weather_network()
        except Exception:
            pass
        try:
            if hasattr(self.mini_widget.weather_module, "shutdown"):
                self.mini_widget.weather_module.shutdown()
            else:
                self.mini_widget.weather_module.stop_network()
        except Exception:
            pass
        try:
            from database.db_conn import close_pool
            close_pool()
        except Exception:
            pass

    def closeEvent(self, event):
        if not self._force_close:
            if not self._confirm_quit():
                event.ignore()
                return
            self._force_close = True
        try:
            self.course_widget.flush()
        except Exception:
            pass
        self._shutdown_resources()
        super().closeEvent(event)

    def _goto_log_day(self, date_str):
        if self.is_mini_mode:
            self.switch_to_full_mode()
        self.tabs.setCurrentIndex(self.TAB_LOG)
        self.log_widget.open_day(date_str)
        self.statusBar().showMessage(f"已打开 {date_str} 班级日志", 3000)

    def _goto_todo(self):
        if self.is_mini_mode:
            self.switch_to_full_mode()
        self.tabs.setCurrentIndex(self.TAB_TODO)
        self.todo_widget.refresh_table()
        self.statusBar().showMessage("已切换到待办事项", 3000)

    def _on_tab_changed(self, index: int):
        """切页时复位滚动，避免日志页叠层/残影带到其它页。"""
        if index == self.TAB_LOG and hasattr(self.log_widget, "reset_scroll"):
            self.log_widget.reset_scroll()
        elif index == self.TAB_HOME and hasattr(self.home_widget, "reset_scroll"):
            self.home_widget.reset_scroll()
