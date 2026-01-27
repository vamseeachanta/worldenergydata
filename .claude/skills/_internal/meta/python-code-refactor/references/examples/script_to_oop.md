# Example: Script to OOP Transformation

> Step-by-step transformation of procedural script into class-based architecture.

---

## Before: Procedural Script

A typical data processing script with global state, no structure, and hard-to-test code.

```python
# data_processor.py - BEFORE refactoring

import json
import requests
from datetime import datetime

# Global configuration
API_URL = "https://api.example.com/data"
API_KEY = "sk-12345"  # Hardcoded secret!
OUTPUT_DIR = "/tmp/reports"
MAX_RETRIES = 3

# Global state
processed_count = 0
error_count = 0
cache = {}

def fetch_data():
    """Fetch data from API."""
    global error_count

    headers = {"Authorization": f"Bearer {API_KEY}"}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(API_URL, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: Status {response.status_code}")
                error_count += 1
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            error_count += 1

    return None

def process_item(item):
    """Process a single item."""
    global processed_count, cache

    item_id = item.get("id")

    # Check cache
    if item_id in cache:
        return cache[item_id]

    # Complex processing logic
    result = {}
    if item.get("type") == "A":
        if item.get("value") > 100:
            if item.get("status") == "active":
                result["score"] = item["value"] * 1.5
                result["category"] = "premium"
            else:
                result["score"] = item["value"] * 1.2
                result["category"] = "standard"
        else:
            result["score"] = item["value"]
            result["category"] = "basic"
    elif item.get("type") == "B":
        result["score"] = item["value"] * 2
        result["category"] = "special"
    else:
        result["score"] = 0
        result["category"] = "unknown"

    result["processed_at"] = datetime.now().isoformat()
    cache[item_id] = result
    processed_count += 1

    return result

def generate_report(results):
    """Generate report from results."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_items": len(results),
        "processed_count": processed_count,
        "error_count": error_count,
        "items": results,
    }

    # Calculate statistics
    scores = [r["score"] for r in results if r.get("score")]
    if scores:
        report["avg_score"] = sum(scores) / len(scores)
        report["max_score"] = max(scores)
        report["min_score"] = min(scores)

    return report

def save_report(report):
    """Save report to file."""
    filename = f"{OUTPUT_DIR}/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {filename}")
    return filename

def main():
    """Main entry point."""
    print("Starting data processing...")

    # Fetch data
    data = fetch_data()
    if not data:
        print("Failed to fetch data!")
        return

    # Process items
    results = []
    for item in data.get("items", []):
        try:
            result = process_item(item)
            results.append(result)
        except Exception as e:
            print(f"Error processing item: {e}")
            global error_count
            error_count += 1

    # Generate and save report
    report = generate_report(results)
    save_report(report)

    print(f"Done! Processed: {processed_count}, Errors: {error_count}")

if __name__ == "__main__":
    main()
```

### Problems with This Code

| Issue | Description |
|-------|-------------|
| Global state | `processed_count`, `error_count`, `cache` are global |
| Hardcoded secrets | API key in source code |
| Untestable | Can't test functions in isolation |
| Complex nesting | `process_item` has deep nesting |
| Mixed concerns | Fetching, processing, reporting all mixed |
| No error handling | Errors silently caught and counted |
| No type hints | Unclear what data types are expected |

---

## After: Class-Based Architecture

Transformed into a clean, testable, maintainable structure.

### Project Structure

```
src/
  data_processor/
    __init__.py
    config.py         # Configuration management
    models.py         # Data models
    client.py         # API client
    processor.py      # Processing logic
    reporter.py       # Report generation
    cache.py          # Caching
    main.py           # Entry point
```

### Step 1: Define Data Models

