# Keathley Canyon completion inputs

The completion report can read the retained KC candidate used by the opt-in
Lower Tertiary financial reproducer. Buckskin is included in that candidate.
The frozen V30 workbook remains the default until the validation requirement in
[issue 842](https://github.com/vamseeachanta/worldenergydata/issues/842) is resolved.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-19 | Added explicit KC report input selection and integrity checks so retained KC records can be inspected without replacing V30. |

## Inputs and provenance

The dataset owner is this repository. The upstream source is BSEE eWell Well
Activity Reports (`bsee-ewell-war`), available from the
[BSEE Data Center](https://www.data.bsee.gov/Main/RawData.aspx).
This workflow reads retained derivatives; it does not fetch or qualify new raw
WAR, borehole, completion or production records.

Both inputs are committed under `FDAS_V30/` beside this guide:

| Input | Purpose | SHA-256 |
| --- | --- | --- |
| `leases_v21_kc.csv` | Lease-to-field and development mapping | `d910033b7d32232dc3ea4fc79c145234c92f577876d3d36d17211e2b54c407d9` |
| `drilling_and_completion_days_v21_kc.csv` | API wellbore identities and stored drilling/completion days | `a6fdd82382ef6c564c0fa0576625630f0f49a969390cdadfb66c02bb5a3bfd64` |

The candidate is historical. Its source vintage and acceptance against the current
WAR activity-code basis are not established by these CSV files. Digests identify
the retained bytes; they do not qualify the engineering results. The current
activity-code implementation is `bsee/analysis/war_rig_days.py`. Re-extraction and
basis validation remain separate work; calendar spans must not silently become
rig-day results.

## Method and worked example

`load_v50_kc_drilling()` validates required columns, unique nonempty numeric API
identifiers, finite nonnegative day values, and consistent lease-to-field names.
The report and `v30_financial_reproducer` use this same loader. Invalid day values
raise an error rather than becoming zero. Optional absent measurements remain
missing. No engineering coefficient or acceptance tolerance is introduced.

The report groups stored wellbore rows by development. Drilling and completion
days are summed separately and rounded to whole days using the existing report
convention, then added. Differences are selected-input minus benchmark.
The method is implemented in `scripts/completion/build_completion_report.py`,
`compute_reconciliation`; no new drilling-day derivation is performed.

For an independent hand calculation, take two **synthetic** wellbores in one
development. The inputs are 2 drilling plus 3 completion days for the first bore,
and 5 drilling plus 7 completion days for the second. Drilling totals 7 days and
completion totals 10 days; D&C totals 17 days across 2 bores. Against a synthetic
benchmark of 16 days and 1 bore, the differences are +1 day and +1 bore. The
disposition is `investigate`, because the day totals differ. This example is
asserted in `test_kc_reconciliation_hand_calculation`; it is not a Buckskin
measurement or a published field benchmark.

## Reproduce a candidate report

From the repository root, with repository dependencies installed:

```bash
uv run python scripts/completion/build_completion_report.py \
  --input-set v50_kc --output-dir "$TMPDIR/kc-completion"
```

Read `verification.html` in the requested output directory. `index.html` contains
the same comparison so that both entry points carry the input limitations.
KC output requires an explicit directory separate from `reports/completion/`.
Running the generator without `--input-set` retains the frozen V30 behavior.
Generated reports are build outputs and need not be committed.

The KC comparison includes Buckskin in the common-development totals and lists
its retained wellbores. Nonzero differences remain flagged. The retained article
comparison is a historical comparator, not independent proof that the current
day-count basis is correct. Producer counts and current-basis validation are
marked `NOT_EVALUATED`; neither can be established from this D&C table alone.

## Remaining acceptance work

The following parts of issue 842 are not established by this change:

- Fresh KC raw-input coverage and current-basis extraction readback.
- Producer-count confirmation from completion and production records.
- A field-code-backed correction to `bsee_field_crosswalk.csv`; a known lease
  identity alone does not establish its BSEE field identifier or confidence.
- Validation allowing replacement of frozen V30 workbooks and migration of
  financial configuration defaults. The existing opt-in financial input remains
  available; the frozen defaults are preserved.

The lease/block correction and retained KC lease additions already exist in the
repository. Historical article totals are not targets that justify changing
the extraction method to force agreement.
