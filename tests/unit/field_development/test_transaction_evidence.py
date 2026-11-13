"""Regression coverage for transaction evidence and withheld catalog inputs."""

import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from worldenergydata.field_development.transaction_package import build_package
from worldenergydata.field_development.transaction_report import write_package

ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / "data/modules/offshore_assets/transactions/na_kika_coulomb.json"
CATALOGS = ("catalog_fields", "catalog_crosswalk", "catalog_host")


def snapshot():
    return json.loads(INPUT.read_bytes())


def test_named_satellites_have_buyer_membership_and_conditional_scope():
    rows = {
        a["name"]: a for a in build_package(snapshot(), ROOT)["lifecycle"]["assets"]
    }
    for name in ("Ariel", "Fourier", "Herschel", "Kepler"):
        row = rows[name]
        assert row["transaction_membership_status"] == "SOURCE_SUPPORTED"
        citation = row["transaction_membership_citation"]
        assert citation["source_id"] == "talos_release"
        assert "four associated fields" in citation["locator"]
        assert name in citation["locator"]
        assert "preferential" in row["transaction_membership_reason"]
        assert "only Coulomb" in row["transaction_membership_reason"]
    assert (
        sum(
            r["transaction_membership_status"] == "SOURCE_SUPPORTED"
            for r in rows.values()
        )
        == 6
    )
    for name in ("East Anstey", "Herschel Expansion"):
        assert rows[name]["transaction_membership_status"] == "NOT_EVALUATED"


def test_buyer_working_interests_are_distinct_from_seller_interests():
    interests = snapshot()["transaction"]["working_interests"]
    buyer = [i for i in interests if i["basis"] == "talos_announced"]
    assert len(buyer) == 2
    assert {i["value"] for i in buyer} == {0.5, 0.25}
    assert all(i["citation"]["source_id"] == "talos_release" for i in buyer)
    satellite = next(i for i in buyer if i["value"] == 0.25)
    assert all(
        name in satellite["subject"]
        for name in ("Na Kika", "Ariel", "Fourier", "Herschel", "Kepler")
    )


def test_upside_terms_are_supported_but_payment_amount_is_unknown():
    term = snapshot()["transaction"]["terms"]["upside"]
    assert term["status"] == "NOT_EVALUATED" and term["value"] is None
    assert term["citation"]["source_id"] == "talos_release"
    assert term["sharing_fraction"] == 0.5
    assert term["effective_from"] == "closing"
    assert term["effective_through"] == "2027-12-31"
    assert term["realized_price_threshold_usd_per_bbl"] == 60


def test_unknown_term_source_is_refused():
    data = snapshot()
    data["transaction"]["terms"]["upside"]["citation"] = {
        "source_id": "unknown",
        "locator": "synthetic terms",
    }
    with pytest.raises(ValueError, match="Citation"):
        build_package(data, ROOT)


@pytest.mark.parametrize("citation", [None, {}, {"source_id": "talos_release"}])
def test_substantive_term_requires_source_and_locator(citation):
    data = snapshot()
    term = data["transaction"]["terms"]["upside"]
    term.pop("citation")
    term.pop("source_id")
    if citation is not None:
        term["citation"] = citation
    with pytest.raises(ValueError, match="Citation"):
        build_package(data, ROOT)


def test_bare_term_source_identifier_requires_citation():
    data = snapshot()
    data["transaction"]["terms"] = {
        "synthetic": {
            "status": "NOT_EVALUATED",
            "value": None,
            "reason": "Synthetic terms are unverified",
            "source_id": "talos_release",
        }
    }
    with pytest.raises(ValueError, match="Citation"):
        build_package(data, ROOT)


def test_unknown_term_without_claim_fields_remains_unevaluated():
    data = snapshot()
    term = {"status": "NOT_EVALUATED", "value": None, "reason": "Unverified"}
    data["transaction"]["terms"] = {"synthetic": term}
    assert build_package(data, ROOT)["transaction"]["terms"]["synthetic"] == term


