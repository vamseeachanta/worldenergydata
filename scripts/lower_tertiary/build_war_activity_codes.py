#!/usr/bin/env python3
"""Build the published definitions page for BSEE WAR ``WELL_ACTIVITY_CD``.

The page exists to be *sent as a link*.  A cold reader must be able to see, in
one screen, three things that this repository has repeatedly conflated:

``published``
    What BSEE itself publishes.  Exactly one relevant domain is published --
    ``BOREHOLE_STAT_CD`` -- and it is a *borehole status* list, not an activity
    list.

``reuse_inferred``
    Six ``WELL_ACTIVITY_CD`` tokens coincide with published
    ``BOREHOLE_STAT_CD`` tokens.  That the WAR field reuses them with the same
    meaning is **our inference**, corroborated by remark text.  BSEE has never
    said so.  Every such row on the page says so, on the row.

``unknown``
    BSEE publishes nothing.  These rows render **no meaning at all** -- only the
    observed evidence and what would settle it.  ``PND`` is one of them, and the
    page must never imply it means "pending": that gloss is precisely the
    unsourced reading that #1065 exists to retire.

The headline, which the page leads with, is a *negative* result: BSEE publishes
no ``WELL_ACTIVITY_CD`` domain at all, so zero of the twelve observed codes has
a published definition *for this field*.  A negative result is only worth
anything if it is auditable, so the surfaces checked (``meta.searched`` in the
definitions YAML) are rendered in full with their URLs and outcomes.

Two inputs, both canonical, neither duplicated here:

``war_activity_codes.yml``
    The single definition source (issue #1065).  Resolved from ``--yaml``, then
    ``$WED_WAR_CODES_YAML``, then the package location, then a development
    scratchpad copy.  This generator never writes it and never second-guesses
    it; it refuses to render a meaning for any ``unknown`` row.

``war_activity_code_frequency.csv``
    Observed frequency per code, recomputed from the raw WAR tables with
    ``--refresh --war-dir`` (~370 MB, not committed) and cached in
    ``reports/lower_tertiary/data/``.  The default path -- and every test --
    reads that committed cache and needs no pandas.

Deterministic output (no timestamps).
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]

#: Canonical definitions artifact, in the package tree (#1065).
PACKAGE_YAML = (
    REPO
    / "packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data"
    / "war_activity_codes.yml"
)
#: Development fallback only -- lets this generator be worked on before the
#: definitions artifact lands in the package tree.  Never used in CI.
SCRATCH_YAML = Path(
    "/tmp/claude-1000/-mnt-local-analysis"
    "/8039d273-5c09-4441-a95a-d38206061b75/scratchpad/war_activity_codes.yml"
)

FREQ_CSV = REPO / "reports/lower_tertiary/data/war_activity_code_frequency.csv"
OUT_HTML = REPO / "reports/lower_tertiary/war-activity-codes.html"

BLOB = "https://github.com/vamseeachanta/worldenergydata/blob/main"
ISSUE = "https://github.com/vamseeachanta/worldenergydata/issues"

#: Path the page cites for the definitions artifact.  Deliberately *not* the
#: resolved path: the page is published from the package location regardless of
#: where a developer read the file from.
YAML_REPO_PATH = (
    "packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data"
    "/war_activity_codes.yml"
)
GENERATOR_REPO_PATH = "scripts/lower_tertiary/build_war_activity_codes.py"
TEST_REPO_PATH = "tests/unit/lower_tertiary/test_war_activity_codes.py"
FREQ_REPO_PATH = "reports/lower_tertiary/data/war_activity_code_frequency.csv"

BOREHOLE_URL = "https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields"

#: BSEE's published ``BOREHOLE_STAT_CDS`` domain, transcribed verbatim from
#: ``BOREHOLE_URL`` (retrieved 2026-07-28 during the #1065 investigation).
#: Frozen here rather than mirrored into the WAR definitions YAML because it is
#: a *different* field's domain -- keeping it out of that file is the whole
#: point.  ``check_published_labels`` asserts the six shared tokens still agree
#: with the YAML, so a drift on either side fails loudly.
BOREHOLE_STAT_CDS: list[tuple[str, str]] = [
    ("APD", "Application for permit to drill"),
    ("AST", "Approved Sidetrack"),
    ("BP", "Bypass"),
    (
        "CNL",
        "Borehole is cancelled. The request to drill the well is cancelled "
        "after the APD or sundry has been approved",
    ),
    ("COM", "Borehole Completed"),
    ("CT", "Core Test Well"),
    ("DRL", "Drilling Active"),
    ("DSI", "Drilling Suspended"),
    ("PA", "Permanently Abandoned"),
    ("ST", "Borehole Side Tracked"),
    ("TA", "Temporarily Abandoned"),
    ("VCW", "Volume Chamber Well"),
]

#: URLs for the surfaces ``meta.searched`` names without one.  Retrieved
#: 2026-07-28 in the same investigation; the YAML records the *outcome*, this
#: records where to go and check it.
SEARCHED_URLS = {
    "Form BSEE-0133 (Well Activity Report)": (
        "https://www.bsee.gov/sites/bsee.gov/files/form-0133-exp-2017.pdf"
    ),
    "30 CFR 250.743": (
        "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250"
        "/subpart-G/subject-group-ECFRa4d25de54b283e6/section-250.743"
    ),
    "ONRR Appendix H": "https://onrr.gov/document/MPRH-Appendix-H.pdf",
}

#: The one string a row is allowed to carry in place of a meaning.
NO_MEANING = "no meaning published"

TIER_ORDER = ["published_other_domain", "unknown"]
TIER_CLASS = {"published_other_domain": "t-inf", "unknown": "t-unk"}
TIER_TITLE = {
    "published_other_domain": "Reuse inferred — the token is published, but for "
    "a different field",
    "unknown": "Unknown — BSEE publishes nothing, so this page shows no meaning",
}
TIER_RULE = {
    "published_other_domain": "BSEE defines these six tokens for "
    "BOREHOLE_STAT_CD. That WELL_ACTIVITY_CD reuses them with the same meaning "
    "is our reading of the evidence, not a BSEE statement.",
    "unknown": "No BSEE domain contains these tokens. The meaning column is "
    "empty by design — filling it in is what created #1065.",
}


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
def resolve_yaml(explicit: str | None = None) -> Path | None:
    """Locate the definitions artifact, or ``None`` if it is not available.

    An explicitly requested path (argument or environment) is honoured
    strictly: if it is missing the caller is told so, rather than being handed
    a different file that happens to exist and shipping a page built from it.
    """
    asked = explicit or os.environ.get("WED_WAR_CODES_YAML")
    if asked:
        path = Path(asked)
        return path if path.exists() else None
    for candidate in (PACKAGE_YAML, SCRATCH_YAML):
        if candidate.exists():
            return candidate
    return None


def load_codes(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    check_published_labels(doc)
    assert_no_meaning_for_unknown(doc)
    return doc


def yaml_lines(path: Path) -> dict[str, int]:
    """Line number of each ``- code:`` entry, for real source permalinks."""
    lines: dict[str, int] = {}
    for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.match(r"\s*-\s+code:\s*(\S+)\s*$", text)
        if match:
            token = match.group(1)
            lines[_key(None if token == "null" else token)] = number
    return lines


def _key(code: str | None) -> str:
    return code if code else "(blank)"


# ---------------------------------------------------------------------------
# The guarantee this page exists to make
# ---------------------------------------------------------------------------
def assert_no_meaning_for_unknown(doc: dict) -> None:
    """An ``unknown`` row may not carry a label. Fail the build, not the reader.

    The whole point of the page is that an undocumented code renders with no
    meaning attached.  If a label ever appears on an ``unknown`` row -- the way
    ``PND | PENDING/UNKNOWN`` once did -- generation stops here rather than
    quietly publishing a guess as a definition.
    """
    for entry in doc["codes"]:
        if entry["provenance"] == "unknown" and entry.get("label") is not None:
            raise ValueError(
                f"{_key(entry['code'])} is provenance=unknown but carries "
                f"label {entry['label']!r}; refusing to publish a meaning for "
                "an undocumented code (see #1065)"
            )


def check_published_labels(doc: dict) -> None:
    """The six reused tokens must still match BSEE's published wording."""
    published = dict(BOREHOLE_STAT_CDS)
    for entry in doc["codes"]:
        if entry["provenance"] != "published_other_domain":
            continue
        expected = published.get(entry["code"])
        if entry["label"] != expected:
            raise ValueError(
                f"{entry['code']}: YAML label {entry['label']!r} no longer "
                f"matches BSEE's published BOREHOLE_STAT_CD wording {expected!r}"
            )


