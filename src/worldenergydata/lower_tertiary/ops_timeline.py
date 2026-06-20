"""ABOUTME: BSEE WAR/OGOR operations-timeline helpers (promoted from scripts/).
ABOUTME: Deterministic well-operation milestones + the .bin OGOR-A loader fallback.

These helpers were previously defined inline in
``scripts/lower_tertiary/generate_field_economics_report.py``. They are promoted
here so the engine path (``uv run python -m worldenergydata <input.yml>``) and
other ``src/`` modules (e.g. the well-benchmarking orchestrator) can import them
without ``sys.path`` hacks. Behaviour is unchanged: the report generator now
re-exports these names from this module.

Two responsibilities live here:

1.  **OGOR-A ``.bin`` fallback loader.** The V30 reproducer reads OGOR-A from
    yearly ``.zip`` archives. When a checkout only carries the pickled ``.bin``
    DataFrames, :func:`ensure_ogor_loader` monkeypatches ``load_ogor_production``
    to read the headerless ``.bin`` files using the exact same column schema /
    normalisation as the zip loader, so downstream aggregation is identical.

2.  **Operations timeline.** Deterministic well-operation milestones (well-added
    / completion / workover / recompletion / re-entry / sidetrack / spud) derived
    from BSEE WAR (Well Activity Reports) + OGOR-A production. Markers only; they
    do not feed any cashflow model.
"""

from __future__ import annotations

import functools
from pathlib import Path

import pandas as pd

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.lower_tertiary import v30_reproducer

# Column schema for headerless OGOR-A files (identical to the zip loader's).
OGOR_COLUMNS = [
    "LEASE_NUMBER",
    "COMPLETION_NAME",
    "PRODUCTION_DATE",
    "DAYS_ON_PROD",
    "PRODUCT_CODE",
    "MON_O_PROD_VOL",
    "MON_G_PROD_VOL",
    "MON_WTR_PROD_VOL",
    "API_WELL_NUMBER",
    "WELL_STAT_CD",
    "AREA_CODE_BLOCK_NUM",
    "OPERATOR_NUM",
    "SORT_NAME",
    "BOEM_FIELD",
    "INJECTION_VOLUME",
    "PROD_INTERVAL_CD",
    "FIRST_PROD_DATE",
    "UNIT_AGT_NUMBER",
    "UNIT_ALOC_SUFFIX",
]

# WAR activity-code -> human label. Source: BSEE Well Activity Report codes.
WAR_ACTIVITY_LABELS = {
    "DRL": "Drilling",
    "COM": "Completion",
    "WO": "Workover",
    "REC": "Recompletion",
    "ST": "Sidetrack",
    "CHZ": "Casing/Hole repair",
    "TA": "Temporary abandonment",
    "PA": "Plug & abandon",
    "PND": "Pending / suspended",
    "DSI": "Drilling suspended",
    "MPF": "Multi-phase / facility work",
    "TBK": "Test / tubing work",
}

# Activity codes that constitute a "critical operation" that moves field value:
#   - first production of a well (well-added) -> derived from OGOR, not WAR
#   - workover / recompletion / re-entry / sidetrack -> WAR
INTERVENTION_CODES = {"WO", "REC", "ST"}


# ---------------------------------------------------------------------------
# .bin OGOR loader (used only when the .zip archives are not present)
# ---------------------------------------------------------------------------


def _ogor_bin_dir() -> Path:
    return get_module_data_safe("bsee") / "bin" / "historical_production_yearly"


def _zips_present() -> bool:
    zip_dir = get_module_data_safe("bsee") / "zip" / "historical_production_yearly"
    if not zip_dir.exists():
        return False
    return any(zip_dir.glob("ogora*delimit.zip"))


@functools.lru_cache(maxsize=8)
def _load_ogor_from_bin_cached(start_year: int, end_year: int) -> pd.DataFrame:
    """Memoized OGOR-A ``.bin`` read (each frame is ~300MB; loaded once)."""
    return _load_ogor_from_bin_uncached(start_year, end_year)


