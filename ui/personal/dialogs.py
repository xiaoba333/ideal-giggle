# -*- coding: utf-8 -*-
"""个人日记 / 里程碑 / 心情弹窗（绿色主题）。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QTextEdit, QFileDialog, QMessageBox, QButtonGroup, QRadioButton,
    QSlider, QFrame, QComboBox, QCheckBox,
)

from service import personal_service
from service.personal_service import (
    MOOD_HAPPY, MOOD_NORMAL, MOOD_TIRED, MOOD_SAD,
)
from utils.date_util import format_date
from utils import personal_image_util
from ui.personal.leaf_button import LeafButton
from ui.personal.styles import PERSONAL_QSS, COLOR_BG, COLOR_PRIMARY, COLOR_SOFT
from ui.personal.diary_canvas import (
    HybridDiaryCanvas, MODE_TEXT, MODE_DRAW, TOOL_PEN, TOOL_ERASER,
)

# 画笔色板：森系绿为主，辅以自然色便于插画
_PEN_COLORS = (
    ("松绿", "#579669"),
    ("墨绿", "#274430"),
    ("叶绿", "#6aad7c"),
    ("亮绿", "#2e9b4a"),
    ("浅绿", "#b2d8bc"),
    ("苔绿", "#3f7550"),
    ("青碧", "#2a9d8f"),
    ("天空", "#5b8def"),
    ("靛蓝", "#3d5a80"),
    ("淡紫", "#8e7cc3"),
    ("玫瑰", "#d4768c"),
    ("珊瑚", "#e07a5f"),
    ("暖橙", "#e09f3e"),
    ("蜜黄", "#e9c46a"),
    ("咖啡", "#8b6914"),
    ("暖墨", "#4a5c48"),
    ("炭黑", "#2e2e2e"),
    ("粉笔白", "#f5f5f0"),
)


def _apply_personal_dialog(dlg: QDialog):
    dlg.setObjectName("personalDialog")
    dlg.setStyleSheet(
        PERSONAL_QSS
        + f"""
        QDialog#personalDialog {{ background: {COLOR_BG}; }}
        QWidget#diaryCanvas {{
            background: {COLOR_SOFT};
            border: 1px solid #b2d8bc;
            border-radius: 10px;
        }}
        QFrame#diaryToolBar {{
            background: #ffffff;
            border: 1px solid #b2d8bc;
            border-radius: 10px;
        }}
        QLabel#toolHint {{
            color: #63806c;
            font-size: 9pt;
        }}
        QComboBox, QSlider, QCheckBox, QLineEdit {{
            color: #274430;
        }}
        """
    )


class DiaryFormDialog(QDialog):
    """文本 + 手绘混合画板日记编辑器。"""

    def __init__(self, parent=None, diary=None, default_date=None):
        super().__init__(parent)
        _apply_personal_dialog(self)
        self.diary = diary
        self.deleted = False
        self._pending_image_abs = None
        self._image_cleared = False
        self.setWindowTitle("编辑日记" if diary else "写日记")
        self.resize(960, 720)
        self.setMinimumSize(820, 600)
        self._build_ui()
        if diary:
            self._fill(diary)
        elif default_date:
            qd = QDate.fromString(format_date(default_date), "yyyy-MM-dd")
            if qd.isValid():
                self._date = qd
                self.lbl_date.setText(qd.toString("yyyy-MM-dd"))

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        head = QHBoxLayout()
        self._date = QDate.currentDate()
        self.lbl_date = QLabel(self._date.toString("yyyy-MM-dd"))
        self.lbl_date.setObjectName("pageTitle")
        head.addWidget(QLabel("日期"))
        head.addWidget(self.lbl_date)
        head.addStretch()
        lay.addLayout(head)

        # —— 工具条 ——
        tools = QFrame()
        tools.setObjectName("diaryToolBar")
        tools.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tlay = QVBoxLayout(tools)
        tlay.setContentsMargins(10, 8, 10, 8)
        tlay.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.btn_mode_text = LeafButton("文本模式")
        self.btn_mode_draw = LeafButton("手绘模式", tone="soft")
        self.btn_mode_text.clicked.connect(lambda: self._set_mode(MODE_TEXT))
        self.btn_mode_draw.clicked.connect(lambda: self._set_mode(MODE_DRAW))
        row1.addWidget(self.btn_mode_text)
        row1.addWidget(self.btn_mode_draw)
        row1.addSpacing(12)

        # 文本工具
        self.lbl_font = QLabel("字号")
        self.combo_font = QComboBox()
        for s in (12, 14, 16, 18, 22, 28):
            self.combo_font.addItem(f"{s}", s)
        self.combo_font.setCurrentIndex(1)
        self.combo_font.currentIndexChanged.connect(self._on_font_size)
        self.chk_bold = QCheckBox("加粗")
        self.chk_bold.toggled.connect(self._on_bold)
        row1.addWidget(self.lbl_font)
        row1.addWidget(self.combo_font)
        row1.addWidget(self.chk_bold)
        row1.addSpacing(12)

        # 手绘工具
        self.btn_pen = LeafButton("画笔")
        self.btn_eraser = LeafButton("橡皮", tone="soft")
        self.btn_pen.clicked.connect(lambda: self._set_tool(TOOL_PEN))
        self.btn_eraser.clicked.connect(lambda: self._set_tool(TOOL_ERASER))
        self.btn_clear_ink = LeafButton("清空手绘", tone="deep")
        self.btn_clear_ink.clicked.connect(self._on_clear_ink)
        row1.addWidget(self.btn_pen)
        row1.addWidget(self.btn_eraser)
        row1.addWidget(self.btn_clear_ink)
        row1.addStretch()
        tlay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(QLabel("画笔颜色"))
        self._color_btns = []
        self._color_group = QButtonGroup(self)
        for i, (name, hex_c) in enumerate(_PEN_COLORS):
            btn = QRadioButton()
            btn.setToolTip(name)
            btn.setStyleSheet(
                f"QRadioButton::indicator {{ width:18px; height:18px;"
                f" border-radius:9px; background:{hex_c}; border:2px solid #274430; }}"
                f"QRadioButton::indicator:checked {{ border:3px solid #ffffff;"
                f" outline: 2px solid {COLOR_PRIMARY}; }}"
            )
            btn.setProperty("pen_color", hex_c)
            self._color_group.addButton(btn, i)
            row2.addWidget(btn)
            self._color_btns.append(btn)
            if i == 0:
                btn.setChecked(True)
        self._color_group.idClicked.connect(self._on_color)

        row2.addSpacing(10)
        row2.addWidget(QLabel("粗细"))
        self.slider_width = QSlider(Qt.Orientation.Horizontal)
        self.slider_width.setRange(1, 24)
        self.slider_width.setValue(4)
        self.slider_width.setFixedWidth(120)
        self.slider_width.valueChanged.connect(self._on_width)
        self.lbl_width = QLabel("4")
        row2.addWidget(self.slider_width)
        row2.addWidget(self.lbl_width)
        row2.addStretch()
        tlay.addLayout(row2)
        lay.addWidget(tools)

        # —— 画布 ——
        self.canvas = HybridDiaryCanvas()
        lay.addWidget(self.canvas, 1)

        # —— 外部配图 ——
        img_row = QHBoxLayout()
        self.lbl_preview = QLabel("暂无外部配图")
        self.lbl_preview.setFixedSize(220, 80)
        self.lbl_preview.setStyleSheet(
            "background:#e6f1ea;border:1px solid #b2d8bc;border-radius:8px;color:#63806c;"
        )
        img_row.addWidget(self.lbl_preview)
        img_btns = QHBoxLayout()
        btn_pick = LeafButton("上传配图")
        btn_pick.clicked.connect(self._on_pick)
        btn_clear = LeafButton("移除配图", tone="soft")
        btn_clear.clicked.connect(self._on_clear_image)
        btn_view = LeafButton("查看大图", tone="soft")
        btn_view.clicked.connect(self._on_view)
        img_btns.addWidget(btn_pick)
        img_btns.addWidget(btn_clear)
        img_btns.addWidget(btn_view)
        img_btns.addStretch()
        img_row.addLayout(img_btns, 1)
        lay.addLayout(img_row)

        btn_row = QHBoxLayout()
        if self.diary:
            btn_del = LeafButton("删除日记", tone="deep")
            btn_del.clicked.connect(self._on_delete)
            btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_cancel = LeafButton("关闭", tone="soft")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = LeafButton("保存")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

        self._set_mode(MODE_TEXT)
        self._set_tool(TOOL_PEN)
        self._on_color(0)

    def _set_mode(self, mode: str):
        self.canvas.set_mode(mode)
        text_on = mode == MODE_TEXT
        self.btn_mode_text.setEnabled(not text_on)
        self.btn_mode_draw.setEnabled(text_on)
        # 文本工具 / 手绘工具显隐感：仍可操作字号（对选中文字）
        for w in (self.btn_pen, self.btn_eraser, self.btn_clear_ink,
                  self.slider_width, self.lbl_width):
            w.setEnabled(not text_on)
        for b in self._color_btns:
            b.setEnabled(not text_on)
        self.combo_font.setEnabled(True)
        self.chk_bold.setEnabled(True)

    def _set_tool(self, tool: str):
        self.canvas.set_tool(tool)

    def _on_color(self, idx: int):
        if 0 <= idx < len(_PEN_COLORS):
            self.canvas.set_pen_color(_PEN_COLORS[idx][1])

    def _on_width(self, value: int):
        self.lbl_width.setText(str(value))
        self.canvas.set_pen_width(value)
        self.canvas.set_eraser_width(max(8, value * 3))

    def _on_font_size(self):
        size = self.combo_font.currentData()
        if size:
            self.canvas.set_default_font_size(int(size))

    def _on_bold(self, checked: bool):
        self.canvas.set_default_bold(checked)

    def _on_clear_ink(self):
        reply = QMessageBox.question(
            self, "清空手绘", "仅清空手绘层，文字保留。确定？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.canvas.clear_ink()

    def _fill(self, diary):
        self._date = QDate.fromString(format_date(diary.get("diary_date")), "yyyy-MM-dd")
        self.lbl_date.setText(self._date.toString("yyyy-MM-dd"))
        self.canvas.load_canvas_data(
            diary.get("canvas_data"),
            fallback_content=diary.get("content"),
        )
        self._refresh_preview()

    def _on_pick(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片 (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            personal_image_util.validate_image_file(path)
        except ValueError as e:
            QMessageBox.warning(self, "提示", str(e))
            return
        self._pending_image_abs = path
        self._image_cleared = False
        self._refresh_preview()

    def _on_clear_image(self):
        self._pending_image_abs = None
        self._image_cleared = True
        self._refresh_preview()

    def _on_view(self):
        from ui.personal.image_preview import open_personal_image_preview
        if self._pending_image_abs:
            open_personal_image_preview(self, self._pending_image_abs, absolute=True)
            return
        if self.diary and self.diary.get("image_path") and not self._image_cleared:
            open_personal_image_preview(self, self.diary.get("image_path"))
        else:
            QMessageBox.information(self, "提示", "暂无图片可预览")

    def _refresh_preview(self):
        pix = QPixmap()
        if self._pending_image_abs:
            pix = personal_image_util.load_pixmap_limited(self._pending_image_abs, 400)
        elif self.diary and self.diary.get("image_path") and not self._image_cleared:
            pix = personal_image_util.load_pixmap_limited(self.diary.get("image_path"), 400)
        if pix.isNull():
            self.lbl_preview.setText("暂无外部配图")
            self.lbl_preview.setPixmap(QPixmap())
        else:
            scaled = pix.scaled(
                self.lbl_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_preview.setText("")
            self.lbl_preview.setPixmap(scaled)

    def _on_delete(self):
        reply = QMessageBox.question(
            self, "确认删除", "确定删除这篇日记吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.deleted = True
            self.accept()

    def get_data(self):
        summary = self.canvas.plain_text_summary()
        return {
            "diary_date": self.lbl_date.text(),
            "content": summary or None,
            "canvas_data": self.canvas.export_canvas_data(),
            "image_source": self._pending_image_abs,
            "clear_image": self._image_cleared,
        }


class MilestoneFormDialog(QDialog):
    def __init__(self, parent=None, milestone=None, default_date=None):
        super().__init__(parent)
        _apply_personal_dialog(self)
        self.milestone = milestone
        self.deleted = False
        self.setWindowTitle("编辑里程碑" if milestone else "添加里程碑")
        self.resize(400, 280)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        form = QFormLayout()
        self.lbl_date = QLabel()
        if milestone:
            self.lbl_date.setText(format_date(milestone.get("mark_date")))
        else:
            self.lbl_date.setText(
                format_date(default_date) or QDate.currentDate().toString("yyyy-MM-dd")
            )
        self.edit_title = QLineEdit()
        self.edit_content = QTextEdit()
        self.edit_content.setMaximumHeight(100)
        form.addRow("日期", self.lbl_date)
        form.addRow("标题 *", self.edit_title)
        form.addRow("详情", self.edit_content)
        lay.addLayout(form)
        if milestone:
            self.edit_title.setText(milestone.get("title") or "")
            self.edit_content.setPlainText(milestone.get("content") or "")

        btn_row = QHBoxLayout()
        if milestone:
            btn_del = LeafButton("删除", tone="deep")
            btn_del.clicked.connect(self._on_delete)
            btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_cancel = LeafButton("关闭", tone="soft")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = LeafButton("保存")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

    def _on_delete(self):
        reply = QMessageBox.question(
            self, "确认删除", "确定删除该里程碑吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.deleted = True
            self.accept()

    def get_data(self):
        return {
            "mark_date": self.lbl_date.text(),
            "title": self.edit_title.text().strip(),
            "content": self.edit_content.toPlainText().strip() or None,
        }


class MoodFormDialog(QDialog):
    OPTIONS = (
        (MOOD_HAPPY, "开心"),
        (MOOD_NORMAL, "一般"),
        (MOOD_TIRED, "疲惫"),
        (MOOD_SAD, "沮丧"),
    )

    def __init__(self, parent=None, date_str=None, current_mood=None):
        super().__init__(parent)
        _apply_personal_dialog(self)
        self.cleared = False
        self.setWindowTitle("当日心情")
        self.resize(360, 220)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.addWidget(QLabel(f"日期：{date_str or ''}"))
        self.group = QButtonGroup(self)
        for i, (val, label) in enumerate(self.OPTIONS):
            rb = QRadioButton(label)
            rb.setProperty("mood_value", val)
            self.group.addButton(rb, i)
            lay.addWidget(rb)
            if current_mood == val:
                rb.setChecked(True)
        if current_mood is None and self.group.buttons():
            self.group.buttons()[0].setChecked(True)

        btn_row = QHBoxLayout()
        btn_clear = LeafButton("清空心情", tone="deep")
        btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        btn_cancel = LeafButton("关闭", tone="soft")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = LeafButton("保存")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

    def _on_clear(self):
        self.cleared = True
        self.accept()

    def selected_mood(self):
        btn = self.group.checkedButton()
        if not btn:
            return None
        return btn.property("mood_value")
