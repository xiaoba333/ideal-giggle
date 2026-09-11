# -*- coding: utf-8 -*-
"""待办事项管理面板（个人 / 班级分表展示）。"""

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QComboBox, QDateEdit,
    QCheckBox, QHeaderView, QFrame,
)

from service import todo_service
from service.todo_service import SCOPE_PERSONAL, SCOPE_CLASS
from utils.date_util import format_date, format_datetime
from ui.styles import (
    QCOLOR_PRIMARY, QCOLOR_DANGER, QCOLOR_DANGER_BG,
    set_secondary_button, set_danger_button,
)
from ui.components.table_style import wrap_table_panel
from ui.components.text_label_util import configure_wrap_label

# 已完成行文字色（绿色）
QCOLOR_DONE = QColor("#2e7d4f")

# 列索引
COL_CHECK = 0
COL_ID = 1
COL_TITLE = 2
COL_CONTENT = 3
COL_DEADLINE = 4
COL_URGENCY = 5
COL_STATUS = 6
COL_COMPLETE = 7
COL_CREATE = 8


class TodoFormDialog(QDialog):
    """新增 / 编辑待办对话框；编辑时可直接删除。"""

    def __init__(self, parent=None, todo=None, default_deadline=None,
                 default_scope=SCOPE_PERSONAL):
        super().__init__(parent)
        self.todo = todo
        self.deleted = False
        self._default_scope = int(default_scope) if default_scope is not None else SCOPE_PERSONAL
        self.setWindowTitle("编辑待办" if todo else "新增待办")
        self.resize(420, 400)
        self._build_ui()
        if todo:
            self._fill_form(todo)
        else:
            idx = self.combo_scope.findData(self._default_scope)
            self.combo_scope.setCurrentIndex(idx if idx >= 0 else 0)
            if default_deadline:
                qd = QDate.fromString(format_date(default_deadline), "yyyy-MM-dd")
                if qd.isValid():
                    self.date_deadline.setDate(qd)
                    self.chk_no_deadline.setChecked(False)
                    self.date_deadline.setEnabled(True)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self.edit_title = QLineEdit()
        self.edit_content = QTextEdit()
        self.edit_content.setMaximumHeight(100)
        self.date_deadline = QDateEdit()
        self.date_deadline.setCalendarPopup(True)
        self.date_deadline.setDisplayFormat("yyyy-MM-dd")
        self.date_deadline.setDate(QDate.currentDate())
        self.chk_no_deadline = QCheckBox("无截止日期")
        self.chk_no_deadline.toggled.connect(
            lambda checked: self.date_deadline.setEnabled(not checked)
        )
        self.combo_scope = QComboBox()
        self.combo_scope.addItem("个人", SCOPE_PERSONAL)
        self.combo_scope.addItem("班级", SCOPE_CLASS)
        self.combo_urgency = QComboBox()
        self.combo_urgency.addItem("普通", 0)
        self.combo_urgency.addItem("紧急", 1)
        self.combo_status = QComboBox()
        self.combo_status.addItem("未完成", 0)
        self.combo_status.addItem("已完成", 1)
        self.lbl_complete = QLabel("—")
        self.lbl_complete.setObjectName("hintLabel")

        form.addRow("标题 *", self.edit_title)
        form.addRow("详情", self.edit_content)
        form.addRow("分类", self.combo_scope)
        form.addRow("截止日期", self.date_deadline)
        form.addRow("", self.chk_no_deadline)
        form.addRow("紧急度", self.combo_urgency)
        form.addRow("状态", self.combo_status)
        form.addRow("完成日期", self.lbl_complete)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        if self.todo:
            btn_del = QPushButton("删除")
            set_danger_button(btn_del)
            btn_del.clicked.connect(self._on_delete)
            btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        set_secondary_button(btn_cancel)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("保存" if self.todo else "新增")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _fill_form(self, todo):
        self.edit_title.setText(todo.get("title") or "")
        self.edit_content.setPlainText(todo.get("content") or "")
        scope = todo.get("scope") if todo.get("scope") is not None else SCOPE_PERSONAL
        idx_s = self.combo_scope.findData(int(scope))
        self.combo_scope.setCurrentIndex(idx_s if idx_s >= 0 else 0)
        deadline = format_date(todo.get("deadline"))
        if deadline:
            qd = QDate.fromString(deadline, "yyyy-MM-dd")
            if qd.isValid():
                self.date_deadline.setDate(qd)
            self.chk_no_deadline.setChecked(False)
        else:
            self.chk_no_deadline.setChecked(True)
        urgency = todo.get("urgency") if todo.get("urgency") is not None else 0
        idx_u = self.combo_urgency.findData(int(urgency))
        self.combo_urgency.setCurrentIndex(idx_u if idx_u >= 0 else 0)
        status = todo.get("status") if todo.get("status") is not None else 0
        idx = self.combo_status.findData(int(status))
        self.combo_status.setCurrentIndex(idx if idx >= 0 else 0)
        done = format_date(todo.get("complete_date"))
        self.lbl_complete.setText(done or "—")

    def _on_delete(self):
        reply = QMessageBox.question(
            self, "确认删除", "确定删除该待办吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.deleted = True
        self.accept()

    def get_data(self):
        deadline = None
        if not self.chk_no_deadline.isChecked():
            deadline = self.date_deadline.date().toString("yyyy-MM-dd")
        return {
            "title": self.edit_title.text().strip(),
            "content": self.edit_content.toPlainText().strip() or None,
            "deadline": deadline,
            "status": self.combo_status.currentData(),
            "urgency": self.combo_urgency.currentData(),
            "scope": self.combo_scope.currentData(),
        }

    def is_changed(self):
        """编辑模式下表单是否相对原记录有改动；新增始终视为有改动。"""
        if not self.todo:
            return True
        data = self.get_data()
        old_title = (self.todo.get("title") or "").strip()
        old_content = (self.todo.get("content") or "").strip() or None
        old_deadline = format_date(self.todo.get("deadline")) or None
        old_status = int(self.todo.get("status") if self.todo.get("status") is not None else 0)
        old_urgency = int(self.todo.get("urgency") if self.todo.get("urgency") is not None else 0)
        old_scope = int(self.todo.get("scope") if self.todo.get("scope") is not None else SCOPE_PERSONAL)
        return (
            data["title"] != old_title
            or data["content"] != old_content
            or data["deadline"] != old_deadline
            or int(data["status"]) != old_status
            or int(data["urgency"]) != old_urgency
            or int(data["scope"]) != old_scope
        )


class TodoWidget(QWidget):
    """待办事项主面板：个人 / 班级两个表格。"""

    COLUMNS = [
        "", "ID", "标题", "详情", "截止日期", "紧急度", "状态", "完成日期", "创建时间",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_busy = False
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        filter_bar = QHBoxLayout()
        filter_bar.setContentsMargins(0, 2, 0, 2)
        filter_bar.setSpacing(10)
        filter_bar.addWidget(QLabel("状态："))
        self.combo_status = QComboBox()
        self.combo_status.addItem("全部", None)
        self.combo_status.addItem("未完成", 0)
        self.combo_status.addItem("已完成", 1)
        filter_bar.addWidget(self.combo_status)

        filter_bar.addWidget(QLabel("紧急度："))
        self.combo_urgency = QComboBox()
        self.combo_urgency.addItem("全部", None)
        self.combo_urgency.addItem("普通", 0)
        self.combo_urgency.addItem("紧急", 1)
        filter_bar.addWidget(self.combo_urgency)

        filter_bar.addWidget(QLabel("截止日期从："))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.chk_start = QCheckBox("启用")
        filter_bar.addWidget(self.date_start)
        filter_bar.addWidget(self.chk_start)

        filter_bar.addWidget(QLabel("到："))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setDate(QDate.currentDate().addMonths(1))
        self.chk_end = QCheckBox("启用")
        filter_bar.addWidget(self.date_end)
        filter_bar.addWidget(self.chk_end)

        btn_filter = QPushButton("筛选")
        btn_filter.setMinimumSize(80, 32)
        btn_filter.clicked.connect(self.refresh_table)
        filter_bar.addWidget(btn_filter)
        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        tip = QLabel(
            "左侧勾选即可标记完成；点击其它列可编辑或删除；"
            "紧急=红色　普通=蓝色　已完成=绿色"
        )
        tip.setObjectName("hintLabel")
        configure_wrap_label(tip)
        tip.setMaximumWidth(1100)
        layout.addWidget(tip)

        self.table_personal = self._make_table()
        self.table_class = self._make_table()
        layout.addWidget(
            self._make_section("个人待办", self.table_personal, SCOPE_PERSONAL), 1
        )
        layout.addWidget(
            self._make_section("班级待办", self.table_class, SCOPE_CLASS), 1
        )

    def _make_table(self):
        table = QTableWidget(0, len(self.COLUMNS))
        table.setHorizontalHeaderLabels(self.COLUMNS)
        table.setCursor(Qt.CursorShape.PointingHandCursor)
        table.cellClicked.connect(self._on_row_clicked)
        table.itemChanged.connect(self._on_check_changed)
        header = table.horizontalHeader()
        header.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(COL_CHECK, 44)
        table.setMinimumHeight(180)
        return table

    def _make_section(self, title, table, scope):
        frame = QFrame()
        frame.setObjectName("todoScopeSection")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        lbl = QLabel(title)
        lbl.setObjectName("pageTitle")
        head.addWidget(lbl)
        head.addStretch()
        btn_add = QPushButton("新增待办")
        btn_add.clicked.connect(lambda _=False, s=scope: self._on_add(s))
        head.addWidget(btn_add)
        lay.addLayout(head)
        lay.addWidget(wrap_table_panel(table), 1)
        return frame

    def _filter_kwargs(self):
        status = self.combo_status.currentData()
        urgency = self.combo_urgency.currentData()
        start = (
            self.date_start.date().toString("yyyy-MM-dd")
            if self.chk_start.isChecked() else None
        )
        end = (
            self.date_end.date().toString("yyyy-MM-dd")
            if self.chk_end.isChecked() else None
        )
        return dict(status=status, urgency=urgency, start_date=start, end_date=end)

    def refresh_table(self):
        kwargs = self._filter_kwargs()
        try:
            personal = todo_service.list_todos(scope=SCOPE_PERSONAL, **kwargs)
            class_rows = todo_service.list_todos(scope=SCOPE_CLASS, **kwargs)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询待办失败：\n{e}")
            return
        self._fill_table(self.table_personal, personal)
        self._fill_table(self.table_class, class_rows)

    def _fill_table(self, table, rows):
        self._check_busy = True
        table.blockSignals(True)
        try:
            table.setRowCount(0)
            for row in rows:
                r = table.rowCount()
                table.insertRow(r)
                urgency_val = int(row.get("urgency") or 0)
                status_val = int(row.get("status") or 0)
                overdue = todo_service.is_overdue(row)
                todo_id = row.get("id")

                chk = QTableWidgetItem()
                chk.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsSelectable
                )
                chk.setCheckState(
                    Qt.CheckState.Checked if status_val == 1 else Qt.CheckState.Unchecked
                )
                chk.setData(Qt.ItemDataRole.UserRole, todo_id)
                chk.setData(Qt.ItemDataRole.UserRole + 1, status_val)
                chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(r, COL_CHECK, chk)

                values = {
                    COL_ID: str(todo_id or ""),
                    COL_TITLE: row.get("title") or "",
                    COL_CONTENT: row.get("content") or "",
                    COL_DEADLINE: format_date(row.get("deadline")),
                    COL_URGENCY: todo_service.urgency_display(urgency_val),
                    COL_STATUS: todo_service.status_display(row),
                    COL_COMPLETE: format_date(row.get("complete_date")) or "—",
                    COL_CREATE: format_datetime(row.get("create_time")),
                }
                if status_val == 1:
                    fg = QCOLOR_DONE
                elif urgency_val == 1:
                    fg = QCOLOR_DANGER
                else:
                    fg = QCOLOR_PRIMARY
                brush = QBrush(fg)
                for c, text in values.items():
                    item = QTableWidgetItem(text)
                    item.setData(Qt.ItemDataRole.ForegroundRole, brush)
                    item.setForeground(brush)
                    if overdue and status_val == 0:
                        item.setBackground(QBrush(QCOLOR_DANGER_BG))
                    if c == COL_STATUS and overdue and status_val == 0:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    table.setItem(r, c, item)
        finally:
            table.blockSignals(False)
            self._check_busy = False

    def _on_check_changed(self, item: QTableWidgetItem):
        if self._check_busy or item is None or item.column() != COL_CHECK:
            return
        table = item.tableWidget()
        todo_id = item.data(Qt.ItemDataRole.UserRole)
        if todo_id is None:
            return
        new_status = 1 if item.checkState() == Qt.CheckState.Checked else 0
        old_status = int(item.data(Qt.ItemDataRole.UserRole + 1) or 0)
        if new_status == old_status:
            return
        try:
            todo_service.change_status(todo_id, new_status)
        except Exception as e:
            self._check_busy = True
            if table is not None:
                table.blockSignals(True)
            item.setCheckState(
                Qt.CheckState.Checked if old_status == 1 else Qt.CheckState.Unchecked
            )
            if table is not None:
                table.blockSignals(False)
            self._check_busy = False
            QMessageBox.warning(self, "失败", str(e))
            return
        self.refresh_table()

    def _on_row_clicked(self, row, column):
        if column == COL_CHECK:
            return
        table = self.sender()
        if not isinstance(table, QTableWidget):
            return
        item = table.item(row, COL_CHECK)
        if item is None:
            return
        todo_id = item.data(Qt.ItemDataRole.UserRole)
        if todo_id is not None:
            self._open_edit(todo_id)

    def _on_add(self, scope=SCOPE_PERSONAL):
        dialog = TodoFormDialog(self, default_scope=scope)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        try:
            todo_service.add_todo(**data)
            QMessageBox.information(self, "成功", "待办已新增")
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _open_edit(self, todo_id):
        try:
            todo = todo_service.get_todo(todo_id)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取待办失败：\n{e}")
            return
        if not todo:
            QMessageBox.warning(self, "提示", "该待办不存在")
            return

        dialog = TodoFormDialog(self, todo)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.deleted:
            try:
                todo_service.remove_todo(todo_id)
                QMessageBox.information(self, "成功", "已删除")
                self.refresh_table()
            except Exception as e:
                QMessageBox.warning(self, "失败", str(e))
            return

        if not dialog.is_changed():
            return
        data = dialog.get_data()
        try:
            todo_service.edit_todo(todo_id, **data)
            QMessageBox.information(self, "成功", "待办已更新")
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
