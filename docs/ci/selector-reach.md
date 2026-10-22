# Selector reachability and explanation

## Summary

These stdlib tools inventory the current selector without changing its routing or
required checks. They remain advisory until the maintainer enables a CI guard.
Path coverage does not prove pytest collection, successful imports or execution.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-22 | Document advisory reachability, static dependents and diff explanations. |

## Audit a checkout

Run from the repository root with a scratch directory outside the checkout:

```sh
python scripts/ci/audit_selector_reach.py --json "$TMPDIR/selector-reach.json" > "$TMPDIR/selector-reach.txt"
python scripts/ci/package_closure.py > "$TMPDIR/package-closure.json"
```

The audit imports `scripts/ci/select_test_targets.py` by path. For every filename
matching `test_*.py` or `*_test.py` beneath `tests/` or `packages/*/tests/`, it
simulates a diff containing only that path. A file is reachable when its selected
scope is not `full` and a target equals that file or is one of its parent
directories. Archived tests are inventoried even when pytest excludes them.
This is **self-diff reachability**: an orphan might still run for some other
contract route or a full run. It is not proof that no possible diff can reach it.

The source table separately simulates every file beneath each member's `src/`
and each `src/worldenergydata/<module>/`. JSON records include probes, scopes,
all targets, targets beyond the always-on set, existing unit homes, and whether
any target was selected. Members without source files are `NOT_EVALUATED`.
Always-on targets must not be mistaken for module-specific coverage.

The initial tree inspection confirms no `tests/unit/` home for `base_configs`,
`testing` or `workflow_api`. `base_configs` is a core route requesting `full`;
the other two select always-on tests without a module home. Top-level
`tests/drilling`, `tests/hse`, `tests/marine`, `tests/reservoir`, `tests/scheduler`
and `tests/_archive` exist outside `tests/unit` and `tests/modules`. Re-run the
audit to inspect the current checkout rather than treating these observations
as permanent routing policy.

## Read the allow-list

`scripts/ci/selector_reach_allowlist.txt` has one **exact test file** per line,
followed by `# reason: ...`. Archived files use `# reason: archived`.
Directories, glob patterns, duplicate entries and entries without reasons are
rejected. Listing an old orphan does not permit a new sibling automatically.
Review the cause before adding an exception; remove entries after routing is
repaired. The guard permits stale entries temporarily so another selector PR
can repair reachability without having to edit this list in the same change.

Run the guard manually:

```sh
uv run --no-project --with pytest python -m pytest tests/ci/test_audit_selector_reach.py --noconftest -o addopts='' -q -p no:cacheprovider --basetemp="$TMPDIR/reach-tests"
```

No workflow or existing selector file changes here. The guard lives in
`tests/ci/`; maintainers can explicitly enable it in their CI selection. The
current selector does not select that directory for its own test-only changes.

## Static package dependents

`package_closure.py` parses workspace Python files with `ast`; it never imports
application code. An edge points from importer to provider. `dependents(package,
imports)` is a pure function over that explicit graph and returns direct and
transitive reverse importers, excluding the queried package even in a cycle.
The CLI reports both direct and transitive dependents for every member.

Ownership comes from member source paths and the longest matching module
prefix. Relative imports are resolved against the importing package. All
syntactic imports count, including optional and type-checking branches.
Ambiguous shared namespace imports provide no edge; dynamic imports, plugins,
root-distribution imports, metadata dependencies and non-Python dependencies
are outside this static inventory. Parse failures are listed as
`not_evaluated` by path, line and error kind; resulting closure is incomplete.

The tests record the current missing dependent-selection behavior as
`xfail(strict=True)`, both for a hand-built chain and for the real workspace.
An eventual selector fix makes these tests unexpectedly pass and requires
removing the corresponding expected-failure marker. Ordinary audit, graph and
explanation assertions remain normal failures.

## Explain a diff

```sh
python scripts/ci/explain_selection.py --base origin/main --head HEAD
git diff --name-status --find-renames origin/main HEAD > "$TMPDIR/changes.txt"
python scripts/ci/explain_selection.py --files-from "$TMPDIR/changes.txt"
```

Ref mode uses a two-tip `git diff BASE HEAD`, not a merge-base diff. It reads
NUL-separated name-status output and preserves spaces, tabs and newlines in
paths. File mode accepts name-only lines, tab-separated name-status records, or
a JSON list such as `[{"status":"D","paths":["src/worldenergydata/testing/old.py"]}]`.
Use JSON for filenames containing tabs or newlines. `--files-from -` reads stdin.
Supply either the ref pair or file input. Successful explanations exit zero.

Each path shows the matching rule (`core`, `contract route`, `module`,
`package`, `ignored`) and its isolated selection. The final block shows the
combined scope, targets and shards returned by the selector's matrix function.
A core edit can dominate the combined scope while another path still explains
its module route. Renames include both endpoints; deletions retain the deleted
path. A route may fire without an existing target directory, so inspect the
targets as well as the rule label. Workflow-registry changes use the always-on
contract rule. Rule labels currently use the selector's routing constants and
patterns; changes to that interface require updating this advisory adapter.

## Reproduce the worked example

The [generated worked example](selector-reach-example.md) gives explicit inputs,
the method, and the resulting audit, dependency closure and explanation:

```sh
python scripts/ci/generate_selector_reach_example.py --example-root "$TMPDIR/selector-example" > "$TMPDIR/selector-reach-example.md"
diff -u docs/ci/selector-reach-example.md "$TMPDIR/selector-reach-example.md"
```

The generator retains its fixture inputs in scratch and refuses to overwrite
differing inputs. Tests rebuild the fixture in `tmp_path` and compare the output
byte for byte. Golden explanation expectations are literal strings calculated
by hand from independent fixture directories, including a rename and deletion.
No saving, avoided-test count or runtime improvement is claimed or measured.
There are no engineering coefficients, numerical acceptance limits or physical
equations in these routing tools.

## Sources

- `scripts/ci/select_test_targets.py`: actual routing rules and matrix interface.
- `pyproject.toml`: pytest file patterns and archive exclusions.
- [Python 3.11 AST reference](https://docs.python.org/3.11/library/ast.html): `Import` and `ImportFrom` nodes.
- [Python 3.11 import statement reference](https://docs.python.org/3.11/reference/simple_stmts.html#the-import-statement): relative import semantics.
- [Git diff documentation](https://git-scm.com/docs/git-diff): two-tip diffs, `--name-status`, rename records and `-z` output.