def meaning_cell(entry: dict) -> str:
    """Render the meaning column for one code row.

    Published-elsewhere rows show BSEE's own wording, marked as belonging to
    the other field.  Unknown rows show a hatched, empty cell -- never a gloss,
    never an inference, never a plausible-looking guess.
    """
    if entry["provenance"] == "unknown":
        return '<span class="badge hold"><span class="d"></span>' f"{NO_MEANING}</span>"
    return (
        f'<span class="lbl">{_e(entry["label"])}</span>'
        '<span class="forfield">BSEE wording, for <code>BOREHOLE_STAT_CD</code></span>'
    )


# ---------------------------------------------------------------------------
# Frequency (needs the raw WAR tables)
# ---------------------------------------------------------------------------
FREQ_COLUMNS = ["code", "rows", "pct", "wellbores", "first_war_year", "last_war_year"]


def _war_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("WED_WAR_DIR")
    if env:
        return Path(env)
    return REPO / "data/modules/bsee/bin/war"


def recompute_frequency(war_dir: Path) -> list[dict]:
    """Observed frequency of each ``WELL_ACTIVITY_CD`` value, corpus-wide."""
    import pandas as pd  # local: the default path never needs it

    main = pd.read_pickle(war_dir / "mv_war_main.bin")
    prop = pd.read_pickle(war_dir / "mv_war_main_prop.bin")
    joined = prop.merge(
        main[["SN_WAR", "API_WELL_NUMBER", "WAR_START_DT"]], on="SN_WAR", how="left"
    )
    joined["api"] = joined["API_WELL_NUMBER"].astype(str).str.strip()
    joined["year"] = pd.to_datetime(
        joined["WAR_START_DT"], errors="coerce", format="mixed"
    ).dt.year
    joined["code"] = joined["WELL_ACTIVITY_CD"].fillna("(blank)")

    total = len(joined)
    rows: list[dict] = []
    for code, group in joined.groupby("code"):
        rows.append(
            {
                "code": code,
                "rows": len(group),
                "pct": f"{100 * len(group) / total:.2f}",
                "wellbores": int(group["api"].nunique()),
                "first_war_year": int(group["year"].min()),
                "last_war_year": int(group["year"].max()),
            }
        )
    rows.sort(key=lambda r: -r["rows"])
    rows.append(
        {
            "code": "(all rows)",
            "rows": total,
            "pct": "100.00",
            "wellbores": int(joined["api"].nunique()),
            "first_war_year": int(joined["year"].min()),
            "last_war_year": int(joined["year"].max()),
        }
    )
    return rows


