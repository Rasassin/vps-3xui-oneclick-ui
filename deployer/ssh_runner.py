from __future__ import annotations

import re
import shlex
import socket
import time
from pathlib import Path
from typing import Callable

import paramiko
from paramiko.ssh_exception import SSHException

from .config import VPSLogin


LogCallback = Callable[[str], None]

TOKEN_RE = re.compile(r"(?i)(api[_-]?token|authorization|bearer)\s*[:= ]+\s*([A-Za-z0-9._~+/=-]{12,})")


class DeploymentError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def redact(text: str, password: str = "") -> str:
    sanitized = text
    if password:
        sanitized = sanitized.replace(password, "[REDACTED]")
    sanitized = TOKEN_RE.sub(lambda m: f"{m.group(1)}=[REDACTED_TOKEN]", sanitized)
    return sanitized


def shell_export(name: str, value: object) -> str:
    return f"export {name}={shlex.quote(str(value))}"


class SSHRunner:
    def __init__(self, login: VPSLogin, log: LogCallback):
        self.login = login
        self.log = log
        self.client: paramiko.SSHClient | None = None

    def __enter__(self) -> "SSHRunner":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.client:
            self.client.close()

    def _log(self, message: str) -> None:
        self.log(redact(message, self.login.password))

    def connect(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._log(f"正在连接 SSH：{self.login.username}@{self.login.host}:{self.login.port}")
            client.connect(
                hostname=self.login.host,
                port=self.login.port,
                username=self.login.username,
                password=self.login.password,
                look_for_keys=False,
                allow_agent=False,
                timeout=15,
                banner_timeout=20,
                auth_timeout=20,
            )
        except paramiko.AuthenticationException as exc:
            raise DeploymentError("AUTH_FAILED", "root 密码错误或 SSH 用户名不正确。") from exc
        except (socket.timeout, TimeoutError) as exc:
            raise DeploymentError("SSH_TIMEOUT", "SSH 端口不通或 VPS 服务商安全组未放行 SSH 端口。") from exc
        except socket.gaierror as exc:
            raise DeploymentError("BAD_HOST", "VPS IP 填写错误，无法解析或连接。") from exc
        except OSError as exc:
            raise DeploymentError("SSH_CONNECT_FAILED", f"SSH 连接失败：{exc}") from exc
        transport = client.get_transport()
        if transport is not None:
            transport.set_keepalive(15)
        self.client = client
        self._log("SSH 连接成功。")

    def upload(self, local_path: Path, remote_path: str, mode: int = 0o700) -> None:
        if not self.client:
            raise DeploymentError("SSH_NOT_CONNECTED", "SSH 未连接。")
        self._log(f"上传远程脚本到 {remote_path}")
        sftp = self.client.open_sftp()
        try:
            sftp.put(str(local_path), remote_path)
            sftp.chmod(remote_path, mode)
        finally:
            sftp.close()

    def run(self, command: str) -> int:
        if not self.client:
            raise DeploymentError("SSH_NOT_CONNECTED", "SSH 未连接。")
        transport = self.client.get_transport()
        if transport is None or not transport.is_active():
            raise DeploymentError("SSH_NOT_CONNECTED", "SSH 连接已断开。")
        try:
            channel = transport.open_session()
            channel.exec_command(command)
        except (SSHException, EOFError, OSError) as exc:
            raise DeploymentError("SSH_SESSION_LOST", f"SSH 执行通道打开失败或已断开：{exc}") from exc
        stdout_buffer = b""
        stderr_buffer = b""
        try:
            while True:
                if channel.recv_ready():
                    stdout_buffer += channel.recv(4096)
                    stdout_buffer = self._flush_lines(stdout_buffer)
                if channel.recv_stderr_ready():
                    stderr_buffer += channel.recv_stderr(4096)
                    stderr_buffer = self._flush_lines(stderr_buffer)
                if channel.exit_status_ready():
                    break
                if not transport.is_active():
                    raise DeploymentError("SSH_SESSION_LOST", "SSH 执行过程中连接中断，请稍后重试。")
                time.sleep(0.1)
            while channel.recv_ready():
                stdout_buffer += channel.recv(4096)
            while channel.recv_stderr_ready():
                stderr_buffer += channel.recv_stderr(4096)
            self._flush_lines(stdout_buffer, force=True)
            self._flush_lines(stderr_buffer, force=True)
            return channel.recv_exit_status()
        except DeploymentError:
            raise
        except (SSHException, EOFError, OSError) as exc:
            raise DeploymentError("SSH_SESSION_LOST", f"SSH 执行过程中连接中断：{exc}") from exc

    def _flush_lines(self, data: bytes, force: bool = False) -> bytes:
        if not data:
            return b""
        text = data.decode("utf-8", errors="replace")
        if not force and "\n" not in text:
            return data
        lines = text.splitlines(keepends=True)
        remainder = b""
        if not force and lines and not lines[-1].endswith("\n"):
            remainder = lines.pop().encode("utf-8", errors="replace")
        for line in lines:
            clean = line.rstrip("\r\n")
            if clean:
                self._log(clean)
        return remainder

    def download_dir_files(self, remote_dir: str, local_dir: Path, file_names: list[str]) -> list[str]:
        if not self.client:
            raise DeploymentError("SSH_NOT_CONNECTED", "SSH 未连接。")
        local_dir.mkdir(parents=True, exist_ok=True)
        downloaded: list[str] = []
        sftp = self.client.open_sftp()
        try:
            for file_name in file_names:
                remote_file = f"{remote_dir}/{file_name}"
                local_file = local_dir / file_name
                try:
                    sftp.get(remote_file, str(local_file))
                    downloaded.append(file_name)
                    self._log(f"已下载结果文件：{file_name}")
                except FileNotFoundError:
                    self._log(f"远程结果文件不存在，已跳过：{file_name}")
                except OSError as exc:
                    raise DeploymentError("DOWNLOAD_FAILED", f"远程结果文件下载失败：{file_name}，{exc}") from exc
        finally:
            sftp.close()
        return downloaded
