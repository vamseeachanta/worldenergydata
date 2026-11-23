"""Australia screening-only adapter tests (#721).

AustraliaAdapter is intentionally EXEMPT from the production ``_ALL_ADAPTERS``
volume-conformance suite (it emits no volumes); this suite covers its actual
contract: a valid empty STANDARD_COLUMNS frame, routability, and metadata-driven
``available_fields``.
"""

from worldenergydata.production.unified.adapters.australia_adapter import (
    AustraliaAdapter,
)
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery
from worldenergydata.production.unified.router import RegionRouter


def test_fetch_returns_valid_but_empty_standard_columns_frame():
    adapter = AustraliaAdapter()
    out = adapter.fetch(ProductionQuery(regions=["australia"]))
    assert list(out.columns) == list(STANDARD_COLUMNS)
    assert out.empty  # screening-only: no production feed yet


def test_region_and_routability():
    assert AustraliaAdapter().region == "australia"
    router = RegionRouter()
    assert isinstance(router.get_adapter("australia"), AustraliaAdapter)
    assert isinstance(router.get_adapter("au"), AustraliaAdapter)


def test_available_fields_come_from_committed_metadata_fixture():
    fields = AustraliaAdapter().available_fields()
    assert "Kingfish" in fields
    assert "Barracouta" in fields


def test_date_range_is_empty_without_production():
    assert AustraliaAdapter().date_range() == ("", "")
