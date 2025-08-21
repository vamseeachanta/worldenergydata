#!/usr/bin/env python
"""
Test Suite Cleanup Script
Identifies and removes problematic, duplicate, and obsolete tests
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
import ast
import re

class TestSuiteCleanup:
    def __init__(self, test_dir: Path = Path("tests")):
        self.test_dir = test_dir
        self.archive_dir = test_dir / "_archived_tests"
        self.report = {
            "removed": [],
            "archived": [],
            "fixed": [],
            "kept": [],
            "errors": []
        }
        
    def analyze_test_file(self, filepath: Path) -> Dict:
        """Analyze a test file for issues"""
        issues = {
            "path": str(filepath),
            "has_tests": False,
            "has_init_in_class": False,
            "import_errors": [],
            "is_helper": False,
            "is_empty": False,
            "test_count": 0
        }
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                
            # Check for actual test functions
            test_count = len(re.findall(r'def test_\w+', content))
            issues["test_count"] = test_count
            issues["has_tests"] = test_count > 0
            
            # Check for empty or near-empty files
            if len(content.strip()) < 100:
                issues["is_empty"] = True
                
            # Check if it's a helper/utility file
            if any(keyword in filepath.name for keyword in ['helper', 'util', 'base', 'conftest', 'fixture']):
                issues["is_helper"] = True
                
            # Check for __init__ in test classes (causes pytest collection errors)
            if '__init__' in content and 'class Test' in content:
                issues["has_init_in_class"] = True
                
            # Check for problematic imports
            if 'from worldenergydata' in content:
                # Try to parse and identify missing imports
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module and 'worldenergydata' in node.module:
                                # Check if module likely exists
                                module_path = node.module.replace('.', '/')
                                if 'memory_processor' in module_path or 'cache_manager' in module_path:
                                    issues["import_errors"].append(node.module)
                except:
                    pass
                    
        except Exception as e:
            issues["errors"] = str(e)
            
        return issues
    
    def categorize_tests(self) -> Tuple[List[Path], List[Path], List[Path]]:
        """Categorize tests into remove, archive, and keep"""
        remove = []  # Broken beyond repair or auto-generated junk
        archive = []  # Potentially valuable but currently broken
        keep = []    # Working tests or easily fixable
        
        for root, dirs, files in os.walk(self.test_dir):
            # Skip archived directory
            if '_archived' in root:
                continue
                
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                filepath = Path(root) / file
                
                # Skip non-test files
                if 'test' not in file and not file.startswith('test_'):
                    continue
                    
                analysis = self.analyze_test_file(filepath)
                
                # Decision logic
                if analysis["is_helper"]:
                    keep.append(filepath)  # Keep helper files
                elif analysis["is_empty"] or analysis["test_count"] == 0:
                    if 'ai_test_generation' in str(filepath):
                        remove.append(filepath)  # Remove empty AI-generated files
                    else:
                        archive.append(filepath)  # Archive empty legacy tests
                elif analysis["has_init_in_class"]:
                    archive.append(filepath)  # Archive tests with __init__ issues
                elif 'ai_test_generation' in str(filepath) and analysis["test_count"] == 0:
                    remove.append(filepath)  # Remove AI test infrastructure with no tests
                elif analysis["import_errors"]:
                    archive.append(filepath)  # Archive tests with import issues
                else:
                    keep.append(filepath)  # Keep working tests
                    
        return remove, archive, keep
    
    def archive_tests(self, files: List[Path]):
        """Archive tests for potential future reference"""
        if not files:
            return
            
        self.archive_dir.mkdir(exist_ok=True)
        
        for filepath in files:
            try:
                rel_path = filepath.relative_to(self.test_dir)
                archive_path = self.archive_dir / rel_path
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(filepath), str(archive_path))
                self.report["archived"].append(str(rel_path))
                print(f"Archived: {rel_path}")
            except Exception as e:
                self.report["errors"].append(f"Failed to archive {filepath}: {e}")
    
    def remove_tests(self, files: List[Path]):
        """Remove test files permanently"""
        for filepath in files:
            try:
                rel_path = filepath.relative_to(self.test_dir) 
                os.remove(filepath)
                self.report["removed"].append(str(rel_path))
                print(f"Removed: {rel_path}")
            except Exception as e:
                self.report["errors"].append(f"Failed to remove {filepath}: {e}")
    
    def fix_init_issues(self, filepath: Path):
        """Fix __init__ issues in test classes"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Remove __init__ methods from test classes
            fixed_content = re.sub(
                r'(class Test\w+.*?:.*?)def __init__\(self.*?\):.*?(?=def|\n\n|\Z)',
                r'\1',
                content,
                flags=re.DOTALL
            )
            
            if fixed_content != content:
                with open(filepath, 'w') as f:
                    f.write(fixed_content)
                self.report["fixed"].append(str(filepath.relative_to(self.test_dir)))
                return True
        except Exception as e:
            self.report["errors"].append(f"Failed to fix {filepath}: {e}")
        return False
    
    def generate_report(self) -> str:
        """Generate cleanup report"""
        report_lines = [
            "# Test Suite Cleanup Report",
            "",
            f"## Summary",
            f"- Tests Removed: {len(self.report['removed'])}",
            f"- Tests Archived: {len(self.report['archived'])}",
            f"- Tests Fixed: {len(self.report['fixed'])}",
            f"- Tests Kept: {len(self.report['kept'])}",
            f"- Errors: {len(self.report['errors'])}",
            ""
        ]
        
        if self.report['removed']:
            report_lines.extend([
                "## Removed Tests (Permanently Deleted)",
                "These were empty, broken, or auto-generated tests with no value:",
                ""
            ])
            for item in sorted(self.report['removed'])[:20]:
                report_lines.append(f"- {item}")
            if len(self.report['removed']) > 20:
                report_lines.append(f"... and {len(self.report['removed']) - 20} more")
            report_lines.append("")
        
        if self.report['archived']:
            report_lines.extend([
                "## Archived Tests (Moved to _archived_tests/)",
                "These may have value but are currently broken:",
                ""
            ])
            for item in sorted(self.report['archived'])[:20]:
                report_lines.append(f"- {item}")
            if len(self.report['archived']) > 20:
                report_lines.append(f"... and {len(self.report['archived']) - 20} more")
            report_lines.append("")
        
        if self.report['errors']:
            report_lines.extend([
                "## Errors During Cleanup",
                ""
            ])
            for error in self.report['errors'][:10]:
                report_lines.append(f"- {error}")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def run_cleanup(self, dry_run: bool = True):
        """Execute the cleanup process"""
        print(f"{'DRY RUN - ' if dry_run else ''}Starting test suite cleanup...")
        print(f"Analyzing tests in {self.test_dir}...")
        
        remove, archive, keep = self.categorize_tests()
        self.report["kept"] = [str(p.relative_to(self.test_dir)) for p in keep]
        
        print(f"\nAnalysis complete:")
        print(f"  - To Remove: {len(remove)} files")
        print(f"  - To Archive: {len(archive)} files")  
        print(f"  - To Keep: {len(keep)} files")
        
        if not dry_run:
            print("\nExecuting cleanup...")
            self.archive_tests(archive)
            self.remove_tests(remove)
            print("\nCleanup complete!")
        else:
            print("\nDRY RUN - No files were actually modified")
            print("Run with dry_run=False to execute cleanup")
        
        return self.generate_report()


if __name__ == "__main__":
    import sys
    
    dry_run = "--execute" not in sys.argv
    cleanup = TestSuiteCleanup()
    report = cleanup.run_cleanup(dry_run=dry_run)
    
    # Save report
    report_path = Path("tests/cleanup_report.md")
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to {report_path}")
    
    if dry_run:
        print("\nTo execute cleanup, run: python tests/cleanup_test_suite.py --execute")