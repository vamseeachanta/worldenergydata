#!/usr/bin/env python3
"""
BSEE Data Consolidation - Compatibility Links Cleanup Script

Removes compatibility links after 30 days to complete the migration process.
This script should be run after verifying all systems have migrated to the new structure.

Usage:
    python cleanup_compatibility_links.py [--dry-run] [--force] [--days=30]
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


class CompatibilityLinksCleanup:
    """Manages cleanup of compatibility links after migration period."""
    
    def __init__(self, base_path: str = None, days_threshold: int = 30):
        """Initialize cleanup manager.
        
        Args:
            base_path: Base path for WorldEnergyData project
            days_threshold: Days after which to remove compatibility links
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.days_threshold = days_threshold
        self.migration_config_path = self.base_path / "scripts" / "bsee_migration" / "migration_config.yaml"
        self.cleanup_log_path = self.base_path / "scripts" / "bsee_migration" / "cleanup_log.yaml"
        
    def load_migration_config(self) -> Dict:
        """Load migration configuration."""
        try:
            with open(self.migration_config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"❌ Migration config not found: {self.migration_config_path}")
            return {}
            
    def check_link_age(self, link_path: Path) -> Tuple[bool, int]:
        """Check if compatibility link is old enough for removal.
        
        Args:
            link_path: Path to the compatibility link
            
        Returns:
            Tuple of (should_remove, age_in_days)
        """
        try:
            if not link_path.exists():
                return False, 0
                
            creation_time = link_path.stat().st_ctime
            age = datetime.now() - datetime.fromtimestamp(creation_time)
            age_days = age.days
            
            return age_days >= self.days_threshold, age_days
        except Exception as e:
            print(f"⚠️  Error checking link age for {link_path}: {e}")
            return False, 0
            
    def find_compatibility_links(self) -> List[Path]:
        """Find all compatibility links created during migration."""
        compatibility_links = []
        
        # Common patterns for compatibility links
        patterns = [
            "**/bsee_data_original*",
            "**/bsee_data_backup*",
            "**/legacy_bsee*",
            "**/old_bsee*"
        ]
        
        for pattern in patterns:
            for path in self.base_path.glob(pattern):
                if path.is_symlink() or path.name.endswith(('.bak', '.old', '.legacy')):
                    compatibility_links.append(path)
                    
        return compatibility_links
        
    def verify_migration_success(self) -> bool:
        """Verify that migration was successful before cleanup."""
        config = self.load_migration_config()
        if not config:
            return False
            
        # Check if consolidated structure exists
        consolidated_path = self.base_path / "src" / "worldenergydata" / "bsee"
        if not consolidated_path.exists():
            print(f"❌ Consolidated structure not found: {consolidated_path}")
            return False
            
        # Check for key modules
        key_modules = ['data_collection.py', 'analysis.py', 'processing.py']
        for module in key_modules:
            module_path = consolidated_path / module
            if not module_path.exists():
                print(f"❌ Key module missing: {module_path}")
                return False
                
        print("✅ Migration success verified")
        return True
        
    def remove_compatibility_link(self, link_path: Path, dry_run: bool = True) -> bool:
        """Remove a compatibility link.
        
        Args:
            link_path: Path to the compatibility link
            dry_run: If True, only simulate removal
            
        Returns:
            True if removal was successful (or would be in dry-run)
        """
        try:
            if dry_run:
                print(f"🔍 Would remove: {link_path}")
                return True
            else:
                if link_path.is_symlink():
                    link_path.unlink()
                elif link_path.is_dir():
                    import shutil
                    shutil.rmtree(link_path)
                else:
                    link_path.unlink()
                print(f"🗑️  Removed: {link_path}")
                return True
        except Exception as e:
            print(f"❌ Error removing {link_path}: {e}")
            return False
            
    def create_cleanup_report(self, removed_links: List[Path], failed_links: List[Path]) -> None:
        """Create cleanup report and log."""
        report = {
            'cleanup_date': datetime.now().isoformat(),
            'days_threshold': self.days_threshold,
            'total_links_found': len(removed_links) + len(failed_links),
            'successfully_removed': len(removed_links),
            'failed_removals': len(failed_links),
            'removed_links': [str(link) for link in removed_links],
            'failed_links': [str(link) for link in failed_links]
        }
        
        # Save cleanup log
        with open(self.cleanup_log_path, 'w') as f:
            yaml.dump(report, f, default_flow_style=False, sort_keys=False)
            
        print(f"\n📊 Cleanup Summary:")
        print(f"   Total compatibility links found: {report['total_links_found']}")
        print(f"   Successfully removed: {report['successfully_removed']}")
        print(f"   Failed removals: {report['failed_removals']}")
        print(f"   Report saved to: {self.cleanup_log_path}")
        
    def run_cleanup(self, dry_run: bool = True, force: bool = False) -> None:
        """Run the cleanup process.
        
        Args:
            dry_run: If True, only simulate cleanup
            force: If True, skip age verification
        """
        print(f"🧹 Starting compatibility links cleanup (dry_run={dry_run})")
        print(f"   Days threshold: {self.days_threshold}")
        
        # Verify migration success
        if not force and not self.verify_migration_success():
            print("❌ Migration verification failed. Use --force to override.")
            return
            
        # Find compatibility links
        compatibility_links = self.find_compatibility_links()
        if not compatibility_links:
            print("✅ No compatibility links found")
            return
            
        print(f"🔍 Found {len(compatibility_links)} compatibility links")
        
        removed_links = []
        failed_links = []
        
        for link_path in compatibility_links:
            should_remove, age_days = self.check_link_age(link_path)
            
            if force or should_remove:
                print(f"📅 Link age: {age_days} days - {link_path}")
                if self.remove_compatibility_link(link_path, dry_run):
                    removed_links.append(link_path)
                else:
                    failed_links.append(link_path)
            else:
                print(f"⏳ Skipping (age: {age_days} days < {self.days_threshold}): {link_path}")
                
        if not dry_run:
            self.create_cleanup_report(removed_links, failed_links)
        else:
            print(f"\n🔍 Dry run complete. Use --no-dry-run to actually remove {len(removed_links)} links")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup BSEE migration compatibility links",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry run (default)
    python cleanup_compatibility_links.py
    
    # Actually remove links older than 30 days
    python cleanup_compatibility_links.py --no-dry-run
    
    # Force removal regardless of age
    python cleanup_compatibility_links.py --no-dry-run --force
    
    # Custom age threshold
    python cleanup_compatibility_links.py --days=60
        """
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        default=True,
        help='Only simulate cleanup (default: True)'
    )
    parser.add_argument(
        '--no-dry-run', 
        action='store_true',
        help='Actually perform cleanup'
    )
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Force cleanup regardless of age or verification'
    )
    parser.add_argument(
        '--days', 
        type=int, 
        default=30,
        help='Days threshold for removing links (default: 30)'
    )
    parser.add_argument(
        '--base-path',
        type=str,
        help='Base path for WorldEnergyData project'
    )
    
    args = parser.parse_args()
    
    # Handle dry-run logic
    dry_run = args.dry_run and not args.no_dry_run
    
    cleanup_manager = CompatibilityLinksCleanup(
        base_path=args.base_path,
        days_threshold=args.days
    )
    
    cleanup_manager.run_cleanup(dry_run=dry_run, force=args.force)


if __name__ == "__main__":
    main()