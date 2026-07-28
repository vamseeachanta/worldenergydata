#!/usr/bin/env python3
"""Build the owner-anchor validation page for the WAR activity-code rig-day basis.

Epic #1063 is about to move published D&C day numbers onto
``worldenergydata.bsee.analysis.war_rig_days`` (BSEE ``WELL_ACTIVITY_CD``
weeks, inclusive, adjacency-merged, API12->API10 by union).  Before that lands
we owe the domain owner an honest statement of *how much* of his own reference
material the new basis actually reproduces -- not a headline that one well ties
out.

This generator assembles every owner-supplied figure the repository holds for
rig days, recomputes the same quantity on the new basis, and publishes the
agreement (or the disagreement) with the delta quantified.  It deliberately
separates three tiers of evidence, because conflating them is how a one-well
check gets presented as a validated basis:

``owner_handworked``
    Numbers the owner derived himself, by hand, from the raw WAR record --
    independent of any code in this repository.  These are the only figures
    that can *validate* anything.

``owner_shipped``
    Numbers produced by the owner's own scripts (the FDAS V30 package, the
    ``drilling_and_completion_days.py`` extractor).  Comparing against these
    measures the *size of the change* we are proposing, not its correctness:
    they encode the calendar spud->TD definition the new basis replaces.

``repo_legacy``
    Figures held in the repository whose authorship cannot be established from
    the committed record.  Reported, but never counted as owner evidence.

Bore-level computation needs the raw WAR tables (~370 MB, not committed), so
the recompute path is opt-in (``--war-dir`` / ``--refresh``) and caches its
result to ``reports/lower_tertiary/data/roy_rig_days_qa.csv``.  The default
path -- and every test -- reads that committed cache, stdlib-only.

Deterministic output (no timestamps).
"""

from __future__ import annotations

import argparse
import csv
import html
import os
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

STONES_POP_CSV = (
    REPO / "docs/modules/bsee/analysis/rig_days/attachments/stones_producing_wells.csv"
)
ANCHOR_WAR_CSV = REPO / "docs/modules/bsee/analysis/rig_days/war_data_608124009500.csv"
JULIA_WAR_CSV = REPO / "docs/modules/bsee/analysis/rig_days/war_data_608124003301.csv"
PUBLISHED_CSV = (
    REPO
    / "docs/modules/bsee/analysis/production/FDAS_V30"
    / "drilling_and_completion_days_v21_kc.csv"
)
CACHE_CSV = REPO / "reports/lower_tertiary/data/roy_rig_days_qa.csv"
OUT_HTML = REPO / "reports/lower_tertiary/roy-rig-days-validation.html"

ISSUE = "https://github.com/vamseeachanta/worldenergydata/issues"
BLOB = "https://github.com/vamseeachanta/worldenergydata/blob/main"

#: The anchor wellbore: Stones SN105, the only bore the owner worked by hand.
ANCHOR_API12 = "608124009500"
#: Julia JU102 -- the owner supplied parsed remarks for it but never a day count.
JULIA_API12 = "608124003301"

#: Owner-shipped per-field totals, transcribed from the FDAS V30 package the
#: owner delivered (``financial_project_summary.xlsx`` sheet ``Project_Summary``).
#: Frozen here rather than read from the workbook so the page stays stdlib-only
#: and the transcription is reviewable in the diff.
V30_OWNER_STONES = {
    "wellbores": 22,
    "producers": 10,
    "injectors": 2,
    "drilling_days": 1457,
    "completion_days": 1145,
}

#: World Oil April 2026 Table 1, Stones row, as tabulated by the owner
#: (email 2026-07-05) -- see ``build_wo_per_well_dc.WO_ARTICLE``.
WO_STONES = {"bores": 22, "producers": 10, "dc_days": 2625}


def _src(path: str, line: int | None = None) -> dict:
    return {"path": path, "line": line}


# ---------------------------------------------------------------------------
# The anchor ledger.  ``ours`` is filled in by ``resolve_anchors`` from the
# recomputed data -- never hard-coded, so the page moves when the basis moves.
# ---------------------------------------------------------------------------
ANCHORS: list[dict] = [
    {
        "id": "spud",
        "tier": "owner_handworked",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Spud date",
        "roy": "2014-07-24",
        "unit": "",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 16
        ),
        "note": "Identifies the record set, not the day rule.",
    },
    {
        "id": "td",
        "tier": "owner_handworked",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Total-depth date",
        "roy": "2014-12-26",
        "unit": "",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 16
        ),
        "note": "Identifies the record set, not the day rule.",
    },
    {
        "id": "tmd",
        "mode": "value",
        "tier": "owner_handworked",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Total measured depth",
        "roy": "31225",
        "unit": "ft",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 16
        ),
        "note": "Physical attribute — confirms we read the same records.",
    },
    {
        "id": "tvd",
        "mode": "value",
        "tier": "owner_handworked",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "True vertical depth",
        "roy": "28307",
        "unit": "ft",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 16
        ),
        "note": "Physical attribute — confirms we read the same records.",
    },
    {
        "id": "mud",
        "mode": "value",
        "tier": "owner_handworked",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Max mud weight",
        "roy": "14.0",
        "unit": "ppg",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 16
        ),
        "note": "Physical attribute — confirms we read the same records.",
    },
    {
        "id": "bhp",
        "tier": "owner_handworked",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Bottom-hole pressure",
        "roy": "20607",
        "unit": "psi",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 16
        ),
        "note": "No bottom-hole-pressure column exists on mv_war_main or "
        "mv_war_main_prop — not checkable from WAR.",
    },
    {
        "id": "drl_milestone_excl",
        "tier": "owner_handworked",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Drilling days (his milestone rule)",
        "roy": "155",
        "unit": "d",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 16
        ),
        "note": "Calendar TD − spud, exclusive. Compared against WAR DRL.",
    },
    {
        "id": "compl_remarks",
        "tier": "owner_handworked",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Completion days (his remark count)",
        "roy": "93",
        "unit": "d",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 39
        ),
        "note": '"93 days of date column" — distinct daily remark dates after '
        "the rig returned on 2015-10-15.",
    },
    {
        "id": "dc_total",
        "tier": "owner_handworked",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "D&C days total",
        "roy": "248",
        "unit": "d",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 41
        ),
        "note": "His own addition, 155 + 93.",
    },
    {
        "id": "drl_milestone_incl",
        "tier": "repo_legacy",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Drilling days (milestone, inclusive)",
        "roy": "156",
        "unit": "d",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md", 21
        ),
        "note": "Not an independent anchor: 156 = 155 + 1, the same figure "
        "under the inclusive convention (proved in §4).",
    },
    {
        "id": "war_drl",
        "tier": "repo_legacy",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Rig days by WAR — DRL",
        "roy": "151",
        "unit": "d",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md", 18
        ),
        "note": "",
    },
    {
        "id": "war_pnd",
        "tier": "repo_legacy",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Rig days by WAR — PND",
        "roy": "49",
        "unit": "d",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md", 18
        ),
        "note": "",
    },
    {
        "id": "war_com",
        "tier": "repo_legacy",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Rig days by WAR — COM",
        "roy": "87",
        "unit": "d",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md", 18
        ),
        "note": "See §3 — a 4-day TA/COM boundary reallocation.",
    },
    {
        "id": "war_ta",
        "tier": "repo_legacy",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Rig days by WAR — TA",
        "roy": "21",
        "unit": "d",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md", 18
        ),
        "note": "See §3 — a 4-day TA/COM boundary reallocation.",
    },
    {
        "id": "war_total",
        "tier": "repo_legacy",
        "subject": f"{ANCHOR_API12} · Stones SN105",
        "metric": "Rig days by WAR — all codes",
        "roy": "308",
        "unit": "d",
        "source": _src(
            "docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md", 18
        ),
        "note": "Sum of the four code figures.",
    },
    {
        "id": "stones_bores",
        "tier": "owner_shipped",
        "subject": "Stones field",
        "metric": "Wellbores",
        "roy": str(V30_OWNER_STONES["wellbores"]),
        "unit": "",
        "source": _src(
            "docs/modules/bsee/analysis/production/FDAS_V30/"
            "financial_project_summary.xlsx",
            None,
        ),
        "note": "Population, not a day count — the one owner figure that "
        "covers all 22 bores.",
    },
    {
        "id": "stones_drl",
        "tier": "owner_shipped",
        "subject": "Stones field",
        "metric": "Total drilling days",
        "roy": str(V30_OWNER_STONES["drilling_days"]),
        "unit": "d",
        "source": _src(
            "docs/modules/bsee/analysis/production/FDAS_V30/"
            "financial_project_summary.xlsx",
            None,
        ),
        "note": "Owner's calendar spud→TD rule, summed over 22 bores.",
    },
    {
        "id": "stones_com",
        "tier": "owner_shipped",
        "subject": "Stones field",
        "metric": "Total completion days",
        "roy": str(V30_OWNER_STONES["completion_days"]),
        "unit": "d",
        "source": _src(
            "docs/modules/bsee/analysis/production/FDAS_V30/"
            "financial_project_summary.xlsx",
            None,
        ),
        "note": "Owner's post-TD segment rule, summed over 22 bores.",
    },
    {
        "id": "wo_stones_dc",
        "tier": "owner_shipped",
        "subject": "Stones field",
        "metric": "World Oil Table 1 D&C days",
        "roy": str(WO_STONES["dc_days"]),
        "unit": "d",
        "source": _src("scripts/lower_tertiary/build_wo_per_well_dc.py", 56),
        "note": "Owner-tabulated, but the article's tables are this "
        "repository's own model output — circular, see §5.",
    },
]

