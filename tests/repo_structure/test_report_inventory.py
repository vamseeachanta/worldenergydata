"""Report classification, reproducibility and publication agreement."""

import hashlib
import importlib.util
import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path, PureWindowsPath

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/maintenance/classify_report_inventory.py"
BUILDER = ROOT / "scripts/build_pages.py"


def inventory_module():
    assert SCRIPT.is_file(), "The reproducible classification script is missing"
    spec = importlib.util.spec_from_file_location("inventory", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def put(root, path, text="<!doctype html>"):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "path,text,replacement,expected",
    [
        ("reports/completion/index.html", "", None, "current"),
        ("reports/completion/report_demo.html", "", None, "current"),
        ("reports/unpublished_demo.html", "", None, "one-off"),
        ("reports/unknown.html", "", None, "undetermined"),
        (
            "reports/old.html",
            '<link rel="successor-version" href="new.html">',
            "reports/new.html",
            "superseded",
        ),
        (
            "reports/old.html",
            '<link rel="successor-version" href="missing.html">',
            None,
            "undetermined",
        ),
        (
            "reports/completion/report_demo.html",
            '<link rel="successor-version" href="new.html">',
            "reports/completion/new.html",
            "superseded",
        ),
        (
            "reports/old.html",
            "Replaced by new.html",
            "reports/new.html",
            "undetermined",
        ),
        (
            "reports/old.html",
            '<link rel="successor-version" href="../../outside.html">',
            None,
            "undetermined",
        ),
    ],
)
def test_rule_order_and_evidence(tmp_path, path, text, replacement, expected):
    module = inventory_module()
    put(tmp_path, "reports/completion/index.html")
    put(tmp_path, path, text)
    if replacement:
        put(tmp_path, replacement)
    rows = {row["path"]: row for row in module.classify_tree(tmp_path, BUILDER)}
    assert rows[path]["classification"] == expected
    if expected == "superseded":
        assert replacement in rows[path]["evidence"]


def test_publication_gate(tmp_path):
    module = inventory_module()
    path = "reports/field-atlas/onepagers/field.html"
    put(tmp_path, path)
    assert (
        module.classify_tree(tmp_path, BUILDER)[0]["classification"] == "undetermined"
    )
    put(tmp_path, "reports/field-atlas/index.html")
    assert all(
        r["classification"] == "current"
        for r in module.classify_tree(tmp_path, BUILDER)
    )


def test_builder_agreement(tmp_path, monkeypatch):
    module = inventory_module()
    from scripts import build_pages as builder

    # Execute the real builder, recording copies; all writes land in tmp_path.
    # Its presentation functions read frozen inputs and perform no network I/O.
    monkeypatch.setattr(builder, "PUBLIC", tmp_path)
    monkeypatch.setattr(builder, "ASSETS", tmp_path / "assets")
    observed = set()
    for name in ("copyfile", "copy2", "copytree"):
        original = getattr(builder.shutil, name)

        def record(src, dst, *args, _original=original, **kwargs):
            source = Path(src)
            inputs = source.rglob("*.html") if source.is_dir() else [source]
            observed.update(
                p.relative_to(ROOT).as_posix()
                for p in inputs
                if p.is_file()
                and p.suffix == ".html"
                and p.is_relative_to(ROOT / "reports")
            )
            return _original(src, dst, *args, **kwargs)

        monkeypatch.setattr(builder.shutil, name, record)
    builder.build()
    assert observed, "No report publication was observed"
    rows = {row["path"]: row for row in module.classify_tree(ROOT, BUILDER)}
    assert {
        p
        for p in observed
        if rows[p]["classification"] not in {"current", "unverified"}
    } == set()


@pytest.mark.artifact_currency
def test_committed_csv_matches(capsys):
    module = inventory_module()
    assert module.main(["--check"]) == 0
    assert (
        ROOT / "docs/modules/report-inventory.csv"
    ).read_bytes() == module.inventory_bytes(ROOT)


