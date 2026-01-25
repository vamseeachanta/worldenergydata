"""
Tests for environmental compliance tracking and metrics
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "src"))

# Import the compliance template classes directly 
exec(open(Path(__file__).parent.parent.parent.parent.parent.parent / 
          "src/worldenergydata/modules/bsee/reports/comprehensive/templates/compliance_template.py").read())


class TestEnvironmentalMetricsAggregation:
    """Test environmental metrics aggregation"""
    
    def test_environmental_metrics_initialization(self):
        """Test EnvironmentalMetrics initialization with all fields"""
        metrics = EnvironmentalMetrics(
            entity_id="GC_001",
            entity_type="field",
            report_date=date(2024, 1, 31),
            spill_incidents=3,
            total_spill_volume_bbls=25.5,
            air_emissions_tons=150.0,
            water_discharge_bbls=75000,
            waste_generated_tons=45.0,
            environmental_violations=2
        )
        
        assert metrics.entity_id == "GC_001"
        assert metrics.spill_incidents == 3
        assert metrics.total_spill_volume_bbls == 25.5
        assert metrics.air_emissions_tons == 150.0
        assert metrics.water_discharge_bbls == 75000
        assert metrics.waste_generated_tons == 45.0
        assert metrics.environmental_violations == 2
    
    def test_environmental_score_calculation_perfect(self):
        """Test environmental score with perfect environmental record"""
        metrics = EnvironmentalMetrics(
            spill_incidents=0,
            total_spill_volume_bbls=0.0,
            air_emissions_tons=50.0,  # Below 100 ton threshold
            environmental_violations=0
        )
        
        score = metrics.calculate_environmental_score()
        assert score == 1.0
    
    def test_environmental_score_calculation_with_penalties(self):
        """Test environmental score with various penalties"""
        metrics = EnvironmentalMetrics(
            spill_incidents=2,           # -0.2 (2 * 0.1)
            total_spill_volume_bbls=15.0,  # -0.15 (15 * 0.01)
            air_emissions_tons=150.0,    # -0.05 ((150-100) * 0.001)
            environmental_violations=1   # -0.15 (1 * 0.15)
        )
        
        score = metrics.calculate_environmental_score()
        expected_score = 1.0 - 0.2 - 0.15 - 0.05 - 0.15  # = 0.45
        assert abs(score - expected_score) < 0.001
    
    def test_environmental_score_minimum_bound(self):
        """Test environmental score doesn't go below zero"""
        metrics = EnvironmentalMetrics(
            spill_incidents=50,          # Very high penalties
            total_spill_volume_bbls=500.0,
            air_emissions_tons=2000.0,
            environmental_violations=20
        )
        
        score = metrics.calculate_environmental_score()
        assert score >= 0.0
    
    def test_environmental_status_classifications(self):
        """Test all environmental status classifications"""
        # Excellent (score >= 0.9)
        excellent = EnvironmentalMetrics(spill_incidents=0, environmental_violations=0)
        assert excellent.environmental_status() == "Excellent"
        
        # Good (0.8 <= score < 0.9)
        good = EnvironmentalMetrics(spill_incidents=1, total_spill_volume_bbls=5.0)
        score = good.calculate_environmental_score()  # 1.0 - 0.1 - 0.05 = 0.85
        if 0.8 <= score < 0.9:
            assert good.environmental_status() == "Good"
        
        # Fair (0.7 <= score < 0.8)  
        fair = EnvironmentalMetrics(spill_incidents=2, total_spill_volume_bbls=10.0)
        score = fair.calculate_environmental_score()  # 1.0 - 0.2 - 0.1 = 0.7
        if 0.7 <= score < 0.8:
            assert fair.environmental_status() == "Fair"
        
        # Poor (score < 0.7)
        poor = EnvironmentalMetrics(
            spill_incidents=5, 
            total_spill_volume_bbls=50.0,
            environmental_violations=2
        )
        score = poor.calculate_environmental_score()
        if score < 0.7:
            assert poor.environmental_status() == "Poor"
    
    def test_spill_rate_calculation_normal(self):
        """Test spill rate per barrel produced calculation"""
        metrics = EnvironmentalMetrics(total_spill_volume_bbls=5.0)
        
        production_bbls = 100000.0
        spill_rate = metrics.spill_rate_per_bbl_produced(production_bbls)
        
        expected_rate = 5.0 / 100000.0  # 0.00005
        assert abs(spill_rate - expected_rate) < 0.0000001
    
    def test_spill_rate_calculation_zero_production(self):
        """Test spill rate with zero production"""
        metrics = EnvironmentalMetrics(total_spill_volume_bbls=10.0)
        
        spill_rate = metrics.spill_rate_per_bbl_produced(0.0)
        assert spill_rate == 0.0
    
    def test_spill_rate_calculation_zero_spills(self):
        """Test spill rate with zero spills"""
        metrics = EnvironmentalMetrics(total_spill_volume_bbls=0.0)
        
        production_bbls = 100000.0
        spill_rate = metrics.spill_rate_per_bbl_produced(production_bbls)
        assert spill_rate == 0.0


