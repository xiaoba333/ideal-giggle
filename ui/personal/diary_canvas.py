# -*- coding: utf-8 -*-
"""个人日记混合画布：文字层 + 手绘层分层共存。"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QEvent, QObject, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics, QImage,
    QMouseEvent, QKeyEvent, QWheelEvent, QTransform,
)
from PyQt6.QtWidgets import (
    QWidget, QTextEdit, QSizePolicy,
)

from ui.personal.styles import COLOR_SOFT, COLOR_TEXT, COLOR_PRIMARY, COLOR_ASSIST


MODE_TEXT = "text"
MODE_DRAW = "draw"
TOOL_PEN = "pen"
TOOL_ERASER = "eraser"

DEFAULT_CANVAS_W = 820
DEFAULT_CANVAS_H = 460

TEXT_DEFAULT_W = 180
TEXT_DEFAULT_H = 72
TEXT_MIN_W = 72
TEXT_MIN_H = 36
# 兼容旧常量；实际上限以画布尺寸为准（见 _max_text_size）
TEXT_MAX_W = 2000
TEXT_MAX_H = 1600
ANGLE_MIN = -60
ANGLE_MAX = 60
_HANDLE = 12
_PAD = 3
_EDGE = 4  # 文本框相对画布边距


def _clamp_angle(angle: float) -> float:
    return max(ANGLE_MIN, min(ANGLE_MAX, float(angle)))


@dataclass
class TextBlock:
    x: float
    y: float
    text: str = ""
    size: int = 14
    bold: bool = False
    color: str = COLOR_TEXT
    w: float = TEXT_DEFAULT_W
    h: float = TEXT_DEFAULT_H
    rotation: float = 0.0

    def font(self) -> QFont:
        f = QFont("Microsoft YaHei", self.size)
        f.setBold(self.bold)
        return f

    def center(self) -> QPointF:
        return QPointF(self.x + self.w / 2.0, self.y + self.h / 2.0)

    def local_rect(self) -> QRectF:
        return QRectF(0, 0, self.w, self.h)

    def transform(self) -> QTransform:
        """画布坐标 -> 文本框局部坐标（左上为原点）的逆：局部 -> 画布。"""
        c = self.center()
        t = QTransform()
        t.translate(c.x(), c.y())
        t.rotate(self.rotation)
        t.translate(-self.w / 2.0, -self.h / 2.0)
        return t

    def map_to_local(self, canvas_pos: QPointF) -> QPointF:
        inv, ok = self.transform().inverted()
        if not ok:
            return QPointF(canvas_pos.x() - self.x, canvas_pos.y() - self.y)
        return inv.map(canvas_pos)

    def contains(self, canvas_pos: QPointF) -> bool:
        lp = self.map_to_local(canvas_pos)
        return self.local_rect().adjusted(-2, -2, 2, 2).contains(lp)

    def bounding_rect(self) -> QRectF:
        """未旋转时的逻辑矩形（左上 + 宽高）。"""
        return QRectF(self.x, self.y, self.w, self.h)

    def aabb(self) -> QRectF:
        """旋转后的轴对齐外接矩形。"""
        t = self.transform()
        corners = [
            t.map(QPointF(0, 0)),
            t.map(QPointF(self.w, 0)),
            t.map(QPointF(self.w, self.h)),
            t.map(QPointF(0, self.h)),
        ]
        xs = [p.x() for p in corners]
        ys = [p.y() for p in corners]
        return QRectF(QPointF(min(xs), min(ys)), QPointF(max(xs), max(ys)))

    def resize_handle_local(self) -> QRectF:
        return QRectF(self.w - _HANDLE, self.h - _HANDLE, _HANDLE, _HANDLE)

    def hit_resize(self, canvas_pos: QPointF) -> bool:
        return self.resize_handle_local().adjusted(2, 2, 4, 4).contains(
            self.map_to_local(canvas_pos)
        )


class HybridDiaryCanvas(QWidget):
    """
    文本模式：点击空白处添加文字，点选/拖动/缩放/旋转/编辑已有文字。
    手绘模式：画笔/橡皮仅作用于墨迹层，不影响文字。
    """

    mode_changed = pyqtSignal(str)
    content_changed = pyqtSignal()

    def __init__(self, parent=None, width=DEFAULT_CANVAS_W, height=DEFAULT_CANVAS_H):
        super().__init__(parent)
        self.setObjectName("diaryCanvas")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(480, 280)

        self._canvas_w = int(width)
        self._canvas_h = int(height)
        self._mode = MODE_TEXT
        self._tool = TOOL_PEN
        self._pen_color = QColor(COLOR_PRIMARY)
        self._pen_width = 4
        self._eraser_width = 18
        self._default_font_size = 14
        self._default_bold = False

        self._texts: List[TextBlock] = []
        self._selected = -1
        self._dragging = False
        self._resizing = False
        self._drag_offset = QPointF(0, 0)
        self._resize_origin: Tuple[float, float] = (TEXT_DEFAULT_W, TEXT_DEFAULT_H)
        self._resize_press_local = QPointF(0, 0)
        self._drawing = False
        self._last_pos: Optional[QPoint] = None

        self._ink = QImage(self._canvas_w, self._canvas_h, QImage.Format.Format_ARGB32_Premultiplied)
        self._ink.fill(Qt.GlobalColor.transparent)

        self._editor: Optional[QTextEdit] = None
        self._editing_index = -1
        self._editor_filter = None

        self.setCursor(Qt.CursorShape.IBeamCursor)

    # ----- public API -----

    def set_mode(self, mode: str):
        self._commit_editor()
        self._mode = MODE_TEXT if mode == MODE_TEXT else MODE_DRAW
        self._selected = -1
        self._dragging = False
        self._resizing = False
        self.setCursor(
            Qt.CursorShape.IBeamCursor if self._mode == MODE_TEXT
            else Qt.CursorShape.CrossCursor
        )
        self.mode_changed.emit(self._mode)
        self.update()

    def mode(self) -> str:
        return self._mode

    def set_tool(self, tool: str):
        self._tool = TOOL_ERASER if tool == TOOL_ERASER else TOOL_PEN

    def tool(self) -> str:
        return self._tool

    def set_pen_color(self, color: QColor | str):
        self._pen_color = QColor(color)

    def set_pen_width(self, width: int):
        self._pen_width = max(1, min(32, int(width)))

    def set_eraser_width(self, width: int):
        self._eraser_width = max(4, min(48, int(width)))

    def set_default_font_size(self, size: int):
        self._default_font_size = max(10, min(36, int(size)))
        if 0 <= self._selected < len(self._texts):
            self._texts[self._selected].size = self._default_font_size
            self.content_changed.emit()
            self.update()

    def set_default_bold(self, bold: bool):
        self._default_bold = bool(bold)
        if 0 <= self._selected < len(self._texts):
            self._texts[self._selected].bold = self._default_bold
            self.content_changed.emit()
            self.update()

    def clear_ink(self):
        self._ink.fill(Qt.GlobalColor.transparent)
        self.content_changed.emit()
        self.update()

    def plain_text_summary(self) -> str:
        parts = [t.text.strip() for t in self._texts if (t.text or "").strip()]
        return "\n".join(parts)

    def export_canvas_data(self) -> str:
        """序列化为 JSON 字符串（含文字 + 手绘 PNG base64）。"""
        self._commit_editor()
        ba = self._ink_to_bytes()
        payload = {
            "version": 2,
            "width": self._canvas_w,
            "height": self._canvas_h,
            "texts": [
                {
                    "x": t.x,
                    "y": t.y,
                    "w": t.w,
                    "h": t.h,
                    "rotation": t.rotation,
                    "text": t.text,
                    "size": t.size,
                    "bold": t.bold,
                    "color": t.color,
                }
                for t in self._texts
            ],
            "ink_png_b64": base64.b64encode(ba).decode("ascii") if ba else "",
        }
        return json.dumps(payload, ensure_ascii=False)

    def load_canvas_data(self, canvas_json: Optional[str], fallback_content: Optional[str] = None):
        """从 JSON 还原；无画布数据时用旧版纯文本兜底。"""
        self._commit_editor()
        self._texts = []
        self._selected = -1
        self._ink = QImage(self._canvas_w, self._canvas_h, QImage.Format.Format_ARGB32_Premultiplied)
        self._ink.fill(Qt.GlobalColor.transparent)

        data = None
        if canvas_json:
            try:
                data = json.loads(canvas_json)
            except (TypeError, json.JSONDecodeError):
                data = None

        if isinstance(data, dict) and data.get("version"):
            w = int(data.get("width") or self._canvas_w)
            h = int(data.get("height") or self._canvas_h)
            self._ensure_ink_size(w, h)
            for item in data.get("texts") or []:
                self._texts.append(self._block_from_dict(item))
            b64 = data.get("ink_png_b64") or ""
            if b64:
                try:
                    raw = base64.b64decode(b64)
                    img = QImage.fromData(raw, "PNG")
                    if not img.isNull():
                        if img.size() != self._ink.size():
                            img = img.scaled(
                                self._ink.size(),
                                Qt.AspectRatioMode.IgnoreAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        self._ink = img.convertToFormat(
                            QImage.Format.Format_ARGB32_Premultiplied
                        )
                except Exception:
                    pass
        elif fallback_content and str(fallback_content).strip():
            self._texts.append(TextBlock(
                x=36, y=36, text=str(fallback_content).strip(),
                size=14, bold=False, color=COLOR_TEXT,
                w=TEXT_DEFAULT_W * 1.6, h=TEXT_DEFAULT_H * 1.4,
            ))
        self.update()

    def sizeHint(self):
        return QSize(self._canvas_w, self._canvas_h)

    # ----- internals -----

    def _block_from_dict(self, item: dict) -> TextBlock:
        text = str(item.get("text") or "")
        size = int(item.get("size") or 14)
        bold = bool(item.get("bold"))
        color = str(item.get("color") or COLOR_TEXT)
        x = float(item.get("x", 40))
        y = float(item.get("y", 40))
        tw = item.get("w")
        th = item.get("h")
        if tw is None or th is None:
            # 旧数据：按文字内容估算框尺寸
            f = QFont("Microsoft YaHei", size)
            f.setBold(bold)
            fm = QFontMetrics(f)
            lines = (text or " ").split("\n")
            est_w = max(fm.horizontalAdvance(line) for line in lines) + 16
            est_h = fm.lineSpacing() * max(1, len(lines)) + 12
            tw, th = est_w, est_h
        cw = max(TEXT_MIN_W, min(TEXT_MAX_W, float(tw)))
        ch = max(TEXT_MIN_H, min(TEXT_MAX_H, float(th)))
        return TextBlock(
            x=x, y=y, text=text, size=size, bold=bold, color=color,
            w=cw, h=ch,
            rotation=_clamp_angle(item.get("rotation") or 0),
        )

    def _max_text_size(self) -> Tuple[float, float]:
        """文本框可拉到接近整张画布。"""
        return (
            float(max(TEXT_MIN_W, self._canvas_w - _EDGE * 2)),
            float(max(TEXT_MIN_H, self._canvas_h - _EDGE * 2)),
        )

    def _clamp_block_size(self, w: float, h: float) -> Tuple[float, float]:
        max_w, max_h = self._max_text_size()
        return (
            max(TEXT_MIN_W, min(max_w, w)),
            max(TEXT_MIN_H, min(max_h, h)),
        )

    def _ensure_ink_size(self, w: int, h: int):
        w, h = max(200, w), max(160, h)
        if self._ink.width() == w and self._ink.height() == h:
            self._canvas_w, self._canvas_h = w, h
            return
        new_ink = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        new_ink.fill(Qt.GlobalColor.transparent)
        p = QPainter(new_ink)
        p.drawImage(0, 0, self._ink)
        p.end()
        self._ink = new_ink
        self._canvas_w, self._canvas_h = w, h

    def _ink_to_bytes(self) -> bytes:
        from PyQt6.QtCore import QBuffer, QIODevice
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        self._ink.save(buf, "PNG")
        return bytes(buf.data())

    def _map_pos(self, pos: QPoint) -> QPoint:
        """控件坐标 -> 画布坐标（居中绘制时的偏移）。"""
        ox = max(0, (self.width() - self._canvas_w) // 2)
        oy = max(0, (self.height() - self._canvas_h) // 2)
        return QPoint(pos.x() - ox, pos.y() - oy)

    def _canvas_origin(self) -> QPoint:
        return QPoint(
            max(0, (self.width() - self._canvas_w) // 2),
            max(0, (self.height() - self._canvas_h) // 2),
        )

    def _hit_text(self, canvas_pos: QPoint) -> int:
        pt = QPointF(canvas_pos)
        for i in range(len(self._texts) - 1, -1, -1):
            if self._texts[i].contains(pt):
                return i
        return -1

    def _clamp_block_pos(self, block: TextBlock):
        """把文本框中心限制在画布内，避免拖出太远。"""
        c = block.center()
        cx = max(8.0, min(self._canvas_w - 8.0, c.x()))
        cy = max(8.0, min(self._canvas_h - 8.0, c.y()))
        block.x = cx - block.w / 2.0
        block.y = cy - block.h / 2.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.fillRect(self.rect(), QColor(COLOR_SOFT))

        origin = self._canvas_origin()
        board = QRect(origin.x(), origin.y(), self._canvas_w, self._canvas_h)
        painter.fillRect(board, QColor("#ffffff"))
        painter.setPen(QPen(QColor(COLOR_ASSIST), 1))
        painter.drawRoundedRect(board.adjusted(0, 0, -1, -1), 8, 8)

        painter.drawImage(origin, self._ink)

        painter.translate(origin)
        for i, block in enumerate(self._texts):
            painter.save()
            c = block.center()
            painter.translate(c)
            painter.rotate(block.rotation)
            painter.translate(-block.w / 2.0, -block.h / 2.0)

            text_rect = QRectF(_PAD, _PAD, block.w - _PAD * 2, block.h - _PAD * 2)
            painter.setFont(block.font())
            painter.setPen(QColor(block.color))
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                    | Qt.TextFlag.TextWordWrap),
                block.text or "",
            )

            if i == self._selected and self._mode == MODE_TEXT:
                painter.setPen(QPen(QColor(COLOR_PRIMARY), 1.2, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(QRectF(0.5, 0.5, block.w - 1, block.h - 1))
                # 右下角缩放把手
                grip = block.resize_handle_local()
                painter.setBrush(QColor(COLOR_PRIMARY))
                painter.setPen(QPen(QColor("#ffffff"), 1))
                painter.drawRect(grip)
            painter.restore()
        painter.resetTransform()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()
        cpos = self._map_pos(event.position().toPoint())
        if not (0 <= cpos.x() < self._canvas_w and 0 <= cpos.y() < self._canvas_h):
            return

        if self._mode == MODE_TEXT:
            self._commit_editor()
            pt = QPointF(cpos)
            # 优先点选中项的缩放角
            if 0 <= self._selected < len(self._texts) and self._texts[self._selected].hit_resize(pt):
                self._resizing = True
                block = self._texts[self._selected]
                self._resize_origin = (block.w, block.h)
                self._resize_press_local = block.map_to_local(pt)
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                self.update()
                return

            hit = self._hit_text(cpos)
            if hit >= 0:
                self._selected = hit
                block = self._texts[hit]
                if block.hit_resize(pt):
                    self._resizing = True
                    self._resize_origin = (block.w, block.h)
                    self._resize_press_local = block.map_to_local(pt)
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                else:
                    self._dragging = True
                    self._drag_offset = QPointF(cpos.x() - block.x, cpos.y() - block.y)
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self._default_font_size = block.size
                self._default_bold = block.bold
            else:
                block = TextBlock(
                    x=float(cpos.x()),
                    y=float(cpos.y()),
                    text="",
                    size=self._default_font_size,
                    bold=self._default_bold,
                    color=COLOR_TEXT,
                    w=TEXT_DEFAULT_W,
                    h=TEXT_DEFAULT_H,
                    rotation=0.0,
                )
                self._texts.append(block)
                self._selected = len(self._texts) - 1
                self.content_changed.emit()
                self._open_editor(self._selected)
            self.update()
        else:
            self._drawing = True
            self._last_pos = cpos
            self._stroke_to(cpos, cpos)

    def mouseMoveEvent(self, event: QMouseEvent):
        cpos = self._map_pos(event.position().toPoint())
        pt = QPointF(cpos)

        if self._mode == MODE_TEXT and self._resizing and 0 <= self._selected < len(self._texts):
            block = self._texts[self._selected]
            local = block.map_to_local(pt)
            ow, oh = self._resize_origin
            nw, nh = self._clamp_block_size(
                local.x() + (ow - self._resize_press_local.x()),
                local.y() + (oh - self._resize_press_local.y()),
            )
            cx, cy = block.center().x(), block.center().y()
            block.w = nw
            block.h = nh
            block.x = cx - block.w / 2.0
            block.y = cy - block.h / 2.0
            self._clamp_block_pos(block)
            self.update()
            return

        if self._mode == MODE_TEXT and self._dragging and 0 <= self._selected < len(self._texts):
            t = self._texts[self._selected]
            t.x = cpos.x() - self._drag_offset.x()
            t.y = cpos.y() - self._drag_offset.y()
            self._clamp_block_pos(t)
            self.update()
            return

        if self._mode == MODE_DRAW and self._drawing and self._last_pos is not None:
            self._stroke_to(self._last_pos, cpos)
            self._last_pos = cpos
            return

        # 悬停光标
        if self._mode == MODE_TEXT:
            if 0 <= self._selected < len(self._texts) and self._texts[self._selected].hit_resize(pt):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif self._hit_text(cpos) >= 0:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.IBeamCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        changed = False
        if self._dragging:
            self._dragging = False
            changed = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self._resizing:
            self._resizing = False
            changed = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self._drawing:
            self._drawing = False
            self._last_pos = None
            changed = True
        if changed:
            self.content_changed.emit()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self._mode != MODE_TEXT or event.button() != Qt.MouseButton.LeftButton:
            return
        cpos = self._map_pos(event.position().toPoint())
        hit = self._hit_text(cpos)
        if hit >= 0:
            self._selected = hit
            self._open_editor(hit)

    def wheelEvent(self, event: QWheelEvent):
        if self._mode != MODE_TEXT or self._editor is not None:
            super().wheelEvent(event)
            return
        if not (0 <= self._selected < len(self._texts)):
            super().wheelEvent(event)
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 3.0 if delta > 0 else -3.0
        block = self._texts[self._selected]
        block.rotation = _clamp_angle(block.rotation + step)
        self.content_changed.emit()
        self.update()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):
        if self._mode == MODE_TEXT and self._selected >= 0 and self._editor is None:
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                del self._texts[self._selected]
                self._selected = -1
                self.content_changed.emit()
                self.update()
                return
            if event.key() == Qt.Key.Key_Return:
                self._open_editor(self._selected)
                return
            # 左右方向键微调角度
            if event.key() == Qt.Key.Key_Left:
                block = self._texts[self._selected]
                block.rotation = _clamp_angle(block.rotation - 3)
                self.content_changed.emit()
                self.update()
                return
            if event.key() == Qt.Key.Key_Right:
                block = self._texts[self._selected]
                block.rotation = _clamp_angle(block.rotation + 3)
                self.content_changed.emit()
                self.update()
                return
            if event.key() == Qt.Key.Key_0 and (
                event.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                self._texts[self._selected].rotation = 0.0
                self.content_changed.emit()
                self.update()
                return
        super().keyPressEvent(event)

    def _stroke_to(self, p0: QPoint, p1: QPoint):
        painter = QPainter(self._ink)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._tool == TOOL_ERASER:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pen = QPen(QColor(0, 0, 0, 0), self._eraser_width,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
        else:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(self._pen_color, self._pen_width,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(p0, p1)
        painter.end()
        self.update()

    def _open_editor(self, index: int):
        if not (0 <= index < len(self._texts)):
            return
        # 已在编辑同一块：只聚焦，避免 commit 删空块后再用旧索引崩溃
        if self._editor is not None and self._editing_index == index:
            self._editor.setFocus()
            return
        target = self._texts[index]
        self._commit_editor()
        # commit 可能删掉空文本块并改变下标，按对象重新定位
        try:
            index = self._texts.index(target)
        except ValueError:
            return
        block = self._texts[index]
        origin = self._canvas_origin()
        self._editor = QTextEdit(self)
        self._editor.setPlainText(block.text)
        self._editor.setFont(block.font())
        self._editor.setStyleSheet(
            "QTextEdit { background: #ffffff; color: #274430;"
            " border: 2px solid #579669; border-radius: 6px; padding: 4px; }"
        )
        # 编辑器用轴对齐外接盒，避免倾斜时输入不便
        aabb = block.aabb()
        x = origin.x() + int(aabb.left())
        y = origin.y() + int(aabb.top())
        w = max(int(aabb.width()), int(block.w), 120)
        h = max(int(aabb.height()), int(block.h), 48)
        self._editor.setGeometry(
            max(origin.x(), x),
            max(origin.y(), y),
            min(w, origin.x() + self._canvas_w - max(origin.x(), x)),
            min(h, origin.y() + self._canvas_h - max(origin.y(), y)),
        )
        self._editing_index = index

        class _FocusFilter(QObject):
            def __init__(self, canvas):
                super().__init__(canvas)
                self._canvas = canvas

            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.FocusOut:
                    self._canvas._commit_editor()
                return False

        self._editor_filter = _FocusFilter(self)
        self._editor.installEventFilter(self._editor_filter)
        self._editor.show()
        self._editor.setFocus()

    def _commit_editor(self):
        if self._editor is None:
            return
        idx = self._editing_index
        text = self._editor.toPlainText()
        editor = self._editor
        self._editor = None
        self._editing_index = -1
        self._editor_filter = None
        editor.hide()
        editor.deleteLater()
        if 0 <= idx < len(self._texts):
            self._texts[idx].text = text
            if not text.strip():
                del self._texts[idx]
                if self._selected == idx:
                    self._selected = -1
                elif self._selected > idx:
                    self._selected -= 1
            self.content_changed.emit()
        self.update()
