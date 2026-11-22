"""Synthetic integer-domain examples for issue #1334, not source qualification.

Hand check: counts enumerate rigs, so zero and whole positive numbers preserve
value; -1 is negative, 1.5 has a fractional part and comma-separated strings
have no declared locale. The exact integer 9007199254740993 must retain its
last digit; these are chosen test inputs, not engineering acceptance limits.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import ROUND_UP, DefaultContext, Inexact, Rounded, localcontext

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


@pytest.mark.parametrize("column", ["WellDepth", "WaterDepth"])
@pytest.mark.parametrize("suffixed", [False, True], ids=["declared", "header"])
@pytest.mark.parametrize("unit", ["ft", "m"])
@pytest.mark.parametrize(
    "context_setting",
    ["low_precision", "trapped_rounding", "restricted_exponents", "round_up"],
)
def test_depth_conversion_is_independent_of_decimal_context(
    tmp_path, column, suffixed, unit, context_setting
):
    """30.49 m = 304900/3048 ft, regardless of caller Decimal settings.

    The rational hand check uses the existing international-foot definition;
    float division supplies an independent expected value. Both depth fields
    and both unit declaration routes must preserve it. The enclosing context
    must also retain its settings and flags.
    """
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame[column] = "30.49"
    if suffixed:
        frame = frame.rename(
            columns={
                "WellDepth": f"WellDepth_{unit}",
                "WaterDepth": f"WaterDepth_{unit}",
            }
        )
    frame.to_excel(path, sheet_name="Pivot Table", index=False)

    with localcontext() as context:
        if context_setting == "low_precision":
            context.prec = 2
        elif context_setting == "trapped_rounding":
            context.traps[Inexact] = context.traps[Rounded] = True
        elif context_setting == "restricted_exponents":
            context.Emax = 0
        else:
            context.prec = 2
            context.rounding = ROUND_UP
        original = context.copy()
        result = load_pivot_table(path, depth_unit=None if suffixed else unit)
        assert context.prec == original.prec
        assert context.rounding == original.rounding
        assert context.Emax == original.Emax
        assert context.traps == original.traps
        assert context.flags == original.flags

    output = "well_depth_ft" if column == "WellDepth" else "water_depth_ft"
    expected = 304900 / 3048 if unit == "m" else 30.49
    assert result[output].tolist() == [expected]
    assert result.attrs["numeric_validation"]["source_depth_units"][output] == unit


def test_depth_conversion_rounds_exact_ratio_once(tmp_path):
    """The exact feet value is just above a binary64 rounding midpoint.

    5490788665690109.3328000000003048 m corresponds exactly to
    18014398509481986.000000000001 ft. Adjacent floats are 18014398509481984
    and 18014398509481988; the latter is nearer. Rounding the quotient to
    28 decimal digits first erases the difference above the midpoint.
    """
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth"] = "5490788665690109.3328000000003048"
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    assert load_pivot_table(path, depth_unit="m").well_depth_ft.tolist() == [
        18014398509481988.0
    ]


@pytest.mark.parametrize("worker", [False, True], ids=["current_thread", "new_thread"])
def test_depth_conversion_does_not_inherit_default_context(
    tmp_path, monkeypatch, worker
):
    """A modified Decimal default must not contaminate conversion contexts."""
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth"] = "30.49"
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    monkeypatch.setattr(DefaultContext, "prec", 2)
    monkeypatch.setattr(DefaultContext, "rounding", ROUND_UP)
    monkeypatch.setattr(DefaultContext, "Emax", 0)
    monkeypatch.setitem(DefaultContext.traps, Inexact, True)
    monkeypatch.setitem(DefaultContext.traps, Rounded, True)
    if worker:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(load_pivot_table, path, depth_unit="m").result()
    else:
        result = load_pivot_table(path, depth_unit="m")
    assert result.well_depth_ft.tolist() == [304900 / 3048]


@pytest.mark.parametrize(
    "depth,expected",
    [
        ("8e-325", 5e-324),
        ("5e307", (5 * 10**311) / 3048),
        ("100000000000000000000e-330", 10**20 / (3048 * 10**326)),
    ],
)
def test_metres_at_float_range_boundaries(tmp_path, depth, expected):
    """Loose exponent guards must retain subnormal and large finite outputs.

    8e-325 / 0.3048 is above half the least binary64 subnormal, so rounds
    to 5e-324 ft. 5e307 / 0.3048 remains below the greatest finite float.
    These are representation stress inputs, not physical depth limits.
    """
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth"] = depth
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    assert load_pivot_table(path, depth_unit="m").well_depth_ft.tolist() == [expected]


@pytest.mark.parametrize("depth", ["7e-325", "1e-326", "1e308", "6e307"])
def test_metres_outside_float_range_rejected(tmp_path, depth):
    """Exact conversions must still reject float overflow and rounding to zero."""
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth"] = depth
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    with pytest.raises(ValueError, match="well_depth_ft.*row"):
        load_pivot_table(path, depth_unit="m")


@pytest.mark.parametrize("unit", ["ft", "m"])
def test_zero_depth_sign_is_preserved(tmp_path, unit):
    """Both declared units retain the sign of a textual negative zero."""
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth"] = "-0"
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    result = load_pivot_table(path, depth_unit=unit)
    assert result.well_depth_ft.iloc[0].hex() == "-0x0.0p+0"


@pytest.mark.parametrize("kind", ["pivot", "summary"])
@pytest.mark.parametrize("count", ["9007199254740993", "1.5"])
def test_count_contract_with_restrictive_decimal_context(tmp_path, kind, count):
    """A whole count stays exact and a fraction remains rejected under traps."""
    path = write_workbook(tmp_path, kind, [count])
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_UP
        context.traps[Inexact] = context.traps[Rounded] = True
        if count == "1.5":
            with pytest.raises(ValueError, match="rig_count"):
                load_counts(path, kind)
        else:
            assert load_counts(path, kind).rig_count.tolist() == [9007199254740993]


@pytest.mark.parametrize("depth", ["1e-999999999999", "1e999999999999"])
def test_compact_extreme_exponents_rejected_before_ratio_allocation(
    tmp_path, monkeypatch, depth
):
    """Extreme exponent tokens must be rejected before expensive allocation.

    The sentinel makes a removed preflight fail without allocating an enormous
    integer in the test process. The workbook loader and rejection are real.
    """
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth"] = depth
    frame.to_excel(path, sheet_name="Pivot Table", index=False)

    def unexpected_ratio(*args):
        raise AssertionError("Extreme depth reached rational allocation")

    monkeypatch.setattr(
        "worldenergydata.baker_hughes.loader.Fraction", unexpected_ratio
    )
    with pytest.raises(ValueError, match="well_depth_ft.*row"):
        load_pivot_table(path, depth_unit="m")


def test_numeric_metres_use_read_back_decimal_value(tmp_path):
    """A numeric Excel 30.49 cell is parsed as decimal 30.49, then converted.

    The parser preserves str(read_back_value), not any earlier binary input
    precision or source measurement precision. 30.49 m = 304900/3048 ft.
    """
    path = write_workbook(tmp_path, "pivot", [1])
    frame = pd.read_excel(path, keep_default_na=False, dtype=object)
    frame["WellDepth"] = 30.49
    frame.to_excel(path, sheet_name="Pivot Table", index=False)
    assert load_pivot_table(path, depth_unit="m").well_depth_ft.tolist() == [
        304900 / 3048
    ]
