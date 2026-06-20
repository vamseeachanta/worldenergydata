"""Empirical well-access calibration from the local BSEE subset (#510).

See package docstring for the design contract. Every public parameter is tagged
``measured`` (with a ``sample_size``) or ``needs_full_dataset`` (structure only,
*never* a fabricated rate).
"""
from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# --- Reuse the WAR taxonomy + rig-day convention (don't rebuild) -------------
# These constants live in lower_tertiary.ops_timeline; mirror them here only as
# a fallback so this package stays importable when the heavy ops_timeline module
# (which depends on v30_reproducer / pydantic-laden config) cannot be imported.
# Source of truth: worldenergydata.lower_tertiary.ops_timeline.
INTERVENTION_CODES = {"WO", "REC", "ST"}
WAR_ACTIVITY_LABELS = {
    "WO": "Workover",
    "REC": "Recompletion",
    "ST": "Sidetrack",
}
# Ordered list of the intervention types the engine calibrates (issue #510).
INTERVENTION_TYPES = ["WO", "REC", "ST"]

# WAR coverage in BSEE reaches back only ~2014; flag rates below this.
WAR_COVERAGE_START_YEAR = 2014
# Below this many events for a given type, mark the rate low-confidence.
MIN_EVENTS_FOR_CONFIDENT_RATE = 30


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------
@dataclass
class ParamSource:
    """A single calibration parameter with hard data-vs-assumption provenance.

    ``source`` is exactly one of:
      - ``"measured"``           -> ``value`` derived from the local data;
                                    ``sample_size`` is the n it was measured over.
      - ``"needs_full_dataset"`` -> ``value`` is ``None``; the parameter is part of
                                    the calibration *structure* but cannot be
                                    grounded on the available subset. No rate is
                                    fabricated.
    """

    name: str
    value: Optional[float]
    units: str
    source: str  # "measured" | "needs_full_dataset"
    sample_size: int = 0
    confidence: str = "n/a"  # "high" | "low" | "n/a"
    note: str = ""

    def __post_init__(self) -> None:
        if self.source not in ("measured", "needs_full_dataset"):
            raise ValueError(f"invalid source {self.source!r}")
        if self.source == "needs_full_dataset" and self.value is not None:
            raise ValueError("needs_full_dataset params must have value=None")
        if self.source == "measured" and self.value is None:
            raise ValueError("measured params must have a non-None value")


@dataclass
class CalibrationResult:
    """Structured calibration output. Serializes to ``calibration.yml``."""

    provenance: dict = field(default_factory=dict)
    intervention_rates: list = field(default_factory=list)  # ParamSource[]
    intervention_durations: list = field(default_factory=list)  # ParamSource[]
    uptime: list = field(default_factory=list)  # ParamSource[]

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "provenance": self.provenance,
            "intervention_rates": [asdict(p) for p in self.intervention_rates],
            "intervention_durations": [asdict(p) for p in self.intervention_durations],
            "uptime": [asdict(p) for p in self.uptime],
        }


