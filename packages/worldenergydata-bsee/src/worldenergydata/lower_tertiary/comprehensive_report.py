"""Comprehensive Lower Tertiary report assembly (#377).

Phase 4 of #373 epic. Consumes outputs from:
- #374 (LT_FIELDS_2026 roster + per-field yamls)
- #375 (run_portfolio → per-field economics + sensitivities + citations)
- #376 (run_portfolio_analytics → 4 cross-field sections)

Produces a single comprehensive report in three parallel formats:
- Markdown (canonical for-humans + version control friendly)
- HTML (buyer-presentable; embedded styling, no external deps)
- PDF (rendered from HTML via Chrome headless)

Public surface:
    - assemble_comprehensive_report(...) -> ComprehensiveReportResult
    - render_markdown(result, path) -> Path
    - render_html(result, path) -> Path
    - render_pdf(html_path, pdf_path) -> Path
    - render_all(result, output_dir) -> Dict[str, Path]
"""

from __future__ import annotations

import ast
import hashlib
import html
import json
import os
import re
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlsplit

import pandas as pd
import yaml

from worldenergydata.lower_tertiary.portfolio import (
    LT_FIELDS_2026,
    fields_config_dir,
)
from worldenergydata.lower_tertiary.portfolio_analytics import (
    PortfolioAnalyticsRun,
    analyze_operator_concentration,
    run_portfolio_analytics,
)
from worldenergydata.lower_tertiary.portfolio_economics import (
    DEFAULT_FEDERAL_ROYALTY,
    DEFAULT_OPEX_PER_BOE,
    PortfolioEconomicsRun,
    run_portfolio,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result bundle
# ---------------------------------------------------------------------------


@dataclass
class ComprehensiveReportResult:
    economics_run: PortfolioEconomicsRun
    analytics_run: PortfolioAnalyticsRun
    field_payloads: Dict[str, Dict[str, object]]
    executive_summary: List[str]  # one bullet per finding
    revision_record: dict = field(default_factory=lambda: load_revision_record())
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Loaders + executive-summary computation
# ---------------------------------------------------------------------------


def _load_field_payload(field_id: str) -> Dict[str, object]:
    path = fields_config_dir() / f"{field_id}.yml"
    with path.open("r", encoding="utf-8") as fh:
        contents = yaml.safe_load(fh) or {}
    return contents.get("field", contents)


def repository_root() -> Path:
    return fields_config_dir().parents[3]


def revision_record_path() -> Path:
    return fields_config_dir().parent / "comprehensive_revision.yml"


def load_revision_record() -> dict:
    record = yaml.safe_load(revision_record_path().read_text(encoding="utf-8"))
    history = record.get("history", [])
    if not history or record.get("revision") != history[-1].get("revision"):
        raise ValueError("Report revision must match the newest history row")
    for row in history:
        if not all(row.get(key) for key in ("revision", "date", "change")):
            raise ValueError("Report revision history has an incomplete row")
        datetime.strptime(row["date"], "%Y-%m-%d")
    return record


def _validate_report(result: ComprehensiveReportResult) -> None:
    ids = [econ.field_id for econ in result.economics_run.results]
    if len(ids) != len(set(ids)) or set(ids) != set(result.field_payloads):
        raise ValueError("Report roster differs from the field inputs")
    if result.revision_record["revision"] != result.revision_record["history"][-1]["revision"]:
        raise ValueError("Report revision differs from the newest history row")
    for econ in result.economics_run.results:
        if econ.citations.empty:
            raise ValueError(f"Missing citations: {econ.field_id}")
        for column in ("input", "publisher", "code_id", "revision"):
            if column not in econ.citations or econ.citations[column].isna().any():
                raise ValueError(f"Missing citation {column}: {econ.field_id}")
            if econ.citations[column].astype(str).str.strip().eq("").any():
                raise ValueError(f"Empty citation {column}: {econ.field_id}")
        config_locator = str(econ.citations.iloc[0]["code_id"])
        if not _citation_resolves(config_locator):
            raise ValueError(f"Unresolved citation: {econ.field_id}")
        for item in _report_citations(result, econ)["code_id"]:
            if not _citation_resolves(item):
                raise ValueError(f"Unresolved citation: {econ.field_id}")


ANNUAL_MIRR_LIMIT = (
    "Annual MIRR: not established; the monthly-period rate routine is applied "
    "to annual cashflows (#373)."
)


def _economic_basis(result: ComprehensiveReportResult) -> str:
    run = result.economics_run
    return (
        f"Oil-price deck: ${run.oil_price_usd_per_bbl:.1f}/bbl, constant nominal scenario; "
        f"discount rate: {run.discount_rate:.1%}; reinvestment rate: {run.reinvestment_rate:.1%}; "
        f"horizon: {run.project_years} years; plateau duration: {run.plateau_years} years; "
        f"annual decline: {run.annual_decline:.1%}. "
        "Unsourced field inputs are assumed (unsourced configuration value, #651). "
        "Generic discount, reinvestment and decline rates and horizon defaults are assumed, based on previous experience. "
        "Capital is charged at inception; oil-only cashflows deduct operating costs and the configured royalty, "
        "before corporate tax. NPV is discounted to model inception, without calendar-year alignment. Gas revenue, escalation and decommissioning are not modelled. "
        "Paired development entries retain combined capital and plateau rates; separate field splits are not established. "
        "Configuration dates govern the input basis; the issue date does not refresh those inputs. "
        + ANNUAL_MIRR_LIMIT
    )


def _field_basis(result: ComprehensiveReportResult, econ) -> str:
    payload = result.field_payloads[econ.field_id]
    cutoff = payload.get("data_through") or "not established"
    return (
        f"Economic basis: oil-price deck ${result.economics_run.oil_price_usd_per_bbl:.1f}/bbl; "
        f"cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); "
        f"data_through: {cutoff}; nominal cost base year: not established. "
        "Production history: not established in this assembly; the plateau is a scenario input, "
        "and the cashflow is a decline-curve projection, not observed BSEE production (#367). "
        "HSE: not established; the upstream placeholder is not an observed zero (#366). "
        "Comparable disclosed cost and escalation basis: not established (#343, #344). "
        "Field status and first-oil schedule are configuration values, not a current operating-status check. "
        + ANNUAL_MIRR_LIMIT
    )


def report_hse(result: ComprehensiveReportResult) -> pd.DataFrame:
    frame = result.analytics_run.hse.copy()
    pending = frame["data_completeness"].astype(str).str.contains("pending", regex=False)
    frame.loc[pending, ["incident_count", "incidents_per_mmbbl"]] = float("nan")
    return frame


UNSOURCED_INPUT_BASIS = "assumed (unsourced configuration value, #651)"


def _citation_rows(payload, field_id, label, path, basis, key):
    rows = []
    source = repository_root() / path.split("#", 1)[0]
    source_revision = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    references = (payload.get("sources") or {}).get(key, []) if key else []
    for reference in references or [None]:
        missing_public = "Not established" if basis == UNSOURCED_INPUT_BASIS else "Not applicable"
        row = {
            "input": label, "publisher": "worldenergydata", "code_id": path,
            "revision": source_revision, "basis": basis,
            "source_id": missing_public, "title": missing_public,
            "url": missing_public, "retrieved": missing_public,
            "sha256": missing_public, "http_status": "Not applicable",
        }
        if reference is not None:
            for name in ("id", "title", "url", "retrieved", "sha256"):
                if name not in reference:
                    raise ValueError(f"Missing public citation {name}: {field_id}")
            row.update({name: reference[name] for name in ("title", "url")})
            row["publisher"] = urlsplit(reference["url"]).netloc
            row["source_id"] = reference["id"]
            row["retrieved"] = reference["retrieved"] or "not retrieved in this revision"
            row["sha256"] = reference["sha256"] or "Not established"
            row["http_status"] = str(reference["http_status"])
            row["basis"] = "public source recorded in configuration; " + reference["retrieval_status"]
            if key == "first_oil":
                row["basis"] += "; exact first-flow day not established by this citation; configured month-start convention retained"
        if key == "partners" and payload.get("working_interest_status") in ("contradicted", "unverified"):
            row["basis"] += "; working interests contradicted or unverified; excluded from concentration"
        rows.append(row)

    return rows


def _report_citations(result: ComprehensiveReportResult, econ) -> pd.DataFrame:
    payload = result.field_payloads[econ.field_id]
    config = f"config/analysis/lower_tertiary/fields/{econ.field_id}.yml"
    module = "packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py"
    analytics = "packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py"
    run = result.economics_run
    rows = []
    unsourced = UNSOURCED_INPUT_BASIS
    generic = "assumed, based on previous experience"

    def add(label, path, basis=unsourced, key=None):
        rows.extend(_citation_rows(payload, econ.field_id, label, path, basis, key))

    add(f"Capex ${econ.capex_mm_usd:,.1f} M", config + "#field.capex.total_mm_usd", key="capex.total_mm_usd")
    add(f"Plateau {econ.plateau_mbopd:.1f} thousand bbl/day", config + "#field.production_profile.plateau_rate_mbopd", key="production_profile.plateau_rate_mbopd")
    opex = payload.get("opex_per_boe", DEFAULT_OPEX_PER_BOE)
    add(f"Opex ${float(opex):.1f}/boe", config + "#field.opex_per_boe" if payload.get("opex_per_boe") else module + "#DEFAULT_OPEX_PER_BOE", key="opex_per_boe")
    add(f"Oil price ${run.oil_price_usd_per_bbl:.1f}/bbl", module + "#run_portfolio.oil_price_usd_per_bbl")
    add(f"Royalty {DEFAULT_FEDERAL_ROYALTY:.1%}", module + "#DEFAULT_FEDERAL_ROYALTY", key="royalty_rate")
    for name, value in (("discount_rate", run.discount_rate), ("reinvestment_rate", run.reinvestment_rate), ("annual_decline", run.annual_decline)):
        add(f"{name}: {value:.1%}", module + "#run_portfolio." + name, generic)
    for name, value in (("project_years", run.project_years), ("plateau_years", run.plateau_years)):
        add(f"{name}: {value}", module + "#run_portfolio." + name, generic)
    add("Sensitivity oil-price deck: " + ", ".join(f"${price:.1f}/bbl" for price in run.sensitivity_prices), module + "#run_portfolio.sensitivity_prices")
    add("First-oil schedule", config + "#field.first_oil", key="first_oil")
    add("Data cutoff", config + "#field.data_through", key="data_through")
    add("Operator", config + "#field.operator", key="operator")
    add("Status", config + "#field.status", key="status")
    add("Working-interest shares", config + "#field.partners" if payload.get("partners") else analytics + "#analyze_operator_concentration", key="partners")
    add("Technology classification", analytics + "#_resolved_dev_system")
    add("NPV, rates, payback, breakeven and sensitivities", module + "#analyze_field", "computed from the scenario inputs above")
    add("Portfolio totals and technology comparisons", analytics + "#run_portfolio_analytics", "computed; plateau-equivalent recovery proxy, not reserves")
    add("Operator concentration", analytics + "#analyze_operator_concentration", "computed from eligible configuration working interests; contradicted or unverified interests excluded")
    add("HSE and disclosed-cost completeness", analytics + "#analyze_hse_per_field", "not established; placeholder values are not measurements")
    add("Report revision and issue date", "config/analysis/lower_tertiary/comprehensive_revision.yml", "issued revision record")
    return pd.DataFrame(rows)


def write_manifest(result: ComprehensiveReportResult, paths: Dict[str, Path], output_dir: Path | str) -> Path:
    root = repository_root()
    inputs = [revision_record_path(), Path(__file__), root / "scripts/reporting/assemble_lt_comprehensive.py"]
    inputs += [root / "packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary" / name for name in ("portfolio.py", "portfolio_economics.py", "portfolio_analytics.py")]
    inputs += [root / "packages/worldenergydata-fdas/src/worldenergydata/fdas/api.py",
               root / "packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py",
               root / "uv.lock", root / "pyproject.toml",
               root / "reports/lower_tertiary_field_summary.md"]
    inputs += [fields_config_dir() / f"{fid}.yml" for fid in result.field_payloads]
    def describe(path, locator):
        data = path.read_bytes()
        return {"path": locator, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    environment = {key: value for key, value in os.environ.items() if key not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR")}
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, env=environment, text=True).strip()
    manifest = {
        "schema_version": 1, "revision": result.revision_record["revision"],
        "report_date": result.revision_record["history"][-1]["date"], "base_commit": base,
        "source_state": "Input digests identify the executed source bytes, including uncommitted changes.",
        "generator_command": "uv run --no-sync python scripts/reporting/assemble_lt_comprehensive.py --output-dir reports/lower_tertiary",
        "inputs": [describe(path, path.relative_to(root).as_posix()) for path in sorted(inputs)],
        "outputs": [describe(path, "reports/lower_tertiary/" + path.name) for path in sorted(paths.values())],
        "pdf_metadata": "Creation and modification dates are fixed to the report issue date; page content is unchanged." if "pdf" in paths else "Not rendered; no PDF artifact is claimed.",
        "limits": {fid: _field_basis(result, econ) for fid, econ in ((r.field_id, r) for r in result.economics_run.results)},
    }
    out = Path(output_dir) / "comprehensive_2026.manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _format_number(value) -> str:
    return "Not established" if value is None or pd.isna(value) else f"{value:,.1f}"


def _report_summary_frame(result: ComprehensiveReportResult) -> pd.DataFrame:
    frame = result.economics_run.to_summary_frame()
    for name in ("irr_annual", "mirr_annual"):
        if name in frame:
            frame[name] *= 100
            frame.rename(columns={name: name + "_pct"}, inplace=True)
    if "mirr_annual_pct" in frame:
        frame["mirr_annual_pct"] = float("nan")
    frame.rename(columns={"plateau_mbopd": "plateau_thousand_bbl_per_day"}, inplace=True)
    return frame


def _citation_resolves(locator: str) -> bool:
    relative, _, fragment = locator.partition("#")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        return False
    source = repository_root() / path
    if not source.is_file():
        return False
    if not fragment:
        return True
    if source.suffix == ".yml":
        value = yaml.safe_load(source.read_text(encoding="utf-8"))
        for key in fragment.split("."):
            if not isinstance(value, dict) or key not in value:
                return False
            value = value[key]
        return True
    if source.suffix == ".py":
        tree = ast.parse(source.read_text(encoding="utf-8"))
        name, _, parameter = fragment.partition(".")
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                return not parameter or parameter in {arg.arg for arg in node.args.args + node.args.kwonlyargs}
            if isinstance(node, ast.Assign) and not parameter:
                if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                    return True
    return False


def _report_technology_frame(result: ComprehensiveReportResult) -> pd.DataFrame:
    return result.analytics_run.technology.rename(columns={
        "mean_capex_per_mmbbl_usd": "mean_capex_usd_per_bbl_proxy",
    })


def _eligible_operator_frame(field_payloads) -> pd.DataFrame:
    eligible = [
        fid for fid, payload in field_payloads.items()
        if payload.get("working_interest_status") not in ("contradicted", "unverified")
    ]
    return analyze_operator_concentration(eligible)


def _report_operator_frame(result: ComprehensiveReportResult) -> pd.DataFrame:
    return _eligible_operator_frame(result.field_payloads).rename(columns={
        "sum_wi_plateau_mbopd": "sum_wi_plateau_thousand_bbl_per_day",
    })


def _operator_exclusion_note(result: ComprehensiveReportResult) -> str:
    names = [
        str(payload.get("display_name") or fid)
        for fid, payload in result.field_payloads.items()
        if payload.get("working_interest_status") in ("contradicted", "unverified")
    ]
    if not names:
        return "Operator concentration, using configuration working-interest shares."
    return " and ".join(names) + " excluded: working interests contradicted or unverified. Shares and concentration index use only the remaining fields."


def _compute_executive_summary(
    economics_run: PortfolioEconomicsRun,
    analytics_run: PortfolioAnalyticsRun,
    operator_frame: pd.DataFrame,
) -> List[str]:
    """Bind executive-summary findings to computed thresholds, not prose."""
    bullets: List[str] = []

    bullets.append(
        f"Economic basis: constant scenario oil price ${economics_run.oil_price_usd_per_bbl:.1f}/bbl; "
        f"discount rate {economics_run.discount_rate:.1%}; before corporate tax. "
        "Costs are assumed (unsourced configuration value, #651), at the configuration dates."
    )

    # Full portfolio capital remains independent of the eligible WI denominator.
    total_capex = sum(r.capex_mm_usd for r in economics_run.results)
    n_fields = len(economics_run.results)
    bullets.append(
        f"Portfolio totals: {n_fields} fields, "
        f"${total_capex:,.0f} M aggregate scenario capex"
    )

    # Strongest field by NPV.
    best = max(economics_run.results, key=lambda r: r.npv_mm_usd)
    bullets.append(
        f"Strongest economics: **{best.display_name}** "
        f"(NPV ${best.npv_mm_usd:,.1f} M @ {economics_run.discount_rate:.1%}, "
        f"breakeven ${_format_number(best.breakeven_oil_usd_per_bbl)}/bbl)"
    )

    # Marginal / negative NPV fields.
    negatives = [r for r in economics_run.results if r.npv_mm_usd < 0]
    if negatives:
        names = ", ".join(r.display_name for r in negatives)
        bullets.append(
            f"Marginal at base case: {names} "
            f"(NPV < 0 at ${economics_run.oil_price_usd_per_bbl:.1f}/bbl "
            "with documented decline-curve cashflow)"
        )

    # Top operator among eligible fields.
    if operator_frame.empty:
        bullets.append("Operator concentration: Not established; no eligible working interests.")
    else:
        top_op = operator_frame.iloc[0]
        bullets.append(
            f"Operator concentration: **{top_op['company']}** holds the largest "
            f"working-interest-weighted capex share at "
            f"{float(top_op['share_capex_pct']):.1f}% across "
            f"{int(top_op['field_count'])} fields"
        )

    # Dominant tech generation.
    tech = analytics_run.technology.sort_values(
        "total_capex_mm_usd", ascending=False
    ).iloc[0]
    bullets.append(
        f"Dominant tech generation: **{tech['dev_system']}** "
        f"({int(tech['field_count'])} fields, "
        f"${float(tech['total_capex_mm_usd']):,.0f} M total scenario capex)"
    )

    # Pre-FID upside.
    pre_fid_count = sum(1 for r in economics_run.results if r.status == "pre_fid")
    if pre_fid_count:
        bullets.append(
            f"Pre-FID configurations: {pre_fid_count} fields classified pre-FID; "
            "current sanction status is not established. Capital estimates are assumed."
        )

    # Caveats reminder.
    bullets.append(
        "Caveats: cashflow basis is documented decline-curve (OGOR-grounded "
        "follow-up under #367); HSE coverage minimum-viable pending #366; "
        "live cost benchmarking pending #343 + #344"
    )

    return bullets


# ---------------------------------------------------------------------------
# Top-level assembly
# ---------------------------------------------------------------------------


def assemble_comprehensive_report(
    field_ids: Iterable[str] = LT_FIELDS_2026,
    *,
    economics_run: Optional[PortfolioEconomicsRun] = None,
    analytics_run: Optional[PortfolioAnalyticsRun] = None,
) -> ComprehensiveReportResult:
    """Run the full chain: economics → analytics → assembly."""
    field_ids = tuple(field_ids)
    if economics_run is None:
        economics_run = run_portfolio(field_ids=field_ids)
    if analytics_run is None:
        analytics_run = run_portfolio_analytics(
            field_ids=field_ids, economics_run=economics_run
        )

    if {r.field_id for r in economics_run.results} != set(field_ids):
        raise ValueError("Economics roster is incomplete; no field may be dropped")
    payloads = {fid: _load_field_payload(fid) for fid in field_ids}
    revision = load_revision_record()
    summary = _compute_executive_summary(economics_run, analytics_run, _eligible_operator_frame(payloads))

    return ComprehensiveReportResult(
        economics_run=economics_run,
        analytics_run=analytics_run,
        field_payloads=payloads,
        executive_summary=summary,
        revision_record=revision,
        timestamp_utc=revision["history"][-1]["date"],
    )


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def _md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a simple Markdown pipe table."""
    if df.empty:
        return "_(no rows)_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |"]
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            val = row[c]
            if pd.isna(val):
                cells.append("Not established")
            elif isinstance(val, float):
                cells.append(f"{val:,.1f}")
            else:
                cells.append(str(val))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_markdown(result: ComprehensiveReportResult, path: Path | str) -> Path:
    """Write the canonical Markdown source. Regeneratable from data."""
    _validate_report(result)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    parts: List[str] = []
    parts.append("# Lower Tertiary Comprehensive Field Report")
    parts.append("")
    parts.append(f"**Revision: {result.revision_record['revision']}**")
    parts.append(f"**Issue date:** {result.timestamp_utc}")
    parts.append(
        f"**Fields:** {len(result.economics_run.results)} GoM Lower Tertiary fields"
    )
    parts.append("")
    parts.append("---")
    parts.append("")

    parts.append("## Executive Summary")
    parts.append("")
    for bullet in result.executive_summary:
        parts.append(f"- {bullet}")
    parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("## Revision history")
    parts.append("")
    parts.append(_md_table(pd.DataFrame(result.revision_record["history"])))
    parts.append("")
    parts.append("Revision history: each row identifies an issue and its reason.")
    parts.append("")
    parts.append("## Economic basis")
    parts.append("")
    parts.append(_economic_basis(result))
    parts.append("")

    parts.append("## Portfolio Economics — All Fields")
    parts.append("")
    parts.append(_md_table(_report_summary_frame(result)))
    parts.append("")
    parts.append("Portfolio economics, using the economic basis above.")
    parts.append("")

    parts.append("## Cross-Field Analytics")
    parts.append("")
    parts.append("### Technology Generation")
    parts.append("")
    parts.append(_md_table(_report_technology_frame(result)))
    parts.append("")
    parts.append("Technology comparisons, using a plateau-equivalent recovery proxy.")
    parts.append("")
    parts.append("### Operator Concentration")
    parts.append("")
    parts.append(_md_table(_report_operator_frame(result)))
    parts.append("")
    parts.append(_operator_exclusion_note(result))
    parts.append("")
    parts.append("### HSE per Field (minimum-viable; full coverage pending #366)")
    parts.append("")
    parts.append(_md_table(report_hse(result)))
    parts.append("")
    parts.append("HSE availability; missing counts are not measured zeroes.")
    parts.append("")
    parts.append("### Cost Benchmark vs Disclosures (no_data pending #343)")
    parts.append("")
    parts.append(_md_table(result.analytics_run.cost_benchmark))
    parts.append("")
    parts.append("Cost comparison availability, using scenario capital costs.")
    parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("## Per-Field Detail")
    parts.append("")
    for econ in result.economics_run.results:
        payload = result.field_payloads[econ.field_id]
        parts.append(f"### {econ.display_name} (`{econ.field_id}`)")
        parts.append("")
        parts.append(f"- **Status:** {econ.status}")
        parts.append(f"- **Operator:** {econ.operator}")
        parts.append(f"- **First oil:** {payload.get('first_oil', 'n/a')}")
        parts.append(f"- **Capex:** ${econ.capex_mm_usd:,.0f} M total")
        parts.append(f"- **Plateau:** {econ.plateau_mbopd:,.0f} thousand bbl/day")
        parts.append(f"- **NPV @ {result.economics_run.discount_rate:.1%}:** ${econ.npv_mm_usd:,.1f} M")
        parts.append(f"- **Payback:** {_format_number(econ.payback_years)} years")
        parts.append(
            f"- **Breakeven oil price:** " f"${_format_number(econ.breakeven_oil_usd_per_bbl)}/bbl"
        )
        parts.append(f"- **Cashflow basis:** `{econ.cashflow_basis}`")
        parts.append(f"- {_field_basis(result, econ)}")
        parts.append("")
        parts.append("**Sensitivity:**")
        parts.append("")
        parts.append(_md_table(econ.sensitivity))
        parts.append("")
        parts.append("Oil-price sensitivity, using the field economic basis.")
        parts.append("")
        parts.append("**Citations:**")
        parts.append("")
        parts.append(_md_table(_report_citations(result, econ)))
        parts.append("")
        parts.append("Numeric-input and calculation references; source digests are in the companion manifest.")
        parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("## Caveats")
    parts.append("")
    parts.append(
        "- **Cashflow basis:** documented decline-curve (plateau×K years → "
        "exponential decline). OGOR-grounded forward path is #367 "
        "(ProductionAPI12 → FDAS migration)."
    )
    parts.append(
        "- **HSE coverage:** placeholder rows pending #366 (HSE bulk dedup + ingest)."
    )
    parts.append(
        "- **Cost benchmarking:** every field flagged `no_data_pending_#343` "
        "until the operator registry seeds disclosures."
    )
    parts.append(
        "- **Pre-FID economics:** configured capital estimates are assumptions; "
        "treat NPV / breakeven as scenario-grade, not commitment-grade."
    )
    parts.append(
        "- **Citation schema:** flat dict per field. Migration to the "
        "workspace-hub `Citation` schema is #361."
    )
    parts.append("")
    parts.append("")

    out.write_text("\n".join(parts).rstrip("\n") + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------


def _html_table(df: pd.DataFrame) -> str:
    return df.to_html(index=False, float_format=lambda x: f"{x:,.1f}", border=1, na_rep="Not established")


def render_html(result: ComprehensiveReportResult, path: Path | str) -> Path:
    """Render the HTML view directly from data."""
    _validate_report(result)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    parts: List[str] = []
    parts.append(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Lower Tertiary Comprehensive Field Report</title>"
        "<style>"
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "max-width:1200px;margin:2em auto;padding:0 1em;color:#222;}"
        "h1{border-bottom:2px solid #333;padding-bottom:0.4em;}"
        "h2{margin-top:2em;color:#003366;border-bottom:1px solid #ccc;padding-bottom:0.3em;}"
        "h3{margin-top:1.5em;color:#444;}"
        "table{border-collapse:collapse;margin:1em 0;font-size:0.9em;}"
        "th,td{border:1px solid #ccc;padding:0.4em 0.7em;text-align:left;}"
        "th{background:#f4f4f4;}"
        ".meta{color:#666;font-size:0.9em;margin-bottom:1em;}"
        ".caveat{background:#fff3cd;border-left:4px solid #f0ad4e;"
        "padding:0.6em 1em;margin:1em 0;}"
        ".exec-summary{background:#eef6fc;border-left:4px solid #3a7bd5;"
        "padding:1em 1.5em;margin:1em 0;}"
        ".field-section{border:1px solid #ddd;padding:1em 1.4em;margin:1em 0;"
        "border-radius:4px;background:#fafafa;}"
        "code{background:#f4f4f4;padding:0.1em 0.3em;border-radius:3px;}"
        "td,th{overflow-wrap:anywhere;}table{table-layout:fixed;width:100%;}"
        "@media print{@page{size:A4 landscape;margin:12mm;}"
        "body{margin:0;max-width:none;font-size:10pt;}table{font-size:8pt;}"
        ".field-section{break-before:page;}tr{break-inside:avoid;}}"
        "</style></head><body>"
    )

    parts.append("<h1>Lower Tertiary Comprehensive Field Report</h1>")
    parts.append(
        f"<div class='meta'>Revision: {html.escape(result.revision_record['revision'])} &middot; "
        f"Issue date: {html.escape(result.timestamp_utc)} &middot; "
        f"{len(result.economics_run.results)} GoM Lower Tertiary fields</div>"
    )

    parts.append("<h2>Executive Summary</h2>")
    parts.append("<div class='exec-summary'><ul>")
    for bullet in result.executive_summary:
        parts.append("<li>" + re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html.escape(bullet)) + "</li>")
    parts.append("</ul></div>")

    parts.append("<h2>Revision history</h2>")
    parts.append(_html_table(pd.DataFrame(result.revision_record["history"])))
    parts.append("<p>Revision history: each row identifies an issue and its reason.</p>")
    parts.append("<h2>Economic basis</h2>")
    parts.append(f"<p>{html.escape(_economic_basis(result))}</p>")

    parts.append("<h2>Portfolio Economics — All Fields</h2>")
    parts.append(_html_table(_report_summary_frame(result)))
    parts.append("<p>Portfolio economics, using the economic basis above.</p>")

    parts.append("<h2>Cross-Field Analytics</h2>")
    parts.append("<h3>Technology Generation</h3>")
    parts.append(_html_table(_report_technology_frame(result)))
    parts.append("<p>Technology comparisons, using a plateau-equivalent recovery proxy.</p>")
    parts.append("<h3>Operator Concentration</h3>")
    parts.append(_html_table(_report_operator_frame(result)))
    parts.append(f"<p>{html.escape(_operator_exclusion_note(result))}</p>")
    parts.append("<h3>HSE per Field</h3>")
    parts.append(
        "<div class='caveat'>Field incident counts and rates are not established. "
        "Full HSE coverage requires #366 (HSE bulk dedup + ingest).</div>"
    )
    parts.append(_html_table(report_hse(result)))
    parts.append("<p>HSE availability; missing counts are not measured zeroes.</p>")
    parts.append("<h3>Cost Benchmark vs Disclosures</h3>")
    parts.append(
        "<div class='caveat'>Live benchmarking requires #343 (operator "
        "registry) + #344 (restatement lineage) seeding the "
        "<code>project_revision_view</code>.</div>"
    )
    parts.append(_html_table(result.analytics_run.cost_benchmark))
    parts.append("<p>Cost comparison availability, using scenario capital costs.</p>")

    parts.append("<h2>Per-Field Detail</h2>")
    for econ in result.economics_run.results:
        payload = result.field_payloads[econ.field_id]
        parts.append("<div class='field-section'>")
        parts.append(
            f"<h3>{html.escape(econ.display_name)} "
            f"(<code>{html.escape(econ.field_id)}</code>)</h3>"
        )
        parts.append(
            f"<div class='meta'>Status: <b>{html.escape(econ.status)}</b> &middot; "
            f"Operator: <b>{html.escape(econ.operator)}</b> &middot; "
            f"First oil: <b>{html.escape(str(payload.get('first_oil', 'n/a')))}</b> &middot; "
            f"Capex: <b>${econ.capex_mm_usd:,.0f} M</b> &middot; "
            f"Plateau: <b>{econ.plateau_mbopd:,.0f} thousand bbl/day</b><br>"
            f"NPV at {result.economics_run.discount_rate:.1%}: <b>${econ.npv_mm_usd:,.1f} M</b> &middot; "
            f"Payback: <b>{_format_number(econ.payback_years)} yr</b> &middot; "
            f"Breakeven: <b>${_format_number(econ.breakeven_oil_usd_per_bbl)}/bbl</b> &middot; "
            f"Cashflow basis: <code>{html.escape(econ.cashflow_basis)}</code></div>"
        )
        parts.append(f"<p>{html.escape(_field_basis(result, econ))}</p>")
        parts.append("<h4>Sensitivity</h4>")
        parts.append(_html_table(econ.sensitivity))
        parts.append("<p>Oil-price sensitivity, using the field economic basis.</p>")
        parts.append("<h4>Citations</h4>")
        parts.append(_html_table(_report_citations(result, econ)))
        parts.append("<p>Numeric-input and calculation references; source digests are in the companion manifest.</p>")
        parts.append("</div>")

    parts.append("<h2>Caveats</h2>")
    parts.append(
        "<ul>"
        "<li><b>Cashflow basis:</b> documented decline-curve. OGOR-grounded "
        "forward path tracked under #367.</li>"
        "<li><b>HSE coverage:</b> placeholder rows pending #366.</li>"
        "<li><b>Cost benchmarking:</b> rows flagged "
        "<code>no_data_pending_#343</code>.</li>"
        "<li><b>Pre-FID economics:</b> scenario-grade, not commitment-grade.</li>"
        "<li><b>Citation schema:</b> flat dict; migration to formal schema is #361.</li>"
        "</ul>"
    )
    parts.append("</body></html>")
    out.write_text("".join(parts) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# PDF renderer (Chrome headless)
# ---------------------------------------------------------------------------


def render_pdf(html_path: Path | str, pdf_path: Path | str) -> Path:
    """Render a real PDF with stable issue-date metadata via Chrome headless."""
    html_p = Path(html_path).resolve()
    pdf_p = Path(pdf_path).resolve()
    pdf_p.parent.mkdir(parents=True, exist_ok=True)

    chrome = (
        shutil.which("google-chrome")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )
    if chrome is None:
        raise FileNotFoundError("Chrome renderer is unavailable")
    profile = tempfile.mkdtemp(prefix="lt-chrome-")

    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--no-first-run",
        "--disable-background-networking",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={pdf_p}",
        f"file://{html_p}",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
    data = pdf_p.read_bytes()
    if not data.startswith(b"%PDF-"):
        raise ValueError("Chrome output is not a PDF")
    issue_date = load_revision_record()["history"][-1]["date"].replace("-", "")
    fixed_date = (issue_date + "000000").encode("ascii")
    data = re.sub(rb"(/(?:CreationDate|ModDate) \(D:)\d{14}", lambda match: match[1] + fixed_date, data)
    pdf_p.write_bytes(data)
    return pdf_p


def render_all(
    result: ComprehensiveReportResult, output_dir: Path | str
) -> Dict[str, Path]:
    """Render Markdown + HTML + PDF outputs into output_dir."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "markdown": render_markdown(result, out / "comprehensive_2026.md"),
        "html": render_html(result, out / "comprehensive_2026.html"),
    }
    try:
        paths["pdf"] = render_pdf(paths["html"], out / "comprehensive_2026.pdf")
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        logger.warning("PDF is unavailable; Markdown and HTML remain delivered")
    return paths
