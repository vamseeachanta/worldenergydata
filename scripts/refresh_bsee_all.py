#!/usr/bin/env python3
"""Standalone parallel download script to replace LFS stub .bin files
with real pickle DataFrames downloaded from BSEE.

Usage:
    python3 scripts/refresh_bsee_all.py                    # Full refresh
    python3 scripts/refresh_bsee_all.py --dry-run           # Show plan only
    python3 scripts/refresh_bsee_all.py --workers 2         # Limit parallelism
    python3 scripts/refresh_bsee_all.py --dir platstruc     # Single directory
    python3 scripts/refresh_bsee_all.py --skip-ogor         # Skip OGOR-A yearly

Dependencies: pandas, requests (no loguru — stdlib logging only).
"""

from __future__ import annotations

import argparse
import io
import logging
import pickle
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from worldenergydata.bsee.data.refresh.url_registry import DatasetSpec

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("bsee-refresh")

PROGRESS_EVERY_BYTES = 5 * 1024 * 1024  # log every 5 MB
CHUNK_SIZE = 32 * 1024  # 32 KB download chunks
MAX_RETRIES = 3
INITIAL_BACKOFF_S = 10
LFS_SIGNATURE = b"version https://git-lfs"


def _get_requests():
    """Import requests lazily so --help/module import stays lightweight."""
    import requests

    return requests


# ── Result dataclass ──────────────────────────────────────────────


@dataclass
class RefreshResult:
    bin_dir: str
    status: str  # "success", "failed", "skipped"
    bins_written: int = 0
    rows_total: int = 0
    bytes_downloaded: int = 0
    error: str = ""
    duration_s: float = 0.0


# ── Helpers ───────────────────────────────────────────────────────


def _slug(name: str) -> str:
    """Sanitize a ZIP-member stem or worksheet name into a bin-name token.

    BOEM workbook names carry spaces, commas, and mixed case
    ("2023 - Table 4 Final"); bins need stable filesystem-safe names.
    """
    import re

    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def is_lfs_stub(path: Path) -> bool:
    """Return True if *path* is a Git LFS pointer file."""
    try:
        with open(path, "rb") as fh:
            header = fh.read(40)
        return header.startswith(LFS_SIGNATURE)
    except OSError:
        return False


def backup_bin(target: Path, run_tag: str) -> Path | None:
    """Move *target* aside to <name>.bak-<run_tag> before a forced overwrite.

    Returns the backup path, or None if *target* did not exist.  Keeps the
    prior (possibly golden-baseline) data recoverable across a --force run.
    """
    if not target.exists():
        return None
    bak = target.with_name(f"{target.name}.bak-{run_tag}")
    target.rename(bak)
    return bak


# ── Orchestrator ──────────────────────────────────────────────────


