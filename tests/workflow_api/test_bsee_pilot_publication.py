# ABOUTME: TDD for the wed#927 BSEE HF pilot publication path — curated outputs,
# ABOUTME: metrics, immutable revision, MAJOR-1 federal gate, MAJOR-2 path-independence, clean-room.
"""Publication-side tests for the BSEE public run-ledger pilot (worldenergydata#927)."""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path

import pytest
from assetutilities.workflow_api import inputs, metrics
from assetutilities.workflow_api import report as report_mod

from worldenergydata.workflow_api import bsee_pilot as P

REPO_ROOT = Path(__file__).resolve().parents[2]

# New committed artifacts that must be free of local absolute paths (AC10).
_NEW_FILES = [
    "config/publication/bsee-production-summary.yml",
    "src/worldenergydata/workflow_api/bsee_pilot.py",
    "scripts/pilots/run_bsee_pilot.py",
    "docs/reports/bsee-production-summary/index.html",
    "tests/workflow_api/goldens/bsee_production_summary.json",
]
_ABS_PATH = re.compile(
    r"(?<![\w.])(?:file:/{0,3}|~/|/(?:home|mnt|Users|root|tmp|srv|opt)/)\S*"
)


# --- AC5: native schema retained; only curated allowlist projects -----------


def test_outputs_retain_native_schema_only_curated_publish(pilot_summary):
    entry = next(e for e in pilot_summary["entries"] if e["variant"]["id"] == "V1")
    # all SIX native outputs are produced (full engineering schema retained)
    assert len(entry["out_bytes"]) == 6
    # only the deterministic curated text outputs project as objects (xlsx excluded)
    projected = entry["projection"].outputs
    assert projected, "at least one curated output projected"
    for o in projected:
        assert o["curated_label"] in {"primary_result", "validation_evidence"}
        assert not any(
            ref["content_digest"].endswith(".xlsx") for ref in o["artifact_refs"]
        )
    # the raw xlsx is recorded (canonical digest) but NOT projected as an object
    assert entry["xlsx_digest"] and len(entry["xlsx_digest"]) == 64
    object_names = {o["role"] for o in projected}
    assert not any(n.endswith(".xlsx") for n in object_names)


# --- AC5: metrics carry definition/units/derivation/quality -----------------


def test_metrics_have_definitions_units_derivations_quality(pilot_config):
    store, defs = P.build_metric_store(pilot_config)
    assert len(defs) == 4
    for definition in defs.values():
        for field in (
            "meaning",
            "unit_or_dimension",
            "derivation",
            "quality_rule",
            "directionality",
            "label",
        ):
            assert definition[field], field
        # metric_id whole-prefix owned by the algorithm
        assert definition["metric_id"].startswith(
            pilot_config["algorithm"]["algorithm_id"] + "/"
        )
    # observations bind to run_id + algorithm
    entry = P.build_projection_for_variant(pilot_config, pilot_config["variants"][0])
    for obs in entry["projection"].metric_observations:
        assert obs["run_id"] == entry["run_id"]
        assert obs["algorithm_id"] == pilot_config["algorithm"]["algorithm_id"]
        assert obs["quality_state"] == "valid"


# --- AC6/AC7: immutable-revision projection (InMemoryHfPort) -----------------


def test_dataset_projection_publishes_immutable_revision(pilot_summary):
    revs = pilot_summary["revisions"]
    assert len(revs) == 3
    for rev in revs.values():
        assert report_mod.is_exact_revision(rev)  # exact 40-hex, immutable
    assert len(set(revs.values())) == 3  # distinct commits (git semantics)
    # the ledger is the SOLE eligibility authority
    assert set(pilot_summary["eligible_run_ids"]) == set(
        pilot_summary["run_ids"].values()
    )
    assert pilot_summary["accepted_count"] == 3


# --- MAJOR-1: federal claim requires a real extract -------------------------


def test_federal_claim_requires_real_extract_snapshot(pilot_config):
    # synthetic fixture forced to a BSEE federal claim -> REJECTED
    v = pilot_config["variants"][0]
    d = P.build_snapshot_descriptor(pilot_config, v["snapshot"], v["api12"])
    forged = dict(
        d,
        source_authority="BSEE",
        redistribution_rights="public-domain",
        license="cc-by-4.0",
    )
    with pytest.raises(P.PilotError):
        P.assert_federal_claim_allowed(forged)
    # the honest synthetic descriptor carries NO federal claim and passes the gate
    assert d["is_real_extract"] is False
    assert d["source_authority"] != "BSEE"
    P.assert_federal_claim_allowed(d)  # no raise


def test_published_dataset_public_cc_by_4_0_under_real_extract(pilot_config):
    # synthetic (dry run): PRIVATE + synthetic license, no federal claim
    syn = P.resolve_visibility(pilot_config)
    assert syn["private"] is True and syn["public"] is False
    assert syn["license"] == "synthetic-fixture-nonfederal"
    assert syn["source_authority"] != "BSEE"
    # WHEN a real extract is committed (is_real_extract=true): PUBLIC + cc-by-4.0 + BSEE
    real_cfg = copy.deepcopy(pilot_config)
    real_cfg["publication"]["is_real_extract"] = True
    real = P.resolve_visibility(real_cfg)
    assert real["public"] is True and real["license"] == "cc-by-4.0"
    assert real["source_authority"] == "BSEE"
    d = P.build_snapshot_descriptor(real_cfg, "wr718", ["177154051100"])
    P.assert_federal_claim_allowed(d)  # allowed under the real-extract gate


