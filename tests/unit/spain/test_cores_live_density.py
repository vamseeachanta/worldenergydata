"""Spain CORES live-loader density audit tests (#807)."""

import json

import pandas as pd
import pytest

from worldenergydata.spain.production.cores_density import (
    CoresCrudeDensityFactor,
    CoresDensityCoverageError,
    CoresOilConversionAudit,
)
from worldenergydata.spain.production.cores_live import (
    DEFAULT_WORKBOOKS,
    STATISTICS_PAGE_URL,
    CoresLiveProductionLoader,
    refresh_ayoluengo_fixture,
)
from worldenergydata.spain.production.cores_loader import GWH_TO_MCF, TONNES_TO_BBL


def test_live_loader_allows_legacy_default_only_when_explicit(tmp_path):
    _write_live_workbooks(
        tmp_path,
        pd.DataFrame([_workbook_row("Ayoluengo", 2.0)]),
        pd.DataFrame([_workbook_row("Ayoluengo", 3.0)]),
    )

    loader = CoresLiveProductionLoader(
        cache_root=tmp_path,
        allow_default_density=True,
    )

    oil = loader.load_oil_production()
    gas = loader.load_gas_production()
    all_products = loader.load_all_production()

    assert oil.iloc[0]["oil_bbl"] == pytest.approx(2.0 * TONNES_TO_BBL)
    assert gas.iloc[0]["gas_mcf"] == pytest.approx(3.0 * GWH_TO_MCF)
    assert all_products.iloc[0]["oil_bbl"] == pytest.approx(2.0 * TONNES_TO_BBL)
    assert all_products.iloc[0]["gas_mcf"] == pytest.approx(3.0 * GWH_TO_MCF)
    assert loader.oil_conversion_audit is not None
    assert loader.oil_conversion_audit.defaulted_fields == ("Ayoluengo",)
    sidecar = _read_density_sidecar(tmp_path)
    assert sidecar["coverage_status"] == "defaulted"
    assert sidecar["defaulted_fields"] == ["Ayoluengo"]
    assert sidecar["default_bbl_per_tonne"] == TONNES_TO_BBL
    assert (tmp_path / "normalized" / "cores_oil_production.csv").exists()
    assert (tmp_path / "normalized" / "cores_gas_production.csv").exists()
    assert (tmp_path / "normalized" / "cores_all_production.csv").exists()


def test_live_loader_rejects_non_boolean_default_opt_in(tmp_path):
    with pytest.raises(ValueError, match="allow_default_density"):
        CoresLiveProductionLoader(
            cache_root=tmp_path,
            allow_default_density="false",
        )


