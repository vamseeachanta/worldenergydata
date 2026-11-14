"""Exercise the real chain and engine; only the live download is substituted."""

import copy
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "examples/workflows/ukcs-reference-report"


@pytest.fixture(autouse=True)
def no_http(monkeypatch):
    import requests

    def refused(*args, **kwargs):
        raise AssertionError("HTTP is forbidden in workflow unit tests")

    monkeypatch.setattr(requests.sessions.Session, "request", refused)


@pytest.fixture
def cfg(tmp_path):
    tmp_path.joinpath("production.csv").write_text(
        "FIELDNAME,PERIODYR,PERIODMNTH,OILPRODMAS,AGASPROKSM,DGASPROKSM,WATPRODVOL\n"
        "FORTIES,2024,1,1000,25,5,100\nFORTIES,2024,2,1100,28,6,120\n"
    )
    return {
        "basename": "ukcs",
        "meta": {"label": "test_ukcs"},
        "Analysis": {
            "analysis_root_folder": str(tmp_path),
            "result_folder": str(tmp_path / "outputs"),
        },
        "data": {"source": "csv", "input_path": "production.csv"},
        "report": {
            "field_name": "Forties",
            "field_meta": {
                "field_name": "FORTIES",
                "water_depth_m": 128.0,
                "source": "NSTA",
            },
            "oil_price_usd_bbl": 75.0,
        },
    }


def route(cfg):
    from worldenergydata.ukcs.ukcs import Ukcs

    return Ukcs().router(cfg)


def read_facts(cfg):
    return json.loads(Path(cfg["ukcs"]["facts_json"]).read_text())


def test_csv_workflow_runs_without_http_and_records_outputs(cfg):
    result = route(cfg)
    assert result["basename"] == "ukcs"
    assert result["ukcs"]["status"] == "completed"
    facts = read_facts(result)
    assert facts["provenance"] == "fixture"
    assert facts["coverage"]["row_count"] == 2
    assert facts["source"]["refreshed_at"] is None
    assert len(facts["source"]["raw_sha256"]["production.csv"]) == 64
    assert facts["input_echo"] == cfg["report"]
    assert Path(result["ukcs"]["report_html"]).parent == Path(
        cfg["Analysis"]["result_folder"]
    )


@pytest.mark.parametrize(
    "change",
    [
        {"data": {"source": "unknown"}},
        {"data": {"source": "csv"}},
        {"data": {"source": "csv", "input_path": "../production.csv"}},
        {"meta": {"label": "../escape"}},
        {"report": {"field_name": ""}},
        {"report": {"field_name": "Forties", "field_meta": {"field_name": "Buzzard"}}},
    ],
)
def test_invalid_configuration_fails_before_outputs(cfg, change):
    cfg.update(change)
    with pytest.raises(ValueError):
        route(cfg)
    assert not Path(cfg["Analysis"]["result_folder"]).exists()


def test_unavailable_field_is_not_reported_as_zero_production(cfg):
    cfg["report"]["field_name"] = "Missing"
    cfg["report"]["field_meta"]["field_name"] = "Missing"
    with pytest.raises(ValueError, match="production"):
        route(cfg)
    assert not Path(cfg["Analysis"]["result_folder"]).exists()


@pytest.mark.parametrize("price", [-1, float("nan"), float("inf"), True, "invalid"])
def test_invalid_price_is_rejected(cfg, price):
    cfg["report"]["oil_price_usd_bbl"] = price
    with pytest.raises(ValueError, match="price"):
        route(cfg)


def test_sparse_metadata_keeps_depth_unknown(cfg):
    cfg["report"]["field_meta"].pop("water_depth_m")
    facts = read_facts(route(cfg))
    assert facts["field_concept"]["water_depth_m"] is None


def test_live_cache_proves_timestamp_and_records_download_controls(cfg, monkeypatch):
    from worldenergydata.ukcs.production.nsta_client import NSTAClient

    raw = pd.read_csv(Path(cfg["Analysis"]["analysis_root_folder"]) / "production.csv")

    def download(self, year, dataset="monthly", force_refresh=False, max_records=None):
        assert year in [2023, 2024] and dataset == "monthly"
        assert force_refresh is True and max_records == 10
        rows = raw.assign(PERIODYR=year)
        rows.to_csv(self.cache_dir / f"nsta_production_{year}_monthly.csv", index=False)
        return rows

    monkeypatch.setattr(NSTAClient, "download", download)
    cfg["data"] = {
        "source": "nsta_live",
        "cache_dir": "cache",
        "year": [2023, 2024],
        "force_refresh": True,
        "max_records": 10,
    }
    facts = read_facts(route(cfg))
    assert facts["provenance"] == "nsta_live"
    assert facts["coverage"] == {
        "row_count": 4,
        "first_period": "2023-01",
        "last_period": "2024-02",
    }
    assert facts["source"]["refreshed_at"]
    assert len(facts["source"]["raw_sha256"]) == 2
    assert facts["source"]["max_records_per_year"] == 10


