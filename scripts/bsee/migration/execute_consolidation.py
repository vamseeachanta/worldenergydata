#!/usr/bin/env python3
"""
BSEE Data Consolidation Script
Execute approved data cleanup and reorganization
Generated: 2025-08-21
"""

import os
import shutil
import hashlib
import json
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

# Configuration
BASE_DIR = Path("data/modules/bsee")
BACKUP_DIR = Path(f"data/modules/bsee.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
APPROVAL_FILE = Path("specs/modules/bsee/consolidation/cleanup-proposal-approved.json")
LOG_FILE = Path("specs/modules/bsee/consolidation/migration_log.txt")

# Duplicates to delete (from legacy/)
DUPLICATES_TO_DELETE = [
    "legacy/data_for_analysis/all_bsee_blocks.csv",
    "legacy/data_for_analysis/completion_perforations.csv",
    "legacy/data_for_analysis/completion_properties.csv",
    "legacy/data_for_analysis/completion_summary.csv",
    "legacy/data_for_analysis/cut_casings.csv",
    "legacy/data_for_analysis/geology_markers.csv",
    "legacy/data_for_analysis/hydrocarbon_bearing_interval.csv",
    "legacy/data_for_analysis/production.csv",
    "legacy/data_for_analysis/ST_BP_and_tree_height.csv",
    "legacy/data_for_analysis/well_activity_bop_tests.csv",
    "legacy/data_for_analysis/well_activity_open_hole.csv",
    "legacy/data_for_analysis/well_activity_remarks.csv",
    "legacy/data_for_analysis/well_activity_summary.csv",
    "legacy/data_for_analysis/well_data.csv",
    "legacy/data_for_analysis/well_directional_surveys.csv",
    "legacy/data_for_analysis/well_tubulars.csv",
    # Legacy online raw well data duplicates
    "legacy/online_raw_well_data/all_bsee_blocks.csv",
    "legacy/online_raw_well_data/completion_perforations.csv",
    "legacy/online_raw_well_data/completion_properties.csv",
    "legacy/online_raw_well_data/completion_summary.csv",
    "legacy/online_raw_well_data/cut_casings.csv",
    "legacy/online_raw_well_data/hydrocarbon_bearing_interval.csv",
    "legacy/online_raw_well_data/production.csv",
    "legacy/online_raw_well_data/ST_BP_and_tree_height.csv",
    "legacy/online_raw_well_data/well_activity_bop_tests.csv",
    "legacy/online_raw_well_data/well_activity_open_hole.csv",
    "legacy/online_raw_well_data/well_activity_remarks.csv",
    "legacy/online_raw_well_data/well_activity_summary.csv",
    "legacy/online_raw_well_data/well_data.csv",
    "legacy/online_raw_well_data/well_directional_surveys.csv",
    "legacy/online_raw_well_data/well_tubulars.csv",
    # Additional legacy duplicates
    "legacy/online_raw_well_data/boreholes.csv",
    "legacy/online_raw_well_data/pipeline.csv",
    "legacy/online_raw_well_data/pipeline_inspections.csv",
    "legacy/online_raw_well_data/pipeline_movements.csv",
    "legacy/online_raw_well_data/platform_structure.csv",
    "legacy/online_raw_well_data/platform_structure_inspections.csv",
    "legacy/online_raw_well_data/production_2016.csv",
    "legacy/online_raw_well_data/production_data.csv",
    "legacy/online_raw_well_data/resource_limit.csv",
    "legacy/online_raw_well_data/ST_BP_and_tree_height_STBP.csv",
    "legacy/online_raw_well_data/well_operations_remarks.csv",
    "legacy/online_raw_well_data/well_tests.csv",
    "legacy/online_raw_well_data/wells_all_meta_data.csv"
]

# File reorganization mapping
FILE_MAPPINGS = {
    # Production data
    "analysis_data/combined_data_for_analysis/production.csv": "current/production/production.csv",
    
    # Wells data
    "analysis_data/combined_data_for_analysis/well_data.csv": "current/wells/well_data.csv",
    "analysis_data/combined_data_for_analysis/well_directional_surveys.csv": "current/wells/well_directional_surveys.csv",
    "analysis_data/combined_data_for_analysis/boreholes.csv": "current/wells/boreholes.csv",
    "analysis_data/combined_data_for_analysis/well_tubulars.csv": "current/wells/well_tubulars.csv",
    
    # Completions data
    "analysis_data/combined_data_for_analysis/completion_perforations.csv": "current/completions/completion_perforations.csv",
    "analysis_data/combined_data_for_analysis/completion_properties.csv": "current/completions/completion_properties.csv",
    "analysis_data/combined_data_for_analysis/completion_summary.csv": "current/completions/completion_summary.csv",
    
    # Operations data
    "analysis_data/combined_data_for_analysis/well_activity_bop_tests.csv": "current/operations/well_activity_bop_tests.csv",
    "analysis_data/combined_data_for_analysis/well_activity_open_hole.csv": "current/operations/well_activity_open_hole.csv",
    "analysis_data/combined_data_for_analysis/well_activity_remarks.csv": "current/operations/well_activity_remarks.csv",
    "analysis_data/combined_data_for_analysis/well_activity_summary.csv": "current/operations/well_activity_summary.csv",
    "analysis_data/combined_data_for_analysis/ST_BP_and_tree_height.csv": "current/operations/ST_BP_and_tree_height.csv",
    "analysis_data/combined_data_for_analysis/cut_casings.csv": "current/operations/cut_casings.csv",
    
    # Geology data
    "analysis_data/combined_data_for_analysis/geology_markers.csv": "current/geology/geology_markers.csv",
    "analysis_data/combined_data_for_analysis/hydrocarbon_bearing_interval.csv": "current/geology/hydrocarbon_bearing_interval.csv",
    
    # Infrastructure data
    "analysis_data/combined_data_for_analysis/all_bsee_blocks.csv": "current/infrastructure/all_bsee_blocks.csv",
    "analysis_data/combined_data_for_analysis/pipeline.csv": "current/infrastructure/pipeline.csv",
    "analysis_data/combined_data_for_analysis/platform_structure.csv": "current/infrastructure/platform_structure.csv",
}


class BSEEMigration:
    def __init__(self):
        self.log_messages = []
        self.deleted_files = []
        self.moved_files = []
        self.archived_files = []
        self.errors = []
        
    def log(self, message: str):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.log_messages.append(log_entry)
        
    def verify_approval(self) -> bool:
        """Verify that cleanup has been approved"""
        if not APPROVAL_FILE.exists():
            self.log("ERROR: Approval file not found")
            return False
            
        with open(APPROVAL_FILE, 'r') as f:
            approval_data = json.load(f)
            
        if approval_data.get('approval_status') != 'APPROVED':
            self.log("ERROR: Cleanup not approved")
            return False
            
        self.log(f"Cleanup approved by {approval_data.get('approved_by')} on {approval_data.get('approval_date')}")
        return True
        
    def create_backup(self) -> bool:
        """Create full backup of current structure"""
        try:
            if BACKUP_DIR.exists():
                self.log(f"Backup already exists at {BACKUP_DIR}")
                return True
                
            self.log(f"Creating backup at {BACKUP_DIR}")
            shutil.copytree(BASE_DIR, BACKUP_DIR)
            self.log("Backup created successfully")
            return True
        except Exception as e:
            self.log(f"ERROR creating backup: {e}")
            self.errors.append(str(e))
            return False
            
    def delete_duplicates(self) -> bool:
        """Delete identified duplicate files"""
        self.log("Starting duplicate deletion...")
        
        for file_path in DUPLICATES_TO_DELETE:
            full_path = BASE_DIR / file_path
            if full_path.exists():
                try:
                    file_size = full_path.stat().st_size
                    full_path.unlink()
                    self.deleted_files.append(str(file_path))
                    self.log(f"Deleted: {file_path} ({file_size:,} bytes)")
                except Exception as e:
                    self.log(f"ERROR deleting {file_path}: {e}")
                    self.errors.append(f"Delete failed: {file_path}")
                    
        self.log(f"Deleted {len(self.deleted_files)} duplicate files")
        return True
        
    def reorganize_files(self) -> bool:
        """Move and reorganize files to new structure"""
        self.log("Starting file reorganization...")
        
        for source, destination in FILE_MAPPINGS.items():
            source_path = BASE_DIR / source
            dest_path = BASE_DIR / destination
            
            if source_path.exists():
                try:
                    # Create destination directory if needed
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Move the file
                    shutil.move(str(source_path), str(dest_path))
                    self.moved_files.append((str(source), str(destination)))
                    self.log(f"Moved: {source} -> {destination}")
                except Exception as e:
                    self.log(f"ERROR moving {source}: {e}")
                    self.errors.append(f"Move failed: {source}")
                    
        self.log(f"Moved {len(self.moved_files)} files")
        return True
        
    def archive_legacy(self) -> bool:
        """Archive remaining legacy directory"""
        self.log("Archiving legacy directory...")
        
        legacy_dir = BASE_DIR / "legacy"
        archive_dir = BASE_DIR / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        archive_path = archive_dir / f"{datetime.now().strftime('%Y-%m-%d')}-legacy.tar.gz"
        
        if legacy_dir.exists():
            try:
                # Count files to archive
                files_to_archive = list(legacy_dir.rglob("*"))
                file_count = sum(1 for f in files_to_archive if f.is_file())
                
                # Create tarball
                with tarfile.open(archive_path, "w:gz") as tar:
                    tar.add(legacy_dir, arcname="legacy")
                    
                self.archived_files.append(str(archive_path))
                self.log(f"Archived {file_count} files to {archive_path}")
                
                # Remove original legacy directory
                shutil.rmtree(legacy_dir)
                self.log("Removed original legacy directory")
                
                return True
            except Exception as e:
                self.log(f"ERROR archiving legacy: {e}")
                self.errors.append(f"Archive failed: {e}")
                return False
        else:
            self.log("Legacy directory not found, skipping archive")
            return True
            
    def organize_binary_files(self) -> bool:
        """Move binary files to raw/binary directory"""
        self.log("Organizing binary files...")
        
        bin_dir = BASE_DIR / "bin"
        raw_binary_dir = BASE_DIR / "raw" / "binary"
        
        if bin_dir.exists():
            try:
                raw_binary_dir.mkdir(parents=True, exist_ok=True)
                
                for bin_file in bin_dir.glob("*.bin"):
                    dest = raw_binary_dir / bin_file.name
                    shutil.move(str(bin_file), str(dest))
                    self.moved_files.append((f"bin/{bin_file.name}", f"raw/binary/{bin_file.name}"))
                    self.log(f"Moved binary: {bin_file.name}")
                    
                # Remove empty bin directory
                if not list(bin_dir.iterdir()):
                    bin_dir.rmdir()
                    self.log("Removed empty bin directory")
                    
                return True
            except Exception as e:
                self.log(f"ERROR organizing binary files: {e}")
                self.errors.append(f"Binary organization failed: {e}")
                return False
        else:
            self.log("Binary directory not found, skipping")
            return True
            
    def organize_zip_files(self) -> bool:
        """Move zip files to raw/compressed directory"""
        self.log("Organizing zip files...")
        
        zip_dir = BASE_DIR / "zip"
        raw_compressed_dir = BASE_DIR / "raw" / "compressed"
        
        if zip_dir.exists():
            try:
                raw_compressed_dir.mkdir(parents=True, exist_ok=True)
                
                for zip_file in zip_dir.glob("*.zip"):
                    dest = raw_compressed_dir / zip_file.name
                    shutil.move(str(zip_file), str(dest))
                    self.moved_files.append((f"zip/{zip_file.name}", f"raw/compressed/{zip_file.name}"))
                    self.log(f"Moved zip: {zip_file.name}")
                    
                # Remove empty zip directory
                if not list(zip_dir.iterdir()):
                    zip_dir.rmdir()
                    self.log("Removed empty zip directory")
                    
                return True
            except Exception as e:
                self.log(f"ERROR organizing zip files: {e}")
                self.errors.append(f"Zip organization failed: {e}")
                return False
        else:
            self.log("Zip directory not found, skipping")
            return True
            
    def cleanup_empty_directories(self) -> bool:
        """Remove any empty directories left after migration"""
        self.log("Cleaning up empty directories...")
        
        empty_dirs = []
        for dirpath, dirnames, filenames in os.walk(BASE_DIR, topdown=False):
            if not dirnames and not filenames:
                empty_dirs.append(dirpath)
                try:
                    Path(dirpath).rmdir()
                    self.log(f"Removed empty directory: {dirpath}")
                except:
                    pass
                    
        self.log(f"Removed {len(empty_dirs)} empty directories")
        return True
        
    def write_summary(self):
        """Write migration summary"""
        summary = [
            "=" * 60,
            "BSEE DATA MIGRATION SUMMARY",
            "=" * 60,
            f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Files Deleted: {len(self.deleted_files)}",
            f"Files Moved: {len(self.moved_files)}",
            f"Files Archived: {len(self.archived_files)}",
            f"Errors Encountered: {len(self.errors)}",
            "",
        ]
        
        if self.errors:
            summary.append("ERRORS:")
            for error in self.errors:
                summary.append(f"  - {error}")
            summary.append("")
            
        # Write to log file
        with open(LOG_FILE, 'w') as f:
            f.write("\n".join(self.log_messages))
            f.write("\n\n")
            f.write("\n".join(summary))
            
        # Display summary
        for line in summary:
            print(line)
            
    def execute(self) -> bool:
        """Execute the complete migration"""
        self.log("Starting BSEE data consolidation...")
        
        # Step 1: Verify approval
        if not self.verify_approval():
            self.log("Migration aborted: No approval")
            return False
            
        # Step 2: Create backup (already done, but verify)
        if not BACKUP_DIR.exists():
            if not self.create_backup():
                self.log("Migration aborted: Backup failed")
                return False
                
        # Step 3: Delete duplicates
        self.delete_duplicates()
        
        # Step 4: Reorganize files
        self.reorganize_files()
        
        # Step 5: Archive legacy
        self.archive_legacy()
        
        # Step 6: Organize binary files
        self.organize_binary_files()
        
        # Step 7: Organize zip files
        self.organize_zip_files()
        
        # Step 8: Cleanup empty directories
        self.cleanup_empty_directories()
        
        # Step 9: Write summary
        self.write_summary()
        
        if self.errors:
            self.log(f"Migration completed with {len(self.errors)} errors")
            return False
        else:
            self.log("Migration completed successfully!")
            return True


if __name__ == "__main__":
    migration = BSEEMigration()
    success = migration.execute()
    exit(0 if success else 1)