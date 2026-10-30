"""Pinned-render contract; all data are synthetic, with independent arithmetic."""

import hashlib
import importlib.util
import io
import json
from pathlib import Path
from urllib.error import URLError
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/hf_export/explorer_visualization.py"
SPEC = importlib.util.spec_from_file_location("explorer_visualization", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

# Synthetic full Git hashes, not published release identifiers; HF download guide
# requires full-length commit hashes, https://huggingface.co/docs/huggingface_hub/guides/download.
DATA_REV = "a" * 40
SOURCE_REV = "b" * 40
RENDER_REV = "c" * 40


@pytest.fixture
def release():
    bundle = {
        "schema_version": "1.0.0",
        "projection": "field_explorer_results",
        "hf_dataset": "worldenergydata",
        "fields": {
            "alpha": {"name": "Synthetic <alpha>", "performance": {"cum_oil_mmbbl": 3}},
            "beta": {"name": "Synthetic beta", "performance": {"cum_oil_mmbbl": 6}},
            "unknown": {"name": "Unknown", "performance": {"cum_oil_mmbbl": None}},
            "zero": {"name": "Zero", "performance": {"cum_oil_mmbbl": 0}},
        },
        "sources": [{"role": "field_detail", "sha256": "d" * 64}],
    }
    raw = json.dumps(bundle, allow_nan=False).encode()
    config = {
        "renderer_revision": RENDER_REV,
        # Deployment choices for these tests, not engineering acceptance limits.
        "limits": {"request_bytes": 4096, "bundle_bytes": 10000, "timeout_seconds": 5},
        "releases": [
            {
                "dataset_id": "public-example/explorer",
                "dataset_revision": DATA_REV,
                "source_revision": SOURCE_REV,
                "bundle_path": "results/explorer_results_bundle.json",
                "bundle_sha256": hashlib.sha256(raw).hexdigest(),
                "public_data_approved": True,
            }
        ],
    }
    return config, raw


def request(app, payload, method="POST", path="/render", origin=None):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    env = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_TYPE": "application/json",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    if origin:
        env["HTTP_ORIGIN"] = origin
    response = {}

    def start(status, headers):
        response.update(status=int(status.split()[0]), headers=dict(headers))

    response["body"] = json.loads(b"".join(app(env, start)))
    return response


def test_render_hand_calculated_bar_lengths_and_trace(release):
    """By hand: maximum=6; normalized widths are 3/6=0.5, 6/6=1, 0/6=0.

    Missing oil is unknown, not zero. The renderer uses a unit SVG viewBox
    for the data bars, so no expected value is obtained from the renderer.
    """
    config, raw = release
    app = mod.create_app(config, fetch=lambda url, **kw: raw)
    result = request(app, {"dataset_revision": DATA_REV, "field_id": "alpha"})
    assert result["status"] == 200
    body = result["body"]
    svg = ET.fromstring(body["svg"])
    bars = {
        e.attrib["data-field"]: float(e.attrib["width"])
        for e in svg.iter()
        if "data-field" in e.attrib
    }
    assert bars == {"alpha": 0.5, "beta": 1.0, "zero": 0.0}
    assert "Unknown: unavailable" in "".join(svg.itertext())
    assert "Synthetic <alpha>" in "".join(svg.itertext())
    assert body["dataset_revision"] == DATA_REV
    assert body["source_revision"] == SOURCE_REV
    assert body["renderer_revision"] == RENDER_REV
    assert body["bundle_sha256"] == hashlib.sha256(raw).hexdigest()
    assert body["sources"] == json.loads(raw)["sources"]
    assert body["media_type"] == "image/svg+xml"
    assert body["metric"] == "cum_oil_mmbbl"
    assert body["units"] == "MMbbl"
    assert "no-store" in result["headers"]["Cache-Control"]


def test_only_approved_pinned_url_is_fetched(release):
    config, raw = release
    calls = []

    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        return raw

    app = mod.create_app(config, fetch=fetch)
    response = request(
        app, {"dataset_revision": DATA_REV}, origin="https://example.org"
    )
    assert response["status"] == 200
    assert calls == [
        (
            f"https://huggingface.co/datasets/public-example/explorer/resolve/{DATA_REV}/results/explorer_results_bundle.json",
            {"max_bytes": 10000, "timeout": 5},
        )
    ]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert "Access-Control-Allow-Credentials" not in response["headers"]


@pytest.mark.parametrize(
    "revision", ["main", "latest", "a" * 7, "a" * 39, "f" * 40, "../main", None]
)
def test_unapproved_or_floating_revision_never_downloaded(release, revision):
    config, _ = release
    app = mod.create_app(
        config, fetch=lambda *a, **k: pytest.fail("unexpected download")
    )
    response = request(app, {"dataset_revision": revision})
    assert response["status"] == 400
    assert response["body"]["issue"].endswith("/issues/966")


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b"[]",
        b"{}",
        b'{"dataset_revision":NaN}',
        b'{"dataset_revision":"main","dataset_revision":"latest"}',
    ],
)
def test_malformed_requests_are_rejected(release, payload):
    config, raw = release
    result = request(mod.create_app(config, fetch=lambda *a, **k: raw), payload)
    assert result["status"] == 400


