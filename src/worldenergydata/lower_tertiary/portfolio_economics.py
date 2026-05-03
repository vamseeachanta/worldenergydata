"""Portfolio-level economics for the Lower Tertiary play (#375).

Applies the lease-NPV walkthrough pattern (#372) at field level to all 10
LT fields. Produces a comparable per-field economics table with
NPV/IRR/MIRR/payback + breakeven + 5-point oil-price sensitivity, and an
embedded citations panel sourcing every numeric input.

Public surface:
    - FieldEconomicsResult — dataclass per field
    - PortfolioEconomicsRun  — bundle of all field results + run metadata
    - analyze_field(field_id, ...) -> FieldEconomicsResult
    - run_portfolio(field_ids=LT_FIELDS_2026, ...) -> PortfolioEconomicsRun
    - portfolio_to_csv(run, path)
    - portfolio_to_html(run, path)

Cashflow basis: documented decline-curve (plateau → exponential decline)
using yaml-declared production_profile + capex.total_mm_usd. Real BSEE
OGOR aggregation is a follow-up (see #367 ProductionAPI12 forward path).
The cashflow_basis citation entry makes the choice explicit per field.
"""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd
import yaml

from worldenergydata.fdas.api import EconomicsQuery
from worldenergydata.lower_tertiary.portfolio import (
    LT_FIELDS_2026,
    fields_config_dir,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults — sourced and surfaced via citations panel per field.
# ---------------------------------------------------------------------------

DEFAULT_DISCOUNT_RATE = 0.10  # FDAS evaluation default
DEFAULT_REINVESTMENT_RATE = 0.06  # FDAS MIRR default
DEFAULT_OIL_PRICE_USD_PER_BBL = 70.0  # EIA STEO Q1 2026 reference
DEFAULT_ANNUAL_DECLINE = 0.08  # typical deepwater decline
DEFAULT_PLATEAU_YEARS = 3  # plateau duration before decline begins
DEFAULT_PROJECT_YEARS = 20
DEFAULT_OPEX_PER_BOE = 15.0
DEFAULT_FEDERAL_ROYALTY = 0.125  # 30 CFR § 250
DEFAULT_OIL_PRICE_SENSITIVITY = (50.0, 60.0, 70.0, 80.0, 100.0)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FieldEconomicsResult:
    field_id: str
    display_name: str
    status: str
    operator: str
    capex_mm_usd: float
    plateau_mbopd: float
    npv_mm_usd: float
    irr_annual: float
    mirr_annual: float
    payback_years: float
    breakeven_oil_usd_per_bbl: Optional[float]
    sensitivity: pd.DataFrame  # columns: oil_price_usd_per_bbl, npv_mm_usd
    citations: pd.DataFrame  # columns: input, publisher, code_id, revision
    cashflow_basis: str  # e.g. "documented_decline" or "bsee_ogor"


@dataclass
class PortfolioEconomicsRun:
    results: List[FieldEconomicsResult]
    discount_rate: float
    reinvestment_rate: float
    oil_price_usd_per_bbl: float
    sensitivity_prices: Tuple[float, ...]
    project_years: int
    plateau_years: int
    annual_decline: float
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_summary_frame(self) -> pd.DataFrame:
        """Compact table — one row per field, no nested sensitivity/citations."""
        rows = []
        for r in self.results:
            row = {
                "field_id": r.field_id,
                "display_name": r.display_name,
                "status": r.status,
                "operator": r.operator,
                "capex_mm_usd": r.capex_mm_usd,
                "plateau_mbopd": r.plateau_mbopd,
                "npv_mm_usd": r.npv_mm_usd,
                "irr_annual": r.irr_annual,
                "mirr_annual": r.mirr_annual,
                "payback_years": r.payback_years,
                "breakeven_oil_usd_per_bbl": r.breakeven_oil_usd_per_bbl,
                "cashflow_basis": r.cashflow_basis,
            }
            for _, s_row in r.sensitivity.iterrows():
                col = f"npv_mm_usd_at_${int(s_row['oil_price_usd_per_bbl'])}"
                row[col] = s_row["npv_mm_usd"]
            rows.append(row)
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Cashflow + economics helpers
# ---------------------------------------------------------------------------


def _build_production_profile(
    plateau_mbopd: float,
    plateau_years: int,
    annual_decline: float,
    project_years: int,
) -> List[float]:
    """Annual production stream in MMbbl. Plateau then exponential decline."""
    # plateau_mbopd is thousand bbl/day — convert to MMbbl/yr.
    # 1 mbopd × 365 days/yr ÷ 1000 = MMbbl/yr (approximately, ignoring leap years).
    annual_at_plateau_mmbbl = plateau_mbopd * 365.0 / 1000.0
    out = []
    for y in range(project_years):
        if y < plateau_years:
            out.append(annual_at_plateau_mmbbl)
        else:
            decline_years = y - plateau_years + 1
            out.append(annual_at_plateau_mmbbl * (1 - annual_decline) ** decline_years)
    return out


def _cashflow_for_oil_price(
    production_mmbbl: Sequence[float],
    capex_mm_usd: float,
    oil_price_usd_per_bbl: float,
    royalty_rate: float,
    opex_per_boe: float,
) -> List[float]:
    """Cashflow series in $M per year; year 0 = -capex."""
    revenue_mm = [p * oil_price_usd_per_bbl for p in production_mmbbl]
    royalty_mm = [r * royalty_rate for r in revenue_mm]
    # Treat opex_per_boe as $/bbl — scaled by production.
    opex_mm = [p * opex_per_boe for p in production_mmbbl]
    net_mm = [
        revenue_mm[y] - royalty_mm[y] - opex_mm[y] for y in range(len(production_mmbbl))
    ]
    return [-float(capex_mm_usd)] + net_mm


def _solve_breakeven_oil_price(
    production_mmbbl: Sequence[float],
    capex_mm_usd: float,
    discount_rate: float,
    royalty_rate: float,
    opex_per_boe: float,
    *,
    low: float = 1.0,
    high: float = 500.0,
    tolerance: float = 0.01,
    max_iter: int = 64,
) -> Optional[float]:
    """Bisection: find oil price where NPV = 0. Returns None if NPV never crosses."""
    econ = EconomicsQuery()

    def npv_at(price: float) -> float:
        cf = _cashflow_for_oil_price(
            production_mmbbl, capex_mm_usd, price, royalty_rate, opex_per_boe
        )
        return econ.npv(cf, discount_rate=discount_rate, period="annual")

    f_low, f_high = npv_at(low), npv_at(high)
    if f_low > 0 and f_high > 0:
        return low  # NPV positive even at $1/bbl — degenerate but possible
    if f_low < 0 and f_high < 0:
        return None  # NPV never goes positive in [low, high]

    for _ in range(max_iter):
        mid = (low + high) / 2
        f_mid = npv_at(mid)
        if abs(f_mid) < tolerance:
            return round(mid, 2)
        if (f_mid < 0) == (f_low < 0):
            low, f_low = mid, f_mid
        else:
            high = mid
    return round((low + high) / 2, 2)


# ---------------------------------------------------------------------------
# Field config loader
# ---------------------------------------------------------------------------


def _load_field_yaml(field_id: str) -> Dict[str, object]:
    path = fields_config_dir() / f"{field_id}.yml"
    if not path.is_file():
        raise FileNotFoundError(f"LT field config missing: {path}")
    with path.open("r", encoding="utf-8") as fh:
        contents = yaml.safe_load(fh) or {}
    return contents.get("field", contents)


# ---------------------------------------------------------------------------
# Per-field analysis
# ---------------------------------------------------------------------------


def analyze_field(
    field_id: str,
    *,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    reinvestment_rate: float = DEFAULT_REINVESTMENT_RATE,
    oil_price_usd_per_bbl: float = DEFAULT_OIL_PRICE_USD_PER_BBL,
    sensitivity_prices: Sequence[float] = DEFAULT_OIL_PRICE_SENSITIVITY,
    project_years: int = DEFAULT_PROJECT_YEARS,
    plateau_years: int = DEFAULT_PLATEAU_YEARS,
    annual_decline: float = DEFAULT_ANNUAL_DECLINE,
    royalty_rate: float = DEFAULT_FEDERAL_ROYALTY,
) -> FieldEconomicsResult:
    """Compute economics for a single field."""
    payload = _load_field_yaml(field_id)

    display_name = str(payload.get("display_name") or field_id)
    status = str(payload.get("status") or "unknown")
    operator = str(payload.get("operator") or "unknown")

    capex = payload.get("capex") or {}
    capex_mm_usd = float(capex.get("total_mm_usd") or 0.0)
    if capex_mm_usd <= 0:
        raise ValueError(
            f"Field {field_id}: capex.total_mm_usd missing or non-positive"
        )

    profile = payload.get("production_profile") or {}
    plateau_mbopd = float(profile.get("plateau_rate_mbopd") or 0.0)
    if plateau_mbopd <= 0:
        raise ValueError(
            f"Field {field_id}: production_profile.plateau_rate_mbopd missing or non-positive"
        )

    opex_per_boe = float(payload.get("opex_per_boe") or DEFAULT_OPEX_PER_BOE)

    production_mmbbl = _build_production_profile(
        plateau_mbopd, plateau_years, annual_decline, project_years
    )
    cashflows = _cashflow_for_oil_price(
        production_mmbbl,
        capex_mm_usd,
        oil_price_usd_per_bbl,
        royalty_rate,
        opex_per_boe,
    )

    econ = EconomicsQuery()
    metrics = econ.all_metrics(cashflows, discount_rate=discount_rate, period="annual")
    # mirr returns (period_mirr, annual_mirr); for annual cashflows the period
    # value IS the annual rate, but we follow the API's stated tuple order.
    _, mirr_annual = econ.mirr(
        cashflows,
        discount_rate=discount_rate,
        reinvestment_rate=reinvestment_rate,
    )

    # Sensitivity sweep at varying oil prices.
    sensitivity_rows = []
    for price in sensitivity_prices:
        cf = _cashflow_for_oil_price(
            production_mmbbl, capex_mm_usd, price, royalty_rate, opex_per_boe
        )
        npv = econ.npv(cf, discount_rate=discount_rate, period="annual")
        sensitivity_rows.append(
            {"oil_price_usd_per_bbl": float(price), "npv_mm_usd": float(npv)}
        )
    sensitivity = pd.DataFrame(sensitivity_rows)

    breakeven = _solve_breakeven_oil_price(
        production_mmbbl,
        capex_mm_usd,
        discount_rate,
        royalty_rate,
        opex_per_boe,
    )

    cashflow_basis = "documented_decline_curve_v1"

    citations = pd.DataFrame(
        [
            {
                "input": f"Field config ({field_id}.yml)",
                "publisher": "worldenergydata",
                "code_id": f"config/analysis/lower_tertiary/fields/{field_id}.yml",
                "revision": "tracked-in-git",
            },
            {
                "input": f"Capex ${capex_mm_usd:,.0f} M total",
                "publisher": payload.get("operator", "field operator"),
                "code_id": f"yaml: field.capex.total_mm_usd ({field_id})",
                "revision": str(payload.get("data_through", "n/a")),
            },
            {
                "input": f"Plateau {plateau_mbopd:,.0f} mbopd",
                "publisher": payload.get("operator", "field operator"),
                "code_id": f"yaml: field.production_profile.plateau_rate_mbopd ({field_id})",
                "revision": str(payload.get("data_through", "n/a")),
            },
            {
                "input": f"Opex ${opex_per_boe:.2f}/boe",
                "publisher": "FDAS / yaml override",
                "code_id": f"yaml: field.opex_per_boe ({field_id}) or default",
                "revision": "embedded",
            },
            {
                "input": f"Royalty {royalty_rate:.1%}",
                "publisher": "BSEE / Department of the Interior",
                "code_id": "30 CFR § 250 (federal offshore royalty)",
                "revision": "current",
            },
            {
                "input": f"Oil price ${oil_price_usd_per_bbl:.0f}/bbl",
                "publisher": "EIA",
                "code_id": "STEO Q1 2026 reference",
                "revision": "2026-01",
            },
            {
                "input": f"Annual decline {annual_decline:.1%}",
                "publisher": "FDAS",
                "code_id": "deepwater_default_decline (lower_tertiary.portfolio_economics)",
                "revision": "embedded",
            },
            {
                "input": f"Plateau duration {plateau_years} years",
                "publisher": "FDAS",
                "code_id": "DEFAULT_PLATEAU_YEARS",
                "revision": "embedded",
            },
            {
                "input": f"Discount rate {discount_rate:.1%}",
                "publisher": "FDAS",
                "code_id": "evaluation_default",
                "revision": "embedded",
            },
            {
                "input": f"Cashflow basis: {cashflow_basis}",
                "publisher": "lower_tertiary.portfolio_economics",
                "code_id": "documented decline-curve fallback per #375 plan",
                "revision": "v1",
            },
        ]
    )

    return FieldEconomicsResult(
        field_id=field_id,
        display_name=display_name,
        status=status,
        operator=operator,
        capex_mm_usd=capex_mm_usd,
        plateau_mbopd=plateau_mbopd,
        npv_mm_usd=float(metrics["npv"]),
        irr_annual=(
            float(metrics["irr_annual"])
            if metrics.get("irr_annual") is not None
            else float("nan")
        ),
        mirr_annual=float(mirr_annual),
        payback_years=(
            float(metrics["payback_years"])
            if metrics.get("payback_years") is not None
            else float("nan")
        ),
        breakeven_oil_usd_per_bbl=breakeven,
        sensitivity=sensitivity,
        citations=citations,
        cashflow_basis=cashflow_basis,
    )


# ---------------------------------------------------------------------------
# Portfolio runner
# ---------------------------------------------------------------------------


def run_portfolio(
    field_ids: Sequence[str] = LT_FIELDS_2026,
    *,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    reinvestment_rate: float = DEFAULT_REINVESTMENT_RATE,
    oil_price_usd_per_bbl: float = DEFAULT_OIL_PRICE_USD_PER_BBL,
    sensitivity_prices: Sequence[float] = DEFAULT_OIL_PRICE_SENSITIVITY,
    project_years: int = DEFAULT_PROJECT_YEARS,
    plateau_years: int = DEFAULT_PLATEAU_YEARS,
    annual_decline: float = DEFAULT_ANNUAL_DECLINE,
    royalty_rate: float = DEFAULT_FEDERAL_ROYALTY,
) -> PortfolioEconomicsRun:
    """Compute portfolio-wide economics across the supplied field roster."""
    results: List[FieldEconomicsResult] = []
    for fid in field_ids:
        try:
            results.append(
                analyze_field(
                    fid,
                    discount_rate=discount_rate,
                    reinvestment_rate=reinvestment_rate,
                    oil_price_usd_per_bbl=oil_price_usd_per_bbl,
                    sensitivity_prices=sensitivity_prices,
                    project_years=project_years,
                    plateau_years=plateau_years,
                    annual_decline=annual_decline,
                    royalty_rate=royalty_rate,
                )
            )
        except Exception as exc:
            logger.error("Failed to analyze field %s: %s", fid, exc)
            raise
    return PortfolioEconomicsRun(
        results=results,
        discount_rate=discount_rate,
        reinvestment_rate=reinvestment_rate,
        oil_price_usd_per_bbl=oil_price_usd_per_bbl,
        sensitivity_prices=tuple(float(p) for p in sensitivity_prices),
        project_years=project_years,
        plateau_years=plateau_years,
        annual_decline=annual_decline,
    )


# ---------------------------------------------------------------------------
# Output renderers
# ---------------------------------------------------------------------------


def portfolio_to_csv(run: PortfolioEconomicsRun, path: Path | str) -> Path:
    """Write the per-field summary table (sensitivities flattened) to CSV."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    run.to_summary_frame().to_csv(output, index=False)
    return output


def _html_escape_record(record: Dict[str, object]) -> Dict[str, str]:
    return {k: html.escape(str(v)) for k, v in record.items()}


def portfolio_to_html(run: PortfolioEconomicsRun, path: Path | str) -> Path:
    """Render a buyer-presentable HTML view with per-field detail + citations."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    summary = run.to_summary_frame()

    parts: List[str] = []
    parts.append(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Lower Tertiary Portfolio Economics</title>"
        "<style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "max-width:1200px;margin:2em auto;padding:0 1em;color:#222;}"
        "h1{border-bottom:2px solid #333;padding-bottom:0.4em;}"
        "h2{margin-top:2em;color:#003366;}"
        "table{border-collapse:collapse;margin:1em 0;font-size:0.92em;}"
        "th,td{border:1px solid #ccc;padding:0.4em 0.7em;text-align:left;}"
        "th{background:#f4f4f4;}"
        ".meta{color:#666;font-size:0.9em;margin-bottom:1em;}"
        ".cite-table{font-size:0.85em;}"
        "</style></head><body>"
    )
    parts.append("<h1>Lower Tertiary Portfolio Economics</h1>")
    parts.append(
        f"<div class='meta'>Run: {html.escape(run.timestamp_utc)} &middot; "
        f"discount_rate={run.discount_rate:.1%} &middot; "
        f"oil_price=${run.oil_price_usd_per_bbl:.0f}/bbl &middot; "
        f"project_years={run.project_years} &middot; "
        f"plateau_years={run.plateau_years} &middot; "
        f"annual_decline={run.annual_decline:.1%}</div>"
    )

    parts.append("<h2>Portfolio summary</h2>")
    parts.append(summary.to_html(index=False, float_format=lambda x: f"{x:,.2f}"))

    for r in run.results:
        parts.append(
            f"<h2>{html.escape(r.display_name)} ({html.escape(r.field_id)})</h2>"
        )
        parts.append(
            f"<div class='meta'>Status: <b>{html.escape(r.status)}</b> &middot; "
            f"Operator: <b>{html.escape(r.operator)}</b> &middot; "
            f"Capex: <b>${r.capex_mm_usd:,.0f} M</b> &middot; "
            f"Plateau: <b>{r.plateau_mbopd:,.0f} mbopd</b> &middot; "
            f"Cashflow basis: <code>{html.escape(r.cashflow_basis)}</code></div>"
        )
        parts.append("<h3>Sensitivity</h3>")
        parts.append(
            r.sensitivity.to_html(index=False, float_format=lambda x: f"{x:,.2f}")
        )
        parts.append("<h3>Citations</h3>")
        parts.append(
            r.citations.to_html(
                index=False, classes="cite-table", border=1, escape=True
            )
        )

    parts.append("</body></html>")
    output.write_text("".join(parts), encoding="utf-8")
    return output
