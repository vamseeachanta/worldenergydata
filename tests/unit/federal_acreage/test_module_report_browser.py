"""Exercise offline chart, comment transport and adjacent-file persistence."""

import json
import shutil
from pathlib import Path

import pytest

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="Optional report browser checks require Playwright"
)
expect = playwright_api.expect
sync_playwright = playwright_api.sync_playwright

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs/reports/modules/wfederalacreage/index.html"


@pytest.fixture()
def page():
    browser_path = next(
        (
            shutil.which(name)
            for name in ("chromium", "chromium-browser", "google-chrome")
            if shutil.which(name)
        ),
        None,
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=browser_path,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        requests = []
        page.route(
            "https://**/*",
            lambda route: (requests.append(route.request.url), route.abort()),
        )
        page.goto(REPORT.as_uri())
        yield page
        assert errors == []
        assert requests == []
        context.close()
        browser.close()


def add_comment(page, text="Check the missing geometry before interpreting coverage."):
    page.select_option("#comment-section", "section-6")
    page.fill("#comment-text", text)
    page.click("#add-comment")
    assert text in page.locator("#comment-list").inner_text()


def test_offline_chart_hover_keyboard_and_change_panel(page):
    bars = page.locator(".bar")
    assert bars.count() == 5
    bars.nth(1).hover()
    assert (
        "Record coverage; acreage 280 acres"
        in page.locator("#chart-detail").inner_text()
    )
    assert "bound 320 acres" in page.locator("#chart-detail").inner_text()
    bars.nth(4).focus()
    assert "acreage 40 acres" in page.locator("#chart-detail").inner_text()
    assert page.locator("#change-list li").count() == 4
    assert page.locator("main > section").count() == 10


def test_comment_export_import_and_html_escaping(page, tmp_path):
    text = '<img src=x onerror="throw Error(1)"> Check units.'
    add_comment(page, text)
    assert page.locator("#comment-list img").count() == 0
    with page.expect_download() as event:
        page.click("#export-comments")
    download = event.value
    target = tmp_path / download.suggested_filename
    download.save_as(target)
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["comments"] == [{"section": "section-6", "text": text}]
    assert saved["revision"] == "1"
    page.reload()
    assert page.locator("#comment-list li").count() == 0
    page.set_input_files("#import-comments", str(target))
    expect(page.locator("#comment-list li")).to_have_count(1)
    assert page.locator("#comment-list").inner_text().endswith(text)
    saved["documentBinding"] = "wrong-document"
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps(saved), encoding="utf-8", newline="\n")
    page.set_input_files("#import-comments", str(wrong))
    expect(page.locator("#comment-status")).to_contain_text("another document revision")
    expect(page.locator("#comment-list li")).to_have_count(1)


def test_adjacent_file_save_and_wrong_folder_rejection(page, tmp_path):
    add_comment(page)
    # The browser permission dialog is replaced; real handlers and serialization
    # run unchanged. Saved bytes are read back as a filesystem artifact below.
    page.evaluate(
        """() => {
      window.writes = [];
      window.folderMatches = true;
      window.showDirectoryPicker = async () => ({getFileHandle: async (name, options) => {
        if (name === 'index.html') return {getFile: async () => ({text: async () =>
          window.folderMatches ? document.documentElement.outerHTML : '<html></html>'})};
        if (name !== 'federal-acreage-comments.json' || !options.create) throw Error('Wrong target');
        return {createWritable: async () => ({write: async text => window.writes.push(text),
                                              close: async () => {window.closedSave = true;}})};
      }});
    }"""
    )
    page.click("#save-comments")
    page.wait_for_function("window.closedSave === true")
    assert (
        page.locator("#comment-status").inner_text()
        == "Comments saved beside the report."
    )
    target = tmp_path / "federal-acreage-comments.json"
    target.write_text(page.evaluate("window.writes[0]"), encoding="utf-8", newline="\n")
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["comments"][0]["section"] == "section-6"
    page.evaluate("window.folderMatches = false")
    page.click("#save-comments")
    assert (
        "does not contain this report revision"
        in page.locator("#comment-status").inner_text()
    )
    assert page.evaluate("window.writes.length") == 1


def test_folder_save_fallback_and_mobile_layout(page):
    page.evaluate("window.showDirectoryPicker = undefined")
    page.click("#save-comments")
    assert "use Export comments" in page.locator("#comment-status").inner_text()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
