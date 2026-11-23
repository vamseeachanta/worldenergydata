import shutil
from pathlib import Path

import pytest

from tests.unit.cost import test_big_foot_cost_output_hardening as hardening


@pytest.fixture()
def squashed_repo(tmp_path: Path) -> tuple[Path, Path, Path, str, str, str]:
    origin = tmp_path / "origin"
    for relative in hardening._builder().INPUT_PATHS:
        target = origin / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(hardening.ROOT / relative, target)
    hardening._git(origin, "init", "-q")
    hardening._git(origin, "config", "user.email", "test@example.com")
    hardening._git(origin, "config", "user.name", "Test")
    hardening._git(origin, "add", ".")
    hardening._git(origin, "commit", "-qm", "durable producer")
    producer = hardening._git(origin, "rev-parse", "HEAD")
    main = hardening._git(origin, "branch", "--show-current")

    hardening._git(origin, "checkout", "-qb", "unrelated")
    (origin / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
    hardening._git(origin, "add", "unrelated.txt")
    hardening._git(origin, "commit", "-qm", "unrelated")
    nonancestor = hardening._git(origin, "rev-parse", "HEAD")
    hardening._git(origin, "checkout", "-q", main)

    hardening._git(origin, "checkout", "-qb", "feature")
    (origin / "artifact.txt").write_text("artifact\n", encoding="utf-8")
    hardening._git(origin, "add", "artifact.txt")
    hardening._git(origin, "commit", "-qm", "feature artifact")
    orphan = hardening._git(origin, "rev-parse", "HEAD")
    hardening._git(origin, "checkout", "-q", main)
    hardening._git(origin, "merge", "--squash", "feature")
    hardening._git(origin, "commit", "-qm", "synthetic squash")
    squash = hardening._git(origin, "rev-parse", "HEAD")
    assert hardening._git(origin, "show", "-s", "--format=%P", squash) == producer
    hardening._git(origin, "branch", "-D", "feature")
    baseline = tmp_path / "baseline"
    hardening._generate(origin, baseline, producer)
    root = tmp_path / "shallow"
    hardening._git(tmp_path, "clone", "-q", "--depth", "1", origin.as_uri(), str(root))
    assert hardening._git(root, "rev-parse", "--is-shallow-repository") == "true"
    assert hardening._git(root, "rev-parse", "HEAD") == squash
    assert hardening._git(root, "show", "-s", "--format=%P", "HEAD") == ""
    assert not hardening._has_commit(root, producer)
    assert not hardening._has_commit(root, orphan)
    refs = hardening._git(origin, "for-each-ref", "--format=%(refname)", "refs/heads")
    assert "refs/heads/feature" not in refs.splitlines()
    return origin, root, baseline, producer, orphan, nonancestor


def test_durable_producer_survives_squash_and_missing_origin(
    squashed_repo, tmp_path: Path
) -> None:
    origin, root, baseline, producer, _, _ = squashed_repo
    hardening._git(root, "remote", "remove", "origin")
    with pytest.raises(ValueError, match="trusted producer history"):
        hardening.hydrate_trusted_producer_history(root, producer)
    hardening._git(root, "remote", "add", "origin", origin.as_uri())
    hardening.hydrate_trusted_producer_history(root, producer)
    hydrated = tmp_path / "hydrated"
    hardening._generate(root, hydrated, producer)
    assert all(
        (baseline / item).read_bytes() == (hydrated / item).read_bytes()
        for item in (hardening.HTML, hardening.CSV, hardening.MANIFEST)
    )


@pytest.mark.parametrize("producer_kind", ("orphan", "fabricated"))
def test_unavailable_producer_rejects(squashed_repo, producer_kind: str) -> None:
    _, root, _, _, orphan, _ = squashed_repo
    producer = orphan if producer_kind == "orphan" else "f" * 40
    with pytest.raises(ValueError, match="producer commit remains unavailable"):
        hardening.hydrate_trusted_producer_history(root, producer)
    assert hardening._git(root, "rev-parse", "--is-shallow-repository") == "false"


def test_existing_nonancestor_producer_rejects(squashed_repo) -> None:
    _, root, _, _, _, nonancestor = squashed_repo
    hardening._git(root, "fetch", "--depth", "2", "origin", "unrelated")
    assert hardening._has_commit(root, nonancestor)
    with pytest.raises(ValueError, match="trusted producer history"):
        hardening.hydrate_trusted_producer_history(root, nonancestor)
