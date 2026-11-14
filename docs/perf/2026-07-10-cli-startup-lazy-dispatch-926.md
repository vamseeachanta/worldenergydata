# CLI startup evidence for issue 926

Measurements were taken on 13 November 2026. The filename follows the approved
plan dated 10 July 2026. This is CLI bootstrap evidence, not engineering input.

## Revisions and environment

- Original reproduction source: `0c5393b18590cf787b3eb020a7d418f3f36fb0f7`.
- Execution base (unmodified main): `d6e2c080107972b193fbff0b4616685f3f8d22fe`.
- Failing-test commit: `74f23fdb` (four deterministic failures).
- Tested implementation: `fb9887b0d909e4d5642f9bea5904c3ec14120fb6`.
- Python 3.12.3, Typer 0.27.3, Rich 15.0.0, uv 0.12.21; Linux,
  filesystem reported as ext2/ext3. The original NTFS-FUSE environment was not
  reproduced. No licensed solver was imported or executed.
- Frozen workspace synchronization installed 271 packages with test/dev extras.
  The lockfile remained unchanged; its SHA-256 was
  `b0d2cf8838e67fe88f9d3b31fa3988a6a018988a937327bf7956fd8b9481491d`.
- Baseline source trees and the implementation used the same synchronized
  dependency environment. The pinned historical source was replayed with its
  root and workspace-member source directories first on PYTHONPATH. Its
  historical dependency lock was not separately synchronized.

The packaged uv executable was used because the system launcher failed to create
its transient DBus scope. The standard-library venv attempt also lacked ensurepip;
uv subsequently created and populated the environment. These are environment
failures, not changes to project dependencies or tests.

## Cold and warm startup

The measured command was `uv run --no-sync worldenergydata landman --help`.
`--no-sync` excluded repeated dependency resolution after frozen synchronization.
Cold means the first measured fresh process at each revision; warm means an
immediate second fresh process. Filesystem and operating-system caches were not
flushed. Each run had a 60-second bound and returned zero.

| Source | Cold process (s) | Warm process (s) |
| --- | ---: | ---: |
| Pinned reproduction source | 3.587 | 3.278 |
| Execution base | 4.103 | 3.047 |
| Implementation | 0.366 | 0.347 |

Table 1. Observed Landman help startup in the synchronized dependency environment.

The original 600-second timeout was not reproduced. These observations establish
reduced import work in this environment; they do not establish a universal timing
threshold or reproduce the original filesystem pathology.

## Import-stack evidence

The issue's bounded probe is:

```bash
timeout 60s .venv/bin/python -u -c '
import faulthandler
faulthandler.dump_traceback_later(15, repeat=True)
import worldenergydata.cli.main
'
```

The import completes before the 15-second dump threshold in this environment.
A shortened repeating timer probe exited with signal 11 during extension loading.
A synchronous faulthandler dump, triggered by a profile hook on entry to Pandas,
completed with exit zero and captured the pinned baseline's eager chain:

```text
File "pandas/__init__.py", line 0 in <module>
File "worldenergydata/common/types.py", line 45 in <module>
File "worldenergydata/common/__init__.py", line 59 in <module>
File "worldenergydata/cli/commands/bsee.py", line 28 in <module>
File "worldenergydata/cli/commands/__init__.py", line 44 in __getattr__
File "worldenergydata/cli/main.py", line 53 in <module>
```

The synchronous probe is reproducible against the pinned source with the
synchronized environment:

```python
import faulthandler
import sys


def snapshot(frame, event, arg):
    if event == "call" and frame.f_code.co_filename.replace("\\", "/").endswith(
        "pandas/__init__.py"
    ):
        sys.setprofile(None)
        faulthandler.dump_traceback()


sys.setprofile(snapshot)
import worldenergydata.cli.main
sys.setprofile(None)
```

Only module-relative frames are retained; machine-specific frame prefixes and
thread addresses are omitted. Current main also shows eager Kansas KGS CLI
support importing Pandas before dispatch.

## Import-time profile

