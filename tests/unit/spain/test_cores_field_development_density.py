"""Spain CORES field-development density provenance tests (#807)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.spain.reports.cores_field_development import (
    CoresReportError,
    build_report,
    render_spain_cores_html,
)


def test_build_report_replaces_deferred_caveat_with_density_provenance(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path)

    summary = build_report(tmp_path)

    assert (
        "oil_tonnes_to_bbl_conversion_deferred_to_issue_807"
        not in summary["limitations"]
    )
    assert (
        "oil_tonnes_to_bbl_uses_cited_field_density_factors" in summary["limitations"]
    )
    assert summary["oil_conversion_audit"]["coverage_status"] == "complete"
    assert summary["oil_conversion_audit"]["factors"][0]["source_url"] == (
        "https://example.test/ayoluengo-density"
    )


def test_report_preserves_defaulted_density_limitations(tmp_path):
    _write_cache(tmp_path, extra_rows=[_cache_row("Albatros", 2025, 1, 5.0, pd.NA)])
    _write_density_sidecar(
        tmp_path,
        coverage_status="defaulted",
        used_fields=["Ayoluengo"],
        defaulted_fields=["Albatros"],
    )

    summary = build_report(tmp_path)
    html = render_spain_cores_html(summary)
    visible_html = html.split('<script type="application/json"', 1)[0]

    assert "oil_tonnes_to_bbl_conversion_deferred_to_issue_807" in html
    assert (
        "oil_tonnes_to_bbl_conversion_deferred_to_issue_807" in summary["limitations"]
    )
    assert any(
        item == "oil_tonnes_to_bbl_has_defaulted_fields: Albatros"
        for item in summary["limitations"]
    )
    assert any(
        item == "oil_tonnes_to_bbl_assumes_default_factor: Albatros=7.33"
        for item in summary["limitations"]
    )
    assert "oil_tonnes_to_bbl_has_defaulted_fields: Albatros" in visible_html
    assert "oil_tonnes_to_bbl_assumes_default_factor: Albatros=7.33" in visible_html
    assert "7.33" in visible_html


def test_report_preserves_default_assumption_when_missing_fields_also_block_conversion(
    tmp_path,
):
    _write_cache(
        tmp_path,
        extra_rows=[
            _cache_row("Albatros", 2025, 1, 5.0, pd.NA),
            _cache_row("Casablanca", 2025, 1, 6.0, pd.NA),
        ],
    )
    _write_density_sidecar(
        tmp_path,
        coverage_status="missing",
        used_fields=["Ayoluengo"],
        defaulted_fields=["Albatros"],
        missing_fields=["Casablanca"],
    )

    summary = build_report(tmp_path)
    html = render_spain_cores_html(summary)
    visible_html = html.split('<script type="application/json"', 1)[0]

    assert any(
        item == "oil_tonnes_to_bbl_blocked_by_missing_density_source: Casablanca"
        for item in summary["limitations"]
    )
    assert any(
        item == "oil_tonnes_to_bbl_assumes_default_factor: Albatros=7.33"
        for item in summary["limitations"]
    )
    assert (
        "oil_tonnes_to_bbl_blocked_by_missing_density_source: Casablanca"
        in visible_html
    )
    assert "oil_tonnes_to_bbl_assumes_default_factor: Albatros=7.33" in visible_html


def test_report_preserves_missing_density_limitations(tmp_path):
    _write_cache(tmp_path, extra_rows=[_cache_row("Albatros", 2025, 1, 5.0, pd.NA)])
    _write_density_sidecar(
        tmp_path,
        coverage_status="missing",
        used_fields=["Ayoluengo"],
        missing_fields=["Albatros"],
    )

    summary = build_report(tmp_path)
    html = render_spain_cores_html(summary)

    assert "oil_tonnes_to_bbl_conversion_deferred_to_issue_807" in html
    assert (
        "oil_tonnes_to_bbl_conversion_deferred_to_issue_807" in summary["limitations"]
    )
    assert any(
        item == "oil_tonnes_to_bbl_has_missing_fields: Albatros"
        for item in summary["limitations"]
    )
    assert any(
        item == "oil_tonnes_to_bbl_blocked_by_missing_density_source: Albatros"
        for item in summary["limitations"]
    )
    visible_html = html.split('<script type="application/json"', 1)[0]
    assert "oil_tonnes_to_bbl_has_missing_fields: Albatros" in visible_html
    assert (
        "oil_tonnes_to_bbl_blocked_by_missing_density_source: Albatros" in visible_html
    )


def test_report_rejects_malformed_density_sidecar(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path)
    sidecar_path = tmp_path / "normalized" / "cores_oil_density_factors.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    del sidecar["factors"][0]["source_url"]
    sidecar_path.write_text(_json_text(sidecar), encoding="utf-8")

    with pytest.raises(CoresReportError, match="source_url"):
        build_report(tmp_path)


def test_report_rejects_malformed_supporting_source_urls(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path)
    sidecar_path = tmp_path / "normalized" / "cores_oil_density_factors.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["factors"][0]["supporting_source_urls"] = "not-a-list"
    sidecar_path.write_text(_json_text(sidecar), encoding="utf-8")

    with pytest.raises(CoresReportError, match="supporting_source_urls"):
        build_report(tmp_path)


def test_report_rejects_defaulted_sidecar_without_defaulted_field_names(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(
        tmp_path,
        coverage_status="defaulted",
        defaulted_fields=["Casablanca"],
    )
    _mutate_density_sidecar(tmp_path, lambda sidecar: sidecar.pop("defaulted_fields"))

    with pytest.raises(CoresReportError, match="defaulted_fields"):
        build_report(tmp_path)


def test_report_rejects_defaulted_sidecar_without_default_bbl_per_tonne(tmp_path):
    _write_cache(tmp_path, extra_rows=[_cache_row("Casablanca", 2025, 1, 5.0, pd.NA)])
    _write_density_sidecar(
        tmp_path,
        coverage_status="defaulted",
        used_fields=["Ayoluengo"],
        defaulted_fields=["Casablanca"],
    )
    _mutate_density_sidecar(
        tmp_path,
        lambda sidecar: sidecar.pop("default_bbl_per_tonne"),
    )

    with pytest.raises(CoresReportError, match="default_bbl_per_tonne"):
        build_report(tmp_path)


@pytest.mark.parametrize(
    "default_bbl_per_tonne",
    [float("nan"), float("inf")],
)
def test_report_rejects_defaulted_sidecar_with_non_finite_default_bbl_per_tonne(
    tmp_path,
    default_bbl_per_tonne,
):
    _write_cache(tmp_path, extra_rows=[_cache_row("Albatros", 2025, 1, 5.0, pd.NA)])
    _write_density_sidecar(
        tmp_path,
        coverage_status="defaulted",
        used_fields=["Ayoluengo"],
        defaulted_fields=["Albatros"],
    )
    _mutate_density_sidecar(
        tmp_path,
        lambda sidecar: sidecar.update(
            {"default_bbl_per_tonne": default_bbl_per_tonne}
        ),
    )

    with pytest.raises(CoresReportError, match="default_bbl_per_tonne"):
        build_report(tmp_path)


def test_report_rejects_complete_sidecar_that_omits_oil_fields(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path, used_fields=[])

    with pytest.raises(CoresReportError, match="Ayoluengo"):
        build_report(tmp_path)


def test_report_rejects_complete_sidecar_without_matching_factor(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path)
    _mutate_density_sidecar(tmp_path, lambda sidecar: sidecar.update({"factors": []}))

    with pytest.raises(CoresReportError, match="Ayoluengo"):
        build_report(tmp_path)


def test_report_rejects_complete_sidecar_with_extra_accepted_factor(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path)

    def mutate(sidecar: dict) -> None:
        extra_factor = dict(sidecar["factors"][0])
        extra_factor.update(
            {
                "field_name": "Casablanca",
                "aliases": ["Casablanca"],
                "api_gravity_deg": None,
                "bbl_per_tonne": 6.95,
                "source_title": "Casablanca density reference",
            }
        )
        sidecar["used_fields"].append("Casablanca")
        sidecar["factors"].append(extra_factor)
        sidecar["oil_field_count"] = 2

    _mutate_density_sidecar(tmp_path, mutate)

    with pytest.raises(CoresReportError, match="Casablanca"):
        build_report(tmp_path)


def test_report_rejects_used_field_without_matching_factor_for_all_oil_fields(tmp_path):
    extra_rows = [_cache_row("Casablanca", 2025, 1, 5.0, pd.NA)]
    _write_cache(tmp_path, extra_rows=extra_rows)
    _write_density_sidecar(tmp_path, used_fields=["Ayoluengo", "Casablanca"])

    with pytest.raises(CoresReportError, match="Casablanca"):
        build_report(tmp_path)


def test_report_rejects_density_sidecar_missing_registry_version(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path)
    _mutate_density_sidecar(tmp_path, lambda sidecar: sidecar.pop("registry_version"))

    with pytest.raises(CoresReportError, match="registry_version"):
        build_report(tmp_path)


def test_report_rejects_density_sidecar_with_invalid_numeric_factor(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path)
    _mutate_density_sidecar(
        tmp_path,
        lambda sidecar: sidecar["factors"][0].update({"bbl_per_tonne": -7.1}),
    )

    with pytest.raises(CoresReportError, match="bbl_per_tonne"):
        build_report(tmp_path)


def test_report_rejects_density_sidecar_with_non_http_source_url(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path)
    _mutate_density_sidecar(
        tmp_path,
        lambda sidecar: sidecar["factors"][0].update(
            {"source_url": "javascript:alert(1)"}
        ),
    )

    with pytest.raises(CoresReportError, match="source_url"):
        build_report(tmp_path)


def test_render_html_shows_density_provenance_fields(tmp_path):
    _write_cache(tmp_path)
    _write_density_sidecar(tmp_path)

    html = render_spain_cores_html(build_report(tmp_path))
    visible_html = html.split('<script type="application/json"', 1)[0]

    assert "Density Provenance" in visible_html
    assert "Ayoluengo density reference" in visible_html
    assert "https://example.test/ayoluengo-density" in visible_html
    assert "operator_record" in visible_html
    assert "7.17883" in visible_html


def test_report_accepts_sidecar_used_fields_matching_factor_aliases(tmp_path):
    _write_cache(tmp_path)
    _rewrite_field_name(tmp_path, "Ayoluengo", "Ayo luengo")
    _write_density_sidecar(tmp_path, used_fields=["Ayo luengo"])
    _mutate_density_sidecar(
        tmp_path,
        lambda sidecar: sidecar["factors"][0].update({"aliases": ["Ayo luengo"]}),
    )

    summary = build_report(tmp_path)

    audit = summary["oil_conversion_audit"]
    assert audit["used_fields"] == ["Ayo luengo"]
    assert audit["factors"][0]["field_name"] == "Ayoluengo"


def _write_cache(root: Path, *, extra_rows: list[dict] | None = None) -> None:
    normalized = root / "normalized"
    metadata = root / "metadata"
    normalized.mkdir(parents=True)
    metadata.mkdir(parents=True)
    all_rows = _cache_rows(extra_rows)
    all_rows.to_csv(normalized / "cores_all_production.csv", index=False)
    all_rows[all_rows["oil_bbl"] > 0].to_csv(
        normalized / "cores_oil_production.csv", index=False
    )
    all_rows[all_rows["gas_mcf"] > 0].to_csv(
        normalized / "cores_gas_production.csv", index=False
    )
    record_count = len(all_rows)
    (root / "_metadata.json").write_text(_json_text(_cache_metadata(record_count)))
    (root / "manifest.json").write_text(_json_text(_cache_manifest(record_count)))
    (metadata / "cores_refresh_metadata.json").write_text(
        _json_text(_workbook_metadata())
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


def _cache_metadata(record_count: int) -> dict:
    return {
        "format": "csv",
        "last_refresh": "2026-07-05T18:37:12.102722+00:00",
        "record_count": record_count,
        "source_url": "https://www.cores.es/en/estadisticas",
    }


def _cache_manifest(record_count: int) -> dict:
    return {
        "job_name": "spain_cores_refresh",
        "records_updated": record_count,
        "status": "success",
        "updated_at": "2026-07-05T18:37:12.102722+00:00",
    }


def _workbook_metadata() -> dict:
    return {
        "refreshed_at_utc": "2026-07-05T18:37:12.102722+00:00",
        "statistics_page": "https://www.cores.es/en/estadisticas",
        "workbooks": {
            "oil": _workbook("https://www.cores.es/oil.xlsx", "0" * 64),
            "gas": _workbook("https://www.cores.es/gas.xlsx", "1" * 64),
        },
    }


def _workbook(source_url: str, sha256: str) -> dict:
    return {
        "byte_count": 12345,
        "last_modified": "Fri, 12 Jun 2026 07:51:41 GMT",
        "sha256": sha256,
        "source_url": source_url,
        "status_code": 200,
    }


def _json_text(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _mutate_density_sidecar(root: Path, mutator) -> None:
    path = root / "normalized" / "cores_oil_density_factors.json"
    sidecar = json.loads(path.read_text(encoding="utf-8"))
    mutator(sidecar)
    path.write_text(_json_text(sidecar), encoding="utf-8")


def _rewrite_field_name(root: Path, old: str, new: str) -> None:
    for path in (root / "normalized").glob("cores_*_production.csv"):
        frame = pd.read_csv(path)
        frame["field_name"] = frame["field_name"].replace(old, new)
        frame.to_csv(path, index=False)


def _write_density_sidecar(
    root: Path,
    *,
    coverage_status: str = "complete",
    used_fields: list[str] | None = None,
    defaulted_fields: list[str] | None = None,
    missing_fields: list[str] | None = None,
) -> None:
    used_fields = ["Ayoluengo"] if used_fields is None else used_fields
    defaulted_fields = [] if defaulted_fields is None else defaulted_fields
    missing_fields = [] if missing_fields is None else missing_fields
    payload = _density_sidecar_payload(
        coverage_status,
        used_fields,
        defaulted_fields,
        missing_fields,
    )
    (root / "normalized" / "cores_oil_density_factors.json").write_text(
        _json_text(payload),
        encoding="utf-8",
    )


def _density_sidecar_payload(
    coverage_status: str,
    used_fields: list[str],
    defaulted_fields: list[str],
    missing_fields: list[str],
) -> dict:
    payload = {
        "schema_version": 1,
        "generated_at": "2026-07-05T18:37:12.102722+00:00",
        "registry_version": "test-2026-07-06",
        "registry_date": "2026-07-06",
        "conversion_basis": "cited_field_density_factors",
        "coverage_status": coverage_status,
        "oil_field_count": (
            len(used_fields) + len(defaulted_fields) + len(missing_fields)
        ),
        "used_fields": used_fields,
        "defaulted_fields": defaulted_fields,
        "missing_fields": missing_fields,
        "factors": [_density_factor()],
    }
    if defaulted_fields:
        payload["default_bbl_per_tonne"] = 7.33
    return payload


def _density_factor() -> dict:
    return {
        "field_name": "Ayoluengo",
        "aliases": ["Ayoluengo"],
        "api_gravity_deg": 30.0,
        "api_gravity_min_deg": None,
        "api_gravity_max_deg": None,
        "bbl_per_tonne": 7.17883,
        "measurement_basis": "representative_api_gravity",
        "source_title": "Ayoluengo density reference",
        "source_url": "https://example.test/ayoluengo-density",
        "source_class": "operator_record",
        "evidence_note": "Synthetic test citation",
        "confidence": "high",
        "accepted_for_conversion": True,
        "supporting_source_urls": [],
    }
