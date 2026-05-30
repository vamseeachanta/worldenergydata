# Standard library imports

# Third party imports
import numpy as np
import pandas as pd
import plotly.graph_objects as go  # noqa: F401
from assetutilities.common.data import SaveData
from assetutilities.common.visualization.visualization_templates_plotly import (
    VisualizationTemplatesPlotly,
)
from assetutilities.common.yml_utilities import WorkingWithYAML  # noqa
from loguru import logger

from worldenergydata.bsee.analysis.legacy.api12_aggregation import (
    BlockFieldAggregator,
    DataFrameMergeUtils,
)
from worldenergydata.bsee.analysis.legacy.api12_economics import (
    NPVCalculator,
    RevenueCalculator,
)
from worldenergydata.bsee.analysis.legacy.api12_io import ProductionResultSaver

# Import from split modules for internal use
from worldenergydata.bsee.analysis.legacy.api12_models import (
    API12SummaryBuilder,
    ProductionRateCalculator,
)
from worldenergydata.bsee.analysis.legacy.api12_visualization import (
    ProductionVisualizer,
)
from worldenergydata.bsee.data.bsee_data import BSEEData
from worldenergydata.common.legacy.data import DateTimeUtility

# Re-export split classes for backward compatibility
__all__ = [
    "ProductionAPI12Analysis",
    "API12SummaryBuilder",
    "ProductionRateCalculator",
    "BlockFieldAggregator",
    "DataFrameMergeUtils",
    "ProductionResultSaver",
    "ProductionVisualizer",
    "RevenueCalculator",
    "NPVCalculator",
]

wwy = WorkingWithYAML()
viz_templates_plotly = VisualizationTemplatesPlotly()

bsee_data = BSEEData()
dtu = DateTimeUtility()
save_data = SaveData()


