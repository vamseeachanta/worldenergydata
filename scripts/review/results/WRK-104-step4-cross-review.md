# WRK-104 Step 4 Cross-Review: Scrape Parser

Date: 2026-02-13

## Files Reviewed

| File | Lines | Description |
|------|-------|-------------|
| `src/worldenergydata/vessel_fleet/collectors/scrape_parser.py` | 345 | Noble + Seadrill scrape JSON parser |
| `tests/modules/vessel_fleet/collectors/test_scrape_parser.py` | 300 | 47 tests across 6 test classes |
| `scripts/vessel_fleet/collect_from_scrape.py` | 98 | Collection script saving to Parquet |

---

## Claude Review

### Overall Assessment

The implementation is well-structured, readable, and pragmatic. At 345 lines, the parser stays well within the 400-line file limit. The code follows clear separation of concerns: utility functions (`classify_rig_type_by_water_depth`, `parse_water_depth_string`), contractor-specific parsers (Noble, Seadrill), and a collection script. The 4-tier PDF link matching strategy for Noble is a thoughtful approach to handling real-world naming inconsistencies between URL slugs and page text.

### Findings

#### P1 - Seadrill positional PDF matching drifts on duplicate rig names (MAJOR)

**File**: `scrape_parser.py:317-328`

```python
for idx, match in enumerate(_SEADRILL_RIG_PATTERN.finditer(raw_html)):
    name = match.group("name").strip()
    if name in seen_names:
        continue
    seen_names.add(name)
    ...
    tech_url = tech_sheet_urls[idx] if idx < len(tech_sheet_urls) else None
```

When a duplicate rig name is encountered, the regex match `idx` increments (from `enumerate`) but the duplicate is skipped. The next unique rig then uses a shifted `idx` that points to the wrong Technical Sheet URL. For current data (17 unique names, no duplicates), this works. But it is a latent correctness bug -- if Seadrill's page ever lists a rig twice (e.g., in two locations), subsequent rigs silently get the wrong PDF.

**Fix**: Maintain a separate counter for matched records, or pop URLs from the list sequentially regardless of deduplication:

```python
url_idx = 0
for match in _SEADRILL_RIG_PATTERN.finditer(raw_html):
    name = match.group("name").strip()
    tech_url = tech_sheet_urls[url_idx] if url_idx < len(tech_sheet_urls) else None
    url_idx += 1
    if name in seen_names:
        continue
    seen_names.add(name)
    ...
```

#### P2 - Noble regex availability capture is restrictive (MINOR)

**File**: `scrape_parser.py:74`

```python
r"Available:\s*(?P<avail>[^\s]+(?:\s+[^\s]+)?)\s+"
```

This pattern captures at most two whitespace-separated tokens (e.g., "Jun 2026"). If Noble changes the format to multi-word availability like "Mid 2026 onwards" or "Q3 2025 - Available", the entire rig entry regex fails to match, silently dropping the rig from results. This is fragile for production use.

**Fix**: Use a more permissive capture that stops at the known trailer:

```python
r"Available:\s*(?P<avail>.+?)\s+Download Summary PDF"
```

And remove the separate `Download Summary PDF` trailer match.

#### P3 - Noble regex water depth accepts only `ft`, but utility handles `feet`/`ft.` (MINOR)

**File**: `scrape_parser.py:73` vs `scrape_parser.py:51`

The regex on line 73 only matches `{digits} ft Water Depth`:
```python
r"(?P<wd>[\d,]+)\s*ft\s+Water Depth\s*"
```

But `parse_water_depth_string()` (line 51) explicitly handles `feet` and `ft.` suffixes. If Noble's page ever uses "12,000 feet Water Depth" or "12,000 ft. Water Depth", the regex silently skips the rig. This inconsistency between the regex and the utility function creates confusion about what formats are actually supported.

**Fix**: Widen the regex to `r"(?P<wd>[\d,]+)\s*(?:ft\.?|feet)\s+Water Depth\s*"` to match what the utility function accepts.

#### P4 - Seadrill `.pdf` suffix check is case-sensitive (MINOR)

**File**: `scrape_parser.py:275`

```python
and link.get("href", "").endswith(".pdf")
```

URLs ending in `.PDF` or `.Pdf` would be rejected. Also, URLs with query parameters like `.pdf?download=1` would not match. Current data is all lowercase `.pdf` so this works today, but it is fragile.

**Fix**: Use `.lower().endswith(".pdf")` or check with `".pdf" in href.lower()`.

#### P5 - `_normalize_noble_name()` is a no-op beyond `.strip()` (MINOR)

**File**: `scrape_parser.py:111-117`

```python
def _normalize_noble_name(raw_name: str) -> str:
    return raw_name.strip()
```

The docstring describes handling "variations" but the function only strips whitespace. This is not a bug, but it is misleading. Either add actual normalization (e.g., collapsing internal whitespace) or simplify to inline `.strip()` and remove the function.

#### P6 - No unit tests for `_match_pdf_link()` fallback tiers (MINOR)

**File**: `test_scrape_parser.py`

The 4-tier PDF matching strategy (`_match_pdf_link`) is the most complex logic in the module, handling direct match, case-insensitive, prefix-stripped, partial, and filename-based matching. Yet there are zero targeted unit tests for this function. The integration tests with real data happen to exercise some paths (all 31 Noble rigs match), but if Noble renames a rig, there is no test coverage for the fallback tiers.

**Fix**: Add a `TestMatchPdfLink` class with synthetic `pdf_links` dicts exercising each tier independently.

