# Disagreement report — plan #718 (2026-07-04)

## Verdicts

| Provider | Verdict |
|---|---|
| claude | MAJOR |
| codex | UNAVAILABLE (codex CLI failed, rc=124: Reading additional input from stdin... OpenAI Codex v0.142.5 -------- workdir: /mnt/local-analysis/wt-wed-718-brazil-plan model: gpt-5.5 provider: openai approval: on-request sandbox: workspace-write [workdir, /tmp, $TMPDIR] (network access enabled) reasoning effort: xhigh reasoning summaries: none session id: 019f2d95-788b-73b0-b832-162060792a38 -------- user # Adversarial plan review  You are an) |
| gemini | UNAVAILABLE (gemini CLI failed, rc=1: Warning: Basic terminal detected (TERM=dumb). Visual rendering will be limited. For the best experience, use a terminal emulator with truecolor support. Warning: 256-color support not detected. Using a terminal with at least 256-color support is recommended for a better visual experience. Error authenticating: IneligibleTierError: This client is no longer supported for Gemini Code Assist for indiv) |

## Findings unique to each provider

A finding is 'unique to X' if its text appears in X's artifact but not
verbatim in any other provider's artifact.

### claude

- **The scheduler job `brazil_anp_refresh.py` is a caller of both changing interfaces and is absent from the plan.** `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py` imports `ANPClient` and `WellProductionLoader` and is built on `_resolve_year_semester(config)`. The plan replaces `ANPClient`'s semester model with monthly resolution (Artifact Map, line 77–79) and rewrites `WellProductionLoader`'s expected columns (line 80–83), but this file appears in neither "Files to Change" (lines 145–157) nor the baseline test command (line 72, which covers only `tests/unit/brazil_anp` + `test_adapters.py`). This silently breaks the refresh job. It is doubly pointed because the plan's own listed dependency **#459 is a scheduler-refresh bug** — the plan is changing the exact subsystem #459 lives in without touching or testing it.
- **The plan's Mar/Presal/Terra partition mitigation contradicts its own concatenation step.** Risks (lines 217–219) assert "`pré-sal` is a subset of offshore data, so aggregation must avoid double counting." But the TDD (lines 164–165) commits to concatenating all three CSVs (`Mar`, `Presal`, `Terra`) with a `location_source` marker. If the Risk's "subset" claim is true, concatenation double-counts every pre-salt well — i.e. Lula, Búzios, and Mero, the marquee fields. In reality ANP publishes these as *disjoint* location partitions (onshore / offshore-post-salt / pre-salt), so concatenation is correct and the Risk statement is factually wrong. Either way the plan is internally inconsistent and one statement is wrong. Resolve empirically (sum one known field across the three files vs. ANP's published field total) before writing the aggregation, and fix whichever statement is false.
- **Acceptance Criterion #1 is non-actionable and the #459 relationship is unresolved.** AC#1 (lines 192–193): "#459 endpoint/schema failure is fixed **or this issue remains blocked** until #459 is closed." A criterion satisfied by the work remaining blocked is not a completion gate. Meanwhile the plan body *is* the #459 fix (Artifact Map line 77–79 replaces the stale CDP endpoint), and Execution mode (lines 11–12) offers "landed first as a dependency" as an alternative. Decide one of: (a) #718 subsumes and closes #459 (drop it from Dependencies, add "Closes #459"), or (b) #459 is a hard precondition owned elsewhere and #718 does not touch the endpoint. As written, ownership of the endpoint fix and the definition of "done" are ambiguous.
- **Pseudocode calls a method that does not exist and does not flag the breaking interface change.** Line 122: `client.download_month(year=2023, month=1, force_refresh=False)`. The current `ANPClient` public surface is entirely `(year, semester)`-keyed (`download`, `is_cached`, `load_cached`, `_cache_key`, `_build_url`). Introducing month-granularity replaces this surface. The plan should state explicitly that `download(year, semester)` and its cache-key scheme are being removed/replaced (relevant to Finding 1's caller audit), rather than presenting `download_month` as if it already exists.
- **Condensate is silently dropped from FDAS liquids, unaddressed for pre-salt.** `to_fdas_production` (contract.py:51–55) maps only `oil_bbl→MONTHLY_OIL_BBL`; the unified schema carries `condensate_bbl` separately (confirmed in `sodir_adapter.py:105,125`). Brazil pre-salt streams carry a material condensate fraction, so FDAS liquids for Lula/Búzios/Mero understate actual liquids. This matches the Norway precedent and the slice is explicitly "pre-tax plumbing" (lines 110–116), so it is not a correctness bug in the chain — but the plan should state that unified `oil_bbl` = oil only (condensate excluded) so a later economics pass does not inherit an unflagged understatement. (MINOR.)
- **The unified `source` label is under-specified.** TDD (lines 177–178) accepts `source="anp"` **or** `source="anp_producao_poco"`. The `source` marker is a contract value downstream consumers key on; an acceptance test permitting either value pins nothing. Choose exactly one. (MINOR.)
- **Plan text drops the diacritic on "Búzios".** Lines 24, 42-adjacent — plan writes "Buzios"; the code (`brazil_anp_adapter.py:31`) uses `"Búzios"`. Per this repo's orthographic rule and because field-name string matching is exact (`fields=["Marlim"]`-style filters), any hardcoded fixture/filter using the unaccented spelling will silently miss the field. (MINOR, but verify no ASCII "Buzios" literal reaches a matcher.)

### codex

(no findings unique to this provider)

### gemini

(no findings unique to this provider)
