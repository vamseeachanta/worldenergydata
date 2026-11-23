#!/usr/bin/env python3
"""
ABOUTME: Parses coverage.xml and generates module-level coverage analysis
ABOUTME: Creates prioritized test expansion roadmap for lowest coverage modules
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Tuple
import sys

def parse_coverage_xml(xml_file: Path) -> Dict[str, Dict]:
    """
    Parse coverage.xml and extract module-level coverage data.

    Returns dict with structure:
    {
        'module_path': {
            'lines_valid': int,
            'lines_covered': int,
            'coverage_pct': float,
            'branch_rate': float
        },
        ...
    }
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        print(f"✓ Successfully parsed XML file", file=sys.stderr)
        print(f"  Root tag: {root.tag}", file=sys.stderr)

    except Exception as e:
        print(f"✗ Failed to parse XML: {e}", file=sys.stderr)
        sys.exit(1)

    modules = {}
    package_count = 0
    class_count = 0

    # Navigate: root -> packages -> package -> classes -> class
    packages_elem = root.find('packages')
    if packages_elem is None:
        print("✗ No <packages> element found", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Found <packages> element", file=sys.stderr)

    for package in packages_elem.findall('package'):
        package_count += 1
        package_name = package.get('name', 'root')

        classes_elem = package.find('classes')
        if classes_elem is None:
            continue

        for cls in classes_elem.findall('class'):
            class_count += 1
            cls_name = cls.get('name', '').replace('.py', '')
            filename = cls.get('filename', cls_name)

            # Get coverage metrics by counting line elements
            lines_elem = cls.find('lines')
            if lines_elem is not None:
                all_lines = lines_elem.findall('line')
                lines_valid = len(all_lines)
                lines_covered = sum(1 for line in all_lines if int(line.get('hits', 0)) > 0)
            else:
                lines_valid = 0
                lines_covered = 0

            branch_rate_str = cls.get('branch-rate', '0')

            try:
                branch_rate = float(branch_rate_str)
            except:
                branch_rate = 0.0

            # Calculate coverage percentage
            if lines_valid > 0:
                coverage_pct = (lines_covered / lines_valid) * 100
            else:
                coverage_pct = 0.0

            # Store module data with full path
            full_path = f"{package_name}/{filename}" if package_name != 'root' else filename
            modules[full_path] = {
                'lines_valid': lines_valid,
                'lines_covered': lines_covered,
                'coverage_pct': coverage_pct,
                'branch_rate': branch_rate,
                'package': package_name,
                'class_name': cls_name
            }

    print(f"✓ Found {package_count} packages, {class_count} classes", file=sys.stderr)
    return modules

def analyze_and_rank(modules: Dict[str, Dict]) -> List[Tuple[str, Dict]]:
    """
    Rank modules by coverage percentage (lowest first).

    Prioritization factors:
    1. Coverage percentage (lowest first - most need)
    2. Number of lines (higher lines = higher impact)
    """
    # Sort by: coverage ascending, then by lines_valid descending
    ranked = sorted(
        modules.items(),
        key=lambda x: (x[1]['coverage_pct'], -x[1]['lines_valid'])
    )
    return ranked

def generate_report(modules: Dict[str, Dict], output_file: Path = None):
    """Generate coverage analysis report."""

    if not modules:
        print("✗ No modules found in coverage.xml")
        return

    # Get ranked list
    ranked = analyze_and_rank(modules)

    # Calculate aggregates
    total_lines_valid = sum(m['lines_valid'] for m in modules.values())
    total_lines_covered = sum(m['lines_covered'] for m in modules.values())
    overall_coverage = (total_lines_covered / total_lines_valid) * 100 if total_lines_valid > 0 else 0

    # Categorize by coverage bands
    bands = {
        '0%': [],
        '1-5%': [],
        '6-10%': [],
        '11-25%': [],
        '26-50%': [],
        '51-75%': [],
        '76-99%': [],
        '100%': []
    }

    for path, data in modules.items():
        pct = data['coverage_pct']
        if pct == 0:
            bands['0%'].append((path, data))
        elif pct <= 5:
            bands['1-5%'].append((path, data))
        elif pct <= 10:
            bands['6-10%'].append((path, data))
        elif pct <= 25:
            bands['11-25%'].append((path, data))
        elif pct <= 50:
            bands['26-50%'].append((path, data))
        elif pct <= 75:
            bands['51-75%'].append((path, data))
        elif pct < 100:
            bands['76-99%'].append((path, data))
        else:
            bands['100%'].append((path, data))

    # Generate report
    report_lines = []
    report_lines.append("=" * 100)
    report_lines.append("COVERAGE GAP ANALYSIS - WORLDENERGYDATA TIER 1")
    report_lines.append("=" * 100)
    report_lines.append("")

    report_lines.append(f"📊 OVERALL METRICS")
    report_lines.append(f"  Total Modules: {len(modules)}")
    report_lines.append(f"  Total Lines Valid: {total_lines_valid:,}")
    report_lines.append(f"  Total Lines Covered: {total_lines_covered:,}")
    report_lines.append(f"  Overall Coverage: {overall_coverage:.2f}%")
    report_lines.append(f"  Gap to 85% Target: {85 - overall_coverage:.2f} percentage points")

    # Calculate additional lines needed to reach 85% coverage
    if total_lines_valid > 0:
        lines_needed = int((0.85 * total_lines_valid) - total_lines_covered)
        report_lines.append(f"  Additional Lines Needed: {max(0, lines_needed):,}")
    else:
        report_lines.append(f"  Additional Lines Needed: N/A (no lines to cover)")
    report_lines.append("")

    # Coverage distribution
    report_lines.append(f"📈 COVERAGE DISTRIBUTION")
    for band in ['0%', '1-5%', '6-10%', '11-25%', '26-50%', '51-75%', '76-99%', '100%']:
        count = len(bands[band])
        if count > 0:
            report_lines.append(f"  {band:>8}: {count:3} modules")
    report_lines.append("")

    # Top 30 lowest coverage modules
    report_lines.append(f"🎯 TOP 30 LOWEST COVERAGE MODULES (HIGHEST PRIORITY)")
    report_lines.append("-" * 100)
    report_lines.append(f"{'Rank':<5} {'Coverage':<12} {'Lines':<15} {'Module Path':<60}")
    report_lines.append("-" * 100)

    for idx, (path, data) in enumerate(ranked[:30], 1):
        coverage_str = f"{data['coverage_pct']:.1f}%"
        lines_str = f"{data['lines_covered']}/{data['lines_valid']}"
        report_lines.append(f"{idx:<5} {coverage_str:<12} {lines_str:<15} {path:<60}")

    report_lines.append("")
    report_lines.append("=" * 100)
    report_lines.append("PRIORITIZATION STRATEGY")
    report_lines.append("=" * 100)
    report_lines.append("")

    # Group by coverage bands for strategic planning
    report_lines.append("🔴 PHASE 1: ZERO COVERAGE MODULES (0% → Target 40%)")
    report_lines.append(f"   Count: {len(bands['0%'])} modules")
    report_lines.append(f"   Impact: High - These modules have ZERO tests")
    report_lines.append(f"   Strategy: Start here - Maximum immediate impact")
    report_lines.append(f"   Effort: Add ~5-10 tests per module to reach 40% coverage")
    report_lines.append("")

    if len(bands['0%']) > 0:
        report_lines.append("   Zero coverage modules:")
        for path, data in sorted(bands['0%'], key=lambda x: -x[1]['lines_valid'])[:10]:
            report_lines.append(f"     • {path} ({data['lines_valid']} lines)")
    report_lines.append("")

    report_lines.append("🟠 PHASE 2: VERY LOW COVERAGE MODULES (1-10% → Target 50%)")
    report_lines.append(f"   Count: {len(bands['1-5%']) + len(bands['6-10%'])} modules")
    report_lines.append(f"   Impact: Medium-High - Mostly untested")
    report_lines.append(f"   Strategy: After Phase 1, these provide good ROI")
    report_lines.append(f"   Effort: Add ~8-15 tests per module to reach 50% coverage")
    report_lines.append("")

    report_lines.append("🟡 PHASE 3: LOW COVERAGE MODULES (11-25% → Target 60%)")
    report_lines.append(f"   Count: {len(bands['11-25%'])} modules")
    report_lines.append(f"   Impact: Medium - Some tests exist, gaps remain")
    report_lines.append(f"   Strategy: Continue after Phase 2")
    report_lines.append(f"   Effort: Add ~10-20 tests per module to reach 60% coverage")
    report_lines.append("")

    report_lines.append("🟢 PHASE 4: MEDIUM COVERAGE MODULES (26-75% → Target 75%+)")
    report_lines.append(f"   Count: {len(bands['26-50%']) + len(bands['51-75%'])} modules")
    report_lines.append(f"   Impact: Medium-Low - Most functionality tested")
    report_lines.append(f"   Strategy: Fill gaps in edge cases and error handling")
    report_lines.append(f"   Effort: Add ~5-10 tests per module for edge cases")
    report_lines.append("")

    report_lines.append("✅ FULLY TESTED MODULES (76-100%)")
    report_lines.append(f"   Count: {len(bands['76-99%']) + len(bands['100%'])} modules")
    report_lines.append(f"   Status: Good - Maintain this quality")
    report_lines.append("")

    report_lines.append("=" * 100)
    report_lines.append("CRITICAL MODULES FOR IMMEDIATE TESTING")
    report_lines.append("=" * 100)
    report_lines.append("")

    # Identify critical modules (validators, schemas, base modules)
    critical_patterns = ['validator', 'schema', 'base', 'engine', 'bsee', 'hse']
    critical_modules = []

    for path, data in ranked:
        for pattern in critical_patterns:
            if pattern.lower() in path.lower():
                critical_modules.append((path, data))
                break

    report_lines.append(f"🎯 HIGHEST CRITICALITY FOR TEST EXPANSION:")
    report_lines.append(f"   (Validators, Schemas, Base modules, Core BSEE/HSE data)")
    report_lines.append("")

    for idx, (path, data) in enumerate(critical_modules[:20], 1):
        coverage_str = f"{data['coverage_pct']:.1f}%"
        lines_str = f"{data['lines_covered']}/{data['lines_valid']}"
        impact = "HIGH" if data['coverage_pct'] == 0 else "MEDIUM" if data['coverage_pct'] < 20 else "LOW"
        report_lines.append(f"  {idx}. [{impact:6}] {coverage_str:>7} {lines_str:>15} - {path}")

    report_lines.append("")

    # Print to console
    report_text = "\n".join(report_lines)
    print(report_text)

    # Save to file if specified
    if output_file:
        output_file.write_text(report_text)
        print(f"\n✓ Report saved to: {output_file}")

    return report_text

if __name__ == '__main__':
    xml_file = Path('/mnt/github/workspace-hub/worldenergydata/coverage.xml')
    output_file = Path('/mnt/github/workspace-hub/worldenergydata/COVERAGE_ANALYSIS.txt')

    print(f"📖 Parsing coverage.xml...", file=sys.stderr)
    modules = parse_coverage_xml(xml_file)

    print(f"✓ Found {len(modules)} modules", file=sys.stderr)
    print(f"📊 Generating analysis report...\n", file=sys.stderr)

    generate_report(modules, output_file)
