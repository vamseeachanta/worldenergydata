# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas==3.1.1", "numpy==2.4.6", "matplotlib==3.11.2", "pillow==13.0.0", "pydantic-settings==2.16.3", "pyyaml==6.0.4"]
# [tool.uv]
# exclude-newer = "2026-11-25T06:00:00Z"
# ///
"""Rebuild Part 1 of Life of a Gulf of America well from the pinned BSEE ZIPs."""

import os
import sys
import tempfile
from pathlib import Path

from source_inputs import EXAMPLE, input_parser, verified_inputs


def main():
    parser = input_parser(__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EXAMPLE / "output",
        help="Destination for the tables, checks and figures (default: output/)",
    )
    args = parser.parse_args()
    destination = args.output_dir
    destination.parent.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(label, action):
        result = action()
        checks.append(f"PASS  {label}")
        return result

    with tempfile.TemporaryDirectory(prefix=".derive-", dir=destination.parent) as scratch:
        work = Path(scratch)
        data_dir = work / "inputs"
        pins = check(
            "Four source archives match manifest byte counts and SHA-256",
            lambda: verified_inputs(args.data_dir, data_dir),
        )
        os.environ["MPLCONFIGDIR"] = str(work / "mplconfig")
        from lease_analysis import build

        output = work / "output"
        output.mkdir()
        build(output, data_dir, pins, check)
        log = "\n".join(checks) + "\n"
        (output / "checks.txt").write_text(log, encoding="utf-8", newline="\n")
        destination.mkdir(exist_ok=True)
        for staged in output.iterdir():
            staged.replace(destination / staged.name)
        print(log, end="")


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="backslashreplace")
    main()
