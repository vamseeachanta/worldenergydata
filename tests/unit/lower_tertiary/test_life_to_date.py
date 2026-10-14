"""Life-to-date evidence, numerical and report contracts."""

import hashlib
import json
import shutil
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.lower_tertiary.life_to_date import (
    analyse,
    build,
    load_verified,
    render,
)

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "economics" / "julia_life_to_date"


@pytest.fixture
def dataset(tmp_path):
    target = tmp_path / "data"
    shutil.copytree(DATA, target)
    return target


def test_retained_digests_and_raw_row_counts():
    monthly, basis, provenance = load_verified(DATA)
    assert basis["field"] == "Julia"
    assert basis["lease"] == "G20351"
    assert not monthly.empty
    for source in provenance["files"]:
        raw = (DATA / source["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        assert len(raw.splitlines()) == source["record_count"] + source.get(
            "header_lines", 0
        )
        assert len(source["source_row_numbers"]) == source["record_count"]


def test_corrupt_raw_bytes_fail_closed(dataset):
    path = dataset / "raw" / "ogora2016.csv"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="digest"):
        load_verified(dataset)


def test_missing_year_fails_closed(dataset):
    manifest_path = dataset / "sources.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"] = [
        f for f in manifest["files"] if f["path"] != "raw/ogora2020.csv"
    ]
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="coverage"):
        load_verified(dataset)


def test_duplicate_completion_month_fails_closed(dataset):
    manifest_path = dataset / "sources.json"
    manifest = json.loads(manifest_path.read_text())
    source = next(f for f in manifest["files"] if f["path"] == "raw/ogora2016.csv")
    path = dataset / source["path"]
    path.write_bytes(path.read_bytes() + path.read_bytes().splitlines(keepends=True)[0])
    source["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    source["record_count"] += 1
    source["source_row_numbers"].append(source["source_row_numbers"][0])
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="duplicate"):
        load_verified(dataset)


def test_monthly_mass_balance_and_gas_units():
    monthly, _, _ = load_verified(DATA)
    result = analyse(DATA)
    assert result["metrics"]["oil_mmbbl"] == pytest.approx(monthly.oil_bbl.sum() / 1e6)
    assert result["metrics"]["gas_bcf"] == pytest.approx(monthly.gas_mcf.sum() / 1e6)
    assert result["metrics"]["boe_mmboe"] == pytest.approx(
        (monthly.oil_bbl.sum() + monthly.gas_mcf.sum() / 6) / 1e6
    )
    assert result["months"] == len(monthly)
    assert (
        monthly.date.tolist()
        == pd.date_range(monthly.date.min(), monthly.date.max(), freq="MS").tolist()
    )


def test_price_and_cashflow_arithmetic():
    monthly, basis, _ = load_verified(DATA)
    result = analyse(DATA)
    a = basis["assumptions"]
    revenue = (
        monthly.oil_bbl.sum() * a["oil_price"]["value"]
        + monthly.gas_mcf.sum() * a["gas_price"]["value"]
    )
    royalty = revenue * a["royalty_rate"]["value"]
    opex = (monthly.oil_bbl.sum() + monthly.gas_mcf.sum() / 6) * a["opex_per_boe"][
        "value"
    ]
    metrics = result["metrics"]
    assert metrics["revenue_usd_mm"] == pytest.approx(revenue / 1e6)
    assert metrics["royalty_usd_mm"] == pytest.approx(royalty / 1e6)
    assert metrics["opex_usd_mm"] == pytest.approx(opex / 1e6)
    assert metrics["operating_cashflow_usd_mm"] == pytest.approx(
        (revenue - royalty - opex) / 1e6
    )
    assert metrics["ltd_npv_usd_mm"] == pytest.approx(
        metrics["pv_operations_usd_mm"] - a["capex_usd_mm"]["value"]
    )


