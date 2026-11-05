"""Validate and store member photos for the local editors."""
import base64
import os
from pathlib import Path
import shutil
import tempfile
import uuid

from build import ROOT, OUT


def store_avatar(encoded):
    if not isinstance(encoded, str):
        raise ValueError("头像格式无效")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValueError("头像格式无效")
    if not 0 < len(raw) <= 2_500_000:
        raise ValueError("头像最大 2.5 MB")
    if raw.startswith(b"\xff\xd8\xff"):
        suffix = "jpg"
    elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
        suffix = "png"
    elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        suffix = "webp"
    else:
        raise ValueError("头像只支持 JPEG、PNG 或 WebP")
    photos = ROOT / "assets/people"
    photos.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex + "." + suffix
    with tempfile.NamedTemporaryFile(dir=photos, delete=False) as temp:
        temp.write(raw)
        temp_name = temp.name
    os.replace(temp_name, photos / name)
    preview = OUT / "assets/people"
    if preview.is_dir():
        shutil.copy2(photos / name, preview / name)
    return "assets/people/" + name
