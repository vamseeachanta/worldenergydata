"""Riser-handling field contract from issue 698, not equipment design data."""

from worldenergydata.vessel_fleet.schemas.drilling_rig import DrillingRigSchema


def test_riser_handling_survives_tabular_round_trip():
    """Synthetic inputs: decimal strings represent exactly the stated numbers.

    Independent expectations: int('2') = 2; float('12.5') = 12.5.
    The values test parsing only and supply no equipment or acceptance limits.
    """
    row = {
        "VESSEL_NAME": "",
        "N_TENSIONERS": "2",
        "TENSIONER_TYPE": "direct_acting",
        "TENSIONER_CAPACITY_KIPS": "12.5",
        "TENSIONER_STROKE_FT": "12.5",
        "TJ_STROKE_FT": "12.5",
        "N_TENSION_WIRES": "2",
        "MOONPOOL_LENGTH_M": "12.5",
        "MOONPOOL_WIDTH_M": "12.5",
    }
    record = DrillingRigSchema(**row).model_dump()
    for field in ("N_TENSIONERS", "N_TENSION_WIRES"):
        assert record[field] == 2
    for field in (
        "TENSIONER_CAPACITY_KIPS",
        "TENSIONER_STROKE_FT",
        "TJ_STROKE_FT",
        "MOONPOOL_LENGTH_M",
        "MOONPOOL_WIDTH_M",
    ):
        assert record[field] == 12.5
    assert record["TENSIONER_TYPE"] == "direct_acting"
    assert DrillingRigSchema(**record).model_dump() == record


def test_riser_handling_domain_model_retains_capabilities():
    """Synthetic parser example: supplied scalar values stay unchanged."""
    from worldenergydata.vessel_fleet.models.drilling_rig import DrillingRigEntry

    record = DrillingRigEntry(
        vessel_name="",
        n_tensioners=2,
        tensioner_type="direct_acting",
        tensioner_capacity_kips=12.5,
        tensioner_stroke_ft=12.5,
        tj_stroke_ft=12.5,
        n_tension_wires=2,
    )
    assert record.n_tensioners == 2
    assert record.tensioner_type == "direct_acting"
    assert record.tensioner_capacity_kips == 12.5
    assert record.tensioner_stroke_ft == 12.5
    assert record.tj_stroke_ft == 12.5
    assert record.n_tension_wires == 2


NUMBER_FIELDS = (
    "N_TENSIONERS",
    "N_TENSION_WIRES",
    "TENSIONER_CAPACITY_KIPS",
    "TENSIONER_STROKE_FT",
    "TJ_STROKE_FT",
)


def test_unknown_and_zero_remain_distinct():
    """Absent/blank is unknown; explicit decimal zero parses to mathematical zero."""
    from worldenergydata.vessel_fleet.models.drilling_rig import DrillingRigEntry

    for field in (*NUMBER_FIELDS, "TENSIONER_TYPE"):
        assert getattr(DrillingRigSchema(VESSEL_NAME=""), field) is None
        assert getattr(DrillingRigEntry(vessel_name=""), field.lower()) is None
        for blank in (None, "", "  "):
            assert (
                getattr(DrillingRigSchema(VESSEL_NAME="", **{field: blank}), field)
                is None
            )
    for field in NUMBER_FIELDS:
        assert getattr(DrillingRigSchema(VESSEL_NAME="", **{field: "0"}), field) == 0


def test_invalid_riser_handling_numbers_are_rejected():
    """Counts/ratings are nonnegative finite numbers, never boolean flags.

    This is a representation domain test, not an equipment acceptance check.
    Negative one, infinities and NaN fall outside that mathematical domain.
    """
    import pytest
    from pydantic import ValidationError

    for field in NUMBER_FIELDS:
        for invalid in (
            -1,
            "-1",
            "nan",
            "inf",
            "-inf",
            float("nan"),
            float("inf"),
            True,
            False,
        ):
            with pytest.raises(ValidationError):
                DrillingRigSchema(VESSEL_NAME="", **{field: invalid})
    for field in ("N_TENSIONERS", "N_TENSION_WIRES"):
        for fraction in ("2.5", 2.5):
            with pytest.raises(ValidationError):
                DrillingRigSchema(VESSEL_NAME="", **{field: fraction})
        assert getattr(DrillingRigSchema(VESSEL_NAME="", **{field: "2.0"}), field) == 2
