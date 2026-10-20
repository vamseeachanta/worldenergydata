"""Source contract examples; all engineering inputs below are synthetic.

Independent acceptance calculation: required facts are length=100 m, beam=20 m,
depth=10 m, draft=5 m, displacement=1000 t, CoG=(0, 0, 4) m, and inertia
(xx, yy, zz, xy, xz, yz)=(2000, 3000, 4000, 0, 0, 0) t*m^2.
These are stipulated fixture inputs, not published properties or solver results.
Every fact is bound to unit-a and condition-a; evidence and rights are present,
so the synthetic record is COMPLETE but cannot be publicly promoted.
Deleting any required fact yields NOT_EVALUATED. Changing any binding yields
REJECTED. No engineering equation or acceptance tolerance is applied.
"""

from __future__ import annotations

import copy
import hashlib

import pytest

from worldenergydata.vessel_fleet.modu_source import (
    SourceRecord,
    assess,
    canonical_bytes,
    commitment,
    load_record,
    verify_source_bytes,
)


def complete_record():
    """Construct fully explicit synthetic evidence; no private input is used."""
    citation = {"source_id": "example", "locator": "stipulated test inputs"}
    binding = {**citation, "physical_id": "unit-a", "condition_id": "condition-a"}
    values = {
        "length": (100, "m"),
        "beam": (20, "m"),
        "depth": (10, "m"),
        "draft": (5, "m"),
        "displacement": (1000, "t"),
        "cog_x": (0, "m"),
        "cog_y": (0, "m"),
        "cog_z": (4, "m"),
        "i_xx": (2000, "t*m^2"),
        "i_yy": (3000, "t*m^2"),
        "i_zz": (4000, "t*m^2"),
        "i_xy": (0, "t*m^2"),
        "i_xz": (0, "t*m^2"),
        "i_yz": (0, "t*m^2"),
    }
    return {
        "schema_version": "1",
        "record_id": "synthetic-example",
        "rig_source_id": "fixture:rig-a",
        "rig_class": "drillship",
        "rig_evidence": citation,
        "physical_id": "unit-a",
        "imo": None,
        "fallback": {
            "identifier": "fixture:physical-a",
            "review_ref": "fixture:review",
            "evidence": citation,
        },
        "aliases": [
            {
                "alias": "fixture:alias-a",
                "physical_id": "unit-a",
                "imo": None,
                "evidence": citation,
            }
        ],
        "identity_evidence": citation,
        "geometry_evidence": citation,
        "condition": {
            "condition_id": "condition-a",
            "physical_id": "unit-a",
            "description": "Stipulated loading",
            "evidence": citation,
        },
        "frame": {
            "origin": "baseline at midship",
            "axes": "right handed: x forward, y port, z up",
            "inertia_reference": "centre_of_gravity",
            "inertia_convention": "tensor_components",
            "evidence": binding,
        },
        "quantities": {
            key: {"value": value, "unit": unit, "evidence": binding.copy()}
            for key, (value, unit) in values.items()
        },
        "sources": [
            {
                "source_id": "example",
                "url": "https://example.org/reference",
                "captured_at": "2026-10-19T00:00:00Z",
                "http_status": 200,
                "sha256": hashlib.sha256(b"abc").hexdigest(),
                "size_bytes": 3,
                "origin": "synthetic",
                "redistribution": "facts_only",
                "rights_evidence": "Synthetic test definition; no original reproduced",
            }
        ],
        "missing_evidence": {},
    }


def test_complete_synthetic_record_is_not_publicly_promotable():
    result = assess(SourceRecord.model_validate(complete_record()))
    assert result.status == "COMPLETE"
    assert not result.promotable
    assert result.reasons == ("NON_PUBLIC_SOURCE:example",)


