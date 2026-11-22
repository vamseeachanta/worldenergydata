"""Rated-capacity contract from issue #742 (2026).

Numeric fixtures are synthetic parser inputs, not equipment ratings or operating
limits. No calculation is performed: each expected result is the literal input
in the same units. Missing source evidence is represented by None, never zero.
"""

import csv
from dataclasses import asdict
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldenergydata.vessel_fleet.models.drilling_rig import DrillingRigEntry
from worldenergydata.vessel_fleet.schemas.drilling_rig import DrillingRigSchema

FIELDS = ("CONDUCTOR_MOMENT_CAPACITY_KN_M", "FLEXJOINT_ANGLE_RATING_DEG")
CURATED = (
    Path(__file__).resolve().parents[3]
    / "packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet"
    / "_data/curated"
)


@pytest.mark.parametrize("field", FIELDS)
def test_missing_rating_is_unknown(field):
    assert getattr(DrillingRigSchema(VESSEL_NAME="T"), field) is None
    assert getattr(DrillingRigEntry(vessel_name="T"), field.lower()) is None


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [None, "", "  "])
def test_blank_csv_rating_is_unknown(field, value):
    record = DrillingRigSchema(VESSEL_NAME="T", **{field: value})
    assert record.model_dump()[field] is None


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [1.25, " 1.25 "])
def test_rating_survives_schema_and_model_serialization(field, value):
    """Synthetic identity check: float('1.25') = 1.25, without conversion."""
    record = DrillingRigSchema(VESSEL_NAME="T", **{field: value})
    assert record.model_dump()[field] == 1.25
    model = DrillingRigEntry(
        vessel_name="T", **{field.lower(): record.model_dump()[field]}
    )
    assert asdict(model)[field.lower()] == 1.25


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize(
    "value", [-1, 0, "-1", "0", "nan", "inf", "-inf", float("nan"), float("inf"), "bad"]
)
def test_invalid_rating_is_rejected(field, value):
    """A usable rated magnitude is finite and positive; this is no design limit."""
    with pytest.raises(ValidationError):
        DrillingRigSchema(VESSEL_NAME="T", **{field: value})


def test_curated_csv_has_explicit_unknown_ratings():
    with (CURATED / "drilling_rigs.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    header, *records = rows
    assert all(header.count(field) == 1 for field in FIELDS)
    assert records
    assert all(len(row) == len(header) for row in records)
    for field in FIELDS:
        assert all(row[header.index(field)] == "" for row in records)


def test_curated_parquet_agrees_with_csv_ratings():
    import pandas as pd

    parquet = pd.read_parquet(CURATED / "drilling_rigs.parquet")
    csv_frame = pd.read_csv(CURATED / "drilling_rigs.csv", keep_default_na=False)
    assert (
        parquet["RIG_NAME"].fillna("").tolist()
        == csv_frame["RIG_NAME"].fillna("").tolist()
    )
    for field in FIELDS:
        assert field in parquet.columns
        assert str(parquet[field].dtype) == "float64"
        assert parquet[field].isna().all()
        assert csv_frame[field].eq("").all()


def test_legacy_positional_moonpool_argument_keeps_its_meaning():
    """Legacy constructor: base fields, 19 rig fields, then moonpool length.

    The synthetic length 1.25 must still bind to moonpool_length_m rather than
    either new capacity field; adding optional ratings must preserve callers.
    """
    from dataclasses import fields

    from worldenergydata.vessel_fleet.models.base import BaseVesselEntry

    base_args = ["T"] + [None] * (len(fields(BaseVesselEntry)) - 1)
    rig_args_before_moonpool = [None] * 19
    record = DrillingRigEntry(*base_args, *rig_args_before_moonpool, 1.25)
    assert record.moonpool_length_m == 1.25
    assert record.conductor_moment_capacity_kn_m is None
    assert record.flexjoint_angle_rating_deg is None
