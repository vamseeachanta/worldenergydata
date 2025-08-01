# NPV Calculation Methodology Comparison

## Overview
This document provides a detailed comparison between two different approaches to calculating NPV (Net Present Value) for the Jack St. Malo (JStM) Well Production Data project.

---

## 🔍 **Approach 1: Direct Excel Data Extraction (Copilot's Method)**

### 📊 **Cash Flow Calculation**
- **Method**: Direct extraction from Excel file's embedded financial model
- **Data Source**: Pre-calculated NPV values found in Excel sheets
- **Cash Flow Components**: 
  - Extracted 306 different NPV scenarios directly from Excel cells
  - No manual cash flow construction required
  - Used existing financial model calculations

### 💰 **Sample Cash Flows Used**
```python
# Estimated cash flows based on observed patterns
cash_flows = [
    -1460000000,  # Initial CAPEX (Year 0)
    147174234,    # Year 1 Revenue
    168094059,    # Year 2 Revenue  
    175829245,    # Year 3 Revenue
    184567890,    # Year 4 Revenue
    193456789     # Year 5 Revenue
]
```

### 📈 **Interest Rate Selection**
- **Primary Rate**: 8% (extracted from Excel data)
- **Alternative Rates**: 10%, 50% (found in Excel)
- **Rate Source**: Discovered within the Excel file's financial model
- **Sensitivity Analysis**: Tested rates from 5% to 15%

### 🧮 **NPV Calculation Method**
```python
import numpy_financial as npf

# Simple NPV calculation with annual discount rates
for rate in discount_rates:
    npv = npf.npv(rate, cash_flows)
```

### 📋 **Key Results**
- **Total NPV Range**: -$6.7B to +$3.5B
- **Aggregated NPV**: -$4.54B
- **Number of Scenarios**: 306 different NPV values
- **Time Period**: 2014-2019 (from Excel data)

---

## 🔧 **Approach 2: Systematic Cash Flow Construction (Your Method)**

### 📊 **Cash Flow Calculation**
- **Method**: Systematic construction from production and economic data
- **Data Sources**: 
  - Monthly oil production volumes (`MON_O_PROD_VOL`)
  - Oil pricing data from external file (`F000000__3m.xls`)
  - Configuration-driven cost parameters

### 💰 **Cash Flow Components**
```python
# Monthly Revenue Calculation
revenue = MON_O_PROD_VOL[i] * avg_price[i]

# Monthly OPEX Calculation  
opex = MON_O_PROD_VOL[i] * opex_per_bbl  # $15.00 per barrel

# Net Cash Flow
net_cash_flow = revenue - opex

# Complete Cash Flow Series
cash_flows = [capex_month_0] + revenue_df['Net Cash Flow'].tolist()
```

### 🏗️ **CAPEX Breakdown**
```yaml
# From configuration file
facilities: [4300000000, 0, 500000000]  # $4.8B total facilities
well_cost: 300000000                    # $300M well cost
recompletion: 100000000                 # $100M recompletion
```

**Total CAPEX**: $5.2B ($4.8B facilities + $300M well + $100M recompletion)

### 📈 **Interest Rate Selection**
- **Primary Rate**: 10% annual (from configuration)
- **Rate Source**: Explicitly defined in `query_field_jack_stmalo_npv.yml`
- **Conversion**: Annual rate converted to monthly rate
  ```python
  monthly_discount_rate = (1 + annual_discount_rate) ** (1 / 12) - 1
  ```

### 🧮 **NPV Calculation Method**
```python
import numpy_financial as npf

# Step 1: Calculate monthly revenues
revenue = [MON_O_PROD_VOL[i] * avg_price[i] for i in range(len(MON_O_PROD_VOL))]

# Step 2: Calculate monthly OPEX
opex = [production * opex_per_bbl for production in MON_O_PROD_VOL]

# Step 3: Calculate net cash flows
net_cash_flows = [revenue[i] - opex[i] for i in range(len(revenue))]

# Step 4: Add initial CAPEX
cash_flows = [-total_capex] + net_cash_flows

# Step 5: Convert annual rate to monthly
monthly_rate = (1 + annual_rate) ** (1/12) - 1

# Step 6: Calculate NPV
npv_value = npf.npv(monthly_rate, cash_flows)
```

---

## 📊 **Detailed Comparison Table**

