"""Offline Arkansas inventory checks; counts are hand tallies of literal rows."""

import copy
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from worldenergydata.modules.state_regulators.arkansas_aogc.source_inventory import (
    summarize_inventory,
    validate_inventory,
)

DOCUMENT = (
    # Repository layout: tests/unit/modules/state_regulators is below the root.
    Path(__file__).parents[4]
    / "docs/data-sources/onshore/arkansas/source-inventory.md"
)


@pytest.fixture
def metadata():
    """Synthetic example: one regulator well source with unknown permissions."""
    return {
        "source_url": "https://example.invalid/regulator/wells",
        "source_category": "regulator",
        "dataset_type": "wells",
        "access_method": "unknown",
        "format": "unknown",
        "rights_status": "unknown",
        "verification_status": "unverified",
        "verification_time": "2026-10-15T00:00:00Z",
    }


def test_regulator_and_county_sources_remain_distinct(metadata):
    county = {
        **metadata,
        "source_url": "https://example.invalid/county/leases",
        "source_category": "county_title",
        "dataset_type": "recorded_leases",
    }
    rows = [metadata, county]
    before = copy.deepcopy(rows)

    assert validate_inventory(rows) == before
    assert summarize_inventory(rows) == {
        # Independent hand tally: one regulator + one county = two sources;
        # both have unknown access/rights and neither has been verified.
        "total_sources": 2,
        "regulator_sources": 1,
        "county_title_sources": 1,
        "unverified_sources": 2,
        "unknown_access_sources": 2,
        "unknown_rights_sources": 2,
    }
    assert rows == before


@pytest.mark.parametrize(
    "field",
    [
        "source_url",
        "source_category",
        "dataset_type",
        "access_method",
        "format",
        "rights_status",
        "verification_status",
        "verification_time",
    ],
)
def test_missing_metadata_rejected(metadata, field):
    del metadata[field]
    with pytest.raises(ValueError, match="missing metadata"):
        validate_inventory([metadata])


@pytest.mark.parametrize("value", [None, "", " ", False])
@pytest.mark.parametrize("field", ["access_method", "rights_status"])
def test_unknown_must_be_explicit(metadata, field, value):
    metadata[field] = value
    with pytest.raises(ValueError, match="nonempty string"):
        validate_inventory([metadata])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("access_method", "probably_downloadable"),
        ("rights_status", "public_means_redistributable"),
        ("verification_status", "dataset_verified"),
        ("source_category", "mixed"),
        ("dataset_type", "unclassified"),
    ],
)
def test_unsupported_status_rejected(metadata, field, value):
    metadata[field] = value
    with pytest.raises(ValueError, match=field):
        validate_inventory([metadata])


@pytest.mark.parametrize(
    ("category", "dataset"),
    [("regulator", "mineral_title"), ("county_title", "production")],
)
def test_dataset_category_mismatch_rejected(metadata, category, dataset):
    metadata.update(source_category=category, dataset_type=dataset)
    with pytest.raises(ValueError, match="dataset_type"):
        validate_inventory([metadata])


@pytest.mark.parametrize("value", ["not-a-time", "2026-10-15", "2026-10-15T00:00:00"])
def test_verification_time_requires_timezone(metadata, value):
    metadata["verification_time"] = value
    with pytest.raises(ValueError, match="verification_time"):
        validate_inventory([metadata])


@pytest.mark.parametrize(
    "url",
    ["relative/page", "file:///example", "https://", "https://example.invalid:bad"],
)
def test_source_url_requires_web_locator(metadata, url):
    metadata["source_url"] = url
    with pytest.raises(ValueError, match="source_url"):
        validate_inventory([metadata])


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/?query=synthetic",
        "https://example.invalid/#section",
        "https://synthetic:synthetic@" + "example.invalid/",
    ],
    ids=["query", "fragment", "userinfo"],
)
def test_source_url_rejects_query_fragment_and_userinfo(metadata, url):
    metadata["source_url"] = url
    with pytest.raises(ValueError, match="source_url"):
        validate_inventory([metadata])


def test_landing_page_check_never_upgrades_rights_or_access(metadata):
    metadata["verification_status"] = "landing_page_verified"
    (row,) = validate_inventory([metadata])
    assert row["access_method"] == "unknown"
    assert row["rights_status"] == "unknown"
    metadata["redistribution_allowed"] = True
    with pytest.raises(ValueError, match="unexpected metadata"):
        validate_inventory([metadata])


def test_restricted_rights_are_preserved(metadata):
    metadata["rights_status"] = "restricted"
    (row,) = validate_inventory([metadata])
    assert row["rights_status"] == "restricted"


