"""Independent replay must finish before promotion or report side effects."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from worldenergydata.workflow_api import bsee_pilot as P


@pytest.fixture
def orchestration(monkeypatch, tmp_path):
    """Observe orchestration without running the engine or a publication port."""
    variants = [{"id": name} for name in ("V1", "V2", "V3")]
    config = {
        "variants": variants,
        "replay_variant": "V2",
        "report_path": "report.html",
    }
    entries = [
        {
            "variant": variant,
            "projection": object(),
            "run_id": f"run-{variant['id']}",
            "output_equality": {"digest": str(index) * 64},
            "metrics": {"value": index},
            "result_hash": f"hash-{variant['id']}",
        }
        for index, variant in enumerate(variants, start=1)
    ]
    replay = dict(entries[1], projection=object())
    events = []
    records = []
    ledger = Mock()
    ledger.records.side_effect = lambda: list(records)
    ledger.eligible_run_ids.side_effect = lambda: [r["run_id"] for r in records]
    hf_port, egress = object(), object()
    visibility = {"private": True, "public": False}

    def build(config_arg, variant):
        assert config_arg is config
        events.append(("build", variant["id"]))
        if len(build_mock.call_args_list) == 4:
            if isinstance(replay_result[0], Exception):
                raise replay_result[0]
            return replay_result[0]
        return entries[variants.index(variant)]

    def compare(expected, observed):
        events.append(("compare", expected, observed))
        return assert_output_equality(expected, observed)

    def promote(projection, **kwargs):
        assert kwargs == {"hf_port": hf_port, "ledger": ledger, "egress": egress}
        entry = next(e for e in entries if e["projection"] is projection)
        events.append(("promote", entry["variant"]["id"]))
        records.append({"run_id": entry["run_id"], "state": "accepted"})
        return f"revision-{entry['variant']['id']}"

    def render(config_arg, accepted, ledger_arg):
        assert config_arg is config
        assert ledger_arg is ledger
        assert [e for e, _ in accepted] == entries
        events.append(("render",))
        return "<html>report</html>"

    replay_result = [replay]
    assert_output_equality = P.identity.assert_output_equality
    build_mock = Mock(side_effect=build)
    promote_mock = Mock(side_effect=promote)
    render_mock = Mock(side_effect=render)
    write_mock = Mock(side_effect=lambda *a, **k: events.append(("write",)))
    monkeypatch.setattr(P, "build_projection_for_variant", build_mock)
    monkeypatch.setattr(P.identity, "assert_output_equality", compare)
    monkeypatch.setattr(P, "Ledger", Mock(return_value=ledger))
    monkeypatch.setattr(P, "make_egress", Mock(return_value=egress))
    monkeypatch.setattr(P, "promote", promote_mock)
    monkeypatch.setattr(P, "render_rolling_report", render_mock)
    monkeypatch.setattr(P, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(P, "resolve_visibility", lambda c: visibility)
    monkeypatch.setattr(Path, "write_text", write_mock)
    return {
        "config": config,
        "entries": entries,
        "replay": replay_result,
        "events": events,
        "records": records,
        "port": hf_port,
        "promote": promote_mock,
        "render": render_mock,
        "write": write_mock,
        "report_path": tmp_path / "report.html",
        "visibility": visibility,
    }


@pytest.mark.parametrize(
    "failure, error",
    [
        ("run_id", P.PilotError),
        ("digest", P.identity.OutputMismatchError),
        ("construction", RuntimeError),
        ("unknown_selector", StopIteration),
        ("missing_selector", KeyError),
    ],
)
def test_replay_failure_has_no_publication_side_effects(orchestration, failure, error):
    case = orchestration
    if failure == "run_id":
        case["replay"][0] = dict(case["replay"][0], run_id="different-run")
    elif failure == "digest":
        case["replay"][0] = dict(
            case["replay"][0], output_equality={"digest": "0" * 64}
        )
    elif failure == "construction":
        case["replay"][0] = RuntimeError("independent replay construction failed")
    elif failure == "unknown_selector":
        case["config"]["replay_variant"] = "absent"
    else:
        del case["config"]["replay_variant"]

    with pytest.raises(error):
        P.run_pilot(case["config"], hf_port=case["port"], write_report=True)

    case["promote"].assert_not_called()
    assert case["records"] == []
    case["render"].assert_not_called()
    case["write"].assert_not_called()
    assert not case["report_path"].exists()


def test_success_checks_replay_before_promoting_original_entries(orchestration):
    case = orchestration
    summary = P.run_pilot(case["config"], hf_port=case["port"], write_report=True)

    assert case["events"] == [
        ("build", "V1"),
        ("build", "V2"),
        ("build", "V3"),
        ("build", "V2"),
        ("compare", "2" * 64, "2" * 64),
        ("promote", "V1"),
        ("promote", "V2"),
        ("promote", "V3"),
        ("render",),
        ("write",),
    ]
    assert all(a is b for a, b in zip(summary["entries"], case["entries"]))
    assert summary["run_ids"] == {f"V{i}": f"run-V{i}" for i in range(1, 4)}
    assert summary["revisions"] == {f"V{i}": f"revision-V{i}" for i in range(1, 4)}
    assert summary["replay"] == {
        "variant": "V2",
        "run_id": "run-V2",
        "same_run_id": True,
    }
    assert summary["accepted_count"] == 3
    assert summary["rejected_count"] == 0
    assert summary["eligible_run_ids"] == ["run-V1", "run-V2", "run-V3"]
    assert summary["ledger"] == case["records"]
    assert summary["report_path"] == str(case["report_path"])
    assert summary["report_html"] == "<html>report</html>"
    assert summary["visibility"] == case["visibility"]
    assert summary["hf_port"] is case["port"]
    assert (
        set(summary["metrics"]) == set(summary["result_hashes"]) == {"V1", "V2", "V3"}
    )
    case["write"].assert_called_once_with("<html>report</html>", encoding="utf-8")
