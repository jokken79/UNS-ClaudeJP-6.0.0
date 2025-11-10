#!/usr/bin/env python3
"""
Baseline Performance Tests for UNS-CLAUDEJP 5.4 Photo Extraction System v2.0

This module executes baseline performance tests to establish performance
metrics for comparison with optimized system.

Usage:
    python run_baseline_tests.py [--config PATH] [--output PATH] [--iterations COUNT]
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
class BaselineTestResult:
    """Result of a baseline test"""
    test_name: str
    iterations: int
    execution_times: List[float]
    avg_execution_time: float
    min_execution_time: float
    max_execution_time: float
    std_deviation: float
    throughput: float  # records per second
    success_rate: float
    memory_usage_mb: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaselineTestRunner:
    """Runs baseline performance tests"""
    
    def __init__(self, config: PhotoExtractionConfig, output_dir: Path = None):
        self.config = config
        self.output_dir = output_dir or Path("baseline_test_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self.logger = create_logger("BaselineTestRunner", config)
        
        # Test results
        self.results: List[BaselineTestResult] = []
        
        self.logger.info("Baseline test runner initialized")
    
    def run_baseline_extraction_test(self, iterations: int = 5) -> BaselineTestResult:
        """Run baseline extraction performance test"""
        self.logger.info(f"Running baseline extraction test with {iterations} iterations")
        
        execution_times = []
        success_count = 0
        memory_usage = 0
        
        # Create temporary script for baseline test
        baseline_script = self._create_baseline_extraction_script()
        
        try:
            for i in range(iterations):
                self.logger.info(f"Running extraction test iteration {i+1}/{iterations}")
                
                start_time = time.time()
                
                # Run baseline extraction
                result = subprocess.run(
                    [sys.executable, str(baseline_script)],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per iteration
                )
                
                end_time = time.time()
                execution_time = end_time - start_time
                execution_times.append(execution_time)
                
                # Check result
                if result.returncode == 0:
                    success_count += 1
                    self.logger.info(f"Iteration {i+1} completed in {execution_time:.2f}s")
                else:
                    self.logger.error(f"Iteration {i+1} failed: {result.stderr}")
                
                # Small delay between iterations
                time.sleep(2)
        
        except Exception as e:
            self.logger.error(f"Baseline extraction test failed: {e}")
            traceback.print_exc()
        
        # Calculate metrics
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0
        min_execution_time = min(execution_times) if execution_times else 0
        max_execution_time = max(execution_times) if execution_times else 0
        std_deviation = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        success_rate = (success_count / iterations * 100) if iterations > 0 else 0
        throughput = 1000 / avg_execution_time if avg_execution_time > 0 else 0  # Assuming 1000 records
        
        result = BaselineTestResult(
            test_name="baseline_extraction",
            iterations=iterations,
            execution_times=execution_times,
            avg_execution_time=avg_execution_time,
            min_execution_time=min_execution_time,
            max_execution_time=max_execution_time,
            std_deviation=std_deviation,
            throughput=throughput,
            success_rate=success_rate,
            memory_usage_mb=memory_usage,
            metadata={
                'success_count': success_count,
                'failure_count': iterations - success_count
            }
        )
        
        self.logger.info(f"Baseline extraction test completed: avg={avg_execution_time:.2f}s, "
                       f"throughput={throughput:.1f} records/sec, success_rate={success_rate:.1f}%")
        
        return result
    
    def run_baseline_cache_test(self, iterations: int = 5) -> BaselineTestResult:
        """Run baseline cache performance test"""
        self.logger.info(f"Running baseline cache test with {iterations} iterations")
        
        execution_times = []
        success_count = 0
        memory_usage = 0
        
        # Create temporary script for baseline cache test
        baseline_script = self._create_baseline_cache_script()
        
        try:
            for i in range(iterations):
                self.logger.info(f"Running cache test iteration {i+1}/{iterations}")
                
                start_time = time.time()
                
                # Run baseline cache test
                result = subprocess.run(
                    [sys.executable, str(baseline_script)],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout per iteration
                )
                
                end_time = time.time()
                execution_time = end_time - start_time
                execution_times.append(execution_time)
                
                # Check result
                if result.returncode == 0:
                    success_count += 1
                    self.logger.info(f"Iteration {i+1} completed in {execution_time:.2f}s")
                else:
                    self.logger.error(f"Iteration {i+1} failed: {result.stderr}")
                
                # Small delay between iterations
                time.sleep(1)
        
        except Exception as e:
            self.logger.error(f"Baseline cache test failed: {e}")
            traceback.print_exc()
        
        # Calculate metrics
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0
        min_execution_time = min(execution_times) if execution_times else 0
        max_execution_time = max(execution_times) if execution_times else 0
        std_deviation = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        success_rate = (success_count / iterations * 100) if iterations > 0 else 0
        throughput = 10000 / avg_execution_time if avg_execution_time > 0 else 0  # Assuming 10000 operations
        
        result = BaselineTestResult(
            test_name="baseline_cache",
            iterations=iterations,
            execution_times=execution_times,
            avg_execution_time=avg_execution_time,
            min_execution_time=min_execution_time,
            max_execution_time=max_execution_time,
            std_deviation=std_deviation,
            throughput=throughput,
            success_rate=success_rate,
            memory_usage_mb=memory_usage,
            metadata={
                'success_count': success_count,
                'failure_count': iterations - success_count
            }
        )
        
        self.logger.info(f"Baseline cache test completed: avg={avg_execution_time:.2f}s, "
                       f"throughput={throughput:.1f} ops/sec, success_rate={success_rate:.1f}%")
        
        return result
    
    def run_baseline_parallel_test(self, iterations: int = 5) -> BaselineTestResult:
        """Run baseline parallel processing test"""
        self.logger.info(f"Running baseline parallel test with {iterations} iterations")
        
        execution_times = []
        success_count = 0
        memory_usage = 0
        
        # Create temporary script for baseline parallel test
        baseline_script = self._create_baseline_parallel_script()
        
        try:
            for i in range(iterations):
                self.logger.info(f"Running parallel test iteration {i+1}/{iterations}")
                
                start_time = time.time()
                
                # Run baseline parallel test
                result = subprocess.run(
                    [sys.executable, str(baseline_script)],
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minute timeout per iteration
                )
                
                end_time = time.time()
                execution_time = end_time - start_time
                execution_times.append(execution_time)
                
                # Check result
                if result.returncode == 0:
                    success_count += 1
                    self.logger.info(f"Iteration {i+1} completed in {execution_time:.2f}s")
                else:
                    self.logger.error(f"Iteration {i+1} failed: {result.stderr}")
                
                # Small delay between iterations
                time.sleep(2)
        
        except Exception as e:
            self.logger.error(f"Baseline parallel test failed: {e}")
            traceback.print_exc()
        
        # Calculate metrics
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0
        min_execution_time = min(execution_times) if execution_times else 0
        max_execution_time = max(execution_times) if execution_times else 0
        std_deviation = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        success_rate = (success_count / iterations * 100) if iterations > 0 else 0
        throughput = 1000 / avg_execution_time if avg_execution_time > 0 else 0  # Assuming 1000 records
        
        result = BaselineTestResult(
            test_name="baseline_parallel",
            iterations=iterations,
            execution_times=execution_times,
            avg_execution_time=avg_execution_time,
            min_execution_time=min_execution_time,
            max_execution_time=max_execution_time,
            std_deviation=std_deviation,
            throughput=throughput,
            success_rate=success_rate,
            memory_usage_mb=memory_usage,
            metadata={
                'success_count': success_count,
                'failure_count': iterations - success_count
            }
        )
        
        self.logger.info(f"Baseline parallel test completed: avg={avg_execution_time:.2f}s, "
                       f"throughput={throughput:.1f} records/sec, success_rate={success_rate:.1f}%")
        
        return result
    
    def _create_baseline_extraction_script(self) -> Path:
        """Create temporary script for baseline extraction test"""
        script_content = f"""
