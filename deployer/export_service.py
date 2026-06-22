from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .config import OUTPUT_DIR


EXPORTABLE_FILES = [
    "result.json",
    "vless-link.txt",
    "vless-qr.png",
    "subscription-link.txt",
    "subscription-qr.png",
    "panel-login.txt",
    "deploy-report.txt",
    "preflight-result.json",
    "preflight-report.txt",
]


def build_export_zip(output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_path = output_dir / f"3xui-oneclick-export-{stamp}.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_name in EXPORTABLE_FILES:
            file_path = output_dir / file_name
            if file_path.exists() and file_path.is_file() and file_path.stat().st_size > 0:
                archive.write(file_path, arcname=file_name)
    return zip_path
