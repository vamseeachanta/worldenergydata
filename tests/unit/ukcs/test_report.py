"""UKCS facts and HTML contracts: fixtures cannot be promoted to live data."""

import json
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from bs4 import BeautifulSoup

from worldenergydata.production.unified.adapters.ukcs_adapter import UkcsAdapter
from worldenergydata.ukcs.production.field_production import UKCSFieldProductionLoader
from worldenergydata.ukcs.production.nsta_client import DEFAULT_BASE_URL
from worldenergydata.ukcs.reference_chain import run_ukcs_reference_chain


@pytest.fixture(autouse=True)
def no_http(monkeypatch):
    import requests

    def refused(*args, **kwargs):
        raise AssertionError("HTTP is forbidden in report unit tests")

    monkeypatch.setattr(requests.sessions.Session, "request", refused)


@pytest.fixture
def chain():
    raw = pd.DataFrame(
        [
            dict(
                FIELDNAME="FORTIES",
                PERIODYR=2024,
                PERIODMNTH=2,
                OILPRODMAS=1100.0,
                AGASPROKSM=28.0,
                DGASPROKSM=6.0,
                WATPRODVOL=120.0,
            ),
            dict(
                FIELDNAME="FORTIES",
                PERIODYR=2024,
                PERIODMNTH=1,
                OILPRODMAS=1000.0,
                AGASPROKSM=25.0,
                DGASPROKSM=5.0,
                WATPRODVOL=100.0,
            ),
        ]
    )

    class Loader:
        def load_field_production(self, field_name):
            return UKCSFieldProductionLoader().load(raw)

    return run_ukcs_reference_chain(
        adapter=UkcsAdapter(loader=Loader()),
        field_name="Forties",
        field_meta={"field_name": "FORTIES", "water_depth_m": 128.0, "source": "NSTA"},
    )


def facts_for(chain, **kwargs):
    from worldenergydata.ukcs.report import build_report_facts

    return build_report_facts(
        chain,
        source_url=DEFAULT_BASE_URL,
        licence="NSTA Open User Licence",
        input_echo={"field_name": "Forties", "oil_price_usd_bbl": np.float64(75.0)},
        **kwargs,
    )


def test_facts_flatten_real_chain_in_month_order(chain):
    chain["pre_tax_metrics"]["months"] = np.int64(2)
    facts = facts_for(chain, provenance="fixture", refreshed_at=None)
    json.dumps(facts, allow_nan=False)
    assert facts["field_name"] == "Forties"
    assert facts["coverage"] == {
        "row_count": 2,
        "first_period": "2024-01",
        "last_period": "2024-02",
    }
    assert [r["period"] for r in facts["production_history"]] == ["2024-01", "2024-02"]
    assert facts["production_history"][0]["oil_bbl"] == pytest.approx(7330.0)
    assert facts["production_history"][0]["gas_mcf"] == pytest.approx(30.0 * 35.3147)
    assert facts["pre_tax_metrics"]["months"] == 2.0
    assert (
        facts["ranked_concepts"][0]["total_score"]
        == chain["ranked_concepts"][0].total_score
    )
    assert (
        facts["ranked_concepts"][0]["rationale"]
        == chain["ranked_concepts"][0].rationale
    )
    assert all(r["name"] for r in facts["ranked_concepts"])
    assert facts["field_concept"]["water_depth_m"] == 128.0
    assert facts["economics_label"] == "chain_plumbing_pre_tax"
    assert facts["source"]["url"] == DEFAULT_BASE_URL
    assert facts["source"]["refreshed_at"] is None
    assert facts["source"]["source_id"] == "uk-nsta-opendata"
    assert (
        datetime.fromisoformat(facts["generated_at"]).utcoffset().total_seconds() == 0
    )


@pytest.mark.parametrize("provenance", [None, "unknown", "seed", "real", "fixture"])
def test_unknown_provenance_fails_closed(chain, provenance):
    assert (
        facts_for(chain, provenance=provenance, refreshed_at=None)["provenance"]
        == "fixture"
    )


@pytest.mark.parametrize("timestamp", [None, "", "invalid", "2024-01-01"])
def test_live_requires_aware_refresh_timestamp(chain, timestamp):
    assert (
        facts_for(chain, provenance="nsta_live", refreshed_at=timestamp)["provenance"]
        == "fixture"
    )


def test_live_requires_nsta_source_tags(chain):
    chain["unified_production"].loc[0, "source"] = "ukcs_mock"
    facts = facts_for(
        chain, provenance="nsta_live", refreshed_at="2026-11-13T10:00:00+00:00"
    )
    assert facts["provenance"] == "fixture"


def test_non_finite_measurements_remain_unknown(chain):
    chain["unified_production"].loc[0, "water_bbl"] = np.nan
    chain["pre_tax_metrics"]["net_cashflow_usd"] = np.inf
    facts = facts_for(chain, provenance="fixture", refreshed_at=None)
    assert facts["production_history"][1]["water_bbl"] is None
    assert facts["pre_tax_metrics"]["net_cashflow_usd"] is None
    json.dumps(facts, allow_nan=False)


def test_empty_coverage_does_not_fabricate_zero_production(chain):
    chain["unified_production"] = chain["unified_production"].iloc[:0]
    facts = facts_for(
        chain, provenance="nsta_live", refreshed_at="2026-11-13T10:00:00Z"
    )
    assert facts["coverage"] == {
        "row_count": 0,
        "first_period": None,
        "last_period": None,
    }
    assert facts["production_history"] == []
    assert facts["provenance"] == "fixture"


