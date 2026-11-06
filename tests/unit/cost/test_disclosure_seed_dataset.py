"""Published figures and independent arithmetic for the report seed."""

from worldenergydata.cost.data_collection.disclosure_seed_dataset import (
    load_seed_disclosure_records,
)
from worldenergydata.fdas.api import DisclosureAnalyticsQuery


def test_seed_has_cited_series_and_flows_through_fdas():
    """Chevron 2023 annual report, Financial Highlights (USD million).

    CAPEX 2022 = 11,974; 2023 = 15,829. Independent subtraction gives
    15,829 - 11,974 = 3,855; relative change = 3,855 / 11,974.
    Coverage of three operators and four consecutive years is the report
    requirement, rather than an engineering acceptance limit.
    """
    records = load_seed_disclosure_records()
    operators = {r.operator for r in records}
    assert operators == {"Chevron", "Shell", "BP"}
    for operator in operators:
        assert sorted(r.fiscal_year for r in records if r.operator == operator) == [
            2020,
            2021,
            2022,
            2023,
        ]
    for record in records:
        for key in (
            "source",
            "publisher",
            "retrieval_date",
            "source_url",
            "page_ref",
            "fiscal_basis",
            "retrieval_note",
            "source_sha256",
        ):
            assert record.provenance[key]
        assert record.provenance["data_tier"] == "seed"
        assert record.currency == "USD"
        assert record.comparability_status is None
    view = DisclosureAnalyticsQuery().operator_capex(records)
    row = next(r for r in view if r.operator == "Chevron" and r.fiscal_year == 2023)
    assert row.reported_capex_usd_mm == 15829
    assert row.yoy_delta_usd_mm == 3855
    assert row.yoy_delta_pct == 3855 / 11974


def test_seed_load_is_independent():
    records = load_seed_disclosure_records()
    records[0].provenance["source"] = "changed"
    records.pop()
    assert load_seed_disclosure_records()[0].provenance["source"] != "changed"
    assert len(load_seed_disclosure_records()) == 12
