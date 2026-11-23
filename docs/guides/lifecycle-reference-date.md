# Lifecycle poster reference dates

The lifecycle builder accepts an explicit reference date so a historical marker
does not imply a current observation. Reference time is deterministic and never
defaults to the system clock.

## Usage

```sh
python scripts/lower_tertiary/build_lifecycle_posters.py --reference-date 2028-02-29
```

This command writes posters, the gallery index, and the explorer sidecar to the
existing lifecycle output directory. Callers of `facts_to_field` can instead pass
`reference_date="2028-02-29"` as a keyword argument and render into temporary
storage. The marker reads **As of 2028-02-29**. Only valid `YYYY-MM-DD` calendar
dates are accepted; the command validates the date before writing any output.

Positions use year plus elapsed days divided by the number of days in that
calendar year, accounting for leap years. January 1 is the year's origin.
Historical gate dates retain their existing year or mid-month interpretation.

## Legacy fallback and limits

Omitting the argument preserves the fixed numeric reference **2026.5**, labelled
**Reference year 2026.5**. It does not invent an exact calendar day. Both routes
require producing status, a first-oil gate, and a reference strictly inside the
existing axis bounds. Dates on or outside the bounds are omitted, never clamped;
changing reference time does not extend the axis or infer missing gates.

Reference time does not refresh production data, validate source facts, or
reclassify the field's phase. Existing generated pages remain historical
artifacts pending a separately scoped regeneration. Source reconciliation,
dossier page-one integration, PDF portability, other development classes, and
the sibling well-timeline builder's fixed marker remain follow-up work in #738.
