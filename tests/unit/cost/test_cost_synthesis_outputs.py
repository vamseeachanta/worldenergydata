"""Report and input integrity tests; expected arithmetic is synthetic and manual."""

import hashlib
import json
from pathlib import Path

import pytest

from worldenergydata.cost.portfolio.reporting import build, load_portfolio

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "data/modules/cost/examples/portfolio_synthesis.json"


def test_deterministic_cost_map_and_manifest(tmp_path):
    """100-(20..30)=70..80; scenarios allocate 60+30+10 and 20+70+10."""
    first = build(EXAMPLE, tmp_path / "first")
    second = build(EXAMPLE, tmp_path / "second")
    assert first == second
    html = (tmp_path / "first/project_cost_map.html").read_text()
    assert ">req-host</a>" in html
    assert ">Project total</a>" in html
    assert "observed" in html and "inferred" in html
    assert "NOT_EVALUATED" not in html
    assert "70.0" in html and "80.0" in html
    assert "Revision history" in html
    csv = (tmp_path / "first/project_cost_map.csv").read_text()
    assert "residual_fraction" in csv
    assert "allocated" in csv and "modeled" in csv
    manifest = json.loads(
        (tmp_path / "first/cost_synthesis_manifest.v3.json").read_text()
    )
    assert manifest["contract_version"] == "3.0.0"
    assert manifest["evidence_status"] == "synthetic"
    for item in manifest["outputs"]:
        assert (
            item["sha256"]
            == hashlib.sha256(
                (tmp_path / "first" / item["path"]).read_bytes()
            ).hexdigest()
        )


def test_production_input_requires_pinned_manifest(tmp_path):
    value = json.loads(EXAMPLE.read_text())
    value["evidence_status"] = "portfolio"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="manifest"):
        load_portfolio(path)


def test_html_escaping_and_opaque_links(tmp_path):
    value = json.loads(EXAMPLE.read_text())
    value["projects"][0]["source"] = '<script>alert("test")</script>'
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value))
    build(path, tmp_path / "report")
    html = (tmp_path / "report/project_cost_map.html").read_text()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_duplicate_json_keys_and_projects_rejected(tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"projects":[],"projects":[]}')
    with pytest.raises(ValueError, match="duplicate"):
        load_portfolio(path)
    value = json.loads(EXAMPLE.read_text())
    value["projects"] *= 2
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="duplicate"):
        load_portfolio(path)


def test_no_scenarios_surfaces_not_evaluated(tmp_path):
    value = json.loads(EXAMPLE.read_text())
    value["scenarios"] = []
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value))
    build(path, tmp_path / "report")
    html = (tmp_path / "report/project_cost_map.html").read_text()
    assert "NOT_EVALUATED" in html
    assert "unallocated unavailable" in html


def test_pinned_portfolio_manifest_and_tamper_detection(tmp_path):
    """Pins are independent hashlib digests; changed source bytes must fail."""
    value = json.loads(EXAMPLE.read_text())
    value["evidence_status"] = "portfolio"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value))
    schema = tmp_path / "schema.json"
    schema.write_text('{"description":"synthetic integrity fixture"}')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "contract_version": "2.0.0",
                "inputs": [{"path": "input.json", "sha256": digest(path)}],
                "schema": {"path": "schema.json", "sha256": digest(schema)},
            }
        )
    )
    kwargs = {
        "manifest": manifest,
        "manifest_sha256": digest(manifest),
        "data_root": tmp_path,
    }
    data, results = load_portfolio(path, **kwargs)
    assert data["evidence_status"] == "portfolio"
    assert results[0].eligible.low == 20
    schema.write_text("{}")
    with pytest.raises(ValueError, match="input digest"):
        load_portfolio(path, **kwargs)


def test_manifest_paths_cannot_escape_root(tmp_path):
    value = json.loads(EXAMPLE.read_text())
    value["evidence_status"] = "portfolio"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "contract_version": "2.0.0",
                "inputs": [],
                "schema": {"path": "../outside", "sha256": "unused"},
            }
        )
    )
    with pytest.raises(ValueError, match="under data root"):
        load_portfolio(
            path,
            manifest=manifest,
            manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
            data_root=tmp_path,
        )


def test_shared_award_cannot_be_counted_across_projects(tmp_path):
    """A shared 20..30 award cannot contribute 40..60 across two projects."""
    from copy import deepcopy

    value = json.loads(EXAMPLE.read_text())
    other = deepcopy(value["projects"][0])
    other["project_id"] = "prj-other"
    value["projects"].append(other)
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="award.*projects"):
        load_portfolio(path)


def test_display_does_not_present_a_rounded_point_as_exact():
    """Point .03 is enclosed by displayed [0.0,0.1], never asserted as 0.0."""
    from decimal import Decimal

    from worldenergydata.cost.portfolio.intervals import Interval
    from worldenergydata.cost.portfolio.reporting import _display

    assert _display(Interval.point(Decimal(".03"))) == "[0.0, 0.1]"


def test_all_html_fragments_resolve_for_unusual_identifiers(tmp_path):
    """Fragment URLs decode percent escapes; DOM IDs must match after decoding."""
    from html.parser import HTMLParser
    from urllib.parse import unquote

    value = json.loads(EXAMPLE.read_text())
    value["projects"][0]["project_id"] = "prj-demo space"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value))
    build(path, tmp_path / "report")

    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = set()
            self.targets = []

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if "id" in attrs:
                self.ids.add(attrs["id"])
            if attrs.get("href", "").startswith("#"):
                self.targets.append(unquote(attrs["href"][1:]))

    parser = Links()
    parser.feed((tmp_path / "report/project_cost_map.html").read_text())
    assert parser.targets and set(parser.targets) <= parser.ids


def test_serialized_negative_residual_bounds():
    """At quantum .1, residual -.03 is enclosed by [-.1,0.0]."""
    from decimal import Decimal

    from worldenergydata.cost.portfolio.intervals import Interval
    from worldenergydata.cost.portfolio.reporting import _bounds

    assert _bounds(Interval.point(Decimal("-.03")), Decimal(".1"))[:2] == (
        "-0.1",
        "0.0",
    )
