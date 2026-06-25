from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import APP_VERSION, PROJECT_ROOT
from .github_publish_evidence import release_web_url
from .github_release_upload_assets import UPLOAD_DIR_TEMPLATE
from .vps_compatibility_plan import expected_checklist_name, missing_systems


TEMPLATE_DIR_TEMPLATE = "external-evidence-templates-v{version}"
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"vless://[0-9a-fA-F-]{36}@", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"panel_password\s*[:=]", re.IGNORECASE),
    re.compile(r"subscription_link\s*[:=]", re.IGNORECASE),
    re.compile(r"root_password\s*[:=]", re.IGNORECASE),
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"token\s*[:=]", re.IGNORECASE),
    re.compile(r"secret\s*[:=]", re.IGNORECASE),
    re.compile(r"APPLE_APP_SPECIFIC_PASSWORD\s*=", re.IGNORECASE),
    re.compile(r"WINDOWS_SIGNING_CERT_PASSWORD\s*=", re.IGNORECASE),
)


@dataclass(frozen=True)
class EvidenceTemplateCheck:
    name: str
    status: str
    detail: str


def template_dir(version: str = APP_VERSION) -> Path:
    return PROJECT_ROOT / "dist" / TEMPLATE_DIR_TEMPLATE.format(version=version)


def command_block(command: str) -> str:
    return f"```bash\n{command}\n```"


def safe_header(version: str) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""Generated at: {generated_at}

Project version: v{version}

Do not paste credentials, node links, subscription links, QR images, panel
login details, private keys, signing secrets, certificate contents, `.env`
content, or local `output/` files into this template.
"""


def github_desktop_template(version: str = APP_VERSION) -> str:
    finalize_command = command_block("npm run external:finalize")
    fallback_command = command_block(
        "python3 scripts/record_external_release_evidence.py --type github_desktop_push --status pass --summary 'Branch pushed with GitHub Desktop.' --notes 'No secrets included.'"
    )
    return f"""# Evidence Template: GitHub Desktop Push

{safe_header(version)}

## What To Do

1. Open GitHub Desktop.
2. Select this repository.
3. Review changed files.
4. Commit with an intentional message.
5. Push the branch.

## Record Evidence

After pushing, run:

{finalize_command}

Manual fallback:

{fallback_command}
"""


def github_release_upload_template(version: str = APP_VERSION) -> str:
    upload_dir = PROJECT_ROOT / "dist" / UPLOAD_DIR_TEMPLATE.format(version=version)
    upload_check_command = command_block("\n".join(["npm run external:finalize", "npm run external:check-remote-assets"]))
    fallback_command = command_block(
        "python3 scripts/record_external_release_evidence.py --type github_release_upload --status pass --summary 'Expected GitHub Release assets are visible remotely.' --url '"
        + release_web_url(version)
        + "' --notes 'No secrets included.'"
    )
    return f"""# Evidence Template: GitHub Release Upload

{safe_header(version)}

Release URL: {release_web_url(version)}

Upload directory:

`{upload_dir}`

## What To Do

1. Open the GitHub Release page.
2. Drag every file from the upload directory into the release asset area.
3. Wait until GitHub finishes uploading every file.

## Record Evidence

After uploading, run:

{upload_check_command}

Manual fallback:

{fallback_command}
"""


def signing_template(version: str = APP_VERSION, platform_name: str = "macOS") -> str:
    if platform_name == "macOS":
        title = "macOS Notarization"
        evidence_type = "macos_notarization"
        command = "npm run electron:sign:mac\nnpm run external:signing-evidence\nnpm run external:finalize"
        summary = "macOS app signed, notarized, stapled, and validated."
    else:
        title = "Windows Signing"
        evidence_type = "windows_signing"
        command = "npm run electron:sign:win\nnpm run external:signing-evidence\nnpm run external:finalize"
        summary = "Windows signed artifact validated."
    signing_command = command_block(command)
    fallback_command = command_block(
        "python3 scripts/record_external_release_evidence.py --type "
        + evidence_type
        + " --status pass --summary '"
        + summary
        + "' --notes 'No signing secrets included.'"
    )
    return f"""# Evidence Template: {title}

{safe_header(version)}

## What To Do

Run this only on a trusted signing-capable machine. Keep signing credentials
outside this repository and outside the generated reports.

## Record Evidence

{signing_command}

Manual fallback:

{fallback_command}
"""


def signed_artifact_validation_template(version: str = APP_VERSION) -> str:
    validation_command = command_block("\n".join(["npm run external:signing-evidence", "npm run external:finalize"]))
    fallback_command = command_block(
        "python3 scripts/record_external_release_evidence.py --type signed_artifact_validation --status pass --summary 'Signed artifacts validated locally.' --notes 'No signing secrets included.'"
    )
    return f"""# Evidence Template: Signed Artifact Validation

{safe_header(version)}

## What To Do

