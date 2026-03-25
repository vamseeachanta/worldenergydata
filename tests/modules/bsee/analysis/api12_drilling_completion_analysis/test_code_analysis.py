"""
Test module for code analysis functions in API12 drilling completion analysis.

This module tests the functionality for analyzing implementation logic
in both drilling_and_completion_days.py and well_api12.py scripts.
"""

import ast
import inspect
from pathlib import Path
from typing import Any, Dict, List

import pytest


class TestCodeAnalysis:
    """Test class for code analysis functionality."""

    @pytest.fixture
    def lease_script_path(self):
        """Path to the lease method script."""
        return "src/worldenergydata/modules/bsee/analysis/custom_scripts/Roy/july/drilling_and_completion_days.py"

    @pytest.fixture
    def api12_script_path(self):
        """Path to the API12 method script."""
        return "src/worldenergydata/modules/bsee/analysis/well_api12.py"

    def test_analyze_script_imports(self, lease_script_path, api12_script_path):
        """Test analysis of import statements in both scripts."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            analyze_script_imports,
        )

        # Analyze lease script imports
        lease_imports = analyze_script_imports(lease_script_path)
        assert isinstance(lease_imports, dict)
        assert "standard_libraries" in lease_imports
        assert "third_party_libraries" in lease_imports
        assert "local_modules" in lease_imports

        # Analyze API12 script imports
        api12_imports = analyze_script_imports(api12_script_path)
        assert isinstance(api12_imports, dict)
        assert "standard_libraries" in api12_imports
        assert "third_party_libraries" in api12_imports
        assert "local_modules" in api12_imports

        print("\nLease Script Imports:")
        for category, imports in lease_imports.items():
            print(f"  {category}: {imports}")

        print("\nAPI12 Script Imports:")
        for category, imports in api12_imports.items():
            print(f"  {category}: {imports}")

    def test_analyze_function_definitions(self, lease_script_path, api12_script_path):
        """Test analysis of function definitions in both scripts."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            analyze_function_definitions,
        )

        # Analyze lease script functions
        lease_functions = analyze_function_definitions(lease_script_path)
        assert isinstance(lease_functions, list)
        assert len(lease_functions) > 0

        # Each function should have name, args, and line numbers
        for func in lease_functions:
            assert "name" in func
            assert "args" in func
            assert "lineno" in func
            assert "docstring" in func

        # Analyze API12 script functions
        api12_functions = analyze_function_definitions(api12_script_path)
        assert isinstance(api12_functions, list)
        assert len(api12_functions) > 0

        print(f"\nLease Script Functions ({len(lease_functions)}):")
        for func in lease_functions:
            print(
                f"  {func['name']}({', '.join(func['args'])}) - Line {func['lineno']}"
            )

        print(f"\nAPI12 Script Functions ({len(api12_functions)}):")
        for func in api12_functions:
            print(
                f"  {func['name']}({', '.join(func['args'])}) - Line {func['lineno']}"
            )

    def test_analyze_data_sources(self, lease_script_path, api12_script_path):
        """Test analysis of data sources used by both scripts."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            analyze_data_sources,
        )

        # Analyze lease script data sources
        lease_sources = analyze_data_sources(lease_script_path)
        assert isinstance(lease_sources, dict)
        assert "database_queries" in lease_sources
        assert "file_operations" in lease_sources
        assert "api_calls" in lease_sources

        # Analyze API12 script data sources
        api12_sources = analyze_data_sources(api12_script_path)
        assert isinstance(api12_sources, dict)
        assert "database_queries" in api12_sources
        assert "file_operations" in api12_sources
        assert "api_calls" in api12_sources

        print("\nLease Script Data Sources:")
        for category, sources in lease_sources.items():
            if sources:
                print(f"  {category}: {sources}")

        print("\nAPI12 Script Data Sources:")
        for category, sources in api12_sources.items():
            if sources:
                print(f"  {category}: {sources}")

    def test_analyze_date_calculations(self, lease_script_path, api12_script_path):
        """Test analysis of date calculation methods in both scripts."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            analyze_date_calculations,
        )

        # Analyze lease script date calculations
        lease_dates = analyze_date_calculations(lease_script_path)
        assert isinstance(lease_dates, dict)
        assert "date_variables" in lease_dates
        assert "date_operations" in lease_dates
        assert "timedelta_operations" in lease_dates

        # Analyze API12 script date calculations
        api12_dates = analyze_date_calculations(api12_script_path)
        assert isinstance(api12_dates, dict)
        assert "date_variables" in api12_dates
        assert "date_operations" in api12_dates
        assert "timedelta_operations" in api12_dates

        print("\nLease Script Date Calculations:")
        for category, items in lease_dates.items():
            if items:
                print(f"  {category}: {items}")

        print("\nAPI12 Script Date Calculations:")
        for category, items in api12_dates.items():
            if items:
                print(f"  {category}: {items}")

    def test_analyze_drilling_completion_logic(
        self, lease_script_path, api12_script_path
    ):
        """Test analysis of drilling and completion day calculation logic."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            analyze_drilling_completion_logic,
        )

        # Analyze lease script drilling/completion logic
        lease_logic = analyze_drilling_completion_logic(lease_script_path)
        assert isinstance(lease_logic, dict)
        assert "drilling_calculations" in lease_logic
        assert "completion_calculations" in lease_logic
        assert "key_variables" in lease_logic

        # Analyze API12 script drilling/completion logic
        api12_logic = analyze_drilling_completion_logic(api12_script_path)
        assert isinstance(api12_logic, dict)
        assert "drilling_calculations" in api12_logic
        assert "completion_calculations" in api12_logic
        assert "key_variables" in api12_logic

        print("\nLease Script Drilling/Completion Logic:")
        for category, items in lease_logic.items():
            if items:
                print(f"  {category}: {items}")

        print("\nAPI12 Script Drilling/Completion Logic:")
        for category, items in api12_logic.items():
            if items:
                print(f"  {category}: {items}")

    def test_compare_methodologies(self, lease_script_path, api12_script_path):
        """Test comparison of methodologies between both scripts."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            compare_methodologies,
        )

        comparison = compare_methodologies(lease_script_path, api12_script_path)

        assert isinstance(comparison, dict)
        assert "data_source_differences" in comparison
        assert "calculation_method_differences" in comparison
        assert "common_approaches" in comparison
        assert "unique_to_lease" in comparison
        assert "unique_to_api12" in comparison

        print("\nMethodology Comparison:")
        for category, details in comparison.items():
            if details:
                print(f"  {category}: {details}")

    def test_extract_business_rules(self, lease_script_path, api12_script_path):
        """Test extraction of business rules from both scripts."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            extract_business_rules,
        )

        # Extract lease script business rules
        lease_rules = extract_business_rules(lease_script_path)
        assert isinstance(lease_rules, list)

        # Extract API12 script business rules
        api12_rules = extract_business_rules(api12_script_path)
        assert isinstance(api12_rules, list)

        print(f"\nLease Script Business Rules ({len(lease_rules)}):")
        for i, rule in enumerate(lease_rules, 1):
            print(f"  {i}. {rule}")

        print(f"\nAPI12 Script Business Rules ({len(api12_rules)}):")
        for i, rule in enumerate(api12_rules, 1):
            print(f"  {i}. {rule}")

    def test_analyze_script_complexity(self, lease_script_path, api12_script_path):
        """Test analysis of script complexity metrics."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            analyze_script_complexity,
        )

        # Analyze lease script complexity
        lease_complexity = analyze_script_complexity(lease_script_path)
        assert isinstance(lease_complexity, dict)
        assert "total_lines" in lease_complexity
        assert "function_count" in lease_complexity
        assert "class_count" in lease_complexity
        assert "import_count" in lease_complexity

        # Analyze API12 script complexity
        api12_complexity = analyze_script_complexity(api12_script_path)
        assert isinstance(api12_complexity, dict)
        assert "total_lines" in api12_complexity
        assert "function_count" in api12_complexity
        assert "class_count" in api12_complexity
        assert "import_count" in api12_complexity

        print("\nScript Complexity Analysis:")
        print("Lease Script:")
        for metric, value in lease_complexity.items():
            print(f"  {metric}: {value}")

        print("API12 Script:")
        for metric, value in api12_complexity.items():
            print(f"  {metric}: {value}")

    def test_identify_key_differences(self, lease_script_path, api12_script_path):
        """Test identification of key differences between the two approaches."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            identify_key_differences,
        )

        differences = identify_key_differences(lease_script_path, api12_script_path)

        assert isinstance(differences, dict)
        assert "data_processing_differences" in differences
        assert "calculation_differences" in differences
        assert "output_format_differences" in differences

        print("\nKey Differences Identified:")
        for category, details in differences.items():
            if details:
                print(f"  {category}:")
                if isinstance(details, list):
                    for item in details:
                        print(f"    - {item}")
                else:
                    print(f"    {details}")

    def test_generate_methodology_summary(self, lease_script_path, api12_script_path):
        """Test generation of comprehensive methodology summary."""
        from tests.modules.bsee.analysis.api12_drilling_completion_analysis.code_analyzer import (
            generate_methodology_summary,
        )

        summary = generate_methodology_summary(lease_script_path, api12_script_path)

        assert isinstance(summary, dict)
        assert "lease_method" in summary
        assert "api12_method" in summary
        assert "comparison" in summary

        # Each method should have detailed analysis
        for method_name in ["lease_method", "api12_method"]:
            method_data = summary[method_name]
            assert "script_path" in method_data
            assert "data_sources" in method_data
            assert "key_functions" in method_data
            assert "calculation_approach" in method_data

        print("\nMethodology Summary Generated:")
        print(
            f"Lease method functions: {len(summary['lease_method']['key_functions'])}"
        )
        print(
            f"API12 method functions: {len(summary['api12_method']['key_functions'])}"
        )
        print(f"Comparison categories: {list(summary['comparison'].keys())}")

        return summary
