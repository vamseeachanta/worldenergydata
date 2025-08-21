"""
Test suite analyzer for identifying cleanup opportunities.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import hashlib
import re


class TestAnalyzer:
    """Analyze test suite for cleanup opportunities."""
    
    def __init__(self, test_dir: Path):
        """
        Initialize test analyzer.
        
        Args:
            test_dir: Root directory of test suite
        """
        self.test_dir = Path(test_dir)
        self.test_files: List[Path] = []
        self.test_methods: Dict[str, List[str]] = {}
        self.duplicate_tests: List[Tuple[str, str]] = []
        self.obsolete_tests: List[str] = []
        self.redundant_tests: List[str] = []
        
    def analyze(self) -> Dict:
        """
        Perform comprehensive test analysis.
        
        Returns:
            Dictionary with analysis results
        """
        # Find all test files
        self.test_files = list(self.test_dir.rglob("test_*.py"))
        
        # Analyze each file
        for test_file in self.test_files:
            self._analyze_file(test_file)
        
        # Find duplicates
        self._find_duplicate_tests()
        
        # Find obsolete tests
        self._find_obsolete_tests()
        
        # Find redundant tests
        self._find_redundant_tests()
        
        return self._generate_report()
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single test file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Extract test methods
            test_methods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('test_'):
                        test_methods.append(node.name)
            
            self.test_methods[str(file_path)] = test_methods
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _find_duplicate_tests(self):
        """Find duplicate test implementations."""
        test_signatures = {}
        
        for file_path in self.test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        # Generate signature hash
                        body_dump = ast.dump(node)
                        # Remove names to find structural duplicates
                        body_normalized = re.sub(r'name=\'[^\']+\'', 'name=\'\'', body_dump)
                        signature = hashlib.md5(body_normalized.encode()).hexdigest()
                        
                        test_id = f"{file_path}::{node.name}"
                        
                        if signature in test_signatures:
                            self.duplicate_tests.append((test_signatures[signature], test_id))
                        else:
                            test_signatures[signature] = test_id
                            
            except Exception as e:
                print(f"Error finding duplicates in {file_path}: {e}")
    
    def _find_obsolete_tests(self):
        """Find tests for deprecated or removed features."""
        obsolete_patterns = [
            r'test_.*_deprecated',
            r'test_.*_legacy',
            r'test_.*_old',
            r'test_.*_v1',  # Old version tests
            r'test_.*_temp',
            r'test_.*_todo',
            r'test_.*_fixme',
        ]
        
        for file_path, methods in self.test_methods.items():
            for method in methods:
                for pattern in obsolete_patterns:
                    if re.match(pattern, method, re.IGNORECASE):
                        self.obsolete_tests.append(f"{file_path}::{method}")
                        break
    
    def _find_redundant_tests(self):
        """Find tests that test the same functionality."""
        # Group tests by similar names
        test_groups = defaultdict(list)
        
        for file_path, methods in self.test_methods.items():
            for method in methods:
                # Extract core test name
                core_name = re.sub(r'test_(.+?)(_\d+|_variant.*|_case.*|_version.*)?$', r'\1', method)
                test_groups[core_name].append(f"{file_path}::{method}")
        
        # Find groups with multiple similar tests
        for core_name, tests in test_groups.items():
            if len(tests) > 3:  # More than 3 similar tests might be redundant
                self.redundant_tests.extend(tests)
    
    def _generate_report(self) -> Dict:
        """Generate analysis report."""
        total_tests = sum(len(methods) for methods in self.test_methods.values())
        
        return {
            'summary': {
                'total_files': len(self.test_files),
                'total_tests': total_tests,
                'duplicate_tests': len(self.duplicate_tests),
                'obsolete_tests': len(self.obsolete_tests),
                'redundant_tests': len(set(self.redundant_tests)),
            },
            'details': {
                'duplicates': self.duplicate_tests,
                'obsolete': self.obsolete_tests,
                'redundant': list(set(self.redundant_tests)),
            },
            'recommendations': self._generate_recommendations(),
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate cleanup recommendations."""
        recommendations = []
        
        if self.duplicate_tests:
            recommendations.append(
                f"Remove {len(self.duplicate_tests)} duplicate tests to reduce maintenance burden"
            )
        
        if self.obsolete_tests:
            recommendations.append(
                f"Archive or remove {len(self.obsolete_tests)} obsolete tests"
            )
        
        if self.redundant_tests:
            unique_redundant = len(set(self.redundant_tests))
            recommendations.append(
                f"Consolidate {unique_redundant} redundant tests into parameterized tests"
            )
        
        # Check for test organization
        if len(self.test_files) > 50:
            recommendations.append(
                "Consider organizing tests into subdirectories by module or feature"
            )
        
        # Check for test naming
        poorly_named = sum(
            1 for methods in self.test_methods.values()
            for method in methods
            if len(method) < 10 or not method.replace('test_', '').replace('_', '').isalnum()
        )
        
        if poorly_named > 10:
            recommendations.append(
                f"Improve naming for {poorly_named} tests to be more descriptive"
            )
        
        return recommendations


