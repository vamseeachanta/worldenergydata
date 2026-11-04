# Linux runner routing and ARM64 dependency limits

Thirteen local jobs request `[self-hosted, Linux]`, allowing either x64 or ARM64
Linux runners. Five jobs retain `[self-hosted, x64]` because the frozen CAD
dependencies cannot install on Linux ARM64. The existing fork predicate and
`ubuntu-latest` fallback remain in CI, docs and brand guard. Job identifiers,
displayed check names, triggers and permissions are unchanged.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-11-04 | Align routing and tests with the mixed policy; retain x64 where frozen dependencies block ARM64. |

## Routing policy

| Workflow | Either Linux architecture | x64 only |
| --- | --- | --- |
| `ci.yml` | 6 | 0 |
| `main-full-run.yml` | 5 | 5 |
| `docs.yml` | 1 | 0 |
| `brand-guard.yml` | 1 | 0 |

Table 1. Local job selectors; 13 + 5 = 18 selectors.

Both `{self-hosted, Linux, X64}` and `{self-hosted, Linux, ARM64}` contain the
labels requested by compatible jobs. GitHub matches all requested labels; see
[runner routing][routing]. This label check does not establish workflow execution.
The CI `domain-tests` job calls an external reusable workflow whose runner
selection is outside this policy.

## Dependency boundary

`uv.lock` pins `nlopt==2.10.0` without a Linux aarch64 wheel or source archive.
The CAD extra selects it through CadQuery on Python 3.11 and newer. The five
frozen `--all-extras` jobs therefore retain x64: `full-suite`, `f821-inventory`,
`type-check`, `dependency-audit` and `performance-benchmark`. No dependency or
lockfile change is included. A separately validated dependency update is required
before opening those jobs to ARM64.

The workflow step audit found no pinned x86 downloads, architecture-specific
artifact names, apt installs, X64 cache keys or setup action architecture inputs.
ARM64 execution still requires validation of the Python 3.10 Cartopy source
build, the CadQuery OCP glibc requirement of 2.31 or newer, and external tools
used by source-only dependencies. Static inspection does not establish successful
installation or execution.

## Verification and follow-up

Run the routing regression without project fixtures or coverage output:

```bash
uv run --offline --no-project --with pytest --with pyyaml python -m pytest \
  tests/ci/test_runner_routing.py --noconftest -o addopts= -q -p no:cacheprovider
```

The regression checks all 18 local selectors, the exact fork fallback expression,
actual label-set matching for both Linux architectures, and x64 retention for
every frozen all-extras job. Workflow changes affect only `runs-on` lines.

Before merge, reconcile the overlapping selector changes in #1801 and inspect
hosted results at the final head. Full workflow execution on both architectures,
the full Python matrix and the fork fallback remain execution checks.

[routing]: https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow
