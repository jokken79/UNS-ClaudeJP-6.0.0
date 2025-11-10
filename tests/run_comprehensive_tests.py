#!/usr/bin/env python3
"""
Comprehensive Test Suite for UNS-CLAUDEJP 5.4 Photo Extraction System v2.0

This module orchestrates all testing suites including performance benchmarks,
scalability tests, load tests, data quality validation, and component validation.

Usage:
    python run_comprehensive_tests.py [--config PATH] [--output PATH] [--test-suite SUITE]
"""

import sys
import os
import json
import time
import argparse
import traceback
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config.photo_extraction_config import PhotoExtractionConfig, load_config
    from utils.logging_utils import create_logger
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


@dataclass
class TestSuiteResult:
    """Result of a test suite execution"""
    suite_name: str
    success: bool
    execution_time: float
    results_file: str
    summary: Dict[str, Any] = None
    error_message: str = ""
    
    def __post_init__(self):
        if self.summary is None:
            self.summary = {}


@dataclass
class ComprehensiveTestReport:
    """Comprehensive test report"""
    timestamp: datetime
    total_execution_time: float
    test_suites: List[TestSuiteResult]
    overall_success: bool
    system_info: Dict[str, Any] = None
    config_summary: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.system_info is None:
            self.system_info = {}
        if self.config_summary is None:
            self.config_summary = {}


