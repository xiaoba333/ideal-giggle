# -*- coding: utf-8 -*-
"""日期格式化工具：统一 YYYY-MM-DD。"""

from datetime import date, datetime


DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def format_date(value):
    """
    将 date/datetime/str 格式化为 YYYY-MM-DD。
    None 或空字符串返回空字符串。
    """
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime(DATE_FMT)
    if isinstance(value, date):
        return value.strftime(DATE_FMT)
    text = str(value).strip()
    if not text:
        return ""
    # 截取前 10 位兼容 DATETIME 字符串
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    try:
        return datetime.strptime(text, DATE_FMT).strftime(DATE_FMT)
    except ValueError:
        try:
            return datetime.strptime(text, DATETIME_FMT).strftime(DATE_FMT)
        except ValueError:
            return text


def format_datetime(value):
    """将 date/datetime/str 格式化为 YYYY-MM-DD HH:MM:SS。"""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime(DATETIME_FMT)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day).strftime(DATETIME_FMT)
    text = str(value).strip()
    if not text:
        return ""
    try:
        return datetime.strptime(text, DATETIME_FMT).strftime(DATETIME_FMT)
    except ValueError:
        try:
            d = datetime.strptime(text[:10], DATE_FMT)
            return d.strftime(DATETIME_FMT)
        except ValueError:
            return text


def parse_date(value):
    """
    解析为 date 对象；无效则返回 None。
    空字符串视为 None。
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], DATE_FMT).date()
    except ValueError:
        return None


def today_str():
    """返回今天的 YYYY-MM-DD。"""
    return date.today().strftime(DATE_FMT)
