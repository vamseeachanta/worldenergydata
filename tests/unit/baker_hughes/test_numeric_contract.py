"""Synthetic integer-domain examples for issue #1334, not source qualification.

Hand check: counts enumerate rigs, so zero and whole positive numbers preserve
value; -1 is negative, 1.5 has a fractional part and comma-separated strings
have no declared locale. The exact integer 9007199254740993 must retain its
last digit; these are chosen test inputs, not engineering acceptance limits.
"""

import pandas as pd
import pytest

from worldenergydata.baker_hughes.loader import load_pivot_table, load_summary


def write_workbook(tmp_path, kind, counts):
    path = tmp_path / "counts.xlsx"
    if kind == "pivot":
        frame = pd.DataFrame(
            {
                "PublishDate": ["2026-01-01"] * len(counts),
                "RigCount": counts,
                "WellDepth": [10] * len(counts),
                "WaterDepth": [""] * len(counts),
                "Country": ["Synthetic"] * len(counts),
            }
        )
        sheet = "Pivot Table"
    else:
        frame = pd.DataFrame(
            {"State": ["Synthetic"] * len(counts), "2026-01-01": counts}
        )
        sheet = "Rigs by State"
    frame.to_excel(path, sheet_name=sheet, index=False)
    return path


def load_counts(path, kind):
    return (
        load_pivot_table(path, depth_unit="ft")
        if kind == "pivot"
        else load_summary(path)
    )


@pytest.mark.parametrize("kind", ["pivot", "summary"])
@pytest.mark.parametrize(
    "bad", [None, "", "NA", "bad", 1.5, "1,234", "1,5", -1, "inf", "NaN", True]
)
def test_rejects_bad_counts(tmp_path, kind, bad):
    """Each input violates the nonnegative whole-count contract above."""
    path = write_workbook(tmp_path, kind, [bad])
    with pytest.raises(ValueError, match=r"rig_count.*row.*nonnegative integer"):
        load_counts(path, kind)


@pytest.mark.parametrize("kind", ["pivot", "summary"])
def test_preserves_whole_counts(tmp_path, kind):
    """Hand check: [0, 2, 3, 9007199254740993] is unchanged by parsing."""
    path = write_workbook(tmp_path, kind, [0, 2.0, "3", "9007199254740993"])
    result = load_counts(path, kind)
    assert result.rig_count.tolist() == [0, 2, 3, 9007199254740993]
    assert (
        result.attrs["numeric_validation"]["rig_count"] == "nonnegative_integer_reject"
    )


def test_invalid_count_is_checked_before_filter(tmp_path):
    """A filter selecting no rows must not hide an invalid input count."""
    path = write_workbook(tmp_path, "pivot", ["bad"])
    with pytest.raises(ValueError, match="rig_count"):
        load_pivot_table(path, country="absent", depth_unit="ft")


@pytest.mark.parametrize("column", ["WellDepth", "WaterDepth"])
@pytest.mark.parametrize("bad", ["bad", "NA", "1,234", "10 m", "inf", "NaN", -1, True])
def test_invalid_depth_rejected(tmp_path, column, bad):
    """F3/F4: invalid/nonfinite/negative depth is distinct from an empty cell."""
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame[column] = bad
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    with pytest.raises(ValueError, match=r"depth_ft.*row.*finite nonnegative"):
        load_pivot_table(path, depth_unit="ft")


def test_ambiguous_depth_requires_declaration(tmp_path):
    """F5/F6: unitless numeric headers do not establish a source unit."""
    path = write_workbook(tmp_path, "pivot", [1])
    with pytest.raises(ValueError, match="depth_unit.*required"):
        load_pivot_table(path)


@pytest.mark.parametrize("unit", ["yards", "FT", "", "survey_ft"])
def test_unsupported_unit_rejected(tmp_path, unit):
    """Only international feet and metres are supported; no guessed aliases."""
    path = write_workbook(tmp_path, "pivot", [1])
    with pytest.raises(ValueError, match="depth_unit"):
        load_pivot_table(path, depth_unit=unit)


@pytest.mark.parametrize("column", ["WellDepth", "WaterDepth"])
def test_header_declaration_mismatch_rejected(tmp_path, column):
    """A metre-labelled column cannot be declared feet by the caller."""
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame.rename(columns={column: column + "_m"}).to_excel(
        path, sheet_name="Pivot Table", index=False
    )
    with pytest.raises(ValueError, match="unit mismatch"):
        load_pivot_table(path, depth_unit="ft")


def test_declared_metres_converted_to_labelled_feet(tmp_path):
    """Hand check: 3.048 m / (0.3048 m/ft) = 10 ft, exactly.

    Source: NIST SP 811 (2008), Appendix B.6, international foot definition
    from the 1959 agreement; 1 ft = 0.3048 m exactly.
    https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf
    Empty water depth remains missing; it is never inferred as zero.
    """
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth"] = "3.048"
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    result = load_pivot_table(path, depth_unit="m")
    assert result.well_depth_ft.tolist() == [10.0]
    assert result.water_depth_ft.isna().all()
    assert result.attrs["numeric_validation"]["output_depth_unit"] == "ft"
    assert result.attrs["numeric_validation"]["source_depth_units"] == {
        "well_depth_ft": "m",
        "water_depth_ft": "m",
    }


def test_detects_units_per_header(tmp_path):
    """Hand check from NIST B.6: 3.048 m = 10 ft; 2 ft stays 2 ft."""
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame = frame.rename(
        columns={"WellDepth": "WellDepth_m", "WaterDepth": "WaterDepth_ft"}
    )
    frame["WellDepth_m"] = "3.048"
    frame["WaterDepth_ft"] = 2
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    result = load_pivot_table(path)
    assert result.well_depth_ft.tolist() == [10.0]
    assert result.water_depth_ft.tolist() == [2.0]
    assert "WellDepth_m" not in result


def test_duplicate_depth_representation_rejected(tmp_path):
    """Duplicate ambiguous/labelled versions cannot override each other."""
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth_m"] = 2
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    with pytest.raises(ValueError, match="one source column"):
        load_pivot_table(path, depth_unit="ft")


@pytest.mark.parametrize("kind", ["pivot", "summary"])
@pytest.mark.parametrize("bad", ["1_234", "1 234", "1\u202f234"])
def test_undeclared_separators_rejected(tmp_path, kind, bad):
    """No locale or grouping convention is declared for any separator."""
    path = write_workbook(tmp_path, kind, [bad])
    with pytest.raises(ValueError, match="rig_count"):
        load_counts(path, kind)


@pytest.mark.parametrize("unit", ["ft", "m"])
@pytest.mark.parametrize("bad", ["1e1000000", "1e-1000000", "1_234"])
def test_unrepresentable_or_grouped_depth_rejected(tmp_path, unit, bad):
    """Huge/tiny synthetic depths must not overflow or silently become zero.

    The chosen exponents are stress inputs, not acceptance limits. A finite,
    nonzero Decimal cannot be represented as float infinity or zero without
    losing its finite/nonzero classification. Grouping has no declared locale.
    """
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth"] = bad
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    with pytest.raises(ValueError, match="well_depth_ft.*row"):
        load_pivot_table(path, depth_unit=unit)
