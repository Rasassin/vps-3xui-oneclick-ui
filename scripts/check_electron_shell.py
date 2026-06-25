from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"electron shell check failed: {message}")


def main() -> int:
    package_path = PROJECT_ROOT / "package.json"
    main_path = PROJECT_ROOT / "electron" / "main.js"
    if not package_path.exists():
        fail("missing package.json")
    if not main_path.exists():
        fail("missing electron/main.js")

    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("main") != "electron/main.js":
        fail("package.json main must be electron/main.js")
    scripts = package.get("scripts", {})
    for name in (
        "electron:dev",
        "electron:build:mac",
        "electron:package:mac",
        "electron:release:mac",
        "electron:build:win",
        "electron:package:win",
        "electron:release:win",
        "electron:sign:win",
    ):
        if name not in scripts:
            fail(f"missing npm script: {name}")
    if "build_electron_bundle_macos.py" not in scripts["electron:build:mac"]:
        fail("electron:build:mac must use the deterministic macOS bundle builder")
    if "package_electron_macos.py" not in scripts["electron:package:mac"]:
        fail("electron:package:mac must use the macOS release packager")
    if "build_electron_bundle_windows.py" not in scripts["electron:build:win"]:
        fail("electron:build:win must use the deterministic Windows bundle builder")
    if "package_electron_windows.py" not in scripts["electron:package:win"]:
        fail("electron:package:win must use the Windows release packager")
    if "sign_electron_windows.ps1" not in scripts["electron:sign:win"]:
        fail("electron:sign:win must use the Windows signing helper")
    if "electron-builder" in json.dumps(package, ensure_ascii=False):
        fail("package.json should use the deterministic bundle scripts instead of electron-builder")

    main_text = main_path.read_text(encoding="utf-8")
    required_markers = [
        "nodeIntegration: false",
        "contextIsolation: true",
        "sandbox: true",
        "bundledSidecarExecutable",
        "--vps-3xui-streamlit-child",
        "VPS_3XUI_OPEN_BROWSER",
        "streamlit",
        "app.getPath(\"userData\")",
        "does not connect to a VPS",
    ]
    for marker in required_markers:
        if marker not in main_text:
            fail(f"electron/main.js missing marker: {marker}")

    print("electron shell check ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
