"""Adapter and CLI tests: all external effects use recording fakes."""

import importlib.util
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts/hf_export"
sys.path.insert(0, str(SCRIPTS))
import explorer_snapshot as snapshot
import publish_explorer_snapshot_to_hf as publisher


class Response(io.BytesIO):
    def __init__(self, data, sha):
        super().__init__(data)
        self.headers = {"x-repo-commit": sha}


def test_hf_atomic_parent_commit(monkeypatch):
    calls = []

    class Operation:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Api:
        def __init__(self, **kwargs):
            assert set(kwargs) == {"token"}

        def create_commit(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(oid="b" * 40)

    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(HfApi=Api, CommitOperationAdd=Operation),
    )
    client = publisher.HuggingFaceBackend("synthetic-auth")
    assert (
        client.commit("namespace/dataset", "a" * 40, {"fields.json": b"[]\n"})
        == "b" * 40
    )
    assert len(calls) == 1
    assert calls[0]["parent_commit"] == "a" * 40
    assert calls[0]["repo_type"] == "dataset"
    operation = calls[0]["operations"][0]
    assert operation.path_in_repo == "fields.json"
    assert operation.path_or_fileobj == b"[]\n"


def test_exact_public_read_and_header(monkeypatch):
    requests = []

    def open_request(request):
        requests.append(request)
        return Response(b"[]\n", "b" * 40)

    monkeypatch.setattr(publisher, "_open_public", open_request)
    client = publisher.HuggingFaceBackend("synthetic-auth")
    assert client.read("namespace/dataset", "b" * 40, "fields.json") == b"[]\n"
    assert requests[0].full_url == snapshot.resolve_url(
        "namespace/dataset", "b" * 40, "fields.json"
    )
    assert "Authorization" not in requests[0].headers
    monkeypatch.setattr(
        publisher, "_open_public", lambda _: Response(b"[]\n", "c" * 40)
    )
    with pytest.raises(ValueError):
        client.read("namespace/dataset", "b" * 40, "fields.json")


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/steal",
        "http://huggingface.co/file",
        "https://" + "user:pass@" + "huggingface.co/file",
    ],
)
def test_redirects_fail_closed(url):
    handler = publisher.PublicRedirect()
    from urllib.request import Request

    with pytest.raises(ValueError):
        handler.redirect_request(
            Request("https://huggingface.co/file"), None, 302, "redirect", {}, url
        )


def test_cli_dry_run_is_write_free_without_sdk_or_auth(monkeypatch, capsys):
    monkeypatch.setattr(publisher, "build_from_git", lambda *a: {"synthetic": b"data"})
    monkeypatch.setattr(
        publisher, "publish_snapshot", lambda *a, **kw: {"publication": "not_published"}
    )
    monkeypatch.setattr(
        publisher, "HuggingFaceBackend", lambda *a: pytest.fail("network client")
    )
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert (
        publisher.main(
            [
                "--config",
                "admission.json",
                "--source-sha",
                "a" * 40,
                "--dataset-id",
                "namespace/dataset",
                "--dry-run",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["publication"] == "not_published"


def test_cli_failure_is_redacted(monkeypatch, capsys):
    def fail(*args):
        raise RuntimeError("synthetic-sensitive-detail")

    monkeypatch.setattr(publisher, "build_from_git", fail)
    assert (
        publisher.main(
            [
                "--config",
                "admission.json",
                "--source-sha",
                "a" * 40,
                "--dataset-id",
                "namespace/dataset",
            ]
        )
        == 1
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == (
        "Snapshot failed; no verified publication receipt was produced.\n"
    )


@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectError])
def test_cli_transport_failure_is_redacted(monkeypatch, capsys, error_type):
    monkeypatch.setattr(publisher, "build_from_git", lambda *a: {"synthetic": b"data"})

    def fail(*args, **kwargs):
        raise error_type("synthetic-sensitive-detail")

    monkeypatch.setattr(publisher, "publish_snapshot", fail)
    assert (
        publisher.main(
            [
                "--config",
                "admission.json",
                "--source-sha",
                "a" * 40,
                "--dataset-id",
                "namespace/dataset",
            ]
        )
        == 1
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == (
        "Snapshot failed; no verified publication receipt was produced.\n"
    )


def test_cli_missing_git_input_is_redacted(monkeypatch, capsys):
    run = snapshot.subprocess.run
    source_sha = run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
    ).stdout.decode().strip()

    def clean_preflight(args, **kwargs):
        # Permit this test's edited checkout; Git object reads remain real.
        if args[3:] == ["status", "--porcelain", "--untracked-files=all"]:
            return SimpleNamespace(stdout=b"")
        return run(args, **kwargs)

    monkeypatch.setattr(snapshot.subprocess, "run", clean_preflight)
    assert (
        publisher.main(
            [
                "--repo",
                str(REPO),
                "--config",
                "missing-admission-for-cli-test.json",
                "--source-sha",
                source_sha,
                "--dataset-id",
                "namespace/dataset",
            ]
        )
        == 1
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == (
        "Snapshot failed; no verified publication receipt was produced.\n"
    )


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("stage", ["build_from_git", "publish_snapshot"])
def test_cli_process_interruptions_propagate(monkeypatch, capsys, interruption, stage):
    monkeypatch.setattr(publisher, "build_from_git", lambda *a: {"synthetic": b"data"})

    def interrupt(*args, **kwargs):
        raise interruption()

    monkeypatch.setattr(publisher, stage, interrupt)
    with pytest.raises(interruption):
        publisher.main(
            [
                "--config",
                "admission.json",
                "--source-sha",
                "a" * 40,
                "--dataset-id",
                "namespace/dataset",
            ]
        )
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == ""


def test_legacy_entrypoint_requires_full_build(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "legacy", SCRIPTS / "publish_explorer_refresh_to_hf.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "argv", ["publisher", "--dry-run"])
    with pytest.raises(SystemExit):
        module.main()


def test_redirect_within_public_hf_origin():
    from urllib.request import Request

    handler = publisher.PublicRedirect()
    request = handler.redirect_request(
        Request("https://huggingface.co/file"),
        None,
        302,
        "redirect",
        {},
        "https://huggingface.co/api/resolve-cache/file",
    )
    assert request.full_url == "https://huggingface.co/api/resolve-cache/file"
    assert "Authorization" not in request.headers


@pytest.mark.parametrize(
    "extra,env",
    [
        (["--publish"], None),
        (["--publish", "--accept-json-migration"], None),
        (["--publish", "--accept-json-migration", "--expected-parent", "a" * 40], None),
    ],
)
def test_live_preflight_requires_migration_parent_and_auth(
    monkeypatch, capsys, extra, env
):
    monkeypatch.setattr(publisher, "build_from_git", lambda *a: {"synthetic": b"data"})
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert (
        publisher.main(
            [
                "--config",
                "admission.json",
                "--source-sha",
                "a" * 40,
                "--dataset-id",
                "namespace/dataset",
                *extra,
            ]
        )
        == 1
    )
    output = capsys.readouterr()
    assert not output.out
    assert "no verified publication receipt" in output.err
