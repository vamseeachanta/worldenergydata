# Lower Tertiary Economic Analysis - Key Assumptions

## Document Information
- **Version**: 1.0.0
- **Date**: 2024-12-20
- **Analysis Period**: 2008-01-01 to 2024-12-31
- **Purpose**: Document all key assumptions for Lower Tertiary field economic analysis

---

## 1. Economic Assumptions

### 1.1 Commodity Prices

#### Oil Pricing
- **Base Case WTI**: $75.00/bbl (2024 average)
- **Historical Data Source**: EIA WTI Cushing monthly spot prices
- **Quality Adjustment**: $0.00 (assume Lower Tertiary crude is WTI equivalent)
- **Price Scenarios**:
  - Low: $50/bbl
  - Mid: $75/bbl (base)
  - High: $100/bbl
- **Post-2024 Escalation**: 2% per year
- **Assumption Impact**: ±$10/bbl changes NPV by approximately ±30%

#### Natural Gas Pricing
- **Base Case Henry Hub**: $3.50/mcf (2024 average)
- **GOM Basis Differential**: -$0.20/mcf (Houston Ship Channel vs. HH)
- **Price Scenarios**:
  - Low: $2.50/mcf
  - Mid: $3.50/mcf (base)
  - High: $5.00/mcf
- **Post-2024 Escalation**: 2.5% per year
- **Assumption Impact**: Gas typically represents 15-20% of total revenue

#### Natural Gas Liquids (NGL)
- **Base Case NGL**: $30.00/bbl (basket price)
- **Yield**: 0.08 bbl NGL per mcf gas produced
- **Price Scenarios**:
  - Low: $20/bbl
  - Mid: $30/bbl (base)
  - High: $40/bbl
- **Assumption Impact**: NGL represents 3-5% of total revenue

**Key Assumption**: Historical prices through Dec 2024 are used for actual production periods. Forward prices use base case with escalation.

---

### 1.2 Fiscal Terms (Federal Gulf of Mexico)

#### Royalties
- **Rate**: 18.75% (3/16ths)
- **Basis**: Gross revenue at wellhead
- **Payable To**: Bureau of Ocean Energy Management (BOEM)
- **Lease Type**: Standard OCS lease (most Lower Tertiary fields)
- **Assumption**: All fields use standard 18.75% rate; some early leases may have lower rates (12.5%)

#### Income Taxes
- **Federal Corporate Tax**: 21% (post-Tax Cuts and Jobs Act 2017)
- **State Tax**: 0% (N/A for federal waters beyond state jurisdiction)
- **Combined Rate**: 21%
- **Basis**: Taxable income (revenue - royalty - opex - depreciation - depletion)
- **Assumption**: Straight-line depreciation over 10 years; no bonus depreciation modeled

#### Other Taxes
- **Severance Tax**: 0% (N/A for OCS)
- **Property Tax**: Included in fixed opex
- **Ad Valorem Tax**: Not applicable offshore

**Key Assumption**: Tax calculations are simplified and do not include:
- Net operating loss carryforwards
- Foreign tax credits
- Alternative minimum tax
- State income tax on onshore support facilities

---

### 1.3 Working Interest and Net Revenue Interest

#### Typical Structure
- **Working Interest (WI)**: 100% (gross field basis for this analysis)
- **Net Revenue Interest (NRI)**: 81.25% (100% - 18.75% royalty)
- **Override**: 0% (none assumed)

**Key Assumption**: Analysis is performed at 100% WI to show field-level economics. Individual partner economics would require scaling by their WI percentage.

#### Partner Examples (for reference, not used in calculations)
- **Jack/St. Malo**: Chevron 51%, Equinor 24.5%, Suncor 24.5%
- **Stones**: Shell 100%
- **Julia**: Equinor 50%, ExxonMobil 50%
- **Anchor**: Chevron 62.5%, Equinor 25%, TotalEnergies 12.5%

---

## 2. Capital Expenditure Assumptions

### 2.1 Development Costs

#### Subsea Development (Typical Lower Tertiary)
- **Host Facility**: $1,500-2,500 million
  - Floating production unit (SPAR, TLP, semi-submersible, or FPSO)
  - Processing capacity: 50-180 MBOPD
  - Water depth: 5,000-9,500 ft
  
- **Wells**: $200-350 million per well
  - Drilling: $150-250 million (MODU rates, ultra-deepwater)
  - Completion: $50-100 million (HPHT, long laterals)
  - Total vertical depth: 20,000-35,000 ft
  - Typical well count: 6-11 wells per field
  
