"""
Validator for AI-generated tests to ensure quality and correctness.
"""

import ast
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


class TestValidator:
    """
    Validates AI-generated tests for syntax, quality, and effectiveness.
    """
    
    def __init__(self):
        """Initialize the test validator."""
        self.validation_results = []
        
    def validate_test_file(self, test_file_path: str) -> Dict[str, Any]:
        """
        Validate a generated test file.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Validation results dictionary
        """
        results = {
            'file': test_file_path,
            'syntax_valid': False,
            'imports_valid': False,
            'structure_valid': False,
            'runnable': False,
            'coverage': 0.0,
            'issues': [],
            'warnings': [],
            'test_count': 0
        }
        
        # Check syntax
        syntax_result = self.check_syntax(test_file_path)
        results['syntax_valid'] = syntax_result[0]
        if not syntax_result[0]:
            results['issues'].append(f"Syntax error: {syntax_result[1]}")
            return results
        
        # Check imports
        import_result = self.check_imports(test_file_path)
        results['imports_valid'] = import_result[0]
        if not import_result[0]:
            results['warnings'].extend(import_result[1])
        
        # Check structure
        structure_result = self.check_test_structure(test_file_path)
        results['structure_valid'] = structure_result[0]
        results['test_count'] = structure_result[1]
        if not structure_result[0]:
            results['issues'].extend(structure_result[2])
        
        # Check if runnable
        run_result = self.check_runnable(test_file_path)
        results['runnable'] = run_result[0]
        if not run_result[0]:
            results['warnings'].append(f"Test execution failed: {run_result[1]}")
        
        # Estimate coverage (simplified)
        if results['runnable']:
            results['coverage'] = self.estimate_coverage(test_file_path)
        
        self.validation_results.append(results)
        return results
    
    def check_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if the test file has valid Python syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            ast.parse(source)
            return (True, None)
        except SyntaxError as e:
            return (False, str(e))
    
    def check_imports(self, file_path: str) -> Tuple[bool, List[str]]:
        """Check if all imports in the test file are valid."""
        warnings = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        try:
            tree = ast.parse(source)
        except:
            return (False, ["Could not parse file for import checking"])
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not self._check_module_exists(alias.name):
                        warnings.append(f"Module '{alias.name}' might not be installed")
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module
                if module and not self._check_module_exists(module):
                    warnings.append(f"Module '{module}' might not be installed")
        
        return (len(warnings) == 0, warnings)
    
    def _check_module_exists(self, module_name: str) -> bool:
        """Check if a module can be imported."""
        # Common modules that are always available
        standard_modules = {
            'unittest', 'pytest', 'sys', 'os', 'pathlib', 'json', 'ast',
            'tempfile', 'collections', 'itertools', 'functools', 're'
        }
        
        if module_name in standard_modules:
            return True
        
        # Check if it's a project module
        if module_name.startswith('worldenergydata'):
            return True
        
        # Check if it's in tests
        if module_name.startswith('tests'):
            return True
        
        # Try to import (simplified check)
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def check_test_structure(self, file_path: str) -> Tuple[bool, int, List[str]]:
        """Check if the test file has proper test structure."""
        issues = []
        test_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        try:
            tree = ast.parse(source)
        except:
            return (False, 0, ["Could not parse file for structure checking"])
        
        has_test_class = False
        has_test_methods = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith('Test'):
                    has_test_class = True
                    
                    # Check for test methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if item.name.startswith('test_'):
                                has_test_methods = True
                                test_count += 1
                            elif item.name in ['setUp', 'tearDown', 'setUpClass', 'tearDownClass']:
                                # These are valid setup/teardown methods
                                pass
                            elif not item.name.startswith('_'):
                                issues.append(f"Method '{item.name}' doesn't follow test naming convention")
            
            elif isinstance(node, ast.FunctionDef):
                # Check for top-level test functions
                if node.name.startswith('test_'):
                    has_test_methods = True
                    test_count += 1
        
        if not has_test_class and not has_test_methods:
            issues.append("No test classes or test functions found")
        
        if test_count == 0:
            issues.append("No test methods found")
        
        return (len(issues) == 0, test_count, issues)
    
    def check_runnable(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if the test file can be executed."""
        
        # Create a simple test runner script
        test_script = f"""
import sys
import os
sys.path.insert(0, r'{os.path.dirname(file_path)}')
sys.path.insert(0, r'{os.path.join(os.getcwd(), "src")}')

try:
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover(r'{os.path.dirname(file_path)}', pattern='{os.path.basename(file_path)}')
    
    if suite.countTestCases() > 0:
        print("OK")
    else:
        print("No tests found")
except Exception as e:
    print(f"Error: {{e}}")
"""
        
        # Write and execute test script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            os.unlink(temp_file)
            
            if "OK" in result.stdout:
                return (True, None)
            else:
                return (False, result.stdout + result.stderr)
        
        except subprocess.TimeoutExpired:
            os.unlink(temp_file)
            return (False, "Test execution timed out")
        except Exception as e:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            return (False, str(e))
    
    def estimate_coverage(self, test_file_path: str) -> float:
        """Estimate coverage provided by the test file."""
        
        # This is a simplified estimation based on test count
        # In reality, you would run coverage.py
        
        with open(test_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        try:
            tree = ast.parse(source)
        except:
            return 0.0
        
        test_count = 0
        assertion_count = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_'):
                    test_count += 1
                    
                    # Count assertions
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if hasattr(child.func, 'attr'):
                                if 'assert' in child.func.attr.lower():
                                    assertion_count += 1
        
        if test_count == 0:
            return 0.0
        
        # Simple heuristic: each test with assertions provides ~10% coverage
        # More assertions = better coverage
        avg_assertions = assertion_count / test_count if test_count > 0 else 0
        estimated_coverage = min(test_count * 10 * (1 + avg_assertions / 5), 100)
        
        return estimated_coverage / 100
    
    def validate_test_suite(self, test_files: List[str]) -> Dict[str, Any]:
        """
        Validate an entire test suite.
        
        Args:
            test_files: List of test file paths
            
        Returns:
            Suite validation results
        """
        suite_results = {
            'total_files': len(test_files),
            'valid_files': 0,
            'total_tests': 0,
            'estimated_coverage': 0.0,
            'issues': [],
            'warnings': [],
            'file_results': []
        }
        
        coverage_sum = 0.0
        
        for test_file in test_files:
            result = self.validate_test_file(test_file)
            suite_results['file_results'].append(result)
            
            if result['syntax_valid'] and result['structure_valid']:
                suite_results['valid_files'] += 1
            
            suite_results['total_tests'] += result['test_count']
            coverage_sum += result['coverage']
            
            suite_results['issues'].extend(result['issues'])
            suite_results['warnings'].extend(result['warnings'])
        
        if len(test_files) > 0:
            suite_results['estimated_coverage'] = coverage_sum / len(test_files)
        
        return suite_results
    
    def suggest_improvements(self, validation_results: Dict[str, Any]) -> List[str]:
        """
        Suggest improvements based on validation results.
        
        Args:
            validation_results: Results from validate_test_file or validate_test_suite
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        if 'file_results' in validation_results:
            # Suite validation results
            if validation_results['estimated_coverage'] < 0.8:
                suggestions.append("Add more test cases to improve coverage")
            
            if validation_results['total_tests'] < validation_results['total_files'] * 5:
                suggestions.append("Consider adding more test methods per test file")
            
            if validation_results['warnings']:
                suggestions.append("Address import warnings to ensure tests can run")
        
        else:
            # Single file validation results
            if validation_results['test_count'] < 3:
                suggestions.append("Add more test methods to thoroughly test the module")
            
            if not validation_results['runnable']:
                suggestions.append("Fix test execution issues before proceeding")
            
            if validation_results['coverage'] < 0.7:
                suggestions.append("Add edge cases and error handling tests")
        
        return suggestions