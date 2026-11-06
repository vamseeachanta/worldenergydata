# Deepwater GoM — Field Development Plan Portfolio

Standalone field development pages and an `index.html` comparison table cover
the ten Lower Tertiary lifecycle fields, alongside the original deepwater examples.
The portfolio now contains 17 profiles: the original 10 and the seven additions
listed in issue #962. Open `index.html` to select a field.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial documented expansion | 2026-10-19 | Added the remaining Lower Tertiary concept pages, input citations and explicit evidence gaps so every registry field has a portfolio reference. |
| Evidence and portability correction | 2026-10-20 | Kept conflicting depths unknown, distinguished design capacity and source timing, limited coverage to the lifecycle roster, and clarified portable generation and legacy drift. |

The initial revision's registry-wide coverage claim is superseded: coverage is
limited to the ten lifecycle fields, rather than every registry entry.

## Coverage and evidence

The additions are Big Foot, Anchor, Jack/St. Malo, Kaskida, North Platte
(subsequently developed as Sparta), Shenandoah and Tiber. The original profiles
and their generated pages remain available.

`_research.json` is the authoring input. Each new profile includes a summary,
engineering rationale, architecture description, limitations, and `evidence`
records with publication date, retrieval time, HTTP status and source digest.
`input_sources` supplies a source reference and a scope comment for each known
input. Digests identify the opened public response, not a claim that the
publisher's page will remain unchanged. Public responses are retained outside
this repository; their full content is not redistributed here.

New pages retain the parameter, rationale, architecture, shortlist and economics
outline of the existing FDP template. They report the documented selection;
ranking, detailed layout, economics and equipment qualification remain
`NOT_EVALUATED` until their required inputs and criteria are sourced. No
well-count default, assumed host offset or heuristic cost is presented as a
field fact. The original profiles retain the legacy illustrative model output.

## Worked example: North Platte / Sparta

Input: Equinor, [Final Investment Decision for Sparta in the US Gulf of Mexico](https://www.equinor.com/news/20231220-final-investment-decision-sparta),
20 December 2023, development-plan paragraph and “Facts about Sparta” box:

```json
{
  "name": "North Platte",
  "concept_type": "semisub_fps",
  "water_depth_m": null,
  "num_wells": 8,
  "plateau_boed": 100000,
  "recoverable_reserves_mmboe": null,
  "first_oil_year": null
}
```

Method: transcribe the planned subsea production-well count and designed peak
capacity. The source reports approximately 1,310 m, while the lifecycle record
lists 4,265 ft; that unresolved depth remains null. No unit conversion is used
to choose a depth. Both records carry the conflict note.
The `plateau_boed` mapping records designed capacity only; the source does not
establish a measured production plateau. The lifecycle prose's approximately
90,000 boe/d expected peak is a separate claim whose basis is not established
by this announcement; the legacy oil plateau is not a conversion of designed
capacity. The source states resources as a lower
bound and startup as a forecast, so neither becomes an exact resource input or
actual first-oil year.

Answer: a documented semisubmersible host with eight planned subsea production
wells, an unknown reconciled water depth and designed peak capacity of 100,000
boe/d. Detailed layout and investment returns are `NOT_EVALUATED`. The regression
test independently transcribes these same published values.

Tiber illustrates a different scope boundary: the source describes six Tiber
wells plus two Guadalupe wells. Only the six Tiber wells enter its field
concept. Combined-hub oil capacity is recorded separately in bbl/d; combined
resources are not assigned to Tiber alone.

## Reproduce the pages and links

With the package and its dependencies available:

```sh
uv run python scripts/field_development/build_fdp_portfolio.py \
    reports/field_development/portfolio/_research.json --documented-only
```

**Legacy regeneration warning:** omitting `--documented-only` rewrites all ten
original model-based examples. Their committed shortlist, economics and layout
already differ from current renderer output. Removing the unsupported well-count
default also changes two legacy well cards from four wells to unknown. Use
`--documented-only` for the documented pages; review the full output in a separate
directory before deliberately re-issuing legacy examples.
`--output-dir <directory>` directs generated pages and the index to a review
folder. Generation does not fetch sources or update the registry.

`config/fields.yml` owns page availability and slugs. After adding a page and
setting its `surfaces.fdp_page` flag, regenerate the lifecycle posters and
Explorer payload with the existing generator:

```sh
uv run python scripts/lower_tertiary/build_lifecycle_posters.py
```

The published site copies the committed pages and Explorer payload. This change
refreshes only the corresponding FDP links in that payload and the posters;
other frozen performance, lease and architecture evidence is preserved.

## Known limits and way forward

Publications are historical snapshots; operators, plans and capacities are
qualified by their publication dates. Some operator pages could not be opened,
so the new profiles cite accessible publisher reports, with the Sparta partner
announcement as a primary source. Shenandoah and Tiber host classifications also
reference the committed lifecycle research and require a host design-basis
confirmation. Conflicting depths, uncertain well inventories and unsourced
inputs stay null rather than being inferred from nearby fields. The sanction-date
page that retains an unknown actual first-oil year explains the later August 2024
startup shown in the lifecycle Explorer; a startup source is required before that
year can be entered as a documented input.

Reported equipment technology does not establish pressure qualification.
Detailed spatial architecture in the Explorer remains a separate evidence gap:
these pages supply concept descriptions, not surveyed well positions. Obtain
current phase-specific inventories, equipment criteria, production profiles and
cost inputs before quantitative engineering or investment assessment.
