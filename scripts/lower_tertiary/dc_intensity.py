"""Shared adapter for opt-in Days/10K listing and dataset previews.

The equation and reference units are specified in issue #1080 and
SPE-87117-MS (2004), public abstract paragraph 4. No basis is selected here.
Raw nullable cells are retained separately from legacy display day counts.
"""

from collections.abc import Iterable, Mapping
from html import escape

from worldenergydata.bsee.analysis.drilling_intensity import (
    Denominator,
    bore_intensity,
    intensity_rollups,
)

# SPE-87117-MS (2004), publisher-deposited public abstract, paragraph 4.
# The units define the 10000-ft scale; the band is not an acceptance limit.
REFERENCE = {
    "days_per_10k_reference_lower": 20,
    "days_per_10k_reference_upper": 23,
    "days_per_10k_reference_citation": "SPE-87117-MS (2004), abstract paragraph 4",
    "days_per_10k_reference_url": "https://api.crossref.org/works/10.2118/87117-MS",
    "days_per_10k_reference_qualification": (
        "Reference only; denominator and comparability not established"
    ),
}


def source_row(row: Mapping, *, basis: object, field: str, block: str) -> dict:
    def number(key: str) -> float | None:
        raw = (row.get(key) or "").strip()
        return float(raw) if raw else None

    return {
        "basis": basis,
        "field": field,
        "block": block,
        "drilling_days": number("DRILLING_DAYS"),
        "MAX_BH_TOTAL_MD": number("MAX_BH_TOTAL_MD"),
        "MAX_WELL_BORE_TVD": number("MAX_WELL_BORE_TVD"),
    }


def add_bore(bore: dict, raw: Mapping, *, field: str, denominator: Denominator) -> None:
    """Attach ratios before a display parser can turn missing days into zero."""
    row = source_row(raw, basis=bore.get("basis"), field=field, block=bore["lease_num"])
    bore["_intensity_input"] = row
    result = bore_intensity(row, denominator=denominator)
    # An absent source basis must not activate the legacy provenance schema.
    if "basis" not in bore:
        result.pop("basis")
    bore.update(result)


def rollup(bores: Iterable[Mapping], *, denominator: Denominator) -> dict:
    """Use the core matched-pair depth weighting, including its basis refusal."""
    rows = [b["_intensity_input"] for b in bores]
    results = intensity_rollups(rows, group_by="field", denominator=denominator)
    if len(results) != 1:
        raise ValueError("an intensity summary requires exactly one field")
    return {k: v for k, v in results[0].items() if k != "field"}


def markdown_preview(devs: Mapping[str, list[dict]]) -> str:
    """Render the additive preview; legacy day-count tables retain their cells."""
    bores = [b for members in devs.values() for b in members]
    if not bores or "_intensity_input" not in bores[0]:
        return ""
    denominator = bores[0]["days_per_10k_ft_denominator"]

    def cell(value: object) -> str:
        if isinstance(value, float):
            return f"{value:.1f}"
        return (
            escape("—" if value is None else str(value))
            .replace("|", "\\|")
            .replace("\r", "")
            .replace("\n", "<br>")
        )

    lines = [
        "## Normalized drilling intensity preview",
        "",
        (
            f"Days/10K ({denominator.upper()}) is the `days_per_10k_ft` alias. "
            "MD uses MAX_BH_TOTAL_MD; TVD uses MAX_WELL_BORE_TVD (feet). "
            "Drilling only; completion is excluded. Field ratios use matched-pair "
            "totals, with separate coverage for each depth. A missing or mixed "
            "basis refuses computation; labels do not certify publication readiness."
        ),
        "",
        (
            "Reference: 20–23 Days/10K, SPE-87117-MS (2004), public abstract "
            "paragraph 4 ([source](https://api.crossref.org/works/10.2118/87117-MS)). "
            "The reference denominator and comparability are not established; "
            "this band is not an acceptance limit."
        ),
        "",
        (
            f"| Record | Days/10K ({denominator.upper()}) | Days/10K (MD) | Days/10K (TVD) "
            "| Basis | Status (MD) | Status (TVD) "
            "| Included / excluded (MD) | Included / excluded (TVD) |"
        ),
        "|---|---:|---:|---:|---|---|---|---|---|",
    ]
    for field, members in devs.items():
        records = [(field, rollup(members, denominator=denominator))]
        records.extend((b["api12"], b) for b in members)
        for name, record in records:
            values = [name] + [
                record.get(key)
                for key in (
                    "days_per_10k_ft",
                    "days_per_10k_md",
                    "days_per_10k_tvd",
                    "basis",
                    "intensity_status_md",
                    "intensity_status_tvd",
                )
            ]
            for suffix in ("md", "tvd"):
                values.append(
                    f"{record[f'included_bores_{suffix}']} / "
                    f"{record[f'excluded_bores_{suffix}']}"
                )
            lines.append("| " + " | ".join(cell(v) for v in values) + " |")
    return "\n".join(lines) + "\n"
