"""
Unit tests for simple modules without complex dependencies.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, "src")


class TestSimpleModules:
    """Test simple modules that don't require domain knowledge."""

    def test_data_file_discovery(self):
        """Test finding data files in directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test files
            (tmpdir / "data1.csv").touch()
            (tmpdir / "data2.xlsx").touch()
            (tmpdir / "readme.txt").touch()
            (tmpdir / "subdir").mkdir()
            (tmpdir / "subdir" / "data3.csv").touch()

            # Find CSV files
            csv_files = list(tmpdir.glob("**/*.csv"))
            assert len(csv_files) == 2

            # Find Excel files
            excel_files = list(tmpdir.glob("**/*.xlsx"))
            assert len(excel_files) == 1

            # Find all data files
            data_extensions = [".csv", ".xlsx", ".parquet"]
            data_files = []
            for ext in data_extensions:
                data_files.extend(tmpdir.glob(f"**/*{ext}"))
            assert len(data_files) == 3

    def test_dataframe_operations(self):
        """Test basic pandas DataFrame operations."""
        # Create sample dataframe
        df = pd.DataFrame(
            {
                "A": [1, 2, 3, 4, 5],
                "B": [10, 20, 30, 40, 50],
                "C": ["a", "b", "c", "d", "e"],
            }
        )

        # Test shape
        assert df.shape == (5, 3)

        # Test column operations
        assert list(df.columns) == ["A", "B", "C"]
        assert df["A"].sum() == 15
        assert df["B"].mean() == 30

        # Test filtering
        filtered = df[df["A"] > 2]
        assert len(filtered) == 3

        # Test grouping
        df["Group"] = ["X", "X", "Y", "Y", "X"]
        grouped = df.groupby("Group")["B"].sum()
        assert grouped["X"] == 80
        assert grouped["Y"] == 70

    def test_configuration_handling(self):
        """Test configuration dictionary handling."""
        config = {
            "database": {"host": "localhost", "port": 5432, "name": "test_db"},
            "processing": {"batch_size": 1000, "parallel": True},
        }

        # Test nested access
        assert config["database"]["host"] == "localhost"
        assert config["processing"]["batch_size"] == 1000

        # Test get with default
        assert config.get("missing", "default") == "default"
        assert config["database"].get("user", "admin") == "admin"

        # Test update
        config["processing"]["batch_size"] = 2000
        assert config["processing"]["batch_size"] == 2000

    def test_string_manipulation(self):
        """Test string manipulation utilities."""
        # Test case conversion
        assert "Hello World".upper() == "HELLO WORLD"
        assert "Hello World".lower() == "hello world"

        # Test splitting and joining
        parts = "one,two,three".split(",")
        assert len(parts) == 3
        assert "-".join(parts) == "one-two-three"

        # Test stripping
        assert "  hello  ".strip() == "hello"
        assert "hello\n".rstrip() == "hello"

        # Test replacement
        assert "hello world".replace("world", "python") == "hello python"

    def test_list_operations(self):
        """Test list manipulation operations."""
        # Test list creation and access
        lst = [1, 2, 3, 4, 5]
        assert lst[0] == 1
        assert lst[-1] == 5
        assert lst[1:3] == [2, 3]

        # Test list modification
        lst.append(6)
        assert len(lst) == 6

        lst.extend([7, 8])
        assert len(lst) == 8

        lst.remove(1)
        assert 1 not in lst

        # Test list comprehension
        squared = [x**2 for x in range(5)]
        assert squared == [0, 1, 4, 9, 16]

    def test_dictionary_operations(self):
        """Test dictionary manipulation operations."""
        # Test creation and access
        d = {"a": 1, "b": 2, "c": 3}
        assert d["a"] == 1
        assert len(d) == 3

        # Test modification
        d["d"] = 4
        assert len(d) == 4

        del d["a"]
        assert "a" not in d

        # Test iteration
        keys = list(d.keys())
        values = list(d.values())
        assert "b" in keys
        assert 2 in values

        # Test dictionary comprehension
        squared = {k: v**2 for k, v in d.items()}
        assert squared["b"] == 4

    def test_file_operations(self):
        """Test file read/write operations."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)
            f.write("test content\nline 2\nline 3")

        # Test file reading
        with open(temp_path, "r") as f:
            content = f.read()
            assert "test content" in content

        with open(temp_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == 3

        # Test file writing
        with open(temp_path, "a") as f:
            f.write("\nline 4")

        with open(temp_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == 4

        # Clean up
        temp_path.unlink()

    def test_exception_handling(self):
        """Test exception handling patterns."""

        # Test basic try-except
        def divide(a, b):
            try:
                return a / b
            except ZeroDivisionError:
                return None

        assert divide(10, 2) == 5
        assert divide(10, 0) is None

        # Test raising exceptions
        def validate_positive(n):
            if n < 0:
                raise ValueError("Number must be positive")
            return n

        assert validate_positive(5) == 5

        with pytest.raises(ValueError):
            validate_positive(-5)

    def test_data_aggregation(self):
        """Test data aggregation operations."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        # Test basic aggregations
        assert sum(data) == 55
        assert len(data) == 10
        assert min(data) == 1
        assert max(data) == 10

        # Test average
        avg = sum(data) / len(data)
        assert avg == 5.5

        # Test filtering and aggregation
        evens = [x for x in data if x % 2 == 0]
        assert sum(evens) == 30
        assert len(evens) == 5

    def test_date_operations(self):
        """Test date manipulation operations."""
        from datetime import datetime, timedelta

        # Test date creation
        dt = datetime(2023, 1, 15)
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 15

        # Test date arithmetic
        tomorrow = dt + timedelta(days=1)
        assert tomorrow.day == 16

        next_month = dt + timedelta(days=30)
        assert next_month.month == 2

        # Test date formatting
        date_str = dt.strftime("%Y-%m-%d")
        assert date_str == "2023-01-15"

        # Test date parsing
        parsed = datetime.strptime("2023-01-15", "%Y-%m-%d")
        assert parsed == dt

    def test_sorting_operations(self):
        """Test sorting operations."""
        # Test list sorting
        lst = [3, 1, 4, 1, 5, 9, 2, 6]
        sorted_lst = sorted(lst)
        assert sorted_lst == [1, 1, 2, 3, 4, 5, 6, 9]

        # Test reverse sorting
        reverse_sorted = sorted(lst, reverse=True)
        assert reverse_sorted == [9, 6, 5, 4, 3, 2, 1, 1]

        # Test sorting with key
        words = ["apple", "pie", "zoo", "elephant"]
        by_length = sorted(words, key=len)
        assert by_length == ["pie", "zoo", "apple", "elephant"]

        # Test sorting dictionaries
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
            {"name": "Charlie", "age": 35},
        ]
        by_age = sorted(data, key=lambda x: x["age"])
        assert by_age[0]["name"] == "Bob"
        assert by_age[-1]["name"] == "Charlie"
