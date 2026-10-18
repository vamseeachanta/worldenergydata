"""The fetcher must refuse unlicensed, oversized or altered payloads."""

import importlib.util
import io
import json
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "scripts/metocean/fetch_bias_correction_benchmark.py"
)


def load_fetcher():
    spec = importlib.util.spec_from_file_location("benchmark_fetch", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("license", [None, "unknown", "all-rights-reserved"])
def test_refuse_unverified_license_before_payload_download(
    tmp_path, monkeypatch, license
):
    module = load_fetcher()
    metadata = {"metadata": {"license": {"id": license}}}
    calls = []

    def opener(url, **kwargs):
        calls.append(url)
        return io.BytesIO(json.dumps(metadata).encode())

    monkeypatch.setattr(module, "urlopen", opener)
    with pytest.raises(ValueError, match="licen"):
        module.fetch(tmp_path)
    assert calls == [module.SPEC["metadata_url"]]
    assert not list(tmp_path.iterdir())


def test_refuse_changed_archive_and_leave_destination_empty(tmp_path, monkeypatch):
    module = load_fetcher()
    calls = []

    def opener(url, **kwargs):
        calls.append(url)
        if url == module.SPEC["metadata_url"]:
            return io.BytesIO(
                json.dumps({"metadata": {"license": {"id": "cc-by-4.0"}}}).encode()
            )
        return io.BytesIO(b"changed")

    monkeypatch.setattr(module, "urlopen", opener)
    with pytest.raises(ValueError, match="size|digest"):
        module.fetch(tmp_path)
    assert len(calls) == 2
    assert not list(tmp_path.iterdir())


def test_refuse_repository_destination_before_network(tmp_path, monkeypatch):
    module = load_fetcher()

    def opener(*args, **kwargs):
        pytest.fail("No download is permitted into the repository")

    monkeypatch.setattr(module, "urlopen", opener)
    with pytest.raises(ValueError, match="outside"):
        module.fetch(module.ROOT / "data/benchmark")


def test_refuse_size_limit_before_payload_download(tmp_path, monkeypatch):
    module = load_fetcher()
    module.SPEC["file"]["bytes"] = 100_000_000
    calls = []

    def opener(url, **kwargs):
        calls.append(url)
        return io.BytesIO(
            json.dumps({"metadata": {"license": {"id": "cc-by-4.0"}}}).encode()
        )

    monkeypatch.setattr(module, "urlopen", opener)
    with pytest.raises(ValueError, match="limit"):
        module.fetch(tmp_path)
    assert len(calls) == 1


def test_refuse_same_size_bad_digest(tmp_path, monkeypatch):
    module = load_fetcher()
    module.SPEC["file"]["bytes"] = 7

    def opener(url, **kwargs):
        if url == module.SPEC["metadata_url"]:
            return io.BytesIO(
                json.dumps({"metadata": {"license": {"id": "cc-by-4.0"}}}).encode()
            )
        return io.BytesIO(b"changed")

    monkeypatch.setattr(module, "urlopen", opener)
    with pytest.raises(ValueError, match="digest"):
        module.fetch(tmp_path)
    assert not list(tmp_path.iterdir())
