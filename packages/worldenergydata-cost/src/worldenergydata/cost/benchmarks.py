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
from collections import Counter, defaultdict
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
    if _text(row, "MATCH_EXCLUSION"):
        raise ValueError(_text(row, "MATCH_EXCLUSION"))
    value = _positive(row, "CAPEX_USD_MM_2026")
    _positive(row, "ESCALATION_FACTOR")
    for column in (
        "INDEX_USED",
        "INDEX_BASE_YEAR",
        "SOURCE_TITLE",
        "SOURCE_URL",
        "CAPEX_BASIS",
    ):
        if not _text(row, column):
            raise ValueError(f"missing {column}")
    # Declared source qualifications are bounds, not observed point costs.
    basis = _text(row, "CAPEX_BASIS")
    if re.match(
        r"^(?:FLOOR|LOWER[- ]BOUND|UPPER[- ]BOUND|IN EXCESS OF|AT LEAST)(?:\s|:|$)",
        basis,
        re.IGNORECASE,
    ) or re.search(r"\b(?:FLOOR|LOWER[- ]BOUND|UPPER[- ]BOUND)\b", basis):
        raise ValueError("CAPEX_BASIS declares a bound, not a point cost")
    if _text(row, "MATCH_METHOD").lower() == "unmatched":
        if _text(row, "CATALOG_FIELD_IDS") or not _text(row, "MATCH_REASON"):
            raise ValueError("unmatched crosswalk requires a reason and no field ID")
    else:
        for column in (
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


def _summary(members):
    p10, p50, p90 = percentile_summary([m["value"] for m in members])
    return {
        "n": len(members),
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "indicative_only": len(members) < 5,
        "comparables": ";".join(sorted(m["project_id"] for m in members)),
        "cost_basis": "USD_2026",
    }


def build_benchmarks(projects):
    """Group independent projects; retain excluded metrics with explicit reasons.

    Rows use the sanctioned-project column names plus PROJECT_ID, field-match
    lineage and disclosed TREE_QUANTITY lineage supplied by ``load_projects``.
    Project IDs are unique, so multiple citations cannot increase group counts.
    """
    projects = list(projects)
    identity_counts = Counter(_text(p, "PROJECT_ID") for p in projects)
    groups, depth_groups = defaultdict(list), defaultdict(list)
    observations, exclusions = [], []
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
        locator_id = project_id.startswith("PROJECT:") and bool(
            project_id.removeprefix("PROJECT:").strip()
        )
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", project_id)
            and not locator_id
        ) or any(c in project_id for c in ";\r\n\t"):
            raise ValueError(
                "Missing or invalid PROJECT_ID in project identity registry"
            )
        if identity_counts[project_id] > 1:
            exclusions.append(
                {
                    "project_id": project_id,
                    "metric": "all",
                    "reason": f"ambiguous duplicate project rows (n={identity_counts[project_id]}); no cost selected",
                    "capex_usd_mm_2026": _text(project, "CAPEX_USD_MM_2026"),
                    "source_url": _text(project, "SOURCE_URL"),
                }
            )
            continue
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
            depth_groups[(metric, group[0])].append(observation)
    rows = []
    for (metric, *group), members in sorted(groups.items()):
        rows.append(
            {
                "metric": metric,
                "unit": METRICS[metric][2],
                **dict(zip(GROUP_COLUMNS, group)),
                **_summary(members),
            }
        )
    return {
        "rows": rows,
        "marginal_rows": [
            {
                "metric": metric,
                "unit": METRICS[metric][2],
                "group_by": "water_depth_band",
                "category": band,
                **_summary(members),
            }
            for (metric, band), members in sorted(depth_groups.items())
        ],
        "observations": sorted(
            observations, key=lambda r: (r["metric"], r["project_id"])
        ),
        "exclusions": sorted(exclusions, key=lambda r: (r["project_id"], r["metric"])),
    }


def _read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        # Header case is tolerated at the crosswalk boundary; values are unchanged.
        fields = tuple(
            (f or "").lstrip("\ufeff").strip().upper()
            for f in (reader.fieldnames or ())
        )
        reader.fieldnames = fields
        return fields, [
            {str(k).strip().upper(): v for k, v in r.items()} for r in reader
        ]


