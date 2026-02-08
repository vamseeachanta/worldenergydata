"""
Test script for chunk-based BSEE data refresh mechanism.

This script demonstrates:
- Change detection using HTTP HEAD requests
- Chunk-based downloads with caching
- Incremental data updates
- Bandwidth optimization
"""

import sys
from pathlib import Path

import yaml
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from worldenergydata.bsee.data.cache.chunk_manager import ChunkManager
from worldenergydata.bsee.data.enhanced.data_refresh_chunked import (
    DataRefreshChunked,
)


def test_chunk_manager():
    """Test the chunk manager functionality."""
    logger.info("=" * 60)
    logger.info("TESTING CHUNK MANAGER")
    logger.info("=" * 60)

    # Initialize chunk manager with test cache directory
    cache_dir = Path.home() / ".worldenergydata" / "test_cache"
    chunk_manager = ChunkManager(cache_dir)

    # Test 1: Check remote changes for all data types
    logger.info("\nTest 1: Checking remote changes")
    urls = {
        "well": "https://www.data.bsee.gov/Well/Files/APDRawData.zip",
        "production": "https://www.data.bsee.gov/Production/Files/ProductionRawData.zip",
        "war": "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
    }

    for data_type, url in urls.items():
        logger.info(f"\nChecking {data_type} data...")
        change_info = chunk_manager.check_remote_changes(url, data_type)

        logger.info(f"  Has changed: {change_info['has_changed']}")
        if change_info["change_reasons"]:
            logger.info(f"  Change reasons: {', '.join(change_info['change_reasons'])}")

        if change_info["remote_metadata"]:
            meta = change_info["remote_metadata"]
            if meta.get("content_length"):
                size_mb = meta["content_length"] / (1024 * 1024)
                logger.info(f"  File size: {size_mb:.2f} MB")
            if meta.get("last_modified"):
                logger.info(f"  Last modified: {meta['last_modified']}")
            if meta.get("etag"):
                logger.info(f"  ETag: {meta['etag'][:20]}...")

    # Test 2: Get cache statistics
    logger.info("\nTest 2: Cache statistics")
    stats = chunk_manager.get_cache_stats()
    logger.info(f"  Cache directory: {stats['cache_dir']}")
    logger.info(f"  Total cache size: {stats['total_size_mb']:.2f} MB")
    logger.info(f"  Cached chunks: {stats['chunk_count']}")
    logger.info(f"  Data types in cache: {list(stats['data_types'].keys())}")

    return chunk_manager


def test_chunked_refresh():
    """Test the full chunked refresh system."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING CHUNKED DATA REFRESH")
    logger.info("=" * 60)

    # Initialize chunked refresh system
    cache_dir = Path.home() / ".worldenergydata" / "test_cache"
    refresh_system = DataRefreshChunked(cache_dir)

    # Validate remote sources first
    logger.info("\nValidating remote data sources...")
    validation_results = refresh_system.validate_remote_sources()

    for data_type, info in validation_results.items():
        logger.info(f"\n{data_type.upper()}:")
        logger.info(f"  Accessible: {'✓' if info['accessible'] else '✗'}")
        logger.info(f"  Size: {info['size_mb']:.1f} MB")
        logger.info(f"  Cached: {'Yes' if info['has_cached_version'] else 'No'}")
        logger.info(f"  Cache current: {'Yes' if info['cache_current'] else 'No'}")

    # Create test configuration
    cfg = {
        "enhanced_mode": True,
        "chunked_refresh": True,
        "incremental_update": True,
        "force_refresh": False,  # Don't force refresh to test caching
        "data": {
            "well": True,  # Enable well data refresh
            "production": False,  # Skip production for faster test
            "war": False,  # Skip WAR (large file) for faster test
        },
        "parameters": {
            "filepath": {
                "apm": {"bin": "data/test/bin/apd"},
                "production": {"bin": "data/test/bin/production"},
                "war": {"bin": "data/test/bin/war"},
            }
        },
    }

    # Test refresh with chunk optimization
    logger.info("\nStarting chunked refresh test...")
    logger.info("Configuration:")
    logger.info(f"  Enhanced mode: {cfg['enhanced_mode']}")
    logger.info(f"  Chunked refresh: {cfg['chunked_refresh']}")
    logger.info(f"  Incremental update: {cfg['incremental_update']}")
    logger.info(f"  Force refresh: {cfg['force_refresh']}")
    logger.info(
        f"  Data types: well={cfg['data']['well']}, production={cfg['data']['production']}, war={cfg['data']['war']}"
    )

    # Run the refresh
    logger.info("\nExecuting refresh...")
    result_cfg, _ = refresh_system.router(cfg)

    # Run again to test caching
    logger.info("\n" + "=" * 60)
    logger.info("TESTING CACHE EFFECTIVENESS")
    logger.info("=" * 60)
    logger.info("\nRunning refresh again to test cache...")

    result_cfg, _ = refresh_system.router(cfg)

    # Get final cache statistics
    logger.info("\nFinal cache statistics:")
    cache_stats = refresh_system.chunk_manager.get_cache_stats()
    logger.info(f"  Total cache size: {cache_stats['total_size_mb']:.2f} MB")
    logger.info(f"  Cached chunks: {cache_stats['chunk_count']}")

    return refresh_system


def test_incremental_updates():
    """Test incremental update functionality."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING INCREMENTAL UPDATES")
    logger.info("=" * 60)

    import numpy as np
    import pandas as pd

    from worldenergydata.bsee.data.cache.chunk_manager import ChunkManager

    chunk_manager = ChunkManager()

    # Create sample DataFrames for testing
    logger.info("\nCreating test DataFrames...")

    # Original data
    old_df = pd.DataFrame(
        {
            "WELL_ID": range(1, 101),
            "PRODUCTION": np.random.rand(100),
            "DATE": pd.date_range("2024-01-01", periods=100),
        }
    )

    # New data with appended rows
    new_df = pd.DataFrame(
        {
            "WELL_ID": range(1, 111),  # 10 new rows
            "PRODUCTION": np.random.rand(110),
            "DATE": pd.date_range("2024-01-01", periods=110),
        }
    )

    # Test change detection
    logger.info("\nTesting change detection...")
    changes = chunk_manager._identify_dataframe_changes(old_df, new_df)

    logger.info(f"  Has changes: {changes['has_changes']}")
    logger.info(f"  Change type: {changes['type']}")
    logger.info(f"  New rows: {changes.get('new_rows', 0)}")

    # Test with updated data
    logger.info("\nTesting with updated rows...")
    updated_df = old_df.copy()
    updated_df.loc[50:60, "PRODUCTION"] = 999  # Update some rows

    changes = chunk_manager._identify_dataframe_changes(old_df, updated_df)
    logger.info(f"  Has changes: {changes['has_changes']}")
    logger.info(f"  Change type: {changes['type']}")
    logger.info(f"  Changed indices: {len(changes.get('changed_indices', []))} rows")


