"""Offline builder contracts for the field-atlas browse funnel (issue #766).

All names, identifiers and counts are synthetic fixture literals. Country counts
are independently assigned inventory examples, not measurements of real fields.
Navigation policy, pagination and page design are outside this test slice.
"""

import importlib.util
import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def atlas(monkeypatch, tmp_path):
    # The file is at <root>/tests/unit/test_field_atlas_build.py.
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "atlas_builder_contract", root / "scripts/field_atlas/build_field_atlas.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "HERE", tmp_path)
    monkeypatch.setattr(module, "ROSTER", tmp_path / "roster.json")
    monkeypatch.setattr(module, "FEED", tmp_path / "feed.json")
    monkeypatch.setattr(module, "TEMPLATE_PATH", tmp_path / "template.html")

    # Explicit answers make any lookup for a non-lifecycle record fail.
    answers = {
        "Known field": "canonical_field",
        "Known alias": "canonical_field",
        "Unregistered field": None,
    }
    registry = SimpleNamespace(resolve=Mock(side_effect=answers.__getitem__))
    monkeypatch.setattr(module, "load_fields", Mock(return_value=registry))
    monkeypatch.setattr(
        module,
        "site_nav",
        SimpleNamespace(inject_for=Mock(side_effect=lambda html, key: html)),
    )
    return module


@pytest.fixture
def country_feed():
    # Independent inventory examples: North has two entries, South has one.
    # Country badges deliberately differ from the roster's field density tier.
    return {
        "countries": [
            {
                "country": "Country South é",
                "fields": 1,
                "badge": "SAMPLE",
                "module": None,
            },
            {
                "country": "Country North",
                "fields": 2,
                "badge": "RICH",
                "module": "example_inventory",
            },
        ],
        "fields": [{"name": "Feed-only field", "density_tier": "roadmap"}],
    }


def build_embedded(atlas, roster, feed=None, *, via_main=False):
    """Run the real builder, parse both payloads and check immutable inputs."""
    atlas.ROSTER.write_text(
        json.dumps(roster, ensure_ascii=False), encoding="utf-8", newline="\n"
    )
    atlas.TEMPLATE_PATH.write_text(
        "<!doctype html><html><title>Example atlas é</title><body>\n"
        '<script id="roster" type="application/json">__ROSTER_JSON__</script>\n'
        '<script id="countries" type="application/json">__COUNTRIES_JSON__</script>\n'
        "</body></html>\n",
        encoding="utf-8",
        newline="\n",
    )
    inputs = [atlas.ROSTER, atlas.TEMPLATE_PATH]
    if feed is not None:
        atlas.FEED.write_text(
            json.dumps(feed, ensure_ascii=False), encoding="utf-8", newline="\n"
        )
        inputs.append(atlas.FEED)
    original_bytes = {path: path.read_bytes() for path in inputs}

    if via_main:
        atlas.main()
        output = (atlas.HERE / "index.html").read_bytes()
        assert b"\r\n" not in output
        html = output.decode("utf-8")
    else:
        html = atlas.build()

    assert "<title>Example atlas é</title>" in html
    assert {path: path.read_bytes() for path in inputs} == original_bytes
    if feed is None:
        assert not atlas.FEED.exists()
    assert "__ROSTER_JSON__" not in html
    assert "__COUNTRIES_JSON__" not in html
    atlas.site_nav.inject_for.assert_called_once_with(html, "atlas")
    payloads = {}
    for name in ("roster", "countries"):
        match = re.search(
            rf'<script id="{name}" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        assert match is not None
        payloads[name] = json.loads(match.group(1))
    return payloads


@pytest.mark.parametrize("via_main", [False, True], ids=["build", "main"])
def test_atlas_missing_feed_keeps_roster(atlas, via_main, capsys):
    roster = [
        {
            "name": "Example field é",
            "country": "Country North",
            "density_tier": "sample",
            "has_lifecycle": False,
        }
    ]

    embedded = build_embedded(atlas, roster, via_main=via_main)
    if via_main:
        assert "(1 fields)" in capsys.readouterr().out

    assert embedded["roster"] == [
        {
            "name": "Example field é",
            "country": "Country North",
            "density_tier": "sample",
            "has_lifecycle": False,
            "lifecycle_id": None,
        }
    ]
    assert embedded["countries"] == []
    atlas.load_fields.return_value.resolve.assert_not_called()


@pytest.mark.parametrize("with_feed", [False, True], ids=["absent-feed", "small-feed"])
def test_atlas_lifecycle_links_use_canonical_registry(atlas, country_feed, with_feed):
    roster = [
        {"name": "Known field", "has_lifecycle": True},
        {"name": "Known alias", "has_lifecycle": True},
        {"name": "Unregistered field", "has_lifecycle": True},
        {"name": "Disabled field", "has_lifecycle": False},
        {"name": "Unflagged field"},
    ]

    embedded = build_embedded(atlas, roster, country_feed if with_feed else None)

    assert embedded["roster"] == [
        {
            "name": "Known field",
            "has_lifecycle": True,
            "lifecycle_id": "canonical_field",
        },
        {
            "name": "Known alias",
            "has_lifecycle": True,
            "lifecycle_id": "canonical_field",
        },
        {
            "name": "Unregistered field",
            "has_lifecycle": True,
            "lifecycle_id": None,
        },
        {"name": "Disabled field", "has_lifecycle": False, "lifecycle_id": None},
        {"name": "Unflagged field", "lifecycle_id": None},
    ]
    atlas.load_fields.assert_called_once_with()
    assert atlas.load_fields.return_value.resolve.call_args_list == [
        (("Known field",), {}),
        (("Known alias",), {}),
        (("Unregistered field",), {}),
    ]
    assert embedded["countries"] == (country_feed["countries"] if with_feed else [])


def test_atlas_feed_preserves_country_density(atlas, country_feed):
    roster = [
        {
            "name": "Unregistered field",
            "has_lifecycle": True,
            "density_tier": "sample",
            "country": "Country North",
        }
    ]

    embedded = build_embedded(atlas, roster, country_feed)

    assert embedded["countries"] == country_feed["countries"]
    assert embedded["roster"] == [
        {
            "name": "Unregistered field",
            "has_lifecycle": True,
            "density_tier": "sample",
            "country": "Country North",
            "lifecycle_id": None,
        }
    ]
