#!/usr/bin/env python3
"""
Quick Documentation Analysis for Task 2
Creates essential outputs without time-intensive duplicate detection
"""

from pathlib import Path
import json
from test_docs_categorization import DocumentCategorizer
from datetime import datetime


def quick_analysis():
    """Perform quick analysis of documentation files"""
    project_root = Path(__file__).parent
    categorizer = DocumentCategorizer()
    
    # Find all documentation files
    doc_files = []
    for ext in ['.md', '.txt']:
        doc_files.extend(list(project_root.rglob(f'*{ext}')))
    
    # Filter out excluded directories
    exclude_patterns = {'node_modules', '__pycache__', '.git', '.pytest_cache', 'venv', 'env'}
    filtered_files = []
    for file_path in doc_files:
        if not any(pattern in str(file_path) for pattern in exclude_patterns):
            filtered_files.append(file_path)
    
    print(f"Found {len(filtered_files)} documentation files")
    
    # Categorize files
    categorized_files = {}
    migration_mapping = {}
    
    for file_path in filtered_files:
        try:
            category, confidence = categorizer.categorize_file(file_path)
            rel_path = str(file_path.relative_to(project_root))
            
            if category not in categorized_files:
                categorized_files[category] = []
            categorized_files[category].append(rel_path)
            
            # Create migration mapping
            new_path = determine_new_path(rel_path, category)
            migration_mapping[rel_path] = {
                'old_path': rel_path,
                'new_path': new_path,
                'category': category,
                'confidence': confidence,
                'action': 'migrate' if confidence > 1.0 else 'review'
            }
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Create comprehensive report
    report = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'total_files': len(filtered_files),
            'categorized_files': len(migration_mapping)
        },
        'categories': {category: len(files) for category, files in categorized_files.items()},
        'file_categories': categorized_files,
        'migration_mapping': migration_mapping
    }
    
    # Save report
    with open('docs_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("Analysis complete!")
    print(f"Categories found: {len(categorized_files)}")
    for category, files in categorized_files.items():
        print(f"  {category}: {len(files)} files")
    
    return report


def determine_new_path(old_path: str, category: str) -> str:
    """Determine new path for file based on category"""
    filename = Path(old_path).name
    
    if category == 'uncategorized':
        return f"docs/uncategorized/{filename}"
    
    # For BSEE files, preserve some structure
    if category == 'data-sources/bsee' and 'modules/bsee' in old_path:
        old_path_obj = Path(old_path)
        if len(old_path_obj.parts) > 3:
            # Preserve subdirectory structure
            subpath = '/'.join(old_path_obj.parts[3:-1])
            return f"docs/{category}/{subpath}/{filename}"
    
    return f"docs/{category}/{filename}"


if __name__ == "__main__":
    quick_analysis()