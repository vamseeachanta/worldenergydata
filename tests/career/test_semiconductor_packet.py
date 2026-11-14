"""Evidence-contract tests, independent of engineering calculations.

Expected outcomes are logical fixtures: a missing file cannot support a built
claim; a researched concept cannot support an implementation claim; local links
must resolve inside the repository. No material values or acceptance limits are
used. Issue #1087 acceptance criteria are the source of this contract.
"""

import copy
import importlib.util
import json
import ntpath
import os
import shlex
import subprocess
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote
from urllib.request import url2pathname

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/career/build_semiconductor_packet.py"
DATA = ROOT / "docs/career/semiconductor-packet.json"
REPORT = ROOT / "docs/reports/semiconductor-career-packet.html"


def builder():
    spec = importlib.util.spec_from_file_location("packet_builder", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def packet():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_committed_report_is_reproducible(packet):
    module = builder()
    module.validate(packet, ROOT)
    assert REPORT.read_text(encoding="utf-8") == module.render(packet, ROOT, REPORT)


@pytest.mark.parametrize("status", ["concept researched", "NOT_EVALUATED"])
def test_unbuilt_evidence_cannot_support_resume_claim(packet, status):
    packet["artifacts"][0]["status"] = status
    packet["claims"][0]["evidence"] = [packet["artifacts"][0]["id"]]
    with pytest.raises(ValueError, match="built evidence"):
        builder().validate(packet, ROOT)


def test_missing_built_file_is_rejected(packet):
    built = next(
        a for a in packet["artifacts"] if a["status"] == "hands-on artifact built"
    )
    built["paths"] = ["missing-evidence.py"]
    with pytest.raises(ValueError, match="evidence file"):
        builder().validate(packet, ROOT)


@pytest.mark.parametrize("path", ["../outside.py", "/outside.py"])
def test_evidence_must_stay_inside_repository(packet, path):
    packet["artifacts"][-1]["paths"] = [path]
    with pytest.raises(ValueError, match="repository-relative"):
        builder().validate(packet, ROOT)


def test_symlink_escape_is_rejected(packet, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("synthetic evidence", encoding="utf-8")
    (repo / "link.txt").symlink_to(outside)
    packet["artifacts"][0]["paths"] = ["link.txt"]
    with pytest.raises(ValueError, match="repository-relative"):
        builder().validate(packet, repo)


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("duplicate", "duplicate artifact"),
        ("unknown", "unknown evidence"),
        ("empty", "built evidence"),
        ("unsupported", "status"),
        ("uncited", "research source"),
        ("unsafe_source", "HTTPS"),
        ("missing_slot", "portfolio slots"),
    ],
)
def test_invalid_evidence_contracts(packet, mutation, message):
    if mutation == "duplicate":
        packet["artifacts"].append(copy.deepcopy(packet["artifacts"][0]))
    elif mutation == "unknown":
        packet["claims"][0]["evidence"] = ["unknown"]
    elif mutation == "empty":
        packet["claims"][0]["evidence"] = []
    elif mutation == "unsupported":
        packet["artifacts"][0]["status"] = "complete"
    elif mutation == "uncited":
        packet["artifacts"][0]["sources"] = []
    elif mutation == "unsafe_source":
        packet["sources"][0]["url"] = "javascript:alert('synthetic')"
    elif mutation == "missing_slot":
        packet["artifacts"] = [a for a in packet["artifacts"] if a["id"] != "fem"]
    with pytest.raises(ValueError, match=message):
        builder().validate(packet, ROOT)


def test_html_escapes_text(packet):
    packet["claims"][0]["text"] = '<script>synthetic & "quoted"</script>'
    rendered = builder().render(packet, ROOT, REPORT)
    assert "<script>" not in rendered
    assert "&lt;script&gt;synthetic &amp; &quot;quoted&quot;" in rendered


@pytest.mark.parametrize(
    "userinfo",
    ["reader", "reader:synthetic", ":synthetic", "", ":", "%72eader:%73ynthetic"],
)
def test_source_userinfo_is_rejected_before_rendering(packet, userinfo):
    packet["sources"][0]["url"] = f"https://{userinfo}@example.invalid/docs"
    module = builder()
    with pytest.raises(ValueError, match="public HTTPS"):
        module.validate(packet, ROOT)
    with pytest.raises(ValueError, match="public HTTPS"):
        module.render(packet, ROOT, REPORT)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/docs",
        "https://example.invalid/docs?contact=public%40example.invalid",
        "https://example.invalid/docs@revision",
    ],
)
def test_public_sources_without_userinfo_remain_supported(packet, url):
    packet["sources"][0]["url"] = url
    rendered = builder().render(packet, ROOT, REPORT)
    assert f'href="{url}"' in rendered


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.extend(value for key, value in attrs if key == "href")


def test_every_report_link_resolves_locally_or_is_a_cited_source(packet):
    parser = Links()
    parser.feed(REPORT.read_text(encoding="utf-8"))
    sources = {s["url"] for s in packet["sources"]}
    assert parser.hrefs
    for href in parser.hrefs:
        if href.startswith("https://"):
            assert href in sources
        else:
            assert (REPORT.parent / unquote(href)).is_file(), href


