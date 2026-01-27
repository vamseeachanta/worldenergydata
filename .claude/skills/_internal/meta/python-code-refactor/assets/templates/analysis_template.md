# Python Codebase Analysis Report

**Generated**: {{timestamp}}
**Target Directory**: `{{target_directory}}`
**Analysis Tool**: python-code-refactor v1.0

---

## Executive Summary

{{executive_summary}}

---

## 1. Codebase Overview

### File Statistics

| Metric | Count |
|--------|-------|
| Python Files | {{python_files_count}} |
| Total Lines of Code | {{total_loc}} |
| Total Functions | {{total_functions}} |
| Total Classes | {{total_classes}} |
| Total Methods | {{total_methods}} |
| Average Lines per File | {{avg_lines_per_file}} |
| Average Functions per File | {{avg_functions_per_file}} |

### File Breakdown

| File | Lines | Functions | Classes | Complexity Score |
|------|-------|-----------|---------|------------------|
{{#each files}}
| `{{this.path}}` | {{this.lines}} | {{this.functions}} | {{this.classes}} | {{this.complexity}} |
{{/each}}

---

## 2. Anti-Patterns Detected

### Priority: Critical (Must Fix)

{{#if critical_antipatterns}}
{{#each critical_antipatterns}}
#### {{this.name}}

**Location**: `{{this.file}}:{{this.line}}`
**Description**: {{this.description}}
**Impact**: {{this.impact}}
**Recommendation**: {{this.recommendation}}

```python
# Current (problematic)
{{this.current_code}}

# Suggested fix
{{this.suggested_fix}}
```

---

{{/each}}
{{else}}
No critical anti-patterns detected.
{{/if}}

### Priority: High

{{#if high_antipatterns}}
{{#each high_antipatterns}}
#### {{this.name}}

**Location**: `{{this.file}}:{{this.line}}`
**Description**: {{this.description}}
**Recommendation**: {{this.recommendation}}

---

{{/each}}
{{else}}
No high-priority anti-patterns detected.
{{/if}}

### Priority: Medium

{{#if medium_antipatterns}}
{{#each medium_antipatterns}}
- **{{this.name}}** at `{{this.file}}:{{this.line}}` - {{this.description}}
{{/each}}
{{else}}
No medium-priority anti-patterns detected.
{{/if}}

### Priority: Low

{{#if low_antipatterns}}
{{#each low_antipatterns}}
- **{{this.name}}** at `{{this.file}}:{{this.line}}` - {{this.description}}
{{/each}}
{{else}}
No low-priority anti-patterns detected.
{{/if}}

### Anti-Pattern Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Code Smells | {{code_smells_critical}} | {{code_smells_high}} | {{code_smells_medium}} | {{code_smells_low}} | {{code_smells_total}} |
| Complexity Issues | {{complexity_critical}} | {{complexity_high}} | {{complexity_medium}} | {{complexity_low}} | {{complexity_total}} |
| Style Violations | {{style_critical}} | {{style_high}} | {{style_medium}} | {{style_low}} | {{style_total}} |
| Security Concerns | {{security_critical}} | {{security_high}} | {{security_medium}} | {{security_low}} | {{security_total}} |

---

## 3. Complexity Metrics

### Cyclomatic Complexity by File

| File | Avg Complexity | Max Complexity | Functions > 10 | Status |
|------|----------------|----------------|----------------|--------|
{{#each complexity_by_file}}
| `{{this.file}}` | {{this.avg}} | {{this.max}} | {{this.high_count}} | {{this.status}} |
{{/each}}

### Cognitive Complexity Analysis

| File | Function | Cognitive Complexity | Threshold | Status |
|------|----------|---------------------|-----------|--------|
{{#each cognitive_complexity}}
| `{{this.file}}` | `{{this.function}}` | {{this.score}} | 15 | {{this.status}} |
{{/each}}

### Top 10 Most Complex Functions

| Rank | Function | File | Cyclomatic | Cognitive | Recommendation |
|------|----------|------|------------|-----------|----------------|
{{#each top_complex_functions}}
| {{this.rank}} | `{{this.function}}` | `{{this.file}}` | {{this.cyclomatic}} | {{this.cognitive}} | {{this.recommendation}} |
{{/each}}

---

## 4. Flake8 Issues

### Summary by Category

| Category | Code Range | Count | Severity |
|----------|------------|-------|----------|
| Indentation | E1xx | {{e1xx_count}} | Style |
| Whitespace | E2xx | {{e2xx_count}} | Style |
| Blank Lines | E3xx | {{e3xx_count}} | Style |
| Imports | E4xx | {{e4xx_count}} | Style |
| Line Length | E5xx | {{e5xx_count}} | Style |
| Statement | E7xx | {{e7xx_count}} | Logic |
| Runtime | E9xx | {{e9xx_count}} | Error |
| Pyflakes | F4xx-F9xx | {{fxxx_count}} | Error |
| McCabe Complexity | C901 | {{c901_count}} | Complexity |

### Issues by File (Top 10)

| File | Total Issues | Critical | Style | Complexity |
|------|--------------|----------|-------|------------|
{{#each flake8_by_file}}
| `{{this.file}}` | {{this.total}} | {{this.critical}} | {{this.style}} | {{this.complexity}} |
{{/each}}

### Detailed Issue List

{{#each flake8_issues}}
- `{{this.file}}:{{this.line}}:{{this.col}}` - **{{this.code}}**: {{this.message}}
{{/each}}

---

## 5. Test Coverage Analysis

### Current Coverage State

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Overall Coverage | {{overall_coverage}}% | 80% | {{coverage_status}} |
| Branch Coverage | {{branch_coverage}}% | 75% | {{branch_status}} |
| Covered Lines | {{covered_lines}} | - | - |
| Missing Lines | {{missing_lines}} | - | - |

### Coverage by Module

| Module | Statements | Covered | Missing | Coverage % |
|--------|------------|---------|---------|------------|
{{#each coverage_by_module}}
| `{{this.module}}` | {{this.statements}} | {{this.covered}} | {{this.missing}} | {{this.percentage}}% |
{{/each}}

### Uncovered Critical Paths

{{#if uncovered_paths}}
{{#each uncovered_paths}}
- `{{this.file}}:{{this.lines}}` - {{this.description}}
{{/each}}
{{else}}
No critical uncovered paths identified.
{{/if}}

---

## 6. OOP Assessment

### Class Quality Metrics

| Class | File | Methods | Attributes | Cohesion | Coupling | Issues |
|-------|------|---------|------------|----------|----------|--------|
{{#each class_metrics}}
| `{{this.name}}` | `{{this.file}}` | {{this.methods}} | {{this.attributes}} | {{this.cohesion}} | {{this.coupling}} | {{this.issues}} |
{{/each}}

### SOLID Principles Violations

{{#if solid_violations}}
{{#each solid_violations}}
#### {{this.principle}} Violation

**Class**: `{{this.class}}`
**File**: `{{this.file}}`
**Issue**: {{this.issue}}
**Recommendation**: {{this.recommendation}}

---

{{/each}}
{{else}}
No significant SOLID principle violations detected.
{{/if}}

### Inheritance Analysis

| Base Class | Derived Classes | Depth | Issues |
|------------|-----------------|-------|--------|
{{#each inheritance}}
| `{{this.base}}` | {{this.derived_count}} | {{this.depth}} | {{this.issues}} |
{{/each}}

---

## 7. Recommendations (Prioritized)

### Immediate Actions (Sprint 1)

{{#each immediate_actions}}
{{this.index}}. **{{this.title}}**
   - Files: {{this.files}}
   - Effort: {{this.effort}}
   - Impact: {{this.impact}}
   - Details: {{this.details}}

{{/each}}

### Short-Term Actions (Sprint 2-3)

{{#each shortterm_actions}}
{{this.index}}. **{{this.title}}**
   - Files: {{this.files}}
   - Effort: {{this.effort}}
   - Impact: {{this.impact}}

{{/each}}

### Long-Term Improvements (Backlog)

{{#each longterm_actions}}
- {{this.title}} ({{this.effort}} effort)
{{/each}}

---

## 8. Risk Assessment

### High-Risk Files (Require Manual Review)

{{#if high_risk_files}}
| File | Risk Score | Reasons | Recommended Action |
|------|------------|---------|-------------------|
{{#each high_risk_files}}
| `{{this.file}}` | {{this.score}}/10 | {{this.reasons}} | {{this.action}} |
{{/each}}
{{else}}
No high-risk files identified.
{{/if}}

### Dependency Analysis

{{#if dependency_issues}}
{{#each dependency_issues}}
- **{{this.type}}**: {{this.description}} ({{this.files}})
{{/each}}
{{else}}
No circular dependencies or coupling issues detected.
{{/if}}

---

## Appendix A: Tool Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Ruff | {{ruff_version}} | Linting and formatting |
| Complexipy | {{complexipy_version}} | Cognitive complexity |
| Pytest | {{pytest_version}} | Testing |
| Coverage | {{coverage_version}} | Code coverage |
| MyPy | {{mypy_version}} | Type checking |

---

## Appendix B: Configuration Used

```toml
{{configuration_toml}}
```

---

*Report generated by python-code-refactor skill*
*Human review recommended for all critical and high-priority items*