def write_frequency(rows: list[dict]) -> None:
    FREQ_CSV.parent.mkdir(parents=True, exist_ok=True)
    with FREQ_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FREQ_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row[c] for c in FREQ_COLUMNS})


def load_frequency() -> dict[str, dict]:
    with FREQ_CSV.open(encoding="utf-8") as fh:
        return {r["code"]: r for r in csv.DictReader(fh)}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def _e(text) -> str:
    return html.escape(str(text), quote=True)


def _blob(path: str, line: int | None = None, label: str | None = None) -> str:
    frag = f"#L{line}" if line else ""
    shown = label or (path.split("/")[-1] + (f":{line}" if line else ""))
    return f'<a href="{BLOB}/{path}{frag}"><code>{_e(shown)}</code></a>'


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
  .hero .lede { font-size: 1.14rem; color: var(--ink-soft); max-width: 64ch; margin: 0 0 20px; }
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
  .tile .v.hold { color: var(--hold); }

  .sec { margin: 46px 0 0; scroll-margin-top: 76px; }
  .sec-head h2 { font-size: 1.5rem; letter-spacing: -.02em; margin: 6px 0 4px; }
  .sec-note { font-size: .92rem; color: var(--ink-soft); max-width: 74ch; margin: 0 0 20px; }
  .sec p { font-size: .94rem; color: var(--ink-soft); max-width: 74ch; }
  .sec p strong, .sec li strong { color: var(--ink); }

  .panel {
    background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
    padding: 20px 22px; box-shadow: var(--shadow); margin: 18px 0;
  }
  .panel h3 { margin: 0 0 6px; font-size: 1.05rem; letter-spacing: -.01em; }
  .panel p { margin: 6px 0 0; font-size: .9rem; color: var(--ink-soft); max-width: 74ch; }
  .panel ul { margin: 8px 0 0; padding-left: 18px; }
  .panel li { font-size: .9rem; color: var(--ink-soft); margin-bottom: 6px; }

  /* --- the three provenance tiers ------------------------------------- */
  .tierkey { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 8px 0 8px; }
  .tk { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px 18px; box-shadow: var(--shadow); position: relative; overflow: hidden; }
  .tk::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 5px; }
  .tk.pub::before { background: var(--accent); }
  .tk.inf::before { background: repeating-linear-gradient(180deg, var(--warn) 0 6px, transparent 6px 10px); }
  .tk.unk::before { background: repeating-linear-gradient(180deg, var(--hold) 0 3px, transparent 3px 9px); opacity: .8; }
  .tk.unk { background: var(--surface-2); border-style: dashed; }
  .tk h4 { margin: 0 0 4px; font-size: .98rem; letter-spacing: -.01em; }
  .tk .n { font-family: var(--mono); font-size: 1.5rem; font-weight: 700; letter-spacing: -.02em; }
  .tk.pub .n { color: var(--accent); } .tk.inf .n { color: var(--warn); } .tk.unk .n { color: var(--hold); }
  .tk p { margin: 6px 0 0; font-size: .84rem; color: var(--ink-soft); }

  .tablewrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); box-shadow: var(--shadow); margin: 16px 0; }
  table { border-collapse: collapse; width: 100%; font-size: .86rem; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { font-family: var(--mono); font-size: .68rem; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-faint); background: var(--surface-2); white-space: nowrap; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; font-family: var(--mono); white-space: nowrap; }
  td.wrap-cell { min-width: 26ch; color: var(--ink-soft); font-size: .82rem; }
  td.code { white-space: nowrap; font-family: var(--mono); font-weight: 700; }
  tbody tr:last-child td { border-bottom: none; }
  code { font-family: var(--mono); font-size: .84em; }

  tr.tierhead td { background: var(--surface-2); padding: 12px; }
  tr.tierhead .th-t { font-family: var(--mono); font-size: .7rem; letter-spacing: .1em; text-transform: uppercase; font-weight: 700; }
  tr.tierhead .th-r { font-size: .82rem; color: var(--ink-soft); margin-top: 2px; max-width: 92ch; }
  tr.t-pub .th-t, tr.t-pub td.code { color: var(--accent-strong); }
  tr.t-inf .th-t { color: var(--warn); }
  tr.t-unk .th-t { color: var(--hold); }

  tr.t-pub td:first-child { border-left: 4px solid var(--accent); }
  tr.t-inf td:first-child { border-left: 4px dashed var(--warn); }
  tr.t-unk td:first-child { border-left: 4px dotted var(--hold); }
  tr.t-unk { background: color-mix(in srgb, var(--hold-wash) 55%, transparent); }
  tr.t-unk td.meaning {
    background: repeating-linear-gradient(45deg,
      transparent 0 6px,
      color-mix(in srgb, var(--hold) 14%, transparent) 6px 12px);
  }
  td.meaning .lbl { font-weight: 600; color: var(--ink); }
  td.meaning .forfield { display: block; font-family: var(--mono); font-size: .68rem; color: var(--ink-faint); margin-top: 2px; }
  td.meaning { min-width: 20ch; }
  .never { display: block; font-size: .72rem; color: var(--ink-faint); margin-top: 4px; font-style: italic; }
  .settle { display: block; margin-top: 6px; font-family: var(--mono); font-size: .72rem; color: var(--accent-strong); }
  .settle.none { color: var(--ink-faint); font-style: italic; }

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
  .callout.hold { border-left-color: var(--hold); background: var(--hold-wash); }
  .callout p { margin: 0; font-size: .9rem; color: var(--ink); max-width: none; }
  .callout p + p { margin-top: 8px; }

  .inference-box {
    border: 2px dashed color-mix(in srgb, var(--bad) 45%, transparent);
    background: var(--bad-wash); border-radius: var(--radius);
    padding: 16px 18px; margin: 18px 0;
  }
  .inference-box .stamp {
    font-family: var(--mono); font-size: .68rem; letter-spacing: .12em;
    text-transform: uppercase; font-weight: 700; color: var(--bad);
    display: inline-flex; align-items: center; gap: 8px;
  }
  .inference-box p { margin: 8px 0 0; font-size: .9rem; color: var(--ink); max-width: none; }

  .legend { display: flex; flex-wrap: wrap; gap: 10px 18px; margin: 22px 0 0; padding: 16px 18px; background: var(--surface-2); border: 1px solid var(--line); border-radius: 12px; }
  .legend .item { display: flex; align-items: center; gap: 8px; font-size: .82rem; color: var(--ink-soft); }
  .legend .sw { width: 10px; height: 10px; border-radius: 3px; }
  .legend .sw.hatch { background: repeating-linear-gradient(45deg, transparent 0 3px, var(--hold) 3px 6px); border: 1px solid var(--hold); }

  footer.site { margin: 56px 0 40px; padding-top: 24px; border-top: 1px solid var(--line); color: var(--ink-soft); font-size: .84rem; }
  footer.site .row { display: flex; flex-wrap: wrap; gap: 6px 20px; align-items: center; justify-content: space-between; }
  footer.site a { color: var(--accent); text-decoration: none; }
  footer.site a:hover { text-decoration: underline; }
  .note { margin-top: 14px; font-size: .78rem; color: var(--ink-faint); font-family: var(--mono); }

  @media (max-width: 900px) { .tiles { grid-template-columns: repeat(2, 1fr); } .tierkey { grid-template-columns: 1fr; } }
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


