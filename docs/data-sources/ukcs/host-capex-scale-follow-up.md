# Follow-on: FDAS host capital unit conversion

Recorded for issue #797 / PR #1979, review finding 2. No remote issue was posted.

`CashflowEngine.generate_monthly_cashflow` reads `HOST_CAPEX_MM` in million USD.
`calculate_host_capex_timing` divides that value over 24 monthly rows, including
assumed first oil and the preceding 23 months. These values then populate
`MonthlyCashflowModel.host_capex_usd` without multiplication by one million.
For the unknown-depth UKCS fallback, 300 million USD therefore enters the
pre-tax cashflow as only 300 USD. The first selected production observation is
used as assumed first oil; it is not evidence of the field's development date.

The report now discloses the fallback, default host assumption, applied USD cost,
monthly window and variable opex rate. The saved live report reconciles as
338,433,442.845825 gross revenue minus 54,149,350.855332 variable opex minus
300 host capital, giving 284,283,791.990493 net cashflow (pre-tax USD).
Explicit drilling and development capital inputs remain absent.

A separate FDAS correction should establish one unit contract for host-capital
timing and consumers, inspect the analogous drilling/facilities conversion
paths, and update dependent reference outputs. Regression acceptance should
require 300 million USD to allocate to 300,000,000 USD in total, reconcile each
monthly cashflow, and preserve the intended schedule. Include UKCS dry and
unknown-depth cases and all other callers of this shared engine. The current
report regressions intentionally expose the existing scale defect; update
their expected costs when that correction lands. After-tax economics remain
deferred to #736.
