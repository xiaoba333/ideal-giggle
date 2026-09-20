# -*- coding: utf-8 -*-
"""课程笔记富文本编辑器：字号、颜色、插图、一二级标题。"""

from __future__ import annotations

import json
import re

from PyQt6.QtCore import QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QImage, QPixmap, QTextCharFormat, QTextCursor, QTextDocument,
    QTextImageFormat,
)
from PyQt6.QtWidgets import (
    QColorDialog, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from ui.course.image_preview import CourseImagePreviewDialog
from utils.course_image_util import (
    absolute_image_path, html_for_display, html_for_storage, load_pixmap_limited,
    save_course_image,
)

_FONT_SIZES = (12, 14, 16, 18, 20, 24, 28, 32)
_INSERT_IMAGE_W = 420


class CourseTextEdit(QTextEdit):
    image_activated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(True)
        self.setFont(QFont("Microsoft YaHei", 12))
        self.setPlaceholderText("")

    def mouseDoubleClickEvent(self, event):
        name = _image_name_at(self, event.position().toPoint())
        if name:
            self.image_activated.emit(name)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


def _image_name_at(edit: QTextEdit, point) -> str:
    cursor = edit.cursorForPosition(point)
    fmt = cursor.charFormat()
    if fmt.isImageFormat():
        return fmt.toImageFormat().name()
    if cursor.position() > 0:
        prev = QTextCursor(cursor)
        prev.setPosition(cursor.position() - 1)
        fmt = prev.charFormat()
        if fmt.isImageFormat():
            return fmt.toImageFormat().name()
    return ""


def extract_outline(document: QTextDocument) -> list[dict]:
    items = []
    block = document.begin()
    while block.isValid():
        level = 0
        fmt = block.blockFormat()
        if hasattr(fmt, "headingLevel"):
            level = int(fmt.headingLevel() or 0)
        text = (block.text() or "").strip()
        if level in (1, 2) and text:
            items.append({
                "level": level,
                "text": text,
                "position": int(block.position()),
            })
        block = block.next()
    return items


class CourseNoteEditor(QWidget):
    """当前笔记的编辑区。未选中笔记时工具与正文不可用。"""

    outline_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._note_id = None
        self._dirty = False
        self._loading = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.flush)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        tools = QHBoxLayout()
        tools.setSpacing(6)
        self.combo_size = QComboBox()
        for size in _FONT_SIZES:
            self.combo_size.addItem(f"{size}", size)
        self.combo_size.setCurrentIndex(1)
        self.combo_size.setFixedWidth(88)
        self.combo_size.currentIndexChanged.connect(self._on_font_size)
        tools.addWidget(QLabel("字号"))
        tools.addWidget(self.combo_size)

        self.btn_color = QPushButton("文字颜色")
        self.btn_color.clicked.connect(self._on_color)
        self.btn_image = QPushButton("插入图片")
        self.btn_image.clicked.connect(self._on_insert_image)
        self.btn_zoom_in = QPushButton("放大图片")
        self.btn_zoom_out = QPushButton("缩小图片")
        self.btn_zoom_in.clicked.connect(lambda: self._scale_image(1.15))
        self.btn_zoom_out.clicked.connect(lambda: self._scale_image(0.87))
        tools.addWidget(self.btn_color)
        tools.addWidget(self.btn_image)
        tools.addWidget(self.btn_zoom_in)
        tools.addWidget(self.btn_zoom_out)
        tools.addStretch()
        root.addLayout(tools)

        marks = QHBoxLayout()
        marks.setSpacing(6)
        self.btn_h1 = QPushButton("一级标题")
        self.btn_h2 = QPushButton("二级标题")
        self.btn_body = QPushButton("正文")
        self.btn_h1.clicked.connect(lambda: self._mark_heading(1))
        self.btn_h2.clicked.connect(lambda: self._mark_heading(2))
        self.btn_body.clicked.connect(lambda: self._mark_heading(0))
        marks.addWidget(self.btn_h1)
        marks.addWidget(self.btn_h2)
        marks.addWidget(self.btn_body)
        marks.addStretch()
        root.addLayout(marks)

        self.edit = CourseTextEdit()
        self.edit.image_activated.connect(self._preview_image)
        self.edit.document().contentsChanged.connect(self._on_doc_changed)
        root.addWidget(self.edit, 1)
        self._set_tools_enabled(False)
        self.edit.setEnabled(False)

    def set_note(self, note: dict | None):
        self._save_timer.stop()
        if note is None:
            self._loading = True
            self._note_id = None
            self._dirty = False
            self.edit.clear()
            self.edit.setEnabled(False)
            self._set_tools_enabled(False)
            self._loading = False
            self.outline_changed.emit([])
            return
        nid = int(note["id"])
        if nid == self._note_id:
            self.edit.setEnabled(True)
            self._set_tools_enabled(True)
            return
        self._loading = True
        self._note_id = None
        self.edit.setEnabled(True)
        stored = note.get("content_html") or ""
        self.edit.setHtml(html_for_display(stored))
        self._register_images()
        self._note_id = nid
        self._dirty = False
        self._loading = False
        self._set_tools_enabled(True)
        self._emit_outline()

    def flush(self):
        self._save_timer.stop()
        if self._loading or not self._note_id or not self._dirty:
            return
        items = extract_outline(self.edit.document())
        stored_outline = [
            {"level": int(it["level"]), "text": it["text"]} for it in items
        ]
        html = html_for_storage(self.edit.toHtml())
        from service import course_service
        course_service.save_content(
            self._note_id, html, json.dumps(stored_outline, ensure_ascii=False)
        )
        self._dirty = False

    def jump_to(self, position: int):
        doc = self.edit.document()
        pos = max(0, min(int(position), max(0, doc.characterCount() - 1)))
        cursor = self.edit.textCursor()
        cursor.setPosition(pos)
        self.edit.setTextCursor(cursor)
        self.edit.ensureCursorVisible()
        self.edit.setFocus()

    def _set_tools_enabled(self, enabled: bool):
        for w in (
            self.combo_size, self.btn_color, self.btn_image,
            self.btn_zoom_in, self.btn_zoom_out,
            self.btn_h1, self.btn_h2, self.btn_body,
        ):
            w.setEnabled(enabled)

    def _on_doc_changed(self):
        if self._loading or not self._note_id:
            return
        self._dirty = True
        self._save_timer.start(500)
        self._emit_outline()

    def _emit_outline(self):
        self.outline_changed.emit(extract_outline(self.edit.document()))

    def _on_font_size(self):
        if self._loading or not self._note_id:
            return
        size = self.combo_size.currentData()
        if not size:
            return
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        self._merge_format(fmt)

    def _on_color(self):
        if not self._note_id:
            return
        color = QColorDialog.getColor(QColor("#2e2a24"), self, "文字颜色")
        if not color.isValid():
            return
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        self._merge_format(fmt)

    def _merge_format(self, fmt: QTextCharFormat):
        cursor = self.edit.textCursor()
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        self.edit.mergeCurrentCharFormat(fmt)
        self.edit.setFocus()

    def _mark_heading(self, level: int):
        if not self._note_id:
            return
        cursor = self.edit.textCursor()
        cursor.beginEditBlock()
        block_fmt = cursor.blockFormat()
        if hasattr(block_fmt, "setHeadingLevel"):
            block_fmt.setHeadingLevel(int(level))
        cursor.setBlockFormat(block_fmt)
        char_fmt = QTextCharFormat()
        if level == 1:
            char_fmt.setFontPointSize(22)
            char_fmt.setFontWeight(QFont.Weight.Bold)
        elif level == 2:
            char_fmt.setFontPointSize(16)
            char_fmt.setFontWeight(QFont.Weight.Bold)
        else:
            char_fmt.setFontPointSize(12)
            char_fmt.setFontWeight(QFont.Weight.Normal)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.mergeCharFormat(char_fmt)
        cursor.endEditBlock()
        self.edit.setTextCursor(cursor)
        self.edit.setFocus()
        self._dirty = True
        self._save_timer.start(500)
        self._emit_outline()

    def _on_insert_image(self):
        if not self._note_id:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "插入图片", "", "图片 (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            rel = save_course_image(path)
            abs_path = absolute_image_path(rel)
            if abs_path is None:
                raise ValueError("图片保存失败")
            pix = load_pixmap_limited(abs_path, max_edge=1600)
            if pix.isNull():
                raise ValueError("图片加载失败")
            width = pix.width()
            if width > _INSERT_IMAGE_W:
                width = _INSERT_IMAGE_W
            url = QUrl.fromLocalFile(str(abs_path))
            self.edit.document().addResource(
                QTextDocument.ResourceType.ImageResource, url, pix
            )
            fmt = QTextImageFormat()
            fmt.setName(url.toString())
            fmt.setWidth(width)
            cursor = self.edit.textCursor()
            cursor.insertImage(fmt)
            self.edit.setTextCursor(cursor)
            self.edit.setFocus()
        except Exception as e:
            QMessageBox.warning(self, "插入失败", str(e))

    def _scale_image(self, factor: float):
        cursor = self._selected_image_cursor()
        if cursor is None:
            QMessageBox.information(self, "提示", "请先单击笔记中的图片")
            return
        fmt = cursor.charFormat().toImageFormat()
        width = fmt.width()
        if width <= 0:
            pix = self._pixmap_for(fmt.name())
            width = pix.width() or _INSERT_IMAGE_W
        fmt.setWidth(max(48, min(1400, int(width * factor))))
        cursor.setCharFormat(fmt)
        self.edit.setFocus()

    def _selected_image_cursor(self) -> QTextCursor | None:
        cursor = self.edit.textCursor()
        if cursor.charFormat().isImageFormat() and cursor.position() > 0:
            end = cursor.position()
            picked = QTextCursor(self.edit.document())
            picked.setPosition(end - 1)
            picked.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            if picked.charFormat().isImageFormat():
                return picked
        probe = QTextCursor(cursor)
        if probe.position() < self.edit.document().characterCount() - 1:
            start = probe.position()
            probe.setPosition(start + 1, QTextCursor.MoveMode.KeepAnchor)
            if probe.charFormat().isImageFormat():
                return probe
        return None

    def _preview_image(self, name: str):
        pix = self._pixmap_for(name)
        if pix.isNull():
            QMessageBox.information(self, "提示", "图片无法打开")
            return
        CourseImagePreviewDialog(pix, self).exec()

    def _pixmap_for(self, name: str) -> QPixmap:
        url = QUrl(name)
        res = self.edit.document().resource(
            QTextDocument.ResourceType.ImageResource, url
        )
        if isinstance(res, QPixmap) and not res.isNull():
            return res
        if isinstance(res, QImage) and not res.isNull():
            return QPixmap.fromImage(res)
        local = url.toLocalFile()
        if local:
            pix = load_pixmap_limited(local, max_edge=2000)
            if not pix.isNull():
                return pix
        path = absolute_image_path(name)
        if path and path.is_file():
            return load_pixmap_limited(path, max_edge=2000)
        return QPixmap()

    def _register_images(self):
        html = self.edit.toHtml()
        doc = self.edit.document()
        for match in re.finditer(
            r'<img\b[^>]*?\bsrc\s*=\s*"([^"]+)"', html, re.IGNORECASE
        ):
            src = match.group(1)
            pix = self._pixmap_for(src)
            if pix.isNull():
                continue
            doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(src), pix)
