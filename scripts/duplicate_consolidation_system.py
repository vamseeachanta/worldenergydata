#!/usr/bin/env python3
"""
Comprehensive duplicate content detection and consolidation system
Task 4.2-4.6: Complete duplicate consolidation workflow
"""

import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, asdict
import difflib
import hashlib
from collections import defaultdict
import re

# Import our test classes for actual implementation
from test_duplicate_consolidation import DuplicateDetector, ContentConsolidator, DuplicateMatch, ConsolidationPlan


class SmartDuplicateAnalyzer:
    """Enhanced duplicate analyzer with domain-specific intelligence"""
    
    def __init__(self, docs_root: Path):
        self.docs_root = docs_root
        self.detector = DuplicateDetector(docs_root)
        self.consolidator = ContentConsolidator(docs_root)
        
        # Domain-specific patterns
        self.header_patterns = [
            r'^# .+$',  # H1 headers
            r'^## .+$', # H2 headers
            r'^### .+$' # H3 headers
        ]
        
        # File patterns that indicate potential duplicates
        self.suspicious_patterns = [
            ('copy', 'duplicate'),
            ('backup', 'old'),
            ('temp', 'tmp'),
            ('_2', '_copy'),
            ('draft', 'final')
        ]
    
    def analyze_all_duplicates(self) -> Dict:
        """Comprehensive analysis of all duplicate content"""
        print("=== DUPLICATE CONTENT ANALYSIS ===")
        print("Scanning documentation for duplicate content...")
        
        # Find all duplicates
        duplicates = self.detector.find_all_duplicates()
        print(f"Found {len(duplicates)} potential duplicate pairs")
        
        # Categorize duplicates
        categorized = self._categorize_duplicates(duplicates)
        
        # Create consolidation plans
        plans = self.consolidator.create_consolidation_plan(duplicates)
        print(f"Created {len(plans)} consolidation plans")
        
        # Generate report
        report = {
            'summary': {
                'total_files_scanned': len(list(self.docs_root.rglob("*.md"))),
                'duplicate_pairs_found': len(duplicates),
                'consolidation_plans': len(plans),
                'estimated_files_to_remove': sum(len(p.files_to_remove) for p in plans)
            },
            'categorized_duplicates': categorized,
            'consolidation_plans': [self._plan_to_dict(p) for p in plans],
            'detailed_matches': [self._match_to_dict(d) for d in duplicates]
        }
        
        return report, duplicates, plans
    
    def _categorize_duplicates(self, duplicates: List[DuplicateMatch]) -> Dict:
        """Categorize duplicates by type and characteristics"""
        categories = {
            'exact_duplicates': [],
            'near_duplicates': [],
            'partial_overlaps': [],
            'filename_suspicious': [],
            'same_directory': [],
            'cross_module': []
        }
        
        for duplicate in duplicates:
            # Basic categorization
            if duplicate.match_type == 'exact':
                categories['exact_duplicates'].append(self._match_to_dict(duplicate))
            elif duplicate.match_type == 'near_duplicate':
                categories['near_duplicates'].append(self._match_to_dict(duplicate))
            else:
                categories['partial_overlaps'].append(self._match_to_dict(duplicate))
            
            # Filename analysis
            if self._has_suspicious_filename(duplicate):
                categories['filename_suspicious'].append(self._match_to_dict(duplicate))
            
            # Directory analysis
            if duplicate.file1.parent == duplicate.file2.parent:
                categories['same_directory'].append(self._match_to_dict(duplicate))
            else:
                categories['cross_module'].append(self._match_to_dict(duplicate))
        
        return categories
    
    def _has_suspicious_filename(self, duplicate: DuplicateMatch) -> bool:
        """Check if filenames suggest duplication"""
        name1 = duplicate.file1.stem.lower()
        name2 = duplicate.file2.stem.lower()
        
        for pattern1, pattern2 in self.suspicious_patterns:
            if (pattern1 in name1 and pattern2 in name2) or (pattern2 in name1 and pattern1 in name2):
                return True
        
        return False
    
    def _match_to_dict(self, match: DuplicateMatch) -> Dict:
        """Convert DuplicateMatch to dictionary for JSON serialization"""
        return {
            'file1': str(match.file1.relative_to(self.docs_root)),
            'file2': str(match.file2.relative_to(self.docs_root)),
            'similarity_score': round(match.similarity_score, 3),
            'match_type': match.match_type,
            'overlapping_sections_count': len(match.overlapping_sections),
            'unique_content_file1_count': len(match.unique_content_file1),
            'unique_content_file2_count': len(match.unique_content_file2)
        }
    
    def _plan_to_dict(self, plan: ConsolidationPlan) -> Dict:
        """Convert ConsolidationPlan to dictionary for JSON serialization"""
        return {
            'primary_file': str(plan.primary_file.relative_to(self.docs_root)),
            'files_to_merge': [str(f.relative_to(self.docs_root)) for f in plan.files_to_merge],
            'files_to_remove': [str(f.relative_to(self.docs_root)) for f in plan.files_to_remove],
            'merge_strategy': plan.merge_strategy
        }