@pytest.mark.parametrize("state", ["absent", "withheld", "missing"])
def test_optional_catalogs_do_not_block_or_publish_derived_claims(tmp_path, state):
    data = snapshot()
    for source_id in CATALOGS:
        if state == "absent":
            data["sources"].pop(source_id)
        else:
            data["sources"][source_id].update(
                optional=True, access="available" if state == "missing" else "withheld"
            )
    original = copy.deepcopy(data)
    package = build_package(data, tmp_path)
    assert data == original
    for row in package["lifecycle"]["assets"]:
        for key in (
            "catalog_discovery",
            "catalog_first_production",
            "catalog_host_concept",
            "block",
            "report_path",
            "host_concept",
        ):
            assert row[key] is None
        assert row["lifecycle_status"] == "NOT_EVALUATED"
        assert row["lifecycle_reason"]
    write_package(package, tmp_path / "out", tmp_path)
    assert "bsee_matched" not in (tmp_path / "out/lifecycle.html").read_text(
        encoding="utf-8"
    )
    assert package["metrics"]["bases"]["talos_announced"]["usd_per_boe"]["value"] > 0


def test_withheld_catalogs_are_not_read_even_when_present(monkeypatch):
    data = snapshot()
    assert all(data["sources"][key]["access"] == "withheld" for key in CATALOGS)

    def forbidden_read(*args, **kwargs):
        pytest.fail("Withheld source content must not be consumed")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    monkeypatch.setattr(Path, "open", forbidden_read)
    package = build_package(data, ROOT)
    assert all(row["host_concept"] is None for row in package["lifecycle"]["assets"])


def test_missing_required_source_raises_domain_error(tmp_path):
    data = snapshot()
    data["sources"]["catalog_fields"].update(access="available", optional=False)
    with pytest.raises(ValueError, match="Required source file is missing"):
        build_package(data, tmp_path)


def test_ratio_rows_expose_both_dates_effective_date_and_cash_basis(tmp_path):
    data = snapshot()
    package = build_package(data, ROOT)
    write_package(package, tmp_path, ROOT)
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    for basis in ("talos_announced", "talos_net"):
        for metric, row in package["metrics"]["bases"][basis].items():
            assert row["consideration_as_of"] == "2026-06-30"
            assert row["consideration_effective_date"] == "2025-07-01"
            assert row["denominator_as_of"] in ("2025-12-31", "2026-03-31")
            assert "different dates" in row["limitation"]
            if metric == "usd_per_boe":
                assert "six months" in row["limitation"]
            if basis == "talos_net":
                assert (
                    "net cash excluding the USD 42.5 million deposit"
                    in row["limitation"]
                )
    assert "Consideration as of" in page and "Denominator as of" in page
    assert (
        "six months" in page
        and "net cash excluding the USD 42.5 million deposit" in page
    )


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_input_digest_matches_binary_snapshot_after_lf_normalization(newline):
    raw = INPUT.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", newline)
    provenance = build_package(json.loads(raw), ROOT)["provenance"]
    assert "CRLF normalized to LF" in provenance["digest_domain"]
    assert (
        provenance["input_sha256"]
        == hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    )


def test_retained_input_digest_matches_binary_readback():
    retained = ROOT / "reports/field_development/transactions/na_kika_coulomb"
    provenance = json.loads((retained / "provenance.json").read_bytes())
    assert (
        provenance["input_sha256"]
        == hashlib.sha256(INPUT.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    )


def test_catalog_receipt_digests_match_committed_binary_bytes():
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR")
    }
    for key in CATALOGS:
        source = snapshot()["sources"][key]
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.autocrlf=false",
                "show",
                source["revision"] + ":" + source["path"],
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert source["digest_domain"] == "source-bytes"
        assert hashlib.sha256(result.stdout).hexdigest() == source["sha256"]


def test_stale_host_claim_is_suppressed_when_optional_source_is_missing(tmp_path):
    data = snapshot()
    data["sources"]["catalog_host"].update(optional=True, access="available")
    hub = next(a for a in data["assets"] if a["kind"] == "hub")
    hub.update(
        host_concept="semisub_fps",
        host_concept_citation={
            "source_id": "catalog_host",
            "locator": "synthetic row",
            "row_name": "Synthetic",
        },
    )
    package = build_package(data, tmp_path)
    row = package["lifecycle"]["assets"][0]
    assert row["host_concept"] is None and row["host_concept_citation"] is None
    assert row["host_concept_reason"]
    echoed = package["input_echo"]["assets"][0]
    assert echoed["host_concept"] is None


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