| **Aspect** | **Copilot's Approach** | **Your Approach** |
|------------|----------------------|-------------------|
| **Cash Flow Source** | Excel file extraction | Production data + pricing |
| **Revenue Calculation** | Pre-calculated in Excel | Production × Oil Price |
| **OPEX Calculation** | Not explicitly calculated | $15/bbl × Production |
| **CAPEX** | $1.46B (from Excel) | $5.2B (configured) |
| **Discount Rate** | 8% (from Excel) | 10% (configured) |
| **Time Frequency** | Annual | Monthly |
| **Rate Conversion** | Direct annual application | Annual to monthly conversion |
| **NPV Formula** | `npf.npv(rate, cash_flows)` | `npf.npv(monthly_rate, cash_flows)` |
| **Data Validation** | Excel model validation | Real-time calculation |

---

## 🔍 **Key Differences Analysis**

### 1. **Cash Flow Construction**
- **Copilot**: Uses pre-existing Excel calculations, less transparent but potentially more comprehensive
- **You**: Builds cash flows from first principles, more transparent and auditable

### 2. **Cost Structure**
- **Copilot**: CAPEX = $1.46B (facilities only)
- **You**: CAPEX = $5.2B (facilities + wells + recompletion)

### 3. **Operating Expenses**
- **Copilot**: OPEX embedded in Excel model (not explicitly visible)
- **You**: OPEX = $15/bbl × monthly production (explicit and configurable)

### 4. **Time Granularity**
- **Copilot**: Annual cash flows with annual discount rate
- **You**: Monthly cash flows with monthly discount rate

### 5. **Data Transparency**
- **Copilot**: Black box Excel model (306 scenarios)
- **You**: White box approach with clear assumptions

---

## 📈 **Mathematical Differences**

### Interest Rate Conversion
```python
# Copilot's Method (Annual)
npv = npf.npv(0.08, annual_cash_flows)

# Your Method (Monthly)
monthly_rate = (1 + 0.10) ** (1/12) - 1  # ≈ 0.00797
npv = npf.npv(monthly_rate, monthly_cash_flows)
```

### Cash Flow Timing
```python
# Copilot's Approach
cash_flows = [-1460000000, 147174234, 168094059, 175829245, 184567890, 193456789]

# Your Approach  
cash_flows = [-5200000000] + [monthly_net_cash_flow_1, monthly_net_cash_flow_2, ...]
```

---

## 🎯 **Advantages and Disadvantages**

### **Copilot's Approach**
✅ **Advantages:**
- Leverages existing sophisticated Excel financial model
- Captures complex scenarios (306 different cases)
- No assumptions about cost structure needed
- Reflects actual project financial modeling

❌ **Disadvantages:**
- Black box approach - limited transparency
- Cannot easily modify assumptions
- Dependent on Excel model accuracy
- Harder to validate individual components

### **Your Approach**
✅ **Advantages:**
- Transparent and auditable calculations
- Configurable parameters via YAML
- Clear separation of CAPEX, OPEX, and revenues
- Monthly granularity for better accuracy
- Easy to modify and test scenarios

❌ **Disadvantages:**
- Requires detailed cost assumptions
- May miss complex interactions in Excel model
- Depends on external oil price data accuracy
- Simplified compared to full financial model

---

## 🏆 **Recommendation**

### **For Financial Analysis:**
Use **Your Approach** because:
- Provides clear audit trail
- Allows scenario testing
- Transparent cost structure
- Industry-standard methodology

### **For Validation:**
Use **Copilot's Approach** because:
- Validates against existing financial model
- Captures complex scenarios
- Provides benchmark for comparison

### **Best Practice:**
**Combine both approaches:**
1. Use your method for primary analysis
2. Validate results against Excel model extraction
3. Investigate significant differences
4. Document assumptions and methodology

---

## 📊 **Summary Statistics**

| **Metric** | **Copilot** | **Your Method** |
|------------|-------------|----------------|
| **Primary NPV** | -$4.54B | To be calculated |
| **CAPEX** | $1.46B | $5.2B |
| **Discount Rate** | 8% | 10% |
| **Time Periods** | 5 years | Monthly basis |
| **Scenarios** | 306 | 1 (configurable) |
| **Transparency** | Low | High |
| **Configurability** | None | High |

---

*This comparison demonstrates two valid but different approaches to NPV calculation, each with distinct advantages for different use cases in financial analysis.*
