from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


APP_NAME = "VPS 3x-ui Oneclick"
DEFAULT_PORT = 8501


def resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parent


def find_free_port(start: int = DEFAULT_PORT) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("无法找到可用的本地端口。")


def wait_for_streamlit(port: int, timeout: int = 45) -> bool:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/_stcore/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.read().decode("utf-8", errors="ignore").strip() == "ok":
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    return False


def build_streamlit_command(root: Path, port: int) -> list[str]:
    app_path = root / "app.py"
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--server.fileWatcherType",
        "none",
        "--browser.gatherUsageStats",
        "false",
    ]


def main() -> int:
    root = resource_root()
    app_path = root / "app.py"
    if not app_path.exists():
        print(f"{APP_NAME} 启动失败：找不到 app.py。")
        return 1

    port = find_free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    command = build_streamlit_command(root, port)
    process = subprocess.Popen(command, cwd=str(root), env=env)
    url = f"http://127.0.0.1:{port}"

    try:
        if wait_for_streamlit(port):
            print(f"{APP_NAME} 已启动：{url}")
            webbrowser.open(url)
        else:
            print(f"{APP_NAME} 启动超时，请查看终端输出。")
            return process.poll() or 1

        while process.poll() is None:
            time.sleep(0.5)
        return int(process.returncode or 0)
    except KeyboardInterrupt:
        print("正在关闭本地应用...")
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
