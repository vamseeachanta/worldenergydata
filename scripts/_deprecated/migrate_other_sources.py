#!/usr/bin/env python3
"""
Migrate other data source documentation
Handles equipment, LNG, onshore, wind energy documentation
"""

import json
import shutil
from pathlib import Path


def migrate_other_data_sources(dry_run=True):
    """Migrate non-BSEE data source documentation"""
    project_root = Path(__file__).parent
    
    # Define migrations for specific known locations
    migrations = {
        # Equipment documentation
        "docs/modules/equipment": "docs/data-sources/equipment",
        
        # LNG documentation  
        "docs/modules/lng": "docs/data-sources/lng",
        
        # Onshore documentation
        "docs/modules/onshore": "docs/data-sources/onshore",
        
        # Wind energy (in raw_data)
        "docs/raw_data/wind": "docs/data-sources/wind",
        
        # SODIR data
        "docs/raw_data/sodir": "docs/data-sources/sodir"
    }
    
    migrated_files = []
    total_files = 0
    
    print("=== MIGRATING OTHER DATA SOURCES ===")
    
    for old_base, new_base in migrations.items():
        old_path = project_root / old_base
        
        if not old_path.exists():
            print(f"[SKIP] Directory not found: {old_base}")
            continue
        
        print(f"\\nMigrating: {old_base} -> {new_base}")
        
        # Find all markdown files in this directory
        md_files = list(old_path.rglob("*.md"))
        total_files += len(md_files)
        
        if not md_files:
            print(f"  No markdown files found in {old_base}")
            continue
        
        print(f"  Found {len(md_files)} files to migrate")
        
        for md_file in md_files:
            try:
                # Calculate relative path within the old base
                rel_path = md_file.relative_to(old_path)
                new_file_path = project_root / new_base / rel_path
                
                if dry_run:
                    print(f"  [DRY RUN] Would migrate: {md_file.relative_to(project_root)} -> {new_file_path.relative_to(project_root)}")
                else:
                    # Ensure destination directory exists
                    new_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file (use copy to preserve original)
                    shutil.copy2(str(md_file), str(new_file_path))
                    print(f"  [OK] Migrated: {md_file.name}")
                    
                migrated_files.append(str(md_file.relative_to(project_root)))
                
            except Exception as e:
                print(f"  [ERROR] Failed to migrate {md_file.name}: {e}")
    
    print(f"\\n=== MIGRATION SUMMARY ===")
    print(f"Total files processed: {total_files}")
    print(f"Successfully migrated: {len(migrated_files)}")
    if dry_run:
        print("DRY RUN - No files were actually moved")
    
    return migrated_files


def migrate_development_docs(dry_run=True):
    """Migrate development-related documentation"""
    project_root = Path(__file__).parent
    
    # Files that should go to development
    dev_files = [
        "docs/development_history.md",
        "docs/development/uv_usage.md"  # Already in right place
    ]
    
    print("\\n=== MIGRATING DEVELOPMENT DOCUMENTATION ===")
    
    migrated = 0
    for file_path in dev_files:
        full_path = project_root / file_path
        
        if not full_path.exists():
            print(f"[SKIP] File not found: {file_path}")
            continue
        
        # Check if already in development folder
        if "docs/development/" in file_path:
            print(f"[SKIP] Already in development folder: {file_path}")
            continue
        
        # Move to development folder
        new_path = project_root / "docs/development" / full_path.name
        
        if dry_run:
            print(f"[DRY RUN] Would migrate: {file_path} -> {new_path.relative_to(project_root)}")
        else:
            try:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(full_path), str(new_path))
                print(f"[OK] Migrated: {full_path.name}")
                migrated += 1
            except Exception as e:
                print(f"[ERROR] Failed to migrate {full_path.name}: {e}")
    
    print(f"Development files migrated: {migrated}")
    return migrated


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Other Data Sources")
    parser.add_argument('--execute', action='store_true', 
                        help='Execute actual migration (default is dry run)')
    
    args = parser.parse_args()
    dry_run = not args.execute
    
    # Migrate other data sources
    migrate_other_data_sources(dry_run=dry_run)
    
    # Migrate development docs
    migrate_development_docs(dry_run=dry_run)