@pytest.mark.parametrize("rows", [None, "rows", {}, [None]])
def test_non_row_inputs_rejected(rows):
    with pytest.raises(ValueError):
        validate_inventory(rows)


def test_empty_inventory_summary():
    # Independent hand tally: an empty inventory has zero in every category.
    assert summarize_inventory([]) == {
        "total_sources": 0,
        "regulator_sources": 0,
        "county_title_sources": 0,
        "unverified_sources": 0,
        "unknown_access_sources": 0,
        "unknown_rights_sources": 0,
    }


def test_documented_inventory_validates():
    text = DOCUMENT.read_text(encoding="utf-8")
    inventory = json.loads(re.search(r"```json\n(.*?)\n```", text, re.S).group(1))
    # The cited inventory table independently lists five regulator discovery
    # targets plus one county directory, all with unknown access and rights.
    assert summarize_inventory(inventory) == {
        "total_sources": 6,
        "regulator_sources": 5,
        "county_title_sources": 1,
        "unverified_sources": 5,
        "unknown_access_sources": 6,
        "unknown_rights_sources": 6,
    }


def test_documented_example_runs_offline():
    text = DOCUMENT.read_text(encoding="utf-8")
    example = re.search(r"```sh\n(.*?)\n```", text, re.S).group(1)
    expected = json.loads(re.findall(r"```json\n(.*?)\n```", text, re.S)[-1])
    environment = {**os.environ, "PYTHON": sys.executable}
    result = subprocess.run(
        ["bash", "-c", example],
        cwd=DOCUMENT.parents[4],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert json.loads(result.stdout) == expected


def test_cli_valid_metadata_prints_summary(metadata):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.modules.state_regulators.arkansas_aogc.source_inventory",
        ],
        input=json.dumps([metadata]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    # Independent hand tally of the single synthetic regulator fixture.
    assert json.loads(result.stdout) == {
        "total_sources": 1,
        "regulator_sources": 1,
        "county_title_sources": 0,
        "unverified_sources": 1,
        "unknown_access_sources": 1,
        "unknown_rights_sources": 1,
    }


def test_cli_invalid_metadata_exits_with_error(metadata):
    del metadata["source_url"]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.modules.state_regulators.arkansas_aogc.source_inventory",
        ],
        input=json.dumps([metadata]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode != 0
    assert "missing metadata" in result.stderr


def _run_cli(payload, *, env=None):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.modules.state_regulators.arkansas_aogc.source_inventory",
        ],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def _assert_invalid_cli(result):
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.splitlines()[-1].endswith(
        "error: invalid inventory: missing metadata or invalid field values"
    )
    assert "example.invalid" not in result.stderr
    assert "synthetic-conflict" not in result.stderr
    assert "rights_status" not in result.stderr


@pytest.mark.parametrize(
    "field",
    (
        "source_url",
        "source_category",
        "dataset_type",
        "access_method",
        "format",
        "rights_status",
        "verification_status",
        "verification_time",
    ),
)
@pytest.mark.parametrize("conflicting", [False, True], ids=["identical", "conflicting"])
def test_cli_rejects_duplicate_metadata_keys(metadata, field, conflicting):
    first_value = "synthetic-conflict" if conflicting else metadata[field]
    # The final occurrence is valid, so ordinary last-key-wins decoding hides
    # both a conflicting earlier value and an identical duplicate.
    first = json.dumps({field: first_value})
    payload = "[" + first[:-1] + ", " + json.dumps(metadata)[1:] + "]"
    _assert_invalid_cli(_run_cli(payload))


def test_cli_rejects_escaped_duplicate_key(metadata):
    payload = '[{"\\u0072ights_status":"restricted",' + json.dumps(metadata)[1:] + "]"
    _assert_invalid_cli(_run_cli(payload))


MALFORMED_URLS = [
    "https://example.invalid\\other/",
    "https://%/",
    "https://%65xample.invalid/",
    "https://example.invalid/%",
    "https://example.invalid/%0",
    "https://example.invalid/%gg",
    "https://example.invalid/a b",
    "https://example .invalid/",
    "https://example.invalid/<invalid>",
    'https://example.invalid/"invalid"',
    "https://example.invalid/?",
    "https://example.invalid/#",
    "https://-example.invalid/",
    "https://example-.invalid/",
    "https://example..invalid/",
    "https://example.invalid../",
    "https://example_invalid/",
    "https://" + "a" * 64 + ".invalid/",
    "https://" + ".".join(["a" * 63] * 4) + "/",
    "https://999.0.2.1/",
    "https://127.1/",
    "https://192.0.2/",
    "https://192.0.2.1./",
    "https://0192.0.2.1/",
    "https://0xc0000201/",
    "https://0x/",
    "https://0X./",
    "https://example.0x/",
    "https://example.0x01/",
    "https://[192.0.2.1]/",
    "https://[2001:db8::1]suffix/",
    "https://[2001:db8::1%25zone]/",
    "https://example.invalid:+80/",
    "https://example.invalid:-1/",
    "https://example.invalid:65536/",
    "https://example.invalid:/",
    "https://example.invalid:\u0668\u0660/",
]


