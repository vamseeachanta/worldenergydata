"""Transaction metrics use synthetic inputs, not asserted transaction values."""

import copy
import json
from pathlib import Path

import pytest

from worldenergydata.field_development.transaction_package import (
    build_package,
    valuation_metrics,
)
from worldenergydata.field_development.transaction_report import write_package


def observation(value, unit, basis="synthetic", subject="synthetic portfolio"):
    """Synthetic fixture values are defined by each test's hand calculation."""
    return {
        "value": value,
        "unit": unit,
        "basis": basis,
        "subject": subject,
        "as_of": "2026-01-01",
        "citation": {"source_id": "hand-calculation", "locator": "test docstring"},
    }


def test_metrics_independent_hand_calculation():
    """USD 120 / 8 boe = USD 15/boe; USD 120 / 4 boe/d = USD 30/(boe/d).

    These are invented exact arithmetic inputs, not public transaction facts.
    No conversion, discount rate, or working-interest factor is assumed.
    """
    result = valuation_metrics(
        observation(120, "USD"),
        observation(8, "boe"),
        observation(4, "boe/d"),
    )
    assert result["usd_per_boe"]["value"] == 15
    assert result["usd_per_flowing_boe_day"]["value"] == 30
    assert result["usd_per_boe"]["status"] == "EVALUATED"


ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / "data/modules/offshore_assets/transactions/na_kika_coulomb.json"


@pytest.mark.parametrize("value", [-1, "NaN", "Infinity", True])
def test_invalid_values_refused(value):
    with pytest.raises(ValueError):
        valuation_metrics(
            observation(value, "USD"), observation(8, "boe"), observation(4, "boe/d")
        )


@pytest.mark.parametrize("identity", ["basis", "subject"])
def test_cross_basis_or_subject_ratios_refused(identity):
    denominator = observation(8, "boe")
    denominator[identity] = "different"
    with pytest.raises(ValueError, match="Mixed"):
        valuation_metrics(observation(120, "USD"), denominator, observation(4, "boe/d"))


def test_missing_denominator_is_not_zero_or_a_failed_transaction():
    """An unavailable reserve input does not suppress the independent 120/4 ratio."""
    missing = {"value": None, "unit": "boe", "reason": "Reserve evidence unavailable"}
    result = valuation_metrics(
        observation(120, "USD"), missing, observation(4, "boe/d")
    )
    assert result["usd_per_boe"]["status"] == "NOT_EVALUATED"
    assert result["usd_per_boe"]["value"] is None
    assert result["usd_per_flowing_boe_day"]["value"] == 30


def test_zero_production_does_not_divide():
    result = valuation_metrics(
        observation(120, "USD"), observation(8, "boe"), observation(0, "boe/d")
    )
    assert result["usd_per_flowing_boe_day"]["status"] == "NOT_EVALUATED"


def test_bare_source_identifier_is_insufficient():
    amount = observation(120, "USD")
    amount["citation"] = {"source_id": "hand-calculation"}
    with pytest.raises(ValueError, match="citation"):
        valuation_metrics(amount, observation(8, "boe"), observation(4, "boe/d"))


def test_real_package_preserves_source_gaps_and_all_transaction_bases():
    data = json.loads(INPUT.read_text())
    package = build_package(data, ROOT)
    assert set(package["metrics"]["bases"]) == {
        "shell_total",
        "talos_announced",
        "talos_net",
        "ridgewood",
    }
    assert package["metrics"]["screening_status"] == "NOT_EVALUATED"
    for basis in package["metrics"]["bases"].values():
        assert all(metric["value"] is None for metric in basis.values())
    assert package["provenance"]["input_sha256"]
    assert package["transaction"]["closing_status"] == "NOT_EVALUATED"
    assert (
        package["transaction"]["terms"]["bp_preferential_right"]["status"]
        == "NOT_EVALUATED"
    )


def test_unavailable_source_cannot_support_known_fact():
    data = json.loads(INPUT.read_text())
    data["bases"]["shell_total"]["consideration"]["citation"][
        "source_id"
    ] = "talos_release"
    with pytest.raises(ValueError, match="unavailable"):
        build_package(data, ROOT)


@pytest.mark.parametrize(
    "source_id", ["catalog_host", "catalog_fields", "catalog_crosswalk"]
)
def test_unavailable_catalog_cannot_support_generated_lifecycle(source_id):
    data = json.loads(INPUT.read_text())
    data["sources"][source_id]["access"] = "unavailable"
    with pytest.raises(ValueError, match="unavailable"):
        build_package(data, ROOT)


def _release_unavailable_with_available_input_citations():
    data = json.loads(INPUT.read_text())
    data["sources"]["input_evidence"] = copy.deepcopy(data["sources"]["shell_release"])
    data["sources"]["shell_release"]["access"] = "unavailable"
    data["transaction"]["buyer_group_citation"]["source_id"] = "input_evidence"
    for fact in data["transaction"]["working_interests"]:
        fact["citation"]["source_id"] = "input_evidence"
    for facts in data["bases"].values():
        for fact in facts.values():
            if fact.get("value") is not None:
                fact["citation"]["source_id"] = "input_evidence"
    return data


@pytest.mark.parametrize("kind", ["hub", "field"])
def test_unavailable_release_cannot_support_generated_lifecycle(kind):
    """The hub isolates membership from the field's concept and host claims."""
    data = _release_unavailable_with_available_input_citations()
    data["assets"] = [asset for asset in data["assets"] if asset["kind"] == kind]
    with pytest.raises(ValueError, match="unavailable"):
        build_package(data, ROOT)