def load_ogor_from_bin(start_year: int = 2000, end_year: int = 2026) -> pd.DataFrame:
    """Read OGOR-A production from headerless pickled ``.bin`` DataFrames.

    Replicates the normalisation that
    :func:`v30_reproducer.load_ogor_production` applies to the zip-sourced
    frames so that downstream aggregation is identical.

    The yearly archives are named ``ogora<year>delimit.bin``. BSEE keeps the
    most-recent (in-progress) year in an *un-suffixed* ``ogoradelimit.bin``
    (currently 2026: periods 202601-202604); that file is enumerated whenever
    its in-file year falls within ``[start_year, end_year]`` so the latest
    months are not silently dropped.

    The parsed frame is memoized and returned as a copy: a benchmark run reads
    the same window several times (well selection, per-well production, decline)
    and the ~300MB deserialization otherwise dominates. Callers always slice +
    ``.copy()`` before mutating, so handing out copies keeps this safe.
    """
    return _load_ogor_from_bin_cached(start_year, end_year).copy()


def _load_ogor_from_bin_uncached(
    start_year: int = 2000, end_year: int = 2026
) -> pd.DataFrame:
    bin_dir = _ogor_bin_dir()

    bin_paths: list[Path] = []
    for year in range(start_year, end_year + 1):
        p = bin_dir / f"ogora{year}delimit.bin"
        if p.exists():
            bin_paths.append(p)
    # Un-suffixed current-year file (e.g. 2026). Include it when its year is in
    # range; detect the year from its first PRODUCTION_DATE period (YYYYMM).
    current = bin_dir / "ogoradelimit.bin"
    if current.exists():
        try:
            cur_raw = pd.read_pickle(current)  # nosec B301 - trusted pipeline-generated local .bin/.pkl (BSEE), not untrusted input
            periods = pd.to_numeric(
                pd.Series([cur_raw.columns[2]] + list(cur_raw.iloc[:, 2])),
                errors="coerce",
            ).dropna()
            cur_year = int(periods.min()) // 100 if len(periods) else None
        except Exception:
            cur_year = None
        if cur_year is not None and start_year <= cur_year <= end_year:
            bin_paths.append(current)

    frames: list[pd.DataFrame] = []
    for bin_path in bin_paths:
        raw = pd.read_pickle(bin_path)  # nosec B301 - trusted pipeline-generated local .bin/.pkl (BSEE), not untrusted input
        # Headerless: column names are the first data row. Rebuild with the
        # canonical column names and prepend the header row as data.
        header_as_row = pd.DataFrame(
            [list(raw.columns)], columns=OGOR_COLUMNS[: raw.shape[1]]
        )
        body = raw.copy()
        body.columns = OGOR_COLUMNS[: raw.shape[1]]
        frame = pd.concat([header_as_row, body], ignore_index=True)
        frames.append(frame)

    if not frames:
        raise FileNotFoundError(f"No OGOR .bin production files found in {bin_dir}")

    df = pd.concat(frames, ignore_index=True)

    df["LEASE_NUMBER"] = (
        df["LEASE_NUMBER"]
        .astype(str)
        .str.strip()
        .str.replace('"', "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.upper()
    )
    df["MON_O_PROD_VOL"] = pd.to_numeric(
        df["MON_O_PROD_VOL"].astype(str).str.replace('"', "", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0.0)
    for col in ("PRODUCT_CODE", "WELL_STAT_CD"):
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .str.replace('"', "", regex=False)
            .str.upper()
        )
    df["PRODUCTION_DATE"] = pd.to_numeric(df["PRODUCTION_DATE"], errors="coerce")
    df["date"] = pd.to_datetime(df["PRODUCTION_DATE"], format="%Y%m", errors="coerce")
    return df


def detect_latest_ogor_month() -> pd.Timestamp:
    """Auto-detect the latest fully-available OGOR-A production month.

    Scans every OGOR-A ``.bin`` file (yearly ``ogora<year>delimit.bin`` plus the
    un-suffixed current-year ``ogoradelimit.bin``) and returns the month-start
    of the maximum ``PRODUCTION_DATE`` period found. Reads from data, never
    hardcoded.
    """
    bin_dir = _ogor_bin_dir()
    max_period: int | None = None
    for bin_path in sorted(bin_dir.glob("ogora*delimit.bin")):
        if ".bak" in bin_path.name:
            continue
        raw = pd.read_pickle(bin_path)  # nosec B301 - trusted pipeline-generated local .bin/.pkl (BSEE), not untrusted input
        periods = pd.to_numeric(
            pd.Series([raw.columns[2]] + list(raw.iloc[:, 2])),
            errors="coerce",
        ).dropna()
        if len(periods):
            file_max = int(periods.max())
            if max_period is None or file_max > max_period:
                max_period = file_max
    if max_period is None:
        raise FileNotFoundError(f"No OGOR .bin files found in {bin_dir}")
    return pd.Timestamp(f"{max_period // 100}-{max_period % 100:02d}-01")


def month_end_str(month_start: pd.Timestamp) -> str:
    """Return the YYYY-MM-DD of the last day of ``month_start``'s month."""
    return str((month_start + pd.offsets.MonthEnd(0)).date())


def ensure_ogor_loader() -> str:
    """If OGOR zips are missing, monkeypatch the loader to read .bin instead.

    Returns a short string describing which source is used (for the report).
    """
    if _zips_present():
        return "BSEE OGOR-A yearly zip archives"
    v30_reproducer.load_ogor_production = load_ogor_from_bin  # type: ignore[assignment]
    # The financial reproducer imported the symbol by reference; patch there too.
    import worldenergydata.lower_tertiary.v30_financial_reproducer as fin

    fin.load_ogor_production = load_ogor_from_bin  # type: ignore[assignment]
    return "BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)"


# ---------------------------------------------------------------------------
# Operations timeline from WAR + OGOR
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=4)
def _read_war_bin(name: str) -> pd.DataFrame:
    """Read a WAR .bin once and memoize it.

    The WAR tables (~64MB combined) are read for every lease and every window;
    deriving operations for a multi-lease field otherwise deserializes the same
    pickles dozens of times. Callers copy before mutating, so caching is safe.
    """
    war_dir = get_module_data_safe("bsee") / "bin" / "war"
    return pd.read_pickle(war_dir / name)  # nosec B301 - trusted pipeline-generated local .bin/.pkl (BSEE), not untrusted input


