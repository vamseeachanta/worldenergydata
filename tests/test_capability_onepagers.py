"""Retained capability HTML cards, using the sibling script-test layout."""

from __future__ import annotations

import html
import importlib.util
import inspect
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/capabilities/build_onepagers.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("capability_builder", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.titles = []
        self.resources = []
        self.in_title = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.titles.append("")
            self.in_title = True
        # Anchors and visible addresses are navigation/content, not fetched assets.
        if tag in {"script", "img", "iframe", "embed", "source", "video", "audio"}:
            self.resources.extend(
                attrs[k] for k in ("src", "srcset", "poster") if k in attrs
            )
        if tag == "link" and attrs.get("rel") in {"stylesheet", "preload", "icon"}:
            self.resources.append(attrs.get("href", ""))
        if tag in {"image", "use"}:
            self.resources.extend(
                attrs[k] for k in ("href", "xlink:href") if k in attrs
            )

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.titles[-1] += data


def assert_page(text, title):
    page = Page(text)
    assert page.titles == [title]
    assert not page.resources
    styles = "".join(re.findall(r"<style[^>]*>(.*?)</style>", text, re.S))
    # Committed typefaces are embedded data; external resources remain forbidden.
    styles = re.sub(r"url\(data:font/ttf;base64,[A-Za-z0-9+/=]+\)", "", styles)
    assert not re.search(
        r"@import\b|(?:url|image|(?:-webkit-)?image-set|src)\s*\(", styles, re.I
    )
    assert "<svg" in text
    assert not re.search(r"\btmp[a-z0-9_]{6,}\.html\b", text)
    assert str(Path.home()) not in text
    assert str(SCRIPT.resolve().parents[2]) not in text


def test_default_build_writes_html_only_without_browser(tmp_path, monkeypatch):
    """The default build writes HTML and cannot launch a browser process."""
    mod = load_builder()
    out = tmp_path / "output"
    monkeypatch.setattr(mod, "_OUT", out)
    monkeypatch.setattr(mod, "_REPO", tmp_path)

    def reject_process(*args, **kwargs):
        raise AssertionError("the default build launched a process")

    monkeypatch.setattr(subprocess, "run", reject_process)
    mod.main([])
    assert {p.name for p in out.iterdir()} == {
        f"{spec['id']}.html" for spec in mod.SPECS
    }
    assert not list(out.rglob("*.pdf"))
    for spec in mod.SPECS:
        assert_page((out / f"{spec['id']}.html").read_text(), spec["title"])


@pytest.mark.parametrize("escaped", [False, True])
def test_title_is_exact_and_escaped(escaped):
    mod = load_builder()
    spec = dict(mod.SPECS[0])
    if escaped:
        spec["title"] = 'Energy <review> & "figures"'
    text = mod._render_html(spec)
    assert_page(text, spec["title"])
    assert f"<title>{html.escape(spec['title'])}</title>" in text


def test_every_spec_has_nonempty_title():
    mod = load_builder()
    for spec in mod.SPECS:
        assert spec["title"].strip()
        assert_page(mod._render_html(spec), spec["title"])


def test_cli_brand_is_inline_after_defaults(tmp_path, monkeypatch):
    mod = load_builder()
    brand = tmp_path / "brand.css"
    css = "h1 { color: #123456; }\n"
    brand.write_text(css, encoding="utf-8")
    out = tmp_path / "output"
    monkeypatch.setattr(mod, "_OUT", out)
    monkeypatch.setattr(mod, "_REPO", tmp_path)
    monkeypatch.setattr(mod, "SPECS", mod.SPECS[:1])
    mod.main(["--brand", str(brand)])
    spec = mod.SPECS[0]
    text = (out / f"{spec['id']}.html").read_text(encoding="utf-8")
    assert css in text
    assert text.index(css) > text.index(".cta{") > text.index(mod._TOKENS)
    assert str(brand) not in text
    assert_page(text, spec["title"])


@pytest.mark.parametrize("kind", ["missing", "directory", "unreadable"])
def test_bad_brand_writes_nothing(tmp_path, monkeypatch, capsys, kind):
    mod = load_builder()
    brand = tmp_path / "brand.css"
    if kind == "directory":
        brand.mkdir()
    if kind == "unreadable":
        brand.write_text("body {}", encoding="utf-8")
        original = Path.read_text

        def read_text(path, *args, **kwargs):
            if path == brand:
                raise PermissionError("stylesheet is unreadable")
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", read_text)
    out = tmp_path / "output"
    monkeypatch.setattr(mod, "_OUT", out)
    with pytest.raises(SystemExit) as error:
        mod.main(["--brand", str(brand)])
    assert error.value.code == 2
    assert "brand stylesheet" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize(
    "css", ['@import "remote.css";', "body {background:url(asset)}", "</style>"]
)
def test_brand_cannot_add_resources_or_markup(css, tmp_path):
    mod = load_builder()
    with pytest.raises(ValueError, match="self-contained"):
        mod.build_onepager(mod.SPECS[0], tmp_path / "output", brand_css=css)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "css", [r'@im\70ort "remote.css";', r"body {background:u\72l(asset)}"]
)
def test_brand_rejects_escaped_resource_references(css, tmp_path):
    mod = load_builder()
    with pytest.raises(ValueError, match="self-contained"):
        mod.build_onepager(
            mod.SPECS[0],
            tmp_path / "output",
            brand_css=css,
        )
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("function", ["image-set", "-webkit-image-set"])
def test_brand_rejects_string_image_resources(function, tmp_path):
    mod = load_builder()
    css = f'body {{background-image: {function}("asset.png" 1x)}}'
    with pytest.raises(ValueError, match="self-contained"):
        mod.build_onepager(
            mod.SPECS[0],
            tmp_path / "output",
            brand_css=css,
        )
    assert not (tmp_path / "output").exists()


