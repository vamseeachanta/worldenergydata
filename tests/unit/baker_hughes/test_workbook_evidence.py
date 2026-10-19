"""Byte identity is evidence, not independent workbook qualification."""

import json

import pytest

from worldenergydata.baker_hughes import report


def test_fingerprint_matches_published_example(tmp_path):
    """Python 3.10 hashlib docs, Hash algorithms: published input and digest.

    https://docs.python.org/3.10/library/hashlib.html#hash-algorithms
    This byte-string example tests hashing only; it is not a source workbook.
    """
    path = tmp_path / "input.bin"
    path.write_bytes(b"Nobody inspects the spammish repetition")

    evidence = report.generate_workbook_evidence(path)

    assert evidence["fingerprint"] == {
        "algorithm": "sha256",
        "digest": "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9406",
    }


@pytest.mark.parametrize("payload", [b"", b"not an Excel workbook"])
def test_fingerprint_does_not_qualify_workbook(tmp_path, payload):
    """Issue 1336 requires independent evidence; arbitrary bytes supply none."""
    path = tmp_path / "unqualified.xlsx"
    path.write_bytes(payload)

    evidence = report.generate_workbook_evidence(path)

    assert evidence["status"] == "NOT_EVALUATED"
    assert set(evidence["checks"]) == {
        "source_revision",
        "depth_units",
        "independent_counts",
        "signed_qa",
    }
    for check in evidence["checks"].values():
        assert check["status"] == "NOT_EVALUATED"
        assert check["reason"]


def test_evidence_is_serializable_without_local_locator(tmp_path):
    """The evidence record retains byte identity without disclosing its path."""
    path = tmp_path / "local-only-location.xlsx"
    path.write_bytes(b"unqualified")

    evidence = report.generate_workbook_evidence(str(path))
    serialized = json.dumps(evidence)

    assert json.loads(serialized) == evidence
    assert str(path) not in serialized
    assert path.name not in serialized


def test_missing_file_produces_no_evidence(tmp_path):
    """An unavailable input cannot acquire a fingerprint or a QA record."""
    with pytest.raises(FileNotFoundError):
        report.generate_workbook_evidence(tmp_path / "missing.xlsx")


def test_directory_produces_no_evidence(tmp_path):
    """A directory is not a fingerprintable workbook input."""
    with pytest.raises(IsADirectoryError):
        report.generate_workbook_evidence(tmp_path)
