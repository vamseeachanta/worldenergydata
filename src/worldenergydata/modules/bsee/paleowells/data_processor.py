"""
Paleowells Data Processor

Processes paleontological well data from BSEE/BOEM sources, including
geological epoch classification and data transformation.
"""

import pandas as pd
from pathlib import Path
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class PaleowellsDataProcessor:
    """Process and analyze paleontological well data from the Gulf of Mexico."""
    
    # Geological epochs for Lower Tertiary
    EPOCHS = ["Paleocene", "Eocene", "Oligocene"]
    
    # Fixed-width file format specification for paleo data
    FWIDTHS = [1, 12, 2, 2, 5, 5, 3, 2, 100, 3, 2, 1]
    
    COLUMN_NAMES = [
        'Record Type',
        'API Well Number',
        'Paleo Report ID Number',
        'Total Number of Reports for API',
        'Measured Depth',
        'True Vertical Depth',
        'Definite/Possible',
        'At/In',
        'Paleo Age',
        'Definite/Possible_2',
        'At/In_2',
        'Ecozone'
    ]
    
    def __init__(self, data_directory: Optional[Path] = None):
        """
        Initialize the Paleowells Data Processor.
        
        Args:
            data_directory: Path to the data directory. If None, uses default.
        """
        if data_directory is None:
            data_directory = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "modules" / "bsee" / "paleowells"
        
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        
    def filter_epochs(self, input_file: Path, output_file: Path, epochs: Optional[List[str]] = None) -> int:
        """
        Filter well data by geological epochs.
        
        Args:
            input_file: Path to input file containing all paleo data
            output_file: Path to output file for filtered data
            epochs: List of epochs to filter for. If None, uses default EPOCHS.
            
        Returns:
            Number of records written
        """
        if epochs is None:
            epochs = self.EPOCHS
            
        records_written = 0
        
        try:
            with open(input_file, 'r') as f_in:
                with open(output_file, 'w') as f_out:
                    for line in f_in:
                        for epoch in epochs:
                            if epoch in line:
                                f_out.write(line)
                                records_written += 1
                                break
                                
            logger.info(f"Filtered {records_written} records containing epochs {epochs}")
            return records_written
            
        except Exception as e:
            logger.error(f"Error filtering epochs: {e}")
            raise
            
    def parse_fixed_width_file(self, input_file: Path, output_csv: Optional[Path] = None) -> pd.DataFrame:
        """
        Parse fixed-width format paleo data file into DataFrame.
        
        Args:
            input_file: Path to fixed-width format file
            output_csv: Optional path to save as CSV
            
        Returns:
            DataFrame with parsed paleo data
        """
        try:
            df = pd.read_fwf(
                input_file,
                widths=self.FWIDTHS,
                names=self.COLUMN_NAMES
            )
            
            logger.info(f"Parsed {len(df)} records from {input_file}")
            logger.info(f"Data shape: {df.shape}")
            
            if output_csv:
                df.to_csv(output_csv, index=False)
                logger.info(f"Saved data to {output_csv}")
                
            return df
            
        except Exception as e:
            logger.error(f"Error parsing fixed-width file: {e}")
            raise
            
    def analyze_well_epochs(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze the distribution of wells by geological epochs.
        
        Args:
            df: DataFrame with paleo well data
            
        Returns:
            Dictionary with analysis results
        """
        analysis = {}
        
        # Extract epoch from Paleo Age column
        df['Epoch'] = df['Paleo Age'].str.extract(r'(Paleocene|Eocene|Oligocene|Miocene|Pliocene)')
        
        # Well count by epoch
        analysis['wells_by_epoch'] = df.groupby('Epoch')['API Well Number'].nunique().to_dict()
        
        # Total unique wells
        analysis['total_unique_wells'] = df['API Well Number'].nunique()
        
        # Depth statistics by epoch
        depth_stats = df.groupby('Epoch')[['Measured Depth', 'True Vertical Depth']].describe()
        analysis['depth_statistics'] = depth_stats.to_dict()
        
        # Definite vs Possible classifications
        analysis['classification_counts'] = df['Definite/Possible'].value_counts().to_dict()
        
        return analysis
        
    def process_paleowells_data(self, 
                               raw_data_file: Optional[Path] = None,
                               output_directory: Optional[Path] = None) -> pd.DataFrame:
        """
        Complete pipeline to process paleowells data.
        
        Args:
            raw_data_file: Path to raw paleo data file
            output_directory: Directory to save processed files
            
        Returns:
            Processed DataFrame
        """
        if output_directory is None:
            output_directory = self.data_directory
            
        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        
        # If raw data file is provided, filter it first
        if raw_data_file:
            filtered_file = output_directory / "lower_tertiary_wells.txt"
            self.filter_epochs(raw_data_file, filtered_file)
        else:
            # Use existing filtered file if available
            filtered_file = output_directory / "lower_tertiary_wells.txt"
            if not filtered_file.exists():
                raise FileNotFoundError(f"No filtered data file found at {filtered_file}")
                
        # Parse the filtered file
        output_csv = output_directory / "paleowells.csv"
        df = self.parse_fixed_width_file(filtered_file, output_csv)
        
        # Perform analysis
        analysis = self.analyze_well_epochs(df)
        
        # Save analysis results
        import json
        analysis_file = output_directory / "paleowells_analysis.json"
        
        # Convert non-serializable items for JSON
        json_analysis = {}
        for key, value in analysis.items():
            if isinstance(value, dict):
                json_analysis[key] = value
            else:
                json_analysis[key] = str(value)
                
        with open(analysis_file, 'w') as f:
            json.dump(json_analysis, f, indent=2)
            
        logger.info(f"Analysis saved to {analysis_file}")
        
        return df