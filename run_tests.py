#!/usr/bin/env python3
"""
Test runner script for ODG Liguria Workflow.
Runs the complete test suite with different configurations.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} - FAILED")
        if result.stderr:
            print(f"Error: {result.stderr}")
        if result.stdout:
            print(f"Output: {result.stdout}")
    
    return result.returncode == 0


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="ODG Liguria Workflow Test Runner")
    parser.add_argument("--lint", action="store_true", help="Run linting checks")
    parser.add_argument("--test", action="store_true", help="Run tests")
    parser.add_argument("--security", action="store_true", help="Run security checks")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Default to running all if no specific option is chosen
    if not any([args.lint, args.test, args.security, args.coverage]):
        args.all = True
    
    success = True
    
    print("🚀 ODG Liguria Workflow Test Runner")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("src").exists():
        print("❌ Error: Run this script from the project root directory")
        sys.exit(1)
    
    # Run linting checks
    if args.lint or args.all:
        print("\n📋 LINTING CHECKS")
        print("-" * 30)
        
        # Black formatting check
        if not run_command(["black", "--check", "--diff", "src/", "scripts/"], "Black formatting check"):
            success = False
        
        # isort import sorting check
        if not run_command(["isort", "--check-only", "--diff", "src/", "scripts/"], "isort import sorting check"):
            success = False
        
        # Flake8 style check
        if not run_command(["flake8", "src/", "scripts/", "--max-line-length=100", "--extend-ignore=E203,W503"], "Flake8 style check"):
            success = False
        
        # MyPy type checking (optional)
        run_command(["mypy", "src/", "--ignore-missing-imports"], "MyPy type checking (optional)")
    
    # Run tests
    if args.test or args.all or args.coverage:
        print("\n🧪 TESTING")
        print("-" * 30)
        
        # Create test directories if they don't exist
        Path("tests/unit").mkdir(parents=True, exist_ok=True)
        Path("tests/integration").mkdir(parents=True, exist_ok=True)
        
        test_cmd = ["pytest", "tests/", "-v"]
        
        if args.coverage or args.all:
            test_cmd.extend(["--cov=src", "--cov-report=term-missing", "--cov-report=html"])
        
        if args.verbose:
            test_cmd.append("-s")
        
        if not run_command(test_cmd, "Pytest test suite"):
            success = False
    
    # Run security checks
    if args.security or args.all:
        print("\n🔒 SECURITY CHECKS")
        print("-" * 30)
        
        # Bandit security check
        run_command(["bandit", "-r", "src/", "-f", "text"], "Bandit security scan")
        
        # Safety vulnerability check
        run_command(["safety", "check"], "Safety vulnerability check")
    
    # Final result
    print("\n" + "=" * 50)
    if success:
        print("✅ All checks passed successfully!")
        sys.exit(0)
    else:
        print("❌ Some checks failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()