from __future__ import annotations

import json
import shlex
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from .config import (
    NodeConfig,
    LAST_SUCCESS_DIR,
    OUTPUT_DIR,
    REMOTE_BACKUP_DIR,
    REMOTE_PREFLIGHT_SCRIPT,
    REMOTE_OUTPUT_FILES,
    REMOTE_HARDEN_SCRIPT,
    REMOTE_RESET_SCRIPT,
    REMOTE_RESULT_DIR,
    REMOTE_SCRIPT,
    VPSLogin,
)
from .result_parser import load_results
from .ssh_runner import DeploymentError, SSHRunner, shell_export


LogCallback = Callable[[str], None]


ERROR_HINTS = {
    "AUTH_FAILED": "root 密码错误或 SSH 用户名不正确。",
    "BAD_HOST": "VPS IP 填错或无法连接。",
    "SSH_TIMEOUT": "SSH 端口不通，或 VPS 服务商安全组没有放行 SSH 端口。",
    "SSH_CONNECT_FAILED": "SSH 连接失败，请检查 VPS IP、端口、用户名和网络。",
    "SSH_SESSION_LOST": "SSH 已连接，但部署执行过程中连接中断。请先清空本地输出后重试；如果仍发生，通常是 VPS 网络到 apt 源不稳定或服务器重启/断连。",
    "APT_INSTALL_FAILED": "VPS 基础依赖安装失败，请检查 VPS 到 Ubuntu/Debian 软件源的网络，或稍后重试。",
    "UNSUPPORTED_OS": "VPS 系统不支持；仅支持 Ubuntu 22.04 / Ubuntu 24.04 / Debian 12。",
    "PORT_IN_USE": "Reality 入站端口被占用，请换一个端口，或检查 443 是否已被其他服务占用。",
    "GITHUB_DOWNLOAD_FAILED": "GitHub 下载 3x-ui 失败，请检查 VPS 到 GitHub 的网络。",
    "XUI_INSTALL_FAILED": "3x-ui 安装失败，请查看部署日志。",
    "XUI_API_FAILED": "3x-ui API 调用失败。",
    "INBOUND_CREATE_FAILED": "Reality inbound 创建失败。",
    "QR_FAILED": "二维码生成失败。",
    "SUBSCRIPTION_FAILED": "订阅链接生成失败，但不影响单节点 VLESS 链接。",
    "DOWNLOAD_FAILED": "远程结果文件下载失败。",
    "PREFLIGHT_FAILED": "部署前检测失败，请查看检测日志。",
    "REMOTE_BACKUP_FAILED": "远程备份失败，请查看日志。",
    "REMOTE_RESET_FAILED": "远程重置失败，请查看日志。",
    "BAD_RESET_CONFIRM": "远程重置确认短语不正确。",
}