class ContentMerger:
    """Intelligent content merger with preservation of unique information"""
    
    def __init__(self):
        self.preserved_content = []
        self.merge_decisions = []
    
    def merge_files_intelligently(self, plan: ConsolidationPlan, duplicates: List[DuplicateMatch]) -> str:
        """Merge files according to plan while preserving unique content"""
        
        # Read primary file
        primary_content = plan.primary_file.read_text(encoding='utf-8', errors='ignore')
        
        # Find duplicates involving primary file
        related_duplicates = [
            d for d in duplicates 
            if d.file1 == plan.primary_file or d.file2 == plan.primary_file
        ]
        
        # Collect unique content from other files
        unique_sections = []
        
        for merge_file in plan.files_to_merge:
            if merge_file in plan.files_to_remove:
                continue  # Skip files marked for removal
            
            # Find the duplicate match for this file
            matching_duplicate = None
            for dup in related_duplicates:
                if dup.file1 == merge_file or dup.file2 == merge_file:
                    matching_duplicate = dup
                    break
            
            if matching_duplicate:
                # Extract unique content
                if matching_duplicate.file1 == merge_file:
                    unique_content = matching_duplicate.unique_content_file1
                else:
                    unique_content = matching_duplicate.unique_content_file2
                
                # Add significant unique sections
                for section in unique_content:
                    if len(section.strip()) > 50:  # Only substantial content
                        unique_sections.append({
                            'content': section,
                            'source_file': str(merge_file),
                            'section_type': self._identify_section_type(section)
                        })
        
        # Merge unique sections into primary content
        merged_content = self._integrate_unique_sections(primary_content, unique_sections)
        
        return merged_content
    
    def _identify_section_type(self, content: str) -> str:
        """Identify the type of content section"""
        content_lower = content.lower()
        
        if content.startswith('#'):
            return 'header'
        elif 'example' in content_lower or 'usage' in content_lower:
            return 'example'
        elif 'note:' in content_lower or 'warning:' in content_lower:
            return 'note'
        elif '```' in content:
            return 'code_block'
        elif content.startswith('- ') or content.startswith('* '):
            return 'list'
        else:
            return 'paragraph'
    
    def _integrate_unique_sections(self, primary_content: str, unique_sections: List[Dict]) -> str:
        """Intelligently integrate unique sections into primary content"""
        if not unique_sections:
            return primary_content
        
        # Group sections by type
        sections_by_type = defaultdict(list)
        for section in unique_sections:
            sections_by_type[section['section_type']].append(section)
        
        # Add sections at appropriate locations
        merged = primary_content
        
        # Add unique headers and substantial content
        if sections_by_type['header'] or sections_by_type['paragraph']:
            merged += "\n\n## Additional Information\n\n"
            
            for section in sections_by_type['header'] + sections_by_type['paragraph']:
                merged += f"{section['content']}\n\n"
                merged += f"*Source: {section['source_file']}*\n\n"
        
        # Add examples section if we have unique examples
        if sections_by_type['example']:
            merged += "\n\n## Additional Examples\n\n"
            for section in sections_by_type['example']:
                merged += f"{section['content']}\n\n"
                merged += f"*Source: {section['source_file']}*\n\n"
        
        # Add notes and warnings
        if sections_by_type['note']:
            merged += "\n\n## Additional Notes\n\n"
            for section in sections_by_type['note']:
                merged += f"{section['content']}\n\n"
        
        return merged


