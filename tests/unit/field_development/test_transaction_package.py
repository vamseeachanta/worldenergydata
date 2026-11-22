"""Package integration, catalog qualification and deterministic report readback."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from worldenergydata.field_development.transaction_package import (
    build_package,
)
from worldenergydata.field_development.transaction_report import write_package

ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / "data/modules/offshore_assets/transactions/na_kika_coulomb.json"


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
    rows = build_package(data, ROOT)["lifecycle"]["assets"]
    assert all(row["lifecycle_status"] == "NOT_EVALUATED" for row in rows)


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
            assert citation["source_id"] in ("shell_release", "talos_release")
            assert citation["locator"]
            assert data["sources"][citation["source_id"]]["access"] == "available"
        else:
            assert citation is None
    assert supported == 6


def test_source_digest_mismatch_refused(tmp_path):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    copied = copy.deepcopy(data)
    _synthetic_catalogs(copied, tmp_path)
    copied["sources"]["catalog_fields"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="digest"):
        build_package(copied, tmp_path)


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
    assert roster["Na Kika"]["host_concept"] is None
    assert roster["Coulomb"]["field_concept"] == "subsea_tieback"
    assert roster["Coulomb"]["catalog_host_concept"] is None
    assert roster["Herschel"]["generated_page_status"] == "NOT_EVALUATED"
    assert roster["Herschel Expansion"]["lifecycle_status"] == "NOT_EVALUATED"
    assert roster["East Anstey"]["transaction_membership_status"] == "NOT_EVALUATED"


def test_block_crosswalk_never_becomes_field_economics_readiness():
    package = build_package(json.loads(INPUT.read_text(encoding="utf-8")), ROOT)
    rows = {row["name"]: row for row in package["economics_readiness"]["fields"]}
    assert rows["Coulomb"]["block_match"] is False
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
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
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


def _synthetic_catalogs(data, root):
    contents = {
        "catalog_fields": "FIELD_NAME,DISCOVERY_DATE,PRODUCTION_START\nSynthetic,2001,2002\n",
        "catalog_host": "VESSEL_NAME,FACILITY_TYPE\nSynthetic,SemiSub\n",
        "catalog_crosswalk": "og_field_name,host_concept,bsee_block_code,matched\nSynthetic,semisub_fps,SY001,1\n",
    }
    for source_id, content in contents.items():
        path = root / (source_id + ".csv")
        path.write_bytes(content.encode("utf-8"))
        data["sources"][source_id] = {
            "path": path.name,
            "access": "available",
            "optional": True,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "digest_domain": "UTF-8 text; CRLF normalized to LF",
        }
    hub = next(a for a in data["assets"] if a["kind"] == "hub")
    hub.update(
        host_concept="semisub_fps",
        host_concept_citation={
            "source_id": "catalog_host",
            "row_name": "Synthetic",
            "locator": "synthetic row",
        },
    )


@pytest.mark.parametrize("change", ["concept", "row", "source"])
def test_host_concept_must_match_its_parsed_catalog_row(change, tmp_path):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    _synthetic_catalogs(data, tmp_path)
    hub = next(a for a in data["assets"] if a["kind"] == "hub")
    if change == "concept":
        hub["host_concept"] = "fpso"
    elif change == "row":
        hub["host_concept_citation"]["row_name"] = "Unknown synthetic row"
    else:
        hub["host_concept_citation"]["source_id"] = "catalog_fields"
    with pytest.raises(ValueError, match="Host concept"):
        build_package(data, tmp_path)


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
    _synthetic_catalogs(data, tmp_path)
    for source in data["sources"].values():
        if "path" not in source:
            continue
        target = tmp_path / source["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        content = target.read_bytes().replace(b"\r\n", b"\n")
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
            indent=2,
        ).encode("utf-8")
        + b"\n"
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


def test_report_omits_catalog_links_with_a_reason(tmp_path):
    package = build_package(json.loads(INPUT.read_text(encoding="utf-8")), ROOT)
    write_package(package, tmp_path, ROOT)
    text = (tmp_path / "lifecycle.html").read_text(encoding="utf-8")
    assert "field-report links are withheld pending redistribution review" in text
    assert "bsee_matched" not in text


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_retained_outputs_match_fresh_build(tmp_path, newline):
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    retained = ROOT / "reports/field_development/transactions/na_kika_coulomb"
    # Render links for the retained destination while writing only in temporary storage.
    outputs = write_package(
        build_package(data, ROOT), tmp_path, ROOT, link_base=retained
    )
    assert len(outputs) == 6
    for output in outputs:
        checkout = tmp_path / ("checkout-" + output.name)
        checkout.write_bytes(
            (retained / output.name)
            .read_bytes()
            .replace(b"\r\n", b"\n")
            .replace(b"\n", newline)
        )
        assert b"\r" not in output.read_bytes()
        assert output.read_bytes() == checkout.read_bytes().replace(b"\r\n", b"\n"), (
            "Retained output drift; rebuild with PYTHONPATH=src python "
            "scripts/field_development/build_na_kika_coulomb_transaction.py"
        )
