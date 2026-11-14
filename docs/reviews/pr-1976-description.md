## Summary

The approved comparator-only plan for [issue 1284](https://github.com/vamseeachanta/worldenergydata/issues/1284#issuecomment-6856237057) is implemented on main by merged [PR 1968](https://github.com/vamseeachanta/worldenergydata/pull/1968), commit `d6e2c080107972b193fbff0b4616685f3f8d22fe`. The original patch records verification in the UKCS agent pack. This follow-up corrects its documentation and supplies a proposed replacement for the existing PR description.

## Review findings addressed

- P2-1: the replay table now has five header and delimiter cells, so GitHub renders the three evidence rows.
- P2-2: the unshipped-evidence claim is removed; the evidence limits are stated below.
- P3-1: the counts table below now has six header and delimiter cells.
- P3-2: PR state and attribution are corrected in the provenance section below.
- P3-3: revision 2 now explicitly includes the same-day comparator replay addendum.

Regression tests exercise table rendering, evidence disclosure, PR state and authorship, and revision history. Each check failed against the reviewed text before its correction.

## Historical comparator verification

The addendum records the original implementation-job runs with Python 3.12.15 and pytest 9.2.0. The posted second-provider review at `d2dee8f9` independently reproduced these counts:

| Run | Selection | Passed | Failed | Errors | Skipped / xfailed / deselected |
| --- | --- | --- | --- | --- | --- |
| Historical red replay | Comparator tests against pre-fix source | 19 | 21 expected | 0 | 0 / 0 / 0 |
| Focused acceptance | Comparator, reference-chain, field-economics and NSTA-client tests | 102 | 0 | 0 | 0 / 0 / 0 |
| Complete UKCS suite | All nine test modules | 199 | 0 | 0 | 0 / 0 / 0 |

The original implementation-job harness, dependency manifest, sanitized logs and count records were not retained in this PR. This table reports historical observations, rather than supplying those original attachments. The 21 historical failures comprise 17 selector-validation and 4 signed-cashflow regressions; the historical replay changed only the comparator source to parent `1e35ee97d665432e35b3c5e7b5bd09788982a185`.

Current-source and comparator-test SHA-256 fingerprints were recomputed for this follow-up and match the revision-2 digests in the pack. Existing supported-selector, signed-cashflow, short-page and reference-chain regressions are preserved. No arithmetic, fiscal constant, test gate or threshold is changed.

## Scope and open items

Required drilling timelines, empty-production rejection in the reference chain and the FDAS rig-rate/USD unit boundary remain deferred by the approved plan. Passing reference-chain tests do not establish drilling-capital completeness. Fiscal-law qualification, new regimes, report regeneration, data refresh and NSTA transport changes remain outside this slice. Whole-issue completion is not claimed.

## Provenance and publication

This review follow-up was prepared by Codex for the existing PR as a local commit and replacement description. Updating the live PR description remains pending under the files-only job restriction. This job performed no push, post or PR mutation, and called no other model or assistant CLI.

Refs [issue 1284](https://github.com/vamseeachanta/worldenergydata/issues/1284).
