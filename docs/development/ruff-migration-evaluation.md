# Ruff migration evaluation

## Summary

This evaluation compares the existing lint stack with a candidate Ruff policy.
It does not replace dependencies, CI commands or hooks, or format the source tree.
Adoption requires reviewed rule and formatter compatibility as well as timing.
The issue's full migration acceptance criteria remain open in #315.
The measurement and inventory conclusions below are unverified pending a
retrievable, sanitized evidence record with a stable reference and digest.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-11-16 | Added an evidence validator and a read-only comparison protocol before changing lint tooling. |
| Update | 2026-11-17 | Rejected unsupported legacy import diagnostics and overflowing timings; marked numerical conclusions unverified because supporting records are unavailable. |
| Record validation | 2026-11-17 | Rejected duplicate JSON keys, noncanonical formatter locations and repeated formatter paths to prevent lost or inflated findings. |
| Evidence preservation | 2026-11-17 | Rejected output paths that alias the input so report generation preserves the original evidence. |
| Validation record | 2026-11-17 | Distinguished historical test counts from current regression coverage and recorded unavailable Markdown lint; benchmark conclusions remain unverified. |
| Publication text | 2026-11-17 | Added a replacement description that qualifies every numerical conclusion and omits obsolete validator line references. |

## Current policy and scope

`pyproject.toml` sets Black and isort to 88 columns. `.flake8` sets its length
check to 100, extends ignores with E203 and W503, and exempts F401 in
`__init__.py`. These widths serve different purposes and remain separate.
The existing first-party import group is `worldenergydata`.

The PR lint commands in `.github/workflows/ci.yml` check Black and isort on
`src/` and `tests/`, but flake8 on `src/` only. The full evaluation explicitly
enumerates every Python file under `src/`, `tests/` and `packages/`, including
files that recursive tool discovery might exclude. It therefore measures a
larger scope than the current PR gate. Existing inline suppressions remain active.

The candidate uses Python 3.10, E/W/F/I only, the same first-party import group,
the F401 exception, an 88-column formatter and a separate 100-column E501 check.
E/W preview rules are enabled in the linter to expose supported pycodestyle
equivalents; formatter preview is disabled. Ruff has no W503 implementation.
An unmapped ignored rule still prevents a claim of exact policy equivalence.
The candidate also exposes supported rules that flake8 ignores by default;
these differences must be reviewed alongside the explicit configuration.
The candidate configuration is experimental and remains outside the repository.

## Collect reproducible evidence

Prepare an isolated interpreter with the exact versions in the results below.
Keep its environment, configuration, raw streams and outputs outside the checkout.
Record installation separately from command timing. Start from an unchanged tree;
do not run fixes or format in place. Use one subprocess and one tool worker at a
time. Source digests use the existing `check_f821.snapshot` and canonical JSON
SHA-256 method, rather than a count of console lines.

```python
from pathlib import Path
from scripts.ci.check_f821 import digest, snapshot

root = Path.cwd().resolve()
files = snapshot([root / p for p in ("src", "tests", "packages")], root)
source_sha256 = digest(files)
```

Save the complete sorted `files` mapping, not only its digest. Pass its keys as
explicit file arguments to each command below. Use the repository's configuration
files by explicit absolute runtime paths where required to prevent nested
configuration discovery. Temporary paths are supplied by the caller.

| Tool | Options before the explicit file arguments |
| --- | --- |
| flake8 | `--jobs=1 --config <repository-config> --exclude= --format='%(path)s:%(row)d:%(col)d:%(code)s:%(text)s'` |
| Black | `--config <repository-pyproject> --workers 1 --check --diff` |
| isort | `--settings-path <repository-pyproject> --check-only --diff` |
| Ruff check | `check --config <candidate-config> --no-cache --no-respect-gitignore --no-force-exclude --output-format json` |
| Ruff format | `format --config <candidate-config> --no-cache --no-respect-gitignore --no-force-exclude --check --output-format json` |