def test_deterministic_output(tmp_path):
    module = inventory_module()
    put(tmp_path, "reports/z_test.html")
    put(tmp_path, "reports/a.html")
    first = module.inventory_bytes(tmp_path, BUILDER)
    second = module.inventory_bytes(tmp_path, BUILDER)
    assert first == second
    assert b"\r" not in first


def test_check_rejects_stale_csv(tmp_path, monkeypatch):
    module = inventory_module()
    target = put(tmp_path, "docs/modules/report-inventory.csv", "stale")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "BUILDER", BUILDER)
    assert module.main(["--check"]) == 1
    assert target.read_text() == "stale"


def test_removed_domain_is_not_current(tmp_path):
    module = inventory_module()
    source = BUILDER.read_text(encoding="utf-8")
    assert '"hse": build_hse,' in source
    changed_builder = put(
        tmp_path,
        "scripts/build_pages.py",
        source.replace('    "hse": build_hse,\n', ""),
    )
    put(tmp_path, "reports/hse/card.html")
    rows = module.classify_tree(tmp_path, changed_builder)
    assert rows[0]["classification"] == "undetermined"


class WindowsOrderedPath(type(Path())):
    """Use Windows path ordering while reading the native temporary tree."""

    def __lt__(self, other):
        return PureWindowsPath(self.as_posix()) < PureWindowsPath(other.as_posix())


class WindowsHtmlPath(type(Path())):
    """Emulate case-insensitive HTML glob matches over the native test tree."""

    def glob(self, pattern):
        candidates = super().glob(pattern[:-5] + ".*")
        return (path for path in candidates if path.suffix.lower() == ".html")

    def rglob(self, pattern):
        candidates = super().rglob(pattern[:-5] + ".*")
        return (path for path in candidates if path.suffix.lower() == ".html")


@pytest.mark.parametrize("path_type", [Path, WindowsHtmlPath])
def test_inventory_requires_lowercase_html_suffix(tmp_path, path_type):
    module = inventory_module()
    paths = [
        "reports/completion/index.html",
        "reports/completion/uppercase.HTML",
        "reports/completion/mixed.Html",
        "reports/ordinary.html",
        "reports/unselected.HTML",
    ]
    originals = {path: put(tmp_path, path).read_bytes() for path in paths}
    rows = module.classify_tree(path_type(tmp_path), BUILDER)
    assert {row["path"]: row["classification"] for row in rows} == {
        "reports/completion/index.html": "current",
        "reports/ordinary.html": "undetermined",
    }
    assert {path: (tmp_path / path).read_bytes() for path in paths} == originals


@pytest.mark.parametrize("path_type", [Path, WindowsOrderedPath])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_portable_inventory_bytes(tmp_path, path_type, newline):
    """Issue #1355: derive exact bytes independently from literal fixture rows.

    Repository-relative string order is Zebra.html, alpha.html, alpha/card.html, zulu.html:
    uppercase Z precedes lowercase a, and '.' precedes '/'. Every fixture is
    unselected, with no replacement or demo/test token: see the final rule in
    docs/modules/repository-architecture.md, 'Report classification rules'.
    LF and CRLF report inputs are equivalent; names differ beyond case so the
    fixture also works on case-insensitive filesystems.
    """
    module = inventory_module()
    paths = [
        "reports/zulu.html",
        "reports/alpha/card.html",
        "reports/alpha.html",
        "reports/Zebra.html",
    ]
    originals = {}
    for path in paths:
        target = put(tmp_path, path)
        target.write_bytes(("<!doctype html>" + newline).encode("utf-8"))
        originals[path] = target.read_bytes()
    root = path_type(tmp_path)
    expected = (
        b"path,classification,evidence\n"
        b"reports/Zebra.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
        b"reports/alpha.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
        b"reports/alpha/card.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
        b"reports/zulu.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
    )
    assert module.inventory_bytes(root, BUILDER) == expected
    assert {path: (tmp_path / path).read_bytes() for path in paths} == originals


def _inventory_git_environment(environment: dict[str, str]) -> dict[str, str]:
    isolated = {k: v for k, v in environment.items() if not k.startswith("GIT_")}
    isolated.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_ATTR_NOSYSTEM="1",
    )
    return isolated