```python
# src/data_processor/models.py
"""Data models for the data processor."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class ItemType(Enum):
    """Valid item types."""
    TYPE_A = "A"
    TYPE_B = "B"
    UNKNOWN = "unknown"

class ItemCategory(Enum):
    """Result categories."""
    PREMIUM = "premium"
    STANDARD = "standard"
    BASIC = "basic"
    SPECIAL = "special"
    UNKNOWN = "unknown"

@dataclass
class Item:
    """Input item from API."""
    id: str
    type: str
    value: float
    status: str = "active"

    @property
    def item_type(self) -> ItemType:
        """Get typed item type."""
        try:
            return ItemType(self.type)
        except ValueError:
            return ItemType.UNKNOWN

    @property
    def is_active(self) -> bool:
        """Check if item is active."""
        return self.status == "active"

@dataclass
class ProcessedItem:
    """Result of processing an item."""
    item_id: str
    score: float
    category: ItemCategory
    processed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "item_id": self.item_id,
            "score": self.score,
            "category": self.category.value,
            "processed_at": self.processed_at.isoformat(),
        }

@dataclass
class ProcessingStats:
    """Statistics from processing."""
    processed_count: int = 0
    error_count: int = 0
    cache_hits: int = 0

    def record_success(self) -> None:
        """Record successful processing."""
        self.processed_count += 1

    def record_error(self) -> None:
        """Record processing error."""
        self.error_count += 1

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        self.cache_hits += 1

@dataclass
class Report:
    """Processing report."""
    generated_at: datetime
    total_items: int
    stats: ProcessingStats
    items: list[ProcessedItem]
    avg_score: Optional[float] = None
    max_score: Optional[float] = None
    min_score: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "total_items": self.total_items,
            "processed_count": self.stats.processed_count,
            "error_count": self.stats.error_count,
            "cache_hits": self.stats.cache_hits,
            "avg_score": self.avg_score,
            "max_score": self.max_score,
            "min_score": self.min_score,
            "items": [item.to_dict() for item in self.items],
        }
```

### Step 2: Configuration Management

```python
# src/data_processor/config.py
"""Configuration management."""

import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Config:
    """Application configuration."""
    api_url: str
    api_key: str
    output_dir: Path
    max_retries: int = 3
    request_timeout: int = 30

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        api_key = os.environ.get("API_KEY")
        if not api_key:
            raise ValueError("API_KEY environment variable is required")

        return cls(
            api_url=os.environ.get("API_URL", "https://api.example.com/data"),
            api_key=api_key,
            output_dir=Path(os.environ.get("OUTPUT_DIR", "/tmp/reports")),
            max_retries=int(os.environ.get("MAX_RETRIES", "3")),
            request_timeout=int(os.environ.get("REQUEST_TIMEOUT", "30")),
        )
```

### Step 3: API Client with Dependency Injection

```python
# src/data_processor/client.py
"""API client for fetching data."""

import logging
from typing import Protocol

import requests

from .config import Config
from .models import Item

logger = logging.getLogger(__name__)

class HTTPClient(Protocol):
    """Protocol for HTTP client."""

    def get(self, url: str, headers: dict, timeout: int) -> requests.Response:
        """Perform GET request."""
        ...

class RequestsClient:
    """Production HTTP client using requests library."""

    def get(self, url: str, headers: dict, timeout: int) -> requests.Response:
        """Perform GET request."""
        return requests.get(url, headers=headers, timeout=timeout)

class DataAPIClient:
    """Client for fetching data from the API."""

    def __init__(self, config: Config, http_client: HTTPClient | None = None):
        """Initialize client with configuration.

        Args:
            config: Application configuration.
            http_client: HTTP client for making requests. Defaults to RequestsClient.
        """
        self._config = config
        self._http = http_client or RequestsClient()

    def fetch_items(self) -> list[Item]:
        """Fetch items from the API.

        Returns:
            List of items from the API.

        Raises:
            APIError: If unable to fetch data after retries.
        """
        headers = {"Authorization": f"Bearer {self._config.api_key}"}

        last_error: Exception | None = None
        for attempt in range(1, self._config.max_retries + 1):
            try:
                response = self._http.get(
                    self._config.api_url,
                    headers=headers,
                    timeout=self._config.request_timeout,
                )

                if response.status_code == 200:
                    return self._parse_response(response.json())

                logger.warning(
                    "API returned status %d on attempt %d",
                    response.status_code,
                    attempt,
                )
                last_error = APIError(f"Status {response.status_code}")

            except requests.RequestException as e:
                logger.warning("Request failed on attempt %d: %s", attempt, e)
                last_error = e

        raise APIError(f"Failed after {self._config.max_retries} attempts") from last_error

    def _parse_response(self, data: dict) -> list[Item]:
        """Parse API response into Item objects."""
        return [
            Item(
                id=item["id"],
                type=item.get("type", "unknown"),
                value=float(item.get("value", 0)),
                status=item.get("status", "active"),
            )
            for item in data.get("items", [])
        ]

class APIError(Exception):
    """Error fetching data from API."""
    pass
```