@pytest.mark.parametrize(
    "data",
    [
        {"source": "nsta_live", "year": 2024},
        {"source": "nsta_live", "cache_dir": "cache"},
        {"source": "nsta_live", "cache_dir": "cache", "year": []},
        {"source": "nsta_live", "cache_dir": "cache", "year": True},
        {"source": "nsta_live", "cache_dir": "cache", "year": 2024, "max_records": 0},
        {
            "source": "nsta_live",
            "cache_dir": "cache",
            "year": 2024,
            "force_refresh": "false",
        },
        {"source": "nsta_live", "cache_dir": "../escape", "year": 2024},
    ],
)
def test_live_requires_explicit_valid_cache_and_year(cfg, data):
    cfg["data"] = data
    with pytest.raises(ValueError):
        route(cfg)
    assert not Path(cfg["Analysis"]["result_folder"]).exists()


def test_download_without_cache_evidence_cannot_claim_live(cfg, monkeypatch):
    from worldenergydata.ukcs.production.nsta_client import NSTAClient

    raw = pd.read_csv(Path(cfg["Analysis"]["analysis_root_folder"]) / "production.csv")
    monkeypatch.setattr(NSTAClient, "download", lambda *a, **k: raw)
    cfg["data"] = {"source": "nsta_live", "cache_dir": "cache", "year": 2024}
    with pytest.raises(ValueError, match="cache"):
        route(cfg)
    assert not Path(cfg["Analysis"]["result_folder"]).exists()


def test_engine_example_and_embed_stay_under_injected_root(tmp_path):
    from worldenergydata.engine import engine

    local_example = tmp_path / "example"
    local_example.mkdir()
    for name in ("input.yml", "sample_nsta_production.csv"):
        shutil.copy2(EXAMPLE / name, local_example / name)
    result = engine(inputfile=str(local_example / "input.yml"))
    assert read_facts(result)["coverage"]["row_count"] == 12
    embed_root = tmp_path / "embedded"
    embed_root.mkdir()
    shutil.copy2(EXAMPLE / "sample_nsta_production.csv", embed_root)
    original = yaml.safe_load((EXAMPLE / "input.yml").read_text())
    preserved = copy.deepcopy(original)
    result = engine(
        cfg=original, embed=True, root_folder=str(embed_root), log_to_file=False
    )
    assert original == preserved
    assert read_facts(result)["provenance"] == "fixture"
    assert Path(result["ukcs"]["facts_json"]).is_relative_to(embed_root)


def test_registry_keeps_ukcs_fixture_only():
    rows = yaml.safe_load((ROOT / "docs/registry/workflows.yaml").read_text())[
        "workflows"
    ]
    row = next((r for r in rows if r["id"] == "ukcs-reference-report"), None)
    assert row is not None, "UKCS report must be discoverable as a durable workflow"
    assert row["data_source"]["network_required"] is False
    assert row["runtime"] == "offline"
    assert row["assertions"]["json"][0]["equals"] == {
        "economics_label": "chain_plumbing_pre_tax",
        "provenance": "fixture",
    }


def test_live_cache_paths_are_ignored():
    import subprocess

    paths = [
        "packages/worldenergydata-ukcs/src/worldenergydata/ukcs/data/nsta_production_2024_monthly.csv",
        "data/modules/ukcs/raw/nsta_production_2024_monthly.csv",
        "data/modules/ukcs/normalized/production.parquet",
        "examples/workflows/ukcs-reference-report/data/modules/ukcs/raw/nsta_production_2024_monthly.csv",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"],
        input="\n".join(paths),
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert set(result.stdout.splitlines()) == set(paths)


def test_live_cache_file_cannot_escape_root_via_symlink(cfg, tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    external = tmp_path.parent / (tmp_path.name + "-outside.csv")
    evidence = (tmp_path / "production.csv").read_text()
    external.write_text(evidence)
    try:
        (cache / "nsta_production_2024_monthly.csv").symlink_to(external)
        cfg["data"] = {"source": "nsta_live", "cache_dir": "cache", "year": 2024}
        with pytest.raises(ValueError, match="cache"):
            route(cfg)
        assert external.read_text() == evidence
        assert not Path(cfg["Analysis"]["result_folder"]).exists()
    finally:
        external.unlink()
