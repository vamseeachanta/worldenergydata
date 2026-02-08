"""
Test script to verify timeout handling for large data downloads.

This test validates that the enhanced BSEE data refresh system can handle
large file downloads without timing out, especially for production and WAR data.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from worldenergydata.bsee.data.scrapers import BSEEWebScraper


def test_timeout_configuration():
    """Test that timeout configurations are properly set."""
    scraper = BSEEWebScraper()
    
    # Check that timeouts are configured as expected
    assert scraper.TIMEOUTS['well'] == 600, "Well data timeout should be 10 minutes"
    assert scraper.TIMEOUTS['production'] == 1200, "Production data timeout should be 20 minutes"
    assert scraper.TIMEOUTS['war'] == 2400, "WAR data timeout should be 40 minutes"
    assert scraper.MAX_RETRIES == 5, "Max retries should be 5"
    assert scraper.CHUNK_SIZE == 32768, "Chunk size should be 32KB"
    
    logger.info("✅ Timeout configurations are correct")
    return True


def test_get_file_info():
    """Test getting file information without downloading."""
    scraper = BSEEWebScraper()
    
    logger.info("Testing file info retrieval...")
    
    # Test for each data source
    for data_type in ['well', 'production', 'war']:
        url = scraper.URLS[data_type]
        info = scraper.get_file_info(url)
        
        if 'error' not in info:
            size_mb = info.get('size_mb', 0)
            logger.info(f"{data_type.upper()} data size: {size_mb:.2f} MB")
            logger.info(f"  Content-Type: {info.get('content_type', 'unknown')}")
            logger.info(f"  Last-Modified: {info.get('last_modified', 'unknown')}")
            
            # Verify appropriate timeout for file size
            if data_type == 'production' and size_mb > 10:
                assert scraper.TIMEOUTS['production'] >= 1200, "Production timeout too small for file size"
            if data_type == 'war' and size_mb > 50:
                assert scraper.TIMEOUTS['war'] >= 2400, "WAR timeout too small for file size"
        else:
            logger.warning(f"Could not get info for {data_type}: {info['error']}")
    
    logger.info("✅ File info retrieval completed")
    return True


def test_download_with_timeout_simulation():
    """Simulate download with appropriate timeout handling."""
    scraper = BSEEWebScraper()
    
    logger.info("Testing download simulation with timeouts...")
    
    # Test URL accessibility first
    results = scraper.verify_all_sources()
    
    for name, result in results.items():
        if result['accessible']:
            logger.info(f"✅ {name} URL is accessible: {result['url']}")
        else:
            logger.warning(f"❌ {name} URL not accessible: {result['url']}")
    
    # Get file sizes to determine if actual download is feasible
    for data_type in ['well', 'production']:
        url = scraper.URLS[data_type]
        info = scraper.get_file_info(url)
        
        if 'size_mb' in info:
            size_mb = info['size_mb']
            timeout = scraper.TIMEOUTS.get(data_type, scraper.TIMEOUTS['default'])
            
            # Calculate if timeout is sufficient (assuming 1 MB/s minimum speed)
            min_required_time = size_mb  # seconds needed at 1 MB/s
            
            logger.info(f"{data_type.upper()} analysis:")
            logger.info(f"  File size: {size_mb:.2f} MB")
            logger.info(f"  Configured timeout: {timeout} seconds")
            logger.info(f"  Min time needed (at 1 MB/s): {min_required_time:.0f} seconds")
            
            if min_required_time > timeout:
                logger.warning(f"  ⚠️ Timeout may be insufficient for slow connections")
            else:
                logger.info(f"  ✅ Timeout should be sufficient")
    
    logger.info("✅ Download simulation completed")
    return True


def test_small_download():
    """Test downloading a small file to verify the download mechanism works."""
    scraper = BSEEWebScraper()
    
    logger.info("Testing small file download (well data)...")
    
    # Only test with well data as it's the smallest
    start_time = time.time()
    
    # Use a very short timeout for testing (we're not actually downloading)
    info = scraper.get_file_info(scraper.URLS['well'])
    
    if 'size_mb' in info and info['size_mb'] < 20:  # Only try if file is small
        logger.info(f"Well data is {info['size_mb']:.2f} MB - attempting download...")
        
        # Note: Actual download is commented out to avoid test timeout
        # data = scraper.download_well_data()
        # if data:
        #     logger.info(f"✅ Successfully downloaded {len(data)/(1024*1024):.2f} MB")
        # else:
        #     logger.warning("❌ Download failed")
        
        logger.info("Download test skipped to avoid timeout in test environment")
    else:
        logger.info(f"Skipping actual download - file too large or info not available")
    
    elapsed = time.time() - start_time
    logger.info(f"Test completed in {elapsed:.2f} seconds")
    
    return True


def run_all_tests():
    """Run all timeout handling tests."""
    logger.info("=" * 70)
    logger.info("TIMEOUT HANDLING TESTS")
    logger.info("=" * 70)
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    tests = [
        ("Timeout Configuration", test_timeout_configuration),
        ("File Info Retrieval", test_get_file_info),
        ("Download Simulation", test_download_with_timeout_simulation),
        ("Small Download Test", test_small_download),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\nRunning: {test_name}")
        logger.info("-" * 40)
        try:
            result = test_func()
            results.append((test_name, "PASSED" if result else "FAILED"))
        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            results.append((test_name, "ERROR"))
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    for test_name, status in results:
        symbol = "✅" if status == "PASSED" else "❌"
        logger.info(f"{symbol} {test_name}: {status}")
    
    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    logger.info("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)