# Database Schema

This is the database schema implementation for the spec detailed in @specs/modules/infrastructure/sub-agents-system/spec.md

> Created: 2025-07-25
> Version: 1.0.0

## Schema Overview

The sub-agents system uses a file-based storage system consistent with WorldEnergyData's architecture, utilizing YAML files for configuration and CSV files for performance tracking. No traditional database changes are required as the system leverages the existing file-based data management approach.

## File-Based Schema Structure

### Agent Configuration Files (YAML)

**Location**: `.agent-os/agents/core/`

```yaml
# energy_economics.yaml
agent:
  metadata:
    name: "energy_economics"
    version: "1.0.0"
    created_date: "2025-07-25"
    last_updated: "2025-07-25"
    specialization: "Energy Economic Analysis"
  
  knowledge_domains:
    - domain_id: "npv_analysis"
      proficiency_level: 8.5
      last_updated: "2025-07-25"
    - domain_id: "production_forecasting" 
      proficiency_level: 7.2
      last_updated: "2025-07-25"
  
  learning_metrics:
    total_learning_sessions: 0
    knowledge_base_size: 0
    performance_score: 0.0
    last_learning_date: null
```

### Knowledge Base Files (Structured Text/Markdown)

**Location**: `.agent-os/agents/knowledge_bases/{agent_name}/`

```
energy_economics/
├── concepts/
│   ├── npv_fundamentals.md
│   ├── discount_rates.md
│   └── risk_assessment.md
├── methodologies/
│   ├── monte_carlo.md
│   ├── sensitivity_analysis.md
│   └── scenario_modeling.md
├── industry_standards/
│   ├── bsee_economics.md
│   ├── spe_guidelines.md
│   └── regulatory_requirements.md
└── code_examples/
    ├── npv_calculations.py
    ├── production_models.py
    └── visualization_examples.py
```

### Performance Tracking (CSV)

**Location**: `.agent-os/agents/learning/performance_metrics/`

```csv
# agent_performance_history.csv
agent_name,date,session_type,knowledge_domains_updated,performance_score,learning_duration_minutes,new_concepts_learned
energy_economics,2025-07-25,initialization,4,0.0,0,0
petroleum_engineering,2025-07-25,initialization,5,0.0,0,0
data_quality,2025-07-25,initialization,4,0.0,0,0
```

### Learning Schedules (YAML)

**Location**: `.agent-os/agents/learning/schedules/`

```yaml
# weekly_learning_schedule.yaml
learning_schedule:
  frequency: "weekly"
  day_of_week: "sunday"
  time: "02:00"
  
  agents:
    - name: "energy_economics"
      priority: "high"
      resources:
        - type: "industry_publications"
          sources: ["SPE", "IAEE", "Energy Policy"]
        - type: "technical_papers"
          sources: ["arxiv", "ResearchGate"]
        - type: "code_repositories"
          sources: ["github_energy_economics"]
    
    - name: "petroleum_engineering"
      priority: "high"
      resources:
        - type: "industry_publications" 
          sources: ["SPE", "JPT", "OGJ"]
        - type: "technical_papers"
          sources: ["OnePetro", "ScienceDirect"]
```

### Learning Resources Index (YAML)

**Location**: `.agent-os/agents/learning/resources/`

```yaml
# resource_index.yaml
resources:
  energy_economics:
    last_updated: "2025-07-25"
    sources:
      - name: "SPE Economics"
        url: "https://www.spe.org/en/jpt/jpt-article-detail/?art=8543"
        type: "industry_publication"
        relevance_score: 9.5
        last_accessed: "2025-07-25"
      
      - name: "NPV Analysis Methods"
        path: "docs/literature/npv_methods.pdf"
        type: "technical_paper"
        relevance_score: 9.0
        last_accessed: "2025-07-25"
```

## Data Integrity and Validation

### Schema Validation Rules

1. **Agent Configuration Validation**:
   - Required fields: name, version, specialization
   - Proficiency levels: 0.0 to 10.0 range
   - Valid domain IDs from predefined list

2. **Performance Metrics Validation**:
   - Performance scores: 0.0 to 10.0 range
   - Learning duration: positive integers
   - Date formats: YYYY-MM-DD

3. **Learning Schedule Validation**:
   - Frequency: "daily", "weekly", "monthly"
   - Day of week: valid day names
   - Time: HH:MM format

### File Organization Standards

- All YAML files follow consistent indentation (2 spaces)
- CSV files include headers and maintain consistent column ordering
- Markdown files in knowledge bases follow standard formatting
- File naming convention: lowercase with underscores

## Migration Strategy

Since this is a new system implementation, no data migration is required. The system will initialize with:

1. **Base agent configurations** with default proficiency levels
2. **Empty performance tracking files** ready for data collection  
3. **Template knowledge base structures** for each specialized agent
4. **Default learning schedules** configured for weekly updates

## Backup and Versioning Strategy

- All configuration files tracked in Git version control
- Performance metrics backed up weekly to `backups/` directory
- Knowledge base changes tracked through Git commits
- Learning resource updates logged with timestamps and change descriptions