def _norm_lease(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.strip()
        .str.upper()
        .str.replace('"', "", regex=False)
        .str.replace(" ", "", regex=False)
    )


def derive_first_production_dates(
    lease_num: str, end_date: str = "2025-05-31"
) -> pd.DataFrame:
    """First production month per API well for a lease (well-added events)."""
    end_year = max(2025, int(end_date[:4]))
    ogor = v30_reproducer.load_ogor_production(start_year=2000, end_year=end_year)
    ogor = ogor[(ogor["date"] >= "2000-09-01") & (ogor["date"] <= end_date)]
    ogor = ogor[ogor["LEASE_NUMBER"] == lease_num.upper()]
    ogor = ogor[ogor["MON_O_PROD_VOL"] > 0].copy()
    if ogor.empty:
        return pd.DataFrame(columns=["API_WELL_NUMBER", "date", "operation", "detail"])
    ogor["API_WELL_NUMBER"] = ogor["API_WELL_NUMBER"].astype(str).str.strip()
    first = (
        ogor.sort_values("date")
        .groupby("API_WELL_NUMBER", as_index=False)["date"]
        .min()
    )
    first["operation"] = "Well online (first production)"
    first["detail"] = first["API_WELL_NUMBER"].apply(lambda a: f"API {a}")
    return first[["API_WELL_NUMBER", "date", "operation", "detail"]]


