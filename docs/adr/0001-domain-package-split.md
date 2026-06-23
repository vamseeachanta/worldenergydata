# ADR 0001 — Independent per-domain package artifacts for `worldenergydata`

- **Status:** Proposed — **DECISION REQUIRED (owner sign-off) before any restructure**
- **Date:** 2026-06-22
- **Issue:** [#529](https://github.com/vamseeachanta/worldenergydata/issues/529) (P3, under epic #526)
- **Type:** Design spike. This ADR validates the approach and records a recommendation. **No package restructure, `pyproject.toml` change, or `uv.lock` change is included.** The proof-of-concept was run entirely in `/tmp` against throwaway scratch packages; the real `src/worldenergydata/` was not modified.

---

## Context

`worldenergydata` ships today as **one wheel, one version**:

- `build-backend = "setuptools.build_meta"`, single distribution `name = "worldenergydata"`, `version = "0.1.0"`.
- `[tool.setuptools.packages.find] where = ["src"]; include = ["worldenergydata*", "external*", "modules*"]` — one wheel auto-discovers everything under `src/`.
- One flat `dependencies` list (~30 runtime deps incl. scrapy, selenium, fastapi; heavier ML pushed to `[project.optional-dependencies]`: `llm`, `safety-ml`, `safety-bert`).
- One console script: `worldenergydata = worldenergydata.cli.main:app`.
- `requires-python = ">=3.10"`; hard dep `assetutilities>=0.1.0,<1.0`.

`src/worldenergydata/` is **44 top-level subpackages** — a genuine monolith spanning regulatory/safety, production/markets, infrastructure, metocean, reporting, and analysis domains.

The **#529 goal** is independently *installable* and *versioned* per-domain artifacts (e.g. `worldenergydata-bsee`, `worldenergydata-subsea`, each at its own version, sharing a common core), so a consumer can install one domain without the whole monolith's dependency footprint, and each domain can be released on its own cadence.

This is the largest and highest-risk item in the epic. The whole effort is gated on one empirical question — **how tangled is the cross-domain import graph?** — which this spike answers.

---

## Evidence

### 1. Cross-domain import coupling (measured on `main`)

Method: walked every `.py` under each top-level subpackage and counted `from worldenergydata.<X> import` / `import worldenergydata.<X>` references, classifying targets as **infra/shared** (`common`, `base_configs`, `cli`, `reporting`, `validation`, `analysis`, `testing`, `modules`, `scheduler`, `dashboard`) vs **data domains**. 1440 total intra-package import lines.

**`common` is unambiguously the shared core.** Fan-in (distinct domains importing a target):

| Target | Imported by N domains | Kind |
|---|---|---|
| `common` | **26** | infra (THE core) |
| `bsee` | 7 | data domain (hub) |
| `fdas` | 3 | data domain |
| `sodir` | 3 | data domain |
| `lower_tertiary`, `texas_rrc`, `metocean`, `eia`, `marine_safety` | 2 each | data domain |
| everything else | 1 | — |

**The graph is far cleaner than feared.** Of 34 data domains:

- **ISOLATED (13)** — import *nothing* intra-package (not even `common`): `baker_hughes`, `cost`, `decommissioning`, `drilling`, `drilling_pressure_management`, `economics`, `eia`, `eia_us`, `marine`, `reservoir`, `well_bore_design`, `well_planning`, `west_africa`.
- **LEAF (16)** — import **only** infra/`common`, no other data domain: `brazil_anp`, `canada`, `landman`, `lng_terminals`, `marine_safety`, `metocean`, `mexico_cnh`, `pipeline_safety`, `production`, `safety_analysis`, `sodir`, `subsea`, `texas_rrc`, `ukcs`, `vessel_fleet`, `vessel_hull_models`.
- **COUPLED (5)** — import other data domains:
  - `bsee` → `lower_tertiary`, `fdas`, `sodir`, `texas_rrc`
  - `lower_tertiary` → `fdas`, `bsee`
  - `well_production_dashboard` → `bsee`
  - `hse` → `bsee`
  - `fdas` → `cost`

So **29 of 34 domains (85%) are trivially splittable** (ISOLATED + LEAF). The only real tangle is a small cluster around `bsee` ⇄ `lower_tertiary`/`fdas` (a cycle) plus `bsee`'s satellites (`hse`, `well_production_dashboard`). `bsee` is the one true hub.

### 2. The root `__init__.py` has runtime side effects (the crux of the namespace question)

`src/worldenergydata/__init__.py` is **not** a thin shim. It:

- defines `__version__ = "0.1.0"`,
- installs a `sys.meta_path` finder via `worldenergydata._compat.install_redirect()` (redirects legacy `worldenergydata.modules.X` → `worldenergydata.X` with a `DeprecationWarning`),
- exposes a lazy top-level `__getattr__` (`marine_safety_api`).

The issue's option (b) assumed a PEP 420 namespace requires **deleting** this root `__init__.py` — a behavioral break. **The POC disproves that assumption** (see below).

### 3. Proof-of-concept results (all run in `/tmp`, throwaway, real `src` untouched)

Environment: Python 3.12 / 3.11, setuptools build backend, `uv 0.11.21`.

- **POC 1 — two separately-built wheels, shared namespace.** Built `worldenergydata-core` (ships `worldenergydata/common/`) and `worldenergydata-bsee` (ships `worldenergydata/bsee/`, depends on core), **no root `__init__.py`** (PEP 420). Installed both into one venv. `import worldenergydata.common` and `import worldenergydata.bsee` both work, and `bsee` cross-imports `common`. ✅ **Independent distributions can share `worldenergydata.*`.**

- **POC 3 — the realistic multi-location case** (the one that actually matters for a uv workspace / editable installs, where each member lives in a different directory):
  - **Case A — PEP 420 (no root `__init__` anywhere):** `worldenergydata.__path__` spans *both* locations; both subpackages import. ✅
  - **Case B — regular root `__init__.py` shipped only by core, `bsee` elsewhere:** `import worldenergydata.bsee` → **`ModuleNotFoundError`**. ❌ **This is the trap:** a plain (regular-package) root `__init__.py` pins `__path__` to one location and blocks distributed extension.
  - **Case C — regular root `__init__.py` + `pkgutil.extend_path`:** `__path__` spans both locations, `bsee` imports, **and `__version__` is preserved.** ✅

- **POC 4 — the *real* `_compat.py` + version + lazy `__getattr__` with a split-out domain.** Copied the actual `src/worldenergydata/_compat.py` into a scratch core, gave the root `__init__` `__version__` + `pkgutil.extend_path` + the real `install_redirect()`, and put `bsee` in a *separate* location. Result: `worldenergydata.bsee` imports from the split-out location **and** the legacy `worldenergydata.modules.bsee` → `worldenergydata.bsee` compat redirect still works. ✅ **The existing side-effecting root `__init__.py` does NOT have to be deleted** — it must adopt `extend_path` (or be marked a pkgutil-style namespace).

- **POC 5 — full target shape: uv workspace.** A `[tool.uv.workspace]` with `packages/core` (v0.1.0) and `packages/bsee` (v0.2.0, `dependencies = ["worldenergydata-core"]`, `[tool.uv.sources] worldenergydata-core = {workspace = true}`). `uv pip install -e` both. Result: `worldenergydata.bsee.whoami()` resolves `worldenergydata.common` across members; `importlib.metadata` reports `core=0.1.0`, `bsee=0.2.0` as **independent distributions**, shared namespace, editable. ✅ **The literal #529 deliverable is achievable end-to-end with uv, which is already adopted here.**

### 4. Downstream blast radius (measured against local clones)

| Consumer | `import worldenergydata.*` (code) | Notes |
|---|---|---|
| `digitalmodel` | 16 import lines, into: `economics` (20 refs), `cost` (10), `eia_us` (5), `decommissioning` (4), `west_africa` (2), `ukcs` (2), `sodir` (2), `brazil_anp` (2), `fdas` (1) | **All but `fdas` are in the ISOLATED/LEAF tier.** |
| `deckhand` | **0** code imports | only a compute-clone path + wiki-repo name; no `import worldenergydata.*`. |
| `assetutilities` | **0** real code imports | only repo-name strings in agent_os tooling/tests + units adapters documented as "matching" wed (no import). |

The downstream import surface is **small and concentrated in `digitalmodel`, and it targets exactly the cheapest-to-split domains.** Provided the import path `worldenergydata.<domain>` is preserved (which POCs 1/4/5 confirm is possible), downstream churn is **zero**.

---

## Options

### (a) uv workspace — multiple member packages (`worldenergydata-core` + per-domain)
`[tool.uv.workspace]` with members `packages/core`, `packages/bsee`, … each its own distribution, depending on `worldenergydata-core` via workspace sources.
- **Pros:** True independent versions/release tags/wheels (the #529 goal). Per-package dependency sets (subsea need not pull scrapy/selenium). uv already adopted. Clean per-domain CI matrix (dovetails P1/P4). **Validated working (POC 5).**
- **Cons:** Largest physical restructure (every domain moves into `packages/<domain>/src/...`). Hidden cross-domain imports become hard build breaks until declared. N `pyproject.toml` to maintain; publishing N distributions is real release overhead.
- **Blast radius:** High *internally* (layout + declared edges + CI + entry point); **zero downstream** if namespace import path is preserved.

### (b) PEP 420 native-namespace split — keep `worldenergydata.<domain>` import path, split into separate distributions
Same import paths, multiple distributions each contributing to the `worldenergydata` namespace package.
- **Pros:** **Zero import churn** internally and downstream. Separates *distribution* from *import* concern — exactly #529's intent. Industry-proven (`azure-*`, `google-cloud-*`). **Validated (POC 1/3A).**
- **Cons (revised by POC):** The issue assumed this requires *deleting* the side-effecting root `__init__.py`. **POC 3C/4 show that is false** — the root `__init__.py` can keep `__version__`, `_compat`, and lazy `__getattr__` if it adopts `pkgutil.extend_path` (or is declared a pkgutil-style namespace). The remaining real risk is misconfiguration (two distros both claiming the namespace root) and historically-finicky editable + namespace behavior — **both passed in POC 4/5.**
- **Blast radius:** Moderate internally (packaging + the `__init__` `extend_path` change); **zero downstream.**

> **(a) and (b) are the same destination, not alternatives.** (a) is the *project layout / build / release* mechanism; (b) is the *import-stability* mechanism. The target is **a uv workspace whose members all publish into the shared `worldenergydata` namespace** (validated together in POC 5).

### (c) one package + per-domain optional-dependency extras + independent release tags
Stay one `worldenergydata` distribution; formalize per-domain `[project.optional-dependencies]` extras (`worldenergydata[bsee]`, `[subsea]`, …); cut per-domain git tags.
- **Pros:** **Smallest change** — no source moves, no import change, no namespace surgery. Immediate install-weight win via extras. Extends the existing `llm`/`safety-ml` extras pattern. Reversible.
- **Cons:** **Not actually independent artifacts** — `worldenergydata-bsee` as a pip-installable distribution does not exist; everyone still installs one wheel at one version. Per-domain "release tags" are cosmetic. Extras gate *dependencies*, not *code* (`worldenergydata.bsee` is still importable/present without the `[bsee]` extra). **Does not satisfy the literal #529 deliverable.**
- **Blast radius:** Low.

### (d) status quo
One package, one version, flat deps, full rebuild/release on any change.
- **Pros:** zero cost.
- **Cons:** meets none of #526's package goals; one heavy dependency footprint and one release cadence for all 44 subpackages.

---

## Decision (recommended)

**Adopt the combined (a)+(b) — a uv workspace whose member packages publish into a shared `worldenergydata` PEP 420 / pkgutil namespace — as the target architecture, and ship (c) immediately as a low-risk down-payment.** This validates the prior comment on #529, with two refinements the POC earned:

1. **The root `__init__.py` does NOT need to be deleted** (correcting option (b)'s stated con). It must adopt `pkgutil.extend_path` so `__version__` + the `_compat` legacy redirect + lazy `__getattr__` survive a distributed split. (POC 4 proves the *real* `_compat.py` coexists with a split-out domain this way.)
2. **The graph is clean enough to make the rollout cheap:** 29 of 34 domains are ISOLATED/LEAF; the only real tangle is the `bsee` ⇄ `lower_tertiary`/`fdas` cycle plus `bsee`'s satellites (`hse`, `well_production_dashboard`).

Rejected:
- **Pure (a) without (b)** (renaming imports to `worldenergydata_bsee`): rejected — unnecessary downstream blast radius; POC shows the namespace path can be preserved for free.
- **(c) as the end state**: rejected — does not deliver independent installable/versioned distributions; valid only as a down-payment.
- **(d)**: rejected — punts the problem.

---

## Phased migration plan

0. **This ADR (gate).** Coupling graph + POC delivered. **No code until sign-off.**
1. **(c) down-payment** (days, low risk, reversible): add per-domain `[project.optional-dependencies]` extras; document per-domain release tagging. Immediate install-weight win, no restructure.
2. **Carve out the core** (first workspace member): extract `worldenergydata-core` = the shared infra (`common`, `base_configs`, `engine`, `cli`, `reporting`, `validation`, `analysis`, `testing`). Convert the root `__init__.py` to `pkgutil.extend_path` (keep `__version__`/`_compat`/lazy `__getattr__`). Everything else stays in the legacy package depending on core. Validate namespace + editable + CI on this single carve. (POC 4/5 are the rehearsal.)
3. **Pilot one ISOLATED domain** (cleanest possible — e.g. `eia_us` or `west_africa`, both ISOLATED *and* imported by `digitalmodel`, so the downstream smoke test is real). Publish `worldenergydata-<domain>` into the shared namespace; prove independent version + release + install end-to-end **plus a `digitalmodel` import smoke test.**
4. **Roll out domain-by-domain, most-isolated first** (ISOLATED → LEAF → COUPLED). Each conversion is its own PR with a downstream-import smoke test. **Ship the `bsee` cluster as a single member** (`bsee` + `lower_tertiary` + `fdas` + `hse` + `well_production_dashboard`) rather than splitting the cycle, OR break the `bsee` ⇄ `lower_tertiary`/`fdas` cycle first (separate refactor) — decide at step 4.
5. **Wire per-domain build/test/publish into the P1 domain matrix and the P4 reusable workflow.** Keep #526's single aggregate required check.

## Risks

- **Highest-risk, largest item in the epic.** Explicit owner sign-off required before any code (this section).
- **Namespace root misconfiguration:** exactly one place may own `worldenergydata/__init__.py`; all others must be `__init__`-less or pure namespace. Mitigated by the `extend_path` core + a CI guard asserting no second root `__init__.py`.
- **The `bsee` cycle:** `bsee` ⇄ `lower_tertiary`/`fdas` cannot be cleanly split into independent wheels without either (a) shipping them as one member or (b) breaking the cycle first. Do not attempt to split mid-cycle.
- **Console-script entry point** (`worldenergydata = worldenergydata.cli.main:app`) and `engine.py`/`__main__.py` dispatch must keep working. Decide whether the CLI lives in core and discovers domain plugins, or stays a meta-package depending on all domains. `cli` currently imports 14 domains directly — treat `cli` as core/meta, not a leaf.
- **Version skew:** independently versioned domains depending on a shared core need a core version-pinning policy, else lockstep returns by the back door.
- **Editable + namespace finickiness:** historically the sharpest edge; passed in POC 4/5 with `uv 0.11.21` + modern setuptools, but re-validate on the real tree at step 2.

---

## DECISION REQUIRED — owner sign-off before any restructure

This ADR is a **spike deliverable only**. Per #529, **no source move, no `pyproject.toml`/`uv.lock` change, and no namespace surgery may begin until the owner signs off on:**

1. the **target** = uv workspace + shared `worldenergydata` namespace (combined a+b);
2. the **down-payment** = ship (c) extras first;
3. the **core boundary** (which modules are `worldenergydata-core`);
4. the **`bsee` cluster** decision (ship-as-one-member vs. break-the-cycle-first);
5. the **CLI** ownership (core/meta vs. plugin discovery).

Sign-off here, then implementation proceeds PR-by-PR per the phased plan, each with a `digitalmodel` downstream smoke test.

---

## Phase 1 implementation note (foundation — issue #529)

Phase 1 lands the low-risk, reversible foundation that *enables* the split
without moving any domain code (code-carving is Phase 2, gated on this being
reviewed). What shipped in this PR:

1. **Namespace-extensible root package.** `src/worldenergydata/__init__.py`
   now adopts `__path__ = pkgutil.extend_path(__path__, __name__)` (ADR POC 3
   Case C / POC 4). `__version__`, the `_compat` legacy redirect, and the lazy
   `__getattr__` are all preserved — this is a no-op for the current single
   distribution and introduces no behavior change. It lets the
   `worldenergydata` namespace later be contributed to by multiple
   independently-built/-versioned distributions (the Phase 2 uv workspace
   members), so downstream `import worldenergydata.<domain>` stays unchanged.

2. **Per-domain optional-dependency extras — DEFERRED (the (c) down-payment).**
   Investigated whether domains have cleanly separable third-party deps.
   They do **not** yet: the heavy deps are shared across many domains *and*
   across shared infra, so nothing can move out of always-installed core
   without breaking core. Measured on `main`:
   - `bs4` → 7 domains **+ `common`** (bsee, lng_terminals, marine_safety,
     metocean, vessel_fleet, west_africa)
   - `plotly` → 13 areas incl. **`common`, `reporting`, `testing`, `dashboard`**
   - `sqlalchemy` → 5 areas incl. **`cli`** (hse, marine_safety, metocean,
     pipeline_safety)
   - `pdfplumber` → 5 domains; `selenium` → **`cli`** + mexico_cnh
   Because shared infra (`common`/`cli`/`reporting`/`testing`) itself pulls
   `bs4`/`plotly`/`sqlalchemy`/`selenium`, per-domain extras would be
   cosmetic (and option (c)'s own con notes extras gate *dependencies*, not
   *code*). Meaningful per-domain extras require the Phase 2 package
   boundaries to exist first, at which point each member declares its own
   dependency set. **The (c) down-payment is deferred to Phase 2.** The
   existing `dev`/`test`/`docs`/`llm`/`safety-ml`/`safety-bert` extras are
   left untouched.

3. **uv workspace scaffolding (prep only, no members).** `pyproject.toml`
   carries a **commented** `[tool.uv.workspace]` / `[tool.uv.sources]` block
   documenting the intended Phase 2 members layout. It is commented because
   activating workspace mode requires member packages to exist; doing so now
   would break the single-package build. No member packages created, no code
   moved.

**Validated (real commands on the fresh clone):**
- `uv build --wheel` succeeds; the wheel still contains **all 43**
  `worldenergydata.*` subpackages (extend_path did not break
  `[tool.setuptools.packages.find]` discovery), and the shipped
  `__init__.py` carries `extend_path`.
- Installed the wheel into a clean venv: `worldenergydata.__version__` ==
  `0.1.0`; `worldenergydata.__path__` is a real extensible list;
  `worldenergydata.common`, `from worldenergydata import bsee`, lazy
  `worldenergydata.marine_safety_api`, and the legacy
  `worldenergydata.modules.bsee` → `worldenergydata.bsee` redirect (with
  `DeprecationWarning`, identity-preserving) all work.
- `pytest tests/unit/common tests/unit/bsee tests/contracts` →
  3013 passed, 29 skipped (pre-existing environmental skips), 0 failures.
  `tests/unit/test_modules_compat.py` → 3 passed.
- `uv.lock` deliberately kept out of the diff.

**Phase 2 readiness:** the namespace mechanism is live and proven on the real
tree; downstream import path is unchanged. The gated next step is carving
`worldenergydata-core` (the fan-in-26 shared infra) as the first uv workspace
member, then rolling out leaf domains most-isolated-first, each as its own PR
with a `digitalmodel` downstream smoke test — exactly the phased plan above.