def main():
    """Main execution function for duplicate consolidation"""
    project_root = Path(__file__).parent
    docs_root = project_root / "docs"
    
    if not docs_root.exists():
        print("Error: docs/ directory not found!")
        return
    
    print("Starting comprehensive duplicate content consolidation...")
    
    # Initialize analyzer
    analyzer = SmartDuplicateAnalyzer(docs_root)
    
    # Analyze duplicates
    report, duplicates, plans = analyzer.analyze_all_duplicates()
    
    # Save analysis report
    report_file = project_root / "duplicate_analysis_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nAnalysis complete! Report saved to {report_file}")
    
    # Print summary
    print("\n=== DUPLICATE ANALYSIS SUMMARY ===")
    summary = report['summary']
    print(f"Files scanned: {summary['total_files_scanned']}")
    print(f"Duplicate pairs found: {summary['duplicate_pairs_found']}")
    print(f"Consolidation plans created: {summary['consolidation_plans']}")
    print(f"Files that can be removed: {summary['estimated_files_to_remove']}")
    
    # Show detailed breakdown
    categorized = report['categorized_duplicates']
    print(f"\nExact duplicates: {len(categorized['exact_duplicates'])}")
    print(f"Near duplicates: {len(categorized['near_duplicates'])}")
    print(f"Partial overlaps: {len(categorized['partial_overlaps'])}")
    print(f"Suspicious filenames: {len(categorized['filename_suspicious'])}")
    print(f"Same directory duplicates: {len(categorized['same_directory'])}")
    print(f"Cross-module duplicates: {len(categorized['cross_module'])}")
    
    # Show specific examples
    if categorized['exact_duplicates']:
        print("\n=== EXACT DUPLICATES (sample) ===")
        for i, dup in enumerate(categorized['exact_duplicates'][:3]):
            print(f"{i+1}. {dup['file1']} <-> {dup['file2']} ({dup['similarity_score']:.1%} similar)")
    
    if categorized['filename_suspicious']:
        print("\n=== SUSPICIOUS FILENAMES (sample) ===")
        for i, dup in enumerate(categorized['filename_suspicious'][:3]):
            print(f"{i+1}. {dup['file1']} <-> {dup['file2']} ({dup['similarity_score']:.1%} similar)")
    
    # Ask user if they want to proceed with consolidation
    print(f"\n=== CONSOLIDATION PREVIEW ===")
    if plans:
        print("Consolidation plans ready:")
        for i, plan_dict in enumerate(report['consolidation_plans'][:5]):  # Show first 5
            print(f"{i+1}. Merge {len(plan_dict['files_to_merge'])} files into {plan_dict['primary_file']}")
            if plan_dict['files_to_remove']:
                print(f"   Will remove: {', '.join(plan_dict['files_to_remove'])}")
        
        if len(report['consolidation_plans']) > 5:
            print(f"   ... and {len(report['consolidation_plans']) - 5} more plans")
    
    print(f"\nDuplicates analysis completed successfully!")
    print(f"Review the report at: {report_file}")
    
    return report, duplicates, plans


if __name__ == "__main__":
    main()