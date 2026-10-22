#!/usr/bin/env python3
"""Build the offline federal acreage module analysis from the public fixture.

Run from the repository: PYTHONPATH=src python scripts/reports/build_federal_acreage_report.py
Only the requested HTML output is written. No live records are acquired.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from html import escape
from pathlib import Path

from worldenergydata.federal_acreage import FixtureRecordProvider, evaluate

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "docs/reports/modules/wfederalacreage"
MODULE = ROOT / "src/worldenergydata/federal_acreage"
EXAMPLE = ROOT / "examples/workflows/federal-acreage-evidence/fixture_records.json"
INPUTS = (EXAMPLE, *sorted(MODULE.glob("*.py")))
ROLLUP_LABELS = {
    "gross_area_acres": "Gross tract",
    "federal_record_coverage_acres": "Record coverage",
    "leased_acres": "Active leases",
    "expired_or_nonleased_acres": "Expired or nonleased",
    "no_record_acres": "Without supplied records",
}
METRIC_KEYS = dict(
    zip(ROLLUP_LABELS, ("gross", "coverage", "leased", "expired", "no_record"))
)


def calculation_digests() -> dict[str, str]:
    """Digest LF-normalized UTF-8 calculation text for portable readback."""
    return {
        path.relative_to(ROOT)
        .as_posix(): hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8"))
        .hexdigest()
        for path in INPUTS
    }


def area_tolerance() -> float:
    """Read the existing software policy rather than duplicating its value."""
    tree = ast.parse((MODULE / "evidence.py").read_text(encoding="utf-8"))
    check = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_check_area"
    )
    limits = [
        node.comparators[0].value
        for node in ast.walk(check)
        if isinstance(node, ast.Compare)
        and isinstance(node.ops[0], ast.Gt)
        and isinstance(node.comparators[0], ast.Constant)
    ]
    if len(limits) != 1:
        raise ValueError(
            "Area policy changed; review the report basis before rebuilding"
        )
    return float(limits[0])


def example_result():
    provider = FixtureRecordProvider(EXAMPLE)
    return evaluate(provider.tract, *provider.records_for_tract(provider.tract))


def example_metrics(result) -> dict[str, float]:
    values = {
        METRIC_KEYS[key]: getattr(result.acreage, key).value for key in ROLLUP_LABELS
    }
    hectare = next(item for item in result.records if item.area.unit == "hectares")
    values.update(
        tract_cells=len(result.tract.aliquots),
        record_count=len(result.records),
        exception_count=len(result.exceptions),
        cell_area=result.tract.gross_area_acres / len(result.tract.aliquots),
        hectare_input=hectare.area.value,
        converted=hectare.area_acres.value,
        overlap=next(
            item.acres for item in result.exceptions if item.kind == "overlap"
        ),
        tolerance=area_tolerance(),
        zero=0,
    )
    if any(value is None for value in values.values()):
        raise ValueError(
            "The example has unavailable values; revise the report narrative"
        )
    return values


def display_number(key: str, value: float) -> str:
    if key in {"hectare_input", "converted"}:
        return f"{value:.4f}"
    if key == "tolerance":
        return f"{value:.1f}"
    return f"{value:.0f}"


def metric(key: str, values: dict[str, float], tag: str = "span") -> str:
    return f'<{tag} data-metric="{key}">{display_number(key, values[key])}</{tag}>'


def area_chart(result, values) -> str:
    parts = [
        '<svg id="area-chart" viewBox="0 0 820 365" role="group" '
        'aria-label="Synthetic tract acreage by output category">'
    ]
    parts.append('<text x="30" y="22">Area (acres)</text>')
    parts.append('<line x1="55" y1="65" x2="800" y2="65" class="limit"/>')
    parts.append(
        '<text x="360" y="48">Gross tract-area bound: '
        f'{metric("gross", values, "tspan")} acres</text>'
    )
    parts.append(f'<text x="30" y="285">{metric("zero", values, "tspan")}</text>')
    for index, (key, label) in enumerate(ROLLUP_LABELS.items()):
        area = getattr(result.acreage, key).value
        x = 70 + index * 147
        height = 210 * area / values["gross"]
        title = (
            f"Synthetic tract; {label}; acreage {area:.0f} acres; "
            f"gross tract-area bound {values['gross']:.0f} acres"
        )
        parts.append(
            f'<rect x="{x}" y="{275-height:.3f}" width="90" '
            f'height="{height:.3f}" class="bar" tabindex="0" '
            f'role="img" aria-label="{escape(title)}" '
            f'data-description="{escape(title)}"><title>{escape(title)}</title></rect>'
        )
        parts.append(
            f'<text x="{x}" y="{265-height:.3f}">'
            f'{metric(METRIC_KEYS[key], values, "tspan")}</text>'
        )
        parts.append(
            f'<text x="{x}" y="305" class="small-label">{escape(label)}</text>'
        )
    parts.append('<text x="55" y="345">Category</text></svg>')
    return "\n".join(parts)


def tract_schematic(result, values) -> str:
    """Draw the actual aliquot nesting, with the inner quarter named first."""
    parts = [
        '<svg viewBox="0 0 760 510" role="img" '
        'aria-label="Idealized single-section plan showing the northern-half tract">',
        '<text x="15" y="30">North ↑</text>',
        '<text x="155" y="30">Idealized section; no surveyed coordinates</text>',
    ]
    tract = set(result.tract.aliquots)
    for outer, ox, oy in (("NW", 0, 0), ("NE", 2, 0), ("SW", 0, 2), ("SE", 2, 2)):
        for inner, ix, iy in (("NW", 0, 0), ("NE", 1, 0), ("SW", 0, 1), ("SE", 1, 1)):
            cell = f"{inner}-{outer}"
            matching = [r for r in result.records if cell in (r.aliquots or [])]
            kind = (
                "outside"
                if cell not in tract
                else (
                    "uncovered"
                    if not matching
                    else (
                        "expired"
                        if all(r.record_status == "expired" for r in matching)
                        else "active"
                    )
                )
            )
            label = {
                "outside": "Outside tract",
                "uncovered": "No supplied record",
                "expired": "Expired lease",
                "active": "Active lease",
            }[kind]
            x, y = 90 + 145 * (ox + ix), 55 + 95 * (oy + iy)
            parts.append(
                f'<rect x="{x}" y="{y}" width="145" height="95" '
                f'class="cell {kind}"><title>{cell}: {label}</title></rect>'
            )
            parts.append(f'<text x="{x+8}" y="{y+32}">{cell}</text>')
            parts.append(
                f'<text x="{x+8}" y="{y+58}" class="small-label">{label}</text>'
            )
            if len(matching) > 1:
                parts.append(
                    f'<text x="{x+8}" y="{y+80}" class="small-label">Overlap</text>'
                )
    parts.append(
        '<rect x="90" y="55" width="580" height="190" class="tract-boundary"/>'
    )
    parts.append(
        '<text x="90" y="466">Each model cell: '
        f'{metric("cell_area", values, "tspan")} acres; tract boundary outlined.</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def record_table(result) -> str:
    rows = []
    for record in result.records:
        acres = (
            format(record.area.value, ".0f")
            if record.area.unit == "acres"
            else "Not applicable"
        )
        hectares = (
            format(record.area.value, ".4f")
            if record.area.unit == "hectares"
            else "Not applicable"
        )
        cells = (
            ", ".join(record.aliquots) if record.aliquots is not None else "Unavailable"
        )
        intersection = (
            "Unavailable"
            if record.intersect_acres.value is None
            else f"{record.intersect_acres.value:.0f}"
        )
        rows.append(
            "<tr>"
            + "".join(
                f"<td>{escape(str(item))}</td>"
                for item in (
                    record.record_serial,
                    record.record_status,
                    acres,
                    hectares,
                    cells,
                    intersection,
                )
            )
            + '<td><a href="#ref-example">Public example</a></td></tr>'
        )
    return "\n".join(rows)


def json_script(value) -> str:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True
    ).replace("<", "\\u003c")


def render_report() -> str:
    result = example_result()
    if result.screening_status != "evidence_partial":
        raise ValueError("Example disposition changed; review the report narrative")
    values = example_metrics(result)
    template = (FOLDER / "report.template.html").read_text(encoding="utf-8")
    style = (FOLDER / "house-style.css").read_text(encoding="utf-8")
    changes = json.loads((FOLDER / "changes.json").read_text(encoding="utf-8"))
    digests = calculation_digests()
    replacements = {
        "style": style,
        "chart": area_chart(result, values),
        "schematic": tract_schematic(result, values),
        "records": record_table(result),
        "data_date": result.data_as_of.date().isoformat(),
        "changes": json_script(changes),
        "digests": json_script(digests),
        "chart_data": json_script(
            {
                "limit": values["gross"],
                "areas": [
                    round(getattr(result.acreage, key).value, 4)
                    for key in ROLLUP_LABELS
                ],
            }
        ),
    }
    html = re.sub(r"@@metric:(\w+)@@", lambda match: metric(match[1], values), template)
    for key, value in replacements.items():
        html = html.replace(f"@@{key}@@", value)
    # Bind the final rendered content, including generated tables and graphics.
    binding = hashlib.sha256(html.encode("utf-8")).hexdigest()
    html = html.replace("@@binding@@", binding)
    if "@@" in html:
        raise ValueError("Unresolved report placeholder")
    return html


def write_report(output: Path) -> None:
    destination = output.resolve()
    protected = {
        *[path.resolve() for path in INPUTS],
        *[path.resolve() for path in FOLDER.iterdir() if path.name != "index.html"],
    }
    if destination in protected or destination.suffix.lower() != ".html":
        raise ValueError("Report output cannot replace input or presentation sources")
    html = render_report()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8", newline="\n")
    if output.read_text(encoding="utf-8") != html:
        raise OSError("Report readback differs from the generated content")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=FOLDER / "index.html")
    args = parser.parse_args()
    write_report(args.output)
    print("Federal acreage module analysis rebuilt.")


if __name__ == "__main__":
    main()
