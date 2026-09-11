# -*- coding: utf-8 -*-
"""个人模式 PIN：本地加密存储（SHA-256 + salt），不入业务库。"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PIN_FILE = ROOT_DIR / "data" / "personal_pin.json"


def _ensure_parent():
    PIN_FILE.parent.mkdir(parents=True, exist_ok=True)


def has_pin() -> bool:
    data = _load()
    return bool(data.get("salt") and data.get("hash"))


def _load() -> dict:
    if not PIN_FILE.is_file():
        return {}
    try:
        with open(PIN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def _save(data: dict) -> None:
    _ensure_parent()
    tmp = PIN_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PIN_FILE)


def _hash_pin(pin: str, salt: str) -> str:
    raw = f"{salt}:{pin}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_pin_format(pin: str) -> str:
    pin = (pin or "").strip()
    if not pin.isdigit():
        raise ValueError("PIN 码须为纯数字")
    if len(pin) < 4 or len(pin) > 6:
        raise ValueError("PIN 码须为 4~6 位数字")
    return pin


def set_pin(pin: str) -> None:
    pin = validate_pin_format(pin)
    salt = secrets.token_hex(16)
    _save({"salt": salt, "hash": _hash_pin(pin, salt)})


def verify_pin(pin: str) -> bool:
    data = _load()
    salt = data.get("salt") or ""
    expected = data.get("hash") or ""
    if not salt or not expected:
        return False
    try:
        pin = validate_pin_format(pin)
    except ValueError:
        return False
    return secrets.compare_digest(_hash_pin(pin, salt), expected)


def change_pin(old_pin: str, new_pin: str) -> None:
    """验证旧 PIN 后写入新 PIN；失败抛 ValueError。"""
    if not has_pin():
        raise ValueError("尚未设置 PIN，请先设置")
    if not verify_pin(old_pin):
        raise ValueError("旧 PIN 码错误")
    new_pin = validate_pin_format(new_pin)
    if old_pin.strip() == new_pin:
        raise ValueError("新 PIN 不能与旧 PIN 相同")
    set_pin(new_pin)


def clear_pin() -> None:
    if PIN_FILE.is_file():
        try:
            PIN_FILE.unlink()
        except OSError:
            pass