Use this standalone `candidate.toml`; the table names differ from a pyproject:

```toml
target-version = "py310"
line-length = 88
exclude = []
[lint]
select = ["E", "W", "F", "I"]
ignore = ["E203"]
preview = true
[lint.pycodestyle]
max-line-length = 100
[lint.per-file-ignores]
"**/__init__.py" = ["F401"]
[lint.isort]
known-first-party = ["worldenergydata"]
```

Before timing, exercise each tool on an external positive probe. For linters,
`scan_canary_missing` must produce F821 and exit 1. For formatters, imports in
reverse order followed by `x=1` must require a change and exit 1. Probes are
separate from the repository inventory and timings. Retain their output.

Run one untimed warm-up, then five serial observations of each command. Measure
with `time.perf_counter()` around the subprocess, including process startup and
output capture. Set `RUFF_NUM_THREADS=1`, `BLACK_NUM_WORKERS=1` and direct both
tool caches to external storage. Ruff cache reads are disabled; Black's diff mode
does not reuse cached formatting results. OS caches and imports are warm; this
is not a cold-start measurement. Retain stderr even when stdout is empty.

Recompute the complete source mapping before and after every invocation, and
require equality, including additions and removals. Store command, return code,
duration in seconds, source digest and both raw streams after every observation.
Resume a completed observation only if its recorded input digest still agrees.
An incomplete or failed observation must remain visible, not become a clean scan.

## Summary input and interpretation

`scripts/ci/summarize_lint_evaluation.py` accepts normalized JSON evidence and
writes a JSON report. It launches no scanners and requires no third-party imports.

```bash
python scripts/ci/summarize_lint_evaluation.py "$evidence" "$summary"
```

The output must name a different file from the input. The CLI rejects identical
or resolved-equivalent paths, symbolic links to the input and existing hard links
with exit 2 before reading or writing evidence. No report is written for this
argument error, including when the input is malformed. Evidence bytes and links
are preserved. Paths whose identity cannot be checked are also rejected. This
check does not protect against another process changing paths during execution;
use a private evidence directory while producing the summary.

The top-level object contains `files` (relative Python paths to SHA-256 values),
`unsupported_rules` (an explicit array), and `tools`. The latter must contain
exactly `flake8`, `black`, `isort`, `ruff-check` and `ruff-format`. Each tool has
its nonempty exact `version`, the identical `files` mapping and five `runs`:

```json
{
  "seconds": 1.0,
  "returncode": 0,
  "error": null,
  "before": "<canonical source-map SHA-256>",
  "after": "<same SHA-256>",
  "probe": true,
  "findings": []
}
```

JSON object keys must be unique at every nesting level. Repeated keys invalidate
the input even when their values agree; decoding must never discard evidence.

Each finding has `path`, positive integer `row` and `column`, `code`, and string
`message`. Flake8 findings accept E/W/F codes only; I001 is accepted only from
Ruff check and participates in the import comparison. Convert scanner filenames
to repository-relative paths. Preserve all
diagnostics: flake8's formatted fields and Ruff's JSON `filename`, `location`,
`code` and `message`. Normalize Black's `would reformat` and isort's incorrectly
sorted file notices to one `FORMAT` record per path at `(1, 1)`; do the same for
Ruff format's JSON filenames. Its message is `would reformat`. Never use stderr
line totals as diagnostic counts. Any parser ambiguity is an evidence error.
The validator requires formatter locations to be `(1, 1)` and permits each path
only once per formatter run, even when messages differ. The same path may recur
in separate observations or different tools.

Exit 0 must accompany no findings; exit 1 must accompany findings. All other
exits, parse failures, absent probes or versions, duplicates, changed inventories,
nonfinite or unrepresentable durations, nonfinite combined timings and unstable
findings invalidate the evidence. CLI exit 2
writes `ERROR`, `UNVERIFIED` parity and no timing claim. CLI exit 0 means valid
evidence, even when parity is blocked or the timing criterion fails.

