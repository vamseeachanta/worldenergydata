"""
Code analyzer module for API12 drilling completion analysis.

This module provides functions to analyze the implementation logic and methodologies
used in both drilling_and_completion_days.py and well_api12.py scripts.
"""

import ast
import re
import inspect
from pathlib import Path
from typing import Dict, List, Any, Tuple
import keyword


def read_script_content(script_path: str) -> str:
    """
    Read the content of a Python script file.
    
    Args:
        script_path (str): Path to the Python script
        
    Returns:
        str: Content of the script file
        
    Raises:
        FileNotFoundError: If the script file doesn't exist
    """
    path = Path(script_path)
    if not path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_script_ast(script_path: str) -> ast.AST:
    """
    Parse a Python script into an Abstract Syntax Tree.
    
    Args:
        script_path (str): Path to the Python script
        
    Returns:
        ast.AST: Parsed AST of the script
    """
    content = read_script_content(script_path)
    return ast.parse(content)


def analyze_script_imports(script_path: str) -> Dict[str, List[str]]:
    """
    Analyze import statements in a Python script.
    
    Args:
        script_path (str): Path to the Python script
        
    Returns:
        Dict[str, List[str]]: Categorized imports
    """
    tree = parse_script_ast(script_path)
    
    imports = {
        'standard_libraries': [],
        'third_party_libraries': [],
        'local_modules': []
    }
    
    # Standard library modules (common ones)
    stdlib_modules = {
        'os', 'sys', 'datetime', 'time', 'json', 'csv', 're', 'math', 
        'collections', 'itertools', 'functools', 'pathlib', 'typing',
        'logging', 'warnings', 'copy', 'pickle', 'sqlite3', 'urllib'
    }
    
    # Third-party libraries (common data science ones)
    third_party_modules = {
        'pandas', 'numpy', 'matplotlib', 'plotly', 'seaborn', 'scipy',
        'sklearn', 'requests', 'beautifulsoup4', 'bs4', 'scrapy', 'selenium',
        'openpyxl', 'xlrd', 'xlwt', 'sqlalchemy', 'psycopg2', 'pymongo'
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name in stdlib_modules:
                    imports['standard_libraries'].append(alias.name)
                elif module_name in third_party_modules:
                    imports['third_party_libraries'].append(alias.name)
                else:
                    imports['local_modules'].append(alias.name)
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                import_str = f"from {node.module} import {', '.join([alias.name for alias in node.names])}"
                
                if module_name in stdlib_modules:
                    imports['standard_libraries'].append(import_str)
                elif module_name in third_party_modules:
                    imports['third_party_libraries'].append(import_str)
                else:
                    imports['local_modules'].append(import_str)
    
    return imports


def analyze_function_definitions(script_path: str) -> List[Dict[str, Any]]:
    """
    Analyze function definitions in a Python script.
    
    Args:
        script_path (str): Path to the Python script
        
    Returns:
        List[Dict[str, Any]]: List of function information
    """
    tree = parse_script_ast(script_path)
    functions = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_info = {
                'name': node.name,
                'args': [arg.arg for arg in node.args.args],
                'lineno': node.lineno,
                'docstring': ast.get_docstring(node) or '',
                'decorators': [decorator.id if hasattr(decorator, 'id') else str(decorator) 
                             for decorator in node.decorator_list],
                'returns_annotation': ast.unparse(node.returns) if node.returns else None
            }
            functions.append(func_info)
    
    return functions


def analyze_data_sources(script_path: str) -> Dict[str, List[str]]:
    """
    Analyze data sources used in a Python script.
    
    Args:
        script_path (str): Path to the Python script
        
    Returns:
        Dict[str, List[str]]: Categorized data sources
    """
    content = read_script_content(script_path)
    
    data_sources = {
        'database_queries': [],
        'file_operations': [],
        'api_calls': []
    }
    
    # Database query patterns
    db_patterns = [
        r'SELECT\s+.*\s+FROM\s+\w+',
        r'INSERT\s+INTO\s+\w+',
        r'UPDATE\s+\w+\s+SET',
        r'DELETE\s+FROM\s+\w+',
        r'\.execute\(',
        r'\.query\(',
        r'pd\.read_sql'
    ]
    
    # File operation patterns
    file_patterns = [
        r'pd\.read_csv\(',
        r'pd\.read_excel\(',
        r'pd\.to_csv\(',
        r'pd\.to_excel\(',
        r'open\(',
        r'\.read\(',
        r'\.write\(',
        r'pathlib\.',
        r'os\.path\.'
    ]
    
    # API call patterns
    api_patterns = [
        r'requests\.get\(',
        r'requests\.post\(',
        r'urllib\.request\.',
        r'http\w*://',
        r'\.json\(\)'
    ]
    
    # Search for patterns
    for pattern in db_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        data_sources['database_queries'].extend(matches)
    
    for pattern in file_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        data_sources['file_operations'].extend(matches)
    
    for pattern in api_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        data_sources['api_calls'].extend(matches)
    
    # Remove duplicates
    for key in data_sources:
        data_sources[key] = list(set(data_sources[key]))
    
    return data_sources


def analyze_date_calculations(script_path: str) -> Dict[str, List[str]]:
    """
    Analyze date calculation methods in a Python script.
    
    Args:
        script_path (str): Path to the Python script
        
    Returns:
        Dict[str, List[str]]: Date calculation analysis
    """
    content = read_script_content(script_path)
    
    date_analysis = {
        'date_variables': [],
        'date_operations': [],
        'timedelta_operations': []
    }
    
    # Date variable patterns
    date_var_patterns = [
        r'\w*date\w*',
        r'\w*time\w*',
        r'\w*spud\w*',
        r'\w*completion\w*',
        r'\w*drilling\w*'
    ]
    
    # Date operation patterns
    date_op_patterns = [
        r'datetime\.',
        r'pd\.to_datetime',
        r'\.dt\.',
        r'\.date\(\)',
        r'\.time\(\)',
        r'\.strftime\(',
        r'\.strptime\('
    ]
    
    # Timedelta patterns
    timedelta_patterns = [
        r'timedelta\(',
        r'pd\.Timedelta',
        r'\.days',
        r'\.total_seconds\(\)',
        r'\-.*date',
        r'date.*\-'
    ]
    
    # Search for patterns
    for pattern in date_var_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        date_analysis['date_variables'].extend(matches)
    
    for pattern in date_op_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        date_analysis['date_operations'].extend(matches)
    
    for pattern in timedelta_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        date_analysis['timedelta_operations'].extend(matches)
    
    # Remove duplicates and filter out keywords
    for key in date_analysis:
        unique_items = list(set(date_analysis[key]))
        date_analysis[key] = [item for item in unique_items 
                             if not keyword.iskeyword(item) and len(item) > 1]
    
    return date_analysis


def analyze_drilling_completion_logic(script_path: str) -> Dict[str, List[str]]:
    """
    Analyze drilling and completion day calculation logic.
    
    Args:
        script_path (str): Path to the Python script
        
    Returns:
        Dict[str, List[str]]: Drilling and completion logic analysis
    """
    content = read_script_content(script_path)
    
    logic_analysis = {
        'drilling_calculations': [],
        'completion_calculations': [],
        'key_variables': []
    }
    
    # Drilling calculation patterns
    drilling_patterns = [
        r'drilling.*days',
        r'drill.*time',
        r'spud.*date',
        r'total.*depth.*date',
        r'rig.*days',
        r'DRL',
        r'drilling_days'
    ]
    
    # Completion calculation patterns
    completion_patterns = [
        r'completion.*days',
        r'complete.*time',
        r'completion.*date',
        r'first.*production',
        r'completion_days',
        r'COMPLETION'
    ]
    
    # Key variable patterns
    key_var_patterns = [
        r'API\w*',
        r'WELL\w*',
        r'LEASE\w*',
        r'DATE\w*',
        r'DAYS\w*'
    ]
    
    # Search for patterns
    for pattern in drilling_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        logic_analysis['drilling_calculations'].extend(matches)
    
    for pattern in completion_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        logic_analysis['completion_calculations'].extend(matches)
    
    for pattern in key_var_patterns:
        matches = re.findall(pattern, content)  # Case sensitive for API variables
        logic_analysis['key_variables'].extend(matches)
    
    # Remove duplicates
    for key in logic_analysis:
        logic_analysis[key] = list(set(logic_analysis[key]))
    
    return logic_analysis


def analyze_script_complexity(script_path: str) -> Dict[str, int]:
    """
    Analyze script complexity metrics.
    
    Args:
        script_path (str): Path to the Python script
        
    Returns:
        Dict[str, int]: Complexity metrics
    """
    content = read_script_content(script_path)
    tree = parse_script_ast(script_path)
    
    metrics = {
        'total_lines': len(content.split('\n')),
        'code_lines': len([line for line in content.split('\n') 
                          if line.strip() and not line.strip().startswith('#')]),
        'function_count': 0,
        'class_count': 0,
        'import_count': 0,
        'comment_lines': len([line for line in content.split('\n') 
                             if line.strip().startswith('#')])
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            metrics['function_count'] += 1
        elif isinstance(node, ast.ClassDef):
            metrics['class_count'] += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            metrics['import_count'] += 1
    
    return metrics


def extract_business_rules(script_path: str) -> List[str]:
    """
    Extract business rules from script comments and docstrings.
    
    Args:
        script_path (str): Path to the Python script
        
    Returns:
        List[str]: List of identified business rules
    """
    content = read_script_content(script_path)
    tree = parse_script_ast(script_path)
    
    rules = []
    
    # Extract from comments
    comment_lines = [line.strip() for line in content.split('\n') 
                    if line.strip().startswith('#')]
    
    for comment in comment_lines:
        # Look for rule-like comments
        if any(keyword in comment.lower() for keyword in 
               ['rule', 'assumption', 'business', 'requirement', 'logic', 'calculate']):
            rules.append(comment.replace('#', '').strip())
    
    # Extract from docstrings
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            docstring = ast.get_docstring(node)
            if docstring:
                # Look for rule-like statements in docstrings
                sentences = re.split(r'[.!?]', docstring)
                for sentence in sentences:
                    if any(keyword in sentence.lower() for keyword in 
                           ['calculate', 'determine', 'compute', 'rule', 'assumption']):
                        rules.append(sentence.strip())
    
    return [rule for rule in rules if len(rule) > 10]  # Filter out very short rules


def compare_methodologies(lease_script_path: str, api12_script_path: str) -> Dict[str, Any]:
    """
    Compare methodologies between the two scripts.
    
    Args:
        lease_script_path (str): Path to lease method script
        api12_script_path (str): Path to API12 method script
        
    Returns:
        Dict[str, Any]: Comparison results
    """
    lease_imports = analyze_script_imports(lease_script_path)
    api12_imports = analyze_script_imports(api12_script_path)
    
    lease_functions = analyze_function_definitions(lease_script_path)
    api12_functions = analyze_function_definitions(api12_script_path)
    
    lease_sources = analyze_data_sources(lease_script_path)
    api12_sources = analyze_data_sources(api12_script_path)
    
    comparison = {
        'data_source_differences': [],
        'calculation_method_differences': [],
        'common_approaches': [],
        'unique_to_lease': [],
        'unique_to_api12': []
    }
    
    # Compare data sources
    lease_all_sources = []
    api12_all_sources = []
    
    for sources in lease_sources.values():
        lease_all_sources.extend(sources)
    for sources in api12_sources.values():
        api12_all_sources.extend(sources)
    
    lease_set = set(lease_all_sources)
    api12_set = set(api12_all_sources)
    
    comparison['common_approaches'] = list(lease_set.intersection(api12_set))
    comparison['unique_to_lease'] = list(lease_set - api12_set)
    comparison['unique_to_api12'] = list(api12_set - lease_set)
    
    # Compare function approaches
    lease_func_names = [f['name'] for f in lease_functions]
    api12_func_names = [f['name'] for f in api12_functions]
    
    if set(lease_func_names) != set(api12_func_names):
        comparison['calculation_method_differences'].append(
            f"Different function structures: Lease has {len(lease_func_names)} functions, "
            f"API12 has {len(api12_func_names)} functions"
        )
    
    return comparison


def identify_key_differences(lease_script_path: str, api12_script_path: str) -> Dict[str, Any]:
    """
    Identify key differences between the two approaches.
    
    Args:
        lease_script_path (str): Path to lease method script
        api12_script_path (str): Path to API12 method script
        
    Returns:
        Dict[str, Any]: Key differences
    """
    lease_content = read_script_content(lease_script_path)
    api12_content = read_script_content(api12_script_path)
    
    lease_complexity = analyze_script_complexity(lease_script_path)
    api12_complexity = analyze_script_complexity(api12_script_path)
    
    differences = {
        'data_processing_differences': [],
        'calculation_differences': [],
        'output_format_differences': []
    }
    
    # Compare complexity
    if lease_complexity['function_count'] != api12_complexity['function_count']:
        differences['data_processing_differences'].append(
            f"Function count differs: Lease has {lease_complexity['function_count']}, "
            f"API12 has {api12_complexity['function_count']}"
        )
    
    # Compare data operations
    lease_data_ops = re.findall(r'pd\.\w+', lease_content)
    api12_data_ops = re.findall(r'pd\.\w+', api12_content)
    
    if set(lease_data_ops) != set(api12_data_ops):
        unique_lease = set(lease_data_ops) - set(api12_data_ops)
        unique_api12 = set(api12_data_ops) - set(lease_data_ops)
        
        if unique_lease:
            differences['data_processing_differences'].append(
                f"Unique pandas operations in lease method: {list(unique_lease)}"
            )
        if unique_api12:
            differences['data_processing_differences'].append(
                f"Unique pandas operations in API12 method: {list(unique_api12)}"
            )
    
    # Look for output differences
    lease_outputs = re.findall(r'to_\w+\(|\.save|\.export|print\(', lease_content)
    api12_outputs = re.findall(r'to_\w+\(|\.save|\.export|print\(', api12_content)
    
    if set(lease_outputs) != set(api12_outputs):
        differences['output_format_differences'].append(
            f"Different output methods detected"
        )
    
    return differences


def generate_methodology_summary(lease_script_path: str, api12_script_path: str) -> Dict[str, Any]:
    """
    Generate comprehensive methodology summary for both scripts.
    
    Args:
        lease_script_path (str): Path to lease method script
        api12_script_path (str): Path to API12 method script
        
    Returns:
        Dict[str, Any]: Comprehensive methodology summary
    """
    summary = {
        'lease_method': {
            'script_path': lease_script_path,
            'imports': analyze_script_imports(lease_script_path),
            'key_functions': analyze_function_definitions(lease_script_path),
            'data_sources': analyze_data_sources(lease_script_path),
            'date_calculations': analyze_date_calculations(lease_script_path),
            'drilling_completion_logic': analyze_drilling_completion_logic(lease_script_path),
            'business_rules': extract_business_rules(lease_script_path),
            'complexity_metrics': analyze_script_complexity(lease_script_path),
            'calculation_approach': 'Lease-based methodology using lease data and well information'
        },
        'api12_method': {
            'script_path': api12_script_path,
            'imports': analyze_script_imports(api12_script_path),
            'key_functions': analyze_function_definitions(api12_script_path),
            'data_sources': analyze_data_sources(api12_script_path),
            'date_calculations': analyze_date_calculations(api12_script_path),
            'drilling_completion_logic': analyze_drilling_completion_logic(api12_script_path),
            'business_rules': extract_business_rules(api12_script_path),
            'complexity_metrics': analyze_script_complexity(api12_script_path),
            'calculation_approach': 'API12-based methodology using well-specific data and timeline analysis'
        },
        'comparison': compare_methodologies(lease_script_path, api12_script_path),
        'key_differences': identify_key_differences(lease_script_path, api12_script_path)
    }
    
    return summary


def save_methodology_analysis(summary: Dict[str, Any], output_path: str) -> None:
    """
    Save methodology analysis to a JSON file.
    
    Args:
        summary (Dict[str, Any]): Methodology summary
        output_path (str): Path to save the analysis
    """
    import json
    
    # Convert any non-serializable objects to strings
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(item) for item in obj]
        else:
            return obj
    
    serializable_summary = make_serializable(summary)
    
    with open(output_path, 'w') as f:
        json.dump(serializable_summary, f, indent=2)