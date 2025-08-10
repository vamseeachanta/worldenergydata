#!/usr/bin/env python3
"""
Link analysis and fixing system for documentation reorganization
Task 5.2: Update all internal links to reflect new file locations
"""

import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
import re
from datetime import datetime
from test_link_validation import LinkValidator, LinkValidationResult


class LinkAnalyzer:
    """Analyze current link status and identify issues"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_root = project_root / "docs"
        self.validator = LinkValidator(self.docs_root)
        
        # Known file relocations from our previous migration work
        self.known_relocations = {
            # Files that were moved from modules/ to data-sources/
            "modules/equipment/anchor/calculation.md": "data-sources/equipment/anchor/calculation.md",
            "modules/equipment/x_tree/x_tree.md": "data-sources/equipment/x_tree/x_tree.md", 
            "modules/onshore/wyoming/data.md": "data-sources/onshore/wyoming/data.md",
            # Files moved from root to appropriate sections
            "petrophysics.md": "data-sources/bsee/analysis/production/normalization_for_laterals.md",
            # Raw data relocations
            "raw_data/sodir/sodir.md": "data-sources/sodir/sodir.md"
        }
    
    def analyze_all_links(self) -> Dict:
        """Comprehensive analysis of all links in documentation"""
        print("=== LINK ANALYSIS ===")
        print("Analyzing all links in documentation...")
        
        # Validate all links
        all_results = self.validator.validate_all_links()
        
        # Categorize results
        categorized = self._categorize_link_results(all_results)
        
        # Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_links_found': len(all_results),
                'valid_links': len([r for r in all_results if r.is_valid]),
                'broken_links': len([r for r in all_results if not r.is_valid]),
                'internal_links': len([r for r in all_results if r.link_type == 'internal']),
                'external_links': len([r for r in all_results if r.link_type == 'external']),
                'anchor_links': len([r for r in all_results if r.link_type == 'anchor']),
                'email_links': len([r for r in all_results if r.link_type == 'email'])
            },
            'categorized_results': categorized,
            'fixable_links': self._identify_fixable_links(all_results),
            'files_with_issues': self._get_files_with_issues(all_results)
        }
        
        return report, all_results
    
    def _categorize_link_results(self, results: List[LinkValidationResult]) -> Dict:
        """Categorize link validation results"""
        categories = {
            'valid_internal': [],
            'valid_external': [],
            'valid_anchors': [],
            'valid_email': [],
            'broken_internal': [],
            'broken_external': [],
            'broken_anchors': [],
            'broken_email': []
        }
        
        for result in results:
            category_key = f"{'valid' if result.is_valid else 'broken'}_{result.link_type}"
            if category_key in categories:
                categories[category_key].append({
                    'source_file': str(result.source_file.relative_to(self.project_root)),
                    'link_text': result.link_text,
                    'link_target': result.link_target,
                    'line_number': result.line_number,
                    'error_message': result.error_message
                })
        
        return categories
    
    def _identify_fixable_links(self, results: List[LinkValidationResult]) -> Dict:
        """Identify links that can be automatically fixed"""
        fixable = {
            'relocations': [],
            'path_corrections': [],
            'case_corrections': []
        }
        
        for result in results:
            if not result.is_valid and result.link_type == 'internal':
                # Check if it's a known relocation
                target_path = result.link_target.split('#')[0]  # Remove anchor
                
                if target_path in self.known_relocations:
                    fixable['relocations'].append({
                        'source_file': str(result.source_file.relative_to(self.project_root)),
                        'old_target': result.link_target,
                        'new_target': self.known_relocations[target_path],
                        'line_number': result.line_number
                    })
                
                # Check for common path issues
                elif self._can_fix_path(result):
                    suggestion = self._suggest_path_fix(result)
                    if suggestion:
                        fixable['path_corrections'].append({
                            'source_file': str(result.source_file.relative_to(self.project_root)),
                            'old_target': result.link_target,
                            'suggested_target': suggestion,
                            'line_number': result.line_number
                        })
        
        return fixable
    
    def _can_fix_path(self, result: LinkValidationResult) -> bool:
        """Check if a broken path can be fixed"""
        target_path = result.link_target.split('#')[0]
        
        # Look for similar files in the docs structure
        target_name = Path(target_path).name
        if target_name:
            matching_files = list(self.docs_root.rglob(target_name))
            return len(matching_files) > 0
        
        return False
    
    def _suggest_path_fix(self, result: LinkValidationResult) -> str:
        """Suggest a corrected path for a broken link"""
        target_path = result.link_target.split('#')[0]
        anchor = '#' + result.link_target.split('#')[1] if '#' in result.link_target else ''
        
        target_name = Path(target_path).name
        if not target_name:
            return None
        
        # Find matching files
        matching_files = list(self.docs_root.rglob(target_name))
        if not matching_files:
            return None
        
        # Choose the best match (closest to source file)
        source_file = result.source_file
        best_match = matching_files[0]  # Just take the first match for now
        
        # Try to find the closest match by comparing path lengths
        source_parts = source_file.parts
        for candidate in matching_files:
            candidate_parts = candidate.parts
            # Count common path segments
            common_parts = 0
            for i, (s_part, c_part) in enumerate(zip(source_parts, candidate_parts)):
                if s_part == c_part:
                    common_parts += 1
                else:
                    break
            # Prefer files with more common path segments
            if common_parts > 0:
                best_match = candidate
                break
        
        # Calculate relative path from source to target
        try:
            relative_path = best_match.relative_to(source_file.parent)
            return str(relative_path) + anchor
        except ValueError:
            # Files are not in same tree, use absolute path from docs root
            try:
                relative_path = best_match.relative_to(self.docs_root)
                return str(relative_path) + anchor
            except ValueError:
                return None
    
    def _get_files_with_issues(self, results: List[LinkValidationResult]) -> Dict:
        """Get files that have link issues"""
        files_with_issues = {}
        
        for result in results:
            if not result.is_valid:
                file_path = str(result.source_file.relative_to(self.project_root))
                
                if file_path not in files_with_issues:
                    files_with_issues[file_path] = {
                        'broken_links': 0,
                        'issues': []
                    }
                
                files_with_issues[file_path]['broken_links'] += 1
                files_with_issues[file_path]['issues'].append({
                    'link_target': result.link_target,
                    'link_type': result.link_type,
                    'line_number': result.line_number,
                    'error': result.error_message
                })
        
        return files_with_issues


class LinkFixer:
    """Fix broken internal links based on analysis"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_root = project_root / "docs"
        self.fixes_applied = []
    
    def fix_all_links(self, fixable_links: Dict, dry_run: bool = True) -> Dict:
        """Fix all fixable links"""
        print(f"=== LINK FIXING {'(DRY RUN)' if dry_run else ''} ===")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'fixes_applied': 0,
            'fixes_failed': 0,
            'errors': []
        }
        
        # Fix known relocations
        relocation_fixes = fixable_links.get('relocations', [])
        for fix in relocation_fixes:
            try:
                success = self._apply_link_fix(
                    fix['source_file'], 
                    fix['old_target'], 
                    fix['new_target'],
                    dry_run
                )
                if success:
                    results['fixes_applied'] += 1
                    print(f"  [OK] Fixed relocation in {fix['source_file']}: {fix['old_target']} -> {fix['new_target']}")
                else:
                    results['fixes_failed'] += 1
                    
            except Exception as e:
                results['fixes_failed'] += 1
                results['errors'].append(f"Failed to fix {fix['source_file']}: {str(e)}")
                print(f"  [ERROR] Failed to fix {fix['source_file']}: {str(e)}")
        
        # Fix path corrections
        path_fixes = fixable_links.get('path_corrections', [])
        for fix in path_fixes:
            try:
                success = self._apply_link_fix(
                    fix['source_file'],
                    fix['old_target'],
                    fix['suggested_target'],
                    dry_run
                )
                if success:
                    results['fixes_applied'] += 1
                    print(f"  [OK] Fixed path in {fix['source_file']}: {fix['old_target']} -> {fix['suggested_target']}")
                else:
                    results['fixes_failed'] += 1
                    
            except Exception as e:
                results['fixes_failed'] += 1
                results['errors'].append(f"Failed to fix {fix['source_file']}: {str(e)}")
                print(f"  [ERROR] Failed to fix {fix['source_file']}: {str(e)}")
        
        print(f"\nLink fixing summary:")
        print(f"  Fixes applied: {results['fixes_applied']}")
        print(f"  Fixes failed: {results['fixes_failed']}")
        
        return results
    
    def _apply_link_fix(self, source_file: str, old_target: str, new_target: str, dry_run: bool) -> bool:
        """Apply a single link fix"""
        file_path = self.project_root / source_file
        
        if not file_path.exists():
            return False
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Use regex to replace the specific link
            # Match [text](old_target) pattern
            old_pattern = re.escape(old_target)
            pattern = rf'\[([^\]]+)\]\({old_pattern}\)'
            replacement = rf'[\1]({new_target})'
            
            new_content = re.sub(pattern, replacement, content)
            
            # Also handle reference-style links [text]: old_target
            ref_pattern = rf'(\[[^\]]+\]):\s*{old_pattern}'
            ref_replacement = rf'\1: {new_target}'
            new_content = re.sub(ref_pattern, ref_replacement, new_content)
            
            if new_content != content:
                if not dry_run:
                    file_path.write_text(new_content, encoding='utf-8')
                
                self.fixes_applied.append({
                    'file': source_file,
                    'old_target': old_target,
                    'new_target': new_target
                })
                return True
            
        except Exception as e:
            print(f"Error fixing link in {source_file}: {e}")
            return False
        
        return False


