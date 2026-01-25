"""
Test generation templates for different types of tests.

These templates are used by the AI test generator to create
appropriate test cases based on the code being tested.
"""

from typing import Dict, Any, List


class TestTemplates:
    """Collection of test generation templates."""
    
    @staticmethod
    def get_unit_test_template() -> str:
        """Template for unit tests."""
        return '''import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from {module_import} import {class_or_function}


class Test{class_name}(unittest.TestCase):
    """Unit tests for {class_name}."""
    
    def setUp(self):
        """Set up test fixtures."""
        {setup_code}
    
    def tearDown(self):
        """Clean up after tests."""
        {teardown_code}
    
    {test_methods}
'''

    @staticmethod
    def get_integration_test_template() -> str:
        """Template for integration tests."""
        return '''import pytest
from pathlib import Path
import sys
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from {module_import} import {class_or_function}
from tests.test_markers import integration


@integration
class Test{class_name}Integration:
    """Integration tests for {class_name}."""
    
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test environment."""
        self.temp_dir = tmp_path
        {setup_code}
    
    {test_methods}
'''

    @staticmethod
    def get_test_method_template(test_type: str) -> str:
        """Get template for specific test method type."""
        templates = {
            'basic': '''
    def test_{function_name}_basic(self):
        """Test basic functionality of {function_name}."""
        # Arrange
        {arrange_code}
        
        # Act
        result = {act_code}
        
        # Assert
        {assert_code}
''',
            'edge_case': '''
    def test_{function_name}_edge_cases(self):
        """Test edge cases for {function_name}."""
        # Test with None
        {none_test}
        
        # Test with empty input
        {empty_test}
        
        # Test with boundary values
        {boundary_test}
''',
            'exception': '''
    def test_{function_name}_raises_{exception_type}(self):
        """Test that {function_name} raises {exception_type}."""
        # Arrange
        {arrange_code}
        
        # Act & Assert
        with self.assertRaises({exception_type}):
            {act_code}
''',
            'return_value': '''
    def test_{function_name}_return_value(self):
        """Test return value of {function_name}."""
        # Arrange
        {arrange_code}
        
        # Act
        result = {act_code}
        
        # Assert
        self.assertIsNotNone(result)
        {specific_assertions}
''',
            'parameterized': '''
    @pytest.mark.parametrize("input_data,expected", [
        {test_cases}
    ])
    def test_{function_name}_parameterized(self, input_data, expected):
        """Parameterized tests for {function_name}."""
        result = {function_call}
        assert result == expected
''',
            'mock': '''
    @patch('{mock_target}')
    def test_{function_name}_with_mock(self, mock_{mock_name}):
        """Test {function_name} with mocked dependencies."""
        # Setup mock
        mock_{mock_name}.return_value = {mock_return}
        
        # Act
        result = {act_code}
        
        # Assert
        mock_{mock_name}.assert_called_once_with({expected_args})
        {result_assertions}
''',
            'async': '''
    async def test_{function_name}_async(self):
        """Test async functionality of {function_name}."""
        # Arrange
        {arrange_code}
        
        # Act
        result = await {act_code}
        
        # Assert
        {assert_code}
''',
            'performance': '''
    @pytest.mark.benchmark
    def test_{function_name}_performance(self, benchmark):
        """Test performance of {function_name}."""
        # Arrange
        {arrange_code}
        
        # Act & Assert
        result = benchmark({function_call})
        assert result is not None
'''
        }
        
        return templates.get(test_type, templates['basic'])
    
    @staticmethod
    def get_fixture_template() -> str:
        """Template for test fixtures."""
        return '''
    @pytest.fixture
    def {fixture_name}(self):
        """Create {fixture_description}."""
        {fixture_code}
        return {return_value}
'''
    
    @staticmethod
    def get_data_fixture_templates() -> Dict[str, str]:
        """Templates for common data fixtures."""
        return {
            'dataframe': '''
    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame for testing."""
        data = {{
            'column1': [1, 2, 3, 4, 5],
            'column2': ['a', 'b', 'c', 'd', 'e'],
            'column3': [10.1, 20.2, 30.3, 40.4, 50.5]
        }}
        return pd.DataFrame(data)
''',
            'config': '''
    @pytest.fixture
    def test_config(self, tmp_path):
        """Create test configuration."""
        return {{
            'basename': 'test',
            'data_path': str(tmp_path / 'data'),
            'output_path': str(tmp_path / 'output'),
            'parameters': {{
                'test_param': 'test_value'
            }}
        }}
''',
            'file': '''
    @pytest.fixture
    def test_file(self, tmp_path):
        """Create temporary test file."""
        test_file = tmp_path / "test_data.txt"
        test_file.write_text("test content\\nline 2\\nline 3")
        return test_file
''',
            'mock_api': '''
    @pytest.fixture
    def mock_api_response(self):
        """Create mock API response."""
        return {{
            'status': 'success',
            'data': {{
                'id': 123,
                'value': 'test_value'
            }}
        }}
'''
        }
    
    @staticmethod
    def generate_assertion(value_type: str, variable_name: str) -> str:
        """Generate appropriate assertion based on value type."""
        assertions = {
            'int': f'self.assertIsInstance({variable_name}, int)',
            'float': f'self.assertIsInstance({variable_name}, (int, float))',
            'str': f'self.assertIsInstance({variable_name}, str)',
            'list': f'self.assertIsInstance({variable_name}, list)',
            'dict': f'self.assertIsInstance({variable_name}, dict)',
            'DataFrame': f'self.assertIsInstance({variable_name}, pd.DataFrame)',
            'None': f'self.assertIsNone({variable_name})',
            'bool': f'self.assertIsInstance({variable_name}, bool)',
            'default': f'self.assertIsNotNone({variable_name})'
        }
        
        return assertions.get(value_type, assertions['default'])
    
    @staticmethod
    def generate_mock_setup(dependency: str, return_value: Any = None) -> str:
        """Generate mock setup code."""
        if return_value is None:
            return_value = "MagicMock()"
        
        return f"""
        mock_{dependency.split('.')[-1]} = MagicMock()
        mock_{dependency.split('.')[-1]}.return_value = {return_value}
"""
    
    @staticmethod
    def generate_test_data(data_type: str, size: str = 'small') -> str:
        """Generate test data creation code."""
        data_generators = {
            'dataframe_small': '''pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })''',
            'dataframe_large': '''pd.DataFrame({
            'col1': np.random.randint(0, 100, 1000),
            'col2': np.random.choice(['a', 'b', 'c', 'd'], 1000)
        })''',
            'array_small': 'np.array([1, 2, 3, 4, 5])',
            'array_large': 'np.random.rand(1000, 100)',
            'dict_simple': "{'key1': 'value1', 'key2': 'value2'}",
            'dict_nested': '''{
            'level1': {
                'level2': {
                    'data': [1, 2, 3]
                }
            }
        }''',
            'list_simple': '[1, 2, 3, 4, 5]',
            'list_complex': '[[i, i**2] for i in range(10)]'
        }
        
        key = f"{data_type}_{size}"
        return data_generators.get(key, "None")


