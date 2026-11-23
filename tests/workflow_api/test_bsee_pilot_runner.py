# ABOUTME: TDD for the wed#927 BSEE HF pilot — snapshot admission, path-independent
# ABOUTME: identity, >=3 variations + exact replay, data_as_of exclusion, reference golden.
"""Runner-side tests for the BSEE public run-ledger pilot (worldenergydata#927).

Built against the REAL assetutilities.workflow_api signatures (verified on main):
identity.derive_run_identity, inputs.make_input/admit, output_contract, publication.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from assetutilities.workflow_api import identity, inputs

from worldenergydata.workflow_api import bsee_pilot as P

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN = (
    REPO_ROOT / "tests" / "workflow_api" / "goldens" / "bsee_production_summary.json"
)


# --- AC1: resource-intel snapshot provenance --------------------------------


def test_snapshot_descriptor_records_provenance(pilot_config):
    v = pilot_config["variants"][0]
    d = P.build_snapshot_descriptor(pilot_config, v["snapshot"], v["api12"])
    # URL / retrieval ts / sha256 snapshot_identity / rights / query+selection / schema
    assert d["public_locator"]["uri"]
    assert d["public_locator"].get("version")  # versioned (pinned)
    assert d["retrieved_at"].endswith("Z")
    assert len(d["snapshot_identity"]) == 64
    assert d["redistribution_rights"]
    assert d["selection"]["area"] and d["selection"]["api12"]
    assert "OIL_PRODUCTION" in d["schema"]
    # the pinned vintage is a SOURCE vintage, not a run timestamp
    assert d["vintage"] == d["data_as_of"]


# --- AC1/AC4: pinned admission passes; run-timestamp-only vintage rejected ---


def test_snapshot_pinned_admission_passes(pilot_config):
    v = pilot_config["variants"][0]
    d = P.build_snapshot_descriptor(pilot_config, v["snapshot"], v["api12"])
    rec = P.build_input_record(d, pilot_config)
    # admits without raising (Gate A) and mints an input_record_id
    assert inputs.admission_reason(rec) is None
    assert inputs.admit(rec) is rec
    assert len(inputs.input_record_id(rec)) == 64


def test_runtime_data_as_of_is_not_source_vintage(pilot_config):
    """A record with only a run-timestamp vintage (no pinned snapshot identity /
    unversioned locator) FAILS Gate A -- the missing snapshot is the rule."""
    unpinned = inputs.make_input(
        kind="dataset_snapshot",
        role="bsee_production_extract",
        schema_version="bsee-ogor-a-1",
        required_for_replay=True,
        content_digest=None,
        replay_location="content_addressed_dataset_object",
        redistribution_rights="owned",
        residency="public",
        source_authority="worldenergydata-synthetic-fixture",
        # unversioned locator + no snapshot_identity => "mutable_unpinned"
        public_locator={"uri": "synthetic://x"},
        data_as_of="2026-07-11T00:00:00Z",  # a run-timestamp-shaped vintage only
        snapshot_identity=None,
    )
    assert inputs.admission_reason(unpinned) == "mutable_unpinned"
    with pytest.raises(inputs.AdmissionError):
        inputs.admit(unpinned)


# --- AC2: >=3 meaningful variations + exactly 1 exact replay ----------------


def test_at_least_three_variations_plus_one_replay(pilot_summary):
    run_ids = pilot_summary["run_ids"]
    assert set(run_ids) == {"V1", "V2", "V3"}
    assert len(set(run_ids.values())) == 3  # distinct, not accidentally equal
    # exactly one exact replay (of the configured replay variant)
    assert pilot_summary["replay"]["same_run_id"] is True
    m = pilot_summary["metrics"]
    assert m["V1"]["total_oil_bbl"] == 90000.0  # README-anchored
    assert m["V2"]["total_oil_bbl"] < m["V1"]["total_oil_bbl"]  # strict subset
    assert m["V3"]["producing_well_count"] == 3  # distinct MC-778 block


# --- AC3: exact replay -> same run_id + output equality ----------------------


def test_exact_replay_same_run_id_and_equality(pilot_config):
    v = next(
        v for v in pilot_config["variants"] if v["id"] == pilot_config["replay_variant"]
    )
    a = P.build_projection_for_variant(pilot_config, v)
    b = P.build_projection_for_variant(pilot_config, v)
    assert a["run_id"] == b["run_id"]
    # equality over the timestamp-free curated set (no mismatch -> no raise)
    assert identity.assert_output_equality(
        a["output_equality"]["digest"], b["output_equality"]["digest"]
    )


def test_data_as_of_structurally_excluded_from_equality(pilot_config):
    """data_as_of lives in provenance (excluded from result_hash(payload)); two
    runs at different wall-clock times already pass exact-replay equality with no
    shared-runner change."""
    from worldenergydata.workflow_api import run_workflow

    e1 = run_workflow("bsee-production-summary")
    # data_as_of lives in PROVENANCE, never in the result payload that result_hash covers
    assert "data_as_of" in e1.provenance
    assert "data_as_of" not in json.dumps(e1.result)
    # so two runs are equal by result_hash regardless of the wall-clock stamp
    e2 = run_workflow("bsee-production-summary")
    assert (
        e1.determinism["result_hash"] == e2.determinism["result_hash"]
    )  # equality holds


# --- AC3/AC9: an equality mismatch blocks publication ------------------------


def test_equality_mismatch_blocks_publication(pilot_config):
    from assetutilities.workflow_api.publication import promotion as promotion_mod

    v = pilot_config["variants"][0]
    entry = P.build_projection_for_variant(pilot_config, v)
    from assetutilities.workflow_api.publication.hf_port import InMemoryHfPort
    from assetutilities.workflow_api.publication.ledger import Ledger

    m = promotion_mod.PromotionMachine(
        entry["projection"],
        hf_port=InMemoryHfPort(),
        ledger=Ledger(),
        egress=P.make_egress(),
    )
    m.validate()
    with pytest.raises(identity.OutputMismatchError):
        m.replay(observed_output_equality="0" * 64)  # perturbed -> mismatch
    assert m.state != "accepted"


# --- AC4: inputs complete/canonical/hashed/schema-valid/replayable ----------


def test_inputs_complete_canonical_hashed_schema_valid_replayable(pilot_config):
    v = pilot_config["variants"][0]
    d = P.build_snapshot_descriptor(pilot_config, v["snapshot"], v["api12"])
    rec = P.build_input_record(d, pilot_config)
    assert rec["schema_version"]  # schema-valid
    assert rec["content_digest"] and len(rec["content_digest"]) == 64  # hashed
    assert rec["replay_location"] in inputs.ALLOWED_REPLAY_LOCATIONS  # replayable
    assert rec["snapshot_identity"] == d["snapshot_identity"]  # pinned/canonical
    assert inputs.admission_reason(rec) is None  # complete


# --- AC2/AC5: reference determinism golden -----------------------------------


def test_bsee_reference_golden(pilot_config):
    golden = json.loads(GOLDEN.read_text())
    for v in pilot_config["variants"]:
        payload, _ = P.execute_variant(
            v["workflow"], v["api12"], v["group_label"], v["snapshot"], pilot_config
        )
        from assetutilities.workflow_api.envelope import result_hash

        g = golden[v["id"]]
        assert result_hash(payload) == g["result_hash"], v["id"]
        got = {o["basename"]: o["sha256"] for o in payload["outputs"]}
        assert got == g["outputs"], v["id"]
