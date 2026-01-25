# Hierarchical Data Flow Design

## Overview
The comprehensive reporting system uses a four-level hierarchy:
**Well → Lease → Field → Block**

## Hierarchy Levels

### 1. Well Level (Base)
- **Key Fields**: API Number, Well Name
- **Data Source**: BSEE production and well data
- **Aggregation**: Individual well metrics

### 2. Lease Level
- **Key Fields**: Lease Number, Lease Name
- **Parent**: Field
- **Aggregation**: Sum of wells in lease

### 3. Field Level
- **Key Fields**: Field Name, Field Code
- **Parent**: Block
- **Aggregation**: Sum of leases in field

### 4. Block Level (Top)
- **Key Fields**: Block Number, Protraction Area
- **Parent**: None (top level)
- **Aggregation**: Sum of fields in block

## Data Flow Patterns

### Bottom-Up Aggregation
1. Collect well-level data from BSEE
2. Aggregate wells to lease level
3. Aggregate leases to field level
4. Aggregate fields to block level

### Top-Down Drill-Down
1. Select block → View fields
2. Select field → View leases
3. Select lease → View wells
4. Select well → View details

## Aggregation Rules

### Production Metrics
- **Daily Production**: Sum at each level
- **Cumulative Production**: Sum at each level
- **Peak Rate**: Maximum at each level
- **Average Rate**: Mean at each level

### Economic Metrics
- **NPV**: Sum at each level
- **Revenue**: Sum at each level
- **Costs**: Sum at each level
- **Profit**: Sum at each level

## Report Generation Workflow

### Step 1: Data Collection
- Query BSEE databases
- Retrieve well, lease, field data

### Step 2: Data Validation
- Validate identifiers
- Check completeness
- Flag anomalies

### Step 3: Hierarchical Aggregation
- Group by hierarchy levels
- Calculate metrics at each level

### Step 4: Economic Calculations
- Apply pricing
- Calculate revenues and costs
- Generate NPV/IRR

### Step 5: Template Processing
- Select and populate templates
- Generate visualizations

### Step 6: Export Generation
- Create Excel, PDF, HTML outputs
- Export data files

## Performance Optimizations
- Parallel processing for aggregation
- Caching at lease, field, block levels
- Incremental updates for new data

---
*Generated for Comprehensive Report System*
