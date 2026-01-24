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

## Key Directories

- `src/` - Analysis modules
- `data/` - Datasets (raw/, processed/)
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