The report retains every path and finding, each duration, median, maximum,
version and digest. It compares complete lint records, including messages, and
separates import-file and formatter-file deltas. Equal counts alone prove nothing.
Even equal nonempty formatting-file sets do not establish identical output;
parity remains unverified in that case. A clean matching observation establishes
agreement on the scanned inputs, not general semantic equivalence of tools.

The under-30-second test uses the unrounded sum of Ruff check and format-check
for each paired full-inventory observation; all five must be strictly below 30.
It is independent of compatibility and must never be inferred from the CI subset.

## Validation record

The initial test record of 34 evaluation cases and 36 existing F821 cases,
70 passes in total, is historical. The current focused run passed all 68
evaluation cases and 36 F821 cases, 104 in total, with no skips. It used:

```bash
uv run --no-project --with pytest --with flake8==7.4.1 --with ruff==0.17.1 \
  python -m pytest tests/ci/test_lint_evaluation.py tests/ci/test_check_f821.py \
  --noconftest -o addopts='' -q -rA -p no:cacheprovider \
  --basetemp="$external_basetemp"
```

The temporary directory is outside the checkout. These synthetic regressions
check evidence validation and scanner error handling; they do not verify any
historical inventory, diagnostic count, rule or file delta, scan stability or
timing. No full-repository suite or full-inventory benchmark was repeated.
Markdown lint was unavailable because `markdownlint` was not installed; no
Markdown lint pass is claimed.

## Description for publication

The following replacement description keeps regression coverage separate from
unverified measurements. It requires a separate edit to the pull request
description; adding it here does not update that description.

> Added a standard-library evidence validator, synthetic regressions and an
> evaluation guide before changing production lint tooling. The validator rejects
> malformed or unstable evidence, repeated JSON keys, invalid formatter records,
> overflowing durations and output paths that alias the input. Lint-record,
> import-file and formatter-file differences are reported separately.
>
> The initial 34 evaluation cases and 36 F821 cases, 70 passes, are historical.
> The current validation record in this guide reports 68 evaluation and 36 F821
> cases, 104 passes with no skips. These synthetic tests validate the evidence
> contract; they establish no historical benchmark result.
>
> All previously reported inventory sizes, diagnostic totals, rule and file
> deltas, stability, timings and the numerical basis of the reported BLOCKED
> verdict remain unverified. Supporting source maps, normalized evidence,
> summaries, commands and raw streams require a retrievable sanitized record
> with a stable reference and artifact digests. No claim is made that every
> unrounded combined Ruff duration met the strict 30-second criterion.
>
> Markdown lint was unavailable because markdownlint was not installed; no pass
> is claimed. No full-repository test run or benchmark is established by these
> regressions. Production dependencies, CI commands, hooks and source formatting
> remain unchanged. Compatibility review and production adoption remain open
> in #315. Boundary snapshots are not atomic, probes do not prove internal file
> coverage, and the validator cannot authenticate its producer.

## Reported measurements (unverified)

Every numerical conclusion in this section, including inventory sizes, finding
counts, rule and file deltas, stability and timing, is unverified. The referenced
external records have no retrievable, durable reference or artifact digest in
this guide. The figures are retained as previously reported observations, not
validated evidence. A source-map digest identifies inputs; it cannot establish
diagnostic totals, execution or elapsed time. No benchmark was repeated for this
update. Verification requires the complete sanitized source map, normalized
evidence, summary, commands and raw streams at a stable maintainer-accessible
reference with artifact digests, followed by validation against those records.

The previous evaluation reported measurements on 2026-11-16 using Python
3.12.15 and a serial Linux process.
The base commit was `efc4fd3f53c4d17eeda1cfdbf0d534e1727cc16e`.
The measured inventory contained 3,182 Python files: 200 in `src/`, 1,688 in
`tests/` and 1,294 in `packages/`. BASE contained 3,181 of those files; the
additional file was the new evaluation test. The complete source map and every
finding were reportedly enumerated in external `evidence.json` and
`summary.json`; those records are unavailable for verification here.

