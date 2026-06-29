# ABOUTME: run_workflow() for worldenergydata — drives wed engine embed (workspace-hub#3286).
# ABOUTME: Reuses assetutilities ResultEnvelope/extract_result/hashing (workspace-hub#3282).

"""Deterministic, in-process worldenergydata workflow runner.

``run_workflow`` resolves a bare single-registry id against wed's own
``docs/registry/workflows.yaml``, builds the run cfg from the row's example
input, and runs the wed engine in EMBED mode under a throwaway ``tempfile.mkdtemp``
root (``engine(cfg=..., embed=True, root_folder=tmp, log_to_file=False)``). All
result + log writes land under that root, which is ``rmtree``'d afterwards, so the
repo/example dirs stay byte-for-byte untouched. Determinism + provenance come
entirely from the shared ``assetutilities.workflow_api`` primitives
(workspace-hub#3282); wed stamps its OWN ``code_version("worldenergydata")``.

Note: wed's bsee router resolves a workflow's input CSVs relative to
``Analysis.analysis_root_folder`` (which embed sets to the injected root). So the
runner ABSOLUTIZES the example's ``data.groups[].production.files`` against the
example directory before the embed run — inputs are read from the repo while
outputs still write under the injected root.
"""

from __future__ import annotations

import copy
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path

import yaml

PACKAGE_NAME = "worldenergydata"

# OOXML / ZIP-container output formats: a ZIP of XML parts whose CONTAINER bytes
# vary every run even when the logical data is identical -- the ZIP records each
# member's mtime as wall-clock at write time, and openpyxl stamps
# ``docProps/core.xml`` with ``created``/``modified`` from ``datetime.now()``.
# Hashing the raw bytes is therefore non-deterministic; we hash normalized member
# content instead (see ``_canonical_content_digest``).
_ZIP_CONTAINER_SUFFIXES = (".xlsx", ".xlsm", ".xltx", ".docx", ".pptx", ".zip")
# Members whose bytes embed wall-clock timestamps; excluded from the digest.
_VOLATILE_ZIP_MEMBERS = frozenset({"docProps/core.xml"})


def _canonical_content_digest(path: str) -> str:
    """Location- and timestamp-independent content digest for one output file.

    Plain files hash by raw bytes (matching ``extract_result``). ZIP-container
    formats (xlsx/docx/...) are digested over their SORTED decompressed members,
    skipping the volatile metadata parts -- ``zipfile.read`` returns logical member
    bytes independent of the ZIP mtime, so the actual sheet/data parts still flow
    into the hash (content-sensitive) while the per-run timestamps do not.
    """
    if path.lower().endswith(_ZIP_CONTAINER_SUFFIXES) and zipfile.is_zipfile(path):
        h = hashlib.sha256()
        with zipfile.ZipFile(path) as zf:
            for name in sorted(zf.namelist()):
                if name in _VOLATILE_ZIP_MEMBERS:
                    continue
                h.update(name.encode("utf-8"))
                h.update(hashlib.sha256(zf.read(name)).digest())
        return h.hexdigest()
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _normalize_container_hashes(payload: dict, cfg_base: dict, root: str) -> None:
    """Rewrite ``outputs[].sha256`` to the timestamp-independent digest in place.

    ``extract_result`` hashes raw bytes, which makes ZIP-container outputs (e.g.
    the bsee ``prod_raw_*.xlsx``) flip the determinism hash every run. We recompute
    each file's digest canonically; for non-container files this reproduces the
    exact raw-bytes digest, so it is a no-op there.
    """
    if payload.get("kind") != "files":
        return
    analysis = cfg_base.get("Analysis", {}) or {}
    results_dir = analysis.get("result_folder") or os.path.join(root, "results")
    for out in payload.get("outputs", []):
        path = os.path.join(results_dir, out.get("basename", ""))
        if os.path.isfile(path):
            out["sha256"] = _canonical_content_digest(path)


def _wed_repo_root() -> Path:
    # runner.py -> workflow_api -> worldenergydata -> src -> <repo root>
    return Path(__file__).resolve().parents[3]


def registry_path() -> Path:
    return _wed_repo_root() / "docs" / "registry" / "workflows.yaml"


def _load_registry() -> dict:
    with open(registry_path()) as fh:
        return yaml.safe_load(fh)


def _resolve_wed_registry_row(workflow_id: str) -> dict:
    for row in _load_registry().get("workflows", []):
        if row.get("id") == workflow_id:
            return row
    raise KeyError(f"unknown workflow_id '{workflow_id}' (not in {registry_path()})")


def _lookup_row_for_cfg(cfg: dict) -> dict | None:
    basename = cfg.get("basename")
    if not basename:
        return None
    for row in _load_registry().get("workflows", []):
        if row.get("basename") == basename or row.get("id") == basename:
            return row
    return None


