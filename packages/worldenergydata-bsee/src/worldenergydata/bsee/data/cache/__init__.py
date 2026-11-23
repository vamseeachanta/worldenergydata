"""
Cache Management Module for BSEE Data

This module provides intelligent caching and change detection
for BSEE data downloads to minimize bandwidth usage.
"""

from .chunk_manager import ChunkManager, ChunkMetadata

__all__ = ["ChunkManager", "ChunkMetadata"]
