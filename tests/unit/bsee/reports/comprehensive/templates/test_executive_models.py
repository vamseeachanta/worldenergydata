"""Tests for BSEE executive reporting models."""

from datetime import datetime
from decimal import Decimal

from worldenergydata.bsee.reports.comprehensive.templates.executive_models import (
    BusinessHighlight,
    ExecutiveChart,
    ExecutiveDashboard,
    ExecutiveKPI,
    ExecutiveSummary,
    KPIStatus,
    PerformanceScore,
    RiskIndicator,
    StrategicInitiative,
    StrategicMetric,
    TrafficLightIndicator,
    TrendDirection,
)


class TestKPIStatus:
    def test_members(self):
        assert KPIStatus.GREEN.value == "green"
        assert KPIStatus.YELLOW.value == "yellow"
        assert KPIStatus.RED.value == "red"
        assert KPIStatus.GRAY.value == "gray"


class TestTrendDirection:
    def test_members(self):
        assert TrendDirection.UP.value == "up"
        assert TrendDirection.DOWN.value == "down"
        assert TrendDirection.STABLE.value == "stable"


class TestExecutiveKPI:
    def test_basic(self):
        kpi = ExecutiveKPI(name="Production", value=1000, unit="bbl/d")
        assert kpi.name == "Production"
        assert kpi.value == 1000
        assert kpi.status == "gray"

    def test_performance_percentage(self):
        kpi = ExecutiveKPI(name="P", value=90, unit="%", target=100)
        assert kpi.get_performance_percentage() == 90.0

    def test_performance_no_target(self):
        kpi = ExecutiveKPI(name="P", value=90, unit="%")
        assert kpi.get_performance_percentage() == 0.0

    def test_performance_zero_target(self):
        kpi = ExecutiveKPI(name="P", value=90, unit="%", target=0)
        assert kpi.get_performance_percentage() == 0.0

    def test_is_meeting_target_true(self):
        kpi = ExecutiveKPI(name="P", value=100, unit="%", target=90)
        assert kpi.is_meeting_target() is True

    def test_is_meeting_target_false(self):
        kpi = ExecutiveKPI(name="P", value=80, unit="%", target=90)
        assert kpi.is_meeting_target() is False

    def test_is_meeting_no_target(self):
        kpi = ExecutiveKPI(name="P", value=80, unit="%")
        assert kpi.is_meeting_target() is False

    def test_to_dict(self):
        kpi = ExecutiveKPI(name="Uptime", value=95.0, unit="%", target=90.0)
        d = kpi.to_dict()
        assert d["name"] == "Uptime"
        assert d["value"] == 95.0
        assert d["target"] == 90.0
        assert "performance" in d

    def test_decimal_value(self):
        kpi = ExecutiveKPI(
            name="P",
            value=Decimal("95.5"),
            unit="%",
            target=Decimal("90"),
        )
        d = kpi.to_dict()
        assert d["value"] == 95.5
        assert d["target"] == 90.0


class TestStrategicMetric:
    def test_basic(self):
        m = StrategicMetric(name="Production", current_value=1000)
        assert m.name == "Production"
        assert m.current_value == 1000

    def test_get_change(self):
        m = StrategicMetric(name="P", current_value=110, previous_value=100)
        assert m.get_change() == 10.0

    def test_get_change_no_previous(self):
        m = StrategicMetric(name="P", current_value=110)
        assert m.get_change() == 0.0

    def test_get_change_percentage(self):
        m = StrategicMetric(name="P", current_value=110, previous_value=100)
        assert m.get_change_percentage() == 10.0

    def test_get_change_percentage_zero_previous(self):
        m = StrategicMetric(name="P", current_value=110, previous_value=0)
        assert m.get_change_percentage() == 0.0

    def test_is_meeting_target(self):
        m = StrategicMetric(name="P", current_value=100, target_value=90)
        assert m.is_meeting_target() is True

    def test_is_meeting_target_below(self):
        m = StrategicMetric(name="P", current_value=80, target_value=90)
        assert m.is_meeting_target() is False

    def test_get_target_gap(self):
        m = StrategicMetric(name="P", current_value=85, target_value=90)
        assert m.get_target_gap() == -5.0

    def test_get_target_gap_no_target(self):
        m = StrategicMetric(name="P", current_value=85)
        assert m.get_target_gap() == 0.0


class TestPerformanceScore:
    def test_excellent(self):
        s = PerformanceScore(overall=95, category_scores={"prod": 95}, period="Q1")
        assert s.get_rating() == "Excellent"

    def test_good(self):
        s = PerformanceScore(overall=85, category_scores={}, period="Q1")
        assert s.get_rating() == "Good"

    def test_satisfactory(self):
        s = PerformanceScore(overall=75, category_scores={}, period="Q1")
        assert s.get_rating() == "Satisfactory"

    def test_needs_improvement(self):
        s = PerformanceScore(overall=65, category_scores={}, period="Q1")
        assert s.get_rating() == "Needs Improvement"

    def test_critical(self):
        s = PerformanceScore(overall=50, category_scores={}, period="Q1")
        assert s.get_rating() == "Critical"


class TestTrafficLightIndicator:
    def test_green_color(self):
        t = TrafficLightIndicator(
            metric_name="T",
            value=100,
            status="green",
            threshold_green=90,
            threshold_yellow=70,
        )
        assert t.get_color_code() == "#28a745"

    def test_yellow_color(self):
        t = TrafficLightIndicator(
            metric_name="T",
            value=80,
            status="yellow",
            threshold_green=90,
            threshold_yellow=70,
        )
        assert t.get_color_code() == "#ffc107"

    def test_red_color(self):
        t = TrafficLightIndicator(
            metric_name="T",
            value=50,
            status="red",
            threshold_green=90,
            threshold_yellow=70,
        )
        assert t.get_color_code() == "#dc3545"

    def test_unknown_status(self):
        t = TrafficLightIndicator(
            metric_name="T",
            value=0,
            status="unknown",
            threshold_green=90,
            threshold_yellow=70,
        )
        assert t.get_color_code() == "#6c757d"


class TestDataclasses:
    def test_executive_summary(self):
        s = ExecutiveSummary(
            key_messages=["msg1"],
            highlights=[{"title": "h1"}],
            lowlights=[],
            recommendations=["r1"],
            outlook="positive",
        )
        assert s.outlook == "positive"
        assert len(s.key_messages) == 1

    def test_business_highlight(self):
        h = BusinessHighlight(
            title="Record",
            description="Record production",
            impact="Revenue up",
            metric="oil_bbl",
            value=10000,
        )
        assert h.title == "Record"

    def test_risk_indicator(self):
        r = RiskIndicator(
            category="Weather",
            risk_level="high",
            description="Hurricane season",
            mitigation="Evac plan",
        )
        assert r.risk_level == "high"

    def test_strategic_initiative(self):
        s = StrategicInitiative(
            name="Digitalization",
            status="in-progress",
            progress=45.0,
            target_date=datetime(2025, 12, 31),
            owner="CTO",
            impact="high",
        )
        assert s.progress == 45.0

    def test_executive_chart(self):
        c = ExecutiveChart(
            type="bar",
            data={"x": [1]},
            layout={},
            config={},
        )
        assert c.type == "bar"

    def test_executive_dashboard(self):
        d = ExecutiveDashboard(
            layout={"cols": 2},
            charts=[],
            components={},
            export_config={},
        )
        assert d.layout["cols"] == 2
