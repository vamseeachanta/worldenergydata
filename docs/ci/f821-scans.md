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

The arithmetic is set cardinality and equality: the count is the length of the
validated repository diagnostic list, and stability requires every sorted list
to equal the first. There are no fitted coefficients or engineering limits.
The [F821 rule definition][f821], [flake8 options][flake8] and
[Ruff configuration reference][ruff-config] define the tool protocol.

The checker exit contract is:

| Status | Exit | Meaning |
| --- | --- | --- |
| STABLE | `0` | Identical empty repository inventories, or explicit inventory mode |
| STABLE | `1` | Identical nonempty repository inventories |
| UNSTABLE / ERROR | `2` | Different findings or invalid/incomplete evidence |

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

The expected nonzero exit means a stable finding, not a tool failure. The timeout
in this example is an explicit execution input. Evidence directories remain
available for inspection; choose a fresh directory for another example.

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
