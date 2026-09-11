# -*- coding: utf-8 -*-
"""班级日志管理面板：自定义日历 + 下方当日日志列表联动。"""

from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QDateEdit, QFileDialog,
    QFrame, QRadioButton, QButtonGroup, QCheckBox,
    QScrollArea, QSizePolicy, QAbstractScrollArea,
)

from dao.classlog_dao import LOG_TYPES
from service import classlog_service, student_service
from utils.date_util import format_date, format_datetime, today_str
from utils.log_image_util import (
    validate_image_file, load_pixmap_limited,
    normalize_image_path, image_file_exists,
)
from ui.styles import set_danger_button, set_secondary_button
from ui.components.log_calendar import LogCalendarWidget
from ui.components.table_style import wrap_table_panel
from ui.components.text_label_util import configure_wrap_label


class _LogDatesWorker(QThread):
    """子线程查询某月有日志的日期，避免阻塞翻页动画。"""

    finished_ok = pyqtSignal(int, int, list)  # year, month, date_str list
    failed = pyqtSignal(str)

    def __init__(self, year: int, month: int, token: int, parent=None):
        super().__init__(parent)
        self.year = year
        self.month = month
        self.token = token

    def run(self):
        try:
            start = QDate(self.year, self.month, 1).addDays(-7)
            end = QDate(self.year, self.month, 1)
            end = QDate(self.year, self.month, end.daysInMonth()).addDays(14)
            dates = classlog_service.list_log_dates(
                start.toString("yyyy-MM-dd"),
                end.toString("yyyy-MM-dd"),
            )
            self.finished_ok.emit(self.year, self.month, dates)
        except Exception as e:
            self.failed.emit(str(e))


class _DayLogsWorker(QThread):
    """子线程查询某日日志列表。"""

    finished_ok = pyqtSignal(str, list)  # date_str, rows
    failed = pyqtSignal(str)

    def __init__(self, date_str: str, token: int, parent=None):
        super().__init__(parent)
        self.date_str = date_str
        self.token = token

    def run(self):
        try:
            rows = classlog_service.list_by_date(self.date_str)
            self.finished_ok.emit(self.date_str, rows)
        except Exception as e:
            self.failed.emit(str(e))


