# worldenergydata-brazil_anp

`brazil_anp` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.brazil_anp` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Production source discovery

`production.source_discovery` discovers published ZIP and CSV links from the
official ANP indexes without assuming a production REST API or uniform file
names. See the [access assessment](../../docs/reports/anp-production-access.md)
for source observations, sample downloads, API status and ingestion limits.

## Illustrative concession royalty scale

`analysis.field_economics.ROYALTY_SCALE` is **illustrative**.
`ROYALTY_SCALE_IS_ILLUSTRATIVE = True` records that the five bands are not
source-qualified fiscal terms. Their values and calculated outputs are retained
for compatibility; no legal production-rate table matching these bands has been
established.

`calculate_royalties_concession` selects the first inclusive threshold and
multiplies gross revenue by its rate. Thresholds use externally supplied barrels
per day. `ConcessionRegime` describes a field context, but the interface does not
establish field aggregation, an averaging basis, a production year, or a location
class. The revenue period and currency are also supplied without qualification.

The first disagreement is the selection rule: daily production selects a rate
in this example, whereas Decreto 2.705/1998, art. 12, §§1–2 specifies a concession
percentage established in the bidding terms and contract. A percentage within
the statutory range alone does not establish a matching production band.

| Code upper threshold (barrels/day) | Code rate (%) | Official comparison | Disposition |
| --- | --- | --- | --- |
| 5,000 | 5 | 5% is the art. 12 §1 minimum; no 5,000 barrels/day threshold is specified | Differ |
| 15,000 | 7.5 | Contract percentage under art. 12 §2; no 15,000 barrels/day threshold is specified | Unconfirmed band |
| 30,000 | 10 | 10% is the art. 12 default; no 30,000 barrels/day threshold is specified | Unconfirmed band |
| 50,000 | 12.5 | Above the art. 12 default of 10%; no 50,000 barrels/day threshold is specified | Differ |
| Unbounded | 15 | Above the art. 12 default of 10%; no corresponding royalty band is specified | Differ |

Table 1. Every band is compared with the cited concession framework; a contract-specific rate is not established for this example.

Sources examined on 2026-10-12:

- Presidency of the Republic, [Lei 9.478, de 6 de agosto de 1997](https://www.planalto.gov.br/ccivil_03/leis/l9478.htm), art. 47, caput and §1: monthly royalties per field, with a 10% default and provision for reduction to a 5% minimum.
- Presidency of the Republic, [Decreto 2.705, de 3 de agosto de 1998](https://www.planalto.gov.br/ccivil_03/decreto/d2705.htm), arts. 11–12, §§1–2: monthly field production valued at reference prices and the contractual concession percentage. Art. 22, caput and §1/I, concerns special participation, with quarterly field production in thousands of cubic metres of oil equivalent, net revenue, production year and location class. That table does not qualify a daily-rate royalty scale.
- ANP, [Royalties](https://www.gov.br/anp/pt-br/assuntos/royalties-e-outras-participacoes/royalties), opening calculation factors and variable definitions: contractual field percentage multiplied by monthly field production and reference prices; oil and gas volumes are in cubic metres. The page's general 5–15% range does not provide the five production-rate bands or establish their concession case.
- ANP, [Participação especial](https://www.gov.br/anp/pt-br/assuntos/royalties-e-outras-participacoes/participacao-especial), opening calculation paragraphs: progressive rates on quarterly net revenue depend on field location, years of production and quarterly production volume.

The shipped `fdas/fiscal/decks/` resources (`norway.yml`, `uk.yml`, `us_gom.yml`)
and production builders `fdas.fiscal.schema` and `fdas.fiscal.terms` exclude this
scale. The synthetic runtime parity test in
`tests/unit/fdas/fiscal/test_deck_parity.py` checks agreement with existing code;
it does not establish regulatory qualification and does not ship a country deck.
These illustrative values shall not be copied into a fiscal deck until the
applicable contract, units, period and governing case are source-qualified.