The installed Ruff 0.17.1 distribution declares `License-Expression: MIT`, and
its supplied licence text starts with `MIT License`. No dependency or lockfile
was changed. The installation log reported 18 packages installed in 7.0 ms;
that cached installation observation is separate from scan durations and does
not measure a cold installation.

| Tool | Version | BASE findings | Evaluation findings | Five durations (s) | Median (s) | Maximum (s) |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| flake8 | 7.4.1 | 3719 | 3719 | 25.7, 25.6, 25.7, 24.8, 24.8 | 25.6 | 25.7 |
| black | 25.9.0 | 22 | 23 | 62.3, 63.1, 63.8, 63.6, 64.7 | 63.6 | 64.7 |
| isort | 9.0.2 | 26 | 26 | 2.8, 2.8, 2.8, 2.8, 2.8 | 2.8 | 2.8 |
| ruff-check | 0.17.1 | 3871 | 3871 | 0.1, 0.1, 0.1, 0.1, 0.1 | 0.1 | 0.1 |
| ruff-format | 0.17.1 | 406 | 407 | 0.1, 0.1, 0.1, 0.1, 0.1 | 0.1 | 0.1 |

Reported combined Ruff check plus format-check durations were 0.2, 0.2, 0.2,
0.2, 0.2 s; the reported median and maximum were 0.2 s. These rounded figures
cannot establish that every unrounded sum was strictly below 30 seconds. The
timing criterion remains unverified pending the original observations.

The previous evaluation reported that all five finding lists per tool agreed
exactly and each before/after source digest agreed with this frozen input map:

```text
083e044b76e36733ede85b80b0a229bf14d41dea5b3a18000227ebc8c2aca110
```

The previous evaluation reported that the benchmark preceded final Black
formatting of the new evaluation test and only that inventory member changed
afterward. Its reported final source-map digest was:

```text
7dd13c032f5a5da33f76fbcb8e910b3ff4661a2d697618986b76edf11f9f50bb
```

Reported timings refer to the earlier frozen snapshot. Neither digest verifies
the elapsed times, counts or the current tree. Current file-level checks are
reported separately in the pull request.

### Reported rule and formatter differences (unverified)

Ruff's installed rule metadata has no counterparts for E121, E122, E123, E124,
E125, E126, E127, E128, E129, E131, E704, W503 or W504. Of these, E121, E123,
E126, E704, W503 and W504 are already ignored by flake8 defaults. E122 is active
and accounts for nine observed legacy findings. The remaining active unmapped
rules also require review even where the current inventory has no finding.
Flake8's full default-ignore value is
`E121,E123,E126,E226,E24,E704,W503,W504`; E203 is additionally ignored by the
repository. Selecting all supported E/W rules in the candidate exposes E226
and the E24 family that flake8 currently ignores. This is a policy difference,
not evidence that existing code acquired new errors.

| Rule | flake8 findings | Ruff findings |
| --- | ---: | ---: |
| E122 | 9 | 0 |
| E225 | 2 | 2 |
| E226 | 0 | 243 |
| E228 | 1 | 1 |
| E231 | 14 | 14 |
| E306 | 1 | 1 |
| E402 | 234 | 143 |
| E501 | 1464 | 1350 |
| E712 | 138 | 138 |
| E713 | 0 | 1 |
| E721 | 0 | 1 |
| E722 | 31 | 31 |
| E731 | 17 | 17 |
| E741 | 19 | 20 |
| F401 | 1268 | 1268 |
| F402 | 4 | 2 |
| F541 | 180 | 183 |
| F601 | 4 | 2 |
| F811 | 23 | 14 |
| F822 | 0 | 91 |
| F823 | 1 | 1 |
| F841 | 248 | 248 |
| I001 | 0 | 39 |
| W291 | 4 | 4 |
| W293 | 54 | 54 |
| W391 | 2 | 2 |
| W605 | 1 | 1 |

