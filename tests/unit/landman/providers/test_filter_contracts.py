"""Every public provider search parameter must affect the query or be rejected.

Oracles: issue #1259's apply-or-raise contract, provider signatures and enum
definitions in this repository. Query field spellings are existing provider
contracts, not qualified live schemas. Each case supplies just one declared
parameter in addition to required arguments, so another filter cannot mask it.
The explicit query dictionaries below are independently hand-written from
these inputs. No numerical coefficients or acceptance tolerances are used.
"""

import inspect
from datetime import date
from unittest.mock import Mock

import pytest

from worldenergydata.landman import providers
from worldenergydata.landman.exceptions import ProviderError
from worldenergydata.landman.models import FluidMineralType, MineralClaimType
from worldenergydata.landman.providers import (
    BaseProvider,
    BLMProvider,
    CountyReferenceProvider,
    StateGISProvider,
)

# Explicit synthetic inputs. Dates reproduce issue #1259 (2026 issue revision).
# The nondefault limit is an input, copied unchanged to the request, not a limit
# inferred from a production service. PLSS values here are sentinel text.
VALUES = {
    "state": "NM",
    "county": "Synthetic County",
    "operator": "Synthetic Operator",
    "operator_name": "Synthetic Operator",
    "section": "section-sentinel",
    "township": "township-sentinel",
    "range_": "range-sentinel",
    "meridian": "meridian-sentinel",
    "claim_type": MineralClaimType.PLACER,
    "lease_type": FluidMineralType.GEOTHERMAL,
    "status": "status-sentinel",
    "claimant": "Synthetic Claimant",
    "lessee": "Synthetic Lessee",
    "limit": 17,
    "start_date": date.fromisoformat("2025-01-01"),
    "end_date": date.fromisoformat("2025-12-31"),
    "online_only": True,
}

CONTRACTS = {
    (StateGISProvider, "search_wells_by_location"): {
        "state": None,  # State selects a URL; checked separately below.
        "county": "UPPER(COUNTY) = 'SYNTHETIC COUNTY'",
        "section": "SECTION = 'section-sentinel'",
        "township": "TOWNSHIP = 'township-sentinel'",
        "range_": "RANGE = 'range-sentinel'",
        "limit": ("resultRecordCount", 17),
    },
    (StateGISProvider, "search_by_operator"): {
        "state": None,
        "operator_name": "UPPER(OPERATOR) LIKE '%SYNTHETIC OPERATOR%'",
        "limit": ("resultRecordCount", 17),
    },
    (StateGISProvider, "search_permits"): {
        "state": None,
        "county": "UPPER(COUNTY) = 'SYNTHETIC COUNTY'",
        "operator": "UPPER(OPERATOR) LIKE '%SYNTHETIC OPERATOR%'",
        "start_date": "ISSUED_AT >= TIMESTAMP '2025-01-01'",
        # Hand calendar arithmetic: the day after Dec 31 is Jan 1 next year.
        "end_date": "ISSUED_AT < TIMESTAMP '2026-01-01'",
        "limit": ("resultRecordCount", 17),
    },
    (BLMProvider, "search_mining_claims"): {
        "state": ("state", "NM"),
        "county": ("county", "SYNTHETIC COUNTY"),
        "township": ("twp", "township-sentinel"),
        "range_": ("rng", "range-sentinel"),
        "section": ("sec", "section-sentinel"),
        "meridian": ("mer", "meridian-sentinel"),
        "claim_type": ("type", "placer"),
        "status": ("status", "status-sentinel"),
        "claimant": ("claimant", "SYNTHETIC CLAIMANT"),
        "limit": ("limit", 17),
    },
    (BLMProvider, "search_fluid_minerals"): {
        "state": ("state", "NM"),
        "county": ("county", "SYNTHETIC COUNTY"),
        "township": ("twp", "township-sentinel"),
        "range_": ("rng", "range-sentinel"),
        "section": ("sec", "section-sentinel"),
        "meridian": ("mer", "meridian-sentinel"),
        "lease_type": ("type", "geothermal"),
        "lessee": ("lessee", "SYNTHETIC LESSEE"),
        "status": ("status", "status-sentinel"),
        "limit": ("limit", 17),
    },
    (CountyReferenceProvider, "search_counties"): {"state": None, "online_only": None},
}


def public_searches():
    """Discover new providers and methods rather than silently omitting them."""
    for _, cls in inspect.getmembers(providers, inspect.isclass):
        if cls is BaseProvider or not issubclass(cls, BaseProvider):
            continue
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if name.startswith("search_"):
                yield cls, name, method


