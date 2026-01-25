# BSEE Data Consolidation Toolkit

A comprehensive set of utility scripts for managing the BSEE data structure consolidation in WorldEnergyData. This toolkit provides end-to-end migration support from initial planning through post-migration monitoring.

## 🎯 Overview

The BSEE consolidation moves scattered BSEE-related modules into a unified `src/worldenergydata/bsee/` structure, improving maintainability, reducing code duplication, and simplifying imports.

### New Structure
```
src/worldenergydata/bsee/
├── __init__.py              # Main BSEE module
├── data_collection.py       # Data collection functionality
├── analysis.py             # Production and economic analysis
└── processing.py           # Data processing and transformations
```

## 🛠️ Available Scripts

### 1. 📝 `update_python_imports.py`
**Purpose**: Identifies and updates Python imports throughout the codebase

**Key Features**:
- Scans entire codebase for transformable imports
- Supports dry-run simulation before making changes
- Creates automatic backups of modified files
- Provides detailed transformation reports
- Supports rollback using backup files

**Usage Examples**:
```bash
# Scan for transformable imports
python update_python_imports.py --scan-only

# Simulate updates with backup
python update_python_imports.py --dry-run --backup

# Execute updates with backup
python update_python_imports.py --no-dry-run --backup

# Rollback changes
python update_python_imports.py --rollback
```

### 2. 🧪 `comprehensive_migration_test.py`
**Purpose**: Comprehensive testing of migration success

**Key Features**:
- Tests import patterns and functionality
- Validates data integrity after migration
- Performance benchmarking
- Legacy compatibility verification
- Detailed test reporting with metrics

**Usage Examples**:
```bash
# Basic migration test
python comprehensive_migration_test.py

# Verbose output with performance tests
python comprehensive_migration_test.py --verbose --performance

# Auto-fix issues if possible
python comprehensive_migration_test.py --fix-issues
```

### 3. 📊 `migration_metrics_report.py`
**Purpose**: Generates comprehensive metrics comparing before/after migration

**Key Features**:
- Directory structure analysis
- Import performance metrics
- Functionality coverage analysis
- Code quality assessment
- Visual charts and reports

**Usage Examples**:
```bash
# Generate YAML report
python migration_metrics_report.py

# Generate HTML report with details
python migration_metrics_report.py --output-format=html --detailed

# Generate JSON report
python migration_metrics_report.py --output-format=json
```

### 4. 🏥 `daily_health_check.py`
**Purpose**: Automated daily health monitoring for BSEE structure

**Key Features**:
- Critical import verification
- Performance monitoring with thresholds
- File integrity checks
- Functionality testing
- Email and Slack notifications
- Configurable alerting

**Usage Examples**:
```bash
# Basic health check
python daily_health_check.py

# With email notifications
python daily_health_check.py --email

# With Slack notifications
python daily_health_check.py --slack

# Schedule with cron (daily at 6 AM)
0 6 * * * /usr/bin/python3 /path/to/daily_health_check.py --email
```

### 5. 🧹 `cleanup_compatibility_links.py`
**Purpose**: Removes compatibility links after 30-day migration period

**Key Features**:
- Age-based cleanup (configurable threshold)
- Migration success verification
- Dry-run simulation
- Cleanup reporting and logging
- Force override options

**Usage Examples**:
```bash
# Dry run (default)
python cleanup_compatibility_links.py

# Actually remove links older than 30 days
python cleanup_compatibility_links.py --no-dry-run

# Force removal regardless of age
python cleanup_compatibility_links.py --no-dry-run --force

# Custom age threshold
python cleanup_compatibility_links.py --days=60
```

### 6. 🚀 `migration_workflow_demo.py`
**Purpose**: Demonstrates the complete migration workflow

**Key Features**:
- End-to-end workflow simulation
- Phase-by-phase execution
- Best practices demonstration
- Command examples
- Workflow logging and reporting

**Usage Examples**:
```bash
# Simulate the complete workflow
python migration_workflow_demo.py

# Actually execute the workflow
python migration_workflow_demo.py --execute

# Show best practices and examples
python migration_workflow_demo.py --best-practices --examples
```

## 📋 Migration Workflow

### Phase 1: Pre-Migration Preparation
1. **Generate baseline metrics**
   ```bash
   python migration_metrics_report.py --output-format=yaml
   ```

2. **Scan for transformable imports**
   ```bash
   python update_python_imports.py --scan-only
   ```

3. **Run existing tests to ensure clean starting point**

### Phase 2: Migration Execution
1. **Simulate import updates**
   ```bash
   python update_python_imports.py --dry-run --backup
   ```

2. **Execute import updates with backup**
   ```bash
   python update_python_imports.py --no-dry-run --backup
   ```

3. **Run comprehensive migration tests**
   ```bash
   python comprehensive_migration_test.py --verbose --performance
   ```

### Phase 3: Post-Migration Validation
1. **Generate post-migration metrics**
   ```bash
   python migration_metrics_report.py --output-format=html --detailed
   ```