class TestCleaner:
    """Clean up test suite based on analysis."""
    
    def __init__(self, test_dir: Path):
        """
        Initialize test cleaner.
        
        Args:
            test_dir: Root directory of test suite
        """
        self.test_dir = Path(test_dir)
        self.archive_dir = self.test_dir / "archived_tests"
        self.cleanup_log = []
    
    def archive_tests(self, test_list: List[str]):
        """
        Archive tests to a separate directory.
        
        Args:
            test_list: List of test identifiers (file::method)
        """
        # Create archive directory
        self.archive_dir.mkdir(exist_ok=True)
        
        # Group by file
        tests_by_file = defaultdict(list)
        for test_id in test_list:
            if '::' in test_id:
                file_path, method = test_id.split('::', 1)
                tests_by_file[file_path].append(method)
        
        for file_path, methods in tests_by_file.items():
            self._archive_from_file(Path(file_path), methods)
    
    def _archive_from_file(self, file_path: Path, methods: List[str]):
        """Archive specific methods from a file."""
        if not file_path.exists():
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse and modify AST
            tree = ast.parse(content)
            
            # Create archive file
            archive_file = self.archive_dir / f"archived_{file_path.name}"
            archived_methods = []
            
            # Remove methods from tree
            new_body = []
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name in methods:
                    archived_methods.append(node)
                    self.cleanup_log.append(f"Archived: {file_path}::{node.name}")
                else:
                    new_body.append(node)
            
            tree.body = new_body
            
            # Write modified file
            if new_body != tree.body:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(ast.unparse(tree))
            
            # Write archived methods
            if archived_methods:
                archive_tree = ast.Module(body=archived_methods, type_ignores=[])
                with open(archive_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n# Archived from {file_path} on {Path.ctime(Path())}\n")
                    f.write(ast.unparse(archive_tree))
                    
        except Exception as e:
            print(f"Error archiving from {file_path}: {e}")
    
    def remove_empty_files(self):
        """Remove test files that have no test methods."""
        for test_file in self.test_dir.rglob("test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file has any test methods
                if 'def test_' not in content:
                    test_file.unlink()
                    self.cleanup_log.append(f"Removed empty file: {test_file}")
                    
            except Exception as e:
                print(f"Error checking {test_file}: {e}")
    
    def consolidate_imports(self):
        """Consolidate and organize imports in test files."""
        for test_file in self.test_dir.rglob("test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST
                tree = ast.parse(content)
                
                # Collect imports
                imports = []
                other_nodes = []
                
                for node in tree.body:
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        imports.append(node)
                    else:
                        other_nodes.append(node)
                
                # Sort imports
                imports.sort(key=lambda x: ast.dump(x))
                
                # Rebuild tree
                tree.body = imports + other_nodes
                
                # Write back
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(ast.unparse(tree))
                    
                self.cleanup_log.append(f"Organized imports in: {test_file}")
                
            except Exception as e:
                print(f"Error organizing imports in {test_file}: {e}")
    
    def generate_cleanup_report(self) -> str:
        """Generate cleanup report."""
        report = ["Test Suite Cleanup Report", "=" * 50, ""]
        
        if self.cleanup_log:
            report.append("Actions Performed:")
            for action in self.cleanup_log:
                report.append(f"  - {action}")
        else:
            report.append("No cleanup actions performed")
        
        report.append("")
        report.append(f"Archive directory: {self.archive_dir}")
        
        return "\n".join(report)


def analyze_and_cleanup(test_dir: str, dry_run: bool = True) -> Dict:
    """
    Analyze and optionally clean up test suite.
    
    Args:
        test_dir: Path to test directory
        dry_run: If True, only analyze without making changes
        
    Returns:
        Analysis results and cleanup report
    """
    test_path = Path(test_dir)
    
    # Analyze
    analyzer = TestAnalyzer(test_path)
    analysis = analyzer.analyze()
    
    # Clean up if not dry run
    cleanup_report = None
    if not dry_run:
        cleaner = TestCleaner(test_path)
        
        # Archive obsolete tests
        if analysis['details']['obsolete']:
            cleaner.archive_tests(analysis['details']['obsolete'])
        
        # Remove empty files
        cleaner.remove_empty_files()
        
        # Organize imports
        cleaner.consolidate_imports()
        
        cleanup_report = cleaner.generate_cleanup_report()
    
    return {
        'analysis': analysis,
        'cleanup_report': cleanup_report,
        'dry_run': dry_run
    }