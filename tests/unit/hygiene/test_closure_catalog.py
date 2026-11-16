"""Offline catalog-resolution contracts for closed-issue claims (#368)."""

import sys
from importlib import import_module
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "hygiene"))

import verify_recent_closures as verifier  # noqa: E402


@pytest.fixture
def catalog():
    return import_module("closure_catalog")


def write_catalog(root, entries):
    path = root / "catalog.yml"
    path.write_text(
        yaml.safe_dump({"modules": {"sample": {"datasets": entries}}}),
        encoding="utf-8",
    )
    return path


def issue(body):
    return verifier.IssueRef(number=368, title="Catalog resolution", body=body)


def test_present_missing_and_uncatalogued_are_distinct(catalog, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/present.csv").touch()
    path = write_catalog(
        tmp_path, [{"path": "data/present.csv"}, {"path": "data/absent.csv"}]
    )
    checker = catalog.make_catalog_checker(path, tmp_path)
    assert checker("data/present.csv") == "present"
    assert checker("data/absent.csv") == "missing_in_allowed_root"
    assert checker("data/other.csv") == "not_catalogued"
    assert path.exists()  # Catalog presence does not establish data presence.


@pytest.mark.parametrize(
    "payload",
    [
        "",
        "[]",
        "modules: []",
        "modules: {sample: []}",
        "modules: {sample: {}}",
        "modules: {sample: {datasets: {}}}",
        "modules: {sample: {datasets: [null]}}",
        "modules: {sample: {datasets: [{path: 2}]}}",
        "modules: {sample: {datasets: [{path: ' '}]}}",
        "modules: {sample: {datasets: [{}]}}",
        "modules: [",
        "!!python/object/apply:os.system ['false']",
    ],
)
def test_invalid_catalog_is_an_error(catalog, tmp_path, payload):
    path = tmp_path / "catalog.yml"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(catalog.CatalogError):
        catalog.make_catalog_checker(path, tmp_path)


def test_missing_catalog_and_empty_datasets(catalog, tmp_path):
    with pytest.raises(catalog.CatalogError):
        catalog.make_catalog_checker(tmp_path / "absent.yml", tmp_path)
    checker = catalog.make_catalog_checker(write_catalog(tmp_path, []), tmp_path)
    assert checker("data/absent.csv") == "not_catalogued"


def test_duplicate_entries_are_deterministic(catalog, tmp_path):
    entry = {"path": "data/item.csv", "format": "csv"}
    checker = catalog.make_catalog_checker(
        write_catalog(tmp_path, [entry, dict(entry)]), tmp_path
    )
    assert checker("data/item.csv") == "missing_in_allowed_root"
    checker = catalog.make_catalog_checker(
        write_catalog(tmp_path, [entry, {**entry, "format": "json"}]), tmp_path
    )
    assert checker("data/item.csv") == "conflicting_duplicate"


@pytest.mark.parametrize(
    "value",
    [
        "../outside",
        "data/../../outside",
        "/data/x",
        "",
        ".",
        "data/$X",
        "data/*.csv",
        "C:\\data\\x",
    ],
)
def test_invalid_claim_never_inspects_filesystem(catalog, tmp_path, value, monkeypatch):
    checker = catalog.make_catalog_checker(write_catalog(tmp_path, []), tmp_path)

    def unexpected(*args, **kwargs):
        pytest.fail("Invalid claims must not inspect targets")

    monkeypatch.setattr(Path, "lstat", unexpected)
    assert checker(value) == "invalid_claim"


def test_links_are_contained_before_inspecting_external_targets(
    catalog, tmp_path, monkeypatch
):
    repo, outside = tmp_path / "repo", tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    (outside / "secret.csv").touch()
    (repo / "escape").symlink_to(outside, target_is_directory=True)
    (repo / "dangling").symlink_to(tmp_path / "unavailable")
    # A second external link must never be followed, even if it points back in.
    (outside / "back").symlink_to(repo)
    checker = catalog.make_catalog_checker(
        write_catalog(
            repo,
            [
                {"path": p}
                for p in ["escape/secret.csv", "escape/back/catalog.yml", "dangling"]
            ],
        ),
        repo,
    )
    original = Path.lstat

    def contained_only(path, *args, **kwargs):
        assert path.is_relative_to(repo)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", contained_only)
    assert checker("escape/secret.csv") == "outside_allowed_root"
    assert checker("escape/back/catalog.yml") == "outside_allowed_root"
    assert checker("dangling") == "outside_allowed_root"


def test_internal_links_dangling_links_and_loops(catalog, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/item.csv").touch()
    (tmp_path / "alias").symlink_to("data", target_is_directory=True)
    (tmp_path / "dangling").symlink_to("absent")
    (tmp_path / "loop").symlink_to("loop")
    checker = catalog.make_catalog_checker(
        write_catalog(
            tmp_path, [{"path": p} for p in ["alias/item.csv", "dangling", "loop"]]
        ),
        tmp_path,
    )
    assert checker("alias/item.csv") == "present"
    assert checker("dangling") == "missing_in_allowed_root"
    assert checker("loop") == "resolution_error"


@pytest.mark.parametrize("mark", ["x", "X", " "])
def test_explicit_grammar_excludes_ordinary_path_checks(mark):
    calls = []

    def unexpected(path):
        pytest.fail("Catalog claim must not invoke ordinary path checking")

    def check(path):
        calls.append(path)
        return "missing_in_allowed_root"

    finding = verifier.analyze_issue(
        issue(f"- [{mark}] Catalog entry resolves: `data/item.csv`"),
        unexpected,
        catalog_checker=check,
    )
    assert calls == ["data/item.csv"]
    assert finding.catalog_results == (("data/item.csv", "missing_in_allowed_root"),)
    assert finding.missing_paths == ()
    assert finding.has_drift
    assert bool(finding.unchecked_boxes) is (mark == " ")


@pytest.mark.parametrize(
    "claim",
    [
        "Catalog entry resolves: `data/item.csv` and more",
        "Catalog entries work: `data/item.csv`",
        "Catalog entry resolves: `../outside`",
        "Catalog entry resolves: `data/item.csv; false`",
    ],
)
def test_unsupported_catalog_claim_is_unverified(claim):
    def unexpected(path):
        pytest.fail("Unsupported claim must not be executed or checked")

    finding = verifier.analyze_issue(
        issue(f"- [x] {claim}"), unexpected, catalog_checker=unexpected
    )
    assert finding.catalog_results == ((claim, "invalid_claim"),)
    assert finding.has_drift


def test_opt_in_and_ordinary_mentions_preserve_default_behavior():
    claim = "Catalog entry resolves: `data/item.csv`"
    finding = verifier.analyze_issue(issue(f"- [x] {claim}"), lambda path: True)
    assert finding.catalog_results == (("data/item.csv", "unverified"),)
    assert finding.has_drift
    finding = verifier.analyze_issue(
        issue("- [x] Created `data/catalog.csv`"), lambda path: True
    )
    assert finding.catalog_results == ()
    assert not finding.has_drift


def test_cli_catalog_selection_and_report(tmp_path, monkeypatch, capsys):
    path = write_catalog(tmp_path, [{"path": "data/absent.csv"}])
    monkeypatch.setattr(
        verifier,
        "fetch_recent_closed_issues",
        lambda *args: [issue("- [x] Catalog entry resolves: `data/absent.csv`")],
    )
    args = ["--repo-root", str(tmp_path), "--catalog", path.name, "--no-report"]
    assert verifier.main(args) == 1
    report = capsys.readouterr().out
    assert "Catalog: `catalog.yml`" in report
    assert "missing_in_allowed_root" in report
    assert "Availability is local to the allowed root" in report
    assert "unverified" in report
    (tmp_path / "data").mkdir()
    (tmp_path / "data/absent.csv").touch()
    assert verifier.main(args) == 0
    assert "Catalog: `catalog.yml`" in capsys.readouterr().out


def test_cli_rejects_missing_or_external_catalog_before_fetch(
    tmp_path, monkeypatch, capsys
):
    def unexpected(*args):
        pytest.fail("Invalid catalog must fail before fetching issues")

    monkeypatch.setattr(verifier, "fetch_recent_closed_issues", unexpected)
    for selection in ["absent.yml", "../catalog.yml"]:
        assert (
            verifier.main(
                ["--repo-root", str(tmp_path), "--catalog", selection, "--no-report"]
            )
            == 2
        )
        assert "ERROR: catalog" in capsys.readouterr().err


def test_link_target_parent_segments_do_not_hide_external_hops(catalog, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "external").symlink_to(outside, target_is_directory=True)
    (repo / "escape").symlink_to("external/../catalog.yml")
    (repo / "data").mkdir()
    (repo / "internal").symlink_to("data/../catalog.yml")
    checker = catalog.make_catalog_checker(
        write_catalog(repo, [{"path": "escape"}, {"path": "internal"}]), repo
    )
    assert checker("escape") == "outside_allowed_root"
    assert checker("internal") == "present"


def test_catalog_file_symlink_cannot_escape(catalog, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    external = write_catalog(tmp_path, [])
    (repo / "catalog.yml").symlink_to(external)
    with pytest.raises(catalog.CatalogError):
        catalog.make_catalog_checker(repo / "catalog.yml", repo)


def test_inaccessible_target_is_unverified(catalog, tmp_path, monkeypatch):
    checker = catalog.make_catalog_checker(
        write_catalog(tmp_path, [{"path": "data/item.csv"}]), tmp_path
    )

    def denied(path):
        raise PermissionError("test denial")

    monkeypatch.setattr(Path, "lstat", denied)
    assert checker("data/item.csv") == "resolution_error"


def test_catalog_claims_are_ordered_deduplicated_and_not_commands():
    calls = []
    claim = "- [x] Catalog entry resolves: `./data/item.csv`"
    finding = verifier.analyze_issue(
        issue(claim + "\n" + claim),
        lambda path: False,
        catalog_checker=lambda path: calls.append(path) or "present",
    )
    assert finding.catalog_results == (("data/item.csv", "present"),)
    assert not finding.has_drift
    assert calls == ["data/item.csv"]


def test_non_checkbox_catalog_mentions_are_ordinary_paths():
    finding = verifier.analyze_issue(
        issue("Catalog entry resolves: `data/item.csv`"), lambda path: False
    )
    assert finding.catalog_results == ()
    assert finding.missing_paths == ("data/item.csv",)


def test_cli_catalog_selection_requires_literal_relative_path(
    tmp_path, monkeypatch, capsys
):
    path = write_catalog(tmp_path, [])

    def unexpected(*args):
        pytest.fail("Nonliteral catalog selection must fail before fetching")

    monkeypatch.setattr(verifier, "fetch_recent_closed_issues", unexpected)
    for selection in [str(path), "data/../catalog.yml"]:
        assert (
            verifier.main(
                ["--repo-root", str(tmp_path), "--catalog", selection, "--no-report"]
            )
            == 2
        )
        assert "ERROR: catalog" in capsys.readouterr().err


def test_parent_segment_after_regular_file_does_not_resolve(catalog, tmp_path):
    (tmp_path / "file").touch()
    (tmp_path / "link").symlink_to("file/../catalog.yml")
    (tmp_path / "escape").symlink_to("../outside")
    checker = catalog.make_catalog_checker(
        write_catalog(tmp_path, [{"path": "link"}, {"path": "escape"}]), tmp_path
    )
    assert checker("link") == "missing_in_allowed_root"
    assert checker("escape") == "outside_allowed_root"
