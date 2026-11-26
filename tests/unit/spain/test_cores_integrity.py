"""Issue 1293 regressions, with synthetic arithmetic and provenance inputs.

Basis: Spain agent pack (2026), section 6 SF1--SF5 and SF7--SF10.
All quantities below are synthetic, not qualified physical conversion factors.
"""

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from worldenergydata.scheduler.jobs.spain_cores_refresh import SpainCoresRefreshJob
from worldenergydata.spain.production.cores_live import CoresLiveProductionLoader
from worldenergydata.spain.production.cores_loader import (
    CoresParseError,
    parse_cores_frame,
)
from worldenergydata.spain.production.cores_source import (
    CoresHttpResponse,
    CoresWorkbookSource,
)
from worldenergydata.spain.reports.cores_field_development import (
    CoresReportError,
    _field_summaries,
    _filter_period,
    _to_unified,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1.234", 1234.0),
        ("1.234,5", 1234.5),
        ("1,234", 1.234),
        ("1.234.567,5", 1234567.5),
        (1.234, 1.234),
        ("0", 0.0),
    ],
)
def test_spanish_text_preserves_place_value(value, expected):
    """SF1: dots group thousands and commas mark decimals in source text.

    Hand calculation: 1*1000+234=1234; adding 5/10 gives 1234.5;
    1+234/1000=1.234; 1*1000000+234*1000+567+5/10=1234567.5.
    Native Excel numbers already carry their value. The synthetic audit is
    explicitly enabled; this test isolates parsing before conversion.
    """
    raw = pd.DataFrame({"Año": ["2.024"], "Mes": ["enero"], "Field A": [value]})
    audit = SimpleNamespace(bbl_per_tonne_for_field=lambda _: 2.0)
    out = parse_cores_frame(raw, product="oil", oil_conversion_audit=audit)
    assert out["year"].tolist() == [2024]
    # Hand calculation uses a synthetic input of 2 barrels per source unit.
    assert out["oil_bbl"].iloc[0] == pytest.approx(expected * 2.0)


@pytest.mark.parametrize("value", ["12.34", "1,2,3", "unknown", -1, float("inf")])
def test_invalid_or_negative_monthly_values_fail_closed(value):
    """SF1/SF10: malformed/nonfinite or negative production cannot be accepted.

    Zero is the lower bound by the production-volume contract (pack SF10),
    not an engineering acceptance tolerance.
    """
    raw = pd.DataFrame({"Year": [2024], "Month": ["January"], "Field A": [value]})
    with pytest.raises(CoresParseError):
        parse_cores_frame(raw, product="gas")


def test_unnamed_columns_and_missing_values_are_not_production():
    """SF2: one real zero observation, no observation for a dash/blank.

    Hand calculation: 0 times any factor = 0; summary 0 adds no field.
    """
    raw = pd.DataFrame(
        {
            "Year": [2024],
            "Month": ["January"],
            "Field A": [0],
            "Field B": ["-"],
            "Field C": [""],
            "Unnamed: 7": [99],
            "Total": [0],
        }
    )
    out = parse_cores_frame(raw, product="gas")
    assert out["field_name"].tolist() == ["Field A"]
    assert out["gas_mcf"].tolist() == [0.0]


def test_fractional_year_and_duplicate_field_keys_fail_closed():
    """SF3: two spellings of the same key cannot create two observations."""
    raw = pd.DataFrame({"Year": [2024.5], "Month": ["January"], "Field A": [0]})
    with pytest.raises(CoresParseError, match="year"):
        parse_cores_frame(raw, product="gas")
    raw = pd.DataFrame(
        [[2024, "January", 0, 0]], columns=["Year", "Month", "Field A", " FIELD Á "]
    )
    with pytest.raises(CoresParseError, match="duplicate"):
        parse_cores_frame(raw, product="gas")


