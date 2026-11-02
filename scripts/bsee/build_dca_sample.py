#!/usr/bin/env python3
"""Build only the three-case public BSEE DCA QA sample; no full-run option.

Reuse the retained julia_life_to_date source owner, verification helpers and
OGOR-A schema. Original records are not copied. Report output excludes operator
and completion names. See docs/guides/bsee-dca-charts.md for sources and units.
"""

import argparse
import hashlib
import io
import json
from html import escape
from pathlib import Path

import pandas as pd

from worldenergydata.bsee.analysis.forecasting.monthly_dca import (
    analyze_monthly,
    prepare_monthly,
)
from worldenergydata.bsee.analysis.forecasting.monthly_dca_plots import (
    build_dca_figure,
    export_static,
    recovery_text,
)
from worldenergydata.bsee.data.sources.bin.ogor_production_loader import (
    OGOR_COLUMN_NAMES,
)
from worldenergydata.lower_tertiary.life_to_date import (
    verify_completion_coverage,
    verify_field_identity,
    verify_inputs,
)

CRITERIA_VERSION = "bsee-dca-sample-v1"
CASES = [
    ("API_WELL_NUMBER", "608124003301", 1000.0),
    ("API_WELL_NUMBER", "608124009400", 1000.0),
    ("FIELD_NAME_CODE", "WR627", 5000.0),
]


def load_sample(data_dir):
    """Verify bytes before parsing and check field/completion coverage."""
    data_dir = Path(data_dir)
    basis = json.loads((data_dir / "basis.json").read_text(encoding="utf-8"))
    provenance = json.loads((data_dir / "sources.json").read_text(encoding="utf-8"))
    verified = verify_inputs(data_dir, basis, provenance)
    verify_field_identity(verified, basis)
    frames = [
        pd.read_csv(
            io.BytesIO(blob), names=OGOR_COLUMN_NAMES, dtype=str, keep_default_na=False
        )
        for path, blob in sorted(verified.items())
        if path.startswith("raw/ogora")
    ]
    records = pd.concat(frames, ignore_index=True)
    records["FIELD_NAME_CODE"] = records.BOEM_FIELD.str.strip()
    if set(records.FIELD_NAME_CODE) != {"WR627"}:
        raise ValueError("sample field differs from the retained source owner")
    coverage = verify_completion_coverage(verified, basis, records)
    if coverage["excluded"]:
        raise ValueError("sample field has excluded completions")
    return records, provenance, coverage


