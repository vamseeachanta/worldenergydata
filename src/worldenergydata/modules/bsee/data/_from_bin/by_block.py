import os
import pickle
import pandas as pd
from pathlib import Path
from typing import Dict, List, Union
from loguru import logger

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
        self.block_columns = [
            'BLOCK', 'BOTM_BLOCK_NUM', 'BOTM_BLOCK_NUMBER', 
            'SURF_BLOCK_NUM', 'BLOCK_NUMBER', 'COMP_BLOCK_NUMBER'
        ]
        
        # Initialize bin_folder_path if cfg is provided
        if cfg is not None:
            self._initialize_bin_path(cfg)
    
    def _initialize_bin_path(self, cfg):
        """Initialize the bin folder path from configuration.
        """
        self.bin_folder_path = Path(cfg['parameters']['filepath']['bin_dir'])
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
        
        block_num = input_group['bottom_block']['number'] if 'number' in input_group['bottom_block'] and input_group['bottom_block']['number'] is not None else None
        bin_path = Path(cfg['parameters']['filepath']['bin_dir'])
        if not bin_path.exists():
            raise FileNotFoundError(f"Bin folder not found: {bin_path}")
        
        block_numbers_array = self.get_block_array(block_num)
        results = self.search_block_numbers(block_numbers_array)
        if not results:
            logger.warning("No results found.")
        else:
            logger.info(f"Found {len(results)} results for block numbers, saving to results directory.")
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
                return df
            else:
                logger.warning(f"File {file_path} does not contain a DataFrame")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return pd.DataFrame()
    
    def search_in_dataframe(self, df: pd.DataFrame, block_numbers: List[Union[str, int]]) -> pd.DataFrame:
        """
        Search for block numbers in a dataframe.
        
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
    
    def search_block_numbers(self, block_numbers: Union[str, int, List[Union[str, int]]]) -> Dict[str, pd.DataFrame]:
        """
        Search for block numbers across all .bin files.
        
        Args:
            block_numbers: Single block number or list of block numbers
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping file paths to matching dataframes
        """
        # Convert single value to list
        if not isinstance(block_numbers, list):
            block_numbers = [block_numbers]
        
        logger.info(f"Getting data for block {block_numbers} START ...")
        
        results = {}
        bin_files = self.get_all_bin_files()
        
        if not bin_files:
            logger.warning("No .bin files found")
            return results
        
        for file_path in bin_files:
            df = self.load_dataframe(file_path)
            if df.empty:
                continue
            
            matches = self.search_in_dataframe(df, block_numbers)
            if not matches.empty:
                results[str(file_path)] = matches
                logger.info(f"Found {len(matches)} matches in {file_path}")
        
        return results
    
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
        else:
            logger.warning("No results to save")
            
        return combined_df
