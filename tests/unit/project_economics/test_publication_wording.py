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
    staged.write_text("Project economics\n")
    subprocess.run(["git", "add", "--", staged.name], cwd=tmp_path, env=env, check=True)
    (tmp_path / "scratch.txt").write_text("Temporary local notes\n")
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


def test_office_documents_use_neutral_wording():
    failures = []
    for path in tracked_files():
        if path.is_file() and zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for member in archive.namelist():
                    if member.endswith(".xml") and has_retired_wording(
                        archive.read(member).decode("utf-8", errors="ignore")
                    ):
                        failures.append(f"{path.relative_to(ROOT)}:{member}")
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
    text = skill.read_text()
    assert "name: project-economics\n" in text
    assert "# Project Economics Skill\n" in text
    assert not has_retired_wording(text)


def test_lock_records_use_normalized_sorted_package_names():
    import tomllib

    lock = tomllib.loads((ROOT / "uv.lock").read_text())
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
    text = output.read_text()
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
