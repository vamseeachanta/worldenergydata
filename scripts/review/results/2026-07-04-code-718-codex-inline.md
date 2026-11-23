# Code Review — worldenergydata #718 Brazil ANP Reference Chain

- **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/718
- **Reviewer:** Codex inline adversarial review
- **Date:** 2026-07-04
- **Scope:** `origin/main...feat/brazil-718-chain`, implementation commit `3db9a232`
- **Verdict:** APPROVE

## Checks Performed

- Verified `ANPClient` now defaults to the official gov.br ANP production-by-well ZIP directory, not the stale CDP APEX endpoint.
- Verified `download_month(year, month)` builds `producao-MM.zip`, caches by month, and keeps the legacy semester wrapper as a concatenating compatibility path.
- Verified official ZIP CSV parsing handles the two-row ANP header and skipped blank row, flattens compound Portuguese headers, tags partition source, and filters data rows by `Periodo`.
- Verified live-source overlap handling is explicit: expected `mar`/`presal` duplicate keys are deduplicated with `presal` priority, while unexpected duplicate source combinations fail closed.
- Verified the current ANP Portuguese well schema converts daily oil, condensate, water, and Brazilian `Mm3/dia` gas rates into monthly `oil_bbl`, `condensate_bbl`, `water_bbl`, and `gas_mcf`.
- Verified `BrazilAnpAdapter(loader=...)` maps normalized ANP production into `STANDARD_COLUMNS` with `source="anp_producao_poco"` while preserving the no-loader synthetic compatibility fixture.
- Verified `BrazilAnpRefreshJob` calls `download_month`, writes month-keyed raw and normalized parquet, and maps legacy semester config to the final month of the semester without calling the stale semester client path.
- Verified Brazil `FieldConcept` mapping reduces ANP field/platform/well metadata into a sparse field concept and the reference-chain runner performs `adapter.fetch -> to_fdas_production -> CashflowEngine` plus `FieldConcept -> recommend`.

## Findings

### Finding 1 — Initial partition-disjoint assumption was false

**Risk:** The earlier plan assumption that `Mar`, `Presal`, and `Terra` partitions were disjoint was wrong. Live January 2023 ANP data showed `mar`/`presal` duplicate field/well/month keys.

**Resolution:** The plan and implementation were changed to treat only `mar`/`presal` overlap as expected, retain `presal`, and raise on all other duplicate source combinations. Live parse evidence after the fix: 6,310 rows, sources `mar`, `presal`, `terra`, duplicate key count 0.

**Status:** resolved.

### Finding 2 — Gas unit interpretation needed a pinned contract

**Risk:** Treating Brazilian ANP `Mm3/dia` as million cubic meters per day would overstate gas by 1,000x. In Brazilian ANP usage here it is thousand cubic meters per day.

**Resolution:** Current-schema tests pin the conversion as daily thousand-m3 gas to monthly Mcf using `GasUnits.SM3_TO_SCF * days`. The implementation keeps the legacy lowercase schema conversion separately.

**Status:** resolved.

### Finding 3 — Scheduler compatibility must not revive the stale CDP path

**Risk:** The old semester-based refresh API could keep calling the stale CDP APEX endpoint even after the monthly direct-source client was added.

**Resolution:** `BrazilAnpRefreshJob` now calls `client.download_month(...)`; tests assert the legacy `download(...)` method is not used. Legacy `year + semester` config only resolves to month 6 or 12 for backward-compatible configuration parsing.

**Status:** resolved.

### Finding 4 — Economics boundary must stay pre-tax plumbing

**Risk:** The issue body mentions Brazil fiscal economics, but this slice does not implement Brazil after-tax fiscal terms or a publishable investment metric.

**Resolution:** The runner returns `economics_label="chain_plumbing_pre_tax"` and only aggregate plumbing metrics. Brazil fiscal terms and after-tax economics remain deferred to the fiscal follow-up.

**Status:** accepted residual scope boundary.

## Evidence

- RED: `tests/unit/brazil_anp/test_anp_client.py` initially failed with missing monthly APIs and stale URL expectations (`10 failed, 2 passed`).
- GREEN focused: `89 passed in 3.70s`.
- GREEN adjacent: `200 passed in 4.89s`.
- GREEN broader post-rebase: `495 passed, 1 skipped in 6.90s`.
- Static checks: `ruff check` on touched files passed.
- Whitespace: `git diff --check` passed.
- Legal scan: dirty diff scan passed before commit; committed-diff scan for `HEAD~1..HEAD` passed. Full-repo `--all` scan still fails on pre-existing unrelated `ENIGMA/enigma` terms outside this issue scope.
- Direct-source live parse: official ANP January 2023 ZIP parsed to 6,310 rows across `mar`, `presal`, and `terra` with 0 duplicate field/well/month keys after expected-overlap dedupe.

## Residual Risk

- External Claude and Gemini code-review attempts were unavailable in this session; separate unavailability artifacts record the exact failure modes.
- Brazil after-tax fiscal economics, condensate-specific revenue treatment, and published Brazil investment metrics are not included in this slice.
