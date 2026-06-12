"""Engine router for offline marine safety workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from worldenergydata.marine_safety.cross_database import CrossDatabaseAnalyzer


class MarineSafety:
    """Run marine safety analyses from engine YAML configuration."""

    module_name = "marine_safety"

    def router(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Run configured marine safety analysis."""
        analysis_type = cfg.get("analysis", {}).get("type", "incident_stats")
        if analysis_type != "incident_stats":
            raise ValueError(
                f"Unsupported marine safety analysis type: {analysis_type}"
            )

        cfg.setdefault(self.module_name, {})
        cfg[self.module_name].update({"analysis": cfg.get("analysis", {}).copy()})
        outputs = self._run_incident_stats(cfg)
        cfg[self.module_name]["status"] = "completed"
        cfg[self.module_name]["outputs"] = outputs
        return cfg

    def _run_incident_stats(self, cfg: dict[str, Any]) -> dict[str, str]:
        data_cfg = cfg.get("data", {})
        if data_cfg.get("source", "csv") != "csv":
            raise ValueError("Marine safety durable workflows require data.source=csv")

        incidents = pd.read_csv(self._input_root(cfg) / data_cfg["file"])
        analyzer = CrossDatabaseAnalyzer()
        incident_type_counts = analyzer.top_incident_types(incidents, n=len(incidents))
        trends = analyzer.trend_analysis(incidents)

        label = cfg.get("meta", {}).get("label", "marine_safety_stats")
        result_folder = self._result_folder(cfg)
        counts_path = result_folder / f"{label}_incident_type_counts.csv"
        trends_path = result_folder / f"{label}_trends.csv"
        summary_path = result_folder / f"{label}_summary.json"

        incident_type_counts.to_csv(counts_path, index=False)
        trends.to_csv(trends_path, index=False)

        summary = {
            "total_incidents": int(len(incidents)),
            "by_source": {
                key: int(value)
                for key, value in incidents["source"]
                .value_counts()
                .sort_index()
                .items()
            },
            "incident_type_counts": {
                row["incident_type"]: int(row["count"])
                for _, row in incident_type_counts.iterrows()
            },
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        return {
            "incident_type_counts_csv": str(counts_path),
            "trends_csv": str(trends_path),
            "summary_json": str(summary_path),
        }

    def _input_root(self, cfg: dict[str, Any]) -> Path:
        return Path(cfg["Analysis"]["analysis_root_folder"])

    def _result_folder(self, cfg: dict[str, Any]) -> Path:
        result_folder = Path(cfg["Analysis"]["result_folder"])
        result_folder.mkdir(parents=True, exist_ok=True)
        return result_folder
