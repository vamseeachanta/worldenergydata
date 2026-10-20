"""Contract tests; all measurements are invented inputs, not field evidence.

Independent hand calculation: one location, two wells and one production record
give four observations. A monthly oil volume of 12 bbl is copied unchanged;
there is no conversion, decline model, depletion estimate or acceptance limit.
Missing pressure and ownership evidence must remain NOT_EVALUATED.
"""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from worldenergydata.underwriting.diligence import build_pack, render_html, write_pack

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "examples/underwriting/input.json"


@pytest.fixture
def payload():
    return json.loads(EXAMPLE.read_text())


def test_observations_and_explicit_gaps(payload):
    pack = build_pack(payload)
    assert pack["sections"]["wells"]["observation_count"] == 2
    assert pack["sections"]["production"]["observations"][0]["value"] == 12
    assert pack["sections"]["production"]["status"] == "OBSERVATIONS_ONLY"
    for section in ("pressure", "lease_title_mineral", "hse"):
        assert pack["sections"][section]["status"] == "NOT_EVALUATED"
        assert pack["sections"][section]["gaps"]
    assert pack["synthetic"] is True
    assert pack["observation_count"] == 4  # location + two wells + production


def test_empty_pack_is_useful(payload):
    payload["observations"] = []
    pack = build_pack(payload)
    assert all(s["status"] == "NOT_EVALUATED" for s in pack["sections"].values())
    assert "not evidence of absence" in render_html(pack)


def test_html_has_all_sections_provenance_and_revision_history(payload):
    report = render_html(build_pack(payload))
    for title in (
        "Asset/location",
        "Wells",
        "Production",
        "Pressure/depletion",
        "Permits/completions",
        "Infrastructure",
        "HSE/environmental overlays",
        "Lease/title/mineral availability",
        "Explicit data gaps",
        "Data inventory",
        "U.S. onshore matrix",
        "Source modules/issues",
    ):
        assert title in report
    assert (
        report.index("Summary")
        < report.index("Revision history")
        < report.index("Wells")
    )
    assert "SYNTHETIC" in report
    assert "well-row-a" in report
    assert "No ownership or title conclusion" in report
    assert "<script" not in report
    assert "<script src" not in report


def test_escape_untrusted_text(payload):
    payload["asset"] = '<script>alert("sample")</script>'
    payload["observations"][0]["value"] = "<img src=x onerror=alert(1)>"
    report = render_html(build_pack(payload))
    assert "<script>" not in report
    assert "<img" not in report
    assert "&lt;script&gt;" in report


@pytest.mark.parametrize("section", ["lease_title_mineral"])
def test_regulator_records_cannot_supply_ownership(payload, section):
    payload["sources"][0]["kind"] = "regulator"
    payload["sources"][0]["publication"] = "public-approved"
    payload["observations"][0]["section"] = section
    with pytest.raises(ValueError, match="ownership"):
        build_pack(payload)


@pytest.mark.parametrize(
    "status", ["configured-only", "partial/error", "missing", "private/legacy"]
)
def test_unavailable_sources_cannot_supply_facts(payload, status):
    payload["sources"][0]["status"] = status
    with pytest.raises(ValueError, match="materialized"):
        build_pack(payload)


def test_public_data_requires_explicit_publication_clearance(payload):
    source = payload["sources"][0]
    source.update(kind="regulator", status="downloaded", publication="unreviewed")
    with pytest.raises(ValueError, match="publication"):
        build_pack(payload)
    source["publication"] = "public-approved"
    assert build_pack(payload)["synthetic"] is False


@pytest.mark.parametrize(
    "field", ["citation", "retrieved_at", "sha256", "license", "coverage"]
)
def test_source_provenance_required(payload, field):
    del payload["sources"][0][field]
    with pytest.raises(ValueError):
        build_pack(payload)


@pytest.mark.parametrize(
    "field", ["source_id", "locator", "observed_on", "unit", "subject"]
)
def test_observation_provenance_required(payload, field):
    del payload["observations"][0][field]
    with pytest.raises(ValueError):
        build_pack(payload)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), None, True, [], {}])