def test_unavailable_unused_release_does_not_block_uncited_roster_entry():
    data = _release_unavailable_with_available_input_citations()
    data["assets"] = [asset for asset in data["assets"] if asset["kind"] == "expansion"]
    rows = build_package(data, ROOT)["lifecycle"]["assets"]
    assert len(rows) == 1
    assert rows[0]["transaction_membership_status"] == "NOT_EVALUATED"


def test_supported_membership_has_an_available_source_and_locator():
    data = json.loads(INPUT.read_text())
    rows = build_package(data, ROOT)["lifecycle"]["assets"]
    supported = 0
    for row in rows:
        citation = row["transaction_membership_citation"]
        if row["transaction_membership_status"] == "SOURCE_SUPPORTED":
            supported += 1
            assert citation["source_id"] == "shell_release"
            assert citation["locator"]
            assert data["sources"][citation["source_id"]]["access"] == "available"
        else:
            assert citation is None
    assert supported == 2


def test_source_digest_mismatch_refused(tmp_path):
    data = json.loads(INPUT.read_text())
    copied = copy.deepcopy(data)
    copied["sources"]["catalog_fields"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="digest"):
        build_package(copied, ROOT)


def test_lifecycle_separates_host_concept_and_field_concept():
    package = build_package(json.loads(INPUT.read_text()), ROOT)
    roster = {row["name"]: row for row in package["lifecycle"]["assets"]}
    assert set(roster) == {
        "Na Kika",
        "Ariel",
        "Coulomb",
        "East Anstey",
        "Fourier",
        "Herschel",
        "Herschel Expansion",
        "Kepler",
    }
    assert roster["Na Kika"]["host_concept"] == "semisub_fps"
    assert roster["Coulomb"]["field_concept"] == "subsea_tieback"
    assert roster["Coulomb"]["catalog_host_concept"] == "semisub_fps"
    assert roster["Herschel"]["generated_page_status"] == "missing"
    assert roster["Herschel Expansion"]["lifecycle_status"] == "NOT_EVALUATED"
    assert roster["East Anstey"]["transaction_membership_status"] == "NOT_EVALUATED"


def test_block_crosswalk_never_becomes_field_economics_readiness():
    package = build_package(json.loads(INPUT.read_text()), ROOT)
    rows = {row["name"]: row for row in package["economics_readiness"]["fields"]}
    assert rows["Coulomb"]["block_match"] is True
    assert rows["Herschel"]["block_match"] is False
    assert all(row["status"] == "NOT_EVALUATED" for row in rows.values())
    assert "verified_field_production" in rows["Coulomb"]["missing_inputs"]
    assert "discount_rate" in rows["Coulomb"]["missing_inputs"]
    assert rows["Coulomb"]["npv_usd"] is None


def test_report_generation_readback_escaping_and_repeatability(tmp_path):
    data = json.loads(INPUT.read_text())
    data["title"] = '<script>alert("synthetic")</script>'
    package = build_package(data, ROOT)
    outputs = write_package(package, tmp_path, ROOT)
    expected = {
        "index.html",
        "lifecycle.html",
        "metrics.json",
        "lifecycle.json",
        "economics_readiness.json",
        "provenance.json",
    }
    assert {path.name for path in outputs} == expected
    before = {path.name: path.read_bytes() for path in outputs}
    write_package(package, tmp_path, ROOT)
    assert before == {path.name: path.read_bytes() for path in outputs}
    page = (tmp_path / "index.html").read_text()
    assert data["title"] not in page
    assert "&lt;script&gt;" in page
    assert "Input echo" in page and "Revision history" in page
    assert "NOT_EVALUATED" in page and "Source provenance" in page
    assert "<script src=" not in page and '<link rel="stylesheet"' not in page
    assert json.loads((tmp_path / "metrics.json").read_text()) == package["metrics"]
    assert (
        json.loads((tmp_path / "provenance.json").read_text()) == package["provenance"]
    )
    assert "Coulomb" in (tmp_path / "lifecycle.html").read_text()


def test_generator_cli_from_repository(tmp_path):
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "scripts/field_development/build_na_kika_coulomb_transaction.py",
            "--out",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (
        json.loads((tmp_path / "economics_readiness.json").read_text())["status"]
        == "NOT_EVALUATED"
    )


def test_executable_source_url_refused():
    data = json.loads(INPUT.read_text())
    data["sources"]["shell_release"]["url"] = "javascript:alert(1)"
    with pytest.raises(ValueError, match="HTTPS"):
        build_package(data, ROOT)


def test_source_path_cannot_escape_repository(tmp_path):
    data = json.loads(INPUT.read_text())
    data["sources"]["catalog_fields"]["path"] = str(tmp_path / "outside.csv")
    with pytest.raises(ValueError, match="inside"):
        build_package(data, ROOT)


def test_retained_outputs_have_exact_structure_classification():
    from scripts.maintenance.verify_repo_structure import load_contract, validate_paths

    contract = load_contract(ROOT / "config/repo_structure.yml")
    prefix = "reports/field_development/transactions/na_kika_coulomb/"
    paths = [
        prefix + name
        for name in (
            "index.html",
            "lifecycle.html",
            "metrics.json",
            "lifecycle.json",
            "economics_readiness.json",
            "provenance.json",
        )
    ]
    assert validate_paths(paths, contract) == []
    assert validate_paths([prefix + "unclassified.json"], contract)
