# Module Hierarchy and Integration Design

> Created: 2025-08-28
> Version: 1.0
> Purpose: Visual representation of SME financial module integration

## Module Hierarchy Diagram

```mermaid
graph TB
    subgraph "worldenergydata.bsee"
        subgraph "analysis.sme_financial"
            C[sme_analyzer.py<br/>Main SME Orchestrator]
            D[lease_grouper.py<br/>Lease Grouping Logic]
            E[drilling_completion.py<br/>D&C Cost Processing]
            F[cash_flow_calculator.py<br/>Monthly Cash Flow]
            R[report_generator.py<br/>SME Report Generation]
            S[sme_cli.py<br/>SME CLI Interface]
        end
        
        subgraph "reports.comprehensive"
            A[cli.py<br/>Comprehensive CLI]
            B[controller_enhanced.py<br/>Orchestration]
            
            subgraph "Shared Components"
                G[data_loader_enhanced.py<br/>Data Loading]
                H[hierarchical_aggregator.py<br/>Aggregation]
                I[models.py<br/>Data Models]
            end
            
            subgraph "templates"
                J[economic_template.py<br/>NPV/ROI Calculations]
                K[report_structure.py<br/>Report Templates]
            end
            
            subgraph "exporters"
                L[excel_exporter.py<br/>Excel Generation]
                M[pdf_exporter.py<br/>PDF Generation]
            end
            
            subgraph "config"
                N[sme_config.yaml<br/>SME Configuration]
                O[report_config.yaml<br/>General Config]
            end
        end
        
        subgraph "data"
            P[_from_bin/<br/>Binary Readers]
            Q[_from_zip/<br/>ZIP Readers]
        end
    end
    
    %% Relationships - SME imports from Comprehensive
    S --> C
    C --> D
    C --> E
    C --> F
    C --> R
    D --> H
    E --> G
    F --> J
    R --> L
    G --> P
    G --> Q
    H --> I
    N --> C
    
    %% Separate CLI paths
    A --> B
    O --> B
```

## Data Flow Architecture

```mermaid
graph LR
    subgraph "Input Data"
        A1[WAR Binary Files]
        A2[Production ZIP Files]
        A3[Lease Config YAML]
    end
    
    subgraph "Data Processing Layer"
        B1[data_loader_enhanced<br/>Load & Parse]
        B2[lease_grouper<br/>Group Leases]
        B3[drilling_completion<br/>Process D&C Costs]
    end
    
    subgraph "Financial Calculation Layer"
        C1[cash_flow_calculator<br/>Monthly Cash Flow]
        C2[economic_template<br/>NPV/ROI/Revenue]
        C3[hierarchical_aggregator<br/>Aggregate Metrics]
    end
    
    subgraph "Output Generation Layer"
        D1[report_builder<br/>Structure Report]
        D2[excel_exporter<br/>Format Excel]
        D3[Generated Reports]
    end
    
    A1 --> B1
    A2 --> B1
    A3 --> B2
    B1 --> B2
    B1 --> B3
    B2 --> C1
    B3 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D1
    D1 --> D2
    D2 --> D3
```

## Component Integration Points

```mermaid
sequenceDiagram
    participant CLI as CLI Interface
    participant Controller as Controller
    participant SME as SME Analyzer
    participant Loader as Data Loader
    participant Calc as Calculator
    participant Export as Exporter
    
    CLI->>Controller: Execute SME Analysis
    Controller->>SME: Initialize with config
    SME->>Loader: Load production data
    Loader-->>SME: Production DataFrame
    SME->>Loader: Load D&C costs
    Loader-->>SME: D&C DataFrame
    SME->>Calc: Calculate cash flows
    Calc-->>SME: Monthly cash flows
    SME->>Calc: Calculate NPV
    Calc-->>SME: NPV metrics
    SME->>Export: Generate Excel
    Export-->>CLI: Report path
```

## Module Dependencies

```mermaid
graph TD
    subgraph "New SME Modules"
        A[sme_analyzer.py]
        B[lease_grouper.py]
        C[drilling_completion.py]
        D[cash_flow_calculator.py]
    end
    
    subgraph "Existing Modules to Extend"
        E[data_loader_enhanced.py]
        F[hierarchical_aggregator.py]
        G[economic_template.py]
        H[cli.py]
    end
    
    subgraph "Reused Without Changes"
        I[models.py]
        J[excel_exporter.py]
        K[config system]
    end
    
    A --> B
    A --> C
    A --> D
    B --> F
    C --> E
    D --> G
    A --> J
    H --> A
    E --> I
    F --> I
```