There are no identical complete lint records, because message text also differs.
For example, at `tests/ci/test_explain_selection.py:44:101`, flake8 reports
`line too long (101 > 100 characters)` and Ruff reports `Line too long (101 > 100)`.
Ignoring messages for a secondary view gives 1,958 shared unique path/row/column/
code coordinates, 1,479 legacy-only coordinates and 1,874 Ruff-only coordinates.
These are unique coordinates, not complete-record counts or proof of equal rule
semantics. The complete-record deltas retain all 3,719 legacy records and 3,832
candidate E/W/F records. Ruff's 39 I001 diagnostics are reported separately.

The import-file delta contains five isort-only files and 17 Ruff-only files.
Every Black-dirty file is also Ruff-dirty; Ruff additionally flags 384 files.
Equal dirty-file membership would still require comparing actual formatted
output. A concrete observed conflict in the new summary module was nested
conditional-expression layout: Black kept a chain on one line while Ruff split
it. Explicit branches now avoid that conflict in the new code. The existing
codebase was not reformatted to remove the measured differences.

The previous evaluation reported `BLOCKED` policy parity. Its numerical basis
remains unverified pending the supporting records. Counts, warm timing and
repeated stability do not justify replacing the production lint stack in this
change.

## Migration sequence and rollback

1. Review the full diagnostic inventories, including message and location changes,
   unsupported rules, default ignores and differing formatting output. Resolve
   disagreements explicitly; do not globally ignore categories to obtain parity.
2. Review a production Ruff version and licence, then add its dependency and
   update the lockfile in a separate change. Remove legacy dependencies only
   when their replacement checks and contributor commands are ready together.
3. Add the reviewed pyproject policy, keeping the distinct lint and formatter
   widths explicit. Review any all-tree formatting and safe lint fixes separately
   from behavioral changes; unsafe fixes require individual review.
4. Change CI and hooks together to run `ruff check` and `ruff format --check`
   over the agreed scope. Update tests that intentionally assert the legacy
   commands only in that adoption change. Obtain completed hosted checks.
5. Remove obsolete configuration after parity and coverage are reviewed. Keep
   the last legacy configuration and dependency revision as the rollback boundary;
   reverting the adoption change must restore CI, hooks and dependencies together.

## Known limits

Source snapshots detect boundary changes, not transient writes between snapshots.
A positive probe confirms invocation and output receipt, not internal coverage of
every file. The summary validates supplied normalized evidence; it cannot prove
that its producer executed the recorded commands. Raw streams and the complete
source map are therefore required for review. Identifying diagnostic paths are
retained in external evidence rather than reproduced in this public guide.
Hosted CI, other operating systems and cold installations are not measured here.

The changed Python module has no swallowed exceptions, skipped records or
engineering defaults. Its validation wrapper raises malformed-structure errors;
the CLI converts input or validation errors to an explicit `ERROR` report and
exit 2. Durations are supplied in seconds; no unit conversion is inferred.
Five observations and the strict 30-second limit come from #315. The synthetic
tests cover errors, source changes and the unrounded timing boundary. The caller's
assertion that a numeric duration really represents seconds has no independent
detection check; issue pending. Formatter record locations `(1, 1)` indicate a
whole-file change, not a claimed original diagnostic position.

## Sources

The [Ruff configuration reference](https://docs.astral.sh/ruff/configuration/)
and [formatter reference](https://docs.astral.sh/ruff/formatter/) were opened on
2026-11-16. Installed rule metadata and CLI help determine version-specific
capabilities. The selected distribution's licence metadata and licence text are
retained with the evidence. Existing policy and scan methodology come from
`.flake8`, `pyproject.toml`, `.github/workflows/ci.yml`,
`.pre-commit-config.yaml` and [the F821 scan guide](../ci/f821-scans.md).
