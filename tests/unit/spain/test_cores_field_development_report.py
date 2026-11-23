"""Spain CORES field-development report tests (#810)."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.spain.production.cores_live import CoresLiveProductionLoader


def test_load_report_source_validates_scheduler_cache_and_counts(tmp_path):
    from worldenergydata.spain.reports.cores_field_development import (
        load_cores_report_source,
    )

    _write_cache(tmp_path)

    source = load_cores_report_source(tmp_path)

    assert source.metadata["source_url"] == "https://www.cores.es/en/estadisticas"
    assert source.metadata["format"] == "csv"
    assert source.metadata["record_count"] == 4
    assert source.manifest["records_updated"] == 4
    assert set(source.all_production["field_name"]) == {"Ayoluengo", "Gaviota"}
    assert source.workbook_metadata["workbooks"]["oil"]["status_code"] == 200
    assert source.workbook_metadata["workbooks"]["gas"]["byte_count"] == 23456


def test_load_report_source_fails_on_missing_workbook_metadata(tmp_path):
    from worldenergydata.spain.reports.cores_field_development import (
        CoresReportError,
        load_cores_report_source,
    )

    _write_cache(tmp_path)
    (tmp_path / "metadata" / "cores_refresh_metadata.json").unlink()

    with pytest.raises(CoresReportError, match="cores_refresh_metadata.json"):
        load_cores_report_source(tmp_path)


def test_load_report_source_fails_on_row_count_mismatch(tmp_path):
    from worldenergydata.spain.reports.cores_field_development import (
        CoresReportError,
        load_cores_report_source,
    )

    _write_cache(tmp_path, record_count=99)

    with pytest.raises(CoresReportError, match="record_count"):
        load_cores_report_source(tmp_path)


def test_load_report_source_fails_on_scheduler_failure_status(tmp_path):
    from worldenergydata.spain.reports.cores_field_development import (
        CoresReportError,
        load_cores_report_source,
    )

    _write_cache(tmp_path, manifest_status="failed")

    with pytest.raises(CoresReportError, match="manifest.json status"):
        load_cores_report_source(tmp_path)


def test_load_report_source_fails_on_missing_workbook_status_code(tmp_path):
    from worldenergydata.spain.reports.cores_field_development import (
        CoresReportError,
        load_cores_report_source,
    )

    _write_cache(tmp_path, include_oil_status=False)

    with pytest.raises(CoresReportError, match="status_code"):
        load_cores_report_source(tmp_path)


def test_normalized_loader_filters_fields_without_live_loader_side_effects(
    tmp_path, monkeypatch
):
    from worldenergydata.spain.reports.cores_field_development import (
        NormalizedCoresReportLoader,
        load_cores_report_source,
    )

    _write_cache(tmp_path)

    def fail_if_live_loader_is_used(*args, **kwargs):
        raise AssertionError("report read path must not instantiate live XLSX loader")

    monkeypatch.setattr(
        CoresLiveProductionLoader, "__init__", fail_if_live_loader_is_used
    )

    loader = NormalizedCoresReportLoader(load_cores_report_source(tmp_path))

    assert len(loader.load_all_production()) == 4
    field = loader.load_field_production("ayoluengo")
    assert field["field_name"].unique().tolist() == ["Ayoluengo"]
    assert field["oil_bbl"].sum() == pytest.approx(30.0)


def test_build_report_routes_economics_through_spain_cores_adapter(
    tmp_path, monkeypatch
):
    from worldenergydata.production.unified.adapters import spain_cores_adapter
    from worldenergydata.spain.reports.cores_field_development import build_report

    _write_cache(tmp_path)
    calls = []
    original_fetch = spain_cores_adapter.SpainCoresAdapter.fetch

    def spy_fetch(self, query):
        calls.append(type(self.loader).__name__)
        return original_fetch(self, query)

    monkeypatch.setattr(spain_cores_adapter.SpainCoresAdapter, "fetch", spy_fetch)

    build_report(tmp_path)

    assert calls == ["NormalizedCoresReportLoader"]


def test_build_report_runs_ayoluengo_economics_and_defers_gas_only(tmp_path):
    from worldenergydata.spain.reports.cores_field_development import build_report

    _write_cache(tmp_path)

    summary = build_report(tmp_path)

    assert summary["source"]["format"] == "csv"
    assert summary["fields"]["field_count"] == 2
    assert summary["economics"]["evaluated_fields"] == ["Ayoluengo"]
    ayoluengo = summary["economics"]["results"]["Ayoluengo"]
    assert ayoluengo["pre_tax_metrics"]["months"] == 2
    assert ayoluengo["pre_tax_metrics"]["onshore_model_mismatch"] is True
    gaviota = next(
        f for f in summary["fields"]["items"] if f["field_name"] == "Gaviota"
    )
    assert "gas_revenue_deferred_to_issue_808" in gaviota["limitations"]
    assert "field_environment_metadata_not_curated" in gaviota["limitations"]


def test_build_report_includes_field_monthly_series_and_conversion_caveat(tmp_path):
    from worldenergydata.spain.reports.cores_field_development import build_report

    _write_cache(tmp_path)

    summary = build_report(tmp_path)

    ayoluengo = next(
        f for f in summary["fields"]["items"] if f["field_name"] == "Ayoluengo"
    )
    assert ayoluengo["monthly"] == [
        {
            "gas_mcf": 0.0,
            "oil_bbl": 10.0,
            "period": "2025-01",
        },
        {
            "gas_mcf": 0.0,
            "oil_bbl": 20.0,
            "period": "2025-02",
        },
    ]
    assert (
        "oil_tonnes_to_bbl_conversion_deferred_to_issue_807" in summary["limitations"]
    )


def test_render_html_is_self_contained_escaped_and_has_provenance(tmp_path):
    from worldenergydata.spain.reports.cores_field_development import (
        build_report,
        render_spain_cores_html,
    )

    _write_cache(tmp_path, source_url="https://example.test/source</script>")

    html = render_spain_cores_html(build_report(tmp_path))

    assert "<script" in html
    assert "https://example.test/source" in html
    assert "source<\\/script>" in html
    assert "onshore_model_mismatch" in html
    assert "oil_tonnes_to_bbl_conversion_deferred_to_issue_807" in html
    assert "Scheduler status" in html
    assert "spain_cores_refresh" in html
    assert "status_code" in html
    assert "last_modified" in html
    assert "sha256" in html
    assert "spain_cores.json" not in html
    assert "src=" not in html
    assert "/mnt/ace" not in html


def test_build_report_outputs_strict_json_for_sparse_product_rows(tmp_path):
    from worldenergydata.spain.reports.cores_field_development import build_report

    _write_cache(tmp_path)
    out_html = tmp_path / "report.html"
    out_json = tmp_path / "report.json"

    build_report(tmp_path, output_html=out_html, output_json=out_json)

    json_text = out_json.read_text(encoding="utf-8")
    html = out_html.read_text(encoding="utf-8")
    payload = re.search(
        r'<script type="application/json" id="cores-data">(.*?)</script>',
        html,
        re.DOTALL,
    ).group(1)

    def reject_non_standard_constant(value):
        raise AssertionError(f"non-standard JSON constant emitted: {value}")

    assert "NaN" not in json_text
    assert "NaN" not in payload
    json.loads(json_text, parse_constant=reject_non_standard_constant)
    json.loads(payload, parse_constant=reject_non_standard_constant)


def test_cli_writes_html_and_json(tmp_path):
    from scripts.spain.build_cores_field_development_report import main

    _write_cache(tmp_path)
    out_html = tmp_path / "report.html"
    out_json = tmp_path / "report.json"

    main(
        [
            "--cache-root",
            str(tmp_path),
            "--output-html",
            str(out_html),
            "--output-json",
            str(out_json),
        ]
    )

    assert out_html.exists()
    assert out_json.exists()
    summary = json.loads(out_json.read_text(encoding="utf-8"))
    assert summary["fields"]["field_count"] == 2
    assert summary["economics"]["evaluated_fields"] == ["Ayoluengo"]


def test_spain_package_declares_reference_chain_dependencies():
    pyproject = Path("packages/worldenergydata-spain/pyproject.toml")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    deps = set(data["project"]["dependencies"])

    assert "worldenergydata-production" in deps
    assert "worldenergydata-fdas" in deps


def _write_cache(
    root: Path,
    *,
    record_count: int = 4,
    source_url: str = "https://www.cores.es/en/estadisticas",
    manifest_status: str = "success",
    include_oil_status: bool = True,
    extra_rows: list[dict] | None = None,
) -> None:
    normalized = root / "normalized"
    metadata = root / "metadata"
    normalized.mkdir(parents=True)
    metadata.mkdir(parents=True)
    all_rows = _cache_rows(extra_rows)
    record_count = len(all_rows) if extra_rows is not None else record_count
    all_rows.to_csv(normalized / "cores_all_production.csv", index=False)
    all_rows[all_rows["oil_bbl"] > 0].to_csv(
        normalized / "cores_oil_production.csv", index=False
    )
    all_rows[all_rows["gas_mcf"] > 0].to_csv(
        normalized / "cores_gas_production.csv", index=False
    )
    (root / "_metadata.json").write_text(
        _json_text(_cache_metadata(record_count, source_url)),
        encoding="utf-8",
    )
    (root / "manifest.json").write_text(
        _json_text(_cache_manifest(record_count, manifest_status)),
        encoding="utf-8",
    )
    (metadata / "cores_refresh_metadata.json").write_text(
        _json_text(_workbook_metadata(source_url, include_oil_status)),
        encoding="utf-8",
    )


def _cache_rows(extra_rows: list[dict] | None = None) -> pd.DataFrame:
    rows = [
        _cache_row("Ayoluengo", 2025, 1, 10.0, pd.NA),
        _cache_row("Ayoluengo", 2025, 2, 20.0, pd.NA),
        _cache_row("Gaviota", 2025, 1, pd.NA, 100.0),
        _cache_row("Gaviota", 2025, 2, pd.NA, 150.0),
    ]
    if extra_rows is not None:
        rows.extend(extra_rows)
    return pd.DataFrame(rows)


def _cache_row(field_name, year, month, oil_bbl, gas_mcf) -> dict:
    return {
        "field_name": field_name,
        "year": year,
        "month": month,
        "oil_bbl": oil_bbl,
        "gas_mcf": gas_mcf,
    }


def _cache_metadata(record_count: int, source_url: str) -> dict:
    return {
        "format": "csv",
        "last_refresh": "2026-07-05T18:37:12.102722+00:00",
        "record_count": record_count,
        "source_url": source_url,
    }


def _cache_manifest(record_count: int, manifest_status: str) -> dict:
    return {
        "job_name": "spain_cores_refresh",
        "records_updated": record_count,
        "status": manifest_status,
        "updated_at": "2026-07-05T18:37:12.102722+00:00",
    }


def _workbook_metadata(source_url: str, include_oil_status: bool) -> dict:
    oil_workbook = {
        "byte_count": 12345,
        "last_modified": "Fri, 12 Jun 2026 07:51:41 GMT",
        "sha256": "0" * 64,
        "source_url": "https://www.cores.es/oil.xlsx",
    }
    if include_oil_status:
        oil_workbook["status_code"] = 200
    return {
        "refreshed_at_utc": "2026-07-05T18:37:12.102722+00:00",
        "statistics_page": source_url,
        "workbooks": {
            "oil": oil_workbook,
            "gas": _gas_workbook_metadata(),
        },
    }


def _gas_workbook_metadata() -> dict:
    return {
        "byte_count": 23456,
        "last_modified": "Fri, 12 Jun 2026 07:52:01 GMT",
        "sha256": "1" * 64,
        "source_url": "https://www.cores.es/gas.xlsx",
        "status_code": 200,
    }


def _json_text(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