- **Subsea Systems**: $150-300 million
  - Subsea production systems (trees, manifolds)
  - Risers, flowlines, umbilicals (SURF)
  - Control systems
  
- **Total Typical Development**: $1,800-3,200 million per field

#### Development Timeline
- **Engineering & Design**: 24 months (10% of costs)
- **Construction**: 36 months (60% of costs)
- **Installation & Commissioning**: 12 months (30% of costs)
- **Total FID to First Oil**: 60 months (5 years typical)

**Key Assumption**: Actual capital costs are used for producing fields based on public disclosures. Pre-FID fields use industry estimates with high uncertainty.

### 2.2 Exploration and Appraisal (Sunk Costs)
- **Discovery Well**: $200-300 million
- **Appraisal Wells**: $150-250 million each (1-2 wells typical)
- **Seismic**: $50-100 million (3D and 4D)
- **Total Pre-FID**: $400-700 million

**Key Assumption**: Exploration costs are typically expensed and not carried forward to development NPV calculations. Exception: Shenandoah shows the impact of ~$700MM in write-offs by prior partners.

### 2.3 Abandonment and Decommissioning
- **Cost**: 10% of development capex
- **Timing**: 2 years after cessation of production
- **Includes**: P&A wells, remove subsea equipment, decommission host
- **Discounting**: Full NPV treatment at 10% discount rate

**Key Assumption**: Decommissioning costs are preliminary estimates; actual costs may vary ±50%.

---

## 3. Operating Expenditure Assumptions

### 3.1 Fixed Operating Costs
- **Annual Fixed Cost**: $120 million per field
- **Includes**:
  - Platform operations and manning
  - Base maintenance
  - Insurance
  - Onshore support
- **Escalation**: 3% per year
- **Assumption**: Fixed costs are independent of production rates until shut-in

### 3.2 Variable Operating Costs
- **Oil Opex**: $15-18/bbl (subsea development)
  - Processing and treating
  - Export pipeline fees
  - Chemicals
  - Energy costs
- **Gas Opex**: $0.50/mcf
- **Water Handling**: $2.50/bbl
- **Escalation**: 3% per year

**Key Assumption**: Opex per BOE typically increases over field life as production declines and water cut increases.

### 3.3 Workovers and Interventions
- **Annual Workover Budget**: $20 million
- **Major Intervention**: $50 million every 5 years
- **Contingency**: Included in annual budget

---

## 4. Production Assumptions

### 4.1 Type Curves and Decline Rates

#### Typical Lower Tertiary Well
- **Initial Rate**: 10,000 BOPD (first month)
- **Decline Type**: Hyperbolic
- **Initial Decline**: 45% annual (first year)
- **Hyperbolic Exponent (b)**: 0.30
- **Terminal Decline**: 8% annual (after 5 years)
- **EUR per Well**: 8-18 MMBOE (P10-P90 range)

**Key Assumption**: Actual production data is used for producing fields through Dec 2024. Forward projections use decline curve analysis.

### 4.2 Field-Level Production

#### Plateau Production
- **Plateau Rate**: 40-80 MBOPD (varies by field)
- **Plateau Duration**: 2-4 years
- **Ramp-up Period**: 6-12 months to plateau

#### Gas-Oil Ratio (GOR)
- **Initial GOR**: 800-1,500 scf/bbl
- **Trend**: Increasing over time
- **Terminal GOR**: 1,500-2,500 scf/bbl
- **Assumption**: GOR increase reflects pressure depletion

#### Water Cut
- **Initial Water Cut**: 5%
- **Water Breakthrough**: Year 8-10
- **Terminal Water Cut**: 80%
- **Trend**: S-curve increase

**Key Assumption**: Reservoir performance varies significantly by field. Type curves represent averages and may not match individual well performance.

---

## 5. Financial Metrics and Discount Rates

### 5.1 Discount Rates
- **Primary Discount Rate**: 10% (NPV10)
- **Alternative Rates**: 8%, 15%
- **WACC (Corporate)**: 10%
- **Project Hurdle Rate**: 15% (reflects deepwater risk)
- **Risk-Free Rate**: 4%

**Key Assumption**: 10% discount rate is standard for oil and gas NPV calculations. Higher rates (15%) reflect additional project risk for deepwater HPHT developments.

