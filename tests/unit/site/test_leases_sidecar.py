"""Offline lease export contracts using only synthetic snapshot records."""

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from worldenergydata.common.fields_registry import load_fields


def _write(path, value):
    path.write_text(json.dumps(value, allow_nan=False) + "\n", encoding="utf-8")


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seal(snapshot):
    _write(
        snapshot / "extract_manifest.json",
        {
            "artifacts": [
                {
                    "file": name,
                    "sha256": _digest(snapshot / name),
                    "size_bytes": (snapshot / name).stat().st_size,
                }
                for name in ("leases.json", "panel_values.json")
            ],
            "source_manifest_sha256": _digest(snapshot / "source_manifest.json"),
        },
    )


@pytest.fixture
def case(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    registry = tmp_path / "fields.yml"
    inputs = yaml.safe_load(
        """
fields:
- canonical_id: alpha
  display_name: Synthetic alpha
  bsee:
    leases: [OCS-G 00011, G00012]
    area_blocks: [ZZ999, ZZ998, ZZ997]
- canonical_id: beta
  display_name: Synthetic beta
  bsee: {leases: [G00021]}
leases:
- lease_num: g00011
  area_block: AA101
  status: PROD
  effective_date: '2000-01-01'
  royalty_system: RS C
panel_values:
- lease_num: G 00011
  expiration_date: null
  expected_expiration_date: '2030-01-01'
  expiration_reason: Actual date absent; expected date is distinct
  current_owners:
  - &owner
    LEASE_NUMBER: G00011
    ASGN_STATUS_CODE: C
    SN_LSE_OWNER: '1'
    OWNER_GROUP_CODE: A
    OWNER_ALIQUOT_CD: '1'
    ASSIGNMENT_PCT: 75.0
    owner_name: null
    owner_name_reason: No unique current name
  - {<<: *owner, SN_LSE_OWNER: '2', OWNER_GROUP_CODE: B, OWNER_ALIQUOT_CD: '2'}
  current_operators:
  - LEASE_NUMBER: G00011
    ASGN_STATUS_CODE: C
    OPERATOR_NUM: '00001'
    operator_name: null
    operator_name_reason: Company number absent
  owner_reason: null
  operator_reason: No resolved current designated operator names
  surface_area: 100.0
  surface_area_unit_code: I
source_manifest:
  files:
  - file: synthetic.zip
    source_url: https://example.org/synthetic.zip
    retrieved_at_utc: '2026-01-01T00:00:00Z'
    terms: {limitations: Not a legal document}
"""
    )
    source_bytes = b"Synthetic source archive bytes\n"
    inputs["source_manifest"]["files"][0].update(
        sha256=hashlib.sha256(source_bytes).hexdigest(), size_bytes=len(source_bytes)
    )
    _write(registry, {"fields": inputs.pop("fields")})
    for name, value in inputs.items():
        _write(snapshot / f"{name}.json", value)
    _seal(snapshot)
    return snapshot, registry, tmp_path / "_leases.json"


def _export(case, fields=("alpha",)):
    from scripts.field_atlas.build_leases_sidecar import export_leases

    snapshot, registry, output = case
    return export_leases(snapshot, registry, list(fields), output)


def _edit(case, name, change):
    path = case[0] / name
    value = json.loads(path.read_text())
    change(value)
    _write(path, value)
    _seal(case[0])


def test_contract_roundtrip_provenance_and_determinism(case):
    before = {p: p.read_bytes() for p in case[0].iterdir()}
    result = _export(case)
    row, missing = result["fields"]["alpha"]["leases"]
    assert row["lease_num"] == "G00011"
    assert row["status"] == "PROD" and row["effective_date"] == "2000-01-01"
    assert row["area_block_source"] == "leases.json:area_block"
    assert row["area_block"] == "AA101"  # Source join, never registry list position.
    assert row["expiration_date"] is None and row["expiration_reason"]
    assert row["expected_expiration_date"] == "2030-01-01"
    assert (
        row["current_owners"]
        == json.loads((case[0] / "panel_values.json").read_text())[0]["current_owners"]
    )
    assert row["current_operators"][0]["operator_name"] is None
    assert row["current_operators"][0]["operator_name_reason"]
    assert row["operator_of_record_history"] is None and row["history_reason"]
    assert result["metadata"]["working_interest_unit"] == "percent (0-100)"
    assert row["surface_area_unit_code"] == "I"
    assert missing["lease_num"] == "G00012" and missing["missing"]
    registry = load_fields(case[1])
    assert all(registry.by_lease(r["lease_num"]) == "alpha" for r in (row, missing))
    metadata = result["metadata"]
    assert (
        metadata["source_references"]
        == json.loads((case[0] / "source_manifest.json").read_text())["files"]
    )
    for name in (
        "leases.json",
        "panel_values.json",
        "extract_manifest.json",
        "source_manifest.json",
    ):
        assert metadata["input_sha256"][name] == _digest(case[0] / name)
    assert metadata["input_sha256"]["registry"] == _digest(case[1])
    assert metadata["source_updated_at"] is None and metadata["limitations"]
    assert json.loads(case[2].read_text()) == result
    second = (case[0], case[1], case[2].with_name("second.json"))
    assert _export(second) == result
    assert second[2].read_bytes() == case[2].read_bytes()
    assert all(p.read_bytes() == content for p, content in before.items())


@pytest.mark.parametrize("name", ["leases.json", "panel_values.json"])
def test_missing_source_rows_have_nulls_and_reasons(case, name):
    _edit(case, name, lambda rows: rows.clear())
    row = _export(case)["fields"]["alpha"]["leases"][0]
    assert name in row["missing"]
    keys = (
        ("area_block", "status", "effective_date", "royalty_system")
        if name == "leases.json"
        else (
            "expiration_date",
            "expected_expiration_date",
            "current_owners",
            "current_operators",
        )
    )
    assert all(row[key] is None for key in keys)
    assert row["missing"][name]


@pytest.mark.parametrize("name", ["leases.json", "panel_values.json"])
@pytest.mark.parametrize("value", [{}, None, "", 42, False, [None], [1]])
def test_tables_require_arrays_of_records(case, name, value):
    _write(case[0] / name, value)
    _seal(case[0])
    with pytest.raises(ValueError, match="array of records"):
        _export(case)
    assert not case[2].exists()


@pytest.mark.parametrize(
    "digest",
    ["placeholder", "a" * 63, "a" * 65, "g" * 64, "a" * 64 + "\n", 1, True, []],
)
def test_source_digest_requires_sha256_hex_string(case, digest):
    _edit(
        case,
        "source_manifest.json",
        lambda manifest: manifest["files"][0].update(sha256=digest),
    )
    with pytest.raises(ValueError):
        _export(case)
    assert not case[2].exists()


def test_uppercase_source_digest_is_preserved(case):
    digest = hashlib.sha256(b"Synthetic source archive bytes\n").hexdigest().upper()
    _edit(
        case,
        "source_manifest.json",
        lambda manifest: manifest["files"][0].update(sha256=digest),
    )
    assert _export(case)["metadata"]["source_references"][0]["sha256"] == digest


def test_interrupted_write_leaves_destination_available_for_retry(case, monkeypatch):
    original_open = io.open

    class InterruptedStream:
        def __init__(self, stream):
            self.stream = stream

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def write(self, content):
            assert not case[2].exists()
            self.stream.write(content[:10])
            raise OSError("Simulated interrupted write")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

    def interrupted_open(file, mode="r", *args, **kwargs):
        stream = original_open(file, mode, *args, **kwargs)
        return InterruptedStream(stream) if "w" in mode or "x" in mode else stream

    before = set(case[2].parent.iterdir())
    with monkeypatch.context() as patch:
        patch.setattr(io, "open", interrupted_open)
        with pytest.raises(OSError, match="Simulated interrupted write"):
            _export(case)
    assert not case[2].exists()
    assert set(case[2].parent.iterdir()) == before
    result = _export(case)
    assert json.loads(case[2].read_text()) == result


def test_readback_failure_does_not_publish(case, monkeypatch):
    original_read = Path.read_bytes
    before = set(case[2].parent.iterdir())

    def corrupt_read(path):
        if path.parent == case[2].parent and path != case[1]:
            return b"{}"
        return original_read(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", corrupt_read)
        with pytest.raises(OSError, match="readback mismatch"):
            _export(case)
    assert not case[2].exists()
    assert set(case[2].parent.iterdir()) == before
    _export(case)


def test_competing_destination_is_preserved(case, monkeypatch):
    original_read = Path.read_bytes
    before = set(case[2].parent.iterdir())

    def competing_read(path):
        content = original_read(path)
        if path.parent == case[2].parent and path != case[1]:
            case[2].write_text("competing output", encoding="utf-8")
        return content

    monkeypatch.setattr(Path, "read_bytes", competing_read)
    with pytest.raises(FileExistsError):
        _export(case)
    assert case[2].read_text() == "competing output"
    assert set(case[2].parent.iterdir()) == before | {case[2]}


@pytest.mark.parametrize(
    "fault",
    (
        "duplicate_lease duplicate_panel unknown_lease unknown_field duplicate_registry "
        "wrong_owner wrong_operator digest size source_digest missing_manifest "
        "duplicate_manifest nonfinite duplicate_json_key missing_source_manifest "
        "invalid_collection"
    ).split(),
)
def test_invalid_inputs_fail_before_writing(case, fault):
    snapshot, registry, output = case
    fields = ("absent",) if fault == "unknown_field" else ("alpha",)
    if fault in ("duplicate_lease", "duplicate_panel"):
        name = "leases.json" if fault == "duplicate_lease" else "panel_values.json"
        _edit(
            case, name, lambda rows: rows.append(dict(rows[0], lease_num="OCS-G 00011"))
        )
    elif fault == "unknown_lease":
        _edit(case, "leases.json", lambda rows: rows[0].update(lease_num="G00999"))
    elif fault == "duplicate_registry":
        registry.write_text(registry.read_text().replace("G00012", "g00011"))
    elif fault in ("wrong_owner", "wrong_operator"):
        key = "current_owners" if fault == "wrong_owner" else "current_operators"
        _edit(
            case,
            "panel_values.json",
            lambda rows: rows[0][key][0].update(LEASE_NUMBER="G00021"),
        )
    elif fault in ("digest", "size", "missing_manifest", "duplicate_manifest"):
        path = snapshot / "extract_manifest.json"
        manifest = json.loads(path.read_text())
        if fault == "digest":
            manifest["artifacts"][0]["sha256"] = "0" * 64
        elif fault == "size":
            manifest["artifacts"][0]["size_bytes"] += 1
        elif fault == "missing_manifest":
            manifest["artifacts"].pop()
        else:
            manifest["artifacts"].append(manifest["artifacts"][0])
        _write(path, manifest)
    elif fault == "invalid_collection":
        _edit(case, "panel_values.json", lambda rows: rows[0].update(current_owners={}))
    elif fault == "source_digest":
        (snapshot / "source_manifest.json").write_text("{}")
    elif fault == "missing_source_manifest":
        # A separate empty input directory exercises absent files without deleting data.
        empty = snapshot / "empty"
        empty.mkdir()
        case = (empty, registry, output)
    elif fault in ("nonfinite", "duplicate_json_key"):
        text = (snapshot / "leases.json").read_text()
        replacement = (
            '"status": NaN' if fault == "nonfinite" else '"status": "A", "status": "B"'
        )
        (snapshot / "leases.json").write_text(
            text.replace('"status": "PROD"', replacement)
        )
        _seal(snapshot)
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        _export(case, fields)
    assert not output.exists()


def test_existing_destination_is_preserved(case):
    case[2].write_text("existing content")
    with pytest.raises(FileExistsError):
        _export(case)
    assert case[2].read_text() == "existing content"


@pytest.mark.parametrize("target", ["snapshot", "registry", "source_directory"])
def test_source_destinations_are_rejected(case, target):
    output = {
        "snapshot": case[0] / "new.json",
        "registry": case[1],
        "source_directory": Path(__file__).resolve().parents[3]
        / "src"
        / "_leases.json",
    }[target]
    before = output.read_bytes() if output.exists() else None
    with pytest.raises(ValueError, match="[Ss]ource"):
        _export((case[0], case[1], output))
    assert (output.read_bytes() if output.exists() else None) == before


def test_cli_explicit_inputs_and_missing_lease_field(case):
    command = [
        sys.executable,
        "-m",
        "scripts.field_atlas.build_leases_sidecar",
        "--snapshot-dir",
        str(case[0]),
        "--registry",
        str(case[1]),
        "--field",
        "beta",
        "--output",
        str(case[2]),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    data = json.loads(case[2].read_text())
    assert list(data["fields"]) == ["beta"]
    assert data["fields"]["beta"]["leases"][0]["lease_num"] == "G00021"
    assert data["fields"]["beta"]["leases"][0]["missing"]
