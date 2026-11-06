"""Generate estimator HTML and full-precision JSON from a supplied request.

No corpus, currency conversion, acceptance criteria, or reference date is
assumed. Run with --help for output arguments; see docs/modules/cost/CAPEX_ESTIMATOR.md.
"""

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from pydantic import Field, model_validator

from worldenergydata.cost.calibration.capex_estimator import (
    CapexEstimator,
    reconcile_estimates,
    render_report,
)
from worldenergydata.cost.calibration.capex_estimator_schema import (
    Contract,
    EstimatorPolicy,
    FeatureSnapshot,
    TrainingRecord,
)


class ReportRequest(Contract):
    records: list[TrainingRecord]
    targets: list[FeatureSnapshot] = Field(min_length=1)
    policy: EstimatorPolicy
    cutoff: date
    issued_on: date
    revision: str = Field(min_length=1)
    required_scopes: dict[str, set[str]] = Field(default_factory=dict)
    prior_revisions: list[tuple[str, str, str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_targets(self):
        keys = [(s.project_id, s.basis.scope_basis) for s in self.targets]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate target project/scope")
        if any("total_project" in scopes for scopes in self.required_scopes.values()):
            raise ValueError("total_project cannot be a component scope")
        return self


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    if len({p.resolve() for p in (args.input, args.html, args.json)}) != 3:
        parser.error("input, HTML and JSON paths must be distinct")
    raw = args.input.read_bytes()
    request = ReportRequest.model_validate_json(raw)
    estimator = CapexEstimator(request.records, request.policy, request.cutoff)
    results = [estimator.predict(target) for target in request.targets]
    reconciliations = []
    for direct in results:
        if direct.basis["scope_basis"] != "total_project":
            continue
        scopes = request.required_scopes.get(direct.project_id, set())
        components = {
            r.basis["scope_basis"]: r
            for r in results
            if r.project_id == direct.project_id and r.basis["scope_basis"] in scopes
        }
        reconciliations.append(
            dict(
                project_id=direct.project_id,
                **reconcile_estimates(direct, components, scopes),
            )
        )
    html = render_report(
        results,
        revision=request.revision,
        issued_on=request.issued_on,
        reconciliations=reconciliations,
        prior_revisions=request.prior_revisions,
    )
    payload = dict(
        input_sha256=hashlib.sha256(raw).hexdigest(),
        results=[asdict(r) for r in results],
        reconciliations=reconciliations,
    )
    machine = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"
    args.html.write_text(html, encoding="utf-8")
    args.json.write_text(machine, encoding="utf-8")
    if (
        args.html.read_text(encoding="utf-8") != html
        or args.json.read_text(encoding="utf-8") != machine
    ):
        raise OSError("saved estimator output failed readback")


if __name__ == "__main__":
    main()
