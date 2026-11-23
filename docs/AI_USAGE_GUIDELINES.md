# AI Usage Guidelines for Repository Work

> **Applicable to**: worldenergydata and all workspace-hub repositories
>
> Version: 1.0.0
> Last Updated: 2025-10-23
> Status: Living Document (continuously updated)

## Overview

This document captures learnings and best practices for using AI tools (especially Claude) when working with this repository. It's organized by effectiveness, from best to worst approaches, based on real-world experience.

---

## ⭐ Best Practices (Highly Recommended)

### 1. Running Script with AI-Prepared Input File + AI-Provided Command

**Rating:** ⭐⭐⭐⭐⭐ **EVEN BETTER** (Highest effectiveness)

**What it is:**
- AI agent prepares the input YAML configuration file
- AI agent provides the exact bash command to execute
- User runs the provided command with the prepared input file

**Why it works best:**
- Complete workflow automation without manual intervention
- AI handles both configuration complexity AND execution syntax
- Reduces human error in both file preparation and command construction
- Follows SPARC methodology (Specification → Configuration → Execution)
- Reproducible and auditable (input file + command are version controlled)

**Example:**

```bash
# AI prepares: config/input/lower_tertiary.yaml
# AI provides this command:
./scripts/bsee/run_lower_tertiary_analysis.sh reports/lower_tertiary

# User just copies and runs the command
# Results: Perfect execution with comprehensive output
```

**When to use:**
- Complex analysis workflows with many parameters
- Economic modeling (NPV analysis, production forecasting)
- Multi-source data integration
- Any task requiring both configuration and execution

**Best with:**
- Claude (excellent at understanding context and generating precise commands)
- BSEE analysis scripts
- Marine safety analysis
- Any module with YAML configuration support

---

### 2. Git Operations with AI (Especially Claude)

**Rating:** ⭐⭐⭐⭐⭐ **GOOD** (Highly effective)

**What it is:**
- Using AI (particularly Claude) to perform git operations
- Branch management, commits, pull requests, merges
- Git workflow orchestration

**Why it works:**
- Claude understands git context extremely well
- Generates proper commit messages following conventions
- Handles complex merge scenarios
- Maintains clean git history

**Example:**

```bash
# Ask Claude to:
# 1. Create feature branch
# 2. Commit changes with meaningful message
# 3. Push to remote
# 4. Create pull request

# Claude executes:
git checkout -b feature/marine-safety-analysis
git add scripts/marine_safety/ config/input/marine_safety.yaml
git commit -m "Add comprehensive marine safety incident analysis

- Multi-source data integration (USCG, NOAA, MAIB, TSB)
- 6 scenario-specific analyses (foundering, collision, etc.)
- Interactive Plotly visualizations
- Bash execution framework"

git push -u origin feature/marine-safety-analysis
gh pr create --title "Marine Safety Analysis Framework" --body "..."
```

**When to use:**
- Feature branch workflows
- Complex commit scenarios
- Pull request creation
- Repository synchronization
- Merge conflict resolution

**Best with:**
- Claude Code (native git integration)
- Multi-file changes
- Workflow automation
- Repository management tasks

---

### 3. Running Script with Input File

**Rating:** ⭐⭐⭐⭐ **GOOD** (Very effective)

**What it is:**
- Running bash scripts with YAML configuration files as input
- User prepares input file (or AI prepares it)
- User manually constructs and runs the command

**Why it works:**
- Separates configuration from execution
- Version-controllable input parameters
- Reproducible analysis workflows
- Clear audit trail

**Example:**

```bash
# Input file: config/input/bsee_all_wells.yaml
# User runs:
./scripts/bsee/run_all_wells_analysis.sh reports/all_wells

# Or with Python directly:
python scripts/analyze_production_by_lease.py \
    --config config/input/bsee_all_wells.yaml \
    --output reports/production_analysis \
    --format html \
    --interactive
```

**When to use:**
- Standardized analysis workflows
- Repeatable processing tasks
- When input parameters need version control
- Production-grade analysis runs

**Best with:**
- BSEE production analysis
- Lower Tertiary NPV calculations
- Marine safety scenarios
- Any modular analysis workflow

---

### 4. Preparing Input Files

**Rating:** ⭐⭐⭐⭐ **GOOD** (Very effective)

**What it is:**
- Using AI to generate YAML configuration files
- Following SPARC workflow templates
- Structured input for bash execution

