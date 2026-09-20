# -*- coding: utf-8 -*-
"""课程笔记图片：独立目录 course_images，不与日志 / 个人图片混用。"""

from __future__ import annotations

import html as html_lib
import re
import time
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QImageReader, QPixmap

ROOT_DIR = Path(__file__).resolve().parent.parent
COURSE_IMAGES_DIRNAME = "course_images"
COURSE_IMAGES_DIR = ROOT_DIR / COURSE_IMAGES_DIRNAME

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_EXT = {".png", ".jpg", ".jpeg"}
_MAX_DECODE_EDGE = 2560

_IMG_SRC = re.compile(
    r'(<img\b[^>]*?\bsrc\s*=\s*")([^"]*)(")',
    re.IGNORECASE,
)


def ensure_course_images_dir() -> Path:
    COURSE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    return COURSE_IMAGES_DIR


def absolute_image_path(rel_path: str) -> Path | None:
    rel = str(rel_path or "").strip().replace("\\", "/")
    if not rel:
        return None
    candidate = (ROOT_DIR / rel).resolve()
    try:
        candidate.relative_to(COURSE_IMAGES_DIR.resolve())
    except ValueError:
        candidate = (COURSE_IMAGES_DIR / Path(rel).name).resolve()
        try:
            candidate.relative_to(COURSE_IMAGES_DIR.resolve())
        except ValueError:
            return None
    return candidate


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
        raise ValueError("仅支持 png / jpg 图片")
    size = path.stat().st_size
    if size <= 0:
        raise ValueError("图片文件无效")
    if size > MAX_IMAGE_BYTES:
        raise ValueError("图片过大（上限 5MB）")
    reader = QImageReader(str(path))
    if not reader.canRead():
        raise ValueError("无法识别该图片文件")
    return str(path.resolve())


def load_pixmap_limited(abs_path: str | Path, max_edge: int = _MAX_DECODE_EDGE) -> QPixmap:
    path = Path(abs_path)
    if not path.is_file():
        return QPixmap()
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and max_edge > 0:
        w, h = size.width(), size.height()
        long_edge = max(w, h)
        if long_edge > max_edge:
            scale = max_edge / float(long_edge)
            reader.setScaledSize(QSize(max(1, int(w * scale)), max(1, int(h * scale))))
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


def save_course_image(source_abs: str | Path) -> str:
    """复制图片到 course_images，返回相对路径 course_images/xxx。"""
    src = Path(validate_image_file(source_abs))
    ensure_course_images_dir()
    stamp = time.strftime("%Y%m%d%H%M%S")
    dest_name = f"{stamp}_{_safe_basename(src.name)}"
    dest = COURSE_IMAGES_DIR / dest_name
    pix = load_pixmap_limited(src, max_edge=_MAX_DECODE_EDGE)
    if pix.isNull():
        raise ValueError("图片加载失败")
    ext = dest.suffix.lower()
    fmt = "PNG" if ext == ".png" else "JPEG"
    quality = 88 if fmt == "JPEG" else -1
    if not pix.save(str(dest), fmt, quality):
        dest.write_bytes(src.read_bytes())
    return f"{COURSE_IMAGES_DIRNAME}/{dest_name}"


def _to_storage_src(src: str) -> str | None:
    text = html_lib.unescape(str(src or "").strip())
    if text.startswith("course_images/"):
        return text
    url = QUrl(text)
    local = url.toLocalFile() if url.isLocalFile() else ""
    if not local:
        return None
    path = Path(local).resolve()
    try:
        path.relative_to(COURSE_IMAGES_DIR.resolve())
    except ValueError:
        return None
    return f"{COURSE_IMAGES_DIRNAME}/{path.name}"


def html_for_storage(raw_html: str) -> str:
    """把编辑器里的本地图片地址改成 course_images 相对路径再入库。"""
    def repl(match):
        rel = _to_storage_src(match.group(2))
        if not rel:
            return match.group(0)
        return f"{match.group(1)}{rel}{match.group(3)}"

    return _IMG_SRC.sub(repl, raw_html or "")


def html_for_display(stored_html: str) -> str:
    """把库内相对路径还原成本地 file URL，供编辑器显示。"""
    def repl(match):
        src = html_lib.unescape(match.group(2)).replace("\\", "/")
        if not src.startswith("course_images/"):
            return match.group(0)
        path = absolute_image_path(src)
        if not path or not path.is_file():
            return match.group(0)
        url = QUrl.fromLocalFile(str(path)).toString()
        return f"{match.group(1)}{url}{match.group(3)}"

    return _IMG_SRC.sub(repl, stored_html or "")
