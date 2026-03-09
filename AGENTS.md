---
purpose: Global energy market data aggregation and analysis — BSEE, EIA, drilling, economics
entry_points: [src/worldenergydata/bsee/, src/worldenergydata/eia/, src/worldenergydata/cli/]
test_command: "PYTHONPATH='src:../assetutilities/src' uv run python -m pytest --noconftest"
depends_on: [assetutilities]
maturity: beta
---
# worldenergydata

Contract: ../AGENTS.md | Source: src/worldenergydata/
Key modules: bsee/, eia/, drilling/, economics/, analysis/, cli/
Note: BSEE binary data (~300 MB) not in git — run scripts/refresh_bsee_all.py after clone
