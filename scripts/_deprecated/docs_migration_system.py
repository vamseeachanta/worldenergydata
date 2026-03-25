#!/usr/bin/env python3
"""
Documentation Migration System
Part of Task 3.2: Develop scripts for systematic file movement
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import argparse


class DocumentationMigrator:
    """Systematic documentation migration system with safety features"""
    
    def __init__(self, project_root: Optional[Path] = None, dry_run: bool = True):
        self.project_root = project_root or Path(__file__).parent
        self.docs_root = self.project_root / "docs"
        self.dry_run = dry_run
        self.migration_log = []
        self.backup_info = {}
        
        # Load migration mapping
        mapping_file = self.project_root / 'docs_analysis_report.json'
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.migration_mapping = data.get('migration_mapping', {})
        else:
            raise FileNotFoundError("Migration mapping not found. Run analysis first.")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash for file integrity verification"""
        if not file_path.exists():
            return ""
        
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.log_action(f"Error calculating hash for {file_path}: {e}", "ERROR")
            return ""
    
    def log_action(self, message: str, action_type: str = "INFO"):
        """Log migration actions for audit trail"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': action_type,
            'message': message
        }
        self.migration_log.append(log_entry)
        print(f"[{action_type}] {message}")
    
    def create_backup_info(self, file_path: Path) -> Dict:
        """Create backup information for rollback capability"""
        if not file_path.exists():
            return {}
        
        return {
            'original_path': str(file_path),
            'size': file_path.stat().st_size,
            'hash': self.calculate_file_hash(file_path),
            'mtime': file_path.stat().st_mtime,
            'backup_created': datetime.now().isoformat()
        }
    
    def validate_migration_mapping(self) -> List[str]:
        """Validate migration mapping for consistency and safety"""
        errors = []
        
        for old_path, migration_info in self.migration_mapping.items():
            # Check required fields
            required_fields = ['old_path', 'new_path', 'category', 'action']
            for field in required_fields:
                if field not in migration_info:
                    errors.append(f"Missing field '{field}' for {old_path}")
            
            # Check source file exists
            source_path = self.project_root / old_path
            if not source_path.exists():
                errors.append(f"Source file does not exist: {old_path}")
            
            # Validate destination path
            new_path = migration_info.get('new_path', '')
            if not new_path.startswith('docs/'):
                errors.append(f"Invalid destination path: {new_path}")
            
            # Check for potential conflicts
            dest_path = self.project_root / new_path
            if dest_path.exists() and str(dest_path) != str(source_path):
                errors.append(f"Destination already exists: {new_path}")
        
        return errors
    
    def prepare_migration(self) -> Dict:
        """Prepare migration by validating and planning"""
        self.log_action("Starting migration preparation", "INFO")
        
        # Validate mapping
        validation_errors = self.validate_migration_mapping()
        if validation_errors:
            for error in validation_errors:
                self.log_action(error, "ERROR")
            raise ValueError(f"Migration validation failed with {len(validation_errors)} errors")
        
        # Categorize migrations
        migration_categories = {}
        for old_path, migration_info in self.migration_mapping.items():
            category = migration_info['category']
            if category not in migration_categories:
                migration_categories[category] = []
            migration_categories[category].append((old_path, migration_info))
        
        # Prepare summary
        preparation_summary = {
            'total_files': len(self.migration_mapping),
            'categories': {cat: len(files) for cat, files in migration_categories.items()},
            'dry_run': self.dry_run,
            'validation_passed': True
        }
        
        self.log_action(f"Migration preparation complete: {preparation_summary}", "INFO")
        return preparation_summary
    
    def migrate_file(self, old_path: str, migration_info: Dict) -> bool:
        """Migrate single file with safety checks"""
        source_path = self.project_root / old_path
        dest_path = self.project_root / migration_info['new_path']
        
        try:
            # Create backup info
            if source_path.exists():
                self.backup_info[old_path] = self.create_backup_info(source_path)
            
            if self.dry_run:
                self.log_action(f"DRY RUN: Would migrate {old_path} -> {migration_info['new_path']}", "DRY_RUN")
                return True
            
            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Perform migration
            if source_path.exists():
                if dest_path.exists() and dest_path != source_path:
                    self.log_action(f"Destination exists, backing up: {dest_path}", "WARNING")
                    backup_path = dest_path.with_suffix(dest_path.suffix + '.backup')
                    shutil.move(str(dest_path), str(backup_path))
                
                # Move file
                shutil.move(str(source_path), str(dest_path))
                
                # Verify migration
                if dest_path.exists():
                    new_hash = self.calculate_file_hash(dest_path)
                    original_hash = self.backup_info[old_path]['hash']
                    
                    if new_hash == original_hash:
                        self.log_action(f"Successfully migrated: {old_path} -> {migration_info['new_path']}", "SUCCESS")
                        return True
                    else:
                        self.log_action(f"Hash mismatch after migration: {old_path}", "ERROR")
                        return False
                else:
                    self.log_action(f"Migration failed - destination not found: {migration_info['new_path']}", "ERROR")
                    return False
            else:
                self.log_action(f"Source file not found: {old_path}", "WARNING")
                return False
                
        except Exception as e:
            self.log_action(f"Error migrating {old_path}: {e}", "ERROR")
            return False
    
    def migrate_category(self, category: str, max_files: Optional[int] = None) -> Dict:
        """Migrate all files in a specific category"""
        self.log_action(f"Starting migration for category: {category}", "INFO")
        
        # Find files in category
        category_files = []
        for old_path, migration_info in self.migration_mapping.items():
            if migration_info['category'] == category:
                category_files.append((old_path, migration_info))
        
        if max_files:
            category_files = category_files[:max_files]
        
        # Migrate files
        results = {
            'category': category,
            'total_files': len(category_files),
            'successful': 0,
            'failed': 0,
            'failed_files': []
        }
        
        for old_path, migration_info in category_files:
            if self.migrate_file(old_path, migration_info):
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['failed_files'].append(old_path)
        
        self.log_action(f"Category {category} migration complete: {results['successful']}/{results['total_files']} successful", "INFO")
        return results
    
    def migrate_all(self) -> Dict:
        """Migrate all documentation files"""
        self.log_action("Starting complete migration", "INFO")
        
        # Prepare migration
        preparation = self.prepare_migration()
        
        # Migrate by category
        overall_results = {
            'preparation': preparation,
            'category_results': {},
            'overall_stats': {
                'total_files': 0,
                'successful': 0,
                'failed': 0
            }
        }
        
        # Process categories in order of importance
        category_order = [
            'data-sources/bsee',  # Largest category first
            'analysis-guides/economic-evaluation',
            'analysis-guides/production-analysis', 
            'analysis-guides/field-development',
            'data-sources/sodir',
            'data-sources/wind',
            'data-sources/lng',
            'data-sources/equipment',
            'data-sources/onshore',
            'user-guide',
            'development',
            'reference/literature',
            'reference/equipment-specs'
        ]
        
        for category in category_order:
            if category in preparation['categories']:
                category_result = self.migrate_category(category)
                overall_results['category_results'][category] = category_result
                
                # Update overall stats
                overall_results['overall_stats']['total_files'] += category_result['total_files']
                overall_results['overall_stats']['successful'] += category_result['successful']
                overall_results['overall_stats']['failed'] += category_result['failed']
        
        self.log_action(f"Complete migration finished: {overall_results['overall_stats']}", "INFO")
        return overall_results
    
    def save_migration_log(self, output_path: Optional[Path] = None) -> Path:
        """Save migration log for audit purposes"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.project_root / f"migration_log_{timestamp}.json"
        
        log_data = {
            'migration_metadata': {
                'timestamp': datetime.now().isoformat(),
                'dry_run': self.dry_run,
                'project_root': str(self.project_root)
            },
            'migration_log': self.migration_log,
            'backup_info': self.backup_info
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        self.log_action(f"Migration log saved to: {output_path}", "INFO")
        return output_path
    
    def verify_migration(self) -> Dict:
        """Verify migration results and check for issues"""
        self.log_action("Starting migration verification", "INFO")
        
        verification_results = {
            'files_checked': 0,
            'files_verified': 0,
            'missing_files': [],
            'hash_mismatches': [],
            'empty_directories': []
        }
        
        # Check migrated files
        for old_path, migration_info in self.migration_mapping.items():
            verification_results['files_checked'] += 1
            
            new_path = self.project_root / migration_info['new_path']
            
            if not new_path.exists():
                verification_results['missing_files'].append(migration_info['new_path'])
                continue
            
            # Verify content if we have backup info
            if old_path in self.backup_info:
                original_hash = self.backup_info[old_path]['hash']
                current_hash = self.calculate_file_hash(new_path)
                
                if original_hash == current_hash:
                    verification_results['files_verified'] += 1
                else:
                    verification_results['hash_mismatches'].append(migration_info['new_path'])
        
        # Check for empty directories that can be cleaned up
        for dir_path in self.docs_root.rglob('*'):
            if dir_path.is_dir():
                if not any(dir_path.iterdir()):
                    verification_results['empty_directories'].append(str(dir_path.relative_to(self.project_root)))
        
        self.log_action(f"Verification complete: {verification_results}", "INFO")
        return verification_results


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Documentation Migration System")
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Perform dry run without actual file moves')
    parser.add_argument('--execute', action='store_true', 
                        help='Execute actual migration (overrides dry-run)')
    parser.add_argument('--category', type=str,
                        help='Migrate only specific category')
    parser.add_argument('--verify', action='store_true',
                        help='Verify migration results')
    
    args = parser.parse_args()
    
    # Initialize migrator
    dry_run = args.dry_run and not args.execute
    migrator = DocumentationMigrator(dry_run=dry_run)
    
    try:
        if args.verify:
            # Verify existing migration
            results = migrator.verify_migration()
            print(f"\nVerification Results: {json.dumps(results, indent=2)}")
        elif args.category:
            # Migrate specific category
            results = migrator.migrate_category(args.category)
            print(f"\nCategory Migration Results: {json.dumps(results, indent=2)}")
        else:
            # Migrate all
            results = migrator.migrate_all()
            print(f"\nMigration Results: {json.dumps(results, indent=2)}")
        
        # Save log
        log_path = migrator.save_migration_log()
        print(f"\nMigration log saved to: {log_path}")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        migrator.log_action(f"Migration failed: {e}", "CRITICAL")
        migrator.save_migration_log()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())