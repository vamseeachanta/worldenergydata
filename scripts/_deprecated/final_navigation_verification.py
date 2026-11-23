#!/usr/bin/env python3
"""
Final verification of navigation and cross-references
Task 5.6: Verify all links work correctly and navigation is intuitive
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict
from test_link_validation import LinkValidator, NavigationAnalyzer


class NavigationVerifier:
    """Comprehensive verification of navigation structure and links"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_root = project_root / "docs"
        self.validator = LinkValidator(self.docs_root)
        self.analyzer = NavigationAnalyzer(self.docs_root)
    
    def verify_complete_navigation(self) -> Dict:
        """Complete verification of navigation structure"""
        print("=== FINAL NAVIGATION VERIFICATION ===")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'verification_passed': True,
            'issues': [],
            'summary': {}
        }
        
        # 1. Verify all links work
        print("\n1. Verifying all internal links...")
        link_results = self._verify_all_links()
        results['link_verification'] = link_results
        
        if link_results['broken_links'] > 0:
            results['verification_passed'] = False
            results['issues'].append(f"{link_results['broken_links']} broken links found")
        
        # 2. Verify navigation structure completeness
        print("\n2. Verifying navigation structure...")
        nav_results = self._verify_navigation_structure()
        results['navigation_verification'] = nav_results
        
        if nav_results['missing_indexes'] > 0:
            results['verification_passed'] = False
            results['issues'].append(f"{nav_results['missing_indexes']} missing navigation indexes")
        
        # 3. Verify user type entry points
        print("\n3. Verifying user type entry points...")
        entry_results = self._verify_user_entry_points()
        results['entry_point_verification'] = entry_results
        
        if not entry_results['all_entry_points_valid']:
            results['verification_passed'] = False
            results['issues'].append("Some user entry points are broken")
        
        # 4. Verify cross-references
        print("\n4. Verifying cross-references...")
        cross_ref_results = self._verify_cross_references()
        results['cross_reference_verification'] = cross_ref_results
        
        # 5. Overall assessment
        results['summary'] = {
            'total_links_checked': link_results['total_links'],
            'broken_links': link_results['broken_links'],
            'navigation_indexes_present': nav_results['indexes_present'],
            'user_entry_points_working': entry_results['working_entry_points'],
            'cross_references_found': cross_ref_results['cross_references_count']
        }
        
        return results
    
    def _verify_all_links(self) -> Dict:
        """Verify all links in documentation"""
        all_results = self.validator.validate_all_links()
        
        broken_links = [r for r in all_results if not r.is_valid]
        
        print(f"  Total links found: {len(all_results)}")
        print(f"  Broken links: {len(broken_links)}")
        
        if broken_links:
            print("  Broken links details:")
            for link in broken_links[:5]:  # Show first 5
                print(f"    - {link.source_file.name}: {link.link_target} ({link.link_type})")
            if len(broken_links) > 5:
                print(f"    ... and {len(broken_links) - 5} more")
        else:
            print("  [OK] All links are working!")
        
        return {
            'total_links': len(all_results),
            'broken_links': len(broken_links),
            'broken_link_details': [
                {
                    'source_file': str(r.source_file.relative_to(self.project_root)),
                    'link_target': r.link_target,
                    'link_type': r.link_type,
                    'error': r.error_message
                } for r in broken_links
            ]
        }
    
    def _verify_navigation_structure(self) -> Dict:
        """Verify navigation structure is complete"""
        nav_structure = self.analyzer.analyze_navigation_structure()
        
        expected_sections = ['data-sources', 'user-guide', 'analysis-guides', 
                           'development', 'reference', 'examples']
        
        missing_indexes = []
        for section in expected_sections:
            if section not in nav_structure.section_indexes:
                section_dir = self.docs_root / section
                if section_dir.exists():
                    missing_indexes.append(section)
        
        print(f"  Navigation indexes present: {len(nav_structure.section_indexes)}")
        print(f"  Missing indexes: {len(missing_indexes)}")
        
        if missing_indexes:
            print(f"    Missing: {', '.join(missing_indexes)}")
        else:
            print("  [OK] All expected navigation indexes present!")
        
        return {
            'indexes_present': len(nav_structure.section_indexes),
            'missing_indexes': len(missing_indexes),
            'missing_index_details': missing_indexes,
            'main_entry_point': 'main' in nav_structure.entry_points
        }
    
    def _verify_user_entry_points(self) -> Dict:
        """Verify user type entry points work correctly"""
        main_readme = self.docs_root / "README.md"
        
        if not main_readme.exists():
            return {
                'all_entry_points_valid': False,
                'working_entry_points': 0,
                'total_entry_points': 0,
                'error': 'Main README.md not found'
            }
        
        # Key entry points for each user type
        user_entry_points = {
            'energy_professional': [
                'user-guide/',
                'data-sources/',
                'analysis-guides/',
                'examples/'
            ],
            'data_analyst': [
                'data-sources/',
                'analysis-guides/', 
                'reference/',
                'examples/'
            ],
            'developer': [
                'development/',
                'reference/',
                'user-guide/',
                'examples/'
            ]
        }
        
        working_points = 0
        total_points = 0
        broken_points = []
        
        for user_type, entry_points in user_entry_points.items():
            for entry_point in entry_points:
                total_points += 1
                entry_path = self.docs_root / entry_point
                
                if entry_path.exists():
                    working_points += 1
                else:
                    broken_points.append(f"{user_type}: {entry_point}")
        
        print(f"  Working entry points: {working_points}/{total_points}")
        
        if broken_points:
            print("  Broken entry points:")
            for point in broken_points:
                print(f"    - {point}")
        else:
            print("  [OK] All user entry points are working!")
        
        return {
            'all_entry_points_valid': len(broken_points) == 0,
            'working_entry_points': working_points,
            'total_entry_points': total_points,
            'broken_entry_points': broken_points
        }
    
    def _verify_cross_references(self) -> Dict:
        """Verify cross-references between sections"""
        cross_refs = self.analyzer._find_cross_references()
        
        valid_cross_refs = 0
        broken_cross_refs = 0
        
        for source, target, relation in cross_refs:
            if source.exists() and target.exists():
                valid_cross_refs += 1
            else:
                broken_cross_refs += 1
        
        print(f"  Cross-references found: {len(cross_refs)}")
        print(f"  Valid cross-references: {valid_cross_refs}")
        print(f"  Broken cross-references: {broken_cross_refs}")
        
        if broken_cross_refs == 0:
            print("  [OK] All cross-references are valid!")
        
        return {
            'cross_references_count': len(cross_refs),
            'valid_cross_references': valid_cross_refs,
            'broken_cross_references': broken_cross_refs
        }


def main():
    """Main verification function"""
    project_root = Path(__file__).parent
    
    print("Starting final navigation and cross-reference verification...")
    
    verifier = NavigationVerifier(project_root)
    results = verifier.verify_complete_navigation()
    
    # Save results
    results_file = project_root / "navigation_verification_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== FINAL VERIFICATION SUMMARY ===")
    summary = results['summary']
    print(f"Total links checked: {summary['total_links_checked']}")
    print(f"Broken links: {summary['broken_links']}")
    print(f"Navigation indexes: {summary['navigation_indexes_present']}")
    print(f"Working user entry points: {summary['user_entry_points_working']}")
    print(f"Cross-references found: {summary['cross_references_found']}")
    
    if results['verification_passed']:
        print(f"\n[SUCCESS] Navigation verification PASSED!")
        print("[OK] All links working")
        print("[OK] Navigation structure complete")
        print("[OK] User entry points functional")
        print("[OK] Cross-references validated")
    else:
        print(f"\n[WARNING] Navigation verification found issues:")
        for issue in results['issues']:
            print(f"  - {issue}")
    
    print(f"\nDetailed results saved to: {results_file}")
    
    # Return appropriate exit code
    return 0 if results['verification_passed'] else 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)