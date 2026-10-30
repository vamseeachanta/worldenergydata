# Offshore reference data availability

The historical offshore asset data set is held privately pending
redistribution-terms review. Field, facility, host, rig, jackup, centroid,
coverage and crosswalk payloads are withheld from this public tree. Notices
beside the former CSV locations identify the unavailable inputs.

The later contractor jackup replacement is also withheld: retained input bytes,
field-level extraction records and redistribution clearance are not established.
Publicly accessible pages alone do not establish redistribution permission.

`worldenergydata.field_development.data_availability.load_withheld_dataset(name)`
raises `DatasetUnavailableError` for each withheld dataset. Existing field,
facility, host and crosswalk readers reject the bundled paths, including stale
copies restored at those paths. Explicit independent inputs retain parser
support; supplying a path does not establish source rights.

## Independent regulator datasets

`curated/lt_reserves_discovery.csv`, `curated/lt_reserves_discrepancies.csv` and
`curated/LT_RESERVES_DISCOVERY.md` remain unchanged. Their basis is the
[BOEM Reserves Inventory Program](https://www.data.boem.gov/Main/HtmlPage.aspx?page=FieldReserves)
and [BSEE qualified fields](https://www.data.bsee.gov/Well/Qualified/Default.aspx).
Their companion source note records units, source versions and limitations.
No historical-scrape value is relabelled as a regulator observation.

## Catalog integration interface

`catalog_integration_schema.json` and the integration schemas in `schema.yaml`
define software interfaces; they contain no retained historical asset rows.
Explicit independent inputs remain supported by the integration API. The
bundled historical catalog is unavailable to the default command-line reader.

Removing current payloads does not remove earlier Git objects or previously
published external copies. History and external-publication disposition remain
maintainer decisions.
