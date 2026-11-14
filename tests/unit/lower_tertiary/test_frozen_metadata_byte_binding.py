"""Synthetic byte-binding checks; no historical workbook is opened here.

Policy citation: docs/data-sources/bsee/analysis/rig_days/
frozen_dc_provenance.md, Metadata contract. These tests establish loader
behaviour, not historical reproduction or a new counting rule.
"""

import hashlib
import importlib.util
import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
POLICY = (
    REPO
    / "docs/modules/bsee/analysis/production/FDAS_V30"
    / "drilling_and_completion_days.provenance.json"
)


@pytest.fixture
def synthetic_frozen(tmp_path, monkeypatch):
    """Copy policy only and bind it independently to literal synthetic cells.

    The 100/101 identifiers, date and D/C = 3/2 example follow the hand example
    in test_frozen_dc_metadata.py: example and
    test_absent_side_is_not_missing_provenance.
    The other row deliberately supplies literal zero counts and a missing date;
    neither is evidence of measured PND. No counts are calculated by the loader.
    """
    path = REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    cells = pd.DataFrame(
        {
            "API_WELL_NUMBER": [100, 101],
            "LEASE_NAME": ["synthetic", "synthetic unknown"],
            "DRILLING_DAYS": [3, 0],
            "COMPLETION_DAYS": [2, 0],
            "WELL_SPUD_DATE": ["2020-01-01", float("nan")],
        }
    )
    workbook = tmp_path / "frozen.xlsx"
    cells.to_excel(workbook, index=False, sheet_name="Sheet1")
    payload = workbook.read_bytes()
    metadata = json.loads(POLICY.read_text(encoding="utf-8"))
    metadata["workbook_sha256"] = hashlib.sha256(payload).hexdigest()
    sidecar = workbook.with_suffix(".provenance.json")
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")
    publication = tmp_path / "published.csv"
    publication.write_bytes(b"previous synthetic publication\n")
    monkeypatch.setattr(builder, "FROZEN_XLSX", workbook)
    monkeypatch.setattr(builder, "OUT_CSV", publication)
    # Rejection must precede candidate loading as well as publication writes.
    monkeypatch.setattr(builder, "CANDIDATE_CSV", tmp_path / "unused-candidate.csv")
    return SimpleNamespace(
        builder=builder,
        cells=cells,
        workbook=workbook,
        payload=payload,
        metadata=metadata,
        sidecar=sidecar,
        publication=publication,
    )


def assert_rejected_before_parse(example, monkeypatch, message):
    """Publication entry point must fail without parsing or changing any bytes."""
    paths = (example.workbook, example.sidecar, example.publication)
    before = {path: path.read_bytes() for path in paths}
    parser = Mock(side_effect=AssertionError("Excel parser must not be called"))
    monkeypatch.setattr(pd, "read_excel", parser)
    with pytest.raises(ValueError, match=message):
        example.builder.main(["--frozen-metadata", str(example.sidecar)])
    parser.assert_not_called()
    assert {path: path.read_bytes() for path in paths} == before


@pytest.mark.parametrize(
    "key", ["drilling", "completion", "missing_values", "pnd", "coverage"]
)
def test_nested_rule_duplicates_rejected_before_parse(
    synthetic_frozen, monkeypatch, key
):
    example = synthetic_frozen
    rule = json.dumps(example.metadata["rule"])
    # Repeat the original value: a last-key-wins decoder would accept this
    # policy. Only the nested duplicate makes the metadata invalid.
    repeated = (
        rule[:-1]
        + f", {json.dumps(key)}: {json.dumps(example.metadata['rule'][key])}}}"
    )
    text = json.dumps(example.metadata).replace(rule, repeated)
    assert json.loads(text) == example.metadata
    example.sidecar.write_text(text, encoding="utf-8")
    assert_rejected_before_parse(example, monkeypatch, "cannot read frozen metadata")


@pytest.mark.parametrize("failure", ["missing", "empty", "nontext", "not_object"])
def test_invalid_nested_rule_rejected_before_parse(
    synthetic_frozen, monkeypatch, failure
):
    example = synthetic_frozen
    if failure == "missing":
        del example.metadata["rule"]["coverage"]
    elif failure == "empty":
        example.metadata["rule"]["coverage"] = ""
    elif failure == "nontext":
        example.metadata["rule"]["coverage"] = None
    else:
        example.metadata["rule"] = list(example.metadata["rule"])
    example.sidecar.write_text(json.dumps(example.metadata), encoding="utf-8")
    assert_rejected_before_parse(example, monkeypatch, "missing frozen metadata rule")


def test_digest_mismatch_rejected_before_parse(synthetic_frozen, monkeypatch):
    example = synthetic_frozen
    other_digest = hashlib.sha256(b"different synthetic workbook bytes").hexdigest()
    assert other_digest != hashlib.sha256(example.payload).hexdigest()
    example.metadata["workbook_sha256"] = other_digest
    example.sidecar.write_text(json.dumps(example.metadata), encoding="utf-8")
    assert_rejected_before_parse(
        example, monkeypatch, "frozen metadata digest mismatch"
    )


def test_excel_parser_uses_digest_bound_bytes(synthetic_frozen, monkeypatch):
    example = synthetic_frozen
    paths = (example.workbook, example.sidecar, example.publication)
    before = {path: path.read_bytes() for path in paths}
    alternate = BytesIO()
    example.cells.assign(DRILLING_DAYS="changed synthetic cell").to_excel(
        alternate, index=False, sheet_name="Sheet1"
    )
    later_payload = alternate.getvalue()
    assert (
        hashlib.sha256(later_payload).hexdigest() != example.metadata["workbook_sha256"]
    )
    real_read_bytes = Path.read_bytes
    # Metadata contract: a single workbook read supplies both hash and parser.
    # Further reads would return a different, independently valid workbook.
    workbook_reads = Mock(side_effect=[example.payload, later_payload])

    def read_bytes(path):
        if path == example.workbook:
            return workbook_reads()
        return real_read_bytes(path)

    real_parser = pd.read_excel

    def parse(stream, *, sheet_name):
        assert isinstance(stream, BytesIO)
        assert stream.getvalue() == example.payload
        assert (
            hashlib.sha256(stream.getvalue()).hexdigest()
            == example.metadata["workbook_sha256"]
        )
        return real_parser(stream, sheet_name=sheet_name)

    parser = Mock(side_effect=parse)
    with monkeypatch.context() as spies:
        spies.setattr(Path, "read_bytes", read_bytes)
        spies.setattr(pd, "read_excel", parser)
        labelled = example.builder.load_frozen(example.workbook, example.sidecar)
        workbook_reads.assert_called_once_with()
        parser.assert_called_once()
        assert parser.call_args.kwargs == {"sheet_name": "Sheet1"}

    pd.testing.assert_frame_equal(labelled[example.cells.columns], example.cells)
    assert list(labelled.columns) == list(example.cells.columns) + [
        "BASIS",
        "PND_DAYS",
        "DAYS_STATUS",
    ]
    assert labelled["BASIS"].eq(example.metadata["basis"]).all()
    assert labelled["PND_DAYS"].isna().all()
    assert str(labelled["PND_DAYS"].dtype) == "Int64"
    assert labelled["DAYS_STATUS"].eq("historical_coverage_unknown").all()
    assert {path: path.read_bytes() for path in paths} == before
