# Python & Data Science Developer Spec Priority Guide

> **Purpose:** Guide Python programmers and Data Science practitioners in selecting appropriate specs from the WorldEnergyData repository based on their skill level and learning objectives.
> 
> **Last Updated:** 2025-09-02
> **Target Audience:** Python Developers, Data Scientists, Data Analysts
> **Note:** This guide prioritizes specs that require strong programming skills but minimal domain expertise

## Overview

This guide maps available specifications in the WorldEnergyData repository to Python and Data Science skills, providing a prioritized learning path for developers. Each spec is evaluated based on **technical complexity** rather than **domain knowledge**, making them suitable for developers who are strong in programming but may lack deep petroleum engineering expertise.

## Important Consideration: Domain Knowledge vs Technical Skills

**Your Situation:** Strong Python/Data Science skills but limited petroleum domain knowledge
**Strategy:** Focus on specs that are:
- Infrastructure and tooling focused
- Data pipeline and integration oriented  
- Dashboard and visualization heavy
- System architecture based
- Testing and validation focused

**Avoid Initially:** Specs requiring deep understanding of:
- Petroleum engineering equations
- Production decline theories
- Economic evaluation models
- Geological interpretations

## Skill Assessment Criteria

Specs are evaluated based on their reinforcement of:
- **Core Python:** Clean coding, OOP, module design
- **Data Wrangling:** Pandas, NumPy, data cleaning
- **Statistical Analysis:** Regression, optimization, forecasting
- **Visualization:** Matplotlib, Plotly, dashboard creation
- **SQL & Databases:** Query optimization, schema design
- **API Integration:** REST APIs, data pipelines
- **Testing & Validation:** Unit tests, data quality checks
- **Documentation:** Technical writing, code comments

## 📊 REVISED HIGH PRIORITY SPECS
*Minimal domain knowledge required - Pure technical implementation*

### 1. SODIR Integration (`sodir-integration`) ⭐⭐⭐⭐⭐ - COMPLETED 

**Status:** 37/37 tasks completed  
**Module:** `specs/modules/data-sources/sodir-integration/`

**Why This Is Perfect For You:**
- **API integration** - Pure technical work
- **Data pipeline development** - No need to understand what the data means
- **ETL processes** - Focus on moving and transforming data
- **Your lead can define business rules**

**Skills Reinforced:**
- REST API integration
- Data pipeline architecture
- Error handling & retry logic
- YAML configuration
- Data normalization patterns

**Domain Knowledge Required:** MINIMAL - You're just moving data from A to B

---

### 2. Well Data Verification (`verification`) ⭐⭐⭐⭐ - COMPLETED

**Status:** 0/X tasks completed  
**Module:** `specs/modules/analysis/verification/`

**Why This Is Perfect For You:**
- **Data validation** - Universal programming concept
- **Quality checks** - Your lead defines rules, you implement
- **Testing patterns** - Standard software engineering
- **Exception handling** - Core programming skill

**Skills Reinforced:**
- Data validation frameworks
- Automated testing
- Exception handling
- Data integrity checks

**Domain Knowledge Required:** LOW - Focus on validation logic, not what data means

---

### 3. Well Data Dashboard (`dashboard`) ⭐⭐⭐⭐ - COMPLETED

**Status:** 0/X tasks completed  
**Module:** `specs/modules/analysis/dashboard/`

**Why This Is Perfect For You:**
- **Dashboard building** - Pure UI/UX work
- **Data visualization** - Frontend development
- **User interface** - Standard web development
- **Monitoring systems** - Technical implementation

**Skills Reinforced:**
- Dashboard development
- Frontend frameworks
- Data visualization
- User experience design

**Domain Knowledge Required:** LOW - Focus on UI/UX, not domain specifics

## 🔧 MEDIUM PRIORITY SPECS
*Good technical work but may need occasional domain input*

### 4. Infrastructure Documentation (`docs-organization`) ⭐⭐⭐

**Status:** 41/41 tasks completed (but could be enhanced)  
**Module:** `specs/modules/infrastructure/docs-organization/`

**Why This Works:**
- **Documentation systems** - Technical writing
- **Organization patterns** - Information architecture
- **Automation opportunities** - Build doc generation tools

**Skills Reinforced:**
- Documentation frameworks
- Automation scripting
- Information architecture
- CI/CD for docs