def test_every_spec_has_no_trailing_whitespace() -> None:
    """Every specification renders without spaces or tabs at line endings."""
    mod = load_builder()
    violations = [
        (spec["id"], number)
        for spec in mod.SPECS
        for number, line in enumerate(mod._render_html(spec).splitlines(), 1)
        if line.endswith((" ", "\t"))
    ]
    assert not violations, violations


BANNED_COPY = {
    "software": (
        "CI",
        "regression-guarded",
        "deterministic",
        "deterministically",
        "stdlib",
        "stdlib-only",
        "regex",
        "JSON data contract",
        "renderers",
        "renderer",
        "frozen workbook",
        "frozen reference workbook",
        "static build",
        "Plotly",
        "Three.js",
        "data contract",
    ),
    "absolutes": (
        "every",
        "never",
        "100%",
        "identical for everyone",
        "every time",
        "to the cent",
        "every major offshore region",
        "instant",
        "instantly",
        "always",
        "exact",
        "validated",
        "certified",
        "100 %",
    ),
    "promotional": (
        "world-class",
        "best-in-class",
        "cutting-edge",
        "revolutionary",
        "revolution",
        "transformative",
        "game changer",
        "seamless",
        "unmatched",
        "unparalleled",
        "showcase",
        "powerful",
        "comprehensive",
        "full field-development plans",
        "guarantee",
        "unique",
        "leading",
        "robust",
        "proven",
        "state-of-the-art",
    ),
}


