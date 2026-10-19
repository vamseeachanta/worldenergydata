# worldenergydata-baker_hughes

`baker_hughes` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 5 final tail, #529).

Importable transparently as `worldenergydata.baker_hughes` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Workbook evidence

`worldenergydata.baker_hughes.report.generate_workbook_evidence(path)` returns a
JSON/YAML-serializable dictionary containing the supplied file's SHA-256 digest
and explicit `NOT_EVALUATED` checks for source revision, depth units, independent
expected counts, and signed QA evidence. Each check includes the missing evidence
as its reason. Local filenames and paths are omitted from the dictionary.

The digest follows [FIPS 180-4 (2015), section 6.2, SHA-256 Hash
Computation](https://csrc.nist.gov/pubs/fips/180-4/upd1/final). It identifies bytes
only: the function does not parse Excel, authenticate the source, establish a
permitted revision, verify a signature, or bind the file to a loaded DataFrame.
Empty files and invalid workbooks therefore remain `NOT_EVALUATED`; file access
errors propagate. The current implementation reads the complete file into memory.

The existing `generate_report(df, source)` remains a descriptive ingestion report.
Neither report establishes independent source accuracy. Workbook qualification,
source-unit evidence and signed QA acceptance remain open under
[the independent-evidence issue](https://github.com/vamseeachanta/worldenergydata/issues/1336).
