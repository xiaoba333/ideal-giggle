# -*- coding: utf-8 -*-
"""黑板便签：省略预览、拖拽、角点缩放、倾斜、双击编辑、右键删除。"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QPoint, QRect, QRectF, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFontMetrics, QAction, QWheelEvent,
)
from PyQt6.QtWidgets import QWidget, QMenu

from ui.personal.handwriting_font import handwriting_font

NOTE_W = 118
NOTE_H = 108
NOTE_MIN_W = 80
NOTE_MIN_H = 72
# 软上限；实际缩放以黑板尺寸为准（见 _paper_limits）
NOTE_MAX_W = 1600
NOTE_MAX_H = 1200
ANGLE_MIN = -28
ANGLE_MAX = 28
_RESIZE_PAD = 16
_PAD = 6  # 外接盒额外边距，避免抗锯齿裁切
_BOARD_EDGE = 12


def _clamp_angle(angle: float) -> float:
    return max(ANGLE_MIN, min(ANGLE_MAX, float(angle)))


def _aabb_size(paper_w: int, paper_h: int, angle_deg: float) -> QSize:
    """纸面旋转后的轴对齐外接矩形尺寸。"""
    rad = math.radians(angle_deg)
    c, s = abs(math.cos(rad)), abs(math.sin(rad))
    bw = int(math.ceil(paper_w * c + paper_h * s)) + _PAD * 2
    bh = int(math.ceil(paper_w * s + paper_h * c)) + _PAD * 2
    return QSize(max(bw, paper_w + _PAD * 2), max(bh, paper_h + _PAD * 2))


class StickyNoteWidget(QWidget):
    moved = pyqtSignal(int, int, int)              # note_id, x, y
    resized = pyqtSignal(int, int, int)            # note_id, paper_w, paper_h
    rotated = pyqtSignal(int, float)               # note_id, angle
    edit_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    raised = pyqtSignal(int)
    # 拖到黑板左右边缘松手 → 移到相邻板；direction: -1 上一块 / 1 下一块
    transfer_edge_requested = pyqtSignal(int, int)
    # 右键选择目标黑板
    transfer_menu_requested = pyqtSignal(int)
    # 拖放结束（含全局坐标，用于落到「上一块/下一块」按钮）
    drag_finished = pyqtSignal(int, int, int, QPoint)  # id, x, y, global_pos

    def __init__(self, note: dict, parent=None):
        super().__init__(parent)
        self.note_id = int(note.get("id"))
        self._full_text = note.get("content") or ""
        self._bg = QColor(note.get("bg_color") or "#f3e6c8")
        self._angle = _clamp_angle(note.get("rotation") or 0)
        self._paper_w = max(NOTE_MIN_W, int(note.get("width") or NOTE_W))
        self._paper_h = max(NOTE_MIN_H, int(note.get("height") or NOTE_H))
        self._paper_w, self._paper_h = self._clamp_paper(self._paper_w, self._paper_h)
        # 外接盒可随倾斜与黑板变大，不再卡死在旧的 280 宽
        self.setMinimumSize(NOTE_MIN_W, NOTE_MIN_H)
        self.setMaximumSize(4096, 4096)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_menu)
        self._dragging = False
        self._resizing = False
        self._edge_intent = 0  # -1 左 / 1 右 / 0 无
        self._press_pos = QPoint()
        self._origin = QPoint()
        self._origin_paper = QSize(self._paper_w, self._paper_h)
        box = _aabb_size(self._paper_w, self._paper_h, self._angle)
        self.setGeometry(
            int(note.get("pos_x") or 40),
            int(note.get("pos_y") or 40),
            box.width(),
            box.height(),
        )

    def set_full_text(self, text: str):
        self._full_text = text or ""
        self.update()

    def full_text(self) -> str:
        return self._full_text

    def angle(self) -> float:
        return self._angle

    def paper_size(self) -> QSize:
        return QSize(self._paper_w, self._paper_h)

    def _paper_limits(self) -> tuple[int, int]:
        """纸面宽高上限：尽量贴近黑板，不再使用偏小的固定横向上限。"""
        parent = self.parentWidget()
        if parent is not None and parent.width() > 40 and parent.height() > 40:
            max_w = max(NOTE_MIN_W, parent.width() - _BOARD_EDGE * 2)
            max_h = max(NOTE_MIN_H, parent.height() - _BOARD_EDGE * 2)
            return min(NOTE_MAX_W, max_w), min(NOTE_MAX_H, max_h)
        return NOTE_MAX_W, NOTE_MAX_H

    def _clamp_paper(self, w: int, h: int) -> tuple[int, int]:
        max_w, max_h = self._paper_limits()
        return (
            max(NOTE_MIN_W, min(max_w, int(w))),
            max(NOTE_MIN_H, min(max_h, int(h))),
        )

    def _center(self) -> QPoint:
        return QPoint(self.x() + self.width() // 2, self.y() + self.height() // 2)

    def _sync_bounds(self, keep_center: bool = True):
        """按纸面尺寸与倾斜角更新控件外接盒。"""
        box = _aabb_size(self._paper_w, self._paper_h, self._angle)
        if keep_center:
            c = self._center()
            self.setGeometry(
                c.x() - box.width() // 2,
                c.y() - box.height() // 2,
                box.width(),
                box.height(),
            )
        else:
            self.resize(box)
        # 限制在父容器内
        parent = self.parentWidget()
        if parent is not None:
            nx = max(0, min(parent.width() - self.width(), self.x()))
            ny = max(0, min(parent.height() - self.height(), self.y()))
            self.move(nx, ny)
        self.update()

    def apply_size(self, w: int, h: int, keep_center: bool = True):
        self._paper_w, self._paper_h = self._clamp_paper(w, h)
        self._sync_bounds(keep_center=keep_center)

    def apply_angle(self, angle: float, emit: bool = False, keep_center: bool = True):
        self._angle = _clamp_angle(angle)
        self._sync_bounds(keep_center=keep_center)
        if emit:
            self.rotated.emit(self.note_id, self._angle)

    def place_at(self, x: int, y: int):
        """按外接盒左上角放置（用于从数据库还原）。"""
        box = _aabb_size(self._paper_w, self._paper_h, self._angle)
        self.setGeometry(int(x), int(y), box.width(), box.height())
        parent = self.parentWidget()
        if parent is not None:
            nx = max(0, min(parent.width() - self.width(), self.x()))
            ny = max(0, min(parent.height() - self.height(), self.y()))
            if nx != self.x() or ny != self.y():
                self.move(nx, ny)
        self.update()

    def _resize_hit(self, pos: QPoint) -> bool:
        return (
            pos.x() >= self.width() - _RESIZE_PAD
            and pos.y() >= self.height() - _RESIZE_PAD
        )

    def _preview_lines_count(self) -> int:
        return max(3, min(12, (self._paper_h - 28) // 16))

    def _preview_text(self) -> str:
        text = (self._full_text or "").replace("\r\n", "\n").strip()
        if not text:
            return "（空白）"
        font = handwriting_font(11)
        fm = QFontMetrics(font)
        max_w = max(40, self._paper_w - 28)
        max_lines = self._preview_lines_count()
        lines = []
        for para in text.split("\n"):
            if not para:
                lines.append("")
            else:
                start = 0
                while start < len(para) and len(lines) < max_lines:
                    chunk = ""
                    for i in range(start, len(para) + 1):
                        part = para[start:i]
                        if fm.horizontalAdvance(part) > max_w and chunk:
                            break
                        chunk = part
                    if not chunk:
                        chunk = para[start:start + 1]
                    lines.append(chunk)
                    start += len(chunk)
            if len(lines) >= max_lines:
                break
        preview = "\n".join(lines[:max_lines])
        flat = text.replace("\n", "")
        prev_flat = preview.replace("\n", "")
        if len(flat) > len(prev_flat) or text.count("\n") >= max_lines:
            if lines:
                last = lines[-1]
                while last and fm.horizontalAdvance(last + "…") > max_w:
                    last = last[:-1]
                lines[-1] = (last or "") + "…"
                preview = "\n".join(lines[:max_lines])
        return preview

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # 在外接盒中心绘制纸面并旋转，纸面不会画出盒子
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        p.translate(cx, cy)
        p.rotate(self._angle)

        half_w = self._paper_w / 2.0
        half_h = self._paper_h / 2.0
        r = QRectF(-half_w, -half_h, self._paper_w, self._paper_h)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(40, 50, 40, 55))
        p.drawRoundedRect(r.adjusted(2, 3, 2, 3), 8, 8)

        p.setBrush(self._bg)
        p.setPen(QPen(QColor("#c9b896"), 1))
        p.drawRoundedRect(r, 8, 8)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 55))
        p.drawRoundedRect(r.adjusted(6, 4, -18, -r.height() * 0.55), 4, 4)

        p.setPen(QPen(QColor("#d4c4a0"), 1))
        p.drawLine(
            int(r.left() + 10), int(r.top() + 14),
            int(r.right() - 10), int(r.top() + 14),
        )

        p.setFont(handwriting_font(11))
        p.setPen(QColor("#5c4030"))
        text_rect = r.adjusted(10, 18, -10, -14)
        p.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                | Qt.TextFlag.TextWordWrap),
            self._preview_text(),
        )

        # 缩放把手画在未旋转的外接盒右下角，便于操作
        p.resetTransform()
        grip = QRect(self.width() - 14, self.height() - 14, 10, 10)
        p.setPen(QPen(QColor("#a89070"), 1.5))
        p.drawLine(grip.left(), grip.bottom(), grip.right(), grip.top())
        p.drawLine(grip.left() + 4, grip.bottom(), grip.right(), grip.top() + 4)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 2.5 if delta > 0 else -2.5
        self.apply_angle(self._angle + step, emit=True)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.raise_()
            self.raised.emit(self.note_id)
            self._press_pos = event.globalPosition().toPoint()
            self._origin = self.pos()
            self._origin_paper = QSize(self._paper_w, self._paper_h)
            self._edge_intent = 0
            if self._resize_hit(event.position().toPoint()):
                self._resizing = True
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self._dragging = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._press_pos
            nw = self._origin_paper.width() + delta.x()
            nh = self._origin_paper.height() + delta.y()
            self.apply_size(nw, nh)
            event.accept()
            return
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._press_pos
            parent = self.parentWidget()
            raw_nx = self._origin.x() + delta.x()
            raw_ny = self._origin.y() + delta.y()
            if parent is not None:
                # 顶住左右边并继续外推 → 标记转移到相邻黑板
                if raw_nx < -8:
                    self._edge_intent = -1
                elif raw_nx > parent.width() - self.width() + 8:
                    self._edge_intent = 1
                else:
                    self._edge_intent = 0
                nx = max(0, min(parent.width() - self.width(), raw_nx))
                ny = max(0, min(parent.height() - self.height(), raw_ny))
            else:
                nx, ny = raw_nx, raw_ny
            self.move(nx, ny)
            event.accept()
            return
        if self._resize_hit(event.position().toPoint()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._resizing:
                self._resizing = False
                self.resized.emit(self.note_id, self._paper_w, self._paper_h)
                self.moved.emit(self.note_id, self.x(), self.y())
                self.setCursor(Qt.CursorShape.OpenHandCursor)
                event.accept()
                return
            if self._dragging:
                self._dragging = False
                self.setCursor(Qt.CursorShape.OpenHandCursor)
                gpos = event.globalPosition().toPoint()
                edge = self._edge_intent
                self._edge_intent = 0
                if edge != 0:
                    self.transfer_edge_requested.emit(self.note_id, edge)
                else:
                    self.drag_finished.emit(self.note_id, self.x(), self.y(), gpos)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.edit_requested.emit(self.note_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _on_menu(self, pos):
        menu = QMenu(self)
        act_edit = QAction("查看 / 编辑", self)
        act_move = QAction("移到其他黑板…", self)
        act_left = QAction("左倾一点", self)
        act_right = QAction("右倾一点", self)
        act_reset = QAction("回正", self)
        act_del = QAction("删除便签", self)
        act_edit.triggered.connect(lambda: self.edit_requested.emit(self.note_id))
        act_move.triggered.connect(lambda: self.transfer_menu_requested.emit(self.note_id))
        act_left.triggered.connect(lambda: self.apply_angle(self._angle - 6, emit=True))
        act_right.triggered.connect(lambda: self.apply_angle(self._angle + 6, emit=True))
        act_reset.triggered.connect(lambda: self.apply_angle(0, emit=True))
        act_del.triggered.connect(lambda: self.delete_requested.emit(self.note_id))
        menu.addAction(act_edit)
        menu.addAction(act_move)
        menu.addSeparator()
        menu.addAction(act_left)
        menu.addAction(act_right)
        menu.addAction(act_reset)
        menu.addSeparator()
        menu.addAction(act_del)
        menu.exec(self.mapToGlobal(pos))
