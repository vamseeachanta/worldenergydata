"""Review-aid contract from issue 420; all report contents are synthetic.

Expected results use literal membership and Boolean OR by hand: a local hit OR
an external hit blocks; a warning alone does not. No engineering coefficients
or statistical acceptance thresholds are used.
"""

import importlib.util
import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts/legal/check-operator-aggregation.sh"
POLICY = ROOT / "data/modules/bsee/operator-aggregation-denylist.yaml"
# Independent policy contract: exact-case aliases block except the ambiguous
# bridge-plug abbreviation; the YAML under test supplies no expected severity.
EXPECTED_ALIASES = [
    ("Shell", "block"),
    ("BP", "warn"),
    ("Anadarko", "block"),
    ("Chevron", "block"),
    ("Murphy", "block"),
    ("LLOG", "block"),
    ("Union Oil", "block"),
    ("Hess", "block"),
    ("Talos", "block"),
    ("Woodside", "block"),
    ("Exxon Mobil", "block"),
    ("ExxonMobil", "block"),
    ("Arena Offshore", "block"),
    ("Kosmos Energy", "block"),
    ("Cantium", "block"),
    ("Beacon Growthco", "block"),
    ("Walter Oil & Gas", "block"),
    ("BP America", "block"),
    ("WPX", "block"),
    ("EOG", "block"),
    ("OXY", "block"),
    ("BP Exploration", "block"),
    ("Walter Oil and Gas", "block"),
    ("Exxon", "block"),
    ("Kosmos", "block"),
    ("Oxy", "block"),
]


def run_check(tmp_path, text, external=None, local=None, filename="memo.md"):
    reports = tmp_path / "reports"
    reports.mkdir(exist_ok=True)
    (reports / filename).write_text(text, encoding="utf-8", newline="\n")
    external_path = tmp_path / "external.yaml"
    external_path.write_text(
        (
            external
            if isinstance(external, str)
            else yaml.safe_dump(
                external
                if external is not None
                else {"client_references": [{"pattern": "Unmatched synthetic marker"}]}
            )
        ),
        encoding="utf-8",
        newline="\n",
    )
    command = [
        "bash",
        str(CHECKER),
        "--reports",
        str(reports),
        "--workspace-denylist",
        str(external_path),
    ]
    if local is not None:
        local_path = tmp_path / "local.yaml"
        local_path.write_text(
            local if isinstance(local, str) else yaml.safe_dump(local),
            encoding="utf-8",
            newline="\n",
        )
        command += ["--operator-denylist", str(local_path)]
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command, check=False, capture_output=True, text=True, encoding="utf-8", env=env
    )
    if result.returncode == 1:
        assert "BLOCK" in result.stdout
        assert result.stderr == ""
    return result


@pytest.mark.parametrize(
    "text",
    ["Operator X", "company A", "OPERATOR Z", "operator A", "COMPANY B", "Company C"],
)
def test_placeholder_blocks(tmp_path, text):
    result = run_check(tmp_path, text)
    assert result.returncode == 1, result.stderr
    assert text not in result.stdout


@pytest.mark.parametrize(
    "text", ["BP America", "WPX", "EOG", "OXY", "Shell Offshore Inc."]
)
def test_named_operator_blocks(tmp_path, text):
    result = run_check(tmp_path, text)
    assert result.returncode == 1, result.stderr


@pytest.mark.parametrize(
    "text",
    [
        "BP Exploration",
        "BP Exploration and Production",
        "Walter Oil and Gas",
        "Exxon",
        "Kosmos",
        "Oxy",
        "Kosmos Energy Gulf of Mexico Operations",
    ],
)
def test_alternate_operator_forms_block(tmp_path, text):
    result = run_check(tmp_path, text)
    assert result.returncode == 1
    assert "BLOCK memo.md:1" in result.stdout


def test_aggregate_language_and_word_boundaries_pass(tmp_path):
    result = run_check(
        tmp_path, "Peer aggregate; oxygen; company analysis; operators overall."
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "text, warning",
    [
        ("Hot work used an oxy-acetylene torch.", False),
        ("The shell of the separator cracked.", False),
        ("A BP was set above the perforations.", True),
        ("the company a contractor hired", False),
        ("Operator x", False),
    ],
)
def test_routine_narratives_do_not_block(tmp_path, text, warning):
    result = run_check(tmp_path, text)
    assert result.returncode == 0, result.stderr
    assert "BLOCK" not in result.stdout
    assert ("WARN memo.md:1" in result.stdout) is warning


