#!/usr/bin/env python3
"""Build the per-well D&C days listing for the World Oil April 2026 QA/QC.

Companion drill-down to the field-level reconciliation matrix in
``reports/lower_tertiary/wo-april-2026-validation.md`` (section 3): one row per
wellbore so each development's D&C total can be audited bore by bore against
the article's Table 1.

Source of truth: ``docs/modules/bsee/analysis/production/FDAS_V30/
drilling_and_completion_days_v21_kc.csv`` — the canonical extractor output on
the V50/wed basis (253 wellbores, 25,404 D&C days). Producer markers come from
the OGOR-A well benchmark CSV (api12 match only; its day columns are calendar
spans, never used here).

Stdlib-only; deterministic output (no timestamps).
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE_CSV = (
    REPO
    / "docs/modules/bsee/analysis/production/FDAS_V30"
    / "drilling_and_completion_days_v21_kc.csv"
)
BENCHMARK_CSV = (
    REPO / "reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv"
)
VINTAGE_CSV = REPO / "reports/lower_tertiary/data/dc_vintage_diff.csv"
OUT_MD = REPO / "reports/lower_tertiary/wo-april-2026-per-well-dc.md"

# Lease-name → development grouping (matches the article's Table 1 rows).
DEV_OF_LEASE = {
    "Cascade": "Cascade Chinook",
    "Chinook": "Cascade Chinook",
    "Jack": "Jack St Malo",
    "St Malo": "Jack St Malo",
}

# Frozen from the article's Table 1 as tabulated by Roy Shilling
# (email 2026-07-05, "GLOBAL NEED for DRY TREES" thread): bores incl.
# sidetracks, producer wells, total D&C days. Big Foot was excluded there.
WO_ARTICLE = {
    "Anchor": (17, 3, 1825),
    "Buckskin": (24, 4, 2004),
    "Cascade Chinook": (14, 3, 2467),
    "Jack St Malo": (73, 24, 6928),
    "Julia": (9, 4, 1687),
    "Kaskida": (7, 0, 841),
    "North Platte": (20, 0, 971),
    "Shenandoah": (23, 4, 2346),
    "Stones": (22, 10, 2625),
    "Tiber": (2, 0, 250),
}

# Reconciliation status per development, mirroring validation-page section 3.
STATUS = {
    "Anchor": "exact",
    "Buckskin": "recovered — +1 bore / +52 days vs article (was missing entirely)",
    "Cascade Chinook": "exact",
    "Jack St Malo": "open — +119 days, suspect post-TD completion over-count (#846)",
    "Julia": "exact",
    "Kaskida": "exact",
    "North Platte": "days exact; +3 zero-day sidetracks",
    "Shenandoah": "resolved — +24 recompletion-accounting days (frozen V30 was −357)",
    "Stones": "exact vs article; +20 post-cutoff well-servicing days",
    "Tiber": "exact",
    "Big Foot": "WED-only — excluded from the article's Table 1",
}

# Bore-level annotations. The two Jack St Malo bores are the entire +234-day
# frozen-vs-candidate delta localized by the #846 diagnostic (PR #897).
BORE_NOTES = {
    "608124015400": "#846 suspect: +48 drill / +71 compl vs frozen V30",
    "608124015504": "#846 suspect: +68 drill / +47 compl vs frozen V30",
}

DEV_NOTES = {
    "Big Foot": (
        "+33 of these completion days accrued after the article's Nov-2025 "
        "cutoff as post-TD servicing on one well (TD 2020) — see validation "
        "section 3.1."
    ),
    "Stones": (
        "+20 of these completion days accrued after the article's Nov-2025 "
        "cutoff as post-TD servicing on three wells (TD 2018–2022) — see "
        "validation section 3.1."
    ),
    "Jack St Malo": (
        "Bores split across two leases: Jack (8 bores, 1,117 D&C days) and "
        "St Malo (65 bores, 5,930 D&C days). The +119-day delta vs the "
        "article is tracked as issue #846; the two flagged bores below carry "
        "the entire +234-day frozen-vs-candidate difference."
    ),
    "Buckskin": (
        "Producer markers are unavailable for Buckskin (the OGOR-A benchmark "
        "covers the seven core LT fields; the article counts 4 producers)."
    ),
}


def _parse_date(raw: str) -> tuple[int, str]:
    """Return (sort_key, iso_string) for an MM/DD/YYYY date; blanks sort last."""
    raw = (raw or "").strip()
    if not raw:
        return (99999999, "—")
    dt = datetime.strptime(raw, "%m/%d/%Y")
    return (int(dt.strftime("%Y%m%d")), dt.strftime("%Y-%m-%d"))


def _int(raw: str) -> int:
    raw = (raw or "").strip()
    return int(float(raw)) if raw else 0


def load_bores() -> dict[str, list[dict]]:
    producers = set()
    with BENCHMARK_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            producers.add(row["api12"].strip())

    devs: dict[str, list[dict]] = {}
    with SOURCE_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            lease_name = row["LEASE_NAME"].strip()
            dev = DEV_OF_LEASE.get(lease_name, lease_name)
            api12 = row["API_WELL_NUMBER"].strip()
            spud_key, spud = _parse_date(row["WELL_SPUD_DATE"])
            _, td = _parse_date(row["TOTAL_DEPTH_DATE"])
            drill = _int(row["DRILLING_DAYS"])
            compl = _int(row["COMPLETION_DAYS"])
            devs.setdefault(dev, []).append(
                {
                    "api12": api12,
                    "bore": row["WELL_NAME"].strip() or api12[-4:],
                    "lease_name": lease_name,
                    "lease_num": row["SURF_LEASE_NUM"].strip(),
                    "spud_key": spud_key,
                    "spud": spud,
                    "td": td,
                    "drill": drill,
                    "compl": compl,
                    "sidetrack": api12[-2:] != "00",
                    "producer": api12 in producers,
                    "note": BORE_NOTES.get(api12, ""),
                }
            )
    for bores in devs.values():
        bores.sort(key=lambda b: (b["spud_key"], b["api12"]))
    return devs


def _fmt(n: int) -> str:
    return f"{n:,}"


def load_vintage_diff() -> dict[str, list[dict]]:
    """Group the frozen-V30 → wed per-bore diff rows by category."""
    groups: dict[str, list[dict]] = {}
    with VINTAGE_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            groups.setdefault(row["category"], []).append(row)
    return groups


def _vintage_section(groups: dict[str, list[dict]]) -> list[str]:
    changed = groups.get("drilling_changed", [])
    late = groups.get("late_data", [])
    servicing = groups.get("servicing_accrual", [])
    wed_only = groups.get("wed_only", [])
    buckskin = [r for r in wed_only if r["dev"] == "Buckskin"]
    stubs = [r for r in wed_only if r["dev"] != "Buckskin"]
    lines = [
        "## Drilling-days resolution (frozen V30 → wed)",
        "",
        "Per-bore diff of the frozen V30 workbook against the wed extract"
        " (committed as `data/dc_vintage_diff.csv`), answering whether drilling"
        " days are stable across data vintages:",
        "",
        f"- **Drilling days changed on {len(changed)} of 253 bores.** Once a"
        " bore reaches TD, its drilling-day count never moves — every bore"
        " populated in both vintages carries identical drilling days.",
        f"- **{len(late)} bores are late data, not reclassification**: they sat"
        " in the frozen V30 workbook as zero-day placeholder rows (no spud/TD)"
        " and now carry real WAR days. These account for every apparent"
        ' "drilling delta".',
        f"- **Completion days are open-ended**: {len(servicing)} long-TD'd"
        " bores accrued additional post-TD servicing days"
        f" (+{sum(int(r['d_compl']) for r in servicing)} days) with zero"
        " drilling movement — the #846 accounting behaviour.",
        f"- **{len(wed_only)} bores exist only in wed**:"
        f" all {len(buckskin)} Buckskin bores (the recovered development) and"
        f" {len(stubs)} zero-day sidetrack stubs (Anchor, North Platte).",
        "",
        "### Late-data bores (zero-day placeholders in frozen V30, real days now)",
        "",
        "| API12 | Development | Spud | Drilling added | Completion added |",
        "|---|---|---|---:|---:|",
    ]
    for r in sorted(late, key=lambda r: (r["dev"], r["api12"])):
        lines.append(
            f"| {r['api12']} | {r['dev']} | {r['spud_wed']} |"
            f" {r['d_drill']} | {r['d_compl']} |"
        )
    lines += [
        "",
        "### Servicing accrual on long-TD'd bores (drilling unchanged)",
        "",
        "| API12 | Development | Spud | Completion days V30 → wed | Added |",
        "|---|---|---|---|---:|",
    ]
    for r in sorted(servicing, key=lambda r: (r["dev"], r["api12"])):
        lines.append(
            f"| {r['api12']} | {r['dev']} | {r['spud_wed']} |"
            f" {r['compl_v30']} → {r['compl_wed']} | +{r['d_compl']} |"
        )
    lines += [
        "",
        "**Implication for the matrix:** every difference against the article"
        " decomposes into (a) wells whose WAR data arrived after the article's"
        " extract and (b) open-ended post-TD completion accrual. Drilling days"
        " need no accounting decision — they are final as printed. The only"
        " open choice is the completion-day boundary rule"
        " ([#846](https://github.com/vamseeachanta/worldenergydata/issues/846)):"
        " where post-TD rig time stops counting as completion and becomes well"
        " servicing.",
        "",
    ]
    return lines


def build_markdown(devs: dict[str, list[dict]], vintage: dict[str, list[dict]]) -> str:
    order = sorted(devs, key=lambda d: (d == "Big Foot", d))  # article devs first
    lines = [
        "# World Oil April 2026 — per-well D&C days listing",
        "",
        "One row per wellbore behind the field-level D&C reconciliation matrix in",
        "[the validation page, section 3](wo-april-2026-validation.html) — the",
        '"listing" requested in the QA/QC review so each development\'s total can',
        "be audited bore by bore against the article's Table 1.",
        "",
        "## Definitions and basis",
        "",
        "- **Source**: canonical extractor output"
        " `drilling_and_completion_days_v21_kc.csv` (V50 = wed basis, BSEE WAR"
        " vintage 2026-02-19): 253 wellbores across 26 leases, 11 developments.",
        "- **Drilling days** = rig-days from spud to total depth (TD)."
        " **Completion days** = rig-days after TD — this includes later"
        " recompletion and well-servicing rig time, the accounting behaviour"
        " tracked in [#846](https://github.com/vamseeachanta/worldenergydata/issues/846).",
        "- **Producer** markers come from the OGOR-A well benchmark (56 producing"
        " wells across the seven core LT fields); its calendar-day columns are"
        " never used here.",
        "- **Sidetrack** bores are identified by a non-zero API12 suffix"
        " (last two digits).",
        "",
        "## Summary vs the article",
        "",
        "| Development | Bores (wed) | Bores (WO) | Producers (wed) | Producers (WO)"
        " | Drilling | Completion | D&C (wed) | D&C (WO) | Δ | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    tot = {"bores": 0, "prod": 0, "drill": 0, "compl": 0, "wo_bores": 0, "wo_dc": 0}
    for dev in order:
        bores = devs[dev]
        n = len(bores)
        prod = sum(1 for b in bores if b["producer"])
        drill = sum(b["drill"] for b in bores)
        compl = sum(b["compl"] for b in bores)
        wo = WO_ARTICLE.get(dev)
        tot["bores"] += n
        tot["prod"] += prod
        tot["drill"] += drill
        tot["compl"] += compl
        if wo:
            tot["wo_bores"] += wo[0]
            tot["wo_dc"] += wo[2]
        delta = f"{drill + compl - wo[2]:+d}" if wo else "—"
        lines.append(
            f"| [{dev}](#{_anchor(dev)}) | {n} | {wo[0] if wo else '—'} |"
            f" {prod or '—'} | {wo[1] if wo else '—'} |"
            f" {_fmt(drill)} | {_fmt(compl)} | {_fmt(drill + compl)} |"
            f" {_fmt(wo[2]) if wo else '—'} | {delta if delta != '+0' else '0'} |"
            f" {STATUS[dev]} |"
        )
    lines.append(
        f"| **Total** | **{tot['bores']}** | **{tot['wo_bores']}** |"
        f" **{tot['prod']}** | **52** |"
        f" **{_fmt(tot['drill'])}** | **{_fmt(tot['compl'])}** |"
        f" **{_fmt(tot['drill'] + tot['compl'])}** | **{_fmt(tot['wo_dc'])}** |"
        " | article excl. Big Foot |"
    )
    lines += [
        "",
        "Producer scope differs between the two counts: wed 56 spans the seven"
        " core LT fields **including Big Foot (8)** but has no markers for"
        " Buckskin; the article's 52 **excludes Big Foot** and includes"
        " Buckskin (4). A dash means no marker, which is a true zero for the"
        " pre-production developments (Kaskida, North Platte, Tiber) and a"
        " coverage gap for Buckskin.",
        "",
        "The drilling / completion split is the first troubleshooting lever the"
        " article's Table 1 cannot provide: the deltas above (Jack St Malo"
        " +119, Shenandoah +24, Buckskin +52) trace to late-arriving well data"
        " and open-ended post-TD completion accounting — never to a change in"
        " any bore's drilling days. The vintage diff below proves it.",
        "",
    ]
    lines += _vintage_section(vintage)
    lines += [
        "## Per-development listings",
        "",
    ]
    for dev in order:
        bores = devs[dev]
        drill = sum(b["drill"] for b in bores)
        compl = sum(b["compl"] for b in bores)
        lines.append(
            f"### {dev} — {len(bores)} bores · {_fmt(drill)} drilling +"
            f" {_fmt(compl)} completion = {_fmt(drill + compl)} D&C days"
        )
        lines.append("")
        if dev in DEV_NOTES:
            lines.append(f"> {DEV_NOTES[dev]}")
            lines.append("")
        lines.append(
            "| API12 | Bore | Lease | Spud | TD date | Drilling | Completion |"
            " D&C | Sidetrack | Producer | Note |"
        )
        lines.append("|---|---|---|---|---|---:|---:|---:|:-:|:-:|---|")
        for b in bores:
            lines.append(
                f"| {b['api12']} | {b['bore']} | {b['lease_name']}"
                f" {b['lease_num']} | {b['spud']} | {b['td']} |"
                f" {b['drill']} | {b['compl']} | {b['drill'] + b['compl']} |"
                f" {'ST' if b['sidetrack'] else ''} |"
                f" {'✓' if b['producer'] else ''} | {b['note']} |"
            )
        lines.append("")
    lines += [
        "## Provenance",
        "",
        "Generated by `scripts/lower_tertiary/build_wo_per_well_dc.py` from the"
        " committed canonical extractor output; totals are pinned to the"
        " validation-page matrix by"
        " `tests/unit/lower_tertiary/test_wo_per_well_dc.py`.",
        "",
    ]
    return "\n".join(lines)


def _anchor(title: str) -> str:
    return title.lower().replace(" ", "-")


def main() -> None:
    devs = load_bores()
    vintage = load_vintage_diff()
    OUT_MD.write_text(build_markdown(devs, vintage), encoding="utf-8")
    total = sum(b["drill"] + b["compl"] for bores in devs.values() for b in bores)
    bores_n = sum(len(bores) for bores in devs.values())
    print(f"wrote {OUT_MD} — {bores_n} bores, {total:,} D&C days")


if __name__ == "__main__":
    main()
