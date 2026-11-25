# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas==3.1.1", "numpy==2.4.6", "matplotlib==3.11.2", "pillow==13.0.0", "pydantic-settings==2.16.3", "pyyaml==6.0.4"]
# [tool.uv]
# exclude-newer = "2026-11-25T06:00:00Z"
# ///
"""Rebuild Part 1 of Life of a Gulf of America well from the pinned BSEE ZIPs."""

import ctypes
import os
import sys
import tempfile
from pathlib import Path

from source_inputs import EXAMPLE, input_parser, verified_inputs


def install_output(staged, destination):
    """Publish the whole generation. After an exchange, scratch owns the old tree."""
    if destination.is_symlink() or staged.resolve().is_relative_to(
        destination.resolve()
    ):
        raise ValueError("The output must be a dedicated directory")
    if not destination.exists() or (
        destination.is_dir() and not any(destination.iterdir())
    ):
        staged.replace(destination)
        return
    if not all(
        (destination / name).is_file()
        for name in ("checks.txt", "numbers.json", "lease_match_bounds.csv")
    ):
        raise ValueError(
            "Choose an empty directory or an existing exploration leasing output"
        )

    # A plain rename cannot replace a populated directory. Ask the filesystem
    # to exchange the names in one operation, keeping both generations intact.
    libc = ctypes.CDLL(None, use_errno=True) if os.name == "posix" else None
    paths = (os.fsencode(staged), os.fsencode(destination))
    if sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        at_fdcwd, rename_exchange = -100, 2
        rc = libc.renameat2(at_fdcwd, paths[0], at_fdcwd, paths[1], rename_exchange)
    elif sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        rename_swap = 2
        rc = libc.renamex_np(*paths, rename_swap)
    else:
        raise OSError(
            "Atomic directory exchange unavailable. Choose a fresh --output-dir."
        )
    if rc:
        error = ctypes.get_errno()
        raise OSError(
            error,
            f"Directory exchange failed ({os.strerror(error)}). Choose a fresh --output-dir.",
        )


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
    if args.data_dir.resolve().is_relative_to(destination.resolve()):
        parser.error("Choose an output directory separate from the source archives")
    destination.parent.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(label, action):
        result = action()
        checks.append(f"PASS  {label}")
        return result

    with tempfile.TemporaryDirectory(
        prefix=".derive-", dir=destination.parent
    ) as scratch:
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
        install_output(output, destination)
        print(log, end="")


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="backslashreplace")
    main()