def main():
    """Main execution function for link analysis and fixing"""
    project_root = Path(__file__).parent
    
    print("Starting comprehensive link analysis and fixing...")
    
    # Analyze all links
    analyzer = LinkAnalyzer(project_root)
    report, all_results = analyzer.analyze_all_links()
    
    # Save analysis report
    report_file = project_root / "link_analysis_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nAnalysis complete! Report saved to {report_file}")
    
    # Print summary
    print("\n=== LINK ANALYSIS SUMMARY ===")
    summary = report['summary']
    print(f"Total links found: {summary['total_links_found']}")
    print(f"Valid links: {summary['valid_links']}")
    print(f"Broken links: {summary['broken_links']}")
    print(f"Internal links: {summary['internal_links']}")
    print(f"External links: {summary['external_links']}")
    print(f"Anchor links: {summary['anchor_links']}")
    
    # Show fixable links
    fixable = report['fixable_links']
    print(f"\n=== FIXABLE LINKS ===")
    print(f"Known relocations: {len(fixable['relocations'])}")
    print(f"Path corrections: {len(fixable['path_corrections'])}")
    print(f"Case corrections: {len(fixable['case_corrections'])}")
    
    if fixable['relocations']:
        print(f"\nRelocation fixes (sample):")
        for fix in fixable['relocations'][:3]:
            print(f"  {fix['source_file']}: {fix['old_target']} -> {fix['new_target']}")
    
    if fixable['path_corrections']:
        print(f"\nPath corrections (sample):")
        for fix in fixable['path_corrections'][:3]:
            print(f"  {fix['source_file']}: {fix['old_target']} -> {fix['suggested_target']}")
    
    # Show files with most issues
    files_with_issues = report['files_with_issues']
    if files_with_issues:
        print(f"\n=== FILES WITH MOST ISSUES ===")
        sorted_files = sorted(files_with_issues.items(), 
                            key=lambda x: x[1]['broken_links'], 
                            reverse=True)
        
        for file_path, file_info in sorted_files[:5]:
            print(f"  {file_path}: {file_info['broken_links']} broken links")
    
    # Fix links
    if fixable['relocations'] or fixable['path_corrections']:
        print(f"\n=== LINK FIXING ===")
        fixer = LinkFixer(project_root)
        
        # First do dry run
        print("Performing dry run...")
        dry_run_results = fixer.fix_all_links(fixable, dry_run=True)
        
        if dry_run_results['fixes_failed'] > 0:
            print(f"[WARNING] {dry_run_results['fixes_failed']} fixes failed in dry run")
            return
        
        print(f"[SUCCESS] Dry run completed - ready to apply {dry_run_results['fixes_applied']} fixes")
        
        # Apply actual fixes
        print("Applying fixes...")
        fix_results = fixer.fix_all_links(fixable, dry_run=False)
        
        # Save fix results
        fix_results_file = project_root / "link_fixing_results.json"
        with open(fix_results_file, 'w', encoding='utf-8') as f:
            json.dump(fix_results, f, indent=2, ensure_ascii=False)
        
        print(f"Fix results saved to {fix_results_file}")
    
    return report, all_results


if __name__ == "__main__":
    main()