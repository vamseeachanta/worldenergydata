import os
import pickle
import pandas as pd
from pathlib import Path
from typing import Dict, List, Union
from loguru import logger

from colorama import Fore, Style
from colorama import init as colorama_init

colorama_init()

class APIData:
    """
    A focused class to get data from .bin files by API well number.
    """

    def __init__(self, cfg=None):
        """
        Initialize the APISearcher with the path to the bin folder.

        Args:
            cfg (dict): Configuration dictionary containing bin folder path
        """
        self.cfg = cfg
        self.bin_folder_path = None
        self.api_columns = ['API Well Number']

        # Initialize bin_folder_path if cfg is provided
        if cfg is not None:
            self._initialize_bin_path(cfg)

    def _initialize_bin_path(self, cfg):
        """
        Initialize the bin folder path from configuration.

        Args:
            cfg (dict): Configuration dictionary
        """
        self.bin_folder_path = Path(cfg['parameters']['filepath']['Well_APD_Default'])
        if not self.bin_folder_path.exists():
            raise FileNotFoundError(f"Bin folder not found: {self.bin_folder_path}")

    def _ensure_bin_path_initialized(self, cfg):
        """
        Ensure bin folder path is initialized, initialize if not.

        Args:
            cfg (dict): Configuration dictionary
        """
        if self.bin_folder_path is None:
            self._initialize_bin_path(cfg)

    def router(self, cfg, input_group=None):
        """
        Main router function to get API data retrieval.

        Args:
            cfg (dict): Configuration dictionary
            input_group (dict): Input group containing API information

        Returns:
            dict: Updated configuration with API search results
        """
        # Ensure bin path is initialized
        self._ensure_bin_path_initialized(cfg)

        cfg_input_api12 = input_group['api12'] if 'api12' in input_group and input_group['api12'] is not None else None

        # Use the initialized bin_folder_path instead of re-reading from config
        if not self.bin_folder_path.exists():
            raise FileNotFoundError(f"Bin folder not found: {self.bin_folder_path}")

        results = self.get_api12_data_from_input_bin_files(cfg_input_api12)
        if not results:
            logger.warning("No results found.")
        else:
            self.save_results(cfg, results, input_group)

        return cfg

    def get_api12_data_from_input_bin_files(self, api_numbers: Union[str, int, List[Union[str, int]]]) -> Dict[str, pd.DataFrame]:
        """
        Get data across all .bin files from input bin file directory by API numbers.

        Args:
            api_numbers: Single API number or an array of API numbers

        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping file paths to matching dataframes
        """
        # Convert single value to list
        if not isinstance(api_numbers, list):
            api_numbers = [api_numbers]

        logger.info(f"Getting data for API {api_numbers[0]} START ...")

        results = {}
        bin_files = self.get_all_bin_files()

        if not bin_files:
            logger.warning(f"No .bin files found in path: {self.bin_folder_path}")
            return results

        for file_path in bin_files:
            logger.info(f"Processing {file_path.name}...")
            df = self.load_dataframe(file_path)
            if df.empty:
                continue

            matches = self.get_api12_matching_data(df, api_numbers)
            if not matches.empty:
                results[str(file_path)] = matches
                logger.success(f"Found {len(matches)} matches in {file_path.name}")

        return results

    def get_all_bin_files(self) -> List[Path]:
        """
        Get all .bin files from the bin folder .

        Returns:
            List[Path]: List of paths to all .bin files
        """
        if self.bin_folder_path is None:
            raise ValueError("bin_folder_path not initialized. Call router method first or provide cfg in __init__.")

        bin_files = []
        # Look for .bin files directly in the apd folder
        for file_path in self.bin_folder_path.glob('*.bin'):
            bin_files.append(file_path)

        return bin_files

    def load_dataframe(self, file_path: Path) -> pd.DataFrame:
        """
        Load a pickled dataframe from a .bin file.

        Args:
            file_path (Path): Path to the .bin file

        Returns:
            pd.DataFrame: Loaded dataframe or empty DataFrame if failed
        """
        try:
            with open(file_path, 'rb') as f:
                df = pickle.load(f)

            if isinstance(df, pd.DataFrame):
                return df
            else:
                logger.warning(f"File {file_path} does not contain a DataFrame, returning empty DataFrame")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()

    def get_api12_matching_data(self, df: pd.DataFrame, api_numbers: List[Union[str, int]]) -> pd.DataFrame:
        """
        Get API12 matching data from a dataframe.

        Args:
            df (pd.DataFrame): The dataframe to search in
            api_numbers (List[Union[str, int]]): List of API numbers to search for

        Returns:
            pd.DataFrame: Filtered dataframe containing matching rows
        """
        if df.empty:
            logger.warning("DataFrame is empty, returning empty DataFrame")
            return pd.DataFrame()

        # Find API columns that exist in the dataframe
        existing_columns = [col for col in self.api_columns if col in df.columns]

        if not existing_columns:
            return pd.DataFrame()

        # Create a mask for matching rows
        mask = pd.Series([False] * len(df))

        for col in existing_columns:
            try:
                if df[col].dtype == 'object':
                    # For string columns, convert to string and use isin
                    col_str = df[col].astype(str)
                    str_api_numbers = [str(api) for api in api_numbers]
                    mask |= col_str.isin(str_api_numbers)
                else:
                    # For numeric columns, use isin directly
                    mask |= df[col].isin(api_numbers)
            except Exception as e:
                logger.error(f"Error searching in column {col}: {e}")
                continue

        return df[mask]

    def parse_input(self, user_input: str) -> List[Union[str, int]]:
        """
        Parse user input to handle multiple API well numbers.

        Args:
            user_input (str): Raw user input string

        Returns:
            List[Union[str, int]]: List of parsed API numbers
        """
        import re
        user_input = str(user_input).strip()
        values = re.split(r'[,;\n\s]+', user_input.strip())

        parsed_values = []
        for value in values:
            value = value.strip()
            if value:
                try:
                    parsed_values.append(int(value))
                except ValueError:
                    parsed_values.append(value)

        return parsed_values

    def save_results(self, cfg, results: Dict[str, pd.DataFrame], input_group=None):
        """
        Save search results to CSV files.

        Args:
            results (Dict[str, pd.DataFrame]): Search results
            cfg (dict): Configuration dictionary
            input_group (dict): Input group containing API information
        """
        from assetutilities.common.utilities import is_dir_valid_func

        api_num = str(input_group['api12'][0])
        label = api_num
        output_path = os.path.join(cfg['Analysis']['result_folder'], 'Data')
        if output_path is None:
            result_folder = self.cfg['Analysis']['result_folder']
            output_path = os.path.join(result_folder, 'Data')
        analysis_root_folder = cfg['Analysis']['analysis_root_folder']
        is_dir_valid, output_path = is_dir_valid_func(output_path, analysis_root_folder)

        output_file = os.path.join(output_path, str(label) + '.csv')

        # Combine all results into a single DataFrame
        combined_df = pd.DataFrame()
        for file_path, df in results.items():
            df_copy = df.copy()
            combined_df = pd.concat([combined_df, df_copy], ignore_index=True)

        # Save the combined results to CSV
        if not combined_df.empty:
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
            logger.info(f"Getting Data for API {api_num} Finished ...")
        else:
            logger.warning("No results to save")

        return combined_df
