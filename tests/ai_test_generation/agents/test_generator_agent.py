"""
AI-powered test generator agent for creating comprehensive test suites.

This agent analyzes source code and generates appropriate test cases
using intelligent pattern recognition and test generation strategies.
"""

import ast
import inspect
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json


class TestGeneratorAgent:
    """
    AI agent for generating test cases from source code.
    """
    
    def __init__(self, coverage_target: float = 0.9):
        """
        Initialize the test generator agent.
        
        Args:
            coverage_target: Target code coverage percentage (0.0 to 1.0)
        """
        self.coverage_target = coverage_target
        self.generated_tests = []
        self.analyzed_modules = []
        
    def analyze_module(self, module_path: str) -> Dict[str, Any]:
        """
        Analyze a Python module to understand its structure.
        
        Args:
            module_path: Path to the Python module
            
        Returns:
            Dictionary containing module analysis results
        """
        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {'error': f'Syntax error in module: {e}'}
        
        analysis = {
            'module_path': module_path,
            'module_name': Path(module_path).stem,
            'classes': [],
            'functions': [],
            'imports': [],
            'constants': [],
            'complexity': 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._analyze_class(node)
                analysis['classes'].append(class_info)
                analysis['complexity'] += class_info['complexity']
                
            elif isinstance(node, ast.FunctionDef):
                if not self._is_method(node, tree):
                    func_info = self._analyze_function(node)
                    analysis['functions'].append(func_info)
                    analysis['complexity'] += func_info['complexity']
                    
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis['imports'].append(alias.name)
                    
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    analysis['imports'].append(f"{module}.{alias.name}")
        
        self.analyzed_modules.append(analysis)
        return analysis
    
    def _analyze_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Analyze a class definition."""
        class_info = {
            'name': node.name,
            'methods': [],
            'complexity': 1,
            'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0,
            'docstring': ast.get_docstring(node)
        }
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._analyze_function(item)
                class_info['methods'].append(method_info)
                class_info['complexity'] += method_info['complexity']
        
        return class_info
    
    def _analyze_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze a function definition."""
        func_info = {
            'name': node.name,
            'args': [arg.arg for arg in node.args.args],
            'complexity': self._calculate_complexity(node),
            'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0,
            'docstring': ast.get_docstring(node),
            'has_return': any(isinstance(n, ast.Return) for n in ast.walk(node)),
            'raises_exceptions': self._get_exceptions(node)
        }
        
        return func_info
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _get_exceptions(self, node: ast.FunctionDef) -> List[str]:
        """Get list of exceptions that a function might raise."""
        exceptions = []
        for child in ast.walk(node):
            if isinstance(child, ast.Raise):
                if child.exc:
                    if isinstance(child.exc, ast.Call):
                        if isinstance(child.exc.func, ast.Name):
                            exceptions.append(child.exc.func.id)
                    elif isinstance(child.exc, ast.Name):
                        exceptions.append(child.exc.id)
        return exceptions
    
    def _is_method(self, node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if a function is a method inside a class."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return True
        return False
    
    def generate_test_strategy(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a test strategy based on module analysis.
        
        Args:
            analysis: Module analysis results
            
        Returns:
            Test strategy dictionary
        """
        strategy = {
            'module': analysis['module_name'],
            'test_file': f"test_{analysis['module_name']}.py",
            'test_classes': [],
            'test_functions': [],
            'test_count': 0,
            'coverage_approach': 'comprehensive'
        }
        
        # Determine testing approach based on complexity
        if analysis['complexity'] > 50:
            strategy['coverage_approach'] = 'focused'
            strategy['priority'] = 'high'
        elif analysis['complexity'] > 20:
            strategy['coverage_approach'] = 'balanced'
            strategy['priority'] = 'medium'
        else:
            strategy['coverage_approach'] = 'comprehensive'
            strategy['priority'] = 'normal'
        
        # Generate test specifications for classes
        for class_info in analysis['classes']:
            test_class = {
                'name': f"Test{class_info['name']}",
                'target_class': class_info['name'],
                'test_methods': []
            }
            
            # Generate test methods for each class method
            for method in class_info['methods']:
                test_methods = self._generate_test_methods_for_function(method)
                test_class['test_methods'].extend(test_methods)
                strategy['test_count'] += len(test_methods)
            
            strategy['test_classes'].append(test_class)
        
        # Generate test specifications for standalone functions
        for func_info in analysis['functions']:
            test_funcs = self._generate_test_methods_for_function(func_info)
            strategy['test_functions'].extend(test_funcs)
            strategy['test_count'] += len(test_funcs)
        
        return strategy
    
    def _generate_test_methods_for_function(self, func_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate test method specifications for a function."""
        test_methods = []
        
        # Basic test
        test_methods.append({
            'name': f"test_{func_info['name']}_basic",
            'type': 'basic',
            'description': f"Test basic functionality of {func_info['name']}"
        })
        
        # Edge cases based on complexity
        if func_info['complexity'] > 2:
            test_methods.append({
                'name': f"test_{func_info['name']}_edge_cases",
                'type': 'edge_case',
                'description': f"Test edge cases for {func_info['name']}"
            })
        
        # Exception tests if function raises exceptions
        if func_info['raises_exceptions']:
            for exc in func_info['raises_exceptions']:
                test_methods.append({
                    'name': f"test_{func_info['name']}_raises_{exc.lower()}",
                    'type': 'exception',
                    'description': f"Test that {func_info['name']} raises {exc}"
                })
        
        # Return value test if function has return
        if func_info['has_return']:
            test_methods.append({
                'name': f"test_{func_info['name']}_return_value",
                'type': 'return_value',
                'description': f"Test return value of {func_info['name']}"
            })
        
        # Parameterized test if function has multiple arguments
        if len(func_info['args']) > 2:
            test_methods.append({
                'name': f"test_{func_info['name']}_parameterized",
                'type': 'parameterized',
                'description': f"Parameterized tests for {func_info['name']}"
            })
        
        return test_methods
    
    def prioritize_modules(self, module_paths: List[str]) -> List[Tuple[str, int]]:
        """
        Prioritize modules for testing based on complexity and coverage.
        
        Args:
            module_paths: List of module paths to prioritize
            
        Returns:
            List of tuples (module_path, priority_score)
        """
        priorities = []
        
        for module_path in module_paths:
            if not os.path.exists(module_path):
                continue
                
            analysis = self.analyze_module(module_path)
            if 'error' in analysis:
                continue
            
            # Calculate priority score
            score = 0
            
            # Complexity factor
            score += analysis['complexity'] * 2
            
            # Size factor (lines of code)
            total_lines = sum(cls['lines'] for cls in analysis['classes'])
            total_lines += sum(func['lines'] for func in analysis['functions'])
            score += total_lines // 10
            
            # Public API factor (non-private functions/classes)
            public_items = len([c for c in analysis['classes'] if not c['name'].startswith('_')])
            public_items += len([f for f in analysis['functions'] if not f['name'].startswith('_')])
            score += public_items * 5
            
            priorities.append((module_path, score))
        
        # Sort by priority score (highest first)
        priorities.sort(key=lambda x: x[1], reverse=True)
        
        return priorities
    
    def generate_test_file_content(self, strategy: Dict[str, Any], template_type: str = 'standard') -> str:
        """
        Generate actual test file content based on strategy.
        
        Args:
            strategy: Test strategy dictionary
            template_type: Type of template to use
            
        Returns:
            Generated test file content as string
        """
        # This will be implemented with actual template generation
        # For now, return a placeholder
        return f"# Generated tests for {strategy['module']}\n# Test count: {strategy['test_count']}\n"
    
    def save_strategy(self, strategy: Dict[str, Any], output_dir: str = "tests/ai_test_generation/strategies"):
        """Save test strategy to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        
        strategy_file = os.path.join(output_dir, f"{strategy['module']}_strategy.json")
        with open(strategy_file, 'w') as f:
            json.dump(strategy, f, indent=2)
        
        return strategy_file