2. **Set up daily health monitoring**
   ```bash
   # Add to crontab
   0 6 * * * /usr/bin/python3 /path/to/daily_health_check.py --email
   ```

### Phase 4: Cleanup (After 30 Days)
1. **Clean up compatibility links**
   ```bash
   python cleanup_compatibility_links.py --no-dry-run
   ```

## ⚙️ Configuration

### Health Check Configuration
Create a `health_check_config.yaml` file for custom configuration:

```yaml
health_check:
  critical_imports:
    - "worldenergydata.bsee"
    - "worldenergydata.bsee.data_collection"
    - "worldenergydata.bsee.analysis"
    - "worldenergydata.bsee.processing"
  performance_thresholds:
    max_import_time: 5.0  # seconds
    max_memory_usage: 500  # MB
  alert_thresholds:
    import_failure_rate: 0.2  # 20%
    performance_degradation: 0.5  # 50% slower

notifications:
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "your-email@example.com"
    password: "your-app-password"
    recipients:
      - "team@example.com"
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/services/..."
    channel: "#alerts"

logging:
  log_file: "health_check.log"
  retention_days: 30
```

## 📊 Output Files and Reports

### Generated Reports Directory Structure
```
scripts/bsee_migration/
├── reports/
│   ├── migration_metrics_YYYYMMDD_HHMMSS.yaml
│   ├── migration_metrics_YYYYMMDD_HHMMSS.html
│   └── migration_metrics_charts.png
├── health_reports/
│   └── health_check_YYYYMMDD_HHMMSS.yaml
├── logs/
│   └── health_check.log
└── import_transformations_YYYYMMDD_HHMMSS.yaml
```

### Report Types
- **Migration Metrics**: Comprehensive before/after comparison
- **Health Reports**: Daily monitoring results
- **Import Transformations**: Detailed transformation logs
- **Test Results**: Migration test outcomes
- **Workflow Logs**: Complete workflow execution logs

## 🚨 Error Handling and Recovery

### Common Issues and Solutions

1. **Import Failures**
   - Check syntax in transformed files
   - Verify new module structure exists
   - Review transformation rules in `update_python_imports.py`

2. **Test Failures**
   - Run individual test categories to isolate issues
   - Check file permissions and paths
   - Verify module dependencies

3. **Performance Issues**
   - Monitor import times with health checks
   - Check for circular dependencies
   - Review module loading order

### Rollback Procedures

1. **Rollback Import Changes**
   ```bash
   python update_python_imports.py --rollback
   ```

2. **Restore from Git**
   ```bash
   git checkout HEAD -- src/worldenergydata/
   ```

3. **Restore from Manual Backup**
   ```bash
   # Restore backup files created before migration
   find . -name "*.backup.*" -exec bash -c 'cp "$1" "${1%.backup.*}"' _ {} \;
   ```

## 📈 Monitoring and Maintenance

### Daily Health Checks
Set up automated daily monitoring:

```bash
# Add to crontab for daily 6 AM health check
0 6 * * * cd /path/to/worldenergydata && /usr/bin/python3 scripts/bsee_migration/daily_health_check.py --email
```

### Weekly Metrics Review
Generate weekly metrics reports:

```bash
# Add to crontab for weekly Sunday reports
0 9 * * 0 cd /path/to/worldenergydata && /usr/bin/python3 scripts/bsee_migration/migration_metrics_report.py --output-format=html --detailed
```

### Monthly Cleanup
Clean up old reports and logs:

```bash
# Add to crontab for monthly cleanup
0 2 1 * * find /path/to/worldenergydata/scripts/bsee_migration -name "*.yaml" -mtime +30 -delete
```

## 🏆 Best Practices

### Before Migration
- ✅ Run full test suite to ensure clean starting point
- ✅ Create complete backup of codebase
- ✅ Generate baseline metrics for comparison
- ✅ Notify team members of migration schedule

### During Migration
- ✅ Use dry-run mode first to identify potential issues
- ✅ Always create backups before modifying files
- ✅ Run tests after each major transformation
- ✅ Monitor transformation reports for unexpected changes

### After Migration
- ✅ Run comprehensive migration test suite
- ✅ Verify all critical functionality works correctly
- ✅ Set up daily health monitoring
- ✅ Update documentation to reflect new structure
- ✅ Schedule compatibility link cleanup after 30 days

### Ongoing Maintenance
- ✅ Monitor daily health check reports
- ✅ Review performance metrics for regressions
- ✅ Keep migration documentation updated
- ✅ Maintain rollback procedures and test them regularly

## 🤝 Contributing

When adding new migration scripts:

1. Follow the established naming convention
2. Include comprehensive command-line interface with examples
3. Add both dry-run and execution modes
4. Provide detailed logging and error handling
5. Update this README with script documentation
6. Add integration with the workflow demo script

## 📞 Support

For issues with the migration toolkit:

1. Check script help with `--help` flag
2. Review generated log files and reports
3. Use verbose mode for detailed debugging
4. Check the comprehensive test results for specific failures
5. Consult the workflow demo for best practice examples

---

*This toolkit ensures a smooth, monitored, and reversible migration process for the BSEE data consolidation initiative.*