def _searched_table(meta: dict) -> list[str]:
    out = [
        '<div class="tablewrap"><table>',
        "<thead><tr><th>Surface checked</th><th>What it turned out to be</th>"
        "<th>Go and check</th></tr></thead><tbody>",
    ]
    for item in meta["searched"]:
        url = item.get("url") or SEARCHED_URLS.get(item["name"], "")
        link = (
            f'<a href="{_e(url)}">open &#8599;</a>'
            if url
            else '<span style="color:var(--ink-faint)">&mdash;</span>'
        )
        out.append(
            "<tr>"
            f"<td><strong>{_e(item['name'])}</strong></td>"
            f'<td class="wrap-cell">{_e(item["result"])}</td>'
            f"<td>{link}</td></tr>"
        )
    out.append(
        f'<tr><td colspan="3" style="background:var(--bad-wash);color:var(--bad);'
        f'font-weight:600">Result on every surface: no <code>WELL_ACTIVITY_CD</code> '
        f"domain. {len(meta['searched'])} of {len(meta['searched'])} negative."
        "</td></tr>"
    )
    out.append("</tbody></table></div>")
    return out


def _borehole_table(observed: set[str]) -> list[str]:
    out = [
        '<div class="tablewrap"><table>',
        "<thead><tr><th>Code</th><th>BSEE's definition, verbatim</th>"
        "<th>Appears in WAR?</th></tr></thead><tbody>",
    ]
    for code, definition in BOREHOLE_STAT_CDS:
        seen = code in observed
        mark = (
            '<span class="badge warn"><span class="d"></span>yes &mdash; reuse inferred</span>'
            if seen
            else '<span class="badge hold"><span class="d"></span>never</span>'
        )
        out.append(
            f'<tr class="t-pub"><td class="code">{_e(code)}</td>'
            f'<td class="wrap-cell" style="color:var(--ink)">{_e(definition)}</td>'
            f"<td>{mark}</td></tr>"
        )
    out.append("</tbody></table></div>")
    return out


