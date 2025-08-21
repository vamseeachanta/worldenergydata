#!/usr/bin/env python3
"""
BSEE Data Consolidation - Daily Health Check Script

Automated daily health monitoring for the BSEE consolidated structure.
Monitors imports, functionality, performance, and data integrity.

Usage:
    python daily_health_check.py [--email] [--slack] [--config=path/to/config.yaml]
    
Schedule with cron:
    # Run daily at 6 AM
    0 6 * * * /usr/bin/python3 /path/to/daily_health_check.py --email
"""

import argparse
import json
import smtplib
import sys
import time
import traceback
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests
import yaml


class BSEEHealthChecker:
    """Daily health monitoring for BSEE consolidated structure."""
    
    def __init__(self, base_path: str = None, config_path: str = None):
        """Initialize health checker.
        
        Args:
            base_path: Base path for WorldEnergyData project
            config_path: Path to configuration file
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.config = self._load_config(config_path)
        self.health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'UNKNOWN',
            'checks': {},
            'alerts': [],
            'metrics': {}
        }
        
        # Add project to Python path
        src_path = self.base_path / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
            
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            'health_check': {
                'critical_imports': [
                    'worldenergydata.bsee',
                    'worldenergydata.bsee.data_collection',
                    'worldenergydata.bsee.analysis',
                    'worldenergydata.bsee.processing'
                ],
                'performance_thresholds': {
                    'max_import_time': 5.0,  # seconds
                    'max_memory_usage': 500  # MB
                },
                'alert_thresholds': {
                    'import_failure_rate': 0.2,  # 20%
                    'performance_degradation': 0.5  # 50% slower
                }
            },
            'notifications': {
                'email': {
                    'enabled': False,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'recipients': []
                },
                'slack': {
                    'enabled': False,
                    'webhook_url': '',
                    'channel': '#alerts'
                }
            },
            'logging': {
                'log_file': 'health_check.log',
                'retention_days': 30
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    # Merge with defaults
                    self._deep_merge(default_config, user_config)
            except Exception as e:
                print(f"⚠️  Could not load config from {config_path}: {e}")
                
        return default_config
        
    def _deep_merge(self, base_dict: Dict, update_dict: Dict) -> None:
        """Deep merge configuration dictionaries."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
                
    def log(self, message: str, level: str = "INFO") -> None:
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        
        # Write to log file if configured
        log_file = self.config['logging'].get('log_file')
        if log_file:
            log_path = self.base_path / "scripts" / "bsee_migration" / "logs" / log_file
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, 'a') as f:
                f.write(log_entry + '\n')
                
    def check_critical_imports(self) -> Dict[str, Any]:
        """Check that all critical imports work correctly."""
        self.log("🔍 Checking critical imports...")
        
        critical_imports = self.config['health_check']['critical_imports']
        import_results = {
            'total_imports': len(critical_imports),
            'successful_imports': 0,
            'failed_imports': [],
            'import_times': {},
            'status': 'PASS'
        }
        
        for import_path in critical_imports:
            try:
                start_time = time.time()
                __import__(import_path)
                import_time = time.time() - start_time
                
                import_results['successful_imports'] += 1
                import_results['import_times'][import_path] = import_time
                
                self.log(f"   ✅ {import_path}: {import_time:.3f}s")
                
            except Exception as e:
                import_results['failed_imports'].append({
                    'import': import_path,
                    'error': str(e)
                })
                self.log(f"   ❌ {import_path}: {e}", "ERROR")
                
        # Calculate failure rate
        failure_rate = len(import_results['failed_imports']) / len(critical_imports)
        alert_threshold = self.config['health_check']['alert_thresholds']['import_failure_rate']
        
        if failure_rate > alert_threshold:
            import_results['status'] = 'FAIL'
            self.health_status['alerts'].append({
                'type': 'CRITICAL_IMPORT_FAILURE',
                'message': f"Import failure rate {failure_rate:.1%} exceeds threshold {alert_threshold:.1%}",
                'details': import_results['failed_imports']
            })
        elif len(import_results['failed_imports']) > 0:
            import_results['status'] = 'WARN'
            self.health_status['alerts'].append({
                'type': 'IMPORT_WARNING',
                'message': f"{len(import_results['failed_imports'])} imports failed",
                'details': import_results['failed_imports']
            })
            
        self.log(f"   📊 Import success rate: {(1-failure_rate):.1%}")
        return import_results
        
    def check_performance_metrics(self) -> Dict[str, Any]:
        """Check performance metrics against thresholds."""
        self.log("⚡ Checking performance metrics...")
        
        performance_results = {
            'total_import_time': 0,
            'memory_usage_mb': 0,
            'performance_score': 0,
            'status': 'PASS'
        }
        
        # Measure total import time
        critical_imports = self.config['health_check']['critical_imports']
        start_time = time.time()
        
        for import_path in critical_imports:
            try:
                __import__(import_path)
            except Exception:
                pass  # Already handled in import check
                
        performance_results['total_import_time'] = time.time() - start_time
        
        # Check memory usage
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            performance_results['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024
        except ImportError:
            self.log("   ⚠️  psutil not available for memory monitoring")
            
        # Check against thresholds
        thresholds = self.config['health_check']['performance_thresholds']
        
        if performance_results['total_import_time'] > thresholds['max_import_time']:
            performance_results['status'] = 'WARN'
            self.health_status['alerts'].append({
                'type': 'SLOW_IMPORTS',
                'message': f"Import time {performance_results['total_import_time']:.2f}s exceeds threshold {thresholds['max_import_time']}s"
            })
            
        if performance_results['memory_usage_mb'] > thresholds['max_memory_usage']:
            performance_results['status'] = 'WARN'
            self.health_status['alerts'].append({
                'type': 'HIGH_MEMORY_USAGE',
                'message': f"Memory usage {performance_results['memory_usage_mb']:.1f}MB exceeds threshold {thresholds['max_memory_usage']}MB"
            })
            
        # Calculate performance score (0-100)
        import_score = min(100, (thresholds['max_import_time'] / max(performance_results['total_import_time'], 0.1)) * 50)
        memory_score = min(100, (thresholds['max_memory_usage'] / max(performance_results['memory_usage_mb'], 1)) * 50)
        performance_results['performance_score'] = import_score + memory_score
        
        self.log(f"   📊 Import time: {performance_results['total_import_time']:.2f}s")
        self.log(f"   📊 Memory usage: {performance_results['memory_usage_mb']:.1f}MB")
        self.log(f"   📊 Performance score: {performance_results['performance_score']:.0f}/100")
        
        return performance_results
        
    def check_file_integrity(self) -> Dict[str, Any]:
        """Check file integrity of BSEE modules."""
        self.log("📁 Checking file integrity...")
        
        integrity_results = {
            'expected_files': [],
            'missing_files': [],
            'corrupted_files': [],
            'status': 'PASS'
        }
        
        bsee_path = self.base_path / "src" / "worldenergydata" / "bsee"
        expected_files = [
            '__init__.py',
            'data_collection.py',
            'analysis.py',
            'processing.py'
        ]
        
        for filename in expected_files:
            file_path = bsee_path / filename
            integrity_results['expected_files'].append(filename)
            
            if not file_path.exists():
                integrity_results['missing_files'].append(filename)
                self.log(f"   ❌ Missing file: {filename}", "ERROR")
            else:
                # Basic syntax check
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        compile(f.read(), str(file_path), 'exec')
                    self.log(f"   ✅ File OK: {filename}")
                except SyntaxError as e:
                    integrity_results['corrupted_files'].append({
                        'file': filename,
                        'error': str(e)
                    })
                    self.log(f"   ❌ Syntax error in {filename}: {e}", "ERROR")
                except Exception as e:
                    self.log(f"   ⚠️  Could not check {filename}: {e}", "WARN")
                    
        if integrity_results['missing_files'] or integrity_results['corrupted_files']:
            integrity_results['status'] = 'FAIL'
            self.health_status['alerts'].append({
                'type': 'FILE_INTEGRITY_ISSUE',
                'message': f"Found {len(integrity_results['missing_files'])} missing and {len(integrity_results['corrupted_files'])} corrupted files",
                'details': {
                    'missing': integrity_results['missing_files'],
                    'corrupted': integrity_results['corrupted_files']
                }
            })
            
        return integrity_results
        
    def check_functionality_samples(self) -> Dict[str, Any]:
        """Check basic functionality with sample operations."""
        self.log("🔧 Checking functionality samples...")
        
        functionality_results = {
            'tested_functions': [],
            'successful_functions': 0,
            'failed_functions': [],
            'status': 'PASS'
        }
        
        # Test basic class instantiation
        test_cases = [
            ('worldenergydata.bsee.data_collection', 'BSEEDataCollector'),
            ('worldenergydata.bsee.analysis', 'ProductionAnalyzer'),
            ('worldenergydata.bsee.processing', 'DirectionalProcessor')
        ]
        
        for module_path, class_name in test_cases:
            test_name = f"{module_path}.{class_name}"
            functionality_results['tested_functions'].append(test_name)
            
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                instance = cls()  # Basic instantiation test
                
                functionality_results['successful_functions'] += 1
                self.log(f"   ✅ {test_name} instantiation OK")
                
            except Exception as e:
                functionality_results['failed_functions'].append({
                    'function': test_name,
                    'error': str(e)
                })
                self.log(f"   ❌ {test_name} failed: {e}", "ERROR")
                
        # Check success rate
        total_tests = len(functionality_results['tested_functions'])
        success_rate = functionality_results['successful_functions'] / total_tests if total_tests > 0 else 0
        
        if success_rate < 0.8:  # 80% success required
            functionality_results['status'] = 'FAIL'
            self.health_status['alerts'].append({
                'type': 'FUNCTIONALITY_FAILURE',
                'message': f"Functionality success rate {success_rate:.1%} below 80%",
                'details': functionality_results['failed_functions']
            })
        elif functionality_results['failed_functions']:
            functionality_results['status'] = 'WARN'
            
        self.log(f"   📊 Functionality success rate: {success_rate:.1%}")
        return functionality_results
        
    def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks and compile results."""
        self.log("🚀 Starting BSEE daily health check...")
        start_time = time.time()
        
        # Run individual checks
        self.health_status['checks']['imports'] = self.check_critical_imports()
        self.health_status['checks']['performance'] = self.check_performance_metrics()
        self.health_status['checks']['file_integrity'] = self.check_file_integrity()
        self.health_status['checks']['functionality'] = self.check_functionality_samples()
        
        # Determine overall status
        check_statuses = [check['status'] for check in self.health_status['checks'].values()]
        
        if 'FAIL' in check_statuses:
            self.health_status['overall_status'] = 'FAIL'
        elif 'WARN' in check_statuses:
            self.health_status['overall_status'] = 'WARN'
        else:
            self.health_status['overall_status'] = 'PASS'
            
        # Add summary metrics
        self.health_status['metrics'] = {
            'total_checks': len(self.health_status['checks']),
            'passed_checks': len([s for s in check_statuses if s == 'PASS']),
            'warning_checks': len([s for s in check_statuses if s == 'WARN']),
            'failed_checks': len([s for s in check_statuses if s == 'FAIL']),
            'total_alerts': len(self.health_status['alerts']),
            'check_duration': time.time() - start_time
        }
        
        self.log(f"✅ Health check complete in {self.health_status['metrics']['check_duration']:.2f}s")
        self.log(f"📊 Overall status: {self.health_status['overall_status']}")
        self.log(f"📊 Alerts generated: {self.health_status['metrics']['total_alerts']}")
        
        return self.health_status
        
    def save_health_report(self) -> Path:
        """Save health check report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = self.base_path / "scripts" / "bsee_migration" / "health_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = reports_dir / f"health_check_{timestamp}.yaml"
        
        with open(report_file, 'w') as f:
            yaml.dump(self.health_status, f, default_flow_style=False, sort_keys=False)
            
        self.log(f"📄 Health report saved to: {report_file}")
        
        # Clean up old reports
        self._cleanup_old_reports(reports_dir)
        
        return report_file
        
    def _cleanup_old_reports(self, reports_dir: Path) -> None:
        """Clean up old health reports based on retention policy."""
        retention_days = self.config['logging']['retention_days']
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for report_file in reports_dir.glob("health_check_*.yaml"):
            try:
                file_time = datetime.fromtimestamp(report_file.stat().st_mtime)
                if file_time < cutoff_date:
                    report_file.unlink()
                    self.log(f"🗑️  Cleaned up old report: {report_file.name}")
            except Exception as e:
                self.log(f"⚠️  Could not clean up {report_file}: {e}")
                
    def send_email_notification(self) -> bool:
        """Send email notification if configured and needed."""
        email_config = self.config['notifications']['email']
        if not email_config['enabled'] or not email_config['recipients']:
            return False
            
        # Only send email for WARN or FAIL status
        if self.health_status['overall_status'] == 'PASS':
            return False
            
        try:
            subject = f"BSEE Health Check Alert - {self.health_status['overall_status']}"
            
            body = f"""
BSEE Daily Health Check Report
Generated: {self.health_status['timestamp']}
Overall Status: {self.health_status['overall_status']}

Summary:
- Total Checks: {self.health_status['metrics']['total_checks']}
- Passed: {self.health_status['metrics']['passed_checks']}
- Warnings: {self.health_status['metrics']['warning_checks']}
- Failed: {self.health_status['metrics']['failed_checks']}
- Total Alerts: {self.health_status['metrics']['total_alerts']}

Alerts:
"""
            
            for alert in self.health_status['alerts']:
                body += f"- {alert['type']}: {alert['message']}\n"
                
            # Send email
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            self.log(f"📧 Email notification sent to {len(email_config['recipients'])} recipients")
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to send email notification: {e}", "ERROR")
            return False
            
    def send_slack_notification(self) -> bool:
        """Send Slack notification if configured and needed."""
        slack_config = self.config['notifications']['slack']
        if not slack_config['enabled'] or not slack_config['webhook_url']:
            return False
            
        # Only send notification for WARN or FAIL status
        if self.health_status['overall_status'] == 'PASS':
            return False
            
        try:
            status_emoji = "🚨" if self.health_status['overall_status'] == 'FAIL' else "⚠️"
            
            message = {
                "channel": slack_config['channel'],
                "text": f"{status_emoji} BSEE Health Check Alert",
                "attachments": [
                    {
                        "color": "danger" if self.health_status['overall_status'] == 'FAIL' else "warning",
                        "title": f"Health Check Status: {self.health_status['overall_status']}",
                        "fields": [
                            {
                                "title": "Timestamp",
                                "value": self.health_status['timestamp'],
                                "short": True
                            },
                            {
                                "title": "Total Alerts",
                                "value": str(self.health_status['metrics']['total_alerts']),
                                "short": True
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(slack_config['webhook_url'], json=message)
            response.raise_for_status()
            
            self.log(f"📱 Slack notification sent")
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to send Slack notification: {e}", "ERROR")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BSEE daily health check monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic health check
    python daily_health_check.py
    
    # With email notifications
    python daily_health_check.py --email
    
    # With Slack notifications  
    python daily_health_check.py --slack
    
    # Custom config file
    python daily_health_check.py --config=/path/to/config.yaml
    
Cron Setup:
    # Run daily at 6 AM
    0 6 * * * /usr/bin/python3 /path/to/daily_health_check.py --email
        """
    )
    
    parser.add_argument(
        '--email',
        action='store_true',
        help='Enable email notifications'
    )
    parser.add_argument(
        '--slack',
        action='store_true',
        help='Enable Slack notifications'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    parser.add_argument(
        '--base-path',
        type=str,
        help='Base path for WorldEnergyData project'
    )
    
    args = parser.parse_args()
    
    # Initialize health checker
    health_checker = BSEEHealthChecker(
        base_path=args.base_path,
        config_path=args.config
    )
    
    # Override notification settings from command line
    if args.email:
        health_checker.config['notifications']['email']['enabled'] = True
    if args.slack:
        health_checker.config['notifications']['slack']['enabled'] = True
        
    try:
        # Run health checks
        health_status = health_checker.run_health_checks()
        
        # Save report
        health_checker.save_health_report()
        
        # Send notifications
        if args.email or health_checker.config['notifications']['email']['enabled']:
            health_checker.send_email_notification()
            
        if args.slack or health_checker.config['notifications']['slack']['enabled']:
            health_checker.send_slack_notification()
            
        # Exit with appropriate code
        if health_status['overall_status'] == 'FAIL':
            sys.exit(1)
        elif health_status['overall_status'] == 'WARN':
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"💥 Health check crashed: {e}")
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()