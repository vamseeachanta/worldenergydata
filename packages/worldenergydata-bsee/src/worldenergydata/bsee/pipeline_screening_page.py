"""Self-contained screening QA report rendering."""

import html
import json

_CLASSES = ("PUBLIC", "DERIVED", "DEFAULT", "UNKNOWN")


def _table(headers, rows, caption):
    headings = "".join(f"<th>{html.escape(str(value))}</th>" for value in headers)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(value))}</td>" for value in row)
        + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table><p>{html.escape(caption)}</p>"


def _revision_table(revision):
    return _table(
        ("Revision", "Date", "What changed", "Why"),
        [
            [row[key] for key in ("revision", "date", "changed", "why")]
            for row in revision["history"]
        ],
        "Table 1. Revision history.",
    )


def _class_table(counts):
    return _table(
        ("Source class", "Cells (count)"),
        counts["source_classes"].items(),
        "Table 2. Data cells by source class; source columns are excluded.",
    )


def _field_table(counts):
    return _table(
        (
            "Field",
            "Public (cells)",
            "Derived (cells)",
            "Default (cells)",
            "Unknown (cells)",
        ),
        [
            [key, *(values[k] for k in _CLASSES)]
            for key, values in counts["by_field"].items()
        ],
        "Table 3. Provenance and unknown values by field. Unknown is a null, distinct from zero.",
    )


def _qa_page(counts, revision):
    return (
        '<!doctype html>\n<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        "<title>Pipeline screening database QA</title><style>body{font:16px system-ui;margin:2rem;max-width:90rem;color:#17212b}"
        "table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:.4rem;text-align:left}h2{margin-top:2rem}</style>"
        f'<body data-revision="{html.escape(revision["revision"])}"><h1>Pipeline screening database QA</h1>'
        f'<h2>Summary</h2><p>{counts["rows"]} case rows represent {counts["segments"]} screening-selected segments. '
        "This is a screening input inventory. It does not establish installed properties or stability acceptance.</p>"
        "<h2>Revision history</h2>"
        + _revision_table(revision)
        + "<h2>Source counts</h2>"
        + _class_table(counts)
        + _field_table(counts)
        + "<h2>Diagnostics</h2><pre>"
        + html.escape(
            json.dumps(
                {
                    key: counts[key]
                    for key in (
                        "selection",
                        "rejected_routes",
                        "length_outliers",
                        "hoop_yield_wall_at_assumed_smys",
                    )
                },
                indent=2,
            )
        )
        + "</pre>"
        + "<h2>Limits</h2><ul><li>Only ACT, OUT, PABN and PREM are selected by explicit policy I-0248. Every other status is excluded and counted. Selection does not establish present operation. Identical permit joins collapse; conflicting engineering values reject.</li>"
        "<li>Geometry uses published coordinates and spherical distances; no datum transformation is performed.</li><li>The cited bulk files have no minimum-depth or burial-design column; those fields are removed.</li>"
        "<li>Nominal size can be an OD proxy. The separate hoop-yield value is not installed wall; it bounds installed wall only where installed SMYS does not exceed assumed SMYS. It includes no design factor, allowance, tolerance or collapse check.</li>"
        "<li>The STD lookup preference is unused in this public build. A supplied dimension requires rights, edition and source qualification.</li>"
        "<li>Hs estimates require at least 10 complete maxima, T at most 4n and a 95% interval. Complete years require 80% annual hours and, in the Atlantic, 80% June-November hours. No marginal period extremes are exported. Four retained years cannot qualify return levels.</li>"
        "<li>Nearest sediment texture does not establish route geotechnical properties. Matches require a retained wave-reporting station or sediment sample within 50 km; friction is a labelled assumption. Station depth remains unknown without explicit depth evidence.</li>"
        "<li>Unknown coating, concrete and contents properties require an evidenced basis before use in stability calculations.</li>"
        "<li>Current is unknown. Wave direction is coming-from, clockwise from north, bearing +90 degrees: the right-hand side when following increasing route sequence. It is an assumption.</li></ul></body></html>\n"
    ).encode()
