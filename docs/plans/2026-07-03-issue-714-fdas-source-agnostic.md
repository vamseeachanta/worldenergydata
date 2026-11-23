# Plan — worldenergydata #714: F1 — extract FDAS into a source-agnostic package + country fiscal-terms decks

- **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/714 (child of epic #713)
- **Status:** v3 (r1 Claude MAJOR + r2 Codex MAJOR both folded); **approved** 2026-07-03 (chat "Approve, and continue work"); implemented same day.
- **Complexity:** T2 | **Lane:** claude (architecture/refactor) | **Execution:** single-lane (shared pyproject/CI surfaces).

## Scope

Carve `fdas` out of the coupled `worldenergydata-bsee` cluster member into its
own source-agnostic member, `worldenergydata-fdas`, so non-US sources can run
field economics without importing the US-GoM `bsee` cluster. Add a strictly
validated **country fiscal-terms deck layer** (v1 = royalty-only consumption)
and preserve exact numerical parity with the BSEE-validated path.

## Feasibility — cycle refutation (Evidence §2)

The `worldenergydata-bsee` pyproject + ADR 0001 documented a `bsee ⇄ fdas`
import cycle as the reason fdas shipped inside the bsee member. **Refuted:** two
independent module-level greps found ZERO `fdas → bsee` / `fdas →
lower_tertiary` edges. fdas is a shared LEAF — `bsee.analysis.production_api12`
and `lower_tertiary.portfolio_{economics,analytics}` import fdas, not the
reverse; fdas's only outbound domain edge is `fdas.api → cost.disclosure_analytics`.
So fdas splits cleanly; the real cycle (`bsee ⇄ lower_tertiary`) is untouched.
Guard: if a real `fdas → bsee` back-edge ever appears, STOP and re-plan.

## Deliverable

1. New workspace member `packages/worldenergydata-fdas/` shipping
   `worldenergydata.fdas` (import path unchanged, PEP 420), decoupled from bsee;
   ADR 0001 + both pyproject cycle comments corrected.
2. Fiscal-terms deck layer — **v1 = royalty-only, `flat|none` models**.
   Versioned strictly-validated YAML decks + fail-closed loader +
   `CashflowEngine.calculate_royalty` integration. Ships 3 decks: `us_gom`
   (per-dev-system royalty == legacy `config.py` values, exact parity),
   `norway` (`model: none`), `uk` (flat 0.0 + EPL metadata). **Brazil deferred
   to #718** (sliding-scale needs a production-rate seam; loader rejects
   `model: sliding_scale` with a #718 pointer). Income-tax / price-marker /
   discount fields are declarative metadata in v1 (revenue/NPV seam → #716).

## Artifact map (implemented)

| Action | Path |
|---|---|
| git mv | `…-bsee/src/worldenergydata/fdas/` → `…-fdas/src/worldenergydata/fdas/` (history-preserving) |
| add | `packages/worldenergydata-fdas/pyproject.toml` (deps: core, cost, numpy, numpy-financial, pandas, openpyxl, pyyaml; package-data `worldenergydata.fdas.fiscal = ["decks/*.yml"]`) |
| add | `packages/worldenergydata-fdas/README.md` (consumed-vs-declarative table) |
| add | `…/fdas/fiscal/{__init__,terms,schema}.py` + `fiscal/decks/{us_gom,norway,uk}.yml` |
| edit | `…/fdas/analysis/cashflow.py` (`fiscal_terms` param + royalty precedence) |
| edit | `…/fdas/__init__.py` (export fiscal surface) |
| edit | `…-bsee/pyproject.toml` (drop fdas include+package-data; drop orphaned cost dep; add fdas dep; rewrite cycle comment) |
| edit | root `pyproject.toml` (add member dep + `[tool.uv.sources]`; fix cycle comments; find-exclude unchanged) + single `uv lock` |
| edit | `docs/adr/0001-domain-package-split.md` (fdas carve-out amendment) |
| edit | `mkdocs.yml` (add member src root) |
| edit | `scripts/ci/select_test_targets.py` (drop fdas from `_CLUSTER_MEMBER_RE`; fdas now auto-routes via `_PACKAGE_MEMBER_RE`) |
| edit | `tests/ci/test_select_test_targets.py` (cluster expectation + new fdas-member routing test) |
| edit | `tests/unit/common/test_namespace_workspace.py` (fdas member-resolution assertion) |
| add | `tests/unit/fdas/fiscal/{test_terms,test_deck_parity,test_cashflow_fiscal}.py` + `tests/unit/fdas/test_packaging.py` |

Two corrections vs. the plan's stated dep list, found on the real tree:
`numpy-financial` **added** (`financial.py` imports it), `scipy` **dropped**
(zero fdas imports).

## Enumeration gates (acceptance)

- **G1** — whole-repo grep of the old fdas path → zero (or each hit patched).
- **G2** — workflows / `module-manifest.yaml` / `MODULE_INDEX.md`: no physical
  member-path enumeration to patch (they reference the unchanged import path).
- **G3** — `uv lock` resolves with no duplicate/conflicting fdas resolution and
  no unrelated version churn.

## Test suites

- **Suite 0 (baseline, pre-move):** scoped set = 371 passed, 2 skipped.
- **Suite 1/2 (packaging/namespace):** member resolution, `worldenergydata.__path__`
  spans the member, decks resolve via `importlib.resources`, cross-member
  consumers still import (`test_packaging.py`).
- **Suite 3 (CI selector):** fdas routes to its own shard; bsee cluster still
  routes its four remaining subpackages; guard test updated.
- **Suite 4 (fiscal schema):** all decks validate; unknown country/field
  fail-closed; `sliding_scale` rejected with #718 pointer; exact-4-keys +
  bounds; provenance required.
- **Suite 5 (parity — do-not-ship-without):** per dev-system, deckless vs
  `us_gom` deck → identical full component vectors + NPV.
- **Suite 6 (non-US decks):** norway `none`→0.0, uk flat 0.0, declarative
  fields provably unconsumed.

## Follow-on issues (filed at closeout, linked to #713)

1. `economics/dcf` ↔ `fdas/core/financial` NPV-surface consolidation.
2. Revenue/NPV price-marker + discount seams (feeds #716).
3. Sliding-scale royalty seam (feeds #718 Brazil).

## Adversarial review

r1 Claude MAJOR (per-dev-system royalty parity; ADR cycle-doc refutation) +
r2 Codex MAJOR (12 findings: pyyaml dep, package-data/install matrix, `flat|none`
restriction + Brazil→#718, parity mechanism, enumeration gates, dep-graph gate,
namespace assertions, strict deck schema, scoped baseline, follow-on
concreteness) — all folded into v3.