def _code_rows(entry: dict, freq: dict, lines: dict[str, int], asked: set[str]) -> str:
    key = _key(entry["code"])
    row = freq.get(key, {})
    tier = entry["provenance"]
    shown = f"<code>{_e(key)}</code>" if entry["code"] else f"<em>{_e(key)}</em>"
    source = (
        f'<a href="{BOREHOLE_URL}">boreholeFields &#8599;</a><br>'
        if tier == "published_other_domain"
        else '<span style="color:var(--ink-faint)">no BSEE source</span><br>'
    )
    source += _blob(
        YAML_REPO_PATH, lines.get(key), f"war_activity_codes.yml:{lines.get(key, '')}"
    )
    evidence = _e(entry["evidence"]) if entry.get("evidence") else ""
    if tier == "unknown":
        settles = (
            ("settle", '<a href="#ask">BSEE TDM would settle it &#8595;</a>')
            if entry["code"] in asked
            else ("settle none", "no token was filed &mdash; nothing to define")
        )
        evidence = (evidence + " " if evidence else "") + (
            f'<span class="{settles[0]}">{settles[1]}</span>'
        )
    meaning = meaning_cell(entry)
    if tier == "unknown":
        meaning += '<span class="never">nothing published &mdash; nothing shown</span>'
    return (
        f'<tr class="{TIER_CLASS[tier]}">'
        f'<td class="code">{shown}</td>'
        f'<td class="meaning">{meaning}</td>'
        f'<td class="num">{int(row.get("rows", 0)):,}</td>'
        f'<td class="num">{_e(row.get("pct", ""))}%</td>'
        f'<td class="num">{int(row.get("wellbores", 0)):,}</td>'
        f'<td class="wrap-cell">{evidence}</td>'
        f"<td>{source}</td>"
        "</tr>"
    )


def _codes_table(doc: dict, freq: dict, lines: dict[str, int]) -> list[str]:
    asked = set(doc["outstanding_query"]["codes"])
    out = [
        '<div class="tablewrap"><table>',
        "<thead><tr><th>Code</th><th>Meaning for <code>WELL_ACTIVITY_CD</code></th>"
        '<th class="num">Rows</th><th class="num">% of rows</th>'
        '<th class="num">Wellbores</th><th>Observed evidence</th>'
        "<th>Source</th></tr></thead><tbody>",
    ]
    for tier in TIER_ORDER:
        group = [c for c in doc["codes"] if c["provenance"] == tier]
        group.sort(key=lambda c: -int(freq.get(_key(c["code"]), {}).get("rows", 0)))
        named = [c for c in group if c["code"]]
        count = f"{len(named)} codes"
        if len(named) != len(group):
            count += f" + {len(group) - len(named)} blank-code row"
        out.append(
            f'<tr class="tierhead {TIER_CLASS[tier]}"><td colspan="7">'
            f'<div class="th-t">{_e(TIER_TITLE[tier])} &middot; {count}</div>'
            f'<div class="th-r">{_e(TIER_RULE[tier])}</div></td></tr>'
        )
        for entry in group:
            out.append(_code_rows(entry, freq, lines, asked))
    out.append("</tbody></table></div>")
    return out


def _pnd_section(doc: dict, freq: dict, lines: dict[str, int]) -> str:
    pnd = next(c for c in doc["codes"] if c["code"] == "PND")
    row = freq["PND"]
    return f"""<section class="sec" id="pnd">
  <div class="sec-head"><p class="eyebrow">4 &middot; The one that moves published economics</p>
  <h2><code>PND</code> &mdash; everything we have, and no definition</h2></div>
  <p class="sec-note">PND is {_e(row["pct"])}% of all WAR wellbore-weeks and touches
  {int(row["wellbores"]):,} wellbores. It is the only undocumented code whose treatment
  changes numbers we publish, so it gets its own section &mdash; and that section still
  does not tell you what it means, because <strong>BSEE has not said</strong>.</p>

  <div class="panel">
    <h3>Observed evidence</h3>
    <p>{_e(pnd["evidence"])}</p>
  </div>
  <div class="panel">
    <h3>Why it matters to published numbers</h3>
    <p>{_e(pnd["impact"])}</p>
  </div>
  <div class="panel">
    <h3>How often it actually occurs</h3>
    <p>{_e(pnd["frequency_note"])}</p>
  </div>

  <div class="inference-box">
    <span class="stamp"><span class="badge bad"><span class="d"></span>inference</span>
    Not a definition &mdash; do not cite this as one</span>
    <p>{_e(pnd["inference"])}</p>
    <p><strong>This paragraph is the reading of engineers looking at remark text, rig
    names and depths.</strong> BSEE publishes no meaning for <code>PND</code>. Nothing in
    this box may be used as a definition, mirrored into a code table, or shipped as a
    label &mdash; that is exactly how <code>PND | PENDING/UNKNOWN</code> entered this
    repository with its uncertainty flag stripped off
    (<a href="{ISSUE}/1065">#1065</a>).</p>
  </div>

  <p>The row for <code>PND</code> in the table above therefore shows
  <em>{NO_MEANING}</em>, and it will keep showing that until
  <a href="#ask">BSEE answers</a>. Source of record:
  {_blob(YAML_REPO_PATH, lines.get("PND"), f"war_activity_codes.yml:{lines.get('PND', '')}")}.</p>
</section>"""


