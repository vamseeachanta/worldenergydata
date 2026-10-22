# FDAS royalty assumptions and compatibility

`AssumptionsManager()` now selects `source-note-v2`: dry-tree royalty is
`0.125`, and `subsea15`, `subsea20` and `default` use `0.1875`. Unknown systems
use the `default` row. The Gulf deck revision 2 agrees with these defaults.
The complete former table is available as `legacy-v1`, including the rounded
deep-water fraction `0.188`. Only the default royalty vector changes; the
other shipped cost and discount inputs retain their previous values.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-21 | Correct default fractions and expose an explicit historical version so previous runs can be reproduced. |

## Source basis and limitations

The percentages come from the shipped Gulf deck's original revision-1
`source_ref` (2026): 12.5% shallow water and 18.75% deep water.
The source is `packages/worldenergydata-fdas/src/worldenergydata/fdas/fiscal/decks/us_gom.yml`.
[NIST SP 811 (2008), section 7.10.2](https://www.nist.gov/pml/special-publication-811/nist-guide-si-chapter-7-rules-and-style-conventions-expressing-values#7102)
defines percent as the number `0.01`, giving `12.5 / 100 = 0.125` and
`18.75 / 100 = 0.1875`. The legacy vector is preserved from `core/config.py`
at repository revision `f82ff2f`; it is a compatibility input.

This is a source-note consistency correction. Current legal applicability,
lease terms, water-depth eligibility and effective dates are **NOT_EVALUATED**.
No lease eligibility is inferred from a development-system name. The Gulf
deck retains its historical effective-date metadata without asserting a new
legal effective date. Income tax and other declarative fiscal fields remain
outside this change; broader fiscal qualification remains under #736.

## Migration and precedence

```python
from worldenergydata.fdas import AssumptionsManager
from worldenergydata.fdas.analysis.cashflow import CashflowEngine

current = AssumptionsManager()  # current.version == "source-note-v2"
historical = AssumptionsManager(version="legacy-v1")
engine = CashflowEngine(historical, dev_system="subsea15", fiscal_terms=None)
```

To reproduce a historical run, pin `legacy-v1`, omit the fiscal deck, and
retain the same production, prices, custom overrides and timing inputs.
This version selector preserves the old assumptions table; it does not pin
every algorithm or dependency used by the historical run.

For flat royalty, precedence remains explicit `royalty_rate` argument, then
supplied fiscal deck, then the supplied assumptions table. A corrected Gulf
deck therefore overrides `legacy-v1`; omit it when requesting historical
rounded rates. Sliding-scale decks retain their existing rate-selection path.

Custom DataFrame, dictionary and Excel inputs retain their supplied fractions.
Their manager reports `version == "custom"`; they are not silently migrated.
A version cannot be combined with a custom DataFrame, and unknown version
names raise `ConfigurationError`. `load_configuration` uses the new default
only when no assumptions workbook is present. Record `manager.version` with
run inputs; custom inputs require retention of the actual supplied table.

## Worked example

Run `python examples/fdas_royalty_versions.py` in an environment with the FDAS
package and its dependencies available. This example uses two synthetic
months, each with 1,000 bbl at 100 USD/bbl, variable OPEX of 10 USD/bbl and
zero host capital and drilling. The generator currently emits zero fixed
OPEX and facilities capital; the example supplies no omitted-cost estimate.

Gross revenue is `1000 * 100 = 100000` USD/month and variable OPEX is
`1000 * 10 = 10000` USD/month. The shipped flat-royalty and net-cashflow
contracts in `analysis/cashflow.py` give:

```text
royalty = gross revenue * fraction
monthly net = gross revenue - royalty - variable OPEX
NPV at zero discount = 2 * monthly net
NPV at synthetic annual 12% = monthly net + monthly net / 1.12**(1/12)
```

The present-value equation follows [OpenStax, Principles of Finance (2022),
section 16.2](https://openstax.org/books/principles-finance/pages/16-2-net-present-value-npv-method).
The first row at time zero and annual-to-monthly compounding convention come
from `core/financial.py::calculate_npv`; there are no pre-production rows in
this zero-capital example. All non-royalty numeric inputs above are synthetic.

| System | Version | Monthly royalty, USD | Monthly net, USD | Zero-rate NPV, USD | Annual 12% NPV, USD |
| --- | --- | ---: | ---: | ---: | ---: |
| dry | either | 12500.0 | 77500.0 | 155000.0 | 154271.5 |
| subsea15, subsea20, default | source-note-v2 | 18750.0 | 71250.0 | 142500.0 | 141830.3 |
| subsea15, subsea20, default | legacy-v1 | 18800.0 | 71200.0 | 142400.0 | 141730.7 |

The corrected deep-water royalty is 50.0 USD/month lower, so net cashflow is
50.0 USD/month higher and zero-rate NPV is 100.0 USD higher. Dry-tree results
are unchanged. Expected values and independent arithmetic are recorded in
`tests/unit/fdas/core/test_assumptions_versions.py`; full component parity
between the default and Gulf deck is covered by the fiscal regression suite.