### Step 4: Processing Logic with Strategy Pattern

```python
# src/data_processor/processor.py
"""Item processing logic."""

from abc import ABC, abstractmethod
from datetime import datetime

from .cache import Cache
from .models import Item, ItemCategory, ItemType, ProcessedItem, ProcessingStats

class ScoringStrategy(ABC):
    """Abstract base for scoring strategies."""

    @abstractmethod
    def calculate_score(self, item: Item) -> float:
        """Calculate score for an item."""
        pass

    @abstractmethod
    def determine_category(self, item: Item) -> ItemCategory:
        """Determine category for an item."""
        pass

class TypeAScoringStrategy(ScoringStrategy):
    """Scoring strategy for Type A items."""

    HIGH_VALUE_THRESHOLD = 100
    PREMIUM_MULTIPLIER = 1.5
    STANDARD_MULTIPLIER = 1.2

    def calculate_score(self, item: Item) -> float:
        """Calculate score based on value and status."""
        if item.value > self.HIGH_VALUE_THRESHOLD:
            multiplier = self.PREMIUM_MULTIPLIER if item.is_active else self.STANDARD_MULTIPLIER
            return item.value * multiplier
        return item.value

    def determine_category(self, item: Item) -> ItemCategory:
        """Determine category based on value and status."""
        if item.value > self.HIGH_VALUE_THRESHOLD:
            return ItemCategory.PREMIUM if item.is_active else ItemCategory.STANDARD
        return ItemCategory.BASIC

class TypeBScoringStrategy(ScoringStrategy):
    """Scoring strategy for Type B items."""

    MULTIPLIER = 2.0

    def calculate_score(self, item: Item) -> float:
        """Type B items get doubled score."""
        return item.value * self.MULTIPLIER

    def determine_category(self, item: Item) -> ItemCategory:
        """Type B items are always special."""
        return ItemCategory.SPECIAL

class DefaultScoringStrategy(ScoringStrategy):
    """Default scoring for unknown types."""

    def calculate_score(self, item: Item) -> float:
        """Unknown types get zero score."""
        return 0.0

    def determine_category(self, item: Item) -> ItemCategory:
        """Unknown types get unknown category."""
        return ItemCategory.UNKNOWN

class ItemProcessor:
    """Processes items using appropriate strategies."""

    def __init__(self, cache: Cache | None = None):
        """Initialize processor with optional cache.

        Args:
            cache: Optional cache for processed items.
        """
        self._cache = cache
        self._stats = ProcessingStats()
        self._strategies: dict[ItemType, ScoringStrategy] = {
            ItemType.TYPE_A: TypeAScoringStrategy(),
            ItemType.TYPE_B: TypeBScoringStrategy(),
            ItemType.UNKNOWN: DefaultScoringStrategy(),
        }

    @property
    def stats(self) -> ProcessingStats:
        """Get processing statistics."""
        return self._stats

    def process(self, item: Item) -> ProcessedItem:
        """Process a single item.

        Args:
            item: Item to process.

        Returns:
            Processed item with score and category.
        """
        # Check cache first
        if self._cache:
            cached = self._cache.get(item.id)
            if cached:
                self._stats.record_cache_hit()
                return cached

        # Get strategy for item type
        strategy = self._strategies.get(item.item_type, self._strategies[ItemType.UNKNOWN])

        # Process item
        result = ProcessedItem(
            item_id=item.id,
            score=strategy.calculate_score(item),
            category=strategy.determine_category(item),
            processed_at=datetime.now(),
        )

        # Cache result
        if self._cache:
            self._cache.set(item.id, result)

        self._stats.record_success()
        return result

    def process_batch(self, items: list[Item]) -> list[ProcessedItem]:
        """Process a batch of items.

        Args:
            items: List of items to process.

        Returns:
            List of processed items (errors are skipped).
        """
        results: list[ProcessedItem] = []

        for item in items:
            try:
                result = self.process(item)
                results.append(result)
            except Exception as e:
                self._stats.record_error()
                # Log but continue processing

        return results
```

