from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import http.client
import urllib.error
import urllib.request
import webbrowser
from importlib.util import find_spec
from pathlib import Path


APP_NAME = "VPS 3x-ui Oneclick"
LAUNCHER_SAFETY_NOTE = "The desktop launcher starts only local Streamlit and does not connect to a VPS."
DEFAULT_PORT = 18501
DEFAULT_HOST = "127.0.0.1"
DEFAULT_TIMEOUT = 120
LAUNCH_LOG = "desktop-launcher.log"
PORT_SCAN_WINDOW = 20
STREAMLIT_CHILD_FLAG = "--vps-3xui-streamlit-child"
CHILD_HOST_ENV = "VPS_3XUI_CHILD_HOST"
CHILD_PORT_ENV = "VPS_3XUI_CHILD_PORT"
REQUIRED_RUNTIME_PATHS = (
    "app.py",
    "deployer",
    "remote_scripts/install_remote.sh",
    "remote_scripts/harden_after_success.sh",
    "output/.gitkeep",
    "data/.gitkeep",
)


def resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parent


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.environ.get(name, "").strip()
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        print(f"{APP_NAME} 启动提示：{name}={raw_value!r} 不是数字，已使用默认值 {default}。")
        return default
    if value < minimum or value > maximum:
        print(f"{APP_NAME} 启动提示：{name}={value} 超出范围，已使用默认值 {default}。")
        return default
    return value


def env_bool(name: str, default: bool = True) -> bool:
    raw_value = os.environ.get(name, "").strip().lower()
    if not raw_value:
        return default
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    print(f"{APP_NAME} 启动提示：{name}={raw_value!r} 无法识别，已使用默认值。")
    return default


def local_host() -> str:
    host = os.environ.get("VPS_3XUI_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    if host not in {"127.0.0.1", "localhost"}:
        print(f"{APP_NAME} 启动提示：VPS_3XUI_HOST 只建议使用 127.0.0.1 或 localhost，已使用默认值。")
        return DEFAULT_HOST
    return host


def find_free_port(host: str, start: int = DEFAULT_PORT) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError("无法找到可用的本地端口。")


def health_check(host: str, port: int) -> bool:
    connection = http.client.HTTPConnection(host, port, timeout=2)
    try:
        connection.request("GET", "/_stcore/health")
        response = connection.getresponse()
        body = response.read().decode("utf-8", errors="ignore").strip()
        return response.status == 200 and body == "ok"
    except (TimeoutError, socket.timeout, OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def wait_for_streamlit(host: str, port: int, timeout: int = DEFAULT_TIMEOUT) -> int | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for candidate_port in range(port, min(port + PORT_SCAN_WINDOW + 1, 65536)):
            if health_check(host, candidate_port):
                return candidate_port
        time.sleep(0.5)
    return None


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def build_streamlit_command(root: Path, host: str, port: int) -> list[str]:
    app_path = root / "app.py"
    if is_frozen_app():
        return [sys.executable, STREAMLIT_CHILD_FLAG]
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--server.fileWatcherType",
        "none",
        "--browser.gatherUsageStats",
        "false",
    ]


def run_streamlit_in_process(root: Path, host: str, port: int) -> int:
    from streamlit.web import bootstrap

    app_path = root / "app.py"
    flag_options = {
        "global.developmentMode": False,
        "server.address": host,
        "server.port": port,
        "server.headless": True,
        "server.fileWatcherType": "none",
        "browser.gatherUsageStats": False,
    }
    bootstrap.load_config_options(flag_options=flag_options)
    bootstrap.run(str(app_path), False, [], flag_options)
    return 0


def run_streamlit_child() -> int:
    root = resource_root()
    host = os.environ.get(CHILD_HOST_ENV, DEFAULT_HOST)
    port = env_int(CHILD_PORT_ENV, DEFAULT_PORT, 1024, 65535)
    return run_streamlit_in_process(root, host, port)


def check_runtime_dependencies() -> list[str]:
    missing = []
    for module_name in ["streamlit", "paramiko", "qrcode", "PIL"]:
        if find_spec(module_name) is None:
            missing.append(module_name)
    return missing


def validate_runtime_files(root: Path) -> list[str]:
    missing = []
    for relative in REQUIRED_RUNTIME_PATHS:
        if not (root / relative).exists():
            missing.append(relative)
    return missing


def launcher_log_path(root: Path) -> Path:
    if is_frozen_app():
        if sys.platform == "darwin":
            output_dir = Path.home() / "Library" / "Application Support" / APP_NAME / "logs"
        elif sys.platform.startswith("win"):
            output_dir = Path.home() / "AppData" / "Local" / APP_NAME / "logs"
        else:
            output_dir = Path.home() / ".local" / "share" / "vps-3xui-oneclick-ui" / "logs"
    else:
        output_dir = root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / LAUNCH_LOG


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()


def tail_text(path: Path, lines: int = 40) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])


def announce(message: str, log_file: object | None = None) -> None:
    print(message, flush=True)
    if log_file is not None:
        log_file.write(f"{message}\n")
        log_file.flush()


def main() -> int:
    if STREAMLIT_CHILD_FLAG in sys.argv:
        return run_streamlit_child()

    root = resource_root()
    app_path = root / "app.py"
    if not app_path.exists():
        print(f"{APP_NAME} 启动失败：找不到 app.py。")
        return 1

    missing_files = validate_runtime_files(root)
    if missing_files:
        print(f"{APP_NAME} 启动失败：运行文件不完整：{', '.join(missing_files)}")
        print("请重新下载完整的 portable 包或源码包。")
        return 1

    missing = check_runtime_dependencies()
    if missing:
        print(f"{APP_NAME} 启动失败：缺少 Python 依赖：{', '.join(missing)}")
        print("请先执行：python -m pip install -r requirements.txt")
        return 1

    host = local_host()
    start_port = env_int("VPS_3XUI_PORT", DEFAULT_PORT, 1024, 65535)
    timeout = env_int("VPS_3XUI_START_TIMEOUT", DEFAULT_TIMEOUT, 5, 300)
    open_browser = env_bool("VPS_3XUI_OPEN_BROWSER", True)
    port = find_free_port(host, start_port)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env[CHILD_HOST_ENV] = host
    env[CHILD_PORT_ENV] = str(port)

    command = build_streamlit_command(root, host, port)
    log_path = launcher_log_path(root)
    log_file = log_path.open("a", encoding="utf-8")
    log_file.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] starting {APP_NAME}\n")
    log_file.write(f"{LAUNCHER_SAFETY_NOTE}\n")
    log_file.flush()
    process = subprocess.Popen(command, cwd=str(root), env=env, stdout=log_file, stderr=subprocess.STDOUT)

    try:
        actual_port = wait_for_streamlit(host, port, timeout)
        if actual_port is not None:
            url = f"http://{host}:{actual_port}"
            announce(f"{APP_NAME} 已启动：{url}", log_file)
            announce(f"启动日志：{log_path}", log_file)
            if open_browser:
                webbrowser.open(url)
            else:
                announce("已按 VPS_3XUI_OPEN_BROWSER=0 跳过自动打开浏览器。", log_file)
        else:
            announce(f"{APP_NAME} 启动超时，请查看日志：{log_path}", log_file)
            recent_log = tail_text(log_path)
            if recent_log:
                announce("最近启动日志：")
                announce(recent_log)
            stop_process(process)
            return process.poll() or 1

        while process.poll() is None:
            time.sleep(0.5)
        return int(process.returncode or 0)
    except KeyboardInterrupt:
        print("正在关闭本地应用...")
        stop_process(process)
        return 0
    finally:
        log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
