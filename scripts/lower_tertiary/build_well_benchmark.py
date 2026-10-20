#!/usr/bin/env python3
"""ABOUTME: CLI for the Lower-Tertiary well-benchmarking analytic (worldenergydata#499).
ABOUTME: Renders the per-well benchmark table to reports/lower_tertiary/*.md + *.csv.

This is the guaranteed entry point for the saved analytic. It also backs the
engine route (``basename: bsee`` + ``analysis.type: well_benchmark``); both paths
call :func:`worldenergydata.lower_tertiary.well_benchmark.run_well_benchmark`.

Usage
-----
    # all producing LT fields, spud >= 2010, latest OGOR-A window
    uv run python scripts/lower_tertiary/build_well_benchmark.py

    # a saved config (same as the engine path consumes)
    uv run python scripts/lower_tertiary/build_well_benchmark.py \
        --config config/input/lt_well_benchmark.yml

Every number traces to public BSEE OGOR-A production + WAR/drilling records run
through the existing per-well primitives. Missing metrics are flagged, never
faked.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from worldenergydata.lower_tertiary.well_benchmark import (  # noqa: E402
    BenchmarkConfig,
    run_well_benchmark,
)

REPORTS_DIR = PROJECT_ROOT / "reports" / "lower_tertiary"

# Columns rendered in the markdown table (order matters), with headers.
_MD_COLUMNS = [
    ("field", "Field"),
    ("well", "Wellbore (API12)"),
    ("spud", "Spud"),
    ("first_oil", "First oil"),
    ("spud_to_completion_calendar_days", "Spud to completion (calendar days)"),
    ("completion_days", "Completion to first oil (calendar days)"),
    ("cum_oil_mmbbl", "Cum oil (MMbbl)"),
    ("uptime_pct", "Uptime %"),
    ("decline_annual_pct", "Decline %/yr"),
    ("eur_mmbbl", "EUR (MMbbl)"),
    ("est_revenue_mm", "Est. revenue ($MM)"),
    ("interventions", "Interventions"),
]


def _fmt(value) -> str:
    if value is None or value == "" or (isinstance(value, float) and pd.isna(value)):
        return "—"  # flag-don't-fake: a blank cell, never a fabricated number
    if isinstance(value, float):
        return f"{value:,.1f}" if abs(value) >= 1 else f"{value:,.3f}"
    return str(value)


def _slug_years(cfg: BenchmarkConfig) -> str:
    lo = cfg.spud_year_min if cfg.spud_year_min is not None else "all"
    hi = cfg.spud_year_max if cfg.spud_year_max is not None else "latest"
    return f"{lo}_{hi}"


def render_markdown(df: pd.DataFrame, cfg: BenchmarkConfig, end_date: str) -> str:
    lines: list[str] = []
    play_label = cfg.play.replace("_", " ").title()
    lines.append(f"# {play_label} Well Benchmarking")
    lines.append("")
    field_label = ", ".join(cfg.fields) if cfg.fields else "all producing fields"
    lines.append(
        f"**Play:** {play_label} &middot; **Fields:** {field_label} &middot; "
        f"**Spud window:** {cfg.spud_year_min or 'all'}–{cfg.spud_year_max or 'latest'} "
        f"&middot; **Data through:** {end_date} (BSEE OGOR-A)"
    )
    lines.append("")
    lines.append(
        f"Per-well benchmark for **{len(df)} producing wells**, sorted by "
        f"cumulative oil. Calendar timing and interventions are "
        f"derived from BSEE WAR + V30 drilling data; first oil, cumulative oil "
        f"and uptime from OGOR-A production; decline (D, EUR) from the "
        f"forecasting module; estimated revenue from monthly oil × the "
        f"historical WTI deck. Cells shown as `—` are not derivable from the "
        f"public data for that well (flagged, not fabricated)."
    )
    lines.append("")

    lines.extend(
        [
            "## Revision history",
            "",
            "| Revision | Date | What changed and why |",
            "|---|---|---|",
            "| 1 | 2026-10-19 | Rename calendar timing to prevent interpretation as drilling rig-time; saved values remain unchanged. |",
            "",
            "Spud to completion is the first completion operation date minus spud; "
            "completion to first oil is first oil minus that completion date. "
            "Both are elapsed calendar intervals, including suspensions, not rig-days. "
            "The benchmark population includes only producing wells in the stated "
            "spud window; it differs from the workbook and article populations on the "
            "[calendar cycle-time page](https://vamseeachanta.github.io/worldenergydata/drilling-insights.html).",
            "",
        ]
    )
    header = "| " + " | ".join(h for _, h in _MD_COLUMNS) + " |"
    sep = "|" + "|".join("---" for _ in _MD_COLUMNS) + "|"
    lines.append(header)
    lines.append(sep)
    for _, r in df.iterrows():
        cells = [
            _fmt(
                r.get(col)
                if col in {"field", "well", "spud", "first_oil"}
                else pd.to_numeric(r.get(col), errors="coerce")
            )
            for col, _ in _MD_COLUMNS
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # Flag summary so missing-data caveats are explicit.
    flagged = df[
        df[["uptime_flag", "revenue_flag", "decline_flag"]].notna().any(axis=1)
    ]
    if not flagged.empty:
        lines.append("## Data flags")
        lines.append("")
        lines.append(
            "Wells where a metric could not be fully derived from public BSEE "
            "data (the value is computed on what is present and flagged here):"
        )
        lines.append("")
        for _, r in flagged.iterrows():
            fl = [
                f"{name}={r[name]}"
                for name in ("uptime_flag", "revenue_flag", "decline_flag")
                if pd.notna(r.get(name)) and r.get(name)
            ]
            if fl:
                lines.append(f"- `{r['well']}` ({r['field']}): {', '.join(fl)}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_Deterministic: same config + same BSEE data → identical table. "
        "Regenerate with_ "
        "`uv run python scripts/lower_tertiary/build_well_benchmark.py "
        "--config config/input/lt_well_benchmark.yml`."
    )
    lines.append("")
    return "\n".join(lines)


def _load_cfg(args: argparse.Namespace) -> BenchmarkConfig:
    if args.config:
        raw = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        bench = raw.get("benchmark", raw)
        return BenchmarkConfig.from_mapping(bench)
    return BenchmarkConfig(
        play=args.play,
        spud_year_min=args.spud_year_min,
        spud_year_max=args.spud_year_max,
        fields=args.fields,
        end_date=args.end_date,
    )


def read_saved_benchmark(path: Path) -> pd.DataFrame:
    """Migrate saved public cells without recomputing or inventing raw inputs.

    Read as strings to preserve identifiers, empty cells and numeric precision.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    calendar = "spud_to_completion_calendar_days"
    if "drilling_days" in df:
        if calendar in df:
            if not df[calendar].equals(df["drilling_days"]):
                raise ValueError("Calendar column and legacy alias conflict")
            return df.drop(columns="drilling_days")
        return df.rename(columns={"drilling_days": calendar})
    if calendar not in df:
        raise ValueError("Saved benchmark has no calendar duration column")
    return df


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="Saved benchmark YAML.")
    parser.add_argument("--play", default="lower_tertiary")
    parser.add_argument("--spud-year-min", type=int, default=2010, dest="spud_year_min")
    parser.add_argument("--spud-year-max", type=int, default=None, dest="spud_year_max")
    parser.add_argument("--fields", nargs="+", default=None)
    parser.add_argument("--end-date", default=None, dest="end_date")
    parser.add_argument(
        "--saved-csv",
        type=Path,
        help="Relabel a saved benchmark without raw-data recomputation; requires --end-date.",
    )
    args = parser.parse_args(argv)

    cfg = _load_cfg(args)
    if args.saved_csv:
        if not args.end_date:
            parser.error("--saved-csv requires --end-date from the saved report")
        df = read_saved_benchmark(args.saved_csv)
        end_date = args.end_date
    else:
        from worldenergydata.lower_tertiary import ops_timeline

        ops_timeline.ensure_ogor_loader()
        end_date = cfg.end_date or ops_timeline.month_end_str(
            ops_timeline.detect_latest_ogor_month()
        )
        df = run_well_benchmark(cfg)
    if df.empty:
        print("No producing wells matched the benchmark config.", flush=True)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"lt_well_benchmark_{cfg.play}_{_slug_years(cfg)}"
    md_path = REPORTS_DIR / f"{stem}.md"
    csv_path = REPORTS_DIR / f"{stem}.csv"

    md_path.write_text(render_markdown(df, cfg, end_date), encoding="utf-8")
    df.to_csv(csv_path, index=False)

    print(f"Wrote {md_path}", flush=True)
    print(f"Wrote {csv_path}", flush=True)
    print(
        f"{len(df)} wells; top cum-oil: {df.iloc[0]['well']} "
        f"({df.iloc[0]['cum_oil_mmbbl']} MMbbl, {df.iloc[0]['field']})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
