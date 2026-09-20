# -*- coding: utf-8 -*-
"""课程模式布局：大类 | 笔记 | 可折叠纲要 | 编辑区。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QAction, QCursor
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPushButton, QSizePolicy,
    QToolButton, QToolTip, QVBoxLayout, QWidget,
)

from service import course_service
from ui.course.editor import CourseNoteEditor


class _TipListWidget(QListWidget):
    """列表条目悬停立刻显示完整名称（缩短默认 Tooltip 延迟）。"""

    def __init__(self, object_name: str = "", parent=None):
        super().__init__(parent)
        if object_name:
            self.setObjectName(object_name)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setSpacing(0)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.itemEntered.connect(self._on_item_entered)

    def _on_item_entered(self, item: QListWidgetItem):
        tip = (item.toolTip() or item.text() or "").strip() if item else ""
        if tip:
            QToolTip.showText(QCursor.pos(), tip, self.viewport())
        else:
            QToolTip.hideText()

    def eventFilter(self, obj, event):
        if obj is self.viewport():
            et = event.type()
            if et == QEvent.Type.Leave:
                QToolTip.hideText()
            elif et == QEvent.Type.ToolTip:
                # QHelpEvent：仍可用 pos() / globalPos()
                item = self.itemAt(event.pos())
                tip = ""
                if item is not None:
                    tip = (item.toolTip() or item.text() or "").strip()
                if tip:
                    QToolTip.showText(event.globalPos(), tip, self.viewport())
                else:
                    QToolTip.hideText()
                return True
            elif et == QEvent.Type.MouseMove:
                # PyQt6 的 QMouseEvent：pos/globalPos 已改为 position/globalPosition
                local = event.position().toPoint()
                item = self.itemAt(local)
                tip = ""
                if item is not None:
                    tip = (item.toolTip() or item.text() or "").strip()
                if tip:
                    if QToolTip.text() != tip:
                        gpos = event.globalPosition().toPoint()
                        QToolTip.showText(gpos, tip, self.viewport())
                else:
                    QToolTip.hideText()
        return super().eventFilter(obj, event)


def _v_split() -> QFrame:
    line = QFrame()
    line.setObjectName("courseSplit")
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFixedWidth(1)
    return line


class CoursePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._outline_sig: list = []
        self._outline_expanded = True
        self._fullscreen = False
        self._build()

    def _build(self):
        self._root = QHBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        self.col_cat = QWidget()
        self.col_cat.setMinimumWidth(112)
        self.col_cat.setMaximumWidth(156)
        self.col_cat.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        cat_lay = QVBoxLayout(self.col_cat)
        cat_lay.setContentsMargins(0, 0, 0, 0)
        cat_lay.setSpacing(4)
        cat_title = QLabel("笔记大类")
        cat_title.setObjectName("courseSection")
        cat_lay.addWidget(cat_title)
        self.cat_list = _TipListWidget()
        self.cat_list.currentItemChanged.connect(self._on_category_changed)
        self.cat_list.customContextMenuRequested.connect(self._on_cat_menu)
        cat_lay.addWidget(self.cat_list, 1)
        self._root.addWidget(self.col_cat, 1)
        self.split_cat = _v_split()
        self._root.addWidget(self.split_cat)

        self.col_note = QWidget()
        self.col_note.setMinimumWidth(112)
        self.col_note.setMaximumWidth(156)
        self.col_note.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        note_lay = QVBoxLayout(self.col_note)
        note_lay.setContentsMargins(8, 0, 0, 0)
        note_lay.setSpacing(4)
        note_title = QLabel("笔记")
        note_title.setObjectName("courseSection")
        note_lay.addWidget(note_title)
        self.note_list = _TipListWidget()
        self.note_list.currentItemChanged.connect(self._on_note_changed)
        self.note_list.customContextMenuRequested.connect(self._on_note_menu)
        note_lay.addWidget(self.note_list, 1)
        self._root.addWidget(self.col_note, 1)
        self.split_note = _v_split()
        self._root.addWidget(self.split_note)

        self.col_outline = QWidget()
        self.col_outline.setObjectName("courseOutlinePanel")
        self.col_outline.setMinimumWidth(140)
        self.col_outline.setMaximumWidth(220)
        self.col_outline.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        out_lay = QVBoxLayout(self.col_outline)
        out_lay.setContentsMargins(8, 0, 0, 0)
        out_lay.setSpacing(4)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(0)
        self.lbl_outline_title = QLabel("纲要")
        self.lbl_outline_title.setObjectName("courseSection")
        head.addWidget(self.lbl_outline_title)
        head.addStretch()
        self.btn_outline_arrow = QToolButton()
        self.btn_outline_arrow.setObjectName("courseOutlineArrow")
        self.btn_outline_arrow.setAutoRaise(True)
        self.btn_outline_arrow.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_outline_arrow.setArrowType(Qt.ArrowType.LeftArrow)
        self.btn_outline_arrow.setFixedSize(22, 22)
        self.btn_outline_arrow.clicked.connect(self._toggle_outline)
        head.addWidget(self.btn_outline_arrow)
        out_lay.addLayout(head)

        self.outline_body = QWidget()
        body_lay = QVBoxLayout(self.outline_body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        self.outline = _TipListWidget("courseOutline")
        self.outline.itemClicked.connect(self._on_outline_clicked)
        body_lay.addWidget(self.outline, 1)
        out_lay.addWidget(self.outline_body, 1)

        self._root.addWidget(self.col_outline, 2)
        self.split_outline = _v_split()
        self._root.addWidget(self.split_outline)

        self.col_editor = QWidget()
        self.col_editor.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        ed_lay = QVBoxLayout(self.col_editor)
        ed_lay.setContentsMargins(10, 0, 0, 0)
        ed_lay.setSpacing(6)
        head_ed = QHBoxLayout()
        head_ed.addStretch()
        self.btn_fullscreen = QPushButton("全屏编辑")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        head_ed.addWidget(self.btn_fullscreen)
        ed_lay.addLayout(head_ed)
        self.editor = CourseNoteEditor()
        self.editor.outline_changed.connect(self._set_outline)
        ed_lay.addWidget(self.editor, 1)
        self._root.addWidget(self.col_editor, 6)

    def reload(self, select_category_id=None, select_note_id=None):
        self.flush()
        self._fill_categories(select_category_id)
        self._fill_notes(select_note_id)

    def flush(self):
        try:
            self.editor.flush()
        except Exception as e:
            print(f"[课程] 保存笔记失败: {e}")

    def _apply_outline_fold(self):
        out_lay = self.col_outline.layout()
        if self._outline_expanded:
            self.lbl_outline_title.show()
            self.outline_body.show()
            self.col_outline.setMinimumWidth(140)
            self.col_outline.setMaximumWidth(220)
            self.btn_outline_arrow.setArrowType(Qt.ArrowType.LeftArrow)
            if out_lay is not None:
                out_lay.setContentsMargins(8, 0, 0, 0)
        else:
            self.lbl_outline_title.hide()
            self.outline_body.hide()
            self.col_outline.setMinimumWidth(28)
            self.col_outline.setMaximumWidth(28)
            self.btn_outline_arrow.setArrowType(Qt.ArrowType.RightArrow)
            if out_lay is not None:
                out_lay.setContentsMargins(2, 0, 2, 0)

    def _toggle_outline(self):
        self._outline_expanded = not self._outline_expanded
        self._apply_outline_fold()

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        visible = not self._fullscreen
        for w in (
            self.col_cat, self.split_cat,
            self.col_note, self.split_note,
            self.col_outline, self.split_outline,
        ):
            w.setVisible(visible)
        self.btn_fullscreen.setText("退出全屏" if self._fullscreen else "全屏编辑")
        if not self._fullscreen:
            self._apply_outline_fold()

    def _current_category_id(self):
        item = self.cat_list.currentItem()
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _current_note_id(self):
        item = self.note_list.currentItem()
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _item_at(self, list_widget: QListWidget, pos) -> QListWidgetItem | None:
        return list_widget.itemAt(pos)

    def _on_cat_menu(self, pos):
        item = self._item_at(self.cat_list, pos)
        if item is not None:
            self.cat_list.setCurrentItem(item)
        menu = QMenu(self)
        act_new = QAction("新建笔记大类", self)
        act_new.triggered.connect(self._on_new_category)
        menu.addAction(act_new)
        if item is not None:
            act_rename = QAction("重命名", self)
            act_del = QAction("删除", self)
            act_rename.triggered.connect(self._on_rename_category)
            act_del.triggered.connect(self._on_delete_category)
            menu.addSeparator()
            menu.addAction(act_rename)
            menu.addAction(act_del)
        menu.exec(self.cat_list.mapToGlobal(pos))

    def _on_note_menu(self, pos):
        item = self._item_at(self.note_list, pos)
        if item is not None:
            self.note_list.setCurrentItem(item)
        menu = QMenu(self)
        act_new = QAction("新建笔记", self)
        act_new.triggered.connect(self._on_new_note)
        menu.addAction(act_new)
        if item is not None:
            act_rename = QAction("重命名", self)
            act_del = QAction("删除", self)
            act_rename.triggered.connect(self._on_rename_note)
            act_del.triggered.connect(self._on_delete_note)
            menu.addSeparator()
            menu.addAction(act_rename)
            menu.addAction(act_del)
        menu.exec(self.note_list.mapToGlobal(pos))

    def _fill_categories(self, select_id=None):
        try:
            cats = course_service.list_categories()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载笔记大类失败：\n{e}")
            cats = []
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        row = 0
        for i, cat in enumerate(cats):
            name = str(cat.get("name") or "未命名")
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, int(cat["id"]))
            item.setToolTip(name)
            self.cat_list.addItem(item)
            if select_id is not None and int(cat["id"]) == int(select_id):
                row = i
        if self.cat_list.count():
            self.cat_list.setCurrentRow(row)
        self.cat_list.blockSignals(False)

    def _fill_notes(self, select_id=None):
        self.flush()
        cat_id = self._current_category_id()
        notes = []
        if cat_id:
            try:
                notes = course_service.list_notes(cat_id)
            except Exception as e:
                QMessageBox.warning(self, "提示", f"加载笔记失败：{e}")
                notes = []
        self.note_list.blockSignals(True)
        self.note_list.clear()
        row = 0
        for i, note in enumerate(notes):
            title = str(note.get("title") or "未命名")
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, int(note["id"]))
            item.setToolTip(title)
            self.note_list.addItem(item)
            if select_id is not None and int(note["id"]) == int(select_id):
                row = i
        if self.note_list.count():
            self.note_list.setCurrentRow(row)
        self.note_list.blockSignals(False)
        self._open_current_note()

    def _open_current_note(self):
        note_id = self._current_note_id()
        if not note_id:
            self.editor.set_note(None)
            return
        try:
            note = course_service.get_note(note_id)
        except Exception as e:
            QMessageBox.warning(self, "提示", f"打开笔记失败：{e}")
            self.editor.set_note(None)
            return
        if not note:
            self.editor.set_note(None)
            return
        self.editor.set_note(note)

    def _on_category_changed(self, _current, _previous):
        self.flush()
        self._fill_notes()

    def _on_note_changed(self, _current, _previous):
        self.flush()
        self._open_current_note()

    def _ask_name(self, title: str, label: str, text: str = "") -> str | None:
        name, ok = QInputDialog.getText(
            self, title, label, QLineEdit.EchoMode.Normal, text
        )
        if not ok:
            return None
        name = (name or "").strip()
        if not name:
            QMessageBox.warning(self, "提示", "名称不能为空")
            return None
        return name

    def _on_new_category(self):
        name = self._ask_name("新建笔记大类", "大类名称：")
        if not name:
            return
        try:
            new_id = course_service.create_category(name)
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        self.reload(select_category_id=new_id)

    def _on_rename_category(self):
        cat_id = self._current_category_id()
        item = self.cat_list.currentItem()
        if not cat_id or item is None:
            QMessageBox.information(self, "提示", "请先选择笔记大类")
            return
        name = self._ask_name("重命名笔记大类", "新名称：", item.text())
        if not name:
            return
        try:
            course_service.rename_category(cat_id, name)
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        note_id = self._current_note_id()
        self.reload(select_category_id=cat_id, select_note_id=note_id)

    def _on_delete_category(self):
        cat_id = self._current_category_id()
        item = self.cat_list.currentItem()
        if not cat_id or item is None:
            QMessageBox.information(self, "提示", "请先选择笔记大类")
            return
        reply = QMessageBox.question(
            self,
            "删除笔记大类",
            f"确定删除「{item.text()}」吗？\n该分类下的全部笔记会一并删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.editor.set_note(None)
        try:
            course_service.remove_category(cat_id)
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        self.reload()

    def _on_new_note(self):
        cat_id = self._current_category_id()
        if not cat_id:
            QMessageBox.information(self, "提示", "请先选择或新建笔记大类")
            return
        name = self._ask_name("新建笔记", "笔记标题：")
        if not name:
            return
        try:
            new_id = course_service.create_note(cat_id, name)
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        self._fill_notes(select_id=new_id)
        self.editor.edit.setFocus()

    def _on_rename_note(self):
        note_id = self._current_note_id()
        item = self.note_list.currentItem()
        if not note_id or item is None:
            QMessageBox.information(self, "提示", "请先选择笔记")
            return
        name = self._ask_name("重命名笔记", "新标题：", item.text())
        if not name:
            return
        try:
            course_service.rename_note(note_id, name)
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        item.setText(name)
        item.setToolTip(name)

    def _on_delete_note(self):
        note_id = self._current_note_id()
        item = self.note_list.currentItem()
        if not note_id or item is None:
            QMessageBox.information(self, "提示", "请先选择笔记")
            return
        reply = QMessageBox.question(
            self,
            "删除笔记",
            f"确定删除笔记「{item.text()}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.editor.set_note(None)
        try:
            course_service.remove_note(note_id)
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        self._fill_notes()

    def _set_outline(self, items: list):
        sig = [(int(it["level"]), it["text"]) for it in items]
        if sig == self._outline_sig and self.outline.count() == len(items):
            for row, it in enumerate(items):
                self.outline.item(row).setData(
                    Qt.ItemDataRole.UserRole, int(it["position"])
                )
                self.outline.item(row).setToolTip(it["text"])
            return
        self._outline_sig = sig
        self.outline.clear()
        for it in items:
            prefix = "    " if int(it["level"]) == 2 else ""
            mark = "一级" if int(it["level"]) == 1 else "二级"
            text = it["text"]
            row = QListWidgetItem(f"{prefix}{mark}  {text}")
            row.setData(Qt.ItemDataRole.UserRole, int(it["position"]))
            row.setToolTip(text)
            self.outline.addItem(row)

    def _on_outline_clicked(self, item: QListWidgetItem):
        pos = item.data(Qt.ItemDataRole.UserRole)
        if pos is None:
            return
        self.editor.jump_to(int(pos))
