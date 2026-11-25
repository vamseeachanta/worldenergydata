# Historical evidence in the original supported-start cohort

Among the 2,514 supported starts in revision `396d3d400660b6e02908d682dda1cd717c448bbf`, 701 API10s (27.9%) have a dated spud before January 2005. Of those, 109 also have an eWell completion before January 2005. A pre-window spud establishes the age of a bore. A spud date alone cannot establish whether the well produced before the production series began.

| Assigned water depth (m) | Original supported starts | A. Pre-2005 spud | B. Undated bore, 2005+ spud and blank first production | C. Pre-2005 completion | D. Union of A, B, C |
| --- | ---: | ---: | ---: | ---: | ---: |
| Under 100 | 1,554 | 479 | 0 | 91 | 479 |
| 100 to under 500 | 195 | 67 | 0 | 11 | 67 |
| 500 to under 1,500 | 396 | 96 | 0 | 7 | 96 |
| 1,500 and deeper | 369 | 59 | 0 | 0 | 59 |
| All assigned depths | 2,514 | 701 | 0 | 109 | 701 |

*Table 1. Distinct API10s in the pre-fix cohort, counted once within each category. All 109 API10s in C also occur in A. A further 592 API10s occur only in A.*

| Category | Example API10s in ascending order (up to 10) |
| --- | --- |
| A | 1770000027, 1770020235, 1770040230, 1770040429, 1770040611, 1770040863, 1770040869, 1770040981, 1770040993, 1770041049 |
| B | No qualifying API10s |
| C | 1770040230, 1770040611, 1770041055, 1770041195, 1770140360, 1770140366, 1770241192, 1770440132, 1770520070, 1770540120 |
| D | 1770000027, 1770020235, 1770040230, 1770040429, 1770040611, 1770040863, 1770040869, 1770040981, 1770040993, 1770041049 |

*Table 2. The examples use the first ten matching identifiers in each nonempty category.*

## Measurement basis

The pre-fix inventory, eWell completion selection, OGOR-A well-month collapse and first-month calculation were run at the revision above with pandas 3.1.1 and NumPy 2.4.6. All 29 ZIPs from the 23 November well snapshot and 25 November 2026 production and lease snapshot matched their SHA-256 pins. The measurement used only the API10s for which that revision returned `start_supported = True`, with their original depth assignments. [Source archive pins](source_pins.json)

For each of those API10s, all matching borehole rows, including cancelled bores, were examined. A requires the earliest parseable `WELL_SPUD_DATE` to precede 1 January 2005. B requires at least one missing or unparseable spud date, at least one spud on or after that date, and no nonblank `FIRST_PROD_DATE` in the joined OGOR-A records. C requires at least one `EOR_OPERATION_CD = C` with `BOREHOLE_STAT_DT` before 1 January 2005. D counts distinct API10s satisfying at least one of A, B or C.

Across the full baseline cohort, zero API10s have an undated `ST00BP00` original bore and zero lack a dated spud on every bore. Applying the three historical screens and requiring a dated spud therefore leaves 1,813 of these original 2,514 starts. This comparison holds the pre-fix signed-volume activity logic fixed.
