#!/usr/bin/env python3
"""
Test Automation Script for EBL Simulation

Comprehensive test runner with different test profiles for development,
CI/CD, and comprehensive validation scenarios.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
import json
import os


class TestRunner:
    """Automated test runner for EBL simulation."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.results = {}
        self.start_time = time.time()
    
    def run_unit_tests(self, fast_only: bool = False) -> bool:
        """Run unit tests."""
        print("🧪 Running Unit Tests...")
        
        cmd = [
            "pytest", "unit/",
            "-v",
            "--tb=short",
            "--cov=python/ebl_sim_modular",
            "--cov-report=term-missing",
            "--junit-xml=junit_unit.xml"
        ]
        
        if fast_only:
            cmd.extend(["-m", "not slow"])
        
        return self._run_pytest(cmd, "unit_tests")
    
    def run_integration_tests(self, with_geant4: bool = False) -> bool:
        """Run integration tests."""
        print("🔗 Running Integration Tests...")
        
        cmd = [
            "pytest", "integration/",
            "-v",
            "--tb=short",
            "--junit-xml=junit_integration.xml"
        ]
        
        if with_geant4:
            cmd.append("--run-integration")
        else:
            cmd.extend(["-m", "not geant4"])
        
        return self._run_pytest(cmd, "integration_tests")
    
    def run_pattern_tests(self, extended: bool = False) -> bool:
        """Run pattern generation tests with property-based testing."""
        print("📐 Running Pattern Generation Tests...")
        
        cmd = [
            "pytest", "unit/test_pattern_generation.py",
            "-v",
            "--tb=short",
            "--junit-xml=junit_patterns.xml"
        ]
        
        if extended:
            cmd.extend([
                "--hypothesis-max-examples=1000",
                "--hypothesis-derandomize"
            ])
        
        return self._run_pytest(cmd, "pattern_tests")
    
    def run_performance_tests(self) -> bool:
        """Run performance and benchmark tests."""
        print("⚡ Running Performance Tests...")
        
        cmd = [
            "pytest", "performance/",
            "-v",
            "--run-slow",
            "--tb=short",
            "--junit-xml=junit_performance.xml"
        ]
        
        return self._run_pytest(cmd, "performance_tests")
    
    def run_gui_tests(self) -> bool:
        """Run GUI tests (if display available)."""
        print("🖥️  Running GUI Tests...")
        
        if not self._check_display():
            print("⚠️  No display available, skipping GUI tests")
            return True
        
        cmd = [
            "pytest", "gui/",
            "-v",
            "--run-gui",
            "--tb=short",
            "--junit-xml=junit_gui.xml"
        ]
        
        return self._run_pytest(cmd, "gui_tests")
    
    def run_mock_geant4_tests(self) -> bool:
        """Run tests that use Geant4 mocks."""
        print("🎭 Running Mock Geant4 Tests...")
        
        cmd = [
            "pytest",
            "-v",
            "-m", "mock_geant4",
            "--tb=short",
            "--junit-xml=junit_mocks.xml"
        ]
        
        return self._run_pytest(cmd, "mock_geant4_tests")
    
    def run_physics_validation(self) -> bool:
        """Run physics validation tests."""
        print("⚛️  Running Physics Validation Tests...")
        
        cmd = [
            "pytest",
            "-v",
            "-m", "physics",
            "--run-slow",
            "--tb=short",
            "--junit-xml=junit_physics.xml"
        ]
        
        return self._run_pytest(cmd, "physics_validation")
    
    def _run_pytest(self, cmd: List[str], test_name: str) -> bool:
        """Run pytest command and capture results."""
        start_time = time.time()
        
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = time.time() - start_time
            
            success = result.returncode == 0
            
            self.results[test_name] = {
                'success': success,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
            
            if success:
                print(f"✅ {test_name} passed ({duration:.1f}s)")
            else:
                print(f"❌ {test_name} failed ({duration:.1f}s)")
                print(f"   Error: {result.stderr.strip()}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error running {test_name}: {e}")
            self.results[test_name] = {
                'success': False,
                'duration': time.time() - start_time,
                'error': str(e)
            }
            return False
        
        finally:
            os.chdir(original_cwd)
    
    def _check_display(self) -> bool:
        """Check if display is available for GUI tests."""
        return os.environ.get('DISPLAY') is not None or os.environ.get('WAYLAND_DISPLAY') is not None
    
    def run_code_quality_checks(self) -> bool:
        """Run code quality checks."""
        print("🔍 Running Code Quality Checks...")
        
        checks = [
            ("Black formatting", ["black", "--check", "--diff", "python/", "tests/"]),
            ("Flake8 linting", ["flake8", "python/", "tests/", "--max-line-length=88"]),
            ("MyPy type checking", ["mypy", "python/ebl_sim_modular/", "--ignore-missing-imports"]),
            ("Import sorting", ["isort", "--check-only", "--diff", "python/", "tests/"])
        ]
        
        all_passed = True
        
        for check_name, cmd in checks:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode == 0:
                    print(f"✅ {check_name} passed")
                else:
                    print(f"❌ {check_name} failed")
                    print(f"   Output: {result.stdout.strip()}")
                    all_passed = False
                    
            except Exception as e:
                print(f"❌ Error running {check_name}: {e}")
                all_passed = False
        
        return all_passed
    
    def generate_coverage_report(self) -> None:
        """Generate comprehensive coverage report."""
        print("📊 Generating Coverage Report...")
        
        try:
            # Combine coverage data
            subprocess.run(["coverage", "combine"], cwd=self.test_dir, check=True)
            
            # Generate HTML report
            subprocess.run(["coverage", "html"], cwd=self.test_dir, check=True)
            
            # Generate XML report for CI
            subprocess.run(["coverage", "xml"], cwd=self.test_dir, check=True)
            
            # Show coverage report
            result = subprocess.run(["coverage", "report"], cwd=self.test_dir, capture_output=True, text=True)
            print(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error generating coverage report: {e}")
    
    def print_summary(self) -> None:
        """Print test execution summary."""
        total_duration = time.time() - self.start_time
        
        print("\n" + "="*60)
        print("🎯 TEST EXECUTION SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.results.values() if r['success'])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Total Duration: {total_duration:.1f}s")
        print()
        
        # Detailed results
        for test_name, result in self.results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            duration = result['duration']
            print(f"{status} {test_name:<25} ({duration:.1f}s)")
        
        print("\n" + "="*60)
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {total - passed} test(s) failed")
            return False
    
    def save_results(self, output_file: Path) -> None:
        """Save test results to JSON file."""
        results_data = {
            'timestamp': time.time(),
            'total_duration': time.time() - self.start_time,
            'results': self.results,
            'summary': {
                'total': len(self.results),
                'passed': sum(1 for r in self.results.values() if r['success']),
                'failed': sum(1 for r in self.results.values() if not r['success'])
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"📝 Test results saved to {output_file}")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="EBL Simulation Test Runner")
    
    # Test selection
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--patterns", action="store_true", help="Run pattern tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--gui", action="store_true", help="Run GUI tests")
    parser.add_argument("--mocks", action="store_true", help="Run mock Geant4 tests")
    parser.add_argument("--physics", action="store_true", help="Run physics validation tests")
    parser.add_argument("--quality", action="store_true", help="Run code quality checks")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    # Test options
    parser.add_argument("--fast", action="store_true", help="Run only fast tests")
    parser.add_argument("--with-geant4", action="store_true", help="Include Geant4 integration tests")
    parser.add_argument("--extended-patterns", action="store_true", help="Run extended pattern tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    
    # Output options
    parser.add_argument("--output", type=str, help="Save results to JSON file")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    
    # Profiles
    parser.add_argument("--profile", choices=["dev", "ci", "full"], help="Use predefined test profile")
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(__file__).parent.parent
    runner = TestRunner(project_root)
    
    if not args.quiet:
        print("🚀 EBL Simulation Test Suite")
        print(f"Project root: {project_root}")
        print(f"Test directory: {runner.test_dir}")
        print()
    
    # Handle profiles
    if args.profile == "dev":
        # Development profile: fast unit tests and integration tests
        args.unit = True
        args.integration = True
        args.patterns = True
        args.mocks = True
        args.fast = True
    elif args.profile == "ci":
        # CI profile: comprehensive but no GUI or slow tests
        args.unit = True
        args.integration = True
        args.patterns = True
        args.mocks = True
        args.quality = True
        args.coverage = True
    elif args.profile == "full":
        # Full profile: everything
        args.all = True
        args.extended_patterns = True
        args.coverage = True
    
    # Default to unit tests if nothing specified
    if not any([args.unit, args.integration, args.patterns, args.performance, 
               args.gui, args.mocks, args.physics, args.quality, args.all]):
        args.unit = True
    
    # Run selected tests
    all_passed = True
    
    if args.all:
        # Run all test categories
        test_functions = [
            lambda: runner.run_unit_tests(args.fast),
            lambda: runner.run_integration_tests(args.with_geant4),
            lambda: runner.run_pattern_tests(args.extended_patterns),
            lambda: runner.run_mock_geant4_tests(),
            lambda: runner.run_performance_tests(),
            lambda: runner.run_gui_tests(),
            lambda: runner.run_physics_validation()
        ]
        
        for test_func in test_functions:
            if not test_func():
                all_passed = False
    else:
        # Run selected test categories
        if args.unit and not runner.run_unit_tests(args.fast):
            all_passed = False
        
        if args.integration and not runner.run_integration_tests(args.with_geant4):
            all_passed = False
        
        if args.patterns and not runner.run_pattern_tests(args.extended_patterns):
            all_passed = False
            
        if args.performance and not runner.run_performance_tests():
            all_passed = False
            
        if args.gui and not runner.run_gui_tests():
            all_passed = False
            
        if args.mocks and not runner.run_mock_geant4_tests():
            all_passed = False
            
        if args.physics and not runner.run_physics_validation():
            all_passed = False
    
    # Run code quality checks
    if args.quality and not runner.run_code_quality_checks():
        all_passed = False
    
    # Generate coverage report
    if args.coverage:
        runner.generate_coverage_report()
    
    # Print summary
    if not args.quiet:
        summary_passed = runner.print_summary()
        all_passed = all_passed and summary_passed
    
    # Save results
    if args.output:
        runner.save_results(Path(args.output))
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()