### Step 5: Cache Implementation

```python
# src/data_processor/cache.py
"""Caching for processed items."""

from typing import Protocol

from .models import ProcessedItem

class Cache(Protocol):
    """Protocol for cache implementations."""

    def get(self, key: str) -> ProcessedItem | None:
        """Get item from cache."""
        ...

    def set(self, key: str, value: ProcessedItem) -> None:
        """Set item in cache."""
        ...

class InMemoryCache:
    """Simple in-memory cache."""

    def __init__(self):
        """Initialize empty cache."""
        self._store: dict[str, ProcessedItem] = {}

    def get(self, key: str) -> ProcessedItem | None:
        """Get item from cache."""
        return self._store.get(key)

    def set(self, key: str, value: ProcessedItem) -> None:
        """Set item in cache."""
        self._store[key] = value

    def clear(self) -> None:
        """Clear all cached items."""
        self._store.clear()
```

### Step 6: Report Generation

```python
# src/data_processor/reporter.py
"""Report generation and saving."""

import json
from datetime import datetime
from pathlib import Path

from .models import ProcessedItem, ProcessingStats, Report

class ReportGenerator:
    """Generates reports from processed items."""

    def generate(
        self,
        items: list[ProcessedItem],
        stats: ProcessingStats,
    ) -> Report:
        """Generate report from processed items.

        Args:
            items: List of processed items.
            stats: Processing statistics.

        Returns:
            Generated report.
        """
        scores = [item.score for item in items if item.score > 0]

        return Report(
            generated_at=datetime.now(),
            total_items=len(items),
            stats=stats,
            items=items,
            avg_score=sum(scores) / len(scores) if scores else None,
            max_score=max(scores) if scores else None,
            min_score=min(scores) if scores else None,
        )

class ReportSaver:
    """Saves reports to files."""

    def __init__(self, output_dir: Path):
        """Initialize with output directory.

        Args:
            output_dir: Directory to save reports.
        """
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, report: Report) -> Path:
        """Save report to JSON file.

        Args:
            report: Report to save.

        Returns:
            Path to saved file.
        """
        filename = f"report_{report.generated_at.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self._output_dir / filename

        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        return filepath
```

### Step 7: Main Application

