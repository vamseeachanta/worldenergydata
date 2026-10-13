# Annual-statement source registry

The registry supports disclosure discovery for
[issue 343](https://github.com/vamseeachanta/worldenergydata/issues/343).
It contains exactly BP, Chevron, Shell, Equinor, Aker BP, TotalEnergies,
ExxonMobil, Murphy Oil and Hess, with fiscal years 2020–2024.

## Evidence and current coverage

`data/operator_statements/observations.json` is the edited input retaining curated
response metadata from the bounded public-source run. `registry.json` is generated
by the emitter and carries the same content in sorted form with validated defaults;
it is never edited by hand. The command in "Loading and regenerating"
regenerates it. No report, filing, webpage body
or engineering cost value is redistributed. SHA-256 and byte counts refer to
the response bytes, not to these JSON files. Retrieval timestamps are UTC.

At the time of retrieval on 2026-10-11, two operator-years were verified:
Aker BP 2023 and 2024. The operator-owned reports-and-presentations listing
supplied both URLs. The PDFs returned HTTP 200, their PDF signatures were
checked, and page 2 running headers established the operator and fiscal year.
The source listing states no licence; this absence grants no redistribution
right. Documents remain outside Git. Remaining years were not inferred from
links, upload-directory years, search results or URL templates.

BP and Chevron returned HTTP 403 at their robots endpoints. Ten year rows
record `access_refused` for **operator-site access in this run**. The source
refused this client's request for the stated scope; this says nothing about
whether the document exists, and the operator-year remains to be obtained
through another channel. Other filing channels were not assessed. The seed has
2 `verified`, 10 `access_refused`, 33 `missing` and 0 `known_unavailable`
operator-years, totalling 45; no seed entry holds evidence of document absence.

Equinor and TotalEnergies landing pages were fetched; documents were not.
ExxonMobil and Murphy Oil investor links were observed on their corporate
homepages; the separate investor sites were not fetched or authorized by the
corporate site's robots policy. Hess's attempted investor and terms locations
returned redirects, which were not followed. Shell's bounded static homepage
review did not establish an annual-report discovery URL. BP, Chevron and Shell
therefore have null discovery locations; notes identify the missing evidence.
These are coverage gaps, not substituted or guessed URLs.

Terms excerpts are reproduced exactly in metadata, alongside their page URL
and retrieval time. `not stated by the source` means no licence wording was
obtained at the recorded location; it never denotes public-domain status.
For redirect/refusal observations, the available robots/refusal location is
recorded, and the undiscovered legal terms remain a gap. Source terms shall be
reviewed again before any later collection or reuse.

## Contract

`operator_statement_registry.py` defines strict Pydantic models with unknown
fields rejected. Each operator stores its name, source domains, reporting-market
context, discovery location, declared document channels, discovery notes,
response observations and the exact five-year map. Market descriptions are
curation context, not extracted engineering facts.

The document-channel vocabulary is `annual_report`, `sec_10k`, `sec_20f` and
`sustainability_report`. The plan's `investor_relations` entry is represented
by `discovery_url`, not treated as a document type; this resolves the open
review finding. The initial rows declare only `annual_report`; additional
channels require source review and do not imply year coverage.

Each operator-year stores one of:

- `verified`: at least one qualifying primary PDF was retrieved and its identity
  checked. Each evidence entry records its actual URL, listing URL, operator,
  fiscal year, document channel, identity quotation/locator, HTTP 200, PDF content
  type, positive byte count, SHA-256, retrieval timestamp and terms provenance.
- `missing`: no qualifying document was fetched; a note explains the gap.
- `access_refused`: source access was refused for the recorded scope; the year
  requires a refusal URL, scope, note and matching retained HTTP 403/429 response
  observation with its address and UTC retrieval time. Document existence is
  unknown and another channel remains necessary.
- `known_unavailable`: evidence states that the document does not exist or was
  not published for that year. It requires a source URL, scope, note, matching
  retained HTTP 200 response observation and `finding_quote` containing the
  explicit absence or nonpublication finding. A refusal cannot justify this
  status; an ordinary HTTP 200 without a finding proves neither status.

Current document validation admits PDF annual statements only. HTML-native SEC
filings need a later contract extension and explicit content/identity checks;
this seed does not claim SEC coverage. Validation checks metadata consistency,
not the truth of a curator's identity quotation or ownership declaration.

`derive_coverage(row)` computes `earliest_covered_year`,
`latest_verified_year`, year statuses and verified years per declared channel.
Both bounds are null when no year is verified. No bound is stored, so missing
or refused years cannot inflate coverage. Multiple documents for one year
still count as one covered operator-year. Channel lists represent evidence
present, not proof of complete channel inventories.

## Loading and regenerating

From the repository root, with the cost package installed in the environment:

The following command regenerates the manifest:

```bash
python - <<'PY'
from pathlib import Path
from worldenergydata.cost.data_collection import (
    derive_coverage, emit_registry, load_registry,
)

inputs = Path("data/operator_statements/observations.json")
manifest = Path("data/operator_statements/registry.json")
manifest.write_bytes(emit_registry(inputs))
registry = load_registry(manifest)
coverage = {row.name: derive_coverage(row) for row in registry.operators}
PY
```

The offline tests reproduce the committed manifest byte for byte, reproduce a
separate explicitly synthetic fixture manifest, reject incomplete evidence,
and show that changed curation inputs change the output. They block the network.
No input or output cache has a machine-specific default.

## Updating and consuming disclosures

A later backfill issue will select missing operator-years and use the discovery
notes and listing location. Before requesting a document, it will read the
source's current robots and terms statements, including those of a different
subdomain or document origin. It will record any refusal and stop that site;
no alternate route will be used to circumvent it. For operators listed on a
regulated exchange, the regulator filing channel is the first backfill step
for operator-years recorded as access refused, subject to that channel's own
source-policy checks.

`statement_source_fetch.fetch_source` performs one request after a two-second
pause, with a descriptive repository-contact User-Agent, a 30-second socket
timeout and a caller-selected byte limit (default 2 MB, maximum 30 MB).
A ceiling above 2 MB requires `document_mode=True`; otherwise validation rejects
it before a request or pause. After the applicable source-policy checks, a
caller can explicitly request document mode:

```python
from worldenergydata.cost.data_collection.statement_source_fetch import fetch_source

metadata, body = fetch_source(document_url, max_bytes=30_000_000, document_mode=True)
```

It returns HTTP errors once, follows no redirects and performs no retries or
server-requested waits. Callers own policy authorization, challenge detection,
PDF signature/identity checks and sequential orchestration. It is a low-level
transport helper, not a crawler or an automatic discovery pipeline.

A verified update will retain immutable response metadata, read back the saved
bytes and verify their digest, establish operator/year identity from the actual
listing or document, and regenerate the manifest through the emitter. A link
alone will leave the year missing. Raw reports will remain outside Git.

Downstream ingestion will reference `DocumentEvidence.url` and its channel to
populate `DisclosureCitation.source_url` and source priority in
`disclosure_ingest_contract.py`. Page references, exact metric quotations,
confidence, reporting scope, units and values still require document analysis;
registry verification does not supply them. Verified-document listing URLs
and dated terms references must match retained successful response observations. Accepted disclosure rows can then
feed `disclosure_analytics.py` for year-over-year views.

Full report backfill, document parsing, currency normalization, restatement
lineage and dashboards remain outside this registry's scope.