class BSEERefreshOrchestrator:
    BIN_ROOT = Path("data/modules/bsee/bin")  # relative to project root

    def __init__(
        self,
        project_root: Path,
        workers: int = 4,
        dry_run: bool = False,
        force: bool = False,
    ):
        self.project_root = project_root
        self.bin_root = project_root / self.BIN_ROOT
        self.workers = workers
        self.dry_run = dry_run
        # When force=True, overwrite real data instead of skipping it, moving
        # each replaced bin aside to <name>.bak-<run_tag> first.
        self.force = force
        self.run_tag = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
        requests = _get_requests()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "WorldEnergyData/1.0 (BSEE Data Refresh)",
                "Accept": "application/zip, application/octet-stream, */*",
            }
        )
        self.results: list[RefreshResult] = []

    # ── download ──────────────────────────────────────────────────

    def _download_zip(self, url: str, timeout_s: int) -> bytes | None:
        """Download *url* with retry and exponential backoff.

        Returns the raw bytes of the response, or None on total failure.
        """
        backoff = INITIAL_BACKOFF_S
        current_timeout = timeout_s

        requests = _get_requests()
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                log.info(
                    "  [attempt %d/%d] GET %s (timeout %ds)",
                    attempt,
                    MAX_RETRIES,
                    url,
                    current_timeout,
                )
                resp = self.session.get(
                    url,
                    stream=True,
                    timeout=current_timeout,
                )
                resp.raise_for_status()

                chunks: list[bytes] = []
                downloaded = 0
                last_logged = 0
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if downloaded - last_logged >= PROGRESS_EVERY_BYTES:
                        log.info(
                            "    ... %.1f MB downloaded",
                            downloaded / (1024 * 1024),
                        )
                        last_logged = downloaded

                data = b"".join(chunks)
                log.info(
                    "  download complete: %.2f MB",
                    len(data) / (1024 * 1024),
                )
                return data

            except (requests.RequestException, OSError) as exc:
                log.warning("  attempt %d failed: %s", attempt, exc)
                if attempt < MAX_RETRIES:
                    log.info("  retrying in %ds ...", backoff)
                    time.sleep(backoff)
                    backoff *= 2
                    current_timeout = int(current_timeout * 1.5)

        log.error("  all %d download attempts failed for %s", MAX_RETRIES, url)
        return None

    # ── zip → bins ────────────────────────────────────────────────

    def _process_zip_to_bins(
        self,
        zip_bytes: bytes,
        spec: "DatasetSpec",
    ) -> RefreshResult:
        """Extract CSV/TXT files from *zip_bytes*, convert each to a
        pickled DataFrame, and write to the appropriate bin directory.
        """
        t0 = time.monotonic()
        bin_dir_path = self.bin_root / spec.bin_dir
        bin_dir_path.mkdir(parents=True, exist_ok=True)

        bins_written = 0
        rows_total = 0

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                data_files = [
                    n
                    for n in zf.namelist()
                    if n.lower().endswith((".txt", ".csv", ".xlsx"))
                ]
                if not data_files:
                    return RefreshResult(
                        bin_dir=spec.bin_dir,
                        status="failed",
                        error="ZIP contains no .txt/.csv/.xlsx files",
                        bytes_downloaded=len(zip_bytes),
                        duration_s=time.monotonic() - t0,
                    )

                def _skip(bin_name: str) -> bool:
                    # Protect real (non-stub) data: skip BEFORE parsing so
                    # idempotent re-runs don't pay the parse cost. --force
                    # never skips (backup happens at write time below).
                    target = bin_dir_path / bin_name
                    if target.exists() and not is_lfs_stub(target) and not self.force:
                        log.info("    skip %s (already real data)", bin_name)
                        return True
                    return False

                for filename in data_files:
                    raw = zf.read(filename)

                    for bin_name, df in self._member_frames(filename, raw, _skip):
                        target = bin_dir_path / bin_name

                        # --force overwrite of real data: back it up first.
                        if target.exists() and not is_lfs_stub(target):
                            bak = backup_bin(target, self.run_tag)
                            if bak is not None:
                                log.info(
                                    "    backed up %s -> %s",
                                    bin_name,
                                    bak.name,
                                )

                        rows_total += len(df)

                        with open(target, "wb") as fh:
                            pickle.dump(df, fh)

                        bins_written += 1
                        log.info(
                            "    wrote %s (%d rows)",
                            bin_name,
                            len(df),
                        )

        except zipfile.BadZipFile as exc:
            return RefreshResult(
                bin_dir=spec.bin_dir,
                status="failed",
                error=f"Bad ZIP: {exc}",
                bytes_downloaded=len(zip_bytes),
                duration_s=time.monotonic() - t0,
            )

        return RefreshResult(
            bin_dir=spec.bin_dir,
            status="success",
            bins_written=bins_written,
            rows_total=rows_total,
            bytes_downloaded=len(zip_bytes),
            duration_s=time.monotonic() - t0,
        )

    def _member_frames(self, filename: str, raw: bytes, skip=None):
        """Yield ``(bin_name, DataFrame)`` pairs for one ZIP member.

        Delimited members (.txt/.csv) keep their historical behavior: one
        bin named after the member stem, parsed with header inference.
        Workbook members (.xlsx — BOEM FieldReserves tables, #847) yield
        one bin per sheet, named ``<stem-slug>__<sheet-slug>.bin`` and
        pickled as the raw ``header=None`` grid: the sheets carry
        multi-row human headers, so downstream parsers own header
        detection (see scripts/field_development/build_lt_reserves_discovery.py).

        *skip* is an optional ``skip(bin_name) -> bool`` predicate checked
        BEFORE parsing, so idempotent re-runs over already-real bins do
        not pay the parse cost.
        """
        import pandas as pd

        skip = skip or (lambda _name: False)
        stem = Path(filename).stem
        if filename.lower().endswith(".xlsx"):
            xf = pd.ExcelFile(io.BytesIO(raw))
            for sheet_name in xf.sheet_names:
                bin_name = f"{_slug(stem)}__{_slug(sheet_name)}.bin"
                if skip(bin_name):
                    continue
                yield bin_name, xf.parse(sheet_name, header=None)
            return

        bin_name = f"{stem}.bin"
        if skip(bin_name):
            return

        # Try utf-8 first, fall back to latin-1
        for encoding in ("utf-8", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("utf-8", errors="replace")

        # Detect delimiter: comma vs pipe
        df = self._read_csv_text(text)
        if df is None:
            log.warning("    could not parse %s — skipping", filename)
            return
        yield bin_name, df

    @staticmethod
    def _read_csv_text(text: str) -> "pd.DataFrame | None":
        """Parse CSV text, trying comma then pipe delimiter."""
        import pandas as pd

        for sep in (",", "|"):
            try:
                df = pd.read_csv(
                    io.StringIO(text),
                    sep=sep,
                    low_memory=False,
                    encoding_errors="replace",
                )
                # Heuristic: a valid parse should produce >1 column for most
                # BSEE datasets (unless it is genuinely single-column).
                if len(df.columns) >= 1:
                    return df
            except Exception:
                continue
        return None

    # ── single spec refresh ───────────────────────────────────────

    def refresh_single(self, spec: "DatasetSpec") -> RefreshResult:
        """Download and process one DatasetSpec."""
        t0 = time.monotonic()
        log.info("[%s] starting refresh  %s", spec.bin_dir, spec.zip_url)

        if self.dry_run:
            bin_dir_path = self.bin_root / spec.bin_dir
            if self.force:
                n = len(spec.expected_bins)
                log.info(
                    "[%s] DRY-RUN(force): would download %s → rewrite %d bin(s)"
                    " (existing real data backed up)",
                    spec.bin_dir,
                    spec.zip_url,
                    n,
                )
            else:
                stubs = sum(
                    1
                    for b in spec.expected_bins
                    if not (bin_dir_path / b).exists() or is_lfs_stub(bin_dir_path / b)
                )
                log.info(
                    "[%s] DRY-RUN: would download %s → %d stubs to replace",
                    spec.bin_dir,
                    spec.zip_url,
                    stubs,
                )
            return RefreshResult(
                bin_dir=spec.bin_dir,
                status="skipped",
                duration_s=time.monotonic() - t0,
            )

        # Check if ALL expected bins are already real data.  With --force we
        # want to refresh them anyway, so skip this early-out.
        bin_dir_path = self.bin_root / spec.bin_dir
        all_real = not self.force and all(
            (bin_dir_path / b).exists() and not is_lfs_stub(bin_dir_path / b)
            for b in spec.expected_bins
        )
        if all_real:
            log.info(
                "[%s] all %d bins are already real data — skipping",
                spec.bin_dir,
                len(spec.expected_bins),
            )
            return RefreshResult(
                bin_dir=spec.bin_dir,
                status="skipped",
                duration_s=time.monotonic() - t0,
            )

        # Download
        zip_bytes = self._download_zip(spec.zip_url, spec.timeout_s)
        if zip_bytes is None:
            return RefreshResult(
                bin_dir=spec.bin_dir,
                status="failed",
                error=f"Download failed after {MAX_RETRIES} retries",
                duration_s=time.monotonic() - t0,
            )

        # Process
        result = self._process_zip_to_bins(zip_bytes, spec)
        result.duration_s = time.monotonic() - t0
        return result

    # ── bulk refresh ──────────────────────────────────────────────

    def refresh_all(
        self,
        specs: list["DatasetSpec"],
    ) -> list[RefreshResult]:
        """Run refresh in two phases: regular first, then OGOR-A."""
        regular = [s for s in specs if not s.is_ogor_a]
        ogor_a = [s for s in specs if s.is_ogor_a]

        results: list[RefreshResult] = []

        # Phase 1 — regular specs
        if regular:
            log.info(
                "=== Phase 1: %d regular datasets (%d workers) ===",
                len(regular),
                self.workers,
            )
            results.extend(self._run_pool(regular, self.workers))

        # Phase 2 — OGOR-A (gentler on BSEE)
        if ogor_a:
            ogor_workers = max(self.workers - 1, 1)
            log.info(
                "=== Phase 2: %d OGOR-A datasets (%d workers) ===",
                len(ogor_a),
                ogor_workers,
            )
            results.extend(self._run_pool(ogor_a, ogor_workers))

        self.results = results
        return results

    def _run_pool(
        self,
        specs: list["DatasetSpec"],
        workers: int,
    ) -> list[RefreshResult]:
        results: list[RefreshResult] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.refresh_single, spec): spec for spec in specs}
            for future in as_completed(futures):
                spec = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = RefreshResult(
                        bin_dir=spec.bin_dir,
                        status="failed",
                        error=str(exc),
                    )
                results.append(result)
                log.info(
                    "[%s] %s  bins=%d  rows=%d  %.1fs",
                    result.bin_dir,
                    result.status,
                    result.bins_written,
                    result.rows_total,
                    result.duration_s,
                )
        return results

    # ── summary ───────────────────────────────────────────────────

    def print_summary(self, results: list[RefreshResult]) -> None:
        total = len(results)
        success = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        bins_written = sum(r.bins_written for r in results)
        total_bytes = sum(r.bytes_downloaded for r in results)
        total_rows = sum(r.rows_total for r in results)
        total_duration = sum(r.duration_s for r in results)

        minutes = int(total_duration) // 60
        seconds = int(total_duration) % 60

        print()
        print("=== BSEE DATA REFRESH SUMMARY ===")
        print(f"Success: {success}/{total} | Failed: {failed} | Skipped: {skipped}")
        from worldenergydata.bsee.data.refresh.url_registry import get_all_specs

        total_expected = sum(len(sp.expected_bins) for sp in get_all_specs())
        print(f"Bins written: {bins_written}/{total_expected}")
        print(f"Rows loaded:  {total_rows:,}")
        print(f"Total downloaded: {total_bytes / (1024 * 1024):.1f} MB")
        print(f"Duration: {minutes}m {seconds}s")

        failures = [r for r in results if r.status == "failed"]
        if failures:
            print()
            print("FAILURES:")
            for r in failures:
                print(f"  {r.bin_dir}: {r.error}")


