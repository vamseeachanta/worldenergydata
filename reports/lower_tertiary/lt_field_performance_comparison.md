# Lower Tertiary — field-performance comparison

All seven producing Lower Tertiary fields, side by side, from **public BSEE
data**. Per-well benchmark aggregated to the field level; economics joined
from the per-field reports. Life-to-date on public data — not full-cycle
sanctioned economics. Deterministic and reproducible.

| Field | Wells | Cum oil (MMbbl) | EUR (MMbbl) | Avg uptime % | Avg decline %/yr | Interventions | NPV, LTD @10% ($MM) | LTD breakeven WTI ($/bbl) | NPV per +$1/bbl ($MM) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Jack St Malo | 24 | 438.8 | 1117 | 89.7 | 18.4 | 6 | -804.5 | 79 | 52.3 |
| Stones | 10 | 89.0 | 509 | 76.9 | 21.4 | 3 | n/a | n/a | n/a |
| Big Foot | 8 | 78.7 | 1324 | 88.2 | 17.2 | 6 | n/a | n/a | n/a |
| Julia | 4 | 77.5 | 256 | 96.3 | 12.2 | 0 | -482.8 | 95 | 17.2 |
| Cascade Chinook | 3 | 39.7 | 92 | 94.6 | 35.9 | 0 | n/a | n/a | n/a |
| Shenandoah | 4 | 21.2 | 1577 | 80.2 | 5.4 | 1 | n/a | n/a | n/a |
| Anchor | 3 | 18.6 | 998 | 88.1 | 0.0 | 0 | n/a | n/a | n/a |
| **Portfolio** | **56** | **763.5** | **5873** | — | — | **16** | — | — | — |

**Reading it:** economics are **life-to-date at 10%** on public BSEE data — they charge each field's full sunk capital against only the oil produced *so far*, not against full-cycle EUR. For fields early in life that is legitimately deep-negative, so those values are **withheld as early-life** (shown `n/a`); only 2 of 7 fields have produced enough of their EUR and clear a credible breakeven to surface a life-to-date number. Those still read negative — the Lower Tertiary's high up-front capital, discounted against a long revenue tail, dominates at this point in life; the LTD breakeven shows how far above the realized ~$69/bbl the field would need to clear zero to date. A credible **full-cycle** recompute is deferred to #973 (gated on validating the decline-fit EUR). See per-field `field_economics_<slug>.md` for the full life-to-date derivation.

_Source: `worldenergydata` BSEE OGOR-A + V30 cost model. Regenerate:_
_`uv run python scripts/lower_tertiary/build_well_benchmark.py` then_
_`uv run python scripts/lower_tertiary/build_field_performance_comparison.py`._
