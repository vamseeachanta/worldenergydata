#!/usr/bin/env python3
"""
Find key duplicates in documentation files
Focuses on the most important files to avoid timeout
"""

import json
from pathlib import Path
import difflib
from test_docs_categorization import DocumentCategorizer


def find_key_duplicates():
    """Find duplicates among key documentation files"""
    
    # Load the analysis report
    with open('docs_analysis_report.json', 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    project_root = Path(__file__).parent
    categorizer = DocumentCategorizer()
    
    # Focus on key categories that are most likely to have duplicates
    key_categories = ['data-sources/bsee', 'analysis-guides/economic-evaluation', 
                     'analysis-guides/production-analysis', 'user-guide']
    
    duplicates = []
    
    for category in key_categories:
        if category in report['file_categories']:
            files = report['file_categories'][category]
            print(f"Checking {len(files)} files in {category} for duplicates...")
            
            # Compare files within the same category
            for i, file1_path in enumerate(files):
                for file2_path in files[i+1:]:
                    file1_full = project_root / file1_path
                    file2_full = project_root / file2_path
                    
                    if file1_full.exists() and file2_full.exists():
                        try:
                            similarity = categorizer.calculate_similarity(file1_full, file2_full)
                            if similarity >= 0.7:  # Lower threshold for demonstration
                                duplicates.append({
                                    'file1': file1_path,
                                    'file2': file2_path,
                                    'category': category,
                                    'similarity': similarity,
                                    'recommendation': get_duplicate_recommendation(
                                        file1_path, file2_path, similarity
                                    )
                                })
                        except Exception as e:
                            print(f"Error comparing {file1_path} and {file2_path}: {e}")
    
    # Save duplicates report
    duplicates_report = {
        'metadata': {
            'categories_checked': key_categories,
            'total_duplicates': len(duplicates)
        },
        'duplicates': duplicates
    }
    
    with open('key_duplicates_report.json', 'w', encoding='utf-8') as f:
        json.dump(duplicates_report, f, indent=2, ensure_ascii=False)
    
    print(f"Found {len(duplicates)} potential duplicates")
    for dup in duplicates:
        print(f"  {dup['similarity']:.2f} similarity: {dup['file1']} <-> {dup['file2']}")
    
    return duplicates


def get_duplicate_recommendation(file1: str, file2: str, similarity: float) -> str:
    """Get recommendation for handling duplicates"""
    if 'legacy' in file1.lower() or 'superseded' in file1.lower():
        return f"Keep {file2}, archive {file1}"
    elif 'legacy' in file2.lower() or 'superseded' in file2.lower():
        return f"Keep {file1}, archive {file2}"
    elif similarity > 0.95:
        return "Files are nearly identical - merge or keep one"
    elif similarity > 0.8:
        return "High similarity - review for content consolidation"
    else:
        return "Moderate similarity - check for overlapping content"


if __name__ == "__main__":
    find_key_duplicates()