def load_projects(data_dir, projects_path=None):
    """Read upstream files without substituting a cost basis or inventing links."""
    data_dir = Path(data_dir)
    path = (
        Path(projects_path) if projects_path is not None else data_dir / INPUT_FILES[0]
    )
    missing = [name for name in INPUT_FILES[1:] if not (data_dir / name).is_file()]
    if not path.is_file():
        missing.append("selected projects table")
    fields, rows = _read_csv(path) if path.is_file() else ((), [])
    missing += [column for column in ESCALATION_COLUMNS if column not in fields]
    if missing:
        raise ValueError("Missing input: " + ", ".join(missing))
    source = data_dir / INPUT_FILES[0]
    if (
        projects_path is not None
        and source.is_file()
        and path.resolve() != source.resolve()
    ):
        digest = sha256(source.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        rebuild = (
            "rebuild with python -m worldenergydata.cost.escalation "
            "--output <derived-table>"
        )
        for row in rows:
            if _text(row, "INPUT_DIGEST_BASIS") != "sha256_utf8_lf" or not _text(
                row, "PROJECTS_SHA256"
            ):
                raise ValueError(
                    "Derived project provenance requires PROJECTS_SHA256 and "
                    f"INPUT_DIGEST_BASIS=sha256_utf8_lf; {rebuild}"
                )
            if _text(row, "PROJECTS_SHA256") != digest:
                raise ValueError(
                    "Derived projects source digest does not match the UTF-8/LF "
                    f"SHA-256 of sanctioned_projects.csv; {rebuild}"
                )
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
    matches, named_matches = {}, {}
    for match in _read_csv(data_dir / "project_field_crosswalk.csv")[1]:
        locator = _text(match, "PROJECT_ID")
        name = (
            locator.removeprefix("PROJECT:") if locator.startswith("PROJECT:") else ""
        )
        if name and _text(match, "PROJECT") not in {"", name}:
            raise ValueError("Crosswalk project and locator disagree")
        cost_id = _text(match, "COST_PROJECT_ID")
        if not name:
            if cost_id and locator and cost_id != locator:
                raise ValueError("Crosswalk identity keys disagree")
            cost_id = cost_id or locator
        if not name and not cost_id:
            raise ValueError("Crosswalk requires an identity or project locator")
        if (cost_id and cost_id in matches) or (name and name in named_matches):
            raise ValueError("Ambiguous crosswalk identity or locator")
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
        metadata = {
            "CATALOG_FIELD_IDS": field_ids,
            "MATCH_METHOD": _text(match, "MATCH_METHOD"),
            "MATCH_CONFIDENCE": _text(match, "CONFIDENCE"),
            "MATCH_EVIDENCE": _text(match, "EVIDENCE"),
            "MATCH_REASON": _text(match, "REASON"),
            "CROSSWALK_COST_ID": cost_id,
            "CROSSWALK_LOCATOR": locator if name else "",
        }
        if cost_id:
            matches[cost_id] = metadata
        if name:
            named_matches[name] = metadata
    for metadata in named_matches.values():
        locator = metadata["CROSSWALK_LOCATOR"]
        if locator in matches and matches[locator] is not metadata:
            raise ValueError("Ambiguous crosswalk identity and locator collision")
    requirements = defaultdict(list)
    for requirement in _read_csv(data_dir / "project_asset_requirements.csv")[1]:
        if (
            _text(requirement, "ASSET_TYPE").lower() in {"subsea tree", "wet tree"}
            and _text(requirement, "QUANTITY_UNIT").lower() == "tree"
            and _text(requirement, "EVIDENCE_DERIVATION").lower() == "disclosed"
        ):
            requirements[_text(requirement, "PROJECT_ID")].append(requirement)
    result = []
    for raw, _ in zip(rows, sanctioned, strict=True):
        name = _text(raw, "PROJECT")
        # Crosswalk and quantity evidence belong to their own input tables.
        raw = {
            k: v
            for k, v in raw.items()
            if not k.startswith(("MATCH_", "TREE_", "CATALOG_FIELD", "CROSSWALK_"))
            and k not in {"FIELD_ID", "FIELD_IDS"}
        }
        supplied_id = _text(raw, "PROJECT_ID")
        registered_id = identities.get(name, "")
        if supplied_id and registered_id and supplied_id != registered_id:
            raise ValueError("Project row and identity registry disagree on PROJECT_ID")
        project_id = supplied_id or registered_id
        by_id = matches.get(project_id)
        by_name = named_matches.get(name)
        if by_id is not None and by_name is not None and by_id is not by_name:
            raise ValueError("Crosswalk identity and project locator disagree")
        match = by_name if by_name is not None else by_id
        match_exclusion = ""
        if match is not None:
            cost_id = match["CROSSWALK_COST_ID"]
            if project_id and cost_id and project_id != cost_id:
                raise ValueError("Crosswalk identity and project identity disagree")
            # A locator-bearing row must agree with the source name even on an ID join.
            locator = match["CROSSWALK_LOCATOR"]
            if locator and locator != f"PROJECT:{name}":
                match_exclusion = "crosswalk locator does not match project name"
                match = None
            else:
                project_id = project_id or cost_id or locator
        row = {
            **raw,
            "PROJECT_ID": project_id,
            **(match or {}),
            "MATCH_EXCLUSION": match_exclusion,
        }
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
    marginal_columns = (
        "metric",
        "unit",
        "group_by",
        "category",
        "n",
        "p10",
        "p50",
        "p90",
        "indicative_only",
        "comparables",
        "cost_basis",
    )
    marginals = _table(
        marginal_columns,
        [
            [
                _figure(r[c]) if c in {"p10", "p50", "p90"} else r[c]
                for c in marginal_columns
            ]
            for r in facts["marginal_rows"]
        ],
        "Separate depth-only view; each project is counted once per metric in this view. "
        "Indicative only below five projects; these rows are not included in the CSV.",
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
                p.get("MATCH_REASON", ""),
                p.get("CAPEX_USD_MM_2026", ""),
                observation["quantity_column"],
                p.get(observation["quantity_column"], ""),
                _figure(observation["value"]),
                observation["unit"],
                p.get("INDEX_USED", ""),
                p.get("INDEX_BASE_YEAR", ""),
                p.get("ESCALATION_FACTOR", ""),
                p.get("ESCALATION_NOTE", ""),
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
            "Crosswalk reason",
            "CAPEX (USD MM 2026)",
            "Quantity column",
            "Quantity (source units)",
            "Intensity",
            "Unit",
            "Index",
            "Index base year",
            "Escalation factor",
            "Escalation note",
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
        [
            "Project ID",
            "Project name if unregistered",
            "Metric",
            "Exclusion reason",
            "Ambiguous supplied CAPEX (USD MM 2026)",
            "Source URL",
        ],
        [
            [
                e["project_id"],
                e.get("project_name", ""),
                e["metric"],
                e["reason"],
                e.get("capex_usd_mm_2026", ""),
                e.get("source_url", ""),
            ]
            for e in facts["exclusions"]
        ],
        "Missing quantities exclude only the affected metric; "
        "missing cost or invalid lineage excludes every metric; "
        "explicit unmatched crosswalk rows retain their reason.",
    )
    exclusion_counts = _table(
        ["Exclusion reason", "Observation exclusions"],
        sorted(Counter(e["reason"] for e in facts["exclusions"]).items()),
        "Counts include project-wide exclusions and exclusions of individual metrics.",
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
                "2026-11-12",
                "Project intensities and source lineage expose benchmark coverage.",
            ],
            [
                "Interface update",
                "2026-11-12",
                "Exact crosswalk joins, explicit unmatched reasons, depth marginals "
                "and bound-cost exclusions expose usable coverage.",
            ],
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
Each reported percentile traces to the project IDs and cited inputs below.
Report date: {escape(report_date)}.</p>
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
<p>The separate marginal table groups by depth alone; its rows are excluded from
the CSV. Explicit unmatched field links retain the upstream reason and do not
exclude an otherwise sourced project cost. CAPEX bases starting with FLOOR,
LOWER-BOUND, LOWER BOUND, UPPER-BOUND, UPPER BOUND, IN EXCESS OF or AT LEAST
(followed by whitespace, a colon or end of text, case-insensitive) declare bounds.
Uppercase whole tokens FLOOR, LOWER-BOUND, LOWER BOUND, UPPER-BOUND or UPPER BOUND
anywhere in the basis also declare bounds. Both lower and upper bounds are excluded
from point percentiles. Other free-text qualifications require source review;
this declared vocabulary does not establish that every bound is identified.</p>
<p>Every row belonging to a repeated project ID is excluded from both views;
the alternative costs are shown below and no cost is selected or averaged.</p>
<p>These ratios divide total project CAPEX by scope quantities;
they are not component purchase prices.
Escalation and field matches are supplied upstream and are not independently verified here.
Exact groups do not establish accounting equivalence: gross/net shares, phase boundaries,
leased facilities, integrated onshore scope, disclosure dates and resource definitions may differ.
Their bases are retained per comparable. No prediction accuracy, population representativeness
or statistically sufficient sample is established by n ≥ 5.</p>
<h2>Groups</h2>{groups}<h2>Marginal groups</h2>{marginals}
<h2>Comparables and sources</h2>{detail}
<ul>{_source_links({"operator_rows": sources})}</ul>
<h2>Excluded observations</h2>{excluded}{exclusion_counts}<h2>Input lineage</h2>
<p>Projects table: {escape(facts['project_table'])}</p>{digests}
<p>Facts SHA-256: {escape(facts_digest(facts))}</p></body></html>"""


def write_benchmarks(data_dir, output_dir, report_date, projects_path=None):
    """Validate all input and rendering before creating either report file."""
    date.fromisoformat(report_date)
    input_paths = {
        name: Path(data_dir) / name
        for name in (INPUT_FILES if projects_path is None else INPUT_FILES[1:])
    }
    if projects_path is not None:
        input_paths["projects_table"] = Path(projects_path)
        source = Path(data_dir) / INPUT_FILES[0]
        if source.is_file() and source.resolve() != Path(projects_path).resolve():
            input_paths["nominal_projects_table"] = source
    for name, path in input_paths.items():
        if not path.is_file():
            raise ValueError(f"Missing input: {name}")
    before = {
        name: sha256(path.read_bytes()).hexdigest()
        for name, path in input_paths.items()
    }
    projects = load_projects(data_dir, projects_path)
    facts = build_benchmarks(projects)
    after = {
        name: sha256(path.read_bytes()).hexdigest()
        for name, path in input_paths.items()
    }
    if before != after:
        raise ValueError("Input bytes changed during benchmark generation")
    if not facts["rows"]:
        counts = Counter(e["reason"] for e in facts["exclusions"])
        reasons = "; ".join(
            f"{reason}: {count}" for reason, count in sorted(counts.items())
        )
        raise ValueError(
            f"No benchmark groups; {len(projects)} projects; "
            f"{len(facts['exclusions'])} exclusions. {reasons}"
        )
    facts["input_digests"] = before
    selected = (
        Path(projects_path)
        if projects_path is not None
        else Path(data_dir) / INPUT_FILES[0]
    )
    facts["project_table"] = selected.name
    html = _html(facts, report_date)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": output_dir / "unit_cost_benchmarks.csv",
        "html": output_dir / "unit_cost_benchmarks.html",
    }
    with paths["csv"].open("w", encoding="utf-8", newline="\n") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in facts["rows"]:
            writer.writerow(
                {
                    k: (str(v).lower() if isinstance(v, bool) else v)
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
    command.add_argument(
        "--projects",
        type=Path,
        help="Use this complete escalated project table instead of sanctioned_projects.csv",
    )
    command.add_argument("--report-date", default=date.today().isoformat())
    args = parser.parse_args(argv)
    try:
        write_benchmarks(
            args.data_dir, args.output_dir, args.report_date, args.projects
        )
    except OSError:
        print(
            "Cannot generate unit-cost benchmarks: input/output file access failed",
            file=sys.stderr,
        )
        return 2
    except (ValueError, KeyError, csv.Error) as error:
        print(f"Cannot generate unit-cost benchmarks: {error}", file=sys.stderr)
        return 2
    print("Wrote unit_cost_benchmarks.csv and unit_cost_benchmarks.html (USD_2026)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
