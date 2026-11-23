#!/usr/bin/env python3
"""
ABOUTME: Marketing brochure generator for worldenergydata modules
ABOUTME: Generates professional markdown and PDF brochures from YAML configuration
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import yaml


class BrochureGenerator:
    """Generate marketing brochures from YAML configuration."""

    def __init__(self, config_path: str, repo_root: Optional[str] = None):
        """
        Initialize brochure generator.

        Args:
            config_path: Path to marketing configuration YAML
            repo_root: Repository root directory (auto-detected if None)
        """
        self.config_path = Path(config_path)
        self.repo_root = Path(repo_root) if repo_root else self._find_repo_root()
        self.config = self._load_config()
        self.output_dir = self.repo_root / self.config.get('pdf_generation', {}).get(
            'output_directory', 'reports/modules/marketing'
        )

    def _find_repo_root(self) -> Path:
        """Find repository root directory."""
        current = Path.cwd()
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        return Path.cwd()

    def _load_config(self) -> Dict:
        """Load YAML configuration."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _read_module_readme(self, module_path: str) -> Optional[str]:
        """Read module README.md if it exists."""
        readme_path = self.repo_root / module_path / 'README.md'
        if readme_path.exists():
            with open(readme_path, 'r') as f:
                return f.read()
        return None

    def _extract_capabilities_from_code(self, module_path: str) -> List[str]:
        """
        Extract capabilities from module code.

        This is a placeholder - in production, would parse __init__.py
        and extract function/class names and docstrings.
        """
        # For now, return capabilities from config
        return []

    def _substitute_template_vars(self, template: str, module: Dict) -> str:
        """
        Substitute template variables with actual values.

        Args:
            template: Template string with {{VARIABLE}} placeholders
            module: Module configuration dictionary

        Returns:
            Template with substituted values
        """
        # Repository-level substitutions
        template = template.replace('{{REPO_NAME}}', self.config['repository']['name'])
        template = template.replace('{{REPO_DESCRIPTION}}', self.config['repository']['description'])
        template = template.replace('{{GITHUB_LINK}}', self.config['repository']['github_url'])
        template = template.replace('{{CONTACT_EMAIL}}', self.config['contact']['email'])

        # Statistics substitutions
        stats = self.config['statistics']
        template = template.replace('{{MODULE_COUNT}}', str(stats['module_count']))
        template = template.replace('{{TEST_COUNT}}', str(stats['test_count']))
        template = template.replace('{{YEARS_EXPERIENCE}}', str(stats['years_experience']))
        template = template.replace('{{PYTHON_FILES}}', str(stats.get('python_files', 'N/A')))
        template = template.replace('{{TEST_FUNCTIONS}}', str(stats.get('test_functions', 'N/A')))

        # Module-specific substitutions
        template = template.replace('{{MODULE_NAME}}', module['name'])
        template = template.replace('{{MODULE_TAGLINE}}', module['tagline'])
        template = template.replace('{{MODULE_PATH}}', module['path'])

        # Industry focus
        template = template.replace(
            '{{INDUSTRY_FOCUS}}',
            self.config['repository_type']['industry_focus']
        )

        # Standards emphasis
        standards_emphasis = self.config['standards_emphasis']
        template = template.replace(
            '{{STANDARDS_EMPHASIS_TITLE}}',
            self._get_standards_title(standards_emphasis['type'])
        )

        return template

    def _get_standards_title(self, emphasis_type: str) -> str:
        """Get appropriate title for standards emphasis section."""
        titles = {
            'data_sources': 'Data Sources',
            'compliance_standards': 'Industry Standards Compliance',
            'methodologies': 'Methodologies',
            'quality_standards': 'Quality Standards'
        }
        return titles.get(emphasis_type, 'Standards')

    def _generate_capabilities_section(self, module: Dict) -> str:
        """Generate capabilities section from module config."""
        capabilities = module.get('capabilities', [])
        if not capabilities:
            return "- Comprehensive analysis capabilities\n- Data processing and validation\n- Interactive reporting"

        lines = []
        for cap in capabilities:
            lines.append(f"- **{cap.split(' - ')[0] if ' - ' in cap else cap}**")
            if ' - ' in cap:
                lines[-1] += f" - {cap.split(' - ', 1)[1]}"
        return '\n'.join(lines)

    def _generate_standards_section(self, module: Dict) -> str:
        """Generate standards/data sources section."""
        standards_config = self.config['standards_emphasis']
        items = standards_config.get('items', [])

        lines = []
        for item in items:
            if isinstance(item, dict):
                name = item.get('name', '')
                desc = item.get('description', '')
                lines.append(f"- **{name}** - {desc}")
            else:
                lines.append(f"- {item}")

        # Add module-specific standards if available
        module_standards = module.get('standards', [])
        for std in module_standards:
            if std not in [line.split('**')[1].split('**')[0] if '**' in line else line.strip('- ') for line in lines]:
                lines.append(f"- {std}")

        return '\n'.join(lines) if lines else "- Industry best practices\n- Quality assurance standards"

    def _generate_benefits_section(self, module: Dict) -> str:
        """Generate key benefits section tailored to target audience."""
        # Generic benefits structure
        benefits = [
            {
                'category': 'Data Quality & Reliability',
                'items': [
                    'Automated data validation and quality checks',
                    'Consistent, reproducible results across analyses'
                ]
            },
            {
                'category': 'Productivity & Efficiency',
                'items': [
                    'Reduce manual data processing time by 70%+',
                    'Streamlined workflows from data to insights'
                ]
            },
            {
                'category': 'Professional Outputs',
                'items': [
                    'Publication-ready interactive visualizations',
                    'Comprehensive reports with customizable templates'
                ]
            }
        ]

        lines = []
        for i, benefit in enumerate(benefits, 1):
            lines.append(f"\n{i}. **{benefit['category']}**")
            for item in benefit['items']:
                lines.append(f"   - {item}")

        return '\n'.join(lines)

    def _generate_integration_section(self, module: Dict) -> str:
        """Generate integration section."""
        integration = self.config.get('integration', {})

        lines = []

        # Compatible software
        compatible = integration.get('compatible_software', [])
        if compatible:
            lines.append(f"- **Compatible with:** {', '.join(compatible)}")

        # Input formats
        inputs = integration.get('input_formats', [])
        if inputs:
            lines.append(f"- **Input formats:** {', '.join(inputs)}")

        # Output formats
        outputs = module.get('output_types', []) or integration.get('output_formats', [])
        if outputs:
            lines.append(f"- **Output formats:** {', '.join(outputs)}")

        return '\n'.join(lines) if lines else "- Industry-standard formats supported"

    def generate_brochure(self, module: Dict, tier: str) -> str:
        """
        Generate markdown brochure for a module.

        Args:
            module: Module configuration dictionary
            tier: Module tier (tier_1_core, tier_2_advanced, etc.)

        Returns:
            Generated markdown content
        """
        template = f"""# {module['name']}
## {module['tagline']}

### Overview

{self._generate_overview(module, tier)}

### Key Capabilities

{self._generate_capabilities_section(module)}

### {self._get_standards_title(self.config['standards_emphasis']['type'])}

{self._generate_standards_section(module)}

### Technical Features

{self._generate_technical_features(module)}

---

## Key Benefits
{self._generate_benefits_section(module)}

### Output Examples

{self._generate_output_examples(module)}

### Integration

{self._generate_integration_section(module)}

---

## About {self.config['repository']['name']}

{self.config['repository']['description']}

**Repository Highlights:**
- **{self.config['statistics']['years_experience']}** years of development and expertise
- **{self.config['statistics']['module_count']}** comprehensive modules
- **{self.config['statistics']['test_count']}** test files with **{self.config['statistics'].get('test_functions', 'N/A')}** rigorous tests
- **{self.config['statistics']['python_files']}** Python files ensuring quality
- Production-ready for enterprise energy analysis
- Open-source with active development

### Contact Information

- **Email:** {self.config['contact']['email']}
- **GitHub:** {self.config['repository']['github_url']}
- **Repository:** WorldEnergyData - Energy data analysis and lifecycle management

---

*Generated by WorldEnergyData Marketing Brochure System*
"""

        return self._substitute_template_vars(template, module)

    def _generate_overview(self, module: Dict, tier: str) -> str:
        """Generate module overview based on tier and audience."""
        name = module['name']
        tagline = module['tagline']

        # Customize based on tier
        if 'tier_1' in tier:
            return f"{name} provides essential capabilities for {tagline.lower()}. This core module serves as the foundation for comprehensive energy data analysis, offering robust data collection, processing, and visualization tools that energy professionals rely on for critical decision-making."
        elif 'tier_2' in tier:
            return f"{name} delivers advanced capabilities for {tagline.lower()}. This specialized module extends core functionality with sophisticated analysis features, enabling detailed insights and complex modeling for professional energy sector applications."
        else:
            return f"{name} offers integration capabilities for {tagline.lower()}. This module enhances workflow automation and system connectivity, supporting seamless data exchange and process optimization across energy analysis platforms."

    def _generate_technical_features(self, module: Dict) -> str:
        """Generate technical features section."""
        # This would ideally parse the module code
        # For now, use generic structure
        return """#### Data Processing
- High-performance data loading and transformation
- Automated data validation and quality assurance
- Support for large-scale datasets

#### Analysis & Visualization
- Interactive Plotly-based visualizations
- Comprehensive statistical analysis
- Customizable reporting templates"""

    def _generate_output_examples(self, module: Dict) -> str:
        """Generate output examples section."""
        output_types = module.get('output_types', [])
        if output_types:
            examples = '\n'.join([f"- {output}" for output in output_types])
            return f"{examples}\n\n*All outputs feature interactive visualizations, comprehensive data tables, and professional formatting suitable for stakeholder presentations.*"
        return "- Interactive plots and visualizations\n- Comprehensive analysis reports\n- Data export capabilities"

    def generate_all_brochures(self, tier_filter: Optional[str] = None) -> List[Path]:
        """
        Generate brochures for all configured modules.

        Args:
            tier_filter: Optional tier to filter (e.g., 'tier_1_core')

        Returns:
            List of generated file paths
        """
        generated_files = []

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Process each tier
        for tier_name, modules in self.config.get('modules', {}).items():
            if tier_filter and tier_name != tier_filter:
                continue

            if not modules:  # Skip empty tiers
                continue

            print(f"\n📁 Processing {tier_name}...")

            for module in modules:
                print(f"  ✏️  Generating: {module['name']}")

                # Generate brochure content
                content = self.generate_brochure(module, tier_name)

                # Create safe filename
                safe_name = module['name'].lower().replace(' ', '_').replace('(', '').replace(')', '')
                filename = f"marketing_brochure_{safe_name}.md"
                filepath = self.output_dir / filename

                # Write to file
                with open(filepath, 'w') as f:
                    f.write(content)

                generated_files.append(filepath)
                print(f"  ✅ Generated: {filepath}")

        return generated_files

    def generate_pdf(self, markdown_path: Path) -> Optional[Path]:
        """
        Generate PDF from markdown using pandoc.

        Args:
            markdown_path: Path to markdown file

        Returns:
            Path to generated PDF, or None if pandoc not available
        """
        import subprocess

        pdf_path = markdown_path.with_suffix('.pdf')

        try:
            # Check if pandoc is available
            subprocess.run(['pandoc', '--version'], capture_output=True, check=True)

            # Generate PDF
            cmd = [
                'pandoc',
                str(markdown_path),
                '-o', str(pdf_path),
                '--pdf-engine=xelatex',
                '-V', 'geometry:margin=1in',
                '-V', 'fontsize=11pt',
                '--toc',
                '--toc-depth=2'
            ]

            subprocess.run(cmd, check=True)
            return pdf_path

        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"  ⚠️  Pandoc not available - PDF generation skipped")
            print(f"     Install with: sudo apt-get install pandoc texlive-xetex")
            return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate marketing brochures for WorldEnergyData modules'
    )
    parser.add_argument(
        '--config',
        default='specs/modules/marketing/worldenergydata_marketing_config.yaml',
        help='Path to marketing configuration YAML'
    )
    parser.add_argument(
        '--tier',
        choices=['tier_1_core', 'tier_2_advanced', 'tier_3_integration', 'tier_4_optional'],
        help='Generate only specific tier (default: all tiers)'
    )
    parser.add_argument(
        '--pdf',
        action='store_true',
        help='Generate PDF files (requires pandoc)'
    )
    parser.add_argument(
        '--module',
        help='Generate only specific module by name'
    )

    args = parser.parse_args()

    print("🚀 WorldEnergyData Marketing Brochure Generator")
    print("=" * 60)

    # Initialize generator
    try:
        generator = BrochureGenerator(args.config)
    except FileNotFoundError:
        print(f"❌ Config file not found: {args.config}")
        sys.exit(1)

    # Generate brochures
    generated_files = generator.generate_all_brochures(tier_filter=args.tier)

    if not generated_files:
        print("\n⚠️  No brochures generated")
        sys.exit(0)

    # Generate PDFs if requested
    if args.pdf:
        print("\n📄 Generating PDFs...")
        for md_file in generated_files:
            pdf_file = generator.generate_pdf(md_file)
            if pdf_file:
                print(f"  ✅ PDF: {pdf_file}")

    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Generated {len(generated_files)} brochure(s)")
    print(f"📁 Output directory: {generator.output_dir}")
    print("\nNext steps:")
    print("  1. Review markdown files in reports/modules/marketing/")
    print("  2. Validate technical accuracy")
    print("  3. Generate PDFs with: --pdf flag")
    print("=" * 60)


if __name__ == '__main__':
    main()