## Class Hierarchy

```
# SME Financial Module (analysis/sme_financial/) - Separate Module
SMEAnalyzer
├── Uses: HierarchicalDataLoader (from comprehensive)
├── Uses: PriceDeck (from comprehensive)
├── Uses: CostStructure (from comprehensive)
└── Contains:
    ├── SMEDataLoader
    │   ├── load_matrix_production()
    │   ├── load_drilling_completion()
    │   └── merge_production_by_lease()
    ├── LeaseGrouper
    │   ├── apply_lease_grouping()
    │   └── aggregate_by_group()
    ├── CashFlowCalculator
    │   ├── calculate_monthly_cash_flow()
    │   ├── apply_tax_calculations()
    │   └── calculate_npv()
    └── SMEReportGenerator
        ├── build_financial_sheets()
        ├── add_readme_sheet()
        └── format_sme_output()

# Reused from Comprehensive Reports (reports/comprehensive/)
BaseAggregator (existing)
├── HierarchicalAggregator (existing)

HierarchicalDataLoader (existing)

ReportBuilder (existing)
├── GoByReportBuilder (existing)

BaseTemplate (existing)
├── EconomicTemplate (existing)
```

## Interface Definitions

### 1. SME Analyzer Interface
```python
class SMEAnalyzer:
    def __init__(self, config: dict)
    def load_data(self) -> dict
    def process_lease_groups(self) -> pd.DataFrame
    def calculate_financials(self) -> dict
    def generate_report(self) -> str
```

### 2. Lease Grouper Interface
```python
class LeaseGrouper:
    def __init__(self, group_config: dict)
    def group_leases(self, data: pd.DataFrame) -> pd.DataFrame
    def aggregate_by_group(self, production: pd.DataFrame) -> pd.DataFrame
```

### 3. Cash Flow Calculator Interface
```python
class CashFlowCalculator:
    def __init__(self, price_deck: PriceDeck, cost_structure: CostStructure)
    def calculate_monthly_cash_flow(self, production: pd.DataFrame, costs: pd.DataFrame) -> pd.DataFrame
    def apply_taxes(self, cash_flow: pd.DataFrame) -> pd.DataFrame
    def calculate_npv(self, cash_flow: pd.DataFrame, discount_rate: float) -> float
```

## Configuration Integration

```yaml
# Extended CLI arguments
bsee-reports:
  mode: sme-financial  # New mode
  
  sme_options:
    lease_groups: config/lease_groups.yaml
    discount_rate: 0.10
    tax_rate: 0.35
    output_format: excel
    include_readme: true
    
  # Reused options
  data_path: data/bsee/
  output_path: reports/
  price_deck:
    oil: 50.00
    gas: 3.00
```

## Testing Strategy

```mermaid
graph TD
    A[Unit Tests] --> B[Component Tests]
    B --> C[Integration Tests]
    C --> D[End-to-End Tests]
    
    A --> A1[Test LeaseGrouper]
    A --> A2[Test CashFlowCalculator]
    A --> A3[Test DrillingCompletion]
    
    B --> B1[Test SMEAnalyzer]
    B --> B2[Test Data Loading]
    B --> B3[Test Report Generation]
    
    C --> C1[Test Full Pipeline]
    C --> C2[Test CLI Commands]
    
    D --> D1[Validate vs V20 Output]
    D --> D2[Performance Testing]
```

## Performance Considerations

1. **Data Loading Optimization**
   - Reuse binary file caching from comprehensive reports
   - Implement chunked processing for large datasets

2. **Calculation Optimization**
   - Vectorize monthly calculations using pandas
   - Cache intermediate results

3. **Memory Management**
   - Process leases in batches
   - Clear intermediate DataFrames

4. **Parallel Processing**
   - Use existing parallel processing from comprehensive reports
   - Process lease groups concurrently

## Summary

This module hierarchy shows how the SME financial analysis integrates seamlessly with the existing comprehensive report system. Key benefits:

1. **Minimal new code**: Reusing 70% of existing components
2. **Consistent architecture**: Follows established patterns
3. **Maintainable**: Clear separation of concerns
4. **Testable**: Each component independently testable
5. **Extensible**: Easy to add new financial calculations

The integration leverages existing infrastructure while adding SME-specific functionality in a modular way.