def test_invalid_measurements_rejected(payload, value):
    payload["observations"][0]["value"] = value
    with pytest.raises(ValueError):
        build_pack(payload)


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:sample",
        "//example.org",
        "https://user:pass" + chr(64) + "example.org",
    ],
)
def test_unsafe_links_rejected(payload, url):
    payload["sources"][0]["url"] = url
    with pytest.raises(ValueError, match="URL"):
        build_pack(payload)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_source",
        "duplicate_source",
        "duplicate_observation",
        "bad_date",
        "future_observation",
        "unknown_section",
        "unknown_field",
    ],
)
def test_ambiguous_inputs_rejected(payload, mutation):
    if mutation == "unknown_source":
        payload["observations"][0]["source_id"] = "absent"
    elif mutation == "duplicate_source":
        payload["sources"].append(copy.deepcopy(payload["sources"][0]))
    elif mutation == "duplicate_observation":
        payload["observations"].append(copy.deepcopy(payload["observations"][0]))
    elif mutation == "bad_date":
        payload["as_of"] = "not-a-date"
    elif mutation == "future_observation":
        payload["observations"][0]["observed_on"] = "2099-01-01"
    elif mutation == "unknown_section":
        payload["observations"][0]["section"] = "typo"
    else:
        payload["observations"][0]["unexpected"] = "ignored?"
    with pytest.raises(ValueError):
        build_pack(payload)


def test_source_gaps_and_caveats_survive(payload):
    payload["sources"][0]["caveats"] = ["Synthetic records only"]
    payload["gaps"]["wells"] = ["No complete well census"]
    pack = build_pack(payload)
    assert "No complete well census" in pack["sections"]["wells"]["gaps"]
    assert "Synthetic records only" in render_html(pack)