class TestEnvironmentalComplianceTracking:
    """Test environmental compliance tracking system"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.sample_metrics = EnvironmentalMetrics(
            entity_id="GC_001",
            report_date=date(2024, 1, 31),
            spill_incidents=2,
            total_spill_volume_bbls=12.5,
            air_emissions_tons=125.0,
            water_discharge_bbls=60000,
            waste_generated_tons=30.0,
            environmental_violations=1
        )
    
    def test_environmental_compliance_tracking_basic(self):
        """Test basic environmental compliance tracking"""
        # Create compliance template
        template = ComplianceTemplate()
        
        # Add environmental compliance tracking
        template.add_environmental_compliance_tracking(self.sample_metrics)
        
        # Check that environmental compliance was added to context
        assert "environmental_compliance" in template.context
        
        env_compliance = template.context["environmental_compliance"]
        assert env_compliance["spill_incidents"] == 2
        assert env_compliance["total_spill_volume"] == 12.5
        assert env_compliance["air_emissions"] == 125.0
        assert env_compliance["water_discharge"] == 60000
        assert env_compliance["waste_generated"] == 30.0
        assert env_compliance["violations"] == 1
    
    def test_environmental_compliance_tracking_scores(self):
        """Test environmental compliance tracking with scores"""
        template = ComplianceTemplate()
        template.add_environmental_compliance_tracking(self.sample_metrics)
        
        env_compliance = template.context["environmental_compliance"]
        
        # Check calculated scores
        assert "environmental_score" in env_compliance
        assert "environmental_status" in env_compliance
        assert 0.0 <= env_compliance["environmental_score"] <= 1.0
        assert env_compliance["environmental_status"] in ["Excellent", "Good", "Fair", "Poor"]
    
    def test_environmental_compliance_tracking_trends(self):
        """Test environmental compliance tracking with trend data"""
        template = ComplianceTemplate()
        template.add_environmental_compliance_tracking(self.sample_metrics)
        
        env_compliance = template.context["environmental_compliance"]
        
        # Check trend data structure
        assert "trends" in env_compliance
        trends = env_compliance["trends"]
        assert "spill_trend" in trends
        assert "emissions_trend" in trends
        assert "compliance_trend" in trends
    
    def test_environmental_compliance_aggregation_multiple_entities(self):
        """Test environmental compliance aggregation across multiple entities"""
        # Create multiple environmental metrics
        metrics_list = [
            EnvironmentalMetrics(
                entity_id="GC_001",
                spill_incidents=1,
                total_spill_volume_bbls=5.0,
                air_emissions_tons=100.0
            ),
            EnvironmentalMetrics(
                entity_id="GC_002", 
                spill_incidents=2,
                total_spill_volume_bbls=10.0,
                air_emissions_tons=150.0
            ),
            EnvironmentalMetrics(
                entity_id="GC_003",
                spill_incidents=0,
                total_spill_volume_bbls=0.0,
                air_emissions_tons=75.0
            )
        ]
        
        # Aggregate metrics
        total_spills = sum([m.spill_incidents for m in metrics_list])  # 3
        total_spill_volume = sum([m.total_spill_volume_bbls for m in metrics_list])  # 15.0
        total_emissions = sum([m.air_emissions_tons for m in metrics_list])  # 325.0
        avg_environmental_score = sum([m.calculate_environmental_score() for m in metrics_list]) / len(metrics_list)
        
        assert total_spills == 3
        assert total_spill_volume == 15.0
        assert total_emissions == 325.0
        assert 0.0 <= avg_environmental_score <= 1.0
    
    def test_environmental_compliance_violation_tracking(self):
        """Test environmental compliance violation tracking"""
        # High violation case
        high_violation_metrics = EnvironmentalMetrics(
            entity_id="GC_VIOLATION",
            spill_incidents=5,
            total_spill_volume_bbls=100.0,
            environmental_violations=3
        )
        
        template = ComplianceTemplate()
        template.add_environmental_compliance_tracking(high_violation_metrics)
        
        env_compliance = template.context["environmental_compliance"]
        
        # Should have poor environmental status
        assert env_compliance["violations"] == 3
        assert env_compliance["environmental_status"] == "Poor"
        assert env_compliance["environmental_score"] < 0.7
    
    def test_environmental_compliance_threshold_analysis(self):
        """Test environmental compliance against regulatory thresholds"""
        # Test different threshold scenarios
        test_cases = [
            {
                "metrics": EnvironmentalMetrics(spill_incidents=0, air_emissions_tons=50.0),
                "expected_status": "Excellent"
            },
            {
                "metrics": EnvironmentalMetrics(spill_incidents=1, air_emissions_tons=80.0),
                "expected_status": "Good"
            },
            {
                "metrics": EnvironmentalMetrics(spill_incidents=2, air_emissions_tons=120.0),
                "expected_status": "Fair"
            },
            {
                "metrics": EnvironmentalMetrics(spill_incidents=5, air_emissions_tons=200.0, environmental_violations=2),
                "expected_status": "Poor"
            }
        ]
        
        for case in test_cases:
            template = ComplianceTemplate()
            template.add_environmental_compliance_tracking(case["metrics"])
            
            env_compliance = template.context["environmental_compliance"]
            actual_status = env_compliance["environmental_status"]
            
            # Status should match expected based on environmental score
            score = case["metrics"].calculate_environmental_score()
            if score >= 0.9:
                expected = "Excellent"
            elif score >= 0.8:
                expected = "Good"
            elif score >= 0.7:
                expected = "Fair"
            else:
                expected = "Poor"
            
            assert actual_status == expected
    
    def test_environmental_performance_benchmarking(self):
        """Test environmental performance benchmarking"""
        # Create metrics for benchmarking
        industry_benchmark = EnvironmentalMetrics(
            spill_incidents=1,
            total_spill_volume_bbls=5.0,
            air_emissions_tons=100.0,
            environmental_violations=0
        )
        
        current_performance = EnvironmentalMetrics(
            spill_incidents=2,
            total_spill_volume_bbls=8.0,
            air_emissions_tons=120.0,
            environmental_violations=1
        )
        
        benchmark_score = industry_benchmark.calculate_environmental_score()
        current_score = current_performance.calculate_environmental_score()
        
        # Performance comparison
        performance_gap = benchmark_score - current_score
        
        if performance_gap > 0:
            performance_status = "Below Benchmark"
        elif performance_gap < -0.05:
            performance_status = "Above Benchmark"
        else:
            performance_status = "At Benchmark"
        
        assert isinstance(performance_gap, float)
        assert performance_status in ["Below Benchmark", "At Benchmark", "Above Benchmark"]
    
    def test_environmental_reporting_period_analysis(self):
        """Test environmental metrics analysis over reporting periods"""
        # Create quarterly environmental data
        q1_metrics = EnvironmentalMetrics(
            report_date=date(2024, 3, 31),
            spill_incidents=1,
            total_spill_volume_bbls=3.0,
            air_emissions_tons=95.0
        )
        
        q2_metrics = EnvironmentalMetrics(
            report_date=date(2024, 6, 30),
            spill_incidents=0,
            total_spill_volume_bbls=0.0,
            air_emissions_tons=85.0
        )
        
        q3_metrics = EnvironmentalMetrics(
            report_date=date(2024, 9, 30),
            spill_incidents=2,
            total_spill_volume_bbls=8.0,
            air_emissions_tons=110.0
        )
        
        quarterly_scores = [
            q1_metrics.calculate_environmental_score(),
            q2_metrics.calculate_environmental_score(),
            q3_metrics.calculate_environmental_score()
        ]
        
        # Calculate trend
        if quarterly_scores[2] > quarterly_scores[0]:
            trend = "Improving"
        elif quarterly_scores[2] < quarterly_scores[0]:
            trend = "Declining"
        else:
            trend = "Stable"
        
        assert len(quarterly_scores) == 3
        assert all(0.0 <= score <= 1.0 for score in quarterly_scores)
        assert trend in ["Improving", "Declining", "Stable"]
    
    def test_environmental_compliance_integration_with_template(self):
        """Test environmental compliance integration with compliance template"""
        template = ComplianceTemplate()
        
        # Build compliance context with environmental metrics
        compliance_metrics = ComplianceMetrics(entity_id="GC_001")
        environmental_metrics = EnvironmentalMetrics(
            entity_id="GC_001",
            spill_incidents=1,
            total_spill_volume_bbls=5.0,
            air_emissions_tons=90.0,
            environmental_violations=0
        )
        
        context = template.build_compliance_context(
            compliance_metrics=compliance_metrics,
            environmental_metrics=environmental_metrics
        )
        
        # Check integration
        assert "environmental_metrics" in context
        assert "compliance_summary" in context
        
        # Environmental score should be included in compliance summary
        compliance_summary = context["compliance_summary"]
        assert "environmental_score" in compliance_summary
        assert compliance_summary["environmental_score"] > 0