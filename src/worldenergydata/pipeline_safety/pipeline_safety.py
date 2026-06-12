"""Engine router for offline pipeline safety workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from worldenergydata.pipeline_safety.workflow import PipelineSafetyWorkflow


class PipelineSafety:
    """Run pipeline safety analyses from engine YAML configuration."""

    module_name = "pipeline_safety"

    def router(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Run the configured pipeline safety workflow."""
        analysis_type = cfg.get("analysis", {}).get("type", "ffs")
        if analysis_type != "ffs":
            raise ValueError(
                f"Unsupported pipeline safety analysis type: {analysis_type}"
            )

        cfg.setdefault(self.module_name, {})
        cfg[self.module_name].update({"analysis": cfg.get("analysis", {}).copy()})
        outputs = self._run_ffs(cfg)
        cfg[self.module_name]["status"] = "completed"
        cfg[self.module_name]["outputs"] = outputs
        return cfg

    def _run_ffs(self, cfg: dict[str, Any]) -> dict[str, str]:
        data_cfg = cfg.get("data", {})
        if data_cfg.get("source", "csv") != "csv":
            raise ValueError(
                "Pipeline safety durable workflows require data.source=csv"
            )

        input_path = self._input_root(cfg) / data_cfg["file"]
        incidents_df = pd.read_csv(input_path)
        method = cfg.get("analysis", {}).get("method", "modified_b31g")

        workflow = PipelineSafetyWorkflow()
        report_df = workflow.generate_report(incidents_df, method=method)
        verdict_summary = workflow.verdict_summary(report_df)
        narrative = workflow.case_study_narrative(report_df)

        label = cfg.get("meta", {}).get("label", "pipeline_safety_ffs")
        result_folder = self._result_folder(cfg)
        report_path = result_folder / f"{label}_report.csv"
        summary_path = result_folder / f"{label}_summary.json"
        narrative_path = result_folder / f"{label}_narrative.txt"

        report_df.to_csv(report_path, index=False)
        summary = {
            "method": method,
            "incident_count": int(len(report_df)),
            "verdict_summary": verdict_summary,
            "minimum_safe_pressure_mpa": float(report_df["safe_pressure_mpa"].min()),
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        narrative_path.write_text(narrative, encoding="utf-8")

        return {
            "report_csv": str(report_path),
            "summary_json": str(summary_path),
            "narrative_txt": str(narrative_path),
        }

    def _input_root(self, cfg: dict[str, Any]) -> Path:
        return Path(cfg["Analysis"]["analysis_root_folder"])

    def _result_folder(self, cfg: dict[str, Any]) -> Path:
        result_folder = Path(cfg["Analysis"]["result_folder"])
        result_folder.mkdir(parents=True, exist_ok=True)
        return result_folder
