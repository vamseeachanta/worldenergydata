"""Offline interaction tests for the single-file module report.

The browser dependency is optional for consumers of the calculation module.
Report delivery requires running these tests with Playwright and Chromium.
"""

import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs/reports/modules/wenergymix/index.html"


@pytest.fixture
def page():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        executable = shutil.which("google-chrome") or shutil.which("chromium")
        browser = runtime.chromium.launch(headless=True, executable_path=executable)
        context = browser.new_context(offline=True, accept_downloads=True)
        page = context.new_page()
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: (
                requests.append(request.url)
                if request.url.startswith(("http:", "https:"))
                else None
            ),
        )
        page.goto(REPORT.as_uri(), wait_until="load")
        yield page
        context.close()
        browser.close()
        assert not errors
        assert not requests


def test_interactive_chart_returns_and_boundary(page):
    assert page.locator("main > section").count() == 10
    assert page.locator("body.hs-doc").count() == 1
    assert page.locator("svg span").count() == 0
    assert "Demand: 20250 MWh" in page.locator("#chart-readout").inner_text()
    assert "Lower limit: 0 MWh" in page.locator("#chart-readout").inner_text()
    page.locator("#chart-case").select_option("1")
    assert "Demand: 1000 MWh" in page.locator("#chart-readout").inner_text()
    page.locator('[data-case="2"]').focus()
    assert "Demand: 0 MWh" in page.locator("#chart-readout").inner_text()
    assert page.locator("#conversion-chart line.limit").count() == 1
    assert page.locator("#example-table tbody tr").count() == 3
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def add_comment(page):
    text = "<img src=x onerror=alert(1)> Check the energy basis."
    page.locator("#comment-section").select_option("section-6")
    page.locator("#comment-text").fill(text)
    page.locator("#add-comment").click()
    assert page.locator("#comment-list img").count() == 0
    return text


def test_comment_export_import_and_binding(page, tmp_path):
    text = add_comment(page)
    with page.expect_download() as download:
        page.locator("#download-comments").click()
    assert download.value.suggested_filename == "energy-mix.comments.json"
    sidecar = tmp_path / download.value.suggested_filename
    download.value.save_as(sidecar)
    saved = json.loads(sidecar.read_text(encoding="utf-8"))
    assert saved["comments"] == [{"section": "section-6", "text": text}]
    page.reload(wait_until="load")
    page.locator("#import-comments").set_input_files(sidecar)
    page.wait_for_function(
        "document.getElementById('comment-status').textContent.startsWith('Saved comments opened')"
    )
    assert page.locator("#comment-list").inner_text().endswith(text)
    saved["binding"] = "different-content"
    mismatch = tmp_path / "different-content.comments.json"
    mismatch.write_text(json.dumps(saved), encoding="utf-8", newline="\n")
    page.locator("#import-comments").set_input_files(mismatch)
    page.wait_for_function(
        "document.getElementById('comment-status').textContent.startsWith('Comments were not opened')"
    )
    assert page.locator("#comment-list li").count() == 1


def test_comments_folder_save_api_contract(page):
    text = add_comment(page)
    # Browser folder-selection UI cannot be automated. The API contract below
    # exercises filename, UTF-8 JSON content and write/close completion.
    page.evaluate("""() => {
      window.savedSidecar = null;
      window.streamClosed = false;
      window.showDirectoryPicker = async () => ({getFileHandle: async name => ({
        createWritable: async () => ({
          write: async text => {window.savedSidecar = {name, text}},
          close: async () => {window.streamClosed = true}
        })
      })});
    }""")
    page.locator("#save-comments").click()
    page.wait_for_function("window.streamClosed === true")
    stored = page.evaluate("window.savedSidecar")
    assert stored["name"] == "energy-mix.comments.json"
    assert json.loads(stored["text"])["comments"][0]["text"] == text
    assert "Comments saved" in page.locator("#comment-status").inner_text()