def _inventory_checkout_bytes(
    caller_root: Path, checkout_root: Path, autocrlf: str
) -> tuple[bytes, bytes]:
    if autocrlf not in {"false", "true"}:
        raise ValueError("autocrlf must be false or true")
    caller_root = caller_root.resolve(strict=True)
    if checkout_root.exists():
        raise FileExistsError(checkout_root)
    environment = _inventory_git_environment(dict(os.environ))

    def git(*arguments, cwd=caller_root, input=None):
        trust = ["-c", f"safe.directory={caller_root}"] if cwd == caller_root else []
        return subprocess.check_output(
            ["git", "-c", f"core.attributesFile={os.devnull}", *trust, *arguments],
            cwd=cwd,
            env=environment,
            input=input,
        )

    reported_root = git("rev-parse", "--show-toplevel").decode().strip()
    if Path(reported_root).resolve(strict=True) != caller_root:
        raise ValueError("caller root must be the repository top level")
    commit = git("rev-parse", "HEAD").decode().strip()
    path = "docs/modules/report-inventory.csv"
    entry = git("ls-tree", "-z", commit, "--", path)
    header, name = entry.rstrip(b"\0").split(b"\t")
    mode, kind, object_id = header.decode().split()
    assert kind == "blob" and name.decode() == path
    blob = git("cat-file", "blob", object_id)
    attributes = git("cat-file", "blob", f"{commit}:.gitattributes")
    git("init", "--quiet", "--template=", str(checkout_root), cwd=checkout_root.parent)
    (checkout_root / ".gitattributes").write_bytes(attributes)
    inserted = (
        git(
            "hash-object",
            "-w",
            "--stdin",
            "--no-filters",
            cwd=checkout_root,
            input=blob,
        )
        .decode()
        .strip()
    )
    git(
        "update-index",
        "--add",
        "--cacheinfo",
        f"{mode},{inserted},{path}",
        cwd=checkout_root,
    )
    git(
        "-c",
        f"core.autocrlf={autocrlf}",
        "-c",
        "core.eol=lf",
        "-c",
        "core.safecrlf=false",
        "checkout-index",
        "--all",
        cwd=checkout_root,
    )
    return blob, (checkout_root / path).read_bytes()


@pytest.mark.parametrize("autocrlf", ["false", "true"])
@pytest.mark.parametrize("inherited_git", [False, True])
def test_inventory_checkout_is_lf(autocrlf, inherited_git, tmp_path, monkeypatch):
    """Compare committed LF bytes with an isolated real Git checkout."""
    if inherited_git:
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
            monkeypatch.setenv(key, str(tmp_path / key))
    blob, checkout = _inventory_checkout_bytes(ROOT, tmp_path / "checkout", autocrlf)
    assert b"\r" not in checkout
    assert checkout == blob


@pytest.fixture
def hostile_inventory(tmp_path):
    """Bootstrap real repositories without depending on the probe helpers."""
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_ATTR_NOSYSTEM="1",
    )

    def git(*args, cwd=ROOT):
        return subprocess.check_output(
            [
                "git",
                "-c",
                f"core.attributesFile={os.devnull}",
                "-c",
                f"safe.directory={ROOT.resolve(strict=True)}",
                *args,
            ],
            cwd=cwd,
            env=environment,
        )

    caller, decoy = tmp_path / "caller repo", tmp_path / "decoy repo"
    path = "docs/modules/report-inventory.csv"
    for repo in (caller, decoy):
        git(
            "clone",
            "--quiet",
            "--shared",
            "--no-checkout",
            "--template=",
            str(ROOT),
            str(repo),
        )
        git("checkout", "HEAD", "--", path, ".gitattributes", cwd=repo)
    script = tmp_path / "filter script.py"
    script.write_text(
        "import sys\n"
        "data = sys.stdin.buffer.read().replace(b'\\r\\n', b'\\n')\n"
        "sys.stdout.buffer.write(data.replace(b'\\n', b'\\r\\n'))\n",
        encoding="utf-8",
    )
    attributes, config = tmp_path / "external attributes", tmp_path / "external config"
    attributes.write_text(f"{path} filter=crlf\n", encoding="utf-8")
    command = " ".join(
        shlex.quote(str(p).replace("\\", "/")) for p in (sys.executable, script)
    )
    git("config", "--file", str(config), "core.attributesFile", str(attributes))
    git("config", "--file", str(config), "filter.crlf.smudge", command)
    git("config", "--file", str(config), "filter.crlf.required", "true")
    return caller, decoy, config, attributes, path


