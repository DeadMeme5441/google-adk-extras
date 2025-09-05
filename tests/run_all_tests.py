#!/usr/bin/env python3
"""Test runner script to execute all tests."""

import asyncio
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_pytest_tests():
    """Run pytest tests."""
    import subprocess
    import sys
    
    # Run unit tests
    print("Running unit tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/unit/", 
        "-v", 
        "--tb=short"
    ], cwd=os.path.join(os.path.dirname(__file__), ".."))
    
    if result.returncode != 0:
        print("Unit tests failed!")
        return False
    
    # Run integration tests
    print("\nRunning integration tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/integration/", 
        "-v", 
        "--tb=short"
    ], cwd=os.path.join(os.path.dirname(__file__), ".."))
    
    if result.returncode != 0:
        print("Integration tests failed!")
        return False
    
    # Run end-to-end tests
    print("\nRunning end-to-end tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/e2e/", 
        "-v", 
        "--tb=short"
    ], cwd=os.path.join(os.path.dirname(__file__), ".."))
    
    if result.returncode != 0:
        print("End-to-end tests failed!")
        return False
    
    print("\nAll tests passed! ✓")
    return True

def run_legacy_tests():
    """Run legacy test scripts."""
    import subprocess
    import sys
    
    print("Running legacy session service tests...")
    result = subprocess.run([
        sys.executable, "tests/test_session_services_integration.py"
    ], cwd=os.path.join(os.path.dirname(__file__), ".."))
    
    if result.returncode != 0:
        print("Legacy session service tests failed!")
        return False
    
    print("Running legacy artifact service tests...")
    result = subprocess.run([
        sys.executable, "tests/test_artifact_services_integration.py"
    ], cwd=os.path.join(os.path.dirname(__file__), ".."))
    
    if result.returncode != 0:
        print("Legacy artifact service tests failed!")
        return False
    
    return True

async def main():
    """Run all tests."""
    print("Running comprehensive test suite...\n")
    
    # Run pytest tests
    pytest_success = run_pytest_tests()
    
    if not pytest_success:
        print("\nPytest tests failed!")
        return 1
    
    # Run legacy tests
    legacy_success = run_legacy_tests()
    
    if not legacy_success:
        print("\nLegacy tests failed!")
        return 1
    
    print("\n🎉 All tests passed! 🎉")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)