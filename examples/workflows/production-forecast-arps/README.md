# Production Forecast Arps

Offline Arps decline workflow using bundled exact synthetic production histories.

The exponential case uses `qi=1000`, `Di=0.1`, and economic limit `100`, so
closed-form EUR is `(1000 - 100) / 0.1 = 9000 bbl`.

The hyperbolic case uses `qi=1000`, `Di=0.1`, `b=0.5`, and the same economic
limit, giving closed-form EUR `13675.444679663216 bbl`.
