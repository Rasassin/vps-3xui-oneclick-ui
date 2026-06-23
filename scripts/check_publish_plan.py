from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import APP_VERSION
from deployer.publish_assistant import collect_publish_steps, publish_plan_overall_status, write_publish_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local GitHub publishing plan without performing publish actions.")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--strict", action="store_true", help="Fail unless the publish plan is pass.")
    parser.add_argument("--write-report", action="store_true", help="Write dist/PUBLISH_PLAN_vX.Y.Z.md.")
    args = parser.parse_args()

    steps = collect_publish_steps(args.version)
    if args.write_report:
        print(write_publish_plan(steps, args.version))
    for step in steps:
        suffix = f" Command: {step.command}" if step.command and step.status != "pass" else ""
        print(f"{step.status}: {step.name} - {step.detail}{suffix}")
    if args.strict and publish_plan_overall_status(steps) != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
