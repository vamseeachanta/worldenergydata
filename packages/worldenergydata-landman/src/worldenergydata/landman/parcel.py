"""Planar rectangular parcel areas with an explicit, caller-sourced area unit."""

from decimal import Decimal


def rectangular_parcel_area(
    width_m: Decimal,
    length_m: Decimal,
    *,
    square_metres_per_unit: Decimal,
) -> Decimal:
    """Return width * length / square_metres_per_unit in the declared area unit.

    Dimensions are finite positive lengths in metres. The conversion factor is
    required: remote GIS acreage and coordinate units are not qualified here.
    For example, NIST SP 811 (2008), Appendix B.8, 'are (a)' entry defines
    100 square metres per are. The caller supplies that factor explicitly.
    Rectangle area: OpenStax, Prealgebra 2e (2020), section 9.4,
    https://openstax.org/books/prealgebra-2e/pages/9-4-use-properties-of-rectangles-triangles-and-trapezoids
    This is a planar rectangle calculation, not a cadastral/geodesic survey.
    Decimal arithmetic follows the caller's active precision context.
    """
    for name, value in (
        ("width_m", width_m),
        ("length_m", length_m),
        ("square_metres_per_unit", square_metres_per_unit),
    ):
        # Mathematical domain: a nondegenerate rectangle has positive finite
        # lengths; a conversion factor must also be nonzero and positive.
        if not value.is_finite() or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    return width_m * length_m / square_metres_per_unit
