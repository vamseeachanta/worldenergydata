"""Offline workflow tests; HTTP is forbidden except for an injected fake client."""

import copy
import json
from pathlib import Path

import pandas as pd
import pytest
import requests
import yaml

from worldenergydata.ukcs.ukcs import Ukcs

EXAMPLE = (
    Path(__file__).resolve().parents[3] / "examples/workflows/ukcs-reference-report"
)


@pytest.fixture(autouse=True)
def no_http(monkeypatch):
    def reject(*args, **kwargs):
        pytest.fail("Unit tests must never use HTTP")

    monkeypatch.setattr(requests.sessions.Session, "request", reject)


@pytest.fixture
def cfg(tmp_path):
    config = yaml.safe_load((EXAMPLE / "input.yml").read_text())
    config["Analysis"] = {
        "analysis_root_folder": str(EXAMPLE),
        "result_folder": str(tmp_path / "results"),
    }
    return config


def test_offline_router_writes_under_result_root(cfg, tmp_path):
    """Invented oil inputs are 100 tonnes/month for 12 months.

    Hand calculation: 12 * 100 * 7.33 = 8,796 bbl, then * 75 = 659,700 USD
    gross oil revenue. Factor: common.units.OilUnits.TONNE_TO_BBL, repository
    conversion registry (generic approximation, not field density validation).
    Price and production are explicit synthetic scenario inputs, not data.
    """
    result = Ukcs().router(cfg)
    assert result is cfg and result["basename"] == "ukcs"
    outputs = result["ukcs"]["outputs"]
    facts = json.loads(Path(outputs["facts_json"]).read_text())
    assert facts["provenance"] == "fixture"
    assert facts["pre_tax_metrics"]["gross_revenue_usd"] == pytest.approx(659700)
    assert sum(r["oil_bbl"] for r in facts["production_history"]) == pytest.approx(8796)
    assert facts["coverage"]["month_count"] == 12
    assert all(Path(path).parent == tmp_path / "results" for path in outputs.values())


def fake_live(monkeypatch, raw, *, write_cache=True):
    class FakeClient:
        def __init__(self, cache_dir):
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        def download(self, year, **kwargs):
            assert year == 2024
            assert kwargs["max_records"] == 24
            assert kwargs["force_refresh"] is True
            if write_cache:
                raw.to_csv(
                    self.cache_dir / f"nsta_production_{year}_monthly.csv", index=False
                )
            return raw

    monkeypatch.setattr("worldenergydata.ukcs.ukcs.NSTAClient", FakeClient)


def live_config(cfg, tmp_path):
    cfg["data"] = {
        "source": "nsta_live",
        "cache_dir": str(tmp_path / "cache"),
        "year": 2024,
        "max_records": 24,
        "force_refresh": True,
    }
    return cfg


def test_live_cache_evidence_and_selection(monkeypatch, cfg, tmp_path):
    raw = pd.read_csv(EXAMPLE / "sample_nsta_production.csv")
    fake_live(monkeypatch, raw)
    facts = Ukcs().run(live_config(cfg, tmp_path))
    assert facts["provenance"] == "nsta_live"
    assert facts["source"]["refreshed_at"]
    evidence = facts["source"]["evidence"]
    assert len(evidence["sha256"]) == 64
    assert evidence["cache_verified"] is True
    assert evidence["coverage_status"] == "bounded_extract_not_complete"
    assert evidence["source_row_count"] == 12


def test_live_requires_cache_file(monkeypatch, cfg, tmp_path):
    raw = pd.read_csv(EXAMPLE / "sample_nsta_production.csv")
    fake_live(monkeypatch, raw, write_cache=False)
    with pytest.raises(ValueError, match="cache"):
        Ukcs().run(live_config(cfg, tmp_path))


@pytest.mark.parametrize(
    "key,value",
    [
        ("year", None),
        ("year", True),
        ("max_records", 0),
        ("max_records", -1),
        ("max_records", True),
        ("cache_dir", ""),
    ],
)
def test_invalid_live_config_fails_before_download(cfg, tmp_path, key, value):
    live_config(cfg, tmp_path)["data"][key] = value
    with pytest.raises(ValueError):
        Ukcs().run(cfg)


def test_missing_field_never_silently_runs_mock(cfg):
    cfg["report"]["field_name"] = "Missing"
    cfg["report"]["field_meta"]["field_name"] = "Missing"
    with pytest.raises(ValueError, match="No production"):
        Ukcs().run(cfg)


def test_unknown_source_rejected(cfg):
    cfg["data"]["source"] = "mock"
    with pytest.raises(ValueError, match="source"):
        Ukcs().run(cfg)


