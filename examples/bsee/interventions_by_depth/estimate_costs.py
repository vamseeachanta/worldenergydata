"""Transparent source-year scenario arithmetic; no escalation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd
import yaml


def event_cost(spread_dayrate, duration_days, mobilisation_usd):
    values = (spread_dayrate, duration_days, mobilisation_usd)
    if any(not math.isfinite(float(v)) or float(v) < 0 for v in values):
        raise ValueError("cost inputs must be finite and nonnegative")
    return spread_dayrate * duration_days + mobilisation_usd


def estimate(basis):
    rows = []
    for scenario in basis["scenarios"]:
        row = {
            k: scenario[k]
            for k in (
                "scenario_id",
                "access_type",
                "applicability",
                "event",
                "asset",
                "dollar_year",
                "pricing_method",
            )
        }
        for case in ("low", "base", "high"):
            if scenario["pricing_method"] == "not priced":
                row[case + "_usd"] = float("nan")
            elif scenario["pricing_method"] == "published total":
                row[case + "_usd"] = scenario[case]["published_cost"]["value"]
            else:
                inputs = scenario[case]
                row[case + "_usd"] = event_cost(
                    *(
                        inputs[k]["value"]
                        for k in ("spread_dayrate", "duration", "mobilisation")
                    )
                )
        if (
            scenario["pricing_method"] != "not priced"
            and not row["low_usd"] <= row["base_usd"] <= row["high_usd"]
        ):
            raise ValueError("scenario ranges must increase")
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--basis", type=Path, default=Path(__file__).with_name("cost_basis.yml")
    )
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    basis = yaml.safe_load(a.basis.read_text(encoding="utf-8"))
    costs = estimate(basis)
    a.out.mkdir(parents=True, exist_ok=True)
    costs.to_csv(a.out / "cost_table.csv", index=False, lineterminator="\n")
    pd.DataFrame(basis["published_pa_comparators"]).to_csv(
        a.out / "published_pa_comparators.csv", index=False, lineterminator="\n"
    )
    print(json.dumps({"cost_scenarios": len(costs), "escalation": False}))
