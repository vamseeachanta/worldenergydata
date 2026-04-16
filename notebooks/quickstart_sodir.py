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
# ## 1. About the SODIR API
#
# SODIR exposes a REST API at `https://factmaps.sodir.no/` with endpoints
# for wellbores, fields, discoveries, blocks, surveys, and production.
# The `worldenergydata` package includes a client with rate limiting and
# caching built in.

# %% [markdown]
# ## 2. Available endpoints
#
# The SODIR module covers these datasets:
#
# | Endpoint      | Table ID | Description                              |
# |---------------|----------|------------------------------------------|
# | blocks        | 1001     | NCS block information                    |
# | wellbores     | 5000     | Wellbore drilling and completion data    |
# | fields        | 2000     | Field-level production and reserves      |
# | discoveries   | 3000     | Discovery details                        |
# | surveys       | 4000     | Seismic survey metadata                  |

# %% [markdown]
# ## 3. Fetching data with the API client
#
# Below is a working example that fetches wellbore data.  If the SODIR API
# is unreachable (corporate firewall, offline), the cell will print an
# error message instead of failing.

# %%
try:
    from worldenergydata.sodir.api_client import SodirAPIClient

    client = SodirAPIClient(
        base_url="https://factmaps.sodir.no",
        rate_limit=5,
        cache_ttl=86400,
    )
    print("SODIR API client initialized")
    print(f"  Base URL: {client.base_url}")
    print("  Ready to query wellbores, fields, discoveries, blocks")
except ImportError as exc:
    print(f"Could not import SODIR client: {exc}")
    print("Install with: pip install worldenergydata")
except Exception as exc:
    print(f"Client init error: {exc}")

# %% [markdown]
# ## 4. Example: fetch NCS wellbores
#
# The snippet below shows how to fetch and explore wellbore data.  It is
# wrapped in a try/except so the notebook does not fail when run offline.

# %%
try:
    from worldenergydata.sodir.datasets import SodirDatasets

    datasets = SodirDatasets(client)
    wellbores_df = datasets.get_wellbores()

    if wellbores_df is not None and not wellbores_df.empty:
        print(f"Fetched {len(wellbores_df):,} NCS wellbores")
        print("Columns:", list(wellbores_df.columns[:10]), "...")
        display_df = wellbores_df.head()
    else:
        print("No wellbore data returned (API may be unreachable)")
        display_df = pd.DataFrame({"note": ["Run when connected to internet"]})

    display_df
except Exception as exc:
    print(f"Skipped live fetch: {exc}")
    print("This is expected when running offline or without network access.")

# %% [markdown]
# ## 5. Working with cached / exported data
#
# After a successful fetch, SODIR data is cached under `data/sodir/cache/`.
# You can also export to CSV for offline analysis:
#
# ```python
# # Export to CSV
# wellbores_df.to_csv("data/sodir/exports/wellbores.csv", index=False)
#
# # Reload later
# df = pd.read_csv("data/sodir/exports/wellbores.csv")
# ```

# %% [markdown]
# ## 6. NCS production analysis (when data is available)
#
# Once you have field production data, common analyses include:

# %%
# Synthetic example showing the kind of analysis you can do with NCS data
ncs_example = pd.DataFrame({
    "field": ["Johan Sverdrup", "Troll", "Ekofisk", "Snorre", "Gullfaks"],
    "peak_oil_kbd": [755, 175, 370, 220, 250],
    "start_year": [2019, 1995, 1971, 1992, 1986],
    "water_depth_m": [115, 330, 75, 350, 220],
})

fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(ncs_example["field"], ncs_example["peak_oil_kbd"], color="steelblue")
ax.set_xlabel("Peak Oil Production (kbd)")
ax.set_title("Major NCS Fields — Peak Production Rates")
ax.invert_yaxis()
plt.tight_layout()
plt.show()

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
