from __future__ import annotations

import argparse
import sys


SCRIPT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.external_release_evidence import ALLOWED_STATUSES, ALLOWED_TYPES, build_evidence, save_evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record sanitized external release evidence without storing passwords, tokens, signing secrets, or node links."
    )
    parser.add_argument("--type", required=True, choices=ALLOWED_TYPES, dest="evidence_type")
    parser.add_argument("--status", required=True, choices=ALLOWED_STATUSES)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--artifact", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    evidence = build_evidence(
        evidence_type=args.evidence_type,
        status=args.status,
        summary=args.summary,
        artifact=args.artifact,
        url=args.url,
        notes=args.notes,
    )
    path = save_evidence(evidence)
    print(f"external release evidence recorded locally: {path}")
    print("The evidence file is under data/ and is ignored by Git.")


if __name__ == "__main__":
    main()
