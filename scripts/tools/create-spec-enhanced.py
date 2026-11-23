#!/usr/bin/env python3
"""
Enhanced /create-spec command for WorldEnergyData with advanced features.
Includes prompt summaries, executive summaries, and mermaid diagrams.
"""

import sys
import os
from datetime import datetime
from pathlib import Path

def create_enhanced_spec_directory(spec_name, module_name=None):
    """Create enhanced specification directory structure."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    if module_name:
        # Module-based organization
        specs_base = Path(".agent-os/specs/modules")
        module_dir = specs_base / module_name
        module_dir.mkdir(parents=True, exist_ok=True)
        spec_folder_name = f"{today}-{spec_name}"
        spec_path = module_dir / spec_folder_name
    else:
        # Traditional organization
        specs_dir = Path(".agent-os/specs")
        specs_dir.mkdir(parents=True, exist_ok=True)
        spec_folder_name = f"{today}-{spec_name}"
        spec_path = specs_dir / spec_folder_name
    
    spec_path.mkdir(exist_ok=True)
    
    # Create enhanced sub-directories
    (spec_path / "sub-specs").mkdir(exist_ok=True)
    (spec_path / "diagrams").mkdir(exist_ok=True)
    (spec_path / "summaries").mkdir(exist_ok=True)
    
    return spec_path

def create_enhanced_spec_file(spec_path, spec_name, variant="enhanced"):
    """Create enhanced spec.md file with all advanced features."""
    
    if variant == "enhanced":
        spec_content = f"""# Spec Requirements Document

> Spec: {spec_name}
> Created: {datetime.now().strftime("%Y-%m-%d")}
> Status: Planning
> Variant: Enhanced
> Repository: WorldEnergyData

## Executive Summary

### Business Impact
[High-level business value and strategic alignment]

### Key Deliverables
- [Primary deliverable with business value]
- [Secondary deliverable with user impact]
- [Technical deliverable with system improvement]

### Success Metrics
- [Quantifiable success measure]
- [User adoption target]
- [Performance improvement goal]

## Overview

[Comprehensive description of what this spec accomplishes in the context of energy data analysis]

## User Stories

### Energy Data Analyst Workflow
As an energy data analyst, I want to [specific functionality], so that I can [business value/time savings].

**Acceptance Criteria:**
- [ ] [Specific testable condition]
- [ ] [User interface requirement]
- [ ] [Performance requirement]

### Research Professional Workflow
As a research professional, I want to [specific functionality], so that I can [research capability/insight generation].

**Acceptance Criteria:**
- [ ] [Data quality requirement]
- [ ] [Analysis capability requirement]
- [ ] [Export/sharing requirement]

## Technical Architecture

### System Design
[High-level architecture description with component interactions]

### Data Flow
```mermaid
graph TD
    A[Data Source] --> B[Processing Engine]
    B --> C[Analysis Module]
    C --> D[Visualization Layer]
    D --> E[Export Interface]
```

### Integration Points
- **BSEE Data Integration:** [Specific integration requirements]
- **Economic Analysis:** [NPV calculation integration]
- **Visualization:** [matplotlib/plotly integration]

## Spec Scope

### Phase 1: Core Implementation
1. **[Feature Name]** - [Implementation details and acceptance criteria]
2. **[Feature Name]** - [Implementation details and acceptance criteria]

### Phase 2: Enhanced Features
1. **[Advanced Feature]** - [Enhanced capability description]
2. **[Integration Feature]** - [Cross-system integration details]

## Out of Scope

- [Explicitly excluded functionality with rationale]
- [Future considerations for next iteration]

## Expected Deliverable

### Technical Deliverables
1. [Specific code module or function with test coverage]
2. [Documentation updates with examples]
3. [Performance benchmarks and optimization]

### User Deliverables
1. [User-facing feature with usage examples]
2. [Updated user documentation and tutorials]
3. [Migration guide if applicable]

## Risk Assessment

### Technical Risks
- **[Risk Category]:** [Description and mitigation strategy]
- **[Risk Category]:** [Description and mitigation strategy]

### Business Risks
- **[Risk Category]:** [Impact and contingency plan]

## Dependencies

### Internal Dependencies
- [Existing WorldEnergyData components required]
- [Agent OS framework components needed]

### External Dependencies
- [Third-party libraries or APIs required]
- [Data source availability requirements]

## Testing Strategy

### Unit Testing
- [Specific test requirements for core functions]
- [Data validation test requirements]

### Integration Testing
- [End-to-end workflow testing requirements]
- [Performance testing requirements]

### User Acceptance Testing
- [User scenario testing requirements]
- [Documentation and tutorial validation]

## Documentation

