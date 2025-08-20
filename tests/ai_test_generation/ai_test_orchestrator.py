"""
Main orchestrator for AI-powered test generation system.

This module coordinates the entire test generation pipeline from
module discovery to test validation and execution.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import glob
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from tests.ai_test_generation.generators.test_generator import AITestGenerator
from tests.ai_test_generation.validators.test_validator import TestValidator


class AITestOrchestrator:
    """
    Orchestrates the entire AI-powered test generation process.
    """
    
    def __init__(self, project_root: str = None):
        """
        Initialize the orchestrator.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or str(Path.cwd())
        self.generator = AITestGenerator(self.project_root)
        self.validator = TestValidator()
        self.discovered_modules = []
        self.generated_tests = {}
        self.validation_results = {}
        
    def discover_modules(self, 
                        source_dir: str = "src/worldenergydata",
                        exclude_patterns: List[str] = None) -> List[str]:
        """
        Discover Python modules that need tests.
        
        Args:
            source_dir: Directory to search for modules
            exclude_patterns: Patterns to exclude from discovery
            
        Returns:
            List of module paths
        """
        exclude_patterns = exclude_patterns or ['__pycache__', '*test*.py', '__init__.py']
        
        # Find all Python files
        pattern = os.path.join(self.project_root, source_dir, "**", "*.py")
        all_files = glob.glob(pattern, recursive=True)
        
        # Filter out excluded patterns
        modules = []
        for file_path in all_files:
            # Check exclusion patterns
            should_exclude = False
            for pattern in exclude_patterns:
                if pattern in file_path:
                    should_exclude = True
                    break
            
            if not should_exclude:
                modules.append(file_path)
        
        self.discovered_modules = modules
        print(f"Discovered {len(modules)} modules for test generation")
        
        return modules
    
    def prioritize_untested_modules(self, test_dir: str = "tests") -> List[str]:
        """
        Identify and prioritize modules without tests.
        
        Args:
            test_dir: Directory containing existing tests
            
        Returns:
            List of module paths without tests, prioritized
        """
        untested = []
        
        for module_path in self.discovered_modules:
            # Check if test file exists
            module_name = Path(module_path).stem
            test_file_pattern = os.path.join(self.project_root, test_dir, "**", f"test_{module_name}.py")
            existing_tests = glob.glob(test_file_pattern, recursive=True)
            
            if not existing_tests:
                untested.append(module_path)
        
        # Prioritize using the generator's prioritization
        if untested:
            prioritized = self.generator.agent.prioritize_modules(untested)
            return [path for path, _ in prioritized]
        
        return untested
    
    def generate_tests_batch(self,
                           modules: List[str] = None,
                           max_modules: int = 10,
                           test_type: str = 'unit',
                           output_dir: str = None) -> Dict[str, str]:
        """
        Generate tests for a batch of modules.
        
        Args:
            modules: List of modules to generate tests for (or None to use discovered)
            max_modules: Maximum number of modules to process
            test_type: Type of tests to generate ('unit' or 'integration')
            output_dir: Directory to save generated tests
            
        Returns:
            Dictionary mapping module paths to generated test paths
        """
        if modules is None:
            modules = self.prioritize_untested_modules()[:max_modules]
        else:
            modules = modules[:max_modules]
        
        if not modules:
            print("No modules to generate tests for")
            return {}
        
        # Determine output directory
        if output_dir is None:
            if test_type == 'unit':
                output_dir = os.path.join(self.project_root, "tests", "ai_generated", "unit")
            else:
                output_dir = os.path.join(self.project_root, "tests", "ai_generated", "integration")
        
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\nGenerating {test_type} tests for {len(modules)} modules...")
        print(f"Output directory: {output_dir}\n")
        
        # Generate tests
        results = {}
        for i, module_path in enumerate(modules, 1):
            module_name = Path(module_path).stem
            print(f"[{i}/{len(modules)}] Generating tests for {module_name}...")
            
            try:
                # Generate test code
                test_code = self.generator.generate_tests_for_module(module_path, test_type)
                
                # Save test file
                test_file_name = f"test_{module_name}.py"
                test_file_path = os.path.join(output_dir, test_file_name)
                
                with open(test_file_path, 'w', encoding='utf-8') as f:
                    f.write(test_code)
                
                results[module_path] = test_file_path
                print(f"  [OK] Generated {test_file_name}")
                
            except Exception as e:
                print(f"  [FAIL] Failed to generate tests: {e}")
                results[module_path] = None
        
        self.generated_tests = results
        return results
    
    def validate_generated_tests(self) -> Dict[str, Any]:
        """
        Validate all generated tests.
        
        Returns:
            Validation results for all generated tests
        """
        if not self.generated_tests:
            print("No generated tests to validate")
            return {}
        
        print(f"\nValidating {len(self.generated_tests)} generated test files...")
        
        test_files = [path for path in self.generated_tests.values() if path]
        
        # Validate individual files
        file_results = {}
        for test_file in test_files:
            print(f"Validating {Path(test_file).name}...")
            result = self.validator.validate_test_file(test_file)
            file_results[test_file] = result
            
            # Print summary
            if result['syntax_valid'] and result['structure_valid']:
                print(f"  [VALID] ({result['test_count']} tests)")
            else:
                print(f"  [INVALID] - {', '.join(result['issues'])}")
        
        # Validate suite
        suite_results = self.validator.validate_test_suite(test_files)
        
        self.validation_results = {
            'file_results': file_results,
            'suite_results': suite_results
        }
        
        return self.validation_results
    
    def generate_report(self, output_file: str = None) -> str:
        """
        Generate a comprehensive report of the test generation process.
        
        Args:
            output_file: Path to save the report (optional)
            
        Returns:
            Report content as string
        """
        report_lines = [
            "=" * 80,
            "AI TEST GENERATION REPORT",
            "=" * 80,
            "",
            f"Project Root: {self.project_root}",
            f"Modules Discovered: {len(self.discovered_modules)}",
            f"Tests Generated: {len(self.generated_tests)}",
            ""
        ]
        
        # Module discovery summary
        if self.discovered_modules:
            report_lines.extend([
                "DISCOVERED MODULES:",
                "-" * 40
            ])
            for module in self.discovered_modules[:10]:
                report_lines.append(f"  • {Path(module).relative_to(self.project_root)}")
            if len(self.discovered_modules) > 10:
                report_lines.append(f"  ... and {len(self.discovered_modules) - 10} more")
            report_lines.append("")
        
        # Generated tests summary
        if self.generated_tests:
            report_lines.extend([
                "GENERATED TESTS:",
                "-" * 40
            ])
            for module_path, test_path in self.generated_tests.items():
                module_name = Path(module_path).stem
                if test_path:
                    test_name = Path(test_path).name
                    report_lines.append(f"  [OK] {module_name} -> {test_name}")
                else:
                    report_lines.append(f"  [FAIL] {module_name} -> FAILED")
            report_lines.append("")
        
        # Validation results
        if self.validation_results:
            suite = self.validation_results.get('suite_results', {})
            report_lines.extend([
                "VALIDATION RESULTS:",
                "-" * 40,
                f"  Valid Files: {suite.get('valid_files', 0)}/{suite.get('total_files', 0)}",
                f"  Total Tests: {suite.get('total_tests', 0)}",
                f"  Estimated Coverage: {suite.get('estimated_coverage', 0):.1%}",
                ""
            ])
            
            # Issues and warnings
            if suite.get('issues'):
                report_lines.extend([
                    "  Issues:",
                ])
                for issue in suite['issues'][:5]:
                    report_lines.append(f"    - {issue}")
                if len(suite['issues']) > 5:
                    report_lines.append(f"    ... and {len(suite['issues']) - 5} more")
            
            if suite.get('warnings'):
                report_lines.extend([
                    "  Warnings:",
                ])
                for warning in suite['warnings'][:5]:
                    report_lines.append(f"    - {warning}")
                if len(suite['warnings']) > 5:
                    report_lines.append(f"    ... and {len(suite['warnings']) - 5} more")
            
            report_lines.append("")
        
        # Suggestions
        if self.validation_results:
            suggestions = self.validator.suggest_improvements(
                self.validation_results.get('suite_results', {})
            )
            if suggestions:
                report_lines.extend([
                    "IMPROVEMENT SUGGESTIONS:",
                    "-" * 40
                ])
                for suggestion in suggestions:
                    report_lines.append(f"  • {suggestion}")
                report_lines.append("")
        
        # Summary
        report_lines.extend([
            "SUMMARY:",
            "-" * 40,
            f"  Test Generation: {'SUCCESS' if self.generated_tests else 'NO TESTS GENERATED'}",
            f"  Validation: {'PASSED' if self.validation_results.get('suite_results', {}).get('valid_files', 0) > 0 else 'FAILED'}",
            "",
            "=" * 80
        ])
        
        report = "\n".join(report_lines)
        
        # Save report if output file specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Report saved to: {output_file}")
        
        return report
    
    def run_full_pipeline(self,
                         source_dir: str = "src/worldenergydata",
                         max_modules: int = 10,
                         test_type: str = 'unit') -> Dict[str, Any]:
        """
        Run the complete test generation pipeline.
        
        Args:
            source_dir: Directory to search for modules
            max_modules: Maximum number of modules to process
            test_type: Type of tests to generate
            
        Returns:
            Complete results dictionary
        """
        print("=" * 80)
        print("STARTING AI-POWERED TEST GENERATION PIPELINE")
        print("=" * 80)
        
        # Step 1: Discover modules
        print("\n[Step 1/4] Discovering modules...")
        self.discover_modules(source_dir)
        
        # Step 2: Generate tests
        print("\n[Step 2/4] Generating tests...")
        self.generate_tests_batch(max_modules=max_modules, test_type=test_type)
        
        # Step 3: Validate tests
        print("\n[Step 3/4] Validating generated tests...")
        self.validate_generated_tests()
        
        # Step 4: Generate report
        print("\n[Step 4/4] Generating report...")
        report = self.generate_report(
            output_file=os.path.join(self.project_root, "tests", "ai_test_generation", "report.txt")
        )
        
        print("\n" + "=" * 80)
        print("PIPELINE COMPLETED")
        print("=" * 80)
        
        return {
            'discovered_modules': self.discovered_modules,
            'generated_tests': self.generated_tests,
            'validation_results': self.validation_results,
            'report': report
        }


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(description='AI-Powered Test Generation')
    parser.add_argument('--source-dir', default='src/worldenergydata',
                       help='Source directory to search for modules')
    parser.add_argument('--max-modules', type=int, default=10,
                       help='Maximum number of modules to process')
    parser.add_argument('--test-type', choices=['unit', 'integration'], default='unit',
                       help='Type of tests to generate')
    parser.add_argument('--output-dir', help='Output directory for generated tests')
    
    args = parser.parse_args()
    
    # Run the pipeline
    orchestrator = AITestOrchestrator()
    results = orchestrator.run_full_pipeline(
        source_dir=args.source_dir,
        max_modules=args.max_modules,
        test_type=args.test_type
    )
    
    # Print summary
    print("\nSummary:")
    print(f"  • Modules discovered: {len(results['discovered_modules'])}")
    print(f"  • Tests generated: {len(results['generated_tests'])}")
    
    validation = results['validation_results'].get('suite_results', {})
    if validation:
        print(f"  • Valid test files: {validation.get('valid_files', 0)}")
        print(f"  • Total test methods: {validation.get('total_tests', 0)}")
        print(f"  • Estimated coverage: {validation.get('estimated_coverage', 0):.1%}")


if __name__ == "__main__":
    main()