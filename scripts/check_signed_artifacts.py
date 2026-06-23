from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT


@dataclass(frozen=True)
class ArtifactCheck:
    name: str
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.status in {"ok", "not_provided", "unsupported"}


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def check_macos_app(path: Path | None) -> list[ArtifactCheck]:
    if path is None:
        return [ArtifactCheck("macOS app", "not_provided", "No macOS app path was provided.")]
    if not path.exists() or not path.is_dir():
        return [ArtifactCheck("macOS app", "failed", f"Missing app bundle: {path}")]
    if platform.system() != "Darwin":
        return [ArtifactCheck("macOS app", "unsupported", "codesign validation requires macOS.")]

    checks: list[ArtifactCheck] = []
    codesign = run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(path)])
    checks.append(
        ArtifactCheck(
            "macOS codesign",
            "ok" if codesign.returncode == 0 else "failed",
            (codesign.stderr or codesign.stdout or "codesign completed").strip(),
        )
    )
    if shutil.which("xcrun"):
        stapler = run(["xcrun", "stapler", "validate", str(path)])
        checks.append(
            ArtifactCheck(
                "macOS stapler",
                "ok" if stapler.returncode == 0 else "failed",
                (stapler.stderr or stapler.stdout or "stapler completed").strip(),
            )
        )
    else:
        checks.append(ArtifactCheck("macOS stapler", "unsupported", "xcrun is missing."))
    return checks


def check_windows_installer(path: Path | None) -> list[ArtifactCheck]:
    if path is None:
        return [ArtifactCheck("Windows installer", "not_provided", "No Windows installer path was provided.")]
    if not path.exists() or not path.is_file():
        return [ArtifactCheck("Windows installer", "failed", f"Missing installer: {path}")]
    if platform.system() != "Windows":
        return [ArtifactCheck("Windows Authenticode", "unsupported", "Authenticode validation requires Windows.")]

    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        return [ArtifactCheck("Windows Authenticode", "failed", "PowerShell is missing.")]
    command = [
        powershell,
        "-NoProfile",
        "-Command",
        (
            "$sig = Get-AuthenticodeSignature -FilePath "
            + json.dumps(str(path))
            + "; $sig | Select-Object Status,StatusMessage,SignerCertificate | ConvertTo-Json -Compress"
        ),
    ]
    result = run(command)
    if result.returncode != 0:
        return [ArtifactCheck("Windows Authenticode", "failed", (result.stderr or result.stdout).strip())]
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return [ArtifactCheck("Windows Authenticode", "failed", result.stdout.strip())]
    status = str(payload.get("Status") or "")
    signer = payload.get("SignerCertificate")
    signer_present = bool(signer)
    ok = status == "Valid" and signer_present
    detail = f"Status={status}; SignerCertificate={'present' if signer_present else 'missing'}"
    return [ArtifactCheck("Windows Authenticode", "ok" if ok else "failed", detail)]


def report_text(checks: list[ArtifactCheck]) -> str:
    rows = "\n".join(f"| {check.name} | {check.status} | `{check.detail}` |" for check in checks)
    return f"""# Signed Artifact Validation v{APP_VERSION}

This report validates signed desktop artifacts when paths are provided.
It does not contain signing secrets, certificate private keys, VPS credentials,
node links, QR images, subscription links, or panel credentials.

Platform: {platform.platform()}

| Check | Status | Detail |
| --- | --- | --- |
{rows}

Status values:

- `ok`: validation succeeded
- `failed`: validation ran and failed
- `not_provided`: no artifact path was supplied
- `unsupported`: this operating system cannot validate that artifact type

Use `--strict` on a release-signing machine to fail if any provided artifact
does not validate.
"""


def write_report(checks: list[ArtifactCheck]) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    report_path = dist_dir / f"SIGNED_ARTIFACT_VALIDATION_v{APP_VERSION}.md"
    report_path.write_text(report_text(checks), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate signed desktop artifacts without connecting to a VPS.")
    parser.add_argument("--macos-app", type=Path, help="Optional signed macOS .app bundle to validate.")
    parser.add_argument("--windows-installer", type=Path, help="Optional signed Windows installer .exe to validate.")
    parser.add_argument("--strict", action="store_true", help="Fail if any provided artifact validation fails.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/SIGNED_ARTIFACT_VALIDATION_vX.Y.Z.md.")
    args = parser.parse_args()

    checks = [
        *check_macos_app(args.macos_app),
        *check_windows_installer(args.windows_installer),
    ]
    if args.write_report:
        print(write_report(checks))
    failures = [check for check in checks if check.status == "failed"]
    if failures:
        print("signed artifact validation failed:")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        if args.strict:
            raise SystemExit(1)
    else:
        print("signed artifact validation ok")


if __name__ == "__main__":
    main()
