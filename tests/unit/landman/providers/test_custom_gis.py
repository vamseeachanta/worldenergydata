"""Unimplemented custom services must explicitly reject searches (#1256).

The oracle is the unimplemented adapter and the filter contract in #1689:
no request is made, so absence of matching records cannot be established.
"""

from unittest.mock import Mock

import pytest

from worldenergydata.landman.exceptions import ProviderError
from worldenergydata.landman.providers.state_gis import StateGISProvider


@pytest.mark.parametrize(
    "state",
    [
        state
        for state, config in StateGISProvider.SUPPORTED_STATES.items()
        if config["api_format"] != "esri_rest"
    ],
)
@pytest.mark.parametrize("method", ["location", "operator", "permits", "detail"])
def test_custom_service_is_explicitly_unimplemented(monkeypatch, state, method):
    """An unsupported service is unavailable, including for detail lookups."""
    with StateGISProvider() as provider:
        request = Mock()
        monkeypatch.setattr(provider, "_get_json", request)
        calls = {
            "location": lambda: provider.search_wells_by_location(
                state.lower(), "Synthetic"
            ),
            "operator": lambda: provider.search_by_operator("Synthetic", state.lower()),
            "permits": lambda: provider.search_permits(state.lower()),
            "detail": lambda: provider.get_well_detail("synthetic-api", state.lower()),
        }
        with pytest.raises(ProviderError, match="not implemented") as caught:
            calls[method]()
        assert caught.value.error_code == "SEARCH_UNSUPPORTED"
        assert caught.value.details["state"] == state
        assert caught.value.details["provider"] == "state_gis"
        request.assert_not_called()
