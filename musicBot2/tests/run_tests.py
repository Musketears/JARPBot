#!/usr/bin/env python3
"""
Test runner script for MusicBot2
"""

import unittest
import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_all_tests():
    """Run all test suites"""
    print("🧪 Running MusicBot2 Test Suite...\n")
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Create test runner
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    # Run tests
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False

def run_specific_test(test_name):
    """Run a specific test file"""
    print(f"🧪 Running specific test: {test_name}\n")
    
    # Import and run specific test
    test_module = f"tests.{test_name}"
    
    try:
        module = __import__(test_module, fromlist=[''])
        suite = unittest.TestLoader().loadTestsFromModule(module)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    except ImportError as e:
        print(f"❌ Error importing test module: {e}")
        return False

def run_unit_tests():
    """Run only unit tests"""
    print("🧪 Running Unit Tests...\n")
    
    unit_tests = [
        'test_config',
        'test_database', 
        'test_helpers',
        'test_gambling',
        'test_gacha',
        'test_logging_commands'
    ]
    
    all_passed = True
    for test in unit_tests:
        print(f"Running {test}...")
        if not run_specific_test(test):
            all_passed = False
    
    return all_passed

def run_integration_tests():
    """Run only integration tests"""
    print("🧪 Running Integration Tests...\n")
    
    return run_specific_test('test_integration')

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MusicBot2 Test Runner')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--test', type=str, help='Run specific test file')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    
    args = parser.parse_args()
    
    if args.test:
        success = run_specific_test(args.test)
    elif args.unit:
        success = run_unit_tests()
    elif args.integration:
        success = run_integration_tests()
    else:
        success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main() 