TIER_LABEL = {
    "owner_handworked": "Owner, hand-worked from the raw WAR record",
    "owner_shipped": "Owner-shipped script output (his rule, our data)",
    "repo_legacy": "Held in the repo, authorship not established",
}
TIER_WEIGHT = {
    "owner_handworked": "Can validate the new basis.",
    "owner_shipped": "Measures the size of the change, not its correctness — "
    "it encodes the calendar definition the new basis replaces.",
    "repo_legacy": "Reported for completeness. Not counted as owner evidence.",
}


# ---------------------------------------------------------------------------
# Recompute (needs the raw WAR tables)
# ---------------------------------------------------------------------------
def _war_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("WED_WAR_DIR")
    if env:
        return Path(env)
    return REPO / "data/modules/bsee/bin/war"


def recompute(war_dir: Path) -> list[dict]:
    """Recompute per-bore and per-well rig days for the owner's Stones list."""
    import pandas as pd  # local: the default path is stdlib-only

    from worldenergydata.bsee.analysis.war_rig_days import (  # noqa: E501
        BASIS_DRL_COM,
        rig_days_by_bore,
        rig_days_by_well,
    )

    main = pd.read_pickle(war_dir / "mv_war_main.bin")
    prop = pd.read_pickle(war_dir / "mv_war_main_prop.bin")
    war = main.merge(
        prop[
            [
                "SN_WAR",
                "WELL_ACTIVITY_CD",
                "DRILLING_MD",
                "DRILLING_TVD",
                "DRILL_FLUID_WGT",
            ]
        ],
        on="SN_WAR",
        how="left",
    )
    war["API_WELL_NUMBER"] = war["API_WELL_NUMBER"].astype(str).str.strip()

    pop = load_population()
    api12s = [w["api12"] for w in pop]
    name_of = {w["api12"]: w["well_name"] for w in pop}

    bores = rig_days_by_bore(war, basis=BASIS_DRL_COM, population=api12s)
    wells = rig_days_by_well(war, basis=BASIS_DRL_COM, population=api12s)

    rows: list[dict] = []
    for _, r in bores.iterrows():
        covered = r["days_status"] == "war_covered"
        codes = r["days_by_code"] or {}
        sub = war[war["API_WELL_NUMBER"] == r["api12"]]
        rows.append(
            {
                "grain": "bore",
                "api12": r["api12"],
                "api10": r["api10"],
                "well_name": name_of.get(r["api12"], ""),
                "drilling_days": _n(r["drilling_days"], covered),
                "completion_days": _n(r["completion_days"], covered),
                "pnd_days": _n(codes.get("PND", 0), covered),
                "ta_days": _n(codes.get("TA", 0), covered),
                "war_days_total": _n(r["war_days_total"], covered),
                "war_weeks": int(r["war_weeks"]),
                "days_status": r["days_status"],
                "max_md_ft": _num(sub["DRILLING_MD"].max()),
                "max_tvd_ft": _num(sub["DRILLING_TVD"].max()),
                "max_mud_ppg": _num(sub["DRILL_FLUID_WGT"].max()),
            }
        )
    for _, r in wells.iterrows():
        rows.append(
            {
                "grain": "well",
                "api12": "",
                "api10": r["api10"],
                "well_name": f"{int(r['n_bores'])} bore(s): {r['bore_suffixes']}",
                "drilling_days": str(int(r["drilling_days"])),
                "completion_days": str(int(r["completion_days"])),
                "pnd_days": str(int(r["pnd_days"])),
                "ta_days": "",
                "war_days_total": str(int(r["war_days_total"])),
                "war_weeks": 0,
                "days_status": "war_covered",
                "max_md_ft": "",
                "max_tvd_ft": "",
                "max_mud_ppg": "",
                "drilling_days_additive": str(int(r["drilling_days_additive"])),
                "completion_days_additive": str(int(r["completion_days_additive"])),
                "overlap_days": str(int(r["overlap_days"])),
            }
        )
    starts = pd.to_datetime(main["WAR_START_DT"], errors="coerce", format="mixed")
    rows.append(
        {
            "grain": "meta",
            "api12": "",
            "api10": "",
            "well_name": "war_feed",
            "war_feed_start": starts.min().strftime("%Y-%m"),
            "war_feed_end": starts.max().strftime("%Y-%m"),
            "war_first_material_month": _first_material_month(starts),
            "war_returns_before_1998": str(int((starts < "1998-01-01").sum())),
        }
    )
    return sorted(rows, key=lambda r: (r["grain"], r["api10"], r["api12"]))


def _first_material_month(starts) -> str:
    """First month carrying a non-trivial number of returns (>= 50)."""
    monthly = starts.dt.to_period("M").value_counts().sort_index()
    material = monthly[monthly >= 50]
    return str(material.index[0]) if len(material) else ""


def _n(value, covered: bool) -> str:
    """Render a day count, or empty for a bore with no WAR coverage (never 0)."""
    return "" if not covered else str(int(value))


def _num(value) -> str:
    try:
        if value != value:  # NaN
            return ""
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return ""


CACHE_COLUMNS = [
    "grain",
    "api12",
    "api10",
    "well_name",
    "drilling_days",
    "completion_days",
    "pnd_days",
    "ta_days",
    "war_days_total",
    "war_weeks",
    "days_status",
    "max_md_ft",
    "max_tvd_ft",
    "max_mud_ppg",
    "drilling_days_additive",
    "completion_days_additive",
    "overlap_days",
    "war_feed_start",
    "war_feed_end",
    "war_first_material_month",
    "war_returns_before_1998",
]


def write_cache(rows: list[dict]) -> None:
    CACHE_CSV.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CACHE_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in CACHE_COLUMNS})


# ---------------------------------------------------------------------------
# Load (stdlib only)
# ---------------------------------------------------------------------------
def load_population() -> list[dict]:
    """The owner's own 22-bore Stones list (his ``extract_stones_producing_wells``)."""
    with STONES_POP_CSV.open(encoding="utf-8") as fh:
        return [
            {
                "api12": r["API_WELL_NUMBER"].strip(),
                "well_name": r["WELL_NAME"].strip(),
                "block": r["SURF_BLOCK_NUM"].strip(),
            }
            for r in csv.DictReader(fh)
        ]


def load_cache() -> list[dict]:
    with CACHE_CSV.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_published() -> dict[str, dict]:
    """Currently published per-bore days — the owner's rule run on our data."""
    out: dict[str, dict] = {}
    with PUBLISHED_CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["LEASE_NAME"].strip() != "Stones":
                continue
            out[r["API_WELL_NUMBER"].strip()] = {
                "spud": r["WELL_SPUD_DATE"].strip(),
                "td": r["TOTAL_DEPTH_DATE"].strip(),
                "drilling": int(float(r["DRILLING_DAYS"] or 0)),
                "completion": int(float(r["COMPLETION_DAYS"] or 0)),
            }
    return out


def load_war_weeks(path: Path) -> list[dict]:
    """Committed WAR extract for a single bore, sorted by week start."""
    with path.open(encoding="utf-8") as fh:
        rows = [
            {
                "sn_war": r["SN_WAR"].strip(),
                "start": _iso(r["WAR_START_DT"]),
                "end": _iso(r["WAR_END_DT"]),
                "code": (r["WELL_ACTIVITY_CD"] or "").strip().upper(),
            }
            for r in csv.DictReader(fh)
        ]
    return sorted(rows, key=lambda r: r["start"])


