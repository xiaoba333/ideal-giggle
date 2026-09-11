# -*- coding: utf-8 -*-
"""立式实体黑板：深绿磨砂 + 深棕木框 + 粉笔肌理。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont
from PyQt6.QtWidgets import QWidget, QSizePolicy

from ui.personal.sticky_note import StickyNoteWidget


class BlackboardWidget(QWidget):
    """黑板画板容器：承载可拖拽便签。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("essayBlackboard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(360, 320)
        self._notes: dict[int, StickyNoteWidget] = {}
        self._title = ""

    def set_title(self, title: str):
        self._title = title or ""
        self.update()

    def clear_notes(self):
        for w in list(self._notes.values()):
            w.setParent(None)
            w.deleteLater()
        self._notes.clear()

    def upsert_note_widget(self, note: dict) -> StickyNoteWidget:
        nid = int(note["id"])
        if nid in self._notes:
            w = self._notes[nid]
            w.set_full_text(note.get("content") or "")
            w.apply_size(
                int(note.get("width") or 118),
                int(note.get("height") or 108),
                keep_center=False,
            )
            w.apply_angle(float(note.get("rotation") or 0), emit=False, keep_center=False)
            w.place_at(int(note.get("pos_x") or 40), int(note.get("pos_y") or 40))
            return w
        w = StickyNoteWidget(note, self)
        self._notes[nid] = w
        w.show()
        return w

    def remove_note_widget(self, note_id: int):
        w = self._notes.pop(int(note_id), None)
        if w is not None:
            w.setParent(None)
            w.deleteLater()

    def note_widgets(self):
        return list(self._notes.values())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # 外框深棕木
        wood = QLinearGradient(0, 0, rect.width(), 0)
        wood.setColorAt(0.0, QColor("#5a3a22"))
        wood.setColorAt(0.5, QColor("#7a5233"))
        wood.setColorAt(1.0, QColor("#4e311c"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(wood)
        p.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 10, 10)

        # 内板深绿磨砂
        board = rect.adjusted(14, 14, -14, -14)
        chalk_bg = QLinearGradient(0, board.top(), 0, board.bottom())
        chalk_bg.setColorAt(0.0, QColor("#1e3d2f"))
        chalk_bg.setColorAt(0.55, QColor("#163328"))
        chalk_bg.setColorAt(1.0, QColor("#102820"))
        p.setBrush(chalk_bg)
        p.drawRoundedRect(board, 4, 4)

        # 粉笔粉尘肌理（稀疏点）
        p.setPen(Qt.PenStyle.NoPen)
        seed = 17
        for i in range(90):
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            x = board.left() + (seed % max(1, board.width()))
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            y = board.top() + (seed % max(1, board.height()))
            a = 18 + (seed % 28)
            p.setBrush(QColor(220, 230, 210, a))
            p.drawEllipse(QPoint(x, y), 1, 1)

        # 内描边
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(90, 120, 100, 80), 1))
        p.drawRoundedRect(board.adjusted(1, 1, -1, -1), 3, 3)

        # 右下角粉笔字：黑板名称
        if self._title:
            p.setPen(QColor(230, 235, 220, 200))
            font = QFont("Microsoft YaHei", 10)
            font.setItalic(True)
            p.setFont(font)
            p.drawText(
                board.adjusted(12, 8, -14, -10),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom),
                self._title,
            )
