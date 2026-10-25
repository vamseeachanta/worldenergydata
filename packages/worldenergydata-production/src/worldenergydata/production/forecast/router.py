"""Engine router for offline production forecast workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from worldenergydata.production.forecast.decline import ArpsDeclineCurve


class ProductionForecast:
    """Run production forecasting workflows from engine YAML configuration."""

    module_name = "production_forecast"

    def router(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Run configured production forecast cases."""
        analysis_type = cfg.get("analysis", {}).get("type", "arps")
        if analysis_type not in {"arps", "probabilistic"}:
            raise ValueError(f"Unsupported production forecast type: {analysis_type}")

        cfg.setdefault(self.module_name, {})
        cfg[self.module_name].update({"analysis": cfg.get("analysis", {}).copy()})
        outputs = (
            self._run_probabilistic(cfg)
            if analysis_type == "probabilistic"
            else self._run_arps(cfg)
        )
        cfg[self.module_name]["status"] = "completed"
        cfg[self.module_name]["outputs"] = outputs
        return cfg

    def _run_probabilistic(self, cfg: dict[str, Any]) -> dict[str, str]:
        from worldenergydata.production.forecast.probabilistic import (
            ProbabilisticForecast,
        )
        from worldenergydata.production.forecast.report import build_report_html

        result = ProbabilisticForecast().run(cfg["probabilistic"])
        folder = self._result_folder(cfg)
        label = cfg.get("meta", {}).get("label", "production_forecast_probabilistic")
        if (
            not isinstance(label, str)
            or not label
            or Path(label).name != label
            or label in {".", ".."}
            or "\\" in label
        ):
            raise ValueError("label must be a single file-name component")
        outputs = {
            key: folder / f"{label}_{suffix}"
            for key, suffix in {
                "run_matrix_csv": "run_matrix.csv",
                "fan_csv": "fan.csv",
                "summary_json": "summary.json",
                "report_html": "report.html",
            }.items()
        }
        result.run_matrix.to_csv(outputs["run_matrix_csv"], index=False)
        result.fan.to_csv(outputs["fan_csv"], index=False)
        outputs["summary_json"].write_text(
            json.dumps(result.summary, indent=2, allow_nan=False), encoding="utf-8"
        )
        outputs["report_html"].write_text(
            build_report_html(result), encoding="utf-8", newline="\n"
        )
        return {key: str(value) for key, value in outputs.items()}

    def _run_arps(self, cfg: dict[str, Any]) -> dict[str, str]:
        adc = ArpsDeclineCurve()
        input_root = self._input_root(cfg)
        result_rows = []
        summary_cases = {}

        for case in cfg["cases"]:
            production = pd.read_csv(input_root / case["file"])
            result = adc.fit(
                production,
                model=case["model"],
                economic_limit=float(case["economic_limit"]),
                months=int(case["forecast_months"]),
            )
            row = {
                "case_id": case["id"],
                "model": result.model,
                "qi": result.qi,
                "Di": result.Di,
                "b": result.b,
                "r_squared": result.r_squared,
                "eur_bbl": result.eur_bbl,
            }
            result_rows.append(row)
            summary_cases[case["id"]] = row

        label = cfg.get("meta", {}).get("label", "production_forecast_arps")
        result_folder = self._result_folder(cfg)
        cases_path = result_folder / f"{label}_cases.csv"
        summary_path = result_folder / f"{label}_summary.json"

        pd.DataFrame(result_rows).to_csv(cases_path, index=False)
        summary = {
            "case_count": len(result_rows),
            "cases": summary_cases,
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        return {
            "cases_csv": str(cases_path),
            "summary_json": str(summary_path),
        }

    def _input_root(self, cfg: dict[str, Any]) -> Path:
        return Path(cfg["Analysis"]["analysis_root_folder"])

    def _result_folder(self, cfg: dict[str, Any]) -> Path:
        result_folder = Path(cfg["Analysis"]["result_folder"])
        result_folder.mkdir(parents=True, exist_ok=True)
        return result_folder