def test_lowercase_short_aliases_do_not_match(tmp_path):
    for alias, _severity in EXPECTED_ALIASES:
        if " " not in alias:
            result = run_check(tmp_path, alias.lower())
            assert result.returncode == 0, result.stderr
            assert "WARN" not in result.stdout


def test_alias_policy_matches_documented_contract():
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    assert [
        (entry["pattern"], entry["severity"]) for entry in policy["operator_aliases"]
    ] == (EXPECTED_ALIASES)
    assert all(
        entry["case_sensitive"] is (" " not in entry["pattern"])
        for entry in policy["operator_aliases"]
    )


@pytest.mark.parametrize("alias,severity", EXPECTED_ALIASES)
def test_aliases_keep_exact_case_detection(tmp_path, alias, severity):
    result = run_check(tmp_path, alias)
    assert result.returncode == (1 if severity == "block" else 0), result.stderr
    assert f"{severity.upper()} memo.md:1" in result.stdout


@pytest.mark.parametrize("alias,severity", EXPECTED_ALIASES)
def test_uppercase_aliases_keep_expected_severity(tmp_path, alias, severity):
    result = run_check(tmp_path, alias.upper())
    assert result.returncode == (1 if severity == "block" else 0)
    assert f"{severity.upper()} memo.md:1" in result.stdout


@pytest.mark.parametrize("source", ["external", "local"])
@pytest.mark.parametrize(
    "text, status",
    [("SYNTHETIC MARKER", 1), ("synthetic marker", 0), ("Synthetic marker", 0)],
)
def test_sensitive_literals_accept_uppercase_only_variant(
    tmp_path, source, text, status
):
    policy = {
        "client_references": [{"pattern": "Synthetic Marker", "case_sensitive": True}]
    }
    result = run_check(tmp_path, text, **{source: policy})
    assert result.returncode == status


@pytest.mark.parametrize("letter_case", ["lower", "upper"])
def test_full_operator_names_remain_case_insensitive(tmp_path, letter_case):
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    for entry in policy["operator_names"]:
        text = getattr(entry["pattern"], letter_case)()
        result = run_check(tmp_path, text)
        assert result.returncode == 1, result.stderr


def test_external_list_union_and_non_disclosure(tmp_path):
    secret_marker = "Restricted synthetic marker"
    result = run_check(
        tmp_path,
        secret_marker,
        {"client_references": [{"pattern": secret_marker, "case_sensitive": False}]},
    )
    assert result.returncode == 1
    assert secret_marker not in result.stdout + result.stderr
    assert str(tmp_path) not in result.stdout + result.stderr


def test_warning_does_not_block(tmp_path):
    result = run_check(
        tmp_path,
        "Synthetic marker",
        {
            "default_severity": "warn",
            "client_references": [{"pattern": "Synthetic marker"}],
        },
    )
    assert result.returncode == 0
    assert "WARN" in result.stdout


def test_case_sensitive_literal_and_regex_metacharacters(tmp_path):
    policy = {"client_references": [{"pattern": "A.B", "case_sensitive": True}]}
    assert run_check(tmp_path, "a.b AxB", policy).returncode == 0
    assert run_check(tmp_path, "A.B", policy).returncode == 1


@pytest.mark.parametrize(
    "policy",
    [
        {"client_references": [{"pattern": "", "severity": "block"}]},
        {"client_references": [{"pattern": "x", "severity": "ignore"}]},
        {"client_references": [{"pattern": "x", "case_sensitive": "false"}]},
        {"client_references": [{"pattern": "[", "regex": True}]},
        {"client_references": "not a list"},
        {},
    ],
)
def test_malformed_policy_fails_closed(tmp_path, policy):
    result = run_check(tmp_path, "Peer aggregate", policy)
    assert result.returncode == 2
    assert "ERROR" in result.stderr


@pytest.mark.parametrize("source", ["external", "local"])
@pytest.mark.parametrize(
    "policy",
    [{"client_references": []}, {"client_references": [], "operator_names": []}],
)
def test_zero_rule_policy_fails_closed(tmp_path, source, policy):
    result = run_check(tmp_path, "Peer aggregate", **{source: policy})
    assert result.returncode == 2
    assert "ERROR" in result.stderr
    assert "Scanned" not in result.stdout
    assert str(tmp_path) not in result.stderr


@pytest.mark.parametrize("source", ["external", "local"])
@pytest.mark.parametrize(
    "unknown", [{"regx": True}, {"case_sensitve": True}, {"severtiy": "warn"}]
)
def test_unknown_rule_fields_fail_closed(tmp_path, source, unknown):
    policy = {"client_references": [{"pattern": "Synthetic marker", **unknown}]}
    result = run_check(tmp_path, "Peer aggregate", **{source: policy})
    assert result.returncode == 2
    assert "ERROR" in result.stderr
    assert "Scanned" not in result.stdout
    assert "Synthetic marker" not in result.stdout + result.stderr
    assert str(tmp_path) not in result.stderr


