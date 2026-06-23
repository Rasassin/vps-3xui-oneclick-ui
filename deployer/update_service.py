from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

from .config import APP_VERSION


GITHUB_REPO = "Rasassin/vps-3xui-oneclick-ui"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    browser_download_url: str
    size: int


@dataclass(frozen=True)
class UpdateStatus:
    current_version: str
    latest_version: str = ""
    release_url: str = ""
    published_at: str = ""
    is_newer: bool = False
    assets: tuple[ReleaseAsset, ...] = ()
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["assets"] = [asdict(asset) for asset in self.assets]
        return data


def parse_semver(version: str) -> tuple[int, int, int] | None:
    match = SEMVER_RE.match(version.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def is_newer_version(latest: str, current: str = APP_VERSION) -> bool:
    latest_parts = parse_semver(latest)
    current_parts = parse_semver(current)
    if latest_parts is None or current_parts is None:
        return False
    return latest_parts > current_parts


def _read_latest_release(timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"vps-3xui-oneclick-ui/{APP_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_latest_release(timeout: int = 8) -> UpdateStatus:
    try:
        payload = _read_latest_release(timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return UpdateStatus(current_version=APP_VERSION, error="GitHub 上还没有可用 Release。")
        return UpdateStatus(current_version=APP_VERSION, error=f"GitHub 返回错误：HTTP {exc.code}")
    except urllib.error.URLError as exc:
        return UpdateStatus(current_version=APP_VERSION, error=f"无法连接 GitHub：{exc.reason}")
    except TimeoutError:
        return UpdateStatus(current_version=APP_VERSION, error="检查更新超时，请稍后再试。")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return UpdateStatus(current_version=APP_VERSION, error=f"检查更新失败：{exc}")

    latest_version = str(payload.get("tag_name") or payload.get("name") or "").strip()
    assets = tuple(
        ReleaseAsset(
            name=str(asset.get("name", "")),
            browser_download_url=str(asset.get("browser_download_url", "")),
            size=int(asset.get("size") or 0),
        )
        for asset in payload.get("assets", [])
        if asset.get("name") and asset.get("browser_download_url")
    )
    return UpdateStatus(
        current_version=APP_VERSION,
        latest_version=latest_version,
        release_url=str(payload.get("html_url") or ""),
        published_at=str(payload.get("published_at") or ""),
        is_newer=is_newer_version(latest_version),
        assets=assets,
    )
