"""Offline entry-point checks with synthetic ZIPs and provenance."""

import importlib.util
import json
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from tests.unit.bsee.fieldreserves_helpers import FIXTURES, archive, history_archive
from worldenergydata.bsee.fieldreserves_fetch import (
    BASE,
    DISCLAIMER,
    emit_manifest,
    record,
)

ROOT = Path(__file__).parents[3]
spec = importlib.util.spec_from_file_location(
    "fieldreserves_entry", ROOT / "scripts/bsee/fetch_fieldreserves_family.py"
)
assert spec is not None and spec.loader is not None
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("live network forbidden")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", denied)


def cache(root: Path) -> None:
    records = []
    for name, body in [
        ("2023 Hist.zip", history_archive()),
        (
            "mastproddelimit.zip",
            archive(
                "mastproddelimit.txt", (FIXTURES / "synthetic_master.csv").read_bytes()
            ),
        ),
        (
            "appendbdelimit.zip",
            archive(
                "appendbdelimit.txt",
                b'"G00001","ZZ001","ZZ","001","ZZ 001"\n',
            ),
        ),
    ]:
        (root / name).write_bytes(body)
        records.append(
            record(
                BASE + "/FieldReserves/Files/" + name.replace(" ", "%20"),
                body,
                "2026-10-11T00:00:00Z",
            )
        )
    (root / "manifest.json").write_text(emit_manifest(records, terms=DISCLAIMER))


def test_cached_entry_emits_schema_and_complete_rows(tmp_path: Path) -> None:
    cache(tmp_path)
    # Input rows: three synthetic history, two master, one Appendix B mapping.
    assert entry.curate_cache(tmp_path) == {
        "history": 3,
        "production_master": 2,
        "appendix": 1,
    }
    data = json.loads((tmp_path / "schema.json").read_text())
    assert data["history"]["FIELD_NAME_CODE"] == "string"
    assert data["monthly"]["status"] == "fetch_only"
    assert data["appendix"]["BLOCK_NUMBER"] == "string"
    assert data["units"]["appendix"] == "Identifiers only; no physical quantities"
    assert (tmp_path / "curated_history.csv").read_text().count("\n") == 4
    assert (
        "G00001,ZZ001,ZZ,001,ZZ 001," in (tmp_path / "curated_appendix.csv").read_text()
    )


def test_cached_entry_rejects_tampered_original(tmp_path: Path) -> None:
    cache(tmp_path)
    (tmp_path / "2023 Hist.zip").write_bytes(b"tampered synthetic")
    with pytest.raises(ValueError, match="digest/size"):
        entry.curate_cache(tmp_path)


def test_cached_entry_rejects_wrong_origin(tmp_path: Path) -> None:
    cache(tmp_path)
    path = tmp_path / "manifest.json"
    path.write_text(path.read_text().replace(BASE, "https://other.gov"))
    with pytest.raises(ValueError, match="provenance"):
        entry.curate_cache(tmp_path)


def test_later_source_failure_leaves_no_partial_curated_output(tmp_path: Path) -> None:
    cache(tmp_path)
    (tmp_path / "mastproddelimit.zip").write_bytes(b"tampered synthetic")
    with pytest.raises(ValueError, match="digest/size"):
        entry.curate_cache(tmp_path)
    assert not list(tmp_path.glob("curated_*.csv"))


def test_existing_schema_preserved_before_any_writes(tmp_path: Path) -> None:
    cache(tmp_path)
    (tmp_path / "schema.json").write_text("preserved synthetic schema")
    with pytest.raises(FileExistsError):
        entry.curate_cache(tmp_path)
    assert (tmp_path / "schema.json").read_text() == "preserved synthetic schema"
    assert not list(tmp_path.glob("curated_*.csv"))


def test_appendix_digest_failure_leaves_no_curated_output(tmp_path: Path) -> None:
    cache(tmp_path)
    (tmp_path / "appendbdelimit.zip").write_bytes(b"tampered synthetic")
    with pytest.raises(ValueError, match="digest/size"):
        entry.curate_cache(tmp_path)
    assert not list(tmp_path.glob("curated_*.csv"))
    assert not (tmp_path / "schema.json").exists()


def test_existing_appendix_output_is_preserved(tmp_path: Path) -> None:
    cache(tmp_path)
    target = tmp_path / "curated_appendix.csv"
    target.write_text("preserved synthetic output")
    with pytest.raises(FileExistsError):
        entry.curate_cache(tmp_path)
    assert target.read_text() == "preserved synthetic output"
    assert not (tmp_path / "curated_history.csv").exists()
