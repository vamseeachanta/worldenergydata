# Lower Tertiary — field-performance comparison

All seven producing Lower Tertiary fields, side by side, from **public BSEE
data**. Per-well benchmark aggregated to the field level; economics joined
from the per-field reports. Life-to-date on public data — not full-cycle
economics. Deterministic and reproducible.

| Field | Wells | Cum oil (MMbbl) | EUR (MMbbl) | Avg uptime % | Avg decline %/yr | Interventions | NPV, LTD @10% ($MM) | LTD breakeven WTI ($/bbl) | NPV per +$1/bbl ($MM) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Jack St Malo | 24 | 438.8 | 500 | 89.7 | 18.4 | 6 | -804.5 | 79 | 52.3 |
| Stones | 10 | 89.0 | 250 | 76.9 | 21.4 | 3 | n/a | n/a | n/a |
| Big Foot | 8 | 78.7 | 200 | 88.2 | 17.2 | 6 | n/a | n/a | n/a |
| Julia | 4 | 77.5 | pending | 96.3 | 12.2 | 0 | -482.8 | 95 | 17.2 |
| Cascade Chinook | 3 | 39.7 | pending | 94.6 | 35.9 | 0 | n/a | n/a | n/a |
| Shenandoah | 4 | 21.2 | 332 | 80.2 | 5.4 | 1 | n/a | n/a | n/a |
| Anchor | 3 | 18.6 | 440 | 88.1 | 0.0 | 0 | n/a | n/a | n/a |
| **Portfolio** | **56** | **763.5** | **1722+** | — | — | **16** | — | — | — |

**Reading it:** **EUR is curated published/booked recoverable reserves** (operator & independent-auditor disclosures, `config/lt_field_reserves.yml`), NOT the decline-fit extrapolation — which ran ~2–6.6x too high (#973). Two fields with no public recoverable figure show `pending`. Economics are **life-to-date at 10%** on public BSEE data: full sunk capital charged against only the oil produced *so far*, not full-cycle EUR. Early-life fields are **withheld** (`n/a`); only 2 of 7 surface a credible life-to-date number, and those still read negative — the Lower Tertiary's high up-front capital, discounted against a long revenue tail, dominates at this point in life. A credible **full-cycle** NPV projected to the curated reserves is the next step (#971 Tier 1). See per-field `field_economics_<slug>.md` for the life-to-date derivation.

_Source: `worldenergydata` BSEE OGOR-A + cost model. Regenerate:_
_`uv run python scripts/lower_tertiary/build_well_benchmark.py` then_
_`uv run python scripts/lower_tertiary/build_field_performance_comparison.py`._
