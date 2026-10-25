"""Offline source-scope checks using synthetic evidence, never dataset access."""

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/metocean/scope_sources.py"
spec = importlib.util.spec_from_file_location("scope_sources", SCRIPT)
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture
def observation():
    snippets = [
        ("package", "package_licence", "LGPL-2.1-or-later"),
        ("terms", "dataset_terms", "NORA3: CC-BY-4.0; attribution required."),
        ("region", "coverage", "NORA3 covers the Norwegian regional seas."),
        ("api", "api", "def import_data(self, save_csv=False):"),
    ]
    source = {
        "source_id": "synthetic",
        "source_url": "https://example.org/metadata",
        "retrieved_utc": "2026-10-24T00:00:00Z",
        "http_status": 200,
        "command_exit": 0,
        "source_sha256": digest("\n".join(text for _, _, text in snippets)),
        "excerpts": [
            {
                "excerpt_id": key,
                "kind": kind,
                "locator": "synthetic metadata; TimeSeries" if kind == "api" else key,
                "text": text,
                "sha256": digest(text),
            }
            for key, kind, text in snippets
        ],
    }
    record = {
        "dataset_id": "NORA3",
        "package_name": "metocean-api",
        "package_version": "1.0.0",
        "package_licence": {
            "state": "CONFIRMED",
            "expression": "LGPL-2.1-or-later",
            "evidence": ["synthetic:package"],
        },
        "dataset_terms": {
            "state": "CONFIRMED",
            "expression": "CC-BY-4.0",
            "evidence": ["synthetic:terms"],
            "redistribution": "NOT_APPROVED",
        },
        "coverage": {
            "state": "CONFIRMED",
            "description": "Regional Norwegian seas; no global coverage claim.",
            "evidence": ["synthetic:region"],
        },
        "source_url": source["source_url"],
        "retrieved_utc": source["retrieved_utc"],
        "http_status": 200,
        "source_sha256": source["source_sha256"],
        "api_symbols": [
            {
                "symbol": "TimeSeries.import_data",
                "signature": "def import_data(self, save_csv=False):",
                "evidence": ["synthetic:api"],
            }
        ],
        "provenance": ["synthetic"],
        "access_state": "METADATA_ONLY",
        "readiness": "SCOPED",
        "missing_inputs": [],
    }
    return {
        "schema_version": 1,
        "validated_benchmark_count": 0,
        "title": "Regional adapter source scope",
        "summary": "Synthetic source inspection only.",
        "revision_history": [
            {"revision": 1, "date": "2026-10-24", "change": "Initial scope."}
        ],
        "scope": {"boundary": "One optional extra for two regional datasets."},
        "inventory": {"status": "Interfaces inspected."},
        "local_interfaces": [],
        "sources": [source],
        "records": [record],
        "contract": {"failure_behavior": "Reject unsupported data and missing units."},
        "method_routes": copy.deepcopy(scope.METHOD_ROUTES),
        "skipped": ["Dependency pin, reference pack and skill changes."],
        "known_limits": ["No engineering qualification or redistribution approval."],
    }


def test_complete_scope_and_deterministic_serialization(observation):
    scope.validate_document(observation)
    first = scope.serialize_document(observation)
    assert first == scope.serialize_document(json.loads(first))
    assert first.endswith("\n")


@pytest.mark.parametrize("expression", ["", "unknown", "LGPL or MIT", None])
def test_missing_or_ambiguous_package_licence(observation, expression):
    observation["records"][0]["package_licence"]["expression"] = expression
    with pytest.raises(ValueError, match="licence"):
        scope.validate_document(observation)


@pytest.mark.parametrize("field", ["package_licence", "dataset_terms", "coverage"])
def test_missing_claim_evidence(observation, field):
    observation["records"][0][field]["evidence"] = []
    with pytest.raises(ValueError, match="evidence"):
        scope.validate_document(observation)


