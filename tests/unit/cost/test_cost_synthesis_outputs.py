"""Report and input integrity tests; expected arithmetic is synthetic and manual."""

import csv
import hashlib
import json
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import pytest

from worldenergydata.cost.portfolio.reporting import build, load_portfolio

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "data/modules/cost/examples/portfolio_synthesis.json"


@pytest.mark.parametrize(
    "requirement_id", ["req-host", "unallocated", "unreconciled_variance"]
)
@pytest.mark.parametrize("target_kind", ["point", "closed-range", "open-range"])
def test_csv_quantity_kinds_distinguish_requirements_from_buckets(
    tmp_path, requirement_id, target_kind
):
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    project = value["projects"][0]
    project["requirement_ids"][0] = requirement_id
    project["contributions"][0]["requirement_ids"][0] = requirement_id
    for scenario in value["scenarios"]:
        scenario["shares"][requirement_id] = scenario["shares"].pop("req-host")
    cases = [("point", Decimal("100"), Decimal("60"), Decimal("30"), Decimal("10"))]
    if target_kind != "point":
        is_open = target_kind == "open-range"
        project["total"] = {
            "low": "90",
            "high": "110",
            "low_open": is_open,
            "high_open": is_open,
        }
        cases = [
            ("lower-bound", Decimal("90"), Decimal("54"), Decimal("27"), Decimal("9")),
            (
                "upper-bound",
                Decimal("110"),
                Decimal("66"),
                Decimal("33"),
                Decimal("11"),
            ),
        ]
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    build(path, tmp_path / "report")
    with (tmp_path / "report/project_cost_map.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert {r["quantity_kind"] for r in rows} == {
        "project_metric",
        "award",
        "requirement",
        "unallocated",
        "unreconciled_variance",
    }
    assert all(
        r["quantity_kind"] == "project_metric" for r in rows if not r["identity"]
    )
    assert all(
        r["quantity_kind"] == "award"
        for r in rows
        if r["derivation"] == "observed" and r["identity"]
    )
    joint = [r for r in rows if r["view"] == "scn-reference"]
    # 100*(.6,.3,.1)=(60,30,10); 90*(.6,.3,.1)=(54,27,9);
    # 110*(.6,.3,.1)=(66,33,11). Each variance is target minus those three = 0.
    for case, target, requirement, wells, unallocated in cases:
        group = [r for r in joint if r["allocation_case"] == case]
        assert len(group) == 4
        assert len({(r["quantity_kind"], r["identity"]) for r in group}) == 4
        amounts = {
            (r["quantity_kind"], r["identity"]): Decimal(r["low"]) for r in group
        }
        assert amounts == {
            ("requirement", requirement_id): requirement,
            ("requirement", "req-wells"): wells,
            ("unallocated", "unallocated"): unallocated,
            ("unreconciled_variance", "unreconciled_variance"): Decimal("0"),
        }
        assert sum(amounts.values()) == target
        assert all(Decimal(r["high"]) == Decimal(r["low"]) for r in group)


