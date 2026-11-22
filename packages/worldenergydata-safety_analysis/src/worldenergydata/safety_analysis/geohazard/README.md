# USGS earthquake observations

`worldenergydata.safety_analysis.geohazard.usgs` supplies a read-only event
client in the existing safety-analysis workspace package. It returns a typed
table as a tuple of `EarthquakeEvent` rows, plus exact response bytes and retrieval
metadata in `QueryResult`. It does not establish whether a point is offshore or
calculate hazard, exposure, or risk.

Both `query_box` and `query_radius` require timezone-aware `start` and `end`
datetimes, a finite `min_magnitude`, and an integer `limit` from 1 through 20,000.
Box bounds are latitude then longitude minima/maxima; date-line rectangles may
use longitude bounds outside ±180, within the documented ±360 range. Radius is
in kilometres and is applied by the service's `maxradiuskm` filter, without a
local geospatial approximation. Date-line response longitudes are retained as
returned within ±360; this behavior has not been exercised live.

The table contains event ID, UTC time, latitude/longitude in degrees, depth in
kilometres, magnitude, magnitude type, place, event URL, query URL, and credit.
Unknown depth and magnitude remain `None`. Magnitude scales are retained as
reported; magnitudes on different scales are not converted.

A count request without a result limit precedes the GeoJSON request. Counts
above the caller's limit are refused with `TooManyEvents`. Catalogue changes
between requests can change results: the second request retains the limit and
its returned row count is checked. `matched_count` is the earlier count, not a
completeness certificate. A zero count skips the download; `raw=None` represents
no downloaded payload. An HTTP 204 response also has `raw=None`.

`QueryResult.requested_limit` retains the caller's cap. `count_mismatch` is
`len(events) != matched_count`; it exposes a difference between the earlier
count and the returned rows, including a no-content response after a positive
count. `limit_reached` is `len(events) >= requested_limit` and flags possible
truncation. When a result is constructed without a requested limit, this property
is `None`. Neither property establishes catalogue completeness: equal counts
can conceal changed event identities, and a reached cap can be an exact match.
No additional requests are made to evaluate these properties.

The parser refuses duplicate JSON members, non-finite numbers (including float
overflow), blank event IDs, repeated event IDs, and non-integer event times.
Optional `metadata.count`, when present, must be an integer equal to the number
of returned features. This count belongs to the downloaded collection; it is
not compared with the earlier count request during parsing. Omitted metadata
or count remains supported for existing recorded responses. A malformed row
or contradictory count raises `ServiceError` for the whole response; partial
rows are not returned. Unknown magnitude and depth remain `None`.

The synchronous client uses GET, an explicit timeout (default 30 seconds, maximum
60), a response cap (default and maximum 5,000,000 bytes), and a pause of at least
two seconds after each attempt. Calls must be sequential. There are no retries,
redirects, credentials, disk caches, or scheduled requests. HTTP 403/429 and HTML
challenge responses raise `AccessRefused`; the caller must stop that source.
`Retry-After` is not followed because retries are disabled. Oversized-query HTTP
400 responses raise `TooManyEvents`; other failures raise `ServiceError`.

## Sources and fixture rights

Protocol parameters, formats, and the 20,000-event limit were inspected in the
[USGS event-service documentation](https://earthquake.usgs.gov/fdsnws/event/1/)
on 2026-10-11 UTC. Field order and GeoJSON structure were inspected in the
[USGS summary specification](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php).
These are the source of URL patterns; no filename listing is used by this API.

Both documentation pages were read again on 2026-10-19 UTC for the integrity
checks and result diagnostics. The GeoJSON Summary v1.0 Output declares string
IDs, integer event times, coordinate order and integer collection counts. The
event-service `limit` parameter caps returned events. Duplicate JSON member
rejection is a client integrity policy informed by
[RFC 8259 (2017), section 4](https://www.rfc-editor.org/rfc/rfc8259#section-4),
which describes ambiguity when names repeat; it is not an RFC requirement to
reject them. Non-finite number rejection follows
[section 6](https://www.rfc-editor.org/rfc/rfc8259#section-6), with float overflow
also refused. Duplicate event rejection and collection-count agreement are
client integrity policies. Focused offline tests use synthetic inputs and
independent row counts and Boolean truth tables rather than hazard thresholds.

The [USGS copyright policy](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)
states: “USGS-authored or produced data and information are considered to be in
the U.S. Public Domain.” The policy also requests proper credit and identifies
exceptions for copyrighted third-party material. The recorded fixture contains
USGS-network event summaries, without third-party imagery or attachments.
Redistribution relies on the quoted public-domain statement, not a blanket
assumption about all content hosted by USGS.

The [USGS robots statement](https://www.usgs.gov/robots.txt) was read on
2026-10-11 UTC. The earthquake service's `/robots.txt` returned HTTP 404, rather
than an access refusal. Service documentation recommends real-time feeds for
applications displaying current events where possible. This client performs
bounded historical queries, rather than polling or crawling.

`tests/fixtures/geohazard/usgs_recorded.geojson` retains the exact small response
from a historical 20-minute, magnitude-6 box query. Its manifest records source,
UTC retrieval, rights wording and URL, SHA-256, byte count, units, and intended
use. It is a parser fixture, not a current engineering assessment. Inline test
payloads are labelled synthetic and do not represent measured observations.

`emit_manifest(payloads, inputs)` computes hashes and sizes from saved bytes.
The committed `manifest.json` is generated with that function from
`provenance_inputs.json`; the offline reproduction test compares exact bytes.
Digest and byte size are computed without hand edits; event count and retrieval
time are declared inputs.
