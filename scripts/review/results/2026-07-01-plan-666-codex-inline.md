# Codex Inline Plan Review - Issue #666

Verdict: APPROVE for `status:plan-review`.

Scope reviewed:
- Issue #666 acceptance criteria.
- Merged Texas RRC prerequisites from #663, #664, and #665.
- Current `/mnt/ace` curated artifact inventory.
- Existing BSEE all-fields and field deep-dive report patterns.

Findings:

1. MAJOR - The plan must not depend on BSEE-specific OGOR report loaders.
   - Risk: importing BSEE report code would mix offshore assumptions, field
     identifiers, and OGOR timelines into the Texas RRC onshore report path.
   - Resolution: the plan creates a Texas RRC-local `reports` package and uses
     BSEE modules only as precedent.

2. MAJOR - The plan must not present RRC pipeline proximity as engineered
   market access.
   - Risk: #665 metrics are centroid/envelope screening outputs, not tie-in
     feasibility, capacity, ownership, tariff, or right-of-way evidence.
   - Resolution: the report content and risk controls require visible caveats
     on the index and every field page.

3. MINOR - The plan should include machine-readable report summary outputs, not
   only HTML.
   - Resolution: the output contract includes CSV, Parquet, quality JSON, and
     manifest JSON alongside HTML pages.

Residual risk:
- The report fanout may produce many pages. The implementation plan includes a
  `--max-fields` option for bounded smoke runs, but the full `/mnt/ace`
  publication run will still need runtime and output-size verification.
