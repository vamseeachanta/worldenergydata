"""Confidentiality regressions use digests rather than retired public wording."""

import functools
import hashlib
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RETIRED_IDENTIFIER = "ef6204f95e580471c2bf651f35d368616a61a7e577e36f7c40c896d176656e12"
RETIRED_ATTRIBUTION = "c866bbdd751ba22cd6428c1137f759b3ae9d231a53fa8a93af6b96a65c278818"
RETIRED_LEGAL_ATTRIBUTIONS = {
    "2cd558e19a4135e71e6d29c0fba2d9eb827bb114e1b24610787b8ff946f78f1e",
    "95363de81894f4be38adff9b2015ae7f85020be6471799f575050d21c66d87d5",
    "e82ddc9746b7017dc7c68d734cf0beac054808b596ff7edcb0df728cb9eebb89",
}
RETIRED_EXPANSIONS = {
    "b011b1eef5c5150a314f4e62da8c93eefeb819142d4bce61cd39a9d8d020840e",
    "016846a6779e4810e46cc22a75b6eb8668570493df69a3b80e3e1f71fc04587e",
    "6922579e6f55513e63611cbafe34eddcf735bca10adc520fd54bfdd4056f445e",
    "c870dba519f2756205430c3837a1ab7102c3143988f36655efc2285580766092",
    "d86d82c793449c331bd15eb7c620a3f5718f411acd2e2566467d5dce466013a3",
}


RETIRED_PERSONAL_ATTRIBUTIONS = {
    "1f4d6bd19d7eae59e960d69089036c99eb69d74a1a127a787ce4e6c2be90c16b",
    "4afdba30f6f5a222c56db0b1ef61776f53577fbc398ce8a1700cbddd6359ad9f",
    "a59b1da0739609cfd823420304bebb268693eade4ff3e1269fce24548c301240",
    "be43bcab40fa211cc91e981d6c7d3dedc1ac874d3b700cb3ce5aafd8bf9e4fdb",
}
REVIEWED_PUBLICATION_PATHS = [
    (
        "docs/modules/bsee/communications/email-review/reviewed/"
        "2026-07-08-project_economics-canonicalization.md"
    ),
    "docs/modules/project_economics/DEPLOYMENT-CHECKLIST.md",
    "docs/modules/project_economics/VALIDATION-REPORT.md",
    "docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md",
    "docs/research/bsee-project_economics-integration-summary.md",
    "docs/research/docs/research/project_economics-INTEGRATION-STATUS.md",
    "docs/research/docs/research/project_economics-documentation-review-summary.md",
    "docs/research/docs/research/project_economics-integration-index.md",
    "docs/research/project_economics-executive-summary.md",
    "docs/research/project_economics-implementation-plan.md",
    "docs/research/project_economics-quick-reference.md",
    "examples/project_economics_complete_workflow.py",
    "packages/worldenergydata-project_economics/src/worldenergydata/project_economics/README.md",
    (
        "packages/worldenergydata-project_economics/src/worldenergydata/"
        "project_economics/core/financial.py"
    ),
    "reports/lower_tertiary/project_economics_revision_comparison.md",
    "reports/lower_tertiary/v30_repeatability_report.md",
    "reports/lower_tertiary/wo-april-2026-validation.md",
    "scripts/build_pages.py",
    "scripts/extract_golden_baseline.py",
    "tests/unit/project_economics/validation/__init__.py",
    "tests/unit/project_economics/validation/test_against_original.py",
    "tests/unit/project_economics/validation/test_v30_determinism.py",
    "tests/unit/vessel_fleet/loaders/test_mnt_ace_fleet_loader.py",
]
PRIVATE_LOCATOR = re.compile(
    r"(?<![\w:\\])(?:/(?:home|mnt|Users)/[\w.-]+|[A-Za-z]:[\\/][\w.-]+|\\\\[\w.-]+\\)"
)


@functools.lru_cache(maxsize=32768)
def digest(text):
    return hashlib.sha256(text.lower().encode()).hexdigest()


def has_retired_wording(text):
    words = re.findall(r"[a-z]+", text.lower())
    for index, word in enumerate(words):
        if digest(word) == RETIRED_IDENTIFIER:
            return True
        for size in (1, 2):
            if digest("".join(words[index : index + size])) == RETIRED_ATTRIBUTION:
                return True
        for size in range(2, 7):
            candidate = "".join(words[index : index + size])
            if (
                len(candidate) in (18, 21, 38)
                and digest(candidate) in RETIRED_LEGAL_ATTRIBUTIONS
            ):
                return True
        window = [w for w in words[index : index + 5] if w != "and"][:4]
        reporting_window = [
            w for w in words[index : index + 6] if w not in {"and", "reporting"}
        ][:4]
        if any(
            len(candidate) == 4 and digest(" ".join(candidate)) in RETIRED_EXPANSIONS
            for candidate in (window, reporting_window)
        ):
            return True
    return False


