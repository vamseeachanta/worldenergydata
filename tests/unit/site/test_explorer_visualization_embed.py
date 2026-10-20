"""Execute the shipped browser integration with a minimal DOM and mocked API."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "reports/field-atlas/atlas_template.html"

# Synthetic revision and hash formats: full HF Git commit hashes and the existing
# bundle exporter's SHA-256 representation; no published results are fabricated.
CONFIG = {
    "endpoint": "https://example.hf.space/render",
    "dataset_id": "public-example/explorer",
    "dataset_revision": "a" * 40,
    "source_revision": "b" * 40,
    "renderer_revision": "c" * 40,
    "bundle_sha256": "d" * 64,
    # Synthetic timeout used only to exercise the browser's bounded request.
    "request_timeout_ms": 1000,
}

HARNESS = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.isConnected = true; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; this.textContent = ''; }
}
const target = new Element('figure');
const calls = [];
const response = {
  ...input.config, media_type: 'image/svg+xml', metric: 'cum_oil_mmbbl', units: 'MMbbl',
  field_id: 'alpha', svg: '<svg xmlns="http://www.w3.org/2000/svg"><text>saved</text></svg>'
};
if (input.mode === 'wrong-revision') response.dataset_revision = 'f'.repeat(40);
if (input.mode === 'wrong-source') response.source_revision = 'f'.repeat(40);
if (input.mode === 'wrong-renderer') response.renderer_revision = 'f'.repeat(40);
if (input.mode === 'wrong-digest') response.bundle_sha256 = 'f'.repeat(64);
if (input.mode === 'wrong-field') response.field_id = 'beta';
if (input.mode === 'wrong-format') response.media_type = 'text/html';
if (input.mode === 'wrong-metric') response.metric = 'forecast';
const config = input.mode === 'unconfigured' ? {} : {...input.config};
if (input.mode === 'floating-config') config.dataset_revision = 'main';
if (input.mode === 'credential-config') {
  const credentialEndpoint = new URL(config.endpoint);
  credentialEndpoint.username = 'synthetic-user';
  credentialEndpoint.password = 'synthetic-password';
  config.endpoint = credentialEndpoint.href;
}
const document = {
  getElementById: () => ({textContent: JSON.stringify(config)}),
  createElement: tag => new Element(tag),
};
const context = vm.createContext({ document, URL, AbortSignal, encodeURIComponent, console,
  fetch: async (url, options) => {
    calls.push({url, options});
    if (input.mode === 'offline') throw new Error('sensitive internal details');
    if (input.mode === 'timeout') throw new DOMException('expired', 'TimeoutError');
    if (input.mode === 'detached') target.isConnected = false;
    return {ok: input.mode !== 'unauthorized', json: async () => response};
  }
});
vm.runInContext(input.source, context);
(async () => {
  await context.loadHfVisualization(target, 'alpha');
  if (input.mode === 'success' || input.mode === 'image-error') {
    const image = target.children.find(e => e.tag === 'img');
    assert.ok(image, 'API image must be embedded');
    assert.equal(image.src, 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(response.svg));
    assert.ok(image.alt.includes('MMbbl'));
    const caption = target.children.find(e => e.tag === 'figcaption');
    for (const key of ['dataset_id','dataset_revision','source_revision','renderer_revision','bundle_sha256']) {
      assert.ok(caption.textContent.includes(response[key]), key + ' must be visible');
    }
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, input.config.endpoint);
    assert.equal(calls[0].options.credentials, 'omit');
    assert.deepEqual(JSON.parse(calls[0].options.body), {dataset_revision: input.config.dataset_revision, field_id:'alpha'});
    assert.equal(calls[0].options.headers['Content-Type'], 'application/json');
    if (input.mode === 'image-error') image.onerror();
    else return;
  }
  if (input.mode === 'detached') {
    assert.ok(!target.children.some(e => e.tag === 'img'), 'stale response must not render');
    return;
  }
  assert.ok(!target.children.some(e => e.tag === 'img'), 'unverified results must not render');
  const link = target.children.find(e => e.tag === 'a');
  assert.ok(link, 'placeholder must link a filed issue');
  assert.ok(link.href.endsWith('/issues/966'));
  const text = target.children.map(e => e.textContent || '').join(' ');
  assert.ok(/unavailable/i.test(text));
  assert.ok(!text.includes('sensitive internal details'));
  if (['unconfigured','floating-config','credential-config'].includes(input.mode)) assert.equal(calls.length, 0);
})().catch(e => {console.error(e); process.exitCode = 1;});
"""


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "unconfigured",
        "offline",
        "unauthorized",
        "wrong-revision",
        "wrong-source",
        "wrong-renderer",
        "wrong-digest",
        "wrong-field",
        "wrong-format",
        "wrong-metric",
        "floating-config",
        "credential-config",
        "image-error",
        "detached",
        "timeout",
    ],
)
def test_browser_render_contract(mode):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is unavailable for browser-script checks")
    text = TEMPLATE.read_text()
    source = text.split("// HF visualization API (#966).", 1)[1].split(
        "// End HF visualization API.", 1
    )[0]
    result = subprocess.run(
        [node, "-e", HARNESS],
        input=json.dumps(
            {
                "source": source,
                "config": CONFIG,
                "mode": mode,
            }
        ),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_template_and_generated_page_have_integration():
    for path in (TEMPLATE, ROOT / "reports/field-atlas/index.html"):
        text = path.read_text()
        assert 'id="hf-viz-config"' in text
        assert 'id="x-hf-viz"' in text
        assert 'loadHfVisualization($("x-hf-viz"), f.id)' in text
        assert "issues/966" in text
