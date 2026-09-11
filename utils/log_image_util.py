# -*- coding: utf-8 -*-
"""班级日志图片附件：目录、存取、压缩加载。"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImageReader

# 项目根目录（utils 的上一级）
ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_IMAGES_DIRNAME = "log_images"
LOG_IMAGES_DIR = ROOT_DIR / LOG_IMAGES_DIRNAME

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_EXT = {".png", ".jpg", ".jpeg"}

# 预览/缩略图解码上限，避免超大图占满内存
_MAX_DECODE_EDGE = 2560
_THUMB_EDGE = 48


def ensure_log_images_dir() -> Path:
    """确保 log_images 目录存在，返回绝对路径。"""
    LOG_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_IMAGES_DIR


def normalize_image_path(raw) -> str:
    """规范化库内相对路径；空 / None -> ''。"""
    if raw is None:
        return ""
    text = str(raw).strip().replace("\\", "/")
    return text


def absolute_image_path(rel_path: str) -> Path | None:
    """相对路径 -> 绝对 Path；无效则 None。"""
    rel = normalize_image_path(rel_path)
    if not rel:
        return None
    # 仅允许落在 log_images 下
    candidate = (ROOT_DIR / rel).resolve()
    try:
        candidate.relative_to(LOG_IMAGES_DIR.resolve())
    except ValueError:
        # 兼容只存了文件名的旧写法
        candidate = (LOG_IMAGES_DIR / Path(rel).name).resolve()
        try:
            candidate.relative_to(LOG_IMAGES_DIR.resolve())
        except ValueError:
            return None
    return candidate


def image_file_exists(rel_path: str) -> bool:
    path = absolute_image_path(rel_path)
    return bool(path and path.is_file())


def _safe_basename(filename: str) -> str:
    name = Path(filename).name
    stem = Path(name).stem
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXT:
        ext = ".jpg"
    stem = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", stem, flags=re.UNICODE).strip("._")
    if not stem:
        stem = "image"
    return f"{stem}{ext}"


def validate_image_file(abs_path: str | Path) -> str:
    """
    校验本地图片；通过返回绝对路径字符串，否则抛 ValueError（友好文案）。
    """
    path = Path(abs_path)
    if not path.is_file():
        raise ValueError("所选文件不存在")
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("仅支持 .png / .jpg / .jpeg 格式")
    size = path.stat().st_size
    if size <= 0:
        raise ValueError("图片文件无效")
    if size > MAX_IMAGE_BYTES:
        mb = MAX_IMAGE_BYTES / (1024 * 1024)
        raise ValueError(f"图片过大（上限 {mb:.0f}MB），请压缩后再上传")
    # 可读性探测
    reader = QImageReader(str(path))
    if not reader.canRead():
        raise ValueError("无法识别该图片文件")
    return str(path.resolve())


def save_log_image(source_abs: str | Path) -> str:
    """
    将本地图片复制到 log_images（时间戳+原文件名），返回相对路径（正斜杠）。
    过大边长会按比例缩放后再保存，降低磁盘与内存占用。
    """
    src = Path(validate_image_file(source_abs))
    ensure_log_images_dir()
    stamp = time.strftime("%Y%m%d%H%M%S")
    dest_name = f"{stamp}_{_safe_basename(src.name)}"
    dest = LOG_IMAGES_DIR / dest_name

    pix = load_pixmap_limited(str(src), max_edge=_MAX_DECODE_EDGE)
    if pix.isNull():
        raise ValueError("图片加载失败")
    # 按扩展名保存
    ext = dest.suffix.lower()
    fmt = "PNG" if ext == ".png" else "JPEG"
    quality = 88 if fmt == "JPEG" else -1
    if not pix.save(str(dest), fmt, quality):
        # 回退为直接复制
        dest.write_bytes(src.read_bytes())

    rel = f"{LOG_IMAGES_DIRNAME}/{dest_name}".replace("\\", "/")
    return rel


def delete_log_image(rel_path: str) -> None:
    """删除本地图片文件（忽略不存在）。"""
    path = absolute_image_path(rel_path)
    if path and path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


def load_pixmap_limited(abs_or_rel: str, max_edge: int = _MAX_DECODE_EDGE) -> QPixmap:
    """
    加载图片并限制最长边，避免大图解码占满内存。
    可传绝对路径或库内相对路径。
    """
    text = str(abs_or_rel or "").strip()
    if not text:
        return QPixmap()
    path = Path(text)
    if not path.is_file():
        resolved = absolute_image_path(text)
        path = resolved if resolved else path
    if not path or not path.is_file():
        return QPixmap()

    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and max_edge > 0:
        w, h = size.width(), size.height()
        long_edge = max(w, h)
        if long_edge > max_edge:
            scale = max_edge / float(long_edge)
            reader.setScaledSize(QSize(int(w * scale), int(h * scale)))
    image = reader.read()
    if image.isNull():
        # 回退
        pix = QPixmap(str(path))
        if pix.isNull() or max_edge <= 0:
            return pix
        return _scale_pixmap(pix, max_edge)
    return QPixmap.fromImage(image)


def load_thumbnail(rel_path: str, edge: int = _THUMB_EDGE) -> QPixmap:
    """卡片用极小缩略图。"""
    pix = load_pixmap_limited(rel_path, max_edge=max(edge * 2, 96))
    if pix.isNull():
        return pix
    return pix.scaled(
        edge,
        edge,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _scale_pixmap(pix: QPixmap, max_edge: int) -> QPixmap:
    if pix.isNull() or max_edge <= 0:
        return pix
    if max(pix.width(), pix.height()) <= max_edge:
        return pix
    return pix.scaled(
        max_edge,
        max_edge,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
