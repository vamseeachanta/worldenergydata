"""Deterministic machine output and an escaped, self-contained HTML cost map."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from hashlib import sha256
from html import escape
from pathlib import Path

from .accounting import Interval


def compare_estimates(direct: Interval | None, bottom_up: Interval | None) -> dict:
    """Interval difference and intersection, without midpoint substitution.

    Definitions: cost-map program plan (2026), Shared Contract to Freeze.
    Dependence between estimates is not assumed away by this comparison.
    """
    if direct is None or bottom_up is None:
        return {"relation": "indeterminate", "variance": None}
    relation = (
        "direct_above"
        if direct.low > bottom_up.high
        else "bottom_up_above" if bottom_up.low > direct.high else "overlap"
    )
    return {
        "relation": relation,
        "variance": Interval(direct.low - bottom_up.high, direct.high - bottom_up.low),
    }


def _json_default(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite report value")
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError("unsupported report value")


def canonical_json(payload: dict) -> str:
    return (
        json.dumps(
            payload,
            default=_json_default,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )


def _table(value, as_percent=False, rounding=None):
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        # asdict recursively converts Interval objects, so recognize their bounds.
        interval = set(value) == {"low", "high"} and all(
            isinstance(bound, Decimal) for bound in value.values()
        )
        fraction_keys = {
            "coverage",
            "residual_fraction",
            "alpha",
            "min_coverage",
            "max_mean_ape",
            "validation_mean_ape",
            "validation_coverage",
            "ape",
        }
        directions = {"low": ROUND_FLOOR, "high": ROUND_CEILING} if interval else {}
        return (
            "<table>"
            + "".join(
                f"<tr><th>{escape(str(key))}</th><td>"
                f"{_table(item, as_percent or key in fraction_keys, directions.get(key))}"
                "</td></tr>"
                for key, item in value.items()
            )
            + "</table>"
        )
    if isinstance(value, (tuple, list)):
        return (
            "<ol>"
            + "".join(f"<li>{_table(item, as_percent)}</li>" for item in value)
            + "</ol>"
        )
    if isinstance(value, Decimal):
        with localcontext() as context:
            if rounding is not None:
                context.rounding = rounding
            return escape(format(value, ".1%" if as_percent else ".1f"))
    return escape("unavailable" if value is None else str(value))


def render_html(payload: dict) -> str:
    """Render only escaped text; supplied source strings never become raw links."""
    sections = (
        ("Inputs", "inputs"),
        ("Asset → project: bottom-up", "bottom_up"),
        ("Project → assets: joint allocations", "top_down"),
        ("Dated trace", "trace"),
        ("Estimator and validation", "estimator"),
        ("Model consistency", "consistency"),
        ("Frozen workbook comparison", "workbook"),
        ("Known limits", "limits"),
        ("Sources", "sources"),
    )
    nav = " · ".join(f'<a href="#{key}">{escape(title)}</a>' for title, key in sections)
    content = "".join(
        f'<section id="{key}"><h2>{escape(title)}</h2>{_table(payload[key])}</section>'
        for title, key in sections
    )
    return (
        '<!doctype html>\n<html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Portfolio cost model: worked example</title>"
        "<style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:1rem;"
        "color:#18313b;background:#f5f7f8}table{border-collapse:collapse;width:100%;"
        "margin:.4rem 0}th,td{border:1px solid #bdcbd0;padding:.4rem;text-align:left;"
        "vertical-align:top}th{width:24%}section{margin-top:2rem}nav{line-height:2}"
        ".notice{padding:1rem;background:#fff0c2}li{margin:.5rem 0}</style>"
        "<h1>Portfolio cost model: worked example</h1><h2>Summary</h2>"
        f'<p class="notice">{escape(payload["summary"])}</p>'
        '<p class="unverified">Synthetic example; real-project cost estimates '
        "remain unevaluated.</p>"
        f'<h2>Revision history</h2>{_table(payload["revision_history"])}'
        "<p>Provenance: disclosed · award_derived · allocated · modeled · assumed · "
        "unavailable. These statuses remain attached to their evidence.</p>"
        "<p>Marginal bands are not additive. Each joint scenario conserves its total. "
        "Missing events are not interpolated. Display values use one decimal place; "
        "the JSON retains calculation precision.</p>"
        f"<nav>{nav}</nav>{content}</html>\n"
    )


def write_report(payload: dict, output_dir: Path) -> None:
    """Write reproducible outputs, pinning input evidence and both output digests.

    No current clock, filesystem path, workstation identity or workbook metadata
    enters the artifact. The revision date is an explicit payload input.
    """
    encoded = canonical_json(payload)
    html = render_html(payload)
    outputs = {"portfolio_example.json": encoded, "portfolio_example.html": html}
    manifest = {
        "contract": "portfolio-worked-example-v1",
        "synthetic": payload["synthetic"],
        "inputs_sha256": sha256(canonical_json(payload["inputs"]).encode()).hexdigest(),
        "output_sha256": {
            name: sha256(value.encode()).hexdigest() for name, value in outputs.items()
        },
        "rounding": "Decimal arithmetic; explicit allocation quantum; display one decimal",
        "generated_at": "explicit revision date; no wall clock",
    }
    outputs["portfolio_example_manifest.json"] = canonical_json(manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in outputs.items():
        (output_dir / name).write_text(value, encoding="utf-8")
