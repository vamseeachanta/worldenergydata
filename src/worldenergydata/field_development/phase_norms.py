# ABOUTME: Phase-norm engine (issue #848) — per-field life-cycle stage metrics vs
# ABOUTME: leave-one-field-out play baselines, with honest degradation states.
"""Phase-norm layer for the field life-cycle hub.

For each canonical Lower Tertiary field and life-cycle stage (drill, complete,
produce, workover, abandon) this module computes the field's stage metric and a
leave-one-field-out play baseline, emitting structured ``NormEntry`` records
serialized to ``_norms.json`` for the poster generator and stage pages.

Methodological contract (plan r3, owner-approved play-norms-only v1):

- single duration basis: ``calendar_days`` (the V30 workbook's day columns are
  TD-minus-spud calendar spans for the vast majority of rows);
- a field is never part of its own baseline (leave-one-field-out);
- deltas are computed only within one basis AND one population;
- thin populations degrade to explicit states — no number is ever fabricated;
- country baselines are ROADMAP (drilling-well database, #681) except the
  all-GoM P&A context share used on the Abandon stage page.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import yaml

SCHEMA_VERSION = "1.0"
STAGES = ("drill", "complete", "produce", "workover", "abandon")

DEFAULT_CONFIG_PATH = "config/phase_norms.yml"

# metric_id -> (stage, source population, unit, aggregation, value key)
XLSX_POP = "xlsx_wellbores"
BENCH_POP = "benchmark_wells"
BASIS_DAYS = "calendar_days"
BASIS_RATIO = "ratio"
BASIS_SHARE = "count_share"

METRICS = {
    "drill_days_median": ("drill", XLSX_POP, "days", "median", "drill_days"),
    "drill_days_per_kft_median": (
        "drill",
        XLSX_POP,
        "days/1000 ft",
        "median",
        "drill_days_per_kft",
    ),
    "completion_days_median": (
        "complete",
        XLSX_POP,
        "days",
        "median",
        "compl_days",
    ),
    "uptime_median": ("produce", BENCH_POP, "%", "median", "uptime_pct"),
    "decline_median": ("produce", BENCH_POP, "%/yr", "median", "decline_annual_pct"),
    "cum_oil_median": ("produce", BENCH_POP, "MMbbl", "median", "cum_oil_mmbbl"),
    "interventions_per_well": (
        "workover",
        BENCH_POP,
        "per well",
        "mean",
        "interventions",
    ),
}

METRIC_BASIS = {
    "drill_days_median": BASIS_DAYS,
    "drill_days_per_kft_median": BASIS_RATIO,
    "completion_days_median": BASIS_DAYS,
    "uptime_median": BASIS_RATIO,
    "decline_median": BASIS_RATIO,
    "cum_oil_median": BASIS_RATIO,
    "interventions_per_well": BASIS_RATIO,
}


class BasisMismatchError(ValueError):
    """Raised when a delta would mix bases or populations."""


class JoinCoverageError(RuntimeError):
    """Raised when benchmark<->xlsx consistency falls below the config gate."""


class GoldenMismatchError(RuntimeError):
    """Raised when the recomputed play median drifts from the published figure."""


@dataclass(frozen=True)
class MetricValue:
    value: float
    n: int
    basis: str
    population: str
    aggregation: str


@dataclass(frozen=True)
class Comparator:
    status: str  # ok | insufficient | unavailable | roadmap
    metric: MetricValue | None = None
    method: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class NormEntry:
    field_id: str
    stage: str
    metric_id: str
    unit: str
    field_status: str  # ok | low_n | insufficient | unavailable | no_data
    field: MetricValue | None
    play: Comparator
    country: Comparator
    delta_play_pct: float | None
    delta_country_pct: float | None


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = repo_root() / p
    with open(p) as fh:
        return yaml.safe_load(fh)


def median(values) -> float:
    return float(statistics.median(values))


def normalize_api(raw) -> str | None:
    """Normalize an API well number to a zero-padded 12-char string.

    Handles float-formatted spreadsheet strings ('608100000001.0').
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(12)


