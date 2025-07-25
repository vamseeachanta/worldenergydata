# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2025-07-25-npv-calculation-accuracy/spec.md

> Created: 2025-07-25
> Status: Ready for Implementation

## Tasks

- [x] 1. Analyze and Document Current NPV Discrepancy Sources
  - [x] 1.1 Write comprehensive tests for current NPV implementation to isolate discrepancy sources
  - [x] 1.2 Create detailed comparison between current implementation and Excel NPV methodology
  - [x] 1.3 Document specific calculation differences (period timing, discount rate application, cash flow construction)
  - [x] 1.4 Verify all tests pass for current implementation baseline

- [ ] 2. Implement Excel-Aligned NPV Calculation Engine
  - [ ] 2.1 Write tests for new Excel-aligned NPV function with known benchmark results
  - [ ] 2.2 Create custom NPV function that exactly mirrors Excel's NPV formula
  - [ ] 2.3 Implement proper period timing (Period 0 for CAPEX, Period 1+ for operations)
  - [ ] 2.4 Add comprehensive logging for cash flow components and discount rate application
  - [ ] 2.5 Verify all tests pass for new NPV implementation

- [ ] 3. Fix Cash Flow Construction and Data Alignment  
  - [ ] 3.1 Write tests for cash flow component calculation (revenue, OPEX, net cash flow)
  - [ ] 3.2 Ensure oil price data exactly matches Excel analysis source
  - [ ] 3.3 Verify production data alignment with Excel analysis periods
  - [ ] 3.4 Implement cash flow validation and comparison utilities
  - [ ] 3.5 Verify all tests pass for cash flow construction

- [ ] 4. Create NPV Accuracy Validation Framework
  - [ ] 4.1 Write automated tests comparing NPV results against Excel benchmarks
  - [ ] 4.2 Implement benchmark validation for multiple discount rates (8%, 10%, 12%)
  - [ ] 4.3 Create test scenarios for different CAPEX and oil price configurations
  - [ ] 4.4 Add performance benchmarking vs previous implementation
  - [ ] 4.5 Verify all validation tests achieve <20% variance from Excel results

- [ ] 5. Integration and Documentation
  - [ ] 5.1 Write integration tests for complete NPV analysis workflow
  - [ ] 5.2 Update existing NPV calculation method in ProductionAPI12Analysis class
  - [ ] 5.3 Ensure backward compatibility with existing configuration files
  - [ ] 5.4 Create documentation explaining NPV alignment methodology and remaining variance sources
  - [ ] 5.5 Verify all integration tests pass and NPV accuracy requirements are met