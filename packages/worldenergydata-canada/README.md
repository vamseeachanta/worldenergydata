# worldenergydata-canada

`canada` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.canada` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## CNSOER legacy monthly production

`worldenergydata.canada.production.cnsoer_loader` reads text extracted with
`pdftotext -layout` from the following public regulator documents:

- [SOEP Monthly Production Report (2019)](https://cdn.cnsoer.ca/sites/default/files/2025-01/soep_monthly_production_report_0.pdf):
  project total and the Thebaud, Venture, North Triumph, Alma and South Venture
  field-total tables.
- [Deep Panuke Monthly Production Report (2018)](https://cdn.cnsoer.ca/sites/default/files/2025-01/dp_monthly_production_report_0.pdf):
  project total on page 1.

The loader accepts supplied text and an explicit project identity (`Sable` or
`Deep Panuke`). It performs no download or file write. Preserve form-feed page
breaks when extracting text. Supply text from the declared project's document;
both documents use the same project-total heading, so text alone cannot prove
project identity.

```python
from worldenergydata.canada.production.cnsoer_loader import CnsoerProductionLoader

# extracted_text is caller-supplied pdftotext -layout output.
loader = CnsoerProductionLoader(raw_text=extracted_text, project="Sable")
monthly = loader.load_field_production("Thebaud")
provenance = loader.metadata()
```

The output contains `field_name`, `year`, `month`, `gas_equivalent_e3m3`,
`water_m3` and `source`. Source identity is `canada-cnsoer`. Metadata records
the extracted-text SHA-256, source URL, units and limitations. This digest
does not authenticate the original PDF. Source identity, freshness and
completeness require separate verification. Missing months remain absent;
recorded zero volumes remain zero. Duplicate months, unsupported headers or
units, invalid values and dates outside the selected report's extent raise
`CnsoerParseError`. Only the selected aggregate is read; wells and other totals
are excluded rather than added to it.

Gas equivalent remains in source units, thousands of cubic metres per month;
water remains in cubic metres per month. No equation or conversion coefficient
is applied. Gas equivalent does not establish saleable gas, calorific value or
condensate volume. This output is not yet an input to `CanadaAdapter`, which
requires canonical sales-gas and liquid volumes. Revenue evaluation remains
`NOT_EVALUATED` pending an explicit sales-volume basis, currency-consistent
prices and applicable fiscal terms. Existing FDAS gas-revenue support can be
used once those inputs are established.

[CNSOER Website Terms of Use](https://cnsoer.ca/website-terms-of-use)
(accessed 2026-10-19) restrict use to personal and non-commercial purposes and
require reproduction permission. Publication permission remains
`NOT_EVALUATED`. Keep regulator PDFs, extracted text and derived volumes out of
Git and public reports until permission is established. Tests contain only
labeled synthetic values. Automatic download, scheduling, canonical-unit
normalization and reference-chain economics remain later slices.
