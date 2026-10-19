# ANP production data access assessment

The inspected sources support a **go for public bulk-file discovery** and a
**no-go for implementing a production REST client from this evidence**. ANP
publishes production CSV and ZIP links. BDEP describes technical-data access;
the re3data BDEP entry is marked offline. No documented production REST endpoint
was identified in these sources. This is a bounded finding, not proof that no
API exists anywhere. Sources were retrieved on 2026-10-19 [1–6].

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Recorded public access evidence and added file discovery to avoid assuming an API or a uniform filename pattern. |

## Access findings

| Question | Observation | Disposition |
| --- | --- | --- |
| Does BDEP document production REST access? | The ANP technical-data page describes geological and geophysical data administration, confidentiality and paid access after exclusivity. Its inspected content does not document a production REST contract [1]. | No endpoint qualified. |
| Does re3data provide that contract? | The repository entry is annotated “Offline: 2020”, describes geophysical, geological and geochemical information, and lists open, fee-restricted and embargoed access. Its navigation includes the registry's own API; that is not a BDEP production API [2]. | The registry entry does not qualify production REST access. |
| Is a production API sample query available? | No production REST endpoint or schema was identified in the inspected content [1–4]. No guessed endpoint was queried. | **NOT_EVALUATED**. A documented endpoint and response schema are required. |
| Are production files available without authentication? | Both official index pages and both selected payload GETs returned HTTP 200 [3–6]. The ZIP opened successfully and the CSV parsed successfully. | File access confirmed for the selected samples at retrieval time. |
| Can the existing filename template describe the catalog? | The well index publishes different monthly ZIP names; the national index includes grouped years, quarterly files and an exceptional annual filename [3, 4]. | Discover links; do not extrapolate filenames or periods. |

Table 1. HTTP status meanings follow RFC 9110 (2022), sections 15.3.1 and 15.5.4 [7].

## Implemented slices

- Slice 1: parse saved official index HTML into file descriptors containing URL,
  title, format and source index. Keep first occurrences in page order; resolve
  relative references and remove fragments. Ignore interactive, external,
  metadata and unrelated dataset links. Raise on an unsupported or empty index.
- Slice 2: fetch either supported index with GET and a caller-supplied timeout.
  Propagate HTTP, network and timeout failures. Report unexpected redirects.
  Discovery performs no payload download or cache write.
- Slice 3: validate discovery against independently enumerated published links
  and record sample payload evidence below. This qualifies discovery and access,
  not ingestion, unit conversion or completeness.

The implementation is
`worldenergydata.brazil_anp.production.source_discovery`. For a saved index:

```python
from worldenergydata.brazil_anp.production.source_discovery import (
    WELL_PRODUCTION_INDEX,
    parse_production_resources,
)

resources = parse_production_resources(saved_html, index_url=WELL_PRODUCTION_INDEX)
```

For a fresh index, call
`discover_production_resources(WELL_PRODUCTION_INDEX, timeout=timeout_seconds)`.
The timeout is caller policy, not a source-derived acceptance limit. Descriptors
make no inference about dates, grain, units or reuse rights. Existing
`ANPClient.download_month` behavior is unchanged.

## Sample observations

Independent enumeration of literal `href` attributes matched the discovery
results: **52 distinct ZIP URLs** in the well index [3] and **126 distinct CSV
URLs** in the national-production directory [4]. These are link counts at
retrieval time, not required future catalog sizes or tested payload counts.

The December 2023 well ZIP [5] returned `application/zip` and contained **3 CSV
members**. Their single-row headers decode with ISO-8859-1 and contain daily-rate
oil columns labelled `bbl/dia` and gas columns labelled `Mm³/dia`. This sample
differs from the existing client's synthetic multirow-header fixtures; parser
compatibility has not been qualified here.

The offshore 2026 CSV [6] returned `text/csv`, parsed with UTF-8 BOM handling and
a comma delimiter, and contained **12,000 data rows**. The `[Mês/Ano]` values
span **01/2026 through 08/2026**. Headers include oil labelled `m³` and gas
labelled `Mm³`. No rows or production measurements are redistributed.

Unit normalization, the meaning of the gas prefix, rate-to-volume conversion,
missing-value treatment, well aggregation and reconciliation with bulletin
totals are **NOT_EVALUATED**. Those checks require dataset metadata and a
separately sourced ingestion contract; discovery preserves URLs without
applying numerical factors. No engineering equations or coefficients are used.

