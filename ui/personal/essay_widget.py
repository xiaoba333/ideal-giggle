# -*- coding: utf-8 -*-
"""感触随笔页面：黑板 + 便签堆。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QDialog,
    QMessageBox, QSizePolicy, QLineEdit, QInputDialog,
)

from service import essay_service
from ui.personal.leaf_button import LeafButton
from ui.personal.blackboard import BlackboardWidget
from ui.personal.sticky_stack import StickyStackWidget
from ui.personal.styles import PERSONAL_QSS, COLOR_BG
from ui.personal.handwriting_font import handwriting_font


class NoteEditDialog(QDialog):
    """新建 / 查看编辑便签全文。"""

    def __init__(self, parent=None, text="", title="编辑便签"):
        super().__init__(parent)
        self.setObjectName("personalDialog")
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(420, 320)
        self.setStyleSheet(
            PERSONAL_QSS
            + f"QDialog#personalDialog {{ background: {COLOR_BG}; }}"
            + "QTextEdit { background:#fffaf0; color:#5c4030;"
            " border:1px solid #b2d8bc; border-radius:8px; padding:8px; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        self.edit = QTextEdit()
        self.edit.setFont(handwriting_font(14))
        self.edit.setPlainText(text or "")
        lay.addWidget(self.edit, 1)
        row = QHBoxLayout()
        row.addStretch()
        btn_cancel = LeafButton("关闭", tone="soft")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = LeafButton("确认")
        btn_ok.clicked.connect(self.accept)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        lay.addLayout(row)
        self.edit.setFocus()

    def text(self) -> str:
        return self.edit.toPlainText().strip()


class EssayWidget(QWidget):
    """感触随笔主页面（无页面滚动，铺满可视区）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._boards: list[dict] = []
        self._index = 0
        self._build_ui()
        self.reload()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("感触随笔")
        title.setObjectName("pageTitle")
        head.addWidget(title)
        head.addStretch()
        self.lbl_board = QLabel("")
        self.lbl_board.setObjectName("hintLabel")
        head.addWidget(self.lbl_board)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(8)
        nav = QHBoxLayout()
        nav.setSpacing(8)
        self.btn_prev = LeafButton("◀ 上一块", tone="soft")
        self.btn_next = LeafButton("下一块 ▶", tone="soft")
        self.btn_new = LeafButton("新建黑板")
        self.btn_rename = LeafButton("重命名", tone="soft")
        self.btn_del = LeafButton("删除黑板", tone="deep")
        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_next.clicked.connect(self._on_next)
        self.btn_new.clicked.connect(self._on_new_board)
        self.btn_rename.clicked.connect(self._on_rename_board)
        self.btn_del.clicked.connect(self._on_delete_board)
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.btn_next)
        nav.addStretch()
        nav.addWidget(self.btn_new)
        nav.addWidget(self.btn_rename)
        nav.addWidget(self.btn_del)
        left.addLayout(nav)

        self.board = BlackboardWidget()
        left.addWidget(self.board, 1)
        body.addLayout(left, 1)

        self.stack = StickyStackWidget()
        self.stack.create_requested.connect(self._on_create_note)
        body.addWidget(self.stack, 0)

        root.addLayout(body, 1)

    def reload(self):
        try:
            self._boards = essay_service.ensure_at_least_one_board()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载黑板失败：\n{e}")
            self._boards = []
            return
        if self._index >= len(self._boards):
            self._index = max(0, len(self._boards) - 1)
        self._refresh_board_view()

    def _current_board(self) -> dict | None:
        if not self._boards:
            return None
        return self._boards[self._index]

    def _refresh_board_view(self):
        board = self._current_board()
        has_prev = self._index > 0
        has_next = self._index < len(self._boards) - 1
        self.btn_prev.setEnabled(has_prev)
        self.btn_next.setEnabled(has_next)
        self.btn_del.setEnabled(len(self._boards) > 1)
        if not board:
            self.lbl_board.setText("暂无黑板")
            self.board.clear_notes()
            self.board.set_title("")
            return

        name = (board.get("title") or "").strip() or "未命名"
        self.lbl_board.setText(f"{self._index + 1}/{len(self._boards)}")
        self.board.set_title(name)
        self.board.clear_notes()
        try:
            notes = essay_service.list_notes(board["id"])
        except Exception as e:
            QMessageBox.warning(self, "提示", f"加载便签失败：{e}")
            notes = []
        for note in notes:
            w = self.board.upsert_note_widget(note)
            self._wire_note(w)

    def _wire_note(self, w):
        w.moved.connect(self._on_note_moved)
        w.resized.connect(self._on_note_resized)
        w.rotated.connect(self._on_note_rotated)
        w.edit_requested.connect(self._on_note_edit)
        w.delete_requested.connect(self._on_note_delete)
        w.raised.connect(self._on_note_raised)
        w.transfer_edge_requested.connect(self._on_note_transfer_edge)
        w.transfer_menu_requested.connect(self._on_note_transfer_menu)
        w.drag_finished.connect(self._on_note_drag_finished)

    def _on_prev(self):
        if self._index <= 0:
            return
        self._index -= 1
        self._refresh_board_view()

    def _on_next(self):
        if self._index >= len(self._boards) - 1:
            return
        self._index += 1
        self._refresh_board_view()

    def _on_new_board(self):
        name, ok = QInputDialog.getText(
            self, "新建黑板", "请输入黑板名称：",
            QLineEdit.EchoMode.Normal, "",
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            QMessageBox.warning(self, "提示", "名称不能为空")
            return
        try:
            new_id = essay_service.create_board(name)
            self._boards = essay_service.list_boards()
            for i, b in enumerate(self._boards):
                if int(b["id"]) == int(new_id):
                    self._index = i
                    break
            self._refresh_board_view()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_rename_board(self):
        board = self._current_board()
        if not board:
            return
        old = (board.get("title") or "").strip() or "未命名"
        name, ok = QInputDialog.getText(
            self, "重命名黑板", "请输入新名称：",
            QLineEdit.EchoMode.Normal, old,
        )
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            QMessageBox.warning(self, "提示", "名称不能为空")
            return
        try:
            essay_service.rename_board(board["id"], name)
            self._boards = essay_service.list_boards()
            # 保持当前索引指向同一块板
            for i, b in enumerate(self._boards):
                if int(b["id"]) == int(board["id"]):
                    self._index = i
                    break
            self._refresh_board_view()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_delete_board(self):
        board = self._current_board()
        if not board:
            return
        if len(self._boards) <= 1:
            QMessageBox.information(self, "提示", "至少保留一块黑板")
            return
        name = (board.get("title") or "").strip() or "未命名"
        reply = QMessageBox.question(
            self, "删除黑板",
            f"确定删除黑板「{name}」及其全部便签吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            essay_service.remove_board(board["id"])
            self._boards = essay_service.list_boards()
            self._index = min(self._index, max(0, len(self._boards) - 1))
            self._refresh_board_view()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_create_note(self):
        board = self._current_board()
        if not board:
            QMessageBox.information(self, "提示", "请先新建一块黑板")
            return
        dlg = NoteEditDialog(self, text="", title="新建便签")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        text = dlg.text()
        if not text:
            QMessageBox.warning(self, "提示", "内容不能为空")
            return
        try:
            count = len(self.board.note_widgets())
            x = 40 + (count % 5) * 24
            y = 48 + (count % 4) * 28
            note_id = essay_service.add_note(board["id"], text, pos_x=x, pos_y=y)
            note = essay_service.get_note(note_id)
            if note:
                w = self.board.upsert_note_widget(note)
                self._wire_note(w)
                w.raise_()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_note_moved(self, note_id: int, x: int, y: int):
        try:
            essay_service.move_note(note_id, x, y, raise_z=True)
        except Exception as e:
            print(f"[随笔] 保存位置失败: {e}")

    def _on_note_drag_finished(self, note_id: int, x: int, y: int, global_pos):
        """松手时若落在上一块/下一块按钮上，则转移到对应黑板。"""
        for btn, direction in ((self.btn_prev, -1), (self.btn_next, 1)):
            if not btn.isEnabled():
                continue
            local = btn.mapFromGlobal(global_pos)
            if btn.rect().contains(local):
                self._transfer_note_to_index(note_id, self._index + direction)
                return
        self._on_note_moved(note_id, x, y)

    def _on_note_transfer_edge(self, note_id: int, direction: int):
        target = self._index + int(direction)
        if target < 0 or target >= len(self._boards):
            # 没有相邻板：仍保存当前位置
            for w in self.board.note_widgets():
                if w.note_id == note_id:
                    self._on_note_moved(note_id, w.x(), w.y())
                    break
            return
        self._transfer_note_to_index(note_id, target)

    def _on_note_transfer_menu(self, note_id: int):
        board = self._current_board()
        if not board:
            return
        others = [b for b in self._boards if int(b["id"]) != int(board["id"])]
        if not others:
            QMessageBox.information(self, "提示", "请先新建另一块黑板")
            return
        labels = []
        for i, b in enumerate(self._boards):
            if int(b["id"]) == int(board["id"]):
                continue
            name = (b.get("title") or "").strip() or "未命名"
            labels.append(f"{i + 1}. {name}")
        choice, ok = QInputDialog.getItem(
            self, "移到其他黑板", "选择目标黑板：", labels, 0, False,
        )
        if not ok or not choice:
            return
        try:
            idx = int(choice.split(".", 1)[0]) - 1
        except ValueError:
            return
        if idx < 0 or idx >= len(self._boards):
            return
        if int(self._boards[idx]["id"]) == int(board["id"]):
            return
        self._transfer_note_to_index(note_id, idx)

    def _transfer_note_to_index(self, note_id: int, target_index: int):
        if target_index < 0 or target_index >= len(self._boards):
            return
        target = self._boards[target_index]
        # 落点：目标板左上区域，避免叠在旧位置看不见
        try:
            existing = essay_service.list_notes(target["id"])
            count = len(existing or [])
            x = 40 + (count % 5) * 24
            y = 48 + (count % 4) * 28
            essay_service.transfer_note(note_id, target["id"], pos_x=x, pos_y=y)
            self._index = target_index
            self._refresh_board_view()
            # 把刚移过去的便签置顶，方便确认
            for w in self.board.note_widgets():
                if w.note_id == note_id:
                    w.raise_()
                    break
            name = (target.get("title") or "").strip() or "未命名"
            self.lbl_board.setText(f"{self._index + 1}/{len(self._boards)} · 已移到「{name}」")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"转移便签失败：{e}")

    def _on_note_resized(self, note_id: int, w: int, h: int):
        try:
            essay_service.resize_note(note_id, w, h, raise_z=True)
        except Exception as e:
            print(f"[随笔] 保存尺寸失败: {e}")

    def _on_note_rotated(self, note_id: int, angle: float):
        try:
            essay_service.rotate_note(note_id, angle, raise_z=True)
            # 倾斜会改变外接盒位置，一并落库
            for w in self.board.note_widgets():
                if w.note_id == note_id:
                    essay_service.move_note(note_id, w.x(), w.y(), raise_z=False)
                    break
        except Exception as e:
            print(f"[随笔] 保存倾斜失败: {e}")

    def _on_note_raised(self, note_id: int):
        pass

    def _on_note_edit(self, note_id: int):
        try:
            note = essay_service.get_note(note_id)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return
        if not note:
            QMessageBox.information(self, "提示", "便签不存在")
            return
        dlg = NoteEditDialog(self, text=note.get("content") or "", title="查看 / 编辑便签")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        text = dlg.text()
        if not text:
            QMessageBox.warning(self, "提示", "内容不能为空")
            return
        try:
            essay_service.edit_note(note_id, content=text)
            for w in self.board.note_widgets():
                if w.note_id == note_id:
                    w.set_full_text(text)
                    break
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_note_delete(self, note_id: int):
        reply = QMessageBox.question(
            self, "删除便签", "确定删除这张便签吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            essay_service.remove_note(note_id)
            self.board.remove_note_widget(note_id)
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
