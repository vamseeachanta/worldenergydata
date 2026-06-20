# Lower Tertiary — field-performance comparison

All seven producing Lower Tertiary fields, side by side, from **public BSEE
data**. Per-well benchmark aggregated to the field level; economics joined
from the per-field reports. Life-to-date on public data — not full-cycle
sanctioned economics. Deterministic and reproducible.

| Field | Wells | Cum oil (MMbbl) | EUR (MMbbl) | Avg uptime % | Avg decline %/yr | Interventions | NPV @10% ($MM) | WTI break-even ($/bbl) | NPV per +$1/bbl ($MM) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Jack St Malo | 24 | 438.8 | 1117 | 89.7 | 18.4 | 6 | -804.5 | 79 | 52.3 |
| Stones | 10 | 89.0 | 509 | 76.9 | 21.4 | 3 | -1,460.8 | 165 | 14.9 |
| Big Foot | 8 | 78.7 | 1324 | 88.2 | 17.2 | 6 | -989.0 | 153 | 12.1 |
| Julia | 4 | 77.5 | 256 | 96.3 | 12.2 | 0 | -482.8 | 95 | 17.2 |
| Cascade Chinook | 3 | 39.7 | 92 | 94.6 | 35.9 | 0 | -1,480.5 | 338 | 5.5 |
| Shenandoah | 4 | 21.2 | 1577 | 80.2 | 5.4 | 1 | -991.3 | 376 | 3.2 |
| Anchor | 3 | 18.6 | 998 | 88.1 | 0.0 | 0 | -1,586.9 | 380 | 5.1 |
| **Portfolio** | **56** | **763.5** | **5873** | — | — | **16** | **-7,795.8** | — | — |

**Reading it:** every field is NPV-negative at 10% life-to-date — the Lower
Tertiary's high up-front capital dominates. Break-even WTI shows how far
above the realized ~$69/bbl each field would need to clear zero; the
per-$1/bbl column is the exact NPV slope (NPV is affine in price).

_Source: `worldenergydata` BSEE OGOR-A + V30 cost model. Regenerate:_
_`uv run python scripts/lower_tertiary/build_well_benchmark.py` then_
_`uv run python scripts/lower_tertiary/build_field_performance_comparison.py`._
