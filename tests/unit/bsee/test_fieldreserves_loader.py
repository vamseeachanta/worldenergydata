"""Synthetic fixtures only; no public-source rows are redistributed."""

import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee import fieldreserves_loader as loader

FIXTURES = Path(__file__).parents[2] / "fixtures/bsee/fieldreserves"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("live network forbidden")

    monkeypatch.setattr(urllib.request, "urlopen", denied)


def archive(name, body):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, body)
    return buf.getvalue()


def history_archive():
    df = pd.read_csv(FIXTURES / "synthetic_history.csv")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as x:
        df.to_excel(x, sheet_name="2023 OFFLDHIST", index=False)
    return archive("2023 HIST/2023 OFFLDHIST.xlsx", output.getvalue())


def test_history_preserves_codes_and_types_with_citations():
    df = loader.load_history(history_archive(), retrieved_utc="2026-10-11T00:00:00Z")
    assert df.FIELD_NAME_CODE.tolist() == ["ZZ001", "ZZ001", "ZZ002"]
    assert str(df.YEAR.dtype) == "Int64"
    assert str(df.ORIGINAL_OIL_RESERVES.dtype) == "Float64"
    assert df.REMAINING_BOE.iloc[1] == 180
    assert df.SOURCE_URL.str.endswith("2023%20Hist.zip").all()
    assert df.SOURCE_SHA256.str.fullmatch("[0-9a-f]{64}").all()
    assert df.SOURCE_MEMBER.eq("2023 HIST/2023 OFFLDHIST.xlsx").all()


def test_master_keeps_each_field_lease_and_first_production_date():
    raw = (FIXTURES / "synthetic_master.csv").read_bytes()
    df = loader.load_master(
        archive("mastproddelimit.txt", raw), retrieved_utc="2026-10-11T00:00:00Z"
    )
    assert len(df) == 2
    assert df.LEASE_NUMBER.tolist() == ["G00001", "G00002"]
    assert df.FIELD_NAME_CODE.eq("ZZ001").all()
    assert pd.api.types.is_datetime64_any_dtype(df.FIRST_PRODUCTION_DATE)


@pytest.mark.parametrize("reader", ["load_history", "load_master"])
def test_missing_renamed_member_fails_loudly(reader):
    with pytest.raises(ValueError, match="member"):
        getattr(loader, reader)(
            archive("renamed.txt", b"synthetic"), retrieved_utc="2026-10-11T00:00:00Z"
        )


def test_master_wrong_column_count_fails():
    with pytest.raises(ValueError, match="10 columns"):
        loader.load_master(
            archive("mastproddelimit.txt", b'"ZZ001","G00001"\n'),
            retrieved_utc="2026-10-11T00:00:00Z",
        )


def test_master_source_hash_marker_is_preserved_not_zero():
    raw = (
        (FIXTURES / "synthetic_master.csv")
        .read_bytes()
        .replace(b'"20"', b'"################"')
    )
    df = loader.load_master(
        archive("mastproddelimit.txt", raw), retrieved_utc="2026-10-11T00:00:00Z"
    )
    assert pd.isna(df.CONDENSATE_STB.iloc[0])
    assert df.SOURCE_MARKERS.iloc[0] == "CONDENSATE_STB=################"


def test_monthly_access_only_reports_missing_decoder():
    with pytest.raises(NotImplementedError, match="Access"):
        loader.load_monthly(
            archive("2023 FldMoPro/2023 FldMoProd.accdb", b"synthetic"),
            retrieved_utc="2026-10-11T00:00:00Z",
        )