def test_role_templates_reference_verified_claims(packet):
    assert {r["id"] for r in packet["roles"]} == {"packaging", "layout", "eda-program"}
    claims = {c["id"] for c in packet["claims"]}
    for role in packet["roles"]:
        assert role["claims"]
        assert set(role["claims"]) <= claims
        assert role["gap"]


def test_cli_writes_report_outside_repository(tmp_path):
    output = tmp_path / "packet.html"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Semiconductor career packet" in output.read_text(encoding="utf-8")


def test_custom_input_provenance_reproduces_report(packet, tmp_path):
    data = tmp_path / "custom & 'quoted' packet.json"
    output = tmp_path / "nested reports" / "custom & 'quoted' report.html"
    # Both fixtures must reach the provenance assertions on Windows too.
    for path in (data, output):
        assert not set('<>:"/\\|?*') & set(path.name), path.name
    packet["summary"] = "Synthetic custom packet for provenance regression."
    data.write_text(json.dumps(packet), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--data", str(data), "--output", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    content = output.read_text(encoding="utf-8")
    assert packet["summary"] in content
    parser = Links()
    parser.feed(content)
    local_targets = {
        local_target(href, output)
        for href in parser.hrefs
        if not href.startswith("https://")
    }
    assert data in local_targets
    assert DATA not in local_targets
    command = shlex.split(unescape(content.split("<code>")[1].split("</code>")[0]))
    assert command == [
        "python",
        "scripts/career/build_semiconductor_packet.py",
        "--data",
        command_path(data),
        "--output",
        command_path(output),
    ]
    output.unlink()
    replay = subprocess.run(
        [sys.executable, *command[1:]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert replay.returncode == 0, replay.stderr
    assert output.read_text(encoding="utf-8") == content


def local_target(href, output):
    if href.startswith("file:"):
        return Path(url2pathname(href[5:])).resolve()
    return (output.parent / unquote(href)).resolve()


def command_path(path):
    if path.anchor != ROOT.anchor:
        return path.as_posix()
    return Path(os.path.relpath(path, ROOT)).as_posix()


@pytest.mark.parametrize("location", ["data", "output", "data-link", "evidence-link"])
@pytest.mark.parametrize(
    "mounts",
    [("D:/external", "C:/checkout"), ("//other/share/file", "//server/repo")],
    ids=["drive", "unc-share"],
)
def test_cross_drive_command_and_links(packet, tmp_path, monkeypatch, location, mounts):
    module = builder()
    data = tmp_path / "custom # & 'quoted'.json"
    output = tmp_path / "nested reports" / "report.html"
    evidence = ROOT / next(p for a in packet["artifacts"] for p in a["paths"])
    failing_pair = {
        "data": (data, ROOT),
        "output": (output, ROOT),
        "data-link": (data, output.parent),
        "evidence-link": (evidence, output.parent),
    }[location]
    relpath = os.path.relpath

    def cross_drive_relpath(path, start):
        if (Path(path).resolve(), Path(start).resolve()) == failing_pair:
            return ntpath.relpath(*mounts)
        return relpath(path, start)

    monkeypatch.setattr(
        module, "os", SimpleNamespace(path=SimpleNamespace(relpath=cross_drive_relpath))
    )
    rendered = module.render(packet, ROOT, output, data)
    command = shlex.split(unescape(rendered.split("<code>")[1].split("</code>")[0]))
    assert command == [
        "python",
        "scripts/career/build_semiconductor_packet.py",
        "--data",
        data.as_posix() if location == "data" else command_path(data),
        "--output",
        output.as_posix() if location == "output" else command_path(output),
    ]
    parser = Links()
    parser.feed(rendered)
    expected = (data if location == "data-link" else evidence).as_uri()
    if location.endswith("-link"):
        assert expected in parser.hrefs
    assert data in {
        local_target(href, output)
        for href in parser.hrefs
        if not href.startswith("https://")
    }
    assert module.render(packet, ROOT, output, data) == rendered


def test_revision_history_records_review_changes(packet):
    assert len(packet["revisions"]) >= 2
    revision = packet["revisions"][-1]
    assert revision["date"] > "2026-10-19"
    for topic in ("contribution", "provenance", "experience", "credential", "Windows"):
        assert topic in revision["change"]
    rendered = builder().render(packet, ROOT, REPORT)
    assert revision["change"] in rendered
    assert revision["date"] in rendered


def test_resume_templates_keep_contribution_placeholder_when_copied(packet):
    claims = {claim["id"]: claim["text"] for claim in packet["claims"]}
    assert claims["packet-tooling"].startswith("[Built/Contributed to]")
    assert claims["data-validation"].startswith("[Implemented/Contributed to]")
    rendered = builder().render(packet, ROOT, REPORT)
    assert "[Built/Contributed to]" in rendered
    assert "[Implemented/Contributed to]" in rendered


def test_experience_transfer_is_explicit_remaining_work(packet):
    limit = next(item for item in packet["limits"] if "experience transfers" in item)
    assert "Later work:" in limit
    assert "verified" in limit
    assert limit in builder().render(packet, ROOT, REPORT)
