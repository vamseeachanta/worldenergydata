# Linux runner routing and ARM64 dependency limits

Trusted jobs run on self-hosted Linux runners, except the two package-index
publishing jobs described below. Both runner pools carry `self-hosted` and
`Linux` labels: `[self-hosted, Linux]` admits either x64 or ARM64, while adding
`x64` restricts a job to that architecture. Label matching is case-insensitive.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-11-04 | Align routing and tests with the mixed policy; retain x64 where frozen dependencies block ARM64. |
| 2 | 2026-11-12 | Document the full-name guard, all local selectors and the package-index publishing exception. |
| 3 | 2026-11-13 | Admit either Linux architecture for four lightweight PR-validation jobs and domain discovery; retain x64 for domain tests and aggregation. |
| 4 | 2026-11-22 | Route same-repository pull requests to GitHub-hosted runners by default, behind the `WED_PR_RUNNER` repository variable. |

## Pull request runner switch (`WED_PR_RUNNER`)

Pull request checks run on GitHub-hosted `ubuntu-latest` by default. The
repository is public, so hosted minutes are free, and PR gates no longer depend
on the self-hosted runners' disk, uv cache or network health.

| `WED_PR_RUNNER` (repository variable) | Same-repository pull requests | Fork pull requests |
| --- | --- | --- |
| unset, or any other value | `ubuntu-latest` | `ubuntu-latest` |
| `self-hosted` | self-hosted Linux labels shown in Table 1 | `ubuntu-latest` |

The switch is read by every job in the PR-triggered workflows: `ci.yml`,
`domain-matrix.yml` (called by `ci.yml` on pull requests only),
`pr-validation.yml`, `brand-guard.yml` and `wheel-ownership.yml`. Push and
dispatch runs of those workflows keep their self-hosted routing. Trusted-only
workflows (`main-full-run.yml`, `docs.yml`, `pages.yml`, `release.yml`) do not
read it and keep the routing below; nightly, licensed and Windows work never runs
on pull requests (architecture decision A4).

To route pull requests back to the self-hosted runners, set the variable:

```bash
gh variable set WED_PR_RUNNER --body self-hosted --repo vamseeachanta/worldenergydata
```

Delete it (`gh variable delete WED_PR_RUNNER`) to return to hosted runners. The
PR jobs install their tools with `astral-sh/setup-uv` and `actions/setup-python`
and use no host paths, so they run unchanged on either runner type.

## Routing policy

For workflows with conditional routing, the guard is
`github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository`.
A PR receives self-hosted labels only when its head repository's full name
matches the current repository and, in PR-triggered workflows,
`vars.WED_PR_RUNNER == 'self-hosted'` (see above). Fork PRs and PRs with missing head-repository
data fall back to `ubuntu-latest`; the old `.fork` Boolean is not used.
Push, dispatch and schedule events select self-hosted Linux runners, subject to
the publishing exception. This policy does not add triggers: currently no
workflow declares a GitHub schedule. Workflows restricted to trusted events
may use literal self-hosted label lists.

| Workflow | Either Linux architecture | x64 only | Always GitHub-hosted |
| --- | --- | --- | --- |
| `brand-guard.yml` | 1 | 0 | 0 |
| `ci.yml` | 6 | 0 | 0 |
| `docs.yml` | 1 | 0 | 0 |
| `domain-matrix.yml` | 1 | 2 | 0 |
| `main-full-run.yml` | 5 | 5 | 0 |
| `pages.yml` | 0 | 2 | 0 |
| `pr-validation.yml` | 4 | 0 | 0 |
| `release.yml` | 0 | 4 | 2 |
| `wheel-ownership.yml` | 1 | 0 | 0 |

Table 1. All 34 local job selectors: 19 architecture-independent + 13 x64 +
2 hosted publishing exceptions. Of the 32 self-hosted selectors, 22 use the
full-name guard and 10 in `main-full-run.yml` use literal label lists.

Both `{self-hosted, Linux, X64}` and `{self-hosted, Linux, ARM64}` contain the
labels requested by compatible jobs. GitHub matches all requested labels; see
[runner routing][routing]. This label check does not establish workflow execution.
The CI `domain-tests` job calls the local reusable `domain-matrix.yml` workflow;
its three selectors are included above. The caller has no `runs-on` selector.

### Lightweight PR-gate tool audit

The five jobs below request `[self-hosted, Linux]` for trusted events. Each
retains the same full-name guard and `ubuntu-latest` fork fallback.

| Job | Tools and architecture requirements |
| --- | --- |
| `pr-title` | `amannn/action-semantic-pull-request@v6` is a Node 24 JavaScript action. No x64 binary is selected by the workflow. |
| `file-size` | `actions/checkout@v7`, bash, git and GNU coreutils (`stat`, `numfmt`); no architecture-specific download or dependency install. |
| `sensitive-files` | `actions/checkout@v7`, bash, git and `mktemp`; filename matching uses bash builtins. |
| `pack-lint` | `actions/checkout@v7`, bash, git, `mktemp` and Python 3.11 via `actions/setup-python@v7`; `scripts/pack_lint.py` uses only the standard library. |
| `discover` | `actions/checkout@v7`, bash, git, text utilities and the runner's existing `python3`; the default selector and embedded validator use only the standard library. |

Table 2. Static tool audit for the five lightweight PR-gate jobs.

The checkout and Python setup actions use Node 24 JavaScript runtimes. No
workflow step in these jobs selects an x64-only binary, CAD dependency or
licensed solver. Discovery retains its existing runner Python requirement;
reusable callers remain responsible for their supplied selector. Domain
`test-domain` and `aggregate` jobs retain x64 routing. This audit establishes
no successful ARM64 workflow execution or live runner-tool availability.

### Publishing exception

Only `release.yml` jobs `publish-testpypi` and `publish-pypi` use
`ubuntu-latest` on trusted events. These package-index uploads stay on ephemeral
GitHub-hosted runners to keep publishing tokens and OIDC uploads off persistent
self-hosted runners. The current upload steps use tokens. The release workflow
accepts tag pushes and manual dispatches; the publishing job conditions remain
in force. Other release jobs retain self-hosted Linux x64 routing. No release
concurrency group is defined, preserving independent release runs without a
shared pending-run queue.

## Dependency boundary

`uv.lock` pins `nlopt==2.10.0` without a Linux aarch64 wheel or source archive.
The CAD extra selects it through CadQuery on Python 3.11 and newer. The five
frozen `--all-extras` jobs in `main-full-run.yml` therefore retain x64: `full-suite`, `f821-inventory`,
`type-check`, `dependency-audit` and `performance-benchmark`. No dependency or
lockfile change is included. A separately validated dependency update is required
before opening those jobs to ARM64. Other existing x64 selectors are retained
as shown in Table 1; this change does not broaden their architecture support.

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
  tests/ci/test_runner_routing.py tests/workflows/test_ci_runner_routing.py \
  tests/workflows/test_ci_triggers.py --noconftest -o addopts= -m "not solver" \
  -q -p no:cacheprovider
```

The regressions cover all 34 local selectors, full-name routing with fork and
missing-head fallbacks, the exact two-job publishing exception on trusted
events, and the absence of release concurrency. Architecture label matching and
frozen all-extras x64 retention are also checked. These are static and local
script checks, not evidence of execution on GitHub runners.

After publication, inspect workflow results at the final implementation head for
[issue 1995](https://github.com/vamseeachanta/worldenergydata/issues/1995).
Full workflow execution on both architectures,
the full Python matrix and the fork fallback remain execution checks.

[routing]: https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow
