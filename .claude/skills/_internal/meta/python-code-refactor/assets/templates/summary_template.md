# Refactoring Summary Report

**Generated**: {{timestamp}}
**Target Directory**: `{{target_directory}}`
**Refactoring Session**: {{session_id}}
**Duration**: {{duration}}

---

## Executive Summary

{{executive_summary}}

**Overall Result**: {{overall_result}}

---

## 1. Changes Made

### By Category

| Category | Files Modified | Changes Made | Auto-Applied | Manual Review Required |
|----------|---------------|--------------|--------------|----------------------|
| Code Smells | {{code_smells_files}} | {{code_smells_changes}} | {{code_smells_auto}} | {{code_smells_manual}} |
| Complexity Reduction | {{complexity_files}} | {{complexity_changes}} | {{complexity_auto}} | {{complexity_manual}} |
| Style Fixes | {{style_files}} | {{style_changes}} | {{style_auto}} | {{style_manual}} |
| Type Annotations | {{types_files}} | {{types_changes}} | {{types_auto}} | {{types_manual}} |
| Documentation | {{docs_files}} | {{docs_changes}} | {{docs_auto}} | {{docs_manual}} |
| **Total** | **{{total_files}}** | **{{total_changes}}** | **{{total_auto}}** | **{{total_manual}}** |

### Detailed Change Log

{{#each changes}}
#### {{this.file}}

**Changes Applied**:
{{#each this.changes}}
- Line {{this.line}}: {{this.description}} ({{this.category}})
{{/each}}

{{#if this.diff}}
```diff
{{this.diff}}
```
{{/if}}

---

{{/each}}

---

## 2. Before/After Metrics Comparison

### Overall Metrics

| Metric | Before | After | Change | Improvement |
|--------|--------|-------|--------|-------------|
| Total Lines of Code | {{loc_before}} | {{loc_after}} | {{loc_change}} | {{loc_improvement}} |
| Average Complexity | {{complexity_before}} | {{complexity_after}} | {{complexity_change}} | {{complexity_improvement}} |
| Max Complexity | {{max_complexity_before}} | {{max_complexity_after}} | {{max_complexity_change}} | {{max_complexity_improvement}} |
| Functions > 10 Complexity | {{high_complexity_before}} | {{high_complexity_after}} | {{high_complexity_change}} | {{high_complexity_improvement}} |
| Test Coverage | {{coverage_before}}% | {{coverage_after}}% | {{coverage_change}}% | {{coverage_improvement}} |
| Flake8 Issues | {{flake8_before}} | {{flake8_after}} | {{flake8_change}} | {{flake8_improvement}} |
| Type Coverage | {{type_coverage_before}}% | {{type_coverage_after}}% | {{type_coverage_change}}% | {{type_coverage_improvement}} |

### Per-File Comparison

| File | Complexity Before | Complexity After | Issues Before | Issues After | Status |
|------|-------------------|------------------|---------------|--------------|--------|
{{#each file_comparison}}
| `{{this.file}}` | {{this.complexity_before}} | {{this.complexity_after}} | {{this.issues_before}} | {{this.issues_after}} | {{this.status}} |
{{/each}}

### Complexity Improvement Chart

```
Before:  {{complexity_chart_before}}
After:   {{complexity_chart_after}}
         |----|----|----|----|----|----|----|----|----|----|
         0    2    4    6    8   10   12   14   16   18   20+
```

---

## 3. Flake8 Improvements

### Issue Resolution Summary

| Category | Before | After | Resolved | New | Net Change |
|----------|--------|-------|----------|-----|------------|
| E1xx (Indentation) | {{e1xx_before}} | {{e1xx_after}} | {{e1xx_resolved}} | {{e1xx_new}} | {{e1xx_net}} |
| E2xx (Whitespace) | {{e2xx_before}} | {{e2xx_after}} | {{e2xx_resolved}} | {{e2xx_new}} | {{e2xx_net}} |
| E3xx (Blank Lines) | {{e3xx_before}} | {{e3xx_after}} | {{e3xx_resolved}} | {{e3xx_new}} | {{e3xx_net}} |
| E4xx (Imports) | {{e4xx_before}} | {{e4xx_after}} | {{e4xx_resolved}} | {{e4xx_new}} | {{e4xx_net}} |
| E5xx (Line Length) | {{e5xx_before}} | {{e5xx_after}} | {{e5xx_resolved}} | {{e5xx_new}} | {{e5xx_net}} |
| E7xx (Statement) | {{e7xx_before}} | {{e7xx_after}} | {{e7xx_resolved}} | {{e7xx_new}} | {{e7xx_net}} |
| E9xx (Runtime) | {{e9xx_before}} | {{e9xx_after}} | {{e9xx_resolved}} | {{e9xx_new}} | {{e9xx_net}} |
| Fxxx (Pyflakes) | {{fxxx_before}} | {{fxxx_after}} | {{fxxx_resolved}} | {{fxxx_new}} | {{fxxx_net}} |
| C901 (Complexity) | {{c901_before}} | {{c901_after}} | {{c901_resolved}} | {{c901_new}} | {{c901_net}} |
| **Total** | **{{total_before}}** | **{{total_after}}** | **{{total_resolved}}** | **{{total_new}}** | **{{total_net}}** |

### Remaining Issues

{{#if remaining_issues}}
| File | Line | Code | Message | Priority |
|------|------|------|---------|----------|
{{#each remaining_issues}}
| `{{this.file}}` | {{this.line}} | {{this.code}} | {{this.message}} | {{this.priority}} |
{{/each}}
{{else}}
All Flake8 issues have been resolved.
{{/if}}

---

## 4. Performance Impact

### Benchmark Results

| Metric | Before | After | Change | Notes |
|--------|--------|-------|--------|-------|
| Import Time | {{import_time_before}}ms | {{import_time_after}}ms | {{import_time_change}} | {{import_time_notes}} |
| Function Call Overhead | {{call_overhead_before}}us | {{call_overhead_after}}us | {{call_overhead_change}} | {{call_overhead_notes}} |
| Memory Footprint | {{memory_before}}MB | {{memory_after}}MB | {{memory_change}} | {{memory_notes}} |

### Potential Performance Considerations

{{#if performance_considerations}}
{{#each performance_considerations}}
- **{{this.title}}**: {{this.description}}
  - Impact: {{this.impact}}
  - Recommendation: {{this.recommendation}}
{{/each}}
{{else}}
No significant performance concerns identified.
{{/if}}

---

## 5. Remaining Issues

### Issues Not Addressed (Require Manual Review)

{{#if remaining_manual}}
{{#each remaining_manual}}
#### {{this.title}}

**File**: `{{this.file}}`
**Type**: {{this.type}}
**Reason Not Auto-Fixed**: {{this.reason}}
**Recommended Action**: {{this.action}}

{{#if this.code_context}}
```python
{{this.code_context}}
```
{{/if}}

---

{{/each}}
{{else}}
All identified issues have been addressed.
{{/if}}

### Technical Debt Remaining

| Category | Count | Effort to Resolve | Priority |
|----------|-------|-------------------|----------|
{{#each technical_debt}}
| {{this.category}} | {{this.count}} | {{this.effort}} | {{this.priority}} |
{{/each}}

---

## 6. Human Review Flags

### Critical Items Requiring Human Verification

{{#if critical_review}}
{{#each critical_review}}
**[{{this.severity}}]** `{{this.file}}:{{this.line}}`

{{this.description}}

**Reason for Flag**: {{this.reason}}
**Suggested Review Focus**: {{this.focus}}

{{#if this.code}}
```python
{{this.code}}
```
{{/if}}

---

{{/each}}
{{else}}
No critical items flagged for human review.
{{/if}}

### Behavioral Changes Warning

{{#if behavioral_changes}}
The following changes may affect runtime behavior:

{{#each behavioral_changes}}
- `{{this.file}}`: {{this.description}} - **{{this.risk_level}} risk**
{{/each}}

**Recommendation**: Run full test suite and perform manual testing of affected functionality.
{{else}}
No behavioral changes detected. All refactoring should be semantically equivalent.
{{/if}}

### Test Coverage for Changed Code

| Changed File | Lines Changed | Lines Covered | Coverage % | Status |
|--------------|--------------|---------------|------------|--------|
{{#each changed_coverage}}
| `{{this.file}}` | {{this.changed}} | {{this.covered}} | {{this.percentage}}% | {{this.status}} |
{{/each}}

---

## 7. Next Steps

### Immediate Actions Required

{{#each immediate_next}}
{{this.index}}. **{{this.title}}**
   - {{this.description}}
   - Estimated effort: {{this.effort}}
{{/each}}

### Recommended Follow-up Tasks

{{#each followup_tasks}}
- [ ] {{this.task}} ({{this.priority}} priority)
{{/each}}

### Commands to Run

```bash
# Verify all tests pass
{{test_command}}

# Check remaining linting issues
{{lint_command}}

# Verify type checking
{{type_check_command}}

# Generate updated coverage report
{{coverage_command}}
```

---

## Appendix A: Files Modified

{{#each modified_files}}
- `{{this.path}}` ({{this.changes}} changes)
{{/each}}

## Appendix B: Git Diff Summary

```
{{git_diff_stat}}
```

## Appendix C: Session Metadata

| Property | Value |
|----------|-------|
| Session ID | {{session_id}} |
| Start Time | {{start_time}} |
| End Time | {{end_time}} |
| Duration | {{duration}} |
| Agent Version | {{agent_version}} |
| Tools Used | {{tools_used}} |
| Auto-Fix Enabled | {{auto_fix_enabled}} |
| Dry Run Mode | {{dry_run_mode}} |

---

*Report generated by python-code-refactor skill*
*Review all flagged items before merging changes*
