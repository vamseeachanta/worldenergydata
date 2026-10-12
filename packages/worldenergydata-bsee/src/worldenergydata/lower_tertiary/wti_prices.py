# ABOUTME: Loads and extends WTI price series beyond the V30 baseline (Jul 2025) through Oct 2025
# ABOUTME: Prefers a pinned local snapshot, then EIA GitHub, FRED, and flat-forward
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import time
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Optional

import pandas as pd

try:
    import requests

    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from worldenergydata.lower_tertiary.v30_reproducer import (
    load_v30_wti_prices as _load_v30,
)

logger = logging.getLogger(__name__)

# Phase 2 batch-3 carve: now 2 levels deeper under
# packages/worldenergydata-bsee/; repo root is parents[5] (was [3]).
PROJECT_ROOT = Path(__file__).resolve().parents[5]
LOCAL_SNAPSHOT_PATH = PROJECT_ROOT / "data/wti-monthly.csv"
MAX_CSV_BYTES = 1_000_000
WTI_USER_AGENT = (
    "WTI monthly snapshot research; " "https://api.github.com/repositories/574746314"
)

EIA_GITHUB_CSV_URL = (
    "https://raw.githubusercontent.com/datasets/oil-prices/main/data/wti-monthly.csv"
)
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_ID = "WTISPLC"
V30_LAST_PRICE = 68.39
V30_LAST_MONTH = pd.Timestamp("2025-07-01")


def load_v30_wti_prices() -> pd.DataFrame:
    """Re-export V30 WTI prices. Columns: Month (datetime), WTI_USD (float)."""
    return _load_v30()


def _parse_wti_csv(
    csv_input: Path | BytesIO | StringIO,
    after_date: pd.Timestamp,
    through_date: pd.Timestamp,
) -> pd.DataFrame:
    """Normalize mirror CSV dates and select only the requested extension."""
    raw = pd.read_csv(csv_input)
    raw.columns = [c.strip() for c in raw.columns]
    raw = raw.rename(columns={"Date": "Month", "Price": "WTI_USD"})
    raw["Month"] = pd.to_datetime(raw["Month"], errors="coerce")
    raw["Month"] = raw["Month"].dt.to_period("M").dt.to_timestamp()
    raw["WTI_USD"] = pd.to_numeric(raw["WTI_USD"], errors="coerce")
    raw = raw.dropna(subset=["Month", "WTI_USD"])
    subset = raw[(raw["Month"] > after_date) & (raw["Month"] <= through_date)]
    return subset[["Month", "WTI_USD"]].reset_index(drop=True)


def _load_local_snapshot_prices(
    after_date: pd.Timestamp, through_date: pd.Timestamp
) -> Optional[pd.DataFrame]:
    """Read the pinned snapshot; expose missing or invalid input at WARNING."""
    try:
        subset = _parse_wti_csv(LOCAL_SNAPSHOT_PATH, after_date, through_date)
    except (OSError, ValueError, KeyError, pd.errors.ParserError):
        logger.warning(
            "WTI local snapshot missing or unparseable; "
            "refresh data/wti-monthly.csv — see data/wti-monthly.PROVENANCE.md"
        )
        return None
    if subset.empty:
        return None
    subset["source"] = "local_snapshot"
    return subset


def _download_wti_csv() -> bytes:
    """One bounded request; refusals/timeouts propagate without retrying."""
    time.sleep(2)
    with requests.get(
        EIA_GITHUB_CSV_URL,
        timeout=15,
        stream=True,
        headers={"User-Agent": WTI_USER_AGENT},
    ) as response:
        response.raise_for_status()
        payload = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            if len(payload) + len(chunk) > MAX_CSV_BYTES:
                raise ValueError("WTI CSV exceeds 1000000-byte response limit")
            payload.extend(chunk)
    return bytes(payload)