def _ensure_default_block(cfg: dict) -> dict:
    """Ensure the ``default.config.overwrite.output`` key the embed path needs.

    The regular (non-embed) config path merges assetutilities' packaged base
    config, which supplies a ``default:`` block; ``configure_embed`` deliberately
    skips that merge (it dispatches the caller cfg directly), so a cfg run via
    embed must already carry the block ``configure_overwrite_filenames`` reads.
    wed's example inputs were written for the normal path and omit it, so inject
    the canonical default here without clobbering a caller-provided value.
    ``overwrite.output: True`` also gives stable (timestamp-free) output
    basenames, which keeps the determinism hash reproducible across runs.
    """
    default = cfg.setdefault("default", {})
    default.setdefault("log_level", "DEBUG")
    config = default.setdefault("config", {})
    overwrite = config.setdefault("overwrite", {})
    overwrite.setdefault("output", True)
    return cfg


def _absolutize_input_paths(cfg: dict, example_dir: Path) -> dict:
    """Rewrite relative workflow input file refs to absolute example paths.

    wed routers resolve inputs against ``Analysis.analysis_root_folder`` (the
    injected embed root). The example's ``production.files`` are relative to the
    example directory, so we make them absolute here; outputs are unaffected.
    """
    for group in cfg.get("data", {}).get("groups", []) or []:
        production = group.get("production", {}) or {}
        files = production.get("files")
        if not files:
            continue
        production["files"] = [
            str((example_dir / f).resolve()) if not Path(f).is_absolute() else f
            for f in files
        ]
    return cfg


def _build_wed_cfg(row: dict, params: dict | None) -> dict:
    from assetutilities.common.update_deep import update_deep_dictionary

    cfg: dict = {"basename": row["basename"]}
    input_rel = row.get("input")
    if input_rel:
        example_path = _wed_repo_root() / input_rel
        with open(example_path) as fh:
            example_cfg = yaml.safe_load(fh) or {}
        cfg = update_deep_dictionary(cfg, example_cfg)
        cfg = _absolutize_input_paths(cfg, example_path.parent)
    if params:
        cfg = update_deep_dictionary(cfg, copy.deepcopy(params))
    cfg = _ensure_default_block(cfg)
    return cfg


def run_workflow(
    workflow_id: str | None = None,
    params: dict | None = None,
    cfg: dict | None = None,
    verify_reproducible: bool = False,
):
    """Run a wed registry workflow in-process and return a typed ResultEnvelope.

    Fail-closed: an unknown id or a router exception returns a
    ``status="error"`` envelope, never raised.
    """
    # Imported lazily so the (heavy) engine + contract imports stay off module load.
    import shutil

    from assetutilities.workflow_api import ResultEnvelope
    from assetutilities.workflow_api.envelope import (
        compute_reproducible,
        input_hash,
        make_provenance,
        result_hash,
        utc_now_iso,
    )
    from assetutilities.workflow_api.runner import ResultLocator, extract_result

    wid = workflow_id or "(inline-cfg)"
    try:
        if cfg is None:
            row = _resolve_wed_registry_row(workflow_id)
            cfg = _build_wed_cfg(row, params)
            locator = ResultLocator.from_row(row)
        else:
            cfg = _ensure_default_block(copy.deepcopy(cfg))
            row = _lookup_row_for_cfg(cfg)
            locator = (
                ResultLocator.from_row(row) if row else ResultLocator.default_for(cfg)
            )

        ihash = input_hash(cfg)

        def _run_once():
            from worldenergydata.engine import engine

            root = tempfile.mkdtemp(prefix="wed_wf_")
            try:
                cfg_base = engine(
                    cfg=copy.deepcopy(cfg),
                    embed=True,
                    root_folder=root,
                    log_to_file=False,
                )
                payload, warns = extract_result(cfg_base, locator, root)
                # extract_result hashes raw bytes; rewrite container outputs (xlsx)
                # to a timestamp-independent digest so the hash is stable per run.
                _normalize_container_hashes(payload, cfg_base, root)
                return payload, warns, result_hash(payload)
            finally:
                shutil.rmtree(root, ignore_errors=True)

        payload, warns, rhash = _run_once()
        repro = compute_reproducible(lambda: _run_once()[2], rhash, verify_reproducible)
        return ResultEnvelope(
            workflow_id=wid,
            status="ok",
            result=payload,
            provenance=make_provenance(
                ihash, package_name=PACKAGE_NAME, data_as_of=utc_now_iso()
            ),
            determinism={"result_hash": rhash, "reproducible": repro},
            confidence=None,
            warnings=warns,
        )
    except Exception as exc:  # fail-closed -> error envelope
        return ResultEnvelope(
            workflow_id=wid,
            status="error",
            result={},
            provenance=make_provenance(None, package_name=PACKAGE_NAME),
            determinism={"result_hash": None, "reproducible": None},
            confidence=None,
            warnings=[str(exc)],
        )
