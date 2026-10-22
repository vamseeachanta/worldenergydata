"""Ingestion integrity regressions using synthetic inputs and hand calculations.

All numeric fixtures are synthetic, with expected arithmetic stated locally.
These tests establish data handling, not regulatory fiscal qualification.
"""

import io
import zipfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from worldenergydata.brazil_anp.analysis.field_economics import (
    ConcessionRegime,
    ParticipationSchedule,
    calculate_royalties_concession,
    calculate_special_participation,
)
from worldenergydata.brazil_anp.field_concept import build_brazil_field_meta
from worldenergydata.brazil_anp.production.anp_client import ANPClient
from worldenergydata.brazil_anp.production.well_production import WellProductionLoader
from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob


def raw_row(**changes):
    row = {
        "Campo": "synthetic-field",
        "Nome Poço ANP": "synthetic-well",
        "Período": "2024/02",
        "Óleo (bbl/dia)": "0.5",
        "Condensado (bbl/dia)": "0",
        "Gás Natural (Mm³/dia) Gás Total": "0",
        "Água (bbl/dia)": "0",
    }
    return pd.DataFrame([{**row, **changes}])


def archive(text=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as out:
        out.writestr("partition.csv" if text is not None else "readme.txt", text or "")
    return buffer.getvalue()


@pytest.mark.parametrize("value", ["0.5", 0.5, "0,5", "1.000,5", "1000.5", 1000.5])
def test_decimal_rates_preserve_value(value):
    """Leap February: 0.5 * 29 = 14.5 or 1000.5 * 29 = 29014.5 bbl."""
    result = WellProductionLoader().load(raw_row(**{"Óleo (bbl/dia)": value}))
    # Use explicit cases rather than the parser under test for the expectation.
    if value in ("1.000,5", "1000.5", 1000.5):
        expected = 29014.5
    else:
        expected = 14.5
    assert result.iloc[0].oil_bbl == expected


@pytest.mark.parametrize("column", ["Campo", "Nome Poço ANP"])
@pytest.mark.parametrize("missing", [None, float("nan"), pd.NA, "", "  "])
def test_missing_identities_are_rejected(column, missing):
    with pytest.raises(ValueError, match="identity"):
        WellProductionLoader().load(raw_row(**{column: missing}))


@pytest.mark.parametrize("value", [None, "", "bad", "nan", float("inf"), -1])
def test_missing_or_invalid_rate_is_rejected(value):
    with pytest.raises(ValueError, match="rate|number"):
        WellProductionLoader().load(raw_row(**{"Óleo (bbl/dia)": value}))


def test_loader_rejects_partial_periods():
    frame = pd.concat([raw_row(), raw_row(Período="02/2024")])
    with pytest.raises(ValueError, match="period"):
        WellProductionLoader().load(frame)


@pytest.mark.parametrize(
    "text",
    [
        None,
        "Campo;Período\n;\n;\n",
        "Campo;Período\n;\n;\nx;02/2024\n",
        "Campo;Other\n;\n;\nx;y\n",
    ],
)
def test_client_rejects_empty_or_invalid_partitions(tmp_path, text):
    with pytest.raises(ValueError):
        ANPClient(cache_dir=str(tmp_path))._read_zip(archive(text))


@pytest.mark.parametrize("kind", ["empty", "partial", "invalid"])
def test_failed_refresh_does_not_publish_snapshots_or_success(tmp_path, kind):
    client = MagicMock()
    client.download_month.return_value = (
        pd.DataFrame() if kind == "empty" else raw_row()
    )
    module = "worldenergydata.scheduler.jobs.brazil_anp_refresh"
    if kind == "invalid":
        client.download_month.return_value = raw_row(Período="02/2024")
    with (
        patch(f"{module}.ANPClient", return_value=client),
        patch(f"{module}.write_refresh_metadata") as metadata,
        patch(f"{module}.write_parquet") as snapshot,
        patch("pandas.DataFrame.to_parquet") as raw_snapshot,
        patch(f"{module}.WellProductionLoader") as loader,
    ):
        if kind == "partial":
            loader.return_value.load.return_value = pd.DataFrame()
        else:
            loader.return_value.load.side_effect = WellProductionLoader().load
        result = BrazilAnpRefreshJob().run(
            {"output_dir": str(tmp_path), "year": 2024, "month": 2}
        )
    assert result.status == "failure"
    assert result.records_updated == 0
    metadata.assert_not_called()
    snapshot.assert_not_called()
    raw_snapshot.assert_not_called()


@pytest.mark.parametrize(
    "wells",
    [
        pd.DataFrame(),
        pd.DataFrame({"POCO": ["a"]}),
        pd.DataFrame({"Campo": ["synthetic"]}),
        pd.DataFrame({"Campo": ["synthetic"], "POCO": [None]}),
    ],
)
def test_missing_well_evidence_stays_unknown(wells):
    meta = build_brazil_field_meta(
        fields_df=pd.DataFrame({"CAMPO": ["synthetic"]}),
        platforms_df=pd.DataFrame(),
        wells_df=wells,
        field_name="synthetic",
    )
    assert meta["well_count"] is None


def test_well_count_uses_distinct_nonblank_identities():
    """The repeated well-month rows {a, a, b} represent exactly two wells."""
    meta = build_brazil_field_meta(
        fields_df=pd.DataFrame({"CAMPO": ["synthetic"]}),
        platforms_df=pd.DataFrame(),
        wells_df=pd.DataFrame({"Campo": ["synthetic"] * 3, "POCO": ["a", " a ", "b"]}),
        field_name="synthetic",
    )
    assert meta["well_count"] == 2


@pytest.mark.parametrize("rate", [None, float("nan"), float("inf"), -1])
@pytest.mark.parametrize("revenue", [0, 100])
def test_unknown_royalty_rate_cannot_use_default(rate, revenue):
    with pytest.raises(ValueError, match="production_rate_bpd"):
        calculate_royalties_concession(revenue, rate)


def test_special_participation_requires_explicit_basis():
    with pytest.raises(ValueError, match="schedule"):
        calculate_special_participation(100)
    with pytest.raises(ValueError, match="schedule"):
        ConcessionRegime().calculate(100, 0, 0, 1)


def test_special_participation_hand_calculation():
    """Synthetic bands: (150 - 100) * 0.2 = 10 currency units per quarter."""
    schedule = ParticipationSchedule(
        currency="TEST",
        period="quarter",
        bands=((100, 0), (float("inf"), 0.2)),
        source="Synthetic hand calculation in test_special_participation_hand_calculation",
    )
    assert (
        calculate_special_participation(
            150, schedule=schedule, currency="TEST", period="quarter"
        )
        == 10
    )
    with pytest.raises(ValueError, match="currency|period"):
        calculate_special_participation(
            150, schedule=schedule, currency="OTHER", period="quarter"
        )
    with pytest.raises(ValueError, match="currency|period"):
        calculate_special_participation(
            150, schedule=schedule, currency="TEST", period="year"
        )


@pytest.mark.parametrize("period", ["02/2024", "2024/13", "prefix2024/02", ""])
def test_client_rejects_mixed_valid_and_invalid_rows(tmp_path, period):
    """One valid plus one invalid row must raise, rather than return one row."""
    csv = f"Campo;Período\n;\n;\nsynthetic;2024/02\nsynthetic;{period}\n"
    with pytest.raises(ValueError, match="period"):
        ANPClient(cache_dir=str(tmp_path))._read_zip(archive(csv))


def test_invalid_download_does_not_replace_valid_cache(tmp_path):
    """Invalid replacement bytes must leave the previously retained bytes intact."""
    client = ANPClient(cache_dir=str(tmp_path))
    retained = archive("Campo;Período\n;\n;\nsynthetic;2024/02\n")
    cache = tmp_path / client._cache_key(2024, 2)
    cache.write_bytes(retained)
    with patch("worldenergydata.brazil_anp.production.anp_client.requests") as requests:
        requests.get.return_value.content = archive()
        with pytest.raises(ValueError):
            client.download_month(2024, 2, force_refresh=True)
    assert cache.read_bytes() == retained


@pytest.mark.parametrize("missing", [None, pd.NA, "", " "])
def test_legacy_schema_also_rejects_missing_names(missing):
    raw = pd.DataFrame(
        {
            "campo": [missing],
            "poco": ["synthetic-well"],
            "data": ["2024-02-01"],
            "oleo_sm3": [0],
            "condensado_sm3": [0],
            "gas_mm3": [0],
            "agua_sm3": [0],
        }
    )
    with pytest.raises(ValueError, match="identity"):
        WellProductionLoader().load(raw)


@pytest.mark.parametrize(
    "bands",
    [
        (),
        ((100, 0.2),),
        ((100, 0), (50, 0.2), (float("inf"), 0.2)),
        ((float("inf"), -0.2),),
        ((float("inf"), float("nan")),),
    ],
)
def test_invalid_participation_bands_are_rejected(bands):
    schedule = ParticipationSchedule(
        currency="TEST",
        period="quarter",
        bands=bands,
        source="Synthetic invalid-input case",
    )
    with pytest.raises(ValueError, match="schedule"):
        calculate_special_participation(
            150, schedule=schedule, currency="TEST", period="quarter"
        )


@pytest.mark.parametrize(
    "currency,period,source",
    [("", "quarter", "test"), ("TEST", "", "test"), ("TEST", "quarter", " ")],
)
def test_participation_schedule_requires_provenance(currency, period, source):
    schedule = ParticipationSchedule(
        currency=currency, period=period, bands=((float("inf"), 0),), source=source
    )
    with pytest.raises(ValueError, match="schedule"):
        calculate_special_participation(
            0, schedule=schedule, currency=currency, period=period
        )


def test_concession_uses_the_explicit_participation_schedule():
    """Synthetic case: net basis 200 - 25 - 25 = 150; SP (150 - 100)*0.2 = 10."""
    schedule = ParticipationSchedule(
        currency="TEST",
        period="quarter",
        bands=((100, 0), (float("inf"), 0.2)),
        source="Synthetic hand calculation in this test",
    )
    result = ConcessionRegime().calculate(
        200,
        25,
        25,
        0,
        participation_schedule=schedule,
        currency="TEST",
        period="quarter",
    )
    assert result.special_participation == 10
