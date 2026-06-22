from __future__ import annotations

from pathlib import Path

import qrcode

from .config import OUTPUT_DIR
from .result_parser import load_results


def make_qr_png(data: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = qrcode.make(data)
    img.save(path)
    return path


def regenerate_output_qrs(output_dir: Path = OUTPUT_DIR) -> list[Path]:
    results = load_results(output_dir)
    regenerated: list[Path] = []
    vless_link = results.get("vless_link", "")
    subscription_link = results.get("subscription_link", "")
    if vless_link:
        regenerated.append(make_qr_png(vless_link, output_dir / "vless-qr.png"))
    if subscription_link:
        regenerated.append(make_qr_png(subscription_link, output_dir / "subscription-qr.png"))
    return regenerated
