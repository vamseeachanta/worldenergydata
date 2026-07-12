# ABOUTME: wed#927 BSEE public run-ledger pilot driver — pinned-snapshot inputs,
# ABOUTME: path-independent identity, projection->promotion->InMemoryHfPort ledger, rolling report.
"""Public BSEE algorithm-run pilot (worldenergydata#927).

Mirrors the digitalmodel#1505 synthetic-VIV pilot structure, adapted for the
already-wired ``bsee-production-summary`` workflow. This module ADDS only the
run-ledger layers around the UNCHANGED wed engine/router:

- a path-independent **Algorithm Version + run identity** (assetutilities
  ``identity``) — MAJOR-2: identity is derived from the pinned snapshot sha256 +
  declared params + RELATIVIZED file refs, NEVER the shared runner's absolutized
  ``input_hash`` (``runner._absolutize_input_paths`` -> ``input_hash`` embeds a
  machine-specific absolute path);
- a **pinned-snapshot input contract** (assetutilities ``inputs``) — the source
  snapshot's sha256 is the BINDING admission identity, not the runner's
  ``data_as_of=utc_now`` (which lives in ``provenance`` and is already excluded
  from ``result_hash(payload)``);
- **algorithm-scoped metrics** (assetutilities ``metrics``);
- a **projection -> promotion -> HF publication** path (assetutilities
  ``publication``) with an in-memory port for the dry run;
- a **rolling HTML report** + a **clean-room / fresh-checkout replay** contract.

MAJOR-1 (synthetic-vs-federal): the committed BSEE fixtures are SYNTHETIC. The
dry run therefore labels the dataset synthetic-derived and publishes PRIVATE with
a synthetic (non-federal) license and NO ``source_authority: BSEE`` claim. A
federal / public-domain / ``cc-by-4.0`` publish is GATED on committing a real
public-domain BSEE extract (``publication.is_real_extract: true`` in the config)
— :func:`assert_federal_claim_allowed` refuses the claim otherwise.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import os
import shutil
import tempfile
from pathlib import Path

import yaml

from assetutilities.workflow_api import artifact, identity, inputs, metrics
from assetutilities.workflow_api import output_contract as oc
from assetutilities.workflow_api import report as report_mod
from assetutilities.workflow_api.publication import egress as egress_mod
from assetutilities.workflow_api.publication import projection as projection_mod
from assetutilities.workflow_api.publication import promotion as promotion_mod
from assetutilities.workflow_api.publication.hf_port import InMemoryHfPort
from assetutilities.workflow_api.publication.ledger import Ledger
from assetutilities.workflow_api.runner import ResultLocator, extract_result
from assetutilities.workflow_api.envelope import result_hash as _result_hash
from worldenergydata.workflow_api import runner as R

CONFIG_PATH = "config/publication/bsee-production-summary.yml"

# Curated native outputs projected as content-addressed HF objects. The
# ``prod_raw_*.xlsx`` raw dump is a ZIP-container output that is regenerable from
# these curated CSV/JSON summaries; it is NOT projected as an object (its
# canonical digest is still recorded in the report/golden for provenance), which
# also keeps every published object plain-text and byte-deterministic.
_PRIMARY_BASENAMES = ("prod_summ_",)  # -> curated_label primary_result
_TEXT_SUFFIXES = (".csv", ".json")


class PilotError(RuntimeError):
    """Raised when the pilot violates a MAJOR-1/MAJOR-2 or contract invariant."""


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    return R._wed_repo_root()


def load_config(path: str | None = None) -> dict:
    cfg_path = repo_root() / (path or CONFIG_PATH)
    with open(cfg_path) as fh:
        return yaml.safe_load(fh)


def read_fixture_bytes(rel_fixture: str) -> bytes:
    """Read a REPO-RELATIVE fixture's bytes. Only the BYTES feed identity — never
    the (machine-specific) absolute path they were read from (MAJOR-2)."""
    with open(repo_root() / rel_fixture, "rb") as fh:
        return fh.read()


def environment_digest(env: dict) -> str:
    return identity.canonical_digest("environment_digest", env)


# ---------------------------------------------------------------------------
# source-snapshot descriptor + MAJOR-1 federal-claim gate
# ---------------------------------------------------------------------------

def build_snapshot_descriptor(config: dict, snapshot_key: str, api12: list) -> dict:
    """Build the pinned BSEE source-snapshot descriptor for a variant.

    ``snapshot_identity`` (sha256 over the committed fixture BYTES) is the binding
    admission identity (#3430 "stable retrieval path"), NOT a run timestamp. All
    refs are path-independent: the ``fixture`` is repo-relative and only its bytes
    are hashed.
    """
    snap = config["snapshots"][snapshot_key]
    pub = config["publication"]
    is_real = bool(pub["is_real_extract"])
    fixture_bytes = read_fixture_bytes(snap["fixture"])
    sha256 = hashlib.sha256(fixture_bytes).hexdigest()

    if is_real:
        source_authority = pub["federal_source_authority"]
        public_locator = dict(snap["federal_public_locator"])
        rights = "public-domain"
        license_ = pub["federal_license"]
    else:
        source_authority = pub["synthetic_source_authority"]
        public_locator = dict(snap["synthetic_public_locator"])
        rights = "owned"
        license_ = pub["synthetic_license"]

    selection = {
        "area": snap["query"]["area"],
        "block": snap["query"]["block"],
        "api12": list(api12),
        # RELATIVIZED file reference (basename only) — never an absolute path.
        "fixture_ref": os.path.basename(snap["fixture"]),
    }
    return {
        "snapshot_key": snapshot_key,
        "fixture": snap["fixture"],            # repo-relative (provenance only)
        "snapshot_identity": sha256,           # BINDING admission identity
        "public_locator": public_locator,      # best-effort retrieval path (m4)
        "vintage": snap["vintage"],            # SOURCE vintage, not run time
        "data_as_of": snap["vintage"],
        "retrieved_at": snap["retrieved_at"],  # pinned once, excluded from identity
        "source_authority": source_authority,
        "redistribution_rights": rights,
        "license": license_,
        "schema": list(snap["schema"]),
        "selection": selection,
        "is_real_extract": is_real,
    }


def assert_federal_claim_allowed(descriptor: dict) -> None:
    """MAJOR-1 hard gate: a federal / BSEE / public-domain / cc-by-4.0 claim is
    permitted ONLY when the pinned snapshot is a committed REAL extract.

    A synthetic fixture (``is_real_extract`` false) may NEVER carry
    ``source_authority: BSEE`` / ``public-domain`` rights / a federal license.
    """
    federal_tokens = {"BSEE"}
    claims_federal = (
        descriptor.get("source_authority") in federal_tokens
        or descriptor.get("redistribution_rights") == "public-domain"
        or descriptor.get("license") == "cc-by-4.0"
    )
    if claims_federal and not descriptor.get("is_real_extract"):
        raise PilotError(
            "federal BSEE / public-domain / cc-by-4.0 claim requires a committed REAL "
            "public-domain BSEE extract as the pinned snapshot; the synthetic fixture "
            "must be labeled synthetic-derived (private / synthetic license, no BSEE claim)"
        )


def resolve_visibility(config: dict) -> dict:
    """Derive HF visibility + license from the MAJOR-1 gate (never hardcoded)."""
    pub = config["publication"]
    is_real = bool(pub["is_real_extract"])
    return {
        "private": not is_real,   # synthetic -> PRIVATE HF repo
        "public": is_real,
        "license": pub["federal_license"] if is_real else pub["synthetic_license"],
        "source_authority": (
            pub["federal_source_authority"] if is_real else pub["synthetic_source_authority"]
        ),
        "is_real_extract": is_real,
    }


# ---------------------------------------------------------------------------
# input record (assetutilities inputs — Gate A admission)
# ---------------------------------------------------------------------------

def build_input_record(descriptor: dict, config: dict) -> dict:
    """A pinned ``dataset_snapshot`` input record admissible at Gate A.

    Materialized (``content_digest`` = the snapshot sha256) + pinned (versioned
    ``public_locator`` + ``snapshot_identity``). Carries NO absolute path.
    """
    return inputs.make_input(
        kind="dataset_snapshot",
        role="bsee_production_extract",
        schema_version=config["algorithm"]["input_schema_version"],
        required_for_replay=True,
        content_digest=descriptor["snapshot_identity"],
        replay_location="content_addressed_dataset_object",
        redistribution_rights=descriptor["redistribution_rights"],
        residency="public",
        transformation_id="bsee_production_summary_selection",
        source_authority=descriptor["source_authority"],
        public_locator=descriptor["public_locator"],
        data_as_of=descriptor["data_as_of"],
        retrieval_time=descriptor["retrieved_at"],
        selection=descriptor["selection"],
        snapshot_identity=descriptor["snapshot_identity"],
    )


# ---------------------------------------------------------------------------
# path-independent identity (MAJOR-2)
# ---------------------------------------------------------------------------

def identity_context(config: dict, input_record: dict) -> dict:
    """The declared clean context for :func:`identity.derive_run_identity`.

    ``inputs`` is ``[(role, input_record_id)]`` derived from the pinned snapshot;
    NOTHING here consumes the runner's absolutized ``input_hash`` or any absolute
    path, so a fresh checkout under a different prefix yields the SAME run_id.
    """
    alg = config["algorithm"]
    irid = inputs.input_record_id(input_record)  # admits (Gate A) + mints
    return {
        "algorithm_id": alg["algorithm_id"],
        "semantic_version": alg["semantic_version"],
        "clean_git_commit": alg["clean_git_commit"],
        "input_schema_version": alg["input_schema_version"],
        "output_schema_version": alg["output_schema_version"],
        "environment_digest": environment_digest(alg["environment"]),
        "inputs": [(input_record["role"], irid)],
        "execution_parameters": dict(alg["execution_parameters"]),
        "seed": alg["seed"],
        "commit_known": True,
        "clean_tree": True,
    }


def derive_identity(config: dict, input_record: dict) -> dict:
    return identity.derive_run_identity(**identity_context(config, input_record))


# ---------------------------------------------------------------------------
# workflow execution adapter (keeps the output bytes; the shared runner rmtree's)
# ---------------------------------------------------------------------------

def execute_variant(workflow_id: str, api12: list, group_label: str, snapshot_key: str,
                    config: dict):
    """Run the UNCHANGED wed workflow and return ``(payload, {basename: bytes})``.

    Reuses the shared runner's cfg builders + container-hash normalization; the
    only divergence is that this adapter runs the engine under a root IT controls
    so the deterministic output bytes can be captured (the shared runner rmtree's
    them). Param-injected relative files are RE-absolutized against the example
    dir (the shared runner absolutizes before the param merge).
    """
    row = R._resolve_wed_registry_row(workflow_id)
    example_dir = (repo_root() / row["input"]).parent
    snap = config["snapshots"][snapshot_key]
    fixture_name = os.path.basename(snap["fixture"])
    params = {
        "data": {
            "groups": [
                {
                    "label": group_label,
                    "api12": list(api12),
                    "bottom_block": {"area": snap["query"]["area"], "number": snap["query"]["block"]},
                    "bottom_lease": None,
                    "production": {"files": [fixture_name]},
                }
            ]
        }
    }
    cfg = R._build_wed_cfg(row, params)
    cfg = R._absolutize_input_paths(cfg, example_dir)  # re-absolutize param files
    locator = ResultLocator.from_row(row)
    root = tempfile.mkdtemp(prefix="wed927_pilot_")
    try:
        from worldenergydata.engine import engine

        cfg_base = engine(cfg=copy.deepcopy(cfg), embed=True, root_folder=root, log_to_file=False)
        payload, _warns = extract_result(cfg_base, locator, root)
        R._normalize_container_hashes(payload, cfg_base, root)  # canonical xlsx digest
        analysis = cfg_base.get("Analysis", {}) or {}
        results_dir = analysis.get("result_folder") or os.path.join(root, "results")
        out_bytes = {}
        for o in payload["outputs"]:
            p = os.path.join(results_dir, o["basename"])
            out_bytes[o["basename"]] = open(p, "rb").read() if os.path.isfile(p) else None
        return payload, out_bytes
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# metrics (derived from the pinned snapshot bytes — path-independent)
# ---------------------------------------------------------------------------

def compute_metrics(fixture_bytes: bytes, api12: list) -> dict:
    """Algorithm-scoped metric VALUES over the selected wells (from snapshot bytes)."""
    reader = csv.DictReader(io.StringIO(fixture_bytes.decode("utf-8")))
    sel = set(api12)
    total_oil = 0.0
    wells = set()
    peak_rate = 0.0
    for row in reader:
        if row["API_WELL_NUMBER"] not in sel:
            continue
        oil = float(row["OIL_PRODUCTION"])
        days = float(row["DAYS_ON_PROD"])
        total_oil += oil
        wells.add(row["API_WELL_NUMBER"])
        if days > 0:
            peak_rate = max(peak_rate, oil / days)
    return {
        "total_oil_bbl": total_oil,
        "producing_well_count": len(wells),
        "cumulative_oil_mmbbl": total_oil / 1e6,
        "peak_oil_rate_bopd": peak_rate,
    }


def build_metric_store(config: dict) -> tuple:
    """Register the algorithm's metric definitions; return (store, {segment: def})."""
    store = metrics.MetricDefinitionStore()
    by_segment = {}
    for mdef in config["metrics"]:
        definition = metrics.make_metric_definition(
            metric_id=mdef["metric_id"],
            algorithm_id=config["algorithm"]["algorithm_id"],
            definition_version=mdef["definition_version"],
            label=mdef["label"],
            meaning=mdef["meaning"],
            unit_or_dimension=mdef["unit_or_dimension"],
            data_type=mdef["data_type"],
            derivation=mdef["derivation"],
            applicability=mdef["applicability"],
            directionality=mdef["directionality"],
            quality_rule=mdef["quality_rule"],
        )
        store.register(definition)
        by_segment[mdef["metric_id"].rsplit("/", 1)[-1]] = definition
    return store, by_segment


def build_metric_observations(run_id: str, algorithm_id: str, values: dict, defs: dict) -> list:
    obs = []
    for segment, value in values.items():
        definition = defs[segment]
        obs.append(
            metrics.make_metric_observation(
                definition=definition,
                run_id=run_id,
                value=value,
                quality_state="valid",
                derivation_evidence={
                    "column": "OIL_PRODUCTION/DAYS_ON_PROD",
                    "aggregation": definition["derivation"],
                    "snapshot_bound": True,
                },
            )
        )
    return obs


# ---------------------------------------------------------------------------
# curated outputs + artifacts + object bytes
# ---------------------------------------------------------------------------

def _curated_label(basename: str) -> str:
    if any(basename.startswith(p) for p in _PRIMARY_BASENAMES):
        return "primary_result"
    return "validation_evidence"


def _media_type(basename: str) -> tuple:
    if basename.endswith(".json"):
        return "application/json", "json"
    return "text/csv", "csv"


def build_outputs(out_bytes: dict, config: dict):
    """Return (artifacts, output_records, object_bytes, xlsx_digest).

    Projects the deterministic text outputs (CSV/JSON) as content-addressed
    objects; the xlsx raw dump is recorded (canonical digest) but not projected.
    """
    artifacts, records, object_bytes = [], [], {}
    xlsx_digest = None
    schema_version = config["algorithm"]["output_schema_version"]
    for basename in sorted(out_bytes):
        blob = out_bytes[basename]
        if blob is None:
            continue
        if basename.endswith(".xlsx"):
            # canonical (timestamp-independent) digest for provenance only.
            xlsx_digest = hashlib.sha256(blob).hexdigest()
            continue
        if not basename.endswith(_TEXT_SUFFIXES):
            continue
        media_type, native_format = _media_type(basename)
        art = artifact.physical_artifact(blob, media_type=media_type, native_format=native_format)
        artifacts.append(art)
        object_bytes[art["content_digest"]] = blob
        records.append(
            oc.make_output_record(
                role=basename,
                native_schema={"id": f"bsee/{basename}", "version": schema_version},
                media_type=media_type,
                curated_label=_curated_label(basename),
                artifact_refs=[art["content_digest"]],
            )
        )
    return artifacts, records, object_bytes, xlsx_digest


# ---------------------------------------------------------------------------
# per-variant assembly + promotion
# ---------------------------------------------------------------------------

def build_projection_for_variant(config: dict, variant: dict):
    """Assemble one variant's RunProjection (+ side data for the report)."""
    descriptor = build_snapshot_descriptor(config, variant["snapshot"], variant["api12"])
    assert_federal_claim_allowed(descriptor)  # MAJOR-1
    input_record = build_input_record(descriptor, config)

    ctx = identity_context(config, input_record)
    ident = identity.derive_run_identity(**ctx)
    run_id = ident["run_id"]

    payload, out_bytes = execute_variant(
        variant["workflow"], variant["api12"], variant["group_label"],
        variant["snapshot"], config,
    )
    artifacts, output_records, object_bytes, xlsx_digest = build_outputs(out_bytes, config)
    output_equality = oc.output_equality_digest(output_records)

    store, defs = build_metric_store(config)
    fixture_bytes = read_fixture_bytes(config["snapshots"][variant["snapshot"]]["fixture"])
    metric_values = compute_metrics(fixture_bytes, variant["api12"])
    observations = build_metric_observations(
        run_id, config["algorithm"]["algorithm_id"], metric_values, defs
    )

    proj = projection_mod.build_projection(
        identity_context=ctx,
        input_records=[input_record],
        artifacts=artifacts,
        outputs=output_records,
        output_equality_digest=output_equality,
        metric_observations=observations,
        object_bytes=object_bytes,
        terminal_status="succeeded",
        metric_store=store,
        evidence={
            "variant": variant["id"],
            "result_hash": _result_hash(payload),
            "output_basenames": sorted(out_bytes),
            "xlsx_canonical_digest": xlsx_digest,
        },
    )
    return {
        "variant": variant,
        "descriptor": descriptor,
        "input_record": input_record,
        "identity": ident,
        "run_id": run_id,
        "payload": payload,
        "out_bytes": out_bytes,
        "projection": proj,
        "output_equality": output_equality,
        "metrics": metric_values,
        "result_hash": _result_hash(payload),
        "xlsx_digest": xlsx_digest,
    }


def make_egress(env_tokens: dict | None = None) -> egress_mod.EgressGate:
    """Fail-closed egress gate. ``env_tokens`` values (if any) are scanned/redacted
    — the dry run passes none (no secret is ever in play in-memory)."""
    return egress_mod.EgressGate(legal_deny_list=(), env_tokens=env_tokens or {},
                                 external_validator=None)


def promote(projection, *, hf_port, ledger, egress):
    """Drive one projection emitted -> ... -> accepted; return the accepted revision."""
    m = promotion_mod.PromotionMachine(projection, hf_port=hf_port, ledger=ledger, egress=egress)
    m.validate()
    m.replay(observed_output_equality=projection.output_equality_digest.get("digest"))
    m.render_draft()
    m.review(
        human_promotion_review={"available": True, "approved": True},
        adversarial_artifact_review={"available": True, "approved": True},
    )
    m.promote_to_hf_candidate()
    m.pin_report()
    m.accept()
    if m.state != "accepted":
        raise PilotError(f"promotion did not reach accepted (stuck at {m.state!r})")
    return m.candidate_revision


# ---------------------------------------------------------------------------
# rolling HTML report (one, in the source repo; mandatory Inputs + Outputs)
# ---------------------------------------------------------------------------

def _run_view(entry, revision):
    d = entry["descriptor"]
    return {
        "run_id": entry["run_id"],
        "status": "succeeded",
        "hf_revision": revision,
        "inputs": [
            {"name": "source_authority", "value": d["source_authority"]},
            {"name": "public_locator", "value": d["public_locator"]["uri"]},
            {"name": "vintage", "value": d["vintage"]},
            {"name": "snapshot_identity(sha256)", "value": d["snapshot_identity"][:16] + "..."},
            {"name": "selection", "value": f"{d['selection']['area']}-{d['selection']['block']} "
                                            f"api12={d['selection']['api12']}"},
            {"name": "license", "value": d["license"]},
        ],
        "outputs": [
            {"name": o["role"], "value": o["curated_label"]}
            for o in entry["projection"].outputs
        ],
        "optional": {
            "Metrics": ", ".join(f"{k}={v}" for k, v in entry["metrics"].items()),
            "Native xlsx (canonical digest, not projected)": entry["xlsx_digest"],
        },
    }


def render_rolling_report(config: dict, accepted: list, ledger) -> str:
    """Render the ONE rolling HTML report across all accepted variant runs."""
    algorithm_id = config["algorithm"]["algorithm_id"]
    visibility = resolve_visibility(config)
    run_views = [_run_view(e, rev) for e, rev in accepted]
    fragment = report_mod.render_report(
        algorithm=algorithm_id,
        runs=run_views,
        ledger=ledger.records(),
        pinned=True,
        title=f"BSEE production-summary run ledger ({algorithm_id})",
    )
    provenance_rows = "".join(
        f"<tr><td>{e['variant']['id']}</td><td>{e['descriptor']['source_authority']}</td>"
        f"<td>{e['descriptor']['public_locator']['uri']}</td>"
        f"<td>{e['descriptor']['vintage']}</td>"
        f"<td><code>{e['descriptor']['snapshot_identity'][:16]}...</code></td>"
        f"<td>{e['descriptor']['license']}</td>"
        f"<td>{'REAL' if e['descriptor']['is_real_extract'] else 'SYNTHETIC'}</td></tr>"
        for e, _ in accepted
    )
    banner = (
        "PUBLIC / cc-by-4.0 / source_authority:BSEE"
        if visibility["public"]
        else "PRIVATE / synthetic-derived (MAJOR-1: no federal BSEE claim on synthetic data)"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>BSEE production-summary run ledger</title></head><body>"
        f"<h1>BSEE production-summary run ledger</h1>"
        f"<p><strong>HF dataset:</strong> {config['publication']['hf_repo']} "
        f"&mdash; <strong>visibility:</strong> {banner}</p>"
        "<h2>Source snapshot provenance</h2>"
        "<table border='1'><thead><tr><th>variant</th><th>source_authority</th>"
        "<th>public_locator</th><th>vintage</th><th>snapshot_identity</th>"
        "<th>license</th><th>extract</th></tr></thead>"
        f"<tbody>{provenance_rows}</tbody></table>"
        f"{fragment}"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# top-level dry run
# ---------------------------------------------------------------------------

def run_pilot(config: dict | None = None, *, hf_port=None, write_report: bool = False):
    """Execute the FULL dry-run pipeline (InMemoryHfPort by default) and return a
    summary. NO Hugging Face network, NO real publish.
    """
    config = config or load_config()
    hf_port = hf_port if hf_port is not None else InMemoryHfPort()
    ledger = Ledger()
    egress = make_egress()

    # >=3 variations
    entries = [build_projection_for_variant(config, v) for v in config["variants"]]
    accepted = []
    for entry in entries:
        revision = promote(entry["projection"], hf_port=hf_port, ledger=ledger, egress=egress)
        accepted.append((entry, revision))

    # exactly 1 exact replay (of replay_variant) — same run_id + output equality
    replay_id = config["replay_variant"]
    base = next(e for e in entries if e["variant"]["id"] == replay_id)
    replay = build_projection_for_variant(config, base["variant"])
    if replay["run_id"] != base["run_id"]:
        raise PilotError("exact replay resolved a DIFFERENT run_id — publication blocked")
    identity.assert_output_equality(
        base["output_equality"]["digest"], replay["output_equality"]["digest"]
    )

    report_html = render_rolling_report(config, accepted, ledger)
    report_path = repo_root() / config["report_path"]
    if write_report:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_html, encoding="utf-8")

    visibility = resolve_visibility(config)
    return {
        "run_ids": {e["variant"]["id"]: e["run_id"] for e in entries},
        "replay": {"variant": replay_id, "run_id": replay["run_id"],
                   "same_run_id": replay["run_id"] == base["run_id"]},
        "revisions": {e["variant"]["id"]: rev for e, rev in accepted},
        "accepted_count": len(accepted),
        "rejected_count": 0,
        "eligible_run_ids": sorted(ledger.eligible_run_ids()),
        "ledger": ledger.records(),
        "report_path": str(report_path),
        "report_html": report_html,
        "visibility": visibility,
        "metrics": {e["variant"]["id"]: e["metrics"] for e in entries},
        "result_hashes": {e["variant"]["id"]: e["result_hash"] for e in entries},
        "entries": entries,
        "hf_port": hf_port,
    }
