# -*- coding: utf-8 -*-
"""学生信息管理面板：点击行编辑/删除，底部仅保留新增。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog,
)

from service import student_service
from ui.styles import set_secondary_button, set_danger_button
from ui.components.table_style import wrap_table_panel
from ui.components.text_label_util import configure_wrap_label


class StudentFormDialog(QDialog):
    """新增 / 编辑学生对话框；编辑时可直接删除。"""

    def __init__(self, parent=None, student=None):
        super().__init__(parent)
        self.student = student
        self.deleted = False
        self.setWindowTitle("编辑学生" if student else "新增学生")
        self.resize(420, 340)
        self._build_ui()
        if student:
            self._fill_form(student)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.edit_student_no = QLineEdit()
        self.edit_name = QLineEdit()
        self.combo_gender = QComboBox()
        self.combo_gender.addItems(["", "男", "女"])
        self.edit_phone = QLineEdit()

        form.addRow("学号 *", self.edit_student_no)
        form.addRow("姓名 *", self.edit_name)
        form.addRow("性别", self.combo_gender)
        form.addRow("联系电话", self.edit_phone)
        self.edit_class = QLineEdit()
        self.edit_class.setPlaceholderText("可空，默认使用班级设置")
        self.edit_moral_base = QLineEdit()
        self.edit_moral_base.setPlaceholderText("可空，默认全体初始分")
        from PyQt6.QtGui import QIntValidator
        self.edit_moral_base.setValidator(QIntValidator(0, 9999, self))
        form.addRow("班级", self.edit_class)
        form.addRow("初始德育分", self.edit_moral_base)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        if self.student:
            btn_del = QPushButton("删除")
            set_danger_button(btn_del)
            btn_del.clicked.connect(self._on_delete)
            btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        set_secondary_button(btn_cancel)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("保存" if self.student else "新增")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _fill_form(self, student):
        self.edit_student_no.setText(student.get("student_no") or "")
        self.edit_name.setText(student.get("name") or "")
        gender = student.get("gender") or ""
        idx = self.combo_gender.findText(gender)
        self.combo_gender.setCurrentIndex(idx if idx >= 0 else 0)
        self.edit_phone.setText(student.get("phone") or "")
        self.edit_class.setText(student.get("class_name") or "")
        if student.get("moral_base") is not None:
            self.edit_moral_base.setText(str(int(student.get("moral_base"))))
        else:
            self.edit_moral_base.clear()

    def _on_delete(self):
        reply = QMessageBox.question(
            self, "确认删除", "确定删除该学生吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.deleted = True
        self.accept()

    def get_data(self):
        base_raw = self.edit_moral_base.text().strip()
        moral_base = int(base_raw) if base_raw else None
        return {
            "student_no": self.edit_student_no.text().strip(),
            "name": self.edit_name.text().strip(),
            "gender": self.combo_gender.currentText().strip() or None,
            "phone": self.edit_phone.text().strip() or None,
            "class_name": self.edit_class.text().strip() or None,
            "moral_base": moral_base,
        }


class StudentWidget(QWidget):
    """学生信息管理主面板。"""

    COLUMNS = ["ID", "学号", "姓名", "性别", "联系电话"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._opening = False
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        tip = QLabel("点击某一行即可编辑或删除该学生。")
        tip.setObjectName("hintLabel")
        configure_wrap_label(tip)
        tip.setMaximumWidth(1100)
        layout.addWidget(tip)

        # 搜索栏：Label + 输入框 + 按钮，布局托管
        search_bar = QHBoxLayout()
        search_bar.setContentsMargins(0, 2, 0, 2)
        search_bar.setSpacing(10)
        lbl_kw = QLabel("姓名/学号：")
        lbl_kw.setObjectName("fieldLabel")
        search_bar.addWidget(lbl_kw, 0)
        self.edit_keyword = QLineEdit()
        self.edit_keyword.setPlaceholderText("模糊搜索，回车或点搜索")
        self.edit_keyword.returnPressed.connect(self.refresh_table)
        search_bar.addWidget(self.edit_keyword, 1)

        btn_search = QPushButton("搜索")
        btn_search.setMinimumSize(80, 32)
        btn_search.clicked.connect(self.refresh_table)
        search_bar.addWidget(btn_search, 0)

        btn_reset = QPushButton("重置")
        btn_reset.setMinimumSize(80, 32)
        set_secondary_button(btn_reset)
        btn_reset.clicked.connect(self._on_reset)
        search_bar.addWidget(btn_reset, 0)
        layout.addLayout(search_bar)

        # 表格
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.table.cellClicked.connect(self._on_row_clicked)
        layout.addWidget(wrap_table_panel(self.table), 1)

        # 底部：新增 + Excel
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)
        btn_add = QPushButton("新增")
        btn_add.clicked.connect(self._on_add)
        btn_bar.addWidget(btn_add)
        btn_import = QPushButton("导入 Excel")
        set_secondary_button(btn_import)
        btn_import.clicked.connect(self._on_import)
        btn_bar.addWidget(btn_import)
        btn_export = QPushButton("导出 Excel")
        set_secondary_button(btn_export)
        btn_export.clicked.connect(self._on_export)
        btn_bar.addWidget(btn_export)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

    def _on_reset(self):
        self.edit_keyword.clear()
        self.refresh_table()

    def refresh_table(self):
        keyword = self.edit_keyword.text().strip()
        try:
            rows = student_service.list_students(keyword)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询学生失败：\n{e}")
            return

        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            values = [
                str(row.get("id") or ""),
                row.get("student_no") or "",
                row.get("name") or "",
                row.get("gender") or "",
                row.get("phone") or "",
            ]
            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row.get("id"))
                self.table.setItem(r, c, item)

    def _row_id(self, row: int):
        item = self.table.item(row, 0)
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_row_clicked(self, row: int, _column: int):
        if self._opening:
            return
        student_id = self._row_id(row)
        if not student_id:
            return
        self._opening = True
        try:
            self._open_edit(student_id)
        finally:
            self._opening = False

    def _on_add(self):
        dialog = StudentFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        try:
            student_service.add_student(**data)
            QMessageBox.information(self, "成功", "学生已新增")
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _open_edit(self, student_id):
        try:
            student = student_service.get_student(student_id)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取学生失败：\n{e}")
            return
        if not student:
            QMessageBox.warning(self, "提示", "该学生不存在")
            self.refresh_table()
            return

        dialog = StudentFormDialog(self, student)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.deleted:
            try:
                student_service.remove_student(student_id)
                QMessageBox.information(self, "成功", "已删除")
                self.refresh_table()
            except Exception as e:
                QMessageBox.warning(self, "失败", str(e))
            return

        data = dialog.get_data()
        try:
            student_service.edit_student(student_id, **data)
            QMessageBox.information(self, "成功", "学生已更新")
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_export(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "导出学生", "学生信息.xlsx", "Excel 文件 (*.xlsx)"
        )
        if not path:
            return
        try:
            n = student_service.export_excel(path, self.edit_keyword.text().strip() or None)
            QMessageBox.information(self, "成功", f"已导出 {n} 名学生")
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_import(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "导入学生", "", "Excel 文件 (*.xlsx *.xls)"
        )
        if not path:
            return
        try:
            ok, skip, updated, errors = student_service.import_excel(
                path, skip_duplicate=True, update_existing=True
            )
            msg = f"新增 {ok}，更新 {updated}，跳过 {skip}"
            if errors:
                msg += f"\n失败 {len(errors)} 条"
            QMessageBox.information(self, "导入完成", msg)
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
