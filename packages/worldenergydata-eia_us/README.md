# worldenergydata-eia_us

`eia_us` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.eia_us` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Series client cache and transport contract

`EIAApiClient.fetch_series` keeps mock and live results in separate in-memory
cache namespaces, keyed by series and query parameters. Reordering parameters
does not change a key; changing `offset`, `length`, or `use_mock` does.
`generate_cache_key(series_id, params)` selects live mode by default; code that
seeds mock entries must pass `use_mock=True`. Disabling caching bypasses both
cache reads and writes. Mock data is synthetic and ignores query filters.

The member declares Requests directly. Offline tests replace `requests.get` while
exercising the live client path, including URL construction, parameter forwarding,
timeout, request spacing, HTTP statuses, malformed payloads, and cache recovery.
Malformed JSON, missing or non-array `response.data`, and non-object records raise
`EIAApiError` before cache insertion. An explicit empty array remains cacheable.
HTTP rate-limit responses raise `EIARateLimitError`; other unsuccessful statuses
and transport failures raise `EIAApiError`.

Spacing follows the existing configurable client policy:
`interval_seconds = 3600 / rate_limit_per_hour` and
`wait_seconds = max(0, interval_seconds - elapsed_seconds)`.
The first live attempt starts immediately; subsequent attempts, including failed
ones, consume a spacing slot. Cache hits and mock fetches consume no slots.
Nonpositive configured rates disable spacing. The default is a local policy,
not a verified EIA quota. The existing request timeout is also a local policy.

Each live fetch requests **one page**, even when `response.total` indicates more
records or is absent. Callers supply `offset` and `length` for subsequent pages.
The [EIA APIv2 technical documentation](https://www.eia.gov/opendata/documentation.php)
(accessed 2026-10-21), “Length and offset”, defines offset as the number of eligible
rows skipped, length as the requested number of rows, and the JSON maximum as
5,000 rows. The client forwards these parameters; it does not enforce the
service's page maximum or automatically collect every page.

## Worked offline example

Inputs are four synthetic values, a page length of two, and offsets zero, two,
and four. The method is to request each page explicitly and concatenate its
records. By hand, the pages contain `[1, 2]`, `[3, 4]`, and `[]`; the answer is
`[1.0, 2.0, 3.0, 4.0]`. Repeating a page uses the cache. Populating mock mode
first cannot satisfy a live fetch. No credential or external request is needed.
The example uses the EIA offset/length semantics cited above, not measured data.

```python
from http import HTTPStatus
from unittest.mock import Mock, patch

from worldenergydata.eia_us.client.eia_api import EIAApiClient

series_id = "PET.MCRFPUS2.M"
pages = [
    [{"period": "2024-01", "value": "1"}, {"period": "2024-02", "value": "2"}],
    [{"period": "2024-03", "value": "3"}, {"period": "2024-04", "value": "4"}],
    [],
]
responses = [
    Mock(status_code=HTTPStatus.OK, json=Mock(return_value={"response": {"data": page}}))
    for page in pages
]
client = EIAApiClient(api_key="TEST_KEY", rate_limit_per_hour=0)
with patch("requests.get", side_effect=responses) as get:
    mock_rows = client.fetch_series(series_id, {"offset": 0, "length": 2}, use_mock=True)
    values = []
    for offset in (0, 2, 4):
        rows = client.fetch_series(series_id, {"offset": offset, "length": 2})
        values.extend(row["value"] for row in rows)
    first_page = client.fetch_series(series_id, {"offset": 0, "length": 2})
    assert first_page != mock_rows
    assert values == [1.0, 2.0, 3.0, 4.0]
    assert get.call_count == 3
print(values)
```

Expected output: `[1.0, 2.0, 3.0, 4.0]`.

## Limits and references

Transport fixtures prove client behavior without contacting EIA; they do not
qualify service availability, data accuracy, or a current service quota. The
client is intended for sequential use; shared concurrent use is not synchronized.
Credential transport, error redaction, retries, and automatic pagination remain
tracked under issue #431. Missing-data regression coverage from issue #1271 is
preserved.

- [EIA APIv2 technical documentation](https://www.eia.gov/opendata/documentation.php),
  “Parameters”, pagination, and “Understanding returned error codes”
  (accessed 2026-10-21).
- [RFC 9110 (2022), section 15](https://www.rfc-editor.org/rfc/rfc9110.html#section-15):
  HTTP success and error status semantics.
- [RFC 6585 (2012), section 4](https://www.rfc-editor.org/rfc/rfc6585.html#section-4):
  Too Many Requests.
- Existing client policy at revision `f82ff2f`, `client/eia_api.py`: configurable
  request spacing and timeout. Synthetic test expectations are derived in the
  test docstrings; they are not production observations.
