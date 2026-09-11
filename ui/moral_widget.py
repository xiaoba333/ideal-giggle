# -*- coding: utf-8 -*-
"""德育分统计页：总分榜 + 明细弹窗 + 初始分设置 + Excel 同步。"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QDialog,
    QFrame, QFileDialog, QFormLayout,
)

from service import moral_service, student_service
from utils.date_util import format_datetime
from ui.styles import set_secondary_button
from ui.components.table_style import wrap_table_panel
from ui.components.text_label_util import configure_wrap_label


class MoralDetailDialog(QDialog):
    """单名学生德育明细。"""

    COLUMNS = ["发生时间", "加减分", "日志事由", "日志类型"]

    def __init__(self, parent=None, student=None, records=None):
        super().__init__(parent)
        self.student = student or {}
        self.records = records or []
        name = self.student.get("name") or ""
        no = self.student.get("student_no") or ""
        total = self.student.get("total_score")
        self.setWindowTitle(f"德育明细 · {name}（{no}）")
        self.setModal(True)
        self.resize(640, 420)
        self.setMinimumSize(520, 320)
        self._build_ui(total)
        self._fill()

    def _build_ui(self, total):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        card = QFrame()
        card.setObjectName("logFormSection")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        tip = QLabel(
            f"当前总分：{total if total is not None else '—'}　"
            f"（初始 {self.student.get('moral_base', '—')} "
            f"+ 加分 {self.student.get('add_sum', 0)} "
            f"− 扣分 {self.student.get('deduct_sum', 0)}）"
        )
        tip.setObjectName("hintLabel")
        configure_wrap_label(tip)
        tip.setMaximumWidth(640)
        card_lay.addWidget(tip)
        root.addWidget(card)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        root.addWidget(wrap_table_panel(self.table), 1)

        btn = QPushButton("关闭")
        set_secondary_button(btn)
        btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn)
        root.addLayout(row)

    def _fill(self):
        self.table.setRowCount(0)
        for row in self.records:
            r = self.table.rowCount()
            self.table.insertRow(r)
            values = [
                format_datetime(row.get("change_time")),
                row.get("score_display") or str(row.get("score_change") or ""),
                row.get("reason_display") or "—",
                row.get("log_type_display") or "—",
            ]
            for c, text in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(text))
        if not self.records:
            self.table.setRowCount(1)
            empty = QTableWidgetItem("暂无加减分记录")
            empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(0, 0, empty)
            self.table.setSpan(0, 0, 1, len(self.COLUMNS))


class MoralBaseDialog(QDialog):
    """设置全体默认初始德育分。"""

    def __init__(self, parent=None, current=100):
        super().__init__(parent)
        self.apply_to_all = False
        self.setWindowTitle("设置默认初始德育分")
        self.setModal(True)
        self.resize(380, 180)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        self.edit = QLineEdit(str(int(current)))
        self.edit.setValidator(QIntValidator(0, 9999, self))
        form.addRow("默认初始分", self.edit)
        lay.addLayout(form)
        tip = QLabel("勾选「同步全体学生」会把每位学生的初始分一并改为该值。")
        tip.setObjectName("hintLabel")
        configure_wrap_label(tip)
        tip.setMaximumWidth(340)
        lay.addWidget(tip)

        from PyQt6.QtWidgets import QCheckBox
        self.chk_all = QCheckBox("同步更新全体学生的初始德育分")
        lay.addWidget(self.chk_all)

        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("取消")
        set_secondary_button(cancel)
        ok = QPushButton("保存")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self._ok)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)

    def _ok(self):
        text = self.edit.text().strip()
        if not text:
            QMessageBox.information(self, "提示", "请填写初始分")
            return
        self.apply_to_all = self.chk_all.isChecked()
        self.accept()

    def value(self):
        return int(self.edit.text().strip())


class MoralStatsWidget(QWidget):
    """德育分统计主面板。"""

    COLUMNS = ["学号", "姓名", "当前总分", "班级"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("moralStatsRoot")
        self._order = "student_no"  # or score_desc
        self._rows = []
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        title = QLabel("德育分统计")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        tip = QLabel(
            "总分 = 初始基础分 + 全部加分 − 全部扣分；双击学生查看历史明细。"
        )
        tip.setObjectName("hintLabel")
        configure_wrap_label(tip)
        tip.setMaximumWidth(1100)
        root.addWidget(tip)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 2, 0, 2)
        bar.setSpacing(10)
        self.lbl_base = QLabel()
        self.lbl_base.setObjectName("hintLabel")
        configure_wrap_label(self.lbl_base)
        bar.addWidget(self.lbl_base, 1)

        self.btn_sort_no = QPushButton("按学号升序")
        set_secondary_button(self.btn_sort_no)
        self.btn_sort_score = QPushButton("按分数从高到低")
        set_secondary_button(self.btn_sort_score)
        self.btn_sort_no.clicked.connect(lambda: self._set_order("student_no"))
        self.btn_sort_score.clicked.connect(lambda: self._set_order("score_desc"))
        bar.addWidget(self.btn_sort_no)
        bar.addWidget(self.btn_sort_score)

        btn_base = QPushButton("设置初始分")
        set_secondary_button(btn_base)
        btn_base.clicked.connect(self._on_set_base)
        bar.addWidget(btn_base)

        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh_table)
        bar.addWidget(btn_refresh)

        btn_export = QPushButton("导出 Excel")
        set_secondary_button(btn_export)
        btn_export.clicked.connect(self._on_export)
        bar.addWidget(btn_export)

        btn_import = QPushButton("导入 Excel")
        set_secondary_button(btn_import)
        btn_import.clicked.connect(self._on_import)
        bar.addWidget(btn_import)
        root.addLayout(bar)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        root.addWidget(wrap_table_panel(self.table), 1)

        self._sync_sort_buttons()

    def _sync_sort_buttons(self):
        self.btn_sort_no.setEnabled(self._order != "student_no")
        self.btn_sort_score.setEnabled(self._order != "score_desc")

    def _set_order(self, order):
        self._order = order
        self._sync_sort_buttons()
        self.refresh_table()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_table()

    def refresh_table(self):
        try:
            base = moral_service.get_moral_base_default()
            self.lbl_base.setText(f"全体默认初始德育分：{base}")
            self._rows = moral_service.list_scoreboard(order_by=self._order)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载德育统计失败：\n{e}")
            return

        self.table.setRowCount(0)
        for row in self._rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            values = [
                row.get("student_no") or "",
                row.get("name") or "",
                str(row.get("total_score") if row.get("total_score") is not None else ""),
                row.get("class_display") or "",
            ]
            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row.get("id"))
                if c == 2:
                    item.setTextAlignment(
                        int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    )
                self.table.setItem(r, c, item)

    def _row_student(self, row_idx: int):
        item = self.table.item(row_idx, 0)
        if not item:
            return None
        sid = item.data(Qt.ItemDataRole.UserRole)
        for row in self._rows:
            if row.get("id") == sid:
                return row
        return None

    def _on_double_click(self, row: int, _column: int):
        student = self._row_student(row)
        if not student:
            return
        try:
            records = moral_service.list_student_history(student.get("id"))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载明细失败：\n{e}")
            return
        dlg = MoralDetailDialog(self, student=student, records=records)
        dlg.exec()

    def _on_set_base(self):
        current = moral_service.get_moral_base_default()
        dlg = MoralBaseDialog(self, current=current)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            moral_service.set_moral_base_default(
                dlg.value(), apply_to_all=dlg.apply_to_all
            )
            QMessageBox.information(self, "成功", "默认初始德育分已保存")
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出学生 Excel", "学生信息_德育.xlsx", "Excel 文件 (*.xlsx)"
        )
        if not path:
            return
        try:
            n = student_service.export_excel(path)
            QMessageBox.information(self, "成功", f"已导出 {n} 名学生（含班级与初始德育分）")
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入学生 Excel", "", "Excel 文件 (*.xlsx *.xls)"
        )
        if not path:
            return
        try:
            ok, skip, updated, errors = student_service.import_excel(
                path, skip_duplicate=True, update_existing=True
            )
            msg = f"新增 {ok}，更新 {updated}，跳过 {skip}"
            if errors:
                msg += f"\n部分失败 {len(errors)} 条：\n" + "\n".join(errors[:8])
            QMessageBox.information(self, "导入完成", msg)
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
