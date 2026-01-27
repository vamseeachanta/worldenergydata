# Flake8 Analysis Report

**Generated**: {{timestamp}}
**Target Directory**: `{{target_directory}}`
**Flake8 Version**: {{flake8_version}}
**Configuration**: {{configuration_source}}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Files Analyzed | {{total_files}} |
| Total Issues Found | {{total_issues}} |
| Critical Issues (E9xx, F8xx) | {{critical_issues}} |
| Style Issues (E1xx-E5xx) | {{style_issues}} |
| Complexity Issues (C901) | {{complexity_issues}} |
| Files with No Issues | {{clean_files}} |
| Clean File Percentage | {{clean_percentage}}% |

**Overall Status**: {{overall_status}}

---

## 1. Issue Counts by Category

### Error Categories

| Code | Category | Count | Severity | Description |
|------|----------|-------|----------|-------------|
| E1xx | Indentation | {{e1xx_count}} | Style | Incorrect indentation levels |
| E2xx | Whitespace | {{e2xx_count}} | Style | Whitespace issues (trailing, missing) |
| E3xx | Blank Lines | {{e3xx_count}} | Style | Incorrect blank line counts |
| E4xx | Import | {{e4xx_count}} | Style | Import ordering and formatting |
| E5xx | Line Length | {{e5xx_count}} | Style | Lines exceeding max length |
| E7xx | Statement | {{e7xx_count}} | Logic | Statement-level issues |
| E9xx | Runtime | {{e9xx_count}} | **Error** | Syntax errors, indentation errors |
| W | Warnings | {{w_count}} | Warning | PEP8 warnings |

### Pyflakes Categories

| Code | Category | Count | Severity | Description |
|------|----------|-------|----------|-------------|
| F401 | Unused Import | {{f401_count}} | Warning | Module imported but unused |
| F402 | Import Shadowed | {{f402_count}} | Warning | Import shadowed by loop variable |
| F403 | Star Import | {{f403_count}} | Warning | Unable to detect undefined names |
| F405 | Name from Star | {{f405_count}} | Warning | Name may be undefined from star import |
| F811 | Redefinition | {{f811_count}} | **Error** | Redefinition of unused name |
| F821 | Undefined Name | {{f821_count}} | **Error** | Undefined name used |
| F822 | Undefined Export | {{f822_count}} | **Error** | Undefined name in __all__ |
| F823 | Local Variable | {{f823_count}} | **Error** | Local variable referenced before assignment |
| F841 | Unused Variable | {{f841_count}} | Warning | Local variable assigned but never used |
| F901 | Raise NotImplemented | {{f901_count}} | **Error** | Using `raise NotImplemented` instead of `raise NotImplementedError` |

### McCabe Complexity

| Code | Category | Count | Threshold | Description |
|------|----------|-------|-----------|-------------|
| C901 | High Complexity | {{c901_count}} | 10 | Function cyclomatic complexity too high |

### Summary by Severity

| Severity | Count | Percentage | Action Required |
|----------|-------|------------|-----------------|
| **Critical (Error)** | {{severity_critical}} | {{severity_critical_pct}}% | Immediate fix required |
| **High (Logic)** | {{severity_high}} | {{severity_high_pct}}% | Fix before merge |
| **Medium (Warning)** | {{severity_medium}} | {{severity_medium_pct}}% | Should fix |
| **Low (Style)** | {{severity_low}} | {{severity_low_pct}}% | Nice to fix |

---

## 2. Issue Counts by File

### All Files Summary

