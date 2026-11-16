# Selector reachability and explanation

## Summary

These stdlib tools inventory the current selector without changing its routing or
workflows. The exact-file orphan comparison reports new gaps whenever the audit
CLI runs. It remains advisory until every added test selects the audit in its
own PR gate; otherwise an unrelated full run could fail on an unseen addition.
Path coverage does not prove pytest collection, successful imports or execution.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-22 | Document advisory reachability, static dependents and diff explanations. |
| Update | 2026-11-06 | Cover current-main orphan tests and explain fast/full modes, merge-base diffs and rename context. |
| Advisory update | 2026-11-06 | Report new and obsolete exceptions, exercise PR goldens on older trees and clarify CI diff inputs. |

## Audit a checkout

Run from the repository root with a scratch directory outside the checkout:

```sh
python scripts/ci/audit_selector_reach.py --json "$TMPDIR/selector-reach.json" > "$TMPDIR/selector-reach.txt"
python scripts/ci/package_closure.py > "$TMPDIR/package-closure.json"
```

The audit imports `scripts/ci/select_test_targets.py` by path. For every filename
matching `test_*.py` or `*_test.py` beneath `tests/` or `packages/*/tests/`, it
simulates a diff containing only that path using push/full-mode `select`, not
the PR fast gate. A file is reachable when its selected
scope is not `full` and a target equals that file or is one of its parent
directories. Archived tests are inventoried even when pytest excludes them.
This is **self-diff reachability**: an orphan might still run for some other
contract route or a full run. It is not proof that no possible diff can reach it.

The source table separately simulates tracked source/configuration inputs beneath each member's `src/`
and each `src/worldenergydata/<module>/`. JSON records include probes, scopes,
all targets, targets beyond the always-on set, existing unit homes, and whether
any target was selected. Members without source files are `NOT_EVALUATED`.
In Git checkouts, source probes and source groups come from `git ls-files -z`,
so untracked build/distribution output cannot change their rows. Plain fixture
roots without a Git index use filesystem source discovery. Cache directories,
compiled bytecode, package metadata, symlinks and Windows junctions are
excluded from both inventories. Legitimate `build`/`dist` test and source
directories remain inventoried. Always-on targets must not be
mistaken for module-specific coverage. The filename conventions mirror the
current pytest configuration; they are not loaded dynamically from it.

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
The archive reason follows pytest exclusions at main revision `841cb7d4`,
including directory patterns and `--ignore` paths. Earlier-only exclusions name
revision `254c0c1d` explicitly; they do not claim that current main excludes those
paths. All such paths remain in the inventory.
Directories, glob patterns, duplicate entries and entries without reasons are
rejected. Listing an old orphan does not permit a new sibling automatically.
Review the cause before adding an exception; remove entries after routing is
repaired. The comparison permits stale entries temporarily so another selector PR
can repair reachability without having to edit this list in the same change.
The CLI adds an `allowlist` object to JSON, with `unlisted` orphan paths and
`reachable` exception paths that can be removed. Both lists and their counts
also appear in the table. The comparison exits zero for either condition;
malformed allow-list entries still fail. Use `--allowlist FILE` to compare a
different exact-file snapshot.

Run the audit tests manually:

```sh
uv run --no-project --with pytest python -m pytest tests/ci/test_audit_selector_reach.py --noconftest -o addopts='' -q -p no:cacheprovider --basetemp="$TMPDIR/reach-tests"
```

No workflow or existing selector file changes here. Audit tests live in
`tests/ci/`, enrolled through the existing full-run target set and the fast gate's
CI-tool route. Test-only changes beneath `tests/ci/` still have no self route.
The real-tree test exercises report generation without enforcing the snapshot;
synthetic tests still require exact-file detection of every new sibling and
reporting of reachable exceptions. The allow-list reflects main revision
`cd5bdf73`, including the reservoir example and removal of ten now-reachable
catalog and repository-structure exceptions. Older selectors can report those
removed entries as unlisted without failing the suite. Enforcing new gaps
requires a separate selector change that runs the audit for every added test.

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
git diff --name-status --find-renames origin/main...HEAD > "$TMPDIR/changes.txt"
python scripts/ci/explain_selection.py --files-from "$TMPDIR/changes.txt"
python scripts/ci/explain_selection.py --mode full --base origin/main --head HEAD
```

Ref mode uses `git diff BASE...HEAD`, matching the merge-base input documented
by the selector. It reads NUL-separated name-status output and preserves spaces,
tabs and newlines in paths. File mode accepts name-only lines or tab-separated
name-status records. Add `--json` to parse a JSON list such as
`[{"status":"D","paths":["src/worldenergydata/testing/old.py"]}]` instead.
Use explicit JSON mode for filenames containing tabs or newlines; a leading
bracket in ordinary file mode remains part of the path. `--files-from -` reads
stdin. Supply either the ref pair or file input.

The default `--mode pr` calls `select_fast` and `to_matrix(fast=True)` to explain
the selector's response to the supplied file list in PR mode. `--mode full`
calls `select` and the full-mode matrix
interface used for push/full selection. Older selector revisions without either
fast API reject PR mode with a stated reason; use full mode for those revisions.
The selected mode is printed before the per-path explanations.

The hosted gate computes its own changed-file list on a checked-out merge.
For a branch behind the base tip, that list can differ from ref mode's
merge-base diff on the branch tip. To reproduce the gate's input, run its diff
command in the same checkout with the same `BASE_SHA`, then pass the result
explicitly:

```sh
git diff --name-only "$BASE_SHA"...HEAD > "$TMPDIR/gate-files.txt"
python scripts/ci/explain_selection.py --mode pr --files-from "$TMPDIR/gate-files.txt"
```

This reproduces selection for those inputs; it does not establish that the
branch-tip ref recipe used the same inputs as a hosted run.

Each path shows the selector's full-mode classification (`core`, `selector route`
or `ignored`) alongside its targets in the requested mode. PR core paths show
`core (fast gate)` so the bounded gate is distinguished from full-mode fan-out.
Labels derive from public selector results;
private regexes and routing tables are not mirrored. The combined block shows
the scope, targets and shards returned by the same selector mode. A full-mode
core edit can dominate combined scope; the fast gate retains its bounded core
selection. Rename/copy sources are labelled **context only** and excluded from
combined selection, matching name-only diff input. Destinations and deleted
paths determine combined selection. A route may fire without an existing target,
so inspect the targets as well as the label. Successful explanations exit zero.

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
All four PR goldens execute against the checkout's fast APIs when available,
falling back to a hand-enumerated fast-capable API fixture on older revisions.
No fallback returns before checking the literal output. Separate rejection
tests cover unsupported APIs. The fixture tests explanation behavior; checking
the real fast selector additionally requires a revision that contains it.
No saving, avoided-test count or runtime improvement is claimed or measured.
There are no engineering coefficients, numerical acceptance limits or physical
equations in these routing tools.

## Sources

- `scripts/ci/select_test_targets.py`: actual routing rules and matrix interface.
- `pyproject.toml`: pytest file patterns and archive exclusions.
- [Python 3.11 AST reference](https://docs.python.org/3.11/library/ast.html): `Import` and `ImportFrom` nodes.
- [Python 3.11 import statement reference](https://docs.python.org/3.11/reference/simple_stmts.html#the-import-statement): relative import semantics.
- [Git diff documentation](https://git-scm.com/docs/git-diff): merge-base diffs, `--name-status`, rename records and `-z` output.
