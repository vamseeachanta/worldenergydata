"""Deterministic, escaped HTML and JSON twins from the result contract."""

import re
from collections.abc import Iterable
from html import escape
from pathlib import Path

from .models import AcreageEvidenceResult

CSS = """
body{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#172b39}
h1{margin-top:0}section{margin:2rem 0}table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{text-align:left;padding:.6rem;border-bottom:1px solid #ccd6df;vertical-align:top}
.banner{padding:1rem;background:#e6eff7;border-left:6px solid #235978}
.fixture,.gap{padding:1rem;background:#fff0cd;border-left:6px solid #996100}
.bar{height:12px;background:#235978;max-width:100%}caption{text-align:left;padding:.8rem}
"""


def text(value: object) -> str:
    return escape("unavailable" if value is None else str(value), quote=True)


def _table(headers: list[str], rows: Iterable[Iterable[object]], caption: str) -> str:
    heading = "".join(f"<th>{text(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{text(v)}</td>" for v in row) + "</tr>" for row in rows
    )
    return (
        f"<table><thead><tr>{heading}</tr></thead><tbody>{body}</tbody>"
        f"<caption>{text(caption)}</caption></table>"
    )


def _acreage(result: AcreageEvidenceResult) -> str:
    rows, bars = [], []
    for key in type(result.acreage).model_fields:
        item = getattr(result.acreage, key)
        value = "unavailable" if item.value is None else f"{item.value:.3f}"
        rows.append([key, value, item.status, item.source_id, item.note])
        if (
            key in {"leased_acres", "expired_or_nonleased_acres", "no_record_acres"}
            and item.value is not None
        ):
            width = 100 * item.value / result.tract.gross_area_acres
            bars.append(
                f"<p>{text(key)}: {value} acres</p>"
                f'<div class="bar" style="width:{width:.3f}%"></div>'
            )
    return _table(
        ["Metric", "Area (acres)", "Status", "Source ID", "Note"],
        rows,
        "Table 1. Quarter-quarter screening acreage.",
    ) + "".join(bars)


def _records(result: AcreageEvidenceResult) -> str:
    rows = [
        [
            r.record_serial,
            r.record_type,
            r.record_status,
            r.effective_date,
            r.expiration_date,
            r.public_lessee,
            r.public_operator,
            f"{r.area.value:.3f} {r.area.unit}",
            r.area_acres.model_dump(),
            r.intersect_acres.model_dump(),
            r.source_id,
            r.retrieved_at.isoformat(),
        ]
        for r in result.records
    ]
    return _table(
        [
            "Serial",
            "Type",
            "Status",
            "Effective date",
            "Expiration date",
            "Lessee",
            "Operator",
            "Reported area",
            "Converted area (acres)",
            "Intersection (acres)",
            "Source ID",
            "Retrieved at",
        ],
        rows,
        "Table 2. Federal record evidence.",
    )


def render_html(result: AcreageEvidenceResult) -> str:
    fixture = (
        '<p class="fixture">FIXTURE-DATA — synthetic screening demonstration.</p>'
        if any(s.kind == "fixture" for s in result.sources)
        else ""
    )
    tract = _table(
        ["Input", "Value"], result.tract.model_dump().items(), "Table 3. Input echo."
    )
    exceptions = _table(
        ["Kind", "Serials", "Area (acres)", "Detail"],
        [
            [e.kind, ", ".join(e.record_serials), e.acres, e.detail]
            for e in result.exceptions
        ],
        "Table 4. Screening exceptions.",
    )
    sources = _table(
        ["Source ID", "Dataset", "Kind", "Retrieved at", "Licence", "URL"],
        [
            [
                s.source_id,
                s.dataset,
                s.kind,
                s.retrieved_at.isoformat(),
                s.license_note,
                s.url,
            ]
            for s in result.sources
        ],
        "Table 5. Provenance appendix.",
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Federal acreage evidence</title>
<style>{CSS}</style></head><body>
<div class="banner"><h1>{text(result.screening_status)}</h1>
<p>{text(', '.join(result.screening_reasons))}</p></div>{fixture}
<p>Data as of {text(result.data_as_of.isoformat())}. This is the data date.</p>
<section><h2>Tract input</h2>{tract}</section>
<section><h2>Acreage rollup</h2>{_acreage(result)}</section>
<section><h2>Federal records</h2>{_records(result)}</section>
<section><h2>Exceptions</h2>{exceptions}</section>
<section class="gap"><h2>County recorder / title-chain gap: not_evaluated</h2>
<p>{text(result.title_chain_gap.statement)}</p></section>
<p>Pilot geometry assumes exactly 40 acres per quarter-quarter in one section.
Lots, irregular surveys and multi-section tracts are not evaluated.</p>
<section><h2>Provenance</h2>{sources}</section></body></html>
"""


def write_outputs(
    result: AcreageEvidenceResult, result_folder: str | Path, label: str
) -> dict[str, Path]:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
        raise ValueError("Output label must be a simple filename slug")
    folder = Path(result_folder)
    folder.mkdir(parents=True, exist_ok=True)
    outputs = {
        "result_json": folder / f"{label}_result.json",
        "report_html": folder / f"{label}_report.html",
    }
    outputs["result_json"].write_text(
        result.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    outputs["report_html"].write_text(render_html(result), encoding="utf-8")
    return outputs
