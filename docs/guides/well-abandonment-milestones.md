# Observed well abandonment milestones

The well timeline displays supplied abandonment observations in its Abandon
card. These observations establish labels and dates, not authoritative final
well status or a complete event history.

## History contract

`build_wells_facts.py` reads semicolon-delimited display entries such as
`Temporary abandonment 2020-02-03; Plug & abandon 2022-10-23`. These synthetic
examples preserve the existing normalized labels, including the ampersand.
Entries must contain a whole label followed by a date in `YYYY-MM-DD` form.
Unsupported entries are omitted rather than parsed from a partial label tail;
calendar validity and source completeness are not checked by this parser.

The legacy `workovers` facts key continues to hold all parsed observations.
`build_well_timelines.py` separates only the exact labels `Temporary
abandonment` and `Plug & abandon` into the Abandon card. Other labels, including
unknown operations and labels merely containing abandonment words, remain in
the Workover card and its event count. Matching is case sensitive.

## Display and interpretation

The Abandon card lists each supplied observation's full date and exact label,
and states that final well status is not established. Without observations it
says: "No abandonment milestone in the supplied history." Absence does not
prove that abandonment has never occurred.

All observations retain their existing calendar marker positions and input
order. Calendar markers use month midpoints, while the card retains day-level
dates. Construction remains on its independent native rig-day scale. Inputs
are preserved during rendering.

## Limits and rollout

This change does not infer final status, abandonment duration or cost, change
the global producing phase or production band, correct the existing observation
time, acquire WAR data, or regenerate committed public pages. Those require
separate work with retained sources. Existing WAR label provenance limits also
apply; display labels are not an authoritative activity-code definition.

Synthetic parser-to-card regressions are in
`tests/unit/lower_tertiary/test_well_abandonment_cards.py`. They require no
workbook, binary archive or solver. The parent issue remains open until the
broader source and publication requirements are addressed.