class PromptTemplates:
    """Templates for AI prompts to generate specific test types."""
    
    @staticmethod
    def get_test_generation_prompt(code: str, test_type: str) -> str:
        """Generate prompt for AI to create tests."""
        return f"""
Generate {test_type} tests for the following Python code:

```python
{code}
```

Requirements:
1. Follow the AAA pattern (Arrange, Act, Assert)
2. Include edge cases and error handling
3. Use appropriate mocking for external dependencies
4. Include docstrings for all test methods
5. Ensure tests are independent and repeatable
6. Add parameterized tests where applicable

Generate comprehensive tests that achieve at least 90% code coverage.
"""
    
    @staticmethod
    def get_fixture_generation_prompt(code: str) -> str:
        """Generate prompt for creating test fixtures."""
        return f"""
Analyze the following code and generate appropriate test fixtures:

```python
{code}
```

Create fixtures for:
1. Common test data structures
2. Mock objects for external dependencies
3. Temporary files/directories if needed
4. Configuration objects
5. Database connections (if applicable)

Ensure fixtures are reusable and properly scoped.
"""
    
    @staticmethod
    def get_mock_generation_prompt(dependencies: List[str]) -> str:
        """Generate prompt for creating mock objects."""
        return f"""
Create mock objects for the following dependencies:
{', '.join(dependencies)}

For each dependency:
1. Create appropriate Mock or MagicMock object
2. Define realistic return values
3. Set up side effects if needed
4. Configure mock attributes
5. Include assertion helpers

Ensure mocks accurately simulate the real dependencies' behavior.
"""