| File | Total | Critical | High | Medium | Low | Status |
|------|-------|----------|------|--------|-----|--------|
{{#each files_summary}}
| `{{this.file}}` | {{this.total}} | {{this.critical}} | {{this.high}} | {{this.medium}} | {{this.low}} | {{this.status}} |
{{/each}}

### Distribution Chart

```
Issues per File Distribution:

0 issues:     {{dist_0}} files  {{dist_0_bar}}
1-5 issues:   {{dist_1_5}} files  {{dist_1_5_bar}}
6-10 issues:  {{dist_6_10}} files  {{dist_6_10_bar}}
11-20 issues: {{dist_11_20}} files  {{dist_11_20_bar}}
21+ issues:   {{dist_21_plus}} files  {{dist_21_plus_bar}}
```

---

## 3. Top 10 Most Problematic Files

These files require the most attention and should be prioritized for refactoring:

| Rank | File | Total Issues | Top Issue Type | Complexity Score | Recommendation |
|------|------|--------------|----------------|------------------|----------------|
{{#each top_problematic}}
| {{this.rank}} | `{{this.file}}` | {{this.total}} | {{this.top_issue}} ({{this.top_issue_count}}) | {{this.complexity}} | {{this.recommendation}} |
{{/each}}

### Analysis of Top Problematic Files

{{#each top_problematic_analysis}}
#### {{this.rank}}. `{{this.file}}`

**Total Issues**: {{this.total_issues}}
**Primary Problems**:
{{#each this.problems}}
- {{this.category}}: {{this.count}} issues
{{/each}}

**Root Cause Analysis**: {{this.root_cause}}

**Recommended Actions**:
{{#each this.actions}}
{{this.index}}. {{this.action}}
{{/each}}

---

{{/each}}

---

## 4. Detailed Issue List

### Critical Issues (Must Fix Immediately)

{{#if critical_list}}
{{#each critical_list}}
#### `{{this.file}}:{{this.line}}:{{this.col}}`

**Code**: {{this.code}}
**Message**: {{this.message}}
**Context**:
```python
{{this.context}}
```
**Fix**: {{this.suggested_fix}}

---

{{/each}}
{{else}}
No critical issues found.
{{/if}}

### High Priority Issues

{{#if high_list}}
| File | Line | Code | Message |
|------|------|------|---------|
{{#each high_list}}
| `{{this.file}}` | {{this.line}} | {{this.code}} | {{this.message}} |
{{/each}}
{{else}}
No high priority issues found.
{{/if}}

### Medium Priority Issues

{{#if medium_list}}
| File | Line | Code | Message |
|------|------|------|---------|
{{#each medium_list}}
| `{{this.file}}` | {{this.line}} | {{this.code}} | {{this.message}} |
{{/each}}
{{else}}
No medium priority issues found.
{{/if}}

### Low Priority Issues (Style)

{{#if low_list}}
<details>
<summary>Click to expand {{low_list_count}} style issues</summary>

| File | Line | Code | Message |
|------|------|------|---------|
{{#each low_list}}
| `{{this.file}}` | {{this.line}} | {{this.code}} | {{this.message}} |
{{/each}}

</details>
{{else}}
No low priority issues found.
{{/if}}

---

## 5. Recommendations

### Quick Wins (Auto-Fixable)

These issues can be automatically fixed by running:

```bash
# Fix with Ruff (recommended)
uv run ruff check --fix {{target_directory}}
uv run ruff format {{target_directory}}

# Or with autopep8
uv run autopep8 --in-place --recursive {{target_directory}}
```

**Auto-fixable issues**:
- E1xx: Indentation ({{e1xx_autofixable}} of {{e1xx_count}})
- E2xx: Whitespace ({{e2xx_autofixable}} of {{e2xx_count}})
- E3xx: Blank lines ({{e3xx_autofixable}} of {{e3xx_count}})
- E5xx: Line length (partial - {{e5xx_autofixable}} of {{e5xx_count}})
- F401: Unused imports ({{f401_autofixable}} of {{f401_count}})
- W: Warnings ({{w_autofixable}} of {{w_count}})

**Total auto-fixable**: {{total_autofixable}} of {{total_issues}} ({{autofixable_percentage}}%)

### Manual Review Required

These issues require human judgment:

{{#each manual_review}}
- **{{this.code}}**: {{this.description}} ({{this.count}} instances)
  - Example: `{{this.example_file}}:{{this.example_line}}`
  - Guidance: {{this.guidance}}
{{/each}}

### Code Quality Improvements

{{#each quality_improvements}}
{{this.index}}. **{{this.title}}**
   - Affected files: {{this.file_count}}
   - Effort: {{this.effort}}
   - Impact: {{this.impact}}
   - Details: {{this.details}}
{{/each}}

### Configuration Recommendations

Based on this analysis, consider updating your Flake8/Ruff configuration:

```toml
# Recommended additions to pyproject.toml
[tool.ruff.lint]
# Rules that had many violations - consider if these match your style guide
ignore = [
{{#each config_ignore_suggestions}}
    "{{this.code}}",  # {{this.reason}} ({{this.count}} current violations)
{{/each}}
]

# Per-file ignores for specific patterns
[tool.ruff.lint.per-file-ignores]
{{#each per_file_ignores}}
"{{this.pattern}}" = [{{this.codes}}]  # {{this.reason}}
{{/each}}
```

---

## 6. Trend Analysis

{{#if has_history}}
### Historical Comparison

| Date | Total Issues | Critical | New Issues | Resolved |
|------|-------------|----------|------------|----------|
{{#each history}}
| {{this.date}} | {{this.total}} | {{this.critical}} | {{this.new}} | {{this.resolved}} |
{{/each}}

### Trend Chart

```
Issues Over Time:
{{trend_chart}}
```
{{else}}
No historical data available. Run this report regularly to track progress.
{{/if}}

---

## Appendix A: Full Issue List

<details>
<summary>Click to expand complete issue list ({{total_issues}} items)</summary>

```
{{full_issue_list}}
```

</details>

## Appendix B: Configuration Used

```ini
{{flake8_config}}
```

## Appendix C: Code Reference

| Code | Full Name | Documentation |
|------|-----------|---------------|
| E1xx | Indentation | [PEP8 - Indentation](https://pep8.org/#indentation) |
| E2xx | Whitespace | [PEP8 - Whitespace](https://pep8.org/#whitespace-in-expressions-and-statements) |
| E3xx | Blank Lines | [PEP8 - Blank Lines](https://pep8.org/#blank-lines) |
| E4xx | Import | [PEP8 - Imports](https://pep8.org/#imports) |
| E5xx | Line Length | [PEP8 - Maximum Line Length](https://pep8.org/#maximum-line-length) |
| E7xx | Statement | [PEP8 - Programming Recommendations](https://pep8.org/#programming-recommendations) |
| E9xx | Runtime | Syntax and runtime errors |
| F4xx | Import | [Pyflakes - Imports](https://github.com/PyCQA/pyflakes) |
| F8xx | Name | [Pyflakes - Names](https://github.com/PyCQA/pyflakes) |
| C901 | Complexity | [McCabe Complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity) |

---

*Report generated by python-code-refactor skill*
*Run `uv run ruff check --fix` to auto-fix many of these issues*
