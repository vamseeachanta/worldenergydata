"""Sourced operator opportunity pages from a registry/screen JSON snapshot.

No screening coefficients or production conversions are introduced here.
The input contract and display arithmetic are documented in
``docs/data-sources/onshore/operator-onepager.md``.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import tempfile
from datetime import date
from html import escape
from pathlib import Path

# Display layout choices, not engineering thresholds. See the contract's
# "Presentation and arithmetic" section. Content flows naturally across pages;
# the PDF readback rejects overflow instead of clipping or hiding it.
STYLE = """
@page { size: A4; margin: 12mm; }
* { box-sizing: border-box; }
body { font: 10pt Arial, sans-serif; color: #152d40; margin: 0; }
h1 { font-size: 19pt; margin: 0 0 4mm; }
h2 { font-size: 12pt; margin: 4mm 0 2mm; }
p { margin: 2mm 0; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; vertical-align: top; padding: 1.5mm;
         border-bottom: 1px solid #c8d3dc; overflow-wrap: anywhere; }
th { width: 25%; }
.bar { height: 3mm; background: #237886; }
.gap { color: #704000; }
.limits { border: 1px solid #704000; padding: 2mm; margin-top: 4mm; }
footer { font-size: 8pt; overflow-wrap: anywhere; margin-top: 3mm; }
.synthetic { font-weight: bold; color: #8a3000; }
"""

SUMMARY = (
    ("well_count_total", "Total wells", "wells", True),
    ("well_count_producing", "Producing wells", "wells", True),
    ("well_count_inactive", "Inactive wells", "wells", True),
    ("field_count", "Fields", "fields", True),
    ("oil_bbl_last12", "Oil", "bbl", False),
    ("gas_mcf_last12", "Gas", "Mcf", False),
    ("water_bbl_last12", "Water", "bbl", False),
)

LIMITATIONS = (
    "Public production supports statistical observations, not an uplift promise. "
    "Reservoir depletion versus mechanical failure cannot be distinguished from "
    "rate data alone; each candidate requires operating records and diagnostics. "
    "Lease totals cannot be interpreted as individual-well production. "
    "Operator of record does not establish ownership or working interest. "
    "Inventory differences can reflect reporting dates, transfers or status changes. "
    "Specific uplift, economics and working interest are NOT_EVALUATED."
)


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected non-empty text")
    return escape(value)


def _number(value: object, *, count: bool = False, signed: bool = False) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or (value < 0 and not signed)
        or (count and int(value) != value)
    ):
        raise ValueError(
            "Expected a finite figure in the permitted range (integer for counts)"
        )
    return value


def _source(source_id: str, sources: dict) -> str:
    if not isinstance(source_id, str) or source_id not in sources:
        raise ValueError("Figure has no known source")
    return f"[{_text(source_id)}]"


def _measure(
    item: dict | None, sources: dict, unit: str, *, count=False, signed=False
) -> str:
    if item is None:
        return "not captured"
    if not isinstance(item, dict) or "value" not in item or "source" not in item:
        raise ValueError("A figure requires value and source; use null for a gap")
    value = _number(item["value"], count=count, signed=signed)
    formatted = str(int(value)) if count else f"{value:,.1f}"
    return f"{formatted} {_text(unit)} {_source(item['source'], sources)}"


def _validate_sources(bundle: dict) -> dict:
    if bundle.get("schema_version") != 1:
        raise ValueError("Unsupported snapshot schema version")
    if bundle.get("data_status") not in {"public", "synthetic"}:
        raise ValueError("data_status must be public or synthetic")
    sources = bundle.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("A regulator dataset and vintage are required")
    for source_id, source in sources.items():
        _text(source_id)
        for field in ("dataset", "vintage", "period", "reference"):
            _text(source.get(field))
        try:
            date.fromisoformat(source["vintage"])
        except ValueError as exc:
            raise ValueError("Source vintage requires an ISO calendar date") from exc
    _source(bundle.get("registry_source"), sources)
    return sources


def _select_operator(bundle: dict, operator_no: str) -> dict:
    operators = bundle.get("operators")
    if not isinstance(operators, list):
        raise TypeError("operators must be a registry list")
    registry = {}
    for operator in operators:
        key = operator.get("operator_no")
        _text(key)
        if key in registry:
            raise ValueError("Duplicate operator ID in registry")
        registry[key] = operator
    if operator_no not in registry:
        raise ValueError("Unknown operator ID")
    return registry[operator_no]


def _candidates(screen: dict, sources: dict, limit: int) -> str:
    candidates = screen.get("candidates")
    if not isinstance(candidates, list):
        raise TypeError("Screen requires a candidate list (empty is permitted)")
    ranks, identities = set(), set()
    rows = []
    for candidate in candidates:
        rank = _number(candidate.get("rank"), count=True)
        identity = _text(candidate.get("entity_id"))
        if rank == 0 or rank in ranks or identity in identities:
            raise ValueError("Candidate ranks and identities must be unique")
        ranks.add(rank)
        identities.add(identity)
        granularity = candidate.get("granularity")
        if granularity not in {"well", "lease"}:
            raise ValueError("Candidate granularity must be well or lease")
        evidence = candidate.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("Each candidate requires sourced evidence")
        evidence_text = "; ".join(
            f"{_text(item.get('label'))}: "
            f"{_measure(item, sources, item.get('unit'), signed=True)}"
            for item in evidence
        )
        basis = (
            "lease-level; not allocated to individual wells"
            if granularity == "lease"
            else "well-level"
        )
        row = (
            f"<tr><td>{int(rank)}</td><td>{identity}<br>{basis}</td>"
            f"<td>{evidence_text}<br>Cause NOT_EVALUATED</td></tr>"
        )
        rows.append((rank, row))
    rows.sort()
    if not rows:
        return "<p>No candidates supplied by the screen; no uplift inferred.</p>"
    omitted = len(rows) - len(rows[:limit])
    note = f"<p>{omitted} additional candidates omitted; full ranking in screen.</p>"
    return (
        "<table><thead><tr><th>Rank</th><th>Candidate / reporting basis</th>"
        "<th>Evidence (inference only)</th></tr></thead><tbody>"
        + "".join(row for _, row in rows[:limit])
        + "</tbody></table>"
        + (note if omitted else "")
    )


def _peers(peer: dict | None, sources: dict) -> str:
    if peer is None:
        return "<p>Peer comparison not captured; NOT_EVALUATED.</p>"
    metric, unit, cohort = (_text(peer.get(k)) for k in ("metric", "unit", "cohort"))
    # No inferred peer values: both measurements must be present for a chart.
    values = [peer.get("operator"), peer.get("median")]
    labels = [_measure(item, sources, peer["unit"]) for item in values]
    if any(item is None for item in values):
        return f"<p>{metric} ({unit}); {cohort}. Peer comparison not captured.</p>"
    maximum = max(item["value"] for item in values)
    if len({sources[item["source"]]["period"] for item in values}) != 1:
        raise ValueError("Peer comparison requires matching reporting periods")
    bars = []
    for name, item, label in zip(("Operator", "Peer median"), values, labels):
        # Contract: width (%) = 100 * value / max(values), or zero if all zero.
        # This is display scaling, not a recovery factor or an uplift estimate.
        width = 100 * item["value"] / maximum if maximum else 0
        bars.append(
            f'<p>{name}: {label}</p><div class="bar" style="width:{width:.1f}%"></div>'
        )
    return f"<p>{metric}; cohort: {cohort}</p>" + "".join(bars)


def render_html(bundle: dict, operator_no: str, *, candidate_limit: int = 5) -> str:
    """Render a deterministic standalone page; limitations cannot be disabled.

    The default candidate count is a layout budget, documented in the contract,
    not an engineering acceptance limit. All supplied rows are validated.
    """
    if (
        isinstance(candidate_limit, bool)
        or not isinstance(candidate_limit, int)
        or candidate_limit < 1
    ):
        raise ValueError("candidate_limit must be a positive integer")
    sources = _validate_sources(bundle)
    operator = _select_operator(bundle, operator_no)
    summary = operator.get("summary", {})
    rows = [
        f"<tr><th>{label}</th><td>"
        f"{_measure(summary.get(key), sources, unit, count=count)}</td></tr>"
        for key, label, unit, count in SUMMARY
    ]
    screen = operator.get("screen")
    if screen is None:
        candidates = "<p>Screen not captured; candidacy NOT_EVALUATED.</p>"
        peers = _peers(None, sources)
        method = "Screen method not captured."
        fpr = "NOT_EVALUATED (validation evidence not captured)"
    else:
        method = (
            _text(screen.get("method")) + " " + _source(screen.get("source"), sources)
        )
        candidates = _candidates(screen, sources, candidate_limit)
        peers = _peers(screen.get("peer_comparison"), sources)
        rate = screen.get("false_positive_rate")
        fpr = (
            _measure(rate, sources, "fraction")
            if rate is not None
            else ("NOT_EVALUATED (validation evidence not captured)")
        )
        if rate is not None and rate["value"] > 1:
            raise ValueError("False-positive fraction must not exceed unity")
        if rate is not None:
            # Percentage display = 100 * supplied fraction; contract arithmetic.
            fpr = f"{100 * rate['value']:.1f} % {_source(rate['source'], sources)}"
    source_rows = "".join(
        f"<p>{_source(key, sources)} {_text(source['dataset'])}; "
        f"vintage {_text(source['vintage'])}; period {_text(source['period'])}; "
        f"{_text(source['reference'])}</p>"
        for key, source in sorted(sources.items())
    )
    banner = (
        '<p class="synthetic">SYNTHETIC EXAMPLE — not regulator observations</p>'
        if (bundle["data_status"] == "synthetic")
        else ""
    )
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>Operator {_text(operator_no)} opportunity screen</title>"
        '<meta http-equiv="Content-Security-Policy" '
        "content=\"default-src 'none'; style-src 'unsafe-inline'\">"
        f"<style>{STYLE}</style></head><body>{banner}"
        f"<h1>Operator {_text(operator_no)} opportunity screen</h1>"
        "<p>Public-data observations; no predicted uplift.</p>"
        f"<h2>Operator summary {_source(bundle['registry_source'], sources)}</h2>"
        f"<table>{''.join(rows)}</table>"
        f"<h2>Ranked candidates</h2><p>{method}</p>{candidates}"
        f"<h2>Peer comparison</h2>{peers}"
        '<section class="limits"><h2>What this data cannot tell you</h2>'
        f"<p>{LIMITATIONS}</p><p>False-positive rate: {fpr}</p></section>"
        f"<footer><h2>Sources and reporting periods</h2>{source_rows}</footer>"
        "</body></html>\n"
    )


def render_pdf(
    html_path: Path, pdf_path: Path, *, chrome="google-chrome", pdfinfo="pdfinfo"
) -> None:
    """Publish only a PDF whose page count has been read back as exactly one.

    Headless execution: Chrome Headless mode (accessed 2026-10-20),
    https://developer.chrome.com/docs/automation-and-testing/headless
    PDF command and header suppression: issue #1128, Requirements.
    Rejected PDFs and profiles remain as diagnostics, outside version control.
    """
    profile = tempfile.mkdtemp(prefix="onepager-profile-")
    with tempfile.NamedTemporaryFile(
        dir=pdf_path.parent, suffix=".pdf", delete=False
    ) as handle:
        pending = Path(handle.name)
    subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={pending.resolve()}",
            html_path.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if not pending.read_bytes().startswith(b"%PDF-"):
        raise ValueError("Chrome did not produce a PDF")
    info = subprocess.run(
        [pdfinfo, str(pending)], check=True, capture_output=True, text=True
    )
    # Issue #1128: exactly one page is the acceptance criterion, not a tolerance.
    pages = re.search(r"^Pages:\s+(\d+)\s*$", info.stdout, re.MULTILINE)
    if pages is None or int(pages.group(1)) != 1:
        raise ValueError(
            "PDF must contain exactly one page; shorten content and rebuild"
        )
    pending.replace(pdf_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--candidate-limit", default=5, type=int)
    parser.add_argument(
        "--html-only", action="store_true", help="Do not claim PDF validation"
    )
    parser.add_argument("--chrome", default="google-chrome")
    parser.add_argument("--pdfinfo", default="pdfinfo")
    args = parser.parse_args(argv)
    try:
        page = render_html(
            json.loads(args.input.read_text(encoding="utf-8")),
            args.operator,
            candidate_limit=args.candidate_limit,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        html_path = args.output_dir / "onepager.html"
        html_path.write_text(page, encoding="utf-8")
        if not args.html_only:
            render_pdf(
                html_path,
                args.output_dir / "onepager.pdf",
                chrome=args.chrome,
                pdfinfo=args.pdfinfo,
            )
    except FileNotFoundError:
        parser.exit(1, "Required input or PDF executable is unavailable.\n")
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        subprocess.CalledProcessError,
    ):
        parser.exit(1, "Invalid snapshot or PDF build; output is not validated.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
