# CRITICAL: Spec Naming Rules for WorldEnergyData

## MANDATORY RULES - NEVER FORGET:

### 1. MODULE-BASED ORGANIZATION
**ALWAYS** use module-based folder structure:
```
specs/modules/[module-name]/[spec-name]/
```

### 2. NO DATES IN FOLDER NAMES
**NEVER** include dates in spec folder names:
- ❌ WRONG: `specs/modules/bsee/2025-08-21-consolidation/`
- ✅ CORRECT: `specs/modules/bsee/consolidation/`

### 3. CORRECT STRUCTURE EXAMPLE
```
specs/
└── modules/
    ├── bsee/
    │   ├── consolidation/
    │   │   ├── spec.md
    │   │   ├── tasks.md
    │   │   └── sub-specs/
    │   └── another-spec/
    ├── financial/
    │   └── npv-analysis/
    └── testing/
        └── comprehensive-test-plan/
```

### 4. WHY THIS MATTERS
- Module organization keeps related specs together
- No dates in folders prevents chronological confusion
- Clean, logical structure for long-term maintenance
- Easier to find and reference specs

## ENFORCEMENT
This rule OVERRIDES any default Agent OS behavior that includes dates in spec folder names.

**CHECK BEFORE CREATING ANY SPEC:**
1. Am I using module-based organization?
2. Did I remove any dates from the folder name?
3. Is the spec in the correct module directory?

---
*This is a MANDATORY instruction with HIGHEST PRIORITY*