"""Shared worked example: docs/examples/tabular-input-validation.md.

Independent hand checks: three rigs remain 3; zero rigs remain 0; 1.5 is not
whole and comma-separated counts have no declared locale. NIST SP 811 (2008),
Appendix B.6 defines 1 international ft = 0.3048 m exactly, so 3.048 m / 0.3048
m/ft = 10 ft. Depth 0 stays 0; an absent water depth stays absent. For both
component types, 2, 0.5 and 3 are finite positive test inputs; weight 1 is
nonnegative, -1 is negative, and infinity and NaN are nonfinite. Literal text
NA is exactly the two-letter string, not absence. No physical capacity is
inferred. All magnitudes are synthetic choices, not catalog or design limits.
Source: https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf
Input-domain rejection rules: issues #1334 and #1305.
"""

import csv
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from worldenergydata.baker_hughes.loader import load_pivot_table, load_summary
from worldenergydata.subsea import ManifoldSupplierLoader
from worldenergydata.subsea.models.mooring import load_mooring_components
from worldenergydata.subsea.models.rigid_jumper import load_rigid_jumpers

FIXTURES = Path(__file__).parents[1] / "fixtures" / "tabular_validation"


def rows(name):
    with (FIXTURES / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


RIG_ROWS = rows("rig_counts.csv")


@pytest.mark.parametrize("row", RIG_ROWS, ids=lambda row: row["case"])
def test_pivot_worked_csv(tmp_path, row):
    """CSV is a transparent input inventory; the loader still reads Excel."""
    path = tmp_path / "pivot.xlsx"
    frame = pd.DataFrame(
        [
            {
                "PublishDate": "2026-01-01",
                "RigCount": row["rig_count"],
                row["well_header"]: row["well_depth"],
                row["water_header"]: row["water_depth"],
            }
        ]
    )
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    errors = {
        "missing_count": "rig_count",
        "invalid_count": "rig_count",
        "fractional_count": "rig_count",
        "locale_count": "rig_count",
        "invalid_well_depth": "well_depth_ft",
        "invalid_water_depth": "water_depth_ft",
        "unit_mismatch": "unit mismatch",
        "undeclared_unit": "depth_unit.*required",
    }
    if row["case"] in errors:
        with pytest.raises(ValueError, match=errors[row["case"]]):
            load_pivot_table(path, depth_unit=row["depth_unit"] or None)
        return
    result = load_pivot_table(path, depth_unit=row["depth_unit"])
    if row["case"] == "clean":
        assert result.rig_count.tolist() == [3]
        assert result.well_depth_ft.tolist() == [10.0]
        assert result.water_depth_ft.isna().all()
    else:
        assert result.rig_count.tolist() == [0]
        assert result.well_depth_ft.tolist() == [0.0]
        assert result.water_depth_ft.tolist() == [0.0]


@pytest.mark.parametrize("row", RIG_ROWS[:6], ids=lambda row: row["case"])
def test_summary_worked_csv(tmp_path, row):
    """Summary has no depth inputs; the first six CSV rows exercise counts."""
    path = tmp_path / "summary.xlsx"
    pd.DataFrame([{"State": "Synthetic", "2026-01-01": row["rig_count"]}]).to_excel(
        path, sheet_name="Rigs by State", index=False
    )
    if row["case"] not in {"clean", "zero"}:
        with pytest.raises(ValueError, match="rig_count"):
            load_summary(path)
    else:
        assert load_summary(path).rig_count.tolist() == (
            [3] if row["case"] == "clean" else [0]
        )


@pytest.mark.parametrize(
    ("name", "load", "positive", "weight"),
    [
        ("rigid_jumpers.csv", load_rigid_jumpers, "od_in", "weight_air_kips"),
        ("mooring.csv", load_mooring_components, "mbl_kn", "weight_kg_per_m"),
    ],
)
@pytest.mark.parametrize(
    "case",
    [
        "clean",
        "positive_infinity",
        "not_a_number",
        "negative_weight",
        "infinite_weight",
        "invalid_numeric_text",
        "absent_weight",
    ],
)
def test_component_worked_csv(tmp_path, name, load, positive, weight, case):
    """Each defective row is tried separately because loading is fail-fast."""
    row = next(row for row in rows(name) if row["case"] == case)
    row.pop("case")
    path = tmp_path / name
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)
    if case in {"positive_infinity", "not_a_number"}:
        with pytest.raises(ValidationError, match=positive):
            load(path)
    elif case in {"negative_weight", "infinite_weight", "invalid_numeric_text"}:
        with pytest.raises(ValidationError, match=weight):
            load(path)
    else:
        result = load(path)[0]
        assert result.manufacturer == "NA"
        assert getattr(result, weight) == (1.0 if case == "clean" else None)
        assert result.notes == ("NA" if case == "clean" else None)
        assert getattr(result, positive) == (2.0 if positive == "od_in" else 3.0)


def test_supplier_worked_csv():
    """Hand check: 'alpha' selects the sole record; '' identifies no company."""
    loader = ManifoldSupplierLoader(FIXTURES / "suppliers.csv")
    with pytest.raises(ValueError, match="non-whitespace"):
        loader.get("")
    result = loader.get("alpha")
    assert result.COMPANY == "Synthetic Alpha"
    assert result.HQ_COUNTRY == "NA"
