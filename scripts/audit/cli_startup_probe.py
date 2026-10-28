"""Measure an installed console in fresh processes; keep raw evidence external.

Example: python scripts/audit/cli_startup_probe.py --repeats 2 --timeout 20
         --output "$TMPDIR/startup.json" -- landman --help

The first process is labelled cold and subsequent processes warm. These labels
refer to process/import state, not a flushed operating-system page cache.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def positive_int(value: str) -> int:
    """Require caller-supplied sample counts and watchdogs, without defaults."""
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=positive_int, required=True)
    parser.add_argument("--timeout", type=positive_int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    executable = shutil.which("worldenergydata")
    if executable is None:
        parser.error("worldenergydata must be installed in the active environment")
    command_args = args.args[1:] if args.args[:1] == ["--"] else args.args
    samples = []
    for index in range(args.repeats):
        started = time.perf_counter()
        try:
            result = subprocess.run(
                [executable, *command_args],
                capture_output=True,
                text=True,
                timeout=args.timeout,
                check=False,
                # Python's import profiler supplies the import stack evidence.
                env={**os.environ, "PYTHONPROFILEIMPORTTIME": "1"},
            )
            sample = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "import_stack": result.stderr,
            }
        except subprocess.TimeoutExpired:
            sample = {"returncode": None, "timed_out": True}
        sample.update(
            cache="cold" if index == 0 else "warm",
            elapsed_seconds=time.perf_counter() - started,
        )
        samples.append(sample)
        # Persist each completed sample; an interrupted probe retains evidence.
        args.output.write_text(
            json.dumps({"args": command_args, "samples": samples}, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
