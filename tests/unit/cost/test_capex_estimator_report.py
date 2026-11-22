"""End-to-end report generation from explicit, validated input records."""

import json
import math
import runpy
import sys
from pathlib import Path

import pytest

from .test_capex_estimator import corpus, policy
from .test_capex_estimator_dataset import DAY, snapshot


def test_report_command_round_trips_outputs_and_input_digest(tmp_path, monkeypatch):
    """The empty corpus cannot establish a CAPEX estimate; both outputs say so."""
    request = dict(
        records=[],
        targets=[snapshot().model_dump(mode="json")],
        policy=policy().model_dump(mode="json"),
        cutoff=DAY.isoformat(),
        issued_on=DAY.isoformat(),
        revision="initial",
    )
    source, html, machine = [
        tmp_path / p for p in ("input.json", "report.html", "result.json")
    ]
    source.write_text(json.dumps(request), encoding="utf-8")
    script = (
        Path(__file__).resolve().parents[3]
        / "scripts/cost/build_capex_estimator_report.py"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [str(script), str(source), "--html", str(html), "--json", str(machine)],
    )
    runpy.run_path(str(script), run_name="__main__")
    result = json.loads(machine.read_text(encoding="utf-8"))
    assert result["results"][0]["status"] == "NOT_EVALUATED"
    assert "NOT_EVALUATED" in html.read_text(encoding="utf-8")
    assert result["reconciliations"][0]["relation"] == "indeterminate"
    assert "Reconciliation" in html.read_text(encoding="utf-8")
    import hashlib

    assert result["input_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_report_command_generates_analytic_backtests(tmp_path, monkeypatch):
    """For the synthetic line, all sixteen distinct projects are held out once."""
    request = dict(
        records=[r.model_dump(mode="json") for r in corpus()],
        targets=[snapshot().model_dump(mode="json")],
        policy=policy().model_dump(),
        cutoff=DAY.isoformat(),
        issued_on=DAY.isoformat(),
        revision="initial",
    )
    source, html, machine = [
        tmp_path / p for p in ("input.json", "report.html", "result.json")
    ]
    source.write_text(json.dumps(request), encoding="utf-8")
    script = (
        Path(__file__).resolve().parents[3]
        / "scripts/cost/build_capex_estimator_report.py"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [str(script), str(source), "--html", str(html), "--json", str(machine)],
    )
    runpy.run_path(str(script), run_name="__main__")
    result = json.loads(machine.read_text(encoding="utf-8"))["results"][0]
    assert len(result["backtests"]) == 16
    assert result["status"] == "modeled"
    assert "p16" in html.read_text(encoding="utf-8")


def test_report_reconciles_total_and_component_models(tmp_path, monkeypatch):
    """Fixture: wells=0.4*C, host=0.5*C; residual=0.1*exp(1.2) at x=2.

    Fractions are definitions of this hand example, not cost-allocation factors.
    """
    rows = []
    targets = []
    for scope, factor in [("total_project", 1), ("wells", 0.4), ("host", 0.5)]:
        for row in corpus():
            basis = row.snapshot.basis.model_copy(update={"scope_basis": scope})
            snap = row.snapshot.model_copy(update={"basis": basis})
            rows.append(
                row.model_copy(update={"snapshot": snap, "amount": row.amount * factor})
            )
        target = snapshot()
        basis = target.basis.model_copy(update={"scope_basis": scope})
        targets.append(target.model_copy(update={"basis": basis}))
    request = dict(
        records=[r.model_dump(mode="json") for r in rows],
        targets=[t.model_dump(mode="json") for t in targets],
        policy=policy().model_dump(),
        cutoff=DAY.isoformat(),
        issued_on=DAY.isoformat(),
        revision="initial",
        required_scopes={"target": ["wells", "host"]},
    )
    source, html, machine = [
        tmp_path / p for p in ("input.json", "report.html", "result.json")
    ]
    source.write_text(json.dumps(request), encoding="utf-8")
    script = (
        Path(__file__).resolve().parents[3]
        / "scripts/cost/build_capex_estimator_report.py"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [str(script), str(source), "--html", str(html), "--json", str(machine)],
    )
    runpy.run_path(str(script), run_name="__main__")
    result = json.loads(machine.read_text(encoding="utf-8"))
    assert result["reconciliations"][0]["variance"] == pytest.approx(
        0.1 * math.exp(1.2)
    )
    assert result["reconciliations"][0]["relation"] == "direct_above"