import sys
import time
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config.photo_extraction_config import load_config
    from scripts.auto_extract_photos_from_databasejp_v2 import AdvancedPhotoExtractor
    from utils.logging_utils import create_logger
    
    # Load configuration
    config = load_config()
    logger = create_logger("BaselineExtraction", config)
    
    # Initialize extractor
    extractor = AdvancedPhotoExtractor(config)
    
    # Find database
    db_path = extractor.find_database()
    if not db_path:
        print("ERROR: Database not found")
        sys.exit(1)
    
    # Perform extraction with minimal dataset (100 records)
    original_chunk_size = config.processing.chunk_size
    config.processing.chunk_size = min(100, original_chunk_size)
    
    # Run extraction
    result = extractor.extract_photos_with_optimization(db_path)
    
    # Restore original chunk size
    config.processing.chunk_size = original_chunk_size
    
    if result['success']:
        print(f"SUCCESS: Extracted {{result['photos_extracted']}} photos in {{result['execution_time']:.2f}}s")
        sys.exit(0)
    else:
        print(f"ERROR: {{result.get('error', 'Unknown error')}}")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
"""
        
        script_path = self.output_dir / "baseline_extraction_test.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return script_path
    
    def _create_baseline_cache_script(self) -> Path:
        """Create temporary script for baseline cache test"""
        script_content = f"""
