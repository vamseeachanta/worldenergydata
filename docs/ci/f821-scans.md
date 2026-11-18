# Reproducible F821 inventories

## Summary

Use `scripts/ci/check_f821.py` for undefined-name inventories and CI. It captures
each linter's exit status, stdout and stderr separately; checks an intentional
F821 probe; and compares complete findings against an unchanged Python source
inventory. Repeated agreement is evidence for the recorded inputs and tools.
It does not establish the cause of the historical variance in #328.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-20 | Added a scan protocol, regression cases and a worked example to prevent incomplete invocations being reported as clean inventories. |
| Bytecode controls | 2026-11-16 | Added isolated cold and warm bytecode observations to distinguish cache state from environment synchronization. |
| Evidence qualification | 2026-11-17 | Withdrew unsupported bytecode measurements and marked the experiment unverified until a retrievable record is available. |
| Final source comparison | 2026-11-17 | Rejects input changes after the last progress write and retains both source digests to prevent invalid stability reports. |
| Regression evidence | 2026-11-18 | Records the current focused test count separately from the unverified bytecode experiment. |
| Status interpretation | 2026-11-18 | Clarifies how callers distinguish inconsistent findings, invalid evidence and refused invocations when all exit with code 2. |
| Missing summary | 2026-11-18 | Requires a summary from the current invocation before interpreting an exit code, because evidence directory creation can fail with exit 1. |

## Why counting output lines is insufficient

The issue's `flake8 ... 2>&1 | wc -l` command counts diagnostics and environment
messages together. The [Bash pipeline contract][bash] makes the pipeline status
the last command's status unless `pipefail` is enabled. A successful `wc` can
therefore hide a failed linter. This is a demonstrable reporting weakness; it
does not prove that it caused the historical counts or that uv has a race.

## Run an inventory

Prepare the development environment first. Choose a new output directory outside
the scan targets; the checker refuses an existing directory to preserve evidence.
The following commands use an already prepared interpreter and never synchronize
the project environment during a scan:

```bash
evidence=$(mktemp -d "${TMPDIR:?}/f821-evidence.XXXXXX")
uv run --no-sync python scripts/ci/check_f821.py src/ tests/ packages/ \
  --runs 5 --timeout 300 --output "$evidence/direct"
uv run --no-sync python scripts/ci/check_f821.py src/ tests/ packages/ \
  --launcher uv --runs 5 --timeout 300 --output "$evidence/uv"
uv run --no-sync python scripts/ci/check_f821.py src/ tests/ packages/ \
  --tool ruff --runs 5 --timeout 300 --output "$evidence/ruff"
```

The repetition count follows the [issue investigation plan][plan]. The timeout
is a caller-supplied execution budget in seconds, not a benchmark acceptance
limit. `--uv` selects a particular uv executable. The uv launcher uses
`--no-project --no-sync --python` to select the same interpreter as the direct
launcher without resolving the project; see the [uv CLI reference][uv].
Direct execution uses `python -m flake8`, avoiding a missing console wrapper.
Both launchers require the selected tool to be installed in that interpreter.

### Control bytecode state

Pass `--bytecode-root` and `--bytecode-policy` together to vary only Python's
bytecode cache. Without these options, the existing invocation and inherited
bytecode environment are preserved. The root must be new, outside all resolved
scan targets, and separate from the evidence directory. Existing empty or
nonempty roots are refused, including symlinks resolving into scan targets.
No earlier cache is removed or reused.

```bash
experiment=$(mktemp -d "${TMPDIR:?}/f821-bytecode.XXXXXX")
uv run --no-sync python scripts/ci/check_f821.py src/ tests/ packages/ \
  --runs 10 --timeout 300 --allow-findings \
  --bytecode-policy cold-per-run --bytecode-root "$experiment/direct-cold-cache" \
  --output "$experiment/direct-cold"
uv run --no-sync python scripts/ci/check_f821.py src/ tests/ packages/ \
  --runs 11 --timeout 300 --allow-findings \
  --bytecode-policy warm-shared --bytecode-root "$experiment/direct-warm-cache" \
  --output "$experiment/direct-warm"
uv run --no-sync python scripts/ci/check_f821.py src/ tests/ packages/ \
  --launcher uv --runs 10 --timeout 300 --allow-findings \
  --bytecode-policy cold-per-run --bytecode-root "$experiment/uv-cold-cache" \
  --output "$experiment/uv-cold"
uv run --no-sync python scripts/ci/check_f821.py src/ tests/ packages/ \
  --launcher uv --runs 11 --timeout 300 --allow-findings \
  --bytecode-policy warm-shared --bytecode-root "$experiment/uv-warm-cache" \
  --output "$experiment/uv-warm"
```

All child processes receive `PYTHONPYCACHEPREFIX` pointing to their isolated
directory. Controlled children also have `PYTHONDONTWRITEBYTECODE` removed so
the experiment can populate caches when the caller disables writes. The parent
environment is unchanged. Version queries use a dedicated `version` directory
and cannot warm measurement directories. Cold mode creates a fresh empty
`run-N` directory for each observation; warm mode creates one `shared` directory,
labels its first observation `priming`, and labels subsequent observations
`warm`. The warm run count includes priming: eleven runs give ten warm samples.
The checker imports no scanned source modules or engineering programs.

