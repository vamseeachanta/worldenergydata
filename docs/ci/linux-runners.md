# Linux runner routing and ARM64 dependency limits

`ci.yml`, `main-full-run.yml`, `docs.yml` and `brand-guard.yml` request
`[self-hosted, Linux]`. Either architecture can match those labels. The existing
fork predicate and `ubuntu-latest` fallback remain in CI, docs and brand guard.
Job identifiers, displayed check names, triggers and permissions are unchanged.

For example, both `{self-hosted, Linux, X64}` and
`{self-hosted, Linux, ARM64}` contain the two requested labels. Hand counting
the local jobs gives 6 + 10 + 1 + 1 = 18 selectors. GitHub matches all requested
labels; see [runner routing][routing]. This example is a label check, not evidence
of workflow execution.

## Workflow audit

All steps in the 18 local jobs were inspected. There are no pinned x86 download
URLs or wheels, architecture-specific artifact names, apt installations,
hardcoded X64 cache keys, or architecture overrides in setup-python/setup-uv
inputs. Python and uv select their default architecture. Artifact names use
Python versions or purpose rather than CPU architecture. No step changes are
required by that inspection.

The `domain-tests` job in CI calls an external reusable workflow at `main`.
Its runner selection is owned there and is not covered by these 18 selectors.
Its effective routing still requires verification. No external workflow or
other local workflow is changed.

## Frozen dependency audit

The audit on 2026-11-04 inspected all 387 entries in `uv.lock`: 347 registry
entries, 39 editable workspace entries and one Git source. The lockfile SHA-256
is `11de511052ef773fe35303e189d1bf251d10cac1df6bf96242ec876c9b8b4e0a`.
The following 24 registry entries have neither a Linux aarch64 wheel nor a
universal `*-any.whl` in that lockfile. Source archives and incoming dependency
markers were inspected separately; missing wheels alone do not imply failure.
See the [wheel tag specification][tags].

| Locked dependency | Linux ARM64 disposition |
| --- | --- |
| `nlopt==2.10.0` | Required by the CAD extra through CadQuery; no aarch64 wheel or source archive. Blocks frozen `--all-extras` installation. |
| `cartopy==0.25.0` | Selected through metocean-stats on Python 3.10; source archive exists, so a source build is required. Python 3.11/3.12 select 0.26.0, which has aarch64 wheels. |
| `pandoc==2.4` | Source archive only; source installation and the external executable require runner validation. |
| `undetected-chromedriver==3.5.5` | Source archive only; browser and driver compatibility require runner validation. |
| `wkhtmltopdf==0.2` | Source archive only; source installation and the external executable require runner validation. |
| `pypydispatcher==2.1.2` | Source archive only; Scrapy selects it only on PyPy, outside the CPython matrix. |
| `excel2img==1.4.0` | Source archive only; incoming dependency is Windows-only. |
| `pywin32==311` | Windows wheels only; incoming dependency paths are Windows-only. |
| `cuda-bindings==12.9.4` | Torch selects this only on x86_64 Linux. |
| `nvidia-cublas-cu12==12.8.4.1` | Torch selects this only on x86_64 Linux. |
| `nvidia-cuda-cupti-cu12==12.8.90` | Torch selects this only on x86_64 Linux. |
| `nvidia-cuda-nvrtc-cu12==12.8.93` | Torch selects this only on x86_64 Linux. |
| `nvidia-cuda-runtime-cu12==12.8.90` | Torch selects this only on x86_64 Linux. |
| `nvidia-cudnn-cu12==9.10.2.21` | Torch selects this only on x86_64 Linux. |
| `nvidia-cufft-cu12==11.3.3.83` | Torch selects this only on x86_64 Linux. |
| `nvidia-cufile-cu12==1.13.1.3` | Torch selects this only on x86_64 Linux. |
| `nvidia-curand-cu12==10.3.9.90` | Torch selects this only on x86_64 Linux. |
| `nvidia-cusolver-cu12==11.7.3.90` | Torch selects this only on x86_64 Linux. |
| `nvidia-cusparse-cu12==12.5.8.93` | Torch selects this only on x86_64 Linux. |
| `nvidia-cusparselt-cu12==0.7.1` | Torch selects this only on x86_64 Linux. |
| `nvidia-nvjitlink-cu12==12.8.93` | Torch selects this only on x86_64 Linux. |
| `nvidia-nvshmem-cu12==3.4.5` | Torch selects this only on x86_64 Linux. |
| `nvidia-nvtx-cu12==12.8.90` | Torch selects this only on x86_64 Linux. |
| `triton==3.6.0` | Torch selects this only on x86_64 Linux. |

Table 1. Locked entries without Linux aarch64 or universal wheels.

The missing files for [nlopt 2.10.0][nlopt] and [Cartopy 0.25.0][cartopy] were
also checked against public release metadata. A separate constraint applies to
`cadquery-ocp==7.9.3.1.1`: its locked aarch64 wheels require glibc 2.31 or newer.
The host glibc versions have not been measured here.

Cross-platform probes used uv 0.11.28 and Python target 3.11:

```bash
uv pip compile pyproject.toml --all-extras \
  --python-platform aarch64-unknown-linux-gnu --python-version 3.11
uv pip compile pyproject.toml --all-extras \
  --python-platform aarch64-manylinux_2_31 --python-version 3.11
```

The first probe failed because its default glibc target did not admit the
CadQuery OCP wheel. The second resolved 367 packages using current versions;
it did not validate the frozen lockfile. A separate binary-only compile of
`nlopt==2.10.0` failed for aarch64. Resolution does not demonstrate a successful
installation or execution; see [uv platform resolution][uv]. No dependency or
lockfile changes are included.

## Verification and follow-up

Run the routing regression without project-wide fixtures or coverage output:

```bash
uv run --no-sync python -m pytest --noconftest -o addopts= \
  -p no:cacheprovider tests/ci/test_runner_routing.py -q
```

The regression checks each local job and the exact fork fallback expression.
On 2026-11-04 it passed all four cases after failing all four against the original
selectors. A broader isolated Python 3.12 run of `tests/ci` produced 334 passes,
41 failures and 5 skips. Of those failures, 14 lacked `plotly` or
`pydantic_settings` in the isolated environment; 27 failed while creating Git
fixture commits. A disposable probe reproduced the latter: text-mode stdin
returned `badTreeSha1`, while the same commit bytes succeeded. Those tests are
unchanged and the broader folder is not reported as passing. YAML lint passed
with two existing line-length warnings; isort passed. Black did not finish
within a 30-second limit. No workflow was executed in this environment.

The routing, replay-checkout and test-target selector files were also run
together: 196 passed and 3 skipped. The skipped cases require Linux shell
execution and were skipped by the existing test guards.

Before relying on self-hosted ARM64 runners for full runs, resolve the frozen
CAD dependency gap, verify the Python 3.10 source build and installed external
tools, and confirm the reusable workflow's routing. Then run all four workflows
on the actual runners, including the full Python matrix and fork fallback
checks. ARM64 execution is not established by this static audit.

[routing]: https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow
[tags]: https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/
[uv]: https://docs.astral.sh/uv/concepts/resolution/#platform-specific-resolution
[nlopt]: https://pypi.org/pypi/nlopt/2.10.0/json
[cartopy]: https://pypi.org/pypi/cartopy/0.25.0/json
