import os
import pickle
import pandas as pd
from pathlib import Path
from typing import Dict, List, Union
from loguru import logger

from colorama import Fore, Style
from colorama import init as colorama_init

colorama_init()

class BlockData:
    """
    A focused class to get block data from .bin files by block number.
    """
    
    def __init__(self,cfg=None):
        """
        Initialize the BlockSearcher with the path to the bin folder.
        
        Args:
            cfg (dict): Configuration dictionary containing bin folder path
        """
        self.cfg = cfg
        self.bin_folder_path = None
        self.block_columns = ['Bottom Block Number']
        
        # Initialize bin_folder_path if cfg is provided
        if cfg is not None:
            self._initialize_bin_path(cfg)
    
    def _initialize_bin_path(self, cfg):
        """Initialize the bin folder path from configuration.
        """
        self.bin_folder_path = Path(cfg['parameters']['filepath']['Well_APD_Default'])
        if not self.bin_folder_path.exists():
            raise FileNotFoundError(f"Bin folder not found: {self.bin_folder_path}")
    
    def _ensure_bin_path_initialized(self, cfg):
        """Ensure bin folder path is initialized, initialize if not.
        """
        if self.bin_folder_path is None:
            self._initialize_bin_path(cfg)
    
    def router(self, cfg, input_group=None):
        """
        Main router function to handle block data retrieval.
        """
        # Ensure bin path is initialized
        self._ensure_bin_path_initialized(cfg)
        
        cfg_input_block = input_group['bottom_block']['number'] if 'number' in input_group['bottom_block'] and input_group['bottom_block']['number'] is not None else None
        
        # Use the initialized bin_folder_path instead of re-reading from config
        if not self.bin_folder_path.exists():
            raise FileNotFoundError(f"Bin folder not found: {self.bin_folder_path}")
        
        block_numbers_array = self.get_block_array(cfg_input_block)
        results = self.get_block_data_from_input_bin_files(block_numbers_array)
        if not results:
            logger.warning("No results found.")
        else:
            self.save_results(cfg, results, input_group)
        
        return cfg
    
    def get_block_data_from_input_bin_files(self, block_numbers: Union[str, int, List[Union[str, int]]]) -> Dict[str, pd.DataFrame]:
        """
        get block data across all .bin files from the bin folder.
        
        Args:
            block_numbers: Single block number or list of block numbers
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping file paths to matching dataframes
        """
        # Convert single value to list
        if not isinstance(block_numbers, list):
            block_numbers = [block_numbers]
        
        logger.info(f"Getting data for block {block_numbers[0]} START ...")
        
        results = {}
        bin_files = self.get_all_bin_files_from_path()
        
        if not bin_files:
            logger.warning(f"No .bin files found in {self.bin_folder_path}")
            return results
        
        for file_path in bin_files:
            logger.info(f"Processing {file_path.name}...")
            df = self.load_dataframe(file_path)
            if df.empty:
                continue
            
            matches = self.get_matching_block_data_from_df(df, block_numbers)
            if not matches.empty:
                results[str(file_path)] = matches
                logger.info(f"Found {len(matches)} matches in {file_path.name}")
        
        return results
    
    def get_all_bin_files_from_path(self) -> List[Path]:
        """
        Get all .bin files from the bin folder.
        
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
                logger.warning(f"File {file_path} does not contain a DataFrame")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()
    
    def get_matching_block_data_from_df(self, df: pd.DataFrame, block_numbers: List[Union[str, int]]) -> pd.DataFrame:
        """
        Get matching block data from a dataframe.
        
        Args:
            df (pd.DataFrame): The dataframe to search in
            block_numbers (List[Union[str, int]]): List of block numbers to search for
            
        Returns:
            pd.DataFrame: Filtered dataframe containing matching rows
        """
        if df.empty:
            return pd.DataFrame()
        
        # Find block columns that exist in the dataframe
        existing_columns = [col for col in self.block_columns if col in df.columns]
        
        if not existing_columns:
            return pd.DataFrame()
        
        # Create a mask for matching rows
        mask = pd.Series([False] * len(df))
        
        for col in existing_columns:
            try:
                if df[col].dtype == 'object':
                    # For string columns, convert to string and use isin
                    col_str = df[col].astype(str)
                    str_block_numbers = [str(bn) for bn in block_numbers]
                    mask |= col_str.isin(str_block_numbers)
                else:
                    # For numeric columns, use isin directly
                    mask |= df[col].isin(block_numbers)
            except Exception as e:
                logger.warning(f"Error searching in column {col}: {e}")
                continue
        
        return df[mask]
    
    def get_block_array(self, user_input) -> List[int]:
        """
        Parse user input to handle multiple block numbers or a single block number.
        """
        if user_input is None:
            raise ValueError("User input cannot be None")
        
        block_numbers = []
        
        # Handle single integer input
        if isinstance(user_input, int):
            block_numbers.append(user_input)
        # Handle iterable input (list, tuple, etc.)
        elif hasattr(user_input, '__iter__') and not isinstance(user_input, str):
            for block in user_input:
                if isinstance(block, int):
                    block_numbers.append(block)
        else:
            raise TypeError(f"Expected int or iterable of ints, got {type(user_input)}")
        
        return block_numbers
    
    def save_results(self, cfg, results: Dict[str, pd.DataFrame], input_group=None):
        """
        Save search results to CSV files.
        
        Args:
            results (Dict[str, pd.DataFrame]): Search results
            cfg (dict): Configuration dictionary
            input_group (dict): Input group containing block information
        """
        from assetutilities.common.utilities import is_dir_valid_func

        bottom_block_num = str(input_group['bottom_block']['number'])
        area = str(input_group['bottom_block']['area'])
        label = area + '_' + bottom_block_num
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
            logger.info(f"Getting Data for Block {bottom_block_num} Finished ...")
        else:
            logger.warning("No results to save")
            
        return combined_df