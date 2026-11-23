"""Observed-production economics with retained raw filing provenance."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pandas as pd

from worldenergydata.bsee.data.sources.bin.ogor_production_loader import OGOR_COLUMN_NAMES


def load_verified(data_dir):
    """Read the retained field production and its declared basis."""
    data_dir = Path(data_dir)
    basis = json.loads((data_dir / "basis.json").read_text())
    provenance = json.loads((data_dir / "sources.json").read_text())
    verified = verify_inputs(data_dir, basis, provenance)
    verify_field_identity(verified, basis)
    frames = []
    for source in provenance["files"]:
        if source["path"].startswith("raw/ogora"):
            frames.append(pd.read_csv(io.BytesIO(verified[source["path"]]), names=OGOR_COLUMN_NAMES,
                                      dtype=str, keep_default_na=False))
    frame = pd.concat(frames, ignore_index=True)
    frame["date"] = pd.to_datetime(frame["PRODUCTION_DATE"], format="%Y%m")
    for source, target in [("MON_O_PROD_VOL", "oil_bbl"), ("MON_G_PROD_VOL", "gas_mcf")]:
        frame[target] = pd.to_numeric(frame[source])
    keys = ["LEASE_NUMBER", "API_WELL_NUMBER", "COMPLETION_NAME", "PRODUCTION_DATE",
            "PROD_INTERVAL_CD", "UNIT_AGT_NUMBER", "UNIT_ALOC_SUFFIX", "PRODUCT_CODE"]
    if frame.duplicated(keys).any():
        raise ValueError("duplicate completion-month record")
    if set(frame.BOEM_FIELD.str.strip()) != {basis["field_code"]}:
        raise ValueError("production field does not agree with basis")
    if not set(frame.LEASE_NUMBER.str.strip()).issubset(basis["leases"]):
        raise ValueError("production lease does not agree with basis")
    basis["completion_coverage"] = verify_completion_coverage(verified, basis, frame)
    monthly = frame.groupby("date", as_index=False)[["oil_bbl", "gas_mcf"]].sum()
    first = monthly.loc[monthly.oil_bbl > 0, "date"].min()
    monthly = monthly.loc[monthly.date >= first].reset_index(drop=True)
    if pd.isna(first) or monthly.empty:
        raise ValueError("no observed oil production")
    if monthly.date.tolist() != pd.date_range(first, monthly.date.max(), freq="MS").tolist():
        raise ValueError("production month coverage is incomplete")
    return monthly, basis, provenance


def verify_inputs(data_dir, basis, provenance):
    """Reject mismatched digests, units and source-year coverage."""
    expected = {f"raw/ogora{year}.csv" for year in basis["production_years"]}
    observed = {source["path"] for source in provenance["files"]
                if source["path"].startswith("raw/ogora")}
    if expected != observed:
        raise ValueError("production year coverage is incomplete")
    if provenance["units"] != {"oil": "bbl", "gas": "Mcf", "water": "bbl"}:
        raise ValueError("production units are not established")
    root = data_dir.resolve()
    if (root / "raw").is_symlink():
        raise ValueError("raw input directory is a symlink")
    verified = {}
    for source in provenance["files"]:
        relative = Path(source["path"])
        path = root / relative
        if relative.is_absolute() or len(relative.parts) != 2 or relative.parts[0] != "raw" or path.is_symlink():
            raise ValueError("input path is outside the dataset")
        blob = path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != source["sha256"]:
            raise ValueError(f"input digest mismatch: {relative}")
        if len(blob.splitlines()) != source["record_count"] + source["header_lines"]:
            raise ValueError("input record count mismatch")
        if len(source["source_row_numbers"]) != source["record_count"]:
            raise ValueError("source row count mismatch")
        if not source["source_url"].startswith("https://www.data.bsee.gov/"):
            raise ValueError("source address is not the recorded publisher")
        verified[source["path"]] = blob
    return verified


def analyse(data_dir):
    """Calculate a pre-tax scenario against observed monthly production only."""
    from worldenergydata.lower_tertiary.npv import (
        calculate_monthly_financials, summarize_field_financials,
    )

    monthly, basis, provenance = load_verified(data_dir)
    a = basis["assumptions"]
    verify_assumptions(a)
    config = {
        "commodity_prices": {
            "oil": {"base_case": {"wti_usd_per_bbl": a["oil_price"]["value"]}},
            "gas": {"base_case": {"henry_hub_usd_per_mcf": a["gas_price"]["value"]}},
        },
        "fiscal_terms": {"royalty": {"rate": a["royalty_rate"]["value"]},
                         "taxes": {"federal_income_tax": {"rate": a["income_tax_rate"]["value"]}}},
        "financial_metrics": {"discount_rates": {"primary_discount_rate": a["discount_rate"]["value"]}},
    }
    financial = calculate_monthly_financials(monthly, config, a["opex_per_boe"]["value"])
    totals = summarize_field_financials(financial, {
        "display_name": basis["field"], "first_oil": monthly.date.min(),
        "capex": {"total_mm_usd": a["capex_usd_mm"]["value"]},
    }, config)
    metrics = {
        "oil_mmbbl": totals["Oil (MMBO)"],
        "gas_bcf": float(monthly.gas_mcf.sum()) / 1e6,
        "boe_mmboe": totals["BOE (MMBOE)"],
        "revenue_usd_mm": totals["Revenue ($MM)"],
        "royalty_usd_mm": totals["Royalty ($MM)"], "opex_usd_mm": totals["Opex ($MM)"],
        "operating_cashflow_usd_mm": totals["Op Cash Flow ($MM)"],
        "capital_usd_mm": totals["CAPEX ($MM)"],
        "pv_operations_usd_mm": totals["NPV Operations ($MM)"],
        "ltd_npv_usd_mm": totals["NPV Project ($MM)"],
    }
    annual = monthly.assign(year=monthly.date.dt.year).groupby("year")[["oil_bbl", "gas_mcf"]].sum()
    return {
        "field": basis["field"], "lease": basis["lease"], "leases": basis["leases"], "block": basis["block"],
        "completion_coverage": basis["completion_coverage"],
        "field_selection_matches_previous_lease_extract": basis["field_selection_matches_previous_lease_extract"],
        "field_code": basis["field_code"], "source_revision": basis["source_revision"],
        "scope": "life-to-date, pre-tax assumption scenario", "assumptions": a,
        "start": monthly.date.min().strftime("%Y-%m"), "end": monthly.date.max().strftime("%Y-%m"),
        "months": len(monthly), "metrics": metrics,
        "summary_metrics": {key: value / 1000 if key.endswith("_usd_mm") else value
                            for key, value in metrics.items()},
        "annual": [{"year": int(year), "oil_mmbbl": float(row.oil_bbl) / 1e6,
                    "gas_bcf": float(row.gas_mcf) / 1e6} for year, row in annual.iterrows()],
        "sources": provenance,
    }


METRIC_LABELS = {
    "oil_mmbbl": ("Observed oil", "MMbbl"),
    "gas_bcf": ("Observed gas", "BCF"),
    "boe_mmboe": ("Energy-equivalent production", "MMboe"),
    "revenue_usd_mm": ("Scenario gross revenue", "USD billion"),
    "royalty_usd_mm": ("Scenario royalty", "USD billion"),
    "opex_usd_mm": ("Scenario operating expenditure", "USD billion"),
    "operating_cashflow_usd_mm": ("Scenario operating cashflow", "USD billion"),
    "capital_usd_mm": ("Assumed capital", "USD billion"),
    "pv_operations_usd_mm": ("Discounted operating cashflow", "USD billion"),
    "ltd_npv_usd_mm": ("Life-to-date discounted balance", "USD billion"),
}


def section(identifier, title, body):
    from html import escape

    return f'<section class="report-section" id="{identifier}"><h2>{escape(title)}</h2>{body}</section>\n'


def summary(result):
    from html import escape

    rows = []
    for key, value in result["summary_metrics"].items():
        label, unit = METRIC_LABELS[key]
        rows.append(f'<tr><td>{label}</td><td>{unit}</td><td data-metric="{key}">{value:,.1f}</td></tr>')
    return section("summary", "1 Executive Summary", f'''
<p>The observed-production scenario can support comparisons of economic assumptions. Investment and full-cycle decisions require a verified cost, fiscal and reserves basis.</p>
<p>The Julia field-coded records cover {escape(result['start'])} through {escape(result['end'])}. Prices, expenditure, royalty and discounting are assumed; tax and future production are excluded.</p>
<p>The scenario quantities and discounted balance are presented in Table 1.1. Monetary totals are in USD billion; this case does not establish actual realized revenue or expenditure.</p>
<table><thead><tr><th>Quantity</th><th>Unit</th><th>Value</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p class="caption">Table 1.1 – Observed production and assumption-case quantities.</p>
''')


def assumption_table(result):
    from html import escape

    rows = []
    for key, item in result["assumptions"].items():
        value, unit = item["value"], item["unit"]
        if key == "income_tax_rate":
            label = "Excluded: pre-tax case"
        else:
            if unit == "1":
                value, unit = value * 100, "%"
            if unit == "USD million":
                value, unit = value / 1000, "USD billion"
            label = f"{value:,.1f} {unit}"
        rows.append(f'<tr><td>{escape(key.replace("_", " "))}</td><td>{label}</td>'
                    f'<td>ASSUMED: {escape(item["reason"])}</td></tr>')
    return '<table><thead><tr><th>Input</th><th>Value and unit</th><th>Basis limitation</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table><p class="caption">Table 3.1 – Economic assumptions and exclusions.</p>'


def introduction_and_basis(result):
    from html import escape

    identity = f"Julia; leases {escape(', '.join(result['leases']))}; field code {escape(result['field_code'])}; block {escape(result['block'])}"
    intro = section("introduction", "2 Introduction", '''
<p>The analysis calculates a field-level pre-tax assumption scenario from retained public production filings. The demonstration summary identifies Julia as the field; it is used only for field selection [I2].</p>
<p>The scope ends at the latest observed field-production month. Decline extrapolation, booked-reserve valuation, full-cycle economics and actual expenditure reconciliation are excluded.</p>
''')
    basis = section("design-data", "3 Design Data", f'''
<p>The input basis comprises field-coded production, well/completion identifiers and field identifiers from public federal filings. The retained rows and their source archive digests are listed in the accompanying manifest.</p>
<h3>3.1 Site or field data</h3><p>{identity}. Observed production spans {result['start']} to {result['end']}, with {result['months']} monthly observations. Earlier retained production records contain zero oil production.</p>
<h3>3.2 Structure or equipment data</h3><p>Well and completion filings support lease identity. Equipment design and mechanical capacities are not evaluated because the calculation uses field-level production and an assumed capital total.</p>
<h3>3.3 Environmental data</h3><p>Not applicable: no environmental loads or physical equipment response are calculated.</p>
<h3>3.4 Vessel data</h3><p>Not applicable: no vessel operation or vessel-dependent cost is modelled.</p>
<h3>3.5 Criteria</h3><p>Input digests, complete monthly coverage, numerical summary agreement and repeatable output bytes are required by the retained criteria record [I3]. The discounted cashflow balance is compared with zero; that arithmetic comparator does not qualify an investment decision.</p>
<h3>3.6 Analysis method</h3><p>The monthly cashflow and discounting equations are set out in Section 4.</p>
<h3>3.7 Assumptions</h3><p>Every economic input is labelled ASSUMED in Table 3.1. Inputs are taken from the recorded repository basis, with their paths retained in the structured results [I4].</p>
{assumption_table(result)}
''')
    return intro + basis


def methodology_and_results(result):
    annual_rows = ''.join(f'<tr><td>{row["year"]}</td><td>{row["oil_mmbbl"]:.1f}</td><td>{row["gas_bcf"]:.1f}</td></tr>'
                          for row in result["annual"])
    methods = section("method", "4 Analysis Methodology", '''
<p>Production is summed by month across all retained field-coded completions. Monetary quantities are calculated using the monthly financial and field-summary functions in worldenergydata [I1]; no production forecast is used.</p>
<p>Gross revenue is oil volume multiplied by the assumed oil price plus gas volume multiplied by the assumed gas price. Royalty is gross revenue multiplied by the assumed royalty fraction. Operating expenditure is energy-equivalent production multiplied by the assumed unit operating cost.</p>
<p>Pre-tax operating cashflow is gross revenue less royalty and operating expenditure. Gas energy-equivalence follows the existing module convention of 6.0 Mcf/boe; gas in BCF is the reported Mcf total divided by one million.</p>
<p>Operating cashflow is discounted by (1 + annual discount rate)<sup>elapsed months / 12</sup>, with the first observed oil month as the origin. The life-to-date balance is discounted operating cashflow less assumed capital charged at that origin.</p>
<p>The computational comparator is independent summation and cashflow arithmetic from retained rows. Digest equality and repeatable builds establish traceability and reproduction; actual sales, expenditure and fiscal records are needed to establish financial accuracy.</p>
''')
    results = section("results", "5 Detailed Results", f'''
<p>The annual observed-production quantities are presented in Table 5.1. The last year contains records only through {result['end']}; annual quantities for that year are incomplete.</p>
<table><thead><tr><th>Year</th><th>Oil (MMbbl)</th><th>Gas (BCF)</th></tr></thead><tbody>{annual_rows}</tbody></table>
<p class="caption">Table 5.1 – Observed field-coded production by calendar year.</p>
<p>The discounted assumption-case balance is {result['summary_metrics']['ltd_npv_usd_mm']:,.1f} USD billion against the zero-balance comparator. Capital is an assumed lump sum, so the balance cannot be interpreted as an audit of historical spending.</p>
''')
    return methods + results


def findings_and_limits(result):
    from html import escape

    limits = ''.join(f'<li>{escape(item["reason"])} See Section 3.7 and [I4].</li>'
                     for item in result["assumptions"].values())
    selection = (
        "Field-code selection returns the same production rows as the previous G20351 lease extract; the production and economic results are unchanged."
        if result["field_selection_matches_previous_lease_extract"] else
        "Field-code selection changes the retained production rows relative to the previous G20351 lease extract."
    )
    coverage = result["completion_coverage"]
    excluded = ''.join(f'<li>API {escape(row["api_well_number"])}: {escape(row["reason"])}</li>'
                       for row in coverage["excluded"])
    completion_limit = (
        f'<li>{coverage["checked_count"]} COM field wells are checked: '
        f'{len(coverage["produced"])} appear in field-coded production; '
        f'{len(coverage["excluded"])} are excluded with the following snapshot-limited reasons.<ul>{excluded}</ul>'
        'Field-code selection does not establish unreported or differently coded production for the excluded APIs.</li>'
    )
    retrieved_dates = ', '.join(sorted({row["retrieved_at"][:10] for row in result["sources"]["files"]}))
    return section("findings", "6 Key Findings", f'''
<p>The findings apply to the observed-production assumption case and its stated data window.</p>
<h3>6.1 Observed production</h3><p>The retained field-coded rows sum to {result['summary_metrics']['oil_mmbbl']:,.1f} MMbbl oil and {result['summary_metrics']['gas_bcf']:,.1f} BCF gas through {result['end']}. These are reported production quantities, not recoverable reserves.</p>
<h3>6.2 Economic balance</h3><p>The discounted balance is {result['summary_metrics']['ltd_npv_usd_mm']:,.1f} USD billion against zero for the assumed price, cost and fiscal case. Actual field profitability and full-cycle value are not established.</p>
''') + section("limitations", "7 Limitations", f'''
<p>The limitations identify missing evidence and the quantities affected. The actions in Section 8 are needed before the scenario can support broader financial decisions.</p>
<ul>{limits}<li>Production is available only through {result['end']}, at the retrieval dates in the source manifest; subsequent production is not included. See Section 5.</li>
<li>Production rows are selected by BOEM_FIELD WR627 and field-lease rows by FIELD_NAME_CODE WR627. Wells are selected by BOTM_FLD_NAME_CD WR627; completion records are joined to the selected well APIs. All columns are retained with LF normalization. {selection} See [I4].</li>
{completion_limit}
<li>Archive digests identify the copies retrieved on {retrieved_dates}. Later downloads, at least of the rolling current-year file, are expected to differ; annual archives may also be revised. The committed raw rows remain the reproducible analysis input. See [I4].</li>
<li>Full-cycle values and reserves-based forecasts remain excluded pending reserves qualification in issue 973. See Section 2.</li>
<li>Assumption-deck reconciliation, depreciation, intangible drilling costs, loss carryforward, severance and royalty relief are not modelled. Those items remain open in issue 651. See Section 3.7.</li></ul>
''')


def recommendations_and_references(result):
    from html import escape

    unique = {item["source_url"] for item in result["sources"]["files"]}
    urls = ''.join(f'<li><a href="{escape(url, quote=True)}">{escape(url)}</a></li>' for url in sorted(unique))
    return section("recommendations", "8 Recommendations", '''
<p>The next economic analysis requires an observed fiscal and expenditure basis. The following actions resolve the material assumptions.</p>
<ol><li>Reconcile prices, operating and capital expenditure, royalty payments and relief with cited public records before qualifying actual financial performance; issue 651 retains the assumption and model-extension scope.</li>
<li>Refresh the production snapshot before a later analysis window is used.</li><li>Qualify recoverable reserves under issue 973 before calculating a full-cycle value.</li></ol>
''') + section("references", "9 References", f'''
<p>The published references identify the federal filings. Internal references identify the calculation and its retained input basis.</p>
<h3>9.1 Published references</h3><p>BSEE OGOR-A production archives, API well/completion filings and deep-water field/lease filings, retrieved on the dates retained in the source manifest:</p><ul>{urls}</ul>
<h3>9.2 Internal references</h3><ul>
<li>[I1] worldenergydata 0.1.0: lower_tertiary.npv monthly financial and field-summary functions; lower_tertiary.life_to_date unit conversion and presentation. Source and executed-code digests are retained in the output manifest.</li>
<li>[I2] reports/lower_tertiary/2026-06-17-julia-granular-economics-summary.md: field selection only.</li>
<li>[I3] data/economics/julia_life_to_date/criteria.json: retained analysis and reporting criteria.</li>
<li>[I4] data/economics/julia_life_to_date/basis.json and sources.json: assumptions, raw-row provenance and source digests.</li></ul>
''')


def render(result, revision):
    """Render the ten-section analysis and data-driven revision history."""
    from html import escape

    history = revision["history"]
    if not history or history[-1]["revision"] != revision["revision"]:
        raise ValueError("revision history does not match declared revision")
    rows = ''.join('<tr>' + ''.join(f'<td>{escape(str(row[key]))}</td>' for key in ("revision", "date", "change")) + '</tr>' for row in history)
    contents = [("summary", "Executive Summary"), ("introduction", "Introduction"),
                ("design-data", "Design Data"), ("method", "Analysis Methodology"),
                ("results", "Detailed Results"), ("findings", "Key Findings"),
                ("limitations", "Limitations"), ("recommendations", "Recommendations"),
                ("references", "References"), ("symbols", "Acronyms and Symbols")]
    nav = ''.join(f'<li><a href="#{key}">{title}</a></li>' for key, title in contents)
    revision_html = f'<section id="revision-history"><h2>Revision history</h2><table><thead><tr><th>Revision</th><th>Date</th><th>What changed and why</th></tr></thead><tbody>{rows}</tbody></table><p class="caption">Table 0.1 – Revision history.</p></section>\n'
    symbols = section("symbols", "10 Acronyms and Symbols", '''
<p>The symbols distinguish reported volumes from scenario monetary values. Positive cashflow is an inflow; negative discounted balance indicates a deficit against assumed capital.</p>
<dl><dt>BSEE</dt><dd>Bureau of Safety and Environmental Enforcement.</dd><dt>OGOR-A</dt><dd>Oil and Gas Operations Report, Part A.</dd><dt>MMbbl</dt><dd>Million barrels of oil.</dd><dt>Mcf</dt><dd>Thousand standard cubic feet of gas.</dd><dt>BCF</dt><dd>Billion standard cubic feet of gas.</dd><dt>boe</dt><dd>Barrel of oil equivalent under the assumed energy conversion.</dd><dt>LTD</dt><dd>Life-to-date: observed production only.</dd><dt>NPV</dt><dd>Net present value, USD; the reported discounted balance is restricted to the stated assumption case.</dd></dl>
''')
    return f'''<!DOCTYPE html>
<html lang="en" data-revision="{escape(revision['revision'], quote=True)}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Julia life-to-date field economics analysis</title>
<style>:root{{--navy:#0B3D91;--teal:#0f8a7e;--ink:#13233f;--muted:#5b6b86;--line:#dbe4f0;--soft:#f4f8fc}}*{{box-sizing:border-box}}body{{font:16px/1.6 system-ui,sans-serif;color:var(--ink);background:var(--soft);margin:0}}main{{max-width:960px;margin:auto;padding:32px;background:white}}h1,h2{{color:var(--navy);line-height:1.25}}h2{{border-top:2px solid var(--line);padding-top:20px}}h3{{color:var(--teal)}}table{{border-collapse:collapse;width:100%;table-layout:fixed;font-size:15px}}th,td{{border-bottom:1px solid var(--line);padding:10px;text-align:left;overflow-wrap:anywhere;vertical-align:top}}th{{background:var(--soft)}}a{{color:var(--navy);overflow-wrap:anywhere}}.caption{{font-size:14px;color:var(--muted)}}dt{{font-weight:600}}dd{{margin-bottom:8px}}@media(max-width:600px){{main{{padding:16px}}table{{font-size:13px}}}}</style></head>
<body><main><h1>Julia life-to-date field economics analysis</h1><nav aria-label="Contents"><h2>Contents</h2><ol>{nav}</ol></nav>
{summary(result)}{revision_html}{introduction_and_basis(result)}{methodology_and_results(result)}{findings_and_limits(result)}{recommendations_and_references(result)}{symbols}</main></body>
</html>
'''


def snapshot(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file()}


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def build(data_dir, output_dir):
    """Build deterministic results, a self-contained report and its manifest."""
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    if output_dir.resolve().is_relative_to(data_dir.resolve()):
        raise ValueError("output directory overlaps retained inputs")
    before = snapshot(data_dir)
    execution = verify_criteria(data_dir)
    result = analyse(data_dir)
    revision = json.loads((data_dir / "revision.json").read_text())
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analysis.html").write_text(render(result, revision), encoding="utf-8")
    write_json(output_dir / "results.json", result)
    if snapshot(data_dir) != before:
        raise ValueError("input bytes changed during calculation")
    code_paths = [
        "packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py",
        "packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py",
        "scripts/lower_tertiary/collect_life_to_date.py",
        "scripts/lower_tertiary/fetch_life_to_date.py",
        "scripts/lower_tertiary/build_life_to_date.py",
    ]
    root = Path(__file__).resolve().parents[5]
    manifest = {
        "owner_repo": "worldenergydata", "dataset_id": "julia_life_to_date",
        "input_dataset_path": "data/economics/julia_life_to_date",
        "source_revision": result["source_revision"], "revision": revision["revision"],
        "scope": result["scope"], "data_through": result["end"],
        "execution": execution,
        "criteria_version": json.loads((data_dir / "criteria.json").read_text())["version"],
        "inputs": [{"path": path, "sha256": value, "bytes": (data_dir / path).stat().st_size} for path, value in before.items()],
        "code": [{"path": path, "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest()}
                 for path in code_paths],
        "outputs": [{"path": path, "bytes": (output_dir / path).stat().st_size,
                     "sha256": hashlib.sha256((output_dir / path).read_bytes()).hexdigest()}
                    for path in ("analysis.html", "results.json")],
        "sources": result["sources"],
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def verify_criteria(data_dir):
    """Bind acceptance to the criterion bytes established before the first run."""
    from datetime import datetime

    execution = json.loads((data_dir / "execution.json").read_text())
    digest = hashlib.sha256((data_dir / "criteria.json").read_bytes()).hexdigest()
    if digest != execution["criteria_sha256"]:
        raise ValueError("criteria digest does not match the established record")
    established = datetime.fromisoformat(execution["criteria_established_at"])
    started = datetime.fromisoformat(execution["first_economic_run_started_at"])
    if established >= started:
        raise ValueError("criteria were not established before the first run")
    return execution


def verify_assumptions(assumptions):
    """Enforce the units, labels and fixed conventions of this scenario."""
    import math

    units = {
        "oil_price": "USD/bbl", "gas_price": "USD/Mcf", "royalty_rate": "1",
        "income_tax_rate": "1", "opex_per_boe": "USD/boe",
        "capex_usd_mm": "USD million", "discount_rate": "1",
        "gas_boe_conversion": "Mcf/boe",
    }
    if set(assumptions) != set(units):
        raise ValueError("assumption set does not match the scenario")
    for key, unit in units.items():
        item = assumptions[key]
        if item.get("status") != "ASSUMED" or not item.get("reason") or not item.get("basis"):
            raise ValueError(f"assumption qualification is missing: {key}")
        value = item["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"assumption value is invalid: {key}")
        if item["unit"] != unit:
            raise ValueError(f"assumption unit is invalid: {key}")
    if assumptions["royalty_rate"]["value"] > 1:
        raise ValueError("assumption royalty fraction exceeds one")
    if assumptions["income_tax_rate"]["value"] != 0:
        raise ValueError("assumption tax is outside the pre-tax scope")
    if assumptions["gas_boe_conversion"]["value"] != 6:
        raise ValueError("assumption gas conversion differs from the existing engine")


def verify_field_identity(verified, basis):
    """Bind the demonstration field to its public field and lease identifiers."""
    expected = (basis["field"], basis["lease"], basis["field_code"], basis["block"])
    if expected != ("Julia", "G20351", "WR627", "WR 584"):
        raise ValueError("field is outside the supported demonstration")
    frame = pd.read_csv(io.BytesIO(verified["raw/field.csv"]), dtype=str, keep_default_na=False)
    if frame.empty or set(frame.FLD_NICK_NAME) != {basis["field"]} or set(frame.FIELD_NAME_CODE) != {basis["field_code"]}:
        raise ValueError("field identifiers do not match the public filing")
    primary = frame.loc[frame.LEASE_NUMBER.str.strip() == basis["lease"]]
    if primary.empty or not ((primary.AREA_CODE.str.strip() + " " + primary.BLOCK_NUMBER.str.strip()) == basis["block"]).any():
        raise ValueError("field identifiers do not match the public filing")
    leases = set(frame.LEASE_NUMBER.str.strip())
    for path, blob in verified.items():
        if path.startswith("raw/ogora"):
            rows = pd.read_csv(io.BytesIO(blob), names=OGOR_COLUMN_NAMES, dtype=str, keep_default_na=False)
            leases.update(rows.LEASE_NUMBER.str.strip())
        elif path == "raw/wells.csv":
            rows = pd.read_csv(io.BytesIO(blob), dtype=str, keep_default_na=False)
            leases.update(rows.SURF_LEASE_NUMBER.str.strip())
            leases.update(rows.BOTM_LEASE_NUMBER.str.strip())
        elif path == "raw/completions.csv":
            rows = pd.read_csv(io.BytesIO(blob), dtype=str, keep_default_na=False)
            leases.update(rows.LEASE_NUMBER.str.strip())
    leases.discard("")
    if leases != set(basis["leases"]):
        raise ValueError("field lease set does not match the retained filings")


def verify_completion_coverage(verified, basis, production):
    """Require a production row or an explicit exclusion for every COM field well."""
    wells = pd.read_csv(io.BytesIO(verified["raw/wells.csv"]), dtype=str, keep_default_na=False)
    if set(wells.BOTM_FLD_NAME_CD.str.strip()) != {basis["field_code"]}:
        raise ValueError("well field does not agree with basis")
    completed = set(wells.loc[wells.BOREHOLE_STAT_CD.str.strip() == "COM", "API_WELL_NUMBER"].str.strip())
    produced = set(production.API_WELL_NUMBER.str.strip())
    missing = completed - produced
    exclusions = basis.get("excluded_completions", [])
    excluded = {item["api_well_number"] for item in exclusions if item.get("reason", "").strip()}
    if missing != excluded or len(exclusions) != len(excluded):
        raise ValueError("completion coverage requires an explicit exclusion reason")
    return {"checked_count": len(completed), "completed": sorted(completed),
            "produced": sorted(completed & produced), "excluded": exclusions}
