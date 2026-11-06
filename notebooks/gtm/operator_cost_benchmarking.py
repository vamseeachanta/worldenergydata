# %% [markdown]
# # Operator cost benchmarking from annual disclosures
#
# ## What this is
# Historical operator CAPEX seed data, derived through the FDAS disclosure API,
# and nominal sanction-cost cohorts. The HTML needs no external assets.
#
# ## What this is not yet
# The canonical annual dataset is pending in issue 334; source coverage in
# issue 343, normalization policy in issue 336, restatement lineage in issue
# 344 and calculation citation sidecars in issue 361 remain separate work.
# OPEX and reservoir/onshore comparisons are NOT_EVALUATED.
#
# Source URLs, fiscal definitions, filing editions and digests are carried by
# every seed row. Seed figures are labelled illustrative, not ingested data.
# Run: `uv run python notebooks/gtm/operator_cost_benchmarking.py`.

# %%
import os
from pathlib import Path

from worldenergydata.cost.data_collection.disclosure_seed_dataset import (
    load_seed_disclosure_records,
)
from worldenergydata.cost.data_collection.public_dataset import load_public_dataset
from worldenergydata.cost.reporting.benchmark_report import (
    build_report_facts,
    write_report,
)
from worldenergydata.fdas.api import DisclosureAnalyticsQuery

REPO_ROOT = Path(__file__).resolve().parents[2]
# Report edition is pinned to the seed retrieval date; no wall-clock calls.
REPORT_DATE = "2026-10-20"
OUT_DIR = Path(os.environ.get("OPERATOR_COST_REPORT_OUT", REPO_ROOT / "reports/gtm"))

# %% [markdown]
# ## Inputs and method
# CAPEX is nominal USD million. Company definitions differ, so no cross-company
# ranking is established. Arithmetic YoY = (current - previous) / previous,
# only for consecutive fiscal years with nonzero prior CAPEX. Qualified YoY
# requires both records to have the same upstream comparability basis.
#
# Cohorts separate region, water-depth proxy, activity and cost type. Median
# and inclusive quartiles summarize the observed nominal amounts without FX
# or inflation normalization. The NIST/SEMATECH e-Handbook section 1.3.3.7,
# Box Plot (web edition retrieved 2026-10-20), defines inner fences at
# Q1 - 1.5*(Q3-Q1) and Q3 + 1.5*(Q3-Q1). Sparse cohorts remain NOT_EVALUATED.

# %%
records = load_seed_disclosure_records()
cost_points = load_public_dataset()
operator_view = DisclosureAnalyticsQuery().operator_capex(records)
facts = build_report_facts(records, cost_points, REPORT_DATE)
for row in operator_view:
    print(
        f"{row.operator} {row.fiscal_year}: {row.reported_capex_usd_mm:,.1f} USD million"
    )

# %% [markdown]
# ## Worked example: input, method, answer
# Chevron Annual Report 2023, Financial Highlights, PDF page 22, reports
# 2022 CAPEX of 11,974 and 2023 CAPEX of 15,829 USD million.
# Independent subtraction: 15,829 - 11,974 = 3,855 USD million.
# Relative change: 3,855 / 11,974 gives 32.2% (displayed to one decimal).
# This is an unqualified arithmetic change; comparability is not established.

# %%
example = next(
    row
    for row in operator_view
    if row.operator == "Chevron" and row.fiscal_year == 2023
)
print(
    f"Worked example: {example.yoy_delta_usd_mm:,.1f} USD million; "
    f"{example.yoy_delta_pct:.1%} arithmetic change (ungated)."
)
outputs = write_report(OUT_DIR, REPORT_DATE)
print("Generated: " + ", ".join(path.name for path in outputs.values()))