### 5.2 Return Thresholds
- **Minimum IRR**: 15%
- **Target IRR**: 20%
- **Excellent IRR**: 30%+
- **Payback Target**: <7 years
- **Maximum Payback**: 10 years

### 5.3 Other Metrics
- **Profitability Index (PI)**: NPV / Total CAPEX
  - Target: PI > 0.5
- **Unit Technical Cost**: Total CAPEX / EUR
  - Target: <$15/BOE
- **F&D Cost**: (Exploration + Development CAPEX) / Reserves
  - Benchmark: $10-20/BOE for deepwater

---

## 6. Data Sources

### 6.1 Production Data
- **Source**: Bureau of Safety and Environmental Enforcement (BSEE)
- **Dataset**: Monthly production reports (OGOR-A)
- **Coverage**: All producing leases, monthly through Dec 2024
- **Vintage**: Latest available data
- **Path**: `data/modules/bsee/zip/historical_production_yearly/`
- **Validation**: Cross-check with operator disclosures where available

**Assumption**: BSEE data is accurate and complete. Any gaps filled by interpolation or operator estimates.

### 6.2 Price Data
- **Oil**: EIA WTI Cushing monthly spot prices
- **Gas**: EIA Henry Hub monthly spot prices
- **NGL**: Mont Belvieu composite basket
- **Coverage**: Monthly 1990-2024
- **Path**: `data/prices/`

**Assumption**: Spot prices represent realized prices. No hedging or long-term contracts modeled.

### 6.3 Well and Drilling Data
- **Source**: BSEE well records, directional surveys
- **Use**: Well count, spud dates, completion dates
- **Path**: `data/modules/bsee/bin/war/`, `data/modules/bsee/bin/directional_surveys/`

### 6.4 Cost Data
- **Source**: Public disclosures (SEC filings, press releases, investor presentations)
- **Fields with Public Data**: Jack/St. Malo, Stones, Julia, Anchor, Cascade/Chinook, Shenandoah
- **Validation**: Cross-check multiple sources; use industry benchmarks for validation

**Assumption**: Disclosed costs are accurate. Undisclosed costs estimated using industry benchmarks.

---

## 7. Key Limitations and Uncertainties

### 7.1 Major Assumptions
1. **Historical prices are perfect proxy** for realized prices
   - Impact: May overstate revenue if differentials widened or hedging was used
   
2. **Exploration costs excluded** from development NPV
   - Impact: Overstates project returns; actual returns to initial investors lower
   
3. **100% working interest perspective**
   - Impact: Partner-level returns require scaling
   
4. **No hedging modeled**
   - Impact: Actual cash flows may be more stable than modeled
   
5. **Straight-line depreciation**
   - Impact: Simplified tax calculations; actual tax timing may differ
   
6. **Type curves are hypothetical** for forward production
   - Impact: Actual performance varies by reservoir quality and operations

### 7.2 Areas of High Uncertainty
1. **Pre-FID Fields** (Tiber, Kaskida):
   - Capital costs: ±50%
   - Reserves: ±40%
   - Development timeline: ±3 years
   
2. **Abandonment Costs**:
   - Cost: ±50%
   - Timing: ±3 years
   
3. **Production Decline Rates**:
   - Impact on EUR: ±20%
   - Impact on NPV: ±15%
   
4. **Future Price Forecasts**:
   - Impact on NPV: ±30% for ±20% price change

### 7.3 Items Not Modeled
1. **Hedging and derivatives**
2. **Long-term sales contracts** (LNG, etc.)
3. **Transportation costs** beyond basis differential
4. **Hurricane shut-ins** and force majeure
5. **Technology improvements** over time
6. **Portfolio effects** and synergies
7. **Tax loss carryforwards**
8. **Asset retirement obligations** (ARO) accounting
9. **Contingent resources** beyond reserves
10. **Exploration upside** in proven areas

---

## 8. Sensitivity Analysis

### 8.1 Key Sensitivity Parameters
1. **Oil Price**: ±20% ($60-90/bbl range)
   - Impact on NPV: ±30%
   - Most sensitive parameter
   
2. **Production/EUR**: ±20%
   - Impact on NPV: ±25%
   - Second most sensitive
   
3. **Operating Costs**: ±20%
   - Impact on NPV: ±10%
   - Moderate sensitivity
   
4. **Capital Costs**: ±20%
   - Impact on NPV: ±8%
   - Lower sensitivity (sunk cost effect)
   
