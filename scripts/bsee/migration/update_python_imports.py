#!/usr/bin/env python3
"""
BSEE Data Consolidation - Python Imports Update Script

Identifies and updates all Python imports throughout the codebase to use the new
consolidated BSEE structure. Handles various import patterns and provides
backup/rollback capabilities.

Usage:
    python update_python_imports.py [--dry-run] [--backup] [--pattern=<regex>]
"""

import argparse
import ast
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any

import yaml


class ImportPatternMatcher:
    """Matches and transforms import patterns."""
    
    def __init__(self):
        """Initialize with transformation rules."""
        self.transformation_rules = {
            # Old structure -> New structure mappings
            'worldenergydata.data_collectors.bsee_data_collector': 'worldenergydata.bsee.data_collection',
            'worldenergydata.analysis.production_analysis': 'worldenergydata.bsee.analysis',
            'worldenergydata.processing.directional_survey_processor': 'worldenergydata.bsee.processing',
            'worldenergydata.bsee_data': 'worldenergydata.bsee',
            'worldenergydata.bsee_analysis': 'worldenergydata.bsee.analysis',
            'worldenergydata.bsee_processing': 'worldenergydata.bsee.processing',
            
            # Legacy class mappings
            'BSEEDataCollector': 'BSEEDataCollector',  # Same class name, different module
            'ProductionAnalyzer': 'ProductionAnalyzer',
            'DirectionalProcessor': 'DirectionalProcessor',
            'DirectionalSurveyProcessor': 'DirectionalProcessor',  # Renamed class
        }
        
        # Patterns for different import styles
        self.import_patterns = [
            # import module
            re.compile(r'^(\s*)import\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*$'),
            # import module as alias
            re.compile(r'^(\s*)import\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+as\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*$'),
            # from module import item
            re.compile(r'^(\s*)from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import\s+([a-zA-Z_][a-zA-Z0-9_*,\s]+)\s*$'),
            # from module import item as alias
            re.compile(r'^(\s*)from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import\s+([a-zA-Z_][a-zA-Z0-9_*,\s]+)\s+as\s+([a-zA-Z_][a-zA-Z0-9_]+)\s*$'),
        ]
        
    def should_transform_import(self, import_line: str) -> bool:
        """Check if an import line should be transformed."""
        # Only transform worldenergydata imports
        if 'worldenergydata' not in import_line:
            return False
            
        # Check against known old patterns
        for old_pattern in self.transformation_rules.keys():
            if old_pattern in import_line:
                return True
                
        return False
        
    def transform_import_line(self, line: str) -> Tuple[str, bool, str]:
        """Transform an import line.
        
        Args:
            line: Original import line
            
        Returns:
            Tuple of (transformed_line, was_changed, change_description)
        """
        original_line = line.strip()
        
        if not self.should_transform_import(original_line):
            return line, False, ""
            
        # Try each pattern
        for pattern in self.import_patterns:
            match = pattern.match(original_line)
            if match:
                return self._apply_transformation(match, line, pattern)
                
        return line, False, ""
        
    def _apply_transformation(self, match, original_line: str, pattern) -> Tuple[str, bool, str]:
        """Apply transformation based on matched pattern."""
        groups = match.groups()
        indent = groups[0]
        
        # Handle different import patterns
        if 'from' in pattern.pattern:
            # from X import Y [as Z]
            module_name = groups[1]
            imports = groups[2]
            
            # Transform module name
            new_module = self._transform_module_name(module_name)
            if new_module != module_name:
                if len(groups) > 3:  # has 'as' clause
                    alias = groups[3]
                    new_line = f"{indent}from {new_module} import {imports} as {alias}"
                else:
                    new_line = f"{indent}from {new_module} import {imports}"
                    
                change_desc = f"Updated module: {module_name} -> {new_module}"
                return new_line + '\n', True, change_desc
                
        else:
            # import X [as Y]
            module_name = groups[1]
            new_module = self._transform_module_name(module_name)
            
            if new_module != module_name:
                if len(groups) > 2:  # has 'as' clause
                    alias = groups[2]
                    new_line = f"{indent}import {new_module} as {alias}"
                else:
                    new_line = f"{indent}import {new_module}"
                    
                change_desc = f"Updated module: {module_name} -> {new_module}"
                return new_line + '\n', True, change_desc
                
        return original_line, False, ""
        
    def _transform_module_name(self, module_name: str) -> str:
        """Transform a module name according to rules."""
        # Direct mapping
        if module_name in self.transformation_rules:
            return self.transformation_rules[module_name]
            
        # Pattern-based transformation
        for old_pattern, new_pattern in self.transformation_rules.items():
            if old_pattern in module_name:
                return module_name.replace(old_pattern, new_pattern)
                
        return module_name