@pytest.mark.parametrize("numeric_field", ["amount", "shares", "quantum"])
def test_numeric_json_preserves_exact_decimal_accounting(tmp_path, numeric_field):
    """100 - 0.1 = 99.90; .6 + .3 + .1 = 1; quantum .01 divides 100."""
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["projects"][0]["contributions"][0]["amount"] = {"low": "0.1", "high": "0.1"}
    if numeric_field == "amount":
        value["projects"][0]["contributions"][0]["amount"] = {"low": 0.1, "high": 0.1}
    elif numeric_field == "shares":
        for scenario in value["scenarios"]:
            scenario["shares"] = {k: float(v) for k, v in scenario["shares"].items()}
            scenario["unallocated_share"] = 0.1
    else:
        value["quantum"] = 0.01
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    build(path, tmp_path / "report")
    with (tmp_path / "report/project_cost_map.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    residual = next(r for r in rows if r["view"] == "residual")
    assert (Decimal(residual["low"]), Decimal(residual["high"])) == (
        Decimal("99.90"),
        Decimal("99.90"),
    )
    manifest = json.loads(
        (tmp_path / "report/cost_synthesis_manifest.v3.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["decimal_policy"]["output_quantum"] == "0.01"
    assert manifest["scenarios"][0]["shares"]["req-host"] == "0.6"
    assert manifest["scenarios"][0]["unallocated_share"] == "0.1"


@pytest.mark.parametrize(
    "low_open,high_open", [(False, False), (True, False), (False, True), (True, True)]
)
def test_ranged_allocation_cases_retain_target_and_limits(
    tmp_path, low_open, high_open
):
    """90*.6=54 and 110*.6=66 belong to distinct conserving boundary cases."""
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["projects"][0]["total"] = {
        "low": "90",
        "high": "110",
        "low_open": low_open,
        "high_open": high_open,
    }
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    _, results = load_portfolio(path)
    allocations = [
        a for a in results[0].allocations if a.scenario_id == "scn-reference"
    ]
    assert [
        (a.case_id, a.total, a.target_endpoint, a.target_open, a.limiting)
        for a in allocations
    ] == [
        ("lower-bound", Decimal(90), "low", low_open, True),
        ("upper-bound", Decimal(110), "high", high_open, True),
    ]
    build(path, tmp_path / "report")
    with (tmp_path / "report/project_cost_map.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    joint = [r for r in rows if r["view"] == "scn-reference"]
    assert len({(r["allocation_case"], r["identity"]) for r in joint}) == 8
    for case, target, endpoint, is_open, host in [
        ("lower-bound", "90", "low", low_open, "54.00"),
        ("upper-bound", "110", "high", high_open, "66.00"),
    ]:
        group = [r for r in joint if r["allocation_case"] == case]
        assert len(group) == 4
        assert {
            (r["target_total"], r["target_endpoint"], r["target_open"], r["limiting"])
            for r in group
        } == {(target, endpoint, str(is_open).lower(), "true")}
        assert sum(Decimal(r["low"]) for r in group) == Decimal(target)
        assert next(r["low"] for r in group if r["identity"] == "req-host") == host

    class Summaries(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_summary = False
            self.rows = []

        def handle_starttag(self, tag, attrs):
            if tag == "summary":
                self.in_summary = True

        def handle_endtag(self, tag):
            if tag == "summary":
                self.in_summary = False

        def handle_data(self, text):
            if self.in_summary:
                self.rows.append(text)

    parser = Summaries()
    parser.feed((tmp_path / "report/project_cost_map.html").read_text(encoding="utf-8"))
    summaries = [s for s in parser.rows if "scn-reference" in s]
    assert len(summaries) == 2
    for summary, case, endpoint, is_open in zip(
        summaries,
        ["lower-bound", "upper-bound"],
        ["low", "high"],
        [low_open, high_open],
    ):
        assert case in summary and "limiting case" in summary
        assert f"{endpoint} endpoint {'open' if is_open else 'closed'}" in summary


def test_point_allocation_case_is_not_a_limiting_endpoint(tmp_path):
    _, results = load_portfolio(EXAMPLE)
    assert all(
        (a.case_id, a.total, a.target_endpoint, a.target_open, a.limiting)
        == ("point", Decimal(100), "point", False, False)
        for a in results[0].allocations
    )
    build(EXAMPLE, tmp_path / "report")
    with (tmp_path / "report/project_cost_map.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if row["derivation"] == "observed":
            assert [
                row[k]
                for k in (
                    "allocation_case",
                    "target_total",
                    "target_endpoint",
                    "target_open",
                    "limiting",
                )
            ] == [""] * 5
        else:
            assert (
                row["allocation_case"],
                row["target_total"],
                row["target_endpoint"],
                row["target_open"],
                row["limiting"],
            ) == ("point", "100", "point", "false", "false")
    assert "limiting case" not in (tmp_path / "report/project_cost_map.html").read_text(
        encoding="utf-8"
    )


def test_html_retains_exact_target_totals_for_close_endpoints(tmp_path):
    """One-decimal display would render both targets as [100.0, 100.1]."""
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["projects"][0]["total"] = {"low": "100.01", "high": "100.02"}
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    build(path, tmp_path / "report")
    html = (tmp_path / "report/project_cost_map.html").read_text(encoding="utf-8")
    assert "target 100.01" in html
    assert "target 100.02" in html


def test_deterministic_cost_map_and_manifest(tmp_path):
    """100-(20..30)=70..80; scenarios allocate 60+30+10 and 20+70+10."""
    first = build(EXAMPLE, tmp_path / "first")
    second = build(EXAMPLE, tmp_path / "second")
    assert first == second
    html = (tmp_path / "first/project_cost_map.html").read_text(encoding="utf-8")
    assert ">req-host</a>" in html
    assert ">Project total</a>" in html
    assert "observed" in html and "inferred" in html
    assert "NOT_EVALUATED" not in html
    assert "70.0" in html and "80.0" in html
    assert "Revision history" in html
    csv = (tmp_path / "first/project_cost_map.csv").read_text(encoding="utf-8")
    assert "residual_fraction" in csv
    assert "allocated" in csv and "modeled" in csv
    manifest = json.loads(
        (tmp_path / "first/cost_synthesis_manifest.v3.json").read_text(encoding="utf-8")
    )
    assert manifest["contract_version"] == "3.0.0"
    assert manifest["evidence_status"] == "synthetic"
    for item in manifest["outputs"]:
        assert (
            item["sha256"]
            == hashlib.sha256(
                (tmp_path / "first" / item["path"]).read_bytes()
            ).hexdigest()
        ), "Rebuild with scripts/cost/build_project_cost_map.py"


def test_production_input_requires_pinned_manifest(tmp_path):
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["evidence_status"] = "portfolio"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="manifest"):
        load_portfolio(path)


def test_html_escaping_and_opaque_links(tmp_path):
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["projects"][0]["source"] = '<script>alert("test")</script>'
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    build(path, tmp_path / "report")
    html = (tmp_path / "report/project_cost_map.html").read_text(encoding="utf-8")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_duplicate_json_keys_and_projects_rejected(tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"projects":[],"projects":[]}', encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_portfolio(path)
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["projects"] *= 2
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_portfolio(path)


def test_no_scenarios_surfaces_not_evaluated(tmp_path):
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["scenarios"] = []
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    build(path, tmp_path / "report")
    html = (tmp_path / "report/project_cost_map.html").read_text(encoding="utf-8")
    assert "NOT_EVALUATED" in html
    assert "unallocated unavailable" in html


def test_pinned_portfolio_manifest_and_tamper_detection(tmp_path):
    """Pins are independent hashlib digests; changed source bytes must fail."""
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["evidence_status"] = "portfolio"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    schema = tmp_path / "schema.json"
    schema.write_text(
        '{"description":"synthetic integrity fixture"}', encoding="utf-8", newline="\n"
    )

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "contract_version": "2.0.0",
                "inputs": [{"path": "input.json", "sha256": digest(path)}],
                "schema": {"path": "schema.json", "sha256": digest(schema)},
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    kwargs = {
        "manifest": manifest,
        "manifest_sha256": digest(manifest),
        "data_root": tmp_path,
    }
    data, results = load_portfolio(path, **kwargs)
    assert data["evidence_status"] == "portfolio"
    assert results[0].eligible.low == 20
    schema.write_text("{}", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="input digest"):
        load_portfolio(path, **kwargs)


def test_manifest_paths_cannot_escape_root(tmp_path):
    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["evidence_status"] = "portfolio"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "contract_version": "2.0.0",
                "inputs": [],
                "schema": {"path": "../outside", "sha256": "unused"},
            }
        ),
        encoding="utf-8",
        newline="\n",
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

    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    other = deepcopy(value["projects"][0])
    other["project_id"] = "prj-other"
    value["projects"].append(other)
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
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

    value = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    value["projects"][0]["project_id"] = "prj-demo space"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
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
    parser.feed((tmp_path / "report/project_cost_map.html").read_text(encoding="utf-8"))
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
