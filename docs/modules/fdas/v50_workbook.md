# V50 financial workbook export

`worldenergydata.fdas.reports.v50_workbook.write_v50_workbook` exports a
candidate financial summary from supplied source objects. It preserves values;
it does not calculate economics or select fiscal assumptions.

The summary uses the exact `Project_Summary` headers and order in the tracked
[lineage workbook](../bsee/analysis/production/FDAS_V30/financial_project_summary.xlsx),
followed by `After-tax NPV USD` and `NPV Reference Date`. The original `NPV USD`
column explicitly means pre-tax NPV in this interface. Each project carries
its own reference date. V30 is lineage-only.

All columns are required. Numeric values must be finite; missing results must
not be replaced by zero. A true zero is permitted. Project names must be unique.
Input columns may arrive in any order, but unknown columns are rejected so that
source mapping cannot silently discard a result. Text is stored as literal text,
including values beginning with a spreadsheet formula prefix.

```python
from worldenergydata.fdas.reports.v50_workbook import (
    V50WorkbookMetadata,
    write_v50_workbook,
)

# summary is a DataFrame mapped explicitly from the financial engine outputs.
# Both NPV columns are in USD, discounted on the same stated convention.
# Dates and provenance below are supplied from the actual run, without defaults.
metadata = V50WorkbookMetadata(
    assumption_version=assumption_version,
    git_commit=full_source_commit,
    production_cutoff=production_cutoff_date,
    wti_deck_source=deck_source_reference,
    npv_reference_convention=reference_convention,
    generated_at=generation_timestamp,  # timezone-aware datetime
)
write_v50_workbook(output_path, summary, metadata)
```

The output contains `Project_Summary` and `Metadata`. The metadata records the
assumption version, full Git object name, production cutoff date, WTI deck source,
NPV reference convention, generation timestamp, tax-basis column names and USD
units. The output file must not already exist; its parent directory must exist.
Neither the source DataFrame nor a previous output file is overwritten.

Canonical acceptance is **NOT_EVALUATED**. The assumptions decision in
[issue 899](https://github.com/vamseeachanta/worldenergydata/issues/899) and the
reference-date decision in
[issue 900](https://github.com/vamseeachanta/worldenergydata/issues/900) remain
prerequisites for the official validation workbook requested by
[issue 901](https://github.com/vamseeachanta/worldenergydata/issues/901).
A caller-supplied version or commit is provenance, not proof of approval.
This exporter cannot designate a workbook as the accepted validation target.

The official dataset run, engine-to-table mapping, monthly cashflow sheets,
committed canonical workbook and validation/comparison links remain later work.
The export tests use synthetic inputs with independent hand calculations and
compare the header schema with the committed lineage workbook; they do not
establish the V50 economic model's validity.
