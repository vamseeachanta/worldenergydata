"""Issue #767: engineering chips link from the published lifecycle layout.

Expected cards come from reports/hse. The publication mapping in build_pages.py
copies posters to public/lifecycle and cards to public/hse, so links ascend once
from lifecycle before entering hse, including sites served beneath a URL prefix.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pytest

# tests/unit/lower_tertiary sits three directories below the repository root.
ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIRECTORY = Path("reports/lower_tertiary/lifecycle")
OUTPUT_DIRECTORY = Path("lifecycle")
TEMPLATE = ROOT / SOURCE_DIRECTORY / "lifecycle_template.html"
EXPECTED_TARGETS = {
    "Mooring fatigue": Path("hse/mooring-fatigue-grounded-card.html"),
    "Fatigue / VIV": Path("hse/riser-fatigue-grounded-card.html"),
}

pytestmark = pytest.mark.unit

# Only JSON strings, bare property names and arrays of JSON strings are needed
# by ENG and ENG_LINK. Full grammar matching rejects expressions and executable
# syntax before json.loads decodes any values; JavaScript is never executed.
STRING = r'"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"'
STRING_ARRAY = rf"\[\s*(?:{STRING}(?:\s*,\s*{STRING})*)?\s*\]"


def _overlay_literal(html: str, name: str) -> dict:
    literals = re.findall(
        rf"^const {re.escape(name)} = (\{{.*?^\}});[ \t]*$",
        html,
        re.MULTILINE | re.DOTALL,
    )
    if len(literals) != 1:
        raise ValueError("Expected a single bounded overlay declaration")
    (literal,) = literals
    if name == "ENG_LINK":
        key, value = STRING, STRING
    elif name == "ENG":
        key, value = r"[A-Za-z_$][A-Za-z0-9_$]*", STRING_ARRAY
    else:
        raise ValueError("Unsupported overlay declaration")
    pair = rf"{key}\s*:\s*{value}"
    if not re.fullmatch(rf"\{{\s*(?:{pair}(?:\s*,\s*{pair})*\s*,?)?\s*\}}", literal):
        raise ValueError("Unsupported overlay literal syntax")
    result = {}
    for match in re.finditer(rf"({key})\s*:\s*({value})", literal):
        raw_key, raw_value = match.groups()
        label = json.loads(raw_key) if name == "ENG_LINK" else raw_key
        if label in result:
            raise ValueError("Duplicate overlay key")
        result[label] = json.loads(raw_value)
    return result


def _assert_targets(html: str, root: Path, output_directory: Path) -> None:
    links = _overlay_literal(html, "ENG_LINK")
    assert links.keys() == EXPECTED_TARGETS.keys()
    for discipline, href in links.items():
        url = urlsplit(href)
        assert not (url.scheme or url.netloc or url.query or url.fragment)
        assert not Path(url.path).is_absolute()
        target = (output_directory / url.path).resolve()
        assert target.is_relative_to(root.resolve())
        assert target.relative_to(root.resolve()) == EXPECTED_TARGETS[discipline]
        assert target.is_file()
        for prefix in ("/", "/sample-site/"):
            base = f"https://example.invalid{prefix}lifecycle/example_lifecycle.html"
            expected = f"https://example.invalid{prefix}{EXPECTED_TARGETS[discipline].as_posix()}"
            assert urljoin(base, href) == expected


def _publish_poster(html: str, tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    spec = importlib.util.spec_from_file_location(
        "overlay_pages_builder", ROOT / "scripts/build_pages.py"
    )
    publisher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher)
    reports = tmp_path / "reports"
    lifecycle = tmp_path / SOURCE_DIRECTORY
    lifecycle.mkdir(parents=True)
    poster_name = "overlay-example_lifecycle.html"
    (lifecycle / poster_name).write_text(html, encoding="utf-8", newline="\n")
    (lifecycle / "index.html").write_text("", encoding="utf-8", newline="\n")
    for relative in EXPECTED_TARGETS.values():
        card = reports / relative
        card.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "reports" / relative, card)
    public = tmp_path / "public"
    monkeypatch.setattr(publisher, "REPORTS", reports)
    monkeypatch.setattr(publisher, "PUBLIC", public)
    publisher.build_lower_tertiary({})
    publisher.build_hse({})
    return public, public / OUTPUT_DIRECTORY / poster_name


def test_engineering_links_resolve_from_lifecycle_output(tmp_path, monkeypatch):
    public, poster = _publish_poster(
        TEMPLATE.read_text(encoding="utf-8"), tmp_path, monkeypatch
    )
    _assert_targets(poster.read_text(encoding="utf-8"), public, poster.parent)


def test_linked_disciplines_are_declared_and_unlinked_chips_keep_fallback():
    html = TEMPLATE.read_text(encoding="utf-8")
    stages = _overlay_literal(html, "ENG")
    disciplines = {discipline for stage in stages.values() for discipline in stage}
    links = _overlay_literal(html, "ENG_LINK")
    assert links.keys() <= disciplines
    assert disciplines - links.keys()
    # Check the maintained chip branches statically, without running JavaScript.
    overlay = html.split('$("f-eng").innerHTML =', 1)[1].split(
        "/* performance vs norm strip", 1
    )[0]
    assert "(ENG[p.key] || []).map(d => {" in overlay
    assert "const href = ENG_LINK[d];" in overlay
    assert re.search(
        r"return href\s*"
        r'\? `<a class="engchip link" href="\$\{href\}">\$\{d\} →</a>`\s*'
        r': `<div class="engchip">\$\{d\}</div>`;',
        overlay,
    )


def test_engineering_cards_reachable_after_temporary_render(tmp_path, monkeypatch):
    builder_path = ROOT / "scripts/lower_tertiary/build_lifecycle_posters.py"
    spec = importlib.util.spec_from_file_location(
        "overlay_poster_builder", builder_path
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)

    # Render into temporary reports, then exercise the actual publication copy
    # mappings. Resolving against source reports would pin the wrong contract.
    public, poster = _publish_poster(
        builder.render({"id": "overlay-example", "name": "Overlay example"}),
        tmp_path,
        monkeypatch,
    )
    rendered = poster.read_text(encoding="utf-8")
    assert "__FIELD_JSON__" not in rendered
    _assert_targets(rendered, public, poster.parent)
    for name in ("ENG", "ENG_LINK"):
        assert _overlay_literal(rendered, name) == _overlay_literal(
            TEMPLATE.read_text(encoding="utf-8"), name
        )


@pytest.mark.parametrize(
    "body",
    [
        '"Mooring fatigue": getLink(),',
        '"Mooring fatigue": "../" + "card.html",',
        '"Mooring fatigue": `../card.html`,',
        '"Mooring fatigue": 1,',
        '"Mooring fatigue": "first", "Mooring fatigue": "second",',
        "...otherLinks,",
        '"Mooring fatigue": "card.html", /* comment */',
        '"Mooring fatigue": "card.html",\n} || runCode();\nconst OTHER = {',
    ],
)
def test_overlay_parser_rejects_unsupported_link_syntax(body):
    with pytest.raises(ValueError):
        _overlay_literal("const ENG_LINK = {\n" + body + "\n};", "ENG_LINK")