def _fetch_eia_github_prices(
    after_date: pd.Timestamp,
    through_date: pd.Timestamp,
) -> Optional[pd.DataFrame]:
    """Download bounded public mirror CSV; return None on fetch/parse failure."""
    if not _HAS_REQUESTS:
        logger.info("requests not installed; skipping EIA GitHub source")
        return None
    try:
        subset = _parse_wti_csv(BytesIO(_download_wti_csv()), after_date, through_date)
    except Exception:
        logger.warning("Failed to fetch or parse EIA GitHub CSV", exc_info=True)
        return None
    if subset.empty:
        logger.info("EIA GitHub CSV has no data after %s", after_date)
        return None
    subset["source"] = "eia_github"
    return subset


def _fetch_fred_prices(
    after_date: pd.Timestamp,
    through_date: pd.Timestamp,
) -> Optional[pd.DataFrame]:
    """Fetch WTI monthly from FRED WTISPLC series. Requires FRED_API_KEY env var."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        logger.info("FRED_API_KEY not set; skipping FRED source")
        return None
    if not _HAS_REQUESTS:
        logger.info("requests not installed; skipping FRED source")
        return None
    params = {
        "series_id": FRED_SERIES_ID,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": (after_date + pd.DateOffset(months=1)).strftime(
            "%Y-%m-%d"
        ),
        "observation_end": through_date.strftime("%Y-%m-%d"),
    }
    try:
        resp = requests.get(FRED_SERIES_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.warning("Failed to fetch FRED API data", exc_info=True)
        return None
    rows = []
    for obs in data.get("observations", []):
        value = obs.get("value", ".")
        if value != ".":
            rows.append({"Month": pd.Timestamp(obs["date"]), "WTI_USD": float(value)})
    if not rows:
        logger.info("FRED API returned no usable observations")
        return None
    df = pd.DataFrame(rows)
    df["source"] = "fred_api"
    return df[["Month", "WTI_USD", "source"]].reset_index(drop=True)


def _covered_periods(df: Optional[pd.DataFrame]) -> set:
    """Return set of Month periods already present in extension df."""
    if df is None or df.empty:
        return set()
    return set(df["Month"].dt.to_period("M"))


def _needed_months(
    v30_last: pd.Timestamp, through_ts: pd.Timestamp
) -> pd.DatetimeIndex:
    """Generate monthly date range for the gap after V30 through target date."""
    return pd.date_range(
        start=v30_last + pd.DateOffset(months=1),
        end=through_ts,
        freq="MS",
    )


def _append(base: Optional[pd.DataFrame], new: pd.DataFrame) -> pd.DataFrame:
    """Concat new rows onto base, handling None base."""
    if base is None:
        return new
    return pd.concat([base, new], ignore_index=True)


def load_extended_wti_prices(through_date: str = "2025-10-01") -> pd.DataFrame:
    """Load V30 WTI prices and extend through ``through_date``.

    Priority: local snapshot, EIA GitHub CSV, FRED API, then flat-forward.
    A two-second pause applies to every production call needing months beyond the snapshot.
    Returns DataFrame: Month (datetime), WTI_USD (float), source (str).
    """
    through_ts = pd.Timestamp(through_date)
    v30_df = _load_v30().copy()
    v30_df["source"] = "v30_xlsx"
    v30_last = v30_df["Month"].max()
    logger.info("V30 prices span %s to %s", v30_df["Month"].min(), v30_last)

    if through_ts <= v30_last:
        return v30_df[["Month", "WTI_USD", "source"]].reset_index(drop=True)

    needed = _needed_months(v30_last, through_ts)
    extension: Optional[pd.DataFrame] = None

    # 1. Pinned local snapshot
    extension = _load_local_snapshot_prices(v30_last, through_ts)
    if extension is not None:
        logger.info("Extended %d months from local snapshot", len(extension))

    # 2. Public mirror — fill uncovered months only
    uncovered = {m.to_period("M") for m in needed} - _covered_periods(extension)
    if uncovered:
        mirror_data = _fetch_eia_github_prices(v30_last, through_ts)
        if mirror_data is not None:
            existing = _covered_periods(extension)
            mirror_data = mirror_data[
                ~mirror_data["Month"].dt.to_period("M").isin(existing)
            ]
            if not mirror_data.empty:
                extension = _append(extension, mirror_data)
                logger.info("Added %d months from EIA GitHub", len(mirror_data))

    # 3. FRED API — fill uncovered months only
    uncovered = {m.to_period("M") for m in needed} - _covered_periods(extension)
    if uncovered:
        fred_data = _fetch_fred_prices(v30_last, through_ts)
        if fred_data is not None:
            existing = _covered_periods(extension)
            fred_data = fred_data[~fred_data["Month"].dt.to_period("M").isin(existing)]
            if not fred_data.empty:
                extension = _append(extension, fred_data)
                logger.info("Added %d months from FRED API", len(fred_data))

    # 4. Flat-forward for any remaining gaps
    still_missing = [
        m for m in needed if m.to_period("M") not in _covered_periods(extension)
    ]
    if still_missing:
        ff_df = pd.DataFrame({"Month": still_missing, "WTI_USD": V30_LAST_PRICE})
        ff_df["source"] = "flat_forward"
        extension = _append(extension, ff_df)
        logger.warning(
            "Flat-forwarded %d months at $%.2f; refresh data/wti-monthly.csv "
            "— see data/wti-monthly.PROVENANCE.md",
            len(ff_df),
            V30_LAST_PRICE,
        )

    # Validate Jul 2025 overlap and drop duplicate (V30 is authoritative)
    if extension is not None:
        overlap = extension[extension["Month"] == V30_LAST_MONTH]
        if not overlap.empty:
            overlap_price = overlap["WTI_USD"].iloc[0]
            if abs(overlap_price - V30_LAST_PRICE) > 0.01:
                logger.warning(
                    "Jul 2025 overlap mismatch: V30=$%.2f, extension=$%.2f",
                    V30_LAST_PRICE,
                    overlap_price,
                )
            extension = extension[extension["Month"] != V30_LAST_MONTH]

    result = pd.concat([v30_df, extension], ignore_index=True)
    result = result.sort_values("Month").reset_index(drop=True)
    return result[["Month", "WTI_USD", "source"]]


def get_wti_source_summary(prices_df: pd.DataFrame) -> dict[str, int]:
    """Return count of months from each source in the prices DataFrame."""
    all_sources = [
        "v30_xlsx",
        "local_snapshot",
        "eia_github",
        "fred_api",
        "flat_forward",
    ]
    counts = prices_df["source"].value_counts().to_dict()
    return {src: int(counts.get(src, 0)) for src in all_sources}


def emit_wti_provenance(snapshot_bytes: bytes, metadata: dict[str, Any]) -> str:
    """Emit reproducible Markdown from committed CSV and source evidence.

    Metadata is observational input, retained in the sidecar for offline replay.
    Committed CSV digest, size, row count, coverage, parsed-values hash and
    comparison differences are computed from the committed file. Retrieved
    digests, size and comparison observations are read from recorded metadata.
    Content identity is checked by reconstructing and hashing the CRLF bytes.
    """
    prices = _parse_wti_csv(
        BytesIO(snapshot_bytes), pd.Timestamp("1900-01-01"), pd.Timestamp("2100-01-01")
    )
    monthly = dict(zip(prices["Month"].dt.strftime("%Y-%m"), prices["WTI_USD"]))
    rows = list(csv.reader(StringIO(snapshot_bytes.decode("utf-8"), newline="")))
    parsed_hash = hashlib.sha256(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    retrieved = metadata.get("mirror_snapshot", {})
    normalisation = metadata.get("line_ending_normalisation", {})
    reconstructed = snapshot_bytes.replace(b"\n", b"\r\n")
    content_identical = (
        b"\r" not in snapshot_bytes
        and hashlib.sha256(reconstructed).hexdigest() == retrieved.get("sha256")
        and len(reconstructed) == retrieved.get("size_bytes")
    )
    identity = (
        "The snapshot is content-identical; line endings normalised to LF as\n"
        "required by the repository's mixed-line-ending hook. The only difference\n"
        f"is removal of {len(reconstructed) - len(snapshot_bytes)} CR bytes."
        if content_identical
        else "Content identity is not established."
    )
    basis = metadata.get("source_price_basis", {})
    lines_basis = (
        "Monthly values are an unweighted average of the daily closing spot prices\n"
        "for a given product over the specified time period. Units: Dollars per Barrel.\n"
        f"Source: [{basis.get('title')}]({basis.get('url')}); "
        f"retrieved {basis.get('retrieved_at_utc', '')[:10]}.\n"
        "The mirror labels each month with the 15th; this date represents the\n"
        "month's average, rather than a price observed on that day.\n"
        f"Mirror documentation: [date conventions]({basis.get('label_url')}); "
        f"retrieved {basis.get('label_retrieved_at_utc', '')[:10]}."
        if basis
        else "Monthly price basis is not established from recorded source evidence."
    )
    lines = [
        "# WTI monthly snapshot provenance",
        "",
        "Source: U.S. Energy Information Administration, Cushing WTI spot price.",
        lines_basis,
        "",
        f"CSV SHA-256 as retrieved: `{retrieved.get('sha256', 'not established')}`",
        f"CSV size as retrieved (bytes): {retrieved.get('size_bytes', 'not established')}",
        f"CSV SHA-256 as committed: `{hashlib.sha256(snapshot_bytes).hexdigest()}`",
        f"CSV size as committed (bytes): {len(snapshot_bytes)}",
        f"Coverage: {min(monthly)} through {max(monthly)} ({len(prices)} rows).",
        "",
        identity,
        "Parsed-values SHA-256 as retrieved: "
        f"`{normalisation.get('retrieved_parsed_values_sha256', 'not established')}`",
        f"Parsed-values SHA-256 as committed: `{parsed_hash}`",
        "The parsed-values hash is SHA-256 of the UTF-8 bytes of",
        '`json.dumps(rows, ensure_ascii=False, separators=(",", ":"))`, where rows',
        "contains every csv.reader row, header first, as lists of unchanged strings.",
        "V30 workbook rows remain authoritative; the snapshot supplies extension months "
        "only after the workbook's last month.",
        "The July 2025 overlap criterion is within $0.01 of $68.39.",
        "",
        "## EIA origin comparison",
        "",
        "Difference is mirror minus EIA. Missing means not established.",
        "",
        "| Month | Mirror (USD/bbl) | EIA (USD/bbl) | Difference (USD/bbl) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for month, eia_price in sorted(metadata["eia_observations_usd_per_barrel"].items()):
        if month in monthly:
            mirror_price = monthly[month]
            lines.append(
                f"| {month} | {mirror_price:.2f} | {eia_price:.2f} | "
                f"{mirror_price - eia_price:.2f} |"
            )
        else:
            lines.append(f"| {month} | Missing | {eia_price:.2f} | Not established |")
    lines += [
        "",
        "## Recorded source evidence and emitter inputs",
        "",
        "```json",
        json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False),
        "```",
        "",
        "## Refresh and reproduce",
        "",
        "Fetch the listed public mirror only after reviewing its terms. Use one",
        "connection, a 15-second timeout, a 1,000,000-byte limit and a 2-second pause.",
        "Record new source metadata and repeat the keyless EIA comparison before",
        "replacing the pin. Extract the JSON block to `wti-source-evidence.json`.",
        "Regenerate this sidecar with:",
        "",
        "```sh",
        "python -m worldenergydata.lower_tertiary.wti_prices "
        "--snapshot data/wti-monthly.csv --metadata wti-source-evidence.json "
        "--provenance data/wti-monthly.PROVENANCE.md",
        "```",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Emit pinned WTI provenance offline")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    args.provenance.write_text(
        emit_wti_provenance(
            args.snapshot.read_bytes(), json.loads(args.metadata.read_text())
        ),
        encoding="utf-8",
    )