### Code Documentation
- [API documentation requirements]
- [Inline documentation standards]

### User Documentation
- [Tutorial creation requirements]
- [Example notebooks and use cases]

### Technical Documentation
- [Architecture documentation updates]
- [Integration guide updates]

## Spec Documentation

- **Tasks:** @{spec_path.name}/tasks.md
- **Technical Specification:** @{spec_path.name}/sub-specs/technical-spec.md
- **API Specification:** @{spec_path.name}/sub-specs/api-spec.md
- **Tests Specification:** @{spec_path.name}/sub-specs/tests.md
- **Executive Summary:** @{spec_path.name}/summaries/executive-summary.md
- **System Architecture:** @{spec_path.name}/diagrams/architecture.mmd
"""
    elif variant == "research":
        spec_content = f"""# Research Specification Document

> Spec: {spec_name}
> Created: {datetime.now().strftime("%Y-%m-%d")}
> Status: Research Planning
> Variant: Research-Focused
> Repository: WorldEnergyData

## Research Objective

[Clear statement of research question or hypothesis to be addressed]

## Background & Literature Review

### Current State of Knowledge
[Summary of existing research and industry practices]

### Knowledge Gaps
[Specific gaps this research will address]

### Research Questions
1. [Primary research question]
2. [Secondary research questions]

## Methodology

### Data Sources
- [Primary data sources and access methods]
- [Secondary data sources for validation]

### Analysis Approach
- [Statistical methods to be employed]
- [Modeling techniques and rationale]

### Validation Strategy
- [How results will be validated]
- [Peer review and reproducibility measures]

## Expected Outcomes

### Research Deliverables
1. [Research findings and insights]
2. [Methodology documentation]
3. [Reproducible analysis notebooks]

### Industry Applications
- [How findings can be applied in practice]
- [Potential impact on energy industry decisions]

## Timeline & Milestones

### Phase 1: Data Collection & Preparation (Weeks 1-2)
- [ ] [Specific milestone]
- [ ] [Specific milestone]

### Phase 2: Analysis & Modeling (Weeks 3-4)
- [ ] [Specific milestone]
- [ ] [Specific milestone]

### Phase 3: Validation & Documentation (Weeks 5-6)
- [ ] [Specific milestone]
- [ ] [Specific milestone]
"""
    else:  # minimal variant
        spec_content = f"""# {spec_name.replace('-', ' ').title()} Specification

> Created: {datetime.now().strftime("%Y-%m-%d")}
> Repository: WorldEnergyData

## Goal
[One sentence describing what this spec achieves]

## User Story
As a [user type], I want [functionality] so that [benefit].

## Requirements
- [ ] [Core requirement]
- [ ] [Core requirement]
- [ ] [Core requirement]

## Tasks
- [ ] [Implementation task]
- [ ] [Testing task]
- [ ] [Documentation task]

## Definition of Done
- [ ] Code implemented and tested
- [ ] Documentation updated
- [ ] All tests passing
"""
    
    with open(spec_path / "spec.md", "w") as f:
        f.write(spec_content)

def create_enhanced_tasks_file(spec_path, spec_name):
    """Create enhanced tasks.md with detailed breakdown."""
    tasks_content = f"""# Spec Tasks - {spec_name}

> Created: {datetime.now().strftime("%Y-%m-%d")}
> Status: Ready for Implementation
> Repository: WorldEnergyData

## Task Summary

**Total Estimated Effort:** [X weeks]
**Priority:** High/Medium/Low
**Dependencies:** [List any dependencies]

## Phase 1: Foundation & Core Implementation

- [ ] **1. Project Setup & Configuration** `M`
  - [ ] 1.1 Create module structure following WorldEnergyData conventions
  - [ ] 1.2 Set up testing infrastructure with pytest
  - [ ] 1.3 Configure UV dependencies in pyproject.toml
  - [ ] 1.4 Initialize documentation structure
  - [ ] 1.5 Verify all foundation tests pass

- [ ] **2. Core Data Processing** `L`
  - [ ] 2.1 Write unit tests for data ingestion functions
  - [ ] 2.2 Implement data loading and validation logic
  - [ ] 2.3 Add data transformation and cleaning functions
  - [ ] 2.4 Implement error handling and logging
  - [ ] 2.5 Verify all core processing tests pass

## Phase 2: Analysis & Integration

- [ ] **3. Analysis Engine** `L`
  - [ ] 3.1 Write unit tests for analysis algorithms
  - [ ] 3.2 Implement core calculation functions
  - [ ] 3.3 Add economic evaluation capabilities (NPV integration)
  - [ ] 3.4 Implement performance optimization
  - [ ] 3.5 Verify all analysis tests pass

