# Semiconductor CAD/FEM research taxonomy

The offline catalog connects technical vocabulary, candidate role families and
proposed portfolio artifacts. It provides a starting point for reviewing a
supplied job description. A keyword match establishes a text occurrence only;
current hiring demand, suitability, artifact completion and engineering
acceptance remain `NOT_EVALUATED`.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Added a sourced catalog and literal evidence report to make portfolio planning reproducible. |

## Scope and basis

The catalog implements a bounded part of #1084. Its role families and artifact
requirements are editorial mappings informed by the technical sources below,
rather than observed vacancy counts or assertions about particular employers.
No personal job-scan records are imported. There are no engineering equations,
material constants, acceptance limits, proficiency scores or ranking weights.

- Slice 1: immutable sources, skills, role families and proposed artifacts.
- Slice 2: deterministic matching of explicit keyword phrases in supplied text.
- Slice 3: JSON catalog and keyword-evidence reports for offline reuse.

## Role-to-skill and artifact matrix

Artifact entries describe work still to build. A catalog entry must never be
used as evidence that a tool was run or a benchmark passed.

| Role family | Skills to demonstrate | Proposed evidence | Technical basis |
| --- | --- | --- | --- |
| ASIC physical design | Digital implementation; process design kit configuration | Reproducible RTL-to-GDS report with process provenance and timing/area interpretation | OpenROAD; OpenLane |
| CAD/layout automation | Scripted layout database operations; process context | Parameterized export/import example with geometry invariants and metadata | KLayout Python; OpenLane |
| Physical design rule verification | Geometric rule checks; process-rule provenance | Scripted rule report with documented rule origins | KLayout DRC; OpenLane |
| Packaging thermal simulation | Finite element heat transfer | Package thermal benchmark with sourced properties, boundary conditions and mesh convergence | Elmer heat model |
| Packaging thermomechanical simulation | Linear elasticity; thermal stress | Package mechanics benchmark with sourced properties, restraints and an independent reference | Elmer elasticity model |

The packaging context is a proposed application of general heat and elasticity
models, rather than a semiconductor qualification endorsed by the model manual.
The role matrix is deliberately incomplete: layout-versus-schematic checking,
reliability/fatigue models and technical program roles need further research.

## Usage

From a source checkout, emit the catalog without installing CAD or FEM tools:

```bash
PYTHONPATH=src python -m worldenergydata.semiconductor catalog
```

Review caller-supplied text using standard input:

```bash
printf '%s\n' 'OpenROAD and DRC experience' |
  PYTHONPATH=src python -m worldenergydata.semiconductor match
```

The JSON retains source references, skill definitions, matching aliases and the
selected role/artifact mappings. It does not repeat the supplied text. Python
callers can import `match_roles` and the immutable `ROLES`, `SKILLS`, `SOURCES`
and `ARTIFACTS` tuples from `worldenergydata.semiconductor.taxonomy`.

Case is ignored. Punctuation, underscores, hyphens and whitespace separate ASCII
letter/digit tokens. Complete phrases match; `OpenROADmap` does not match
`openroad`. All matching aliases are retained once in catalog order; roles are
also returned in catalog order. There is no stemming, ranking, inferred synonym
or negation handling. For example, `no DRC required` still contains `drc`, and
`heat transfer in buildings` still contains `heat transfer`. Human review must
establish context. Non-ASCII terminology is outside the curated vocabulary.

## Sources

All sources were opened on 2026-10-19. Web pages are unversioned; the catalog
records that retrieval date rather than inferring a software release.

- [OpenROAD documentation](https://openroad.readthedocs.io/en/latest/), introduction and application/flow overview: digital physical implementation vocabulary.
- [OpenLane: Using PDKs](https://openlane2.readthedocs.io/en/latest/usage/about_pdks.html), process design kits and configuration: process context for reproducible flows.
- [KLayout Python scripting documentation](https://www.klayout.de/doc-qt5/programming/python.html), Python macros and database API: scripted layout operations.
- [KLayout DRC basics](https://www.klayout.de/doc-qt5/manual/drc_basic.html), basic scripts and report database: geometric width/space checks. Its illustrative dimensions are not adopted as process rules.
- [Elmer Models Manual](https://www.nic.funet.fi/pub/sci/physics/elmer/doc/ElmerModelsManual.pdf), January 20, 2026 edition, software version 26.1, Heat Equation and Linear Elasticity chapters: heat-transfer, elasticity and thermal-stress vocabulary. No equations or material values are implemented here.

The Elmer website returned HTTP 403; the cited institutional document copy was
opened successfully. No documentation payload is redistributed by this change.

## Validation and later slices

Tests manually enumerate synthetic keyword evidence, role/artifact mappings,
empty and invalid inputs, word boundaries, repeated aliases and ambiguous
phrases. Referential checks ensure every skill resolves to a source and every
role resolves to proposed artifacts covering its skills. Report tests exercise
both module commands from another working directory, deterministic JSON and
explicit unevaluated assessments. Expected results are editorial contracts,
not predictions from a model or measurements from a solver.

Further work requires an open-source EDA run (#1085), layout export/import
demonstration (#1086), a sourced FEM benchmark and an evidence-backed portfolio
packet (#1087). These are not delivered or certified by the catalog. Fresh
public job research and a reviewed job-to-skill matrix are also outstanding.
Any engineering benchmark must obtain its properties, loads, acceptance basis
and independent expected results before reporting an engineering pass.
