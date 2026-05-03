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

import html
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import yaml

from worldenergydata.lower_tertiary.portfolio import (
    LT_FIELDS_2026,
    fields_config_dir,
)
from worldenergydata.lower_tertiary.portfolio_analytics import (
    PortfolioAnalyticsRun,
    run_portfolio_analytics,
)
from worldenergydata.lower_tertiary.portfolio_economics import (
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


def _compute_executive_summary(
    economics_run: PortfolioEconomicsRun,
    analytics_run: PortfolioAnalyticsRun,
) -> List[str]:
    """Bind executive-summary findings to computed thresholds, not prose."""
    bullets: List[str] = []

    # Total portfolio capex from analytics (sum of WI capex shares ≡ total capex).
    total_capex = float(analytics_run.operator["sum_wi_capex_mm_usd"].sum())
    n_fields = len(economics_run.results)
    bullets.append(
        f"Portfolio totals: {n_fields} fields, "
        f"${total_capex:,.0f} M aggregate capex"
    )

    # Strongest field by NPV.
    best = max(economics_run.results, key=lambda r: r.npv_mm_usd)
    bullets.append(
        f"Strongest economics: **{best.display_name}** "
        f"(NPV ${best.npv_mm_usd:,.0f} M @ 10%, "
        f"breakeven ${best.breakeven_oil_usd_per_bbl}/bbl)"
    )

    # Marginal / negative NPV fields.
    negatives = [r for r in economics_run.results if r.npv_mm_usd < 0]
    if negatives:
        names = ", ".join(r.display_name for r in negatives)
        bullets.append(
            f"Marginal at base case: {names} "
            f"(NPV < 0 at $70/bbl with documented decline-curve cashflow)"
        )

    # Top operator.
    top_op = analytics_run.operator.iloc[0]
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
        f"${float(tech['total_capex_mm_usd']):,.0f} M total capex)"
    )

    # Pre-FID upside.
    pre_fid_count = sum(1 for r in economics_run.results if r.status == "pre_fid")
    if pre_fid_count:
        bullets.append(
            f"Pre-FID pipeline: {pre_fid_count} fields awaiting sanction; "
            f"capex estimates carry preliminary tag in citations panel"
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

    payloads = {fid: _load_field_payload(fid) for fid in field_ids}
    summary = _compute_executive_summary(economics_run, analytics_run)

    return ComprehensiveReportResult(
        economics_run=economics_run,
        analytics_run=analytics_run,
        field_payloads=payloads,
        executive_summary=summary,
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
                cells.append("—")
            elif isinstance(val, float):
                cells.append(f"{val:,.2f}")
            else:
                cells.append(str(val))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_markdown(result: ComprehensiveReportResult, path: Path | str) -> Path:
    """Write the canonical Markdown source. Regeneratable from data."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    parts: List[str] = []
    parts.append("# Lower Tertiary Comprehensive Field Report")
    parts.append("")
    parts.append(f"**Generated:** {result.timestamp_utc}")
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
    parts.append("## Portfolio Economics — All Fields")
    parts.append("")
    parts.append(_md_table(result.economics_run.to_summary_frame()))
    parts.append("")

    parts.append("## Cross-Field Analytics")
    parts.append("")
    parts.append("### Technology Generation")
    parts.append("")
    parts.append(_md_table(result.analytics_run.technology))
    parts.append("")
    parts.append("### Operator Concentration")
    parts.append("")
    parts.append(_md_table(result.analytics_run.operator))
    parts.append("")
    parts.append("### HSE per Field (minimum-viable; full coverage pending #366)")
    parts.append("")
    parts.append(_md_table(result.analytics_run.hse))
    parts.append("")
    parts.append("### Cost Benchmark vs Disclosures (no_data pending #343)")
    parts.append("")
    parts.append(_md_table(result.analytics_run.cost_benchmark))
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
        parts.append(f"- **Plateau:** {econ.plateau_mbopd:,.0f} mbopd")
        parts.append(f"- **NPV @ 10%:** ${econ.npv_mm_usd:,.0f} M")
        parts.append(f"- **Payback:** {econ.payback_years:.1f} years")
        parts.append(
            f"- **Breakeven oil price:** " f"${econ.breakeven_oil_usd_per_bbl}/bbl"
        )
        parts.append(f"- **Cashflow basis:** `{econ.cashflow_basis}`")
        parts.append("")
        parts.append("**Sensitivity:**")
        parts.append("")
        parts.append(_md_table(econ.sensitivity))
        parts.append("")
        parts.append("**Citations:**")
        parts.append("")
        parts.append(_md_table(econ.citations))
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
        "- **Pre-FID economics:** capex carries preliminary tag in field yamls; "
        "treat NPV / breakeven as scenario-grade, not commitment-grade."
    )
    parts.append(
        "- **Citation schema:** flat dict per field. Migration to the "
        "workspace-hub `Citation` schema is #361."
    )
    parts.append("")
    parts.append(
        "_This report is regenerated from "
        "`src/worldenergydata/lower_tertiary/comprehensive_report.py` + "
        "the upstream economics (#375) and analytics (#376) modules. "
        "Source-of-record for the field roster is "
        "`reports/lower_tertiary_field_summary.md`._"
    )
    parts.append("")

    out.write_text("\n".join(parts), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------


def _html_table(df: pd.DataFrame) -> str:
    return df.to_html(index=False, float_format=lambda x: f"{x:,.2f}", border=1)


def render_html(result: ComprehensiveReportResult, path: Path | str) -> Path:
    """Render a buyer-presentable HTML view directly from data."""
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
        "</style></head><body>"
    )

    parts.append("<h1>Lower Tertiary Comprehensive Field Report</h1>")
    parts.append(
        f"<div class='meta'>Generated: {html.escape(result.timestamp_utc)} &middot; "
        f"{len(result.economics_run.results)} GoM Lower Tertiary fields</div>"
    )

    parts.append("<h2>Executive Summary</h2>")
    parts.append("<div class='exec-summary'><ul>")
    for bullet in result.executive_summary:
        parts.append(f"<li>{html.escape(bullet)}</li>")
    parts.append("</ul></div>")

    parts.append("<h2>Portfolio Economics — All Fields</h2>")
    parts.append(_html_table(result.economics_run.to_summary_frame()))

    parts.append("<h2>Cross-Field Analytics</h2>")
    parts.append("<h3>Technology Generation</h3>")
    parts.append(_html_table(result.analytics_run.technology))
    parts.append("<h3>Operator Concentration</h3>")
    parts.append(_html_table(result.analytics_run.operator))
    parts.append("<h3>HSE per Field</h3>")
    parts.append(
        "<div class='caveat'>Minimum-viable per the #376 plan. "
        "Full HSE coverage requires #366 (HSE bulk dedup + ingest).</div>"
    )
    parts.append(_html_table(result.analytics_run.hse))
    parts.append("<h3>Cost Benchmark vs Disclosures</h3>")
    parts.append(
        "<div class='caveat'>Live benchmarking requires #343 (operator "
        "registry) + #344 (restatement lineage) seeding the "
        "<code>project_revision_view</code>.</div>"
    )
    parts.append(_html_table(result.analytics_run.cost_benchmark))

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
            f"Plateau: <b>{econ.plateau_mbopd:,.0f} mbopd</b><br>"
            f"NPV@10%: <b>${econ.npv_mm_usd:,.0f} M</b> &middot; "
            f"Payback: <b>{econ.payback_years:.1f} yr</b> &middot; "
            f"Breakeven: <b>${econ.breakeven_oil_usd_per_bbl}/bbl</b> &middot; "
            f"Cashflow basis: <code>{html.escape(econ.cashflow_basis)}</code></div>"
        )
        parts.append("<h4>Sensitivity</h4>")
        parts.append(_html_table(econ.sensitivity))
        parts.append("<h4>Citations</h4>")
        parts.append(_html_table(econ.citations))
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
    parts.append(
        "<div class='meta'>Regenerated from "
        "<code>src/worldenergydata/lower_tertiary/comprehensive_report.py</code>. "
        "Source-of-record for roster: "
        "<code>reports/lower_tertiary_field_summary.md</code>.</div>"
    )

    parts.append("</body></html>")
    out.write_text("".join(parts), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# PDF renderer (Chrome headless)
# ---------------------------------------------------------------------------


def render_pdf(html_path: Path | str, pdf_path: Path | str) -> Path:
    """Render the HTML to PDF via Chrome / Chromium headless.

    Falls back to writing a placeholder text file if no Chrome binary is
    available (e.g., in CI without headless Chrome) — the HTML output
    remains the canonical buyer-facing artifact in that case.
    """
    html_p = Path(html_path).resolve()
    pdf_p = Path(pdf_path).resolve()
    pdf_p.parent.mkdir(parents=True, exist_ok=True)

    chrome = (
        shutil.which("google-chrome")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )
    if chrome is None:
        pdf_p.write_text(
            "PDF rendering skipped: no chrome / chromium binary found on PATH. "
            f"HTML source available at {html_p}\n",
            encoding="utf-8",
        )
        logger.warning("No chrome binary found; wrote placeholder at %s", pdf_p)
        return pdf_p

    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={pdf_p}",
        f"file://{html_p}",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        pdf_p.write_text(
            f"PDF rendering failed: {exc}\nHTML source available at {html_p}\n",
            encoding="utf-8",
        )
        logger.warning("Chrome PDF rendering failed: %s", exc)
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
    paths["pdf"] = render_pdf(paths["html"], out / "comprehensive_2026.pdf")
    return paths