- [ ] **4. Integration with Existing Systems** `M`
  - [ ] 4.1 Write integration tests with BSEE data pipeline
  - [ ] 4.2 Implement data flow connections
  - [ ] 4.3 Add compatibility with existing visualization tools
  - [ ] 4.4 Test end-to-end workflows
  - [ ] 4.5 Verify all integration tests pass

## Phase 3: User Interface & Documentation

- [ ] **5. User Interface** `M`
  - [ ] 5.1 Write tests for user interface functions
  - [ ] 5.2 Implement command-line interface or notebook integration
  - [ ] 5.3 Add configuration and customization options
  - [ ] 5.4 Implement user input validation
  - [ ] 5.5 Verify all UI tests pass

- [ ] **6. Documentation & Examples** `S`
  - [ ] 6.1 Create comprehensive API documentation
  - [ ] 6.2 Write tutorial notebooks with real examples
  - [ ] 6.3 Add inline code documentation following standards
  - [ ] 6.4 Create migration guide if applicable
  - [ ] 6.5 Verify documentation builds and examples run

## Phase 4: Quality Assurance & Deployment

- [ ] **7. Quality Assurance** `M`
  - [ ] 7.1 Run complete test suite (unit, integration, performance)
  - [ ] 7.2 Code review and refactoring based on feedback
  - [ ] 7.3 Performance testing and optimization
  - [ ] 7.4 Security review and validation
  - [ ] 7.5 Final verification of all quality gates

- [ ] **8. Deployment & Rollout** `S`
  - [ ] 8.1 Prepare release notes and changelog
  - [ ] 8.2 Package and publish to appropriate channels
  - [ ] 8.3 Update main repository documentation
  - [ ] 8.4 Communicate rollout to stakeholders
  - [ ] 8.5 Monitor deployment and gather initial feedback

## Definition of Done

- [ ] All code implemented following WorldEnergyData coding standards
- [ ] Test coverage >= 80% with all tests passing
- [ ] Code quality checks pass (black, isort, ruff, mypy)
- [ ] Documentation complete with working examples
- [ ] Performance benchmarks meet requirements
- [ ] Integration tests pass with existing WorldEnergyData components
- [ ] Stakeholder review and approval completed

## Effort Estimates

- **XS:** 1-2 hours
- **S:** 1-2 days  
- **M:** 3-5 days
- **L:** 1-2 weeks
- **XL:** 3-4 weeks

## Notes

- Follow UV package management conventions
- Integrate with existing BSEE and economic analysis modules
- Ensure compatibility with Python 3.9+ as specified in tech stack
- Use matplotlib/plotly for any visualization requirements
- Follow Agent OS development workflow and documentation standards
"""
    
    with open(spec_path / "tasks.md", "w") as f:
        f.write(tasks_content)

def create_executive_summary(spec_path, spec_name):
    """Create executive summary for business stakeholders."""
    summary_content = f"""# Executive Summary - {spec_name}

> Created: {datetime.now().strftime("%Y-%m-%d")}
> Audience: Business Stakeholders, Project Sponsors
> Repository: WorldEnergyData

## Business Case

### Problem Statement
[Clear description of the business problem this spec addresses]

### Proposed Solution
[High-level solution overview focusing on business value]

### Expected Benefits
- **Cost Savings:** [Quantified cost reduction or efficiency gains]
- **Time Savings:** [Quantified time reduction in analysis workflows]
- **Capability Enhancement:** [New capabilities enabled for users]
- **Competitive Advantage:** [How this differentiates WorldEnergyData]

## Investment & Resources

### Development Effort
- **Estimated Timeline:** [X weeks/months]
- **Team Requirements:** [Developer roles and time allocation]
- **External Dependencies:** [Third-party requirements or partnerships]

### Success Metrics
- **User Adoption:** [Target number of active users or use cases]
- **Performance Improvement:** [Quantifiable performance gains]
- **Business Impact:** [Revenue, cost, or efficiency improvements]

## Risk Assessment

### High-Impact Risks
- **[Risk Category]:** [Impact and probability assessment]
- **[Risk Category]:** [Mitigation strategy and contingency plan]

### Mitigation Strategies
- [Primary risk mitigation approach]
- [Contingency planning for critical risks]

## Recommendation

[Clear recommendation with next steps and decision points for stakeholders]

### Go/No-Go Criteria
- [ ] [Critical success factor]
- [ ] [Resource availability confirmation]
- [ ] [Stakeholder alignment verification]

## Appendix

### Technical Details Summary
[High-level technical approach without implementation details]

