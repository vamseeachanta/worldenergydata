# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas==3.1.1", "pydantic-settings==2.16.3", "pyyaml==6.0.4"]
# [tool.uv]
# exclude-newer = "2026-11-25T06:00:00Z"
# ///
"""Cross-check lease matches and write the detailed bounds report."""

import json
import re
import tempfile
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

import lease_analysis as analysis
from bore_basis import MEMBER
from lease_basis import LEASE_SCHEMA, read_leases
from source_inputs import BORE, EXAMPLE, REPOSITORY, TAPE, input_parser, verified_inputs

FIELDS = {
    "API_WELL_NUMBER": "api12",
    "REGION_CODE": "region",
    "WELL_TYPE_CODE": "type_code",
    "WELL_SPUD_DATE": "date_text",
    "BOTM_LEASE_NUMBER": "bottom",
    "SURF_LEASE_NUMBER": "surface",
}


def raw_tape_ids(tape_path):
    layout = json.loads((REPOSITORY / LEASE_SCHEMA).read_bytes())["tables"]["lease"]
    (field,) = [f for f in layout["fields"] if f["name"] == "Lease Number"]
    start = field["start"] - 1
    with ZipFile(tape_path) as archive, archive.open(layout["member"]) as member:
        return [
            line[start : start + field["length"]].decode("cp1252") for line in member
        ]


def read_bore_file(bore_path, cutoff):
    with ZipFile(bore_path) as archive, archive.open(MEMBER) as member:
        raw = pd.read_csv(
            member, usecols=list(FIELDS), dtype=str, keep_default_na=False
        )
    raw = raw.rename(columns=FIELDS)
    gulf = raw.loc[raw.region.str.strip().eq("G")].apply(lambda col: col.str.strip())
    if not gulf.api12.str.fullmatch(r"[0-9]{12}").all() or not gulf.api12.is_unique:
        raise ValueError("Invalid or duplicate Gulf API12")
    gulf["api10"] = gulf.api12.str[:10]
    gulf["spud"] = pd.to_datetime(gulf.date_text.replace("", pd.NA), format="%m/%d/%Y")
    if gulf.spud.gt(cutoff).any():
        raise ValueError("Gulf spud after the pinned collection date")
    return raw, gulf


def lease_hits(bores, effective):
    # Find original type and bottom before selecting a lease or an issue year.
    dated = bores.dropna(subset=["spud"])
    earliest = dated.groupby("api10").spud.transform("min")
    first = dated.loc[dated.spud.eq(earliest), ["api10", "spud", "type_code", "bottom"]]
    first = first.drop_duplicates()
    original = first.loc[~first.api10.duplicated(keep=False) & first.type_code.eq("E")]
    original_ids = set(
        original.loc[original.spud.ge(original.bottom.map(effective)), "bottom"]
    )

    ends = bores[["bottom", "surface", "spud", "type_code"]].melt(
        id_vars=["spud", "type_code"],
        var_name="endpoint",
        value_name="lease",
        ignore_index=False,
    )
    ends = ends.loc[ends.lease.isin(effective.index)].copy()
    ends["effective"] = ends.lease.map(effective)
    on_time = ends.loc[ends.spud.ge(ends.effective)]
    bottom = set(on_time.loc[on_time.endpoint.eq("bottom"), "lease"])
    surface = set(on_time.loc[on_time.endpoint.eq("surface"), "lease"])
    exploratory = on_time.loc[on_time.type_code.eq("E")]
    hits = {
        "original": original_ids,
        "a": bottom,
        "b": surface,
        "c": set(on_time.lease),
        "d": set(exploratory.lease),
        "e": set(ends.lease),
        "overlap": bottom & surface,
        "e_bottom": set(exploratory.loc[exploratory.endpoint.eq("bottom"), "lease"]),
        "pre": set(ends.loc[ends.spud.lt(ends.effective), "lease"]),
        "undated": set(ends.loc[ends.spud.isna(), "lease"]),
    }
    if not original_ids <= hits["e_bottom"] <= hits["d"] <= hits["c"] <= hits["e"]:
        raise ValueError(
            "Lease sets violate nesting of the original and broader criteria"
        )
    if hits["e"] != hits["c"] | hits["pre"] | hits["undated"]:
        raise ValueError("Spud-date categories do not cover the endpoint matches")
    return hits, on_time