@pytest.mark.parametrize("source", ["external", "local"])
def test_workspace_descriptive_rule_fields_remain_supported(tmp_path, source):
    policy = {
        "client_references": [
            {"pattern": "Synthetic marker", "description": "Synthetic description"}
        ]
    }
    result = run_check(tmp_path, "Synthetic marker", **{source: policy})
    assert result.returncode == 1
    assert "Synthetic description" not in result.stdout + result.stderr


@pytest.mark.parametrize("source", ["external", "local"])
@pytest.mark.parametrize(
    "policy",
    [
        "client_references:\n  - pattern: Synthetic marker\nclient_references: []\n",
        (
            "client_references:\n  - pattern: Synthetic marker\n"
            "    pattern: Replacement marker\n"
        ),
        (
            "client_references:\n  - pattern: Synthetic marker\n"
            "    severity: block\n    severity: warn\n"
        ),
        (
            "sources:\n  - title: Synthetic source\n    title: Replacement source\n"
            "client_references: []\n"
        ),
    ],
    ids=["section", "entry-pattern", "entry-severity", "nested-metadata"],
)
def test_duplicate_policy_keys_fail_closed(tmp_path, source, policy):
    result = run_check(tmp_path, "Synthetic marker", **{source: policy})
    assert result.returncode == 2
    assert "ERROR" in result.stderr
    assert "no blocking matches" not in result.stdout
    assert "Synthetic marker" not in result.stdout + result.stderr
    assert "Replacement marker" not in result.stdout + result.stderr
    assert str(tmp_path) not in result.stdout + result.stderr


def test_top_twenty_source_rows_are_present():
    """BSEE PDRANKOP, 15-Oct-2026, CY2024, p.1, first twenty Total Oil rows.

    The expected names are transcribed independently from the source table;
    truncated source labels remain as printed, without invented completions.
    """
    expected = {
        "Shell Offshore Inc.",
        "BP Exploration & Production Inc.",
        "Anadarko Petroleum Corporation",
        "Chevron U.S.A. Inc.",
        "Murphy Exploration & Production Co",
        "LLOG Exploration Offshore, L.L.C.",
        "Union Oil Company of California",
        "Hess Corporation",
        "Talos QN Exploration LLC",
        "Woodside Energy (GOM) Inc.",
        "Exxon Mobil Corporation",
        "Arena Offshore, LP",
        "Kosmos Energy Gulf of Mexico Opera",
        "Talos Energy Ventures, LLC",
        "Talos Petroleum LLC",
        "Cantium, LLC",
        "Beacon Growthco Operating Company,",
        "Walter Oil & Gas Corporation",
        "Shell Gulf of Mexico Inc.",
        "Talos ERT LLC",
    }
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    assert policy["sources"][0]["edition"] == "15-OCT-2026"
    assert {entry["pattern"] for entry in policy["operator_names"]} == expected
    assert all(entry["severity"] == "block" for entry in policy["operator_names"])


def test_each_sourced_operator_is_detected(tmp_path):
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    for entry in policy["operator_names"]:
        result = run_check(tmp_path, entry["pattern"])
        assert result.returncode == 1, result.stderr


def test_multiword_operator_names_and_aliases_accept_hard_wrapping(tmp_path):
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    entries = [(entry["pattern"], "block") for entry in policy["operator_names"]]
    for pattern, severity in entries + EXPECTED_ALIASES:
        if len(pattern.split()) > 1:
            result = run_check(tmp_path, "\n".join(pattern.split()))
            assert result.returncode == (1 if severity == "block" else 0)
            assert f"{severity.upper()} memo.md:1" in result.stdout


@pytest.mark.parametrize("separator", ["\n", "  ", "\t", "\u00a0", "\r\n"])
@pytest.mark.parametrize("source", ["external", "local"])
def test_literal_policy_whitespace_is_flexible(tmp_path, separator, source):
    policy = {"client_references": [{"pattern": "Synthetic marker"}]}
    result = run_check(tmp_path, f"Synthetic{separator}marker", **{source: policy})
    assert result.returncode == 1
    assert "BLOCK memo.md:1" in result.stdout


