"""Engine router for the offline federal-acreage fixture workflow."""

from pathlib import Path
from typing import Any

from .evidence import evaluate
from .models import TractOfInterest
from .provider import FixtureRecordProvider
from .report import write_outputs


class FederalAcreage:
    def router(self, cfg: dict[str, Any]) -> dict[str, Any]:
        if cfg["data"]["source"] != "fixture":
            raise ValueError("Federal acreage pilot requires data.source=fixture")
        root = Path(cfg["Analysis"]["analysis_root_folder"])
        provider = FixtureRecordProvider(root / cfg["data"]["file"])
        tract = (
            TractOfInterest.model_validate(cfg["tract"])
            if "tract" in cfg
            else provider.tract
        )
        result = evaluate(tract, *provider.records_for_tract(tract))
        outputs = write_outputs(
            result,
            cfg["Analysis"]["result_folder"],
            cfg.get("meta", {}).get("label", "federal_acreage_evidence"),
        )
        cfg.setdefault("federal_acreage", {}).update(
            status="completed",
            outputs={key: str(path) for key, path in outputs.items()},
        )
        return cfg
