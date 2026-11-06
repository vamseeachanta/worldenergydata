"""Self-contained, offline transaction and lifecycle reports with JSON readback."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path


def _text(value: object) -> str:
    return html.escape(str(value) if value is not None else "NOT_EVALUATED", quote=True)


def _quantity(fact: dict) -> str:
    if "range" in fact:
        return " – ".join(f"{value:,}" for value in fact["range"])
    return f'{fact["value"]:,}' if fact.get("value") is not None else "NOT_EVALUATED"


def _table(headers: list[str], rows: list[list]) -> str:
    header = "".join(f"<th scope='col'>{_text(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_text(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return (
        f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"
        f"<p>Table. {_text(', '.join(headers))}.</p>"
    )


def _page(title: str, summary: str, body: str, revisions: list[list]) -> str:
    revision = _table(["Revision", "Date", "Change and reason"], revisions)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_text(title)}</title><style>
body{{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:1rem;color:#162b3c}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
td,th{{border:1px solid #abbcc8;padding:.5rem;text-align:left}}
th{{background:#edf3f7}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf3f7;padding:1rem}}
details{{margin:1rem 0}}a{{color:#125e83}}.status{{border-left:5px solid #b96b00;padding:1rem}}
</style></head><body><h1>{_text(title)}</h1>
<h2>Summary</h2><p class="status">{_text(summary)}</p>
<h2>Revision history</h2>
{revision}
<nav><a href="index.html">Transaction</a> | <a href="lifecycle.html">Lifecycle</a></nav>
{body}</body></html>
"""


def _lifecycle_body(package: dict, out: Path, root: Path) -> str:
    rows = []
    links = []
    for asset in package["lifecycle"]["assets"]:
        rows.append(
            [
                asset["name"],
                asset["kind"],
                asset["host_concept"],
                asset["field_concept"],
                asset["catalog_discovery"],
                asset["catalog_first_production"],
                asset["transaction_membership_status"],
                asset["transaction_membership_reason"],
                asset["generated_page_status"],
            ]
        )
        if asset["report_path"]:
            try:
                target = Path(
                    os.path.relpath(root / asset["report_path"], out)
                ).as_posix()
            except ValueError:
                links.append(
                    f'<li>{_text(asset["name"])}: link omitted because output and '
                    "repository use different drives.</li>"
                )
                continue
            links.append(
                f'<li><a href="{_text(target)}">{_text(asset["name"])}</a></li>'
            )
    return (
        f'<p>{_text(package["lifecycle"]["coverage_note"])}</p>'
        + _table(
            [
                "Asset",
                "Role",
                "Host concept",
                "Field concept",
                "Catalog discovery",
                "Catalog first production",
                "Sale membership",
                "Membership basis or limitation",
                "Existing page",
            ],
            rows,
        )
        + f'<p>{_text(package["lifecycle"]["limitation"])}</p>'
        + "<h2>Existing field-development pages</h2><ul>"
        + "".join(links)
        + "</ul>"
    )


