"""Issue #767: engineering chips link from the published lifecycle layout.

Expected destinations are the existing cards named in the issue. Independently
walking from reports/lower_tertiary/lifecycle to reports/hse requires ascending
through lower_tertiary to reports before entering hse.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import pytest

# tests/unit/lower_tertiary sits three directories below the repository root.
ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIRECTORY = Path("reports/lower_tertiary/lifecycle")
TEMPLATE = ROOT / OUTPUT_DIRECTORY / "lifecycle_template.html"
EXPECTED_TARGETS = {
    "Mooring fatigue": Path("reports/hse/mooring-fatigue-grounded-card.html"),
    "Fatigue / VIV": Path("reports/hse/riser-fatigue-grounded-card.html"),
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


def test_engineering_links_resolve_from_lifecycle_output():
    _assert_targets(TEMPLATE.read_text(), ROOT, ROOT / OUTPUT_DIRECTORY)


def test_linked_disciplines_are_declared_and_unlinked_chips_keep_fallback():
    html = TEMPLATE.read_text()
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


def test_engineering_cards_reachable_after_temporary_render(tmp_path):
    builder_path = ROOT / "scripts/lower_tertiary/build_lifecycle_posters.py"
    spec = importlib.util.spec_from_file_location(
        "overlay_poster_builder", builder_path
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)

    # Mirror the published directory tree, including the actual destination
    # cards. A flat temporary directory would hide the relative-path defect.
    output_directory = tmp_path / OUTPUT_DIRECTORY
    output_directory.mkdir(parents=True)
    for relative in EXPECTED_TARGETS.values():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    poster = output_directory / "overlay-example.html"
    poster.write_text(
        builder.render({"id": "overlay-example", "name": "Overlay example"})
    )
    rendered = poster.read_text()
    assert "__FIELD_JSON__" not in rendered
    _assert_targets(rendered, tmp_path, poster.parent)
    for name in ("ENG", "ENG_LINK"):
        assert _overlay_literal(rendered, name) == _overlay_literal(
            TEMPLATE.read_text(), name
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
