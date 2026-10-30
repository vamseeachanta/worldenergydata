"""Structural contracts for the report-hub reference, required by issue #1059.

The committed QA/QC hub supplies the semantic labels and class tokens below.
These checks protect reader support without pinning layout, card counts, badge
wording, issue numbers, or numerical report values.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

REPO = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").is_file()
)
REFERENCE = REPO / "reports" / "lower_tertiary" / "wo-april-2026-qaqc-hub.html"


@dataclass
class _Element:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list = field(default_factory=list)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, _Element):
                yield from child.walk()

    def has_class(self, token: str) -> bool:
        return token in (self.attrs.get("class") or "").split()

    @property
    def text(self) -> str:
        return " ".join(
            " ".join(
                child.text if isinstance(child, _Element) else child
                for child in self.children
            ).split()
        )


class _HubParser(HTMLParser):
    """Retain semantic containers and text, independent of wrapper depth."""

    _void_tags = set(
        "area base br col embed hr img input link meta param source track wbr".split()
    )

    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.root = _Element("document")
        self.stack = [self.root]
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        element = _Element(tag, dict(attrs))
        self.stack[-1].children.append(element)
        if tag not in self._void_tags:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Element(tag, dict(attrs)))

    def handle_endtag(self, tag):
        for index in reversed(range(len(self.stack))):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _cards(root: _Element) -> list[_Element]:
    cards = [node for node in root.walk() if node.has_class("card")]
    assert cards, "report cards are missing"
    for card in cards:
        assert card.tag == "a" and (card.attrs.get("href") or "").strip(), (
            "report card destination is missing"
        )
    return cards


def _assert_cards_have_badges(root: _Element) -> None:
    for card in _cards(root):
        badges = [node for node in card.walk() if node.has_class("badge")]
        assert badges and all(badge.text for badge in badges), (
            "report card evidence/status badge is missing or empty"
        )


def _guided_path(root: _Element) -> _Element:
    paths = [node for node in root.walk() if node.has_class("path")]
    assert paths, "guided reading path is missing"
    for path in paths:
        assert any(
            node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
            and node.text.casefold() == "guided reading path"
            for node in path.walk()
        ), "guided reading path heading is missing"
    return next(iter(paths))


def _assert_reader_support(root: _Element) -> None:
    legends = [
        node
        for node in root.walk()
        if (node.attrs.get("aria-label") or "").casefold() == "evidence badge legend"
    ]
    assert legends, "evidence badge legend is missing"
    assert any(
        node.has_class("item") and node.text
        for legend in legends
        for node in legend.walk()
    ), "evidence badge legend explanations are missing"
    _guided_path(root)
    assert any(
        node.tag == "a"
        and "provenance" in node.text.casefold()
        and (node.attrs.get("href") or "").strip()
        for footer in root.walk()
        if footer.tag == "footer"
        for node in footer.walk()
    ), "provenance footer link is missing"


def _is_issue_target(href: str) -> bool:
    url = urlsplit(href)
    return (
        url.scheme == "https"
        and url.netloc == "github.com"
        and re.fullmatch(r"/[^/]+/[^/]+/issues/[1-9]\d*/?", url.path) is not None
    )


def _assert_guided_targets(root: _Element) -> None:
    destinations = {card.attrs["href"] for card in _cards(root)}
    links = [node for node in _guided_path(root).walk() if node.tag == "a"]
    assert links, "guided reading path is empty"
    for link in links:
        href = (link.attrs.get("href") or "").strip()
        assert href, "guided reading path destination is missing"
        assert link.text, "guided reading path link label is empty"
        assert href in destinations or _is_issue_target(href), (
            "guided reading path destination is neither a report card nor an issue"
        )


@pytest.fixture
def reference() -> _Element:
    return _HubParser(REFERENCE.read_text(encoding="utf-8")).root


def test_reference_cards_have_evidence_badges(reference):
    """Issue #1059: every report card states its evidence or status."""
    _assert_cards_have_badges(reference)


