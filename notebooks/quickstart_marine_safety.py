# %% [markdown]
# # Marine Safety Incidents -- Quickstart
#
# Analyze marine safety incident data from CSV files included in the
# repository.  The repo ships three small curated datasets covering
# fatalities, foundering events, and hatch-related incidents.
#
# ## Prerequisites
# - Python 3.11+
# - pandas, matplotlib
# - Data files in `data/modules/marine_safety/input/` (included in the repo)

# %%
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "modules"
    / "marine_safety"
    / "input"
)

# %% [markdown]
# ## 1. Load incident datasets
#
# Three CSV files are available without running any data pipelines.

# %%
fatalities = pd.read_csv(DATA_DIR / "fatality_incidents.csv")
foundering = pd.read_csv(DATA_DIR / "foundering_incidents.csv")
hatch = pd.read_csv(DATA_DIR / "hatch_incidents.csv")

print(f"Fatality incidents:   {len(fatalities)}")
print(f"Foundering incidents: {len(foundering)}")
print(f"Hatch incidents:      {len(hatch)}")

# %%
fatalities.head()

# %% [markdown]
# ## 2. Fatality analysis — causes of death

# %%
cause_counts = fatalities["cause_of_death"].value_counts()

fig, ax = plt.subplots(figsize=(10, 5))
cause_counts.plot.barh(ax=ax, color="indianred")
ax.set_xlabel("Number of Incidents")
ax.set_title("Marine Fatalities by Cause of Death")
ax.invert_yaxis()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 3. Fatality timeline

# %%
fatalities["date"] = pd.to_datetime(fatalities["date"], errors="coerce")
fatalities["month"] = fatalities["date"].dt.to_period("M")

monthly = fatalities.groupby("month")["fatalities"].sum()

fig, ax = plt.subplots(figsize=(10, 4))
monthly.plot(kind="bar", ax=ax, color="steelblue", edgecolor="white")
ax.set_xlabel("Month")
ax.set_ylabel("Fatalities")
ax.set_title("Monthly Fatality Count")
ax.set_xticklabels([str(p) for p in monthly.index], rotation=45, ha="right")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 4. Foundering incidents
#
# Foundering means a vessel sinking or capsizing.

# %%
foundering["date"] = pd.to_datetime(foundering["date"], errors="coerce")
print(f"Total foundering fatalities: {foundering['fatalities'].sum()}")
foundering[["incident_id", "date", "vessel_name", "fatalities", "location"]]

# %% [markdown]
# ## 5. Hatch-related incidents by severity

# %%
severity_counts = hatch["severity"].value_counts()

fig, ax = plt.subplots(figsize=(7, 5))
colors = {
    "Critical": "#e74c3c",
    "High": "#e67e22",
    "Medium": "#f1c40f",
    "Low": "#2ecc71",
}
bar_colors = [colors.get(s, "gray") for s in severity_counts.index]
severity_counts.plot.bar(ax=ax, color=bar_colors, edgecolor="white")
ax.set_xlabel("Severity")
ax.set_ylabel("Number of Incidents")
ax.set_title("Hatch Incidents by Severity")
ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 6. Combined overview
#
# Merge all three datasets into a single view with a common category column.

# %%
fatalities_slim = fatalities[
    ["incident_id", "date", "vessel_name", "description"]
].copy()
fatalities_slim["category"] = "Fatality"

foundering_slim = foundering[
    ["incident_id", "date", "vessel_name", "description"]
].copy()
foundering_slim["category"] = "Foundering"

hatch_slim = hatch[["incident_id", "date", "vessel_name", "description"]].copy()
hatch_slim["category"] = "Hatch"

combined = pd.concat([fatalities_slim, foundering_slim, hatch_slim], ignore_index=True)
combined["date"] = pd.to_datetime(combined["date"], errors="coerce")

fig, ax = plt.subplots(figsize=(8, 4))
combined["category"].value_counts().plot.bar(
    ax=ax, color=["indianred", "steelblue", "goldenrod"]
)
ax.set_ylabel("Number of Incidents")
ax.set_title("Incidents by Category")
ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 7. Using the query API (optional)
#
# The marine safety query API connects to the full SQLite database
# (requires running the data pipeline first):
#
# ```python
# import worldenergydata as wed
#
# # Query across all sources
# df = wed.marine_safety_api.incidents.query(source="maib", year=2022)
#
# # Multi-source, multi-year query
# df = wed.marine_safety_api.incidents.query(
#     vessel_type="tanker", start_year=2020, end_year=2023
# )
#
# # Trend analysis
# trends = wed.marine_safety_api.incidents.trends(df)
#
# # Risk hotspots
# hotspots = wed.marine_safety_api.incidents.risk_hotspots(df)
# ```

# %% [markdown]
# ## Summary
#
# This notebook covered:
# - Loading three marine safety CSV datasets
# - Fatality cause analysis and timeline
# - Foundering event overview
# - Hatch incident severity classification
# - Combined incident overview
# - How to use the query API for full-database analysis