class PythonImportsUpdater:
    """Updates Python imports throughout the codebase."""
    
    def __init__(self, base_path: str = None, custom_patterns: Dict[str, str] = None):
        """Initialize imports updater.
        
        Args:
            base_path: Base path for WorldEnergyData project
            custom_patterns: Additional transformation patterns
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.matcher = ImportPatternMatcher()
        
        # Add custom patterns if provided
        if custom_patterns:
            self.matcher.transformation_rules.update(custom_patterns)
            
        self.scan_results = {
            'files_scanned': 0,
            'files_with_imports': 0,
            'files_modified': 0,
            'total_imports_found': 0,
            'imports_transformed': 0,
            'transformations': [],
            'errors': []
        }
        
    def find_python_files(self, include_patterns: List[str] = None) -> List[Path]:
        """Find all Python files to scan."""
        if include_patterns is None:
            include_patterns = ['**/*.py']
            
        python_files = []
        
        for pattern in include_patterns:
            for file_path in self.base_path.glob(pattern):
                if file_path.is_file() and file_path.suffix == '.py':
                    # Skip certain directories
                    skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'venv', 'env', '.venv'}
                    if not any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                        python_files.append(file_path)
                        
        return sorted(python_files)
        
    def scan_file_for_imports(self, file_path: Path) -> Dict[str, Any]:
        """Scan a file for import statements."""
        file_result = {
            'file_path': str(file_path.relative_to(self.base_path)),
            'imports_found': [],
            'transformable_imports': 0,
            'syntax_valid': True,
            'error': None
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse with AST for validation
            try:
                ast.parse(content)
            except SyntaxError as e:
                file_result['syntax_valid'] = False
                file_result['error'] = f"Syntax error: {e}"
                return file_result
                
            # Scan line by line for imports
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                stripped_line = line.strip()
                
                # Check for import statements
                if (stripped_line.startswith('import ') or 
                    stripped_line.startswith('from ') and ' import ' in stripped_line):
                    
                    import_info = {
                        'line_number': line_num,
                        'original_line': line,
                        'is_transformable': self.matcher.should_transform_import(stripped_line)
                    }
                    
                    file_result['imports_found'].append(import_info)
                    
                    if import_info['is_transformable']:
                        file_result['transformable_imports'] += 1
                        
        except Exception as e:
            file_result['error'] = str(e)
            
        return file_result
        
    def transform_file(self, file_path: Path, dry_run: bool = True, 
                      backup: bool = True) -> Dict[str, Any]:
        """Transform imports in a single file.
        
        Args:
            file_path: Path to the Python file
            dry_run: If True, don't actually modify files
            backup: If True, create backup before modifying
            
        Returns:
            Dictionary with transformation results
        """
        transform_result = {
            'file_path': str(file_path.relative_to(self.base_path)),
            'transformations_applied': [],
            'lines_changed': 0,
            'backup_created': False,
            'success': False,
            'error': None
        }
        
        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()
                
            # Transform each line
            new_lines = []
            for line_num, line in enumerate(original_lines, 1):
                transformed_line, was_changed, change_desc = self.matcher.transform_import_line(line)
                
                new_lines.append(transformed_line)
                
                if was_changed:
                    transform_result['transformations_applied'].append({
                        'line_number': line_num,
                        'original': line.strip(),
                        'transformed': transformed_line.strip(),
                        'description': change_desc
                    })
                    transform_result['lines_changed'] += 1
                    
            # Only proceed if changes were made
            if transform_result['lines_changed'] == 0:
                transform_result['success'] = True
                return transform_result
                
            if not dry_run:
                # Create backup if requested
                if backup:
                    backup_path = file_path.with_suffix(f'.py.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                    shutil.copy2(file_path, backup_path)
                    transform_result['backup_created'] = True
                    
                # Write transformed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                    
            transform_result['success'] = True
            
        except Exception as e:
            transform_result['error'] = str(e)
            
        return transform_result
        
    def scan_codebase(self, include_patterns: List[str] = None) -> Dict[str, Any]:
        """Scan entire codebase for import patterns."""
        print("🔍 Scanning codebase for Python imports...")
        
        python_files = self.find_python_files(include_patterns)
        print(f"   Found {len(python_files)} Python files to scan")
        
        scan_summary = {
            'files_scanned': 0,
            'files_with_transformable_imports': 0,
            'total_transformable_imports': 0,
            'file_details': []
        }
        
        for file_path in python_files:
            scan_summary['files_scanned'] += 1
            file_result = self.scan_file_for_imports(file_path)
            
            if file_result['transformable_imports'] > 0:
                scan_summary['files_with_transformable_imports'] += 1
                scan_summary['total_transformable_imports'] += file_result['transformable_imports']
                scan_summary['file_details'].append(file_result)
                
                print(f"   📄 {file_result['file_path']}: {file_result['transformable_imports']} transformable imports")
                
        print(f"\n📊 Scan Summary:")
        print(f"   Files scanned: {scan_summary['files_scanned']}")
        print(f"   Files with transformable imports: {scan_summary['files_with_transformable_imports']}")
        print(f"   Total transformable imports: {scan_summary['total_transformable_imports']}")
        
        return scan_summary
        
    def update_imports(self, include_patterns: List[str] = None, dry_run: bool = True,
                      backup: bool = True) -> Dict[str, Any]:
        """Update imports across the entire codebase.
        
        Args:
            include_patterns: File patterns to include in scan
            dry_run: If True, don't actually modify files
            backup: If True, create backups before modifying
            
        Returns:
            Dictionary with update results
        """
        print(f"🚀 {'Simulating' if dry_run else 'Performing'} import updates...")
        
        python_files = self.find_python_files(include_patterns)
        
        update_summary = {
            'files_processed': 0,
            'files_modified': 0,
            'total_transformations': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'transformation_details': [],
            'errors': []
        }
        
        for file_path in python_files:
            update_summary['files_processed'] += 1
            
            # Check if file has transformable imports first
            scan_result = self.scan_file_for_imports(file_path)
            if scan_result['transformable_imports'] == 0:
                continue
                
            # Transform the file
            transform_result = self.transform_file(file_path, dry_run, backup)
            
            if transform_result['success']:
                update_summary['successful_updates'] += 1
                
                if transform_result['lines_changed'] > 0:
                    update_summary['files_modified'] += 1
                    update_summary['total_transformations'] += transform_result['lines_changed']
                    update_summary['transformation_details'].append(transform_result)
                    
                    print(f"   {'📋' if dry_run else '✅'} {transform_result['file_path']}: {transform_result['lines_changed']} imports updated")
                    
                    # Show details for first few files
                    if len(update_summary['transformation_details']) <= 5:
                        for trans in transform_result['transformations_applied']:
                            print(f"      Line {trans['line_number']}: {trans['description']}")
                            
            else:
                update_summary['failed_updates'] += 1
                update_summary['errors'].append({
                    'file': str(file_path.relative_to(self.base_path)),
                    'error': transform_result['error']
                })
                print(f"   ❌ Failed to update {file_path.relative_to(self.base_path)}: {transform_result['error']}")
                
        print(f"\n📊 Update Summary:")
        print(f"   Files processed: {update_summary['files_processed']}")
        print(f"   Files modified: {update_summary['files_modified']}")
        print(f"   Total transformations: {update_summary['total_transformations']}")
        print(f"   Successful updates: {update_summary['successful_updates']}")
        print(f"   Failed updates: {update_summary['failed_updates']}")
        
        return update_summary
        
    def create_transformation_report(self, summary: Dict[str, Any], 
                                   output_path: Path = None) -> Path:
        """Create detailed transformation report."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.base_path / "scripts" / "bsee_migration" / f"import_transformations_{timestamp}.yaml"
            
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            'transformation_report': {
                'timestamp': datetime.now().isoformat(),
                'base_path': str(self.base_path),
                'transformation_rules': self.matcher.transformation_rules,
                'summary': summary
            }
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(report, f, default_flow_style=False, sort_keys=False)
            
        print(f"📄 Transformation report saved to: {output_path}")
        return output_path
        
    def rollback_transformations(self, backup_pattern: str = "*.backup.*") -> Dict[str, Any]:
        """Rollback transformations using backup files."""
        print("🔄 Rolling back transformations from backups...")
        
        rollback_summary = {
            'backups_found': 0,
            'files_restored': 0,
            'failed_restorations': 0,
            'errors': []
        }
        
        # Find backup files
        backup_files = list(self.base_path.glob(f"**/{backup_pattern}"))
        rollback_summary['backups_found'] = len(backup_files)
        
        for backup_file in backup_files:
            try:
                # Determine original file path
                original_file = Path(str(backup_file).split('.backup.')[0] + '.py')
                
                if original_file.exists():
                    # Restore from backup
                    shutil.copy2(backup_file, original_file)
                    rollback_summary['files_restored'] += 1
                    print(f"   ✅ Restored: {original_file.relative_to(self.base_path)}")
                    
                    # Remove backup file
                    backup_file.unlink()
                    
            except Exception as e:
                rollback_summary['failed_restorations'] += 1
                rollback_summary['errors'].append({
                    'backup_file': str(backup_file.relative_to(self.base_path)),
                    'error': str(e)
                })
                print(f"   ❌ Failed to restore {backup_file.relative_to(self.base_path)}: {e}")
                
        print(f"\n📊 Rollback Summary:")
        print(f"   Backups found: {rollback_summary['backups_found']}")
        print(f"   Files restored: {rollback_summary['files_restored']}")
        print(f"   Failed restorations: {rollback_summary['failed_restorations']}")
        
        return rollback_summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update Python imports for BSEE consolidation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scan for transformable imports (dry run)
    python update_python_imports.py --scan-only
    
    # Update imports with backup (dry run)
    python update_python_imports.py --dry-run --backup
    
    # Actually update imports
    python update_python_imports.py --no-dry-run --backup
    
    # Update only specific patterns
    python update_python_imports.py --pattern="src/**/*.py" --no-dry-run
    
    # Rollback changes
    python update_python_imports.py --rollback
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Only simulate changes (default: True)'
    )
    parser.add_argument(
        '--no-dry-run',
        action='store_true',
        help='Actually perform changes'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        default=True,
        help='Create backups before modifying files (default: True)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create backups'
    )
    parser.add_argument(
        '--pattern',
        type=str,
        action='append',
        help='File patterns to include (can be used multiple times)'
    )
    parser.add_argument(
        '--scan-only',
        action='store_true',
        help='Only scan for transformable imports, do not modify'
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback previous transformations using backup files'
    )
    parser.add_argument(
        '--base-path',
        type=str,
        help='Base path for WorldEnergyData project'
    )
    
    args = parser.parse_args()
    
    # Handle argument logic
    dry_run = args.dry_run and not args.no_dry_run
    backup = args.backup and not args.no_backup
    include_patterns = args.pattern if args.pattern else None
    
    # Initialize updater
    updater = PythonImportsUpdater(base_path=args.base_path)
    
    if args.rollback:
        # Rollback transformations
        rollback_summary = updater.rollback_transformations()
        sys.exit(0 if rollback_summary['failed_restorations'] == 0 else 1)
        
    elif args.scan_only:
        # Only scan for imports
        scan_summary = updater.scan_codebase(include_patterns)
        updater.create_transformation_report(scan_summary)
        
    else:
        # Update imports
        update_summary = updater.update_imports(
            include_patterns=include_patterns,
            dry_run=dry_run,
            backup=backup
        )
        updater.create_transformation_report(update_summary)
        
        # Exit with appropriate code
        if update_summary['failed_updates'] > 0:
            sys.exit(1)
        else:
            print(f"\n🎉 Import updates {'simulated' if dry_run else 'completed'} successfully!")
            sys.exit(0)


if __name__ == "__main__":
    main()