`report.json` records the policy, each child's bytecode directory and command,
the version query, and each observation's state, source digest, full finding
digest and exit status. A final snapshot after the last progress write is
compared with the initial inventory for every invocation. Both `source_sha256`
and `source_after_sha256` are retained when the snapshots differ; the checker
reports `ERROR` and exits `2`. Unchanged inputs retain the existing exit contract.
Failures retain raw streams and available metadata and keep the existing error
exit contract. Raw evidence stays outside the repository because it can contain
runtime paths. These controls do not create a fresh dependency environment,
clear operating-system file caches, or reconstruct historical package versions.

For exploratory inventories, `--allow-findings` accepts stable nonempty findings.
It never accepts an incomplete, failed or inconsistent scan. CI omits this flag.

## Method and evidence

1. Expand the supplied repository-relative files and directories into a sorted,
   deduplicated set of Python files. Record each file's SHA-256 and a digest of
   the complete mapping. Empty or missing targets are errors. Directory symlinks
   are not traversed; files resolving outside the working directory are rejected.
2. Record the interpreter, command and tool version. Use isolated linter settings
   and explicit file arguments so local ignores, ignore files and discovery
   exclusions cannot silently shrink the requested scope. flake8 runs serially;
   Ruff receives a single-thread execution setting.
   Inline `noqa` suppressions remain honored by both tools.
3. Add a probe containing only `scan_canary_missing` to the external evidence
   directory. It must yield exactly one F821 at row one, column one. Exclude that
   finding from repository counts. Missing or duplicated probe diagnostics are
   errors, including empty stdout with a successful exit status.
4. Retain raw streams as `version.stdout`, `version.stderr`, `run-1.stdout`,
   `run-1.stderr`, and corresponding files for later runs. Preserve status and
   command metadata in `report.json`. A timeout retains available partial output.
   Treat malformed output, syntax diagnostics, unexpected paths, duplicates,
   spawn failures and unexpected exit statuses as errors.
5. Check the source inventory before and after each scan, including added or
   removed files. Sort findings by path, row, column, code and message. Compare
   the complete records, including multiplicity, rather than only their count.
   Write progress after each completed observation and retain all failed evidence.
   After the last progress write, record and compare a final source snapshot
   before declaring findings stable.

The arithmetic is set cardinality and equality: the count is the length of the
validated repository diagnostic list, and stability requires every sorted list
to equal the first. There are no fitted coefficients or engineering limits.
The [F821 rule definition][f821], [flake8 options][flake8] and
[Ruff configuration reference][ruff-config] define the tool protocol.

The table applies when the current invocation prints a status summary on stdout.

| Status | Exit | Meaning |
| --- | --- | --- |
| STABLE | `0` | Identical empty repository inventories, or explicit inventory mode |
| STABLE | `1` | Identical nonempty repository inventories |
| UNSTABLE / ERROR | `2` | Different findings or invalid/incomplete evidence |

Treat any exit without a stdout summary as a refused or failed invocation.
Exit `1` without a summary can occur when the checker cannot create the evidence
directory, for example when its parent is a regular file. Argument and directory
validation refusals exit `2`, print usage to stderr and write no new report.
When a summary is present, read `status` there or in the report created by this
invocation to distinguish `UNSTABLE` from `ERROR`.

