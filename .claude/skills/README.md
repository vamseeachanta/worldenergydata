# worldenergydata - Repository Skills

> Repository-specific Claude Code skills for energy data analysis and visualization.
>
> Location: `worldenergydata/.claude/skills/`

## Overview

This collection provides **10 specialized skills** for energy industry data workflows including BSEE/SODIR data extraction, production forecasting, NPV analysis, and interactive visualizations. These skills are automatically activated when Claude Code determines they're relevant to the current task.

## Available Skills

| Skill | Description |
|-------|-------------|
| [bsee-data-extractor](bsee-data-extractor/SKILL.md) | Extract and process US offshore oil/gas data from BSEE public database |
| [energy-data-visualizer](energy-data-visualizer/SKILL.md) | Create interactive energy data visualizations with Plotly |
| [fdas-economics](fdas-economics/SKILL.md) | FDAS economic analysis with production profiles, capex, opex, and NPV calculations |
| [field-analyzer](field-analyzer/SKILL.md) | Analyze oil/gas field performance, production trends, and reserves |
| [marine-safety-incidents](marine-safety-incidents/SKILL.md) | Analyze BSEE marine safety incidents including injuries, fatalities, and pollution events |
| [npv-analyzer](npv-analyzer/SKILL.md) | Calculate NPV, IRR, and economic metrics for energy projects |
| [production-forecaster](production-forecaster/SKILL.md) | Forecast production using decline curve analysis and type curves |
| [sodir-data-extractor](sodir-data-extractor/SKILL.md) | Extract Norwegian Continental Shelf data from SODIR (NPD) |
| [web-scraper-energy](web-scraper-energy/SKILL.md) | Scrape energy industry websites for data collection |
| [well-production-dashboard](well-production-dashboard/SKILL.md) | Interactive well production dashboard with monthly/annual analysis and visualization |

## Skill Categories

### Data Extraction

- **bsee-data-extractor**: US offshore production, wells, platforms, operators, leases from BSEE
- **sodir-data-extractor**: Norwegian fields, production, wells, facilities from SODIR/NPD
- **web-scraper-energy**: Custom web scraping for energy data sources

### Economic Analysis

- **fdas-economics**: Full cycle economics (FDAS format) with production profiles and cashflows
- **npv-analyzer**: Net present value, internal rate of return, breakeven calculations

### Production Analysis

- **production-forecaster**: Decline curve analysis (Arps), type curve matching, EUR estimation
- **field-analyzer**: Field-level production trends, reserves tracking, performance metrics
- **well-production-dashboard**: Monthly/annual well production metrics with interactive visualizations

### Safety & Compliance

- **marine-safety-incidents**: BSEE safety incident analysis, injury rates, pollution events

### Visualization

- **energy-data-visualizer**: Interactive Plotly charts for production, economics, and trends

## Usage

### Automatic Activation

Skills activate automatically based on their description:

```
User: "Extract production data from BSEE for Gulf of Mexico"
Claude: [Activates bsee-data-extractor skill]

User: "Run NPV analysis on the Lower Tertiary project"
Claude: [Activates npv-analyzer skill]

User: "Create production forecast using decline curves"
Claude: [Activates production-forecaster skill]

User: "Analyze marine safety incidents for the platform"
Claude: [Activates marine-safety-incidents skill]
```

### Manual Reference

Reference skills directly in prompts:

```
"Using the fdas-economics skill, calculate project economics"
"Apply the production-forecaster skill for EUR estimation"
"Use the well-production-dashboard skill to analyze monthly trends"
```

## Directory Structure

```
worldenergydata/.claude/skills/
├── README.md                     # This file
├── bsee-data-extractor/
│   └── SKILL.md
├── energy-data-visualizer/
│   └── SKILL.md
├── fdas-economics/
│   └── SKILL.md
├── field-analyzer/
│   └── SKILL.md
├── marine-safety-incidents/
│   └── SKILL.md
├── npv-analyzer/
│   └── SKILL.md
├── production-forecaster/
│   └── SKILL.md
├── sodir-data-extractor/
│   └── SKILL.md
├── web-scraper-energy/
│   └── SKILL.md
└── well-production-dashboard/
    └── SKILL.md
```

## Integration with Global Skills

These repository-specific skills complement the global skills in `~/.claude/skills/`:

- **Global**: General development, document handling, reporting
- **Repository-specific**: Domain-specific energy data analysis

## Related Documentation

- [worldenergydata Module Documentation](../../docs/)
- [BSEE Data Module](../../src/worldenergydata/bsee/)
- [SODIR Data Module](../../src/worldenergydata/sodir/)
- [Workspace Hub Skills](../../../.claude/skills/README.md)

---

*Repository-specific skills for worldenergydata energy industry workflows*
