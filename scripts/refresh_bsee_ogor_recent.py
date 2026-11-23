#!/usr/bin/env python3
"""Targeted refresh of the most recent BSEE OGOR-A yearly production files.

The bulk refresher (scripts/refresh_bsee_all.py) only *backfills Git-LFS
stubs* — it skips any bin that is already real data, so it cannot UPDATE
existing files.  It also hardcodes OGOR-A years 1996-2024 plus one
unsuffixed "current" file, a mapping that goes stale every January:

    - When a year finalizes, BSEE publishes ogora<YEAR>delimit.zip and the
      unsuffixed ogoradelimit.zip rolls forward to the new in-progress year.
    - As of mid-2026: ogora2025delimit.zip = finalized 2025; ogoradelimit.zip
      = partial 2026; ogora2026delimit.zip does NOT exist yet (returns HTML).

This script refreshes ONLY the recent OGOR-A files and *forces* overwrite of
real data, backing up each replaced bin to a timestamped <bin>.bak-<run> so
the prior (e.g. golden-baseline) data stays recoverable.

Usage:
    uv run python scripts/refresh_bsee_ogor_recent.py            # 2025 + current(2026)
    uv run python scripts/refresh_bsee_ogor_recent.py --dry-run  # probe availability only
    uv run python scripts/refresh_bsee_ogor_recent.py --years 2025 current
    uv run python scripts/refresh_bsee_ogor_recent.py --years 2026          # once 2026 finalizes
    uv run python scripts/refresh_bsee_ogor_recent.py --no-backup
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Reuse the canonical orchestrator so download + parse (encoding/delimiter
# detection, headerless-CSV handling, pickle format) stay byte-for-byte
# identical to the bulk refresher.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_bsee_all import (  # noqa: E402
    BSEERefreshOrchestrator,
    _find_project_root,
    log,
)

OGOR_BIN_DIR = "historical_production_yearly"
BSEE_BASE = "https://www.data.bsee.gov/Production/Files"
# OGOR-A zips are small (<2 MB); a tight-ish timeout is fine.
OGOR_TIMEOUT_S = 600


def _spec_for(year: str):
    """Map a --years token to (zip_url, expected_bin_name).

    A 4-digit year Y  -> ogora{Y}delimit.zip   -> ogora{Y}delimit.bin
    'current'/'latest' -> ogoradelimit.zip      -> ogoradelimit.bin
    """
    from worldenergydata.bsee.data.refresh.url_registry import DatasetSpec

    token = year.strip().lower()
    if token in ("current", "latest"):
        stem = "ogoradelimit"
    elif token.isdigit() and len(token) == 4:
        stem = f"ogora{token}delimit"
    else:
        raise SystemExit(
            f"Invalid --years token {year!r}: use a 4-digit year or 'current'."
        )
    return DatasetSpec(
        bin_dir=OGOR_BIN_DIR,
        zip_url=f"{BSEE_BASE}/{stem}.zip",
        expected_bins=[f"{stem}.bin"],
        timeout_s=OGOR_TIMEOUT_S,
        is_ogor_a=True,
    )


def _looks_like_zip(blob: bytes) -> bool:
    """True if the payload starts with the ZIP local-file-header magic.

    BSEE serves stale/nonexistent URLs as HTTP 200 + an HTML page, so a
    status check is not enough — inspect the actual bytes.
    """
    return blob[:2] == b"PK"


def _backup_existing(bin_dir_path: Path, expected_bins: list[str], run_tag: str) -> list[Path]:
    """Move each existing real bin out of the way so the (stub-only)
    orchestrator guard will write fresh data.  Returns the backup paths.
    """
    backups: list[Path] = []
    for name in expected_bins:
        target = bin_dir_path / name
        if target.exists():
            bak = target.with_name(f"{name}.bak-{run_tag}")
            target.rename(bak)
            backups.append(bak)
            log.info("    backed up %s -> %s", name, bak.name)
    return backups


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh the most recent BSEE OGOR-A yearly files only.",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        default=["2025", "current"],
        metavar="Y",
        help="Years to refresh: 4-digit years and/or 'current' "
        "(default: 2025 current).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Probe BSEE for availability + size; download/write nothing.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Overwrite existing bins in place without a .bak copy "
        "(NOT recommended — golden baseline depends on these files).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Parallel download threads (default: 2, gentle on BSEE).",
    )
    args = parser.parse_args()

    project_root = _find_project_root()
    log.info("Project root: %s", project_root)

    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    specs = [_spec_for(y) for y in args.years]
    orch = BSEERefreshOrchestrator(
        project_root=project_root, workers=args.workers, dry_run=args.dry_run,
    )
    bin_dir_path = orch.bin_root / OGOR_BIN_DIR
    # Stable per-run tag without Date.now(); good enough for unique backups.
    run_tag = time.strftime("%Y%m%dT%H%M%S", time.gmtime())

    results = []
    for spec in specs:
        log.info("[%s] %s", spec.expected_bins[0], spec.zip_url)
        blob = orch._download_zip(spec.zip_url, spec.timeout_s)
        if blob is None:
            log.error("  download failed (network) — skipping")
            results.append((spec.expected_bins[0], "failed", 0, 0))
            continue
        if not _looks_like_zip(blob):
            log.warning(
                "  NOT a zip (%d bytes, looks like BSEE HTML stub) — this "
                "year is likely not published yet; skipping",
                len(blob),
            )
            results.append((spec.expected_bins[0], "unavailable", 0, 0))
            continue

        if args.dry_run:
            log.info("  DRY-RUN: valid zip, %.2f MB — would refresh %s",
                     len(blob) / 1e6, spec.expected_bins[0])
            results.append((spec.expected_bins[0], "dry-run", 0, len(blob)))
            continue

        if not args.no_backup:
            _backup_existing(bin_dir_path, spec.expected_bins, run_tag)
        else:
            # Without backup we must still clear the path, since the
            # orchestrator refuses to overwrite real (non-stub) data.
            for name in spec.expected_bins:
                tgt = bin_dir_path / name
                if tgt.exists():
                    tgt.unlink()

        res = orch._process_zip_to_bins(blob, spec)
        status = res.status
        results.append(
            (spec.expected_bins[0], status, res.rows_total, res.bytes_downloaded)
        )
        if status == "success":
            log.info("  -> %s: %d rows written", spec.expected_bins[0], res.rows_total)
        else:
            log.error("  -> %s: %s (%s)", spec.expected_bins[0], status, res.error)

    # ── summary ──
    print()
    print("=== OGOR-A RECENT REFRESH SUMMARY ===")
    if not args.dry_run and not args.no_backup:
        print(f"Backup tag: .bak-{run_tag}  (rollback: rename .bak-* back)")
    for name, status, rows, nbytes in results:
        print(f"  {name:<28} {status:<12} rows={rows:<10,} {nbytes/1e6:.2f} MB")

    if any(s == "failed" for _, s, _, _ in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
