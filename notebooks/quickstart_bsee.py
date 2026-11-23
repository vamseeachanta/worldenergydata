# %% [markdown]
# # BSEE Data -- Quickstart
#
# Explore Gulf of Mexico well and production data from the Bureau of Safety
# and Environmental Enforcement (BSEE).  This notebook loads CSV files
# shipped in the repository so it works without running `make data`.
#
# ## Prerequisites
# - Python 3.11+
# - pandas, matplotlib
# - Data files in `data/modules/bsee/current/` (included in the repo)

# %%
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Resolve repo-relative data path
DATA_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "modules" / "bsee" / "current"
)

# %% [markdown]
# ## 1. Load well data
#
# The `well_data.csv` file contains ~57 000 OCS well records with location,
# depth, operator, and status information.

# %%
wells = pd.read_csv(DATA_DIR / "wells" / "well_data.csv")
print(f"Loaded {len(wells):,} well records with {wells.shape[1]} columns")
wells.head()

# %%
print("Columns:", list(wells.columns))

# %% [markdown]
# ## 2. Water depth distribution
#
# Deepwater wells (> 1 000 ft) dominate the modern Gulf of Mexico portfolio.

# %%
fig, ax = plt.subplots(figsize=(10, 5))
wells["WATER_DEPTH"].dropna().hist(bins=60, ax=ax, edgecolor="white")
ax.set_xlabel("Water Depth (ft)")
ax.set_ylabel("Number of Wells")
ax.set_title("BSEE Wells — Water Depth Distribution")
ax.axvline(1000, color="red", linestyle="--", label="Deepwater threshold (1 000 ft)")
ax.legend()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 3. Top operators by well count

# %%
top_operators = wells["COMPANY_NAME"].value_counts().head(15)

fig, ax = plt.subplots(figsize=(10, 6))
top_operators.plot.barh(ax=ax, color="steelblue")
ax.set_xlabel("Number of Wells")
ax.set_title("Top 15 Operators by Well Count")
ax.invert_yaxis()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 4. Spud activity over time
#
# Parse spud dates and look at drilling activity by year.

# %%
wells["spud_date"] = pd.to_datetime(wells["WELL_SPUD_DATE"], errors="coerce")
wells["spud_year"] = wells["spud_date"].dt.year

spud_by_year = wells.dropna(subset=["spud_year"]).groupby("spud_year").size()
spud_by_year = spud_by_year[spud_by_year.index >= 1980]

fig, ax = plt.subplots(figsize=(10, 5))
spud_by_year.plot(ax=ax, marker="o", markersize=3)
ax.set_xlabel("Year")
ax.set_ylabel("Wells Spudded")
ax.set_title("BSEE — Annual Well Spud Activity")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 5. Deepwater vs. shelf wells

# %%
wells["depth_class"] = pd.cut(
    wells["WATER_DEPTH"],
    bins=[0, 500, 1000, 5000, 15000],
    labels=[
        "Shallow (<500 ft)",
        "Mid-water (500-1000 ft)",
        "Deepwater (1000-5000 ft)",
        "Ultra-deep (>5000 ft)",
    ],
)
depth_counts = wells["depth_class"].value_counts().sort_index()

fig, ax = plt.subplots(figsize=(8, 5))
depth_counts.plot.bar(ax=ax, color=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"])
ax.set_ylabel("Number of Wells")
ax.set_title("Wells by Water Depth Classification")
ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 6. Production data (small sample)
#
# The repo includes a small production CSV (~100 rows).  Full production
# data requires `make data` to download BSEE binary files.

# %%
prod = pd.read_csv(DATA_DIR / "production" / "production.csv")
print(f"Production sample: {len(prod)} records")
prod.head()

# %% [markdown]
# ## 7. Using the query API (optional)
#
# If you have installed the package and run `make data`, you can use the
# query API for richer access:
#
# ```python
# import worldenergydata as wed
#
# df = wed.bsee.production.query(year=2022)
# df = wed.bsee.wells.query(area_code="MC")
# df = wed.bsee.companies.query(name="Shell")
# summary = wed.bsee.production.annual_summary(2022)
# ```

# %% [markdown]
# ## Summary
#
# This notebook covered:
# - Loading BSEE well data from CSV
# - Water depth distribution analysis
# - Top operators and drilling trends
# - Deepwater vs. shelf classification
# - How to use the query API for deeper analysis