def delta_pct(field: MetricValue, baseline: MetricValue) -> float:
    """Percent delta field-vs-baseline; refuses cross-basis/population compares."""
    if field.basis != baseline.basis or field.population != baseline.population:
        raise BasisMismatchError(
            f"cannot compare {field.basis}/{field.population} "
            f"against {baseline.basis}/{baseline.population}"
        )
    return round((field.value - baseline.value) / baseline.value * 100.0, 1)


# ---------------------------------------------------------------------------
# loaders
# ---------------------------------------------------------------------------


def _num(v) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_lt_population(xlsx_path: str | Path, cfg: dict):
    """Load the LT wellbore population from the V30 workbook.

    Returns ``(rows, exclusions)``. Rows carry per-metric values already
    censored (non-positive or over ``max_days`` durations become ``None`` and
    are counted). Blank/TOTALS trailer rows (no LEASE_NAME) and unmapped lease
    names are dropped entirely.
    """
    import openpyxl

    lease_map = cfg["lease_name_to_field"]
    max_days = cfg["max_days"]
    exclusions = {
        "blank_or_totals": 0,
        "unmapped_lease": 0,
        "drill_nonpositive": 0,
        "drill_over_max": 0,
        "compl_nonpositive": 0,
        "compl_over_max": 0,
    }

    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    header = [c for c in next(it)]
    idx = {name: header.index(name) for name in header if name}

    def censor(value, kind):
        v = _num(value)
        if v is None:
            return None
        if v <= 0:
            exclusions[f"{kind}_nonpositive"] += 1
            return None
        if v > max_days:
            exclusions[f"{kind}_over_max"] += 1
            return None
        return v

    rows = []
    for raw in it:
        lease = raw[idx["LEASE_NAME"]]
        if lease in (None, ""):
            exclusions["blank_or_totals"] += 1
            continue
        field_id = lease_map.get(str(lease).strip())
        if field_id is None:
            exclusions["unmapped_lease"] += 1
            continue
        drill = censor(raw[idx["DRILLING_DAYS"]], "drill")
        compl = censor(raw[idx["COMPLETION_DAYS"]], "compl")
        tvd = _num(raw[idx["MAX_WELL_BORE_TVD"]])
        per_kft = None
        if drill is not None and tvd and tvd > 0:
            per_kft = drill / (tvd / 1000.0)
        rows.append(
            {
                "field_id": field_id,
                "lease_name": str(lease).strip(),
                "api": normalize_api(raw[idx["API_WELL_NUMBER"]]),
                "drill_days": drill,
                "compl_days": compl,
                "tvd_ft": tvd,
                "drill_days_per_kft": per_kft,
            }
        )
    wb.close()
    return rows, exclusions


def load_benchmark(csv_path: str | Path, cfg: dict):
    """Load the per-well benchmark CSV (strings in, typed values out)."""
    field_map = cfg["benchmark_field_to_field"]
    rows = []
    with open(csv_path, newline="") as fh:
        for r in csv.DictReader(fh):
            field_id = field_map.get((r.get("field") or "").strip())
            if field_id is None:
                continue
            rows.append(
                {
                    "field_id": field_id,
                    "api": normalize_api(r.get("api12")),
                    "uptime_pct": _num(r.get("uptime_pct")),
                    "decline_annual_pct": _num(r.get("decline_annual_pct")),
                    "cum_oil_mmbbl": _num(r.get("cum_oil_mmbbl")),
                    "interventions": _num(r.get("interventions")),
                }
            )
    return rows


def benchmark_consistency(bench_rows, lt_rows) -> float:
    """Fraction of benchmark wells whose API matches an LT wellbore of the
    SAME canonical field. Validates the lease-name crosswalk."""
    if not bench_rows:
        return 1.0
    by_api = {}
    for r in lt_rows:
        if r["api"]:
            by_api[r["api"]] = r["field_id"]
    ok = sum(1 for b in bench_rows if by_api.get(b["api"]) == b["field_id"])
    return ok / len(bench_rows)


def assert_join_coverage(coverage: float, cfg: dict) -> None:
    if coverage < cfg["join_coverage_min"]:
        raise JoinCoverageError(
            f"benchmark<->xlsx field-consistency {coverage:.2%} below "
            f"gate {cfg['join_coverage_min']:.0%}"
        )


