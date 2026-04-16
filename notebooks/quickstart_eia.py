# %% [markdown]
# # EIA (US Energy Information Administration) -- Quickstart
#
# Access US energy statistics from the EIA API v2.  The EIA provides weekly
# petroleum supply/demand data, natural gas storage reports, state-level
# production, and international energy data.
#
# ## Prerequisites
# - Python 3.11+
# - pandas, matplotlib, requests
# - An EIA API key (free from https://www.eia.gov/opendata/register.php)
# - Set the environment variable: `export EIA_API_KEY=your_key_here`

# %%
import os

import matplotlib.pyplot as plt
import pandas as pd

# %% [markdown]
# ## 1. Check API key
#
# The EIA API v2 requires a free API key.

# %%
api_key = os.environ.get("EIA_API_KEY")
if api_key:
    print(f"EIA API key found ({api_key[:4]}...{api_key[-4:]})")
else:
    print("EIA_API_KEY not set.")
    print("Get a free key at: https://www.eia.gov/opendata/register.php")
    print("Then: export EIA_API_KEY=your_key_here")

# %% [markdown]
# ## 2. Available endpoints
#
# The worldenergydata EIA client covers these weekly feeds:
#
# | Endpoint                        | Description                           |
# |---------------------------------|---------------------------------------|
# | `petroleum/sum/snd/w`           | Weekly petroleum status (crude, stocks, imports) |
# | `natural-gas/stor/sum/dcu/nus/w`| Weekly natural gas storage            |
#
# The `eia_us` module adds:
# - State-level production data
# - Basin-level production and decline analysis
# - Drilling productivity reports
# - International country production

# %% [markdown]
# ## 3. Using the EIA feed client

# %%
try:
    from worldenergydata.eia.client import EIAFeedClient

    if api_key:
        client = EIAFeedClient(api_key=api_key)
        print("EIA client initialized successfully")
    else:
        print("Skipping client init — no API key")
        print("Set EIA_API_KEY to enable live data fetching")
except ImportError as exc:
    print(f"Could not import EIA client: {exc}")
except Exception as exc:
    print(f"Client error: {exc}")

# %% [markdown]
# ## 4. Fetching weekly petroleum data
#
# The code below fetches the most recent weekly petroleum status report.
# It is wrapped in try/except so the notebook runs cleanly without an API
# key.

# %%
try:
    if api_key:
        from worldenergydata.eia.client import EIAFeedClient, PETROLEUM_WEEKLY_PATH

        client = EIAFeedClient(api_key=api_key)
        data = client.fetch(PETROLEUM_WEEKLY_PATH, params={"length": 52})

        if data:
            df = pd.DataFrame(data)
            print(f"Fetched {len(df)} weekly petroleum records")
            df.head()
        else:
            print("No data returned")
    else:
        print("Skipped — set EIA_API_KEY to fetch live data")
except Exception as exc:
    print(f"Fetch error: {exc}")
    print("This is expected without a valid API key or network access.")

# %% [markdown]
# ## 5. Example: US crude oil production trends
#
# Since live data requires an API key, here is a synthetic example showing
# the type of analysis the EIA module supports.

# %%
# Synthetic US crude production data (annual, thousand barrels per day)
us_crude = pd.DataFrame({
    "year": list(range(2010, 2026)),
    "production_kbd": [
        5482, 5646, 6506, 7441, 8774, 9431, 8853, 9356,
        10964, 12247, 11316, 11254, 11886, 12927, 13201, 13400,
    ],
})

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(us_crude["year"], us_crude["production_kbd"], marker="o", color="steelblue")
ax.fill_between(us_crude["year"], us_crude["production_kbd"], alpha=0.15, color="steelblue")
ax.set_xlabel("Year")
ax.set_ylabel("Production (kbd)")
ax.set_title("US Crude Oil Production (EIA Data)")
ax.set_ylim(bottom=0)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 6. State-level production
#
# The `eia_us` module provides state-level breakdowns:
#
# ```python
# from worldenergydata.eia_us.production.state_production import StateProduction
#
# sp = StateProduction(api_key=api_key)
# df = sp.fetch(state="TX", start_year=2020)
# ```

# %%
# Synthetic top producing states
states = pd.DataFrame({
    "state": ["Texas", "New Mexico", "North Dakota", "Alaska", "Colorado",
              "Oklahoma", "California", "Wyoming", "Louisiana", "Utah"],
    "production_kbd": [5600, 1900, 1200, 440, 430, 380, 340, 250, 105, 100],
})

fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(states["state"], states["production_kbd"], color="steelblue")
ax.set_xlabel("Production (kbd)")
ax.set_title("Top 10 US Oil-Producing States (EIA Estimate)")
ax.invert_yaxis()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 7. Basin decline analysis
#
# ```python
# from worldenergydata.eia_us.analysis.basin_decline import BasinDeclineAnalysis
#
# bda = BasinDeclineAnalysis(api_key=api_key)
# results = bda.analyze(basin="Permian", vintage_years=[2020, 2021, 2022])
# ```

# %% [markdown]
# ## 8. Automated ingestion
#
# For scheduled data collection:
#
# ```bash
# # Ingest latest weekly petroleum data
# uv run python -m worldenergydata.eia.ingestion_runner
#
# # Or via Make
# make data-eia
# ```

# %% [markdown]
# ## Summary
#
# This notebook covered:
# - EIA API key setup and client initialization
# - Weekly petroleum and natural gas data endpoints
# - US crude oil production trends
# - State-level and basin-level analysis modules
# - Automated ingestion for scheduled updates