Profiles were captured with
`python -X importtime -c "import worldenergydata.cli.main"`.
Cumulative CLI import time was 2,595,980 microseconds at the pinned source,
2,639,678 microseconds at the execution base, and 99,773 microseconds after the
change. Instrumented timings are diagnostic and differ from console wall time.

| Revision | Module | Self time (microseconds) |
| --- | --- | ---: |
| Pinned source | scipy.stats._continuous_distns | 131901 |
| Pinned source | scipy.signal._support_alternative_backends | 89342 |
| Pinned source | scipy.stats._stats_py | 77715 |
| Execution base | scipy.stats._continuous_distns | 131321 |
| Execution base | scipy.signal._support_alternative_backends | 85692 |
| Execution base | scipy.stats._stats_py | 76004 |
| Implementation | site | 11319 |
| Implementation | encodings | 5366 |
| Implementation | rich.console | 5255 |

Table 2. Largest self-time contributors in each captured import-time profile.

## Deterministic acceptance budget

`tests/unit/cli/test_lazy_dispatch.py` uses isolated Python subprocesses and
forbids network connection and name-resolution attempts. Bare import, root help,
Landman help and FDAS help load none of:

- `pandas`, `numpy`, `pydantic`;
- `worldenergydata.common`, `worldenergydata.safety_analysis`;
- `worldenergydata.cli.commands.bsee`.

Each family probe additionally requires its selected command module and rejects
all other command-family modules. Bare import and root help load no families.
No unit assertion depends on wall-clock performance. Installed-console smoke
checks retain their existing 20-second bound and now include both light families.

## Compatibility and review

Current main has 18 families, including HSE added after the approved plan. All
18 were retained in registration order. The independent info-table order and
both description surfaces were copied verbatim; forecast follows lower-tertiary
in that table. Root help and info were byte-identical to execution-base captures
at 120 columns, with colors disabled consistently.

The lazy proxy uses TyperGroup so that the installed Typer's vendored Click is
used consistently. A temporary Typer wrapper builds each selected family through
normal `add_typer` registration. This preserves registration help overrides,
hyphenated names, one-command groups and root-only completion flags without
mutating the family's app. The proxy fallback was not needed.

Manual defect review checked context ownership, single-command grouping, cached
listing duplication, completion, native errors, and metadata order. Regression
coverage includes synthetic family equivalence against eager Typer registration.
The old drift guard was updated to inspect the nonempty registry and exact info
membership; otherwise removal of literal `add_typer` calls would make it vacuous.
No other model or assistant CLI was invoked.

## Verification and remaining blockers

The complete focused command was:

```bash
python -m pytest tests/unit/cli/ tests/integration/cli/ \
  tests/unit/kansas_kgs/test_cli.py -q -m "not solver"
```

The installed console was on PATH, and MPLCONFIGDIR was writable. A startup audit
hook rejected any OrcFxAPI import attempt. The final implementation run recorded
**179 passed, 1 failed, 2 xfailed, 2 xpassed**. The nine new lazy-dispatch cases
passed. Existing expected-failure markers were not changed.

The failure is
`TestMainCLI::test_status_command_exits_successfully`:
`TypeError: unsupported format string passed to NoneType.__format__`.
It also failed on unmodified main before implementation. Committed metadata has a
null record count that the unchanged status command formats numerically. The
approved plan explicitly preserves that command; no test was weakened or skipped.
This pre-existing failure prevents an all-green acceptance claim.

Black, isort and flake8 passed across src/tests using the locked tool versions and
current CI options. Repository mypy reported 882 errors in the execution base and
881 after implementation, with zero new diagnostic messages. Both new modules
passed a focused type check. Root version, Python-module CLI fallthrough and
BSEE, safety-analysis, HSE, forecast and marine-safety help returned zero.
The YAML router, version function, status function and root callback were
preserved. The lockfile and the Landman provider-routing files were untouched.

The changed patch passed an independent secret scan. A broader tree scan flagged
seven pre-existing generic-key patterns outside this change; it is not evidence
of patch findings. The retired identifier/legal scanner was not reinstated.
Publication, issue comments, PR creation, external model review and merging were
not performed under the files-only job constraint.