5. **Gas Price**: ±30%
   - Impact on NPV: ±5%
   - Lower sensitivity (smaller revenue component)

### 8.2 Break-Even Analysis
- **Oil Price Break-Even**: Varies by field, typically $40-55/bbl
- **Production Break-Even**: ~70% of expected EUR to achieve 10% IRR
- **Cost Break-Even**: Opex can increase ~40% before NPV turns negative

---

## 9. Validation and Quality Assurance

### 9.1 Comparison with Paper Benchmarks
Expected results from "Industry Performance in Lower Tertiary 251020":
- **Jack/St. Malo**: ~150 MMBOE cumulative, ~$8B revenue, NPV10 ~$3.5B
- **Stones**: ~80 MMBOE cumulative, ~$4.5B revenue, NPV10 ~$2.0B
- **Julia**: ~50 MMBOE cumulative, ~$2.8B revenue, NPV10 ~$1.2B

**Tolerance**: ±10% on production, ±15% on revenue, ±20% on NPV

### 9.2 Cross-Checks
1. **Production vs. reserves**: Cumulative production should be <80% of reserves
2. **Revenue vs. price**: Average realized price should be within ±10% of WTI
3. **Opex per BOE**: Should trend upward over time
4. **NPV/CAPEX**: Should be >0.3 for commercial projects
5. **IRR**: Should be >15% for FID decision

### 9.3 Data Quality Checks
1. **Production data**: No negative values, no impossible spikes
2. **Price data**: Within historical bounds ($20-150/bbl for oil)
3. **Cost data**: Within industry benchmarks (±30%)
4. **Decline curves**: Physically reasonable (DI < 95%/year)

---

## 10. References and Documentation

### 10.1 Primary Sources
1. **BSEE Data Portal**: https://www.data.bsee.gov/
2. **EIA Petroleum Data**: https://www.eia.gov/petroleum/data.php
3. **SEC EDGAR**: https://www.sec.gov/edgar.shtml
4. **Operator websites**: Investor relations sections

### 10.2 Industry Benchmarks
1. **Rystad Energy**: UCube database (deepwater costs)
2. **Wood Mackenzie**: Gulf of Mexico analysis
3. **IHS Markit**: Vantage production data
4. **Evaluate Energy**: Deepwater economics

### 10.3 Technical References
1. **Arps, J.J.** (1945): "Analysis of Decline Curves" (hyperbolic decline)
2. **SPE Monograph 1**: "Petroleum Reservoir Engineering"
3. **BOEM**: "Deepwater Gulf of Mexico Economic Parameters"

---

## Document Control
- **Created**: 2024-12-20
- **Last Updated**: 2024-12-20
- **Version**: 1.0.0
- **Next Review**: Upon data refresh or methodology change
- **Owner**: WorldEnergyData Analysis Team

---

## Appendix: Assumption Summary Table

| Category | Parameter | Base Case | Low Case | High Case | Source |
|----------|-----------|-----------|----------|-----------|--------|
| **Prices** |
| | Oil (WTI) | $75/bbl | $50/bbl | $100/bbl | EIA |
| | Gas (HH) | $3.50/mcf | $2.50/mcf | $5.00/mcf | EIA |
| | NGL | $30/bbl | $20/bbl | $40/bbl | Industry |
| **Fiscal** |
| | Royalty | 18.75% | 18.75% | 18.75% | BOEM |
| | Income Tax | 21% | 21% | 21% | IRS |
| **CAPEX** |
| | Host Facility | $2,000M | $1,500M | $2,500M | Disclosures |
| | Well Cost | $200M | $150M | $250M | Industry |
| | SURF per Well | $25M | $20M | $30M | Industry |
| **OPEX** |
| | Oil Opex | $15/bbl | $12/bbl | $18/bbl | Industry |
| | Gas Opex | $0.50/mcf | $0.40/mcf | $0.60/mcf | Industry |
| | Fixed Annual | $120M | $100M | $150M | Disclosures |
| **Production** |
| | Initial Rate | 10 MBOPD | 8 MBOPD | 12 MBOPD | Type Curve |
| | Initial Decline | 45%/yr | 35%/yr | 55%/yr | Type Curve |
| | EUR per Well | 12 MMBOE | 8 MMBOE | 18 MMBOE | Type Curve |
| **Financial** |
| | Discount Rate | 10% | 8% | 15% | Corporate |
| | Min IRR | 15% | - | - | Corporate |
| | Payback Target | 7 yrs | - | 10 yrs | Corporate |