def build_html(doc: dict, freq: dict, lines: dict[str, int]) -> str:
    meta = doc["meta"]
    codes = doc["codes"]
    named = [c for c in codes if c["code"]]
    inferred = [c for c in codes if c["provenance"] == "published_other_domain"]
    unknown = [c for c in codes if c["provenance"] == "unknown"]
    #: The blank row is a *missing value*, not a code; it is counted separately
    #: everywhere so "6 + 6 = the twelve codes" always holds on the page.
    unknown_named = [c for c in unknown if c["code"]]
    observed = {c["code"] for c in codes if c["code"]}
    never_in_war = [c for c, _ in BOREHOLE_STAT_CDS if c not in observed]
    total_rows = int(freq["(all rows)"]["rows"])
    unknown_rows = sum(int(freq[c["code"]]["rows"]) for c in unknown_named)
    blank_rows = int(freq["(blank)"]["rows"])
    ask = doc["outstanding_query"]

    body: list[str] = []
    body.append(
        f"""<header class="site">
  <div class="wrap site-inner">
    <span class="wordmark">{GLYPH}AceEngineer</span>
    <nav class="capability" aria-label="WAR activity-code definitions navigation">
      <a href="#" class="active">Activity codes</a>
      <a href="wo-april-2026-qaqc-hub.html">QA/QC hub</a>
      <a href="roy-rig-days-validation.html">Basis</a>
      <a href="wo-april-2026-validation.html">Matrix</a>
      <a href="{ISSUE}/1065" class="ext">#1065</a>
      <a href="{BLOB}/{YAML_REPO_PATH}" class="ext">Definitions YAML</a>
    </nav>
  </div>
</header>"""
    )
    body.append('<div class="wrap">')
    body.append(
        '<div class="crumb"><a href="index.html">Reports</a><span class="sep">&#9656;</span>'
        '<a href="wo-april-2026-qaqc-hub.html">D&amp;C Days QA/QC</a>'
        '<span class="sep">&#9656;</span><span>WAR activity codes</span></div>'
    )

    # ---- hero -------------------------------------------------------------
    body.append(
        f"""<section class="hero">
  <p class="eyebrow">BSEE <code>WELL_ACTIVITY_CD</code> &middot; issue #1065 &middot;
  WAR vintage {_e(meta["data_vintage"])}</p>
  <h1>BSEE publishes no <code>WELL_ACTIVITY_CD</code> domain at all.</h1>
  <p class="lede">Every drilling-day number this repository publishes rests on a
  twelve-value activity code in BSEE's Well Activity Reports. <strong>Not one of those
  twelve values has a published definition for this field.</strong> This page states,
  code by code, what BSEE actually publishes, what we inferred, and what nobody knows
  &mdash; and links each claim to its source so you can check it rather than trust it.</p>
  <span class="disposition"><span class="dot"></span>0 of {len(named)} codes defined by
  BSEE for <code>WELL_ACTIVITY_CD</code></span>
  <div class="facts">
    <div>Field <span>{_e(meta["field"])}</span></div>
    <div>Table <span>{_e(meta["source_table"])}</span></div>
    <div>Rows <span>{total_rows:,}</span></div>
    <div>Surfaces checked <span>{len(meta["searched"])} &middot; all negative</span></div>
    <div>Retrieved <span>{_e(meta["retrieved"])}</span></div>
  </div>
</section>"""
    )

    # ---- tiles ------------------------------------------------------------
    body.append(
        f"""<section class="tiles" aria-label="Provenance at a glance">
  <div class="tile"><div class="k">Published for this field</div>
    <div class="v bad">0<small>/{len(named)}</small></div>
    <div class="sub">no BSEE domain exists for <code>WELL_ACTIVITY_CD</code></div></div>
  <div class="tile"><div class="k">Reuse inferred</div>
    <div class="v warn">{len(inferred)}</div>
    <div class="sub">published for <code>BOREHOLE_STAT_CD</code>; the reuse is ours</div></div>
  <div class="tile"><div class="k">Unknown</div>
    <div class="v hold">{len(unknown_named)}</div>
    <div class="sub">no meaning published, so none shown &mdash; plus {blank_rows:,} rows
    carrying no code at all</div></div>
  <div class="tile"><div class="k">Rows on an unknown code</div>
    <div class="v bad">{100 * unknown_rows / total_rows:.1f}<small>%</small></div>
    <div class="sub">{unknown_rows:,} of {total_rows:,} wellbore-weeks</div></div>
</section>"""
    )

    # ---- tier key ---------------------------------------------------------
    body.append(
        f"""<section class="sec" id="how-to-read">
  <div class="sec-head"><p class="eyebrow">How to read this page</p>
  <h2>Three tiers, and they are not interchangeable</h2></div>
  <p class="sec-note">Every statement on this page sits in exactly one of three tiers.
  The tier is carried by colour, by border style and by the words on the row &mdash; a
  reader who only skims should still never mistake an inference for a published fact.</p>
  <div class="tierkey">
    <div class="tk pub">
      <p class="eyebrow" style="color:var(--accent-strong)">Tier 1 &middot; solid teal</p>
      <h4>Published by BSEE</h4>
      <div class="n">{len(BOREHOLE_STAT_CDS)}</div>
      <p>BSEE's own words, for <code>BOREHOLE_STAT_CD</code>, quoted verbatim from its
      field-values page. This is the only definitional material BSEE publishes anywhere
      near this data.</p>
    </div>
    <div class="tk inf">
      <p class="eyebrow" style="color:var(--warn)">Tier 2 &middot; dashed amber</p>
      <h4>Reuse inferred</h4>
      <div class="n">{len(inferred)}</div>
      <p>The token is published &mdash; for a different field. Reading it the same way in
      <code>WELL_ACTIVITY_CD</code> is <strong>our inference</strong>, corroborated by
      remark text and shown on every row. BSEE has never confirmed it.</p>
    </div>
    <div class="tk unk">
      <p class="eyebrow" style="color:var(--hold)">Tier 3 &middot; dotted grey, hatched</p>
      <h4>Unknown</h4>
      <div class="n">{len(unknown_named)}</div>
      <p>BSEE publishes nothing. The meaning cell is hatched and empty on purpose. You get
      the observed evidence and what would settle it &mdash; never a guess dressed as a
      definition. A thirteenth row covers the {blank_rows:,} wellbore-weeks that carry no
      code at all.</p>
    </div>
  </div>
</section>"""
    )

    # ---- 1. the negative result -------------------------------------------
    body.append(
        f"""<section class="sec" id="negative">
  <div class="sec-head"><p class="eyebrow">1 &middot; The headline, made auditable</p>
  <h2>Where we looked for a published domain, and what we found</h2></div>
  <p class="sec-note">&ldquo;BSEE publishes nothing&rdquo; is a claim about absence, and
  absence is only credible if you can see where somebody looked. These are the
  {len(meta["searched"])} surfaces checked on {_e(meta["retrieved"])}. Each links to the
  surface itself, so the negative result is reproducible in a browser rather than taken on
  trust.</p>"""
    )
    body += _searched_table(meta)
    body.append(
        f"""  <p><code>{_e(meta["field"])}</code> exists only inside the raw dump
  (<code>{_e(meta["source_table"])}</code>). BSEE ships no layout file, no readme and no
  code table with it, and the field is absent from the eWell WAR field-definitions grid
  that documents its 23 siblings. It is an undocumented internal column exposed by a raw
  data release &mdash; which is not a criticism of BSEE, but it is a fact every consumer
  of these numbers needs to know.</p>
</section>"""
    )

    # ---- 2. what is published ---------------------------------------------
    body.append(
        f"""<section class="sec" id="published">
  <div class="sec-head"><p class="eyebrow">2 &middot; Tier 1</p>
  <h2>What BSEE <em>does</em> publish: <code>BOREHOLE_STAT_CD</code></h2></div>
  <p class="sec-note">One relevant domain is published, at
  <a href="{BOREHOLE_URL}">data.bsee.gov borehole field values &#8599;</a>. It is a
  <strong>borehole status</strong> list, not an activity list, and this repository
  previously carried it in a directory named for the WAR field &mdash; which is how a
  borehole-status table came to be presented as the WAR activity vocabulary.</p>"""
    )
    body += _borehole_table(observed)
    body.append(
        f"""  <div class="callout">
    <p><strong>{_e(doc["borehole_stat_cd"]["note"])}</strong></p>
    <p>The six that never appear in WAR are
    {", ".join(f"<code>{_e(c)}</code>" for c in never_in_war)}. The six WAR tokens absent
    from this list are
    {", ".join(f"<code>{_e(c['code'])}</code>" for c in unknown if c["code"])}. Half the
    observed WAR vocabulary is outside the borehole-status domain entirely: they are
    related domains, not the same domain, and the published list must not be presented as
    the WAR list.</p>
  </div>
</section>"""
    )

    # ---- 3. the code table ------------------------------------------------
    body.append(
        f"""<section class="sec" id="codes">
  <div class="sec-head"><p class="eyebrow">3 &middot; Tiers 2 and 3</p>
  <h2>The {len(named)} codes observed in <code>WELL_ACTIVITY_CD</code></h2></div>
  <p class="sec-note">Frequencies are the whole corpus &mdash; {total_rows:,} wellbore-week
  rows of <code>{_e(meta["source_table"])}</code>, WAR vintage {_e(meta["data_vintage"])},
  recomputed by this page's generator and cached at
  {_blob(FREQ_REPO_PATH)}. Every row links to its line in the definitions
  artifact. A blank-code row is included because 882 rows carry no value at all.</p>"""
    )
    body += _codes_table(doc, freq, lines)
    body.append(
        """  <div class="legend" aria-label="Provenance legend">
    <span class="eyebrow" style="align-self:center">Provenance</span>
    <span class="item"><span class="sw" style="background:var(--accent)"></span>Published by BSEE &mdash; solid teal rule</span>
    <span class="item"><span class="sw" style="background:var(--warn)"></span>Reuse inferred &mdash; dashed amber rule, on every row</span>
    <span class="item"><span class="sw hatch"></span>Unknown &mdash; dotted grey rule, hatched meaning cell, no meaning shown</span>
  </div>
</section>"""
    )

    # ---- 4. PND -----------------------------------------------------------
    body.append(_pnd_section(doc, freq, lines))

    # ---- 5. the ask -------------------------------------------------------
    ask_codes = ", ".join(f"<code>{_e(c)}</code>" for c in ask["codes"])
    ask_rows = sum(int(freq[c]["rows"]) for c in ask["codes"])
    body.append(
        f"""<section class="sec" id="ask">
  <div class="sec-head"><p class="eyebrow">5 &middot; What would settle it</p>
  <h2>One open query to BSEE &mdash; and it must cover the whole domain</h2></div>
  <p class="sec-note">No amount of further analysis of our own copy of the data can turn
  an inference into a definition. Only the data steward can.</p>
  <div class="panel">
    <h3>Outstanding query</h3>
    <ul>
      <li><strong>To</strong> &mdash; <code>{_e(ask["contact"])}</code>
      (BSEE Technical Data Management)</li>
      <li><strong>Ask</strong> &mdash; {_e(ask["ask"])}</li>
      <li><strong>Codes</strong> &mdash; {ask_codes}
      ({ask_rows:,} rows, {100 * ask_rows / total_rows:.1f}% of the corpus)</li>
      <li><strong>Tracked as</strong> &mdash;
      <a href="{ISSUE}/{meta["issue"]}">#{meta["issue"]}</a></li>
    </ul>
  </div>
  <div class="callout bad">
    <p><strong>Do not ask about <code>PND</code> alone.</strong> The issue was raised about
    PND because PND showed up in a rig-day total, but PND is {_e(freq["PND"]["pct"])}% of
    rows and the other five undocumented codes together are
    {100 * (unknown_rows - int(freq["PND"]["rows"])) / total_rows:.2f}%. A reply that
    defines only PND leaves the larger hole open and would let this page be quietly
    retired while most of the vocabulary is still undocumented.</p>
  </div>
  <div class="callout hold">
    <p><strong>Cheaper avenue, still untried.</strong> BSEE's own eWell WAR report viewer
    renders a <code>STATUS</code> cell per report. If that cell spells the status out
    rather than printing the token, it is a published answer available today &mdash; but
    it renders through an image pipeline, so it needs one manual browser check on a report
    known to carry an undocumented code. Until somebody does that, or TDM replies, tier 3
    stays empty.</p>
  </div>
</section>"""
    )

    # ---- 6. provenance ----------------------------------------------------
    body.append(
        f"""<section class="sec" id="source">
  <div class="sec-head"><p class="eyebrow">6 &middot; Follow it to source</p>
  <h2>Everything on this page, and where it comes from</h2></div>
  <div class="tablewrap"><table>
    <thead><tr><th>What</th><th>Where</th><th>Why you'd open it</th></tr></thead>
    <tbody>
      <tr><td>Definitions artifact</td><td>{_blob(YAML_REPO_PATH)}</td>
        <td class="wrap-cell">The single source for these codes. Code imports it; this
        page is generated from it; nothing else may hold a second copy.</td></tr>
      <tr><td>Observed frequency</td><td>{_blob(FREQ_REPO_PATH)}</td>
        <td class="wrap-cell">Row, percentage and wellbore counts per code, recomputed
        from the raw WAR tables at WAR vintage {_e(meta["data_vintage"])}.</td></tr>
      <tr><td>Generator</td><td>{_blob(GENERATOR_REPO_PATH)}</td>
        <td class="wrap-cell">Builds this page. Refuses to run if any
        <code>unknown</code> row acquires a label.</td></tr>
      <tr><td>Pins</td><td>{_blob(TEST_REPO_PATH)}</td>
        <td class="wrap-cell">Asserts the page is byte-regenerable, self-contained, and
        that no unknown code renders a meaning.</td></tr>
      <tr class="t-pub"><td>BSEE borehole field values</td>
        <td><a href="{BOREHOLE_URL}">data.bsee.gov &#8599;</a></td>
        <td class="wrap-cell">The tier-1 source, quoted verbatim in &sect;2.</td></tr>
      <tr><td>Issue</td><td><a href="{ISSUE}/{meta["issue"]}">#{meta["issue"]}</a></td>
        <td class="wrap-cell">The open question and the BSEE query.</td></tr>
    </tbody></table></div>
</section>"""
    )

    body.append(
        f"""  <footer class="site">
    <div class="row">
      <span>BSEE WAR activity codes &mdash; what is published, what is inferred,
      what is unknown &middot; issue #{meta["issue"]}</span>
      <a href="{BLOB}/{GENERATOR_REPO_PATH}">Generator &amp; provenance &#8599;</a>
    </div>
    <p class="note">// self-contained &mdash; no external assets. Generated from
    war_activity_codes.yml; regenerate with
    <code>build_war_activity_codes.py</code>; pinned by
    tests/unit/lower_tertiary/test_war_activity_codes.py</p>
  </footer>
</div>"""
    )

    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>BSEE WAR Activity Codes &mdash; Published, Inferred, Unknown</title>\n"
        f"<style>{STYLE}</style>\n</head>\n<body>\n"
        + "\n".join(body)
        + "\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------