Validate signed macOS and Windows artifacts on the appropriate machines. Do not
copy signing certificates or private keys into this repository.

## Record Evidence

{validation_command}

Manual fallback:

{fallback_command}
"""


def vps_template(system: str, version: str = APP_VERSION) -> str:
    record_command = command_block(
        "\n".join(
            [
                "python3 scripts/record_vps_compatibility_from_output.py --system '" + system + "' --provider-region 'Provider / Region'",
                "npm run external:finalize",
            ]
        )
    )
    fallback_command = command_block(
        "python3 scripts/record_vps_compatibility.py --system '"
        + system
        + "' --provider-region 'Provider / Region' --status pass --ssh pass --preflight pass --deploy pass --vless-qr pass --subscription pass --panel-login pass --reset not_tested --notes 'No secrets here.'"
    )
    return f"""# Evidence Template: VPS Compatibility / {system}

{safe_header(version)}

## What To Do

1. Use a fresh `{system}` VPS when possible.
2. Run the local app deployment flow.
3. Confirm SSH, preflight, deployment, VLESS QR/link, optional subscription,
   and panel login behavior.
4. Do not paste local output files or connection details into this template.

## Record Evidence From Local Output

{record_command}

Manual fallback:

{fallback_command}
"""


def readme_text(version: str = APP_VERSION) -> str:
    missing = ", ".join(missing_systems()) or "none"
    recommended_flow = command_block("\n".join(["npm run external:operator-guide", "npm run external:evidence-templates", "npm run external:finalize"]))
    return f"""# External Evidence Templates v{version}

{safe_header(version)}

This folder contains sanitized templates for external work that cannot be
finished by local source edits alone.

Missing VPS systems: `{missing}`

Recommended flow:

{recommended_flow}
"""


def template_files(version: str = APP_VERSION) -> dict[str, str]:
    files = {
        "README.md": readme_text(version),
        "github-desktop-push.md": github_desktop_template(version),
        "github-release-upload.md": github_release_upload_template(version),
        "macos-notarization.md": signing_template(version, "macOS"),
        "windows-signing.md": signing_template(version, "Windows"),
        "signed-artifact-validation.md": signed_artifact_validation_template(version),
    }
    for system in missing_systems():
        files[f"vps-{expected_checklist_name(system)}"] = vps_template(system, version)
    return files


def write_templates(version: str = APP_VERSION) -> Path:
    directory = template_dir(version)
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("*.md"):
        stale.unlink()
    for name, text in template_files(version).items():
        (directory / name).write_text(text, encoding="utf-8")
    return directory


def check_forbidden_patterns(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return ""


def check_templates(version: str = APP_VERSION) -> list[EvidenceTemplateCheck]:
    directory = template_dir(version)
    if not directory.exists() or not directory.is_dir():
        return [EvidenceTemplateCheck("Evidence template directory", "fail", f"missing directory: {directory}")]
    checks: list[EvidenceTemplateCheck] = []
    files = sorted(path for path in directory.iterdir() if path.is_file())
    directories = sorted(path.name for path in directory.iterdir() if path.is_dir())
    if directories:
        checks.append(EvidenceTemplateCheck("No nested directories", "fail", "nested directories found: " + ", ".join(directories)))
    else:
        checks.append(EvidenceTemplateCheck("No nested directories", "pass", "template directory contains files only."))

    expected_names = set(template_files(version))
    actual_names = {path.name for path in files}
    missing = sorted(expected_names - actual_names)
    unexpected = sorted(actual_names - expected_names)
    if missing or unexpected:
        detail = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if unexpected:
            detail.append("unexpected: " + ", ".join(unexpected))
        checks.append(EvidenceTemplateCheck("Expected template files", "fail", "; ".join(detail)))
    else:
        checks.append(EvidenceTemplateCheck("Expected template files", "pass", "template files match current external evidence needs."))

    marker_failures = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in ("Do not paste credentials", "Record Evidence"):
            if path.name != "README.md" and marker not in text:
                marker_failures.append(f"{path.name} missing {marker!r}")
    if marker_failures:
        checks.append(EvidenceTemplateCheck("Template content markers", "fail", "; ".join(marker_failures)))
    else:
        checks.append(EvidenceTemplateCheck("Template content markers", "pass", "all evidence templates include safety and recording markers."))

    pattern_failures = []
    for path in files:
        pattern = check_forbidden_patterns(path)
        if pattern:
            pattern_failures.append(f"{path.name}: {pattern}")
    if pattern_failures:
        checks.append(EvidenceTemplateCheck("Template secret scan", "fail", "; ".join(pattern_failures)))
    else:
        checks.append(EvidenceTemplateCheck("Template secret scan", "pass", "no obvious secrets, node links, credentials, or private keys found."))
    return checks


def template_checks_overall_status(checks: list[EvidenceTemplateCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "pending" for check in checks):
        return "pending"
    return "pass"