class VisibleCopy(HTMLParser):
    """Collect readable template copy while excluding styles and navigation URLs."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.in_style = False
        self.parts: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "style":
            self.in_style = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if not self.in_style:
            self.parts.append(data)


def copy_fields(mod) -> list[tuple[str, str, str]]:
    """Return the page, field and text subject to editorial constraints."""
    fields = []
    for spec in mod.SPECS:
        for field in ("title", "std", "blurb", "figures", "bullets"):
            value = spec[field]
            text = (
                value
                if isinstance(value, str)
                else " ".join(
                    " ".join(item) if isinstance(item, (list, tuple)) else item
                    for item in value
                )
            )
            fields.append((spec["id"], field, text))
    fields.append(
        ("template", "fixed text", " ".join(VisibleCopy(mod._TEMPLATE).parts))
    )
    return fields


def wording_findings(fields: list, category: str) -> list:
    """Locate banned phrases and unqualified verification claims in visible copy."""
    findings = []
    for page, field, text in fields:
        for phrase in BANNED_COPY[category]:
            if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I):
                findings.append((page, field, phrase))
        if category == "absolutes":
            for sentence in re.split(r"[.!?](?:\s|$)", text):
                reference_pattern = (
                    r"\bverified\s+against\s+(?:"
                    + "|".join(re.escape(reference) for reference in NAMED_REFERENCES)
                    + r")(?!\w)"
                )
                if re.search(r"\bverified\b", sentence, re.I) and not re.search(
                    reference_pattern, sentence, re.I
                ):
                    findings.append((page, field, "verified without reference"))
    return findings


@pytest.mark.parametrize("category", BANNED_COPY)
def test_copy_excludes_banned_wording(category: str) -> None:
    """Reject software practice, absolutes and promotional descriptions."""
    assert not wording_findings(copy_fields(load_builder()), category)


@pytest.mark.parametrize("category", BANNED_COPY)
def test_wording_rules_reject_case_variants(category: str) -> None:
    """Exercise the checker independently of the current editorial table."""
    for phrase in BANNED_COPY[category]:
        assert wording_findings([("page", "blurb", phrase.upper())], category)
        assert not wording_findings([("page", "blurb", "x" + phrase + "x")], category)


def test_verified_requires_sentence_reference() -> None:
    """A reference in a later sentence does not qualify the verification claim."""
    assert wording_findings(
        [("page", "blurb", "Verified. Against reference values.")], "absolutes"
    )
    assert not wording_findings(
        [("page", "blurb", "Verified against FDAS V30 Financial Project Summary.")],
        "absolutes",
    )


def test_each_page_states_source_and_data_basis() -> None:
    """Require a named source and an explicit recorded or missing data cut-off."""
    for spec in load_builder().SPECS:
        assert re.search(
            r"data as of: (?:\d{4}(?:-\d{2}(?:-\d{2})?)?|not recorded)(?:\b|$)",
            spec["std"],
        ), spec["id"]
        assert spec["std"].split("data as of:")[0].strip(" ·"), spec["id"]
        assert spec["std"] in html.unescape(load_builder()._render_html(spec))


def test_footer_has_fixed_revision_date() -> None:
    """Require the declared editorial revision in the footer of each rendered page."""
    mod = load_builder()
    assert getattr(mod, "REVISION_DATE", None) == "2026-10-13"
    for spec in mod.SPECS:
        assert f"Revision: {mod.REVISION_DATE}" in mod._render_html(spec)


def test_pages_embed_committed_font_weights() -> None:
    """Require three embedded faces from the committed open-licence family."""
    import base64

    mod = load_builder()
    font_dir = SCRIPT.parents[2] / "reports/capabilities/assets/fonts/OpenSans"
    assert (font_dir / "OFL.txt").is_file()
    for spec in mod.SPECS:
        text = mod._render_html(spec)
        assert "Arial" not in text and "Helvetica" not in text
        faces = re.findall(r"@font-face\s*\{([^}]+)\}", text)
        assert len(faces) == 3
        for weight, name in ((400, "Regular"), (700, "Bold"), (800, "ExtraBold")):
            face = next(f for f in faces if f"font-weight:{weight}" in f)
            assert 'font-family:"Open Sans"' in face
            payload = re.search(r"url\(data:font/ttf;base64,([A-Za-z0-9+/=]+)\)", face)
            assert payload
            assert (
                base64.b64decode(payload[1], validate=True)
                == (font_dir / f"OpenSans-{name}.ttf").read_bytes()
            )
        assert 'font-family="Open Sans"' in text


def assert_unique_titles(specs: list[dict]) -> None:
    """Reject repeated page titles irrespective of their page identifiers."""
    titles = [spec["title"].strip().casefold() for spec in specs]
    assert len(titles) == len(set(titles)), "duplicate page title"


def test_page_titles_are_unique() -> None:
    """Check current titles and demonstrate rejection of a duplicate title."""
    specs = load_builder().SPECS
    assert_unique_titles(specs)
    with pytest.raises(AssertionError, match="duplicate page title"):
        assert_unique_titles(specs + [dict(specs[0], id="duplicate")])


def test_footer_avoids_unavailable_arrow_glyph() -> None:
    """The decorative arrow requires a system font outside the committed family."""
    assert "&rarr;" not in load_builder()._TEMPLATE


def test_source_and_engineering_abbreviations_are_expanded() -> None:
    """Use full source and engineering terms in the one-page summaries."""
    unexplained = (
        r"\b(?:BSEE|EIA|WAR|NPV|WTI|USCG|TSB|IMO|GISIS|MAIB|DLP|TD|MD|HSE|DEXPI)\b"
    )
    for page, field, text in copy_fields(load_builder()):
        assert not re.search(unexplained, text), (page, field)


def test_economic_pages_state_price_and_cost_basis() -> None:
    """Identify price inputs separately from the recorded cost assumptions."""
    ids = {"sec-economics", "portfolio", "benchmark", "sec-playbook", "fd-showcase"}
    for spec in load_builder().SPECS:
        if spec["id"] in ids or spec["id"].startswith("economics-"):
            assert "Price:" in spec["std"], spec["id"]
            assert "cost:" in spec["std"], spec["id"]


def test_country_name_is_spelled_out_in_source_basis() -> None:
    """Expand the country name alongside the public agency name on each page."""
    for spec in load_builder().SPECS:
        assert not re.search(r"(?<!\w)U\.S\.(?!\w)", spec["std"], re.I), spec["id"]


NAMED_REFERENCES = (
    "FDAS V30 Financial Project Summary",
    "World Oil April 2026 article",
)


def committed_copy_fields(directory: Path) -> list:
    """Collect readable text from retained pages without embedded font payloads."""
    return [
        (page.name, "readable text", " ".join(VisibleCopy(page.read_text()).parts))
        for page in sorted(directory.glob("*.html"))
    ]


def assert_economics_cutoff(specs: list[dict]) -> None:
    """Require the economics basis to equal its cited data vintage."""
    data_path = (
        SCRIPT.parents[2] / "reports/lower_tertiary/data/all_fields_economics.json"
    )
    vintage_text = json.loads(data_path.read_text())["meta"]["vintage"]
    vintage = re.search(r"through (\d{4}-\d{2})", vintage_text).group(1)
    for spec in specs:
        if spec["id"] in {"sec-economics", "portfolio", "benchmark"} or spec[
            "id"
        ].startswith("economics-"):
            printed = re.search(
                r"data as of: (\d{4}-\d{2}(?:-\d{2})?)(?=\s|$)", spec["std"]
            )
            assert printed is not None, spec["id"]
            assert printed.group(1) == vintage, spec["id"]


def test_committed_html_copy_excludes_banned_wording() -> None:
    """Apply the editorial word rules to each committed readable page."""
    directory = SCRIPT.parents[2] / "reports/capabilities/pdf"
    fields = committed_copy_fields(directory)
    assert len(fields) == 26
    for category in BANNED_COPY:
        assert not wording_findings(fields, category)


def test_committed_html_negative_control(tmp_path: Path) -> None:
    """Detect a prohibited phrase in retained text but ignore font styles."""
    (tmp_path / "page.html").write_text("<style>never</style><p>NEVER</p>")
    assert wording_findings(committed_copy_fields(tmp_path), "absolutes")
    visible_url = "https://example.org/guarantee"
    (tmp_path / "url.html").write_text(f"<p>{visible_url}</p>")
    assert ("url.html", "readable text", "guarantee") in wording_findings(
        committed_copy_fields(tmp_path), "promotional"
    )


@pytest.mark.parametrize(
    "phrase",
    (
        "guarantee",
        "unique",
        "leading",
        "robust",
        "proven",
        "state-of-the-art",
        "always",
        "exact",
        "validated",
        "certified",
        "100 %",
    ),
)
def test_extended_words_negative_control(phrase: str) -> None:
    """Reject each added word as a whole word irrespective of case."""
    assert any(
        wording_findings([("page", "blurb", phrase.upper())], category)
        for category in BANNED_COPY
    )


def test_verified_named_reference_negative_control() -> None:
    """Reject a verification claim without a reference from the named set."""
    assert wording_findings(
        [("page", "blurb", "Verified against arbitrary values.")], "absolutes"
    )


def test_economics_cutoff_matches_cited_data() -> None:
    """Read the vintage once from the source rather than duplicating its date."""
    assert_economics_cutoff(load_builder().SPECS)


def test_economics_cutoff_negative_control() -> None:
    """Demonstrate that an unsupported cutoff is rejected."""
    spec = dict(load_builder().SPECS[0], std="data as of: unsupported")
    with pytest.raises(AssertionError, match=spec["id"]):
        assert_economics_cutoff([spec])
    prefix_only = dict(load_builder().SPECS[0])
    prefix_only["std"] = re.sub(
        r"(data as of: \d{4}-\d{2})", r"\1-01", prefix_only["std"]
    )
    with pytest.raises(AssertionError, match=prefix_only["id"]):
        assert_economics_cutoff([prefix_only])


def test_explicit_empty_figures_has_no_trailing_whitespace() -> None:
    """An explicitly empty figures list emits no block or trailing whitespace."""
    mod = load_builder()
    text = mod._render_html(dict(mod.SPECS[0], figures=[]))
    assert '<div class="figs">' not in text
    assert all(not line.endswith((" ", "\t")) for line in text.splitlines())


@pytest.mark.parametrize("spec", load_builder().SPECS, ids=lambda spec: spec["id"])
def test_page_basis_and_plain_label(spec: dict) -> None:
    """Keep the estimated cost basis and remove unsupported template buttons."""
    mod = load_builder()
    assert "incurred costs" not in spec["blurb"]
    if "Price:" in spec["std"]:
        assert "pre-tax" in spec["std"], spec["id"]
    text = mod._render_html(spec)
    assert "Capability summary" in text
    assert '<span class="cta">' not in text
    assert '<a class="live" href="' in text
    assert ">Explore live</a>" in text


def test_builder_has_no_pdf_print_interface(tmp_path):
    """The builder exposes an HTML-only interface without browser lookup."""
    mod = load_builder()
    assert not hasattr(mod, "_to_pdf")
    assert not hasattr(mod, "_CHROME")
    assert "renderer" not in inspect.signature(mod.build_onepager).parameters
    spec = mod.SPECS[0]
    source = mod.build_onepager(spec, tmp_path)
    assert source == tmp_path / f"{spec['id']}.html"
    assert list(tmp_path.iterdir()) == [source]
    assert not list(tmp_path.rglob("*.pdf"))
