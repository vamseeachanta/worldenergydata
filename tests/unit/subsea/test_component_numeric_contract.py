"""Component-domain regressions for issue #1305, using synthetic records.

All magnitudes below are test choices, not design limits or catalog values.
Hand check: positive means v > 0; nonnegative means v >= 0, so -1 fails
and zero is allowed only for optional weight. Neither infinity nor NaN is
finite. These logical requirements come from issue #1305's input contract.
"""

import csv

import pytest
from pydantic import ValidationError

from worldenergydata.subsea.models.mooring import (
    MooringComponentSpec,
    load_mooring_components,
)
from worldenergydata.subsea.models.rigid_jumper import (
    RigidJumperSpec,
    load_rigid_jumpers,
)

CASES = {
    "jumper": (
        RigidJumperSpec,
        load_rigid_jumpers,
        {
            "component_id": "synthetic",
            "manufacturer": "NA",
            "od_in": 2,
            "wall_thickness_in": 0.5,
            "length_ft": 10,
            "material_grade": "NA",
            "pressure_rating_psi": 3,
            "weight_air_kips": 1,
            "connection_type": "NA",
            "data_source": "synthetic",
            "notes": "NA",
        },
        ("od_in", "wall_thickness_in", "pressure_rating_psi"),
        "weight_air_kips",
    ),
    "mooring": (
        MooringComponentSpec,
        load_mooring_components,
        {
            "component_id": "synthetic",
            "manufacturer": "NA",
            "component_type": "chain",
            "size_mm": 2,
            "mbl_kn": 3,
            "weight_kg_per_m": 1,
            "material": "NA",
            "grade": "NA",
            "data_source": "synthetic",
            "notes": "NA",
        },
        ("mbl_kn",),
        "weight_kg_per_m",
    ),
}
FIELDS = [
    (kind, field) for kind, case in CASES.items() for field in (*case[3], case[4])
]


def csv_record(tmp_path, kind, changes):
    model, load, base, _, _ = CASES[kind]
    path = tmp_path / (kind + ".csv")
    row = base | changes
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)
    return load, path, model, row


@pytest.mark.parametrize(("kind", "field"), FIELDS)
@pytest.mark.parametrize("bad", [float("inf"), float("-inf"), float("nan"), -1])
@pytest.mark.parametrize("route", ["model", "csv"])
def test_rejects_nonfinite_or_negative(tmp_path, kind, field, bad, route):
    """Each of the four positivity fields and both weights must reject."""
    load, path, model, row = csv_record(tmp_path, kind, {field: bad})
    with pytest.raises(ValidationError, match=field):
        model(**row) if route == "model" else load(path)


@pytest.mark.parametrize(
    ("kind", "field"),
    [(kind, field) for kind, case in CASES.items() for field in case[3]],
)
def test_positive_fields_reject_zero(kind, field):
    """Hand check: 0 is not strictly positive."""
    model, _, row, _, _ = CASES[kind]
    with pytest.raises(ValidationError, match=field):
        model(**(row | {field: 0}))


@pytest.mark.parametrize("kind", CASES)
@pytest.mark.parametrize("weight", [0, 1, None])
def test_optional_weight_accepts_nonnegative_or_absent(kind, weight):
    """Hand check: 0 and 1 are nonnegative, and missing weight is permitted."""
    model, _, row, _, field = CASES[kind]
    assert getattr(model(**(row | {field: weight})), field) == weight


@pytest.mark.parametrize("kind", CASES)
@pytest.mark.parametrize("token", ["NA", "N/A", "null", "None", "nan"])
def test_csv_preserves_literal_text(tmp_path, kind, token):
    """Literal text equality requires no engineering magnitude assumption."""
    _, _, row, _, _ = CASES[kind]
    text_fields = [key for key, value in row.items() if value == "NA"]
    load, path, _, _ = csv_record(tmp_path, kind, dict.fromkeys(text_fields, token))
    result = load(path)[0]
    for field in text_fields:
        assert getattr(result, field) == token


@pytest.mark.parametrize("kind", CASES)
def test_csv_empty_optional_fields_remain_absent(tmp_path, kind):
    """Only an empty cell denotes absence; zero weight stays zero."""
    weight = CASES[kind][4]
    load, path, _, _ = csv_record(tmp_path, kind, {"notes": "", weight: ""})
    result = load(path)[0]
    assert result.notes is None
    assert getattr(result, weight) is None


@pytest.mark.parametrize(("kind", "field"), FIELDS)
def test_csv_na_in_numeric_field_rejected(tmp_path, kind, field):
    """NA in numeric cells must fail, including optional weights."""
    load, path, _, _ = csv_record(tmp_path, kind, {field: "NA"})
    with pytest.raises(ValidationError, match=field):
        load(path)
