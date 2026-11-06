"""Transaction metrics use synthetic inputs, not asserted transaction values."""

import copy
import hashlib
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
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    package = build_package(data, ROOT)
    assert set(package["metrics"]["bases"]) == {
        "shell_total",
        "talos_announced",
        "talos_net",
        "ridgewood",
    }
    assert package["metrics"]["screening_status"] == "NOT_EVALUATED"
    for basis in ("shell_total", "ridgewood"):
        assert all(
            metric["value"] is None
            for metric in package["metrics"]["bases"][basis].values()
        )
    assert package["provenance"]["input_sha256"]
    assert package["transaction"]["closing_status"] == "NOT_EVALUATED"
    assert (
        package["transaction"]["terms"]["bp_preferential_right"]["status"]
        == "NOT_EVALUATED"
    )


def test_unavailable_source_cannot_support_known_fact():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    data["sources"]["talos_release"]["access"] = "unavailable"
    with pytest.raises(ValueError, match="unavailable"):
        build_package(data, ROOT)


@pytest.mark.parametrize(
    "source_id", ["catalog_host", "catalog_fields", "catalog_crosswalk"]
)
def test_unavailable_catalog_cannot_support_generated_lifecycle(source_id):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    data["sources"][source_id]["access"] = "unavailable"
    with pytest.raises(ValueError, match="unavailable"):
        build_package(data, ROOT)


def _release_unavailable_with_available_input_citations():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
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
    data = json.loads(INPUT.read_text(encoding="utf-8"))
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
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    copied = copy.deepcopy(data)
    copied["sources"]["catalog_fields"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="digest"):
        build_package(copied, ROOT)


def test_lifecycle_separates_host_concept_and_field_concept():
    package = build_package(json.loads(INPUT.read_text(encoding="utf-8")), ROOT)
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
    package = build_package(json.loads(INPUT.read_text(encoding="utf-8")), ROOT)
    rows = {row["name"]: row for row in package["economics_readiness"]["fields"]}
    assert rows["Coulomb"]["block_match"] is True
    assert rows["Herschel"]["block_match"] is False
    assert all(row["status"] == "NOT_EVALUATED" for row in rows.values())
    assert "verified_field_production" in rows["Coulomb"]["missing_inputs"]
    assert "discount_rate" in rows["Coulomb"]["missing_inputs"]
    assert rows["Coulomb"]["npv_usd"] is None


def test_report_generation_readback_escaping_and_repeatability(tmp_path):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
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
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert data["title"] not in page
    assert "&lt;script&gt;" in page
    assert "Input echo" in page and "Revision history" in page
    assert "NOT_EVALUATED" in page and "Source provenance" in page
    assert "<script src=" not in page and '<link rel="stylesheet"' not in page
    assert (
        json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
        == package["metrics"]
    )
    assert (
        json.loads((tmp_path / "provenance.json").read_text(encoding="utf-8"))
        == package["provenance"]
    )
    assert "Coulomb" in (tmp_path / "lifecycle.html").read_text(encoding="utf-8")


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
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (
        json.loads((tmp_path / "economics_readiness.json").read_text(encoding="utf-8"))[
            "status"
        ]
        == "NOT_EVALUATED"
    )


def test_executable_source_url_refused():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    data["sources"]["shell_release"]["url"] = "javascript:alert(1)"
    with pytest.raises(ValueError, match="HTTPS"):
        build_package(data, ROOT)


def test_source_path_cannot_escape_repository(tmp_path):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
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


def test_buyer_evidence_preserves_acquired_interest_and_adjusted_range():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    package = build_package(data, ROOT)
    announced = data["bases"]["talos_announced"]
    net = data["bases"]["talos_net"]
    assert announced["consideration"]["value"] == 850_000_000
    assert announced["reserves"]["value"] == 23_000_000
    assert announced["production"]["value"] == 16_000
    assert net["consideration"]["range"] == [450_000_000, 500_000_000]
    assert net["consideration"]["excludes_deposit_usd"] == 42_500_000
    assert announced["reserves"]["reserve_category"] == "proved"
    assert announced["production"]["measurement_period"] == "2026-Q1"
    for basis in ("talos_announced", "talos_net"):
        for fact in data["bases"][basis].values():
            assert fact["subject"] == "Talos acquired interests"
            assert fact["basis"] == basis
            assert fact["citation"]["source_id"] == "talos_release"
    ratios = package["metrics"]["bases"]["talos_announced"]
    # Hand calculation: 850 million / 23 million = 36.956521739 USD/boe.
    assert ratios["usd_per_boe"]["value"] == pytest.approx(36.956521739)
    # Hand calculation: 850,000,000 / 16,000 = 53,125 USD/(boe/d).
    assert ratios["usd_per_flowing_boe_day"]["value"] == 53_125
    adjusted = package["metrics"]["bases"]["talos_net"]
    # Hand calculations: 450/23 = 19.565217391; 500/23 = 21.739130435.
    assert adjusted["usd_per_boe"]["range"] == pytest.approx(
        [19.565217391, 21.739130435]
    )
    assert adjusted["usd_per_boe"]["status"] == "EVALUATED_RANGE"
    assert all(
        r["value"] is None for r in package["metrics"]["bases"]["ridgewood"].values()
    )