class ProductionAPI12Analysis:
    """
    Production analysis for API12 wells.

    This class orchestrates production analysis using specialized components:
    - API12SummaryBuilder: Creates summary DataFrames
    - ProductionRateCalculator: Calculates production rates
    - BlockFieldAggregator: Aggregates data by block/field
    - ProductionResultSaver: Saves analysis results
    - ProductionVisualizer: Creates visualizations
    - RevenueCalculator: Generates revenue tables
    - NPVCalculator: Performs NPV calculations
    """

    def __init__(self):
        # Initialize component classes
        self._summary_builder = API12SummaryBuilder()
        self._rate_calculator = ProductionRateCalculator()
        self._aggregator = BlockFieldAggregator()
        self._merge_utils = DataFrameMergeUtils()
        self._result_saver = ProductionResultSaver()
        self._visualizer = ProductionVisualizer()
        self._revenue_calculator = RevenueCalculator()
        self._npv_calculator = NPVCalculator()

    def router(self, cfg):
        pass

    def run_production_analysis(self, cfg, data):
        logger.info("Starting production analysis...")
        production_groups = data.get("production_data", None)
        logger.info(f"Production groups found: {production_groups is not None}")
        groups_dict = {}
        if production_groups is None:
            logger.error("No production data found in the provided data.")

        production_summary_df_groups = pd.DataFrame()
        production_df_api12s = []
        prod_rate_bopd_groups = pd.DataFrame(columns=["PRODUCTION_DATETIME"])
        prod_cumulative_mmbbl_groups = pd.DataFrame(columns=["PRODUCTION_DATETIME"])
        api12_array_groups = []

        for group_idx, production_group in enumerate(production_groups):
            prod_rate_bopd_group = pd.DataFrame(columns=["PRODUCTION_DATETIME"])
            prod_cumulative_mmbbl_group = pd.DataFrame(columns=["PRODUCTION_DATETIME"])
            api12_array_group = cfg["data"]["groups"][group_idx]["api12"]
            api12_array_groups = api12_array_groups + api12_array_group

            for api12_idx, api12 in enumerate(api12_array_group):
                production_df_api12 = production_group[api12]

                _, production_analysis_dict_api12 = self.analyze_data_for_api12(
                    cfg, api12, production_df_api12
                )
                summary_df_api12 = production_analysis_dict_api12["summary_df_api12"]
                production_analysis_df_api12 = production_analysis_dict_api12[
                    "api12_df"
                ]

                production_df_api12s.append(production_analysis_df_api12)
                production_summary_df_groups = pd.concat(
                    [production_summary_df_groups, summary_df_api12], ignore_index=True
                )

                if not len(production_analysis_df_api12):
                    production_analysis_df_api12 = pd.DataFrame(
                        columns=[
                            "PRODUCTION_DATETIME",
                            "O_PROD_RATE_BOPD",
                            "O_CUMMULATIVE_PROD_MMBBL",
                        ]
                    )

                prod_rate_bopd_api12 = production_analysis_df_api12[
                    ["PRODUCTION_DATETIME", "O_PROD_RATE_BOPD"]
                ].rename(columns={"O_PROD_RATE_BOPD": api12})

                prod_rate_bopd_group = pd.merge(
                    prod_rate_bopd_group,
                    prod_rate_bopd_api12,
                    on=["PRODUCTION_DATETIME"],
                    how="outer",
                )

                prod_cumulative_mmbbl_api12 = production_analysis_df_api12[
                    ["PRODUCTION_DATETIME", "O_CUMMULATIVE_PROD_MMBBL"]
                ].rename(columns={"O_CUMMULATIVE_PROD_MMBBL": api12})
                prod_cumulative_mmbbl_group = pd.merge(
                    prod_cumulative_mmbbl_group,
                    prod_cumulative_mmbbl_api12,
                    on=["PRODUCTION_DATETIME"],
                    how="outer",
                )

            prod_rate_bopd_group = prod_rate_bopd_group.replace({np.nan: None})
            prod_rate_bopd_group.sort_values(by=["PRODUCTION_DATETIME"], inplace=True)
            prod_rate_bopd_group.reset_index(inplace=True, drop=True)

            prod_cumulative_mmbbl_group = prod_cumulative_mmbbl_group.replace(
                {np.nan: None}
            )
            prod_cumulative_mmbbl_group.sort_values(
                by=["PRODUCTION_DATETIME"], inplace=True
            )
            prod_cumulative_mmbbl_group.reset_index(inplace=True, drop=True)

            self._result_saver.save_result_group(cfg, group_idx, prod_rate_bopd_group)

            prod_rate_bopd_groups = pd.merge(
                prod_rate_bopd_groups,
                prod_rate_bopd_group,
                on=["PRODUCTION_DATETIME"],
                how="outer",
            )
            self.pd_merge_clean_column_names(prod_rate_bopd_groups)
            prod_rate_bopd_groups = prod_rate_bopd_groups.replace({np.nan: None})
            prod_rate_bopd_groups.sort_values(by=["PRODUCTION_DATETIME"], inplace=True)
            prod_rate_bopd_groups.reset_index(inplace=True, drop=True)

            prod_cumulative_mmbbl_groups = pd.merge(
                prod_cumulative_mmbbl_groups,
                prod_cumulative_mmbbl_group,
                on=["PRODUCTION_DATETIME"],
                how="outer",
            )
            self.pd_merge_clean_column_names(prod_cumulative_mmbbl_groups)
            prod_cumulative_mmbbl_groups = prod_cumulative_mmbbl_groups.replace(
                {np.nan: None}
            )
            prod_cumulative_mmbbl_groups.sort_values(
                by=["PRODUCTION_DATETIME"], inplace=True
            )

            prod_cumulative_mmbbl_groups.reset_index(inplace=True, drop=True)

        api12_df = production_analysis_dict_api12["api12_df"]

        self._result_saver.save_result_groups(
            cfg,
            api12_array_groups,
            production_df_api12s,
            production_summary_df_groups,
            prod_rate_bopd_groups,
            prod_cumulative_mmbbl_groups,
        )

        prod_cumulative_mmbbl_groups_by_block = (
            self._aggregator.convert_well_df_to_block_df(
                cfg, prod_cumulative_mmbbl_groups
            )
        )

        self._aggregator.convert_block_to_field(prod_cumulative_mmbbl_groups_by_block)

        if "economics" in cfg and cfg["economics"]["flag"]:
            revenue_df = self._revenue_calculator.generate_revenue_table(cfg, api12_df)
            self._npv_calculator.perform_npv_calculation(cfg, revenue_df)

        groups_dict["production_df_api12s"] = production_df_api12s
        groups_dict["prod_rate_bopd_groups"] = prod_rate_bopd_groups
        groups_dict["prod_cumulative_mmbbl_groups"] = prod_cumulative_mmbbl_groups
        groups_dict["production_summary_df_groups"] = production_summary_df_groups

        return cfg, groups_dict

    def pd_merge_clean_column_names(self, merged_df):
        """Delegate to DataFrameMergeUtils."""
        return self._merge_utils.clean_merged_column_names(merged_df)

    def save_result_group(self, cfg, group_idx, production_analysis_df_group):
        """Delegate to ProductionResultSaver."""
        return self._result_saver.save_result_group(
            cfg, group_idx, production_analysis_df_group
        )

    def save_result_groups(
        self,
        cfg,
        api12_array_groups,
        production_df_api12s,
        production_summary_df_groups,
        prod_rate_bopd_groups,
        prod_cumulative_mmbbl_groups,
    ):
        """Delegate to ProductionResultSaver."""
        return self._result_saver.save_result_groups(
            cfg,
            api12_array_groups,
            production_df_api12s,
            production_summary_df_groups,
            prod_rate_bopd_groups,
            prod_cumulative_mmbbl_groups,
        )

    def analyze_data_for_api12(self, cfg, api12, api12_df):
        api12_df_analyzed = api12_df.copy()
        summary_df_api12 = pd.DataFrame()
        completion_names = []
        if not api12_df.empty:
            completion_names = api12_df.COMPLETION_NAME.unique()

        for completion_name in completion_names:
            api12_df_analyzed = api12_df[
                api12_df.COMPLETION_NAME == completion_name
            ].copy()
            api12_df_analyzed = (
                self._rate_calculator.add_production_rate_and_date_to_df(
                    cfg, api12_df_analyzed
                )
            )
            api12_df_analyzed.sort_values(by=["PRODUCTION_DATETIME"], inplace=True)
            api12_df_analyzed.reset_index(inplace=True)
            if api12_df_analyzed.O_PROD_RATE_BOPD.max() > 0:
                summary_df_api12_by_completion_name = (
                    self._summary_builder.get_summary_df_api12(
                        api12, completion_name, api12_df_analyzed
                    )
                )
                summary_df_api12 = pd.concat(
                    [summary_df_api12, summary_df_api12_by_completion_name],
                    ignore_index=True,
                )

        prod_anal_api12_dict = {
            "api12_df": api12_df_analyzed,
            "api12": api12,
            "summary_df_api12": summary_df_api12,
            "completion_names": completion_names,
        }

        return cfg, prod_anal_api12_dict

    def get_summary_df_api12(self, well_api12, completion_name, api12_df):
        """Delegate to API12SummaryBuilder."""
        return self._summary_builder.get_summary_df_api12(
            well_api12, completion_name, api12_df
        )

    def add_production_rate_and_date_to_df(self, cfg, api12_df):
        """Delegate to ProductionRateCalculator."""
        return self._rate_calculator.add_production_rate_and_date_to_df(cfg, api12_df)

    def convert_well_df_to_block_df(self, cfg, df_api12: pd.DataFrame) -> pd.DataFrame:
        """Delegate to BlockFieldAggregator."""
        return self._aggregator.convert_well_df_to_block_df(cfg, df_api12)

    def extract_block_mapping(self, cfg):
        """Delegate to BlockFieldAggregator."""
        return self._aggregator.extract_block_mapping(cfg)

    def convert_block_to_field(self, df_block: pd.DataFrame) -> pd.DataFrame:
        """Delegate to BlockFieldAggregator."""
        return self._aggregator.convert_block_to_field(df_block)

    def plot_production_rate_by_well(self, cfg, prod_rates_df):
        """Delegate to ProductionVisualizer."""
        return self._visualizer.plot_production_rate_by_well(cfg, prod_rates_df)

    def plot_prod_cumulative_mmbbl_by_well(self, cfg, prod_cumulative_mmbbl_groups):
        """Delegate to ProductionVisualizer."""
        return self._visualizer.plot_prod_cumulative_mmbbl_by_well(
            cfg, prod_cumulative_mmbbl_groups
        )

    def plot_prod_cumulative_mmbbl_by_block(
        self, cfg, prod_cumulative_mmbbl_groups_by_block
    ):
        """Delegate to ProductionVisualizer."""
        return self._visualizer.plot_prod_cumulative_mmbbl_by_block(
            cfg, prod_cumulative_mmbbl_groups_by_block
        )

    def plot_prod_cumulative_mmbbl_by_field(
        self, cfg, prod_cumulative_mmbbl_groups_by_field
    ):
        """Delegate to ProductionVisualizer."""
        return self._visualizer.plot_prod_cumulative_mmbbl_by_field(
            cfg, prod_cumulative_mmbbl_groups_by_field
        )

    def plot_revenues(self, cfg, revenue_df):
        """Delegate to ProductionVisualizer."""
        return self._visualizer.plot_revenues(cfg, revenue_df)

    def generate_revenue_table(self, cfg, api12_df):
        """Delegate to RevenueCalculator."""
        revenue_df = self._revenue_calculator.generate_revenue_table(cfg, api12_df)
        self._npv_calculator.perform_npv_calculation(cfg, revenue_df)
        return revenue_df

    def perform_npv_calculation(self, cfg, revenue_df):
        """Delegate to NPVCalculator."""
        return self._npv_calculator.perform_npv_calculation(cfg, revenue_df)

    def perform_excel_aligned_npv_calculation(self, cfg, revenue_df):
        """Delegate to NPVCalculator."""
        return self._npv_calculator.perform_excel_aligned_npv_calculation(
            cfg, revenue_df
        )

    def perform_decline_analysis_api12(self, cfg, api12_df):
        # TODO: Implement decline analysis
        pass
