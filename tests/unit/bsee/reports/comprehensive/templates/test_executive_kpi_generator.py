"""Tests for executive KPI generator."""

from worldenergydata.bsee.reports.comprehensive.templates.executive_kpi_generator import (
    KPIGenerator,
)


class TestKPIGeneratorInit:
    def test_default_thresholds(self):
        gen = KPIGenerator()
        t = gen.kpi_thresholds
        assert "uptime" in t
        assert "efficiency" in t
        assert "safety_trir" in t
        assert "emissions_intensity" in t
        assert "roi" in t
        assert "npv" in t
        assert t["uptime"]["green"] == 95
        assert t["uptime"]["yellow"] == 90

    def test_custom_thresholds(self):
        custom = {"uptime": {"green": 99, "yellow": 95}}
        gen = KPIGenerator(kpi_thresholds=custom)
        assert gen.kpi_thresholds["uptime"]["green"] == 99


class TestDetermineKpiStatus:
    def test_green(self):
        gen = KPIGenerator()
        assert gen.determine_kpi_status(100, 95) == "green"

    def test_yellow(self):
        gen = KPIGenerator()
        # 95 * 0.95 = 90.25; 91 >= 90.25 but < 95
        assert gen.determine_kpi_status(91, 95) == "yellow"

    def test_red(self):
        gen = KPIGenerator()
        # 95 * 0.95 = 90.25; 80 < 90.25
        assert gen.determine_kpi_status(80, 95) == "red"

    def test_exact_target(self):
        gen = KPIGenerator()
        assert gen.determine_kpi_status(95, 95) == "green"


class TestDetermineFinancialStatus:
    def test_green(self):
        gen = KPIGenerator()
        assert gen.determine_financial_status(1000, 900) == "green"

    def test_yellow(self):
        gen = KPIGenerator()
        # 1000 * 0.9 = 900; 910 >= 900 but < 1000
        assert gen.determine_financial_status(910, 1000) == "yellow"

    def test_red(self):
        gen = KPIGenerator()
        # 1000 * 0.9 = 900; 800 < 900
        assert gen.determine_financial_status(800, 1000) == "red"

    def test_no_target(self):
        gen = KPIGenerator()
        assert gen.determine_financial_status(1000, None) == "gray"

    def test_zero_target(self):
        gen = KPIGenerator()
        assert gen.determine_financial_status(1000, 0) == "gray"


class TestDetermineProductionStatus:
    def test_green(self):
        gen = KPIGenerator()
        assert gen.determine_production_status(100, 90) == "green"

    def test_yellow(self):
        gen = KPIGenerator()
        # 100 * 0.95 = 95; 96 >= 95 but < 100
        assert gen.determine_production_status(96, 100) == "yellow"

    def test_red(self):
        gen = KPIGenerator()
        assert gen.determine_production_status(80, 100) == "red"

    def test_no_target(self):
        gen = KPIGenerator()
        assert gen.determine_production_status(100, None) == "gray"


class TestDetermineSafetyStatus:
    def test_green(self):
        gen = KPIGenerator()
        assert gen.determine_safety_status(0.3) == "green"

    def test_yellow(self):
        gen = KPIGenerator()
        assert gen.determine_safety_status(0.7) == "yellow"

    def test_red(self):
        gen = KPIGenerator()
        assert gen.determine_safety_status(1.5) == "red"

    def test_boundary_green(self):
        gen = KPIGenerator()
        assert gen.determine_safety_status(0.5) == "green"

    def test_boundary_yellow(self):
        gen = KPIGenerator()
        assert gen.determine_safety_status(1.0) == "yellow"


class TestDetermineEmissionsStatus:
    def test_green(self):
        gen = KPIGenerator()
        # green threshold = 15 * 1000 = 15000
        assert gen.determine_emissions_status(10000) == "green"

    def test_yellow(self):
        gen = KPIGenerator()
        # yellow threshold = 20 * 1000 = 20000
        assert gen.determine_emissions_status(18000) == "yellow"

    def test_red(self):
        gen = KPIGenerator()
        assert gen.determine_emissions_status(25000) == "red"

    def test_boundary_green(self):
        gen = KPIGenerator()
        assert gen.determine_emissions_status(15000) == "green"

    def test_boundary_yellow(self):
        gen = KPIGenerator()
        assert gen.determine_emissions_status(20000) == "yellow"


class TestDetermineTrafficLightStatus:
    def test_green(self):
        gen = KPIGenerator()
        assert gen.determine_traffic_light_status(100, 90, 80) == "green"

    def test_yellow(self):
        gen = KPIGenerator()
        assert gen.determine_traffic_light_status(85, 90, 80) == "yellow"

    def test_red(self):
        gen = KPIGenerator()
        assert gen.determine_traffic_light_status(70, 90, 80) == "red"


