"""Dimensional value assertions for synthetic rectangular parcels (#1327)."""

from decimal import Decimal

import pytest

from worldenergydata.landman.parcel import rectangular_parcel_area


def test_rectangular_parcel_area_in_declared_unit():
    """Hand calculation: 20 m * 30 m = 600 m2; 600 / 100 = 6 are.

    The rectangle is synthetic, with twenty rows of thirty unit squares.
    Source for the exact conversion 1 are = 100 m2: NIST SP 811 (2008),
    Appendix B.8, alphabetical table, 'are (a)' entry, accessed 2026-10-22.
    https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf
    Decimal equality is exact; no acceptance tolerance is introduced.
    """
    area_are = rectangular_parcel_area(
        Decimal(20), Decimal(30), square_metres_per_unit=Decimal(100)
    )
    assert area_are == Decimal(6)


def test_conversion_factor_is_required():
    """A missing unit conversion cannot be guessed from unqualified GIS data."""
    with pytest.raises(TypeError):
        rectangular_parcel_area(Decimal(20), Decimal(30))


@pytest.mark.parametrize("field", ["width_m", "length_m", "square_metres_per_unit"])
@pytest.mark.parametrize("invalid", ["0", "-1", "NaN", "Infinity", "-Infinity"])
def test_invalid_dimensions_and_conversion_are_rejected(field, invalid):
    """A nondegenerate rectangle and an area-unit factor must be finite/positive.

    Zero collapses area (or divides by zero for the factor); negative lengths
    are outside the declared geometric domain. Nonfinite values cannot describe
    a measured parcel. These are mathematical domain checks, not design limits.
    """
    values = {
        "width_m": Decimal(20),
        "length_m": Decimal(30),
        "square_metres_per_unit": Decimal(100),
    }
    values[field] = Decimal(invalid)
    with pytest.raises(ValueError, match=field):
        rectangular_parcel_area(**values)
