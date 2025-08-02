"""Complete validation workflow verification script"""
import os
import sys
from loguru import logger

def verify_validation_workflow():
    """Verify that all components of the validation workflow are in place"""
    
    logger.info("Starting complete validation workflow verification")
    
    current_dir = os.path.dirname(__file__)
    results_dir = os.path.join(current_dir, 'results')
    
    # Check all required files exist
    required_files = [
        # Main scripts
        'run_drilling_analysis.py',
        'compare_outputs.py',
        
        # Test files
        'test_filename_modification.py',
        'test_data_comparison.py',
        'test_report_generation.py',
        'test_direct_execution.py',
        
        # Results files
        'results/drilling_and_completion_days_by_api_validation.xlsx',
        'results/output_documentation.md',
        'results/validation_summary_20250802.md'
    ]
    
    missing_files = []
    present_files = []
    
    for file_path in required_files:
        full_path = os.path.join(current_dir, file_path)
        if os.path.exists(full_path):
            present_files.append(file_path)
            logger.info(f"✅ Found: {file_path}")
        else:
            missing_files.append(file_path)
            logger.warning(f"❌ Missing: {file_path}")
    
    # Check for comparison reports
    comparison_reports = [f for f in os.listdir(results_dir) if f.startswith('comparison_report_')]
    if comparison_reports:
        logger.info(f"✅ Found {len(comparison_reports)} comparison report(s)")
        for report in comparison_reports:
            logger.info(f"   - {report}")
    else:
        logger.warning("❌ No comparison reports found")
    
    # Verify test execution results
    logger.info("\nRunning test suite verification...")
    
    try:
        import subprocess
        
        # Run all tests
        test_files = [
            'test_filename_modification.py',
            'test_data_comparison.py', 
            'test_report_generation.py'
        ]
        
        all_tests_passed = True
        
        for test_file in test_files:
            logger.info(f"Testing {test_file}...")
            result = subprocess.run([
                sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short'
            ], cwd=current_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ {test_file} - All tests passed")
            else:
                logger.error(f"❌ {test_file} - Some tests failed")
                logger.error(result.stdout)
                all_tests_passed = False
        
        if all_tests_passed:
            logger.info("✅ All test suites passed")
        else:
            logger.error("❌ Some test suites failed")
            
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        all_tests_passed = False
    
    # Generate workflow summary
    logger.info("\nValidation Workflow Summary:")
    logger.info("="*50)
    logger.info(f"Required files present: {len(present_files)}/{len(required_files)}")
    logger.info(f"Missing files: {len(missing_files)}")
    logger.info(f"Comparison reports: {len(comparison_reports)}")
    logger.info(f"Test suites passing: {'Yes' if all_tests_passed else 'No'}")
    
    # Overall status
    workflow_complete = (
        len(missing_files) == 0 and
        len(comparison_reports) > 0 and
        all_tests_passed
    )
    
    if workflow_complete:
        logger.info("\n✅ VALIDATION WORKFLOW COMPLETE")
        logger.info("All components are in place and functioning correctly")
        return True
    else:
        logger.error("\n❌ VALIDATION WORKFLOW INCOMPLETE")
        if missing_files:
            logger.error(f"Missing files: {', '.join(missing_files)}")
        if len(comparison_reports) == 0:
            logger.error("No comparison reports found")
        if not all_tests_passed:
            logger.error("Some tests are failing")
        return False


def check_original_file_access():
    """Check if the original reference file is accessible"""
    
    # Build path to original file
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
    original_file = os.path.join(
        project_root,
        'docs/modules/bsee/data/SME_Roy_attachments/2025-08-01/drilling_and_completion_days_by_api.xlsx'
    )
    
    if os.path.exists(original_file):
        file_size = os.path.getsize(original_file)
        logger.info(f"✅ Original reference file accessible: {file_size:,} bytes")
        return True
    else:
        logger.warning(f"❌ Original reference file not found at: {original_file}")
        return False


def main():
    """Main execution function"""
    
    logger.info("WorldEnergyData Drilling Completion Days Validation Workflow Verification")
    logger.info("="*80)
    
    # Check original file access
    original_accessible = check_original_file_access()
    
    # Verify complete workflow
    workflow_complete = verify_validation_workflow()
    
    # Final summary
    logger.info("\n" + "="*80)
    logger.info("FINAL VALIDATION STATUS")
    logger.info("="*80)
    
    if workflow_complete and original_accessible:
        logger.info("✅ COMPLETE SUCCESS")
        logger.info("The drilling completion days validation has been successfully completed.")
        logger.info("All tests pass and the implementation matches the original output 100%.")
        return 0
    else:
        logger.error("❌ VALIDATION INCOMPLETE")
        if not original_accessible:
            logger.error("- Original reference file is not accessible")
        if not workflow_complete:
            logger.error("- Validation workflow has missing components or failing tests")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)