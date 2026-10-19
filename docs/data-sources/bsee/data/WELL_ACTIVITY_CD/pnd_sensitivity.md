# Interim PND sensitivity reporting

`rig_days_pnd_sensitivity` returns both PND treatments together, per bore or
per well, while the `WELL_ACTIVITY_CD` definition remains unvalidated. It
supports interim comparison for issue #1065 without choosing an authoritative
completion basis. Including PND in completion is an assumption, not a meaning
assigned to the code.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Added paired reporting guidance so PND treatment stays explicit. |

## Usage

Supply the joined WAR frame: `mv_war_main` provides `API_WELL_NUMBER`,
`WAR_START_DT` and `WAR_END_DT`; `mv_war_main_prop` provides
`WELL_ACTIVITY_CD`, joined on `SN_WAR`.

```python
from worldenergydata.bsee.analysis.war_pnd_sensitivity import (
    rig_days_pnd_sensitivity,
)

# joined_war is the caller's assembled WAR DataFrame.
by_bore = rig_days_pnd_sensitivity(joined_war)
by_well = rig_days_pnd_sensitivity(joined_war, grain="well")
by_bore.to_csv("pnd_sensitivity_by_bore.csv", index=False)
```

The default `grain="bore"` produces API12 rows. `grain="well"` produces API10
rows by unioning intervals across selected bores. The optional `population`
argument always contains API12 identifiers, including when requesting well
results; it filters bores before the well union.

Each entity has an `excluded` row and an `included_in_completion` row in
`pnd_treatment`. All excluded rows precede all included rows. Each row also
carries `basis` and `pnd_definition_status="unvalidated"`. The latter describes
the code definition even when no PND dates occur. An empty input without a
population returns an empty frame with the report columns.

| Treatment | Drilling codes | Completion codes | PND definition status |
| --- | --- | --- | --- |
| `excluded` | DRL | COM | unvalidated |
| `included_in_completion` | DRL | COM and PND | unvalidated |

Both scenarios reuse the existing
[rig-day engine](../../../../../packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/war_rig_days.py).
Its inclusive calendar-day convention, coverage statuses, null durations and
diagnostic columns are retained. At well grain, the engine also emits
`*_additive` per-bore sums; those sums can exceed the interval union.
No new arithmetic convention or acceptance threshold is introduced.

## Independent calendar example

For synthetic COM dates January 1 through January 7 and PND dates January 5
through January 11, inclusive counting gives:

- Excluded completion: the dates January 1 through January 7, hence 7 days.
- Included completion: the dates January 1 through January 11, hence 11 days.
- PND diagnostic: the dates January 5 through January 11, hence 7 days.

These values are a hand enumeration, not observed operations. The overlap is
January 5, 6 and 7, so adding the PND diagnostic to excluded completion would
count those dates twice. The same example across different bores demonstrates
why well results must union intervals rather than sum bore totals.

The [unit tests](../../../../../tests/unit/bsee/analysis/test_war_pnd_sensitivity.py)
write out the independent expected counts for overlap, duplicate intervals,
PND-only activity, absent coverage, population restriction and well union.
If only PND is present, excluded completion remains null with
`no_activity_coded`; it is not a measured zero. A requested bore with no WAR
coverage remains null in both scenarios. Missing activity codes do not become
PND. Reject and coverage diagnostics follow the underlying engine at each grain.

## Evidence and limitations

The policy source is issue #1065, Action 2, and the repository's
[publication-status note](publication_status.md), checked 2026-10-12.
The following public pages were reopened on 2026-10-19; both returned HTTP 200:

| Source | Bounded finding |
| --- | --- |
| [BSEE eWell WAR Field Definitions](https://www.data.bsee.gov/Well/eWellWAR/FieldDefinitions.aspx) | The rendered list runs from SN_WAR to BOTM_BLOCK_NUM and omits WELL_ACTIVITY_CD. |
| [BSEE borehole field definitions](https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields) | BOREHOLE_STAT_CDS is a different domain and contains no PND entry. |

Only the returned pages were inspected; dynamic panels and authenticated help
were not inspected. This does not prove that a definition is unavailable
everywhere. The canonical
[activity vocabulary](../../../../../packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data/war_activity_codes.yml)
continues to record PND with unknown provenance and no definition. Borehole
status wording and ONRR production-status codes do not validate WAR meanings.

These scenarios describe sensitivity to a declared treatment. They do not
establish uncertainty bounds, non-productive time or measured completion
activity. Other activity codes remain governed by the existing engine and
vocabulary; this helper addresses PND alone.

Sending the enquiry, recording its actual transmission date and obtaining an
official reply remain for the maintainers. No transmission, elapsed wait or
reply is asserted here. Existing published datasets and reports have not been
regenerated; consumers can adopt this API when publishing interim results.
