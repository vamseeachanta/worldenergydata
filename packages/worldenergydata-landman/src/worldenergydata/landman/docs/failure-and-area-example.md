# Provider failure and parcel area example

A failed transport raises an error, an error envelope leaves no cache entry,
and the synthetic rectangular parcel has an area of 6.0 are. All records and
transports below are synthetic; no live service is contacted.

## Revision history

| Revision | Date | What changed and why |
|---|---|---|
| 0 | 2026-10-22 | Added an executable failure, recovery and dimensional area example |

## Inputs, method and answer

The first transport raises a connection error. The provider must propagate
`APIError`, rather than return zero wells or `RecordNotFoundError`. The second
transport returns an error envelope, then one well feature. Validation occurs
before caching: the first call fails with zero cache entries, the second returns
one well and creates one entry, and the third returns that well without another
request. These expected counts follow the supplied response sequence by hand.
HTTP success uses the named `httpx.codes.OK` status from RFC 9110 (2022),
section 15.3.1; transport success alone does not establish a valid record list.

The parcel inputs are width 20.0 m and length 30.0 m, with output in are.
Rectangle area is width × length (OpenStax, *Prealgebra 2e*, 2020, section 9.4).
NIST SP 811 (2008), Appendix B.8, the `are (a)` entry, defines exactly
100 square metres per are. The factor is a required input, not inferred from
remote GIS fields. Hand calculation: 20.0 × 30.0 = 600.0 m²;
600.0 / 100.0 = **6.0 are**. Decimal equality needs no acceptance tolerance.

```python
from decimal import Decimal

import httpx

from worldenergydata.landman.exceptions import APIError, ParsingError
from worldenergydata.landman.parcel import rectangular_parcel_area
from worldenergydata.landman.providers.state_gis import StateGISProvider

# Zero retries and zero delay exercise terminal offline failures immediately.
def unavailable(request):
    raise httpx.ConnectError("Synthetic unavailable service", request=request)

with StateGISProvider(max_retries=0, rate_limit_delay=0) as provider:
    provider._client = httpx.Client(transport=httpx.MockTransport(unavailable))
    try:
        provider.search_wells_by_location("TX", "Synthetic")
    except APIError:
        assert provider.cache_stats()["entries"] == 0
    else:
        raise AssertionError("Transport failure became an empty success")

requests = []

def recover(request):
    requests.append(request)
    if len(requests) == 1:
        return httpx.Response(httpx.codes.OK, json={"error": {}})
    return httpx.Response(httpx.codes.OK, json={
        "features": [{"attributes": {"API_NUMBER": "WELL-A"}}]
    })

with StateGISProvider(max_retries=0, rate_limit_delay=0) as provider:
    provider._client = httpx.Client(transport=httpx.MockTransport(recover))
    try:
        provider.search_wells_by_location("TX", "Synthetic")
    except ParsingError:
        assert provider.cache_stats()["entries"] == 0
    else:
        raise AssertionError("Error envelope became an empty success")
    # Hand trace: error, recovery, cached recovery -> two requests, one entry.
    for _ in range(2):
        result = provider.search_wells_by_location("TX", "Synthetic")
        assert result.total_count == result.returned_count == 1
        assert [well.api_number for well in result.wells] == ["WELL-A"]
    assert len(requests) == 2
    assert provider.cache_stats()["entries"] == 1

# NIST SP 811 (2008), Appendix B.8, are: exactly 100 square metres per are.
area_are = rectangular_parcel_area(
    Decimal("20"), Decimal("30"), square_metres_per_unit=Decimal("100")
)
assert area_are == Decimal("6")
```

## Sources and limits

- [OpenStax, Prealgebra 2e (2020), section 9.4, rectangles](https://openstax.org/books/prealgebra-2e/pages/9-4-use-properties-of-rectangles-triangles-and-trapezoids), accessed 2026-10-22.
- [NIST SP 811 (2008), Appendix B.8](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf), accessed 2026-10-22.
- [RFC 9110 (2022), section 15.3.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.1).
- #1256 and #1260 define failure visibility and cache behavior.

Executable check: `tests/unit/landman/test_failure_area_example.py::test_failure_and_area_worked_example`.
The parcel helper checks a planar rectangle only. It does not convert GIS
coordinates, establish a CRS, reconcile acreage from records, or qualify title
or live-service completeness. Decimal arithmetic uses the caller's context.
