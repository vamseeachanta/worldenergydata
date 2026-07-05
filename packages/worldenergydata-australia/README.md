# worldenergydata-australia

Australia source package for offshore field-development screening.

The initial #721 slice is **FieldConcept / screening-only**: Australia has no
national open per-field *offshore production* database, so this member ingests
the strong AU asset — field metadata (per-field water depth, spud date) from
**DataVic Open Data** (Resources Victoria) and **NOPTA** (Commonwealth offshore
titles/wells), both **CC-BY-4.0** — and runs the field-development concept
screening (`recommend()`) on it. Production economics are explicitly deferred
(no volumes), and the chain output is labelled `production_available=False` so
the zeroed cashflow is never mistaken for a screening result.
