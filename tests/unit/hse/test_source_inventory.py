"""The HSE source inventory is complete, consistent and matches the monthly config."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
INVENTORY = REPO / "data" / "modules" / "hse" / "source_inventory.yml"
MONTHLY = REPO / "config" / "hse" / "monthly_sources.yml"
DOC = REPO / "docs" / "hse" / "source-inventory.md"

REQUIRED = {
    "id",
    "group",
    "authority",
    "what",
    "url",
    "terms",
    "format",
    "access",
    "held",
    "refresh",
    "refresh_script",
    "last_run",
    "decision",
}
OPTIONAL = {
    "held_where",
    "held_records",
    "held_records_basis",
    "held_latest_date",
    "held_note",
}
ACCESS = {"public_bulk", "public_docs", "blocked", "login", "paid"}
HELD = {"yes", "partial", "links_only", "no"}
REFRESH = {"monthly", "manual", "none"}
CANDIDATES = {
    "bsee_incident_investigations",
    "bsee_investigation_reports",
    "bsee_safety_alerts",
    "phmsa_pipeline_incidents",
    "uscg_misle",
    "uscg_cgmix",
    "ntsb_marine",
    "imo_gisis",
    "uk_hse_offshore_statistics",
    "uk_maib",
    "havtil_rnnp",
    "nopsema",
    "emsa_emcip",
    "iogp",
    "csb",
    "iadc_isp",
}


def _sources() -> list[dict]:
    doc = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    assert doc["schema_version"] == 1
    dt.date.fromisoformat(doc["checked"])
    return doc["sources"]


def test_every_entry_has_the_required_fields_and_controlled_values() -> None:
    sources = _sources()
    ids = [s["id"] for s in sources]
    assert len(ids) == len(set(ids))
    for s in sources:
        assert REQUIRED <= set(s) <= REQUIRED | OPTIONAL, s["id"]
        assert s["access"] in ACCESS and s["held"] in HELD, s["id"]
        assert s["refresh"] in REFRESH and s["decision"] in {"owner", "none"}, s["id"]
        assert s["url"].startswith("https://"), s["id"]
        if s["last_run"] != "none" and s["last_run"] != "not confirmed":
            dt.date.fromisoformat(s["last_run"])


def test_named_candidate_sources_are_all_present() -> None:
    assert CANDIDATES <= {s["id"] for s in _sources()}


def test_login_and_paid_sources_wait_for_the_owner_and_are_not_refreshed() -> None:
    for s in _sources():
        if s["access"] in {"login", "paid"}:
            assert s["decision"] == "owner", s["id"]
            assert s["refresh"] != "monthly", s["id"]


def test_monthly_sources_point_at_hosts_in_the_monthly_config() -> None:
    config = yaml.safe_load(MONTHLY.read_text(encoding="utf-8"))
    hosts = {u.split("/")[2] for src in config["sources"] for u in src["urls"]}
    for s in _sources():
        if s["refresh"] == "monthly":
            assert s["url"].split("/")[2] in hosts, s["id"]


def test_doc_lists_every_source() -> None:
    text = DOC.read_text(encoding="utf-8")
    for s in _sources():
        assert f"`{s['id']}`" in text, s["id"]


def test_every_count_states_how_it_was_obtained() -> None:
    for s in _sources():
        if isinstance(s.get("held_records"), int):
            basis = s.get("held_records_basis", "")
            assert len(basis.split()) >= 6, s["id"]
        else:
            assert "held_records_basis" not in s, s["id"]


def test_sources_not_held_carry_no_count() -> None:
    for s in _sources():
        if s["held"] == "no":
            assert "held_records" not in s, s["id"]