def build(yaml_path: Path) -> str:
    doc = load_codes(yaml_path)
    return build_html(doc, load_frequency(), yaml_lines(yaml_path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yaml",
        help="Path to war_activity_codes.yml (default: $WED_WAR_CODES_YAML, else "
        "the package copy).",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Recompute code frequencies from the raw WAR tables and rewrite the cache.",
    )
    parser.add_argument(
        "--war-dir",
        help="Directory holding mv_war_main.bin / mv_war_main_prop.bin "
        "(default: $WED_WAR_DIR, else data/modules/bsee/bin/war).",
    )
    args = parser.parse_args(argv)

    yaml_path = resolve_yaml(args.yaml)
    if yaml_path is None:
        parser.error(
            f"definitions artifact not found; expected {PACKAGE_YAML} "
            "or pass --yaml/$WED_WAR_CODES_YAML"
        )

    if args.refresh:
        war_dir = _war_dir(args.war_dir)
        if not (war_dir / "mv_war_main_prop.bin").exists():
            parser.error(f"WAR tables not found under {war_dir}; pass --war-dir")
        write_frequency(recompute_frequency(war_dir))
        print(f"refreshed {FREQ_CSV} from {war_dir}")

    OUT_HTML.write_text(build(yaml_path), encoding="utf-8")
    doc = load_codes(yaml_path)
    unknown = [c for c in doc["codes"] if c["provenance"] == "unknown"]
    print(
        f"wrote {OUT_HTML} — {len(doc['codes'])} rows, "
        f"{len(unknown)} with no meaning published (definitions: {yaml_path})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
