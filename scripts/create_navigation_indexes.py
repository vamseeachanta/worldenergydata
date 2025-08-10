#!/usr/bin/env python3
"""
Create navigation index files (README.md) for each major section
Task 5.3: Create navigation index files (README.md) for each major section
"""

from pathlib import Path
from typing import Dict, List
import re
from datetime import datetime


class NavigationIndexCreator:
    """Create comprehensive navigation index files for each section"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_root = project_root / "docs"
        
        # Section configurations
        self.sections = {
            'data-sources': {
                'title': 'Data Sources',
                'description': 'Documentation for all energy data sources integrated into WorldEnergyData',
                'user_types': ['energy-professional', 'data-analyst'],
                'subsections': ['bsee', 'sodir', 'equipment', 'onshore']
            },
            'user-guide': {
                'title': 'User Guide',
                'description': 'Getting started guides and tutorials for WorldEnergyData users',
                'user_types': ['energy-professional', 'data-analyst', 'developer'],
                'subsections': []
            },
            'analysis-guides': {
                'title': 'Analysis Guides',
                'description': 'Methodologies and best practices for energy data analysis',
                'user_types': ['energy-professional', 'data-analyst'],
                'subsections': []
            },
            'development': {
                'title': 'Development',
                'description': 'Technical documentation for developers and contributors',
                'user_types': ['developer'],
                'subsections': []
            },
            'reference': {
                'title': 'Reference',
                'description': 'API documentation, technical specifications, and reference materials',
                'user_types': ['developer', 'data-analyst'],
                'subsections': []
            },
            'examples': {
                'title': 'Examples',
                'description': 'Code examples, tutorials, and sample analyses',
                'user_types': ['energy-professional', 'data-analyst', 'developer'],
                'subsections': []
            }
        }
    
    def create_all_navigation_indexes(self) -> Dict:
        """Create navigation index files for all sections"""
        print("=== CREATING NAVIGATION INDEXES ===")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'indexes_created': 0,
            'indexes_updated': 0,
            'sections_processed': [],
            'errors': []
        }
        
        for section_name, section_config in self.sections.items():
            section_dir = self.docs_root / section_name
            
            if not section_dir.exists():
                print(f"  [SKIP] Section directory does not exist: {section_name}")
                continue
            
            try:
                index_file = section_dir / "README.md"
                existed_before = index_file.exists()
                
                # Generate index content
                content = self._generate_section_index(section_name, section_config, section_dir)
                
                # Write index file
                index_file.write_text(content, encoding='utf-8')
                
                if existed_before:
                    results['indexes_updated'] += 1
                    print(f"  [UPDATED] {section_name}/README.md")
                else:
                    results['indexes_created'] += 1
                    print(f"  [CREATED] {section_name}/README.md")
                
                results['sections_processed'].append(section_name)
                
            except Exception as e:
                error_msg = f"Failed to create index for {section_name}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"  [ERROR] {error_msg}")
        
        return results
    
    def _generate_section_index(self, section_name: str, section_config: Dict, section_dir: Path) -> str:
        """Generate index content for a specific section"""
        
        # Header
        content = f"# {section_config['title']}\n\n"
        content += f"{section_config['description']}\n\n"
        
        # Target users
        if section_config['user_types']:
            user_types_formatted = ', '.join([
                self._format_user_type(ut) for ut in section_config['user_types']
            ])
            content += f"**Target Users:** {user_types_formatted}\n\n"
        
        # Table of contents
        content += "## Contents\n\n"
        
        # Discover actual content in directory
        md_files = self._discover_section_content(section_dir)
        
        if section_name == 'data-sources':
            content += self._generate_data_sources_toc(section_dir, md_files)
        else:
            content += self._generate_generic_toc(section_dir, md_files)
        
        # Quick start section
        content += "\n## Quick Start\n\n"
        content += self._generate_quick_start_section(section_name, section_config)
        
        # Related sections
        content += "\n## Related Documentation\n\n"
        content += self._generate_related_links(section_name)
        
        # Footer
        content += f"\n---\n\n"
        content += f"*Last updated: {datetime.now().strftime('%Y-%m-%d')}*  \n"
        content += f"*Generated automatically by WorldEnergyData documentation system*\n"
        
        return content
    
    def _discover_section_content(self, section_dir: Path) -> Dict[str, List[Path]]:
        """Discover markdown files organized by subdirectory"""
        content = {}
        
        # Get all markdown files
        md_files = list(section_dir.rglob("*.md"))
        
        # Exclude README files from content listing
        md_files = [f for f in md_files if f.name.lower() != 'readme.md']
        
        # Group by immediate subdirectory
        for md_file in md_files:
            try:
                relative_path = md_file.relative_to(section_dir)
                if len(relative_path.parts) > 1:
                    subdir = relative_path.parts[0]
                else:
                    subdir = "root"
                
                if subdir not in content:
                    content[subdir] = []
                content[subdir].append(md_file)
            except ValueError:
                continue
        
        return content
    
    def _generate_data_sources_toc(self, section_dir: Path, md_files: Dict[str, List[Path]]) -> str:
        """Generate specialized TOC for data sources section"""
        toc = ""
        
        # Data source priority order
        priority_sources = ['bsee', 'sodir', 'equipment', 'onshore']
        
        # Process priority sources first
        for source in priority_sources:
            if source in md_files:
                toc += f"\n### {source.upper()} Data\n\n"
                toc += self._format_source_files(section_dir, source, md_files[source])
        
        # Process remaining sources
        remaining_sources = set(md_files.keys()) - set(priority_sources) - {'root'}
        for source in sorted(remaining_sources):
            toc += f"\n### {source.title()} Data\n\n"
            toc += self._format_source_files(section_dir, source, md_files[source])
        
        # Root level files
        if 'root' in md_files:
            toc += f"\n### General Documentation\n\n"
            for file_path in sorted(md_files['root']):
                title = self._extract_title_from_file(file_path)
                rel_path = file_path.relative_to(section_dir)
                toc += f"- [{title}]({rel_path})\n"
        
        return toc
    
    def _format_source_files(self, section_dir: Path, source: str, files: List[Path]) -> str:
        """Format files for a specific data source"""
        content = ""
        
        # Group files by type (analysis, data, etc.)
        file_groups = {}
        for file_path in files:
            try:
                rel_path = file_path.relative_to(section_dir / source)
                if len(rel_path.parts) > 1:
                    group = rel_path.parts[0]
                else:
                    group = "overview"
                
                if group not in file_groups:
                    file_groups[group] = []
                file_groups[group].append(file_path)
            except ValueError:
                continue
        
        # Format each group
        for group_name in sorted(file_groups.keys()):
            if group_name != "overview":
                content += f"**{group_name.title()}:**\n"
            
            for file_path in sorted(file_groups[group_name]):
                title = self._extract_title_from_file(file_path)
                rel_path = file_path.relative_to(section_dir)
                content += f"- [{title}]({rel_path})\n"
            
            content += "\n"
        
        return content
    
    def _generate_generic_toc(self, section_dir: Path, md_files: Dict[str, List[Path]]) -> str:
        """Generate generic TOC for non-data-source sections"""
        toc = ""
        
        # Process subdirectories
        for subdir in sorted(md_files.keys()):
            if subdir == "root":
                continue
            
            toc += f"\n### {subdir.replace('-', ' ').title()}\n\n"
            
            for file_path in sorted(md_files[subdir]):
                title = self._extract_title_from_file(file_path)
                rel_path = file_path.relative_to(section_dir)
                toc += f"- [{title}]({rel_path})\n"
        
        # Root level files
        if 'root' in md_files:
            toc += f"\n### Documentation Files\n\n"
            for file_path in sorted(md_files['root']):
                title = self._extract_title_from_file(file_path)
                rel_path = file_path.relative_to(section_dir)
                toc += f"- [{title}]({rel_path})\n"
        
        return toc
    
    def _extract_title_from_file(self, file_path: Path) -> str:
        """Extract title from markdown file"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Look for first H1 header
            h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if h1_match:
                return h1_match.group(1).strip()
            
            # Fallback to filename
            return file_path.stem.replace('_', ' ').replace('-', ' ').title()
            
        except Exception:
            return file_path.stem.replace('_', ' ').replace('-', ' ').title()
    
    def _generate_quick_start_section(self, section_name: str, section_config: Dict) -> str:
        """Generate quick start section for the index"""
        
        if section_name == 'data-sources':
            return """For energy professionals getting started with data analysis:

1. **Choose your data source** - Start with [BSEE](bsee/) for US offshore data or [SODIR](sodir/) for Norwegian data
2. **Review the data structure** - Check the analysis guides for each source
3. **See examples** - Look at the analysis examples in each section
4. **Access the data** - Follow the data access instructions

For developers integrating data sources:
- Check the [development documentation](../development/) for API details
- Review data schemas and formats in each source directory
"""
        
        elif section_name == 'user-guide':
            return """1. **Installation** - Follow the installation guide to set up WorldEnergyData
2. **First Analysis** - Try the quick examples to get familiar with the library
3. **API Reference** - Explore the full API documentation
4. **Advanced Usage** - Learn about advanced features and customization
"""
        
        elif section_name == 'development':
            return """For contributors to WorldEnergyData:

1. **Development Setup** - Set up your development environment
2. **Code Standards** - Review our coding standards and practices
3. **Testing** - Learn about our testing approach
4. **Contributing** - Submit your first contribution
"""
        
        else:
            return f"Browse the {section_config['title'].lower()} documentation above to find what you need."
    
    def _generate_related_links(self, section_name: str) -> str:
        """Generate related documentation links"""
        links = []
        
        if section_name == 'data-sources':
            links = [
                "[Analysis Guides](../analysis-guides/) - Learn analysis methodologies",
                "[Examples](../examples/) - See practical examples", 
                "[Development](../development/) - Technical integration details"
            ]
        elif section_name == 'user-guide':
            links = [
                "[Data Sources](../data-sources/) - Available data sources",
                "[Examples](../examples/) - Code examples and tutorials",
                "[Reference](../reference/) - API documentation"
            ]
        elif section_name == 'analysis-guides':
            links = [
                "[Data Sources](../data-sources/) - Data source documentation",
                "[Examples](../examples/) - Practical examples",
                "[User Guide](../user-guide/) - Getting started"
            ]
        elif section_name == 'development':
            links = [
                "[Reference](../reference/) - API specifications",
                "[Data Sources](../data-sources/) - Data integration details",
                "[User Guide](../user-guide/) - User-facing features"
            ]
        elif section_name == 'reference':
            links = [
                "[User Guide](../user-guide/) - Getting started",
                "[Development](../development/) - Development guides",
                "[Examples](../examples/) - Usage examples"
            ]
        elif section_name == 'examples':
            links = [
                "[User Guide](../user-guide/) - Getting started",
                "[Data Sources](../data-sources/) - Data documentation", 
                "[Analysis Guides](../analysis-guides/) - Methodologies"
            ]
        
        if links:
            return "\n".join([f"- {link}" for link in links])
        else:
            return "- [Main Documentation](../README.md) - Return to main documentation"
    
    def _format_user_type(self, user_type: str) -> str:
        """Format user type for display"""
        return user_type.replace('-', ' ').title()


def main():
    """Main execution function"""
    project_root = Path(__file__).parent
    
    print("Creating navigation index files for all sections...")
    
    creator = NavigationIndexCreator(project_root)
    results = creator.create_all_navigation_indexes()
    
    print(f"\n=== NAVIGATION INDEX CREATION SUMMARY ===")
    print(f"Indexes created: {results['indexes_created']}")
    print(f"Indexes updated: {results['indexes_updated']}")
    print(f"Sections processed: {len(results['sections_processed'])}")
    
    if results['errors']:
        print(f"Errors encountered: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")
    
    if results['sections_processed']:
        print(f"\nProcessed sections:")
        for section in results['sections_processed']:
            print(f"  [OK] {section}")
    
    print(f"\nNavigation indexes ready! Each section now has a comprehensive README.md")
    
    return results


if __name__ == "__main__":
    main()