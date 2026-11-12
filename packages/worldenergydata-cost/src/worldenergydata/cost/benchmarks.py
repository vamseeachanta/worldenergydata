"""Source-traceable project CAPEX intensities; escalation is an upstream input.

Run ``python -m worldenergydata.cost.benchmarks benchmarks --help``.
No nominal fallback, field matching, FX conversion or component allocation is
performed. See docs/modules/cost/UNIT_COST_BENCHMARKS.md for the input contract.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import date
from hashlib import sha256
from html import escape
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit

from worldenergydata.cost.data_collection.calibration_schema import WaterDepthBand
from worldenergydata.cost.reporting.benchmark_report import (
    _source_links,
    _table,
    facts_digest,
    percentile_summary,
)
from worldenergydata.cost.timeseries.dataset import read_sanctioned_csv

CSV_COLUMNS = (
    "metric",
    "unit",
    "water_depth_band",
    "region",
    "development_type",
    "host_type",
    "n",
    "p10",
    "p50",
    "p90",
    "indicative_only",
    "comparables",
    "cost_basis",
)
GROUP_COLUMNS = ("water_depth_band", "region", "development_type", "host_type")
# Multipliers convert the supplied denominator to the unit in the metric.
METRICS = {
    "capex_per_well": ("WELL_COUNT", 1.0, "USD_MM_2026/well"),
    "capex_per_tree": ("TREE_QUANTITY", 1.0, "USD_MM_2026/tree"),
    "capex_per_surf_km": ("SURF_KM", 1.0, "USD_MM_2026/km"),
    "capex_per_kboed": ("PEAK_PRODUCTION_BOEPD", 0.001, "USD_MM_2026/kboe/d"),
    # USD MM / MMboe is USD/boe: the two million multipliers cancel.
    "capex_per_boe": ("RECOVERABLE_RESOURCE_MMBOE", 1.0, "USD_2026/boe"),
}
INPUT_FILES = (
    "sanctioned_projects.csv",
    "cost_project_identity.csv",
    "project_field_crosswalk.csv",
    "project_asset_requirements.csv",
)
ESCALATION_COLUMNS = (
    "CAPEX_USD_MM_2026",
    "INDEX_USED",
    "INDEX_BASE_YEAR",
    "ESCALATION_FACTOR",
)


def _text(row, column):
    return str(row.get(column, "") or "").strip()


def _positive(row, column):
    try:
        value = float(_text(row, column))
    except ValueError:
        raise ValueError(f"missing or invalid {column}") from None
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{column} must be finite and positive")
    return value


def _public_url(value):
    parsed = urlsplit(value)
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and not parsed.username
    )


def _depth_band(raw):
    if not raw:
        return "unknown"
    try:
        depth = float(raw)
    except ValueError:
        return "unknown"
    if not isfinite(depth) or depth < 0:
        return "unknown"
    for ceiling, band in (
        (300, WaterDepthBand.SHALLOW),
        (1000, WaterDepthBand.MID),
        (2000, WaterDepthBand.DEEP),
    ):
        if depth <= ceiling:
            return band.value
    return WaterDepthBand.ULTRA_DEEP.value


def _project_cost(row):
    value = _positive(row, "CAPEX_USD_MM_2026")
    _positive(row, "ESCALATION_FACTOR")
    for column in (
        "INDEX_USED",
        "INDEX_BASE_YEAR",
        "SOURCE_TITLE",
        "SOURCE_URL",
        "CAPEX_BASIS",
        "CATALOG_FIELD_IDS",
        "MATCH_METHOD",
        "MATCH_CONFIDENCE",
        "MATCH_EVIDENCE",
    ):
        if not _text(row, column):
            raise ValueError(f"missing {column}")
    if not _public_url(_text(row, "SOURCE_URL")):
        raise ValueError("SOURCE_URL must be a public HTTP(S) source reference")
    try:
        base_year = int(_text(row, "INDEX_BASE_YEAR"))
    except ValueError:
        raise ValueError("invalid INDEX_BASE_YEAR") from None
    if not 0 < base_year <= 2026:
        raise ValueError("INDEX_BASE_YEAR must be a positive year no later than 2026")
    return value


def build_benchmarks(projects):
    """Group independent projects; retain excluded metrics with explicit reasons.

    Rows use the sanctioned-project column names plus PROJECT_ID, field-match
    lineage and disclosed TREE_QUANTITY lineage supplied by ``load_projects``.
    Project IDs are unique, so multiple citations cannot increase group counts.
    """
    groups = defaultdict(list)
    observations, exclusions, seen = [], [], set()
    for project in projects:
        project_id = _text(project, "PROJECT_ID")
        if not project_id:
            exclusions.append(
                {
                    "project_id": "unknown",
                    "project_name": _text(project, "PROJECT"),
                    "metric": "all",
                    "reason": "missing PROJECT_ID in project row or identity registry",
                }
            )
            continue
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", project_id):
            raise ValueError(
                "Missing or invalid PROJECT_ID in project identity registry"
            )
        if project_id in seen:
            raise ValueError(f"Duplicate project: {project_id}")
        seen.add(project_id)
        try:
            capex = _project_cost(project)
        except ValueError as error:
            exclusions.append(
                {"project_id": project_id, "metric": "all", "reason": str(error)}
            )
            continue
        group = (
            _depth_band(_text(project, "WATER_DEPTH_M")),
            *(
                _text(project, column.upper()) or "unknown"
                for column in GROUP_COLUMNS[1:]
            ),
        )
        for metric, (column, multiplier, unit) in METRICS.items():
            try:
                quantity = _positive(project, column)
                if column == "TREE_QUANTITY":
                    for required in ("TREE_SOURCE_URL", "TREE_SOURCE_LOCATOR"):
                        if not _text(project, required):
                            raise ValueError(f"missing {required}")
                    if not _public_url(_text(project, "TREE_SOURCE_URL")):
                        raise ValueError("invalid TREE_SOURCE_URL")
                intensity = capex / (quantity * multiplier)
                if not isfinite(intensity) or intensity <= 0:
                    raise ValueError("derived intensity must be finite and positive")
            except (ValueError, ZeroDivisionError) as error:
                reason = (
                    _text(project, "TREE_EXCLUSION")
                    if column == "TREE_QUANTITY"
                    else ""
                )
                exclusions.append(
                    {
                        "project_id": project_id,
                        "metric": metric,
                        "reason": reason or str(error),
                    }
                )
                continue
            observation = {
                "project_id": project_id,
                "metric": metric,
                "unit": unit,
                "value": intensity,
                "capex_usd_mm_2026": capex,
                "quantity": quantity,
                "quantity_column": column,
                "project": dict(project),
            }
            observations.append(observation)
            groups[(metric, *group)].append(observation)
    rows = []
    for (metric, *group), members in sorted(groups.items()):
        p10, p50, p90 = percentile_summary([m["value"] for m in members])
        rows.append(
            {
                "metric": metric,
                "unit": METRICS[metric][2],
                **dict(zip(GROUP_COLUMNS, group)),
                "n": len(members),
                "p10": p10,
                "p50": p50,
                "p90": p90,
                "indicative_only": len(members) < 5,
                "comparables": ";".join(sorted(m["project_id"] for m in members)),
                "cost_basis": "USD_2026",
            }
        )
    return {
        "rows": rows,
        "observations": sorted(
            observations, key=lambda r: (r["metric"], r["project_id"])
        ),
        "exclusions": sorted(exclusions, key=lambda r: (r["project_id"], r["metric"])),
    }


def _read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        # Header case is tolerated at the crosswalk boundary; values are unchanged.
        fields = tuple((f or "").strip().upper() for f in (reader.fieldnames or ()))
        return fields, [
            {str(k).strip().upper(): v for k, v in r.items()} for r in reader
        ]


def load_projects(data_dir):
    """Read upstream files without substituting a cost basis or inventing links."""
    data_dir = Path(data_dir)
    missing = [name for name in INPUT_FILES if not (data_dir / name).is_file()]
    path = data_dir / "sanctioned_projects.csv"
    fields, rows = _read_csv(path) if path.is_file() else ((), [])
    missing += [column for column in ESCALATION_COLUMNS if column not in fields]
    if missing:
        raise ValueError("Missing input: " + ", ".join(missing))
    # Reuse the existing sanctioned-project reader for its schema and CAPEX-basis check.
    sanctioned = read_sanctioned_csv(path)
    identities = {}
    for identity in _read_csv(data_dir / "cost_project_identity.csv")[1]:
        if (
            _text(identity, "ENTITY_KIND") != "project"
            or _text(identity, "ACTIVE").lower() != "true"
            or _text(identity, "SOURCE_TABLE") != "sanctioned_projects.csv"
        ):
            continue
        locator = _text(identity, "SOURCE_RECORD_LOCATOR")
        if not locator.startswith("PROJECT="):
            continue
        name = locator.removeprefix("PROJECT=")
        if name in identities:
            raise ValueError("Duplicate sanctioned-project identity locator")
        identities[name] = _text(identity, "OPAQUE_ID")
    matches = {}
    for match in _read_csv(data_dir / "project_field_crosswalk.csv")[1]:
        project_id = _text(match, "PROJECT_ID")
        if project_id in matches:
            raise ValueError(f"Ambiguous crosswalk rows for {project_id}")
        # Explicit aliases cover singular/multiple catalog-field IDs, not name matching.
        field_ids = next(
            (
                _text(match, key)
                for key in (
                    "CATALOG_FIELD_IDS",
                    "CATALOG_FIELD_ID",
                    "FIELD_IDS",
                    "FIELD_ID",
                )
                if _text(match, key)
            ),
            "",
        )
        matches[project_id] = {
            "CATALOG_FIELD_IDS": field_ids,
            "MATCH_METHOD": _text(match, "MATCH_METHOD"),
            "MATCH_CONFIDENCE": _text(match, "CONFIDENCE"),
            "MATCH_EVIDENCE": _text(match, "EVIDENCE"),
        }
    requirements = defaultdict(list)
    for requirement in _read_csv(data_dir / "project_asset_requirements.csv")[1]:
        if (
            _text(requirement, "ASSET_TYPE").lower() in {"subsea tree", "wet tree"}
            and _text(requirement, "QUANTITY_UNIT").lower() == "tree"
            and _text(requirement, "EVIDENCE_DERIVATION").lower() == "disclosed"
        ):
            requirements[_text(requirement, "PROJECT_ID")].append(requirement)
    result = []
    for raw, project in zip(rows, sanctioned):
        supplied_id = _text(raw, "PROJECT_ID")
        registered_id = identities.get(project.project, "")
        if supplied_id and registered_id and supplied_id != registered_id:
            raise ValueError("Project row and identity registry disagree on PROJECT_ID")
        project_id = supplied_id or registered_id
        row = {**raw, "PROJECT_ID": project_id, **matches.get(project_id, {})}
        trees = requirements[project_id]
        if len(trees) == 1:
            row.update(
                TREE_QUANTITY=_text(trees[0], "QUANTITY"),
                TREE_SOURCE_URL=_text(trees[0], "SOURCE_URL"),
                TREE_SOURCE_LOCATOR=_text(trees[0], "SOURCE_LOCATOR"),
            )
        else:
            row["TREE_EXCLUSION"] = (
                "ambiguous" if trees else "missing"
            ) + " disclosed subsea TREE_QUANTITY"
        result.append(row)
    return result


def _figure(value):
    """One decimal place; scientific notation keeps small positives above zero."""
    return f"{value:.1e}" if 0 < value < 0.05 else f"{value:.1f}"


def _html(facts, report_date):
    groups = _table(
        CSV_COLUMNS,
        [
            [_figure(r[c]) if c in {"p10", "p50", "p90"} else r[c] for c in CSV_COLUMNS]
            for r in facts["rows"]
        ],
        "Group percentiles; indicative_only is true below five independent projects.",
    )
    comparables = []
    sources = []
    for observation in facts["observations"]:
        p = observation["project"]
        comparables.append(
            [
                observation["metric"],
                observation["project_id"],
                p.get("PROJECT", ""),
                p.get("CATALOG_FIELD_IDS", ""),
                p.get("MATCH_METHOD", ""),
                p.get("MATCH_CONFIDENCE", ""),
                p.get("MATCH_EVIDENCE", ""),
                _figure(observation["capex_usd_mm_2026"]),
                observation["quantity_column"],
                # Small quantities retain significant figures to avoid displaying a false zero.
                f"{observation['quantity']:.6g}",
                _figure(observation["value"]),
                observation["unit"],
                p.get("INDEX_USED", ""),
                p.get("INDEX_BASE_YEAR", ""),
                p.get("ESCALATION_FACTOR", ""),
                p.get("CAPEX_BASIS", ""),
                p.get("SCOPE_IS_OFFSHORE_ONLY", "unknown"),
                p.get("SOURCE_TITLE", ""),
                p.get("SOURCE_URL", ""),
                p.get("PAGE_REFERENCE", ""),
                p.get("ACCESSED_DATE", ""),
                (
                    p.get("TREE_SOURCE_URL", "")
                    if observation["metric"] == "capex_per_tree"
                    else ""
                ),
                (
                    p.get("TREE_SOURCE_LOCATOR", "")
                    if observation["metric"] == "capex_per_tree"
                    else ""
                ),
            ]
        )
        sources.append(
            {
                "provenance": {
                    "source_url": p.get("SOURCE_URL", ""),
                    "source": p.get("SOURCE_TITLE", ""),
                }
            }
        )
        if observation["metric"] == "capex_per_tree":
            sources.append(
                {
                    "provenance": {
                        "source_url": p.get("TREE_SOURCE_URL", ""),
                        "source": p.get("TREE_SOURCE_LOCATOR", ""),
                    }
                }
            )
    detail = _table(
        [
            "Metric",
            "Project ID",
            "Project",
            "Catalog field IDs",
            "Match method",
            "Match confidence",
            "Match evidence",
            "CAPEX (USD MM 2026)",
            "Quantity column",
            "Quantity (source units)",
            "Intensity",
            "Unit",
            "Index",
            "Index base year",
            "Escalation factor",
            "CAPEX basis",
            "Offshore only",
            "Source title",
            "Source URL",
            "Source locator",
            "Accessed date",
            "Tree quantity source URL",
            "Tree quantity locator",
        ],
        comparables,
        "Every member behind each group figure; quantities follow the columns in the method.",
    )
    excluded = _table(
        ["Project ID", "Project name if unregistered", "Metric", "Exclusion reason"],
        [
            [e["project_id"], e.get("project_name", ""), e["metric"], e["reason"]]
            for e in facts["exclusions"]
        ],
        "Missing quantities exclude only the affected metric; "
        "missing cost or lineage excludes every metric.",
    )
    digests = _table(
        ["Input", "SHA-256"],
        sorted(facts["input_digests"].items()),
        "Raw input bytes at generation; this does not establish source freshness.",
    )
    history = _table(
        ["Revision", "Date", "Change and reason"],
        [
            [
                "Initial",
                report_date,
                "Project intensities and source lineage expose benchmark coverage.",
            ]
        ],
        "Report edition history.",
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Project unit-cost benchmarking analysis — USD_2026</title>
<style>body{{font:16px system-ui,sans-serif;max-width:100rem;margin:2rem auto;
padding:0 1rem;color:#163448}}
.table-wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%}}
th,td{{padding:.6rem;text-align:left;border-bottom:1px solid #ccd9df}}
th{{background:#eaf2f7}}.caption{{font-size:.9rem}}a{{color:#145d83}}</style></head><body>
<h1>Project unit-cost benchmarking analysis — USD_2026</h1>
<p>Summary: descriptive project CAPEX intensities in constant 2026 USD.
Groups with n &lt; 5 are indicative only.
Each reported percentile traces to the project IDs and cited inputs below.</p>
<h2>Revision history</h2>{history}
<h2>Method and limits</h2><p>Equal project weights;
P10/P50/P90 use linear interpolation over sorted observations:
h = (n - 1) p, interpolating the two surrounding ranks
(Python statistics.quantiles, method=inclusive).
A singleton has three equal percentiles. These are empirical cost percentiles,
not petroleum resource exceedance probabilities.</p>
<p>CAPEX_USD_MM_2026 / WELL_COUNT (wells), / TREE_QUANTITY (subsea trees), / SURF_KM (km),
/ (PEAK_PRODUCTION_BOEPD / 1000) (kboe/d), and / RECOVERABLE_RESOURCE_MMBOE (USD_2026/boe).
TREE_QUANTITY is project_asset_requirements.csv QUANTITY, with QUANTITY_UNIT=tree,
a disclosed subsea-tree row,
and its own source URL and locator. Project well counts are never used as tree counts.</p>
<p>The keys are water-depth band, region, development type and host type.
Depth bands are shallow (0–300 m),
mid (&gt;300–1000 m), deep (&gt;1000–2000 m), ultra_deep (&gt;2000 m); absent keys remain unknown.
No fuzzy aliases are applied. A project is counted once in each metric.</p>
<p>These ratios divide total project CAPEX by scope quantities;
they are not component purchase prices.
Escalation and field matches are supplied upstream and are not independently verified here.
Exact groups do not establish accounting equivalence: gross/net shares, phase boundaries,
leased facilities, integrated onshore scope, disclosure dates and resource definitions may differ.
Their bases are retained per comparable. No prediction accuracy, population representativeness
or statistically sufficient sample is established by n ≥ 5.</p>
<h2>Groups</h2>{groups}<h2>Comparables and sources</h2>{detail}
<ul>{_source_links({"operator_rows": sources})}</ul>
<h2>Excluded observations</h2>{excluded}<h2>Input lineage</h2>{digests}
<p>Facts SHA-256: {escape(facts_digest(facts))}</p></body></html>"""