# ---------------------------------------------------------------------------
# Data resolution (import-light: by-path fallback when common.__init__ blocks)
# ---------------------------------------------------------------------------
def _resolve_bsee_root() -> Path:
    """Return the local BSEE module-data root, import-light.

    Tries the normal package import first; if the heavy ``common`` __init__
    blocks it (e.g. missing pydantic, #407/#451/#418), loads ``data_resolver``
    by file path.
    """
    try:
        from worldenergydata.common.data_resolver import get_module_data_safe

        return get_module_data_safe("bsee")
    except Exception:
        here = Path(__file__).resolve()
        # .../src/worldenergydata/bsee/analysis/well_access_calibration/calibrator.py
        resolver_path = (
            here.parents[3] / "common" / "data_resolver.py"
        )
        spec = importlib.util.spec_from_file_location(
            "_wac_data_resolver", resolver_path
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod.get_module_data_safe("bsee")


def _load_war_activity(bsee_root: Path) -> pd.DataFrame:
    """Load the WAR activity table, preferring the .bin pickles, else the CSV.

    Returns a frame with at least: ``API_WELL_NUMBER``, ``WELL_ACTIVITY_CD``,
    ``WAR_START_DT``, ``WAR_END_DT``. Empty frame if neither source is present.
    """
    cols = ["API_WELL_NUMBER", "WELL_ACTIVITY_CD", "WAR_START_DT", "WAR_END_DT"]
    war_bin = bsee_root / "bin" / "war" / "mv_war_main.bin"
    if war_bin.is_file():
        df = pd.read_pickle(war_bin)  # nosec B301 - trusted pipeline-generated local .bin/.pkl (BSEE), not untrusted input
        keep = [c for c in cols if c in df.columns]
        return df[keep].copy()
    csv = bsee_root / "current" / "operations" / "well_activity_summary.csv"
    if csv.is_file():
        df = pd.read_csv(csv)
        keep = [c for c in cols if c in df.columns]
        return df[keep].copy()
    return pd.DataFrame(columns=cols)


def _load_production(bsee_root: Path) -> pd.DataFrame:
    csv = bsee_root / "current" / "production" / "production.csv"
    if csv.is_file():
        return pd.read_csv(csv)
    return pd.DataFrame()


def _load_well_data(bsee_root: Path) -> pd.DataFrame:
    csv = bsee_root / "current" / "wells" / "well_data.csv"
    if csv.is_file():
        return pd.read_csv(csv, low_memory=False)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Core (pure) calibration from already-loaded frames
# ---------------------------------------------------------------------------
def _rig_days(start: pd.Series, end: pd.Series) -> pd.Series:
    """Duration convention reused from WellRigDays.get_war_days.

    rig_days = (WAR_END_DT - WAR_START_DT).days + 1 when positive, else the raw
    day delta. Vectorized; NaT -> NaN.
    """
    delta = (end - start).dt.days
    return delta.where(delta <= 0, delta + 1)


def calibrate_from_frames(
    war: pd.DataFrame,
    production: Optional[pd.DataFrame] = None,
    well_data: Optional[pd.DataFrame] = None,
    *,
    data_label: str = "in-memory frames",
) -> CalibrationResult:
    """Compute calibration parameters from already-loaded frames (deterministic).

    HARD separation: a parameter is ``measured`` only when grounded; otherwise it
    is emitted as ``needs_full_dataset`` with ``value=None`` (never a guessed rate).
    """
    production = production if production is not None else pd.DataFrame()
    well_data = well_data if well_data is not None else pd.DataFrame()

    rates: list = []
    durations: list = []
    uptime: list = []

    # --- normalize WAR -----------------------------------------------------
    have_war = not war.empty and {
        "WELL_ACTIVITY_CD",
        "WAR_START_DT",
    }.issubset(war.columns)
    if have_war:
        w = war.copy()
        w["WELL_ACTIVITY_CD"] = (
            w["WELL_ACTIVITY_CD"].astype(str).str.strip().str.upper()
        )
        w["_start"] = pd.to_datetime(w["WAR_START_DT"], errors="coerce")
        if "WAR_END_DT" in w.columns:
            w["_end"] = pd.to_datetime(w["WAR_END_DT"], errors="coerce")
        else:
            w["_end"] = pd.NaT
        w = w.dropna(subset=["_start"])
        total_events = int(len(w))
        wells_in_war = (
            int(w["API_WELL_NUMBER"].astype(str).str.strip().nunique())
            if "API_WELL_NUMBER" in w.columns
            else 0
        )
        year_min = int(w["_start"].dt.year.min()) if total_events else None
        year_max = int(w["_start"].dt.year.max()) if total_events else None
    else:
        w = pd.DataFrame()
        total_events = 0
        wells_in_war = 0
        year_min = year_max = None

    # --- exposure-years (groundable only if WAR wells map to spud dates) ----
    exposure_well_years = None
    exposure_n = 0
    if have_war and not well_data.empty and "WELL_SPUD_DATE" in well_data.columns:
        wd = well_data.copy()
        wd["_api12"] = (
            wd["API_WELL_NUMBER"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(12)
            .str[:12]
        )
        wd["_spud"] = pd.to_datetime(wd["WELL_SPUD_DATE"], errors="coerce")
        war_api12 = (
            w["API_WELL_NUMBER"].astype(str).str.strip().str[:12].unique()
            if "API_WELL_NUMBER" in w.columns
            else []
        )
        matched = wd[wd["_api12"].isin(war_api12)].dropna(subset=["_spud"])
        if not matched.empty:
            asof = w["_start"].max()
            years = (asof - matched["_spud"]).dt.days / 365.25
            years = years[years > 0]
            if not years.empty:
                exposure_well_years = float(years.sum())
                exposure_n = int(len(years))

    # --- per-type intervention rates + durations ---------------------------
    for code in INTERVENTION_TYPES:
        label = WAR_ACTIVITY_LABELS.get(code, code)
        sub = w[w["WELL_ACTIVITY_CD"] == code] if have_war else pd.DataFrame()
        n_events = int(len(sub))

        # frequency = events / well-exposure-years (only if exposure grounded)
        if exposure_well_years and exposure_well_years > 0:
            conf = (
                "low"
                if (
                    n_events < MIN_EVENTS_FOR_CONFIDENT_RATE
                    or (year_min is not None and year_min >= WAR_COVERAGE_START_YEAR)
                )
                else "high"
            )
            note = (
                f"events/well-exposure-year for {label}; "
                f"exposure={exposure_well_years:.1f} well-yr over {exposure_n} wells"
            )
            if year_min is not None and year_min >= WAR_COVERAGE_START_YEAR:
                note += (
                    f"; WAR window {year_min}-{year_max} (<{WAR_COVERAGE_START_YEAR} "
                    "back-history absent)"
                )
            rates.append(
                ParamSource(
                    name=f"lambda_{code}",
                    value=round(n_events / exposure_well_years, 6),
                    units="events/well-year",
                    source="measured",
                    sample_size=n_events,
                    confidence=conf,
                    note=note,
                )
            )
        else:
            rates.append(
                ParamSource(
                    name=f"lambda_{code}",
                    value=None,
                    units="events/well-year",
                    source="needs_full_dataset",
                    sample_size=n_events,
                    note=(
                        f"{n_events} {label} events present but well-exposure-years "
                        "not groundable on this subset (WAR wells do not map to "
                        "spud dates / no full OGOR exposure). Counts measured; "
                        "rate needs the materialized WAR+well dataset."
                    ),
                )
            )

        # duration distribution (mean WAR-reported rig-days), if end-dates exist
        if n_events and "_end" in sub.columns and sub["_end"].notna().any():
            dur = _rig_days(sub["_start"], sub["_end"]).dropna()
            if not dur.empty:
                conf = "low" if n_events < MIN_EVENTS_FOR_CONFIDENT_RATE else "high"
                durations.append(
                    ParamSource(
                        name=f"duration_mean_{code}",
                        value=round(float(dur.mean()), 4),
                        units="rig-days",
                        source="measured",
                        sample_size=int(len(dur)),
                        confidence=conf,
                        note=(
                            f"mean WAR-reported rig-days for {label} "
                            f"(min={dur.min():.1f}, max={dur.max():.1f}); "
                            "WAR rows are weekly-capped so durations may be "
                            "truncated to the reporting window"
                        ),
                    )
                )
                continue
        durations.append(
            ParamSource(
                name=f"duration_mean_{code}",
                value=None,
                units="rig-days",
                source="needs_full_dataset",
                sample_size=n_events,
                note=(
                    f"no usable WAR_END_DT for {label} on this subset; "
                    "duration distribution needs the full WAR dataset"
                ),
            )
        )

    # --- A_facility uptime from DAYS_ON_PROD -------------------------------
    if not production.empty and "DAYS_ON_PROD" in production.columns:
        prod = production.copy()
        prod["DAYS_ON_PROD"] = pd.to_numeric(
            prod["DAYS_ON_PROD"], errors="coerce"
        )
        prod = prod.dropna(subset=["DAYS_ON_PROD"])
        # uptime fraction = days_on_prod / calendar days in the month (assume 30.4)
        if not prod.empty:
            frac = (prod["DAYS_ON_PROD"] / 30.4).clip(upper=1.0)
            uptime.append(
                ParamSource(
                    name="A_facility",
                    value=round(float(frac.mean()), 6),
                    units="fraction",
                    source="measured",
                    sample_size=int(len(frac)),
                    confidence="low"
                    if len(frac) < MIN_EVENTS_FOR_CONFIDENT_RATE
                    else "high",
                    note="mean monthly DAYS_ON_PROD / 30.4 across production records",
                )
            )
    if not uptime:
        uptime.append(
            ParamSource(
                name="A_facility",
                value=None,
                units="fraction",
                source="needs_full_dataset",
                sample_size=0,
                note=(
                    "production subset has no DAYS_ON_PROD column "
                    "(local production.csv is API+date only); A_facility needs "
                    "the materialized OGOR/production dataset with DAYS_ON_PROD"
                ),
            )
        )

    provenance = {
        "issue": 510,
        "generated_utc": None,  # set by write_calibration_yaml for determinism control
        "data_label": data_label,
        "war_events_total": total_events,
        "war_wells": wells_in_war,
        "war_year_min": year_min,
        "war_year_max": year_max,
        "war_exposure_well_years": (
            round(exposure_well_years, 2) if exposure_well_years else None
        ),
        "war_exposure_wells": exposure_n,
        "war_coverage_note": (
            f"BSEE WAR coverage reaches back ~{WAR_COVERAGE_START_YEAR}; "
            "Lower-Tertiary intervention history is sparse -> rates flagged "
            "low-confidence"
        ),
        "circularity_guard": (
            "demand rate must be calibrated from dry-tree-capable analogs "
            "(spar/TLP); subsea analogs reserved for the access multiplier only "
            "(issue #510). This adapter emits raw per-type rates; the consuming "
            "engine applies the analog split."
        ),
    }

    return CalibrationResult(
        provenance=provenance,
        intervention_rates=rates,
        intervention_durations=durations,
        uptime=uptime,
    )


def calibrate(*, data_label: Optional[str] = None) -> CalibrationResult:
    """Calibrate from the local BSEE subset resolved via WED_DATA_ROOT/data."""
    root = _resolve_bsee_root()
    war = _load_war_activity(root)
    production = _load_production(root)
    well_data = _load_well_data(root)
    return calibrate_from_frames(
        war,
        production,
        well_data,
        data_label=data_label or f"local BSEE subset @ {root}",
    )


# ---------------------------------------------------------------------------
# Emit calibration.yml
# ---------------------------------------------------------------------------
def write_calibration_yaml(
    result: CalibrationResult,
    path: str | Path,
    *,
    timestamp: Optional[str] = None,
) -> Path:
    """Serialize a CalibrationResult to ``calibration.yml``.

    ``timestamp`` is recorded under provenance; pass a fixed value for
    deterministic output (tests do this). Defaults to UTC now.
    """
    import yaml  # local import keeps package import-light

    payload = result.to_dict()
    payload["provenance"]["generated_utc"] = (
        timestamp
        if timestamp is not None
        else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    out = Path(path)
    with out.open("w") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False, default_flow_style=False)
    return out