def group_counts(ids, hits):
    group = set(ids)
    counts = {key: len(group & leases) for key, leases in hits.items()}
    counts["n"] = len(group)
    counts["balance"] = counts["a"] + counts["b"] - counts["c"]
    if counts["balance"] != counts["overlap"]:
        raise ValueError("Endpoint conservation failed")
    extra = group & (hits["e"] - hits["c"])
    pre = extra & hits["pre"]
    undated = extra & hits["undated"]
    counts.update(
        extra=len(extra),
        earlier_only=len(pre - undated),
        missing_only=len(undated - pre),
        both=len(pre & undated),
    )
    if len(extra) != counts["earlier_only"] + counts["missing_only"] + counts["both"]:
        raise ValueError("Unclassified lease in the any-date increment")
    return counts


def checked_groups(leases, hits, reference_csv):
    reference = pd.read_csv(reference_csv, dtype={"issue_year": str})
    reference = reference.set_index(["issue_year", "depth_band"])
    if not reference.index.is_unique:
        raise ValueError("Duplicate year/depth row in the reference")
    rows = {}
    for year, band, group in analysis.groups(leases, range(2005, 2021)):
        counts = group_counts(group.lease_id, hits)
        published = reference.loc[(year, band)]
        for key, col in [
            ("n", "leases"),
            ("original", "explored_leases"),
            ("e_bottom", "leases_with_any_e_bore"),
        ]:
            if counts[key] != published[col]:
                raise ValueError(
                    f"{year} / {band}: {key}={counts[key]} vs {published[col]}"
                )
        rows[year, band] = counts
    if rows.keys() != set(reference.index):
        raise ValueError("Coverage differs from the original year and depth grid")
    for year in [*map(str, range(2005, 2021)), analysis.ALL_YEARS]:
        for key, value in rows[year, analysis.ALL].items():
            if sum(rows[year, b][key] for b in analysis.BANDS) != value:
                raise ValueError(f"Band counts fail to sum: {year}, {key}")
    return rows


def normalise(value):
    compact = "".join(value.split()).upper()
    return re.sub(r"^G0+(?=[0-9]+$)", "G", compact)


def format_audit(tape, raw):
    tape_raw = set(tape)
    tape_ids = {s.strip() for s in tape}
    canonical = {normalise(s) for s in tape}
    if len(tape_ids) != len(canonical) or "" in canonical:
        raise ValueError("Blank or ambiguous normalized tape ID")
    rows = []
    for scope, records in [
        ("Whole file", raw),
        ("Gulf", raw.loc[raw.region.str.strip().eq("G")]),
    ]:
        bottom, surface = Counter(records.bottom), Counter(records.surface)
        for field, freq in [
            ("Bottom", bottom),
            ("Surface", surface),
            ("Combined", bottom + surface),
        ]:
            nonblank = {s for s in freq if s.strip()}
            literal = {s for s in nonblank if s not in tape_raw}
            trimmed = {s for s in nonblank if s.strip() not in tape_ids}
            still_out = {s for s in nonblank if normalise(s) not in canonical}
            if not still_out <= trimmed <= literal:
                raise ValueError("Normalization lost a source match")

            def tally(keys, frequency=freq):
                return f"{len(keys):,} / {sum(frequency[s] for s in keys):,}"

            rows.append(
                [
                    scope,
                    field,
                    sum(freq[s] for s in freq.keys() - nonblank),
                    tally(literal),
                    tally(literal - still_out),
                    tally(trimmed),
                    tally(trimmed - still_out),
                    tally(still_out),
                ]
            )
    return rows


def examples(values, tape_ids, cohort_ids):
    unique = list(dict.fromkeys(values))
    groups = [
        [s for s in unique if s.strip().isdigit()],
        [s for s in unique if s.strip().startswith("G0")],
        [s for s in unique if s.strip() in cohort_ids],
        [s for s in unique if s.strip() and s.strip() not in tape_ids],
    ]
    sample = list(dict.fromkeys([s for group in groups for s in group[:5]] + unique))[
        :20
    ]
    if len(sample) != 20:
        raise ValueError("Fewer than 20 distinct source examples")
    return [f"`{s!r}`" for s in sample]