def clear_output(output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.name in {".gitkeep", LAST_SUCCESS_DIR.name}:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _copy_output_files(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for child in source_dir.iterdir():
        if child.name in {".gitkeep", LAST_SUCCESS_DIR.name}:
            continue
        target = target_dir / child.name
        if child.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def _backup_success_output() -> tempfile.TemporaryDirectory | None:
    current = load_results(OUTPUT_DIR)
    if current.get("status") != "success":
        return None
    temp_dir = tempfile.TemporaryDirectory(prefix="3xui-oneclick-output-")
    backup_dir = Path(temp_dir.name)
    _copy_output_files(OUTPUT_DIR, backup_dir)
    return temp_dir


def _save_last_success() -> None:
    current = load_results(OUTPUT_DIR)
    if current.get("status") != "success":
        return
    if LAST_SUCCESS_DIR.exists():
        shutil.rmtree(LAST_SUCCESS_DIR)
    _copy_output_files(OUTPUT_DIR, LAST_SUCCESS_DIR)


def _restore_output_backup(temp_dir: tempfile.TemporaryDirectory | None) -> bool:
    if temp_dir is not None:
        backup_dir = Path(temp_dir.name)
    elif LAST_SUCCESS_DIR.exists():
        backup_dir = LAST_SUCCESS_DIR
    else:
        return False
    if not (backup_dir / "result.json").exists():
        return False
    clear_output()
    _copy_output_files(backup_dir, OUTPUT_DIR)
    return True


def validate_inputs(login: VPSLogin, config: NodeConfig) -> None:
    validate_login(login)
    if not (1 <= config.reality_port <= 65535):
        raise DeploymentError("BAD_REALITY_PORT", "Reality 入站端口必须在 1-65535 之间。")
    if not (1 <= config.panel_port <= 65535):
        raise DeploymentError("BAD_PANEL_PORT", "3x-ui 面板端口必须在 1-65535 之间。")
    if not config.sni.strip() or "://" in config.sni:
        raise DeploymentError("BAD_SNI", "SNI 只填写域名，不要带 http:// 或 https://。")
    if not config.target.strip() or "://" in config.target:
        raise DeploymentError("BAD_TARGET", "Target 使用 域名:端口 格式，不要带 http:// 或 https://。")


def validate_login(login: VPSLogin) -> None:
    if not login.host.strip():
        raise DeploymentError("BAD_HOST", "请填写 VPS IP。")
    if not (1 <= login.port <= 65535):
        raise DeploymentError("BAD_PORT", "SSH 端口必须在 1-65535 之间。")
    if not login.username.strip():
        raise DeploymentError("BAD_USER", "请填写 SSH 用户名。")
    if not login.password:
        raise DeploymentError("AUTH_FAILED", "请填写 VPS 密码。")


def deploy(login: VPSLogin, config: NodeConfig, log: LogCallback) -> dict:
    validate_inputs(login, config)
    previous_success = _backup_success_output()
    clear_output()
    if not REMOTE_SCRIPT.exists():
        raise DeploymentError("LOCAL_SCRIPT_MISSING", f"本地远程脚本不存在：{REMOTE_SCRIPT}")

    with SSHRunner(login, log) as runner:
        runner.upload(REMOTE_SCRIPT, "/root/install_remote.sh")
        runner.upload(REMOTE_HARDEN_SCRIPT, "/root/harden_after_success.sh")
        exports = [
            shell_export("ONECLICK_NODE_NAME", config.node_name),
            shell_export("ONECLICK_REALITY_PORT", config.reality_port),
            shell_export("ONECLICK_SNI", config.sni),
            shell_export("ONECLICK_TARGET", config.target),
            shell_export("ONECLICK_FINGERPRINT", config.fingerprint),
            shell_export("ONECLICK_PANEL_PORT", config.panel_port),
            shell_export("ONECLICK_GENERATE_SSH_KEY", int(config.generate_ssh_key)),
            shell_export("ONECLICK_RUN_HARDENING", int(config.run_hardening)),
            shell_export("ONECLICK_PUBLIC_HOST", login.host),
        ]
        command = " && ".join(exports + ["bash /root/install_remote.sh"])
        exit_code = runner.run(command)
        if exit_code != 0:
            partial = {}
            try:
                runner.download_dir_files(REMOTE_RESULT_DIR, OUTPUT_DIR, ["result.json", "deploy-report.txt"])
                partial = load_results(OUTPUT_DIR)
            except DeploymentError:
                pass
            code = str(partial.get("error_code") or "REMOTE_DEPLOY_FAILED")
            remote_message = str(partial.get("error_message") or "").strip()
            message = remote_message or ERROR_HINTS.get(code, "远程部署失败，请查看实时日志和部署报告。")
            restored = _restore_output_backup(previous_success)
            if restored:
                log("部署失败，已自动恢复上一轮成功的本地二维码和链接。")
            raise DeploymentError(code, message)

        downloaded = runner.download_dir_files(REMOTE_RESULT_DIR, OUTPUT_DIR, REMOTE_OUTPUT_FILES)
        if "result.json" not in downloaded:
            raise DeploymentError("DOWNLOAD_FAILED", "缺少 result.json，远程结果文件下载失败。")
    results = load_results(OUTPUT_DIR)
    result_file = OUTPUT_DIR / "result.json"
    if result_file.exists():
        try:
            raw = json.loads(result_file.read_text(encoding="utf-8", errors="replace"))
            raw["local_output_dir"] = str(OUTPUT_DIR)
            result_file.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            results["local_output_dir"] = str(OUTPUT_DIR)
        except json.JSONDecodeError:
            pass
    _save_last_success()
    return results


def preflight(login: VPSLogin, config: NodeConfig, log: LogCallback) -> dict:
    validate_inputs(login, config)
    if not REMOTE_PREFLIGHT_SCRIPT.exists():
        raise DeploymentError("LOCAL_SCRIPT_MISSING", f"本地预检脚本不存在：{REMOTE_PREFLIGHT_SCRIPT}")

    with SSHRunner(login, log) as runner:
        runner.upload(REMOTE_PREFLIGHT_SCRIPT, "/root/preflight_3xui_oneclick.sh")
        exports = [
            shell_export("ONECLICK_REALITY_PORT", config.reality_port),
            shell_export("ONECLICK_PANEL_PORT", config.panel_port),
        ]
        exit_code = runner.run(" && ".join(exports + ["bash /root/preflight_3xui_oneclick.sh"]))
        try:
            runner.download_dir_files(REMOTE_RESULT_DIR, OUTPUT_DIR, ["preflight-result.json", "preflight-report.txt"])
        except DeploymentError:
            if exit_code == 0:
                raise
        if exit_code != 0:
            raise DeploymentError("PREFLIGHT_FAILED", "部署前检测脚本执行失败。")
    return load_results(OUTPUT_DIR).get("preflight", {})


def download_remote_results(login: VPSLogin, log: LogCallback) -> dict:
    validate_login(login)

    with SSHRunner(login, log) as runner:
        downloaded = runner.download_dir_files(REMOTE_RESULT_DIR, OUTPUT_DIR, REMOTE_OUTPUT_FILES)
        if "result.json" not in downloaded:
            raise DeploymentError("DOWNLOAD_FAILED", "远程结果目录里没有 result.json。")

    results = load_results(OUTPUT_DIR)
    result_file = OUTPUT_DIR / "result.json"
    if result_file.exists():
        try:
            raw = json.loads(result_file.read_text(encoding="utf-8", errors="replace"))
            raw["local_output_dir"] = str(OUTPUT_DIR)
            result_file.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            results["local_output_dir"] = str(OUTPUT_DIR)
        except json.JSONDecodeError:
            pass
    _save_last_success()
    return results


def backup_remote_results(login: VPSLogin, log: LogCallback) -> str:
    validate_login(login)

    with SSHRunner(login, log) as runner:
        backup_dir = shlex.quote(REMOTE_BACKUP_DIR)
        result_dir = shlex.quote(REMOTE_RESULT_DIR)
        result_parent = shlex.quote(str(Path(REMOTE_RESULT_DIR).parent))
        result_name = shlex.quote(Path(REMOTE_RESULT_DIR).name)
        command = (
            "set -Eeuo pipefail; "
            f"mkdir -p {backup_dir}; "
            f"test -d {result_dir}; "
            f"backup_path={backup_dir}\"/result-$(date +%Y%m%d-%H%M%S).tgz\"; "
            f"tar -C {result_parent} -czf \"$backup_path\" {result_name}; "
            "chmod 600 \"$backup_path\"; "
            "printf '%s\\n' \"$backup_path\""
        )
        exit_code = runner.run(command)
        if exit_code != 0:
            raise DeploymentError("REMOTE_BACKUP_FAILED", "远程结果备份失败。")
    return f"{REMOTE_BACKUP_DIR}/result-*.tgz"


def reset_remote_oneclick(
    login: VPSLogin,
    *,
    confirm_phrase: str,
    uninstall_xui: bool,
    log: LogCallback,
) -> dict:
    validate_login(login)
    if confirm_phrase != "RESET_3XUI_ONECLICK":
        raise DeploymentError("BAD_RESET_CONFIRM", "远程重置确认短语不正确。")
    if not REMOTE_RESET_SCRIPT.exists():
        raise DeploymentError("LOCAL_SCRIPT_MISSING", f"本地重置脚本不存在：{REMOTE_RESET_SCRIPT}")

    with SSHRunner(login, log) as runner:
        runner.upload(REMOTE_RESET_SCRIPT, "/root/reset_3xui_oneclick.sh")
        exports = [
            shell_export("ONECLICK_RESET_CONFIRM", confirm_phrase),
            shell_export("ONECLICK_RESET_UNINSTALL_XUI", int(uninstall_xui)),
        ]
        exit_code = runner.run(" && ".join(exports + ["bash /root/reset_3xui_oneclick.sh"]))
        clear_output()
        try:
            runner.download_dir_files(REMOTE_RESULT_DIR, OUTPUT_DIR, ["reset-result.json", "reset-report.txt"])
        except DeploymentError:
            if exit_code == 0:
                raise
        if exit_code != 0:
            partial = load_results(OUTPUT_DIR)
            reset_result = partial.get("reset", {})
            code = str(reset_result.get("error_code") or "REMOTE_RESET_FAILED")
            message = str(reset_result.get("error_message") or ERROR_HINTS["REMOTE_RESET_FAILED"])
            raise DeploymentError(code, message)
    return load_results(OUTPUT_DIR)
