"""Review-aid contract from issue 420; all report contents are synthetic.

Expected results use literal membership and Boolean OR by hand: a local hit OR
an external hit blocks; a warning alone does not. No engineering coefficients
or statistical acceptance thresholds are used.
"""

import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts/legal/check-operator-aggregation.sh"
POLICY = ROOT / "data/modules/bsee/operator-aggregation-denylist.yaml"


def run_check(tmp_path, text, external=None, local=None):
    reports = tmp_path / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "memo.md").write_text(text, encoding="utf-8")
    external_path = tmp_path / "external.yaml"
    external_path.write_text(
        (
            external
            if isinstance(external, str)
            else yaml.safe_dump(
                external if external is not None else {"client_references": []}
            )
        ),
        encoding="utf-8",
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
            local if isinstance(local, str) else yaml.safe_dump(local), encoding="utf-8"
        )
        command += ["--operator-denylist", str(local_path)]
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command, check=False, capture_output=True, text=True, env=env
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
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    for entry in policy["operator_aliases"]:
        if " " not in entry["pattern"]:
            result = run_check(tmp_path, entry["pattern"].lower())
            assert result.returncode == 0, result.stderr
            assert "WARN" not in result.stdout


def test_aliases_keep_exact_case_detection(tmp_path):
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    for entry in policy["operator_aliases"]:
        result = run_check(tmp_path, entry["pattern"])
        severity = entry["severity"]
        assert result.returncode == (1 if severity == "block" else 0), result.stderr
        assert f"{severity.upper()} memo.md:1" in result.stdout


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


@pytest.mark.parametrize(
    "kind", ["empty", "binary", "nul", "utf16", "linked-file", "linked-directory"]
)
def test_unscannable_report_inputs_fail_closed(tmp_path, kind):
    reports = tmp_path / "reports"
    reports.mkdir()
    external = tmp_path / "external.yaml"
    external.write_text("client_references: []\n", encoding="utf-8")
    if kind == "binary":
        (reports / "memo.bin").write_bytes(b"\xff")
    elif kind == "nul":
        (reports / "memo.bin").write_bytes(b"Peer aggregate.\x00")
    elif kind == "utf16":
        (reports / "memo.bin").write_bytes("Operator X".encode("utf-16le"))
    elif kind.startswith("linked"):
        target = tmp_path / "target"
        target.mkdir()
        (target / "memo.md").write_text("Peer aggregate", encoding="utf-8")
        source = target / "memo.md" if kind == "linked-file" else target
        (reports / "link").symlink_to(source, target_is_directory=source.is_dir())
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
    )
    assert result.returncode == 2
    assert "ERROR" in result.stderr
    assert "no blocking matches" not in result.stdout
    assert str(tmp_path) not in result.stderr


def test_missing_external_policy_fails_closed(tmp_path):
    result = subprocess.run(
        ["bash", str(CHECKER), "--workspace-denylist", str(tmp_path / "missing.yaml")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert str(tmp_path) not in result.stderr


def test_placeholder_split_across_lines_blocks(tmp_path):
    """Issue 420 placeholder rule: whitespace between label parts includes a newline."""
    result = run_check(tmp_path, "Peer aggregate.\nOperator\nX")
    assert result.returncode == 1
    assert "memo.md:2" in result.stdout
