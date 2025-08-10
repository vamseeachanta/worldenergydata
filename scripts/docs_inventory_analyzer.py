#!/usr/bin/env python3
"""
Documentation Inventory and Analysis System
Part of Task 2.2-2.6: Comprehensive analysis and categorization of existing documentation
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
import difflib
import re
from datetime import datetime
from test_docs_categorization import DocumentCategorizer


class DocumentInventory:
    """Comprehensive documentation inventory and analysis system"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent
        self.docs_root = self.project_root / "docs"
        self.categorizer = DocumentCategorizer()
        self.inventory = {}
        self.migration_mapping = {}
        self.duplicates = []
        
        # File type categorization
        self.documentation_extensions = {'.md', '.txt', '.rst'}
        self.exclude_patterns = {
            'node_modules', '__pycache__', '.git', '.pytest_cache', 
            'venv', 'env', '.venv', 'build', 'dist'
        }
    
    def create_comprehensive_inventory(self) -> Dict:
        """Create comprehensive inventory of all documentation files"""
        print("Creating comprehensive documentation inventory...")
        
        inventory = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'project_root': str(self.project_root),
                'total_files': 0,
                'markdown_files': 0,
                'text_files': 0,
                'other_files': 0
            },
            'files': {},
            'categories': {},
            'directories': {}
        }
        
        # Scan all files in the project
        for file_path in self.project_root.rglob('*'):
            if self._should_include_file(file_path):
                file_info = self._analyze_file(file_path)
                inventory['files'][str(file_path.relative_to(self.project_root))] = file_info
                
                # Update counters
                inventory['metadata']['total_files'] += 1
                if file_path.suffix == '.md':
                    inventory['metadata']['markdown_files'] += 1
                elif file_path.suffix == '.txt':
                    inventory['metadata']['text_files'] += 1
                else:
                    inventory['metadata']['other_files'] += 1
        
        # Group by categories
        inventory['categories'] = self._group_by_categories(inventory['files'])
        
        # Analyze directory structure
        inventory['directories'] = self._analyze_directory_structure()
        
        self.inventory = inventory
        return inventory
    
    def _should_include_file(self, file_path: Path) -> bool:
        """Determine if file should be included in inventory"""
        if not file_path.is_file():
            return False
        
        # Check file extension
        if file_path.suffix not in self.documentation_extensions:
            return False
        
        # Check exclude patterns
        path_parts = file_path.parts
        for exclude_pattern in self.exclude_patterns:
            if any(exclude_pattern in part for part in path_parts):
                return False
        
        return True
    
    def _analyze_file(self, file_path: Path) -> Dict:
        """Analyze individual file and extract metadata"""
        try:
            stat = file_path.stat()
            
            # Read file content for analysis
            content = ""
            content_preview = ""
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                content_preview = content[:500] + "..." if len(content) > 500 else content
            except Exception as e:
                content_preview = f"Error reading file: {e}"
            
            # Categorize file
            category, confidence = self.categorizer.categorize_file(file_path)
            
            # Extract basic metadata
            file_info = {
                'path': str(file_path.relative_to(self.project_root)),
                'name': file_path.name,
                'stem': file_path.stem,
                'suffix': file_path.suffix,
                'size_bytes': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'content_preview': content_preview,
                'content_length': len(content),
                'line_count': len(content.splitlines()) if content else 0,
                'category': category,
                'category_confidence': confidence,
                'parent_directory': str(file_path.parent.relative_to(self.project_root)),
                'is_legacy': self._is_legacy_file(file_path),
                'content_type': self._determine_content_type(content, file_path),
                'keywords': self._extract_keywords(content),
                'headers': self._extract_headers(content) if file_path.suffix == '.md' else []
            }
            
            return file_info
            
        except Exception as e:
            return {
                'path': str(file_path.relative_to(self.project_root)),
                'error': str(e),
                'category': 'uncategorized',
                'category_confidence': 0.0
            }
    
    def _is_legacy_file(self, file_path: Path) -> bool:
        """Determine if file is legacy/superseded content"""
        path_str = str(file_path).lower()
        legacy_indicators = [
            'legacy', 'superseded', 'old', 'deprecated', 'archived',
            '_legacy', 'backup', 'temp', 'draft'
        ]
        return any(indicator in path_str for indicator in legacy_indicators)
    
    def _determine_content_type(self, content: str, file_path: Path) -> str:
        """Determine the type of content in the file"""
        content_lower = content.lower()
        
        # Check for specific content types
        if any(keyword in content_lower for keyword in ['installation', 'setup', 'getting started']):
            return 'user_guide'
        elif any(keyword in content_lower for keyword in ['api', 'function', 'class', 'method']):
            return 'api_documentation'
        elif any(keyword in content_lower for keyword in ['example', 'tutorial', 'walkthrough']):
            return 'example'
        elif any(keyword in content_lower for keyword in ['test', 'testing', 'pytest', 'unittest']):
            return 'test_documentation'
        elif any(keyword in content_lower for keyword in ['specification', 'spec', 'requirements']):
            return 'specification'
        elif any(keyword in content_lower for keyword in ['data', 'dataset', 'database']):
            return 'data_documentation'
        elif any(keyword in content_lower for keyword in ['analysis', 'methodology', 'algorithm']):
            return 'analysis_guide'
        elif file_path.suffix == '.txt' and 'readme' not in file_path.name.lower():
            return 'data_file'
        else:
            return 'general_documentation'
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract key terms from content"""
        if not content:
            return []
        
        # Simple keyword extraction
        content_lower = content.lower()
        
        # Define important keywords to look for
        important_keywords = [
            'bsee', 'sodir', 'wind', 'lng', 'onshore', 'offshore',
            'npv', 'economic', 'production', 'analysis', 'field',
            'development', 'drilling', 'completion', 'well',
            'api', 'installation', 'tutorial', 'example', 'guide'
        ]
        
        found_keywords = []
        for keyword in important_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _extract_headers(self, content: str) -> List[str]:
        """Extract markdown headers from content"""
        if not content:
            return []
        
        headers = []
        for line in content.splitlines():
            if line.strip().startswith('#'):
                headers.append(line.strip())
        
        return headers[:10]  # Limit to first 10 headers
    
    def _group_by_categories(self, files: Dict) -> Dict:
        """Group files by their categorized destinations"""
        categories = {}
        
        for file_path, file_info in files.items():
            category = file_info.get('category', 'uncategorized')
            if category not in categories:
                categories[category] = []
            categories[category].append(file_path)
        
        return categories
    
    def _analyze_directory_structure(self) -> Dict:
        """Analyze current directory structure"""
        directories = {}
        
        for dir_path in self.project_root.rglob('*'):
            if dir_path.is_dir() and not self._should_exclude_dir(dir_path):
                rel_path = str(dir_path.relative_to(self.project_root))
                
                # Count files in directory
                md_files = len(list(dir_path.glob('*.md')))
                txt_files = len(list(dir_path.glob('*.txt')))
                subdirs = len([d for d in dir_path.iterdir() if d.is_dir()])
                
                directories[rel_path] = {
                    'markdown_files': md_files,
                    'text_files': txt_files,
                    'subdirectories': subdirs,
                    'is_docs_related': 'docs' in rel_path or 'documentation' in rel_path.lower()
                }
        
        return directories
    
    def _should_exclude_dir(self, dir_path: Path) -> bool:
        """Check if directory should be excluded from analysis"""
        path_parts = dir_path.parts
        for exclude_pattern in self.exclude_patterns:
            if any(exclude_pattern in part for part in path_parts):
                return True
        return False
    
    def find_duplicates(self, similarity_threshold: float = 0.8) -> List[Dict]:
        """Find duplicate or highly similar documentation files"""
        print(f"Finding duplicates with similarity threshold {similarity_threshold}...")
        
        if not self.inventory:
            self.create_comprehensive_inventory()
        
        duplicates = []
        files = list(self.inventory['files'].keys())
        
        for i, file1_path in enumerate(files):
            for file2_path in files[i+1:]:
                file1_full_path = self.project_root / file1_path
                file2_full_path = self.project_root / file2_path
                
                if file1_full_path.exists() and file2_full_path.exists():
                    similarity = self.categorizer.calculate_similarity(
                        file1_full_path, file2_full_path
                    )
                    
                    if similarity >= similarity_threshold:
                        duplicate_info = {
                            'file1': file1_path,
                            'file2': file2_path,
                            'similarity': similarity,
                            'file1_size': self.inventory['files'][file1_path].get('size_bytes', 0),
                            'file2_size': self.inventory['files'][file2_path].get('size_bytes', 0),
                            'recommended_action': self._recommend_duplicate_action(
                                file1_path, file2_path, similarity
                            )
                        }
                        duplicates.append(duplicate_info)
        
        self.duplicates = duplicates
        return duplicates
    
    def _recommend_duplicate_action(self, file1: str, file2: str, similarity: float) -> str:
        """Recommend action for handling duplicate files"""
        file1_info = self.inventory['files'][file1]
        file2_info = self.inventory['files'][file2]
        
        # If one is clearly legacy, recommend keeping the other
        if file1_info.get('is_legacy') and not file2_info.get('is_legacy'):
            return f"Keep {file2}, remove {file1} (legacy)"
        elif file2_info.get('is_legacy') and not file1_info.get('is_legacy'):
            return f"Keep {file1}, remove {file2} (legacy)"
        
        # If one is much larger, it might have more content
        size1 = file1_info.get('size_bytes', 0)
        size2 = file2_info.get('size_bytes', 0)
        if size1 > size2 * 1.5:
            return f"Keep {file1} (larger), merge content from {file2}"
        elif size2 > size1 * 1.5:
            return f"Keep {file2} (larger), merge content from {file1}"
        
        # Default recommendation
        return "Manual review required - merge content"
    
    def create_migration_mapping(self) -> Dict:
        """Create detailed migration mapping from old to new structure"""
        print("Creating migration mapping...")
        
        if not self.inventory:
            self.create_comprehensive_inventory()
        
        migration_mapping = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'total_files': len(self.inventory['files'])
            },
            'migrations': {},
            'conflicts': [],
            'manual_review': []
        }
        
        for file_path, file_info in self.inventory['files'].items():
            category = file_info.get('category', 'uncategorized')
            confidence = file_info.get('category_confidence', 0.0)
            
            # Determine new path
            new_path = self._determine_new_path(file_path, category, file_info)
            
            migration_info = {
                'old_path': file_path,
                'new_path': new_path,
                'category': category,
                'confidence': confidence,
                'action': self._determine_migration_action(file_info, confidence),
                'file_size': file_info.get('size_bytes', 0),
                'content_type': file_info.get('content_type', 'unknown'),
                'is_legacy': file_info.get('is_legacy', False)
            }
            
            migration_mapping['migrations'][file_path] = migration_info
            
            # Flag for manual review if confidence is low
            if confidence < 2.0:
                migration_mapping['manual_review'].append(file_path)
        
        self.migration_mapping = migration_mapping
        return migration_mapping
    
    def _determine_new_path(self, old_path: str, category: str, file_info: Dict) -> str:
        """Determine the new path for a file based on its category"""
        if category == 'uncategorized':
            return f"docs/uncategorized/{Path(old_path).name}"
        
        # Handle specific categories
        base_new_path = f"docs/{category}"
        filename = Path(old_path).name
        
        # For BSEE files, maintain some structure
        if category == 'data-sources/bsee' and 'modules/bsee' in old_path:
            # Preserve some of the internal structure
            old_path_obj = Path(old_path)
            if len(old_path_obj.parts) > 3:  # Has subdirectories
                subpath = '/'.join(old_path_obj.parts[3:-1])  # Skip 'docs/modules/bsee' and filename
                return f"{base_new_path}/{subpath}/{filename}"
        
        return f"{base_new_path}/{filename}"
    
    def _determine_migration_action(self, file_info: Dict, confidence: float) -> str:
        """Determine the recommended action for migrating a file"""
        if file_info.get('is_legacy'):
            return 'archive'  # Move to archive or mark for deletion
        elif confidence < 1.0:
            return 'manual_review'
        elif confidence >= 3.0:
            return 'auto_migrate'
        else:
            return 'review_and_migrate'
    
    def save_inventory(self, output_path: Optional[Path] = None) -> Path:
        """Save inventory to JSON file"""
        if output_path is None:
            output_path = self.project_root / 'docs_inventory.json'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.inventory, f, indent=2, ensure_ascii=False)
        
        print(f"Inventory saved to {output_path}")
        return output_path
    
    def save_migration_mapping(self, output_path: Optional[Path] = None) -> Path:
        """Save migration mapping to JSON file"""
        if output_path is None:
            output_path = self.project_root / 'migration_mapping.json'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.migration_mapping, f, indent=2, ensure_ascii=False)
        
        print(f"Migration mapping saved to {output_path}")
        return output_path
    
    def save_duplicates_report(self, output_path: Optional[Path] = None) -> Path:
        """Save duplicates report to JSON file"""
        if output_path is None:
            output_path = self.project_root / 'duplicates_report.json'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.duplicates, f, indent=2, ensure_ascii=False)
        
        print(f"Duplicates report saved to {output_path}")
        return output_path
    
    def generate_summary_report(self) -> Dict:
        """Generate comprehensive summary report"""
        if not self.inventory:
            self.create_comprehensive_inventory()
        
        summary = {
            'inventory_summary': {
                'total_files': self.inventory['metadata']['total_files'],
                'markdown_files': self.inventory['metadata']['markdown_files'],
                'text_files': self.inventory['metadata']['text_files'],
                'categories': len(self.inventory['categories']),
                'directories_analyzed': len(self.inventory['directories'])
            },
            'categorization_summary': {},
            'migration_summary': {},
            'duplicates_summary': {
                'total_duplicates': len(self.duplicates),
                'high_similarity': len([d for d in self.duplicates if d['similarity'] > 0.9]),
                'medium_similarity': len([d for d in self.duplicates if 0.8 <= d['similarity'] <= 0.9])
            }
        }
        
        # Categorization summary
        for category, files in self.inventory['categories'].items():
            summary['categorization_summary'][category] = len(files)
        
        # Migration summary
        if self.migration_mapping:
            actions = {}
            for migration in self.migration_mapping['migrations'].values():
                action = migration['action']
                actions[action] = actions.get(action, 0) + 1
            summary['migration_summary'] = actions
        
        return summary


def main():
    """Main function to run the complete analysis"""
    print("Starting comprehensive documentation analysis...")
    
    # Initialize inventory system
    inventory_system = DocumentInventory()
    
    # Create comprehensive inventory
    inventory = inventory_system.create_comprehensive_inventory()
    print(f"Analyzed {inventory['metadata']['total_files']} files")
    
    # Find duplicates
    duplicates = inventory_system.find_duplicates()
    print(f"Found {len(duplicates)} potential duplicates")
    
    # Create migration mapping
    migration_mapping = inventory_system.create_migration_mapping()
    print(f"Created migration plan for {len(migration_mapping['migrations'])} files")
    
    # Save all results
    inventory_system.save_inventory()
    inventory_system.save_migration_mapping()
    inventory_system.save_duplicates_report()
    
    # Generate and print summary
    summary = inventory_system.generate_summary_report()
    print("\n=== ANALYSIS SUMMARY ===")
    print(json.dumps(summary, indent=2))
    
    return inventory_system


if __name__ == "__main__":
    main()