```python
# src/data_processor/main.py
"""Main application entry point."""

import logging
import sys

from .cache import InMemoryCache
from .client import APIError, DataAPIClient
from .config import Config
from .processor import ItemProcessor
from .reporter import ReportGenerator, ReportSaver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class DataProcessorApp:
    """Main application orchestrating the data processing pipeline."""

    def __init__(
        self,
        client: DataAPIClient,
        processor: ItemProcessor,
        report_generator: ReportGenerator,
        report_saver: ReportSaver,
    ):
        """Initialize application with dependencies.

        Args:
            client: API client for fetching data.
            processor: Item processor.
            report_generator: Report generator.
            report_saver: Report saver.
        """
        self._client = client
        self._processor = processor
        self._report_generator = report_generator
        self._report_saver = report_saver

    def run(self) -> int:
        """Run the data processing pipeline.

        Returns:
            Exit code (0 for success, 1 for failure).
        """
        logger.info("Starting data processing...")

        try:
            # Fetch data
            items = self._client.fetch_items()
            logger.info("Fetched %d items", len(items))

            # Process items
            results = self._processor.process_batch(items)
            logger.info(
                "Processed %d items (errors: %d)",
                self._processor.stats.processed_count,
                self._processor.stats.error_count,
            )

            # Generate and save report
            report = self._report_generator.generate(results, self._processor.stats)
            filepath = self._report_saver.save(report)
            logger.info("Report saved to %s", filepath)

            return 0

        except APIError as e:
            logger.error("Failed to fetch data: %s", e)
            return 1

def create_app(config: Config) -> DataProcessorApp:
    """Create application with dependencies.

    Args:
        config: Application configuration.

    Returns:
        Configured application instance.
    """
    cache = InMemoryCache()
    return DataProcessorApp(
        client=DataAPIClient(config),
        processor=ItemProcessor(cache),
        report_generator=ReportGenerator(),
        report_saver=ReportSaver(config.output_dir),
    )

def main() -> int:
    """Entry point for command line."""
    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        return 1

    app = create_app(config)
    return app.run()

if __name__ == "__main__":
    sys.exit(main())
```

---

## Key Transformations Summary

| Before | After |
|--------|-------|
| Global variables | Encapsulated in classes |
| Hardcoded secrets | Environment variables |
| Single script | Modular package |
| No types | Full type hints |
| Nested conditionals | Strategy pattern |
| Mixed concerns | Single responsibility |
| Untestable | Dependency injection |
| Procedural flow | Object-oriented design |

---

## Testing the Refactored Code

```python
# tests/test_processor.py
"""Tests for ItemProcessor."""

import pytest
from datetime import datetime

from src.data_processor.models import Item, ItemCategory
from src.data_processor.processor import ItemProcessor
from src.data_processor.cache import InMemoryCache

class TestItemProcessor:
    """Tests for ItemProcessor."""

    def test_process_type_a_high_value_active(self):
        """Type A high value active items get premium score."""
        processor = ItemProcessor()
        item = Item(id="1", type="A", value=150, status="active")

        result = processor.process(item)

        assert result.score == 150 * 1.5  # Premium multiplier
        assert result.category == ItemCategory.PREMIUM

    def test_process_type_a_high_value_inactive(self):
        """Type A high value inactive items get standard score."""
        processor = ItemProcessor()
        item = Item(id="1", type="A", value=150, status="inactive")

        result = processor.process(item)

        assert result.score == 150 * 1.2  # Standard multiplier
        assert result.category == ItemCategory.STANDARD

    def test_process_type_b(self):
        """Type B items get special category."""
        processor = ItemProcessor()
        item = Item(id="1", type="B", value=100)

        result = processor.process(item)

        assert result.score == 200  # Doubled
        assert result.category == ItemCategory.SPECIAL

    def test_cache_hit(self):
        """Cached items are returned without reprocessing."""
        cache = InMemoryCache()
        processor = ItemProcessor(cache)
        item = Item(id="1", type="A", value=100)

        # First call - processes and caches
        result1 = processor.process(item)
        assert processor.stats.processed_count == 1
        assert processor.stats.cache_hits == 0

        # Second call - returns from cache
        result2 = processor.process(item)
        assert processor.stats.processed_count == 1  # Not incremented
        assert processor.stats.cache_hits == 1
        assert result1.score == result2.score
```
