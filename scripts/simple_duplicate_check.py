#!/usr/bin/env python3
"""
Simple duplicate detection based on filename similarity
"""

import json
from pathlib import Path
import difflib


def find_filename_duplicates():
    """Find files with similar names that might be duplicates"""
    
    with open('docs_analysis_report.json', 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    all_files = []
    for category, files in report['file_categories'].items():
        for file_path in files:
            all_files.append({
                'path': file_path,
                'name': Path(file_path).name,
                'stem': Path(file_path).stem,
                'category': category
            })
    
    # Find files with similar names
    potential_duplicates = []
    
    for i, file1 in enumerate(all_files):
        for file2 in all_files[i+1:]:
            # Check name similarity
            name_similarity = difflib.SequenceMatcher(None, 
                                                    file1['stem'].lower(), 
                                                    file2['stem'].lower()).ratio()
            
            if name_similarity > 0.7:  # Similar names
                potential_duplicates.append({
                    'file1': file1['path'],
                    'file2': file2['path'],
                    'name_similarity': name_similarity,
                    'same_category': file1['category'] == file2['category'],
                    'file1_category': file1['category'],
                    'file2_category': file2['category']
                })
    
    # Also check for exact filename matches in different locations
    filename_groups = {}
    for file_info in all_files:
        name = file_info['name'].lower()
        if name not in filename_groups:
            filename_groups[name] = []
        filename_groups[name].append(file_info)
    
    exact_duplicates = []
    for filename, files in filename_groups.items():
        if len(files) > 1:
            exact_duplicates.append({
                'filename': filename,
                'locations': [f['path'] for f in files],
                'categories': [f['category'] for f in files]
            })
    
    # Create report
    duplicate_report = {
        'potential_name_duplicates': len(potential_duplicates),
        'exact_filename_duplicates': len(exact_duplicates),
        'name_based_duplicates': potential_duplicates,
        'filename_duplicates': exact_duplicates
    }
    
    with open('simple_duplicates_report.json', 'w', encoding='utf-8') as f:
        json.dump(duplicate_report, f, indent=2, ensure_ascii=False)
    
    print(f"Found {len(potential_duplicates)} potential name-based duplicates")
    print(f"Found {len(exact_duplicates)} exact filename duplicates")
    
    return duplicate_report


if __name__ == "__main__":
    find_filename_duplicates()