def _transaction_body(package: dict) -> str:
    rows = []
    for basis, metrics in package["metrics"]["bases"].items():
        for metric, result in metrics.items():
            value = (
                f'{result["value"]:,.2f}'
                if result["value"] is not None
                else result["status"]
            )
            if "range" in result:
                value = " – ".join(f"{bound:,.2f}" for bound in result["range"])
            inputs = result["inputs"]
            numerator = inputs["consideration"]
            denominator = inputs["denominator"]
            input_values = (
                f'{_quantity(numerator)} {numerator["unit"]} / '
                f'{_quantity(denominator)} {denominator["unit"]}'
            )
            rows.append(
                [
                    basis,
                    metric,
                    value,
                    result["unit"],
                    input_values,
                    result["reason"]
                    or "Same basis and acquired-interest subject; no return threshold",
                ]
            )
    facts = package["input_echo"]
    body = (
        "<h2>Announced transaction</h2>"
        + _table(
            ["Basis", "Consideration (USD)", "Subject", "Basis or limitation"],
            [
                [
                    basis,
                    _quantity(values["consideration"]),
                    values["consideration"].get("subject"),
                    values["consideration"].get("reason")
                    or values["consideration"]["citation"]["locator"],
                ]
                for basis, values in facts["bases"].items()
            ],
        )
        + f'<p>Closing: {_text(package["transaction"]["closing_status"])}</p>'
        + _table(
            ["Subject", "Sold working interest (fraction)", "Source locator"],
            [
                [fact["subject"], fact["value"], fact["citation"]["locator"]]
                for fact in package["transaction"]["working_interests"]
            ],
        )
        + "<h2>Transaction ratios</h2>"
        + _table(
            ["Basis", "Metric", "Result", "Unit", "Inputs", "Criterion or limitation"],
            rows,
        )
        + "<p>Method: consideration USD / acquired-interest reserves boe; "
        "consideration USD / acquired-interest production boe/day. "
        "No interest scaling, energy-equivalence conversion or "
        "assumed cash-flow parameters are applied.</p>"
        + "<h2>Terms and preferential-right scenarios</h2>"
        + _table(
            ["Term", "Status", "Missing evidence"],
            [
                [key, term["status"], term["reason"]]
                for key, term in package["transaction"]["terms"].items()
            ],
        )
        + _table(
            ["Conditional scenario", "Status", "Basis"],
            [
                [scenario["id"], scenario["status"], scenario["reason"]]
                for scenario in package["transaction"]["scenarios"]
            ],
        )
        + "<h2>Field economics readiness</h2>"
        + _table(
            [
                "Field",
                "Block candidate",
                "Block matched",
                "Economics status",
                "Missing inputs",
            ],
            [
                [
                    row["name"],
                    row["block"],
                    row["block_match"],
                    row["status"],
                    ", ".join(row["missing_inputs"]),
                ]
                for row in package["economics_readiness"]["fields"]
            ],
        )
        + "<p>NPV is NOT_EVALUATED for every field. "
        "Refresh requires verified field-to-lease/API membership, dated BSEE production, "
        "aligned reserves and interest scope, price, costs, fiscal terms, "
        "discount rate and abandonment timing.</p>" + "<h2>Source provenance</h2>"
    )
    for source_id, source in package["provenance"]["sources"].items():
        body += (
            f'<details><summary>{_text(source_id)}: {_text(source["access"])}</summary>'
        )
        if "url" in source:
            body += f'<a href="{_text(source["url"])}">Public source</a>'
        source_json = json.dumps(source, indent=2, ensure_ascii=False, allow_nan=False)
        body += f"<pre>{_text(source_json)}</pre></details>"
    body += (
        "<h2>Input echo</h2><details><summary>Complete cited input snapshot</summary>"
    )
    input_json = json.dumps(facts, indent=2, ensure_ascii=False, allow_nan=False)
    body += f"<pre>{_text(input_json)}</pre></details>"
    body += (
        '<p>Machine-readable files: <a href="metrics.json">metrics</a>, '
        '<a href="lifecycle.json">lifecycle</a>, '
    )
    body += (
        '<a href="economics_readiness.json">readiness</a>, '
        '<a href="provenance.json">provenance</a>.</p>'
    )
    return body


def write_package(
    package: dict, out: Path, root: Path, *, link_base: Path | None = None
) -> list[Path]:
    """Write and read back the complete output set; repeated builds are identical."""
    payloads = {
        "index.html": _page(
            package["title"],
            package["metrics"]["criterion"],
            _transaction_body(package),
            package["revision_history"],
        ),
        "lifecycle.html": _page(
            package["lifecycle"]["title"],
            "Lifecycle coverage is partial; source gaps remain NOT_EVALUATED.",
            _lifecycle_body(package, link_base if link_base is not None else out, root),
            package["revision_history"],
        ),
        **{
            f"{key}.json": json.dumps(
                package[key], indent=2, ensure_ascii=False, allow_nan=False
            )
            + "\n"
            for key in ("metrics", "lifecycle", "economics_readiness", "provenance")
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    outputs = []
    for name, text in payloads.items():
        path = out / name
        path.write_text(text, encoding="utf-8", newline="\n")
        if path.read_text(encoding="utf-8") != text:
            raise OSError("Generated artifact readback mismatch")
        outputs.append(path)
    return outputs
