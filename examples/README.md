# WorldEnergyData Examples

## Safety Classification

| File | Safety Class | Notes |
|------|-------------|-------|
| `fdas_complete_workflow.py` | `fixture-only` | Pure financial calculations, no data or network |
| `validation_examples.py` | `fixture-only` | Validation logic only, no external I/O |
| `marine_safety_cause_visualization_demo.py` | `data-required` | Requires local marine safety DB |
| `llm_classification_demo.py` | `unsafe-unbounded` | Downloads ~1.6 GB BART model; set `WORLDENERGYDATA_RUN_LLM_EXAMPLES=1` |
| `marine_safety/generate_cause_report.py` | `data-required` | Requires local marine safety DB |
| `marine_safety/llm_detection_example.py` | `unsafe-unbounded` | Downloads large LLM model; set `WORLDENERGYDATA_RUN_LLM_EXAMPLES=1` |
| `marine_safety/batch_llm_processing.py` | `unsafe-unbounded` | Downloads large LLM model; set `WORLDENERGYDATA_RUN_LLM_EXAMPLES=1` |

## Safety Classes

| Class | Meaning |
|-------|---------|
| `bounded-safe` | No data, network, or credentials required |
| `fixture-only` | Uses bundled YAML/static config only |
| `data-required` | Requires local dataset (run `make data` first) |
| `credential-required` | Requires API key or credentials |
| `network-required` | Makes outbound network requests |
| `server-starting` | Starts a local HTTP/web server |
| `unsafe-unbounded` | Downloads large artifacts or has no size bound |

## Running LLM Examples

LLM examples are gated behind an environment variable to prevent accidental
large model downloads:

```bash
WORLDENERGYDATA_RUN_LLM_EXAMPLES=1 python examples/llm_classification_demo.py
WORLDENERGYDATA_RUN_LLM_EXAMPLES=1 python examples/marine_safety/llm_detection_example.py
WORLDENERGYDATA_RUN_LLM_EXAMPLES=1 python examples/marine_safety/batch_llm_processing.py
```

Without the variable set, these scripts print a skip message and exit 0.

## Quick Start

```bash
# Safe — no prerequisites
uv run python examples/fdas_complete_workflow.py
uv run python examples/validation_examples.py

# Requires local data (run `make data` first)
uv run python examples/marine_safety/generate_cause_report.py
uv run python examples/marine_safety_cause_visualization_demo.py
```
