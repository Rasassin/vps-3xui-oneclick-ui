from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from importlib.util import find_spec
from pathlib import Path


APP_NAME = "VPS 3x-ui Oneclick"
DEFAULT_PORT = 8501
LAUNCH_LOG = "desktop-launcher.log"


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


def check_runtime_dependencies() -> list[str]:
    missing = []
    for module_name in ["streamlit", "paramiko", "qrcode", "PIL"]:
        if find_spec(module_name) is None:
            missing.append(module_name)
    return missing


def launcher_log_path(root: Path) -> Path:
    output_dir = root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / LAUNCH_LOG


def main() -> int:
    root = resource_root()
    app_path = root / "app.py"
    if not app_path.exists():
        print(f"{APP_NAME} 启动失败：找不到 app.py。")
        return 1

    missing = check_runtime_dependencies()
    if missing:
        print(f"{APP_NAME} 启动失败：缺少 Python 依赖：{', '.join(missing)}")
        print("请先执行：python -m pip install -r requirements.txt")
        return 1

    port = find_free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    command = build_streamlit_command(root, port)
    log_path = launcher_log_path(root)
    log_file = log_path.open("a", encoding="utf-8")
    log_file.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] starting {APP_NAME}\n")
    log_file.flush()
    process = subprocess.Popen(command, cwd=str(root), env=env, stdout=log_file, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"

    try:
        if wait_for_streamlit(port):
            print(f"{APP_NAME} 已启动：{url}")
            print(f"启动日志：{log_path}")
            webbrowser.open(url)
        else:
            print(f"{APP_NAME} 启动超时，请查看日志：{log_path}")
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
    finally:
        log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
