# %% [markdown]
# # FDAS Financial Analysis -- Quickstart
#
# Run field-development economics calculations using the FDAS module.
# This notebook is entirely computational — no data files are needed.
#
# ## Prerequisites
# - Python 3.11+
# - numpy, numpy-financial, matplotlib, pandas

# %%
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from worldenergydata.fdas.api import EconomicsQuery

econ = EconomicsQuery()

# %% [markdown]
# ## 1. Net Present Value (NPV)
#
# A simple deepwater development: $500 M upfront capex followed by 20 years
# of annual production revenue.

# %%
capex = -500  # $M invested at t=0
annual_revenue = [60] * 20  # $60 M/yr for 20 years
cashflows = [capex] + annual_revenue

npv_10 = econ.npv(cashflows, discount_rate=0.10, period="annual")
npv_08 = econ.npv(cashflows, discount_rate=0.08, period="annual")
npv_12 = econ.npv(cashflows, discount_rate=0.12, period="annual")

print(f"NPV @ 10%: ${npv_10:,.1f} M")
print(f"NPV @  8%: ${npv_08:,.1f} M")
print(f"NPV @ 12%: ${npv_12:,.1f} M")

# %% [markdown]
# ## 2. Internal Rate of Return (IRR)

# %%
period_irr, annual_irr = econ.irr(cashflows, period="annual")
print(f"Annual IRR: {annual_irr:.2%}")

# %% [markdown]
# ## 3. Modified Internal Rate of Return (MIRR)
#
# MIRR avoids the multiple-IRR problem by specifying separate financing and
# reinvestment rates.

# %%
mirr_m, mirr_a = econ.mirr(cashflows, discount_rate=0.10, reinvestment_rate=0.06)
print(f"Annual MIRR (finance=10%, reinvest=6%): {mirr_a:.2%}")

# %% [markdown]
# ## 4. Payback period

# %%
periods, years = econ.payback_period(cashflows, period="annual")
print(f"Payback: {years:.1f} years (period {periods})")

# %% [markdown]
# ## 5. All metrics at once
#
# `all_metrics()` returns a dictionary with NPV, IRR, MIRR, and payback in
# a single call.

# %%
metrics = econ.all_metrics(cashflows, discount_rate=0.10, period="annual")
for key in ["npv", "irr_annual", "mirr_annual", "payback_years"]:
    val = metrics.get(key)
    if isinstance(val, float):
        print(f"  {key}: {val:,.4f}")
    else:
        print(f"  {key}: {val}")

# %% [markdown]
# ## 6. Sensitivity analysis — NPV vs. discount rate

# %%
rates = np.arange(0.02, 0.21, 0.01)
npvs = [econ.npv(cashflows, discount_rate=r, period="annual") for r in rates]

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(rates * 100, npvs, marker="o", markersize=4)
ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
ax.fill_between(rates * 100, npvs, 0, where=[n > 0 for n in npvs],
                alpha=0.15, color="green", label="NPV > 0")
ax.fill_between(rates * 100, npvs, 0, where=[n <= 0 for n in npvs],
                alpha=0.15, color="red", label="NPV < 0")
ax.set_xlabel("Discount Rate (%)")
ax.set_ylabel("NPV ($M)")
ax.set_title("NPV Sensitivity to Discount Rate")
ax.legend()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 7. Comparing investment scenarios
#
# Compare three hypothetical field-development concepts side by side.

# %%
scenarios = {
    "Base case": {"capex": -500, "revenue": 60, "years": 20},
    "High capex / high revenue": {"capex": -800, "revenue": 110, "years": 20},
    "Low capex / low revenue": {"capex": -250, "revenue": 35, "years": 15},
}

records = []
for name, s in scenarios.items():
    cf = [s["capex"]] + [s["revenue"]] * s["years"]
    m = econ.all_metrics(cf, discount_rate=0.10, period="annual")
    records.append({
        "Scenario": name,
        "Capex ($M)": abs(s["capex"]),
        "Annual Rev ($M)": s["revenue"],
        "Years": s["years"],
        "NPV ($M)": round(m["npv"], 1),
        "IRR (%)": round((m.get("irr_annual") or 0) * 100, 1),
        "Payback (yr)": round(m.get("payback_years") or 0, 1),
    })

comparison = pd.DataFrame(records)
print(comparison.to_string(index=False))

# %% [markdown]
# ## 8. Cashflow waterfall chart

# %%
cumulative = np.cumsum(cashflows)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Bar chart of periodic cashflows
colors = ["#e74c3c" if c < 0 else "#2ecc71" for c in cashflows]
ax1.bar(range(len(cashflows)), cashflows, color=colors, edgecolor="white")
ax1.set_xlabel("Year")
ax1.set_ylabel("Cashflow ($M)")
ax1.set_title("Annual Cashflows")
ax1.axhline(0, color="gray", linewidth=0.8)

# Cumulative cashflow
ax2.plot(range(len(cumulative)), cumulative, marker="o", markersize=4, color="steelblue")
ax2.axhline(0, color="gray", linestyle="--", linewidth=0.8)
ax2.fill_between(range(len(cumulative)), cumulative, 0,
                 where=cumulative >= 0, alpha=0.15, color="green")
ax2.fill_between(range(len(cumulative)), cumulative, 0,
                 where=cumulative < 0, alpha=0.15, color="red")
ax2.set_xlabel("Year")
ax2.set_ylabel("Cumulative Cashflow ($M)")
ax2.set_title("Cumulative Cashflow")

plt.tight_layout()
plt.show()

# %% [markdown]
# ## Summary
#
# This notebook covered:
# - NPV, IRR, MIRR, and payback period calculations
# - Sensitivity analysis across discount rates
# - Scenario comparison for multiple development concepts
# - Cashflow waterfall visualization
