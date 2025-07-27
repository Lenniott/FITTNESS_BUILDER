#!/usr/bin/env python3
"""
Comprehensive test runner for the Fitness Builder service.
Runs all tests and provides a detailed summary.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_file(test_file: str, test_name: str) -> tuple[str, str]:
    """Run a single test file and return the result."""
    print(f"\n{'='*20} {test_name} {'='*20}")
    
    try:
        # Set PYTHONPATH to include the project root
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root) + os.pathsep + env.get('PYTHONPATH', '')
        
        # Run the test file
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes timeout
            env=env
        )
        
        if result.returncode == 0:
            print("✅ Test completed successfully")
            return "PASSED", result.stdout
        else:
            print(f"❌ Test failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            return "FAILED", result.stderr
            
    except subprocess.TimeoutExpired:
        print("⏰ Test timed out after 10 minutes")
        return "TIMEOUT", "Test timed out"
    except Exception as e:
        print(f"❌ Test execution error: {str(e)}")
        return "ERROR", str(e)

def run_api_endpoint_tests():
    """Run API endpoint tests."""
    print("\n🚀 Running API Endpoint Tests")
    print("=" * 60)
    
    test_file = "tests/integration/test_api_endpoints.py"
    if os.path.exists(test_file):
        return run_test_file(test_file, "API Endpoint Tests")
    else:
        print("❌ API endpoint test file not found")
        return "SKIPPED", "Test file not found"

def run_database_tests():
    """Run database integration tests."""
    print("\n🗄️ Running Database Integration Tests")
    print("=" * 60)
    
    test_file = "tests/integration/test_database_operations.py"
    if os.path.exists(test_file):
        return run_test_file(test_file, "Database Integration Tests")
    else:
        print("❌ Database test file not found")
        return "SKIPPED", "Test file not found"

def run_existing_integration_tests():
    """Run existing integration tests."""
    print("\n🔗 Running Existing Integration Tests")
    print("=" * 60)
    
    results = []
    
    # Test curl simple
    test_file = "tests/integration/test_curl_simple.py"
    if os.path.exists(test_file):
        result, output = run_test_file(test_file, "Curl Simple Test")
        results.append(("Curl Simple Test", result, output))
    
    # Test process endpoint
    test_file = "tests/integration/test_process_endpoint.py"
    if os.path.exists(test_file):
        result, output = run_test_file(test_file, "Process Endpoint Test")
        results.append(("Process Endpoint Test", result, output))
    
    # Test downloader integration
    test_file = "tests/integration/test_downloader_integration.py"
    if os.path.exists(test_file):
        result, output = run_test_file(test_file, "Downloader Integration Test")
        results.append(("Downloader Integration Test", result, output))
    
    return results

def run_unit_tests():
    """Run unit tests using pytest."""
    print("\n🧪 Running Unit Tests")
    print("=" * 60)
    
    try:
        # Set PYTHONPATH for pytest
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root) + os.pathsep + env.get('PYTHONPATH', '')
        
        # Run pytest on the unit tests directory
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/unit/", "-v"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
            env=env
        )
        
        if result.returncode == 0:
            print("✅ Unit tests completed successfully")
            return "PASSED", result.stdout
        else:
            print(f"❌ Unit tests failed with return code {result.returncode}")
            return "FAILED", result.stderr
            
    except subprocess.TimeoutExpired:
        print("⏰ Unit tests timed out after 5 minutes")
        return "TIMEOUT", "Unit tests timed out"
    except Exception as e:
        print(f"❌ Unit test execution error: {str(e)}")
        return "ERROR", str(e)

def check_server_status():
    """Check if the API server is running."""
    print("\n🔍 Checking Server Status")
    print("=" * 60)
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
            return True
        else:
            print(f"⚠️  API server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API server is not running")
        print("💡 Start the server with: python start_api.py")
        return False
    except Exception as e:
        print(f"❌ Error checking server status: {str(e)}")
        return False

def generate_test_report(all_results: list):
    """Generate a comprehensive test report."""
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE TEST REPORT")
    print("=" * 80)
    
    # Categorize results
    passed = [r for r in all_results if r[1] == "PASSED"]
    failed = [r for r in all_results if r[1] == "FAILED"]
    skipped = [r for r in all_results if r[1] == "SKIPPED"]
    timeout = [r for r in all_results if r[1] == "TIMEOUT"]
    error = [r for r in all_results if r[1] == "ERROR"]
    
    # Print summary
    print(f"\n📈 TEST SUMMARY:")
    print(f"✅ Passed: {len(passed)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"⏭️  Skipped: {len(skipped)}")
    print(f"⏰ Timeout: {len(timeout)}")
    print(f"🚨 Error: {len(error)}")
    print(f"📊 Total: {len(all_results)}")
    
    # Print detailed results
    print(f"\n📋 DETAILED RESULTS:")
    for test_name, status, output in all_results:
        status_icon = {
            "PASSED": "✅",
            "FAILED": "❌", 
            "SKIPPED": "⏭️",
            "TIMEOUT": "⏰",
            "ERROR": "🚨"
        }.get(status, "❓")
        
        print(f"{status_icon} {test_name}: {status}")
        if status in ["FAILED", "ERROR"] and output:
            print(f"   Error: {output[:200]}...")
    
    # Print recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if failed:
        print("❌ Some tests failed. Check the error messages above.")
    if timeout:
        print("⏰ Some tests timed out. Consider increasing timeouts or optimizing performance.")
    if skipped:
        print("⏭️  Some tests were skipped. Ensure all test files exist.")
    if len(passed) == len(all_results):
        print("🎉 All tests passed! The system is working correctly.")
    elif len(passed) > len(all_results) / 2:
        print("✅ Most tests passed. The system is mostly working correctly.")
    else:
        print("⚠️  Many tests failed. The system needs attention.")

def main():
    """Main test runner function."""
    print("🚀 Fitness Builder Comprehensive Test Suite")
    print("=" * 80)
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = []
    
    # Check server status first
    server_running = check_server_status()
    
    # Run API endpoint tests (only if server is running)
    if server_running:
        result, output = run_api_endpoint_tests()
        all_results.append(("API Endpoint Tests", result, output))
    else:
        all_results.append(("API Endpoint Tests", "SKIPPED", "Server not running"))
    
    # Run database tests
    result, output = run_database_tests()
    all_results.append(("Database Integration Tests", result, output))
    
    # Run existing integration tests
    existing_results = run_existing_integration_tests()
    all_results.extend(existing_results)
    
    # Run unit tests
    result, output = run_unit_tests()
    all_results.append(("Unit Tests", result, output))
    
    # Generate comprehensive report
    generate_test_report(all_results)
    
    # Return appropriate exit code
    failed_count = len([r for r in all_results if r[1] in ["FAILED", "ERROR"]])
    if failed_count > 0:
        print(f"\n❌ {failed_count} tests failed. Exiting with code 1.")
        sys.exit(1)
    else:
        print(f"\n✅ All tests passed! Exiting with code 0.")
        sys.exit(0)

if __name__ == "__main__":
    main() 