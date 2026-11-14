"""Engine router for the offline disclosure benchmarking report."""

from pathlib import Path
from typing import Any

from worldenergydata.cost.reporting.benchmark_report import write_report


class CostWorkflow:
    """Generate the existing report from explicit workflow configuration."""

    def router(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Write both artifacts and mark completion only after successful writes."""
        analysis_type = cfg["analysis"]["type"]
        if analysis_type != "disclosure_benchmark":
            raise ValueError(f"Unsupported cost analysis type: {analysis_type}")

        report_date = cfg["report"]["report_date"]
        result_folder = Path(cfg["Analysis"]["result_folder"])
        outputs = write_report(result_folder, report_date)
        cfg["cost"] = {
            "status": "completed",
            "outputs": {key: str(path) for key, path in outputs.items()},
        }
        return cfg
