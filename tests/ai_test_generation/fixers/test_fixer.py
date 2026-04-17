"""
AI Test Fixer - Automatically fixes common issues in AI-generated tests
"""

import ast
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class AITestFixer:
    """Fixes common issues in AI-generated test files."""

    def __init__(self):
        self.fixes_applied = []
        self.modules_cache = {}

    def fix_test_file(self, file_path: Path) -> bool:
        """
        Fix a single test file.

        Args:
            file_path: Path to the test file

        Returns:
            True if fixes were applied and file saved
        """
        try:
            # Convert to absolute path to avoid issues
            file_path = Path(file_path).resolve()
            logger.info(f"Fixing: {file_path.name}")

            # Read the file
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Apply fixes in order
            content = self._fix_direct_function_calls(content, file_path)
            content = self._fix_setup_method(content)
            content = self._fix_assert_statements(content)
            content = self._fix_imports(content, file_path)
            content = self._fix_test_markers(content)
            content = self._fix_parameterized_tests(content)

            # Only write if changes were made
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"  ✓ Fixed {file_path.name}")
                return True
            else:
                logger.info(f"  - No fixes needed for {file_path.name}")
                return False

        except Exception as e:
            logger.error(f"  ✗ Error fixing {file_path.name}: {str(e)}")
            return False

    def _fix_direct_function_calls(self, content: str, file_path: Path) -> str:
        """Fix direct function calls like __init__() and router()."""

        # Extract the module being tested from imports
        module_match = re.search(
            r"from worldenergydata\.(.+?) import (.+?)$", content, re.MULTILINE
        )
        if not module_match:
            return content

        module_path = module_match.group(1)
        imported_items = module_match.group(2)

        # Parse imported items (could be class or functions)
        imported_list = [item.strip() for item in imported_items.split(",")]

        # Fix __init__ calls
        if "__init__" in content:
            # These are usually class constructors, fix them
            for item in imported_list:
                if item and item[0].isupper():  # Likely a class
                    content = re.sub(
                        r"result = __init__\(\)",
                        f"instance = {item}()\n        # instance initialized",
                        content,
                    )
                    content = re.sub(
                        r"result = __init__\((.+?)\)",
                        f"instance = {item}(\\1)\n        # instance initialized",
                        content,
                    )

        # Fix standalone function calls (without self.)
        # Look for patterns like "result = function_name("
        for func_match in re.finditer(r"result = ([a-z_][a-zA-Z0-9_]*)\(", content):
            func_name = func_match.group(1)

            # Skip if it's a known built-in or already has self.
            if func_name in [
                "len",
                "str",
                "int",
                "float",
                "list",
                "dict",
                "tuple",
                "print",
                "open",
                "range",
                "enumerate",
            ]:
                continue

            # Check if this function should be a method call
            if (
                f"def test_{func_name}" in content
                or f"def test__{func_name}" in content
            ):
                # This is likely a module-level function that needs to be imported
                if func_name not in imported_items:
                    # Add to imports if it's being tested but not imported
                    old_import = (
                        f"from worldenergydata.{module_path} import {imported_items}"
                    )
                    new_import = f"from worldenergydata.{module_path} import {imported_items}, {func_name}"
                    content = content.replace(old_import, new_import, 1)

        return content

    def _fix_setup_method(self, content: str) -> str:
        """Fix setup method to follow pytest conventions."""

        # Change setup to setup_method for class-based tests
        content = re.sub(
            r"def setup\(self, tmp_path\):",
            "def setup_method(self, method, tmp_path):",
            content,
        )

        # If setup doesn't use tmp_path, make it simpler
        content = re.sub(
            r"def setup\(self\):", "def setup_method(self, method):", content
        )

        # Fix the fixture usage
        content = re.sub(
            r"@pytest\.fixture\(autouse=True\)\s*\n\s*def setup_method",
            "def setup_method",
            content,
        )

        return content

    def _fix_assert_statements(self, content: str) -> str:
        """Fix assertion statements to use pytest style."""

        # Fix self.assertIsNotNone -> assert ... is not None
        content = re.sub(
            r"self\.assertIsNotNone\((.+?)\)", r"assert \1 is not None", content
        )

        # Fix self.assertIsNone -> assert ... is None
        content = re.sub(r"self\.assertIsNone\((.+?)\)", r"assert \1 is None", content)

        # Fix self.assertEqual -> assert ... ==
        content = re.sub(
            r"self\.assertEqual\((.+?),\s*(.+?)\)", r"assert \1 == \2", content
        )

        # Fix self.assertIsInstance
        content = re.sub(
            r"self\.assertIsInstance\((.+?),\s*(.+?)\)",
            r"assert isinstance(\1, \2)",
            content,
        )

        # Fix self.assertTrue
        content = re.sub(r"self\.assertTrue\((.+?)\)", r"assert \1", content)

        # Fix self.assertFalse
        content = re.sub(r"self\.assertFalse\((.+?)\)", r"assert not \1", content)

        return content

    def _fix_imports(self, content: str, file_path: Path) -> str:
        """Fix import statements and add missing imports."""

        # Ensure tests.test_markers exists or use pytest markers directly
        if "from tests.test_markers import" in content:
            content = content.replace(
                "from tests.test_markers import integration", "import pytest"
            )
            content = content.replace("@integration", "@pytest.mark.integration")
            content = content.replace(
                "from tests.test_markers import unit", "import pytest"
            )
            content = content.replace("@unit", "@pytest.mark.unit")

        # Fix the path insertion - should be parent.parent.parent for most test files
        if "sys.path.insert" in content:
            # For Windows, just use a simpler approach
            # The test files are in tests/ai_generated/[unit|integration]/
            # So we need to go up 3 levels to get to project root
            content = re.sub(
                r'sys\.path\.insert\(0, str\(Path\(__file__\)\.parent\.parent\.parent / "src"\)\)',
                "sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))",
                content,
            )

        return content

    def _fix_test_markers(self, content: str) -> str:
        """Fix test markers and class decorators."""

        # If using class-based tests, ensure pytest compatibility
        if "@integration" in content or "@unit" in content:
            if "import pytest" not in content:
                # Add pytest import at the top
                import_section = re.search(r"(import .+?\n)+", content)
                if import_section:
                    end_pos = import_section.end()
                    content = content[:end_pos] + "import pytest\n" + content[end_pos:]

        return content

    def _fix_parameterized_tests(self, content: str) -> str:
        """Fix parameterized test issues."""

        # Fix parameterized tests that don't match the actual function signature
        # Find all parameterized test methods
        param_tests = re.findall(
            r'@pytest\.mark\.parametrize\("(.+?)",\s*\[(.+?)\]\).*?\n.*?def (test_\w+)\(self,\s*(.+?)\):',
            content,
            re.DOTALL,
        )

        for params, values, test_name, test_args in param_tests:
            # Check if the parameters match the arguments
            param_list = [p.strip() for p in params.split(",")]
            arg_list = [a.strip() for a in test_args.split(",")]

            # If only using input_data but function expects more, fix it
            if len(param_list) < len(arg_list):
                # The test is expecting more parameters than provided
                # This often happens when the test wrongly expects the original function params
                # Fix by adjusting the test method arguments
                old_pattern = f"def {test_name}\\(self, {test_args}\\):"
                new_pattern = f"def {test_name}(self, {params}):"
                content = content.replace(old_pattern, new_pattern)

        return content

    def fix_all_tests(self, test_dir: Path) -> Dict[str, Any]:
        """
        Fix all test files in a directory.

        Args:
            test_dir: Directory containing test files

        Returns:
            Dictionary with fix statistics
        """
        stats = {
            "total_files": 0,
            "fixed_files": 0,
            "failed_files": 0,
            "files_fixed": [],
            "files_failed": [],
        }

        # Find all test files
        test_files = list(test_dir.glob("**/test_*.py"))
        stats["total_files"] = len(test_files)

        logger.info(f"\n{'='*60}")
        logger.info(f"AI TEST FIXER")
        logger.info(f"{'='*60}")
        logger.info(f"Found {len(test_files)} test files to check\n")

        for test_file in test_files:
            if self.fix_test_file(test_file):
                stats["fixed_files"] += 1
                stats["files_fixed"].append(test_file.name)
            else:
                # Check if it actually failed or just didn't need fixes
                try:
                    with open(test_file, "r") as f:
                        # If we can read it, it didn't fail, just didn't need fixes
                        pass
                except:
                    stats["failed_files"] += 1
                    stats["files_failed"].append(test_file.name)

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Files: {stats['total_files']}")
        logger.info(f"Files Fixed: {stats['fixed_files']}")
        logger.info(f"Files Failed: {stats['failed_files']}")
        logger.info(
            f"No Changes Needed: {stats['total_files'] - stats['fixed_files'] - stats['failed_files']}"
        )

        return stats


def main():
    """Main function to fix AI-generated tests."""

    # Define directories to fix
    dirs_to_fix = [
        Path("tests/ai_generated/unit"),
        Path("tests/ai_generated/integration"),
    ]

    fixer = AITestFixer()
    all_stats = {}

    for test_dir in dirs_to_fix:
        if test_dir.exists():
            logger.info(f"\nProcessing {test_dir}...")
            stats = fixer.fix_all_tests(test_dir)
            all_stats[str(test_dir)] = stats
        else:
            logger.warning(f"Directory not found: {test_dir}")

    # Overall summary
    logger.info(f"\n{'='*60}")
    logger.info(f"OVERALL RESULTS")
    logger.info(f"{'='*60}")

    total_fixed = sum(s["fixed_files"] for s in all_stats.values())
    total_files = sum(s["total_files"] for s in all_stats.values())

    logger.info(f"Total files processed: {total_files}")
    logger.info(f"Total files fixed: {total_fixed}")
    logger.info(
        f"Success rate: {(total_fixed/total_files*100):.1f}%"
        if total_files > 0
        else "N/A"
    )

    return all_stats


if __name__ == "__main__":
    main()
