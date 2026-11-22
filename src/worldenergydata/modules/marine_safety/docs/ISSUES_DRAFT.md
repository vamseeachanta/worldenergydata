# Marine safety compatibility issue drafts

These two drafts concern the compatibility boundary. Canonical-package test defects remain tracked by the [canonical marine-safety pack](../../../../../packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/docs/agent-pack.md) (#1236), section 6 and section 10 C4–C10, including drafts 1, 3, 4, 5, 7 and 8 in the canonical [ISSUES_DRAFT.md](../../../../../packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/docs/ISSUES_DRAFT.md). They must not be filed again from this list. Existing collection references remain #1239 and #327.

## Draft 1: Reconcile compatibility exports and missing-target diagnostics

Responsible role: module maintainer.

At code revision `72716499230d3457ce90a5bcd23a8a8367bc0bd3`, the compatibility analysis initializer declares `CauseAnalysisReport` and `ReportFilters`, but the active redirect selects the canonical analysis initializer, which binds neither. Check C1 in [agent-pack.md](agent-pack.md) records 2 missing exports among 14 declarations. The direct canonical `analysis.cause_report` import is the tested route.

The shared finder also catches `ModuleNotFoundError` and `ValueError` during target resolution and returns no spec; no dedicated check establishes the missing-target diagnostic contract. C5 establishes available-target identity and deprecation warnings in both import orders; missing-target errors remain unverified. Evidence: [src/worldenergydata/_compat.py:L103-L123] and [src/worldenergydata/modules/marine_safety/analysis/__init__.py:L13-L36].

The original assessment did not commit identity or warning evidence. The current
`tests/unit/test_modules_compat.py` covers the five suffixes in both import orders
with `is` and `pytest.warns(DeprecationWarning)`, and strengthens known attribute
access to require canonical object identity. These checks already exist at the
current base; their passing result closes only the available-target evidence gap.
They do not establish missing-export or missing-target diagnostics.

Required resolution:

- Reconcile declared and active exports and add a regression check covering all 14 declarations.
- Define and test missing-target diagnostics, including errors raised inside a canonical dependency.
- State compatibility maturity and reconcile wider documentation claims against the canonical assessment (U1 and U2).
- The pack explicitly names this file as an unfiled placeholder. Replace the placeholder only after a maintainer files this draft.

## Draft 4: Register compatibility method families in the implementation map

Responsible role: registry maintainer.

The implementation-map audit at `3256bab95f84da3d9fadce8d5dcf8458d66d1eb4` contains no implementation row inside `src/worldenergydata/modules/marine_safety/`. Section 9 therefore records an empty inventory and a counted-family grep of `NOT_APPLICABLE`.

Required resolution:

- Register legacy import dispatch, wildcard export and explicit export, the three method families in section 3, with their compatibility paths and the shared dispatch helper.
- Distinguish delegating compatibility helpers from independent incident-analysis implementations.
- Recompute the inventory and counted-family selection from the first map revision containing in-package rows.
- The pack explicitly names this file as an unfiled placeholder. Replace the placeholder only after a maintainer files this draft.