def test_live_merge_matches_case_and_accents_without_multiplication(
    tmp_path, monkeypatch
):
    """SF3: one oil key + the same gas key = one joined row (2, 3)."""
    loader = CoresLiveProductionLoader(cache_root=tmp_path)
    oil = pd.DataFrame(
        {"field_name": ["Field Á"], "year": [2024], "month": [1], "oil_bbl": [2.0]}
    )
    gas = pd.DataFrame(
        {"field_name": [" FIELD A "], "year": [2024], "month": [1], "gas_mcf": [3.0]}
    )
    monkeypatch.setattr(loader, "load_oil_production", lambda: oil)
    monkeypatch.setattr(loader, "load_gas_production", lambda: gas)
    out = loader.load_all_production()
    assert len(out) == 1
    assert out[["oil_bbl", "gas_mcf"]].iloc[0].tolist() == [2.0, 3.0]
    monkeypatch.setattr(loader, "load_gas_production", lambda: pd.concat([gas, gas]))
    with pytest.raises(CoresParseError, match="duplicate"):
        loader.load_all_production()


def test_cache_reuse_keeps_acquisition_time_and_forced_refresh_fetches(tmp_path):
    """SF4: clock steps are synthetic; reuse cannot advance acquisition time.

    Two initial GETs + zero reuse GETs + one single-product GET + two
    forced GETs = five GETs.
    Single-product updates cannot claim both workbooks are freshly fetched.
    """
    calls = []
    now = ["2026-01-01T00:00:00Z"]

    def http_get(url, **kwargs):
        calls.append(url)
        return CoresHttpResponse(content=b"workbook", headers={})

    source = CoresWorkbookSource(
        cache_root=tmp_path, http_get=http_get, clock=lambda: now[0]
    )
    source.download_all(validate_links=False)
    original = source.metadata()
    now[0] = "2026-02-01T00:00:00Z"
    source.download_all(validate_links=False)
    reused = source.metadata()
    assert len(calls) == 2
    assert reused["refreshed_at_utc"] == original["refreshed_at_utc"]
    assert reused["checked_at_utc"] == now[0]
    assert all(w["cache_reused"] for w in reused["workbooks"].values())
    source.download("oil", force_refresh=True, validate_links=False)
    assert source.metadata()["refreshed_at_utc"] == original["refreshed_at_utc"]
    now[0] = "2026-03-01T00:00:00Z"
    source.download_all(force_refresh=True, validate_links=False)
    assert len(calls) == 5
    assert source.metadata()["refreshed_at_utc"] == now[0]


def test_orphan_cache_has_unknown_acquisition_time(tmp_path):
    """SF4: filesystem presence is not evidence of a network acquisition."""
    source = CoresWorkbookSource(cache_root=tmp_path)
    source.raw_dir.mkdir()
    from worldenergydata.spain.production.cores_source import DEFAULT_WORKBOOKS

    for workbook in DEFAULT_WORKBOOKS.values():
        (source.raw_dir / workbook.filename).write_bytes(b"cached")
    source.download_all(validate_links=False)
    assert source.metadata()["refreshed_at_utc"] is None


def test_scheduler_fetches_by_default_and_retains_source_timestamp(tmp_path):
    """SF4: scheduler completion time cannot replace source acquisition time."""

    class Loader:
        def __init__(self, **kwargs):
            pass

        def refresh(self, *, force_refresh):
            assert force_refresh is True

        def metadata(self):
            return {"refreshed_at_utc": "2026-01-01T00:00:00Z"}

        def load_all_production(self):
            return pd.DataFrame({"row": [0]})

    job = SpainCoresRefreshJob()
    job._loader_class = lambda: Loader
    assert job.run({"output_dir": tmp_path}).status == "success"
    metadata = json.loads((tmp_path / "_metadata.json").read_text())
    assert metadata["last_refresh"] == "2026-01-01T00:00:00Z"
    assert metadata["last_checked"] != metadata["last_refresh"]


def test_report_unknowns_stay_null_and_partial_totals_are_labelled():
    """SF5: observed oil [2, missing] is not a complete total of 2.

    Hand calculation: gas [0, 3] sums to 3; true zero stays zero. All unknown
    quantities serialize as JSON null, not zero or nonstandard NaN tokens.
    """
    frame = pd.DataFrame(
        {
            "field_name": ["Field A", "Field A"],
            "year": [2024, 2024],
            "month": [1, 2],
            "oil_bbl": [2.0, None],
            "gas_mcf": [0.0, 3.0],
        }
    )
    item = _field_summaries(frame)[0]
    assert item["oil_bbl"] is None
    assert item["gas_mcf"] == 3.0
    assert item["monthly"][0]["gas_mcf"] == 0.0
    assert item["monthly"][1]["oil_bbl"] is None
    assert "oil_bbl_missing_observations" in item["limitations"]
    json.dumps(item, allow_nan=False)
    unified = _to_unified(frame)
    assert pd.isna(unified.loc[1, "oil_bbl"])
    assert unified["water_bbl"].isna().all()
    assert unified["condensate_bbl"].isna().all()


