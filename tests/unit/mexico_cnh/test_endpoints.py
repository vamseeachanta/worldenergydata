"""Tests for Mexico CNH endpoints configuration."""

from worldenergydata.mexico_cnh.endpoints import (
    CNHEndpoint,
    CNHEndpoints,
    CNHPortal,
    DEFAULT_RATE_LIMITS,
    DEFAULT_TIMEOUTS,
)


class TestCNHPortal:
    def test_all_portals(self):
        assert len(CNHPortal) == 6

    def test_values(self):
        assert CNHPortal.SIH.value == "sih"
        assert CNHPortal.PRODUCTION.value == "production"
        assert CNHPortal.MAPS.value == "maps"
        assert CNHPortal.OPEN_DATA.value == "open_data"
        assert CNHPortal.RONDAS.value == "rondas"
        assert CNHPortal.CONTRACTS.value == "contracts"


class TestCNHEndpoint:
    def test_defaults(self):
        ep = CNHEndpoint(name="Test", url="https://example.com", portal=CNHPortal.SIH)
        assert ep.requires_javascript is True
        assert ep.requires_auth is False
        assert ep.description == ""

    def test_custom_values(self):
        ep = CNHEndpoint(
            name="Open Data",
            url="https://datos.gob.mx",
            portal=CNHPortal.OPEN_DATA,
            requires_javascript=False,
            description="Open data portal",
        )
        assert ep.requires_javascript is False
        assert ep.description == "Open data portal"


class TestCNHEndpoints:
    def test_base_urls(self):
        assert "gob.mx" in CNHEndpoints.BASE_URL
        assert "hidrocarburos" in CNHEndpoints.SIH_BASE
        assert "rondasmexico" in CNHEndpoints.RONDAS_BASE

    def test_sih_urls_use_base(self):
        assert CNHEndpoints.SIH_DASHBOARD.startswith(CNHEndpoints.SIH_BASE)
        assert CNHEndpoints.SIH_PRODUCTION.startswith(CNHEndpoints.SIH_BASE)
        assert CNHEndpoints.SIH_WELLS.startswith(CNHEndpoints.SIH_BASE)

    def test_production_urls(self):
        assert "mensual" in CNHEndpoints.PRODUCTION_MONTHLY
        assert "anual" in CNHEndpoints.PRODUCTION_ANNUAL
        assert "operador" in CNHEndpoints.PRODUCTION_BY_OPERATOR

    def test_download_urls(self):
        assert "xlsx" in CNHEndpoints.DOWNLOADS_PRODUCTION_XLS
        assert "xlsx" in CNHEndpoints.DOWNLOADS_WELLS_XLS

    def test_api_urls(self):
        assert "/api/v1" in CNHEndpoints.API_BASE
        assert CNHEndpoints.API_PRODUCTION.startswith(CNHEndpoints.API_BASE)

    def test_get_all_endpoints(self):
        eps = CNHEndpoints.get_all_endpoints()
        assert isinstance(eps, dict)
        assert len(eps) > 10
        for name, ep in eps.items():
            assert isinstance(ep, CNHEndpoint)
            assert ep.url

    def test_get_endpoint_found(self):
        ep = CNHEndpoints.get_endpoint("sih_dashboard")
        assert ep is not None
        assert ep.portal == CNHPortal.SIH

    def test_get_endpoint_not_found(self):
        ep = CNHEndpoints.get_endpoint("nonexistent")
        assert ep is None

    def test_get_endpoints_by_portal_sih(self):
        sih_eps = CNHEndpoints.get_endpoints_by_portal(CNHPortal.SIH)
        assert len(sih_eps) > 0
        for name, ep in sih_eps.items():
            assert ep.portal == CNHPortal.SIH

    def test_get_endpoints_by_portal_open_data(self):
        od_eps = CNHEndpoints.get_endpoints_by_portal(CNHPortal.OPEN_DATA)
        assert len(od_eps) > 0
        for ep in od_eps.values():
            assert ep.portal == CNHPortal.OPEN_DATA

    def test_get_javascript_required(self):
        js_eps = CNHEndpoints.get_javascript_required_endpoints()
        assert len(js_eps) > 0
        for ep in js_eps.values():
            assert ep.requires_javascript is True

    def test_get_direct_download(self):
        dl_eps = CNHEndpoints.get_direct_download_endpoints()
        assert len(dl_eps) > 0
        for ep in dl_eps.values():
            assert ep.requires_javascript is False
            assert "download" in ep.name.lower() or "download" in list(dl_eps.keys())[0]


class TestDefaultTimeouts:
    def test_all_portals_have_timeouts(self):
        for portal in CNHPortal:
            assert portal in DEFAULT_TIMEOUTS
            assert DEFAULT_TIMEOUTS[portal] > 0

    def test_maps_has_longest_timeout(self):
        assert DEFAULT_TIMEOUTS[CNHPortal.MAPS] == 90


class TestDefaultRateLimits:
    def test_all_portals_have_rate_limits(self):
        for portal in CNHPortal:
            assert portal in DEFAULT_RATE_LIMITS
            assert DEFAULT_RATE_LIMITS[portal] > 0

    def test_open_data_fastest(self):
        assert DEFAULT_RATE_LIMITS[CNHPortal.OPEN_DATA] == 1.0