class LogFormDialog(QDialog):
    """新增 / 编辑日志：类型、参与学生、正文、日期、德育分。"""

    def __init__(self, parent=None, log=None, default_date=None, lock_date=False):
        super().__init__(parent)
        self.log = log
        self.lock_date = lock_date
        self.deleted = False
        self._student_checks = []  # list[(checkbox, student_dict)]
        self._add_checks = []      # 加分名单
        self._deduct_checks = []   # 扣分名单
        self._stored_image_path = ""
        self._pending_image_abs = None
        self._image_cleared = False
        self.setObjectName("logFormDialog")
        self.setWindowTitle("编辑日志" if log else "新增日志")
        self.setModal(True)
        self.resize(540, 800)
        self.setMinimumSize(480, 560)
        self._build_ui(default_date)
        self._load_students()
        if log:
            self._fill_form(log)
        else:
            self._refresh_image_preview()

    def _section(self, title: str):
        box = QFrame()
        box.setObjectName("logFormSection")
        box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)
        head = QLabel(title)
        head.setObjectName("logFormSectionTitle")
        lay.addWidget(head)
        return box, lay

    def _build_ui(self, default_date):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)

        # —— 日期 ——
        date_box, date_lay = self._section("填写日期")
        self.date_log = QDateEdit()
        self.date_log.setCalendarPopup(True)
        self.date_log.setDisplayFormat("yyyy-MM-dd")
        if default_date:
            qd = QDate.fromString(format_date(default_date), "yyyy-MM-dd")
            self.date_log.setDate(qd if qd.isValid() else QDate.currentDate())
        else:
            self.date_log.setDate(QDate.currentDate())
        if self.lock_date:
            self.date_log.setEnabled(False)
        date_lay.addWidget(self.date_log)
        root.addWidget(date_box)

        # —— 日志类型 ——
        type_box, type_lay = self._section("日志类型（必选）")
        type_row = QHBoxLayout()
        type_row.setSpacing(14)
        self.type_group = QButtonGroup(self)
        self.type_group.setExclusive(True)
        self._type_radios = {}
        for i, name in enumerate(LOG_TYPES):
            radio = QRadioButton(name)
            radio.setObjectName("logTypeRadio")
            self.type_group.addButton(radio, i)
            self._type_radios[name] = radio
            radio.toggled.connect(self._on_type_toggled)
            type_row.addWidget(radio)
        type_row.addStretch()
        type_lay.addLayout(type_row)

        self.remark_wrap = QWidget()
        remark_lay = QHBoxLayout(self.remark_wrap)
        remark_lay.setContentsMargins(0, 4, 0, 0)
        remark_lay.setSpacing(8)
        remark_lay.addWidget(QLabel("备注 *"))
        self.edit_type_remark = QLineEdit()
        self.edit_type_remark.setPlaceholderText("请填写「其他」类型的具体说明")
        self.edit_type_remark.setMaxLength(100)
        remark_lay.addWidget(self.edit_type_remark, 1)
        self.remark_wrap.setVisible(False)
        type_lay.addWidget(self.remark_wrap)
        root.addWidget(type_box)

        # —— 参与学生 ——
        stu_box, stu_lay = self._section("参与学生")
        tool = QHBoxLayout()
        tool.setSpacing(8)
        self.lbl_stu_hint = QLabel("加载中…")
        self.lbl_stu_hint.setObjectName("hintLabel")
        configure_wrap_label(self.lbl_stu_hint)
        tool.addWidget(self.lbl_stu_hint, 1)
        btn_all = QPushButton("全选")
        set_secondary_button(btn_all)
        btn_none = QPushButton("取消全选")
        set_secondary_button(btn_none)
        btn_all.clicked.connect(self._select_all_students)
        btn_none.clicked.connect(self._clear_all_students)
        tool.addWidget(btn_all)
        tool.addWidget(btn_none)
        stu_lay.addLayout(tool)

        self.student_scroll = QScrollArea()
        self.student_scroll.setObjectName("logStudentScroll")
        self.student_scroll.setWidgetResizable(True)
        self.student_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.student_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.student_scroll.setMinimumHeight(140)
        self.student_host = QWidget()
        self.student_host.setObjectName("logStudentHost")
        self.student_list_lay = QVBoxLayout(self.student_host)
        self.student_list_lay.setContentsMargins(6, 4, 6, 4)
        self.student_list_lay.setSpacing(4)
        self.student_list_lay.addStretch()
        self.student_scroll.setWidget(self.student_host)
        stu_lay.addWidget(self.student_scroll)
        root.addWidget(stu_box)

        # —— 日志内容 ——
        content_box, content_lay = self._section("日志内容")
        self.edit_content = QTextEdit()
        self.edit_content.setPlaceholderText(
            "填写本次活动 / 会议记录正文…（德育事由将复用此内容）"
        )
        self.edit_content.setMinimumHeight(90)
        content_lay.addWidget(self.edit_content)
        root.addWidget(content_box)

        # —— 图片附件 ——
        img_box, img_lay = self._section("图片附件（可选）")
        img_tool = QHBoxLayout()
        img_tool.setSpacing(8)
        self.btn_pick_image = QPushButton("选择图片")
        set_secondary_button(self.btn_pick_image)
        self.btn_pick_image.clicked.connect(self._on_pick_image)
        img_tool.addWidget(self.btn_pick_image)
        self.btn_remove_image = QPushButton("移除图片")
        set_danger_button(self.btn_remove_image)
        self.btn_remove_image.clicked.connect(self._on_remove_image)
        img_tool.addWidget(self.btn_remove_image)
        self.lbl_image_hint = QLabel("支持 png / jpg / jpeg，单张不超过 5MB")
        self.lbl_image_hint.setObjectName("hintLabel")
        configure_wrap_label(self.lbl_image_hint)
        img_tool.addWidget(self.lbl_image_hint, 1)
        img_lay.addLayout(img_tool)

        self.lbl_image_preview = QLabel()
        self.lbl_image_preview.setObjectName("logImagePreview")
        self.lbl_image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image_preview.setMinimumHeight(120)
        self.lbl_image_preview.setMaximumHeight(160)
        self.lbl_image_preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.lbl_image_preview.setText("未选择图片")
        img_lay.addWidget(self.lbl_image_preview)
        root.addWidget(img_box)

        # —— 德育分（可同时加分 + 扣分；均需手动勾选学生） ——
        moral_box, moral_lay = self._section("德育分（可选，可同时加分与扣分）")
        tip = QLabel("加分/扣分互不排斥；不会按「参与学生」自动加分，须分别勾选名单。")
        tip.setObjectName("hintLabel")
        configure_wrap_label(tip)
        tip.setMaximumWidth(720)
        moral_lay.addWidget(tip)

        # 加分区
        add_head = QHBoxLayout()
        add_head.setSpacing(8)
        add_head.addWidget(QLabel("加分分数"))
        self.edit_add_score = QLineEdit()
        self.edit_add_score.setPlaceholderText("正整数，如 2；不填则不加分")
        self.edit_add_score.setValidator(QIntValidator(1, 9999, self))
        self.edit_add_score.setMaximumWidth(120)
        add_head.addWidget(self.edit_add_score)
        add_head.addStretch(1)
        btn_a_all = QPushButton("全选")
        set_secondary_button(btn_a_all)
        btn_a_none = QPushButton("取消全选")
        set_secondary_button(btn_a_none)
        btn_a_all.clicked.connect(self._select_all_add)
        btn_a_none.clicked.connect(self._clear_all_add)
        add_head.addWidget(btn_a_all)
        add_head.addWidget(btn_a_none)
        moral_lay.addLayout(add_head)

        self.lbl_add_hint = QLabel("勾选需要加分的学生")
        self.lbl_add_hint.setObjectName("hintLabel")
        configure_wrap_label(self.lbl_add_hint)
        moral_lay.addWidget(self.lbl_add_hint)

        self.add_scroll = QScrollArea()
        self.add_scroll.setObjectName("logStudentScroll")
        self.add_scroll.setWidgetResizable(True)
        self.add_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.add_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.add_scroll.setMinimumHeight(100)
        self.add_host = QWidget()
        self.add_list_lay = QVBoxLayout(self.add_host)
        self.add_list_lay.setContentsMargins(6, 4, 6, 4)
        self.add_list_lay.setSpacing(4)
        self.add_list_lay.addStretch()
        self.add_scroll.setWidget(self.add_host)
        moral_lay.addWidget(self.add_scroll)

        # 扣分区
        deduct_head = QHBoxLayout()
        deduct_head.setSpacing(8)
        deduct_head.addWidget(QLabel("扣分分数"))
        self.edit_deduct_score = QLineEdit()
        self.edit_deduct_score.setPlaceholderText("正整数，如 1；不填则不扣分")
        self.edit_deduct_score.setValidator(QIntValidator(1, 9999, self))
        self.edit_deduct_score.setMaximumWidth(120)
        deduct_head.addWidget(self.edit_deduct_score)
        deduct_head.addStretch(1)
        btn_d_all = QPushButton("全选")
        set_secondary_button(btn_d_all)
        btn_d_none = QPushButton("取消全选")
        set_secondary_button(btn_d_none)
        btn_d_all.clicked.connect(self._select_all_deduct)
        btn_d_none.clicked.connect(self._clear_all_deduct)
        deduct_head.addWidget(btn_d_all)
        deduct_head.addWidget(btn_d_none)
        moral_lay.addLayout(deduct_head)

        self.lbl_deduct_hint = QLabel("勾选需要扣分的学生")
        self.lbl_deduct_hint.setObjectName("hintLabel")
        configure_wrap_label(self.lbl_deduct_hint)
        moral_lay.addWidget(self.lbl_deduct_hint)

        self.deduct_scroll = QScrollArea()
        self.deduct_scroll.setObjectName("logStudentScroll")
        self.deduct_scroll.setWidgetResizable(True)
        self.deduct_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.deduct_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.deduct_scroll.setMinimumHeight(100)
        self.deduct_host = QWidget()
        self.deduct_list_lay = QVBoxLayout(self.deduct_host)
        self.deduct_list_lay.setContentsMargins(6, 4, 6, 4)
        self.deduct_list_lay.setSpacing(4)
        self.deduct_list_lay.addStretch()
        self.deduct_scroll.setWidget(self.deduct_host)
        moral_lay.addWidget(self.deduct_scroll)
        root.addWidget(moral_box)

        root.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        if self.log:
            btn_del = QPushButton("删除")
            set_danger_button(btn_del)
            btn_del.clicked.connect(self._on_delete)
            btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        set_secondary_button(btn_cancel)
        btn_submit = QPushButton("保存" if self.log else "提交")
        btn_cancel.clicked.connect(self.reject)
        btn_submit.clicked.connect(self._on_submit)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_submit)
        outer.addLayout(btn_row)

    def _on_delete(self):
        reply = QMessageBox.question(
            self, "确认删除", "确定删除该日志吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.deleted = True
        self.accept()

    def _load_students(self):
        for lay in (self.student_list_lay, self.add_list_lay, self.deduct_list_lay):
            while lay.count():
                item = lay.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
        self._student_checks.clear()
        self._add_checks.clear()
        self._deduct_checks.clear()

        try:
            students = student_service.list_students()
        except Exception as e:
            self.lbl_stu_hint.setText(f"学生名单加载失败：{e}")
            self.student_list_lay.addStretch()
            self.add_list_lay.addStretch()
            self.deduct_list_lay.addStretch()
            return

        if not students:
            self.lbl_stu_hint.setText("暂无学生，请先在「学生信息」中录入")
            tip = QLabel("暂无学生数据")
            tip.setObjectName("hintLabel")
            tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.student_list_lay.addWidget(tip)
            self.student_list_lay.addStretch()
            self.add_list_lay.addStretch()
            self.deduct_list_lay.addStretch()
            return

        n = len(students)
        self.lbl_stu_hint.setText(f"共 {n} 人，可多选本次参与人员")
        self.lbl_add_hint.setText(f"共 {n} 人，勾选加分名单（与参与名单独立）")
        self.lbl_deduct_hint.setText(f"共 {n} 人，勾选扣分名单（与参与名单独立）")
        for stu in students:
            sid = stu.get("id")
            name = stu.get("name") or ""
            no = stu.get("student_no") or ""
            label = f"{name}（{no}）" if no else name

            cb = QCheckBox(label)
            cb.setObjectName("logStudentCheck")
            self.student_list_lay.addWidget(cb)
            self._student_checks.append((cb, stu))

            acb = QCheckBox(label)
            acb.setObjectName("logStudentCheck")
            self.add_list_lay.addWidget(acb)
            self._add_checks.append((acb, stu))

            dcb = QCheckBox(label)
            dcb.setObjectName("logStudentCheck")
            self.deduct_list_lay.addWidget(dcb)
            self._deduct_checks.append((dcb, stu))

        self.student_list_lay.addStretch()
        self.add_list_lay.addStretch()
        self.deduct_list_lay.addStretch()

    def _select_all_students(self):
        for cb, _ in self._student_checks:
            cb.setChecked(True)

    def _clear_all_students(self):
        for cb, _ in self._student_checks:
            cb.setChecked(False)

    def _select_all_add(self):
        for cb, _ in self._add_checks:
            cb.setChecked(True)

    def _clear_all_add(self):
        for cb, _ in self._add_checks:
            cb.setChecked(False)

    def _select_all_deduct(self):
        for cb, _ in self._deduct_checks:
            cb.setChecked(True)

    def _clear_all_deduct(self):
        for cb, _ in self._deduct_checks:
            cb.setChecked(False)

    def _selected_log_type(self):
        for name, radio in self._type_radios.items():
            if radio.isChecked():
                return name
        return None

    def _on_type_toggled(self, checked):
        if not checked:
            return
        is_other = self._selected_log_type() == "其他"
        self.remark_wrap.setVisible(is_other)
        if not is_other:
            self.edit_type_remark.clear()
        elif is_other:
            self.edit_type_remark.setFocus()

    def _selected_participants(self):
        result = []
        for cb, stu in self._student_checks:
            if cb.isChecked():
                result.append({
                    "id": stu.get("id"),
                    "name": stu.get("name") or "",
                })
        return result

    def _selected_ids(self, checks):
        ids = []
        for cb, stu in checks:
            if cb.isChecked() and stu.get("id") is not None:
                ids.append(stu.get("id"))
        return ids

    def _parse_optional_score(self, edit: QLineEdit, label: str):
        raw = edit.text().strip()
        if not raw:
            return None
        try:
            score = int(raw)
        except ValueError:
            raise ValueError(f"{label}仅支持整数")
        if score <= 0:
            raise ValueError(f"{label}须为正整数")
        return score

    def _fill_form(self, log):
        date_str = format_date(log.get("log_date")) or today_str()
        qd = QDate.fromString(date_str, "yyyy-MM-dd")
        if qd.isValid():
            self.date_log.setDate(qd)

        log_type = (log.get("log_type") or log.get("title") or "").strip()
        if log_type.startswith("其他"):
            log_type = "其他"
        radio = self._type_radios.get(log_type)
        if radio:
            radio.setChecked(True)
        remark = (log.get("type_remark") or "").strip()
        if not remark and (log.get("title") or "").startswith("其他："):
            remark = (log.get("title") or "")[3:].strip()
        self.edit_type_remark.setText(remark)
        self.remark_wrap.setVisible(log_type == "其他")

        self.edit_content.setPlainText(log.get("content") or "")

        people = log.get("participants_list") or []
        selected_ids = {p.get("id") for p in people if p.get("id") is not None}
        selected_names = {(p.get("name") or "") for p in people if p.get("name")}
        for cb, stu in self._student_checks:
            sid = stu.get("id")
            name = stu.get("name") or ""
            if selected_ids:
                cb.setChecked(sid in selected_ids)
            else:
                cb.setChecked(name in selected_names)

        add_score = log.get("moral_add_score")
        deduct_score = log.get("moral_deduct_score")
        add_ids = set(log.get("moral_add_student_ids") or [])
        deduct_ids = set(log.get("moral_deduct_student_ids") or [])
        # 兼容旧数据：仅有 moral_type / moral_score / moral_student_ids
        if add_score is None and deduct_score is None:
            try:
                mtype = int(log.get("moral_type") or 0)
            except (TypeError, ValueError):
                mtype = 0
            score = log.get("moral_score")
            old_ids = set(log.get("moral_student_ids") or [])
            if mtype == 1 and score is not None:
                add_score = abs(int(score))
                # 旧加分按参与人；编辑时尽量勾选参与人
                add_ids = selected_ids or old_ids
            elif mtype == 2 and score is not None:
                deduct_score = abs(int(score))
                deduct_ids = old_ids
            elif mtype == 3 and score is not None:
                add_score = abs(int(score))

        if add_score is not None:
            self.edit_add_score.setText(str(int(add_score)))
        else:
            self.edit_add_score.clear()
        if deduct_score is not None:
            self.edit_deduct_score.setText(str(int(deduct_score)))
        else:
            self.edit_deduct_score.clear()
        for cb, stu in self._add_checks:
            cb.setChecked(stu.get("id") in add_ids)
        for cb, stu in self._deduct_checks:
            cb.setChecked(stu.get("id") in deduct_ids)

        self._stored_image_path = normalize_image_path(log.get("image_path"))
        self._pending_image_abs = None
        self._image_cleared = False
        self._refresh_image_preview()

    def _on_pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg);;PNG (*.png);;JPEG (*.jpg *.jpeg)",
        )
        if not path:
            return
        try:
            abs_path = validate_image_file(path)
        except ValueError as e:
            QMessageBox.information(self, "提示", str(e))
            return
        self._pending_image_abs = abs_path
        self._image_cleared = False
        self._refresh_image_preview()

    def _on_remove_image(self):
        self._pending_image_abs = None
        self._image_cleared = True
        self._refresh_image_preview()

    def _refresh_image_preview(self):
        has = False
        pix = None
        if self._pending_image_abs:
            pix = load_pixmap_limited(self._pending_image_abs, max_edge=480)
            has = not pix.isNull()
        elif not self._image_cleared and self._stored_image_path:
            if image_file_exists(self._stored_image_path):
                pix = load_pixmap_limited(self._stored_image_path, max_edge=480)
                has = not pix.isNull()
            else:
                self.lbl_image_preview.clear()
                self.lbl_image_preview.setText("原图片文件已丢失")
                self.btn_remove_image.setEnabled(True)
                return
        if has and pix is not None:
            scaled = pix.scaled(
                280, 140,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_image_preview.setPixmap(scaled)
            self.lbl_image_preview.setText("")
            self.btn_remove_image.setEnabled(True)
        else:
            self.lbl_image_preview.clear()
            self.lbl_image_preview.setText("未选择图片")
            self.btn_remove_image.setEnabled(False)

    def _on_submit(self):
        log_type = self._selected_log_type()
        if not log_type:
            QMessageBox.information(self, "提示", "请选择日志类型")
            return
        if log_type == "其他" and not self.edit_type_remark.text().strip():
            QMessageBox.information(self, "提示", "选择「其他」时请填写备注")
            self.edit_type_remark.setFocus()
            return

        try:
            add_score = self._parse_optional_score(self.edit_add_score, "加分分数")
            deduct_score = self._parse_optional_score(
                self.edit_deduct_score, "扣分分数"
            )
        except ValueError as e:
            QMessageBox.information(self, "提示", str(e))
            return

        add_ids = self._selected_ids(self._add_checks)
        deduct_ids = self._selected_ids(self._deduct_checks)
        if add_score is not None and not add_ids:
            QMessageBox.information(self, "提示", "加分请勾选需要加分的学生")
            return
        if deduct_score is not None and not deduct_ids:
            QMessageBox.information(self, "提示", "扣分请勾选需要扣分的学生")
            return
        if add_ids and add_score is None:
            QMessageBox.information(self, "提示", "请填写加分分数")
            self.edit_add_score.setFocus()
            return
        if deduct_ids and deduct_score is None:
            QMessageBox.information(self, "提示", "请填写扣分分数")
            self.edit_deduct_score.setFocus()
            return
        self.accept()

    def get_data(self):
        log_type = self._selected_log_type()
        remark = self.edit_type_remark.text().strip() or None
        if log_type != "其他":
            remark = None
        add_raw = self.edit_add_score.text().strip()
        deduct_raw = self.edit_deduct_score.text().strip()
        clear_image = bool(self._image_cleared and not self._pending_image_abs)
        return {
            "log_date": self.date_log.date().toString("yyyy-MM-dd"),
            "log_type": log_type,
            "type_remark": remark,
            "title": classlog_service.format_type({
                "log_type": log_type,
                "type_remark": remark,
            }),
            "content": self.edit_content.toPlainText().strip() or None,
            "participants": self._selected_participants(),
            "moral_add_score": int(add_raw) if add_raw else None,
            "moral_add_student_ids": self._selected_ids(self._add_checks),
            "moral_deduct_score": int(deduct_raw) if deduct_raw else None,
            "moral_deduct_student_ids": self._selected_ids(self._deduct_checks),
            "image_source": self._pending_image_abs,
            "clear_image": clear_image,
        }


class LogWidget(QWidget):
    """班级日志：日历选日 + 下方列表同步刷新。"""

    DAY_COLUMNS = ["ID", "类型", "参与人员", "德育", "正文", "创建时间"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_day = today_str()
        self._marks_token = 0
        self._day_token = 0
        self._dates_worker = None
        self._day_worker = None
        self._build_ui()
        self._bind_calendar()
        self._load_marks_async(
            self.calendar.year_shown(), self.calendar.month_shown()
        )
        self._load_day_async(self.current_day)

    def _build_ui(self):
        # 本页只占 Tab 内容区，高度不随内部日历/表格撑破父级（避免叠在其它页之上）
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("logPageScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        # 关键：不按内部超高内容向父布局报告高度，否则会把整页顶出视口并叠层残影
        self.scroll.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored
        )
        vp = self.scroll.viewport()
        # 日志页内容高、可滚动：不用 OpaquePaintEvent，避免滑动时原高度残影
        vp.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        vp.setAutoFillBackground(True)

        self.inner = QWidget()
        self.inner.setObjectName("logPageScrollInner")
        self.inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.inner.setAutoFillBackground(True)
        root = QVBoxLayout(self.inner)
        root.setContentsMargins(12, 12, 12, 16)
        root.setSpacing(10)

        tip = QLabel("点击日期查看当日班级日志；点击某条记录可编辑或删除；有记录的日期左上角会显示手写「＃」标记。")
        tip.setObjectName("hintLabel")
        configure_wrap_label(tip)
        tip.setMaximumWidth(1100)
        root.addWidget(tip)

        # 历史检索：布局托管 Label + 输入框 + 搜索按钮，禁止绝对坐标
        search_bar = QHBoxLayout()
        search_bar.setContentsMargins(0, 2, 0, 2)
        search_bar.setSpacing(10)
        lbl_search = QLabel("历史检索：")
        lbl_search.setObjectName("fieldLabel")
        lbl_search.setWordWrap(False)
        search_bar.addWidget(lbl_search, 0)
        self.edit_keyword = QLineEdit()
        self.edit_keyword.setPlaceholderText("输入关键词后回车或点搜索，将跳转到匹配日期")
        self.edit_keyword.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.edit_keyword.returnPressed.connect(self._on_history_search)
        search_bar.addWidget(self.edit_keyword, 1)
        btn_search = QPushButton("搜索")
        btn_search.setMinimumSize(80, 32)
        btn_search.clicked.connect(self._on_history_search)
        search_bar.addWidget(btn_search, 0)
        root.addLayout(search_bar)

        self.calendar = LogCalendarWidget()
        self.calendar.setMinimumHeight(360)
        self.calendar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        root.addWidget(self.calendar)

        legend = QLabel("日期格左上角「＃」表示该日有班级日志")
        legend.setObjectName("legendLabel")
        configure_wrap_label(legend)
        legend.setMaximumWidth(1100)
        root.addWidget(legend)

        self.lbl_day_title = QLabel()
        self.lbl_day_title.setObjectName("pageTitle")
        root.addWidget(self.lbl_day_title)

        # 新增按钮：日历左下方、记录表上方
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(0, 2, 0, 2)
        btn_bar.setSpacing(8)
        btn_add = QPushButton("新增本日日志")
        btn_add.clicked.connect(self._on_add)
        btn_bar.addWidget(btn_add)
        btn_bar.addStretch()
        root.addLayout(btn_bar)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line)

        self.table = QTableWidget(0, len(self.DAY_COLUMNS))
        self.table.setHorizontalHeaderLabels(self.DAY_COLUMNS)
        self.table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.table.cellClicked.connect(self._on_row_clicked)
        # 当日活动表加高，多显示几行；整页由外层滚动承载
        self.table.setMinimumHeight(420)
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        table_panel = wrap_table_panel(self.table)
        table_panel.setMinimumHeight(468)
        table_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        root.addWidget(table_panel)
        root.addStretch(1)

        self.scroll.setWidget(self.inner)
        outer.addWidget(self.scroll)

    def reset_scroll(self):
        """切回本页时滚到顶部（与首页一致）。"""
        self.scroll.verticalScrollBar().setValue(0)
        self.scroll.horizontalScrollBar().setValue(0)

    def _bind_calendar(self):
        self.calendar.date_selected.connect(self._on_date_selected)
        self.calendar.month_changed.connect(self._on_month_changed)

    # ---------- 异步数据 ----------
    def _load_marks_async(self, year: int, month: int):
        self._marks_token += 1
        token = self._marks_token
        worker = _LogDatesWorker(year, month, token, self)

        def _ok(y, m, dates, tok=token):
            if tok != self._marks_token:
                return
            if y != self.calendar.year_shown() or m != self.calendar.month_shown():
                return
            self.calendar.set_log_dates(dates)

        def _fail(msg, tok=token):
            if tok != self._marks_token:
                return
            print(f"[班级日志] 加载日历标记失败: {msg}")

        worker.finished_ok.connect(_ok)
        worker.failed.connect(_fail)
        self._dates_worker = worker
        worker.start()

    def _load_day_async(self, date_str: str):
        self.current_day = date_str
        self.lbl_day_title.setText(f"{date_str} 班级日志（加载中…）")
        self._day_token += 1
        token = self._day_token
        worker = _DayLogsWorker(date_str, token, self)

        def _ok(day, rows, tok=token):
            if tok != self._day_token:
                return
            self._fill_day_table(day, rows)

        def _fail(msg, tok=token):
            if tok != self._day_token:
                return
            QMessageBox.critical(self, "错误", f"查询当日日志失败：\n{msg}")

        worker.finished_ok.connect(_ok)
        worker.failed.connect(_fail)
        self._day_worker = worker
        worker.start()

    def _fill_day_table(self, date_str: str, rows):
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            log_type = classlog_service.format_type(row)
            people = classlog_service.format_participants(row) or "（未选）"
            values = [
                str(row.get("id") or ""),
                log_type,
                people,
                classlog_service.format_moral(row),
                row.get("content") or "",
                format_datetime(row.get("create_time")),
            ]
            for c, text in enumerate(values):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row.get("id"))
                self.table.setItem(r, c, item)

        if not rows:
            self.lbl_day_title.setText(f"{date_str} 班级日志（暂无记录）")
        else:
            self.lbl_day_title.setText(f"{date_str} 班级日志（{len(rows)} 条）")

    # ---------- 日历联动 ----------
    def _on_date_selected(self, qdate: QDate):
        if not qdate or not qdate.isValid():
            return
        self._load_day_async(qdate.toString("yyyy-MM-dd"))

    def _on_month_changed(self, year: int, month: int):
        self._load_marks_async(year, month)
        sel = self.calendar.selected_date()
        if sel.year() != year or sel.month() != month:
            today = QDate.currentDate()
            if year == today.year() and month == today.month():
                qd = today
            else:
                qd = QDate(year, month, 1)
            self.calendar.set_selected_date(qd, emit_signal=False)
            self._load_day_async(qd.toString("yyyy-MM-dd"))
        else:
            self._load_day_async(sel.toString("yyyy-MM-dd"))

    def open_day(self, date_str):
        """供外部（首页等）跳转到指定日期。"""
        qd = QDate.fromString(format_date(date_str), "yyyy-MM-dd")
        if not qd.isValid():
            qd = QDate.currentDate()
        self.calendar.set_selected_date(qd, emit_signal=False)
        self._load_marks_async(qd.year(), qd.month())
        self._load_day_async(qd.toString("yyyy-MM-dd"))

    def _refresh_after_mutate(self):
        """增删改后刷新标记与当日列表。"""
        self._load_marks_async(
            self.calendar.year_shown(), self.calendar.month_shown()
        )
        self._load_day_async(self.current_day)

    def _on_history_search(self):
        keyword = self.edit_keyword.text().strip()
        if not keyword:
            QMessageBox.information(self, "提示", "请输入检索关键词")
            return
        try:
            rows = classlog_service.search_logs(keyword=keyword)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        if not rows:
            QMessageBox.information(self, "提示", "未找到匹配日志")
            return

        first = rows[0]
        date_str = format_date(first.get("log_date"))
        qd = QDate.fromString(date_str, "yyyy-MM-dd")
        if qd.isValid():
            self.open_day(date_str)

        if len(rows) > 1:
            QMessageBox.information(
                self, "检索结果",
                f"共找到 {len(rows)} 条，已打开最近一条所属日期：{date_str}",
            )

    def _on_row_clicked(self, row, _column):
        item = self.table.item(row, 0)
        if item is None:
            return
        log_id = item.data(Qt.ItemDataRole.UserRole)
        if log_id is not None:
            self._open_edit(log_id)

    def _on_add(self):
        dialog = LogFormDialog(
            self, default_date=self.current_day, lock_date=True
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        data["log_date"] = self.current_day
        try:
            classlog_service.add_log(**data)
            QMessageBox.information(self, "成功", "日志已新增")
            self._refresh_after_mutate()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _open_edit(self, log_id):
        try:
            log = classlog_service.get_log(log_id)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取日志失败：\n{e}")
            return
        if not log:
            QMessageBox.warning(self, "提示", "该日志不存在")
            return

        dialog = LogFormDialog(self, log=log)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.deleted:
            try:
                classlog_service.remove_log(log_id)
                QMessageBox.information(self, "成功", "已删除")
                self._refresh_after_mutate()
            except Exception as e:
                QMessageBox.warning(self, "失败", str(e))
            return

        data = dialog.get_data()
        try:
            classlog_service.edit_log(log_id, **data)
            QMessageBox.information(self, "成功", "日志已更新")
            new_day = data["log_date"]
            if new_day != self.current_day:
                self.open_day(new_day)
            else:
                self._refresh_after_mutate()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