@pytest.mark.parametrize("autocrlf", ["false", "true"])
def test_inventory_checkout_rejects_external_filter(
    tmp_path, monkeypatch, hostile_inventory, autocrlf
):
    caller, _, config, _, path = hostile_inventory
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    environment = {
        k: v
        for k, v in os.environ.items()
        if k not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"}
    }
    control = subprocess.check_output(
        [
            "git",
            "-c",
            f"core.autocrlf={autocrlf}",
            "cat-file",
            "--filters",
            f"HEAD:{path}",
        ],
        cwd=caller,
        env=environment,
    )
    assert b"\r\n" in control, "The external filter must be active"
    monkeypatch.setitem(globals(), "ROOT", caller)
    test_inventory_checkout_is_lf(autocrlf, False, tmp_path, monkeypatch)


def test_inventory_checkout_git_boundary(tmp_path, monkeypatch, hostile_inventory):
    caller, _, _, _, _ = hostile_inventory
    original, calls = subprocess.check_output, []

    def record(arguments, **kwargs):
        calls.append((arguments, kwargs["cwd"], kwargs["env"].copy()))
        return original(arguments, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", record)
    for present in (False, True):
        calls.clear()
        with monkeypatch.context() as context:
            if present:
                context.setenv("HOME", str(tmp_path / "unchanged home"))
            else:
                context.delenv("HOME", raising=False)
            context.setenv("GIT_CONFIG_COUNT", "1")
            context.setenv("GIT_CONFIG_KEY_0", "core.autocrlf")
            context.setenv("GIT_CONFIG_VALUE_0", "true")
            parent = dict(os.environ)
            blob, checkout = _inventory_checkout_bytes(
                caller, tmp_path / f"boundary-{present}", "true"
            )
            assert checkout == blob
            assert dict(os.environ) == parent
            assert calls
            for arguments, cwd, environment in calls:
                trust = [a for a in arguments if a.startswith("safe.directory=")]
                assert trust == (
                    [f"safe.directory={caller.resolve(strict=True)}"]
                    if cwd == caller.resolve()
                    else []
                )
                assert arguments[:3] == [
                    "git",
                    "-c",
                    f"core.attributesFile={os.devnull}",
                ]
                assert {
                    k: v for k, v in environment.items() if k.startswith("GIT_")
                } == {
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_SYSTEM": os.devnull,
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_ATTR_NOSYSTEM": "1",
                }
                assert {
                    k: v for k, v in environment.items() if not k.startswith("GIT_")
                } == {k: v for k, v in parent.items() if not k.startswith("GIT_")}
                if "init" in arguments:
                    assert "--template=" in arguments
                    assert trust == []
                    assert cwd != caller.resolve()
            assert any(cwd == caller.resolve() for _, cwd, _ in calls)
            assert any(cwd != caller.resolve() for _, cwd, _ in calls)
    with pytest.raises(ValueError, match="autocrlf"):
        _inventory_checkout_bytes(caller, tmp_path / "invalid", "input")
    with pytest.raises(FileExistsError):
        _inventory_checkout_bytes(caller, caller, "false")
    with pytest.raises(ValueError, match="root"):
        _inventory_checkout_bytes(caller / "docs", tmp_path / "nested", "false")


def test_inventory_checkout_preserves_caller_state(
    tmp_path, monkeypatch, hostile_inventory
):
    caller, decoy, config, attributes, path = hostile_inventory

    def snapshot(root):
        return {
            p.relative_to(root).as_posix(): (
                stat.S_IFMT(p.lstat().st_mode),
                (
                    os.readlink(p)
                    if p.is_symlink()
                    else (
                        hashlib.sha256(p.read_bytes()).hexdigest()
                        if p.is_file()
                        else None
                    )
                ),
            )
            for p in root.rglob("*")
        }

    before = {repo: snapshot(repo) for repo in (caller, decoy)}
    external = {p: p.read_bytes() for p in (config, attributes)}
    template = tmp_path / "hostile template"
    template.mkdir()
    (template / "sentinel").write_text("must not be copied", encoding="utf-8")
    parent = dict(os.environ)
    with monkeypatch.context() as context:
        injections = {
            "GIT_DIR": str(decoy / ".git"),
            "GIT_WORK_TREE": str(decoy),
            "GIT_COMMON_DIR": str(decoy / ".git"),
            "GIT_INDEX_FILE": str(decoy / ".git/index"),
            "GIT_OBJECT_DIRECTORY": str(decoy / ".git/objects"),
            "GIT_CONFIG_GLOBAL": str(config),
            "GIT_CONFIG_SYSTEM": str(config),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.eol",
            "GIT_CONFIG_VALUE_0": "crlf",
            "GIT_CONFIG_PARAMETERS": "'core.autocrlf=true'",
            "GIT_TEMPLATE_DIR": str(template),
        }
        for key, value in injections.items():
            context.setenv(key, value)
        during = {repo: snapshot(repo) for repo in before}
        assert during == before
        hostile_parent = dict(os.environ)
        target = tmp_path / "checkout"
        blob, checkout = _inventory_checkout_bytes(caller, target, "true")
        assert checkout == blob
        assert dict(os.environ) == hostile_parent
        assert {repo: snapshot(repo) for repo in before} == during
        assert {p: p.read_bytes() for p in external} == external
        assert not list(target.rglob("sentinel"))
        working = {
            p.relative_to(target).as_posix(): p.read_bytes()
            for p in target.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(target).parts
        }
        assert working == {
            path: blob,
            ".gitattributes": (caller / ".gitattributes").read_bytes(),
        }
        metadata = snapshot(target / ".git")
        assert {"HEAD", "config", "index"} <= metadata.keys()
        git_environment = _inventory_git_environment(dict(os.environ))
        index = subprocess.check_output(
            ["git", "-c", f"core.attributesFile={os.devnull}", "ls-files", "--stage"],
            cwd=target,
            env=git_environment,
        )
        object_id = hashlib.sha1(
            b"blob " + str(len(blob)).encode() + b"\0" + blob
        ).hexdigest()
        assert index == f"100644 {object_id} 0\t{path}\n".encode()
        assert f"objects/{object_id[:2]}/{object_id[2:]}" in metadata
    assert dict(os.environ) == parent
    assert {repo: snapshot(repo) for repo in before} == before


@pytest.mark.parametrize("change", ["crlf", "content", "order"])
def test_check_preserves_byte_equality(tmp_path, monkeypatch, change):
    """Issue #1355 requires byte equality, including row order and line endings.

    Each mutation independently changes the canonical bytes: CRLF adds CR;
    content substitutes a classification; order reverses the two data rows.
    --check must reject each without writing; --write must restore LF bytes.
    """
    module = inventory_module()
    put(tmp_path, "reports/a.html")
    put(tmp_path, "reports/z.html")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "BUILDER", BUILDER)
    canonical = (
        b"path,classification,evidence\n"
        b"reports/a.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
        b"reports/z.html,undetermined,"
        b"no decisive publication or replacement evidence under these rules\n"
    )
    if change == "crlf":
        changed = canonical.replace(b"\n", b"\r\n")
    elif change == "content":
        changed = canonical.replace(b"undetermined", b"current")
    else:
        header, first, second = canonical.splitlines(keepends=True)
        changed = header + second + first
    target = put(tmp_path, module.INVENTORY)
    target.write_bytes(changed)
    assert module.main(["--check"]) == 1
    assert target.read_bytes() == changed
    assert module.main(["--write"]) == 0
    assert target.read_bytes() == canonical
    assert module.main(["--check"]) == 0
