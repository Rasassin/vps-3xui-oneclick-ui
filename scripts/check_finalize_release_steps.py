from __future__ import annotations

import argparse
import ast
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent / "finalize_external_release.py"


def node_value(node: ast.AST) -> str:
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    if isinstance(node, ast.Name):
        return node.id
    return ast.dump(node)


def literal_command(node: ast.AST) -> tuple[str, ...] | None:
    if not isinstance(node, ast.List):
        return None
    return tuple(node_value(item) for item in node.elts)


def duplicate_run_step_commands(path: Path = SCRIPT_PATH) -> list[str]:
    source = path.read_text(encoding="utf-8")
    module = ast.parse(source)
    seen: dict[tuple[str, ...], str] = {}
    duplicates: list[str] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call) or getattr(node.func, "id", "") != "run_step":
            continue
        if len(node.args) < 2:
            continue
        command = literal_command(node.args[1])
        if command is None:
            continue
        name = node_value(node.args[0])
        previous = seen.get(command)
        if previous:
            duplicates.append(f"{previous} / {name}: {' '.join(command)}")
        else:
            seen[command] = name
    return duplicates


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check finalize_external_release.py for duplicate direct run_step commands. "
            "This does not push, upload, sign, connect to a VPS, or store credentials."
        )
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    duplicates = duplicate_run_step_commands()
    if duplicates:
        print("fail: duplicate finalize commands")
        for duplicate in duplicates:
            print(f"- {duplicate}")
        if args.strict:
            raise SystemExit(1)
        return
    print("pass: finalize release steps contain no duplicate direct run_step commands.")


if __name__ == "__main__":
    main()