SEARCHES = list(public_searches())
CASES = [
    pytest.param(cls, name, parameter, id=f"{cls.__name__}.{name}.{parameter}")
    for cls, name, method in SEARCHES
    for parameter in inspect.signature(method).parameters
    if parameter != "self"
]


@pytest.mark.parametrize(("cls", "method", "parameter"), CASES)
@pytest.mark.parametrize("configured_dates", [False, True])
def test_each_declared_filter_is_applied_or_rejected(
    monkeypatch, cls, method, parameter, configured_dates
):
    """All remote searches are intercepted at the service boundary, never helpers.

    Local county lookup oracle: from the synthetic four-entry table, NM selects
    NM's two counties; online_only selects the two enabled counties. These exact
    sets are calculated by hand below, not by the method under test.
    """
    assert (cls, method) in CONTRACTS, "Add an independent oracle for this search"
    assert parameter in CONTRACTS[cls, method], "Add an oracle for this parameter"
    options = {}
    if cls is StateGISProvider and configured_dates:
        options["permit_date_fields"] = {"NM": "ISSUED_AT"}
    with cls(**options) as provider:
        get_json = Mock(return_value={"features": [], "results": []})
        monkeypatch.setattr(provider, "_get_json", get_json)
        if cls is CountyReferenceProvider:
            monkeypatch.setattr(
                provider,
                "COUNTY_DATA",
                {
                    "NM": {"ALPHA": {"online_search_available": True}, "BETA": {}},
                    "TX": {"GAMMA": {"online_search_available": True}, "DELTA": {}},
                },
            )
        kwargs = {
            key: VALUES[key]
            for key, arg in inspect.signature(
                getattr(provider, method)
            ).parameters.items()
            if arg.default is inspect.Parameter.empty
        }
        kwargs[parameter] = VALUES[parameter]

        if (
            cls is StateGISProvider
            and parameter in {"start_date", "end_date"}
            and not configured_dates
        ):
            with pytest.raises(ProviderError) as caught:
                getattr(provider, method)(**kwargs)
            assert caught.value.error_code == "PERMIT_DATE_FILTER_UNSUPPORTED"
            get_json.assert_not_called()
            return

        result = getattr(provider, method)(**kwargs)
        if cls is CountyReferenceProvider:
            expected = (
                {("NM", "ALPHA"), ("NM", "BETA")}
                if parameter == "state"
                else {("NM", "ALPHA"), ("TX", "GAMMA")}
            )
            assert {(row.state, row.county) for row in result} == expected
            get_json.assert_not_called()
            return

        get_json.assert_called_once()
        url = get_json.call_args.args[0]
        params = get_json.call_args.kwargs["params"]
        if cls is StateGISProvider:
            # Source: SUPPORTED_STATES declares NM's wells and permits services.
            service = "Permits" if method == "search_permits" else "Wells"
            assert (
                url
                == f"https://gis.emnrd.nm.gov/arcgis/rest/services/{service}/MapServer/0/query"
            )
        expected = CONTRACTS[cls, method][parameter]
        if isinstance(expected, tuple):
            key, value = expected
            assert params[key] == value
        elif expected is not None:
            assert expected in params["where"].split(" AND ")


@pytest.mark.parametrize("state", StateGISProvider.SUPPORTED_STATES)
@pytest.mark.parametrize(
    ("method", "filters"),
    [
        (
            "search_wells_by_location",
            {"county": "Synthetic", "section": "section-sentinel"},
        ),
        ("search_by_operator", {"operator_name": "Synthetic"}),
        ("search_permits", {"county": "Synthetic", "operator": "Synthetic"}),
    ],
)
def test_every_state_service_applies_filters_or_raises(
    monkeypatch, state, method, filters
):
    """Custom/sonris paths must not silently answer with an empty record set."""
    with StateGISProvider() as provider:
        get_json = Mock(return_value={"features": []})
        monkeypatch.setattr(provider, "_get_json", get_json)
        if state in {"TX", "NM"}:  # ESRI states in the repository configuration.
            getattr(provider, method)(state=state, **filters)
            get_json.assert_called_once()
            assert "SYNTHETIC" in get_json.call_args.kwargs["params"]["where"]
        else:
            with pytest.raises(ProviderError) as caught:
                getattr(provider, method)(state=state, **filters)
            assert caught.value.error_code == "SEARCH_UNSUPPORTED"
            assert caught.value.details == {
                "module": "landman",
                "provider": "state_gis",
                "state": state,
                "method": method,
            }
            get_json.assert_not_called()