def test_canonical_commitment_and_source_verification():
    """NIST SHA-256 worked example, One Block Message Sample, pp. 1-4.

    https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/SHA256.pdf
    The published digest of 'abc' supplies the independent expected value.
    """
    record = SourceRecord.model_validate(complete_record())
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert record.sources[0].sha256 == expected
    verify_source_bytes(record, {"example": b"abc"})
    reversed_keys = dict(reversed(list(complete_record().items())))
    other = SourceRecord.model_validate(reversed_keys)
    assert canonical_bytes(record) == canonical_bytes(other)
    assert commitment(record) == hashlib.sha256(canonical_bytes(record)).hexdigest()
    changed = copy.deepcopy(complete_record())
    changed["quantities"]["draft"]["value"] = 6
    assert commitment(SourceRecord.model_validate(changed)) != commitment(record)
    with pytest.raises(ValueError, match="SOURCE_BYTES_MISMATCH"):
        verify_source_bytes(record, {"example": b"tampered"})
    with pytest.raises(ValueError, match="SOURCE_BYTES_MISSING"):
        verify_source_bytes(record, {})


@pytest.mark.parametrize("field", list(complete_record()["quantities"]))
def test_every_missing_engineering_fact_blocks(field):
    data = complete_record()
    del data["quantities"][field]
    data["missing_evidence"][field] = "Not supplied in source"
    result = assess(SourceRecord.model_validate(data))
    assert result.status == "NOT_EVALUATED"
    assert not result.promotable
    assert f"MISSING:{field}" in result.reasons


@pytest.mark.parametrize(
    "case,reason",
    [
        ("name_only", "IDENTITY_MISSING"),
        ("imo_conflict", "IMO_CONFLICT"),
        ("alias_collision", "ALIAS_COLLISION"),
        ("different_unit", "PHYSICAL_UNIT_MISMATCH"),
        ("loading", "LOADING_MISMATCH"),
        ("citation", "UNKNOWN_SOURCE"),
        ("unit", "UNIT_MISMATCH"),
        ("frame", "FRAME_MISSING"),
        ("geometry", "GEOMETRY_MISSING"),
    ],
)
def test_identity_loading_and_evidence_fail_closed(case, reason):
    data = complete_record()
    if case == "name_only":
        data["fallback"] = None
    elif case == "imo_conflict":
        # Deliberately conflicting identifiers; these are not real source claims.
        data["imo"] = "1234567"
        data["aliases"][0]["imo"] = "7654321"
    elif case == "alias_collision":
        data["aliases"].append({**data["aliases"][0], "physical_id": "unit-b"})
    elif case == "different_unit":
        data["quantities"]["draft"]["evidence"]["physical_id"] = "unit-b"
    elif case == "loading":
        data["condition"]["condition_id"] = "condition-b"
    elif case == "citation":
        data["identity_evidence"]["source_id"] = "absent"
    elif case == "unit":
        data["quantities"]["draft"]["unit"] = "ft"
    elif case == "frame":
        data["frame"] = None
    elif case == "geometry":
        data["geometry_evidence"] = None
    result = assess(SourceRecord.model_validate(data))
    assert not result.promotable
    assert any(item.startswith(reason) for item in result.reasons)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_invalid_numeric_input_rejected(value):
    data = complete_record()
    data["quantities"]["draft"]["value"] = value
    with pytest.raises(ValueError):
        SourceRecord.model_validate(data)


def test_duplicate_json_keys_rejected(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"record_id":"a","record_id":"b"}')
    with pytest.raises(ValueError, match="DUPLICATE_KEY"):
        load_record(path)


def test_committed_public_candidate():
    from worldenergydata.vessel_fleet.modu_source import PUBLIC_RECORD

    record = load_record(PUBLIC_RECORD)
    assert len(record.sources) == 1
    assert record.sources[0].origin == "public"
    result = assess(record)
    assert result.status == "NOT_EVALUATED"
    assert not result.promotable
    assert "IDENTITY_MISSING" in result.reasons
    assert "LOADING_MISSING" in result.reasons
    assert set(record.missing_evidence) >= set(complete_record()["quantities"])


def test_unknown_fields_and_false_readiness_rejected():
    data = complete_record()
    data["promotable"] = True
    with pytest.raises(ValueError):
        SourceRecord.model_validate(data)