#### P7 - No unit tests for `_extract_noble_pdf_links()` or `_extract_seadrill_tech_sheet_links()` (MINOR)

These helper functions are tested only indirectly via the integration tests. A synthetic test with crafted `links` arrays would confirm the alternating Rig Summary / Download Summary PDF pattern extraction works correctly and catches regressions.

#### P8 - Collection script lacks error handling (MINOR)

**File**: `collect_from_scrape.py:44-65`

`main()` calls `parse_noble_scrape()` and `parse_seadrill_scrape()` without try/except. If one contractor's JSON is missing or malformed, the entire script aborts. For a batch collection script, it would be better to catch per-contractor errors, log them, and continue to the next contractor.

#### P9 - Known limitation: water-depth-based rig type classification (Acknowledged)

The docstring and task description both acknowledge that classifying rig type by water depth alone can misclassify units. Noble Courage (10,000 ft) is classified as drillship but is actually a semi. This is acceptable for an initial implementation where no explicit type labels are available from Noble's page, but should be tracked for correction when better data arrives.

### Strengths

- Clean code organization with well-named functions and clear docstrings
- Proper deduplication via `seen_names` sets
- `parse_water_depth_string()` is robust, handling commas, units, whitespace, and non-numeric input
- Seadrill type normalization via explicit mapping (`_SEADRILL_TYPE_MAP`) with a sensible fallback
- Tests validate against real scraped data (31 Noble, 17 Seadrill) confirming production correctness
- Edge case tests cover empty JSON, missing files, and negative/zero water depths
- Collection script includes a summary with rig type breakdown and PDF link counts

**Verdict**: MINOR

Rationale: The P1 finding (Seadrill positional PDF drift on duplicates) is a correctness bug that could silently produce wrong data, but it does not affect current production data (no duplicates exist). All other findings are defensive improvements. The code works correctly for its current input set and is well-tested against real data. Recommend fixing P1 and P2 before the next data refresh.

---

## Codex CLI Review

**Model**: gpt-5.3-codex (OpenAI Codex v0.98.0)

Codex performed direct code inspection and runtime validation against real JSON data, confirming:
- Noble: 31 regex matches, 31 unique, 31 PDF links matched (0 missing)
- Seadrill: 17 regex matches, 17 unique, 17 tech sheet URLs matched (0 missing)
- Reproduced the P1 bug with synthetic duplicate input (second unique rig mapped to third URL)

### Findings

1. **MAJOR** -- Incorrect Seadrill PDF assignment when duplicate rig names appear. Line 317 uses `enumerate(finditer(...))` but duplicates are skipped at line 319, while URL mapping at line 328 still uses the unmodified `idx`. Reproduced with synthetic input: second unique rig mapped to third URL.

2. **MINOR** -- Noble regex availability capture (`line 74`) limits to at most two tokens. Multi-word values like "Mid 2026 onwards" cause the entire rig match to fail. Also, line 73 only accepts `ft` while `parse_water_depth_string` (line 51) supports `feet`/`ft.`.

3. **MINOR** -- Seadrill PDF link extraction (`line 274-275`) requires exact text "Technical Sheet" and lowercase `.pdf` suffix. URLs with `.PDF` or query parameters would be missed.

4. **MINOR** -- No targeted unit tests for: duplicate-name index shift behavior, regex variant handling, or link-matching fallback tiers.

**Verdict**: MAJOR

---

## Gemini CLI Review

**Model**: Gemini CLI (Google)

Note: Gemini was unable to read the files from the correct path (looked for `worldenergydata/vessel_fleet/` instead of `src/worldenergydata/vessel_fleet/`), so it reviewed based on the piped content.

### Findings

Gemini assessed the regex patterns as "well-constructed, leveraging non-greedy matching and named capture groups effectively." It found:

- Classification logic correctly implements water depth thresholds covering all defined ranges and boundaries
- Noble PDF link matching demonstrates a "sophisticated approach" with multiple fallback strategies
- Seadrill positional matching is "suitable given the expected consistency" of the data
- Test suite provides "excellent coverage" including boundary conditions, edge cases, and integration tests against real data

No specific issues raised.

**Verdict**: APPROVE

---

## Summary

| Reviewer | Verdict | Findings |
|----------|---------|----------|
| Claude (Opus 4.6) | MINOR | 9 findings (1x P1 latent correctness, 2x P2 regex fragility, 6x P3 minor) |
| Codex CLI (gpt-5.3-codex) | MAJOR | 4 findings (1x MAJOR duplicate-name PDF shift, 3x MINOR) |
| Gemini CLI | APPROVE | No issues raised |

**Reviewers**: 3
**Verdicts**: 1 APPROVE, 1 MINOR, 1 MAJOR

### Consensus

Two of three reviewers independently identified the same Seadrill positional PDF matching bug (P1), confirming it as a real correctness concern. Codex rated it MAJOR; Claude rated the overall review as MINOR because the bug is latent (no duplicates in current data). The regex fragility findings (Noble availability pattern, `ft` vs `feet`) were also independently identified by both Claude and Codex.

### Recommended Actions (Priority Order)

1. **Fix P1**: Seadrill PDF positional matching -- decouple `enumerate` index from URL index to handle duplicates correctly
2. **Fix P2**: Widen Noble availability regex to stop at trailer instead of limiting to two tokens
3. **Fix P3**: Align Noble regex water depth unit matching with `parse_water_depth_string()` supported formats
4. **Add tests**: Unit tests for `_match_pdf_link()` fallback tiers and `_extract_*` helpers with synthetic data
5. **Harden**: Case-insensitive `.pdf` check for Seadrill tech sheets
