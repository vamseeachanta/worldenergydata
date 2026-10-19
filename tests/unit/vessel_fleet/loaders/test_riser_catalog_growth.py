"""Generic component vocabulary does not imply qualified equipment ratings."""

from worldenergydata.vessel_fleet.loaders.drilling_riser_loader import (
    VALID_COMPONENT_TYPES,
    DrillingRiserLoader,
)


def test_generic_rotating_control_device_has_no_invented_ratings():
    """NOV, Managed Pressure Drilling Systems, undated, retrieved 2026-10-19.

    https://www.nov.com/products/managed-pressure-drilling-systems
    The public overview establishes the component type only. It supplies no
    generic dimensions, weights or ratings; independent expected values are
    therefore unknown, not a numerical equipment example.
    """
    import pandas as pd

    loader = DrillingRiserLoader()
    record = loader.get_by_id("RCD-GENERIC")
    assert record is not None
    assert record["COMPONENT_TYPE"] == "rotating_control_device"
    assert record["COMPONENT_TYPE"] in VALID_COMPONENT_TYPES
    assert "NOT_EVALUATED" in record["NOTES"]
    assert "Managed Pressure Drilling Systems" in record["DATA_SOURCE"]
    numeric_fields = (
        "OD_IN",
        "ID_IN",
        "WALL_THICKNESS_IN",
        "LENGTH_FT",
        "WEIGHT_AIR_KIPS",
        "WEIGHT_WATER_KIPS",
        "BUOYANCY_COVERAGE_PCT",
        "BUOYANCY_OD_IN",
        "PRESSURE_RATING_PSI",
        "BORE_SIZE_IN",
        "HEIGHT_FT",
        "ANNULAR_COUNT",
        "SHEAR_RAM_COUNT",
        "PIPE_RAM_COUNT",
        "MAX_ANGLE_DEG",
        "STIFFNESS_FT_KIP_PER_DEG",
        "STROKE_FT",
        "OUTER_BARREL_LENGTH_FT",
        "INNER_BARREL_LENGTH_FT",
    )
    assert all(pd.isna(record[field]) for field in numeric_fields)
    assert pd.isna(record["MANUFACTURER"])
    assert loader.get_by_type("rotating_control_device")["COMPONENT_ID"].tolist() == [
        "RCD-GENERIC"
    ]
    assert (
        "RCD-GENERIC"
        not in loader.filter_by_pressure_rating(min_psi=0)["COMPONENT_ID"].tolist()
    )


def _write_component_ids(tmp_path, ids):
    """Synthetic identity fixtures contain no equipment ratings."""
    import pandas as pd

    rows = [
        {
            "COMPONENT_ID": component_id,
            "COMPONENT_TYPE": "rotating_control_device",
            "DATA_SOURCE": "Synthetic identity fixture",
            "NOTES": "NOT_EVALUATED",
            "OD_IN": None,
            "PRESSURE_RATING_PSI": None,
            "BORE_SIZE_IN": None,
            "BOP_TYPE": None,
            "MANUFACTURER": None,
        }
        for component_id in ids
    ]
    pd.DataFrame(rows).to_csv(tmp_path / "drilling_riser_components.csv", index=False)


def test_duplicate_ids_cannot_select_an_arbitrary_record(tmp_path):
    """Repeated literal identifiers are ambiguous, independent of equipment data."""
    import pytest

    _write_component_ids(tmp_path, ["DUPLICATE", "DUPLICATE"])
    loader = DrillingRiserLoader(tmp_path)
    with pytest.raises(ValueError, match="COMPONENT_ID.*unique"):
        loader.get_by_id("DUPLICATE")
    assert loader._df is None


def test_component_ids_are_nonempty_unpadded_strings(tmp_path):
    """Missing and padded identifiers cannot serve as stable join keys."""
    import pytest

    for invalid in (None, "", "   ", " PADDED", "PADDED "):
        _write_component_ids(tmp_path, [invalid])
        loader = DrillingRiserLoader(tmp_path)
        with pytest.raises(ValueError, match="COMPONENT_ID"):
            loader.load()
        assert loader._df is None


def test_numeric_looking_identifier_retains_leading_zeroes(tmp_path):
    """Literal '0007' remains '0007'; it is an identifier, not a count."""
    _write_component_ids(tmp_path, ["0007"])
    record = DrillingRiserLoader(tmp_path).get_by_id("0007")
    assert record is not None
    assert record["COMPONENT_ID"] == "0007"


def test_identifier_text_is_not_a_missing_value_token(tmp_path):
    """Opaque IDs preserve even strings that pandas treats as null by default."""
    ids = ["NA", "NULL", "nan"]
    _write_component_ids(tmp_path, ids)
    loader = DrillingRiserLoader(tmp_path)
    assert loader.load()["COMPONENT_ID"].tolist() == ids
