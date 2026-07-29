# `WELL_ACTIVITY_CD` — where the definitions actually live

> **This file used to be mislabelled.** Its directory and filename say
> `WELL_ACTIVITY_CD`, but its contents were BSEE's **`BOREHOLE_STAT_CD`**
> (borehole *status*) list — the column headers literally read
> `BOREHOLE STAT CD | BOREHOLE STAT DESC` — with one locally invented row
> (`PND`) appended to the bottom. Anyone reading it as the WAR activity-code
> domain was reading the wrong domain. Corrected under
> [#1065](https://github.com/vamseeachanta/worldenergydata/issues/1065).

## Two facts to carry away

1. **BSEE publishes no code list for `WELL_ACTIVITY_CD`.** Not a partial one, not
   an out-of-date one — none. The eWell WAR field definitions page, the
   `eWellWARRawData.zip` archive, Form BSEE-0133, 30 CFR 250.743 and ONRR
   Appendix H were each checked; every one is negative. The searches and their
   results are recorded in the canonical file below.
2. **The list reproduced further down is the `BOREHOLE_STAT_CD` domain**, which
   *is* published by BSEE. Six WAR activity tokens (`WO`, `CHZ`, `PND`, `MPF`,
   `REC`, `TBK`) do not appear in it at all, and six published borehole codes
   never appear in WAR. The two vocabularies overlap; they are not the same
   vocabulary.

## Canonical source

The single definition source for the WAR activity codes is:

```
packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data/war_activity_codes.yml
```

Load it in code — do not re-type it:

```python
from worldenergydata.bsee.analysis.war_activity_codes import (
    load_activity_codes,   # the whole document, including provenance
    activity_labels,       # code -> label, documented codes ONLY
    undocumented_codes,    # the six BSEE has never defined
)
```

Each code there carries a `provenance` field. `published_other_domain` means the
token is published — in `BOREHOLE_STAT_CD`, and its reuse as an activity code is
**our inference**, corroborated by remark text, not a BSEE statement. `unknown`
means BSEE has published nothing and its `label` is `null`.

**Never attach a meaning to a code whose provenance is `unknown`.** `WO`, `PND`,
`CHZ`, `MPF`, `REC` and `TBK` together are ~16% of WAR rows; a basis that
includes or excludes any of them is making a choice, not a measurement. The full
domain is outstanding with BSEE (TDM@bsee.gov) — the ask is the whole vocabulary,
not `PND` alone.

## BSEE `BOREHOLE_STAT_CD` — the real, published list

Source: <https://www.data.bsee.gov/Main/HtmlPage.aspx?page=boreholeFields>.
Preserved here as the borehole-status reference it actually is.

| BOREHOLE_STAT_CD | BOREHOLE_STAT_DESC |
|------------------|---------------------|
| APD              | APPLICATION FOR PERMIT TO DRILL |
| AST              | APPROVED SIDETRACK |
| CNL              | BOREHOLE IS CANCELLED. THE REQUEST TO DRILL THE WELL IS CANCELLED AFTER THE APD OR SUNDRY HAS BEEN APPROVED. THE STATUS DATE IS THE DATE THE BOREHOLE WAS CANCELLED. |
| COM              | BOREHOLE COMPLETED  |
| CT               | CORE TEST WELL      |
| DRL              | DRILLING ACTIVE     |
| DSI              | DRILLING SUSPENDED  |
| PA               | PERMANENTLY ABANDONED |
| ST               | BOREHOLE SIDETRACKED |
| TA               | TEMPORARILY ABANDONED |
| VCW              | VOLUME CHAMBER WELL |

### The `PND` row that used to sit at the bottom of that table

The table above previously carried a twelfth row, `PND | PENDING/UNKNOWN`,
followed by the note:

> PND means we guessed it as unknown.

That row is **not BSEE's**. `PND` does not appear in the published
`BOREHOLE_STAT_CD` domain; it was added locally because the token shows up in WAR
data. It has been lifted out of the table so it can no longer be mistaken for a
published borehole status, and the honesty of the original note is now carried
properly in `war_activity_codes.yml`, where `PND` has `label: null`.

The note was right, and it matters: mirrors of this file that dropped the
`/UNKNOWN` qualifier and the sentence beneath it — leaving a bare
`PND | PENDING` — are how a hedge became a fact.

---

*Superseded as a definition source; retained as the `BOREHOLE_STAT_CD` reference.
Last updated: 2026-07-28.*