**Domain Knowledge Required:** LOW - Organizing information, not creating it

## 🌐 CROSS-REPOSITORY OPPORTUNITIES
*Expand your technical skills with specs from related repositories*

### From DigitalModel Repository
**Repository:** https://github.com/vamseeachanta/digitalmodel

#### 1. MathCAD to Python PSF Conversion ⭐⭐⭐⭐⭐ - COMPLETED
**Module:** `specs/modules/marine-engineering/mathcad-to-python-psf`
**Why Perfect for You:**
- Pure Python conversion work
- Mathematical operations with NumPy/SciPy
- Code modernization focus
- Algorithm implementation (formulas provided by experts)

#### 2. Test Suite Automation ⭐⭐⭐⭐⭐
**Module:** `specs/modules/test-suite-automation/`
**Why Perfect for You:**
- pytest infrastructure development
- CI/CD pipeline automation
- Coverage reporting systems
- Pure software engineering

### From AssetUtilities Repository
**Repository:** https://github.com/vamseeachanta/assetutilities

#### 1. Agent OS Infrastructure ⭐⭐⭐⭐
**Module:** `specs/modules/agent-os/`
**Why Perfect for You:**
- System architecture design
- Agent coordination patterns
- CLI tool development
- Pure software architecture

## 📉 AVOID THESE SPECS (FOR NOW)
*Require deep petroleum engineering knowledge*

### Domain-Heavy Specs to Skip:
- **Decline Curve Analysis** - Requires understanding Arps equations, production decline theory
- **Directional Surveys** - Requires knowledge of wellbore trajectories, drilling engineering

**Strategy:** Let your lead handle these or pair-program where they provide domain context and you implement

## 🎯 EXPANDED Learning Path (Cross-Repository Technical Focus)

### Phase 1: Pure Infrastructure & Architecture (Weeks 1-4)
**Focus: System Design & Architecture**
1. **AssetUtilities:** `agent-os` - Command systems
2. **DigitalModel:** `development-tools` - Developer productivity
   - Pure Python architecture
   - No domain knowledge needed
   - Build confidence with system design

### Phase 2: Testing & Automation (Weeks 5-8)
**Focus: Quality & Automation**
1. **DigitalModel:** `test-suite-automation` - Testing infrastructure
2. **DigitalModel:** `development-tools` - Developer productivity
   - CI/CD pipelines
   - Testing frameworks
   - Automation tools

### Phase 3: Data Integration & Processing (Weeks 9-12)
**Focus: Data Pipelines & APIs**
1. **WorldEnergyData:** `sodir-integration` - API integration
2. **DigitalModel:** `mathcad-to-python-psf` - Engineering calculations port
   - API integration
   - Data pipelines
   - ETL processes
   - Engineering calculations

### Phase 4: Dashboards & Validation (Weeks 13-16)
**Focus: User Interfaces & Data Quality**
1. **WorldEnergyData:** `well-data-verification-dashboard`
2. **WorldEnergyData:** `docs-organization` - Documentation systems
   - Data validation (lead provides rules)
   - Dashboard development
   - Quality monitoring

### Phase 5: Domain Bridge (Weeks 17-20)
**Focus: Gradual Domain Integration**
- Start with pair programming on domain-heavy specs
- Lead explains concepts, you implement
- Focus on implementation excellence

## 💡 Success Tips

### For Each Spec:
1. **Read the full spec first** - Understand the business context
2. **Review existing code** - Learn from patterns in the repo
3. **Start with tests** - Follow TDD practices
4. **Document as you go** - Update task_summary.md
5. **Seek feedback early** - Don't wait until completion

### General Best Practices:
- **Use the existing environment:** Always use `uv` and the repo's virtual environment
- **Follow standards:** Adhere to `.agent-os/standards/`
- **Leverage agents:** Use specialized agents when available
- **Parallel processing:** Implement concurrent operations where possible
- **Clean commits:** Make atomic, well-described commits


## 📚 Additional Resources

### Repository Documentation
- `.agent-os/standards/` - Coding standards and best practices
- `.agent-os/product/` - Product context and architecture
- `specs/modules/` - All available specifications

### Cross-Repository Resources
- **DigitalModel:** Engineering simulations, signal processing, automation
- **AssetUtilities:** Utility functions, authentication, parallel processing
- **WorldEnergyData:** Energy data analysis, dashboards, integrations

