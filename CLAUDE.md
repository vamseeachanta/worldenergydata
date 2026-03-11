# World Energy Data
> Inherits workspace-hub | Python 3.11+ / pandas / Plotly / pytest

## Rules
1. Data attribution + timestamp required | Units: BTU/MWh/barrels standardized
2. All visualizations: interactive HTML | Validate EIA/IEA formats
3. TDD mandatory | Files ≤500 lines | BSEE binary (~300MB) not in git — run `make data`

## Data Tier
Tier 1 — Collection: raw public-source data.
Governance: `docs/DATA_RESIDENCE_POLICY.md` | Local data: `docs/data/LOCAL_DATA_PATTERN.md`

## Commands
`uv run pytest` | `uv run python -m src.main`

## Dirs
`src/` `data/{raw,processed,modules}/` `reports/` `tests/`
> Full rules inherited from workspace-hub/CLAUDE.md | Agents: `.claude/docs/agents.md`
