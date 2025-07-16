import os
import pickle
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LeaseData:
    """
    A focused class to get lease data from .bin files by lease number.
    """
    
    def __init__(self, cfg=None):
        """
        Initialize the LeaseData with the path to the bin folder.
        
        Args:
            cfg (dict): Configuration dictionary containing bin folder path
        """
        self.cfg = cfg
        self.bin_folder_path = None
        self.lease_columns = [
            'BOTM_LEASE_NUM', 'BOTM_LEASE_NUMBER', 'SURF_LEASE_NUM', 
            'LEASE_NUMBER', 'LEASE', 'COMP_LEASE_NUMBER'
        ]
        
        # Initialize bin_folder_path if cfg is provided
        if cfg is not None:
            self._initialize_bin_path(cfg)
    
    def _initialize_bin_path(self, cfg):
        """
        Initialize the bin folder path from configuration.
        
        Args:
            cfg (dict): Configuration dictionary
        """
        self.bin_folder_path = Path(cfg['parameters']['filepath']['bin_dir'])
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
        Main router function to handle lease data retrieval.
        
        Args:
            cfg (dict): Configuration dictionary
            input_group (dict): Input group containing lease information
            
        Returns:
            dict: Updated configuration with lease data
        """
        # Ensure bin path is initialized
        self._ensure_bin_path_initialized(cfg)
        
        lease_num = input_group['lease']['number'] if input_group and 'lease' in input_group and 'number' in input_group['lease'] and input_group['lease']['number'] is not None else None
        bin_path = Path(cfg['parameters']['filepath']['bin_dir'])
        if not bin_path.exists():
            raise FileNotFoundError(f"Bin folder not found: {bin_path}")
        
        lease_numbers = self.parse_input(lease_num)
        results = self.search_lease_numbers(lease_numbers)
        if not results:
            logger.warning("No results found.")
        else:
            logger.info(f"Found {len(results)} results for lease numbers, saving to results directory.")
            self.save_results(cfg, results, input_group)
        
        return cfg
    def get_all_bin_files(self) -> List[Path]:
        """
        Find all .bin files in the bin folder and its subfolders.
        
        Returns:
            List[Path]: List of paths to all .bin files
        """
        if self.bin_folder_path is None:
            raise ValueError("bin_folder_path not initialized. Call router method first or provide cfg in __init__.")
        
        bin_files = []
        for root, dirs, files in os.walk(self.bin_folder_path):
            for file in files:
                if file.endswith('.bin'):
                    bin_files.append(Path(root) / file)
        
        logger.info(f"Found {len(bin_files)} .bin files")
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
                logger.debug(f"Successfully loaded {file_path} with shape {df.shape}")
                return df
            else:
                logger.warning(f"File {file_path} does not contain a DataFrame")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()
    
    def search_in_dataframe(self, df: pd.DataFrame, lease_numbers: List[Union[str, int]]) -> pd.DataFrame:
        """
        Search for lease numbers in a dataframe.
        
        Args:
            df (pd.DataFrame): The dataframe to search in
            lease_numbers (List[Union[str, int]]): List of lease numbers to search for
            
        Returns:
            pd.DataFrame: Filtered dataframe containing matching rows
        """
        if df.empty:
            return pd.DataFrame()
        
        # Find lease columns that exist in the dataframe
        existing_columns = [col for col in self.lease_columns if col in df.columns]
        
        if not existing_columns:
            return pd.DataFrame()
        
        # Create a mask for matching rows
        mask = pd.Series([False] * len(df))
        
        for col in existing_columns:
            try:
                if df[col].dtype == 'object':
                    # For string columns, convert to string and use isin
                    col_str = df[col].astype(str)
                    str_lease_numbers = [str(ln) for ln in lease_numbers]
                    mask |= col_str.isin(str_lease_numbers)
                else:
                    # For numeric columns, use isin directly
                    mask |= df[col].isin(lease_numbers)
            except Exception as e:
                logger.warning(f"Error searching in column {col}: {e}")
                continue
        
        return df[mask]
    
    def parse_input(self, user_input: str) -> List[Union[str, int]]:
        """
        Parse user input to handle multiple lease numbers.
        
        Args:
            user_input (str): Raw user input string
            
        Returns:
            List[Union[str, int]]: List of parsed lease numbers
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
    
    def search_lease_numbers(self, lease_numbers: Union[str, int, List[Union[str, int]]]) -> Dict[str, pd.DataFrame]:
        """
        Search for lease numbers across all .bin files.
        
        Args:
            lease_numbers: Single lease number or list of lease numbers
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping file paths to matching dataframes
        """
        # Convert single value to list
        if not isinstance(lease_numbers, list):
            lease_numbers = [lease_numbers]
        
        logger.info(f"Searching for lease numbers: {lease_numbers}")
        
        results = {}
        bin_files = self.get_all_bin_files()
        
        if not bin_files:
            logger.warning("No .bin files found")
            return results
        
        for file_path in bin_files:
            df = self.load_dataframe(file_path)
            if df.empty:
                continue
            
            matches = self.search_in_dataframe(df, lease_numbers)
            if not matches.empty:
                results[str(file_path)] = matches
                logger.info(f"Found {len(matches)} matches in {file_path}")
        
        return results
    
    def save_results(self, cfg, results: Dict[str, pd.DataFrame], input_group=None):
        """
        Save search results to CSV files.
        
        Args:
            cfg (dict): Configuration dictionary
            results (Dict[str, pd.DataFrame]): Search results
            input_group (dict): Input group containing lease information
        """
        from assetutilities.common.utilities import is_dir_valid_func

        lease_num = str(input_group['lease']['number']) if input_group and 'lease' in input_group and 'number' in input_group['lease'] else 'unknown'
        label = 'lease'+ lease_num
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
            df_copy['source_file'] = file_path
            combined_df = pd.concat([combined_df, df_copy], ignore_index=True)
        
        # Save the combined results to CSV
        if not combined_df.empty:
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
        else:
            logger.warning("No results to save")
            
        return combined_df