## Retrieval evidence

All requests were anonymous, read-only GETs with a browser-compatible user
agent, made sequentially. Raw responses and request metadata are retained as
working evidence. The hashes below identify the exact response bytes examined;
only the assessment is published here. All listed responses returned HTTP 200.

| Source | Retrieved at (UTC) | SHA-256 of response bytes |
| --- | --- | --- |
| [1] BDEP context | 2026-10-19T17:26:58Z | `bb9f47934c6ccde3de3c159aed82709ab30e69c61dedbd0f824261c6a27ee898` |
| [2] re3data entry | 2026-10-19T17:26:45Z | `7911bfef8bd322f37c3cf51089dfef91e301b08615013d73dc8c8e41e354bbf5` |
| [3] Well index | 2026-10-19T17:27:08Z | `4cf254a0900c7a3939934ad34bc4eaff81dfa9780702deed4bb92adc0efff033` |
| [4] National index | 2026-10-19T17:27:19Z | `4a6631d6e6bca7523b628cc385238ff0e76fb9fbd6fa7d084d1fae5fcb37462f` |
| [5] Well ZIP | 2026-10-19T17:27:51Z | `707d49a585cc2b97c9e21c9a19292c3987ce0023ec5ee8c34744cf29953636ff` |
| [6] National CSV | 2026-10-19T17:29:20Z | `2809f2084dea5d5cbd842d9f75b8cc788b25a94653270ea4633512603dfd72aa` |
| [7] HTTP semantics | 2026-10-19T17:29:39Z | `d431760660ea44e130f6e919dab216df2d0b3a490567a98089267523368fe1e5` |

Table 2. Timestamps are request-start times; hashes cover bodies as received.

## Test basis

The discovery tests use synthetic HTML and literal URL examples from [3, 4],
including irregular ZIP names and the exceptional annual CSV name. Expected
outputs are those explicit hrefs, not URLs produced by the implementation.
Duplicate-link expectations are enumerated by hand in the test docstring.
Transport tests use a synthetic caller-selected timeout and injected failures;
the HTTP denial status is defined in [7]. No test needs network access or a
production measurement. The existing client tests are also run as regression
coverage; they do not establish compatibility with the live sample.

## Known limits and way forward

The production pages' footer states Creative Commons Attribution-NoDerivatives
3.0 Unported [3, 4]. A dataset-specific reuse licence was not qualified. Do not
treat successful access as permission to redistribute transformed datasets.
Dataset terms, onshore payload contents, catalog APIs outside the inspected
pages and production completeness remain **NOT_EVALUATED**.

Later slices should qualify units and reuse terms from dataset metadata, add
an ingestion adapter for the current national CSVs, qualify the historical ZIP
parser against actual headers, and connect validated ingestion to refresh jobs.
Reassess REST access if ANP publishes an endpoint contract. Production scheduling
and transformed-data redistribution remain outside this change.

## Sources

1. ANP, [Dados Técnicos](https://www.gov.br/anp/pt-br/assuntos/exploracao-e-producao-de-oleo-e-gas/dados-tecnicos), technical-data administration and access paragraphs; accessed 2026-10-19.
2. re3data, [Exploration and Production Data Bank](https://www.re3data.org/repository/r3d100010989), repository status, access and remarks; record editing status 2026-08-07, accessed 2026-10-19.
3. ANP, [Produção de Petróleo e Gás Natural por Poço](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/producao-de-petroleo-e-gas-natural-por-poco), archive links and licence footer; accessed 2026-10-19.
4. ANP, [Fase de Desenvolvimento e Produção](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/fase-de-desenvolvimento-e-producao), Produção Nacional links and licence footer; accessed 2026-10-19.
5. ANP, [December 2023 well-production ZIP](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/arquivos-producao-de-petroleo-e-gas-natural-por-poco/2023/producao-12.zip), archive members and headers; retrieved 2026-10-19.
6. ANP, [Offshore 2026 production CSV](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/arquivos-fase-de-desenvolvimento-e-producao/arquivos-producao-de-petroleo-e-gas-natural-nacional/pm/producao-mar-2026.csv), header, row count and period values; retrieved 2026-10-19.
7. IETF, [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html), 2022, sections 15.3.1 (200 OK) and 15.5.4 (403 Forbidden); accessed 2026-10-19.