def table(headers, rows):
    def row(cells):
        return "| " + " | ".join(str(cell) for cell in cells) + " |"

    return "\n".join(
        [row(headers), row(["---"] * len(headers)), *(row(r) for r in rows)]
    )


def share(n, total):
    return f"{n:,} ({100 * n / total:.2f}%)" if total else "0 (n/a)"


def report(leases, raw, gulf, tape, rows, eligible, cutoff, pins):
    pooled = rows[analysis.ALL_YEARS, analysis.ALL]
    deep = rows["2005", analysis.BANDS[3]]
    n = pooled["n"]
    deep_ids = leases.loc[
        leases.issue_year.eq(2005) & leases.depth_band.eq(analysis.BANDS[3]), "lease_id"
    ]
    deep_e = eligible.loc[eligible.type_code.eq("E") & eligible.lease.isin(deep_ids)]
    surface_only = set(deep_e.lease) - set(
        deep_e.loc[deep_e.endpoint.eq("bottom"), "lease"]
    )
    witness = (
        gulf.loc[deep_e.loc[deep_e.lease.isin(surface_only)].index]
        .sort_values(["spud", "api12"])
        .iloc[0]
    )
    text = [
        "# How many Gulf leases saw an exploration well?",
        (
            f"**The {100 * pooled['original'] / n:.2f}% result reproduces for the original-spud, bottom-lease rule.** "
            f"The reconstruction finds {pooled['original']:,} of {n:,} leases. Counting all dated type E "
            f"bores at the bottom adds {pooled['e_bottom'] - pooled['original']} leases "
            f"({pooled['e_bottom']:,} total). Allowing an E bore at the surface adds another "
            f"{pooled['d'] - pooled['e_bottom']}. **Variant d best matches “leases that saw an exploration well”** "
            f"when either recorded endpoint counts and later exploratory branches qualify. It gives "
            f"**{pooled['d']:,} of {n:,} ({100 * pooled['d'] / n:.2f}%)**. "
            f"A surface-only match establishes where the bore started. Its bottom can lie on another lease."
        ),
        (
            f"For 2005 leases in at least 1,500 m, the original result is "
            f"**{deep['original']} of {deep['n']} ({100 * deep['original'] / deep['n']:.2f}%)**. "
            f"Variant d gives **{deep['d']} of {deep['n']} ({100 * deep['d'] / deep['n']:.2f}%)**. "
            f"The additional lease is `{witness.surface}`. Type E bore `{witness.api12}` spudded on "
            f"{witness.spud:%Y-%m-%d} with that surface lease and bottom lease `{witness.bottom}`."
        ),
        (
            f"Across the full cohort, all dated types at either endpoint reach "
            f"{pooled['c']:,} of {n:,} ({100 * pooled['c'] / n:.2f}%). Counting both ends and later E bores "
            f"raises the exploration share by {100 * (pooled['d'] - pooled['original']) / n:.2f} percentage points. "
            f"Even the widest rule, including undated listings, reaches {100 * pooled['e'] / n:.2f}%. "
            "These files establish observed endpoint matches through the snapshot. "
            "They cannot establish unrecorded well-path crossings, eventual drilling, or the basis of an external estimate."
        ),
        "## Lease incidence",
        (
            "Every percentage uses the lease count in its row. Each lease counts once per column. "
            "A dated match requires WELL_SPUD_DATE on or after the matched lease’s own effective date "
            "through the borehole snapshot. The effective day qualifies. No lease-end-date filter is applied."
        ),
        (
            "- **Original** · earliest dated Gulf spud for the ten-digit well (first ten digits of API12), "
            "with type E and a matching bottom lease. A tie with conflicting bottoms or types excludes the well.\n"
            "- **a, b, c** · any dated borehole, any type, including sidetracks and bypasses. "
            "Column a uses the bottom lease, b the surface lease, and c either endpoint.\n"
            "- **d** · the same either-endpoint match as c, restricted to type E on that borehole row.\n"
            "- **e** · either endpoint, any type, including rows dated before effectiveness and rows with no spud date."
        ),
    ]
    order = [analysis.ALL, *analysis.BANDS]
    periods = [(analysis.ALL_YEARS, "2005 to 2020"), ("2005", "2005")]
    for year, label in periods:
        incidence = []
        for band in order:
            g = rows[year, band]
            incidence.append(
                [
                    band,
                    f"{g['n']:,}",
                    *[
                        share(g[k], g["n"])
                        for k in ("original", "a", "b", "c", "d", "e")
                    ],
                ]
            )
        text.extend(
            [
                f"### Leases effective in {label}",
                table(
                    [
                        "Lease depth",
                        "Leases",
                        "Original E",
                        "a · Bottom",
                        "b · Surface",
                        "c · Either",
                        "d · E either",
                        "e · Any date",
                    ],
                    incidence,
                ),
            ]
        )
    checks = []
    for year, label in periods:
        for band in order:
            g = rows[year, band]
            checks.append(
                [
                    label,
                    band,
                    f"{g['a']} + {g['b']} − {g['c']} = {g['balance']}",
                    g["overlap"],
                    g["extra"],
                    g["earlier_only"],
                    g["missing_only"],
                    g["both"],
                    share(g["e"] - g["missing_only"], g["n"]),
                ]
            )
    text.extend(
        [
            "## Endpoint overlap and date-filter losses",
            (
                f"**{pooled['overlap']} leases** have both a qualifying bottom match and a qualifying surface match. "
                "The two matches can come from different boreholes. The intersection column counts these lease IDs directly "
                "to check the inclusion-exclusion identity a + b − c. "
                f"Removing the date rule adds **{pooled['extra']} leases**. Of these, {pooled['earlier_only']} "
                f"have only earlier spuds and {pooled['missing_only']} have only undated listings. "
                "An undated listing alone does not establish a spud. The last column counts leases with "
                "at least one recorded spud date at either endpoint, before or after effectiveness or on the day."
            ),
            table(
                [
                    "Effective years",
                    "Lease depth",
                    "a + b − c",
                    "Intersection",
                    "e − c",
                    "Earlier only",
                    "Undated only",
                    "Both",
                    "Any recorded spud date",
                ],
                checks,
            ),
            "## Borehole type codes",
            (
                "Counts below are borehole records. The two cohort columns count a bore once if either endpoint "
                "qualifies under c, including when both ends qualify. The 2005 column is a subset of 2005 to 2020."
            ),
        ]
    )
    cohort_2005 = set(leases.loc[leases.issue_year.eq(2005), "lease_id"])
    types = gulf.type_code
    series = [
        raw.type_code.str.strip(),
        types,
        types.loc[eligible.index.unique()],
        types.loc[eligible.loc[eligible.lease.isin(cohort_2005)].index.unique()],
    ]
    census = (
        pd.concat([s.replace("", "(blank)").value_counts() for s in series], axis=1)
        .fillna(0)
        .astype(int)
        .sort_index()
    )
    totals = [len(s) for s in series]
    if list(census.sum()) != totals:
        raise ValueError("Type census does not reconcile to borehole rows")
    census_rows = [
        [code, *[f"{v:,}" for v in cells]] for code, cells in census.iterrows()
    ]
    text.extend(
        [
            table(
                ["WELL_TYPE_CODE", "Whole file", "Gulf", "c · 2005 to 2020", "c · 2005"],
                [*census_rows, ["Total", *[f"{v:,}" for v in totals]]],
            ),
            "## Lease-number format",
        ]
    )
    audit = format_audit(tape, raw)
    tape_ids = {s.strip() for s in tape}
    text.extend(
        [
            (
                f"All **{len(tape_ids):,} distinct tape IDs** are eligible for this lookup, across all effective years "
                "and statuses. A literal comparison retains the tape field’s fixed-width padding and the CSV "
                "field’s original spaces. The existing join strips outer whitespace on both sides and preserves "
                "case and zeros. Full normalization removes whitespace, folds case and strips leading zeros "
                "only from the numeric suffix of a G-prefixed ID. An unprefixed number keeps its zeros."
            ),
            table(
                [
                    "Scope",
                    "Endpoint",
                    "Blank rows",
                    "Literal misses",
                    "Literal misses recovered by full norm.",
                    "Misses after trim",
                    "Additional recoveries after trim",
                    "Still unmatched",
                ],
                audit,
            ),
            (
                "Each pair is **distinct nonblank source strings / field occurrences**. Combined pools both "
                "fields, so a string can contribute twice on one bore. All recoveries come from trimming field "
                "padding. Case and leading-zero normalization recover zero further matches. No two decoded "
                "tape IDs collapse together. Formatting therefore adds zero cohort leases to the existing join."
            ),
            "### Twenty distinct strings per source field",
            (
                "Quotes delimit the exact source text, including spaces before or after an ID. Each column "
                "is sampled independently to show legacy numeric, G-prefixed, cohort and unmatched forms where present."
            ),
            table(
                ["LSETAPE · Lease Number", "BOTM_LEASE_NUMBER", "SURF_LEASE_NUMBER"],
                zip(
                    *(
                        examples(values, tape_ids, set(leases.lease_id))
                        for values in [tape, raw.bottom, raw.surface]
                    )
                ),
            ),
            "## Basis and reproduction",
            (
                f"The denominator uses the same Gulf effective lease records and lease-block depth bands as "
                f"derive.py. Maximum block depth is converted from feet to metres (× 0.3048). Missing or "
                f"invalid depth ranges go in Unknown. The bore filter is REGION_CODE = G with a unique "
                f"12-digit API per row. The latest Gulf spud was **{gulf.spud.max():%Y-%m-%d}** "
                f"and the borehole collection cutoff was **{cutoff:%Y-%m-%d}**. Follow-up varies by effective year."
            ),
            table(
                ["Pinned archive / member", "SHA-256 of archive"],
                [
                    [
                        f"{TAPE} · LSETAPE.DAT",
                        f"`{pins[TAPE]['sha256']}`",
                    ],
                    [f"{BORE} · {MEMBER}", f"`{pins[BORE]['sha256']}`"],
                ],
            ),
            (
                f"Run `uv run bound_check.py --data-dir bsee-inputs` in this folder. The script verifies archive digests and byte "
                f"counts against source_pins.json. It reconciles the lease denominator, the original E count and "
                f"the all-bore E-bottom count to every one of the {len(rows)} year/depth rows in "
                f"`output/exploration.csv` before writing this report."
            ),
        ]
    )
    return "\n\n".join(text) + "\n"


