#!/usr/bin/env python3
"""
Test runner script for the Personal AI Assistant
"""
import sys
import subprocess
import argparse
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and return the result"""
    print(f"\n🔬 {description}")
    print(f"Running: {' '.join(command)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def install_test_dependencies():
    """Install test dependencies"""
    return run_command(
        ["pip", "install", "pytest", "pytest-asyncio", "pytest-mock", "freezegun"],
        "Installing test dependencies"
    )


def run_unit_tests():
    """Run unit tests"""
    return run_command(
        ["python", "-m", "pytest", "tests/unit", "-v", "-m", "unit"],
        "Running unit tests"
    )


def run_integration_tests():
    """Run integration tests"""
    return run_command(
        ["python", "-m", "pytest", "tests/integration", "-v", "-m", "integration"],
        "Running integration tests"
    )


def run_calendar_tests():
    """Run calendar-specific tests"""
    return run_command(
        ["python", "-m", "pytest", "-v", "-m", "calendar"],
        "Running Google Calendar tests"
    )


def run_telegram_tests():
    """Run Telegram-specific tests"""
    return run_command(
        ["python", "-m", "pytest", "-v", "-m", "telegram"],
        "Running Telegram bot tests"
    )


def run_all_tests():
    """Run all tests"""
    return run_command(
        ["python", "-m", "pytest", "tests/", "-v"],
        "Running all tests"
    )


def run_fast_tests():
    """Run fast tests (excluding slow/external service tests and telegram tests)"""
    return run_command(
        ["python", "-m", "pytest", "tests/", "-v", "-m", "not slow and not telegram"],
        "Running fast tests (excluding slow and telegram tests)"
    )


def run_coverage_tests():
    """Run tests with coverage reporting"""
    commands = [
        (["pip", "install", "pytest-cov"], "Installing coverage tools"),
        (["python", "-m", "pytest", "tests/", "--cov=.", "--cov-report=html", "--cov-report=term"], 
         "Running tests with coverage")
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    print("\n📊 Coverage report generated in htmlcov/index.html")
    return True


def validate_project_structure():
    """Validate project structure"""
    print("\n🏗️  Validating project structure")
    print("-" * 50)
    
    required_files = [
        "main.py",
        "models/user.py",
        "models/agent_state.py",
        "nodes/planning.py",
        "nodes/checkins.py",
        "nodes/interrupts.py",
        "utils/telegram_bot.py",
        "utils/google_calendar.py",
        "prompts/system_prompt.py",
        "prompts/phase_prompts.py",
        "tests/conftest.py",
        "pytest.ini"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    else:
        print("✅ All required files present")
        return True


def run_lint_checks():
    """Run linting checks"""
    commands = [
        (["pip", "install", "flake8", "black"], "Installing linting tools"),
        (["python", "-m", "flake8", ".", "--max-line-length=100", "--exclude=venv"], "Running flake8 linting"),
        (["python", "-m", "black", ".", "--check", "--exclude=venv"], "Checking code formatting with black")
    ]
    
    success = True
    for command, description in commands:
        if not run_command(command, description):
            success = False
    
    return success


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Test runner for Personal AI Assistant")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--calendar", action="store_true", help="Run calendar tests")
    parser.add_argument("--telegram", action="store_true", help="Run Telegram tests")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--lint", action="store_true", help="Run linting checks")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    parser.add_argument("--validate", action="store_true", help="Validate project structure")
    parser.add_argument("--all", action="store_true", help="Run all tests and checks")
    
    args = parser.parse_args()
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print("🧪 Personal AI Assistant Test Runner")
    print("=" * 50)
    
    success = True
    
    if args.install_deps or args.all:
        if not install_test_dependencies():
            success = False
    
    if args.validate or args.all:
        if not validate_project_structure():
            success = False
    
    if args.lint or args.all:
        if not run_lint_checks():
            success = False
            print("⚠️  Linting issues found (not blocking)")
    
    if args.unit:
        if not run_unit_tests():
            success = False
    elif args.integration:
        if not run_integration_tests():
            success = False
    elif args.calendar:
        if not run_calendar_tests():
            success = False
    elif args.telegram:
        if not run_telegram_tests():
            success = False
    elif args.fast:
        if not run_fast_tests():
            success = False
    elif args.coverage:
        if not run_coverage_tests():
            success = False
    elif args.all:
        if not run_all_tests():
            success = False
    else:
        # Default: run fast tests
        if not run_fast_tests():
            success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())