@pytest.mark.parametrize("depth", [1, 1100])
def test_array_field_ids_are_rejected_before_download(release, depth):
    config, _ = release
    # Construct raw JSON so decoder recursion, rather than encoder recursion,
    # is exercised while the request remains below the configured byte limit.
    payload = (
        b'{"dataset_revision":"'
        + DATA_REV.encode()
        + b'","field_id":'
        + b"[" * depth
        + b"0"
        + b"]" * depth
        + b"}"
    )
    assert len(payload) <= config["limits"]["request_bytes"]
    app = mod.create_app(
        config, fetch=lambda *a, **k: pytest.fail("unexpected download")
    )
    result = request(app, payload)
    assert result["status"] == 400
    assert result["body"]["issue"].endswith("/issues/966")
    assert "svg" not in result["body"]


def test_request_limits_and_methods(release):
    config, raw = release
    app = mod.create_app(config, fetch=lambda *a, **k: raw)
    assert request(app, b"x" * 4097)["status"] == 413
    assert request(app, {}, method="GET")["status"] == 405
    assert request(app, {}, path="/other")["status"] == 404
    assert request(app, {}, method="OPTIONS")["status"] == 200


def test_digest_mismatch_does_not_render(release):
    config, raw = release
    result = request(
        mod.create_app(config, fetch=lambda *a, **k: raw + b" "),
        {"dataset_revision": DATA_REV},
    )
    assert result["status"] == 502
    assert result["body"]["error"] == "Saved results failed validation"
    assert "svg" not in result["body"]


def test_upstream_error_has_no_sensitive_exception_text(release):
    config, _ = release

    def unavailable(*a, **k):
        raise URLError("private exception details")

    result = request(
        mod.create_app(config, fetch=unavailable), {"dataset_revision": DATA_REV}
    )
    assert result["status"] == 503
    assert "private exception details" not in json.dumps(result)


@pytest.mark.parametrize(
    "change",
    [
        {"source_revision": "main"},
        {"public_data_approved": False},
        {"bundle_path": "../secret"},
        {"dataset_id": "https://example.org/data"},
        {"bundle_sha256": "invalid"},
        {"dataset_revision": "main"},
    ],
)
def test_invalid_release_configuration_fails_closed(release, change):
    config, _ = release
    config["releases"][0].update(change)
    with pytest.raises(ValueError):
        mod.create_app(config)


@pytest.mark.parametrize("value", [-1, True, "3", float("inf")])
def test_invalid_saved_values_fail_instead_of_guessing(release, value):
    config, raw = release
    bundle = json.loads(raw)
    bundle["fields"]["alpha"]["performance"]["cum_oil_mmbbl"] = value
    raw = json.dumps(bundle).encode()
    config["releases"][0]["bundle_sha256"] = hashlib.sha256(raw).hexdigest()
    result = request(
        mod.create_app(config, fetch=lambda *a, **k: raw),
        {"dataset_revision": DATA_REV},
    )
    assert result["status"] == 502


def test_zero_only_data_has_zero_width_without_division_error(release):
    config, raw = release
    bundle = json.loads(raw)
    bundle["fields"] = {"zero": bundle["fields"]["zero"]}
    raw = json.dumps(bundle).encode()
    config["releases"][0]["bundle_sha256"] = hashlib.sha256(raw).hexdigest()
    result = request(
        mod.create_app(config, fetch=lambda *a, **k: raw),
        {"dataset_revision": DATA_REV},
    )
    assert result["status"] == 200
    assert 'width="0"' in result["body"]["svg"]