def derive_war_operations(lease_num: str, end_date: str = "2025-05-31") -> pd.DataFrame:
    """Critical well operations from WAR data for a lease.

    Returns drilling/completion spud-style milestones plus interventions
    (workover/recompletion/sidetrack). Each row: API_WELL_NUMBER, date,
    operation, detail.
    """
    main = _read_war_bin("mv_war_main.bin")
    prop = _read_war_bin("mv_war_main_prop.bin")

    main = main.copy()
    main["SURF_LEASE_NUM"] = _norm_lease(main["SURF_LEASE_NUM"])
    main = main[main["SURF_LEASE_NUM"] == lease_num.upper()]
    if main.empty:
        return pd.DataFrame(columns=["API_WELL_NUMBER", "date", "operation", "detail"])

    j = main.merge(
        prop[["SN_WAR", "WELL_ACTIVITY_CD"]],
        on="SN_WAR",
        how="left",
    )
    j["act"] = j["WELL_ACTIVITY_CD"].astype(str).str.strip().str.upper()
    j["date"] = pd.to_datetime(j["WAR_START_DT"], errors="coerce")
    j["API_WELL_NUMBER"] = j["API_WELL_NUMBER"].astype(str).str.strip()
    j = j.dropna(subset=["date"])
    j = j[j["date"] <= end_date]

    rows: list[dict] = []
    # For each well + activity-code, take the earliest WAR date as the
    # milestone for that operation phase (deterministic).
    grouped = (
        j.groupby(["API_WELL_NUMBER", "WELL_NAME", "act"], as_index=False)["date"]
        .min()
        .sort_values("date")
    )
    for _, r in grouped.iterrows():
        code = r["act"]
        # Drilling (DRL) is sourced from drilling-data spud dates (more
        # complete + cost-aligned) via derive_spud_milestones; keep only
        # completions and interventions from WAR here to avoid duplicates.
        if code == "COM" or code in INTERVENTION_CODES:
            label = WAR_ACTIVITY_LABELS.get(code, code)
            well = str(r["WELL_NAME"]).strip()
            rows.append(
                {
                    "API_WELL_NUMBER": r["API_WELL_NUMBER"],
                    "date": r["date"],
                    "operation": label,
                    "detail": f"{well} ({r['API_WELL_NUMBER']})",
                }
            )
    return pd.DataFrame(
        rows, columns=["API_WELL_NUMBER", "date", "operation", "detail"]
    )


def detect_reentries(lease_num: str, end_date: str = "2025-05-31") -> pd.DataFrame:
    """Detect re-entries / recompletions via API completion-suffix changes.

    BSEE encodes recompletions / re-entries as a new completion suffix on the
    same wellbore (e.g. ``...3300`` -> ``...3301``). The first WAR/production
    record for a non-zero suffix on an existing wellbore marks a re-entry.
    """
    main = _read_war_bin("mv_war_main.bin").copy()
    main["SURF_LEASE_NUM"] = _norm_lease(main["SURF_LEASE_NUM"])
    main = main[main["SURF_LEASE_NUM"] == lease_num.upper()]
    if main.empty:
        return pd.DataFrame(columns=["API_WELL_NUMBER", "date", "operation", "detail"])
    main["date"] = pd.to_datetime(main["WAR_START_DT"], errors="coerce")
    main["API_WELL_NUMBER"] = main["API_WELL_NUMBER"].astype(str).str.strip()
    main = main.dropna(subset=["date"])
    main = main[main["date"] <= end_date]

    # Wellbore = first 12 digits of API; suffix = remaining digits.
    main["wellbore"] = main["API_WELL_NUMBER"].str[:12]
    main["suffix"] = main["API_WELL_NUMBER"].str[12:]
    rows: list[dict] = []
    for wb, grp in main.groupby("wellbore"):
        suffixes = sorted(grp["suffix"].dropna().unique())
        nonzero = [s for s in suffixes if s and s.strip("0")]
        for sfx in nonzero:
            sub = grp[grp["suffix"] == sfx]
            first_date = sub["date"].min()
            well = str(sub["WELL_NAME"].iloc[0]).strip()
            api = sub["API_WELL_NUMBER"].iloc[0]
            rows.append(
                {
                    "API_WELL_NUMBER": api,
                    "date": first_date,
                    "operation": "Re-entry / recompletion",
                    "detail": f"{well} ({api}, suffix {sfx})",
                }
            )
    return pd.DataFrame(
        rows, columns=["API_WELL_NUMBER", "date", "operation", "detail"]
    )


