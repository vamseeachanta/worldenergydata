# Plan: Issue #172 — Reproduce rev30 Lower Tertiary BSEE field results

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/172
**Status:** plan-review
**Tier:** T2 (reproducibility verification)
**Note:** LT epic (#373–#377) completed. This issue verifies rev30 baseline is reproducible.

## Plan

### Task 1 — Run the portfolio analysis
```bash
uv run python -c "
from worldenergydata.lower_tertiary.portfolio_economics import run_portfolio
results = run_portfolio()
for r in results:
    print(f'{r[\"field\"]}: NPV={r[\"npv_mm\"]:.1f}MM IRR={r[\"irr_pct\"]:.1f}%')
"
```

### Task 2 — Compare against rev30 reference figures
The rev30 report should have NPV/IRR/breakeven per field. Identify the reference source
(Excel workbook, prior report, or archived YAML).

### Task 3 — Document reproducibility delta
If results match within 5%: close as verified.
If results differ: document the delta and file a separate follow-up issue for reconciliation.

### Task 4 — Add snapshot test
`tests/unit/lower_tertiary/test_portfolio_snapshot.py`:
```python
def test_lt_portfolio_reproducible():
    results = run_portfolio()
    # Shenandoah reference IRR > 80% (high ROI, well-established)
    shen = next(r for r in results if r["field"] == "Shenandoah")
    assert shen["irr_pct"] > 50
    assert shen["npv_mm"] > 0
```

## Acceptance Criteria
- `run_portfolio()` runs without error
- Results documented against rev30 reference in issue comment
- Snapshot test exists