# --- AC7: rolling report has mandatory Inputs+Outputs + revision links -------


def test_rolling_report_has_inputs_outputs_and_revision_links(pilot_summary):
    html = pilot_summary["report_html"]
    assert "Inputs" in html and "Outputs" in html
    assert "hf://revision/" in html  # links to exact revisions
    assert "Source snapshot provenance" in html  # provenance section
    for rev in pilot_summary["revisions"].values():
        assert rev in html  # each pinned revision linked
    assert "snapshot_identity" in html


# --- AC8: clean-room replay reproduces the accepted outputs ------------------


def test_clean_room_replay_reproduces_accepted_outputs(pilot_config, pilot_summary):
    for v in pilot_config["variants"]:
        payload, _ = P.execute_variant(
            v["workflow"], v["api12"], v["group_label"], v["snapshot"], pilot_config
        )
        from assetutilities.workflow_api.envelope import result_hash

        assert result_hash(payload) == pilot_summary["result_hashes"][v["id"]], v["id"]


# --- AC9: failed runs excluded from metric/decision populations -------------


def test_failed_run_excluded_from_metrics_and_decisions(pilot_config):
    # a non-succeeded run may not enter metrics / insights / decisions
    for surface in ("metrics", "insights", "decisions"):
        with pytest.raises(metrics.MetricsError):
            metrics.assert_population_admissible("reproducible_failure", surface)
    # and population_eligible is False for a failed status
    store, defs = P.build_metric_store(pilot_config)
    definition = next(iter(defs.values()))
    obs = metrics.make_metric_observation(
        definition=definition,
        run_id="r",
        value=1.0,
        quality_state="valid",
        derivation_evidence={"x": 1},
    )
    assert (
        metrics.population_eligible(
            terminal_status="reproducible_failure",
            run_algorithm_id=pilot_config["algorithm"]["algorithm_id"],
            observation=obs,
            store=store,
        )
        is False
    )
    # a fail-closed error envelope from run_workflow is a non-ok status
    from worldenergydata.workflow_api import run_workflow

    err = run_workflow("does-not-exist")
    assert err.status == "error"


# --- AC10: no private data / no local absolute paths ------------------------


def test_no_private_data_or_absolute_paths():
    for rel in _NEW_FILES:
        text = (REPO_ROOT / rel).read_text()
        hits = [m.group(0) for m in _ABS_PATH.finditer(text)]
        # allow the documented plug-point comment mentioning the shared runner, not a path
        assert not hits, f"absolute path leak in {rel}: {hits[:3]}"


# --- MAJOR-2: published canonical input carries no absolute path ------------


def test_published_canonical_input_has_no_absolute_path(pilot_summary):
    from assetutilities.workflow_api import identity as ident_mod

    entry = pilot_summary["entries"][0]
    rec = entry["input_record"]
    assert inputs._has_path_leak(rec) is False
    # the published run record (canonical) contains no absolute path either
    run_record_text = ident_mod.canonicalize(entry["projection"].run_record())
    assert not _ABS_PATH.search(run_record_text)
    # the selection carries a RELATIVIZED fixture ref (basename), never an abs path
    assert rec["selection"]["fixture_ref"] == os.path.basename(
        rec["selection"]["fixture_ref"]
    )
    assert not rec["selection"]["fixture_ref"].startswith("/")


# --- MAJOR-2: fresh-checkout replay (different prefix) -> same run_id --------


def test_fresh_checkout_replay_same_run_id(pilot_config, tmp_path, monkeypatch):
    v = next(
        v for v in pilot_config["variants"] if v["id"] == pilot_config["replay_variant"]
    )
    d1 = P.build_snapshot_descriptor(pilot_config, v["snapshot"], v["api12"])
    rid1 = P.derive_identity(pilot_config, P.build_input_record(d1, pilot_config))[
        "run_id"
    ]

    # copy the fixture BYTES to a DIFFERENT absolute prefix and read from there
    src = P.repo_root() / pilot_config["snapshots"][v["snapshot"]]["fixture"]
    dst = tmp_path / "other" / "checkout" / "prefix" / os.path.basename(str(src))
    dst.parent.mkdir(parents=True)
    dst.write_bytes(src.read_bytes())
    monkeypatch.setattr(P, "read_fixture_bytes", lambda rel: dst.read_bytes())

    d2 = P.build_snapshot_descriptor(pilot_config, v["snapshot"], v["api12"])
    rid2 = P.derive_identity(pilot_config, P.build_input_record(d2, pilot_config))[
        "run_id"
    ]
    assert rid1 == rid2 and len(rid1) == 64  # identity is path-independent
