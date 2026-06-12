"""Offline SODIR workflow helpers for registry examples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from worldenergydata.sodir.analysis import SodirAnalysis


class SodirOfflineWorkflow:
    """Run local CSV-backed SODIR workflows without API access."""

    module_name = "sodir"

    def router(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Run a local SODIR field summary workflow."""
        analysis_type = cfg.get("analysis", {}).get("type", "field_summary")
        if analysis_type != "field_summary":
            raise ValueError(
                f"Unsupported offline SODIR analysis type: {analysis_type}"
            )

        data_path = self._input_root(cfg) / cfg["data"]["input_path"]
        result_folder = self._result_folder(cfg)
        label = cfg.get("meta", {}).get("label", "sodir_field_summary")

        analysis = SodirAnalysis(
            {
                "input_path": str(data_path),
                "output_path": str(result_folder),
                "analysis_type": "portfolio",
            }
        )
        analysis.load_data()
        portfolio = analysis.analyze_portfolio()

        fields_path = result_folder / f"{label}_fields.csv"
        production_path = result_folder / f"{label}_production.csv"
        portfolio_path = result_folder / f"{label}_portfolio.json"

        analysis.data["fields"].to_csv(fields_path, index=False)
        analysis.data.get("production").to_csv(production_path, index=False)
        portfolio_path.write_text(
            json.dumps(self._json_safe(portfolio), indent=2),
            encoding="utf-8",
        )

        cfg.setdefault(self.module_name, {})
        cfg[self.module_name]["status"] = "completed"
        cfg[self.module_name]["analysis"] = {
            "type": analysis_type,
            "portfolio": self._json_safe(portfolio),
        }
        cfg[self.module_name]["outputs"] = {
            "portfolio_json": str(portfolio_path),
            "fields_csv": str(fields_path),
            "production_csv": str(production_path),
        }
        return cfg

    def _input_root(self, cfg: dict[str, Any]) -> Path:
        return Path(cfg["Analysis"]["analysis_root_folder"])

    def _result_folder(self, cfg: dict[str, Any]) -> Path:
        result_folder = Path(cfg["Analysis"]["result_folder"])
        result_folder.mkdir(parents=True, exist_ok=True)
        return result_folder

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, np.generic):
            return value.item()
        return value
