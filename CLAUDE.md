# World Energy Data

> Inherits: workspace-hub | Target: <18% (1.4KB)

## Project Focus

Global energy market data aggregation, analysis, and visualization platform.

## Tech Stack

- Python 3.11+ with uv
- Data: pandas, numpy
- Viz: Plotly (interactive HTML)
- Testing: pytest

## Project Rules

1. Data sources must include attribution and timestamp
2. Energy units standardized (BTU, MWh, barrels)
3. All visualizations interactive HTML
4. Validate against EIA/IEA formats
5. TDD mandatory — tests before implementation
6. Files under 500 lines (modular design)

## Data Governance

Data governance: see workspace-hub `docs/DATA_RESIDENCE_POLICY.md`

This repo owns **Tier 1 — Collection Data**: raw data from external public sources (APIs, web scraping, downloads). If the data comes from an external public source, it belongs here.

## Key Directories

- `src/` - Analysis modules
- `data/` - Datasets (raw/, processed/, modules/)
- `reports/` - HTML reports
- `tests/` - Test files

## Commands

```bash
uv run pytest              # Tests
uv run python -m src.main  # Run analysis
```

## Reference

- Agents: `.claude/docs/agents.md`
- Full rules: Inherited from workspace-hub/CLAUDE.md

---

*Verbose docs in `.claude/docs/`*