def derive_spud_milestones(dev_name: str, end_date: str = "2025-05-31") -> pd.DataFrame:
    """Drilling (spud) milestones from the V30 drilling data for a development.

    The WAR feed only reaches back to ~2014, so it misses early appraisal
    bores — yet the cashflow model dates D&C capital from ``WELL_SPUD_DATE``
    (``_get_dev_dnc_dates``). Pulling spud dates from the SAME drilling source
    the cost model uses makes the annotations align with the early outflows
    (e.g. Julia's 2008 appraisal bore), closing that gap. One marker per
    wellbore spud (re-drills/sidetracks each carry their own spud date).
    """
    from worldenergydata.lower_tertiary.v30_financial_reproducer import _norm_name
    from worldenergydata.lower_tertiary.v30_reproducer import (
        load_v30_drilling,
        load_v30_leases,
    )

    dnc = load_v30_drilling().copy()
    leases = load_v30_leases()
    lease_name_to_dev = dict(
        zip(leases["LEASE_NAME"].apply(_norm_name), leases["DEV_NAME"])
    )
    dnc["development"] = dnc["LEASE_NAME"].apply(_norm_name).map(lease_name_to_dev)
    dnc = dnc[dnc["development"] == dev_name].copy()
    dnc["date"] = pd.to_datetime(dnc["WELL_SPUD_DATE"], errors="coerce")
    dnc = dnc.dropna(subset=["date"])
    dnc = dnc[dnc["date"] <= end_date]
    rows: list[dict] = []
    for _, r in dnc.sort_values("date").iterrows():
        well = str(r.get("WELL_NAME", "")).strip()
        api = str(r.get("API_WELL_NUMBER", "")).strip()
        rows.append(
            {
                "API_WELL_NUMBER": api,
                "date": r["date"],
                "operation": "Drilling (spud)",
                "detail": well or api,
            }
        )
    return pd.DataFrame(
        rows, columns=["API_WELL_NUMBER", "date", "operation", "detail"]
    )


def leases_for_dev(dev_name: str) -> list[str]:
    """All V30 lease numbers mapped to *dev_name* (deterministic, sorted).

    Lets a multi-lease field (e.g. Jack St Malo spans 6 leases) be reported
    without the caller naming each lease — the operations timeline then covers
    every lease's wells, not just one.
    """
    from worldenergydata.lower_tertiary.v30_reproducer import load_v30_leases

    lz = load_v30_leases()
    return sorted(
        {
            str(ln).strip().upper()
            for ln, dev in zip(lz["LEASE_NUM"], lz["DEV_NAME"])
            if dev == dev_name and str(ln).strip()
        }
    )


def build_operations_timeline(
    leases: str | list[str],
    end_date: str = "2025-05-31",
    dev_name: str | None = None,
) -> pd.DataFrame:
    """Combined, de-duplicated, deterministic operations timeline for a field.

    ``leases`` may be a single lease number or a list (multi-lease fields).
    Drilling milestones come from the drilling data (spud dates, cost-aligned
    and complete back to first appraisal); WAR supplies completions and
    interventions (workover/recompletion/sidetrack). ``dev_name`` enables the
    drilling-data spud markers; without it, drilling falls back to WAR only.
    """
    if isinstance(leases, str):
        leases = [leases]
    parts: list[pd.DataFrame] = []
    for lease_num in leases:
        parts.append(derive_first_production_dates(lease_num, end_date))
        parts.append(derive_war_operations(lease_num, end_date))
        parts.append(detect_reentries(lease_num, end_date))
    if dev_name:
        parts.append(derive_spud_milestones(dev_name, end_date))
    non_empty = [p for p in parts if not p.empty]
    if not non_empty:
        return pd.DataFrame(columns=["API_WELL_NUMBER", "date", "operation", "detail"])
    ops = pd.concat(non_empty, ignore_index=True)
    # Collapse only TRULY identical events across leases. Key on the wellbore
    # API + date + operation (+ detail) so distinct wells that happen to share a
    # name/date are NOT merged (human-readable detail alone is unsafe identity).
    ops = ops.drop_duplicates(subset=["API_WELL_NUMBER", "date", "operation", "detail"])
    ops["month"] = ops["date"].dt.to_period("M").dt.to_timestamp()
    ops = ops.sort_values(["date", "operation"]).reset_index(drop=True)
    return ops