These are checker interface values, not acceptance tolerances. The raw linter
must exit `1` even for a clean repository because the probe is always a finding;
see [flake8's exit-code implementation][flake8-exit] and
[Ruff's exit-code contract][ruff-exit]. The checker reports repository counts
after excluding the probe.

CI adds this check before the existing formatting and lint commands. The full
lint job uploads `f821-scan-evidence` even when a scan fails. Evidence contains
absolute runtime paths and raw diagnostics: review it before copying anything
into public documentation. The checker prints only status and count summaries.

## Worked example

Input `sample.py` contains exactly:

```python
missing_name
```

Independent hand calculation: the expression uses one name, with no assignment,
import or builtin defining it. The F821 rule therefore gives one finding at row
one, column one. The probe adds one separate raw finding, which the checker
removes. Two identical observations produce repository counts `[1, 1]`, status
`STABLE`, and checker exit `1`. Replacing the input with `missing_name = None`
defines the name, so the repository counts become `[0, 0]` and checker exit `0`.
These expectations are asserted against both real linters in
`tests/ci/test_check_f821.py`, independently of checker output generation.

Run the example without putting temporary files in the repository:

```bash
checker="$PWD/scripts/ci/check_f821.py"
python_bin=$(uv run --no-sync python -c 'import sys; print(sys.executable)')
example=$(mktemp -d "${TMPDIR:?}/f821-example.XXXXXX")
mkdir "$example/input"
printf 'missing_name\n' > "$example/input/sample.py"
(
  cd "$example/input"
  "$python_bin" "$checker" sample.py --runs 2 --timeout 30 \
    --output "$example/evidence"
)
```

For this input, expect exit `1` together with a `STABLE` summary and counts
`[1, 1]`. The timeout is an explicit input. Choose a fresh directory for each
invocation to preserve the previous evidence.

## Investigation and remaining limits

The comparison on 2026-10-20 covered 2,701 Python files in `src/`, `tests/` and
`packages/`. flake8 7.4.1 used pyflakes 4.0.3 and pycodestyle 2.15.0. The tool
versions, input digests, raw streams and per-run metadata were recorded together.

| Tool and invocation | Consecutive repository finding counts | Result |
| --- | --- | --- |
| flake8, direct interpreter | `0, 0, 0, 0, 0` | STABLE |
| flake8, uv with the same interpreter | `0, 0, 0, 0, 0` | STABLE |
| Ruff 0.17.1, direct interpreter | `0, 0, 0, 0, 0` | STABLE |

The source digest and complete finding digest matched across all fifteen scans.
This comparison used a prepared environment and did not reproduce the variance.

The historical uv cold-start race is **NOT_EVALUATED**: the original environment
and failed invocation are unavailable in the supplied evidence. Clearing shared
caches or rebuilding the full dependency environment is outside this change. Controlled
direct/uv comparisons use an already prepared interpreter, so they isolate the
invocation route, not environment synchronization or bytecode compilation.

### Focused regression verification

On 2026-11-18, the focused suites `tests/ci/test_check_f821.py` and
`tests/ci/test_f821_bytecode_state.py` passed all 56 tests with no skips at
`175821297c7ff30e0946c4da0783e3197618f03c`. The six real-flake8 cases in
`test_final_snapshot_validates_source_after_last_progress` cover changed and
unchanged inputs after the last progress write under inherited, cold-per-run and
warm-shared bytecode settings. Changed inputs retain distinct source digests and
produce `ERROR` with exit `2`; unchanged controls retain matching digests and
produce `STABLE` with exit `0`.

These regression results establish the tested checker behavior. They do not
establish historical experiment inventories, tool versions, cross-condition
agreement or bytecode-file counts. The bytecode-cache experiment remains
**UNVERIFIED** under the evidence requirements below.

### Bytecode-cache experiment: unverified

The reported bytecode-cache experiment is **UNVERIFIED**: this pull request
provides no retrievable, head-bound evidence record for its inputs, tool versions,
observation results, exit statuses, cross-condition agreement or cache population.
The numerical results and source and finding digests have been withdrawn from
this summary. No conclusion about observed bytecode-state variance is established.

The four bytecode-control commands above describe a comparison to run; their
observation counts are example execution inputs, not verified measurements.
Offline subprocess tests check directory allocation, cache-state labels,
environment isolation and evidence handling. They do not substantiate a real
experiment's observation counts, process statuses, agreement or bytecode-file
counts.

Before reporting measurements, provide a sanitized evidence manifest tied to the
exact tested commit and a stable record reference accessible to the maintainer.
Record the commands and tool versions, before/after source digests, and each
condition's per-observation process status, finding count and digest, cache state
and measured cache population. Include hashes of the supporting records so the
summary can be checked without publishing raw runtime paths.

The historical synchronization hypothesis remains **NOT_EVALUATED**. A controlled
bytecode comparison in a prepared interpreter would not vary dependency
environment preparation, historical versions or operating-system file-cache state.
A synchronized-environment experiment still requires a separate bounded design.

The probe confirms that the selected rule runs and its output is received. It
cannot prove that a linter internally analyzed every file. Stable repeated
inventories cannot detect the same deterministic omission in every run. Separate
source digests detect changes at the observation boundaries; they do not provide
an atomic filesystem snapshot against a concurrent writer.

Ruff and flake8 can implement different rule semantics. Compare locations and
scope before drawing migration conclusions. The broader formatter/linter
migration remains in #315; this change retains the existing lint stack.

The cached Ruff version named by the lockfile could not locate its executable
when invoked with `python -m ruff --version` (`FileNotFoundError: [path removed]`).
The regression checks therefore used available Ruff 0.17.1. The lockfile is
unchanged, and the added CI scan uses flake8 rather than Ruff.

[bash]: https://www.gnu.org/software/bash/manual/html_node/Pipelines.html
[plan]: ../plans/2026-05-04-issue-328-flake8-race.md
[flake8]: https://flake8.pycqa.org/en/latest/user/options.html
[flake8-exit]: https://flake8.pycqa.org/en/latest/_modules/flake8/main/application.html#Application.exit_code
[ruff-config]: https://docs.astral.sh/ruff/configuration/
[ruff-exit]: https://docs.astral.sh/ruff/linter/#exit-codes
[f821]: https://docs.astral.sh/ruff/rules/undefined-name/
[uv]: https://docs.astral.sh/uv/reference/cli/

Public references were opened on 2026-10-20. Tool versions and measured scan
results belong to the recorded evidence, rather than being assumed constants.
