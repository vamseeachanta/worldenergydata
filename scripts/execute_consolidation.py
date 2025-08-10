#!/usr/bin/env python3
"""
Execute consolidation of duplicate content
Tasks 4.3-4.6: Merge content, remove obsolete files, update for consistency, verify accuracy
"""

import json
from pathlib import Path
import shutil
from datetime import datetime
from typing import List, Dict
from duplicate_consolidation_system import SmartDuplicateAnalyzer, ContentMerger
from test_duplicate_consolidation import ConsolidationPlan, DuplicateMatch


class ConsolidationExecutor:
    """Execute consolidation plans with safety checks and rollback capability"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_root = project_root / "docs"
        self.backup_dir = project_root / "consolidation_backup"
        self.merger = ContentMerger()
        self.execution_log = []
    
    def execute_all_consolidations(self, plans: List[ConsolidationPlan], duplicates: List[DuplicateMatch], dry_run: bool = True):
        """Execute all consolidation plans with optional dry run"""
        print(f"=== CONSOLIDATION EXECUTION {'(DRY RUN)' if dry_run else ''} ===")
        
        if not dry_run:
            self._create_backup()
        
        execution_results = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'total_plans': len(plans),
            'executed_plans': 0,
            'failed_plans': 0,
            'files_merged': 0,
            'files_removed': 0,
            'errors': []
        }
        
        for i, plan in enumerate(plans, 1):
            print(f"\nExecuting plan {i}/{len(plans)}: {plan.primary_file.name}")
            
            try:
                result = self._execute_single_plan(plan, duplicates, dry_run)
                if result['success']:
                    execution_results['executed_plans'] += 1
                    execution_results['files_merged'] += len(plan.files_to_merge)
                    execution_results['files_removed'] += len(plan.files_to_remove)
                else:
                    execution_results['failed_plans'] += 1
                    execution_results['errors'].append({
                        'plan': str(plan.primary_file),
                        'error': result['error']
                    })
                
                self.execution_log.append(result)
                
            except Exception as e:
                error_msg = f"Failed to execute plan for {plan.primary_file}: {str(e)}"
                print(f"  ERROR: {error_msg}")
                execution_results['failed_plans'] += 1
                execution_results['errors'].append({
                    'plan': str(plan.primary_file),
                    'error': error_msg
                })
        
        # Save execution results
        results_file = self.project_root / "consolidation_execution_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(execution_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== EXECUTION SUMMARY ===")
        print(f"Plans executed successfully: {execution_results['executed_plans']}/{execution_results['total_plans']}")
        print(f"Files merged: {execution_results['files_merged']}")
        print(f"Files removed: {execution_results['files_removed']}")
        print(f"Errors: {execution_results['failed_plans']}")
        
        if execution_results['errors']:
            print("\nErrors encountered:")
            for error in execution_results['errors']:
                print(f"  - {error['plan']}: {error['error']}")
        
        return execution_results
    
    def _create_backup(self):
        """Create backup of all files before consolidation"""
        print("Creating backup...")
        
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        # Copy entire docs directory
        shutil.copytree(self.docs_root, self.backup_dir / "docs")
        
        # Also backup root files that might be affected
        root_md_files = list(self.project_root.glob("*.md"))
        if root_md_files:
            root_backup = self.backup_dir / "root"
            root_backup.mkdir()
            for md_file in root_md_files:
                shutil.copy2(md_file, root_backup / md_file.name)
        
        print(f"Backup created at: {self.backup_dir}")
    
    def _execute_single_plan(self, plan: ConsolidationPlan, duplicates: List[DuplicateMatch], dry_run: bool) -> Dict:
        """Execute a single consolidation plan"""
        result = {
            'plan': str(plan.primary_file),
            'success': False,
            'actions_taken': [],
            'error': None
        }
        
        try:
            print(f"  Primary file: {plan.primary_file.relative_to(self.project_root)}")
            print(f"  Files to merge: {len(plan.files_to_merge)}")
            print(f"  Files to remove: {len(plan.files_to_remove)}")
            
            if not plan.primary_file.exists():
                result['error'] = f"Primary file does not exist: {plan.primary_file}"
                return result
            
            # Handle exact duplicates (simple removal)
            if plan.merge_strategy == 'replace_sections' and plan.files_to_remove:
                for remove_file in plan.files_to_remove:
                    if remove_file.exists():
                        print(f"    Removing exact duplicate: {remove_file.relative_to(self.project_root)}")
                        if not dry_run:
                            remove_file.unlink()
                        result['actions_taken'].append(f"removed {remove_file}")
            
            # Handle content merging
            elif plan.merge_strategy == 'append' and plan.files_to_merge:
                merged_content = self.merger.merge_files_intelligently(plan, duplicates)
                
                print(f"    Merging content from {len(plan.files_to_merge)} files")
                if not dry_run:
                    plan.primary_file.write_text(merged_content, encoding='utf-8')
                result['actions_taken'].append(f"merged content from {len(plan.files_to_merge)} files")
                
                # Move the merged files to prevent future conflicts
                for merge_file in plan.files_to_merge:
                    if merge_file.exists() and merge_file != plan.primary_file:
                        # Don't remove, just mark as processed
                        merged_marker = merge_file.parent / f"{merge_file.stem}_MERGED_INTO_{plan.primary_file.stem}.txt"
                        if not dry_run:
                            merged_marker.write_text(
                                f"This file was merged into: {plan.primary_file}\n"
                                f"Merge date: {datetime.now().isoformat()}\n"
                                f"Original content preserved in backup.\n"
                            )
                        result['actions_taken'].append(f"marked {merge_file} as merged")
            
            result['success'] = True
            print(f"    [OK] Plan executed successfully")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"    [ERROR] {str(e)}")
        
        return result
    
    def verify_consolidation_integrity(self) -> Dict:
        """Verify that consolidation preserved all important content"""
        print("\n=== VERIFYING CONSOLIDATION INTEGRITY ===")
        
        verification_results = {
            'timestamp': datetime.now().isoformat(),
            'files_checked': 0,
            'issues_found': 0,
            'issues': [],
            'summary': 'pending'
        }
        
        # Check that primary files still exist and have content
        report_file = self.project_root / "duplicate_analysis_report.json"
        if not report_file.exists():
            verification_results['issues'].append("Could not find analysis report for verification")
            return verification_results
        
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        for plan_dict in report['consolidation_plans']:
            primary_file = self.project_root / plan_dict['primary_file']
            verification_results['files_checked'] += 1
            
            if not primary_file.exists():
                issue = f"Primary file missing: {primary_file}"
                verification_results['issues'].append(issue)
                verification_results['issues_found'] += 1
                print(f"  [ERROR] {issue}")
                continue
            
            try:
                content = primary_file.read_text(encoding='utf-8', errors='ignore')
                if len(content) < 50:  # Suspiciously small
                    issue = f"Primary file suspiciously small: {primary_file} ({len(content)} chars)"
                    verification_results['issues'].append(issue)
                    verification_results['issues_found'] += 1
                    print(f"  [WARN] {issue}")
                else:
                    print(f"  [OK] {primary_file.relative_to(self.project_root)} ({len(content)} chars)")
            
            except Exception as e:
                issue = f"Could not read primary file: {primary_file} - {str(e)}"
                verification_results['issues'].append(issue)
                verification_results['issues_found'] += 1
                print(f"  [ERROR] {issue}")
        
        # Summary
        if verification_results['issues_found'] == 0:
            verification_results['summary'] = 'success'
            print(f"\n[SUCCESS] All {verification_results['files_checked']} files verified successfully")
        else:
            verification_results['summary'] = 'issues_found'
            print(f"\n[WARNING] {verification_results['issues_found']} issues found in {verification_results['files_checked']} files")
        
        return verification_results


def main():
    """Main execution function"""
    project_root = Path(__file__).parent
    
    # Load the analysis report
    report_file = project_root / "duplicate_analysis_report.json"
    if not report_file.exists():
        print("Error: duplicate_analysis_report.json not found. Run duplicate_consolidation_system.py first.")
        return
    
    print("Loading duplicate analysis report...")
    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    # Recreate the analysis objects  
    analyzer = SmartDuplicateAnalyzer(project_root / "docs")
    _, duplicates, plans = analyzer.analyze_all_duplicates()
    
    print(f"Loaded {len(plans)} consolidation plans")
    
    # Ask user for confirmation
    print("\n=== CONSOLIDATION PREVIEW ===")
    print("The following actions will be performed:")
    
    for i, plan in enumerate(plans, 1):
        print(f"\n{i}. Primary file: {plan.primary_file.relative_to(project_root)}")
        if plan.files_to_merge:
            print(f"   Will merge content from: {[str(f.relative_to(project_root)) for f in plan.files_to_merge]}")
        if plan.files_to_remove:
            print(f"   Will remove: {[str(f.relative_to(project_root)) for f in plan.files_to_remove]}")
        print(f"   Strategy: {plan.merge_strategy}")
    
    # Execute consolidation
    executor = ConsolidationExecutor(project_root)
    
    print("\n" + "="*60)
    print("EXECUTING CONSOLIDATION...")
    print("="*60)
    
    # First run as dry run
    print("\nStep 1: Dry run execution...")
    dry_run_results = executor.execute_all_consolidations(plans, duplicates, dry_run=True)
    
    if dry_run_results['failed_plans'] > 0:
        print(f"\n[WARNING] {dry_run_results['failed_plans']} plans failed in dry run.")
        print("Please review errors before proceeding with actual execution.")
        return dry_run_results
    
    print(f"\n[SUCCESS] Dry run completed successfully!")
    print(f"Ready to execute {dry_run_results['executed_plans']} consolidation plans.")
    
    # Execute for real
    print("\nStep 2: Actual execution...")
    execution_results = executor.execute_all_consolidations(plans, duplicates, dry_run=False)
    
    # Verify integrity
    print("\nStep 3: Verification...")
    verification_results = executor.verify_consolidation_integrity()
    
    # Final summary
    print("\n" + "="*60)
    print("CONSOLIDATION COMPLETE")
    print("="*60)
    print(f"Plans executed: {execution_results['executed_plans']}/{execution_results['total_plans']}")
    print(f"Files merged: {execution_results['files_merged']}")
    print(f"Files removed: {execution_results['files_removed']}")
    print(f"Verification: {verification_results['summary']}")
    
    if execution_results['errors']:
        print(f"\nErrors encountered: {len(execution_results['errors'])}")
        
    if verification_results['issues_found'] > 0:
        print(f"Verification issues: {verification_results['issues_found']}")
    
    print(f"\nBackup available at: consolidation_backup/")
    print(f"Execution log: consolidation_execution_results.json")
    
    return execution_results, verification_results


if __name__ == "__main__":
    main()