"""
Test script for optimized BSEE data processing.

This script demonstrates the performance improvements from chunked and parallel processing
for all three data sources: well, production, and WAR data.

Usage:
    python test_optimized_processing.py
"""

import sys
import time
from pathlib import Path
from datetime import datetime
import psutil
import gc

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from worldenergydata.modules.bsee.data.scrapers import BSEEWebScraper
from worldenergydata.modules.bsee.data.processors import MemoryProcessor, OptimizedProcessor
from loguru import logger

def format_bytes(bytes_value):
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"

def get_memory_info():
    """Get current memory usage."""
    process = psutil.Process()
    mem_info = process.memory_info()
    return {
        'rss': mem_info.rss,
        'rss_str': format_bytes(mem_info.rss),
        'percent': process.memory_percent()
    }

def test_data_source(data_type, url, use_optimized=True):
    """
    Test processing for a specific data source.
    
    Args:
        data_type: Type of data (well, production, war)
        url: URL to download from
        use_optimized: Whether to use optimized processing
    """
    print(f"\n{'='*70}")
    print(f"Testing {data_type.upper()} Data Processing")
    print(f"Mode: {'OPTIMIZED' if use_optimized else 'STANDARD'}")
    print(f"{'='*70}")
    
    # Initial memory
    gc.collect()
    initial_memory = get_memory_info()
    print(f"Initial memory: {initial_memory['rss_str']} ({initial_memory['percent']:.1f}%)")
    
    # Download data
    print(f"\n1. Downloading {data_type} data...")
    scraper = BSEEWebScraper()
    download_start = time.time()
    
    zip_data = scraper.download_zip_to_memory(url, data_type=data_type)
    
    if not zip_data:
        print(f"   ERROR: Failed to download {data_type} data")
        return None
    
    download_time = time.time() - download_start
    file_size = len(zip_data)
    print(f"   Downloaded: {format_bytes(file_size)} in {download_time:.2f} seconds")
    print(f"   Speed: {format_bytes(file_size/download_time)}/s")
    
    # Process data
    print(f"\n2. Processing {data_type} data...")
    processor = MemoryProcessor(use_optimized=use_optimized)
    
    process_start = time.time()
    
    # Call appropriate processing method
    if data_type == 'well':
        result = processor.process_well_data(zip_data, {})
    elif data_type == 'production':
        result = processor.process_production_data(zip_data, {})
    elif data_type == 'war':
        result = processor.process_war_data(zip_data, {})
    else:
        print(f"   ERROR: Unknown data type {data_type}")
        return None
    
    process_time = time.time() - process_start
    
    # Memory after processing
    final_memory = get_memory_info()
    memory_increase = final_memory['rss'] - initial_memory['rss']
    
    # Results
    print(f"\n3. Results:")
    print(f"   Processing time: {process_time:.2f} seconds")
    print(f"   Memory increase: {format_bytes(memory_increase)}")
    print(f"   Final memory: {final_memory['rss_str']} ({final_memory['percent']:.1f}%)")
    
    if result:
        total_rows = 0
        for filename, data in result.items():
            if isinstance(data, dict) and 'shape' in data:
                rows = data['shape'][0]
                total_rows += rows
                print(f"   - {filename}: {rows:,} rows")
        
        print(f"   Total rows processed: {total_rows:,}")
        if process_time > 0:
            print(f"   Processing speed: {total_rows/process_time:.0f} rows/second")
    
    # Get detailed stats if using optimized processor
    if use_optimized and hasattr(processor, 'optimized_processor'):
        stats = processor.optimized_processor.get_processing_summary()
        if stats:
            print(f"\n4. Optimized Processing Statistics:")
            print(f"   Files processed: {stats.get('files_processed', 0)}")
            print(f"   Average speed: {stats.get('average_rows_per_second', 0):.0f} rows/second")
            if 'file_details' in stats:
                for file, details in stats['file_details'].items():
                    print(f"   - {file}:")
                    print(f"     Rows: {details['rows']:,}")
                    print(f"     Time: {details['time_seconds']:.2f}s")
                    print(f"     Speed: {details['rows_per_second']:.0f} rows/s")
                    print(f"     Memory: {details['memory_mb']:.1f} MB")
    
    # Cleanup
    del zip_data
    del result
    gc.collect()
    
    return {
        'data_type': data_type,
        'file_size': file_size,
        'download_time': download_time,
        'process_time': process_time,
        'memory_increase': memory_increase,
        'total_rows': total_rows if result else 0
    }

def compare_processing_modes():
    """Compare standard vs optimized processing."""
    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON: Standard vs Optimized Processing")
    print("="*70)
    
    # Test each data source
    test_configs = [
        # ('well', 'https://www.data.bsee.gov/Well/Files/APDRawData.zip'),
        # ('production', 'https://www.data.bsee.gov/Production/Files/ProductionRawData.zip'),
        ('war', 'https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip'),  # Uncomment for full test
    ]
    
    results = []
    
    for data_type, url in test_configs:
        # Test with optimized processing
        print(f"\n\n{'#'*70}")
        print(f"Testing {data_type.upper()} with OPTIMIZED processing")
        print(f"{'#'*70}")
        optimized_result = test_data_source(data_type, url, use_optimized=True)
        if optimized_result:
            optimized_result['mode'] = 'optimized'
            results.append(optimized_result)
        
        # Optional: Test with standard processing for comparison
        # Uncomment the following to compare with standard processing
        # print(f"\n\n{'#'*70}")
        # print(f"Testing {data_type.upper()} with STANDARD processing")
        # print(f"{'#'*70}")
        # standard_result = test_data_source(data_type, url, use_optimized=False)
        # if standard_result:
        #     standard_result['mode'] = 'standard'
        #     results.append(standard_result)
    
    # Summary
    print("\n\n" + "="*70)
    print("SUMMARY OF RESULTS")
    print("="*70)
    
    for result in results:
        print(f"\n{result['data_type'].upper()} ({result.get('mode', 'unknown').upper()}):")
        print(f"  File size: {format_bytes(result['file_size'])}")
        print(f"  Download time: {result['download_time']:.2f}s")
        print(f"  Processing time: {result['process_time']:.2f}s")
        print(f"  Memory increase: {format_bytes(result['memory_increase'])}")
        print(f"  Total rows: {result['total_rows']:,}")
        if result['process_time'] > 0:
            print(f"  Processing speed: {result['total_rows']/result['process_time']:.0f} rows/s")

def main():
    """Main test function."""
    print("="*70)
    print("BSEE Data Processing - Optimized Performance Test")
    print("="*70)
    print(f"Start time: {datetime.now()}")
    print(f"System memory: {format_bytes(psutil.virtual_memory().total)}")
    print(f"Available memory: {format_bytes(psutil.virtual_memory().available)}")
    
    try:
        # Run performance comparison
        compare_processing_modes()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nEnd time: {datetime.now()}")
    print("="*70)

if __name__ == "__main__":
    main()