def test_asset_claims_and_lifecycle_presentation_follow_input(tmp_path):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    asset = next(a for a in data["assets"] if a["name"] == "Coulomb")
    asset.update(
        host="Synthetic host",
        host_citation={"source_id": "shell_release", "locator": "synthetic host"},
        field_concept=None,
        field_concept_citation=None,
        transaction_membership_status="NOT_EVALUATED",
        transaction_membership_citation=None,
        transaction_membership_reason="Synthetic membership withdrawal",
    )
    data["lifecycle_title"] = "Synthetic lifecycle"
    data["lifecycle_limitation"] = "Synthetic limitation"
    package = build_package(data, ROOT)
    row = next(a for a in package["lifecycle"]["assets"] if a["name"] == "Coulomb")
    assert row["host"] == "Synthetic host"
    assert row["field_concept"] is None
    assert row["transaction_membership_status"] == "NOT_EVALUATED"
    assert row["transaction_membership_citation"] is None
    write_package(package, tmp_path, ROOT)
    text = (tmp_path / "lifecycle.html").read_text(encoding="utf-8")
    assert "Synthetic lifecycle" in text
    assert "Synthetic limitation" in text
    assert "Synthetic membership withdrawal" in text


@pytest.mark.parametrize("change", ["concept", "row", "source"])
def test_host_concept_must_match_its_parsed_catalog_row(change):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    hub = next(a for a in data["assets"] if a["kind"] == "hub")
    if change == "concept":
        hub["host_concept"] = "fpso"
    elif change == "row":
        hub["host_concept_citation"]["row_name"] = "Unknown synthetic row"
    else:
        hub["host_concept_citation"]["source_id"] = "catalog_fields"
    with pytest.raises(ValueError, match="Host concept"):
        build_package(data, ROOT)


@pytest.mark.parametrize(
    "claim", ["host", "host_concept", "field_concept", "transaction_membership"]
)
def test_input_lifecycle_claims_require_citations(claim):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    asset = next(a for a in data["assets"] if a["name"] == "Coulomb")
    if claim == "host_concept":
        asset[claim] = "semisub_fps"
    asset[claim + "_citation"] = None
    with pytest.raises(ValueError, match="Citation"):
        build_package(data, ROOT)


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_catalog_digests_survive_checkout_line_endings(tmp_path, newline):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    for source in data["sources"].values():
        if "path" not in source:
            continue
        target = tmp_path / source["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        content = (ROOT / source["path"]).read_bytes().replace(b"\r\n", b"\n")
        target.write_bytes(content.replace(b"\n", newline))
    package = build_package(data, tmp_path)
    assert (
        package["metrics"]["bases"]["talos_announced"]["usd_per_boe"]["status"]
        == "EVALUATED"
    )


def test_non_ascii_input_digest_matches_declared_canonical_domain():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    data["title"] = "Synthetic Δ lifecycle"
    expected = hashlib.sha256(
        json.dumps(
            data,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    provenance = build_package(data, ROOT)["provenance"]
    assert provenance["input_sha256"] == expected
    assert "ensure_ascii=False" in provenance["digest_domain"]


def test_report_formats_buyer_ratios_and_consideration(tmp_path):
    package = build_package(json.loads(INPUT.read_text(encoding="utf-8")), ROOT)
    write_package(package, tmp_path, ROOT)
    text = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "36.96" in text
    assert "53,125.00" in text
    assert "19.57" in text and "21.74" in text
    assert "1,700,000,000" in text
    assert "450,000,000" in text and "500,000,000" in text


def test_report_omits_cross_drive_links_with_a_reason(tmp_path, monkeypatch):
    import worldenergydata.field_development.transaction_report as report

    def different_drives(*args):
        raise ValueError("Synthetic different drives")

    monkeypatch.setattr(report.os.path, "relpath", different_drives)
    package = build_package(json.loads(INPUT.read_text(encoding="utf-8")), ROOT)
    write_package(package, tmp_path, ROOT)
    text = (tmp_path / "lifecycle.html").read_text(encoding="utf-8")
    assert "link omitted because output and repository use different drives" in text
    assert "bsee_matched" not in text


def test_retained_outputs_match_fresh_build(tmp_path):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    retained = ROOT / "reports/field_development/transactions/na_kika_coulomb"
    # Render links for the retained destination while writing only in temporary storage.
    outputs = write_package(
        build_package(data, ROOT), tmp_path, ROOT, link_base=retained
    )
    assert len(outputs) == 6
    for output in outputs:
        assert output.read_bytes() == (retained / output.name).read_bytes(), (
            "Retained output drift; rebuild with PYTHONPATH=src python "
            "scripts/field_development/build_na_kika_coulomb_transaction.py"
        )


@pytest.mark.parametrize(
    "bounds",
    [
        [],
        [1],
        [1, 2, 3],
        [2, 1],
        [None, 2],
        [True, 2],
        [-1, 2],
        ["NaN", 2],
        [1, "Infinity"],
    ],
)
def test_invalid_consideration_ranges_are_refused(bounds):
    amount = observation(None, "USD")
    amount["range"] = bounds
    with pytest.raises(ValueError):
        valuation_metrics(amount, observation(8, "boe"), observation(4, "boe/d"))


@pytest.mark.parametrize("ranged", [False, True])
def test_non_finite_ratio_cannot_receive_an_evaluated_status(ranged):
    amount = observation("1e1000", "USD")
    if ranged:
        amount.update(value=None, range=["1e1000", "2e1000"])
    with pytest.raises(ValueError, match="finite"):
        valuation_metrics(amount, observation(8, "boe"), observation(4, "boe/d"))