def tracked_files():
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=True,
    )
    return [ROOT / os.fsdecode(name) for name in result.stdout.split(b"\0") if name]


def test_inventory_includes_staged_files_but_excludes_untracked_scratch(
    tmp_path, monkeypatch
):
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    subprocess.run(["git", "init", "-q", str(tmp_path)], env=env, check=True)
    staged = tmp_path / "public.txt"
    staged.write_text("Project economics\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "add", "--", staged.name], cwd=tmp_path, env=env, check=True)
    (tmp_path / "scratch.txt").write_text(
        "Temporary local notes\n", encoding="utf-8", newline="\n"
    )
    monkeypatch.setenv("GIT_DIR", str(ROOT / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(ROOT))
    monkeypatch.setenv("GIT_COMMON_DIR", str(ROOT / ".git"))
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)
    assert tracked_files() == [staged]


def test_tracked_public_text_and_paths_use_neutral_wording():
    failures = []
    for path in tracked_files():
        if not path.exists() and not path.is_symlink():
            continue
        if has_retired_wording(path.relative_to(ROOT).as_posix()):
            failures.append("path")
        if not path.is_file() or path.is_symlink() or zipfile.is_zipfile(path):
            continue
        data = path.read_bytes()
        if b"\0" not in data and has_retired_wording(
            data.decode("utf-8", errors="ignore")
        ):
            failures.append(path.relative_to(ROOT).as_posix())
    assert not failures, f"Public wording violations: {failures}"


@pytest.mark.parametrize(
    "relative_path",
    [
        "docs/data-sources/bsee/analysis/field/field_layout.md",
        "docs/data-sources/bsee/data/drilling_data_rev1.md",
        "docs/data-sources/bsee/data/well/well_count.md",
    ],
)
def test_reviewed_correspondence_uses_roles_instead_of_addresses(relative_path):
    address = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}")
    lines = (ROOT / relative_path).read_text(encoding="utf-8").splitlines()
    violations = [
        number for number, line in enumerate(lines, 1) if address.search(line)
    ]
    assert not violations, f"Address found in {relative_path} at lines {violations}"


def test_office_documents_use_neutral_wording():
    failures = []
    for path in tracked_files():
        if path.is_file() and zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for member in archive.namelist():
                    if member.endswith(".xml") and has_retired_wording(
                        archive.read(member).decode("utf-8", errors="ignore")
                    ):
                        failures.append(f"{path.relative_to(ROOT).as_posix()}:{member}")
    assert not failures, f"Office wording violations: {failures}"


def test_intervention_pdf_uses_neutral_wording():
    import pdfplumber

    with pdfplumber.open(
        ROOT / "docs/intervention-db/intervention-stats-brief.pdf"
    ) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert not has_retired_wording(text)


def test_project_economics_skill_has_one_neutral_name():
    skill = ROOT / ".claude/skills/project-economics/SKILL.md"
    assert skill.is_file()
    text = skill.read_text(encoding="utf-8")
    assert "name: project-economics\n" in text
    assert "# Project Economics Skill\n" in text
    assert not has_retired_wording(text)


def test_lock_records_use_normalized_sorted_package_names():
    import tomllib

    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    names = [package["name"] for package in lock["package"]]
    assert names == sorted(names)
    assert "worldenergydata-project-economics" in names
    assert all(name == re.sub(r"[-_.]+", "-", name).lower() for name in names)


def test_report_generator_emits_neutral_footer(tmp_path):
    from scripts.gtm import generate_project_economics_gtm_report as report

    results = [report.run_scenario(scenario) for scenario in report.SCENARIOS]
    decline, history = report.run_decline_curve_demo()
    output = tmp_path / "project-economics.html"
    report.generate_html(results, decline, history, output)
    text = output.read_text(encoding="utf-8")
    assert "Project economics (project_economics)" in text
    assert not has_retired_wording(text)


def test_intervention_renderer_emits_neutral_header(monkeypatch):
    pytest.importorskip("markdown")
    monkeypatch.syspath_prepend(str(ROOT / "docs/intervention-db"))
    import render_brief

    text = render_brief.render_html("## Overview\nPublic summary.", "2026-05-04")
    assert "GoM Subsea Well Intervention" in text
    assert not has_retired_wording(text)


