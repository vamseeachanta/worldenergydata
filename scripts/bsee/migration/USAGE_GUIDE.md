# BSEE Migration Toolkit - Quick Usage Guide

## 🚀 Quick Start

### 1. Run the Complete Workflow (Simulation)
```bash
cd /path/to/worldenergydata
python scripts/bsee_migration/migration_workflow_demo.py
```

### 2. Execute the Migration
```bash
# First, scan for potential issues
python scripts/bsee_migration/update_python_imports.py --scan-only

# Simulate the changes
python scripts/bsee_migration/update_python_imports.py --dry-run --backup

# Execute with backup
python scripts/bsee_migration/update_python_imports.py --no-dry-run --backup

# Test the migration
python scripts/bsee_migration/comprehensive_migration_test.py --verbose

# Generate metrics report
python scripts/bsee_migration/migration_metrics_report.py --output-format=html --detailed
```

### 3. Set Up Daily Monitoring
```bash
# Add to crontab for daily health checks at 6 AM
echo "0 6 * * * cd /path/to/worldenergydata && python scripts/bsee_migration/daily_health_check.py --email" | crontab -
```

### 4. Clean Up After 30 Days
```bash
# Simulate cleanup
python scripts/bsee_migration/cleanup_compatibility_links.py

# Actually clean up
python scripts/bsee_migration/cleanup_compatibility_links.py --no-dry-run
```

## 🛠️ Individual Script Usage

### Update Python Imports
```bash
# Scan only
python scripts/bsee_migration/update_python_imports.py --scan-only

# Dry run with backup
python scripts/bsee_migration/update_python_imports.py --dry-run --backup

# Execute with backup
python scripts/bsee_migration/update_python_imports.py --no-dry-run --backup

# Rollback if needed
python scripts/bsee_migration/update_python_imports.py --rollback
```

### Test Migration Success
```bash
# Basic test
python scripts/bsee_migration/comprehensive_migration_test.py

# Verbose with performance
python scripts/bsee_migration/comprehensive_migration_test.py --verbose --performance

# Auto-fix issues
python scripts/bsee_migration/comprehensive_migration_test.py --fix-issues
```

### Generate Metrics Report
```bash
# YAML format
python scripts/bsee_migration/migration_metrics_report.py

# HTML with details
python scripts/bsee_migration/migration_metrics_report.py --output-format=html --detailed

# JSON format
python scripts/bsee_migration/migration_metrics_report.py --output-format=json
```

### Daily Health Check
```bash
# Basic check
python scripts/bsee_migration/daily_health_check.py

# With notifications
python scripts/bsee_migration/daily_health_check.py --email --slack

# With custom config
python scripts/bsee_migration/daily_health_check.py --config=/path/to/config.yaml
```

### Cleanup Compatibility Links
```bash
# Dry run (default)
python scripts/bsee_migration/cleanup_compatibility_links.py

# Execute cleanup
python scripts/bsee_migration/cleanup_compatibility_links.py --no-dry-run

# Force cleanup regardless of age
python scripts/bsee_migration/cleanup_compatibility_links.py --no-dry-run --force

# Custom age threshold
python scripts/bsee_migration/cleanup_compatibility_links.py --days=60
```

## 📊 Understanding Output

### Import Scan Results
- **Files scanned**: Total Python files examined
- **Transformable imports**: Imports that need updating
- **Transformation report**: Detailed YAML file with all findings

### Migration Test Results
- **Import success rate**: Percentage of imports working correctly
- **Performance metrics**: Import times and memory usage
- **Functionality tests**: Whether key features work
- **Overall status**: PASS/WARN/FAIL

### Health Check Results
- **Critical imports**: Core module import status
- **Performance monitoring**: Against configured thresholds
- **File integrity**: Syntax and structure validation
- **Alerts**: Issues requiring attention

### Metrics Reports
- **Structure analysis**: File counts, lines of code, organization
- **Performance comparison**: Before/after migration timing
- **Functionality coverage**: Classes, functions, features detected
- **Success indicators**: Migration quality measures

## 🚨 Troubleshooting

### Import Update Issues
```bash
# Check syntax errors
python -m py_compile src/worldenergydata/bsee/*.py

# Rollback if needed
python scripts/bsee_migration/update_python_imports.py --rollback

# Manual inspection
python scripts/bsee_migration/update_python_imports.py --scan-only
```

### Test Failures
```bash
# Run with verbose output
python scripts/bsee_migration/comprehensive_migration_test.py --verbose

# Check specific functionality
python -c "import worldenergydata.bsee; print('Import successful')"

# Performance issues
python scripts/bsee_migration/migration_metrics_report.py --output-format=json
```

### Health Check Problems
```bash
# Run with verbose logging
python scripts/bsee_migration/daily_health_check.py --verbose

# Check configuration
python scripts/bsee_migration/daily_health_check.py --config=health_config.yaml

# Manual verification
python -c "from worldenergydata.bsee.data_collection import BSEEDataCollector; print('OK')"
```

## 📅 Recommended Schedule

### Pre-Migration (Day -1)
- [ ] Run baseline metrics report
- [ ] Scan for transformable imports
- [ ] Ensure all tests pass
- [ ] Create full backup

### Migration Day (Day 0)
- [ ] Execute import updates with backup
- [ ] Run comprehensive migration tests
- [ ] Generate post-migration metrics
- [ ] Set up daily health monitoring

### Post-Migration Monitoring (Days 1-30)
- [ ] Daily: Automated health checks
- [ ] Weekly: Review health reports
- [ ] Monthly: Generate metrics comparison

### Cleanup (Day 30+)
- [ ] Clean up compatibility links
- [ ] Archive migration reports
- [ ] Update team documentation

## 🎯 Success Criteria

### ✅ Migration Success Indicators
- Import success rate > 80%
- No critical functionality failures
- Performance within 50% of baseline
- All key modules present and functional

### ⚠️ Warning Signs
- Import failures > 20%
- Performance degradation > 50%
- Missing key functionality
- Syntax errors in transformed files

### ❌ Failure Conditions
- Critical imports completely broken
- Core functionality unavailable
- Data integrity compromised
- Rollback required

---

*For detailed documentation, see README.md in the same directory.*