def test_live_loader_default_registry_fails_closed_on_source_gaps(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_cores_xlsx(
        raw_dir / DEFAULT_WORKBOOKS["oil"].filename,
        pd.DataFrame([_workbook_row("Ayoluengo", 2.0)]),
    )

    loader = CoresLiveProductionLoader(cache_root=tmp_path)

    with pytest.raises(CoresDensityCoverageError, match="Ayoluengo"):
        loader.load_oil_production()


def test_live_loader_applies_density_registry_and_writes_oil_conversion_audit(tmp_path):
    _write_live_workbooks(
        tmp_path,
        pd.DataFrame([_workbook_row("Ayoluengo", 2.0)]),
        pd.DataFrame([_workbook_row("Ayoluengo", 3.0)]),
    )
    registry_path = _write_density_registry(tmp_path, [_density_entry()])

    loader = CoresLiveProductionLoader(
        cache_root=tmp_path,
        oil_density_registry_path=registry_path,
    )

    all_products = loader.load_all_production()

    assert all_products.iloc[0]["oil_bbl"] == pytest.approx(2.0 * 6.95)
    assert all_products.iloc[0]["gas_mcf"] == pytest.approx(3.0 * GWH_TO_MCF)
    sidecar = _read_density_sidecar(tmp_path)
    assert sidecar["registry_version"] == "test-2026-07-06"
    assert sidecar["registry_date"] == "2026-07-06"
    assert sidecar["coverage_status"] == "complete"
    assert sidecar["oil_field_count"] == 1
    assert sidecar["used_fields"] == ["Ayoluengo"]
    assert sidecar["defaulted_fields"] == []
    assert sidecar["missing_fields"] == []
    assert sidecar["factors"][0]["field_name"] == "Ayoluengo"
    assert sidecar["factors"][0]["bbl_per_tonne"] == 6.95
    assert sidecar["factors"][0]["source_url"] == "https://example.test/ayoluengo"


def test_live_loader_missing_density_is_fail_closed_without_default(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_cores_xlsx(
        raw_dir / DEFAULT_WORKBOOKS["oil"].filename,
        pd.DataFrame(
            [
                {
                    "Year": 2026,
                    "Month": "June",
                    "Ayoluengo": 2.0,
                    "Casablanca": 1.0,
                    "Grand total": 3.0,
                }
            ]
        ),
    )
    registry_path = _write_density_registry(tmp_path, [_density_entry()])
    loader = CoresLiveProductionLoader(
        cache_root=tmp_path,
        oil_density_registry_path=registry_path,
        allow_default_density=False,
    )

    with pytest.raises(CoresDensityCoverageError, match="Casablanca"):
        loader.load_oil_production()
    assert not (tmp_path / "normalized" / "cores_oil_density_factors.json").exists()


def test_refresh_ayoluengo_fixture_records_density_provenance(tmp_path):
    oil = pd.DataFrame(
        [
            {"field_name": "Ayoluengo", "year": 2026, "month": 1, "oil_bbl": 13.9},
        ]
    )
    source_metadata = {
        "statistics_page": STATISTICS_PAGE_URL,
        "workbooks": {
            "oil": {
                "source_url": DEFAULT_WORKBOOKS["oil"].source_url,
                "last_modified": "Fri, 12 Jun 2026 07:51:41 GMT",
            }
        },
    }

    result = refresh_ayoluengo_fixture(
        oil_frame=oil,
        metadata=source_metadata,
        output_dir=tmp_path,
        refreshed_at_utc="2026-07-04T00:00:00Z",
        oil_conversion_audit=_single_field_audit(),
    )

    written_metadata = json.loads(result.metadata_path.read_text())
    assert written_metadata["conversion"] == (
        "oil_bbl = tonnes * cited_field_density_factors"
    )
    assert written_metadata["conversion_factors"]["oil_tonnes_to_bbl_by_field"] == {
        "Ayoluengo": 6.95
    }
    audit = written_metadata["oil_conversion_audit"]
    assert audit["coverage_status"] == "complete"
    assert audit["used_fields"] == ["Ayoluengo"]
    assert audit["factors"][0]["source_url"] == "https://example.test/ayoluengo"


def test_refresh_ayoluengo_fixture_records_default_density_factor(tmp_path):
    oil = pd.DataFrame(
        [
            {"field_name": "Ayoluengo", "year": 2026, "month": 1, "oil_bbl": 13.9},
        ]
    )
    result = refresh_ayoluengo_fixture(
        oil_frame=oil,
        metadata={"workbooks": {"oil": {}}},
        output_dir=tmp_path,
        refreshed_at_utc="2026-07-04T00:00:00Z",
        oil_conversion_audit=_defaulted_audit(),
    )

    written_metadata = json.loads(result.metadata_path.read_text())
    assert written_metadata["conversion_factors"]["oil_tonnes_to_bbl_default"] == (
        TONNES_TO_BBL
    )
    assert written_metadata["oil_conversion_audit"]["default_bbl_per_tonne"] == (
        TONNES_TO_BBL
    )


def _workbook_row(field_name: str, value: float) -> dict:
    return {"Year": 2026, "Month": "June", field_name: value, "Grand total": value}


def _write_cores_xlsx(path, frame):
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"note": ["landing sheet"]}).to_excel(
            writer,
            sheet_name="Start",
            index=False,
        )
        frame.to_excel(writer, sheet_name="Production", index=False, startrow=5)


def _write_live_workbooks(tmp_path, oil_frame, gas_frame=None):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _write_cores_xlsx(raw_dir / DEFAULT_WORKBOOKS["oil"].filename, oil_frame)
    if gas_frame is not None:
        _write_cores_xlsx(raw_dir / DEFAULT_WORKBOOKS["gas"].filename, gas_frame)


def _density_entry(**overrides):
    entry = {
        "field_name": "Ayoluengo",
        "aliases": ["ayoluengo"],
        "api_gravity_deg": None,
        "api_gravity_min_deg": None,
        "api_gravity_max_deg": None,
        "bbl_per_tonne": 6.95,
        "measurement_basis": "representative produced stream",
        "source_title": "Example operator assay",
        "source_url": "https://example.test/ayoluengo",
        "source_class": "operator_record",
        "evidence_note": "Accepted field-specific conversion factor.",
        "confidence": "high",
        "accepted_for_conversion": True,
    }
    entry.update(overrides)
    return entry


def _write_density_registry(tmp_path, factors):
    path = tmp_path / "density.json"
    path.write_text(
        json.dumps(
            {
                "registry_version": "test-2026-07-06",
                "registry_date": "2026-07-06",
                "factors": factors,
            }
        ),
        encoding="utf-8",
    )
    return path


def _single_field_audit():
    factor = CoresCrudeDensityFactor(**_density_entry())
    return CoresOilConversionAudit(
        used_factors=(factor,),
        defaulted_fields=(),
        missing_fields=(),
        _accepted_entries=(("ayoluengo", factor),),
        _defaulted_field_keys=(),
    )


def _defaulted_audit():
    return CoresOilConversionAudit(
        used_factors=(),
        defaulted_fields=("Ayoluengo",),
        missing_fields=(),
        _accepted_entries=(),
        _defaulted_field_keys=("ayoluengo",),
    )


def _read_density_sidecar(tmp_path) -> dict:
    return json.loads(
        (tmp_path / "normalized" / "cores_oil_density_factors.json").read_text()
    )
