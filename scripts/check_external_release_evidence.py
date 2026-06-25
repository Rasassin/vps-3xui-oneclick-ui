from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION, PROJECT_ROOT
from deployer.external_release_evidence import compact_evidence, load_evidence, validate_evidence_rows
from scripts.build_external_evidence_report import write_report as write_evidence_report


def audit_report_text(version: str, before_count: int, after_count: int, problems: list[str]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    status = "fail" if problems else "pass"
    problem_rows = "\n".join(f"- {problem}" for problem in problems) or "- none"
    return f"""# External Evidence Audit v{version}

Generated at: {generated_at}

Overall status: `{status}`

Rows before compaction: `{before_count}`

Rows after compaction: `{after_count}`

This report audits the ignored local external evidence file. It does not push
commits, create tags, upload assets, sign binaries, connect to a VPS, store
credentials, or include secrets.

## Problems

{problem_rows}
"""


def write_audit_report(version: str, before_count: int, after_count: int, problems: list[str]) -> Path:
    dist_dir = PROJECT_ROOT / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    path = dist_dir / f"EXTERNAL_EVIDENCE_AUDIT_v{version}.md"
    path.write_text(audit_report_text(version, before_count, after_count, problems), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit and optionally compact external release evidence without publishing, signing, "
            "connecting to a VPS, or storing credentials."
        )
    )
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--compact", action="store_true", help="Rewrite evidence file with one latest row per evidence type.")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail if evidence has duplicates, invalid rows, or sensitive patterns.")
    args = parser.parse_args()

    evidence = load_evidence()
    before_count = len(evidence)
    counts = Counter(item.evidence_type for item in evidence)
    duplicate_types = sorted(item for item, count in counts.items() if count > 1)
    compacted = compact_evidence(evidence)
    problems = validate_evidence_rows(compacted)
    if duplicate_types:
        problems = [*problems, "duplicate evidence rows compacted: " + ", ".join(duplicate_types)]

    evidence_changed = False
    if args.compact and evidence != compacted:
        from deployer.external_release_evidence import EVIDENCE_FILE
        import json
        from dataclasses import asdict

        EVIDENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_FILE.write_text(json.dumps([asdict(item) for item in compacted], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        evidence_changed = True
        evidence = load_evidence()
        compacted = compact_evidence(evidence)
        problems = validate_evidence_rows(compacted)

    if args.write_report:
        print(write_audit_report(args.version, before_count, len(compacted), problems))
        if evidence_changed:
            print(write_evidence_report(args.version))

    print(f"evidence rows before compaction: {before_count}")
    print(f"evidence rows after compaction: {len(compacted)}")
    for item in compacted:
        print(f"{item.status}: {item.evidence_type} - {item.summary}")
    for problem in problems:
        print(f"problem: {problem}")

    if args.strict and problems:
        raise SystemExit(1)
    if any(not problem.startswith("duplicate evidence rows compacted:") for problem in problems):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