def test_reference_has_legend_guided_path_and_provenance(reference):
    """Issue #1059: readers get a badge key, reading guidance and source access."""
    _assert_reader_support(reference)


def test_guided_path_links_are_card_or_issue_targets(reference):
    """Issue #1059: the nonempty reading sequence reaches reports or issues."""
    _assert_guided_targets(reference)


# Synthetic structural examples; the issue target cites this contract's #1059.
_MINIMAL_HUB = """
<a class="card" href="report.html"><span class="badge">Evidence</span></a>
<div aria-label="Evidence badge legend"><span class="item">Evidence key</span></div>
<div class="path"><h3>Guided reading path</h3><a href="report.html">Read</a></div>
<footer><a href="source.csv">Data &amp; provenance</a></footer>
"""


def test_helpers_accept_minimal_semantic_containers():
    """Wrappers, styling, extra classes and inline elements are not pinned."""
    text = _MINIMAL_HUB.replace('class="card"', 'class="wide card"').replace(
        "Evidence</span>", "<strong>Evidence</strong><br>status</span>"
    )
    text = text.replace(
        "</h3>",
        '</h3><a href="https://github.com/example/reports/issues/1059">Decide</a>',
    )
    root = _HubParser(text).root
    _assert_cards_have_badges(root)
    _assert_reader_support(root)
    _assert_guided_targets(root)


@pytest.mark.parametrize(
    "old, new, message",
    [
        ('class="badge"', 'class="decoration"', "evidence/status badge"),
        ("Evidence</span>", "</span>", "evidence/status badge"),
        ('href="report.html"', 'href=""', "report card destination"),
    ],
    ids=["missing-badge", "empty-badge", "missing-card-destination"],
)
def test_card_helper_rejects_missing_evidence(old, new, message):
    """A card cannot borrow its evidence from another card or the legend."""
    text = _MINIMAL_HUB.replace(old, new)
    text += '<a class="card" href="other.html"><span class="badge">OK</span></a>'
    with pytest.raises(AssertionError, match=message):
        _assert_cards_have_badges(_HubParser(text).root)


@pytest.mark.parametrize(
    "old, new, message",
    [
        ("Evidence badge legend", "Other legend", "badge legend is missing"),
        ("Evidence key", "", "legend explanations are missing"),
        ('class="path"', 'class="other"', "reading path is missing"),
        ("Guided reading path", "Other heading", "path heading is missing"),
        ("<footer>", "<aside>", "provenance footer link is missing"),
        ('href="source.csv"', 'href=""', "provenance footer link is missing"),
    ],
    ids=[
        "missing-legend",
        "empty-legend",
        "missing-path",
        "unlabelled-path",
        "missing-footer",
        "missing-provenance-destination",
    ],
)
def test_reader_support_helper_rejects_missing_elements(old, new, message):
    """The reader-support contract rejects absent or uninformative containers."""
    with pytest.raises(AssertionError, match=message):
        _assert_reader_support(_HubParser(_MINIMAL_HUB.replace(old, new)).root)


@pytest.mark.parametrize(
    "replacement, message",
    [
        ("", "reading path is empty"),
        ("<a>Read</a>", "path destination is missing"),
        ('<a href="">Read</a>', "path destination is missing"),
        ('<a href="report.html"></a>', "link label is empty"),
        ('<a href="missing.html">Read</a>', "neither a report card nor an issue"),
        (
            '<a href="https://github.com/example/reports/issues/invalid">Read</a>',
            "neither a report card nor an issue",
        ),
    ],
    ids=[
        "empty-path",
        "missing-href",
        "empty-href",
        "empty-label",
        "unlisted-report",
        "invalid-issue",
    ],
)
def test_guided_target_helper_rejects_missing_destinations(replacement, message):
    """Missing or unrelated targets fail even when valid report cards exist."""
    text = _MINIMAL_HUB.replace('<a href="report.html">Read</a>', replacement)
    with pytest.raises(AssertionError, match=message):
        _assert_guided_targets(_HubParser(text).root)
