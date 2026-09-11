# -*- coding: utf-8 -*-
"""感触随笔：手写字体解析。"""

from __future__ import annotations

from PyQt6.QtGui import QFont, QFontDatabase

_HAND_CANDIDATES = (
    "站酷快乐体",
    "HappyZcool-2016",
    "ZCOOL KuaiLe",
    "站酷快乐手写",
    "Microsoft YaHei",
    "微软雅黑",
)
_resolved: str | None = None


def handwriting_font(point_size: int = 13, bold: bool = False) -> QFont:
    global _resolved
    if _resolved is None:
        try:
            available = set(QFontDatabase.families())
        except Exception:
            available = set()
        for name in _HAND_CANDIDATES:
            if name in available:
                _resolved = name
                break
        if _resolved is None:
            _resolved = "Microsoft YaHei"
    font = QFont(_resolved)
    font.setPointSize(point_size)
    font.setBold(bold)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font
