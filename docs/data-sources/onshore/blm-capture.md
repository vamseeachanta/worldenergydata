# BLM public lease raw capture

The capture contract preserves one bounded oil-and-gas lease response and its
provenance. Offline fixtures establish byte retention and failure behavior; live
payload retention rights are not established. Federal administrative records do
not establish county title chains or current mineral ownership.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-11-23 | Define bounded capture and record current publisher metadata before payload acquisition. |

## Publisher evidence

Read-only metadata requests returned HTTP 200 on 2026-11-23 UTC:

- [Current service directory](https://nlsdbpubgis.blm.gov/arcgis/rest/?f=pjson).
  The historical `gis.blm.gov` national MLRS feature-service address redirects
  here; it no longer identifies the former feature service.
- [Fluid minerals directory](https://nlsdbpubgis.blm.gov/arcgis/rest/services/Fluid_Minerals?f=pjson).
- [Oil-and-gas lease disposition service](https://nlsdbpubgis.blm.gov/arcgis/rest/services/Fluid_Minerals/Oil_Gas_Leases_Case_Disp/MapServer?f=pjson).
- [Authorized layer 0](https://nlsdbpubgis.blm.gov/arcgis/rest/services/Fluid_Minerals/Oil_Gas_Leases_Case_Disp/MapServer/0?f=pjson).

The publisher identifies the source as BLM MLRS legal land descriptions geocoded
against PLSS. Some cases cannot be geocoded; geometry quality varies. Layer 0
advertises Query capability, pagination and a 2,000-record maximum. Pending,
Interim and Closed layers are listed but are outside this capture contract.
No request rate, freshness guarantee or affirmative payload redistribution
license was observed in these metadata responses. Copyright attribution alone
is not retention permission. No payload query was executed.

Only metadata access is established. Before a live request, the caller must
review applicable publisher terms and supply an `Evidence` declaration with a
credential-free BLM HTTPS terms reference, substantive terms and publisher-access
notes, aware check time and `retention="permitted"`. A declaration records the caller's review;
the module cannot authenticate permission or determine its expiry. Synthetic
evidence is labelled and cannot enable `fetch_capture`.

## Request and storage contract

`worldenergydata.landman.blm_capture.fetch_capture(root, capture_id,
evidence=reviewed_evidence)` explicitly opts into one GET to layer 0 `/query`.
Parameters are fixed: `f=json`, `where=1=1`, `outFields=*`,
`returnGeometry=false`, `orderByFields=OBJECTID`, `resultRecordCount=10`.
No arbitrary endpoint, credentials, redirects, retries, paging, portal forms or
account access is supported. Each network operation has a 15-second timeout;
this is not a total wall-clock deadline. Decoded response bytes are capped at
1,000,000 bytes, with reads in 65,536-byte chunks. Raw means the decoded HTTP
entity bytes exposed by the client, before JSON parsing or reserialization.

The caller supplies the canonical storage root corresponding to logical
`landman/blm/raw`. Each portable `capture_id` creates a new directory containing:

- `response.json`: exact response bytes, including whitespace.
- `manifest.json`: schema version, UTC capture/check timestamps, publisher,
  fixed query URL, metadata URL, terms evidence and retention declaration;
  relative raw member name, SHA-256, byte length, record cap/count and source
  transfer-limit flag.

Both files are read back. The completion manifest follows raw-byte readback.
`status="captured"` establishes byte capture, not readiness for underwriting.
Every bundle has `coverage="partial"`, including successful empty responses.
An absent transfer-limit flag is `null`, distinct from an explicit `false`.
Malformed/error JSON, duplicate members, non-finite JSON constants, excess bytes
or records and invalid attributes fail before output creation. Existing captures
are never overwritten. Traversal and existing symlink roots are rejected.
Disk failures may leave an incomplete directory; preserve it for diagnosis and
use a new capture identifier. Concurrent hostile filesystem mutation is outside
this writer's trust boundary; use a caller-controlled storage directory.

## Observed field map

| Underwriting concept | Layer 0 field or disposition |
| --- | --- |
| Lease/case identifier | `CSE_NR`, `LEG_CSE_NR`; administrative identifiers, not a title opinion. |
| Effective/expiration date | `EFF_DT`, `EXP_DT` have date types; conversion and missing-date handling are deferred. |
| Public lessee/operator | No dedicated field observed; unavailable in this slice. |
| Acreage | `RCRD_ACRS`, alias Case Acres; retained without arithmetic or independent area qualification. |
| Rental/royalty terms | No dedicated fields observed; unavailable in this slice. |
| Legal/spatial keys | `ADMIN_STATE`, `GEO_STATE`, `SF_ID`, `OBJECTID`; legal-description parsing and geometry acquisition are deferred. |
| Status and quality | `CSE_DISP`, `PRDCNG`, `QLTY`, `CSE_META`; no interpretation is performed. |

Missing fields and nulls remain as received. No date, unit, ownership, acreage
or financial default is substituted. Normalization, nationwide completeness,
current lease qualification, provider integration, county records and storage
deployment remain subsequent work under issue #913.
