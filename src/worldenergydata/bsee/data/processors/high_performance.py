"""
Optimized Processor Module for BSEE Data

This module provides optimized processing for all three BSEE data sources:
- Well (APD) data: ~10-20 MB
- Production data: ~50-80 MB
- WAR data: ~120 MB

Features:
- Chunked processing for memory efficiency
- Parallel processing for multiple files
- Progress tracking
- Memory monitoring
- Data type optimization
"""

import concurrent.futures
import gc
import io
import pickle
import time
import zipfile
from functools import partial
from pathlib import Path
from typing import Any, ByteString, Dict, Tuple

import pandas as pd
from loguru import logger

# Try to import optional dependencies
try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    logger.warning("tqdm not installed - progress bars will be simple")
    TQDM_AVAILABLE = False

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil not installed - memory monitoring will be limited")
    PSUTIL_AVAILABLE = False


class OptimizedProcessor:
    """
    Optimized processor for BSEE data with chunked and parallel processing.
    """

    # Chunk sizes optimized for each data type
    CHUNK_SIZES = {
        "well": 50000,  # Well data chunks
        "production": 100000,  # Production data chunks
        "war": 25000,  # WAR data chunks (larger file, smaller chunks)
        "default": 50000,
    }

    # Maximum workers for parallel processing
    MAX_WORKERS = {
        "well": 4,  # Well files are smaller, can handle more workers
        "production": 3,  # Medium size files
        "war": 2,  # Large files, fewer workers to avoid memory issues
        "default": 3,
    }

    # Data type optimizations for memory efficiency
    DTYPE_OPTIMIZATIONS = {
        "well": {
            "API_WELL_NUMBER": "category",
            "WELL_NAME": "category",
            "OPERATOR_NAME": "category",
            "SURFACE_AREA_CODE": "category",
            "BOTTOM_AREA_CODE": "category",
            "WELL_TYPE_CODE": "category",
            "STATUS_CODE": "category",
        },
        "production": {
            "API_WELL_NUMBER": "category",
            "PRODUCTION_DATE": "datetime64[ns]",
            "DAYS_ON_PRODUCTION": "int16",
            "OIL_VOLUME": "float32",
            "GAS_VOLUME": "float32",
            "WATER_VOLUME": "float32",
        },
        "war": {
            "API_WELL_NUMBER": "category",
            "ACTIVITY_DATE": "datetime64[ns]",
            "ACTIVITY_TYPE": "category",
            "RIG_NAME": "category",
            "CONTRACTOR": "category",
            "WATER_DEPTH": "float32",
        },
    }

    def __init__(self):
        """Initialize the optimized processor."""
        self.processed_data = {}
        self.processing_stats = {}
        self.memory_threshold_mb = 1000  # 1GB threshold

    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            mem_info = process.memory_info()
            return {
                "rss_mb": mem_info.rss / 1024 / 1024,
                "vms_mb": mem_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
            }
        else:
            return {"rss_mb": 0, "vms_mb": 0, "percent": 0}

    def optimize_dataframe_dtypes(
        self, df: pd.DataFrame, data_type: str
    ) -> pd.DataFrame:
        """
        Optimize DataFrame data types to reduce memory usage.

        Args:
            df: DataFrame to optimize
            data_type: Type of data (well, production, war)

        Returns:
            Optimized DataFrame
        """
        dtype_map = self.DTYPE_OPTIMIZATIONS.get(data_type, {})

        for col, dtype in dtype_map.items():
            if col in df.columns:
                try:
                    if dtype == "datetime64[ns]":
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                    elif dtype == "category":
                        # Only convert to category if it saves memory
                        if df[col].nunique() / len(df) < 0.5:  # Less than 50% unique
                            df[col] = df[col].astype("category")
                    else:
                        df[col] = df[col].astype(dtype)
                except Exception as e:
                    logger.warning(f"Could not optimize {col} to {dtype}: {e}")

        # Optimize integer columns
        for col in df.select_dtypes(include=["int64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="integer")

        # Optimize float columns
        for col in df.select_dtypes(include=["float64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="float")

        return df

    def process_csv_chunked(
        self, file_handle, filename: str, data_type: str, progress_callback=None
    ) -> pd.DataFrame:
        """
        Process a CSV file in chunks with progress tracking.

        Args:
            file_handle: File handle to read from
            filename: Name of the file being processed
            data_type: Type of data (well, production, war)
            progress_callback: Optional callback for progress updates

        Returns:
            Processed DataFrame
        """
        chunk_size = self.CHUNK_SIZES.get(data_type, self.CHUNK_SIZES["default"])
        chunks = []
        total_rows = 0
        start_time = time.time()

        logger.info(f"Processing {filename} in chunks of {chunk_size} rows")

        try:
            # Process file in chunks
            for chunk_num, chunk in enumerate(
                pd.read_csv(
                    file_handle,
                    chunksize=chunk_size,
                    low_memory=False,
                    encoding="ISO-8859-1",
                )
            ):
                # Optimize data types
                chunk = self.optimize_dataframe_dtypes(chunk, data_type)

                # Apply data-specific processing
                if data_type == "well":
                    chunk = self.process_well_chunk(chunk)
                elif data_type == "production":
                    chunk = self.process_production_chunk(chunk)
                elif data_type == "war":
                    chunk = self.process_war_chunk(chunk)

                chunks.append(chunk)
                total_rows += len(chunk)

                # Progress update
                if progress_callback:
                    progress_callback(chunk_num, total_rows)
                elif chunk_num % 10 == 0:
                    logger.info(f"  {filename}: Processed {total_rows:,} rows")

                # Periodic garbage collection
                if chunk_num % 20 == 0:
                    gc.collect()

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            raise

        # Combine all chunks
        if chunks:
            result = pd.concat(chunks, ignore_index=True)
            elapsed = time.time() - start_time
            logger.info(
                f"Completed {filename}: {total_rows:,} rows in {elapsed:.2f} seconds"
            )

            # Store statistics
            self.processing_stats[filename] = {
                "rows": total_rows,
                "time_seconds": elapsed,
                "rows_per_second": total_rows / elapsed if elapsed > 0 else 0,
                "memory_mb": result.memory_usage(deep=True).sum() / 1024 / 1024,
            }

            return result
        else:
            return pd.DataFrame()

    def process_well_chunk(self, chunk: pd.DataFrame) -> pd.DataFrame:
        """Process a chunk of well data."""
        # Remove rows with missing API numbers
        chunk = chunk[chunk["API_WELL_NUMBER"].notna()]

        # Convert dates if present
        date_columns = ["SPUD_DATE", "COMPLETION_DATE", "STATUS_DATE"]
        for col in date_columns:
            if col in chunk.columns:
                chunk[col] = pd.to_datetime(chunk[col], errors="coerce")

        return chunk

    def process_production_chunk(self, chunk: pd.DataFrame) -> pd.DataFrame:
        """Process a chunk of production data."""
        # Remove rows with zero production
        if "OIL_VOLUME" in chunk.columns and "GAS_VOLUME" in chunk.columns:
            chunk = chunk[(chunk["OIL_VOLUME"] > 0) | (chunk["GAS_VOLUME"] > 0)]

        # Calculate total BOE if needed
        if "GAS_VOLUME" in chunk.columns and "OIL_VOLUME" in chunk.columns:
            chunk["BOE_TOTAL"] = chunk["OIL_VOLUME"] + (chunk["GAS_VOLUME"] / 6000)

        return chunk

    def process_war_chunk(self, chunk: pd.DataFrame) -> pd.DataFrame:
        """Process a chunk of WAR data."""
        # Remove rows with missing activity types
        if "ACTIVITY_TYPE" in chunk.columns:
            chunk = chunk[chunk["ACTIVITY_TYPE"].notna()]

        # Parse activity dates
        if "ACTIVITY_DATE" in chunk.columns:
            chunk["ACTIVITY_DATE"] = pd.to_datetime(
                chunk["ACTIVITY_DATE"], errors="coerce"
            )
            chunk["ACTIVITY_YEAR"] = chunk["ACTIVITY_DATE"].dt.year
            chunk["ACTIVITY_MONTH"] = chunk["ACTIVITY_DATE"].dt.month

        return chunk

    def process_single_file_parallel(
        self, zip_data: bytes, filename: str, data_type: str
    ) -> Tuple[str, pd.DataFrame]:
        """
        Process a single file from ZIP archive (for parallel execution).

        Args:
            zip_data: ZIP file data
            filename: File to process
            data_type: Type of data

        Returns:
            Tuple of (filename, processed DataFrame)
        """
        logger.info(f"Starting parallel processing of {filename}")

        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                with zf.open(filename) as file:
                    df = self.process_csv_chunked(file, filename, data_type)
                    return (filename, df)
        except Exception as e:
            logger.error(f"Error in parallel processing {filename}: {e}")
            return (filename, pd.DataFrame())

    def process_zip_optimized(
        self, zip_data: ByteString, data_type: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Process ZIP file with parallel and chunked processing.

        Args:
            zip_data: ZIP file data
            data_type: Type of data (well, production, war)

        Returns:
            Dictionary mapping filenames to DataFrames
        """
        results = {}
        start_time = time.time()
        initial_memory = self.get_memory_usage()

        logger.info(f"Starting optimized {data_type} data processing")
        logger.info(f"Initial memory: {initial_memory['rss_mb']:.1f} MB")

        # List all CSV/TXT files in ZIP
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            data_files = [
                f for f in zf.namelist() if f.endswith(".txt") or f.endswith(".csv")
            ]
            logger.info(f"Found {len(data_files)} files to process")

        if len(data_files) == 0:
            logger.warning("No data files found in ZIP")
            return results

        # Determine if we should use parallel processing
        use_parallel = len(data_files) > 1
        max_workers = self.MAX_WORKERS.get(data_type, self.MAX_WORKERS["default"])

        if use_parallel:
            logger.info(f"Using parallel processing with {max_workers} workers")

            # Process files in parallel
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                # Submit all files for processing
                process_func = partial(
                    self.process_single_file_parallel, zip_data, data_type=data_type
                )

                if TQDM_AVAILABLE:
                    # With progress bar
                    futures = {executor.submit(process_func, f): f for f in data_files}

                    with tqdm(
                        total=len(data_files), desc=f"Processing {data_type} files"
                    ) as pbar:
                        for future in concurrent.futures.as_completed(futures):
                            filename = futures[future]
                            try:
                                file_result, df = future.result(timeout=300)
                                results[file_result] = df
                                pbar.update(1)
                                pbar.set_postfix({"file": filename, "rows": len(df)})
                            except Exception as e:
                                logger.error(f"Failed to process {filename}: {e}")
                                pbar.update(1)
                else:
                    # Without progress bar
                    futures = []
                    for filename in data_files:
                        future = executor.submit(process_func, filename)
                        futures.append((future, filename))

                    for future, filename in futures:
                        try:
                            file_result, df = future.result(timeout=300)
                            results[file_result] = df
                            logger.info(f"Completed {filename}: {len(df)} rows")
                        except Exception as e:
                            logger.error(f"Failed to process {filename}: {e}")
        else:
            # Process single file (no parallel needed)
            filename = data_files[0]
            logger.info(f"Processing single file: {filename}")

            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                with zf.open(filename) as file:
                    df = self.process_csv_chunked(file, filename, data_type)
                    results[filename] = df

        # Final statistics
        elapsed = time.time() - start_time
        final_memory = self.get_memory_usage()
        memory_increase = final_memory["rss_mb"] - initial_memory["rss_mb"]

        total_rows = sum(len(df) for df in results.values())
        logger.info(f"Completed {data_type} processing:")
        logger.info(f"  - Files: {len(results)}")
        logger.info(f"  - Total rows: {total_rows:,}")
        logger.info(f"  - Time: {elapsed:.2f} seconds")
        logger.info(f"  - Memory increase: {memory_increase:.1f} MB")
        logger.info(f"  - Final memory: {final_memory['rss_mb']:.1f} MB")

        return results

    def save_to_binary(
        self, data_dict: Dict[str, pd.DataFrame], output_dir: str, data_type: str
    ) -> None:
        """
        Save processed data to binary format (pickle).

        Args:
            data_dict: Dictionary of DataFrames
            output_dir: Output directory path
            data_type: Type of data
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for filename, df in data_dict.items():
            # Create output filename
            base_name = Path(filename).stem
            output_file = output_path / f"{base_name}.bin"

            # Save as pickle
            with open(output_file, "wb") as f:
                pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info(f"Saved {output_file}: {len(df)} rows")

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing statistics."""
        if not self.processing_stats:
            return {}

        total_rows = sum(s["rows"] for s in self.processing_stats.values())
        total_time = sum(s["time_seconds"] for s in self.processing_stats.values())
        total_memory = sum(s["memory_mb"] for s in self.processing_stats.values())

        return {
            "files_processed": len(self.processing_stats),
            "total_rows": total_rows,
            "total_time_seconds": total_time,
            "average_rows_per_second": total_rows / total_time if total_time > 0 else 0,
            "total_memory_mb": total_memory,
            "file_details": self.processing_stats,
        }
