# -*- coding: utf-8 -*-
"""
IP 公网定位工具：通过公网 IP 解析城市（不使用 GPS）。
请求在调用方 QThread 中执行，本模块仅提供同步函数。
"""

import json
import urllib.error
import urllib.request

# 默认备用城市（定位失败时使用）
DEFAULT_CITY = "杭州"

REQUEST_TIMEOUT = 10

# 多个免费 IP 定位源，按序尝试
_IP_API_URLS = [
    "http://ip-api.com/json/?lang=zh-CN&fields=status,message,country,regionName,city,query",
    "https://ipapi.co/json/",
]


def _http_get_json(url, timeout=REQUEST_TIMEOUT):
    """发起 GET 并解析 JSON；超时转为 TimeoutError。"""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ClassManager/1.0 (weather-location)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except Exception as e:
        msg = str(e).lower()
        if "timed out" in msg or "timeout" in msg:
            raise TimeoutError(f"IP 定位超时（{timeout}s）") from e
        raise



def _parse_ip_api(data):
    if not isinstance(data, dict):
        return None
    if data.get("status") == "fail":
        return None
    city = (data.get("city") or "").strip()
    if not city:
        return None
    return {
        "city": city,
        "region": (data.get("regionName") or "").strip(),
        "country": (data.get("country") or "").strip(),
        "ip": (data.get("query") or "").strip(),
        "source": "ip-api",
    }


def _parse_ipapi_co(data):
    if not isinstance(data, dict):
        return None
    if data.get("error"):
        return None
    city = (data.get("city") or "").strip()
    if not city:
        return None
    return {
        "city": city,
        "region": (data.get("region") or "").strip(),
        "country": (data.get("country_name") or data.get("country") or "").strip(),
        "ip": (data.get("ip") or "").strip(),
        "source": "ipapi.co",
    }


def locate_city_by_ip(timeout=REQUEST_TIMEOUT):
    """
    通过公网 IP 解析当前城市。
    :return: dict {city, region, country, ip, source}
    :raises: Exception 全部源失败时抛出（调用方捕获后使用默认城市）
    """
    errors = []
    for url in _IP_API_URLS:
        try:
            data = _http_get_json(url, timeout=timeout)
            if "ip-api.com" in url:
                result = _parse_ip_api(data)
            else:
                result = _parse_ipapi_co(data)
            if result and result.get("city"):
                return result
            errors.append(f"{url}: 无城市字段")
        except Exception as e:
            errors.append(f"{url}: {e}")

    raise RuntimeError("IP 定位失败: " + " | ".join(errors))


def locate_city_or_default(timeout=REQUEST_TIMEOUT):
    """
    定位成功返回城市名；失败返回默认备用城市。
    :return: (city_name: str, from_ip: bool, detail: dict|None)
    """
    try:
        detail = locate_city_by_ip(timeout=timeout)
        return detail["city"], True, detail
    except Exception as e:
        print(f"[定位] 使用默认城市 {DEFAULT_CITY}，原因: {e}")
        return DEFAULT_CITY, False, None
