"""Kept capability pages and PDF rendering, using the sibling script-test layout."""

from __future__ import annotations

import html
import importlib.util
import re
import shutil
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
    assert not re.search(
        r"@import\b|(?:url|image|(?:-webkit-)?image-set|src)\s*\(", styles, re.I
    )
    assert "<svg" in text
    assert not re.search(r"\btmp[a-z0-9_]{6,}\.html\b", text)
    assert str(Path.home()) not in text
    assert str(SCRIPT.resolve().parents[2]) not in text


@pytest.mark.parametrize("write_pdf", [False, True])
def test_build_keeps_html_and_prints_same_file(tmp_path, write_pdf):
    mod = load_builder()
    spec = mod.SPECS[0]
    calls = []

    def renderer(source, target):
        assert source.read_text(encoding="utf-8").startswith("<!doctype html>")
        calls.append((source, target))
        if write_pdf:
            target.write_bytes(b"PDF fixture")

    out = tmp_path / "output"
    mod.build_onepager(spec, out, renderer=renderer)
    source = out / f"{spec['id']}.html"
    target = out / f"{spec['id']}.pdf"
    assert calls == [(source, target)]
    assert set(out.iterdir()) == ({source, target} if write_pdf else {source})
    assert set(tmp_path.iterdir()) == {out}
    assert_page(source.read_text(encoding="utf-8"), spec["title"])


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
    monkeypatch.setattr(mod, "_CHROME", "unused")
    monkeypatch.setattr(mod, "_to_pdf", lambda source, target: None)
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


def test_browser_receives_kept_path(tmp_path, monkeypatch):
    mod = load_builder()
    source = tmp_path / "kept.html"
    source.write_text(mod._render_html(mod.SPECS[0]), encoding="utf-8")
    commands = []
    monkeypatch.setattr(mod, "_CHROME", "browser")
    monkeypatch.setattr(
        mod.subprocess, "run", lambda command, **kwargs: commands.append(command)
    )
    mod._to_pdf(source, tmp_path / "kept.pdf")
    assert commands[0][-1] == str(source.resolve())
    assert {p.name for p in tmp_path.iterdir()} == {"kept.html"}


def test_real_pdf_document_title(tmp_path):
    mod = load_builder()
    if not mod._CHROME:
        pytest.skip("not applicable: Chrome is absent")
    if not shutil.which("pdfinfo"):
        pytest.skip("not applicable: pdfinfo is absent")
    spec = mod.SPECS[0]
    mod.build_onepager(spec, tmp_path)
    info = subprocess.run(
        ["pdfinfo", str(tmp_path / f"{spec['id']}.pdf")],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    title = next(
        line.split(":", 1)[1].strip()
        for line in info.splitlines()
        if line.startswith("Title:")
    )
    assert title == spec["title"]
    assert not re.search(r"\btmp[a-z0-9_]{6,}", title)


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
            renderer=lambda source, target: None,
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
            renderer=lambda source, target: None,
        )
    assert not (tmp_path / "output").exists()
