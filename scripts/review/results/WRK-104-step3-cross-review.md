# WRK-104 Step 3 Cross-Review: Extended Fleet Collection

Date: 2026-02-13

## Claude Review

### Files Reviewed
- `scripts/vessel_fleet/collect_drilling_fleet.py` (236 lines)
- `tests/modules/vessel_fleet/test_collect_drilling_fleet.py` (240 lines)
- `src/worldenergydata/vessel_fleet/collectors/scrape_parser.py` (supporting module, 345 lines)
- `src/worldenergydata/vessel_fleet/collectors/fleet_page_collector.py` (supporting module, 116 lines)
- `src/worldenergydata/vessel_fleet/storage/parquet.py` (supporting module, 81 lines)

### Fallback Chain Correctness

The three-source fallback chain is correctly implemented in `collect_operator_fleet()`:

1. **Web scrape** (gated by `try_web=True` AND config loaded successfully) - lines 161-164
2. **Scrape JSON** (gated by operator being in `_SCRAPE_PARSERS` dict AND JSON file existing) - lines 167-169
3. **KNOWN_VESSELS** (always attempted via `_load_known_vessels`) - lines 172-174

All three are collected into a `candidates` list, then `max(candidates, key=lambda x: len(x[1]))` selects the source with the most records. This is not a strict fallback chain (first-success-wins) but rather a best-of-N policy. The docstring says "fallback" but the behavior is "best source wins." This semantic distinction could confuse future maintainers.

### Source Selection Logic

The `max()` selection at line 181 is correct. When multiple sources tie on record count, Python's `max()` returns the first encountered item, which preserves the insertion order: web > scrape_json > known_vessels. This implicit tie-break is reasonable (prefer fresher data) but is undocumented and untested.

### Error Handling

**Strengths:**
- Each source function wraps its logic in try/except and returns `[]` on failure
- `_collect_from_web` catches any exception from `FleetPageCollector.collect()`
- `_collect_from_scrape_json` catches import errors and parse errors
- `_load_known_vessels` catches module import failures and missing attributes
- `collect_operator_fleet` handles config import failure gracefully (sets `config = None`, which disables web scrape)
- The script never crashes on a single operator failure; it logs and moves on

**Concerns:**
- P2: `_load_known_vessels` mutates the `KNOWN_VESSELS` list in-place via `vessel.setdefault()` on lines 74-77. If the module is imported multiple times (which `importlib.import_module` caches), subsequent calls will see previously-set defaults. This is not harmful (setdefault is idempotent for same values) but mutating imported module-level data is a code smell.
- P3: `_collect_from_scrape_json` does a deferred import inside a try block (lines 113-116). This means an import error in `scrape_parser` module is silently swallowed. If the module has a bug, the error message at line 133 only says "Scrape JSON parse failed" without distinguishing import vs parse failure.

### Test Quality

**Strengths:**
- 14 tests across 4 test classes with clear separation of concerns
- `sample_config_module` fixture creates a real importable Python module in `tmp_path` - well designed
- No network calls during testing: `try_web=False` is the default, and `FleetPageCollector` is mocked when `try_web=True`
- `test_web_scrape_disabled_by_default` verifies the mock is never called
- `test_web_scrape_failure_falls_back` verifies graceful degradation to KNOWN_VESSELS
- Integration tests (`TestCollectionSummary`) verify all 13 real configs load successfully

**Concerns:**
- P1: `test_scrape_json_preferred_over_known_vessels` (line 174) asserts `len(records) >= 31` but Noble has 31 records in BOTH scrape_json and known_vessels. The test cannot distinguish which source was selected. To truly verify preference, the test would need to check a field unique to the scrape_json source (e.g., `WATER_DEPTH_RATING_FT` or `RIG_DESIGN` which scrape_parser adds but KNOWN_VESSELS may not have).
- P2: No test exercises the tie-break behavior (equal record counts from two sources). Since Noble scrape and known both have 31, the test `test_scrape_json_preferred_over_known_vessels` actually hits a tie but does not verify which source won.
- P2: No test for `_collect_from_scrape_json` when the parser function raises an exception (line 132 error path).
- P2: No test for `collect_operator_fleet` when the config module import fails (line 155 error path).
- P3: The `sample_config_module` fixture inserts into `sys.path` but never cleans up. Across multiple tests this could accumulate stale paths. Using `monkeypatch.syspath_prepend()` would be cleaner.
- P3: `ContractorConfig` import at test line 15 is unused in the test file.

### Code Quality

