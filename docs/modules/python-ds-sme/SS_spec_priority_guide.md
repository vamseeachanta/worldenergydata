# Python & Data Science Developer Spec Priority Guide

> **Purpose:** Guide Python programmers and Data Science practitioners in selecting appropriate specs from the WorldEnergyData repository based on their skill level and learning objectives.
> 
> **Last Updated:** 2025-09-01
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

### 1. Sub-Agents System (`sub-agents-system`) ⭐⭐⭐⭐⭐

**Status:** 0/59 tasks completed  
**Module:** `specs/modules/infrastructure/sub-agents-system/`

**Why This Is Perfect For You:**
- **Pure Python architecture** - No petroleum knowledge needed
- **System design focus** - Leverage your programming skills
- **AI/ML integration** - Modern tech stack you can relate to
- **Your lead can provide domain context when needed**

**Skills Reinforced:**
- Object-oriented design patterns
- Module architecture & interfaces
- Agent-based systems
- Performance monitoring
- Clean code organization

**Domain Knowledge Required:** MINIMAL - It's all about system design

---

### 2. SODIR Integration (`sodir-integration`) ⭐⭐⭐⭐⭐

**Status:** 0/37 tasks completed  
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

### 3. Well Data Verification Dashboard (`well-data-verification-dashboard`) ⭐⭐⭐⭐

**Status:** 0/115 tasks completed  
**Module:** `specs/modules/analysis/well-data-verification-dashboard/`

**Why This Is Perfect For You:**
- **Data validation** - Universal programming concept
- **Dashboard building** - Pure UI/UX work
- **Quality checks** - Your lead defines rules, you implement
- **Testing patterns** - Standard software engineering

**Skills Reinforced:**
- Data validation frameworks
- Dashboard development
- Automated testing
- Exception handling
- Monitoring systems

**Domain Knowledge Required:** LOW - Focus on validation logic, not what data means

## 🔧 MEDIUM PRIORITY SPECS
*Good technical work but may need occasional domain input*

### 4. Trunk-Based Development Workflow (`trunk-based-development-workflow`) ⭐⭐⭐⭐

**Status:** 0/35 tasks completed  
**Module:** `specs/modules/infrastructure/trunk-based-development-workflow/`

**Why This Works For You:**
- **Pure DevOps** - No domain knowledge needed
- **Git workflows** - Universal software engineering
- **CI/CD setup** - Technical infrastructure work

**Skills Reinforced:**
- Git best practices
- GitHub Actions automation
- Testing pipelines
- Code review processes

**Domain Knowledge Required:** NONE - Pure software engineering

---

### 5. DCA Interactive Dashboard (`dca-interactive-dashboard`) ⭐⭐⭐

**Status:** 0/49 tasks completed  
**Module:** `specs/modules/analysis/dca-interactive-dashboard/`

**Why This Could Work:**
- **Frontend heavy** - Focus on UI/UX, not equations
- **Plotly Dash** - Technical framework implementation
- **Your lead provides formulas** - You just implement them
- **Interactive controls** - Pure programming work

**Skills Reinforced:**
- Dashboard development (Plotly Dash)
- Real-time interactivity
- Web app development
- Responsive design

**Domain Knowledge Required:** MEDIUM - Need to understand what users want to see, but not the math behind it

---

### 6. Infrastructure Documentation (`docs-organization`) ⭐⭐⭐

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

## 📉 AVOID THESE SPECS (FOR NOW)
*Require deep petroleum engineering knowledge*

### Domain-Heavy Specs to Skip:
- **Decline Curve Analysis** - Requires understanding Arps equations, production decline theory
- **Directional Surveys** - Requires knowledge of wellbore trajectories, drilling engineering

**Strategy:** Let your lead handle these or pair-program where they provide domain context and you implement

## 🎯 REVISED Learning Path (Technical Focus)

### Phase 1: Pure Infrastructure (Weeks 1-4)
1. **Start with `sub-agents-system`**
   - Pure Python architecture
   - No domain knowledge needed
   - Build confidence with system design

### Phase 2: DevOps Foundation (Weeks 5-8)
2. **Add `trunk-based-development-workflow`**
   - Git workflows
   - CI/CD pipelines
   - Team collaboration tools

### Phase 3: Data Integration (Weeks 9-12)
3. **Master `sodir-integration`**
   - API integration
   - Data pipelines
   - ETL processes

### Phase 4: Validation Systems (Weeks 13-16)
4. **Build `well-data-verification-dashboard`**
   - Data validation (lead provides rules)
   - Dashboard development
   - Quality monitoring

### Phase 5: Collaborative Work (Weeks 17-20)
5. **Pair on `dca-interactive-dashboard`**
   - Lead provides equations
   - You build the UI
   - Learn domain gradually

### Phase 6: Domain Bridge (Weeks 21-24)
6. **Gradually take on domain specs**
   - Start with pair programming
   - Lead explains concepts
   - You implement solutions

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

### Key Technologies to Master
- **Python:** Advanced pandas, NumPy, scipy
- **Visualization:** Plotly, Dash, matplotlib
- **Databases:** PostgreSQL, SQL optimization
- **APIs:** REST, authentication, rate limiting
- **Testing:** pytest, mock, fixtures
- **DevOps:** Git, GitHub Actions, Docker

## 🎯 Revised Skills Matrix (Domain Knowledge Required)

| Spec | Python Skills | Domain Knowledge | Suitable for You | Collaboration Strategy |
|------|--------------|------------------|------------------|----------------------|
| sub-agents-system | ⭐⭐⭐⭐⭐ | ⭐ | ✅ PERFECT | Solo work |
| sodir-integration | ⭐⭐⭐⭐ | ⭐ | ✅ PERFECT | Solo work |
| trunk-based-development | ⭐⭐⭐ | None | ✅ PERFECT | Solo work |
| well-data-verification | ⭐⭐⭐⭐ | ⭐⭐ | ✅ GOOD | Lead defines rules |
| dca-interactive-dashboard | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⚠️ MAYBE | Lead provides formulas |
| docs-organization | ⭐⭐⭐ | ⭐ | ✅ GOOD | Solo work |
| decline-curve-analysis | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ AVOID | Lead handles |

## 🚀 Getting Started with Minimal Domain Knowledge

### Your Action Plan:
1. **Start with `sub-agents-system`** - Pure technical architecture work
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

---

*Remember: You don't need to be a petroleum engineer to write great petroleum software. Focus on what you do best - clean, efficient, well-tested code.*