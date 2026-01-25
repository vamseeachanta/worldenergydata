"""
Test runner script to verify SODIR integration tests.

This script runs all integration tests and provides a summary of results.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def run_integration_tests():
    """Run all integration tests and report results."""
    
    # Create test loader
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Test files to run
    test_modules = [
        'test_sodir_module',
        'test_api_client',
        'test_processors',
        'test_data_collection',
        'test_analysis',
        'test_integration',
        'test_cross_regional_validation',
        'test_performance'
    ]
    
    print("=" * 80)
    print("SODIR INTEGRATION TEST SUITE")
    print("=" * 80)
    print()
    
    # Load each test module
    loaded_tests = {}
    for module_name in test_modules:
        try:
            module = __import__(module_name)
            module_suite = loader.loadTestsFromModule(module)
            test_count = module_suite.countTestCases()
            suite.addTests(module_suite)
            loaded_tests[module_name] = test_count
            print(f"[OK] Loaded {module_name}: {test_count} tests")
        except ImportError as e:
            print(f"[FAIL] Failed to load {module_name}: {e}")
            loaded_tests[module_name] = 0
        except Exception as e:
            print(f"✗ Error loading {module_name}: {e}")
            loaded_tests[module_name] = 0
    
    print()
    print("-" * 80)
    print(f"Total tests loaded: {suite.countTestCases()}")
    print("-" * 80)
    print()
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    # Module summary
    print("Test Modules:")
    for module, count in loaded_tests.items():
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {module}: {count} tests")
    
    print()
    print("Test Results:")
    print(f"  Total Tests Run: {result.testsRun}")
    print(f"  Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    # Success rate
    if result.testsRun > 0:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
        print(f"  Success Rate: {success_rate:.1f}%")
    
    # Overall status
    print()
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
        
        # Show failures
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures[:5]:  # Show first 5
                print(f"  - {test}")
        
        # Show errors  
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors[:5]:  # Show first 5
                print(f"  - {test}")
    
    print()
    print("=" * 80)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


def verify_module_structure():
    """Verify that all required module files exist."""
    print("\nVerifying Module Structure:")
    print("-" * 40)
    
    required_files = [
        'sodir_module/__init__.py',
        'sodir_module/sodir.py',
        'sodir_module/api_client.py',
        'sodir_module/cache.py',
        'sodir_module/data.py',
        'sodir_module/analysis.py',
        'sodir_module/storage.py',
        'sodir_module/processors/__init__.py',
        'sodir_module/processors/block_processor.py',
        'sodir_module/processors/wellbore_processor.py',
        'sodir_module/processors/field_processor.py',
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        exists = full_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path}")
        if not exists:
            all_exist = False
    
    if all_exist:
        print("\n✅ All required module files exist!")
    else:
        print("\n⚠️  Some module files are missing!")
    
    return all_exist


if __name__ == "__main__":
    print("SODIR Integration Test Runner")
    print("=" * 80)
    
    # Verify module structure
    structure_ok = verify_module_structure()
    
    if not structure_ok:
        print("\n⚠️ Warning: Module structure incomplete, tests may fail")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            sys.exit(1)
    
    # Run tests
    exit_code = run_integration_tests()
    
    # Exit with appropriate code
    sys.exit(exit_code)