import sys
import time
import random
import string
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config.photo_extraction_config import load_config
    from cache.photo_cache import create_cache_manager
    from utils.logging_utils import create_logger
    
    # Load configuration
    config = load_config()
    logger = create_logger("BaselineCache", config)
    
    # Initialize cache manager
    cache_manager = create_cache_manager(config, logger)
    
    # Test cache performance with 10000 operations
    operations = 10000
    set_operations = operations // 2
    get_operations = operations // 2
    
    # Cache set operations
    start_time = time.time()
    for i in range(set_operations):
        key = f"baseline_test_{{i:06d}}"
        value = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
        cache_manager.set(key, value, ttl_seconds=3600)
    set_time = time.time() - start_time
    
    # Cache get operations
    start_time = time.time()
    hits = 0
    for i in range(get_operations):
        key = f"baseline_test_{{i:06d}}"
        result = cache_manager.get(key)
        if result:
            hits += 1
    get_time = time.time() - start_time
    
    total_time = set_time + get_time
    throughput = operations / total_time if total_time > 0 else 0
    hit_rate = (hits / get_operations * 100) if get_operations > 0 else 0
    
    print(f"SUCCESS: Cache test completed in {{total_time:.2f}}s, "
          f"throughput={{throughput:.1f}} ops/sec, hit_rate={{hit_rate:.1f}}%")
    sys.exit(0)
        
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
"""
        
        script_path = self.output_dir / "baseline_cache_test.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return script_path
    
    def _create_baseline_parallel_script(self) -> Path:
        """Create temporary script for baseline parallel test"""
        script_content = f"""
