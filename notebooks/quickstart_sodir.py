# %% [markdown]
# # SODIR (Norwegian Continental Shelf) -- Quickstart
#
# Access Norwegian petroleum data from the SODIR (formerly NPD) public API.
# SODIR provides wellbore, field, discovery, block, and production data for
# the entire Norwegian Continental Shelf (NCS).
#
# ## Prerequisites
# - Python 3.11+
# - `requests` (for API calls)
# - pandas, matplotlib
# - No local data files required — data is fetched from the public API

# %%
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# %% [markdown]
# ## 1. About the SODIR data source
#
# SODIR publishes Norwegian Continental Shelf (NCS) petroleum data as public
# "tableview" CSV reports under `https://factpages.sodir.no/`.  The
# `worldenergydata.sodir.factpages` helper fetches these reports into pandas
# DataFrames and keeps an on-disk snapshot under `data/modules/sodir/` so the
# analysis is reproducible offline (e.g. during a demo without network access).
#
# Note: the legacy `api_client.SodirAPIClient` targets the older
# `factmaps.sodir.no` DataService endpoint, which currently returns HTTP 400.
# Use the factpages helper below for live data.

# %% [markdown]
# ## 2. Available reports
#
# The factpages helper exposes these curated NCS reports:
#
# | Key                       | SODIR report             | Description                         |
# |---------------------------|--------------------------|-------------------------------------|
# | `fields`                  | field                    | Field operator, area, hydrocarbon   |
# | `field_production_yearly` | field_production_yearly  | Per-field, per-year production       |
# | `wellbores_development`   | wellbore_development_all | Development wellbores               |
# | `discoveries`             | discovery                | NCS discoveries                     |

# %% [markdown]
# ## 3. Fetch NCS field overview
#
# `refresh=False` (default) reads the committed snapshot; pass `refresh=True`
# to pull fresh data live and update the snapshot.  If a live fetch fails it
# transparently falls back to the snapshot, so this cell never hard-fails.

# %%
from worldenergydata.sodir import factpages as fp

fields = fp.fetch_fields()  # set refresh=True for a live pull
print(f"Loaded {len(fields):,} NCS fields with {len(fields.columns)} columns")
print("\nTop operators by field count:")
print(fields["cmpLongName"].value_counts().head(8).to_string())

# %%
# Operators bar chart -- a quick read on who runs the Norwegian shelf.
top_ops = fields["cmpLongName"].value_counts().head(8)
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(top_ops.index, top_ops.values, color="steelblue")
ax.set_xlabel("Number of NCS fields operated")
ax.set_title("Top NCS Field Operators (SODIR)")
ax.invert_yaxis()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 4. NCS field production by year
#
# Per-field, per-year volumes (oil, gas, NGL, condensate, oil-equivalent) in
# million/billion standard cubic metres, straight from the live SODIR report.

# %%
prod = fp.fetch_field_production_yearly()
print(f"Loaded {len(prod):,} field-year production rows")
print(f"  Year range: {int(prod['prfYear'].min())}-{int(prod['prfYear'].max())}")

# Aggregate net oil-equivalent production per year across the sample.
oe_by_year = prod.groupby("prfYear")["prfPrdOeNetMillSm3"].sum()
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(oe_by_year.index, oe_by_year.values, marker="o", color="darkgreen")
ax.set_xlabel("Year")
ax.set_ylabel("Net oil-equivalent (MillSm3)")
ax.set_title("NCS Field Production by Year (SODIR sample)")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 5. Working with cached / exported data
#
# Snapshots are written to `data/modules/sodir/<report>.csv` on every live
# fetch and are read back automatically when `refresh=False`.  To export a
# different slice for offline analysis:
#
# ```python
# fields.to_csv("data/modules/sodir/fields.csv", index=False)
# df = pd.read_csv("data/modules/sodir/fields.csv")
# ```

# %% [markdown]
# ## 7. Scheduler integration
#
# For automated data collection, use the worldenergydata scheduler:
#
# ```bash
# # Fetch all SODIR datasets
# uv run python -m worldenergydata.scheduler --module sodir --action fetch
#
# # Or use Make
# make data-sodir
# ```

# %% [markdown]
# ## Summary
#
# This notebook covered:
# - SODIR API endpoints and available datasets
# - Initializing the API client with rate limiting
# - Fetching NCS wellbore data
# - Caching and exporting for offline use
# - Example NCS field production analysis
# - Scheduler integration for automated data collection
