# CLI startup and lazy command families

The root console registers family names and help text without importing their
implementations. Selecting a family constructs its existing Typer application;
its callbacks, options, nested commands and context settings remain in control.
Root help, info, version, invalid commands and root completion need no family.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Defer family imports and document reproducible startup checks. |

## Method and sources

[Click: Lazily Loading Subcommands](https://click.palletsprojects.com/en/stable/complex/#lazily-loading-subcommands)
(accessed 2026-10-20) explains lazy registration and warns that help and completion
can resolve commands. The implementation therefore exposes a metadata-only
Typer group and imports the family when its context is constructed. A wrapper
uses normal `add_typer` conversion to preserve the existing registration overrides.
The loaded group is cached within that converted command, with no global cache.

The public names, descriptions and ordering come from `cli/main.py` at base
commit `d867ba1e011bb7558e0e9dd02e118160657f9633`. That revision is also the
baseline for the measurements below. The regression tests exercise the installed
`worldenergydata` console from a synchronized workspace, rather than invoking
only a child app. Every registered family's help is tested offline.

## Deterministic startup budget

The import budget follows directly from command selection, as required by
issue #926. Root-only requests select no family, so their expected family set is
empty. For `landman --help`, the expected set is
`{worldenergydata.cli.commands.landman}`; for `fdas --help` and `eia --help`, substitute the selected name.
These focused help paths must also leave BSEE, Pandas, NumPy, Pydantic, the
common package and safety analysis unloaded. These
exact sets are enforced in fresh processes with socket operations rejected.

The process watchdog is the existing public-console smoke test's 20 seconds
(`tests/unit/cli/test_cli_smoke.py::_run_cli`). It catches hangs; it is not a
portable performance threshold. The import-set assertions are the deterministic
acceptance criterion. No engineering equations or empirical coefficients apply.

## Worked example

Inputs: an installed workspace, `landman --help`, two fresh processes and the
existing smoke-test watchdog. Put evidence outside the checkout:

```bash
python scripts/audit/cli_startup_probe.py \
  --repeats 2 --timeout 20 --output "$TMPDIR/startup.json" -- landman --help
```

The probe measures elapsed time as `end - start` with `time.perf_counter`, invokes
the installed console script, and records Python import-profile stack evidence.
The first process is labelled cold and the next warm. These labels describe
fresh process imports; the operating-system page cache was not flushed.
Each completed sample is saved before starting the next one.

Observed results from the same synchronized workspace, with import profiling
enabled for both revisions (seconds, rounded to one decimal place):

| Tree | Cold process | Warm process | Exit status |
| --- | ---: | ---: | ---: |
| Pinned baseline above | 1.2 | 1.2 | 0 |
| Lazy dispatch working tree | 0.1 | 0.1 | 0 |

The baseline import recorder found all root command families, including BSEE.
Selected completed imports in the baseline import-profile stack were:

```text
pydantic
worldenergydata.common.data_resolver
numpy
pandas
worldenergydata.common
worldenergydata.safety_analysis.cli
```

The changed tree loads only `cli.commands.landman` among command families and
loads neither Pandas nor NumPy. The installed-console tests independently assert
that answer; timing alone is not used to infer import isolation.

Before implementation, the focused installed-console tests produced seven
failures and one pass: unrelated imports caused the failures, while the existing
root registration metadata already passed. The changed implementation passes
the corresponding checks.

## Verification and limits

```bash
python -m pytest tests/unit/cli tests/integration/cli tests/unit/kansas_kgs/test_cli.py \
  --noconftest -o addopts= -q -rA -p no:cacheprovider --basetemp="$TMPDIR/cli-tests"
```

Use an environment containing the installed workspace and pytest. The repository
AGENTS contract permits `--noconftest`; overriding default coverage output keeps
test artifacts outside the checkout. New tests also exercise nested callbacks,
parent context, family options, completion, repeated loading and an unavailable
family. The probe has independent hand-calculated timing and timeout tests. The final
focused suite passed 183 tests, including 41 new tests. Root help and `info`
were compared byte-for-byte with the pinned baseline at the same terminal
width and were identical. The two omitted lazy command exports are now listed
explicitly: `lower_tertiary` and `production_forecast`.

This change defers each family as a unit. Heavy dependencies needed by the
selected family can still load. It does not change provider routing, acquire
data, or promise identical timings on other environments. Packaging and workspace
synchronization costs are outside the measured console invocation.
