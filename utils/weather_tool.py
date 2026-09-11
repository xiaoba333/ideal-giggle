# -*- coding: utf-8 -*-
"""
天气接口工具：城市地理编码 + 实况天气（Open-Meteo，免 Key）。
仅内存短时缓存天气数据；禁止持久化「查询城市」。
供 QThread 调用。
"""

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from threading import Lock

from utils.location_tool import DEFAULT_CITY, REQUEST_TIMEOUT

# WMO 天气代码 → 中文简述
_WMO_WEATHER = {
    0: "晴",
    1: "大体晴",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "强毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴冰雹",
    99: "强雷暴冰雹",
}

# 短时缓存：同一城市 N 秒内不重复请求（仅天气数据，不含「目标城市」配置）
_CACHE_TTL_SEC = 120
_cache = {}
_cache_lock = Lock()


def _http_get_json(url, timeout=REQUEST_TIMEOUT):
    """
    GET JSON；超时与网络异常转为明确错误，便于 UI 展示。
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ClassManager/1.0 (weather)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except socket.timeout as e:
        raise TimeoutError(f"连接超时（{timeout}s）") from e
    except TimeoutError as e:
        raise TimeoutError(f"连接超时（{timeout}s）") from e
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, socket.timeout):
            raise TimeoutError(f"连接超时（{timeout}s）") from e
        if isinstance(reason, TimeoutError):
            raise TimeoutError(f"连接超时（{timeout}s）") from e
        msg = str(reason or e)
        if "timed out" in msg.lower():
            raise TimeoutError(f"连接超时（{timeout}s）") from e
        raise RuntimeError(f"网络错误：{msg}") from e
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}") from e


def clear_weather_cache(city=None):
    """清除天气缓存；city 为 None 时清空全部。不涉及任何城市偏好文件。"""
    with _cache_lock:
        if city is None:
            _cache.clear()
        else:
            _cache.pop(city.strip(), None)


def weather_code_to_text(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "未知"
    return _WMO_WEATHER.get(code, f"天气代码{code}")


def geocode_city(city_name, timeout=REQUEST_TIMEOUT):
    """
    将中文城市名解析为经纬度。
    :return: {name, latitude, longitude, country, admin1}
    """
    city_name = (city_name or "").strip()
    if not city_name:
        raise ValueError("城市名称不能为空")

    query = urllib.parse.urlencode({
        "name": city_name,
        "count": 1,
        "language": "zh",
        "format": "json",
    })
    url = f"https://geocoding-api.open-meteo.com/v1/search?{query}"
    data = _http_get_json(url, timeout=timeout)
    results = (data or {}).get("results") or []
    if not results:
        raise RuntimeError(f"未找到城市「{city_name}」，请检查名称")

    item = results[0]
    return {
        "name": item.get("name") or city_name,
        "latitude": float(item["latitude"]),
        "longitude": float(item["longitude"]),
        "country": item.get("country") or "",
        "admin1": item.get("admin1") or "",
    }


def fetch_current_weather(latitude, longitude, timeout=REQUEST_TIMEOUT):
    """按经纬度拉取当前天气。"""
    query = urllib.parse.urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
        "wind_speed_unit": "kmh",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{query}"
    data = _http_get_json(url, timeout=timeout)
    current = (data or {}).get("current")
    if not current:
        raise RuntimeError("天气接口未返回实况数据")

    code = current.get("weather_code")
    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    wind = current.get("wind_speed_10m")

    return {
        "condition": weather_code_to_text(code),
        "temperature": None if temp is None else f"{round(float(temp))}℃",
        "humidity": None if humidity is None else f"{int(humidity)}%",
        "wind": None if wind is None else f"{round(float(wind), 1)} km/h",
        "weather_code": code,
        "raw": current,
    }


def get_weather_by_city(city_name, timeout=REQUEST_TIMEOUT, use_cache=True):
    """
    按城市名查询天气（仅内存短时缓存天气结果）。
    失败时不回退到任何「历史搜索城市」。
    """
    city_name = (city_name or "").strip() or DEFAULT_CITY
    cache_key = city_name

    if use_cache:
        with _cache_lock:
            hit = _cache.get(cache_key)
            if hit and (time.time() - hit["ts"] < _CACHE_TTL_SEC):
                result = dict(hit["data"])
                result["from_cache"] = True
                return result

    geo = geocode_city(city_name, timeout=timeout)
    weather = fetch_current_weather(geo["latitude"], geo["longitude"], timeout=timeout)

    display_city = geo["name"]
    if geo.get("admin1") and geo["admin1"] not in display_city:
        display_city = f"{geo['admin1']} · {geo['name']}"

    result = {
        "city": display_city,
        "query_city": city_name,
        "condition": weather["condition"],
        "temperature": weather["temperature"] or "--℃",
        "humidity": weather["humidity"] or "--%",
        "wind": weather["wind"] or "--",
        "weather_code": weather.get("weather_code"),
        "from_cache": False,
    }

    with _cache_lock:
        _cache[cache_key] = {"ts": time.time(), "data": dict(result)}

    return result