import sys
import time
import random
import threading
import concurrent.futures
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config.photo_extraction_config import load_config
    from performance.optimization import create_performance_optimizer
    from utils.logging_utils import create_logger
    
    # Load configuration
    config = load_config()
    logger = create_logger("BaselineParallel", config)
    
    # Initialize performance optimizer
    perf_optimizer = create_performance_optimizer(config, logger)
    
    # Test parallel processing with 1000 tasks
    tasks = 1000
    
    def cpu_intensive_task(item):
        # Simulate CPU-intensive work
        total = 0
        for i in range(100):
            total += item * i
        return total
    
    # Process tasks in parallel
    start_time = time.time()
    results = perf_optimizer.process_tasks(list(range(tasks)), cpu_intensive_task, "baseline_test")
    end_time = time.time()
    
    execution_time = end_time - start_time
    throughput = tasks / execution_time if execution_time > 0 else 0
    success_count = sum(1 for r in results if r is not None)
    success_rate = (success_count / tasks * 100) if tasks > 0 else 0
    
    print(f"SUCCESS: Parallel test completed in {{execution_time:.2f}}s, "
          f"throughput={{throughput:.1f}} tasks/sec, success_rate={{success_rate:.1f}}%")
    sys.exit(0)
        
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
"""
        
        script_path = self.output_dir / "baseline_parallel_test.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return script_path
    
    def run_all_baseline_tests(self, iterations: int = 5) -> List[BaselineTestResult]:
        """Run all baseline tests"""
        self.logger.info("Starting baseline performance tests")
        
        all_results = []
        
        try:
            # 1. Baseline Extraction Test
            extraction_result = self.run_baseline_extraction_test(iterations)
            all_results.append(extraction_result)
            
            # 2. Baseline Cache Test
            cache_result = self.run_baseline_cache_test(iterations)
            all_results.append(cache_result)
            
            # 3. Baseline Parallel Test
            parallel_result = self.run_baseline_parallel_test(iterations)
            all_results.append(parallel_result)
            
            self.logger.info("All baseline tests completed successfully")
        
        except Exception as e:
            self.logger.error(f"Baseline test suite failed: {e}")
            traceback.print_exc()
        
        return all_results
    
    def save_results(self, results: List[BaselineTestResult], filename: str = None) -> bool:
        """Save baseline test results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"baseline_test_results_{timestamp}.json"
        
        output_file = self.output_dir / filename
        
        # Convert results to serializable format
        serializable_results = [asdict(result) for result in results]
        
        # Add metadata
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config.to_dict(),
            'results': serializable_results,
            'summary': self.generate_summary(results)
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Baseline test results saved to: {output_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            return False
    
    def generate_summary(self, results: List[BaselineTestResult]) -> Dict[str, Any]:
        """Generate summary statistics from baseline test results"""
        if not results:
            return {}
        
        # Calculate overall metrics
        total_iterations = sum(r.iterations for r in results)
        avg_execution_time = statistics.mean([r.avg_execution_time for r in results])
        avg_throughput = statistics.mean([r.throughput for r in results])
        avg_success_rate = statistics.mean([r.success_rate for r in results])
        
        # Test-specific summaries
        test_summaries = {}
        for result in results:
            test_summaries[result.test_name] = {
                'iterations': result.iterations,
                'avg_execution_time': result.avg_execution_time,
                'min_execution_time': result.min_execution_time,
                'max_execution_time': result.max_execution_time,
                'std_deviation': result.std_deviation,
                'throughput': result.throughput,
                'success_rate': result.success_rate,
                'memory_usage_mb': result.memory_usage_mb
            }
        
        return {
            'total_iterations': total_iterations,
            'avg_execution_time': avg_execution_time,
            'avg_throughput': avg_throughput,
            'avg_success_rate': avg_success_rate,
            'test_summaries': test_summaries
        }


def main():
    """Main baseline test execution"""
    parser = argparse.ArgumentParser(
        description="Baseline Performance Tests for UNS-CLAUDEJP 5.4 Photo Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                                    # Run baseline tests with default iterations
    %(prog)s --config custom_config.json          # Use custom configuration
    %(prog)s --output results/                   # Save to specific directory
    %(prog)s --iterations 10                       # Run 10 iterations per test
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
        default='baseline_test_results',
        help='Output directory for results (default: baseline_test_results)'
    )
    
    parser.add_argument(
        '--iterations',
        type=int,
        default=5,
        help='Number of iterations per test (default: 5)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_path = args.config
        config = load_config(config_path)
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("UNS-CLAUDEJP 5.4 - Baseline Performance Tests")
        print("=" * 60)
        print(f"Output directory: {output_dir}")
        print(f"Iterations per test: {args.iterations}")
        print(f"Configuration: {config_path or 'default'}")
        print()
        
        # Run baseline tests
        runner = BaselineTestRunner(config, output_dir)
        results = runner.run_all_baseline_tests(args.iterations)
        
        # Save results
        success = runner.save_results(results)
        
        if success:
            print("\nBaseline tests completed successfully!")
            print(f"Results saved to: {output_dir}")
            
            # Print summary
            summary = runner.generate_summary(results)
            print(f"\nSummary:")
            print(f"  Total iterations: {summary['total_iterations']}")
            print(f"  Average execution time: {summary['avg_execution_time']:.2f}s")
            print(f"  Average throughput: {summary['avg_throughput']:.1f} ops/sec")
            print(f"  Average success rate: {summary['avg_success_rate']:.1f}%")
            
            print(f"\nTest Results:")
            for test_name, test_summary in summary['test_summaries'].items():
                print(f"  {test_name.replace('_', ' ').title()}:")
                print(f"    Avg execution time: {test_summary['avg_execution_time']:.2f}s")
                print(f"    Throughput: {test_summary['throughput']:.1f} ops/sec")
                print(f"    Success rate: {test_summary['success_rate']:.1f}%")
                print(f"    Std deviation: {test_summary['std_deviation']:.2f}s")
            
            return 0
        else:
            print("ERROR: Failed to save baseline test results")
            return 1
    
    except KeyboardInterrupt:
        print("\nBaseline tests interrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