# ---------------------------------------------------------------------------
# baselines and norms
# ---------------------------------------------------------------------------


def _values(rows, field_id, key, include: bool):
    return [
        r[key]
        for r in rows
        if (r["field_id"] == field_id) == include and r.get(key) is not None
    ]


def _aggregate(values, aggregation: str) -> float:
    if aggregation == "median":
        return round(median(values), 2)
    if aggregation == "mean":
        return round(sum(values) / len(values), 2)
    raise ValueError(f"unknown aggregation {aggregation}")


def loo_baseline(rows, field_id: str, key: str, cfg: dict) -> Comparator:
    """Leave-one-field-out play baseline for ``key``."""
    metric_id = next((m for m, spec in METRICS.items() if spec[4] == key), None)
    spec = METRICS[metric_id]
    pool = _values(rows, field_id, key, include=False)
    if len(pool) < cfg["min_n"]:
        return Comparator(
            status="insufficient",
            method="leave_one_field_out",
            reason=f"baseline population n={len(pool)} < min_n={cfg['min_n']}",
        )
    mv = MetricValue(
        value=_aggregate(pool, spec[3]),
        n=len(pool),
        basis=METRIC_BASIS[metric_id],
        population=spec[1],
        aggregation=spec[3],
    )
    return Comparator(status="ok", metric=mv, method="leave_one_field_out")


def _field_metric(rows, field_id, metric_id, cfg):
    stage, population, unit, aggregation, key = METRICS[metric_id]
    vals = _values(rows, field_id, key, include=True)
    if not vals:
        return None, "no_data"
    if len(vals) < cfg["field_min_n"]:
        return None, "insufficient"
    mv = MetricValue(
        value=_aggregate(vals, aggregation),
        n=len(vals),
        basis=METRIC_BASIS[metric_id],
        population=population,
        aggregation=aggregation,
    )
    status = "low_n" if len(vals) < cfg["low_n_threshold"] else "ok"
    return mv, status


def compute_norms(lt_rows, bench_rows, cfg: dict) -> list[NormEntry]:
    """Compute all NormEntry records for every field × stage × metric."""
    country = Comparator(
        status=cfg.get("country", {}).get("status", "roadmap"),
        reason=cfg.get("country", {}).get(
            "reason", "country baseline not yet available"
        ),
    )
    entries: list[NormEntry] = []
    for field_id in cfg["field_ids"]:
        for metric_id, spec in METRICS.items():
            stage, population, unit, aggregation, key = spec
            rows = lt_rows if population == XLSX_POP else bench_rows
            field_mv, field_status = _field_metric(rows, field_id, metric_id, cfg)
            play = (
                loo_baseline(rows, field_id, key, cfg)
                if field_mv is not None
                else Comparator(
                    status="unavailable",
                    reason=f"no field-side metric ({field_status})",
                )
            )
            dp = None
            if field_mv is not None and play.status == "ok":
                dp = delta_pct(field_mv, play.metric)
            entries.append(
                NormEntry(
                    field_id=field_id,
                    stage=stage,
                    metric_id=metric_id,
                    unit=unit,
                    field_status=field_status if field_mv is None else field_status,
                    field=field_mv,
                    play=play,
                    country=country,
                    delta_play_pct=dp,
                    delta_country_pct=None,
                )
            )
        # abandon stage: field/play unavailable in v1 (no per-field abandonment
        # population); country context stat is attached page-side, not per field.
        entries.append(
            NormEntry(
                field_id=field_id,
                stage="abandon",
                metric_id="pa_share",
                unit="%",
                field_status="unavailable",
                field=None,
                play=Comparator(
                    status="unavailable",
                    reason="no per-field abandonment population in v1",
                ),
                country=Comparator(
                    status="context_only",
                    reason="all-GoM PA/TA share shown on the stage page "
                    "(vintage-mix caveat)",
                ),
                delta_play_pct=None,
                delta_country_pct=None,
            )
        )
    return entries


