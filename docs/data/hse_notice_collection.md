# HSE public notice collection

## Summary

Offline adapters turn reviewed OPRED PON1 pages and manually obtained HSE notice
spreadsheets into the existing source-neutral offshore collection. The executable
worked example produces one synthetic event with three source rows, citations, a
deduplication log and a digest manifest. Public OPRED layouts were checked; live
HSE spreadsheet validation and the third real seed source are **BLOCKED-NETWORK**.
No raw downloads or actual installation identities are added to Git.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-22 | Added offline notice adapters, intake instructions and a synthetic worked example to extend public offshore evidence coverage. |

## Scope and existing contracts

This implements the file-adapter scope of #1685 under the fields, deduplication,
citation and privacy requirements of #1325 (2026). It reuses `Event`,
`SourceDocument`, `check_privacy` and `OffshoreImporter`; `HSEIncident` is unchanged.
The source registry required by #1684 is already present at
`data/modules/hse/offshore/source_registry.json`, and the source-label corrections
are covered by the existing offshore tests. No replacement registry is created.

Event identity includes the published date, country, area, block and installation.
Operation and failure mode use the existing controlled terms; the original
paraphrase is limited to 50 words (#1325, Fields). Injury and fatality counts stay
unknown when the input does not publish counts. A notice's issue and compliance
dates belong to its source row, never to the incident date. Leads remain outside
admitted evidence until verified at a permitted official source.

## Inputs and method

`worldenergydata.hse.importers.notice_loaders.parse_pon1` takes an HTML string,
official record URL, actual access date, curated context and a reviewed-text
inventory. The context supplies `event_id`, country, area, operation, equipment,
controlled failure mode, paraphrase and optional installation aliases. These are
reviewed inputs, not inferred facts. Published release values cannot be overridden.

The parser reads the notification reference and header/value rows in `main`, checks
the OGL footer, and preserves the single published quantity and unit. Oil and
chemical layouts are supported. Repeated substance fields and mixed releases are
refused because the event schema holds one release tuple. No density, conversion
factor, geographic coordinate conversion, injury count or timezone is assumed.
The observed time is retained in a provenance note; the event remains date-only.
The original source cause is separate from the curated mechanical failure term.
Publication date remains unknown when the page supplies no issue date.

`load_hse_notices` takes a local public `.xlsx`, an explicit worksheet and header
row, a canonical-to-published column mapping, date format, actual access date,
reviewed-text inventory and `source_ref -> event_id` associations. Header rows use
one-based indexing as documented by openpyxl's `Worksheet.iter_rows` API. Required
mapped fields are `source_ref`, `title`, `doc_type`, `issue_date` and `status`;
optional fields are `compliance_date`, `legal_provision`, `url` and `summary`.
The only admitted notice types are improvement and prohibition notices.

A mapping must be inspected against the actual public workbook; the synthetic
headers are not asserted to be the live layout. Association is manual because
service dates do not identify an incident. Only explicitly selected references
are processed. Missing references, duplicate headers/references, populated
personal columns and formulas refuse intake. Missing or unreadable workbooks
return `manual_required` and official URLs. The command does not retry a blocked
source, submit forms, log in or download anything.

All selected free text, including unused columns, must appear in an independently
curated privacy inventory. A new name in a free-text cell fails before persistence;
contact patterns are rejected even if approved. Populated personal columns are
refused even if their strings appear in the inventory. Diagnostics do not echo
suspect values. This is a fail-closed admission policy, not universal name
recognition: a falsely approved inventory can admit a name in an ordinary text
field. Independent review of that inventory remains necessary. Never generate it
by copying incoming strings automatically.

## Running the offline intake

Use a Python environment with the repository dependencies and `openpyxl` available.
Set `WED_DATA_ROOT` to a configured directory outside the checkout. The command
refuses a root inside the repository and restricts export names to one component.

```bash
python scripts/import_hse_notices.py --manual-hse
python scripts/import_hse_notices.py --pon1 "$PON1_HTML" \
  --config "$NOTICE_CONFIG" --export reviewed-notices
python scripts/import_hse_notices.py --pon1 "$PON1_HTML" \
  --hse-xlsx "$HSE_XLSX" --config "$NOTICE_CONFIG" --export reviewed-notices
```

The config contains `context`, `pon1_url`, ISO `access_date` and `reviewed_text`.
For HSE also supply `columns`, `sheet`, `header_row`, `date_format` and
`associations`. An HSE-only run needs complete reviewed `events` in the config;
it must not substitute notice dates for event dates. Optional `sources` attaches
additional reviewed metadata, with the same privacy and official-URL checks.
The executable test example constructs a complete config from synthetic literals.

Exit codes are 0 for successful intake or an explicitly requested manual URL
list, 1 for refused input, and 2 for a file that needs a manual step or invalid
command arguments. A missing HSE file creates no database. Successful intake
writes `modules/hse/offshore/offshore.sqlite` beneath the external root and exports
`events.json`, `sources.json` with citations, `external_links.json`,
`dedup_log.json`, `gates.json` and `manifest.json` beneath the chosen export name.
The manifest records counts and SHA-256 digests of those outputs. Existing exports
are not overwritten with differing content. Provenance notes returned by the
parser should be retained with the manually reviewed input packet; the existing
SQLite schema persists event/source rows, not arbitrary packet annotations.

Reruns are unique on `(source, source_ref)`. Event matching requires normalized
installation names or reviewed aliases, country and a date difference of at most
two days (#1325, Deduplication). No approximate spelling match is accepted.
Every match records its pair, rule, score and disposition. Existing BSEE and
marine-safety identities must be reconciled using the existing importer before
bulk acceptance; they are linked rather than copied. Pilot and bulk review gates
are never approved by this command. See the
[offshore intake contract](../../data/modules/hse/offshore/README.md).

## Worked example: inputs, method and answer

This uses the seed date, 93.87 kg and stated cause from #1325 with synthetic
installation, company and substance identifiers. It is **not** a verified
three-source reconstruction of the actual event.

| Input | Published layout or synthetic basis | Use |
| --- | --- | --- |
| `tests/unit/hse/fixtures/notices/pon1_synthetic.html` | OPRED notification 4966 layout, with seed date/quantity/cause and synthetic identity | Release facts and date-only event |
| Workbook generated in `test_cli_three_source_example_and_rerun` | Explicit synthetic headers and dates | HSE source row with manual event association |
| Alert metadata generated in that test's config | Synthetic metadata on the official agency domain | Third source row; no copied alert prose |
| `tests/unit/hse/fixtures/notices/reviewed_text.json` | Hand-curated synthetic inventory | Privacy admission for raw and normalized strings |

Run the example with a temporary directory outside the checkout:

```bash
python -m pytest --noconftest -o addopts='' -p no:cacheprovider \
  tests/unit/hse/test_notice_loaders.py::test_cli_three_source_example_and_rerun \
  --basetemp="$TMPDIR/hse-notice-example" -q
```

Method: parse the PON1 fields, map the HSE row, attach the synthetic alert, then
call the transactional importer and export. The expected answer, counted from
those inputs, is one event and three source rows. The event date is 2024-02-01;
the release is 93.87 kg and the stated cause is `Riser - Total Rupture`. The HSE
notice's synthetic issue date, 2024-03-21, remains a source date. Injury and
fatality counts remain null. Repeating the command adds no evidence rows.
A separate planted alias case uses 2024-02-03: subtracting February 1 gives two
days, so the stated matching rule yields one event and two source references.
The exported log contains both the event-match rule and the unique-key skip.

## Verification

The loader and command tests passed 44 synthetic cases. The existing offshore
collection regression suite passed 126 cases, for 170 passing cases together.
Ruff, Black, isort, Bandit at the repository severity/confidence threshold, the
repository structure guard and file hygiene checks passed. These checks exercise
offline inputs; they do not establish live HSE access or independent source review.

## Sources and access findings

All current checks below were made on 2026-10-22. Used responses, effective URL,
UTC retrieval time and HTTP status are retained with external working evidence;
raw downloads are excluded from Git.

| Source | Result and rule supported |
| --- | --- |
| [OPRED notification 4966 (2024)](https://itportal.energysecurity.gov.uk/irs/publications/pon1/2024/notification/4966) | HTTP 200; header/value layout, 93.87 kg, stated cause, date-only precision and OGL footer |
| [OPRED notification 6788 (2024)](https://itportal.energysecurity.gov.uk/irs/publications/pon1/2024/notification/6788) | HTTP 200; oil product/quantity labels and published tonnes unit; no conversion inferred |
| [OPRED robots rules](https://itportal.energysecurity.gov.uk/robots.txt) | HTTP 200; public notification paths are permitted |
| [HSE temporary-register page](https://www.hse.gov.uk/enforce/temporary-register-notices.htm) | HTTP 200; official spreadsheet link, improvement/prohibition scope and OGL footer |
| [HSE robots rules](https://www.hse.gov.uk/robots.txt) | HTTP 200; `/*.xls` disallows the linked `.xlsx` path too; spreadsheet not requested |
| [SEC robots rules](https://www.sec.gov/robots.txt) | HTTP 403; stopped without requesting the seed filing |
| [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | HTTP 200; attribution requirement and personal-data exemption |
| [openpyxl worksheet API (3.1, accessed 2026)](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.worksheet.worksheet.html) | HTTP 200; one-based header-row input to `iter_rows` |

Each source row uses the existing citation format: agency, document type,
reference, title, issue date or explicit unknown, URL, access date and licence.
OGL rows append: Contains public sector information licensed under the Open
Government Licence v3.0.

## Later slices and review limits

The real seed remains short of three verified sources. Its HSE notice cannot be
confirmed from the blocked spreadsheet; SEC also denied access. Existing IADC
metadata in the committed pilot packet was not re-fetched by this change.
The synthetic example does not promote either unavailable source or approve the
pilot. Manual permitted acquisition, column/terms review and source verification
are required before adding actual HSE facts. Multi-substance releases and input
coordinates need a separate representation or explicit reviewed conversion.
No claim is made that the complete HSE register, existing identity indexes or
bulk acceptance have been checked.
