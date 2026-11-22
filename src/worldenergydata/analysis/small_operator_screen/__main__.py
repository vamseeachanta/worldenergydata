"""Run the JSON screen; persist evidence even when the validation gate fails."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .screen import run_screen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("output must differ from input")
    raw = args.input.read_bytes()
    payload = json.loads(raw)
    result = run_screen(payload["data"], payload["config"])
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    # Exit codes are protocol values: zero success, two unevaluated, one failed.
    return {"PASS": 0, "NOT_EVALUATED": 2, "FAIL": 1}[result["validation"]["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