@pytest.mark.parametrize(
    "start,end", [("2024-1", None), ("2024-13", None), ("2024-02", "2024-01")]
)
def test_period_filters_reject_invalid_or_reversed_bounds(start, end):
    """SF9: ISO monthly keys sort in time order only when validated."""
    frame = pd.DataFrame({"year": [2024], "month": [1]})
    with pytest.raises(CoresReportError):
        _filter_period(frame, start, end)


def test_invalid_source_date_emits_warning_instead_of_silent_fallback():
    """SF7: a synthetic malformed HTTP date is visibly unverified."""
    from worldenergydata.spain.production.cores_live import _source_updated_date

    with pytest.warns(RuntimeWarning, match="source date is unverified"):
        assert _source_updated_date({"last_modified": "invalid"}) is None


def test_unknown_product_totals_and_valid_inclusive_period_filter():
    """SF5/SF9: absent oil is null; inclusive January keeps the sole row."""
    frame = pd.DataFrame(
        {"field_name": ["Field A"], "year": [2024], "month": [1], "gas_mcf": [0.0]}
    )
    assert _field_summaries(frame)[0]["oil_bbl"] is None
    assert len(_filter_period(frame, "2024-01", "2024-01")) == 1
    assert _filter_period(frame, "2024-02", None).empty


def test_excel_readers_preserve_text_and_native_number_distinction(tmp_path):
    """SF1, CLDR 48 es symbols: text 1.234 = 1234, native 1.234 stays 1.234.

    Independent multiplication by the synthetic input factor 2 gives 2468
    and 2.468 barrels respectively. Both XLSX reader paths preserve types.
    """
    from worldenergydata.spain.production.cores_loader import CoresProductionLoader

    path = tmp_path / "production.xlsx"
    raw = pd.DataFrame(
        {
            "Year": [2024, 2024],
            "Month": ["January", "February"],
            "Field A": ["1.234", 1.234],
        }
    )
    raw.to_excel(path, sheet_name="Production", startrow=5, index=False)
    audit = SimpleNamespace(bbl_per_tonne_for_field=lambda _: 2.0)
    out = CoresProductionLoader(
        product="oil", path=path, oil_conversion_audit=audit
    ).load()
    assert out["oil_bbl"].tolist() == pytest.approx([2468.0, 2.468])
    live_raw = CoresLiveProductionLoader(cache_root=tmp_path)._read_workbook(path)
    assert isinstance(live_raw.loc[0, "Field A"], str)
    assert live_raw.loc[1, "Field A"] == 1.234


def test_live_merge_keeps_one_display_name_across_disjoint_months(
    tmp_path, monkeypatch
):
    """SF3: spelling differences across months still identify a single field."""
    loader = CoresLiveProductionLoader(cache_root=tmp_path)
    oil = pd.DataFrame(
        {"field_name": ["Field Á"], "year": [2024], "month": [1], "oil_bbl": [0]}
    )
    gas = pd.DataFrame(
        {"field_name": ["FIELD A"], "year": [2024], "month": [2], "gas_mcf": [0]}
    )
    monkeypatch.setattr(loader, "load_oil_production", lambda: oil)
    monkeypatch.setattr(loader, "load_gas_production", lambda: gas)
    out = loader.load_all_production()
    assert out["field_name"].unique().tolist() == ["Field Á"]
    assert len(out) == 2
    assert out.loc[out["month"] == 2, "oil_bbl"].isna().all()


def test_scheduler_rejects_text_boolean_before_loading(tmp_path):
    """A text false value is not an opt-in to network refresh or cache reuse."""
    result = SpainCoresRefreshJob().run(
        {"output_dir": tmp_path, "force_refresh": "false"}
    )
    assert result.status == "failure"
    assert result.retryable is False
    assert "force_refresh must be boolean" in result.error_msg


def test_shipped_schedule_requests_workbook_downloads():
    """SF4: the shipped schedule must not override fetching with cache reuse."""
    from worldenergydata.scheduler.config import load_config

    config = load_config("config/scheduler/scheduler_config.yml")
    assert config.get_job_config("spain_cores_refresh")["force_refresh"] is True