def calculate_bounds(data_dir, pins, reference_csv, report_path=None):
    """Count matches from the verified snapshot and reconcile the saved exploration rows."""
    cutoff = pd.Timestamp(pins[BORE]["collection_end_utc"]).tz_convert(None).normalize()
    leases, _, _ = read_leases(data_dir / TAPE, REPOSITORY)
    leases = leases.loc[leases.issue_year.between(2005, 2020)].copy()
    leases["depth_band"] = analysis.depth_band(leases.lease_depth_m)
    raw, gulf = read_bore_file(data_dir / BORE, cutoff)
    hits, eligible = lease_hits(gulf, leases.set_index("lease_id").effective_date)
    rows = checked_groups(leases, hits, reference_csv)
    if report_path is not None:
        content = report(
            leases, raw, gulf, raw_tape_ids(data_dir / TAPE), rows, eligible, cutoff, pins
        )
        report_path.write_text(content, encoding="utf-8")
    return rows


def main():
    parser = input_parser(__doc__)
    parser.add_argument(
        "--exploration-csv", type=Path, default=EXAMPLE / "output/exploration.csv"
    )
    parser.add_argument("--report", type=Path, default=EXAMPLE / "bound-check.md")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as scratch:
        data_dir = Path(scratch) / "inputs"
        pins = verified_inputs(args.data_dir, data_dir, (BORE, TAPE))
        calculate_bounds(data_dir, pins, args.exploration_csv, args.report)


if __name__ == "__main__":
    main()