**Why it works:**
- AI understands YAML structure and validation
- Follows established templates and patterns
- Reduces configuration errors
- Enables complex parameter specification

**Example:**

```yaml
# AI generates: config/input/lower_tertiary.yaml

metadata:
  feature_name: "lower-tertiary-field-analysis"
  created: "2025-10-22"
  status: "production"

requirements:
  functional:
    - requirement: "Calculate NPV with configurable discount rates"
      priority: "high"
      implemented: true

processing:
  steps:
    - name: "calculate_npv"
      module: "analysis.economics"
      function: "calculate_npv"
      params:
        discount_rate: 0.10
        oil_price: 75.0
        gas_price: 3.50

fields:
  Anchor:
    capex_million: 5500
    first_production: "2024-08-01"
    peak_rate_bopd: 75000
```

**When to use:**
- New analysis workflows
- Complex configuration requirements
- Parameter-heavy operations
- Economic modeling setup

**Best with:**
- Claude (excellent YAML generation)
- Template-based configurations
- Multi-parameter scenarios

---

## ⚠️ Use With Caution

### 5. Running a Script (Standalone)

**Rating:** ⭐⭐⭐ **OK BUT...** (Limited effectiveness)

**What it is:**
- Running bash scripts without input files
- Hardcoded parameters or defaults
- Direct script execution

**Why it's limited:**
- Less reproducible (parameters not version controlled)
- Harder to modify parameters
- Limited audit trail
- Difficult to share exact configuration

**Example:**

```bash
# Just running the script
./scripts/run_all_analyses.sh

# Works, but:
# - Uses default parameters
# - No customization without editing script
# - Hard to reproduce exact conditions
```

**When acceptable:**
- Quick exploratory analysis
- Testing script functionality
- Default parameter runs
- One-off executions

**Better alternative:**
- Prepare input file first
- Use script + input file approach
- Version control your configuration

---

## ❌ Avoid These Approaches

### 6. Running LLM Descriptions

**Rating:** ⭐ **PRETTY BAD SIDE** (Least effective)

**What it is:**
- Asking AI to describe what a script does
- Using AI to explain code instead of running it
- Theoretical analysis instead of practical execution

**Why it fails:**
- No actual results produced
- Theoretical understanding ≠ working implementation
- Wastes time on description instead of action
- Doesn't advance the actual work

**Example of what NOT to do:**

```
❌ BAD: "Can you describe what analyze_lower_tertiary_npv.py does?"
    Result: Long description, no actionable output

✅ GOOD: "Prepare input file for lower tertiary NPV analysis and
          provide the command to run it"
    Result: Working configuration + executable command + actual results
```

**Why to avoid:**
- Doesn't produce tangible results
- Time spent on explanation, not execution
- Creates false sense of progress
- Better to just run the code with proper inputs

**Better alternative:**
- Prepare input file + run script
- Let results speak for themselves
- Review actual output instead of descriptions

---

## 🎯 Workflow Recommendations

### Recommended Workflow Pattern

```
1. ⭐⭐⭐⭐⭐ AI prepares input YAML file
   └─ Following template in templates/input_config.yaml
   └─ Validated against schema
   └─ Version controlled in config/input/

2. ⭐⭐⭐⭐⭐ AI provides exact bash command
   └─ Points to correct script in scripts/
   └─ References prepared input file
   └─ Includes all necessary flags

3. ⭐⭐⭐⭐⭐ User executes command
   └─ Copy/paste provided command
   └─ Review output and results
   └─ Version control any changes

4. ⭐⭐⭐⭐⭐ Use Claude for git operations
   └─ Commit results
   └─ Create meaningful commit messages
   └─ Manage branches and PRs
```

### Anti-Pattern to Avoid

```
❌ DON'T:
1. Ask AI to describe what script does
2. Manually construct complex commands
3. Run scripts without input files
4. Skip version control of configurations
```

---

## 📊 Effectiveness Matrix

| Approach | Rating | Time Saved | Error Rate | Reproducibility | Recommended? |
|----------|--------|------------|------------|----------------|--------------|
| Script + AI Input + AI Command | ⭐⭐⭐⭐⭐ | 90% | Very Low | Excellent | ✅ **YES** |
| Git Operations (Claude) | ⭐⭐⭐⭐⭐ | 80% | Very Low | Excellent | ✅ **YES** |
| Script + Input File | ⭐⭐⭐⭐ | 70% | Low | Very Good | ✅ **YES** |
| Preparing Input Files | ⭐⭐⭐⭐ | 75% | Low | Very Good | ✅ **YES** |
| Script Only (no input) | ⭐⭐⭐ | 40% | Medium | Poor | ⚠️ **SOMETIMES** |
| LLM Descriptions | ⭐ | -20% | N/A | None | ❌ **NO** |