@pytest.mark.parametrize("extension", ["html", "HTML", "htm"])
@pytest.mark.parametrize("entity", ["&amp;", "&#38;", "&#x26;"])
def test_html_entities_are_decoded_before_matching(tmp_path, extension, entity):
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    for entry in policy["operator_names"]:
        if "&" in entry["pattern"]:
            result = run_check(
                tmp_path,
                entry["pattern"].replace("&", entity),
                filename=f"memo.{extension}",
            )
            assert result.returncode == 1
            assert f"BLOCK memo.{extension}:1" in result.stdout


@pytest.mark.parametrize(
    "text",
    [
        "Peer&#10;aggregate\nSynthetic &amp; Marker",
        "Peer aggregate\nSynthetic&#10;&amp; Marker",
    ],
)
def test_html_entity_decoding_preserves_source_line_numbers(tmp_path, text):
    result = run_check(
        tmp_path,
        text,
        {"client_references": [{"pattern": "Synthetic & Marker"}]},
        filename="memo.html",
    )
    assert result.returncode == 1
    assert "BLOCK memo.html:2" in result.stdout
    assert "memo.html:3" not in result.stdout
    assert text not in result.stdout + result.stderr


def test_non_html_text_is_not_entity_decoded(tmp_path):
    result = run_check(
        tmp_path,
        "Synthetic &amp; Marker",
        {"client_references": [{"pattern": "Synthetic & Marker"}]},
    )
    assert result.returncode == 0
    assert "BLOCK" not in result.stdout


