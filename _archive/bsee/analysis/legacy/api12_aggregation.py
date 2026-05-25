# Third party imports
import pandas as pd


class BlockFieldAggregator:
    """Aggregates production data from well to block and field levels."""

    def convert_well_df_to_block_df(
        self, cfg: dict, df_api12: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Convert production DataFrame by well into production DataFrame by block.

        Args:
            cfg: Configuration dictionary containing block mapping
            df_api12: Input DataFrame with datetime and API12 columns

        Returns:
            New DataFrame with production datetime and block production data
        """
        datetime_col = df_api12.columns[0]
        block_to_api12s = self.extract_block_mapping(cfg)
        df_block = pd.DataFrame()
        df_block[datetime_col] = df_api12[datetime_col]

        for block, api12s_list in block_to_api12s.items():
            block_col_name = f"block_{block}"
            existing_api12s = [
                api12 for api12 in api12s_list if api12 in df_api12.columns
            ]
            if not existing_api12s:
                df_block[block_col_name] = 0
            else:
                df_block[block_col_name] = df_api12[existing_api12s].sum(axis=1)

        return df_block

    def extract_block_mapping(self, cfg: dict) -> dict:
        """
        Extract block to API12 mapping from configuration.

        Args:
            cfg: Configuration dictionary

        Returns:
            Dictionary mapping block IDs to lists of API12 identifiers
        """
        mapping = {}
        for group in cfg.get("data", {}).get("groups", []):
            block_ids = []
            block_id = (
                group["bottom_block"].get("number")
                if group["bottom_block"] is not None
                else None
            )
            if block_id is not None:
                block_ids.append(block_id)
            api12s = group.get("api12", [])
            for block in block_ids:
                block_str = str(block)
                api12_strs = [str(api12) for api12 in api12s]
                mapping[block_str] = api12_strs
        return mapping

    def convert_block_to_field(self, df_block: pd.DataFrame) -> pd.DataFrame:
        """
        Convert block-level DataFrame to field-level DataFrame.

        Args:
            df_block: DataFrame with datetime and block columns

        Returns:
            New DataFrame with datetime and field-level production
        """
        datetime_col = df_block.columns[0]
        field_df = pd.DataFrame()
        field_df[datetime_col] = df_block[datetime_col]

        block_columns = [col for col in df_block.columns if col.startswith("block_")]
        field_df["St Malo"] = df_block[block_columns].sum(axis=1)

        return field_df


class DataFrameMergeUtils:
    """Utility functions for DataFrame merging operations."""

    @staticmethod
    def clean_merged_column_names(merged_df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean column names after pandas merge operations.

        Removes _x and _y suffixes and duplicate columns from merge.

        Args:
            merged_df: DataFrame with potentially duplicate column names

        Returns:
            DataFrame with cleaned column names
        """
        merged_df.columns = merged_df.columns.map(str)
        merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith("_y")]
        merged_df.columns = merged_df.columns.str.replace("_x", "", regex=True)
        return merged_df