def test_worked_example_writes_a_replayable_answer(tmp_path):
    """Independent hand calculation: 3/6=0.5, 6/6=1, 0/6=0; null is unknown."""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples/explorer_visualization_demo.py"),
            "--output",
            str(tmp_path),
        ],
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads((tmp_path / "synthetic_manifest.json").read_text())
    response = json.loads((tmp_path / "render_response.json").read_text())
    raw = (tmp_path / "input_bundle.json").read_bytes()
    assert manifest["releases"][0]["bundle_sha256"] == hashlib.sha256(raw).hexdigest()
    assert response["svg"] == (tmp_path / "chart.svg").read_text()
    svg = ET.fromstring(response["svg"])
    assert {
        e.attrib["data-field"]: float(e.attrib["width"])
        for e in svg.iter()
        if "data-field" in e.attrib
    } == {
        "alpha": 0.5,
        "beta": 1.0,
        "zero": 0.0,
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/datasets/public-example/data/resolve/main/data.json",
        "https://example.invalid/data.json",
        "file:///data.json",
        "https://huggingface.co/other/data.json",
        "https://huggingface.co/datasets/data?token=forbidden",
    ],
)
def test_downloader_rejects_non_public_hf_urls_before_open(monkeypatch, url):
    monkeypatch.setattr(mod, "public_opener", lambda: pytest.fail("must not open"))
    with pytest.raises(ValueError):
        mod.download(url, max_bytes=10000, timeout=5)


def test_downloader_bounds_reads_and_has_no_file_or_http_redirects(monkeypatch):
    """Operational fixture: 3 bytes allowed; 4 bytes returned must be rejected."""
    from contextlib import nullcontext

    opener = mod.public_opener()
    # These requests have no protocol handler and cannot read local files or
    # make plaintext requests, including when a remote redirect targets them.
    for url in ("file:///data.json", "http://example.invalid"):
        with pytest.raises(URLError):
            opener.open(url)

    class Response:
        def read(self, count):
            assert count == 4
            return b"data"

    class Opener:
        def open(self, url, timeout):
            assert timeout == 5
            return nullcontext(Response())

    monkeypatch.setattr(mod, "public_opener", Opener)
    with pytest.raises(ValueError, match="byte limit"):
        mod.download(
            "https://huggingface.co/datasets/example/data", max_bytes=3, timeout=5
        )


def test_unknown_field_is_a_request_error(release):
    config, raw = release
    result = request(
        mod.create_app(config, fetch=lambda *a, **k: raw),
        {"dataset_revision": DATA_REV, "field_id": "absent"},
    )
    assert result["status"] == 400
    assert "svg" not in result["body"]


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": "unsupported"},
        {"projection": "other"},
        {"hf_dataset": "other"},
        {"sources": []},
        {"sources": [{"sha256": "invalid"}]},
        {"fields": []},
        {"fields": {"bad": []}},
    ],
)
def test_unsupported_bundle_or_missing_provenance_is_not_rendered(release, change):
    config, raw = release
    bundle = json.loads(raw)
    bundle.update(change)
    raw = json.dumps(bundle).encode()
    config["releases"][0]["bundle_sha256"] = hashlib.sha256(raw).hexdigest()
    result = request(
        mod.create_app(config, fetch=lambda *a, **k: raw),
        {"dataset_revision": DATA_REV},
    )
    assert result["status"] == 502


def test_config_requires_unambiguous_revision_and_resource_inputs(release):
    config, _ = release
    config["releases"].append(dict(config["releases"][0]))
    with pytest.raises(ValueError, match="Ambiguous"):
        mod.create_app(config)
    config["releases"].pop()
    config["limits"]["request_bytes"] = True
    with pytest.raises(ValueError, match="resource limits"):
        mod.create_app(config)
    config["limits"] = []
    with pytest.raises(TypeError):
        mod.create_app(config)


def test_repeated_request_is_byte_stable(release):
    config, raw = release
    app = mod.create_app(config, fetch=lambda *a, **k: raw)
    assert request(app, {"dataset_revision": DATA_REV}) == request(
        app, {"dataset_revision": DATA_REV}
    )


def test_server_startup_uses_required_manifest_and_explicit_bind(
    release, tmp_path, monkeypatch
):
    config, _ = release
    path = tmp_path / "approved-releases.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("EXPLORER_RENDER_MANIFEST", str(path))
    monkeypatch.delenv("BIND_HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    calls = []

    class Server:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def serve_forever(self):
            calls.append("serve")

    def server(bind, port, app):
        # Local binding is the authored safe default. The exposed default port
        # follows https://huggingface.co/docs/hub/spaces-sdks-docker.
        calls.append((bind, port, callable(app)))
        return Server()

    monkeypatch.setattr(mod, "make_server", server)
    mod.main()
    assert calls == [("localhost", 7860, True), "serve"]
    calls.clear()
    monkeypatch.setenv("BIND_HOST", "configured-interface")
    monkeypatch.setenv("PORT", "8000")  # Synthetic operational input.
    mod.main()
    assert calls == [("configured-interface", 8000, True), "serve"]
