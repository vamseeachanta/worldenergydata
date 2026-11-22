# D&C republication review

The local audit exposes changes on identical bore populations and checks the
retained publication snapshots before figures are replaced. It does not authorize
replacement. Wider-population weekly-record confirmation, financial reruns and
external publication remain `NOT_EVALUATED` when that evidence is unavailable.

## Revision history

| Revision | Date | What changed and why |
|---|---|---|
| initial | 2026-10-21 | Add a readable review and snapshot checks to expose incomplete republication evidence. |

## Inputs and method

`scripts/lower_tertiary/build_dc_republication_audit.py` reads the retained
extractor CSV, committed per-well WAR histories and operational sample through
the existing day-basis comparison module. It retains the displayed source
population, labels coverage, records input digests and keeps all methods:

- **Milestone:** drilling is TD minus spud; completion is the inclusive union of
  reported intervals clipped at TD. Unreported gaps add no completion days.
  Source: issue #1064, revised decision of 2026-10-12, and
  [day basis comparison, Rule and conventions](day_basis_comparison.md#rule-and-conventions).
- **Activity code:** separate DRL and COM interval unions. Other codes remain in
  the granular breakdown; PND is not assigned an inferred meaning.
  Source: the same comparison, Rule and conventions, and
  [WAR interval method](rig_days_by_WAR.md).
- **Interim:** inclusive spud-to-TD and inclusive TD-to-last-reported-end calendar
  spans. TD appears in both phases and calendar gaps remain included.
  Source: [summary, preferred completion method 3](rig_days_summary.md), dated
  2025-06-02, formulas for drilling and preferred completion.
- **Change:** after minus before, computed only for identical available
  bore/metric pairs. Source: issue #1079, Mandatory: show the change (2026).

The milestone decision retains the other methods and requires confirmation over
the wider population before replacement. Matching two retained surfaces is not
that confirmation. Undated legacy zeros stay in the displayed snapshot but are
excluded from paired comparisons. Nulls are never filled with measured zeros.

## Run the audit

Choose an existing output folder outside the repository and set `AUDIT_OUT` to
that folder. With the namespace packages on the Python path:

```sh
export PYTHONPATH=src:packages/worldenergydata-core/src:packages/worldenergydata-bsee/src:scripts
uv run --no-project --with 'pandas>=2.3.3,<3.0' --with pyyaml --with pydantic-settings --with loguru \
  python scripts/lower_tertiary/build_dc_republication_audit.py \
  --output "$AUDIT_OUT/audit.json" \
  --markdown-output "$AUDIT_OUT/review.md" --report-date 2026-10-21
```

The report date is an explicit input; neither output embeds a generation time or
absolute source path. JSON-only invocation remains supported. Both destinations
are validated before writing, must differ, and must resolve outside the source
repository. The existing snapshot files are read without executing generators.
The pandas constraint follows the repository dependency declaration in
`pyproject.toml`. The review includes the existing shared WAR methodology note,
including weekly-boundary uncertainty and the unconfirmed historical coverage
floor; it does not introduce a new normalization or acceptance threshold.

## Worked example

The synthetic example is implemented independently in
`tests/unit/lower_tertiary/test_dc_republication_audit.py`. All dates and counts
below are test inputs, not field assumptions or acceptance limits.

Spud is January 1 and TD is January 8 of the same year. Reported intervals are
DRL January 1–7, PND January 8–14 and COM January 22–28. The retained source
displays drilling 6 and completion 10, giving D&C 16. A second bore has no dates
or weekly records and displays legacy zeros.

| Method | Drilling calculation | Completion calculation | D&C | D&C change from 16 |
|---|---|---|---:|---:|
| milestone | 8 − 1 = 7 | 7 + 7 = 14 reported days from TD | 21 | +5 |
| activity code | DRL = 7 | COM = 7 | 14 | −2 |
| interim | 8 − 1 + 1 = 8 | 28 − 8 + 1 = 21 | 29 | +13 |

The January 15–21 gap contributes no reported time. Interim includes that gap
and counts TD in both phases. PND contributes to milestone completion but is
separate from activity-code completion. The known bore contributes a paired
subtotal; the missing bore prevents a confirmed replacement development total.
Per-development NPV changes remain null with `NOT_EVALUATED`, rather than being
inferred by multiplying days by an assumed rate. Discounted capital also depends
on timing and the common cost deck; the existing financial reproducer must be
rerun on confirmed inputs.

## Snapshot checks and interpretation

`scripts/lower_tertiary/dc_surface_audit.py` compares retained source counts with:

- The validation reconciliation matrix: development membership, bore count and
  D&C total.
- The per-well listing: bore membership and drilling/completion/D&C values,
  plus development summary counts.
- The drill-down embedded JSON: bore identity, development attribution and
  drilling/completion values, plus development summary counts.
- The vintage CSV: current-side bore identity, development attribution and
  drilling/completion values.

`MATCH` means those displayed counts agree exactly. `MISMATCH` identifies extra,
missing or different values; `INVALID` identifies malformed counts or schemas;
missing artifacts remain `NOT_EVALUATED`. JSON records findings and the digest
of each inspected artifact. Historical vintage categories, narrative statements,
drill-down block totals and basis correctness are outside these checks. Remote
dataset and website surfaces remain explicitly `NOT_EVALUATED`; the overall
surface-agreement status never certifies publication from local matches alone.

## Completion requirements

Obtain and confirm the wider weekly population before replacing any figure.
Then regenerate all surfaces together, publish the per-development before/after
and reasons in the validation page, rerun the financial model on identical cost
and production assumptions, and disclose the NPV delta per development. Update
exact fidelity pins only with the corresponding confirmed output and rationale.
The existing reference-well regression still checks DRL 151 and total 308 from
the committed interval rows; that is reproducibility evidence, not independent
validation of a default basis. Source: the comparison's Test well section and
the hand calculation in the audit test docstring.

The publication steps for the external dataset and website are separate from
this read-only audit. Until they have been inspected after regeneration, no
claim that all six surfaces agree is supported.