### Key Technologies to Master
- **Python:** Advanced pandas, NumPy, scipy
- **Visualization:** Plotly, Dash, matplotlib
- **Databases:** PostgreSQL, SQL optimization
- **APIs:** REST, authentication, rate limiting
- **Testing:** pytest, mock, fixtures
- **DevOps:** Git, GitHub Actions, Docker
- **Mathematical Computing:** NumPy, SciPy, SymPy for engineering calculations

## 🎯 Revised Skills Matrix (Domain Knowledge Required)

### WorldEnergyData Repository
| Spec | Python Skills | Domain Knowledge | Suitable for You | Collaboration Strategy |
|------|--------------|------------------|------------------|----------------------|
| sodir-integration | ⭐⭐⭐⭐ | ⭐ | ✅ PERFECT | Solo work |
| well-data-verification | ⭐⭐⭐⭐ | ⭐⭐ | ✅ GOOD | Lead defines rules |
| docs-organization | ⭐⭐⭐ | ⭐ | ✅ GOOD | Solo work |
| decline-curve-analysis | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ AVOID | Lead handles |

### DigitalModel Repository
| Spec | Python Skills | Domain Knowledge | Suitable for You | Collaboration Strategy |
|------|--------------|------------------|------------------|----------------------|
| mathcad-to-python-psf | ⭐⭐⭐⭐⭐ | ⭐⭐ | ✅ PERFECT | Lead provides formulas |
| test-suite-automation | ⭐⭐⭐⭐ | ⭐ | ✅ PERFECT | Solo work |
| development-tools | ⭐⭐⭐ | ⭐ | ✅ PERFECT | Solo work |
| orcaflex | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ AVOID | Requires engineering expertise |
| marine-engineering | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ AVOID | Requires naval architecture knowledge |

### AssetUtilities Repository
| Spec | Python Skills | Domain Knowledge | Suitable for You | Collaboration Strategy |
|------|--------------|------------------|------------------|----------------------|
| agent-os | ⭐⭐⭐⭐ | ⭐ | ✅ PERFECT | Solo work |

## 🚀 Getting Started with Minimal Domain Knowledge

### Your Action Plan:
1. **Start with `sodir-integration`** - Pure API integration work
2. **Communicate with your lead** about domain requirements upfront
3. **Focus on implementation excellence** rather than domain understanding
4. **Ask for domain context** when you hit blockers, not before

### Collaboration Template with Lead:
```
"I'm working on [SPEC NAME]. 
I need you to provide:
1. Business rules/formulas
2. Expected outputs
3. Edge cases to handle
I'll handle all the technical implementation."
```

### Key Success Factors:
- **You bring:** Strong Python, clean code, testing, architecture
- **Lead brings:** Domain knowledge, formulas, business logic
- **Together:** Complete, well-engineered solutions

## 📋 Quick Reference: Cross-Repository Work

### Repository Cloning Commands
```bash
# Clone all repositories for comprehensive work
git clone https://github.com/vamseeachanta/worldenergydata.git
git clone https://github.com/vamseeachanta/digitalmodel.git
git clone https://github.com/vamseeachanta/assetutilities.git
```

### Priority Order for Python/Data Developers
1. **Immediate Start (No Domain Knowledge):**
   - WorldEnergyData: `sodir-integration`
   - DigitalModel: `test-suite-automation`
   - AssetUtilities: `agent-os`

2. **Next Wave (Minimal Domain Knowledge):**
   - WorldEnergyData: `well-data-verification-dashboard`
   - DigitalModel: `mathcad-to-python-psf`

3. **Advanced (Some Domain Context Helpful):**
   - WorldEnergyData: `docs-organization`
   - DigitalModel: `development-tools`

### Specs to AVOID (Heavy Domain Knowledge Required):
- ❌ DigitalModel: `orcaflex`, `marine-engineering`, `orcawave`
- ❌ WorldEnergyData: `decline-curve-analysis`, `directional-surveys`
- ❌ AssetUtilities: `naval-arch-qms-ai-transformation`

---

*Remember: You don't need to be a petroleum/marine engineer to write great engineering software. Focus on what you do best - clean, efficient, well-tested code. The domain experts will provide the formulas and business logic.*