@pytest.mark.parametrize(
    "kind",
    [
        "empty",
        "binary",
        "nul",
        "utf16",
        pytest.param(
            "special",
            marks=pytest.mark.skipif(
                not hasattr(os, "mkfifo"), reason="FIFO creation is unavailable"
            ),
        ),
        "linked-file",
        "linked-directory",
    ],
)
def test_unscannable_report_inputs_fail_closed(tmp_path, kind):
    reports = tmp_path / "reports"
    reports.mkdir()
    external = tmp_path / "external.yaml"
    external.write_text(
        "client_references:\n  - pattern: Unmatched synthetic marker\n",
        encoding="utf-8",
        newline="\n",
    )
    if kind == "binary":
        (reports / "memo.bin").write_bytes(b"\xff")
    elif kind == "nul":
        (reports / "memo.bin").write_bytes(b"Peer aggregate.\x00")
    elif kind == "utf16":
        (reports / "memo.bin").write_bytes("Operator X".encode("utf-16le"))
    elif kind == "special":
        os.mkfifo(reports / "memo.pipe")
    elif kind.startswith("linked"):
        target = tmp_path / "target"
        target.mkdir()
        (target / "memo.md").write_text(
            "Peer aggregate", encoding="utf-8", newline="\n"
        )
        source = target / "memo.md" if kind == "linked-file" else target
        try:
            (reports / "link").symlink_to(source, target_is_directory=source.is_dir())
        except (OSError, NotImplementedError):
            pytest.skip("Symbolic-link creation is unavailable")
    result = subprocess.run(
        [
            "bash",
            str(CHECKER),
            "--reports",
            str(reports),
            "--workspace-denylist",
            str(external),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 2
    assert "ERROR" in result.stderr
    assert "no blocking matches" not in result.stdout
    assert str(tmp_path) not in result.stderr


@pytest.mark.skipif(
    os.name == "nt" or getattr(os, "geteuid", lambda: 0)() == 0,
    reason="Directory permission denial requires an unprivileged POSIX process",
)
def test_unreadable_subdirectory_fails_closed(tmp_path):
    restricted = tmp_path / "reports" / "restricted"
    restricted.mkdir(parents=True)
    (restricted / "memo.md").write_text("Operator X", encoding="utf-8", newline="\n")
    restricted.chmod(0)
    try:
        try:
            list(restricted.iterdir())
        except PermissionError:
            pass
        else:
            pytest.skip("Directory listing is permitted despite the mode restriction")
        result = run_check(tmp_path, "Peer aggregate")
    finally:
        restricted.chmod(0o700)
    assert result.returncode == 2
    assert "ERROR" in result.stderr
    assert "no blocking matches" not in result.stdout
    assert "Operator X" not in result.stdout + result.stderr
    assert str(tmp_path) not in result.stdout + result.stderr


def test_nested_readable_report_is_scanned(tmp_path):
    nested = tmp_path / "reports" / "nested"
    nested.mkdir(parents=True)
    (nested / "memo.md").write_text(
        "Peer aggregate\nOperator X", encoding="utf-8", newline="\n"
    )
    result = run_check(tmp_path, "Peer aggregate")
    assert result.returncode == 1
    assert "BLOCK nested/memo.md:2" in result.stdout
    assert "Scanned 2 report files; BLOCK" in result.stdout


@pytest.fixture
def checker_module():
    spec = importlib.util.spec_from_file_location(
        "operator_aggregation_checker",
        CHECKER.with_name("check_operator_aggregation.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("location", ["root", "nested"])
def test_directory_reparse_points_fail_closed(
    tmp_path, monkeypatch, checker_module, location
):
    reports = tmp_path / "reports"
    nested = reports / "nested"
    nested.mkdir(parents=True)
    (nested / "memo.md").write_text("Peer aggregate", encoding="utf-8", newline="\n")
    linked = reports if location == "root" else nested
    original_lstat = Path.lstat

    def reparse_lstat(path):
        metadata = original_lstat(path)
        if path == linked:
            return SimpleNamespace(
                st_mode=metadata.st_mode,
                st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
            )
        return metadata

    monkeypatch.setattr(Path, "lstat", reparse_lstat)
    with pytest.raises(ValueError, match="linked"):
        checker_module.scan_reports(reports, [])


def test_disappearing_report_stat_fails_closed(tmp_path, monkeypatch, checker_module):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "readable.md").write_text(
        "Peer aggregate", encoding="utf-8", newline="\n"
    )
    missing = reports / "missing.md"
    missing.write_text("Operator X", encoding="utf-8", newline="\n")
    original_lstat = Path.lstat

    def failing_lstat(path):
        if path == missing:
            raise FileNotFoundError("report disappeared")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", failing_lstat)
    with pytest.raises(FileNotFoundError):
        checker_module.scan_reports(reports, [])


def test_enumeration_error_fails_closed_with_readable_sibling(
    tmp_path, monkeypatch, checker_module, capsys
):
    reports = tmp_path / "reports"
    restricted = reports / "restricted"
    restricted.mkdir(parents=True)
    (reports / "readable.md").write_text(
        "Peer aggregate", encoding="utf-8", newline="\n"
    )
    external = tmp_path / "external.yaml"
    external.write_text(
        "client_references:\n  - pattern: Synthetic marker\n",
        encoding="utf-8",
        newline="\n",
    )
    original_iterdir = Path.iterdir

    def failing_iterdir(path):
        if path == restricted:
            raise PermissionError("directory enumeration denied")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", failing_iterdir)
    monkeypatch.setattr(
        checker_module.sys,
        "argv",
        ["checker", "--reports", str(reports), "--workspace-denylist", str(external)],
    )
    assert checker_module.main() == 2
    output = capsys.readouterr()
    assert "ERROR" in output.err
    assert "Scanned" not in output.out
    assert str(tmp_path) not in output.out + output.err


def test_nonregular_metadata_fails_closed(tmp_path, monkeypatch, checker_module):
    reports = tmp_path / "reports"
    reports.mkdir()
    unusual = reports / "memo.txt"
    unusual.write_text("Peer aggregate", encoding="utf-8", newline="\n")
    original_lstat = Path.lstat

    def nonregular_lstat(path):
        return (
            SimpleNamespace(st_mode=stat.S_IFIFO)
            if path == unusual
            else original_lstat(path)
        )

    monkeypatch.setattr(Path, "lstat", nonregular_lstat)
    with pytest.raises(ValueError, match="unsupported"):
        checker_module.scan_reports(reports, [])


def test_missing_external_policy_fails_closed(tmp_path):
    result = subprocess.run(
        ["bash", str(CHECKER), "--workspace-denylist", str(tmp_path / "missing.yaml")],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 2
    assert str(tmp_path) not in result.stderr


def test_placeholder_split_across_lines_blocks(tmp_path):
    """Issue 420 placeholder rule: whitespace between label parts includes a newline."""
    result = run_check(tmp_path, "Peer aggregate.\nOperator\nX")
    assert result.returncode == 1
    assert "memo.md:2" in result.stdout


@pytest.mark.parametrize(
    "text",
    [
        "Operators A and B",
        "Companies X",
        "Operator **X**",
        "Company _A_",
        "Operator 'X'",
        'Company "A"',
        "Operator-X",
        "Company: X",
        "Operator 1",
        "Companies 12 and 13",
    ],
)
def test_formatted_plural_and_numbered_placeholders_block(tmp_path, text):
    result = run_check(tmp_path, text)
    assert result.returncode == 1
    assert "BLOCK memo.md:1" in result.stdout


@pytest.mark.parametrize(
    "text", ["Operators overall", "Company analysis", "Operator **x**", "Operator 12A"]
)
def test_placeholder_extensions_retain_word_and_case_boundaries(tmp_path, text):
    result = run_check(tmp_path, text)
    assert result.returncode == 0
    assert "BLOCK" not in result.stdout