def write_benchmarks(data_dir, output_dir, report_date):
    """Validate all input and rendering before creating either report file."""
    date.fromisoformat(report_date)
    projects = load_projects(data_dir)
    facts = build_benchmarks(projects)
    facts["input_digests"] = {
        name: sha256((Path(data_dir) / name).read_bytes()).hexdigest()
        for name in INPUT_FILES
    }
    html = _html(facts, report_date)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": output_dir / "unit_cost_benchmarks.csv",
        "html": output_dir / "unit_cost_benchmarks.html",
    }
    with paths["csv"].open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in facts["rows"]:
            writer.writerow(
                {
                    k: (
                        str(v).lower()
                        if isinstance(v, bool)
                        else _figure(v) if k in {"p10", "p50", "p90"} else v
                    )
                    for k, v in row.items()
                }
            )
    paths["html"].write_text(html, encoding="utf-8", newline="\n")
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser(
        "benchmarks", help="Build cited constant-2026-USD unit-cost groups"
    )
    command.add_argument(
        "--data-dir", type=Path, default=Path("data/modules/cost/curated")
    )
    command.add_argument("--output-dir", type=Path, default=Path("reports/cost"))
    command.add_argument("--report-date", default=date.today().isoformat())
    args = parser.parse_args(argv)
    try:
        write_benchmarks(args.data_dir, args.output_dir, args.report_date)
    except (ValueError, KeyError, OSError, csv.Error) as error:
        print(f"Cannot generate unit-cost benchmarks: {error}", file=sys.stderr)
        return 2
    print("Wrote unit_cost_benchmarks.csv and unit_cost_benchmarks.html (USD_2026)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