def test_bandwidth_savings():
    """Calculate and display bandwidth savings from chunking."""
    logger.info("\n" + "=" * 60)
    logger.info("BANDWIDTH SAVINGS ANALYSIS")
    logger.info("=" * 60)

    # Typical file sizes (approximate)
    file_sizes_mb = {"well": 10, "production": 30, "war": 120}

    # Simulate different scenarios
    scenarios = [
        {"name": "Daily refresh (no changes)", "cache_hit_rate": 0.95, "days": 30},
        {"name": "Weekly refresh (some changes)", "cache_hit_rate": 0.70, "days": 30},
        {"name": "First-time download", "cache_hit_rate": 0.0, "days": 1},
    ]

    for scenario in scenarios:
        logger.info(f"\nScenario: {scenario['name']}")
        logger.info(f"  Cache hit rate: {scenario['cache_hit_rate']*100:.0f}%")
        logger.info(f"  Period: {scenario['days']} days")

        total_without_cache = sum(file_sizes_mb.values()) * scenario["days"]
        total_with_cache = total_without_cache * (1 - scenario["cache_hit_rate"])
        savings = total_without_cache - total_with_cache

        logger.info(f"  Without caching: {total_without_cache:.0f} MB")
        logger.info(f"  With caching: {total_with_cache:.0f} MB")
        logger.info(
            f"  Bandwidth saved: {savings:.0f} MB ({(savings/total_without_cache)*100:.1f}%)"
        )

        # Time savings (assuming 10 Mbps connection)
        time_saved_minutes = (savings * 8) / (
            10 * 60
        )  # Convert MB to minutes at 10 Mbps
        logger.info(f"  Time saved: {time_saved_minutes:.1f} minutes")


def main():
    """Main test function."""
    logger.info("BSEE CHUNKED DATA REFRESH TEST SUITE")
    logger.info("=" * 60)

    try:
        # Test 1: Chunk Manager
        chunk_manager = test_chunk_manager()

        # Test 2: Chunked Refresh System
        refresh_system = test_chunked_refresh()

        # Test 3: Incremental Updates
        test_incremental_updates()

        # Test 4: Bandwidth Savings Analysis
        test_bandwidth_savings()

        logger.info("\n" + "=" * 60)
        logger.info("ALL TESTS COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

        # Offer to clear test cache
        logger.info("\nTest cache location: ~/.worldenergydata/test_cache")
        response = input("Clear test cache? (y/n): ")
        if response.lower() == "y":
            chunk_manager.clear_cache()
            logger.info("Test cache cleared")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
