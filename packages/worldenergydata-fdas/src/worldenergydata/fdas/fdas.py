"""Engine router for offline FDAS durable workflows."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from worldenergydata.fdas.api import EconomicsQuery


class FDAS:
    """Route FDAS economics workflows from YAML engine configuration."""

    module_name = "fdas"

    def router(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Run the configured FDAS analysis and attach output metadata."""
        analysis_type = cfg.get("analysis", {}).get("type", "field_npv")
        cfg.setdefault(self.module_name, {})
        cfg[self.module_name].update({"analysis": cfg.get("analysis", {}).copy()})

        if analysis_type == "field_npv":
            outputs = self._run_field_npv(cfg)
        elif analysis_type == "npv_sensitivity":
            outputs = self._run_npv_sensitivity(cfg)
        else:
            raise ValueError(f"Unsupported FDAS analysis type: {analysis_type}")

        cfg[self.module_name]["status"] = "completed"
        cfg[self.module_name]["outputs"] = outputs
        return cfg

    def _run_field_npv(self, cfg: dict[str, Any]) -> dict[str, str]:
        cashflow_cfg = cfg.get("cashflow", {})
        cashflows = self._read_cashflows(cfg, cashflow_cfg)
        period = cashflow_cfg.get("period", "annual")
        discount_rate = float(cashflow_cfg.get("discount_rate", 0.10))

        metrics = EconomicsQuery.all_metrics(
            cashflows,
            discount_rate=discount_rate,
            period=period,
        )
        label = cfg.get("meta", {}).get("label", "fdas_field_npv")
        result_folder = self._result_folder(cfg)

        field = cfg.get("field", {})
        summary_path = result_folder / f"{label}_summary.json"
        metrics_path = result_folder / f"{label}_metrics.csv"

        summary = {
            "field": field,
            "cashflow": {
                "period": period,
                "discount_rate": discount_rate,
                "count": int(len(cashflows)),
            },
            "metrics": self._json_safe(metrics),
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        metrics_row = {
            "field_name": field.get("name", ""),
            "period": period,
            "discount_rate": discount_rate,
            "npv": metrics["npv"],
            "npv_trimmed": metrics["npv_trimmed"],
            "irr_annual": metrics["irr_annual"],
            "mirr_annual": metrics["mirr_annual"],
            "payback_years": metrics["payback_years"],
        }
        pd.DataFrame([metrics_row]).to_csv(metrics_path, index=False)

        return {
            "summary_json": str(summary_path),
            "metrics_csv": str(metrics_path),
        }

    def _run_npv_sensitivity(self, cfg: dict[str, Any]) -> dict[str, str]:
        cashflow_cfg = cfg.get("cashflow", {})
        sensitivity_cfg = cfg.get("sensitivity", {})
        period = cashflow_cfg.get("period", "annual")
        discount_rate = float(cashflow_cfg.get("discount_rate", 0.10))

        base_capex = float(sensitivity_cfg["base_capex"])
        oil_price = float(sensitivity_cfg["oil_price"])
        production = float(sensitivity_cfg["production_bbl_per_period"])
        opex = float(sensitivity_cfg["opex_per_period"])
        periods = int(sensitivity_cfg["periods"])

        rows = []
        for price_multiplier in sensitivity_cfg["price_multipliers"]:
            for rate_multiplier in sensitivity_cfg["rate_multipliers"]:
                net_operating_cashflow = (
                    oil_price
                    * float(price_multiplier)
                    * production
                    * float(rate_multiplier)
                    - opex
                )
                cashflows = np.array(
                    [-base_capex] + [net_operating_cashflow] * periods,
                    dtype=float,
                )
                metrics = EconomicsQuery.all_metrics(
                    cashflows,
                    discount_rate=discount_rate,
                    period=period,
                )
                rows.append(
                    {
                        "price_multiplier": float(price_multiplier),
                        "rate_multiplier": float(rate_multiplier),
                        "net_operating_cashflow": net_operating_cashflow,
                        "npv": metrics["npv"],
                        "irr_annual": metrics["irr_annual"],
                        "payback_years": metrics["payback_years"],
                    }
                )

        matrix = pd.DataFrame(rows).sort_values(["price_multiplier", "rate_multiplier"])
        label = cfg.get("meta", {}).get("label", "fdas_npv_sensitivity")
        result_folder = self._result_folder(cfg)
        matrix_path = result_folder / f"{label}_matrix.csv"
        summary_path = result_folder / f"{label}_summary.json"

        matrix.to_csv(matrix_path, index=False)
        best_case = matrix.loc[matrix["npv"].idxmax()].to_dict()
        worst_case = matrix.loc[matrix["npv"].idxmin()].to_dict()
        summary = {
            "field": cfg.get("field", {}),
            "case_count": int(len(matrix)),
            "best_case": self._json_safe(best_case),
            "worst_case": self._json_safe(worst_case),
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        return {
            "matrix_csv": str(matrix_path),
            "summary_json": str(summary_path),
        }

    def _read_cashflows(
        self,
        cfg: dict[str, Any],
        cashflow_cfg: dict[str, Any],
    ) -> np.ndarray:
        if cashflow_cfg.get("source", "csv") != "csv":
            raise ValueError(
                "FDAS durable workflows currently require cashflow.source=csv"
            )

        csv_path = self._input_root(cfg) / cashflow_cfg["file"]
        df = pd.read_csv(csv_path)
        if "cashflow" not in df.columns:
            raise ValueError(f"FDAS cashflow CSV missing 'cashflow' column: {csv_path}")
        return pd.to_numeric(df["cashflow"], errors="raise").to_numpy(dtype=float)

    def _input_root(self, cfg: dict[str, Any]) -> Path:
        return Path(cfg["Analysis"]["analysis_root_folder"])

    def _result_folder(self, cfg: dict[str, Any]) -> Path:
        result_folder = Path(cfg["Analysis"]["result_folder"])
        result_folder.mkdir(parents=True, exist_ok=True)
        return result_folder

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, np.generic):
            return self._json_safe(value.item())
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