def test_reproducible_separate_outputs_and_input_digest(tmp_path, payload):
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_pack(EXAMPLE, first)
    write_pack(EXAMPLE, second)
    assert sorted(p.name for p in first.iterdir()) == ["index.html", "summary.json"]
    for name in ("index.html", "summary.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    summary = json.loads((first / "summary.json").read_text())
    assert summary["input_sha256"] == hashlib.sha256(EXAMPLE.read_bytes()).hexdigest()
    assert "input_sha256" not in (first / "index.html").read_text()
    with pytest.raises(FileExistsError):
        write_pack(EXAMPLE, first)


@pytest.mark.parametrize("name", ["index.html", "summary.json"])
def test_output_bytes_use_lf_on_windows(tmp_path, monkeypatch, name):
    original_open = Path.open

    def windows_open(path, mode="r", *args, **kwargs):
        # Exercise real text I/O with the Windows default newline translation.
        if "w" in mode and "b" not in mode and kwargs.get("newline") is None:
            kwargs["newline"] = "\r\n"
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", windows_open)
    output = tmp_path / "pack"
    write_pack(EXAMPLE, output)
    raw = (output / name).read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r" not in raw


@pytest.mark.parametrize(
    "retrieved_at,rejected",
    [
        ("2026-10-20T23:30:00-01:00", True),
        ("2026-10-21T00:30:00+01:00", False),
        ("2026-10-20T23:59:59+00:00", False),
        ("2026-10-21T00:00:00+00:00", True),
        ("2026-10-20T12:00:00", True),
    ],
)
def test_retrieval_cutoff_uses_utc(payload, retrieved_at, rejected):
    payload["as_of"] = "2026-10-20"
    payload["sources"][0]["retrieved_at"] = retrieved_at
    if rejected:
        with pytest.raises(ValueError, match="retrieval"):
            build_pack(payload)
    else:
        assert build_pack(payload)["sources"][0]["retrieved_at"] == retrieved_at


def test_invalid_input_does_not_create_output(tmp_path):
    source = tmp_path / "invalid.json"
    source.write_text("{}")
    output = tmp_path / "output"
    with pytest.raises(ValueError):
        write_pack(source, output)
    assert not output.exists()


@pytest.mark.parametrize("member", ["publication", "value", "observations"])
def test_duplicate_json_members_rejected_before_output(tmp_path, payload, member):
    payload["sources"][0].update(kind="regulator", publication="public-approved")
    raw = json.dumps(payload)
    if member == "publication":
        raw = raw.replace(
            '"publication": "public-approved"',
            '"publication": "unreviewed", "publication": "public-approved"',
            1,
        )
    elif member == "value":
        raw = raw.replace('"value": 12', '"value": 99, "value": 12', 1)
    else:
        raw = raw.replace(
            '"observations": [', '"observations": [], "observations": [', 1
        )
    source = tmp_path / "ambiguous.json"
    source.write_text(raw, encoding="utf-8")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Duplicate JSON member"):
        write_pack(source, output)
    assert not output.exists()


@pytest.mark.parametrize("target", ["sources", "references"])
@pytest.mark.parametrize(
    "url",
    [
        "docs/%2e%2e/%2e%2e/outside.txt",
        "docs/%2E%2E/outside.txt",
        "docs/.%2e/outside.txt",
        "docs/%2e./outside.txt",
        "docs/%2e/outside.txt",
        "docs/sub%2f..%2foutside.txt",
        "docs/sub%2F..%2Foutside.txt",
        "docs/sub%5c..%5coutside.txt",
        "docs/sub%5C..%5Coutside.txt",
    ],
)
def test_encoded_relative_link_traversal_rejected(payload, target, url):
    payload[target][0]["url"] = url
    if target == "references":
        payload[target][0]["status"] = "AVAILABLE"
    with pytest.raises(ValueError, match="URL"):
        build_pack(payload)


@pytest.mark.parametrize("target", ["sources", "references"])
def test_encoded_relative_filename_preserved(payload, target):
    payload[target][0]["url"] = "docs/source%20notes.txt"
    if target == "references":
        payload[target][0]["status"] = "AVAILABLE"
    report = render_html(build_pack(payload), "https://example.org/repository/")
    assert 'href="https://example.org/repository/docs/source%20notes.txt"' in report


@pytest.mark.parametrize(
    "root", ["javascript:alert(1)", "file:sample", "//example.org"]
)
def test_repository_root_url_rejected(payload, root):
    with pytest.raises(ValueError, match="URL"):
        render_html(build_pack(payload), root)


def test_public_repository_root_links(payload):
    report = render_html(build_pack(payload), "https://example.org/repository/")
    assert 'href="https://example.org/repository/docs/' in report


def test_title_source_is_separate_evidence(payload):
    payload["sources"][0].update(kind="title", publication="public-approved")
    payload["observations"][0]["section"] = "lease_title_mineral"
    pack = build_pack(payload)
    assert pack["sections"]["lease_title_mineral"]["status"] == "OBSERVATIONS_ONLY"
    assert "No ownership or title conclusion" in render_html(pack)


def test_required_coverage_references(payload):
    payload["references"] = []
    with pytest.raises(ValueError, match="references"):
        build_pack(payload)


def test_synthetic_source_digest_identifies_invented_inputs(payload):
    raw = json.dumps(
        payload["observations"], sort_keys=True, separators=(",", ":")
    ).encode()
    assert payload["sources"][0]["sha256"] == hashlib.sha256(raw).hexdigest()


def test_reissue_retains_prior_revision_rows(payload):
    previous = {
        "revision": "draft",
        "date": "2026-10-19",
        "change": "Record evidence gaps.",
    }
    payload["previous_revisions"] = [previous]
    pack = build_pack(payload)
    assert pack["revision_history"] == [
        previous,
        {
            "revision": "initial",
            "date": payload["as_of"],
            "change": payload["revision_note"],
        },
    ]
    report = render_html(pack)
    assert report.index("Record evidence gaps.") < report.index(
        payload["revision_note"]
    )


@pytest.mark.parametrize(
    "revision,day", [("initial", "2026-10-19"), ("draft", "2099-01-01")]
)
def test_invalid_prior_revisions_rejected(payload, revision, day):
    payload["previous_revisions"] = [
        {"revision": revision, "date": day, "change": "Earlier issue."}
    ]
    with pytest.raises(ValueError):
        build_pack(payload)


def test_cli(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.underwriting",
            str(EXAMPLE),
            str(tmp_path / "pack"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "pack/index.html").exists()


def test_committed_worked_answer_matches_generator(tmp_path):
    write_pack(EXAMPLE, tmp_path / "pack")
    for name in ("index.html", "summary.json"):
        assert (EXAMPLE.parent / name).read_bytes() == (
            tmp_path / "pack" / name
        ).read_bytes()
