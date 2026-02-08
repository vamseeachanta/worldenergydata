"""
Main orchestrator for SME financial analysis pipeline

This module coordinates all components of the financial analysis:
- Data loading (production, drilling, completion)
- Lease grouping and development assignment
- Cash flow calculations
- Report generation
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from worldenergydata.common import get_logger

# Import comprehensive report components as needed
from ...reports.comprehensive.hierarchical_aggregator import CostStructure, PriceDeck
from .cash_flow_calculator import CashFlowCalculator, FinancialParameters
from .data_loader import SMEDataLoader
from .drilling_completion import DrillingCompletionProcessor
from .lease_grouper import LeaseGrouper
from .report_generator import ReportGenerator
from .validators import DataValidator

logger = get_logger(__name__)


@dataclass
class AnalysisConfig:
    """Configuration for financial analysis"""

    input_path: str
    output_path: str
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    developments: List[str] = field(default_factory=list)
    oil_price_scenario: str = "mid"  # low, mid, high
    discount_rate: float = 0.10
    tax_rate: float = 0.35
    working_interest: float = 1.0
    net_revenue_interest: float = 0.875
    version: str = "V20"

    # Processing options
    use_cache: bool = True
    parallel_processing: bool = True
    max_workers: int = 4
    chunk_size: int = 10000

    # Development type mappings
    development_types: Dict[str, str] = field(
        default_factory=lambda: {
            "Stones": "subsea",
            "Anchor": "dry_tree",
            "Stampede": "subsea",
            "Julia": "subsea",
        }
    )

    def __post_init__(self):
        """Validate configuration after initialization"""
        self.start_date = pd.to_datetime(self.start_date)
        self.end_date = pd.to_datetime(self.end_date)

        if self.start_date > self.end_date:
            raise ValueError("Start date must be before end date")

        if not 0 <= self.discount_rate <= 1:
            raise ValueError("Discount rate must be between 0 and 1")

        if not 0 <= self.tax_rate <= 1:
            raise ValueError("Tax rate must be between 0 and 1")


@dataclass
class AnalysisResult:
    """Result of financial analysis"""

    success: bool
    output_file: Optional[str] = None
    development_results: Optional[Dict] = None
    metrics_summary: Optional[Dict] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


class FinancialAnalyzer:
    """Main orchestrator for SME financial analysis"""

    def __init__(self, config: AnalysisConfig):
        """
        Initialize the analyzer with configuration

        Args:
            config: Analysis configuration
        """
        self.config = config

        # Initialize components
        self.data_loader = SMEDataLoader(data_path=Path(config.input_path))

        self.lease_grouper = LeaseGrouper()
        self.drilling_loader = DrillingCompletionProcessor()
        self.cash_flow_calculator = CashFlowCalculator()
        self.report_generator = ReportGenerator()

        # Initialize validator
        self.validator = DataValidator()

        # Initialize price deck and cost structure from comprehensive reports
        self._init_economics()

        logger.info(f"Initialized FinancialAnalyzer with config: {config}")

    def _init_economics(self):
        """Initialize economic parameters from comprehensive reports"""
        # Create price deck based on scenario
        self.price_deck = PriceDeck()
        if self.config.oil_price_scenario == "low":
            self.price_deck.oil_price = 60.00
        elif self.config.oil_price_scenario == "high":
            self.price_deck.oil_price = 90.00
        else:  # mid
            self.price_deck.oil_price = 75.00

        # Create cost structure
        self.cost_structure = CostStructure()

        # Set financial parameters
        self.financial_params = FinancialParameters(
            discount_rate_annual=self.config.discount_rate,
            corporate_tax_rate=self.config.tax_rate,
            royalty_rate=1.0
            - self.config.net_revenue_interest,  # Convert NRI to royalty
            wti_base_price=self.price_deck.oil_price,
        )

    def run_analysis(self, output_path: Optional[str] = None) -> AnalysisResult:
        """
        Run complete financial analysis pipeline

        Args:
            output_path: Path for output Excel file

        Returns:
            AnalysisResult with status and output information
        """
        import time

        start_time = time.time()

        try:
            logger.info("Starting financial analysis pipeline")

            # Load data
            production_data, drilling_data = self.load_data()

            # Validate input data
            if not self.validator.validate_production_data(production_data):
                raise ValueError("Production data validation failed")

            if drilling_data is not None and not self.validator.validate_drilling_data(
                drilling_data
            ):
                raise ValueError("Drilling data validation failed")

            # Process developments
            development_results = self.process_developments(
                production_data, drilling_data
            )

            # Generate report
            if output_path is None:
                output_path = (
                    Path(self.config.output_path)
                    / f"financial_analysis_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
                )

            report_path = self.generate_report(development_results, str(output_path))

            # Calculate summary metrics
            metrics_summary = self._calculate_summary_metrics(development_results)

            # Validate output
            if not self.validator.validate_results(development_results):
                logger.warning("Output validation detected potential issues")

            execution_time = time.time() - start_time
            logger.info(
                f"Analysis completed successfully in {execution_time:.2f} seconds"
            )

            return AnalysisResult(
                success=True,
                output_file=report_path,
                development_results=development_results,
                metrics_summary=metrics_summary,
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return AnalysisResult(
                success=False,
                error_message=str(e),
                execution_time=time.time() - start_time,
            )

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load production and drilling data

        Returns:
            Tuple of (production_data, drilling_data)
        """
        logger.info("Loading data from repository")

        # Load production data
        production_data = self.data_loader.load_production_data(
            start_date=self.config.start_date, end_date=self.config.end_date
        )

        # Load drilling and completion data
        drilling_data = self.drilling_loader.load_drilling_data()

        logger.info(
            f"Loaded {len(production_data)} production records and {len(drilling_data)} drilling records"
        )

        return production_data, drilling_data

    def process_developments(
        self,
        production_data: pd.DataFrame,
        drilling_data: Optional[pd.DataFrame] = None,
    ) -> Dict:
        """
        Process each development and calculate financials

        Args:
            production_data: Production data
            drilling_data: Drilling and completion data

        Returns:
            Dictionary with results for each development
        """
        logger.info("Processing developments")

        # Group leases by development
        if self.config.developments:
            # Use specified developments
            development_groups = self.lease_grouper.group_by_development(
                production_data, self.config.developments
            )
        else:
            # Auto-detect developments - group all as single development for now
            development_groups = {"All_Leases": production_data}

        results = {}

        for dev_name, dev_data in development_groups.items():
            logger.info(f"Processing development: {dev_name}")

            try:
                # Get development type
                dev_type = self.config.development_types.get(dev_name, "subsea")

                # Process single development
                dev_results = self._process_single_development(
                    dev_name, dev_data, drilling_data, dev_type
                )

                results[dev_name] = dev_results

            except Exception as e:
                logger.error(f"Error processing {dev_name}: {str(e)}")
                results[dev_name] = {
                    "error": str(e),
                    "cash_flow": pd.DataFrame(),
                    "metrics": {},
                }

        return results

    def _process_single_development(
        self,
        name: str,
        production_data: pd.DataFrame,
        drilling_data: Optional[pd.DataFrame],
        development_type: str,
    ) -> Dict:
        """
        Process a single development

        Args:
            name: Development name
            production_data: Production data for this development
            drilling_data: Drilling data (optional)
            development_type: Type of development (subsea, dry_tree)

        Returns:
            Dictionary with cash flow and metrics
        """
        # Calculate monthly cash flows
        cash_flow_df = self.cash_flow_calculator.calculate_monthly_cash_flow(
            production_data=production_data,
            drilling_data=drilling_data,
            price_deck=self.price_deck,
            cost_structure=self.cost_structure,
            financial_params=self.financial_params,
            development_type=development_type,
        )

        # Calculate financial metrics
        metrics = self.calculate_financial_metrics(cash_flow_df)

        # Add development metadata
        first_oil_date = (
            production_data["year_month"].min() if not production_data.empty else None
        )
        producer_count = (
            production_data["API"].nunique() if "API" in production_data.columns else 0
        )

        return {
            "cash_flow": cash_flow_df,
            "metrics": metrics,
            "first_oil": first_oil_date,
            "development_type": development_type,
            "producer_count": producer_count,
            "total_wells": producer_count,
        }

    def calculate_financial_metrics(self, cash_flow_df: pd.DataFrame) -> Dict:
        """
        Calculate financial metrics for a cash flow stream

        Args:
            cash_flow_df: DataFrame with cash flow data

        Returns:
            Dictionary with financial metrics
        """
        if cash_flow_df.empty:
            return {}

        # Calculate NPV
        npv = self.cash_flow_calculator.calculate_npv(
            cash_flow_df, self.financial_params.discount_rate_annual
        )

        # Calculate MIRR
        mirr = self.cash_flow_calculator.calculate_mirr(
            cash_flow_df, self.financial_params.discount_rate_annual
        )

        # Calculate other metrics
        total_revenue = (
            cash_flow_df["Revenue_Net"].sum() if "Revenue_Net" in cash_flow_df else 0
        )
        total_opex = cash_flow_df["OPEX"].sum() if "OPEX" in cash_flow_df else 0
        total_capex = cash_flow_df["CAPEX"].sum() if "CAPEX" in cash_flow_df else 0
        total_oil = (
            cash_flow_df["Gross_Oil_bbls"].sum()
            if "Gross_Oil_bbls" in cash_flow_df
            else 0
        )

        # Payback period
        cum_cash_flow = (
            cash_flow_df["Net_Cash_Flow"].cumsum()
            if "Net_Cash_Flow" in cash_flow_df
            else pd.Series()
        )
        payback_months = (
            (cum_cash_flow > 0).idxmax()
            if not cum_cash_flow.empty and (cum_cash_flow > 0).any()
            else None
        )

        return {
            "npv": npv,
            "mirr_annual": mirr,
            "total_revenue": total_revenue,
            "total_opex": total_opex,
            "total_capex": total_capex,
            "total_oil_bbls": total_oil,
            "payback_months": payback_months,
            "roi": (
                (total_revenue - total_opex - total_capex) / total_capex
                if total_capex > 0
                else 0
            ),
        }

    def generate_report(self, development_results: Dict, output_path: str) -> str:
        """
        Generate Excel report

        Args:
            development_results: Results for all developments
            output_path: Path for output file

        Returns:
            Path to generated report
        """
        logger.info(f"Generating report: {output_path}")

        # Generate report using report generator
        report_path = self.report_generator.generate_report(
            development_data=development_results,
            output_path=output_path,
            version=self.config.version,
        )

        logger.info(f"Report generated: {report_path}")

        return report_path

    def _calculate_summary_metrics(self, development_results: Dict) -> Dict:
        """
        Calculate summary metrics across all developments

        Args:
            development_results: Results for all developments

        Returns:
            Dictionary with summary metrics
        """
        total_npv = sum(
            res.get("metrics", {}).get("npv", 0) for res in development_results.values()
        )

        total_oil = sum(
            res.get("metrics", {}).get("total_oil_bbls", 0)
            for res in development_results.values()
        )

        total_revenue = sum(
            res.get("metrics", {}).get("total_revenue", 0)
            for res in development_results.values()
        )

        total_capex = sum(
            res.get("metrics", {}).get("total_capex", 0)
            for res in development_results.values()
        )

        development_count = len(development_results)
        successful_count = sum(
            1 for res in development_results.values() if "error" not in res
        )

        return {
            "total_npv": total_npv,
            "total_oil_bbls": total_oil,
            "total_revenue": total_revenue,
            "total_capex": total_capex,
            "development_count": development_count,
            "successful_count": successful_count,
            "average_npv": total_npv / successful_count if successful_count > 0 else 0,
        }
