from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = PROJECT_ROOT / "desktop" / "assets"
ICONSET_DIR = ASSET_DIR / "icon.iconset"

ICON_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def draw_icon(size: int) -> Image.Image:
    scale = size / 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def xy(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return tuple(round(value * scale) for value in values)  # type: ignore[return-value]

    radius = round(180 * scale)
    draw.rounded_rectangle(xy((64, 64, 960, 960)), radius=radius, fill=(255, 79, 86, 255))
    draw.rounded_rectangle(xy((126, 126, 898, 898)), radius=round(138 * scale), outline=(255, 255, 255, 70), width=max(2, round(18 * scale)))

    # Server body
    draw.rounded_rectangle(xy((250, 244, 774, 602)), radius=round(44 * scale), fill=(255, 255, 255, 245))
    draw.rounded_rectangle(xy((306, 306, 718, 370)), radius=round(24 * scale), fill=(44, 55, 72, 255))
    draw.rounded_rectangle(xy((306, 424, 718, 488)), radius=round(24 * scale), fill=(44, 55, 72, 255))

    for cx, cy in ((354, 338), (354, 456)):
        draw.ellipse(xy((cx - 13, cy - 13, cx + 13, cy + 13)), fill=(75, 216, 137, 255))

    # Reality routing nodes
    center = (512, 712)
    nodes = [(346, 690), (512, 784), (678, 690)]
    line_width = max(5, round(22 * scale))
    for node in nodes:
        draw.line(
            (round(center[0] * scale), round(center[1] * scale), round(node[0] * scale), round(node[1] * scale)),
            fill=(255, 255, 255, 230),
            width=line_width,
        )
    draw.ellipse(xy((464, 664, 560, 760)), fill=(44, 55, 72, 255))
    for cx, cy in nodes:
        draw.ellipse(xy((cx - 46, cy - 46, cx + 46, cy + 46)), fill=(255, 255, 255, 245))
        draw.ellipse(xy((cx - 20, cy - 20, cx + 20, cy + 20)), fill=(44, 55, 72, 255))

    return image


def save_iconset(base: Image.Image) -> None:
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True)
    size_map = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for file_name, size in size_map.items():
        base.resize((size, size), Image.Resampling.LANCZOS).save(ICONSET_DIR / file_name)


def build_icns() -> None:
    if not shutil.which("iconutil"):
        return
    subprocess.run(
        ["iconutil", "-c", "icns", str(ICONSET_DIR), "-o", str(ASSET_DIR / "icon.icns")],
        check=True,
        cwd=PROJECT_ROOT,
    )


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    base = draw_icon(1024)
    base.save(ASSET_DIR / "icon.png")
    base.save(ASSET_DIR / "icon.ico", sizes=[(size, size) for size in ICON_SIZES if size <= 256])
    save_iconset(base)
    build_icns()
    print(ASSET_DIR)


if __name__ == "__main__":
    main()
