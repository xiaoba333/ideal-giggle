# -*- coding: utf-8 -*-
"""天气简易矢量图案（QPainter 绘制，无外部图片依赖）。"""

from math import cos, sin, pi

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPolygonF
from PyQt6.QtWidgets import QWidget

from ui.styles import COLOR_PRIMARY


def condition_to_icon_kind(condition, weather_code=None):
    """根据天气文案或 WMO 代码选择图案类型。"""
    text = (condition or "").strip()
    try:
        code = int(weather_code) if weather_code is not None else None
    except (TypeError, ValueError):
        code = None

    if code is not None:
        if code == 0 or code == 1:
            return "sunny"
        if code in (2, 3):
            return "cloudy"
        if code in (45, 48):
            return "fog"
        if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            return "rain"
        if code in (71, 73, 75, 77, 85, 86):
            return "snow"
        if code in (95, 96, 99):
            return "storm"

    if any(k in text for k in ("晴", "阳")):
        return "sunny"
    if any(k in text for k in ("云", "阴")):
        return "cloudy"
    if "雾" in text:
        return "fog"
    if any(k in text for k in ("雪",)):
        return "snow"
    if any(k in text for k in ("雷", "暴")):
        return "storm"
    if any(k in text for k in ("雨", "毛毛")):
        return "rain"
    return "cloudy"


class WeatherIconWidget(QWidget):
    """圆形浅蓝底 + 天气符号图案。"""

    def __init__(self, parent=None, size=96):
        super().__init__(parent)
        self._kind = "cloudy"
        self._size = size
        self.setFixedSize(size, size)
        self.setObjectName("weatherIcon")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_kind(self, kind):
        kind = kind or "cloudy"
        if kind == self._kind:
            return
        self._kind = kind
        self.update()

    def set_from_weather(self, condition, weather_code=None):
        self.set_kind(condition_to_icon_kind(condition, weather_code))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 所有绘制、translate、坐标变换代码写在这里
        w, h = self.width(), self.height()
        margin = 4
        rect = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)

        grad = QRadialGradient(rect.center(), rect.width() / 2)
        grad.setColorAt(0, QColor("#ffffff"))
        grad.setColorAt(1, QColor("#d6e8fb"))
        painter.setPen(QPen(QColor(COLOR_PRIMARY), 2))
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(rect)

        cx, cy = rect.center().x(), rect.center().y()
        kind = self._kind

        if kind == "sunny":
            self._draw_sunny(painter, cx, cy, rect.width())
        elif kind == "rain":
            self._draw_rain(painter, cx, cy, rect.width())
        elif kind == "snow":
            self._draw_snow(painter, cx, cy, rect.width())
        elif kind == "storm":
            self._draw_storm(painter, cx, cy, rect.width())
        elif kind == "fog":
            self._draw_fog(painter, cx, cy, rect.width())
        else:
            self._draw_cloudy(painter, cx, cy, rect.width())

    def _draw_sunny(self, p, cx, cy, d):
        r = d * 0.18
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#f0b429"))
        p.drawEllipse(QPointF(cx, cy), r, r)
        pen = QPen(QColor("#f0b429"), max(2, int(d * 0.04)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for i in range(8):
            a = i * pi / 4
            x1 = cx + cos(a) * r * 1.35
            y1 = cy + sin(a) * r * 1.35
            x2 = cx + cos(a) * r * 1.85
            y2 = cy + sin(a) * r * 1.85
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_cloudy(self, p, cx, cy, d):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#9bb8d9"))
        p.drawEllipse(QPointF(cx - d * 0.12, cy + d * 0.02), d * 0.16, d * 0.14)
        p.drawEllipse(QPointF(cx + d * 0.08, cy), d * 0.2, d * 0.16)
        p.drawEllipse(QPointF(cx - d * 0.02, cy - d * 0.08), d * 0.15, d * 0.13)
        p.setBrush(QColor("#c5d8ef"))
        p.drawEllipse(QPointF(cx + d * 0.02, cy + d * 0.06), d * 0.22, d * 0.12)

    def _draw_rain(self, p, cx, cy, d):
        self._draw_cloudy(p, cx, cy - d * 0.08, d * 0.9)
        pen = QPen(QColor(COLOR_PRIMARY), max(2, int(d * 0.035)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for dx in (-0.12, 0, 0.12):
            x = cx + d * dx
            y0 = cy + d * 0.12
            p.drawLine(QPointF(x, y0), QPointF(x - d * 0.04, y0 + d * 0.16))

    def _draw_snow(self, p, cx, cy, d):
        self._draw_cloudy(p, cx, cy - d * 0.1, d * 0.85)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        for dx, dy in ((-0.1, 0.14), (0.02, 0.2), (0.12, 0.12)):
            p.drawEllipse(QPointF(cx + d * dx, cy + d * dy), d * 0.035, d * 0.035)

    def _draw_storm(self, p, cx, cy, d):
        self._draw_cloudy(p, cx, cy - d * 0.1, d * 0.9)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#f0b429"))
        bolt = QPolygonF([
            QPointF(cx + d * 0.02, cy + d * 0.02),
            QPointF(cx - d * 0.06, cy + d * 0.14),
            QPointF(cx + d * 0.0, cy + d * 0.14),
            QPointF(cx - d * 0.04, cy + d * 0.28),
            QPointF(cx + d * 0.1, cy + d * 0.1),
            QPointF(cx + d * 0.02, cy + d * 0.1),
        ])
        p.drawPolygon(bolt)

    def _draw_fog(self, p, cx, cy, d):
        pen = QPen(QColor("#8aa4c2"), max(2, int(d * 0.045)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for i, dy in enumerate((-0.12, -0.02, 0.08)):
            y = cy + d * dy
            inset = d * (0.08 + i * 0.02)
            p.drawLine(
                QPointF(cx - d * 0.28 + inset, y),
                QPointF(cx + d * 0.28 - inset, y),
            )