def test_package_licence_cannot_supply_dataset_terms(observation):
    observation["records"][0]["dataset_terms"] = copy.deepcopy(
        observation["records"][0]["package_licence"]
    )
    with pytest.raises(ValueError, match="dataset_terms"):
        scope.validate_document(observation)


@pytest.mark.parametrize("field", ["retrieved_utc", "http_status", "source_sha256"])
def test_missing_retrieval_evidence(observation, field):
    del observation["sources"][0][field]
    with pytest.raises(ValueError, match=field):
        scope.validate_document(observation)


def test_excerpt_digest_mismatch(observation):
    observation["sources"][0]["excerpts"][0]["text"] += " altered"
    with pytest.raises(ValueError, match="digest"):
        scope.validate_document(observation)


def test_retained_body_digest_mismatch(observation, tmp_path):
    (tmp_path / "synthetic.body").write_text("wrong body")
    with pytest.raises(ValueError, match="digest"):
        scope.validate_document(observation, evidence_dir=tmp_path)
    (tmp_path / "synthetic.body").write_text(
        "\n".join(e["text"] for e in observation["sources"][0]["excerpts"])
    )
    scope.validate_document(observation, evidence_dir=tmp_path)


@pytest.mark.parametrize("status,exit_code", [(403, 22), (200, 28), (0, 6)])
def test_unavailable_source_cannot_be_scoped(observation, status, exit_code):
    observation["sources"][0].update(http_status=status, command_exit=exit_code)
    observation["records"][0]["http_status"] = status
    with pytest.raises(ValueError, match="retrieval"):
        scope.validate_document(observation)


def test_complete_blocked_record_is_a_valid_result(observation):
    record = observation["records"][0]
    record.update(
        readiness="BLOCKED",
        access_state="UNAVAILABLE",
        missing_inputs=["Dataset terms and API source could not be retrieved."],
        api_symbols=[],
    )
    for field in ("package_licence", "dataset_terms", "coverage"):
        record[field].update(state="UNKNOWN", evidence=[])
    observation["sources"][0].update(http_status=403, command_exit=22)
    record["http_status"] = 403
    scope.validate_document(observation)


def test_blocked_record_must_name_missing_inputs(observation):
    observation["records"][0]["readiness"] = "BLOCKED"
    with pytest.raises(ValueError, match="missing_inputs"):
        scope.validate_document(observation)


def test_unsupported_dataset(observation):
    observation["records"][0]["dataset_id"] = "ERA5"
    with pytest.raises(ValueError, match="dataset"):
        scope.validate_document(observation)


@pytest.mark.parametrize("symbol", ["EVA", "contours.IFORM", "TimeSeries.fake"])
def test_invented_api_symbol(observation, symbol):
    observation["records"][0]["api_symbols"][0]["symbol"] = symbol
    with pytest.raises(ValueError, match="API"):
        scope.validate_document(observation)


def test_missing_api_symbols_prevents_scope(observation):
    observation["records"][0]["api_symbols"] = []
    with pytest.raises(ValueError, match="API"):
        scope.validate_document(observation)


def test_blanket_delegation_rejected(observation):
    observation["method_routes"] = {"all": ["pyextremes", "scipy.stats", "virocon"]}
    with pytest.raises(ValueError, match="delegation"):
        scope.validate_document(observation)


def test_local_interface_digest_checked(observation, tmp_path):
    observation["local_interfaces"] = [
        {"path": "interface.py", "source_sha256": digest("expected"), "signatures": []}
    ]
    (tmp_path / "interface.py").write_text("changed")
    with pytest.raises(ValueError, match="digest"):
        scope.validate_document(observation, repo_root=tmp_path)


def test_render_escapes_untrusted_text(observation):
    observation["summary"] = "<script>alert('metadata')</script>"
    rendered = scope.render_html(observation)
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    for heading in ("Summary", "Revision history", "Scope", "Source observations"):
        assert heading in rendered
    assert rendered.index("Revision history") < rendered.index("Scope</h2>")