def test_no_forecast_or_full_cycle_result():
    result = analyse(DATA)
    assert result["scope"] == "life-to-date, pre-tax assumption scenario"
    assert "eur" not in result
    assert "full_cycle_npv" not in result
    assert all(a["status"] == "ASSUMED" for a in result["assumptions"].values())
    assert all(a["reason"] and a["basis"] for a in result["assumptions"].values())


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.metrics = {}
        self.metric = None
        self.resources = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-metric" in attrs:
            self.metric = attrs["data-metric"]
        if tag in {"script", "link", "img", "iframe", "source", "video", "audio"}:
            self.resources.extend(attrs.get(k) for k in ("src", "href") if attrs.get(k))

    def handle_data(self, data):
        if self.metric:
            self.metrics[self.metric] = data
            self.metric = None


def test_summary_matches_every_module_metric():
    result = analyse(DATA)
    page = Page()
    page.feed(render(result, json.loads((DATA / "revision.json").read_text())))
    assert set(page.metrics) == set(result["summary_metrics"])
    for key, value in result["summary_metrics"].items():
        assert page.metrics[key] == f"{value:,.1f}"
    assert not page.resources


def test_revision_history_immediately_follows_summary():
    result = analyse(DATA)
    revision = json.loads((DATA / "revision.json").read_text())
    html = render(result, revision)
    assert html.index('id="summary"') < html.index('id="revision-history"')
    assert html.index('id="revision-history"') < html.index('id="introduction"')
    assert f'data-revision="{revision["revision"]}"' in html
    assert revision["history"][-1]["revision"] == revision["revision"]
    assert html.count('class="report-section"') == 10


def test_mismatched_revision_is_rejected():
    result = analyse(DATA)
    revision = json.loads((DATA / "revision.json").read_text())
    revision["revision"] = "unexpected"
    with pytest.raises(ValueError, match="revision"):
        render(result, revision)


def test_build_twice_identical_with_valid_output_digests(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    build(DATA, first)
    build(DATA, second)
    for name in ("analysis.html", "results.json", "manifest.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    manifest = json.loads((first / "manifest.json").read_text())
    for output in manifest["outputs"]:
        assert (
            hashlib.sha256((first / output["path"]).read_bytes()).hexdigest()
            == output["sha256"]
        )
    assert (
        manifest["source_revision"]
        == json.loads((DATA / "basis.json").read_text())["source_revision"]
    )


def test_criteria_digest_mismatch_is_rejected(dataset, tmp_path):
    criteria = dataset / "criteria.json"
    criteria.write_bytes(criteria.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="criteria"):
        build(dataset, tmp_path / "out")


def test_criteria_recorded_after_run_is_rejected(dataset, tmp_path):
    path = dataset / "execution.json"
    record = json.loads(path.read_text())
    record["first_economic_run_started_at"] = "1970-01-01T00:00:00Z"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="criteria"):
        build(dataset, tmp_path / "out")


@pytest.mark.parametrize("key", ["gas_boe_conversion", "income_tax_rate", "oil_price"])
def test_assumption_scope_and_labels_are_enforced(dataset, key):
    path = dataset / "basis.json"
    basis = json.loads(path.read_text())
    if key == "gas_boe_conversion":
        basis["assumptions"][key]["value"] += 1
    elif key == "income_tax_rate":
        basis["assumptions"][key]["value"] = basis["assumptions"]["discount_rate"][
            "value"
        ]
    else:
        basis["assumptions"][key]["status"] = "UNVERIFIED"
    path.write_text(json.dumps(basis))
    with pytest.raises(ValueError, match="assumption"):
        analyse(dataset)


def test_field_identity_matches_public_filing(dataset):
    path = dataset / "basis.json"
    basis = json.loads(path.read_text())
    basis["field"] = basis["field_code"]
    path.write_text(json.dumps(basis))
    with pytest.raises(ValueError, match="field"):
        load_verified(dataset)