@pytest.mark.parametrize("label", ["../escape", "a/b", "a\\b"])
def test_output_label_cannot_escape_result_root(cfg, label):
    cfg["meta"]["label"] = label
    with pytest.raises(ValueError, match="label"):
        Ukcs().router(cfg)


def test_required_price_cannot_use_inherited_default(cfg):
    del cfg["report"]["oil_price_usd_bbl"]
    with pytest.raises(ValueError, match="oil_price"):
        Ukcs().run(cfg)


@pytest.mark.parametrize("price", [float("nan"), float("inf"), -1, True])
def test_invalid_price_rejected(cfg, price):
    cfg["report"]["oil_price_usd_bbl"] = price
    with pytest.raises(ValueError, match="oil_price"):
        Ukcs().run(cfg)


def test_bad_period_and_negative_production_rejected(cfg, monkeypatch):
    raw = pd.read_csv(EXAMPLE / "sample_nsta_production.csv")
    raw.loc[0, "PERIODMNTH"] = 13
    monkeypatch.setattr(pd, "read_csv", lambda *a, **k: raw)
    with pytest.raises(ValueError, match="month"):
        Ukcs().run(cfg)
    raw.loc[0, "PERIODMNTH"] = 1
    raw.loc[0, "OILPRODMAS"] = -1
    with pytest.raises(ValueError, match="nonnegative"):
        Ukcs().run(cfg)


def test_field_metadata_must_match_selection(cfg):
    cfg["report"]["field_meta"]["field_name"] = "Another"
    with pytest.raises(ValueError, match="field_meta"):
        Ukcs().run(cfg)


def test_engine_embed_isolated(cfg, tmp_path):
    from worldenergydata.engine import engine

    config = copy.deepcopy(cfg)
    config["default"] = {"log_level": "INFO", "config": {"overwrite": {"output": True}}}
    config["data"]["input_path"] = str(EXAMPLE / "sample_nsta_production.csv")
    result = engine(
        cfg=config,
        embed=True,
        root_folder=str(tmp_path / "embedded"),
        log_to_file=False,
    )
    assert result["basename"] == "ukcs"
    for path in result["ukcs"]["outputs"].values():
        assert Path(path).is_relative_to(tmp_path / "embedded")
        assert Path(path).is_file()


def test_live_retains_digest_snapshot(monkeypatch, cfg, tmp_path):
    """The retained raw bytes, digest and published facts must identify one input."""
    import hashlib

    raw = pd.read_csv(EXAMPLE / "sample_nsta_production.csv")
    fake_live(monkeypatch, raw)
    facts = Ukcs().run(live_config(cfg, tmp_path))
    cache_bytes = (tmp_path / "cache/nsta_production_2024_monthly.csv").read_bytes()
    digest = hashlib.sha256(cache_bytes).hexdigest()
    assert facts["source"]["evidence"]["sha256"] == digest
    assert (tmp_path / "cache/snapshots" / f"{digest}.csv").read_bytes() == cache_bytes


def test_cached_year_mismatch_rejected(monkeypatch, cfg, tmp_path):
    raw = pd.read_csv(EXAMPLE / "sample_nsta_production.csv")
    raw["PERIODYR"] = 2023
    fake_live(monkeypatch, raw)
    with pytest.raises(ValueError, match="year"):
        Ukcs().run(live_config(cfg, tmp_path))


def test_live_multiple_years_and_oldest_timestamp(monkeypatch, cfg, tmp_path):
    import os

    raw = pd.read_csv(EXAMPLE / "sample_nsta_production.csv")

    class MultiYearClient:
        def __init__(self, cache_dir):
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        def download(self, year, **kwargs):
            frame = raw.assign(PERIODYR=year)
            path = self.cache_dir / f"nsta_production_{year}_monthly.csv"
            frame.to_csv(path, index=False)
            # Synthetic timestamps order two cache writes without wall-clock sleeps.
            os.utime(path, (year, year))
            return frame

    monkeypatch.setattr("worldenergydata.ukcs.ukcs.NSTAClient", MultiYearClient)
    live_config(cfg, tmp_path)["data"]["year"] = [2024, 2023]
    facts = Ukcs().run(cfg)
    assert facts["coverage"]["month_count"] == 24
    assert facts["source"]["refreshed_at"] == min(
        c["refreshed_at"] for c in facts["source"]["evidence"]["caches"]
    )


@pytest.mark.parametrize(
    "start,end", [("2024-00", None), (None, "2024-13"), ("2024-02", "2024-01")]
)
def test_period_boundaries_must_be_valid_and_ordered(cfg, start, end):
    cfg["report"].update(start=start, end=end)
    with pytest.raises(ValueError, match="period"):
        Ukcs().run(cfg)
