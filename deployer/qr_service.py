from __future__ import annotations

from pathlib import Path

import qrcode


def make_qr_png(data: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = qrcode.make(data)
    img.save(path)
    return path