@pytest.mark.parametrize(
    "provenance, badge", [("fixture", "fixture/seed"), ("nsta_live", "real: NSTA live")]
)
def test_html_is_self_contained_and_labels_pre_tax(chain, provenance, badge):
    from worldenergydata.ukcs.report import render_report_html

    facts = facts_for(chain, provenance=provenance, refreshed_at="2026-11-13T10:00:00Z")
    html = render_report_html(facts)
    soup = BeautifulSoup(html, "html.parser")
    assert badge in soup.get_text()
    assert "chain_plumbing_pre_tax" in soup.get_text()
    assert "NOT a UK investment NPV" in soup.get_text()
    assert "capital inputs are not supplied" in soup.get_text()
    assert "After-tax UK fiscal treatment is deferred" in soup.get_text()
    assert soup.find(
        "a", href="https://github.com/vamseeachanta/worldenergydata/issues/736"
    )
    assert soup.find("svg") and soup.find("details")
    assert not soup.select("script[src], link[href], img[src], iframe[src]")
    assert "NSTA Open User Licence" in soup.get_text()
    assert "2024-01" in soup.get_text()
    for section in (
        "Source coverage",
        "Production history",
        "Concept screening",
        "Pre-tax metrics",
    ):
        assert section in soup.get_text()


def test_html_escapes_untrusted_values_and_links(chain):
    from worldenergydata.ukcs.report import render_report_html

    facts = facts_for(chain, provenance="fixture", refreshed_at=None)
    facts["field_name"] = '<img src=x onerror="alert(1)">'
    facts["source"]["url"] = "javascript:alert(1)"
    facts["ranked_concepts"][0]["rationale"] = ["<script>alert(1)</script>"]
    facts["input_echo"]["field_name"] = "</pre><script>alert(1)</script>"
    soup = BeautifulSoup(render_report_html(facts), "html.parser")
    assert not soup.find("img") and not soup.find("script")
    assert not soup.select('a[href^="javascript:"]')
    assert '<img src=x onerror="alert(1)">' in soup.get_text()


def test_generate_report_uses_fixture_and_requested_directory(tmp_path):
    from worldenergydata.ukcs.report import generate_report

    facts = generate_report(output_dir=tmp_path)
    assert facts["provenance"] == "fixture"
    assert facts["coverage"]["row_count"] == 12
    assert json.loads((tmp_path / "_facts.json").read_text()) == facts
    assert (tmp_path / "index.html").is_file()


def test_nullable_missing_source_tag_fails_closed(chain):
    chain["unified_production"]["source"] = pd.Series(["nsta", pd.NA], dtype="string")
    facts = facts_for(
        chain, provenance="nsta_live", refreshed_at="2026-11-13T10:00:00Z"
    )
    assert facts["provenance"] == "fixture"


def test_production_chart_preserves_calendar_gaps(chain):
    import re

    from worldenergydata.ukcs.report import render_report_html

    facts = facts_for(chain, provenance="fixture", refreshed_at=None)
    facts["production_history"] = [
        {"period": "2024-01", "oil_bbl": 100.0, "gas_mcf": 10.0, "water_bbl": 1.0},
        {"period": "2024-02", "oil_bbl": 200.0, "gas_mcf": 20.0, "water_bbl": 2.0},
        {"period": "2024-04", "oil_bbl": 400.0, "gas_mcf": 40.0, "water_bbl": 4.0},
    ]
    soup = BeautifulSoup(render_report_html(facts), "html.parser")
    line = soup.find("svg").find("path", stroke="#176a75")["d"]
    x_values = [float(v) for v in re.findall(r"[ML]([\d.]+),", line)]
    assert x_values == pytest.approx([70.0, 273.333333, 680.0], abs=0.01)


def test_report_tests_deny_http_before_transport(monkeypatch):
    import requests

    def transport_must_not_run(*args, **kwargs):
        raise AssertionError("HTTP reached transport")

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", transport_must_not_run)
    with pytest.raises(AssertionError, match="HTTP is forbidden in report unit tests"):
        requests.Session().get("https://example.invalid/")


def test_committed_live_report_discloses_defaults_and_evidence():
    from worldenergydata.ukcs.report import _REPO_ROOT, render_report_html

    facts = json.loads((_REPO_ROOT / "reports/ukcs_reference/_facts.json").read_text())
    basis = facts["cashflow_basis"]
    assert basis["development_system"] == "subsea15"
    assert basis["variable_opex_usd_per_bbl"] == 12.0
    assert basis["cashflow_window"] == {
        "first_period": "2023-02",
        "last_period": "2025-12",
        "row_count": 35,
    }
    assert basis["applied_costs_usd"]["host_capex"] == 300.0
    assert facts["pre_tax_metrics"]["net_cashflow_usd"] == pytest.approx(
        facts["pre_tax_metrics"]["gross_revenue_usd"]
        - facts["pre_tax_metrics"]["royalty_usd"]
        - sum(basis["applied_costs_usd"].values())
    )
    assert facts["source"]["raw_bytes_retained_in_repository"] is False
    assert facts["source"]["force_refresh"] is True
    assert (
        _REPO_ROOT / "reports/ukcs_reference/index.html"
    ).read_text() == render_report_html(facts)


def test_live_report_discloses_unretained_raw_bytes(chain):
    from worldenergydata.ukcs.report import render_report_html

    facts = facts_for(
        chain, provenance="nsta_live", refreshed_at="2026-11-13T10:00:00Z"
    )
    assert facts["source"]["raw_bytes_retained_in_repository"] is False
    visible = BeautifulSoup(render_report_html(facts), "html.parser").get_text()
    assert "Source bytes are not retained in the repository" in visible
    assert "cannot be re-derived from the digest alone" in visible
