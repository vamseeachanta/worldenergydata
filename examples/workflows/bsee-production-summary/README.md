# BSEE Production Summary

Offline BSEE production workflow using bundled synthetic Gulf of Mexico CSV data.

Run:

```bash
uv run python -m worldenergydata examples/workflows/bsee-production-summary/input.yml
```

Expected outputs:

- `examples/workflows/bsee-production-summary/outputs/prod_summ_bsee_production_summary.csv`
- `examples/workflows/bsee-production-summary/outputs/prod_summ_bsee_production_summary.json`
- `examples/workflows/bsee-production-summary/outputs/prod_rate_bopd_bsee_production_summary.csv`
- `examples/workflows/bsee-production-summary/outputs/prod_cumulative_mmbbl_bsee_production_summary.csv`
- `examples/workflows/bsee-production-summary/outputs/prod_all_block_WR_718.csv`
- `examples/workflows/bsee-production-summary/outputs/prod_raw_bsee_production_summary.xlsx`

Expected oil total: 90,000 bbl across 2 API12 wells.
