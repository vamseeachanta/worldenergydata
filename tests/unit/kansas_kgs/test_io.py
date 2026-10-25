"""Tests for Kansas KGS pressure-observation output persistence."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest


def test_output_writer_enforces_ace_root(tmp_path) -> None:
    from worldenergydata.kansas_kgs.io import write_pressure_observation_outputs

    with pytest.raises(ValueError, match="/mnt/ace"):
        write_pressure_observation_outputs(
            normalized_pressure=pd.DataFrame(),
            normalized_wells=pd.DataFrame(),
            observations=pd.DataFrame(),
            coverage=pd.DataFrame(),
            quality={},
            output_root=tmp_path,
        )


def test_output_writer_writes_csv_parquet_quality_manifest(tmp_path) -> None:
    from worldenergydata.kansas_kgs.io import (
        load_pressure_observations,
        write_pressure_observation_outputs,
    )

    observations = pd.DataFrame(
        [
            {
                "api10": "1506720048",
                "api_state_code": "15",
                "api_county_code": "067",
                "pressure_psia": 62.0,
            }
        ]
    )
    manifest = write_pressure_observation_outputs(
        normalized_pressure=pd.DataFrame([{"api10": "1506720048"}]),
        normalized_wells=pd.DataFrame([{"api10": "1506720048"}]),
        observations=observations,
        coverage=pd.DataFrame([{"county_name": "Grant", "test_year": 1997}]),
        quality={"row_count": 1},
        output_root=tmp_path,
        generated_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
        input_paths=[tmp_path / "raw/manifest.json"],
        source_manifest={
            "sources": {
                "pressure_proration": {
                    "source_url": "https://www.kgs.ku.edu/source.txt",
                    "sha256": "raw-sha",
                    "observed_at": "2026-07-03T00:00:00Z",
                }
            }
        },
        limitations=["not_initial_reservoir_pressure"],
        allow_non_ace_root=True,
        command="worldenergydata kansas-kgs build-pressure-observations",
        code_revision="abc123",
    )

    assert manifest.csv_path.exists()
    assert manifest.parquet_path.exists()
    assert manifest.quality_path.exists()
    assert manifest.manifest_path.exists()
    loaded = load_pressure_observations(manifest.csv_path)
    assert loaded.iloc[0]["api10"] == "1506720048"
    assert loaded.iloc[0]["api_state_code"] == "15"
    assert loaded.iloc[0]["api_county_code"] == "067"
    payload = json.loads(manifest.manifest_path.read_text(encoding="utf-8"))
    assert payload["generated_at"] == "2026-07-03T00:00:00Z"
    assert payload["row_count"] == 1
    assert payload["code_revision"] == "abc123"
    assert payload["code_dirty"] is None
    assert payload["source_manifest"]["sources"]["pressure_proration"]["sha256"] == (
        "raw-sha"
    )
    assert payload["limitations"] == ["not_initial_reservoir_pressure"]
    assert payload["output_hashes"]["well_pressure_observations.csv"]["size_bytes"] > 0
    assert (
        len(payload["output_hashes"]["well_pressure_observations.csv"]["sha256"]) == 64
    )
    assert not list(tmp_path.rglob(".staging-*"))


def test_output_writer_does_not_promote_normalized_files_when_curated_write_fails(
    tmp_path,
    monkeypatch,
) -> None:
    from worldenergydata.kansas_kgs.io import (
        NORMALIZED_PRESSURE,
        NORMALIZED_WELLS,
        write_pressure_observation_outputs,
    )

    original_to_parquet = pd.DataFrame.to_parquet

    def fail_curated_parquet(self, path, *args, **kwargs):
        if Path(path).name == "well_pressure_observations.parquet":
            raise RuntimeError("curated parquet failed")
        return original_to_parquet(self, path, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fail_curated_parquet)

    with pytest.raises(RuntimeError, match="curated parquet failed"):
        write_pressure_observation_outputs(
            normalized_pressure=pd.DataFrame([{"api10": "1506720048"}]),
            normalized_wells=pd.DataFrame([{"api10": "1506720048"}]),
            observations=pd.DataFrame([{"api10": "1506720048"}]),
            coverage=pd.DataFrame([{"county_name": "Grant", "test_year": 1997}]),
            quality={"row_count": 1},
            output_root=tmp_path,
            allow_non_ace_root=True,
        )

    assert not (tmp_path / NORMALIZED_PRESSURE).exists()
    assert not (tmp_path / NORMALIZED_WELLS).exists()
    assert not list(tmp_path.rglob(".staging-*"))


@pytest.mark.parametrize(
    "binding,missing",
    [(None, False)]
    + [
        (binding, missing)
        for binding in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "combined")
        for missing in (False, True)
    ],
)
def test_manifest_uses_package_revision_from_unrelated_repository(
    tmp_path, monkeypatch, binding, missing
):
    """Independent provenance oracle for issue #1352 (2026), defect 3.

    The package checkout has a HEAD; a fresh unrelated Git repository has
    none. The manifest must retain the package HEAD, not return the caller's
    absent revision, even with conflicting or invalid repository bindings.
    Dirty state is compared with Git's own tracked status. Both independent
    oracles exclude all inherited Git settings before bindings are injected.
    No commit or identity configuration is needed in the temporary repository.
    """
    import subprocess

    from worldenergydata.kansas_kgs import io

    oracle_env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    package_dir = Path(io.__file__).resolve().parent
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=package_dir, env=oracle_env, text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=package_dir,
            env=oracle_env,
            text=True,
        ).strip()
    )
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    subprocess.run(
        ["git", "init", "--quiet"], cwd=unrelated, env=oracle_env, check=True
    )
    target = tmp_path / "missing" if missing else unrelated
    bindings = {
        "GIT_DIR": target / ".git",
        "GIT_WORK_TREE": target,
        "GIT_COMMON_DIR": target / ".git",
    }
    for key, value in bindings.items():
        if binding in (key, "combined"):
            monkeypatch.setenv(key, str(value))
    monkeypatch.chdir(unrelated)
    caller_env = os.environ.copy()
    manifest = io.write_pressure_observation_outputs(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        {},
        output_root=tmp_path / "output",
        allow_non_ace_root=True,
    )
    payload = json.loads(manifest.manifest_path.read_text())
    assert (payload["code_revision"], payload["code_dirty"]) == (revision, dirty)
    assert dict(os.environ) == caller_env