def test_hypothetical_public_complete_evidence_requires_matching_bytes():
    """Hypothetical public metadata tests policy; it is not a public MODU record."""
    data = complete_record()
    data["sources"][0]["origin"] = "public"
    record = SourceRecord.model_validate(data)
    assert not assess(record).promotable
    result = assess(record, source_bytes={"example": b"abc"})
    assert result.status == "COMPLETE"
    assert result.promotable
    assert result.reasons == ()


@pytest.mark.parametrize("origin", ["private", "licensed"])
def test_restricted_sources_never_qualify(origin):
    data = complete_record()
    data["sources"][0]["origin"] = origin
    assert not assess(
        SourceRecord.model_validate(data), source_bytes={"example": b"abc"}
    ).promotable


@pytest.mark.parametrize("rights", ["unknown", "prohibited"])
def test_unknown_or_prohibited_redistribution_blocks(rights):
    data = complete_record()
    data["sources"][0].update(origin="public", redistribution=rights)
    result = assess(SourceRecord.model_validate(data), source_bytes={"example": b"abc"})
    assert result.status == "NOT_EVALUATED"
    assert not result.promotable
    assert "RIGHTS_NOT_CLEARED:example" in result.reasons


@pytest.mark.parametrize("key", ["condition", "identity_evidence", "fallback", "frame"])
def test_missing_source_citations_cannot_qualify(key):
    data = complete_record()
    citation = data[key] if key == "identity_evidence" else data[key]["evidence"]
    citation["source_id"] = "absent"
    result = assess(SourceRecord.model_validate(data))
    assert result.status == "REJECTED"
    assert "UNKNOWN_SOURCE:absent" in result.reasons


def test_duplicate_source_ids_and_invalid_imo_rejected():
    data = complete_record()
    data["sources"].append(data["sources"][0].copy())
    assert "DUPLICATE_SOURCE_ID" in assess(SourceRecord.model_validate(data)).reasons
    data = complete_record()
    data.update(imo="text", fallback=None)
    assert "IMO_FORMAT" in assess(SourceRecord.model_validate(data)).reasons


@pytest.mark.parametrize("field", ["length", "beam", "draft", "displacement", "i_xx"])
def test_nonpositive_physical_scalar_rejected(field):
    data = complete_record()
    data["quantities"][field]["value"] = 0
    assert f"NONPOSITIVE:{field}" in assess(SourceRecord.model_validate(data)).reasons


def test_missing_and_contradictory_dispositions():
    data = complete_record()
    del data["quantities"]["length"]
    assert (
        "MISSING_DISPOSITION:length"
        in assess(SourceRecord.model_validate(data)).reasons
    )
    data = complete_record()
    data["missing_evidence"]["length"] = "Unknown despite quantity"
    assert (
        "CONTRADICTORY_DISPOSITION:length"
        in assess(SourceRecord.model_validate(data)).reasons
    )


def test_public_example_inputs_method_and_answer(monkeypatch, capsys):
    import json
    import runpy
    from pathlib import Path

    example = (
        Path(__file__).resolve().parents[3]
        / "examples/vessel_fleet/modu_source_example.py"
    )
    monkeypatch.setattr("sys.argv", [str(example)])
    runpy.run_path(str(example), run_name="__main__")
    answer = json.loads(capsys.readouterr().out)
    assert answer["status"] == "NOT_EVALUATED"
    assert answer["promotable"] is False
    assert "MISSING:displacement" in answer["reasons"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "not-a-digest"),
        ("size_bytes", 0),
        ("captured_at", "2026-10-19T00:00:00"),
        ("captured_at", "2999-01-01T00:00:00Z"),
        ("url", "http://example.org/reference"),
        ("rights_evidence", " "),
    ],
)
def test_invalid_source_provenance_rejected(field, value):
    data = complete_record()
    data["sources"][0][field] = value
    with pytest.raises(ValueError):
        SourceRecord.model_validate(data)


def test_unavailable_response_and_empty_aliases_block():
    data = complete_record()
    data["sources"][0]["http_status"] = 404  # RFC 9110 (2022), section 15.5.5.
    data["aliases"] = []
    result = assess(SourceRecord.model_validate(data))
    assert result.status == "NOT_EVALUATED"
    assert "SOURCE_UNAVAILABLE:example" in result.reasons
    assert "ALIASES_MISSING" in result.reasons