def compute_abandon_context(well_data_csv: str | Path, cfg: dict) -> dict:
    """All-GoM PA/TA share from BOREHOLE_STAT_CD (context stat, not a baseline)."""
    pa_codes = set(cfg["abandon"]["pa_codes"])
    total = 0
    pa = 0
    with open(well_data_csv, newline="") as fh:
        for r in csv.DictReader(fh):
            code = (r.get("BOREHOLE_STAT_CD") or "").strip()
            if not code:
                continue
            total += 1
            if code in pa_codes:
                pa += 1
    share = round(pa / total * 100.0, 1) if total else None
    return {
        "share_pct": share,
        "n": total,
        "pa_n": pa,
        "caveat": (
            "All-GoM boreholes across every vintage since the 1940s; the "
            "vintage mix (shallow-shelf era dominates) makes this a context "
            "number, not a norm for young deepwater fields."
        ),
    }


# ---------------------------------------------------------------------------
# chips + serialization
# ---------------------------------------------------------------------------


def chips_for_field(entries, field_id: str, cfg: dict) -> list[dict]:
    """Poster chip payload: one chip per stage using the configured primary metric."""
    chip_metrics = cfg["chip_metrics"]
    by_key = {(e.field_id, e.metric_id): e for e in entries}
    chips = []
    for stage in STAGES:
        metric_id = chip_metrics[stage]
        e = by_key.get((field_id, metric_id))
        if e is None or e.field is None:
            state = (
                "no_data"
                if (e is None or e.field_status == "no_data")
                else (e.field_status if e else "no_data")
            )
            chips.append(
                {
                    "stage": stage,
                    "state": state if state != "ok" else "no_data",
                    "href": f"norms/{stage}.html#{field_id}",
                }
            )
            continue
        chip = {
            "stage": stage,
            "state": e.field_status,  # ok | low_n
            "value": e.field.value,
            "unit": e.unit,
            "n": e.field.n,
            "href": f"norms/{stage}.html#{field_id}",
        }
        if e.delta_play_pct is not None:
            chip["delta_play_pct"] = e.delta_play_pct
            chip["play_n"] = e.play.metric.n
        chips.append(chip)
    return chips


def _mv_dict(mv: MetricValue | None):
    if mv is None:
        return None
    return {
        "value": mv.value,
        "n": mv.n,
        "basis": mv.basis,
        "population": mv.population,
        "aggregation": mv.aggregation,
    }


def _cmp_dict(c: Comparator):
    return {
        "status": c.status,
        "metric": _mv_dict(c.metric),
        "method": c.method,
        "reason": c.reason,
    }


def build_provenance(sources, exclusions, join_coverage, extras=None) -> dict:
    prov = {
        "sources": sources,
        "exclusions": exclusions,
        "join_coverage": join_coverage,
    }
    if extras:
        prov.update(extras)
    return prov


def sha256_of(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_norms_json(entries, provenance, out_path: str | Path, chips=None) -> None:
    doc = {
        "schema_version": SCHEMA_VERSION,
        "provenance": provenance,
        **({"chips": chips} if chips is not None else {}),
        "entries": [
            {
                "field_id": e.field_id,
                "stage": e.stage,
                "metric_id": e.metric_id,
                "unit": e.unit,
                "field_status": e.field_status,
                "field": _mv_dict(e.field),
                "play": _cmp_dict(e.play),
                "country": _cmp_dict(e.country),
                "delta_play_pct": e.delta_play_pct,
                "delta_country_pct": e.delta_country_pct,
            }
            for e in sorted(entries, key=lambda x: (x.field_id, x.stage, x.metric_id))
        ],
    }
    Path(out_path).write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )


def assert_golden(lt_rows, cfg: dict) -> None:
    """Fail the build if the recomputed play drill median drifts from the
    published drilling-insights figure."""
    drill = [r["drill_days"] for r in lt_rows if r["drill_days"] is not None]
    med = median(drill)
    want_n = cfg["golden"]["drill_population_n"]
    want_med = cfg["golden"]["drill_play_median_days"]
    if len(drill) != want_n or abs(med - want_med) > 0.05:
        raise GoldenMismatchError(
            f"drill population n={len(drill)} median={med} vs published "
            f"n={want_n} median={want_med} — reconcile filters before publishing"
        )