@pytest.mark.parametrize("url", MALFORMED_URLS)
def test_source_url_rejects_malformed_syntax(metadata, url):
    metadata["source_url"] = url
    with pytest.raises(ValueError, match="source_url"):
        validate_inventory([metadata])


@pytest.mark.parametrize("url", MALFORMED_URLS)
def test_cli_rejects_malformed_url_without_disclosure(metadata, url):
    metadata["source_url"] = url
    result = _run_cli(json.dumps([metadata]))
    _assert_invalid_cli(result)
    assert url not in result.stderr


@pytest.mark.parametrize(
    "control",
    [chr(code) for code in range(32)] + ["\x7f", "\x85", "\x9b", "\xa0", "\u3000"],
    ids=lambda char: f"u{ord(char):04x}",
)
@pytest.mark.parametrize("position", ["leading", "hostname", "path", "trailing"])
def test_source_url_rejects_controls_before_normalization(metadata, control, position):
    urls = {
        "leading": control + "https://example.invalid/",
        "hostname": "https://example" + control + ".invalid/",
        "path": "https://example.invalid/" + control + "source",
        "trailing": "https://example.invalid/" + control,
    }
    metadata["source_url"] = urls[position]
    with pytest.raises(ValueError, match="source_url"):
        validate_inventory([metadata])


@pytest.mark.parametrize(
    "url",
    [
        "\x00https://example.invalid/",
        "\thttps://example.invalid/",
        "https://example\x00.invalid/",
        "https://example.invalid/\x00source",
        "https://example.invalid/\x7fsource",
        "https://example.invalid/\x85source",
        "https://example.invalid/\x9bsource",
        "https://example.invalid/\x1f",
        "\xa0https://example.invalid/",
    ],
)
def test_cli_rejects_url_controls_without_disclosure(metadata, url):
    metadata["source_url"] = url
    _assert_invalid_cli(_run_cli(json.dumps([metadata])))


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid/",
        "https://source1/",
        "https://source1.example.invalid/",
        "https://example.invalid./",
        "https://xn--bcher-kva.invalid/",
        "https://192.0.2.1/",
        "https://[2001:db8::1]/",
        "https://[2001:DB8::1]:443/source",
        "https://example.invalid:0/",
        "https://example.invalid:65535/",
        "https://example.invalid/%2Fsource%20page%25",
        "https://example.invalid/a!$&'()*+,;=:@_-~.json",
        "  https://example.invalid/source  ",
    ],
)
def test_source_url_valid_syntax_remains_accepted(metadata, url):
    metadata["source_url"] = url
    assert validate_inventory([metadata])[0]["source_url"] == url.strip(" ")
    result = _run_cli(json.dumps([metadata]))
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["total_sources"] == 1


def test_cli_reads_utf8_metadata_with_ascii_standard_streams(metadata):
    metadata["format"] = "synthetic \u00e9"
    environment = {**os.environ, "PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"}
    result = _run_cli(json.dumps([metadata], ensure_ascii=False), env=environment)
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["total_sources"] == 1


def test_cli_rejects_deeply_nested_json_without_traceback():
    _assert_invalid_cli(_run_cli("[" * 10000))


@pytest.mark.parametrize(
    "payload", [b"\xff", b"\xef\xbb\xbf[]"], ids=["invalid-utf8", "bom"]
)
def test_cli_rejects_invalid_utf8_or_bom_without_traceback(payload):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.modules.state_regulators.arkansas_aogc.source_inventory",
        ],
        input=payload,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.splitlines()[-1].endswith(
        b"error: invalid inventory: missing metadata or invalid field values"
    )


def test_validation_and_summary_do_not_open_network_connections(metadata, monkeypatch):
    def reject_connection(*args, **kwargs):
        raise AssertionError("metadata validation attempted a network connection")

    monkeypatch.setattr(socket, "socket", reject_connection)
    assert validate_inventory([metadata]) == [metadata]
    assert summarize_inventory([metadata])["total_sources"] == 1