# ── CLI ───────────────────────────────────────────────────────────


def _find_project_root() -> Path:
    """Walk up from this script's location looking for pyproject.toml."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # Fallback: assume scripts/ is one level below project root
    return Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download BSEE datasets and replace LFS stub .bin files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show download plan without executing.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel download threads (default: 4).",
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="Refresh only this bin subdirectory (e.g. 'platstruc').",
    )
    parser.add_argument(
        "--skip-ogor",
        action="store_true",
        help="Skip OGOR-A yearly production files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh datasets that are already real data (not just LFS "
        "stubs).  Each replaced bin is backed up to <name>.bak-<UTCstamp>. "
        "NOTE: OGOR-A year mapping is stale (no ogora2025delimit entry, and "
        "ogoradelimit now = the current in-progress year); for recent "
        "production use scripts/refresh_bsee_ogor_recent.py instead.",
    )
    args = parser.parse_args()

    project_root = _find_project_root()
    log.info("Project root: %s", project_root)

    # Ensure url_registry is importable
    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from worldenergydata.bsee.data.refresh.url_registry import (
        DatasetSpec,
        get_all_specs,
        get_ogor_a_specs,
        get_regular_specs,
        get_specs_for_dir,
    )

    # Build spec list based on CLI flags
    if args.dir:
        specs = get_specs_for_dir(args.dir)
        if not specs:
            log.error("No specs found for directory '%s'", args.dir)
            sys.exit(1)
        log.info("Filtered to %d spec(s) for dir '%s'", len(specs), args.dir)
    elif args.skip_ogor:
        specs = list(get_regular_specs())
        log.info("Skipping OGOR-A: %d regular specs", len(specs))
    else:
        specs = list(get_all_specs())
        log.info("Full refresh: %d total specs", len(specs))

    orchestrator = BSEERefreshOrchestrator(
        project_root=project_root,
        workers=args.workers,
        dry_run=args.dry_run,
        force=args.force,
    )
    if args.force and not args.dry_run:
        log.info("FORCE mode: existing bins backed up to .bak-%s", orchestrator.run_tag)

    results = orchestrator.refresh_all(specs)
    orchestrator.print_summary(results)

    if any(r.status == "failed" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