- Clean structure, well under 500-line limits
- Type hints throughout
- Logging is appropriate at INFO/WARNING levels
- `_SCRAPE_PARSERS` dict + `_collect_from_scrape_json` function nicely decouple parser dispatch
- The `main()` function properly uses `argparse` with sensible defaults
- File is 236 lines, well within limits

### Summary of Findings

| # | Severity | Finding |
|---|----------|---------|
| 1 | P1 | `test_scrape_json_preferred_over_known_vessels` does not actually verify source preference (Noble has 31 in both sources) |
| 2 | P2 | Tie-break behavior (equal counts) is undocumented and untested |
| 3 | P2 | `_load_known_vessels` mutates module-level KNOWN_VESSELS list in-place |
| 4 | P2 | Missing test for scrape_parser exception path in `_collect_from_scrape_json` |
| 5 | P2 | Missing test for config import failure path in `collect_operator_fleet` |
| 6 | P3 | Docstring says "fallback chain" but behavior is "best-of-N by count" - terminology mismatch |
| 7 | P3 | Unused `ContractorConfig` import in test file |
| 8 | P3 | `sys.path` pollution in `sample_config_module` fixture (no cleanup) |

**Verdict**: MINOR

The implementation is solid and functional. The fallback-to-best-source logic works correctly, error handling is comprehensive, and no network calls leak into tests. The P1 finding (test not actually verifying source preference) is notable but the underlying logic is correct. The P2 findings are reasonable improvements for a follow-up pass.

---

## Codex CLI Review

**Model**: gpt-5.3-codex (OpenAI Codex v0.98.0)

### Findings

1. **MAJOR** `test_scrape_json_preferred_over_known_vessels` does not verify source precedence, only count.
   `tests/modules/vessel_fleet/test_collect_drilling_fleet.py:174`
   The assertion is `len(records) >= 31` while the comment says scrape and known both have 31. This passes whether `collect_operator_fleet()` returns scrape, known, or even duplicated data. Core behavior ("best source wins") is not actually tested.

2. **MAJOR** Core tie-break behavior in multi-source selection is untested.
   `scripts/vessel_fleet/collect_drilling_fleet.py:181`
   `max(candidates, key=len)` with insertion order makes ties resolve as `web > scrape_json > known_vessels`, but no test locks this in. A future refactor could silently change deterministic source choice without test failure.

3. **MINOR** Script behavior description mixes "fallback chain" with "most-records wins," which are different policies.
   `scripts/vessel_fleet/collect_drilling_fleet.py:4`, `scripts/vessel_fleet/collect_drilling_fleet.py:144`
   True fallback implies first successful source; current code evaluates all candidates and chooses largest. If this is intentional, wording should be explicit to avoid mis-implementation.

4. **MINOR** Error paths are partially covered, but key exception paths are not exercised.
   `tests/modules/vessel_fleet/test_collect_drilling_fleet.py:114`
   No test for parser exceptions in `_collect_from_scrape_json()` (`collect_drilling_fleet.py:132`), and no test for config-import failure behavior inside `collect_operator_fleet()` (`collect_drilling_fleet.py:152`).

**Verdict**: MAJOR

---

## Gemini CLI Review

**Model**: Gemini CLI

### Findings

- Fallback chain logic (web -> scrape JSON -> known_vessels, with max-records selection) is correctly implemented and thoroughly tested.
- Error handling in data collection functions is robust, logging issues and gracefully returning empty lists.
- Test coverage is excellent for critical functions, leveraging pytest fixtures and unittest.mock.patch effectively.
- Code quality, readability, type hinting, and modularity are strong.
- Consider adding tests for `main()` execution and a clearer web scrape success scenario for completeness, but this is not critical.

**Verdict**: APPROVE

---

## Summary

| Reviewer | Verdict |
|----------|---------|
| Claude (Opus 4.6) | MINOR |
| Codex CLI (gpt-5.3-codex) | MAJOR |
| Gemini CLI | APPROVE |

- **Reviewers**: 3
- **Verdicts**: 1 APPROVE, 1 MINOR, 1 MAJOR
- **Consensus**: The implementation logic is correct and functional. All three reviewers agree the fallback chain works and error handling is solid. The divergence is on test coverage: Codex rates MAJOR because `test_scrape_json_preferred_over_known_vessels` does not truly verify source preference (both sources return 31 records), and tie-break behavior is untested. Claude concurs on these findings as P1/P2 but rates MINOR since the underlying logic is correct. Gemini finds no issues.
- **Recommended action**: Add a targeted test that verifies source selection when sources return different record counts (e.g., mock scrape_json to return 5 records, known_vessels to return 2, assert known is not chosen). This would resolve the primary concern from both Claude and Codex reviews. Clarify "fallback chain" terminology in docstrings.
