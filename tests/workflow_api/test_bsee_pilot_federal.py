# ABOUTME: TDD for the wed#927 BSEE FEDERAL (real-extract) path — a GENUINE public-domain
# ABOUTME: BSEE OGOR-A 2024 slice publishes PUBLIC / cc-by-4.0 / source_authority:BSEE.
"""Federal real-extract tests for the BSEE public run-ledger pilot (worldenergydata#927).

These exercise the SEPARATE ``bsee-production-summary-federal.yml`` config, whose
pinned snapshot is a committed REAL public-domain BSEE OGOR-A extract (Green Canyon
478, 2024). The MAJOR-1 gate therefore PERMITS the federal claim and the dataset
resolves PUBLIC / cc-by-4.0 / BSEE. The synthetic default config stays PRIVATE.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from worldenergydata.workflow_api import bsee_pilot as P

REPO_ROOT = Path(__file__).resolve().parents[2]
FEDERAL_CONFIG = "config/publication/bsee-production-summary-federal.yml"
FEDERAL_SLICE = "examples/workflows/bsee-production-summary/ogora2024_GC478.csv"
GOLDEN = (
    REPO_ROOT
    / "tests"
    / "workflow_api"
    / "goldens"
    / "bsee_production_summary_federal.json"
)

# The genuine slice + its digest (over the committed bytes) and the parent bulk
# file it was cut from — the reproducible admission identities.
EXPECTED_SNAPSHOT_IDENTITY = (
    "3c160686cb3a860010d049192f539f59ace24e727ebd0e5f3b80df35a8ea1960"
)
EXPECTED_PARENT_ZIP_SHA256 = (
    "63f1cbfa3351b067c49ef1c599b38691c4782f0e3e94ab6478eb1b83e981ebe1"
)

_ABS_PATH = re.compile(
    r"(?<![\w.])(?:file:/{0,3}|~/|/(?:home|mnt|Users|root|tmp|srv|opt)/)\S*"
)


@pytest.fixture(scope="session")
def federal_config():
    return P.load_config(FEDERAL_CONFIG)


@pytest.fixture(scope="session")
def federal_summary(federal_config, quiet_logging_cm):
    """Full federal dry-run (InMemoryHfPort, NO HF network, NO real publish)."""
    with quiet_logging_cm():                   # chatty engine; see conftest note
        return P.run_pilot(config=federal_config, write_report=False)


# --- the committed slice IS the pinned real extract (reproducible identity) ---


def test_committed_slice_matches_pinned_snapshot_identity(federal_config):
    slice_bytes = (REPO_ROOT / FEDERAL_SLICE).read_bytes()
    assert hashlib.sha256(slice_bytes).hexdigest() == EXPECTED_SNAPSHOT_IDENTITY
    d = P.build_snapshot_descriptor(
        federal_config, "gc478", federal_config["variants"][0]["api12"]
    )
    assert d["snapshot_identity"] == EXPECTED_SNAPSHOT_IDENTITY
    assert d["parent_zip_sha256"] == EXPECTED_PARENT_ZIP_SHA256
    # >=3 distinct producing wells actually present in the pinned slice
    text = slice_bytes.decode("utf-8").splitlines()
    header = text[0].split(",")
    api_i, oil_i = header.index("API_WELL_NUMBER"), header.index("OIL_PRODUCTION")
    producers = {
        r.split(",")[api_i] for r in text[1:] if float(r.split(",")[oil_i]) > 0
    }
    assert len(producers) >= 3


# --- MAJOR-1: a committed real extract PERMITS the federal claim -------------


def test_real_extract_permits_federal_public_cc_by_4_0(federal_config, federal_summary):
    vis = federal_summary["visibility"]
    assert vis["public"] is True and vis["private"] is False
    assert vis["license"] == "cc-by-4.0"
    assert vis["source_authority"] == "BSEE"
    assert vis["is_real_extract"] is True
    # the gate PASSES for every federal variant's descriptor (no raise)
    for v in federal_config["variants"]:
        d = P.build_snapshot_descriptor(federal_config, v["snapshot"], v["api12"])
        assert d["is_real_extract"] is True
        assert d["source_authority"] == "BSEE"
        assert d["redistribution_rights"] == "public-domain"
        assert d["license"] == "cc-by-4.0"
        P.assert_federal_claim_allowed(d)  # allowed


# --- AC2: >=3 real variations + exactly one exact replay --------------------


def test_three_real_variations_plus_replay(federal_summary):
    run_ids = federal_summary["run_ids"]
    assert set(run_ids) == {"V1", "V2", "V3"}
    assert len(set(run_ids.values())) == 3  # distinct, not accidentally equal
    assert federal_summary["replay"]["same_run_id"] is True
    assert federal_summary["accepted_count"] == 3
    assert federal_summary["rejected_count"] == 0
    revs = federal_summary["revisions"]
    assert len(set(revs.values())) == 3  # distinct immutable revisions


def test_real_metrics_are_genuine_bsee_values(federal_summary):
    m = federal_summary["metrics"]
    # genuine GC478 2024 oil totals (BSEE OGOR-A), value-preserving from source
    assert m["V1"]["total_oil_bbl"] == 10010908.0  # SS001+SS002+SS006
    assert m["V1"]["producing_well_count"] == 3
    assert m["V2"]["total_oil_bbl"] == 4309618.0  # SS001 only
    assert m["V2"]["producing_well_count"] == 1
    assert m["V3"]["producing_well_count"] == 2  # SS001+SS002
    # strict subset ordering
    assert (
        m["V2"]["total_oil_bbl"] < m["V3"]["total_oil_bbl"] < m["V1"]["total_oil_bbl"]
    )


# --- AC7: the federal report renders REAL snapshot provenance ---------------


def test_federal_report_renders_real_provenance_and_attribution(federal_summary):
    html = federal_summary["report_html"]
    assert "PUBLIC / cc-by-4.0 / source_authority:BSEE" in html
    # CC-BY attribution to the BSEE data center
    assert "BSEE Data Center, OGOR-A, data.bsee.gov" in html
    # real retrieval URL + parent-file digest + snapshot_identity + retrieval date
    assert "https://www.data.bsee.gov/Production/Files/ogora2024delimit.zip" in html
    assert EXPECTED_PARENT_ZIP_SHA256 in html
    assert EXPECTED_SNAPSHOT_IDENTITY[:16] in html
    assert "2026-07-11T00:00:00Z" in html  # pinned retrieval timestamp
    assert "Inputs" in html and "Outputs" in html
    for rev in federal_summary["revisions"].values():
        assert rev in html
    # every provenance row is labeled REAL (no synthetic rows on the federal path)
    assert "REAL" in html and "SYNTHETIC" not in html


# --- AC8: clean-room replay reproduces the accepted outputs (federal golden) --


def test_federal_reference_golden(federal_config):
    golden = json.loads(GOLDEN.read_text())
    from assetutilities.workflow_api.envelope import result_hash

    for v in federal_config["variants"]:
        payload, _ = P.execute_variant(
            v["workflow"], v["api12"], v["group_label"], v["snapshot"], federal_config
        )
        g = golden[v["id"]]
        assert result_hash(payload) == g["result_hash"], v["id"]
        got = {o["basename"]: o["sha256"] for o in payload["outputs"]}
        assert got == g["outputs"], v["id"]


# --- AC10: no private data / no local absolute paths in the federal artifacts -


def test_federal_artifacts_have_no_absolute_paths(federal_summary):
    for rel in (FEDERAL_CONFIG, FEDERAL_SLICE):
        text = (REPO_ROOT / rel).read_text()
        hits = [m.group(0) for m in _ABS_PATH.finditer(text)]
        assert not hits, f"absolute path leak in {rel}: {hits[:3]}"
    # the rendered federal report carries no machine-absolute path either
    assert not _ABS_PATH.search(federal_summary["report_html"])
    # and the published canonical run record is path-independent
    from assetutilities.workflow_api import identity as ident_mod

    entry = federal_summary["entries"][0]
    run_record_text = ident_mod.canonicalize(entry["projection"].run_record())
    assert not _ABS_PATH.search(run_record_text)


# --- the SYNTHETIC default path stays PRIVATE / synthetic (unchanged) --------


def test_synthetic_default_path_stays_private():
    syn = P.load_config()  # default bsee-production-summary.yml
    vis = P.resolve_visibility(syn)
    assert vis["private"] is True and vis["public"] is False
    assert vis["license"] == "synthetic-fixture-nonfederal"
    assert vis["source_authority"] != "BSEE"
    # a synthetic descriptor may NEVER carry a federal claim
    v = syn["variants"][0]
    d = P.build_snapshot_descriptor(syn, v["snapshot"], v["api12"])
    assert d["is_real_extract"] is False
    forged = dict(d, source_authority="BSEE", license="cc-by-4.0")
    with pytest.raises(P.PilotError):
        P.assert_federal_claim_allowed(forged)