### Competitive Analysis
[Brief comparison with alternative approaches or solutions]
"""
    
    summary_path = spec_path / "summaries"
    summary_path.mkdir(exist_ok=True)
    
    with open(summary_path / "executive-summary.md", "w") as f:
        f.write(summary_content)

def create_mermaid_diagrams(spec_path, spec_name):
    """Create system architecture and workflow diagrams."""
    
    # System architecture diagram
    architecture_diagram = f"""# System Architecture - {spec_name}

```mermaid
graph TB
    subgraph "Data Sources"
        A[BSEE Database]
        B[SODIR Database]
        C[Wind Energy Data]
        D[Public APIs]
    end
    
    subgraph "WorldEnergyData Core"
        E[Data Ingestion Layer]
        F[Processing Engine]
        G[Analysis Modules]
        H[Economic Evaluation]
    end
    
    subgraph "User Interface"
        I[Python API]
        J[Jupyter Notebooks]
        K[Command Line Tools]
        L[Export Functions]
    end
    
    subgraph "Output & Visualization"
        M[matplotlib Charts]
        N[plotly Interactive]
        O[CSV/Excel Export]
        P[PDF Reports]
    end
    
    A --> E
    B --> E
    C --> E
    D --> E
    
    E --> F
    F --> G
    F --> H
    
    G --> I
    H --> I
    I --> J
    I --> K
    I --> L
    
    J --> M
    J --> N
    K --> O
    L --> P
```

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant API as WorldEnergyData API
    participant Engine as Processing Engine
    participant BSEE as BSEE Database
    participant Analysis as Analysis Module
    participant Viz as Visualization

    User->>API: Request analysis
    API->>Engine: Initialize processing
    Engine->>BSEE: Fetch raw data
    BSEE-->>Engine: Return data
    Engine->>Analysis: Process data
    Analysis-->>Engine: Return results
    Engine->>Viz: Generate visualizations
    Viz-->>Engine: Return charts/plots
    Engine-->>API: Compiled results
    API-->>User: Analysis complete
```

## Component Integration

```mermaid
classDiagram
    class DataSource {{
        +connect()
        +fetch_data()
        +validate()
    }}
    
    class ProcessingEngine {{
        +load_config()
        +process_data()
        +apply_transformations()
    }}
    
    class AnalysisModule {{
        +calculate_npv()
        +generate_forecasts()
        +create_comparisons()
    }}
    
    class VisualizationEngine {{
        +create_plots()
        +generate_reports()
        +export_results()
    }}
    
    DataSource --> ProcessingEngine
    ProcessingEngine --> AnalysisModule
    AnalysisModule --> VisualizationEngine
```
"""
    
    diagrams_path = spec_path / "diagrams"
    diagrams_path.mkdir(exist_ok=True)
    
    with open(diagrams_path / "architecture.mmd", "w") as f:
        f.write(architecture_diagram)

def main():
    """Main enhanced create-spec command."""
    if len(sys.argv) < 2:
        print("Usage: python create-spec-enhanced.py <spec-name> [module-name] [variant]")
        print("Variants: enhanced (default), research, minimal")
        print("Examples:")
        print("  python create-spec-enhanced.py sodir-integration energy-sources enhanced")
        print("  python create-spec-enhanced.py wind-analysis renewables research")
        print("  python create-spec-enhanced.py quick-feature core minimal")
        return 1
    
    spec_name = sys.argv[1]
    module_name = sys.argv[2] if len(sys.argv) > 2 else None
    variant = sys.argv[3] if len(sys.argv) > 3 else "enhanced"
    
    if variant not in ["enhanced", "research", "minimal"]:
        print(f"Invalid variant: {variant}. Use: enhanced, research, or minimal")
        return 1
    
    try:
        print(f"🚀 Creating {variant} specification: {spec_name}")
        
        # Create directory structure
        spec_path = create_enhanced_spec_directory(spec_name, module_name)
        print(f"📁 Created: {spec_path}")
        
        # Create files based on variant
        create_enhanced_spec_file(spec_path, spec_name, variant)
        
        if variant in ["enhanced", "research"]:
            create_enhanced_tasks_file(spec_path, spec_name)
            create_executive_summary(spec_path, spec_name)
            
        if variant == "enhanced":
            create_mermaid_diagrams(spec_path, spec_name)
        
        print(f"✅ Enhanced specification '{spec_name}' created successfully!")
        print(f"📍 Location: {spec_path}")
        print(f"📄 Main file: {spec_path}/spec.md")
        
        if variant == "enhanced":
            print(f"📊 Executive Summary: {spec_path}/summaries/executive-summary.md")
            print(f"🎯 System Diagrams: {spec_path}/diagrams/architecture.mmd")
            print(f"📋 Enhanced Tasks: {spec_path}/tasks.md")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error creating specification: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())