def test_renderer_regression_skips_when_optional_markdown_is_absent(tmp_path):
    script = """
import importlib.abc
import sys
import pytest

class MissingMarkdown(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "markdown":
            raise ModuleNotFoundError("Optional dependency absent", name="markdown")

sys.modules.pop("markdown", None)
sys.meta_path.insert(0, MissingMarkdown())
raise SystemExit(pytest.main(sys.argv[1:]))
"""
    target = (
        f"{Path(__file__).resolve()}::test_intervention_renderer_emits_neutral_header"
    )
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            target,
            "--noconftest",
            "-o",
            "addopts=",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "Optional-dependency test failed instead of skipping"
    assert "1 skipped" in result.stdout


def test_portfolio_citations_use_neutral_publishers():
    from worldenergydata.lower_tertiary.portfolio_economics import analyze_field

    result = analyze_field("anchor")
    text = " ".join(result.citations["publisher"])
    assert "Project economics reference" in text
    assert not has_retired_wording(text)


def publication_violations(text):
    failures = []
    for number, line in enumerate(text.splitlines(), 1):
        if PRIVATE_LOCATOR.search(line):
            failures.append((number, "private locator"))
        if any(
            digest(word) in RETIRED_PERSONAL_ATTRIBUTIONS
            for word in re.findall(
                r"[a-z]+",
                re.sub(r"https?://\S+|[\w.-]+/worldenergydata", "", line.lower()),
            )
        ):
            failures.append((number, "personal attribution"))
    return failures


@pytest.mark.parametrize("relative_path", REVIEWED_PUBLICATION_PATHS)
def test_reviewed_publication_sources_use_relative_paths_and_roles(relative_path):
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    violations = publication_violations(text)
    assert not violations, f"Publication violations in {relative_path}: {violations}"


def test_publication_screen_detects_generic_locators_and_attributions(monkeypatch):
    locator = "/".join(("", "Users", "contributor", "source.txt"))
    assert {kind for _, kind in publication_violations(locator)} == {"private locator"}
    monkeypatch.setattr(
        sys.modules[__name__],
        "RETIRED_PERSONAL_ATTRIBUTIONS",
        {"7ee8a8789d5be8d2be3b35505ab433d8e7ab18a25ad4abf066a47b0bd86ce851"},
    )
    assert publication_violations("Source: contributor") == [
        (1, "personal attribution")
    ]
    assert not publication_violations(
        "Reference implementation: docs/reference/source.py"
    )


def test_report_builder_preserves_relative_reference_page_name(tmp_path, monkeypatch):
    from scripts import build_pages

    reports = tmp_path / "reports"
    source = reports / "lower_tertiary" / "reference-rig-days-validation.html"
    source.parent.mkdir(parents=True)
    source.write_text("<p>Reference basis</p>\n", encoding="utf-8", newline="\n")
    output = tmp_path / "public"
    output.mkdir()
    monkeypatch.setattr(build_pages, "REPORTS", reports)
    monkeypatch.setattr(build_pages, "PUBLIC", output)
    build_pages.build_lower_tertiary({})
    published = output / source.name
    if not published.is_file():
        pytest.fail("Reference page was not copied")
    assert published.read_bytes() == source.read_bytes()
    build_pages.build_index()
    landing = (output / "index.html").read_text(encoding="utf-8")
    if f'href="{source.name}"' not in landing:
        pytest.fail("Reference page link is absent from the landing page")
    from scripts.maintenance import classify_report_inventory

    rows = classify_report_inventory.classify_tree(tmp_path)
    selected = next(
        row for row in rows if row["path"] == source.relative_to(tmp_path).as_posix()
    )
    assert selected["classification"] == "current"


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        (b"Document\n\n", b"Document\n", True),
        (b"Document\n\n", b"Changed\n", False),
        (b"First\r\nSecond\r\n", b"First\nSecond\n", False),
    ],
)
def test_eof_format_proof_rejects_content_and_line_ending_changes(
    before, after, expected
):
    assert eof_only_change(before, after) is expected


def eof_only_change(before, after):
    return after == before.rstrip(b"\r\n") + b"\n"


def verify_eof_formatting(snapshot_path, relative_paths):
    import json

    if not relative_paths:
        raise SystemExit("No formatting targets supplied")
    snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    for relative_path in relative_paths:
        target = ROOT / relative_path
        if Path(relative_path).is_absolute() or not target.resolve().is_relative_to(
            ROOT
        ):
            raise SystemExit("Formatting target is outside the repository")
        before = bytes.fromhex(snapshot[relative_path])
        if not eof_only_change(before, target.read_bytes()):
            raise SystemExit("Changes beyond end-of-file formatting")
    print(f"Verified EOF formatting only for {len(relative_paths)} files")


if __name__ == "__main__":
    verify_eof_formatting(sys.argv[1], sys.argv[2:])
