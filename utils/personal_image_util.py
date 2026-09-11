# -*- coding: utf-8 -*-
"""个人日记图片附件：独立目录 personal_images，与班级日志隔离。"""

from __future__ import annotations

import re
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImageReader

ROOT_DIR = Path(__file__).resolve().parent.parent
PERSONAL_IMAGES_DIRNAME = "personal_images"
PERSONAL_IMAGES_DIR = ROOT_DIR / PERSONAL_IMAGES_DIRNAME

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_EXT = {".png", ".jpg", ".jpeg"}
_MAX_DECODE_EDGE = 2560
_THUMB_EDGE = 48


def ensure_personal_images_dir() -> Path:
    PERSONAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    return PERSONAL_IMAGES_DIR


def normalize_image_path(raw) -> str:
    if raw is None:
        return ""
    return str(raw).strip().replace("\\", "/")


def absolute_image_path(rel_path: str) -> Path | None:
    rel = normalize_image_path(rel_path)
    if not rel:
        return None
    candidate = (ROOT_DIR / rel).resolve()
    try:
        candidate.relative_to(PERSONAL_IMAGES_DIR.resolve())
    except ValueError:
        candidate = (PERSONAL_IMAGES_DIR / Path(rel).name).resolve()
        try:
            candidate.relative_to(PERSONAL_IMAGES_DIR.resolve())
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
        raise ValueError("图片过大（上限 5MB），请压缩后再上传")
    reader = QImageReader(str(path))
    if not reader.canRead():
        raise ValueError("无法识别该图片文件")
    return str(path.resolve())


def save_personal_image(source_abs: str | Path) -> str:
    src = Path(validate_image_file(source_abs))
    ensure_personal_images_dir()
    stamp = time.strftime("%Y%m%d%H%M%S")
    dest_name = f"{stamp}_{_safe_basename(src.name)}"
    dest = PERSONAL_IMAGES_DIR / dest_name

    pix = load_pixmap_limited(str(src), max_edge=_MAX_DECODE_EDGE)
    if pix.isNull():
        raise ValueError("图片加载失败")
    ext = dest.suffix.lower()
    fmt = "PNG" if ext == ".png" else "JPEG"
    quality = 88 if fmt == "JPEG" else -1
    if not pix.save(str(dest), fmt, quality):
        dest.write_bytes(src.read_bytes())
    return f"{PERSONAL_IMAGES_DIRNAME}/{dest_name}".replace("\\", "/")


def delete_personal_image(rel_path: str) -> None:
    path = absolute_image_path(rel_path)
    if path and path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


def load_pixmap_limited(abs_or_rel: str, max_edge: int = _MAX_DECODE_EDGE) -> QPixmap:
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
        pix = QPixmap(str(path))
        if pix.isNull() or max_edge <= 0:
            return pix
        return pix.scaled(
            max_edge, max_edge,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return QPixmap.fromImage(image)


def load_thumbnail(rel_path: str, edge: int = _THUMB_EDGE) -> QPixmap:
    pix = load_pixmap_limited(rel_path, max_edge=max(edge * 2, 96))
    if pix.isNull():
        return pix
    return pix.scaled(
        edge, edge,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