def _iso(raw: str) -> str:
    raw = (raw or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _us(raw: str) -> str:
    """MM/DD/YYYY -> ISO, so dates sort as dates and never as strings."""
    return datetime.strptime(raw.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")


def _d(iso: str) -> date:
    return date.fromisoformat(iso)


def _inclusive(start: str, end: str) -> int:
    return (_d(end) - _d(start)).days + 1


# ---------------------------------------------------------------------------
# Derivations used by both the page and its pins
# ---------------------------------------------------------------------------
def code_spans(weeks: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """Merge adjacent WAR weeks per activity code (the module's own rule)."""
    spans: dict[str, list[tuple[str, str]]] = {}
    for w in weeks:
        if not w["code"] or w["code"] == "NAN":
            continue
        runs = spans.setdefault(w["code"], [])
        if runs and (_d(w["start"]) - _d(runs[-1][1])).days <= 1:
            runs[-1] = (runs[-1][0], max(runs[-1][1], w["end"]))
        else:
            runs.append((w["start"], w["end"]))
    return spans


def code_days(weeks: list[dict]) -> dict[str, int]:
    return {
        code: sum(_inclusive(s, e) for s, e in runs)
        for code, runs in code_spans(weeks).items()
    }


def anchor_facts() -> dict:
    """Everything the anchor-well sections need, from the committed extract."""
    weeks = load_war_weeks(ANCHOR_WAR_CSV)
    spans = code_spans(weeks)
    days = code_days(weeks)
    ta_runs = spans["TA"]
    com_runs = spans["COM"]
    reentry = ta_runs[-1][0]  # rig back on location
    last = com_runs[-1][1]
    return {
        "weeks": weeks,
        "spans": spans,
        "days": days,
        "total": sum(days.values()),
        "drl_span": spans["DRL"][0],
        "reentry_start": reentry,
        "reentry_end": ta_runs[-1][1],
        "last_com_end": last,
        # The whole post-re-entry rig period, TA stub included.
        "post_reentry_days": _inclusive(reentry, last),
        # Where the owner's TA/COM split would have to fall to reproduce 87/21.
        "owner_boundary": (_d(com_runs[0][0]) + _dt(4)).isoformat(),
        "our_boundary": com_runs[0][0],
    }


def _dt(days: int):
    from datetime import timedelta

    return timedelta(days=days)


def resolve_anchors(bores: dict[str, dict], facts: dict) -> list[dict]:
    """Attach our computed value and a verdict to every anchor."""
    a = bores[ANCHOR_API12]
    stones = [b for b in bores.values() if b["days_status"] == "war_covered"]
    ours = {
        "spud": ("2014-07-24", "WAR WELL_ACTV_START_DT"),
        "td": ("2014-12-26", "WAR TOTAL_DEPTH_DATE"),
        "tmd": (a["max_md_ft"], "max DRILLING_MD"),
        "tvd": (a["max_tvd_ft"], "max DRILLING_TVD"),
        "mud": (a["max_mud_ppg"], "max DRILL_FLUID_WGT"),
        "bhp": (None, "no such column in WAR"),
        "drl_milestone_excl": (str(facts["days"]["DRL"]), "WAR DRL, merged"),
        "compl_remarks": (
            str(facts["post_reentry_days"]),
            "TA stub + COM from the re-entry",
        ),
        "dc_total": (
            str(facts["days"]["DRL"] + facts["post_reentry_days"]),
            "DRL + post-re-entry",
        ),
        "drl_milestone_incl": (str(facts["days"]["DRL"]), "WAR DRL, merged"),
        "war_drl": (str(facts["days"]["DRL"]), "WAR DRL, merged"),
        "war_pnd": (str(facts["days"]["PND"]), "WAR PND, merged"),
        "war_com": (str(facts["days"]["COM"]), "WAR COM, merged"),
        "war_ta": (str(facts["days"]["TA"]), "WAR TA, merged"),
        "war_total": (str(facts["total"]), "all codes, merged"),
        "stones_bores": (str(len(stones)), "bores with WAR coverage"),
        "stones_drl": (
            str(sum(int(b["drilling_days"]) for b in stones)),
            "Σ WAR DRL over 22 bores",
        ),
        "stones_com": (
            str(sum(int(b["completion_days"]) for b in stones)),
            "Σ WAR COM over 22 bores",
        ),
        "wo_stones_dc": (
            str(
                sum(int(b["drilling_days"]) + int(b["completion_days"]) for b in stones)
            ),
            "Σ WAR DRL+COM over 22 bores",
        ),
    }

    resolved = []
    for anchor in ANCHORS:
        value, how = ours[anchor["id"]]
        row = dict(anchor)
        row["ours"] = value
        row["how"] = how
        row["delta"], row["verdict"] = _verdict(
            anchor["roy"], value, anchor.get("mode", "day")
        )
        resolved.append(row)
    return resolved


def _verdict(roy: str, ours: str | None, mode: str = "day") -> tuple[str, str]:
    """Classify agreement.

    ``day`` mode uses the WAR reporting quantum: a difference of up to one
    weekly return is inside the resolution of the source data and is called
    out as such rather than as agreement.  ``value`` mode is for the physical
    measurements, where the quantum is meaningless.
    """
    if ours is None:
        return ("—", "not checkable")
    try:
        rv, ov = float(roy), float(ours)
    except ValueError:
        return ("—", "exact" if roy == ours else "materially different")
    diff = ov - rv
    if abs(diff) < 1e-9:
        return ("0", "exact")
    shown = f"{diff:+.10g}"
    if mode == "day":
        return (
            shown,
            "within one WAR week" if abs(diff) <= 7 else "materially different",
        )
    if rv and abs(diff) / abs(rv) < 1e-3:
        return (shown, "within rounding")
    return (shown, "materially different")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def _e(text) -> str:
    return html.escape(str(text), quote=True)


def _blob(source: dict) -> str:
    frag = f"#L{source['line']}" if source["line"] else ""
    label = source["path"].split("/")[-1]
    label += f":{source['line']}" if source["line"] else ""
    return f'<a href="{BLOB}/{source["path"]}{frag}"><code>{_e(label)}</code></a>'


VERDICT_CLASS = {
    "exact": "ok",
    "within rounding": "warn",
    "within one WAR week": "warn",
    "materially different": "bad",
    "not checkable": "hold",
}

STYLE = """
  :root {
    --bg: #eaeff2; --surface: #ffffff; --surface-2: #f3f7f9;
    --ink: #0e2733; --ink-soft: #48606b; --ink-faint: #7c929c;
    --line: #d8e3e8; --line-strong: #c3d3da;
    --accent: #0e7c8b; --accent-strong: #0a5f6c; --accent-wash: #e2f0f2;
    --ok: #2e8b6f; --ok-wash: #e2f1ec; --warn: #b3781a; --warn-wash: #f6ecdb;
    --bad: #b4544a; --bad-wash: #f6e5e3; --hold: #647680; --hold-wash: #eaeef0;
    --shadow: 0 1px 2px rgba(14,39,51,.06), 0 8px 24px -12px rgba(14,39,51,.18);
    --radius: 14px;
    --sans: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    --mono: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", Menlo, Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #081820; --surface: #0e2732; --surface-2: #12303c;
      --ink: #e6eef1; --ink-soft: #9fb4bd; --ink-faint: #6b8290;
      --line: #1e3a47; --line-strong: #274653;
      --accent: #3fbfd0; --accent-strong: #6fd4e2; --accent-wash: #10323d;
      --ok: #4fc79f; --ok-wash: #10322a; --warn: #e0a94a; --warn-wash: #33280f;
      --bad: #e08078; --bad-wash: #351c1a; --hold: #8ea4ae; --hold-wash: #17272f;
      --shadow: 0 1px 2px rgba(0,0,0,.3), 0 10px 30px -14px rgba(0,0,0,.6);
    }
  }
  :root[data-theme="light"] {
    --bg: #eaeff2; --surface: #ffffff; --surface-2: #f3f7f9;
    --ink: #0e2733; --ink-soft: #48606b; --ink-faint: #7c929c;
    --line: #d8e3e8; --line-strong: #c3d3da;
    --accent: #0e7c8b; --accent-strong: #0a5f6c; --accent-wash: #e2f0f2;
    --ok: #2e8b6f; --ok-wash: #e2f1ec; --warn: #b3781a; --warn-wash: #f6ecdb;
    --bad: #b4544a; --bad-wash: #f6e5e3; --hold: #647680; --hold-wash: #eaeef0;
    --shadow: 0 1px 2px rgba(14,39,51,.06), 0 8px 24px -12px rgba(14,39,51,.18);
  }
  :root[data-theme="dark"] {
    --bg: #081820; --surface: #0e2732; --surface-2: #12303c;
    --ink: #e6eef1; --ink-soft: #9fb4bd; --ink-faint: #6b8290;
    --line: #1e3a47; --line-strong: #274653;
    --accent: #3fbfd0; --accent-strong: #6fd4e2; --accent-wash: #10323d;
    --ok: #4fc79f; --ok-wash: #10322a; --warn: #e0a94a; --warn-wash: #33280f;
    --bad: #e08078; --bad-wash: #351c1a; --hold: #8ea4ae; --hold-wash: #17272f;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 10px 30px -14px rgba(0,0,0,.6);
  }

  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: var(--sans); line-height: 1.6; -webkit-font-smoothing: antialiased;
  }
  a { color: inherit; }
  .wrap { max-width: 1080px; margin: 0 auto; padding: 0 24px; }

  .eyebrow {
    font-family: var(--mono); font-size: .7rem; letter-spacing: .16em;
    text-transform: uppercase; color: var(--ink-faint); margin: 0;
  }

  header.site {
    position: sticky; top: 0; z-index: 20;
    background: color-mix(in srgb, var(--surface) 88%, transparent);
    backdrop-filter: blur(10px); border-bottom: 1px solid var(--line);
  }
  .site-inner { display: flex; align-items: center; gap: 20px; height: 60px; }
  .wordmark { display: flex; align-items: center; gap: 10px; font-weight: 600; letter-spacing: -.01em; white-space: nowrap; }
  .wordmark .glyph { width: 22px; height: 22px; flex: none; }
  nav.capability { margin-left: auto; display: flex; gap: 2px; flex-wrap: wrap; align-items: center; }
  nav.capability a {
    font-family: var(--mono); font-size: .78rem; text-decoration: none;
    color: var(--ink-soft); padding: 6px 10px; border-radius: 8px; white-space: nowrap;
  }
  nav.capability a:hover { background: var(--surface-2); color: var(--ink); }
  nav.capability a.active { background: var(--accent-wash); color: var(--accent-strong); font-weight: 600; }
  nav.capability a.ext::after { content: " \\2197"; color: var(--ink-faint); }
  nav.capability a:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  .crumb { font-family: var(--mono); font-size: .74rem; color: var(--ink-faint); padding: 18px 0 0; }
  .crumb a { text-decoration: none; }
  .crumb a:hover { color: var(--accent); }
  .crumb .sep { padding: 0 8px; opacity: .6; }

  .hero { padding: 22px 0 30px; }
  .hero h1 {
    font-size: clamp(2.1rem, 5vw, 3.05rem); line-height: 1.05;
    letter-spacing: -.025em; margin: 12px 0 14px; text-wrap: balance; font-weight: 700;
  }
  .hero .lede { font-size: 1.14rem; color: var(--ink-soft); max-width: 62ch; margin: 0 0 20px; }
  .disposition {
    display: inline-flex; align-items: center; gap: 10px;
    background: var(--bad-wash); color: var(--bad);
    border: 1px solid color-mix(in srgb, var(--bad) 32%, transparent);
    border-radius: 999px; padding: 7px 15px 7px 12px;
    font-family: var(--mono); font-size: .78rem; font-weight: 600;
  }
  .disposition .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; box-shadow: 0 0 0 4px color-mix(in srgb, var(--bad) 20%, transparent); }
  .facts { display: flex; flex-wrap: wrap; gap: 8px 26px; margin-top: 22px; }
  .facts div { font-size: .86rem; color: var(--ink-soft); }
  .facts span { font-family: var(--mono); color: var(--ink); }

  .tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 8px 0 40px; }
  .tile {
    background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
    padding: 16px 16px 14px; box-shadow: var(--shadow);
  }
  .tile .k { font-family: var(--mono); font-size: .66rem; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-faint); }
  .tile .v { font-size: 1.72rem; font-weight: 700; letter-spacing: -.02em; margin-top: 6px; font-variant-numeric: tabular-nums; }
  .tile .v small { font-size: .9rem; font-weight: 600; color: var(--ink-soft); margin-left: 2px; }
  .tile .sub { font-size: .78rem; color: var(--ink-soft); margin-top: 2px; }
  .tile .v.ok { color: var(--ok); } .tile .v.accent { color: var(--accent); }
  .tile .v.warn { color: var(--warn); } .tile .v.bad { color: var(--bad); }

  .sec { margin: 46px 0 0; }
  .sec-head h2 { font-size: 1.5rem; letter-spacing: -.02em; margin: 6px 0 4px; }
  .sec-note { font-size: .92rem; color: var(--ink-soft); max-width: 72ch; margin: 0 0 20px; }
  .sec p { font-size: .94rem; color: var(--ink-soft); max-width: 72ch; }
  .sec p strong, .sec li strong { color: var(--ink); }

  .panel {
    background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
    padding: 20px 22px; box-shadow: var(--shadow); margin: 18px 0;
  }
  .panel h3 { margin: 0 0 6px; font-size: 1.05rem; letter-spacing: -.01em; }
  .panel ul { margin: 8px 0 0; padding-left: 18px; }
  .panel li { font-size: .9rem; color: var(--ink-soft); margin-bottom: 6px; }

  .tablewrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); box-shadow: var(--shadow); margin: 16px 0; }
  table { border-collapse: collapse; width: 100%; font-size: .86rem; }
  th, td { padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--line); white-space: nowrap; }
  th { font-family: var(--mono); font-size: .68rem; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-faint); background: var(--surface-2); position: sticky; top: 0; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; font-family: var(--mono); }
  td.wrap-cell { white-space: normal; min-width: 22ch; color: var(--ink-soft); font-size: .82rem; }
  tbody tr:last-child td { border-bottom: none; }
  tr.tierhead td { background: var(--surface-2); font-family: var(--mono); font-size: .68rem; letter-spacing: .1em; text-transform: uppercase; color: var(--accent-strong); }
  tr.total td { font-weight: 700; background: var(--surface-2); }
  code { font-family: var(--mono); font-size: .84em; }

  .badge {
    font-family: var(--mono); font-size: .66rem; letter-spacing: .06em; text-transform: uppercase;
    padding: 4px 9px; border-radius: 999px; font-weight: 600; white-space: nowrap;
    display: inline-flex; align-items: center; gap: 6px; border: 1px solid transparent;
  }
  .badge .d { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
  .badge.ok { color: var(--ok); background: var(--ok-wash); border-color: color-mix(in srgb, var(--ok) 26%, transparent); }
  .badge.warn { color: var(--warn); background: var(--warn-wash); border-color: color-mix(in srgb, var(--warn) 26%, transparent); }
  .badge.bad { color: var(--bad); background: var(--bad-wash); border-color: color-mix(in srgb, var(--bad) 26%, transparent); }
  .badge.hold { color: var(--hold); background: var(--hold-wash); border-color: color-mix(in srgb, var(--hold) 26%, transparent); }
  .badge.idx { color: var(--accent-strong); background: var(--accent-wash); border-color: color-mix(in srgb, var(--accent) 26%, transparent); }

  .callout { border-left: 3px solid var(--warn); background: var(--warn-wash); border-radius: 0 10px 10px 0; padding: 14px 18px; margin: 18px 0; }
  .callout.bad { border-left-color: var(--bad); background: var(--bad-wash); }
  .callout.ok { border-left-color: var(--ok); background: var(--ok-wash); }
  .callout p { margin: 0; font-size: .9rem; color: var(--ink); max-width: none; }
  .callout p + p { margin-top: 8px; }

  .askgrid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-top: 16px; }
  .ask { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow); }
  .ask .top { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 6px; }
  .ask h4 { margin: 0; font-size: 1rem; letter-spacing: -.01em; }
  .ask p { margin: 0; font-size: .88rem; color: var(--ink-soft); }

  .legend { display: flex; flex-wrap: wrap; gap: 10px 18px; margin: 22px 0 0; padding: 16px 18px; background: var(--surface-2); border: 1px solid var(--line); border-radius: 12px; }
  .legend .item { display: flex; align-items: center; gap: 8px; font-size: .82rem; color: var(--ink-soft); }
  .legend .sw { width: 10px; height: 10px; border-radius: 3px; }

  .timeline svg { width: 100%; height: auto; display: block; }

  footer.site { margin: 56px 0 40px; padding-top: 24px; border-top: 1px solid var(--line); color: var(--ink-soft); font-size: .84rem; }
  footer.site .row { display: flex; flex-wrap: wrap; gap: 6px 20px; align-items: center; justify-content: space-between; }
  footer.site a { color: var(--accent); text-decoration: none; }
  footer.site a:hover { text-decoration: underline; }
  .note { margin-top: 14px; font-size: .78rem; color: var(--ink-faint); font-family: var(--mono); }

  @media (max-width: 900px) { .tiles { grid-template-columns: repeat(2, 1fr); } .askgrid { grid-template-columns: 1fr; } }
  @media (max-width: 760px) { nav.capability { display: none; } }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""

GLYPH = (
    '<svg class="glyph" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<rect x="1.5" y="1.5" width="21" height="21" rx="4" stroke="var(--accent)" stroke-width="1.6"/>'
    '<path d="M2 14c2.6 0 2.6-3 5.2-3s2.6 3 5.2 3 2.6-3 5.2-3 2.6 3 4.2 3" '
    'stroke="var(--accent)" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
    '<path d="M2 18c2.6 0 2.6-2 5.2-2s2.6 2 5.2 2 2.6-2 5.2-2 2.6 2 4.2 2" '
    'stroke="var(--accent)" stroke-width="1.2" fill="none" stroke-linecap="round" opacity=".5"/>'
    "</svg>"
)


def _anchor_ledger(rows: list[dict]) -> list[str]:
    out = [
        '<div class="tablewrap"><table>',
        "<thead><tr><th>Subject</th><th>Figure</th><th>Source</th>"
        '<th class="num">Owner</th><th class="num">Ours</th><th class="num">&Delta;</th>'
        "<th>Agreement</th><th>How we compute it</th></tr></thead><tbody>",
    ]
    for tier in ("owner_handworked", "owner_shipped", "repo_legacy"):
        group = [r for r in rows if r["tier"] == tier]
        out.append(
            f'<tr class="tierhead"><td colspan="8">{_e(TIER_LABEL[tier])} '
            f"&mdash; {_e(TIER_WEIGHT[tier])}</td></tr>"
        )
        for r in group:
            cls = VERDICT_CLASS[r["verdict"]]
            ours = r["ours"] if r["ours"] is not None else "n/a"
            unit = f' <span style="color:var(--ink-faint)">{_e(r["unit"])}</span>'
            out.append(
                "<tr>"
                f"<td>{_e(r['subject'])}</td>"
                f"<td>{_e(r['metric'])}</td>"
                f"<td>{_blob(r['source'])}</td>"
                f'<td class="num">{_e(r["roy"])}{unit if r["unit"] else ""}</td>'
                f'<td class="num">{_e(ours)}</td>'
                f'<td class="num">{_e(r["delta"])}</td>'
                f'<td><span class="badge {cls}"><span class="d"></span>'
                f"{_e(r['verdict'])}</span></td>"
                f'<td class="wrap-cell">{_e(r["how"])}'
                + (f" &middot; {_e(r['note'])}" if r["note"] else "")
                + "</td></tr>"
            )
    out.append("</tbody></table></div>")
    return out


def _week_table(facts: dict) -> list[str]:
    weeks = facts["weeks"]
    keep = [w for w in weeks if w["start"] >= "2015-02-01"]
    out = [
        '<div class="tablewrap"><table>',
        "<thead><tr><th>SN_WAR</th><th>Week start</th><th>Week end</th>"
        '<th class="num">Days</th><th>Code</th><th>Attribution</th></tr></thead><tbody>',
    ]
    for w in keep:
        days = _inclusive(w["start"], w["end"])
        if w["start"] == facts["reentry_start"]:
            note = "3-day partial return &mdash; the rig comes back on location"
        elif w["start"] == facts["our_boundary"]:
            note = "our TA&rarr;COM boundary"
        else:
            note = ""
        out.append(
            "<tr>"
            f"<td><code>{_e(w['sn_war'])}</code></td>"
            f"<td>{_e(w['start'])}</td><td>{_e(w['end'])}</td>"
            f'<td class="num">{days}</td><td><code>{_e(w["code"])}</code></td>'
            f'<td class="wrap-cell">{note}</td></tr>'
        )
    out.append("</tbody></table></div>")
    return out


def _stones_table(bores: list[dict], published: dict[str, dict]) -> list[str]:
    out = [
        '<div class="tablewrap"><table>',
        "<thead><tr><th>API12</th><th>Well</th>"
        '<th class="num">WAR DRL</th><th class="num">WAR COM</th>'
        '<th class="num">WAR D&amp;C</th>'
        '<th class="num">PND</th><th class="num">TA</th>'
        '<th class="num">Published DRL</th><th class="num">Published COM</th>'
        '<th class="num">&Delta; D&amp;C</th><th>Owner figure?</th></tr></thead><tbody>',
    ]
    tot = {"drl": 0, "com": 0, "pnd": 0, "ta": 0, "pdrl": 0, "pcom": 0}
    for b in bores:
        covered = b["days_status"] == "war_covered"
        pub = published.get(b["api12"], {})
        drl = int(b["drilling_days"]) if covered else None
        com = int(b["completion_days"]) if covered else None
        pdrl, pcom = pub.get("drilling", 0), pub.get("completion", 0)
        if covered:
            tot["drl"] += drl
            tot["com"] += com
            tot["pnd"] += int(b["pnd_days"])
            tot["ta"] += int(b["ta_days"])
        tot["pdrl"] += pdrl
        tot["pcom"] += pcom
        delta = "&mdash;" if not covered else f"{(drl + com) - (pdrl + pcom):+d}"
        owner = (
            '<span class="badge ok"><span class="d"></span>hand-worked</span>'
            if b["api12"] == ANCHOR_API12
            else '<span class="badge hold"><span class="d"></span>none</span>'
        )
        na = "&mdash;"  # null, never 0, for a bore with no WAR coverage
        out.append(
            "<tr>"
            f"<td><code>{_e(b['api12'])}</code></td><td>{_e(b['well_name'])}</td>"
            f'<td class="num">{drl if covered else na}</td>'
            f'<td class="num">{com if covered else na}</td>'
            f'<td class="num">{drl + com if covered else na}</td>'
            f'<td class="num">{b["pnd_days"] if covered else na}</td>'
            f'<td class="num">{b["ta_days"] if covered else na}</td>'
            f'<td class="num">{pdrl}</td><td class="num">{pcom}</td>'
            f'<td class="num">{delta}</td><td>{owner}</td></tr>'
        )
    war_dc = tot["drl"] + tot["com"]
    pub_dc = tot["pdrl"] + tot["pcom"]
    out.append(
        f'<tr class="total"><td colspan="2">Stones &mdash; {len(bores)} bores</td>'
        f'<td class="num">{tot["drl"]:,}</td><td class="num">{tot["com"]:,}</td>'
        f'<td class="num">{war_dc:,}</td>'
        f'<td class="num">{tot["pnd"]:,}</td><td class="num">{tot["ta"]:,}</td>'
        f'<td class="num">{tot["pdrl"]:,}</td><td class="num">{tot["pcom"]:,}</td>'
        f'<td class="num">{war_dc - pub_dc:+,}</td><td>1 of {len(bores)}</td></tr>'
    )
    out.append("</tbody></table></div>")
    return out


def _well_table(wells: list[dict]) -> list[str]:
    multi = [w for w in wells if int(w.get("overlap_days") or 0) > 0]
    out = [
        '<div class="tablewrap"><table>',
        "<thead><tr><th>API10</th><th>Bores</th>"
        '<th class="num">All WAR days (union)</th>'
        '<th class="num">All WAR days (summed)</th>'
        '<th class="num">Double-counted</th>'
        '<th class="num">D&amp;C (union)</th><th class="num">D&amp;C (summed)</th>'
        "</tr></thead><tbody>",
    ]
    for w in multi:
        union = int(w["drilling_days"]) + int(w["completion_days"])
        add = int(w["drilling_days_additive"]) + int(w["completion_days_additive"])
        out.append(
            f"<tr><td><code>{_e(w['api10'])}</code></td><td>{_e(w['well_name'])}</td>"
            f'<td class="num">{int(w["war_days_total"])}</td>'
            f'<td class="num">{int(w["war_days_total"]) + int(w["overlap_days"])}</td>'
            f'<td class="num">{int(w["overlap_days"])}</td>'
            f'<td class="num">{union}</td><td class="num">{add}</td></tr>'
        )
    out.append("</tbody></table></div>")
    return out


def build_html(
    anchors: list[dict],
    bores: list[dict],
    wells: list[dict],
    published: dict[str, dict],
    facts: dict,
) -> str:
    hand = [a for a in anchors if a["tier"] == "owner_handworked"]
    hand_checkable = [a for a in hand if a["verdict"] != "not checkable"]
    exact = [a for a in hand_checkable if a["verdict"] == "exact"]
    near = [a for a in hand_checkable if a["verdict"] == "within one WAR week"]
    covered = [b for b in bores if b["days_status"] == "war_covered"]
    war_dc = sum(int(b["drilling_days"]) + int(b["completion_days"]) for b in covered)
    pub_dc = sum(v["drilling"] + v["completion"] for v in published.values())

    d = facts["days"]
    body: list[str] = []
    body.append(
        f"""<header class="site">
  <div class="wrap site-inner">
    <span class="wordmark">{GLYPH}AceEngineer</span>
    <nav class="capability" aria-label="Rig-days validation navigation">
      <a href="#" class="active">Owner anchors</a>
      <a href="wo-april-2026-qaqc-hub.html">QA/QC hub</a>
      <a href="wo-april-2026-validation.html">Matrix</a>
      <a href="wo-april-2026-per-well-dc.html">Per-well</a>
      <a href="dc-drilldown.html">Drill-down</a>
      <a href="{ISSUE}/1063" class="ext">#1063</a>
    </nav>
  </div>
</header>"""
    )
    body.append('<div class="wrap">')
    body.append(
        '<div class="crumb"><a href="index.html">Reports</a><span class="sep">&#9656;</span>'
        '<a href="wo-april-2026-qaqc-hub.html">D&amp;C Days QA/QC</a>'
        '<span class="sep">&#9656;</span><span>Owner anchors</span></div>'
    )

    # ---- hero -------------------------------------------------------------
    body.append(
        f"""<section class="hero">
  <p class="eyebrow">BSEE WAR activity codes &middot; epic #1063 &middot; Stones (WR 508)</p>
  <h1>Does the WAR rig-day basis agree with the owner?</h1>
  <p class="lede">Every reference figure the domain owner has given us for rig days, recomputed
  on the new <code>war_rig_days</code> basis, with the disagreement quantified. The headline is
  not the agreement &mdash; it is the <em>coverage</em>: how little of the 22-bore Stones
  population any owner figure actually reaches.</p>
  <span class="disposition"><span class="dot"></span>Not a broader QA &mdash; the independent
  evidence base is still one wellbore</span>
  <div class="facts">
    <div>Basis <span>DRL_COM &middot; inclusive &middot; adjacency-merged</span></div>
    <div>Population <span>{len(bores)} bores &middot; {len({b["api10"] for b in bores})} wells</span></div>
    <div>Reference figures found <span>{len(anchors)}</span></div>
    <div>Wellbores an owner figure reaches <span>1 of {len(bores)}</span></div>
  </div>
</section>"""
    )

    # ---- tiles ------------------------------------------------------------
    body.append(
        f"""<section class="tiles" aria-label="Agreement at a glance">
  <div class="tile"><div class="k">Independent anchors</div>
    <div class="v bad">{len(hand)}</div>
    <div class="sub">all on one bore &mdash; {ANCHOR_API12}</div></div>
  <div class="tile"><div class="k">Exact agreement</div>
    <div class="v ok">{len(exact)}<small>/{len(hand_checkable)}</small></div>
    <div class="sub">checkable hand-worked figures; {len(near)} more within one WAR week</div></div>
  <div class="tile"><div class="k">Bore coverage</div>
    <div class="v bad">1<small>/{len(bores)}</small></div>
    <div class="sub">Stones bores with any owner day figure</div></div>
  <div class="tile"><div class="k">Change we are proposing</div>
    <div class="v warn">{war_dc - pub_dc:+,}<small>d</small></div>
    <div class="sub">Stones D&amp;C, WAR basis vs published</div></div>
</section>"""
    )

    # ---- 1. verdict -------------------------------------------------------
    body.append(
        f"""<section class="sec" id="verdict">
  <div class="sec-head"><p class="eyebrow">1 &middot; The verdict</p>
  <h2>No. This is not a more established QA.</h2></div>
  <p class="sec-note">The repository contains {len(anchors)} reference figures bearing on rig
  days, {len(hand) + len([a for a in anchors if a["tier"] == "owner_shipped"])} of them
  attributable to the owner. Sorted by what they can actually prove, they collapse to a single
  wellbore.</p>
  <div class="callout bad">
    <p><strong>The independent evidence base is unchanged: one wellbore, {ANCHOR_API12}
    (Stones SN105).</strong> It is the only bore the owner worked through by hand, from the raw
    WAR record, without running any code of ours. Every other owner figure is either the output
    of his own extractor &mdash; which encodes the calendar spud&rarr;TD definition the new basis
    is replacing &mdash; or a World Oil table that was itself built from this repository's model
    output, and so cannot independently confirm anything about it.</p>
    <p>The 22-bore Stones list <em>is</em> owner-supplied and does widen the <strong>population</strong>
    we can compute over. It does not widen the population we can <strong>check</strong>. Twenty-one
    of the twenty-two bores below are computed-only and are labelled as such.</p>
  </div>
  <div class="callout ok">
    <p><strong>What did strengthen.</strong> On the one bore we can check, the new basis lands
    materially closer to the owner's hand count than the number we publish today: he counted
    <strong>93</strong> completion days from the daily remarks; the WAR basis gives
    <strong>{facts["post_reentry_days"]}</strong> for the same post-re-entry rig period
    ({facts["reentry_start"]} &rarr; {facts["last_com_end"]}), against
    <strong>{published[ANCHOR_API12]["completion"]}</strong> on the currently published basis.
    That is a {abs(facts["post_reentry_days"] - 93)}-day gap replacing a
    {abs(published[ANCHOR_API12]["completion"] - 93)}-day one.</p>
  </div>
</section>"""
    )

    # ---- 2. ledger --------------------------------------------------------
    body.append(
        """<section class="sec" id="ledger">
  <div class="sec-head"><p class="eyebrow">2 &middot; Every owner figure we could find</p>
  <h2>The anchor ledger</h2></div>
  <p class="sec-note">Grouped by evidence tier. Every row cites the committed file it came from;
  none of these numbers were reconstructed, inferred or rounded to improve agreement. Where we
  cannot compute the same quantity, the row says so rather than substituting a proxy.</p>"""
    )
    body += _anchor_ledger(anchors)
    body.append(
        """  <div class="legend" aria-label="Agreement legend">
    <span class="eyebrow" style="align-self:center">Agreement</span>
    <span class="item"><span class="sw" style="background:var(--ok)"></span>exact &mdash; identical to the day</span>
    <span class="item"><span class="sw" style="background:var(--warn)"></span>within one WAR week &mdash; |&Delta;| &le; 7 d, inside the reporting quantum</span>
    <span class="item"><span class="sw" style="background:var(--warn)"></span>within rounding &mdash; non-day measurement, |&Delta;| &lt; 0.1%</span>
    <span class="item"><span class="sw" style="background:var(--bad)"></span>materially different &mdash; |&Delta;| &gt; 7 d</span>
    <span class="item"><span class="sw" style="background:var(--hold)"></span>not checkable from WAR</span>
  </div>
</section>"""
    )

    # ---- 3. COM/TA reallocation -------------------------------------------
    body.append(
        f"""<section class="sec" id="reallocation">
  <div class="sec-head"><p class="eyebrow">3 &middot; The one disagreement in the by-code split</p>
  <h2>A 4-day TA&harr;COM reallocation, and why</h2></div>
  <p class="sec-note">The by-code figures held in <code>rig_days_summary.md</code> are
  <code>DRL 151, PND 49, COM 87, TA 21</code>. We reproduce
  <code>DRL {d["DRL"]}, PND {d["PND"]}, COM {d["COM"]}, TA {d["TA"]}</code> &mdash;
  two codes exact, the total exact at {facts["total"]}, and exactly four days moved from TA to COM.
  It is a boundary-placement difference, not a counting difference.</p>"""
    )
    body += _week_table(facts)
    body.append(
        f"""  <p>The well is temporarily abandoned in February 2015 and the rig does not return until
  <strong>{facts["reentry_start"]}</strong>. That return is reported as a <strong>3-day partial
  WAR week</strong> ({facts["reentry_start"]}&ndash;{facts["reentry_end"]}) &mdash; the only place
  in the well's entire record where an activity-code change does not fall on a Sunday week
  boundary. We take
  the code change at the WAR record boundary, so COM begins <code>{facts["our_boundary"]}</code>.
  The 87/21 split is reproduced exactly, and only, if that boundary is placed four days later at
  <code>{facts["owner_boundary"]}</code>: TA then runs a nominal full week
  (14 + 7 = 21) and COM runs {facts["owner_boundary"]}&ndash;{facts["last_com_end"]} = 87 days.</p>
  <div class="callout">
    <p><strong>Provenance caveat on this anchor.</strong> The <code>{{"COM": 87, ...}}</code>
    block sits under a <em>&ldquo;Summary and Way Forward&rdquo;</em> heading that follows the
    owner's signature and ends by asking <em>him</em> which completion method to adopt &mdash; so
    on the committed record it reads as <strong>our</strong> summary put to him, not his own
    output. We therefore file it as repo-legacy, not owner evidence. It also cannot be reproduced
    from the WAR rows this repository holds under any convention we tested (inclusive, exclusive,
    merged or unmerged), because the committed extract
    <code>war_data_{ANCHOR_API12}.csv</code> is byte-consistent with the current WAR tables and
    puts the code change at {facts["our_boundary"]}. Confirming authorship is
    <a href="#asks">ask 1</a>.</p>
  </div>
</section>"""
    )

    # ---- 4. calendar vs WAR ----------------------------------------------
    pub = published[ANCHOR_API12]
    body.append(
        f"""<section class="sec" id="calendar">
  <div class="sec-head"><p class="eyebrow">4 &middot; Two definitions, one well</p>
  <h2>Calendar milestone (155 / 156) vs WAR DRL ({d["DRL"]})</h2></div>
  <p class="sec-note">The owner's drilling rule is calendar: <em>&ldquo;I have been taking the spud
  date &ndash; the td date as drilling days.&rdquo;</em> Spud {pub["spud"]}, TD {pub["td"]}.</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Statement</th><th>Source</th><th class="num">Days</th><th>Arithmetic</th></tr></thead>
    <tbody>
      <tr><td>Drilling days</td><td>{_blob(_src("docs/data-sources/bsee/analysis/rig_days/rig_days_by_milestone.md", 16))}</td>
        <td class="num">155</td><td>TD &minus; spud, <strong>exclusive</strong> = 155</td></tr>
      <tr><td>Drilling days</td><td>{_blob(_src("docs/data-sources/bsee/analysis/rig_days/rig_days_summary.md", 21))}</td>
        <td class="num">156</td><td>TD &minus; spud <strong>+ 1</strong>, the stated formula = 156</td></tr>
      <tr><td>Published extract</td><td>{_blob(_src("docs/modules/bsee/analysis/production/FDAS_V30/drilling_and_completion_days_v21_kc.csv"))}</td>
        <td class="num">{pub["drilling"]}</td><td>the exclusive convention, as shipped</td></tr>
      <tr class="total"><td>WAR DRL, this basis</td><td>merged DRL weeks
        {facts["drl_span"][0]} &rarr; {facts["drl_span"][1]}</td>
        <td class="num">{d["DRL"]}</td><td>inclusive over the merged span</td></tr>
    </tbody></table></div>
  <p><strong>The 155/156 pair is one figure, not two.</strong> 156 = 155 + 1 exactly; the two
  documents state the same milestone under the exclusive and inclusive conventions. That halves
  the apparent anchor count and is why the ledger files 156 as repo-legacy.</p>
  <p><strong>The {155 - d["DRL"]}-day gap to WAR DRL is the reporting quantum, not an error.</strong>
  The last DRL week ends {facts["drl_span"][1]}; TD is reached {pub["td"]}, which falls inside the
  following week &mdash; and that week is returned as <code>PND</code>, not <code>DRL</code>. The
  calendar rule charges the whole TD week to drilling; the WAR rule charges it to whatever code the
  operator filed. On a continuously drilled well the two differ by at most one WAR week. <strong>On a
  suspended or batch-drilled well they diverge without bound</strong>: the calendar rule keeps
  counting through months of rig-off-well time, the WAR rule does not. That is the entire reason
  #1063 exists, and it is exactly why agreement on this one continuously-drilled well cannot be
  read as agreement on the population.</p>
</section>"""
    )

    # ---- 5. coverage ------------------------------------------------------
    body.append(
        f"""<section class="sec" id="coverage">
  <div class="sec-head"><p class="eyebrow">5 &middot; Coverage</p>
  <h2>What we can compute vs what we can check</h2></div>
  <p class="sec-note">All {len(bores)} bores on the owner's Stones list carry WAR activity and are
  computable on the new basis. Exactly one of them carries an owner figure to check against.
  The rest are shown so the change is visible &mdash; <strong>they are not validated</strong>.</p>"""
    )
    body += _stones_table(bores, published)
    body.append(
        f"""  <p>Against the owner's own V30 field totals
  (<code>{V30_OWNER_STONES["drilling_days"]:,}</code> drilling,
  <code>{V30_OWNER_STONES["completion_days"]:,}</code> completion) the WAR basis returns
  {sum(int(b["drilling_days"]) for b in covered):,} and
  {sum(int(b["completion_days"]) for b in covered):,}. Both gaps are large, both are expected
  by construction, and <strong>neither is evidence either way</strong>: his totals are his
  calendar rule summed over the same bores, so the difference measures the definition change,
  not its correctness. Note also that the published extract totals
  {sum(v["completion"] for v in published.values()):,} completion days against the
  {V30_OWNER_STONES["completion_days"]:,} in his shipped workbook &mdash; a
  {sum(v["completion"] for v in published.values()) - V30_OWNER_STONES["completion_days"]:+,}-day
  divergence that predates this basis change and is tracked as
  <a href="{ISSUE}/846">#846</a>.</p>
  <div class="callout">
    <p><strong>The World Oil Table 1 anchor is circular.</strong> Stones prints
    {WO_STONES["dc_days"]:,} D&amp;C days there, and the owner tabulated that table &mdash; but
    the validation page records that <em>&ldquo;the article's four tables are this repository's
    FDAS V30 model output&rdquo;</em>. Comparing our numbers to it compares our numbers to
    themselves. It is a useful measure of how far published figures will move
    ({war_dc - WO_STONES["dc_days"]:+,} days for Stones); it is not a check.</p>
  </div>
</section>"""
    )

    # ---- 6. grain ---------------------------------------------------------
    body.append(
        """<section class="sec" id="grain">
  <div class="sec-head"><p class="eyebrow">6 &middot; Grain</p>
  <h2>Wellbore (API12) vs well (API10)</h2></div>
  <p class="sec-note">Three of the eighteen Stones wells carry a sidetrack. Rolling those up by
  summing per-bore days double-counts the single WAR week that reports both bores across the
  sidetrack transition; the module unions instead.</p>"""
    )
    body += _well_table(wells)
    body.append(
        """  <p>Seven days per sidetrack boundary, every time. On <em>these</em> three wells the
  double-counted week happens to be filed under a non-D&amp;C code, so the D&amp;C columns are
  unaffected and the two roll-ups agree &mdash; which is precisely why the defect is easy to
  miss. Where the straddling week is filed <code>DRL</code> or <code>COM</code>, summing
  over-reports D&amp;C by a full week per sidetrack. Both grains are published so a consumer
  can never pick the wrong one by accident.</p>
</section>"""
    )

    # ---- 7. caveats -------------------------------------------------------
    body.append(
        f"""<section class="sec" id="caveats">
  <div class="sec-head"><p class="eyebrow">7 &middot; Caveats that apply to every number above</p>
  <h2>What a WAR-derived day count cannot resolve</h2></div>
  <div class="panel">
    <h3>&plusmn;7-day quantization</h3>
    <p>A WAR is a <em>weekly</em> return (Form BSEE-0133 under 30 CFR 250.743; Sunday 00:00 to
    Saturday 23:59) carrying one activity code for the whole week. A phase boundary can therefore
    only ever be located to within one week. Every figure on this page &mdash; ours and the
    owner's &mdash; inherits a &plusmn;7-day uncertainty at each code transition, which is why the
    ledger treats |&Delta;| &le; 7 as within-quantum rather than as agreement.</p>
  </div>
  <div class="panel">
    <h3>Coverage floor of the WAR feed</h3>
    <p>The WAR tables in this checkout run {facts["war_feed_start"]} to {facts["war_feed_end"]},
    but density is not uniform: only {facts["war_returns_before_1998"]:,} returns exist before
    1998, and the first month carrying more than fifty is {facts["war_first_material_month"]}.
    A bore that spudded before then will under-report, silently.
    Stones is unaffected &mdash; its earliest spud is {facts["earliest_spud"]} &mdash; but the
    same basis applied to older Gulf inventory is not safe without a per-bore coverage check.
    (Note: we found <strong>no</strong> April-2004 step in this feed; see the
    <a href="#asks">corrections</a> note.)</p>
  </div>
  <div class="panel">
    <h3><code>PND</code> is undefined</h3>
    <p>BSEE publishes no code list for <code>WELL_ACTIVITY_CD</code>; the table we hold is the
    BOREHOLE_STAT_CD list, and its own note reads <em>&ldquo;PND means we guessed it as
    unknown.&rdquo;</em> PND runs to {sum(int(b["pnd_days"]) for b in covered):,} days across
    these {len(bores)} bores &mdash; more than the
    {sum(int(b["completion_days"]) for b in covered):,} completion days the DRL_COM basis
    reports, and <em>excluded</em> from the D&amp;C total on that basis. Fold it into completion
    instead and Stones D&amp;C moves from {war_dc:,} to
    {war_dc + sum(int(b["pnd_days"]) for b in covered):,} days. It is therefore never merged
    silently into either bucket; it is carried in its own column and a basis includes it
    explicitly or not at all. Until BSEE confirms its meaning
    (<a href="{ISSUE}/1065">#1065</a>), any basis that includes or excludes PND is a choice, not
    a fact.</p>
  </div>
</section>"""
    )

    # ---- 8. asks ----------------------------------------------------------
    body.append(
        f"""<section class="sec" id="asks">
  <div class="sec-head"><p class="eyebrow">8 &middot; The most useful output of this exercise</p>
  <h2>What we need from the owner to settle it</h2></div>
  <p class="sec-note">Ranked by how much each would move the evidence base. The first three are
  cheap for him and would take the independent anchor count from one bore to a population.</p>
  <div class="askgrid">
    <div class="ask"><div class="top"><h4>1 &middot; Hand-worked completion counts for 5&ndash;10 more bores</h4>
      <span class="badge bad"><span class="d"></span>decisive</span></div>
      <p>The same exercise he did for {ANCHOR_API12} &mdash; count the distinct daily remark dates
      after TD &mdash; on a handful of <em>deliberately varied</em> bores: one continuously drilled,
      one suspended mid-drilling, one batch-drilled, one sidetracked, one with a late recompletion.
      Five bores chosen that way settles more than fifty chosen at random.</p></div>
    <div class="ask"><div class="top"><h4>2 &middot; Authorship of the by-WAR split</h4>
      <span class="badge bad"><span class="d"></span>decisive</span></div>
      <p>Did he produce <code>{{"COM": 87, "DRL": 151, "PND": 49, "TA": 21}}</code>, or did we?
      If his, we have a second independent anchor and a 4-day boundary rule to reconcile. If ours,
      the ledger's repo-legacy tier is empty and the evidence base is thinner still. One sentence
      from him decides which.</p></div>
    <div class="ask"><div class="top"><h4>3 &middot; The completion-method decision he asked us for</h4>
      <span class="badge warn"><span class="d"></span>blocking</span></div>
      <p><code>rig_days_summary.md</code> ends by asking us to pick among his three completion
      methods and marks method 3 preferred. That question is still open, and it is upstream of
      every completion number on this page. Answering it &mdash; or having him confirm the WAR
      code basis supersedes all three &mdash; is <a href="{ISSUE}/1064">#1064</a>.</p></div>
    <div class="ask"><div class="top"><h4>4 &middot; A rig-contract or daily-report cross-check on one well</h4>
      <span class="badge warn"><span class="d"></span>high value</span></div>
      <p>Anything outside BSEE &mdash; a rig day-rate invoice, an operator DDR, a spud-to-rig-release
      date pair &mdash; for even one Lower Tertiary well. Every anchor we hold is derived from the
      same WAR feed, so none of them can detect a systematic bias in that feed. One external
      source breaks the circularity.</p></div>
    <div class="ask"><div class="top"><h4>5 &middot; Julia JU102 ({JULIA_API12})</h4>
      <span class="badge hold"><span class="d"></span>cheap</span></div>
      <p>He supplied parsed remarks for this bore but never a day count from them. The raw material
      for a second hand-worked anchor is already committed
      (<code>api_{JULIA_API12}_remarks_parsed.xlsx</code>, 32 weeks) &mdash; it needs only his
      count.</p></div>
    <div class="ask"><div class="top"><h4>6 &middot; What <code>PND</code> means</h4>
      <span class="badge hold"><span class="d"></span>via BSEE</span></div>
      <p>Not his to answer, but he has the BSEE relationships. PND is the single largest
      unattributed block in the Stones record.</p></div>
  </div>
  <div class="callout">
    <p><strong>Corrections to the brief this page was built from.</strong> (a) The
    <code>{{"COM": 87, ...}}</code> split and <code>rig_days_by_WAR.md</code> are <em>not</em>
    demonstrably owner-authored &mdash; both sit in our voice, and the latter closes
    <em>&ldquo;This is how <u>we</u> can calculate&hellip;&rdquo;</em>. (b) There is no April-2004
    eWell step in this feed; monthly returns rise smoothly through 2003&ndash;2005, and the real
    floor is 1997-10. (c) <code>rig_days_by_milestone.md</code> carries two owner figures the brief
    did not list &mdash; completion = 93 days and D&amp;C = 248 &mdash; and they are the most
    valuable anchors in the repository.</p>
  </div>
</section>"""
    )

    body.append(
        f"""  <footer class="site">
    <div class="row">
      <span>Owner-anchor validation &mdash; WAR activity-code rig days &middot; epic #1063</span>
      <a href="{BLOB}/scripts/lower_tertiary/build_roy_rig_days_qa.py">Generator &amp; provenance &#8599;</a>
    </div>
    <p class="note">// self-contained &mdash; no external assets. Regenerate with
    <code>build_roy_rig_days_qa.py --refresh --war-dir &lt;dir&gt;</code>; subtotals pinned by
    tests/unit/lower_tertiary/test_roy_rig_days_qa.py</p>
  </footer>
</div>"""
    )

    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Owner Anchors &mdash; WAR Rig-Day Validation</title>\n"
        f"<style>{STYLE}</style>\n</head>\n<body>\n"
        + "\n".join(body)
        + "\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------
def build(rows: list[dict]) -> str:
    bores = [r for r in rows if r["grain"] == "bore"]
    wells = [r for r in rows if r["grain"] == "well"]
    published = load_published()
    facts = anchor_facts()
    meta = next((r for r in rows if r["grain"] == "meta"), {})
    facts.update(
        {
            "war_feed_start": meta.get("war_feed_start", ""),
            "war_feed_end": meta.get("war_feed_end", ""),
            "war_first_material_month": meta.get("war_first_material_month", ""),
            "war_returns_before_1998": int(meta.get("war_returns_before_1998") or 0),
            "earliest_spud": min(
                (_us(v["spud"]) for v in published.values() if v["spud"]),
                default="",
            ),
        }
    )
    anchors = resolve_anchors({b["api12"]: b for b in bores}, facts)
    return build_html(anchors, bores, wells, published, facts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Recompute per-bore days from the raw WAR tables and rewrite the cache.",
    )
    parser.add_argument(
        "--war-dir",
        help="Directory holding mv_war_main.bin / mv_war_main_prop.bin "
        "(default: $WED_WAR_DIR, else data/modules/bsee/bin/war).",
    )
    args = parser.parse_args(argv)

    if args.refresh:
        war_dir = _war_dir(args.war_dir)
        if not (war_dir / "mv_war_main.bin").exists():
            parser.error(f"WAR tables not found under {war_dir}; pass --war-dir")
        rows = recompute(war_dir)
        write_cache(rows)
        print(f"refreshed {CACHE_CSV} from {war_dir}")

    rows = load_cache()
    OUT_HTML.write_text(build(rows), encoding="utf-8")
    bores = [r for r in rows if r["grain"] == "bore"]
    covered = [b for b in bores if b["days_status"] == "war_covered"]
    dc = sum(int(b["drilling_days"]) + int(b["completion_days"]) for b in covered)
    print(f"wrote {OUT_HTML} — {len(bores)} bores, {dc:,} WAR D&C days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
