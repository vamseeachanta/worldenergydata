# Offline offshore wind input validation

## Summary

The normalized loader rejects ambiguous measurement text and malformed evidence
locators before an observation can enter an offline query or manifest. These
checks validate syntax; source accuracy, access permission and reuse rights
remain NOT_EVALUATED.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-21 | Define measurement syntax and shared evidence URL checks. |

## Measurement contract and worked example

This is a repository input policy, not a claim about native IRENASTAT headers.
Measurements use ASCII decimal or scientific notation with an optional leading
plus. Decimal points and signed exponents are supported. Separators, underscores,
Unicode digits and negative signs are rejected. Blank retains its existing meaning
of unavailable; a supplied zero remains a measured zero. Existing finite float
validation remains in force; the loader does not promise exact decimal storage.

For an authored synthetic row, `capacity_mw=1e2` means one times ten squared,
so the returned capacity is `100 MW`. `generation_gwh=.5` means one half,
so returned generation is `0.5 GWh`. These are independent arithmetic examples,
not source observations or a capacity-to-generation calculation. Replacing the
capacity text with `1_000` fails validation. A negative value such as `-1e-9999`
fails before float conversion could turn it into negative zero.

```python
from pathlib import Path
from worldenergydata.energy_mix.irena import load_export

raw = Path("tests/fixtures/energy_mix/irena_offshore_synthetic.csv").read_bytes()
raw = raw.replace(b"10.5,20.25", b"1e2,.5")
row = load_export(raw)[0]
assert row["capacity_mw"] == 100
assert row["generation_gwh"] == 0.5
```

## Evidence locator contract

Both observation source URLs and real-export terms URLs require HTTPS, a hostname,
no embedded credentials and a valid port when supplied. Whitespace, control
characters and backslashes are rejected before URL parsing can discard them.
A missing hostname such as `https://:443/data` fails; the reserved synthetic
locator `https://example.invalid/data` passes syntax validation without implying
that it resolves or grants rights. No DNS lookup, source retrieval, hostname
registry validation or network-address permission check is performed.

## Discovery and remaining work

Merged pull requests [1162](https://github.com/vamseeachanta/worldenergydata/pull/1162),
[1359](https://github.com/vamseeachanta/worldenergydata/pull/1359) and
[1522](https://github.com/vamseeachanta/worldenergydata/pull/1522) already provide
the normalized loader, manifests, module documentation and offline queries.
This change adds two independent validation slices and their regression tests.

A fresh read of the [robots endpoint](https://www.irena.org/robots.txt) on
2026-10-21 returned HTTP 200. The subsequent request to the
[IRENASTAT page](https://www.irena.org/Data/Downloads/IRENASTAT) returned HTTP 403.
No alternate access route was attempted. The historical refusal in `fetch_irena`
is retained; it records the earlier probe rather than current robots availability.
Native schema, permitted exports, actual observations and current reuse terms
remain outstanding in [issue 1095](https://github.com/vamseeachanta/worldenergydata/issues/1095).
No physical coefficients, acceptance limits or sourced observation values are
introduced by these syntax policies.
