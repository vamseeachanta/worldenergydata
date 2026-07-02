# Codex Inline Plan Review - Issue #695

**Plan:** `docs/plans/2026-07-02-issue-695-texas-rrc-field-opportunity-architecture-ranking.md`
**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/695
**Reviewer:** Codex inline
**Date:** 2026-07-02
**Default stance:** non-approve unless defects are explicitly resolved

## Verdict

APPROVE FOR USER APPROVAL REQUEST after the mitigations embedded in this plan.

## Findings

### Finding 1 - MAJOR - Opportunity scores can imply economics or reserves

A combined opportunity score can be misread as NPV, reserves, or commercial
attractiveness, especially when ranked output is used for field-development
screening.

Resolution in plan: the score is explicitly named a deterministic screening
heuristic with `texas_rrc_field_opportunity_v1`; component scores, weights,
quality penalties, and caveats are emitted in the ranking output and manifest.
The plan excludes reserves, economics, tariffs, capacity, right-of-way, and
engineered design.

### Finding 2 - MAJOR - Architecture classes can overstate engineering certainty

Labels such as high-access redevelopment or constrained activity could be
mistaken for a facility architecture recommendation.

Resolution in plan: the vocabulary uses `architecture_signal_*`, each row emits
reason and follow-up text, and the plan explicitly says these are screening
signals rather than engineered architecture decisions.

### Finding 3 - MODERATE - Operator concentration is not automatically good or bad

The issue asks for an operator concentration component, but concentration can
mean easier engagement, blocked opportunity, or merely a reporting artifact.
Treating it as a directional value score would be unjustified.

Resolution in plan: the component is constrained to decision context. It
rewards reliable operator evidence, records concentrated or fragmented context
in `key_drivers`, and does not claim either state is economically superior.

### Finding 4 - MODERATE - Existing field-atlas summary omits some infrastructure detail

The #666 summary does not expose every #665 infrastructure field, such as the
nearest pipeline identifier. Depending only on the summary could lose
potentially useful traceability.

Resolution in plan: #666 summary is the preferred primary input, and upstream
#664/#665/#663 manifests and datasets remain fallback inputs. The stable #695
contract stays at class/score/distance/count level; it does not require hidden
pipeline identifiers.

### Finding 5 - MODERATE - Missing lifecycle and GIS data can dominate top fields

The current field-atlas output preserves caveats including missing lifecycle,
missing well GIS, lease-level production, and RRC GIS screening-only distances.
A naive ranking could put high-production but low-confidence fields at the top
without surfacing confidence loss.

Resolution in plan: missing source values add quality penalties, low-confidence
classification is first in rule order, and caveats/quality flags are stable
output columns.

### Finding 6 - MINOR - Dirty code revision in the #666 manifest is provenance,
not a source gap

The live #666 manifest was generated at `2026-07-02T02:27:21Z` with a
`+dirty` code revision. Blocking #695 on that would create unnecessary churn
because the source gaps are empty and the artifact is already materialized.

Resolution in plan: the downstream manifest will record the upstream code
revision while treating it as provenance rather than a missing-source condition.

## Required implementation watchpoints

- Keep all publication output under
  `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/`.
- Add tests before implementation for scoring, architecture classes, quality
  penalties, output persistence, HTML rendering, and CLI wiring.
- Ensure the CLI does not fetch PatchOps or network sources.
- Keep the ranking formula in one versioned location so later scoring versions
  can be added without breaking existing artifacts.
- Run a bounded `--max-fields` smoke build before full 67,082-row publication.
