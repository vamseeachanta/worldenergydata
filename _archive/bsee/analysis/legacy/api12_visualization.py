# Standard library imports
import os

# Third party imports
import pandas as pd
import plotly.graph_objects as go
from assetutilities.common.visualization.visualization_templates_plotly import (
    VisualizationTemplatesPlotly,
)

viz_templates_plotly = VisualizationTemplatesPlotly()


class ProductionVisualizer:
    """Creates production data visualizations."""

    def plot_production_rate_by_well(
        self, cfg: dict, prod_rates_df: pd.DataFrame
    ) -> None:
        """
        Plot production rates by well.

        Args:
            cfg: Configuration dictionary
            prod_rates_df: DataFrame with production rates
        """
        from assetutilities.engine import engine as au_engine

        plot_yml = viz_templates_plotly.get_xy_line_df(cfg["Analysis"].copy())
        plot_yml["data"]["groups"][0]["file_name"] = prod_rates_df

        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "prod_rate_by_well_" + groups_label
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, "Plot", file_label)

        settings = {
            "file_name": file_name,
            "title": "Production Data for API12",
            "xlabel": "PRODUCTION_DATETIME",
            "ylabel": "production",
            "columns_var_name": "api12",
            "customize_xdate_ticks": {
                "flag": True,
                "start_time": "2018-01-01",
                "end_time": "2025-04-03",
            },
        }
        plot_yml["settings"].update(settings)
        au_engine(inputfile=None, cfg=plot_yml, config_flag=False)

    def plot_prod_cumulative_mmbbl_by_well(
        self, cfg: dict, prod_cumulative_mmbbl_groups: pd.DataFrame
    ) -> None:
        """
        Plot cumulative production by well.

        Args:
            cfg: Configuration dictionary
            prod_cumulative_mmbbl_groups: DataFrame with cumulative production
        """
        from assetutilities.engine import engine as au_engine

        plot_yml = viz_templates_plotly.get_xy_line_df(cfg["Analysis"].copy())
        plot_yml["data"]["groups"][0]["file_name"] = prod_cumulative_mmbbl_groups

        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "prod_cumulative_mmbbl_by_well_" + groups_label
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, "Plot", file_label)

        settings = {
            "file_name": file_name,
            "title": "Cumulative Production by well",
            "xlabel": "PRODUCTION_DATETIME",
            "ylabel": "cumulative_production",
            "columns_var_name": "api12",
            "customize_xdate_ticks": {
                "flag": True,
                "start_time": "2010-01-01",
                "end_time": "2025-06-03",
            },
        }
        plot_yml["settings"].update(settings)
        au_engine(inputfile=None, cfg=plot_yml, config_flag=False)

    def plot_prod_cumulative_mmbbl_by_block(
        self, cfg: dict, prod_cumulative_mmbbl_groups_by_block: pd.DataFrame
    ) -> None:
        """
        Plot cumulative production by block.

        Args:
            cfg: Configuration dictionary
            prod_cumulative_mmbbl_groups_by_block: DataFrame with block-level production
        """
        from assetutilities.engine import engine as au_engine

        plot_yml = viz_templates_plotly.get_xy_line_df(cfg["Analysis"].copy())
        plot_yml["data"]["groups"][0][
            "file_name"
        ] = prod_cumulative_mmbbl_groups_by_block

        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "prod_cumulative_mmbbl_by_block_" + groups_label
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, "Plot", file_label)

        settings = {
            "file_name": file_name,
            "title": "Cumulative Production by block",
            "xlabel": "PRODUCTION_DATETIME",
            "ylabel": "cumulative_production",
            "columns_var_name": "block",
            "customize_xdate_ticks": {
                "flag": True,
                "start_time": "2015-01-01",
                "end_time": "2025-06-03",
            },
        }
        plot_yml["settings"].update(settings)
        au_engine(inputfile=None, cfg=plot_yml, config_flag=False)

    def plot_prod_cumulative_mmbbl_by_field(
        self, cfg: dict, prod_cumulative_mmbbl_groups_by_field: pd.DataFrame
    ) -> None:
        """
        Plot cumulative production by field.

        Args:
            cfg: Configuration dictionary
            prod_cumulative_mmbbl_groups_by_field: DataFrame with field-level production
        """
        from assetutilities.engine import engine as au_engine

        plot_yml = viz_templates_plotly.get_xy_line_df(cfg["Analysis"].copy())
        plot_yml["data"]["groups"][0][
            "file_name"
        ] = prod_cumulative_mmbbl_groups_by_field

        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "prod_cumulative_mmbbl_by_field_" + groups_label
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, "Plot", file_label)

        settings = {
            "file_name": file_name,
            "title": "Cumulative Production by field",
            "xlabel": "PRODUCTION_DATETIME",
            "ylabel": "cumulative_production",
            "columns_var_name": "field",
            "customize_xdate_ticks": {
                "flag": True,
                "start_time": "2013-01-01",
                "end_time": "2025-06-03",
            },
        }
        plot_yml["settings"].update(settings)
        au_engine(inputfile=None, cfg=plot_yml, config_flag=False)

    def plot_revenues(self, cfg: dict, revenue_df: pd.DataFrame) -> None:
        """
        Plot monthly revenues from oil production.

        Args:
            cfg: Configuration dictionary
            revenue_df: DataFrame with revenue data
        """
        revenue_df["Month"] = pd.to_datetime(
            revenue_df["Month"], format="%Y%m", errors="coerce"
        )
        months = revenue_df["Month"].tolist()
        revenue_usd = revenue_df["Revenue (USD)"].tolist()

        fig = go.Figure(data=[go.Bar(name="Revenue (USD)", x=months, y=revenue_usd)])

        fig.update_layout(
            title="Monthly Revenue from Oil Production",
            xaxis=dict(title="Month", dtick="M3"),
            yaxis=dict(
                title="Revenue (USD)",
                tickprefix="$",
                tickformat=",",
                range=[0, 40000000],
            ),
            template="plotly_white",
        )

        groups_label = cfg["meta"].get("label", None)
        if groups_label is None:
            groups_label = cfg["Analysis"]["file_name_for_overwrite"]

        file_label = "monthly_revenues_" + groups_label
        result_folder = cfg["Analysis"]["result_folder"]
        file_name = os.path.join(result_folder, "Plot", file_label + ".html")
        fig.write_html(file_name, include_plotlyjs="cdn")