def test_cli_rejects_invalid_input_before_writing(observation, tmp_path):
    observation["records"][0]["dataset_id"] = "unsupported"
    source = tmp_path / "input.json"
    source.write_text(json.dumps(observation))
    output = tmp_path / "report"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(source), "--out-dir", str(output)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not output.exists()


@pytest.mark.parametrize(
    "expression", ["", "unknown", "CC-BY-4.0 or unspecified", None]
)
def test_missing_or_ambiguous_dataset_licence(observation, expression):
    observation["records"][0]["dataset_terms"]["expression"] = expression
    with pytest.raises(ValueError, match="dataset_terms"):
        scope.validate_document(observation)


def test_unverified_mapping_prevents_scope(observation):
    observation["contract"]["missing_inputs"] = ["Confirm current rotation and units."]
    with pytest.raises(ValueError, match="contract"):
        scope.validate_document(observation)


def test_utc_timezone_required(observation):
    observation["sources"][0]["retrieved_utc"] = "2026-10-24T00:00:00"
    with pytest.raises(ValueError, match="UTC"):
        scope.validate_document(observation)


def test_record_digest_cannot_disagree_with_retrieval(observation):
    observation["records"][0]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="retrieval"):
        scope.validate_document(observation)


def test_missing_retained_body_rejected(observation, tmp_path):
    with pytest.raises(ValueError, match="body is missing"):
        scope.validate_document(observation, evidence_dir=tmp_path)


def test_duplicate_sources_and_datasets_rejected(observation):
    observation["sources"].append(copy.deepcopy(observation["sources"][0]))
    with pytest.raises(ValueError, match="unique"):
        scope.validate_document(observation)
    observation["sources"].pop()
    observation["records"].append(copy.deepcopy(observation["records"][0]))
    with pytest.raises(ValueError, match="duplicate dataset"):
        scope.validate_document(observation)


def test_api_signature_cannot_execute_or_contain_a_body(observation):
    observation["records"][0]["api_symbols"][0][
        "signature"
    ] = "def import_data(self):\n    raise RuntimeError('invented body')"
    with pytest.raises(ValueError, match="API"):
        scope.validate_document(observation)


def test_excerpt_must_exist_in_retained_source(observation, tmp_path):
    body = "\n".join(e["text"] for e in observation["sources"][0]["excerpts"])
    observation["sources"][0]["source_sha256"] = digest(body)
    observation["records"][0]["source_sha256"] = digest(body)
    (tmp_path / "synthetic.body").write_text(body)
    scope.validate_document(observation, evidence_dir=tmp_path)
    excerpt = observation["sources"][0]["excerpts"][0]
    excerpt["text"] = "An invented licence statement with a fresh excerpt digest."
    excerpt["sha256"] = digest(excerpt["text"])
    with pytest.raises(ValueError, match="retained source"):
        scope.validate_document(observation, evidence_dir=tmp_path)


def test_checked_in_report_is_blocked_and_regenerates(tmp_path):
    path = SCRIPT.parents[2] / "docs/research/metocean-adapter-scope.json"
    document = json.loads(path.read_text())
    scope.validate_document(document, repo_root=SCRIPT.parents[2])
    assert {r["dataset_id"] for r in document["records"]} == {"NORA3", "NorKyst800"}
    assert all(r["readiness"] == "BLOCKED" for r in document["records"])
    assert path.read_text() == scope.serialize_document(document)
    assert path.with_suffix(".html").read_text() == scope.render_html(document)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(path), "--out-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / path.name).read_bytes() == path.read_bytes()
    assert (tmp_path / path.with_suffix(".html").name).read_bytes() == path.with_suffix(
        ".html"
    ).read_bytes()


def test_scope_cannot_claim_validated_benchmarks(observation):
    observation["validated_benchmark_count"] = 1
    with pytest.raises(ValueError, match="benchmark"):
        scope.validate_document(observation)