class TestGenerateFinancialKpis:
    def test_revenue(self):
        gen = KPIGenerator()
        kpis = gen._generate_financial_kpis(
            {"revenue": 1000000, "revenue_target": 900000},
            lambda h: "stable",
        )
        assert len(kpis) == 1
        assert kpis[0].name == "Revenue"
        assert kpis[0].value == 1000000
        assert kpis[0].status == "green"

    def test_ebitda(self):
        gen = KPIGenerator()
        kpis = gen._generate_financial_kpis(
            {"ebitda": 500000},
            lambda h: "up",
        )
        assert len(kpis) == 1
        assert kpis[0].name == "EBITDA"

    def test_roi(self):
        gen = KPIGenerator()
        kpis = gen._generate_financial_kpis(
            {"roi": 25},
            lambda h: "up",
        )
        assert len(kpis) == 1
        assert kpis[0].name == "ROI"
        assert kpis[0].status == "green"  # 25 >= 20

    def test_empty(self):
        gen = KPIGenerator()
        kpis = gen._generate_financial_kpis({}, lambda h: "stable")
        assert kpis == []


class TestGenerateOperationalKpis:
    def test_uptime(self):
        gen = KPIGenerator()
        kpis = gen._generate_operational_kpis(
            {"uptime_percentage": 97},
            lambda h: "stable",
        )
        assert len(kpis) == 1
        assert kpis[0].name == "Uptime"
        assert kpis[0].status == "green"

    def test_efficiency(self):
        gen = KPIGenerator()
        kpis = gen._generate_operational_kpis(
            {"efficiency_rate": 82},
            lambda h: "down",
        )
        assert len(kpis) == 1
        assert kpis[0].name == "Efficiency"

    def test_empty(self):
        gen = KPIGenerator()
        kpis = gen._generate_operational_kpis({}, lambda h: "stable")
        assert kpis == []


class TestGenerateProductionKpis:
    def test_total_boe(self):
        gen = KPIGenerator()
        kpis = gen._generate_production_kpis(
            {"total_boe": 50000, "production_target": 45000},
            lambda h: "up",
        )
        assert len(kpis) == 1
        assert kpis[0].name == "Production Volume"
        assert kpis[0].status == "green"

    def test_empty(self):
        gen = KPIGenerator()
        kpis = gen._generate_production_kpis({}, lambda h: "stable")
        assert kpis == []


class TestGenerateSafetyKpis:
    def test_trir(self):
        gen = KPIGenerator()
        kpis = gen._generate_safety_kpis(
            {"trir": 0.3},
            lambda h: "down",
        )
        assert len(kpis) == 1
        assert kpis[0].name == "Safety Score"
        # value = 100 - (0.3 * 20) = 94
        assert kpis[0].value == 94.0
        assert kpis[0].status == "green"

    def test_empty(self):
        gen = KPIGenerator()
        kpis = gen._generate_safety_kpis({}, lambda h: "stable")
        assert kpis == []


class TestGenerateEnvironmentalKpis:
    def test_emissions(self):
        gen = KPIGenerator()
        kpis = gen._generate_environmental_kpis(
            {"emissions_tons_co2": 10000},
            lambda h: "down",
        )
        assert len(kpis) == 1
        assert kpis[0].name == "Emissions"
        assert kpis[0].status == "green"

    def test_empty(self):
        gen = KPIGenerator()
        kpis = gen._generate_environmental_kpis({}, lambda h: "stable")
        assert kpis == []


class TestGenerateExecutiveKpis:
    def test_all_categories(self):
        gen = KPIGenerator()
        data = {
            "financial": {"revenue": 1000000, "revenue_target": 900000},
            "operational": {"uptime_percentage": 97},
            "production": {"total_boe": 50000},
            "safety": {"trir": 0.3},
            "environmental": {"emissions_tons_co2": 10000},
        }
        kpis = gen.generate_executive_kpis(data)
        assert len(kpis) == 5
        categories = {k.category for k in kpis}
        assert categories == {"Financial", "Operational", "Production", "Safety", "Environmental"}

    def test_empty_data(self):
        gen = KPIGenerator()
        kpis = gen.generate_executive_kpis({})
        assert kpis == []

    def test_partial_data(self):
        gen = KPIGenerator()
        data = {"financial": {"revenue": 500000}}
        kpis = gen.generate_executive_kpis(data)
        assert len(kpis) == 1
        assert kpis[0].category == "Financial"

    def test_custom_trend_calculator(self):
        gen = KPIGenerator()
        data = {"financial": {"revenue": 500000, "revenue_history": [400, 450, 500]}}
        kpis = gen.generate_executive_kpis(data, trend_calculator=lambda h: "up")
        assert kpis[0].trend == "up"

    def test_default_trend_is_stable(self):
        gen = KPIGenerator()
        data = {"financial": {"revenue": 500000}}
        kpis = gen.generate_executive_kpis(data)
        assert kpis[0].trend == "stable"
