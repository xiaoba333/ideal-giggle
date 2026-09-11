# -*- coding: utf-8 -*-
"""
大小窗共享天气状态：避免大屏晴 / 小窗雨各自定位导致图标不一致。
仅内存，不落盘。
"""

from __future__ import annotations

from threading import Lock

_lock = Lock()
_last_weather: dict | None = None
_preferred_city: str | None = None  # 最近一次成功查询用的城市名


def get_last_weather() -> dict | None:
    with _lock:
        return dict(_last_weather) if _last_weather else None


def set_last_weather(data: dict | None):
    global _last_weather, _preferred_city
    with _lock:
        if not isinstance(data, dict) or not data:
            return
        _last_weather = dict(data)
        city = (data.get("query_city") or data.get("city") or "").strip()
        if city:
            # query_city 优先（用户输入/定位原始名），避免展示名「省 · 市」干扰地理编码
            q = (data.get("query_city") or "").strip()
            _preferred_city = q or city.split("·")[-1].strip() or city


def get_preferred_city() -> str | None:
    with _lock:
        return _preferred_city


def set_preferred_city(city: str | None):
    global _preferred_city
    with _lock:
        city = (city or "").strip() or None
        _preferred_city = city


def clear_preferred_city():
    global _preferred_city
    with _lock:
        _preferred_city = None
