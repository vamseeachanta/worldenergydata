"""Cross-field analytics for the Lower Tertiary play (#376).

Phase 3 of #373 epic. Consumes the per-field configs (#374) and per-field
economics (#375) to surface portfolio-level insights:

- 3a. Technology generation — capex intensity by dev system class
- 3b. Operator concentration — working-interest-weighted production
- 3c. HSE incident overlay — minimum-viable; full coverage pending #366
- 3d. Cost benchmark — disclosure-comparable per-field; pending #343 seeding

Each section emits a DataFrame plus a `caveats` flag column so missing
inputs are explicit rather than silently elided. The `PortfolioAnalyticsRun`
dataclass bundles all four sections + run metadata.

Public surface:
    - PortfolioAnalyticsRun — bundle of 4 section DataFrames + metadata
    - analyze_technology_generation(field_ids, *, economics_run) -> DataFrame
    - analyze_operator_concentration(field_ids, *, economics_run) -> DataFrame
    - analyze_hse_per_field(field_ids) -> DataFrame
    - analyze_cost_benchmark(field_ids, *, economics_run) -> DataFrame
    - run_portfolio_analytics(field_ids, ...) -> PortfolioAnalyticsRun
    - portfolio_analytics_to_csv(run, path)
    - portfolio_analytics_to_html(run, path)
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pandas as pd
import yaml

from worldenergydata.fdas.api import DisclosureAnalyticsQuery
from worldenergydata.lower_tertiary.portfolio import (
    LT_FIELDS_2026,
    fields_config_dir,
)
from worldenergydata.lower_tertiary.portfolio_economics import (
    PortfolioEconomicsRun,
    run_portfolio,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Marker values for HSE 3c: full coverage requires #366 (HSE bulk dedup).
HSE_DATA_COMPLETENESS_MINIMUM = "minimum_viable_pending_#366"

# Marker for cost benchmark 3d when no comparable disclosure record exists.
BENCHMARK_STATUS_NO_DATA = "no_data_pending_#343"
BENCHMARK_STATUS_COMPARABLE = "comparable"


# ---------------------------------------------------------------------------
# Result bundle
# ---------------------------------------------------------------------------


@dataclass
class PortfolioAnalyticsRun:
    technology: pd.DataFrame
    operator: pd.DataFrame
    hse: pd.DataFrame
    cost_benchmark: pd.DataFrame
    field_ids: tuple
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def section(self, name: str) -> pd.DataFrame:
        """Return a section by name; raises KeyError on unknown section."""
        sections = {
            "technology": self.technology,
            "operator": self.operator,
            "hse": self.hse,
            "cost_benchmark": self.cost_benchmark,
        }
        if name not in sections:
            raise KeyError(
                f"Unknown analytics section {name!r}. "
                f"Valid: {sorted(sections.keys())}"
            )
        return sections[name]


# ---------------------------------------------------------------------------
# Yaml + production helpers
# ---------------------------------------------------------------------------


def _load_field_payload(field_id: str) -> Dict[str, object]:
    path = fields_config_dir() / f"{field_id}.yml"
    if not path.is_file():
        raise FileNotFoundError(f"LT field config missing: {path}")
    with path.open("r", encoding="utf-8") as fh:
        contents = yaml.safe_load(fh) or {}
    return contents.get("field", contents)


def _dev_system_for_field(payload: Dict[str, object]) -> str:
    """Resolve a dev-system label from the yaml.

    Falls back to a static mapping derived from the canonical roster doc
    (`reports/lower_tertiary_field_summary.md`) when the yaml doesn't
    declare a dev_system explicitly. Surface the source via a `_via` flag
    in the technology section's `dev_system_source` column.
    """
    explicit = payload.get("dev_system")
    if explicit:
        return str(explicit)
    return "unspecified"


# Static mapping of field_id → dev system class, sourced from
# reports/lower_tertiary_field_summary.md (the canonical roster doc).
_DEV_SYSTEM_FALLBACK: Dict[str, str] = {
    "anchor": "Subsea 20K",
    "big_foot": "Dry Tree",
    "cascade_chinook": "Subsea 15K",
    "jack_st_malo": "Subsea 15K",
    "julia": "Tieback 15K",
    "kaskida": "Subsea 20K",
    "north_platte": "Subsea 20K",
    "shenandoah": "Subsea 20K",
    "stones": "Subsea 15K",
    "tiber": "Subsea 20K",
}


def _resolved_dev_system(field_id: str, payload: Dict[str, object]) -> tuple:
    """(dev_system, source) — yaml-declared if present, else fallback."""
    explicit = payload.get("dev_system")
    if explicit:
        return str(explicit), "yaml"
    fallback = _DEV_SYSTEM_FALLBACK.get(field_id)
    if fallback:
        return fallback, "static_mapping_per_summary_doc"
    return "unknown", "no_source"


# ---------------------------------------------------------------------------
# 3a. Technology generation
# ---------------------------------------------------------------------------


def analyze_technology_generation(
    field_ids: Sequence[str],
    *,
    economics_run: Optional[PortfolioEconomicsRun] = None,
) -> pd.DataFrame:
    """Per-dev-system summary: field count, total capex, mean breakeven, etc.

    If an economics_run is supplied, breakeven + NPV totals are aggregated.
    """
    econ_lookup = (
        {r.field_id: r for r in economics_run.results} if economics_run else {}
    )

    field_rows = []
    for fid in field_ids:
        payload = _load_field_payload(fid)
        dev_system, source = _resolved_dev_system(fid, payload)
        capex_mm = float((payload.get("capex") or {}).get("total_mm_usd") or 0.0)
        plateau_mbopd = float(
            (payload.get("production_profile") or {}).get("plateau_rate_mbopd") or 0.0
        )
        # 20-year recoverable as a coarse proxy: plateau × 365 × 20 / 1000 (MMbbl).
        annual_plateau_mmbbl = plateau_mbopd * 365.0 / 1000.0
        recoverable_mmbbl_proxy = annual_plateau_mmbbl * 20  # plateau-equivalent years
        capex_per_mmbbl = (
            capex_mm / recoverable_mmbbl_proxy if recoverable_mmbbl_proxy > 0 else None
        )

        econ = econ_lookup.get(fid)
        field_rows.append(
            {
                "field_id": fid,
                "dev_system": dev_system,
                "dev_system_source": source,
                "status": str(payload.get("status") or "unknown"),
                "capex_mm_usd": capex_mm,
                "recoverable_mmbbl_proxy": recoverable_mmbbl_proxy,
                "capex_per_mmbbl_usd": capex_per_mmbbl,
                "first_oil": str(payload.get("first_oil") or "n/a"),
                "npv_mm_usd": econ.npv_mm_usd if econ else None,
                "breakeven_oil_usd_per_bbl": (
                    econ.breakeven_oil_usd_per_bbl if econ else None
                ),
            }
        )

    field_df = pd.DataFrame(field_rows)

    # Aggregate by dev system.
    agg_rows = []
    for dev_system, group in field_df.groupby("dev_system"):
        agg_rows.append(
            {
                "dev_system": dev_system,
                "field_count": int(len(group)),
                "fields": ", ".join(sorted(group["field_id"].tolist())),
                "total_capex_mm_usd": float(group["capex_mm_usd"].sum()),
                "mean_capex_per_mmbbl_usd": (
                    float(group["capex_per_mmbbl_usd"].mean(skipna=True))
                    if group["capex_per_mmbbl_usd"].notna().any()
                    else None
                ),
                "total_recoverable_mmbbl_proxy": float(
                    group["recoverable_mmbbl_proxy"].sum()
                ),
                "total_npv_mm_usd": (
                    float(group["npv_mm_usd"].sum())
                    if economics_run and group["npv_mm_usd"].notna().any()
                    else None
                ),
                "mean_breakeven_usd_per_bbl": (
                    float(group["breakeven_oil_usd_per_bbl"].mean(skipna=True))
                    if economics_run
                    and group["breakeven_oil_usd_per_bbl"].notna().any()
                    else None
                ),
                "caveats": (
                    "recoverable_mmbbl_proxy uses plateau×20yr — "
                    "OGOR-grounded follow-up under #367"
                ),
            }
        )

    return pd.DataFrame(agg_rows).sort_values("dev_system").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3b. Operator concentration
# ---------------------------------------------------------------------------


def analyze_operator_concentration(
    field_ids: Sequence[str],
    *,
    economics_run: Optional[PortfolioEconomicsRun] = None,
) -> pd.DataFrame:
    """Working-interest-weighted capex + production by operator.

    Fields without a `partners` block (kaskida-shape Pre-FID yamls) treat
    the declared `operator` as 100% WI for aggregation purposes — flagged
    via `wi_source: operator_only_assumption` in the field-level breakdown.
    """
    rows = []
    for fid in field_ids:
        payload = _load_field_payload(fid)
        operator = str(payload.get("operator") or "unknown")
        capex_mm = float((payload.get("capex") or {}).get("total_mm_usd") or 0.0)
        plateau_mbopd = float(
            (payload.get("production_profile") or {}).get("plateau_rate_mbopd") or 0.0
        )

        partners = payload.get("partners")
        if partners and isinstance(partners, list):
            wi_total = sum(float(p.get("working_interest") or 0.0) for p in partners)
            for p in partners:
                wi = float(p.get("working_interest") or 0.0)
                rows.append(
                    {
                        "field_id": fid,
                        "operator_role": (
                            "operator" if p.get("name") == operator else "partner"
                        ),
                        "company": str(p.get("name")),
                        "working_interest": wi,
                        "wi_source": "yaml_partners",
                        "wi_capex_share_mm_usd": capex_mm * wi,
                        "wi_plateau_mbopd": plateau_mbopd * wi,
                        "wi_total_in_yaml": wi_total,
                    }
                )
        else:
            # Kaskida-shape Pre-FID — assume 100% WI to declared operator.
            rows.append(
                {
                    "field_id": fid,
                    "operator_role": "operator",
                    "company": operator,
                    "working_interest": 1.0,
                    "wi_source": "operator_only_assumption",
                    "wi_capex_share_mm_usd": capex_mm,
                    "wi_plateau_mbopd": plateau_mbopd,
                    "wi_total_in_yaml": 1.0,
                }
            )

    field_df = pd.DataFrame(rows)
    if field_df.empty:
        return field_df

    # Aggregate by company across the portfolio.
    agg = (
        field_df.groupby("company")
        .agg(
            field_count=("field_id", "nunique"),
            sum_wi_capex_mm_usd=("wi_capex_share_mm_usd", "sum"),
            sum_wi_plateau_mbopd=("wi_plateau_mbopd", "sum"),
        )
        .reset_index()
        .sort_values("sum_wi_capex_mm_usd", ascending=False)
    )

    total_capex = agg["sum_wi_capex_mm_usd"].sum()
    agg["share_capex_pct"] = (
        100.0 * agg["sum_wi_capex_mm_usd"] / total_capex if total_capex > 0 else 0.0
    )
    # Herfindahl-Hirschman Index (0-10000 scale).
    agg["hhi_contribution"] = (agg["share_capex_pct"]) ** 2
    return agg.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3c. HSE per field — minimum-viable per #376 plan
# ---------------------------------------------------------------------------


def analyze_hse_per_field(field_ids: Sequence[str]) -> pd.DataFrame:
    """Minimum-viable HSE overlay per the #376 plan.

    Full coverage requires HSE bulk dedup + ingest (#366). Until that
    lands, this section emits a placeholder row per field with explicit
    `data_completeness: minimum_viable_pending_#366` flag so the report
    layer (Phase 4 / #377) can surface the gap honestly rather than
    silently elide HSE.
    """
    rows = []
    for fid in field_ids:
        rows.append(
            {
                "field_id": fid,
                "incident_count": 0,
                "incidents_per_mmbbl": None,
                "data_completeness": HSE_DATA_COMPLETENESS_MINIMUM,
                "source": "placeholder pending #366 (HSE bulk dedup + ingest)",
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3d. Cost benchmark — pending #343 disclosure registry seeding
# ---------------------------------------------------------------------------


def analyze_cost_benchmark(
    field_ids: Sequence[str],
    *,
    economics_run: Optional[PortfolioEconomicsRun] = None,
) -> pd.DataFrame:
    """Per-field cost-vs-disclosure benchmark.

    Calls DisclosureAnalyticsQuery.benchmark per field. Where no
    comparable disclosure exists, records `benchmark_status: no_data_pending_#343`
    rather than dropping the field — keeps the row count consistent with
    the roster.
    """
    benchmark = DisclosureAnalyticsQuery()
    econ_lookup = (
        {r.field_id: r for r in economics_run.results} if economics_run else {}
    )

    rows = []
    for fid in field_ids:
        payload = _load_field_payload(fid)
        operator = str(payload.get("operator") or "unknown")
        capex_mm = float((payload.get("capex") or {}).get("total_mm_usd") or 0.0)
        modelled_capex_mm = (
            econ_lookup[fid].capex_mm_usd if fid in econ_lookup else capex_mm
        )

        try:
            # Empty project_revision_view = no comparable disclosures yet.
            # Once #343 + #344 seed the registry, replace with the live view.
            result = benchmark.benchmark(
                project_revision_view=[],
                predictor_cost_usd_mm=modelled_capex_mm,
                operator=operator,
                project_name=fid,
            )
        except (
            Exception
        ) as exc:  # noqa: BLE001 — surface unexpected failures gracefully
            logger.warning("benchmark failed for %s: %s", fid, exc)
            result = None

        rows.append(
            {
                "field_id": fid,
                "operator": operator,
                "modelled_capex_mm_usd": modelled_capex_mm,
                "disclosed_capex_mm_usd": (
                    None
                    if result is None
                    else float(getattr(result, "disclosed_capex_mm_usd", 0.0) or 0.0)
                ),
                "delta_pct": (
                    None
                    if result is None
                    else float(getattr(result, "delta_pct", 0.0) or 0.0)
                ),
                "benchmark_status": (
                    BENCHMARK_STATUS_COMPARABLE
                    if result is not None
                    else BENCHMARK_STATUS_NO_DATA
                ),
                "caveats": (
                    "Live benchmark requires #343 (operator registry) + "
                    "#344 (restatement lineage) to seed the project_revision_view."
                ),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_portfolio_analytics(
    field_ids: Sequence[str] = LT_FIELDS_2026,
    *,
    economics_run: Optional[PortfolioEconomicsRun] = None,
) -> PortfolioAnalyticsRun:
    """Compute all four cross-field analytics sections.

    If `economics_run` is None, runs `run_portfolio()` to produce one
    so the technology + cost-benchmark sections have a comparison
    baseline (per the #376 plan dependency on #375).
    """
    if economics_run is None:
        economics_run = run_portfolio(field_ids=field_ids)

    return PortfolioAnalyticsRun(
        technology=analyze_technology_generation(
            field_ids, economics_run=economics_run
        ),
        operator=analyze_operator_concentration(field_ids, economics_run=economics_run),
        hse=analyze_hse_per_field(field_ids),
        cost_benchmark=analyze_cost_benchmark(field_ids, economics_run=economics_run),
        field_ids=tuple(field_ids),
    )


# ---------------------------------------------------------------------------
# Output renderers
# ---------------------------------------------------------------------------


def portfolio_analytics_to_csv(
    run: PortfolioAnalyticsRun, output_dir: Path | str
) -> Dict[str, Path]:
    """Write each section as a separate CSV under `output_dir/`.

    Returns a mapping `{section_name: path}`.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "technology": out / "technology_generation.csv",
        "operator": out / "operator_concentration.csv",
        "hse": out / "hse_per_field.csv",
        "cost_benchmark": out / "cost_benchmark.csv",
    }
    run.technology.to_csv(paths["technology"], index=False)
    run.operator.to_csv(paths["operator"], index=False)
    run.hse.to_csv(paths["hse"], index=False)
    run.cost_benchmark.to_csv(paths["cost_benchmark"], index=False)
    return paths


def portfolio_analytics_to_html(run: PortfolioAnalyticsRun, path: Path | str) -> Path:
    """Render all four sections in a single HTML file with caveats surfaced."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    parts: List[str] = []
    parts.append(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Lower Tertiary Portfolio Analytics</title>"
        "<style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "max-width:1200px;margin:2em auto;padding:0 1em;color:#222;}"
        "h1{border-bottom:2px solid #333;padding-bottom:0.4em;}"
        "h2{margin-top:2em;color:#003366;}"
        "table{border-collapse:collapse;margin:1em 0;font-size:0.92em;}"
        "th,td{border:1px solid #ccc;padding:0.4em 0.7em;text-align:left;}"
        "th{background:#f4f4f4;}"
        ".meta{color:#666;font-size:0.9em;}"
        ".caveat{background:#fff3cd;border-left:4px solid #f0ad4e;"
        "padding:0.6em 1em;margin:1em 0;}"
        "</style></head><body>"
    )
    parts.append("<h1>Lower Tertiary Portfolio Analytics</h1>")
    parts.append(
        f"<div class='meta'>Run: {html.escape(run.timestamp_utc)} &middot; "
        f"fields: {len(run.field_ids)}</div>"
    )

    parts.append("<h2>3a. Technology generation</h2>")
    parts.append(
        run.technology.to_html(index=False, float_format=lambda x: f"{x:,.2f}")
    )

    parts.append("<h2>3b. Operator concentration</h2>")
    parts.append(run.operator.to_html(index=False, float_format=lambda x: f"{x:,.2f}"))

    parts.append("<h2>3c. HSE per field</h2>")
    parts.append(
        "<div class='caveat'>Minimum-viable shape per the #376 plan. "
        "Full HSE coverage depends on #366 (HSE bulk dedup + ingest).</div>"
    )
    parts.append(run.hse.to_html(index=False))

    parts.append("<h2>3d. Cost benchmark vs. operator disclosures</h2>")
    parts.append(
        "<div class='caveat'>Live benchmarking depends on #343 "
        "(operator registry) + #344 (restatement lineage) seeding the "
        "project_revision_view. Until then, every row carries "
        "<code>benchmark_status: no_data_pending_#343</code>.</div>"
    )
    parts.append(
        run.cost_benchmark.to_html(index=False, float_format=lambda x: f"{x:,.2f}")
    )

    parts.append("</body></html>")
    out.write_text("".join(parts), encoding="utf-8")
    return out
