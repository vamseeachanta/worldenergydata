"""Source manifest integrity: every shipped row traces to a reviewed public file."""

import json

import pytest

from worldenergydata.india_dgh import load_awarded_blocks, load_source_manifest
from worldenergydata.india_dgh.sources import data_path, verify_file

PUBLIC_HOSTS = (
    "https://www.dghindia.gov.in/",
    "https://dghindia.gov.in/",
    "https://ppac.gov.in/",
    "https://www.ppac.gov.in/",
    "https://web.archive.org/",
)


def test_manifest_entries_are_public_and_pinned():
    manifest = load_source_manifest()
    for entry in manifest["files"]:
        assert entry["url"].startswith(PUBLIC_HOSTS), entry["id"]
        assert "ndrdgh" not in entry["url"]  # NDR needs registration; never used
        assert len(entry["sha256"]) == 64 and entry["terms_url"].startswith("https://")


def test_every_block_row_cites_a_manifest_file():
    ids = {e["id"] for e in load_source_manifest()["files"]}
    assert set(load_awarded_blocks().source_id) <= ids


def test_manifest_rejects_entry_without_digest(tmp_path, monkeypatch):
    bad = {
        "files": [
            {
                "id": "x",
                "publisher": "p",
                "title": "t",
                "url": "https://ppac.gov.in/x",
                "filename": "x",
                "sha256": "",
                "retrieved": "2026-10-31",
                "terms_url": "https://x",
            }
        ]
    }
    target = tmp_path / "source_manifest.json"
    target.write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr(
        "worldenergydata.india_dgh.sources.data_path", lambda name: tmp_path / name
    )
    with pytest.raises(ValueError, match="SHA-256"):
        load_source_manifest()


def test_verify_file_detects_changed_bytes(tmp_path):
    entry = load_source_manifest()["files"][0]
    changed = tmp_path / entry["filename"]
    changed.write_bytes(b"replaced by publisher")
    with pytest.raises(ValueError, match="does not match"):
        verify_file(changed, entry["id"])


def test_shipped_tables_exist():
    for name in ("awarded_blocks.csv", "basins.csv", "production.csv"):
        assert data_path(name).is_file(), name


def test_module_manifest_example_imports_and_loads_tables():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[3]
    manifest = yaml.safe_load((root / "module-manifest.yaml").read_text())
    entries = manifest["modules"]
    entry = next(item for item in entries if item["id"] == "india_dgh")
    namespace = {}
    exec(entry["entry_point"], namespace)
    assert entry["key_classes"] == [
        "load_awarded_blocks",
        "load_production",
        "load_basins",
    ]
    assert {name: len(namespace[name]()) for name in entry["key_classes"]} == {
        "load_awarded_blocks": 175,
        "load_production": 960,
        "load_basins": 26,
    }


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("matches", [False, True])
def test_fetch_validates_before_writing(tmp_path, monkeypatch, existing, matches):
    import hashlib
    import runpy
    from pathlib import Path
    from types import SimpleNamespace

    root = Path(__file__).resolve().parents[3]
    script = runpy.run_path(str(root / "scripts/india_dgh/fetch_sources.py"))
    main = script["main"]
    payload = b"reviewed source" if matches else b"different source"
    manifest = {
        "files": [
            {
                "id": "test_source",
                "filename": "source.bin",
                "url": "https://ppac.gov.in/source",
                "sha256": hashlib.sha256(b"reviewed source").hexdigest(),
            }
        ]
    }
    monkeypatch.setitem(
        main.__globals__,
        "MANIFEST",
        SimpleNamespace(read_text=lambda **kwargs: json.dumps(manifest)),
    )
    monkeypatch.setitem(main.__globals__, "fetch", lambda url: payload)
    target = tmp_path / "source.bin"
    if existing:
        target.write_bytes(b"original source")
    assert main(["--dest", str(tmp_path)]) == (0 if matches else 1)
    if matches:
        assert target.read_bytes() == payload
    elif existing:
        assert target.read_bytes() == b"original source"
    else:
        assert not target.exists()


def test_package_author_metadata_has_no_email():
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10; provided by pytest
        import tomli as tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    metadata = tomllib.loads(
        (root / "packages/worldenergydata-india_dgh/pyproject.toml").read_text()
    )
    assert all("email" not in author for author in metadata["project"]["authors"])
