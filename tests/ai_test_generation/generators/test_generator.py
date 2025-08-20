"""
Main test generator that orchestrates AI-powered test creation.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import ast
import json

from tests.ai_test_generation.agents.test_generator_agent import TestGeneratorAgent
from tests.ai_test_generation.templates.test_templates import TestTemplates, PromptTemplates


class AITestGenerator:
    """
    Main orchestrator for AI-powered test generation.
    """
    
    def __init__(self, project_root: str = None):
        """
        Initialize the AI test generator.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or os.getcwd()
        self.agent = TestGeneratorAgent(coverage_target=0.9)
        self.templates = TestTemplates()
        self.prompts = PromptTemplates()
        self.generated_tests = []
        
    def generate_tests_for_module(self, module_path: str, test_type: str = 'unit') -> str:
        """
        Generate tests for a specific module.
        
        Args:
            module_path: Path to the Python module
            test_type: Type of tests to generate ('unit' or 'integration')
            
        Returns:
            Generated test code as string
        """
        # Analyze the module
        analysis = self.agent.analyze_module(module_path)
        
        if 'error' in analysis:
            return f"# Error analyzing module: {analysis['error']}"
        
        # Generate test strategy
        strategy = self.agent.generate_test_strategy(analysis)
        
        # Generate test code based on strategy
        test_code = self._generate_test_code(analysis, strategy, test_type)
        
        # Save strategy for future reference
        self.agent.save_strategy(strategy)
        
        return test_code
    
    def _generate_test_code(self, analysis: Dict[str, Any], strategy: Dict[str, Any], test_type: str) -> str:
        """Generate actual test code based on analysis and strategy."""
        
        # Select appropriate template
        if test_type == 'unit':
            template = self.templates.get_unit_test_template()
        else:
            template = self.templates.get_integration_test_template()
        
        # Generate module import path
        module_import = self._get_module_import_path(analysis['module_path'])
        
        # Generate test methods
        test_methods = []
        
        # Generate tests for classes
        for test_class in strategy['test_classes']:
            for test_method in test_class['test_methods']:
                method_code = self._generate_test_method(
                    test_method, 
                    test_class['target_class'],
                    analysis
                )
                test_methods.append(method_code)
        
        # Generate tests for functions
        for test_func in strategy['test_functions']:
            method_code = self._generate_test_method(
                test_func,
                None,
                analysis
            )
            test_methods.append(method_code)
        
        # Build the test file
        test_code = template.format(
            module_import=module_import,
            class_or_function=self._get_main_import(analysis),
            class_name=self._get_test_class_name(analysis),
            setup_code=self._generate_setup_code(analysis),
            teardown_code=self._generate_teardown_code(analysis),
            test_methods='\n'.join(test_methods)
        )
        
        return test_code
    
    def _generate_test_method(self, test_spec: Dict[str, Any], target_class: Optional[str], analysis: Dict[str, Any]) -> str:
        """Generate a single test method."""
        
        # Get the appropriate template
        template = self.templates.get_test_method_template(test_spec['type'])
        
        # Find the target function/method info
        target_info = self._find_target_info(test_spec['name'], target_class, analysis)
        
        if not target_info:
            return f"    # TODO: Implement {test_spec['name']}"
        
        # Generate test code components
        function_name = self._extract_function_name(test_spec['name'])
        
        # Fill in the template
        if test_spec['type'] == 'basic':
            return self._generate_basic_test(function_name, target_info, template)
        elif test_spec['type'] == 'edge_case':
            return self._generate_edge_case_test(function_name, target_info, template)
        elif test_spec['type'] == 'exception':
            return self._generate_exception_test(function_name, target_info, template, test_spec)
        elif test_spec['type'] == 'return_value':
            return self._generate_return_value_test(function_name, target_info, template)
        elif test_spec['type'] == 'parameterized':
            return self._generate_parameterized_test(function_name, target_info, template)
        else:
            return f"    # TODO: Implement {test_spec['name']}"
    
    def _generate_basic_test(self, function_name: str, target_info: Dict[str, Any], template: str) -> str:
        """Generate a basic test method."""
        
        # Generate test data based on function arguments
        arrange_code = self._generate_arrange_code(target_info)
        
        # Generate function call
        act_code = self._generate_function_call(function_name, target_info)
        
        # Generate assertions
        assert_code = self._generate_assertions(target_info)
        
        return template.format(
            function_name=function_name,
            arrange_code=arrange_code,
            act_code=act_code,
            assert_code=assert_code
        )
    
    def _generate_edge_case_test(self, function_name: str, target_info: Dict[str, Any], template: str) -> str:
        """Generate edge case tests."""
        
        none_test = f"result = {function_name}(None)\n        self.assertIsNone(result)"
        empty_test = f"result = {function_name}([])\n        self.assertEqual(result, [])"
        boundary_test = f"result = {function_name}(0)\n        self.assertIsNotNone(result)"
        
        return template.format(
            function_name=function_name,
            none_test=none_test,
            empty_test=empty_test,
            boundary_test=boundary_test
        )
    
    def _generate_exception_test(self, function_name: str, target_info: Dict[str, Any], template: str, test_spec: Dict[str, Any]) -> str:
        """Generate exception test."""
        
        # Extract exception type from test name
        exception_type = test_spec['name'].split('_')[-1].capitalize()
        if exception_type.lower() == 'error':
            exception_type = 'Exception'
        
        arrange_code = "invalid_input = None"
        act_code = f"{function_name}(invalid_input)"
        
        return template.format(
            function_name=function_name,
            exception_type=exception_type,
            arrange_code=arrange_code,
            act_code=act_code
        )
    
    def _generate_return_value_test(self, function_name: str, target_info: Dict[str, Any], template: str) -> str:
        """Generate return value test."""
        
        arrange_code = self._generate_arrange_code(target_info)
        act_code = self._generate_function_call(function_name, target_info)
        specific_assertions = "self.assertIsInstance(result, (dict, list, str, int, float))"
        
        return template.format(
            function_name=function_name,
            arrange_code=arrange_code,
            act_code=act_code,
            specific_assertions=specific_assertions
        )
    
    def _generate_parameterized_test(self, function_name: str, target_info: Dict[str, Any], template: str) -> str:
        """Generate parameterized test."""
        
        # Generate test cases
        test_cases = """
        (1, 1),
        (2, 4),
        (3, 9),
        (0, 0),
        (-1, 1)"""
        
        function_call = f"{function_name}(input_data)"
        
        return template.format(
            function_name=function_name,
            test_cases=test_cases,
            function_call=function_call
        )
    
    def _generate_arrange_code(self, target_info: Dict[str, Any]) -> str:
        """Generate arrangement code for test."""
        
        if not target_info.get('args'):
            return "# No setup needed"
        
        arrange_lines = []
        for arg in target_info['args']:
            if arg == 'self':
                continue
            elif 'df' in arg.lower() or 'data' in arg.lower():
                arrange_lines.append(f"{arg} = pd.DataFrame({{'col1': [1, 2, 3]}})")
            elif 'config' in arg.lower() or 'cfg' in arg.lower():
                arrange_lines.append(f"{arg} = {{'key': 'value'}}")
            elif 'path' in arg.lower() or 'file' in arg.lower():
                arrange_lines.append(f"{arg} = 'test_path.txt'")
            else:
                arrange_lines.append(f"{arg} = 'test_value'")
        
        return '\n        '.join(arrange_lines) if arrange_lines else "# No setup needed"
    
    def _generate_function_call(self, function_name: str, target_info: Dict[str, Any]) -> str:
        """Generate function call code."""
        
        args = [arg for arg in target_info.get('args', []) if arg != 'self']
        arg_string = ', '.join(args)
        
        return f"{function_name}({arg_string})"
    
    def _generate_assertions(self, target_info: Dict[str, Any]) -> str:
        """Generate assertion code."""
        
        if target_info.get('has_return'):
            return "self.assertIsNotNone(result)"
        else:
            return "# Function has no return value"
    
    def _generate_setup_code(self, analysis: Dict[str, Any]) -> str:
        """Generate setup code for test class."""
        return "self.test_instance = None  # Initialize if needed"
    
    def _generate_teardown_code(self, analysis: Dict[str, Any]) -> str:
        """Generate teardown code for test class."""
        return "pass  # Clean up if needed"
    
    def _get_module_import_path(self, module_path: str) -> str:
        """Convert file path to module import path."""
        
        # Remove .py extension
        module_path = module_path.replace('.py', '')
        
        # Convert path separators to dots
        module_path = module_path.replace(os.sep, '.')
        module_path = module_path.replace('/', '.')
        
        # Remove src prefix if present
        if 'src.worldenergydata' in module_path:
            module_path = module_path.split('src.')[-1]
        elif 'worldenergydata' in module_path:
            module_path = 'worldenergydata' + module_path.split('worldenergydata')[-1]
        
        return module_path
    
    def _get_main_import(self, analysis: Dict[str, Any]) -> str:
        """Get the main class or function to import."""
        
        if analysis['classes']:
            return analysis['classes'][0]['name']
        elif analysis['functions']:
            return analysis['functions'][0]['name']
        else:
            return analysis['module_name']
    
    def _get_test_class_name(self, analysis: Dict[str, Any]) -> str:
        """Generate test class name."""
        
        if analysis['classes']:
            return analysis['classes'][0]['name']
        else:
            # Convert module name to PascalCase
            parts = analysis['module_name'].split('_')
            return ''.join(part.capitalize() for part in parts)
    
    def _find_target_info(self, test_name: str, target_class: Optional[str], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find information about the target function/method."""
        
        # Extract function name from test name
        function_name = self._extract_function_name(test_name)
        
        # Search in classes
        if target_class:
            for class_info in analysis['classes']:
                if class_info['name'] == target_class:
                    for method in class_info['methods']:
                        if method['name'] == function_name:
                            return method
        
        # Search in functions
        for func in analysis['functions']:
            if func['name'] == function_name:
                return func
        
        return None
    
    def _extract_function_name(self, test_name: str) -> str:
        """Extract function name from test method name."""
        
        # Remove 'test_' prefix
        if test_name.startswith('test_'):
            test_name = test_name[5:]
        
        # Remove suffixes like '_basic', '_edge_cases', etc.
        suffixes = ['_basic', '_edge_cases', '_raises_', '_return_value', '_parameterized', '_with_mock', '_async', '_performance']
        for suffix in suffixes:
            if suffix in test_name:
                test_name = test_name.split(suffix)[0]
                break
        
        return test_name
    
    def batch_generate_tests(self, module_paths: List[str], output_dir: str = "tests/generated") -> Dict[str, str]:
        """
        Generate tests for multiple modules.
        
        Args:
            module_paths: List of module paths to generate tests for
            output_dir: Directory to save generated tests
            
        Returns:
            Dictionary mapping module paths to generated test file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Prioritize modules
        prioritized = self.agent.prioritize_modules(module_paths)
        
        results = {}
        
        for module_path, priority in prioritized:
            print(f"Generating tests for {module_path} (priority: {priority})")
            
            # Generate test code
            test_code = self.generate_tests_for_module(module_path)
            
            # Determine output file name
            module_name = Path(module_path).stem
            test_file_name = f"test_{module_name}.py"
            test_file_path = os.path.join(output_dir, test_file_name)
            
            # Save test file
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_code)
            
            results[module_path] = test_file_path
            self.generated_tests.append(test_file_path)
        
        return results
    
    def generate_test_suite_config(self) -> Dict[str, Any]:
        """Generate configuration for the test suite."""
        
        config = {
            'test_directories': ['tests/unit', 'tests/integration', 'tests/generated'],
            'coverage_target': 0.9,
            'test_markers': ['unit', 'integration', 'slow', 'smoke'],
            'generated_tests': self.generated_tests,
            'statistics': {
                'modules_analyzed': len(self.agent.analyzed_modules),
                'tests_generated': sum(s['test_count'] for s in self.agent.analyzed_modules if 'test_count' in s)
            }
        }
        
        return config