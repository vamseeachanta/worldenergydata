# Quickstart Notebooks

Percent-format Python scripts (`# %%` cells) that work in VS Code, JupyterLab, or any Jupytext-compatible editor.

## Notebooks

| File | Module | Description |
|------|--------|-------------|
| `quickstart_bsee.py` | BSEE | Gulf of Mexico wells, water depths, operator analysis |
| `quickstart_fdas.py` | FDAS | NPV, IRR, MIRR, payback, sensitivity analysis |
| `quickstart_marine_safety.py` | Marine Safety | Fatality, foundering, and hatch incident analysis |
| `quickstart_sodir.py` | SODIR | Norwegian Continental Shelf API and field data |
| `quickstart_eia.py` | EIA | US petroleum production and state-level trends |
| `lease_npv_walkthrough.py` | BSEE + FDAS | End-to-end: real BSEE lease → dev-system classification → cashflow → NPV/IRR/MIRR/payback → citations panel (#358) |

## How to run

- **VS Code**: Open file, click "Run Cell" above any `# %%` marker
- **JupyterLab**: `pip install jupytext`, then open `.py` files as notebooks
- **Command line**: `python notebooks/quickstart_fdas.py` (runs all cells sequentially)

## Prerequisites

```bash
pip install pandas matplotlib numpy numpy-financial
# For API notebooks (SODIR, EIA): pip install requests
# For EIA: export EIA_API_KEY=your_key
```

BSEE and Marine Safety notebooks load CSV files from `data/modules/` and work without additional setup.
FDAS is purely computational and needs no data files.
SODIR and EIA fetch from public APIs and require network access (or cached data).