class ComprehensiveTestRunner:
    """Orchestrates comprehensive testing of the photo extraction system"""
    
    def __init__(self, config: PhotoExtractionConfig, output_dir: Path = None):
        self.config = config
        self.output_dir = output_dir or Path("comprehensive_test_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self.logger = create_logger("ComprehensiveTestRunner", config)
        
        # Test suite results
        self.test_results: List[TestSuiteResult] = []
        
        self.logger.info("Comprehensive test runner initialized")
    
    def run_test_suite(self, suite_name: str, script_path: str, 
                       args: List[str] = None) -> TestSuiteResult:
        """Run a specific test suite"""
        self.logger.info(f"Running test suite: {suite_name}")
        
        start_time = time.time()
        
        try:
            # Prepare command
            cmd = [sys.executable, str(script_path)]
            
            # Add config argument if not specified
            if args and '--config' not in ' '.join(args):
                cmd.extend(['--config', str(Path(__file__).parent.parent / 'backend' / 'config' / 'photo_extraction_config.json')])
            
            # Add output directory
            cmd.extend(['--output', str(self.output_dir / suite_name.lower().replace(' ', '_'))])
            
            # Add additional arguments
            if args:
                cmd.extend(args)
            
            self.logger.info(f"Executing: {' '.join(cmd)}")
            
            # Run test suite
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Check result
            success = result.returncode == 0
            
            # Find results file
            results_file = None
            if success:
                # Look for results file in output directory
                suite_output_dir = self.output_dir / suite_name.lower().replace(' ', '_')
                if suite_output_dir.exists():
                    for file in suite_output_dir.glob("*.json"):
                        results_file = str(file)
                        break
            
            # Parse summary from results file
            summary = {}
            if results_file and Path(results_file).exists():
                try:
                    with open(results_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if 'summary' in data:
                        summary = data['summary']
                    elif 'validation_summary' in data:
                        summary = data['validation_summary']
                
                except Exception as e:
                    self.logger.error(f"Failed to parse summary from {results_file}: {e}")
            
            test_result = TestSuiteResult(
                suite_name=suite_name,
                success=success,
                execution_time=execution_time,
                results_file=results_file or "",
                summary=summary,
                error_message=result.stderr if not success else ""
            )
            
            if success:
                self.logger.info(f"Test suite '{suite_name}' completed successfully in {execution_time:.2f}s")
            else:
                self.logger.error(f"Test suite '{suite_name}' failed in {execution_time:.2f}s: {result.stderr}")
            
            return test_result
        
        except subprocess.TimeoutExpired:
            end_time = time.time()
            execution_time = end_time - start_time
            
            test_result = TestSuiteResult(
                suite_name=suite_name,
                success=False,
                execution_time=execution_time,
                results_file="",
                error_message="Test suite timed out after 1 hour"
            )
            
            self.logger.error(f"Test suite '{suite_name}' timed out after 1 hour")
            return test_result
        
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            test_result = TestSuiteResult(
                suite_name=suite_name,
                success=False,
                execution_time=execution_time,
                results_file="",
                error_message=str(e)
            )
            
            self.logger.error(f"Test suite '{suite_name}' failed with exception: {e}")
            return test_result
    
    def run_all_test_suites(self, suite_filter: str = None) -> List[TestSuiteResult]:
        """Run all test suites"""
        self.logger.info("Starting comprehensive test suite execution")
        
        # Define test suites
        test_suites = [
            {
                'name': 'Performance Benchmarks',
                'script': 'performance_benchmarks.py',
                'args': []
            },
            {
                'name': 'Scalability Tests',
                'script': 'scalability_tests.py',
                'args': []
            },
            {
                'name': 'Load Tests',
                'script': 'load_tests.py',
                'args': []
            },
            {
                'name': 'Data Quality Validation',
                'script': 'data_quality_validation.py',
                'args': []
            },
            {
                'name': 'Component Validation',
                'script': 'component_validation.py',
                'args': []
            }
        ]
        
        # Filter test suites if specified
        if suite_filter:
            test_suites = [s for s in test_suites if suite_filter.lower() in s['name'].lower()]
            self.logger.info(f"Filtered to test suite: {suite_filter}")
        
        # Run each test suite
        all_results = []
        tests_dir = Path(__file__).parent
        
        for suite in test_suites:
            script_path = tests_dir / suite['script']
            
            if not script_path.exists():
                self.logger.error(f"Test script not found: {script_path}")
                continue
            
            result = self.run_test_suite(suite['name'], script_path, suite['args'])
            all_results.append(result)
        
        self.logger.info("All test suites execution completed")
        return all_results
    
    def generate_comprehensive_report(self, results: List[TestSuiteResult]) -> ComprehensiveTestReport:
        """Generate comprehensive test report"""
        self.logger.info("Generating comprehensive test report")
        
        # Calculate overall metrics
        total_suites = len(results)
        successful_suites = sum(1 for r in results if r.success)
        overall_success = successful_suites == total_suites
        total_execution_time = sum(r.execution_time for r in results)
        
        # Get system information
        try:
            import platform
            import psutil
            
            system_info = {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'disk_free_gb': psutil.disk_usage('.').free / (1024**3)
            }
        except Exception as e:
            system_info = {'error': str(e)}
        
        # Get configuration summary
        config_summary = {
            'extraction_method': self.config.extraction_method.value,
            'chunk_size': self.config.processing.chunk_size,
            'max_workers': self.config.processing.max_workers,
            'cache_enabled': self.config.cache.enable_cache,
            'cache_backend': self.config.cache.cache_backend,
            'validation_enabled': self.config.validation.enable_validation
        }
        
        # Create report
        report = ComprehensiveTestReport(
            timestamp=datetime.now(),
            total_execution_time=total_execution_time,
            test_suites=results,
            overall_success=overall_success,
            system_info=system_info,
            config_summary=config_summary
        )
        
        self.logger.info("Comprehensive test report generated")
        return report
    
    def save_report(self, report: ComprehensiveTestReport, filename: str = None) -> bool:
        """Save comprehensive test report to file"""
        if filename is None:
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_test_report_{timestamp}.json"
        
        output_file = self.output_dir / filename
        
        try:
            # Convert report to serializable format
            serializable_report = asdict(report)
            
            # Convert test suite results to serializable format
            serializable_report['test_suites'] = [asdict(result) for result in report.test_suites]
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Comprehensive test report saved to: {output_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
            return False
    
    def generate_html_report(self, report: ComprehensiveTestReport, filename: str = None) -> bool:
        """Generate HTML report for better visualization"""
        if filename is None:
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_test_report_{timestamp}.html"
        
        output_file = self.output_dir / filename
        
        try:
            # Generate HTML content
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UNS-CLAUDEJP 5.4 - Comprehensive Test Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
            margin-bottom: 30px;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h1 {{
            font-size: 2.5em;
            text-align: center;
        }}
        h2 {{
            font-size: 1.8em;
            margin-top: 30px;
        }}
        h3 {{
            font-size: 1.4em;
            margin-top: 25px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-item {{
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            border-radius: 4px;
        }}
        .summary-item h3 {{
            margin-top: 0;
            color: #2c3e50;
            border-bottom: none;
            padding-bottom: 5px;
        }}
        .test-suite {{
            margin-bottom: 30px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }}
        .test-suite-header {{
            background-color: #3498db;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .test-suite-header h2 {{
            margin: 0;
            border: none;
            padding: 0;
        }}
        .status-success {{
            background-color: #2ecc71;
        }}
        .status-failure {{
            background-color: #e74c3c;
        }}
        .test-suite-content {{
            padding: 20px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}
        .metric {{
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-label {{
            font-size: 0.9em;
            color: #7f8c8d;
        }}
        .error-message {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-family: monospace;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>UNS-CLAUDEJP 5.4 - Comprehensive Test Report</h1>
        <p style="text-align: center; font-size: 1.2em; color: #7f8c8d;">
            Generated on {report.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
        </p>
        
        <div class="summary">
            <div class="summary-item">
                <h3>Overall Status</h3>
                <div class="metric-value {'status-success' if report.overall_success else 'status-failure'}" style="padding: 10px; border-radius: 4px; color: white;">
                    {'PASSED' if report.overall_success else 'FAILED'}
                </div>
                <div class="metric-label">
                    {sum(1 for r in report.test_suites if r.success)}/{len(report.test_suites)} test suites passed
                </div>
            </div>
            
            <div class="summary-item">
                <h3>Total Execution Time</h3>
                <div class="metric-value">{report.total_execution_time:.2f}s</div>
                <div class="metric-label">
                    ({report.total_execution_time/60:.1f} minutes)
                </div>
            </div>
            
            <div class="summary-item">
                <h3>System Information</h3>
                <div class="metric-label">
                    Platform: {report.system_info.get('platform', 'Unknown')}<br>
                    Python: {report.system_info.get('python_version', 'Unknown')}<br>
                    CPU Cores: {report.system_info.get('cpu_count', 'Unknown')}<br>
                    Memory: {report.system_info.get('memory_total_gb', 0):.1f}GB
                </div>
            </div>
            
            <div class="summary-item">
                <h3>Configuration</h3>
                <div class="metric-label">
                    Extraction Method: {report.config_summary.get('extraction_method', 'Unknown')}<br>
                    Chunk Size: {report.config_summary.get('chunk_size', 0)}<br>
                    Max Workers: {report.config_summary.get('max_workers', 0)}<br>
                    Cache: {report.config_summary.get('cache_enabled', False)} ({report.config_summary.get('cache_backend', 'Unknown')})
                </div>
            </div>
        </div>
        
        <h2>Test Suite Results</h2>
"""
            
            # Add test suite results
            for suite_result in report.test_suites:
                status_class = "status-success" if suite_result.success else "status-failure"
                status_text = "PASSED" if suite_result.success else "FAILED"
                
                html_content += f"""
        <div class="test-suite">
            <div class="test-suite-header {status_class}">
                <h2>{suite_result.suite_name}</h2>
                <div style="font-size: 1.2em; font-weight: bold;">{status_text}</div>
            </div>
            <div class="test-suite-content">
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">{suite_result.execution_time:.2f}s</div>
                        <div class="metric-label">Execution Time</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{suite_result.results_file or 'N/A'}</div>
                        <div class="metric-label">Results File</div>
                    </div>
                </div>
"""
                
                # Add summary if available
                if suite_result.summary:
                    html_content += "<h3>Summary</h3>"
                    
                    if 'total_tests' in suite_result.summary:
                        html_content += f"""
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">{suite_result.summary['total_tests']}</div>
                            <div class="metric-label">Total Tests</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{suite_result.summary.get('overall_success_rate', 0):.1f}%</div>
                            <div class="metric-label">Success Rate</div>
                        </div>
                    </div>
"""
                    
                    if 'categories' in suite_result.summary:
                        html_content += "<table>"
                        html_content += "<tr><th>Category</th><th>Tests</th><th>Success Rate</th><th>Avg Performance</th></tr>"
                        
                        for category, cat_summary in suite_result.summary['categories'].items():
                            success_rate = cat_summary.get('avg_success_rate', 0)
                            performance = cat_summary.get('avg_throughput', 0)
                            
                            html_content += f"""
                        <tr>
                            <td>{category.replace('_', ' ').title()}</td>
                            <td>{cat_summary.get('test_count', 0)}</td>
                            <td>{success_rate:.1f}%</td>
                            <td>{performance:.1f} ops/sec</td>
                        </tr>
"""
                        
                        html_content += "</table>"
                
                # Add error message if available
                if suite_result.error_message:
                    html_content += f"""
                <div class="error-message">
                    <strong>Error:</strong> {suite_result.error_message}
                </div>
"""
                
                html_content += """
            </div>
        </div>
"""
            
            html_content += f"""
    </div>
    
    <div class="footer">
        <p>UNS-CLAUDEJP 5.4 Photo Extraction System v2.0 - Comprehensive Test Report</p>
        <p>Generated on {report.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
</body>
</html>
"""
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"HTML report saved to: {output_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            return False
    
    def run_comprehensive_tests(self, suite_filter: str = None) -> bool:
        """Run comprehensive test suite"""
        self.logger.info("Starting comprehensive test execution")
        
        try:
            # Run all test suites
            results = self.run_all_test_suites(suite_filter)
            
            # Generate report
            report = self.generate_comprehensive_report(results)
            
            # Save JSON report
            json_success = self.save_report(report)
            
            # Save HTML report
            html_success = self.generate_html_report(report)
            
            # Print summary
            self.print_summary(report)
            
            return json_success and html_success
        
        except Exception as e:
            self.logger.error(f"Comprehensive test execution failed: {e}")
            traceback.print_exc()
            return False
    
    def print_summary(self, report: ComprehensiveTestReport):
        """Print test summary to console"""
        print("\n" + "=" * 80)
        print("UNS-CLAUDEJP 5.4 - COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        print(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Overall Status: {'PASSED' if report.overall_success else 'FAILED'}")
        print(f"Total Execution Time: {report.total_execution_time:.2f}s ({report.total_execution_time/60:.1f} minutes)")
        print(f"Test Suites: {sum(1 for r in report.test_suites if r.success)}/{len(report.test_suites)} passed")
        
        print("\nTest Suite Results:")
        for suite_result in report.test_suites:
            status = "PASSED" if suite_result.success else "FAILED"
            print(f"  {suite_result.suite_name}: {status} ({suite_result.execution_time:.2f}s)")
        
        print("\n" + "=" * 80)


def main():
    """Main comprehensive test execution"""
    parser = argparse.ArgumentParser(
        description="Comprehensive Test Suite for UNS-CLAUDEJP 5.4 Photo Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                                    # Run all test suites
    %(prog)s --test-suite "Performance"    # Run specific test suite
    %(prog)s --config custom_config.json     # Use custom configuration
    %(prog)s --output results/              # Save to specific directory
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='comprehensive_test_results',
        help='Output directory for results (default: comprehensive_test_results)'
    )
    
    parser.add_argument(
        '--test-suite',
        type=str,
        help='Specific test suite to run (Performance, Scalability, Load, Data Quality, Component)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_path = args.config
        config = load_config(config_path)
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("UNS-CLAUDEJP 5.4 - Comprehensive Test Suite")
        print("=" * 80)
        print(f"Output directory: {output_dir}")
        print(f"Test suite filter: {args.test_suite or 'All suites'}")
        print(f"Configuration: {config_path or 'default'}")
        print()
        
        # Run comprehensive tests
        runner = ComprehensiveTestRunner(config, output_dir)
        success = runner.run_comprehensive_tests(args.test_suite)
        
        if success:
            print("\nComprehensive test suite completed successfully!")
            return 0
        else:
            print("\nERROR: Comprehensive test suite failed!")
            return 1
    
    except KeyboardInterrupt:
        print("\nComprehensive test suite interrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)