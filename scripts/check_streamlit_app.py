from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deployer.config import PROJECT_ROOT


def ensure_runtime_python() -> None:
    required_imports = ["streamlit", "paramiko", "qrcode", "PIL"]
    missing = [name for name in required_imports if importlib.util.find_spec(name) is None]
    if not missing:
        return

    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if not venv_python.exists() or Path(sys.prefix).resolve() == (PROJECT_ROOT / ".venv").resolve():
        raise SystemExit(f"streamlit app check failed: missing Python imports: {', '.join(missing)}")

    os.execv(str(venv_python), [str(venv_python), *sys.argv])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local Streamlit UI smoke test without connecting to a VPS.")
    parser.add_argument("--timeout", type=int, default=20, help="AppTest timeout in seconds.")
    args = parser.parse_args()

    ensure_runtime_python()
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError as exc:
        raise SystemExit("streamlit app check failed: streamlit.testing.v1 is unavailable.") from exc

    app_test = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=args.timeout)
    app_test.run()
    exceptions = list(app_test.exception)
    if exceptions:
        for exception in exceptions:
            print(exception)
        raise SystemExit("streamlit app check failed: app raised exceptions during initial render.")
    print("streamlit app check ok")


if __name__ == "__main__":
    main()
