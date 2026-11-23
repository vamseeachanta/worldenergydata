# BSEE Well Comparison

Offline BSEE production comparison workflow using bundled synthetic Gulf of Mexico CSV data.

Run:

```bash
uv run python -m worldenergydata examples/workflows/bsee-well-comparison/input.yml
```

Expected outputs:

- `examples/workflows/bsee-well-comparison/outputs/prod_summ_bsee_well_comparison.csv`
- `examples/workflows/bsee-well-comparison/outputs/prod_summ_bsee_well_comparison.json`
- `examples/workflows/bsee-well-comparison/outputs/prod_rate_bopd_bsee_well_comparison.csv`
- `examples/workflows/bsee-well-comparison/outputs/prod_cumulative_mmbbl_bsee_well_comparison.csv`
- `examples/workflows/bsee-well-comparison/outputs/prod_all_block_MC_778.csv`
- `examples/workflows/bsee-well-comparison/outputs/prod_raw_bsee_well_comparison.xlsx`

Expected oil total: 139,000 bbl across 3 API12 wells.