def _save_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def build(data_dir, output_dir):
    """Retain plotted arrays, compact metrics, provenance and output hashes.

    Acceptance v1: exactly two wells and one field, verified source digests,
    b <= 1, Dterm=0.06 nominal/year, 36-month fit window, two-year holdout,
    dated interactive and static panels and source/output readback. Owner QA
    remains pending regardless of test or export success.
    Economic limits 1,000 bbl/d per well and 5,000 bbl/d per field are
    illustrative inputs, not published field economics. Pradhan 2020 §2.1
    gives the public 6% terminal-decline example; it is not field calibration.
    """
    records, provenance, coverage = load_sample(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sections, metrics, outputs = [], [], []
    for group, key, limit in CASES:
        result = analyze_monthly(
            prepare_monthly(records, group, key),
            economic_limit=limit,
            terminal_decline=0.06,
            b_max=1,
            fit_months=36,
            backtest_years=2,
        )
        slug = ("well-" if group == "API_WELL_NUMBER" else "field-") + key
        export_static(result, output_dir / slug)
        outputs.extend([f"{slug}.svg", f"{slug}.png"])
        history = result.history.frame.rename_axis("date").reset_index()
        history["fitted"] = history.date.isin(result.fit_dates)
        history["fitted_rate_bpd"] = float("nan")
        history.loc[history.fitted, "fitted_rate_bpd"] = result.model.rate(
            (result.fit_dates - result.origin).days.to_numpy() / 365.25
        )
        history["cumulative_bbl"] = history.oil_bbl.fillna(0).cumsum()
        history.to_csv(
            output_dir / f"{slug}-history.csv", index=False, date_format="%Y-%m-%d"
        )
        pd.DataFrame(
            {
                "date": result.forecast_dates,
                "rate_bpd": result.forecast_rates,
                "cumulative_bbl": result.forecast_cumulative_bbl,
            }
        ).to_csv(
            output_dir / f"{slug}-forecast.csv",
            index=False,
            date_format="%Y-%m-%dT%H:%M:%S",
        )
        outputs.extend([f"{slug}-history.csv", f"{slug}-forecast.csv"])
        bt = result.backtest
        if bt is not None:
            pd.DataFrame(
                {
                    "date": bt.dates,
                    "actual_bpd": bt.actual,
                    "old_forecast_bpd": bt.predicted,
                }
            ).to_csv(
                output_dir / f"{slug}-backtest.csv", index=False, date_format="%Y-%m-%d"
            )
            outputs.append(f"{slug}-backtest.csv")
        item = {
            "slug": slug,
            "label": result.history.label,
            "model": result.model_name,
            "qi_bpd": result.model.initial_rate,
            "nominal_decline_per_year": result.model.decline,
            "b": result.model.b,
            "terminal_nominal_decline_per_year": 0.06,
            "economic_limit_bpd": limit,
            "history_start": f"{result.history.frame.index[0]:%Y-%m-%d}",
            "today": f"{result.history.frame.index[-1]:%Y-%m-%d}",
            "fit_start": f"{result.fit_dates[0]:%Y-%m-%d}",
            "fit_points": len(result.fit_dates),
            "fit_rmse_bpd": result.rmse_bpd,
            "shut_in_months": int(result.history.frame.shut_in.sum()),
            "missing_months": int(result.history.frame.missing.sum()),
            "partial_months": int(result.history.frame.partial.sum()),
            "observed_bbl": result.observed_bbl,
            "remaining_bbl": result.remaining_bbl,
            "eur_bbl": result.eur_bbl,
            "limit_reached": result.limit_reached,
            "forecast_end": result.forecast_dates[-1].isoformat(),
            "backtest_cutoff": bt.cutoff.isoformat() if bt else None,
            "backtest_rmse_bpd": bt.rmse_bpd if bt else None,
            "backtest_points": len(bt.dates) if bt else 0,
        }
        metrics.append(item)
        plot = build_dca_figure(result).to_html(
            full_html=False,
            include_plotlyjs="cdn" if not sections else False,
            config={"responsive": True},
            div_id=f"chart-{slug}",
        )
        table = history.to_html(
            index=False, float_format=lambda value: f"{value:,.2f}", na_rep="Unreported"
        )
        sections.append(
            f'<section id="{slug}"><h2>{escape(result.history.label)}</h2>'
            f"<p>{escape(recovery_text(result))}. Fit RMSE: {result.rmse_bpd:,.0f} bbl/d; "
            f"fit starts {item['fit_start']}; {item['fit_points']} active months. "
            f"Economic-limit scenario: {limit:,.0f} bbl/d.</p>{plot}"
            f'<p><a href="{slug}.svg">SVG</a> · <a href="{slug}.png">PNG</a> · '
            f'<a href="{slug}-history.csv">Observed arrays</a> · '
            f'<a href="{slug}-forecast.csv">Forecast arrays</a></p>'
            f'<details><summary>Static report panel</summary><img src="{slug}.png" '
            f'alt="{escape(recovery_text(result))}; forecast compared with withheld actuals"></details>'
            f"<details><summary>Accessible monthly data table</summary>{table}</details></section>"
        )
    _save_json(
        output_dir / "metrics.json",
        {"criteria_version": CRITERIA_VERSION, "cases": metrics},
    )
    outputs.append("metrics.json")
    source_rows = [
        item for item in provenance["files"] if item["path"].startswith("raw/ogora")
    ]
    urls = "".join(
        f'<li><a href="{escape(item["source_url"], quote=True)}">{escape(item["path"])}</a> · '
        f"retrieved {escape(item['retrieved_at'])}</li>"
        for item in source_rows
    )
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BSEE sample decline charts — QA preview</title><style>
body{{font:16px system-ui,sans-serif;color:#263746;max-width:1300px;margin:2rem auto;padding:0 1rem}}
h1,h2{{color:#174a68}}section{{margin:3rem 0;border-top:1px solid #d9e2e8}}p{{line-height:1.55}}
.notice{{background:#e7f3fa;border-left:4px solid #0072b2;padding:1rem}}img{{max-width:100%}}
table{{border-collapse:collapse;font-size:12px}}td,th{{padding:5px;text-align:right;border-bottom:1px solid #ddd}}
details{{margin:1rem 0;overflow:auto}}a{{color:#006399}}</style></head><body>
<h1>BSEE monthly decline curves — sample QA preview</h1>
<p class="notice">Two API wells and one field only. Owner sample review is pending. No full dataset run is included.</p>
<p>Source owner: <code>data/economics/julia_life_to_date</code>; source ID <code>bsee-data-center</code>.
The retained snapshot ends in June 2026; it is not a live November 2026 update. “Today” means the last reported month.
The field chart sums all retained field wells, rather than only the two displayed wells. Field membership coverage:
{len(coverage["produced"])} completed APIs with reported production.</p>
<p>Method: bounded exponential/hyperbolic/harmonic Arps comparison by AIC, b ≤ 1; continuous terminal exponential
tail at 6% nominal/year; trailing 36-month fit; back-test refit two years before the last report. Economic limits
are illustrative user inputs: <strong>income = costs is not established</strong>. Nominal 6% is not effective 6%.
Blue shading distinguishes observed barrels from remaining forecast; the observed area uses calendar-month steps.
EUR means observed-window oil plus forecast to the scenario limit, not independently verified lifecycle reserves.
Internal missing or partial reports, or a truncated horizon, withhold EUR.</p>
<p>Operational effects including fluid fill, liquid loading, pump failure and changing well inventory can mimic decline.
Zero-oil months are marked and excluded from fitting; back-test error includes reported zero-oil months.
Absent reports are not treated as measured zero. Rates use calendar days, including downtime, not producing days.
Back-test errors are descriptive; no predictive-accuracy acceptance threshold has been established.
Interactive charts require Plotly 2.35.2 from its CDN; SVG, PNG and CSV links work offline.</p>
{"".join(sections)}
<h2>Method references and retained data</h2><p>Arps (1945), doi:10.2118/945228-G;
<a href="https://www.e-education.psu.edu/eme801/sites/www.e-education.psu.edu.eme801/files/Production%20Decline%20for%20Shale%20Gas%20Wells.pdf">Penn State EME 801, equations (1)–(2)</a>;
<a href="https://blasingame.engr.tamu.edu/0_TAB_Grad/TAB_Grad_Thesis_Archive/MS_073_PRADHAN_Yogashril_Thesis_TAMU_%28Dec_2020%29.pdf">Pradhan (2020), section 2.1, page 9</a>;
<a href="https://www.data.bsee.gov/Main/HtmlPage.aspx?page=ogorA">BSEE OGOR-A definitions</a>.
No original standards or proprietary material is reproduced.</p><ul>{urls}</ul>
<p>Criteria: {CRITERIA_VERSION}. <a href="metrics.json">Metrics</a> · <a href="manifest.json">Source and output digests</a>.</p>
</body></html>"""
    (output_dir / "index.html").write_text(page, encoding="utf-8")
    outputs.append("index.html")
    manifest = {
        "criteria_version": CRITERIA_VERSION,
        "qa_status": "awaiting-owner-sample-review",
        "dataset_id": provenance["dataset_id"],
        "source_id": "bsee-data-center",
        "source_owner": "data/economics/julia_life_to_date",
        "source_manifest_sha256": hashlib.sha256(
            (Path(data_dir) / "sources.json").read_bytes()
        ).hexdigest(),
        "cases": metrics,
        "inputs": [
            {k: item[k] for k in ("path", "sha256", "source_url", "retrieved_at")}
            for item in provenance["files"]
        ],
        "units": {
            "oil": "bbl",
            "rate": "bbl/calendar-day",
            "nominal_decline": "year^-1",
        },
        "outputs": [],
    }
    for name in outputs:
        blob = (output_dir / name).read_bytes()
        if len(blob) >= 5_000_000:
            raise ValueError("sample artifact exceeds the 5 MB retention bound")
        manifest["outputs"].append(
            {
                "path": name,
                "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )
    _save_json(output_dir / "manifest.json", manifest)
    # Read back the persisted manifest and every listed artifact before returning.
    saved = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    for item in saved["outputs"]:
        if (
            hashlib.sha256((output_dir / item["path"]).read_bytes()).hexdigest()
            != item["sha256"]
        ):
            raise ValueError("output digest mismatch")
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir", type=Path, default=Path("data/economics/julia_life_to_date")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.data_dir, args.output_dir)
    print(
        f"{len(result['cases'])} sample cases; {len(result['outputs'])} artifacts; {result['qa_status']}"
    )


if __name__ == "__main__":
    main()