---

## 🔄 Application Across Repositories

### This Pattern Applies To:

1. **worldenergydata** (this repository)
   - BSEE production analysis
   - Lower Tertiary NPV calculations
   - Marine safety incident analysis
   - All modular analysis workflows

2. **All workspace-hub repositories**
   - Any repository with scripts/ directory
   - Any YAML-based configuration system
   - Any analysis or data processing workflows
   - Git operations across all repos

3. **Future repositories**
   - Establish scripts/ + config/input/ structure
   - Create YAML templates
   - Build bash execution framework
   - Follow same best practices

### Universal Principles:

1. **Configuration as Code**: Always use input files over hardcoded parameters
2. **AI-Assisted Execution**: Let AI prepare both input and commands
3. **Git Integration**: Use Claude for git operations
4. **Version Control**: Track inputs, outputs, and configurations
5. **Avoid Descriptions**: Execute, don't describe

---

## 📝 Examples by Module

### BSEE Analysis

```bash
# ⭐⭐⭐⭐⭐ BEST: AI prepares config + provides command
# AI creates: config/input/lower_tertiary_custom.yaml
# AI provides:
./scripts/bsee/run_lower_tertiary_analysis.sh reports/custom_npv

# ⭐⭐⭐⭐ GOOD: User prepares config, runs with input
./scripts/bsee/run_all_wells_analysis.sh reports/all_wells

# ⭐⭐⭐ OK: Run with defaults
./scripts/bsee/run_lower_tertiary_analysis.sh

# ❌ BAD: Ask AI to describe what the script does
"What does run_lower_tertiary_analysis.sh do?"
```

### Marine Safety Analysis

```bash
# ⭐⭐⭐⭐⭐ BEST: Complete AI-assisted workflow
# AI creates: config/input/marine_safety_custom.yaml
# AI provides:
./scripts/marine_safety/run_all_incident_analysis.sh \
    reports/custom_analysis \
    config/input/marine_safety_custom.yaml

# ⭐⭐⭐⭐ GOOD: Standard execution with input
./scripts/marine_safety/run_all_incident_analysis.sh reports/marine_safety

# ❌ BAD: Theoretical discussion instead of execution
"Can you explain the marine safety analysis workflow?"
```

### Git Operations

```bash
# ⭐⭐⭐⭐⭐ BEST: Claude handles everything
# Claude executes:
git checkout -b feature/new-analysis
git add scripts/ config/ docs/
git commit -m "Add new analysis module with YAML config"
git push -u origin feature/new-analysis
gh pr create --title "New Analysis Module"

# ⭐⭐⭐ OK: Manual git operations
# User manually types each command
# More error-prone, slower
```

---

## 🔄 Future Updates

This document will be continuously updated with:
- New effectiveness ratings as we gain experience
- Additional workflow patterns
- Tool-specific best practices
- Cross-repository learnings
- Community contributions

### Update Process:

1. Test new AI approach in real workflow
2. Evaluate effectiveness (time, errors, reproducibility)
3. Add to this document with rating
4. Share across workspace-hub repositories
5. Incorporate feedback and refinements

---

## 💡 Key Takeaways

1. **Best Approach**: AI prepares input file + provides command to run
2. **Git Operations**: Always use Claude (especially Claude Code)
3. **Input Files**: Essential for reproducibility and version control
4. **Avoid Descriptions**: Execute code, don't describe it
5. **Version Control**: Track configurations, not just code
6. **Consistency**: Apply these patterns across all repositories

---

## 📞 Questions or Suggestions?

This is a living document. As we discover new patterns or refine existing ones:
- Update this file with new learnings
- Share insights across workspace-hub repositories
- Document what works (and what doesn't)
- Keep rating system current

**Remember**: The goal is to maximize effectiveness while minimizing errors and time spent. Always prefer execution over description, and let AI handle the complex configuration and command construction.

---

**Last Updated**: 2025-10-23
**Next Review**: As new patterns emerge
**Status**: Active and continuously evolving
