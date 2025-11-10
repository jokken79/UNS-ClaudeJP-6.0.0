#!/usr/bin/env python3
"""
Performance Benchmarks for UNS-CLAUDEJP 5.4 Photo Extraction System v2.0

This module provides comprehensive performance benchmarking to validate the
optimizations implemented in the system and compare with baseline metrics.

Usage:
    python performance_benchmarks.py [--config PATH] [--output PATH] [--verbose]
"""

import sys
import os
import json
import time
import psutil
import traceback
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics
import threading
import concurrent.futures
from contextlib import contextmanager

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config.photo_extraction_config import PhotoExtractionConfig, load_config
    from scripts.auto_extract_photos_from_databasejp_v2 import AdvancedPhotoExtractor
    from utils.logging_utils import create_logger
    from cache.photo_cache import create_cache_manager
    from performance.optimization import create_performance_optimizer
    from validation.photo_validator import create_photo_validator
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""
    test_name: str
    dataset_size: int
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    photos_extracted: int
    errors: int
    success_rate: float
    throughput: float  # records per second
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite"""
    
    def __init__(self, config: PhotoExtractionConfig, output_dir: Path = None):
        self.config = config
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self.logger = create_logger("PerformanceBenchmark", config)
        
        # Initialize components
        self.extractor = None
        self.cache_manager = None
        self.performance_optimizer = None
        
        # Benchmark results
        self.results: List[BenchmarkResult] = []
        self.system_metrics: List[SystemMetrics] = []
        
        # Monitoring
        self.monitoring_active = False
        self.monitor_thread = None
        
        self.logger.info("Performance benchmark initialized")
    
    def setup_components(self):
        """Setup system components for benchmarking"""
        try:
            self.extractor = AdvancedPhotoExtractor(self.config)
            self.cache_manager = create_cache_manager(self.config, self.logger)
            self.performance_optimizer = create_performance_optimizer(self.config, self.logger)
            
            self.logger.info("Components setup completed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup components: {e}")
            return False
    
    @contextmanager
    def resource_monitor(self):
        """Context manager for resource monitoring"""
        self.start_monitoring()
        try:
            yield
        finally:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """Start system resource monitoring"""
        self.monitoring_active = True
        self.system_metrics.clear()
        
        def monitor_loop():
            while self.monitoring_active:
                try:
                    # Get system metrics
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    memory = psutil.virtual_memory()
                    disk_io = psutil.disk_io_counters()
                    network_io = psutil.net_io_counters()
                    
                    metrics = SystemMetrics(
                        cpu_percent=cpu_percent,
                        memory_mb=memory.used / (1024 * 1024),
                        memory_percent=memory.percent,
                        disk_io_read_mb=disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
                        disk_io_write_mb=disk_io.write_bytes / (1024 * 1024) if disk_io else 0,
                        network_io_sent_mb=network_io.bytes_sent / (1024 * 1024) if network_io else 0,
                        network_io_recv_mb=network_io.bytes_recv / (1024 * 1024) if network_io else 0
                    )
                    
                    self.system_metrics.append(metrics)
                    time.sleep(0.5)  # Sample every 500ms
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(1.0)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop system resource monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Resource monitoring stopped")
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary of collected resource metrics"""
        if not self.system_metrics:
            return {}
        
        cpu_values = [m.cpu_percent for m in self.system_metrics]
        memory_values = [m.memory_mb for m in self.system_metrics]
        memory_percent_values = [m.memory_percent for m in self.system_metrics]
        
        return {
            'cpu': {
                'avg': statistics.mean(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values),
                'std': statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
            },
            'memory_mb': {
                'avg': statistics.mean(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'std': statistics.stdev(memory_values) if len(memory_values) > 1 else 0
            },
            'memory_percent': {
                'avg': statistics.mean(memory_percent_values),
                'max': max(memory_percent_values),
                'min': min(memory_percent_values),
                'std': statistics.stdev(memory_percent_values) if len(memory_percent_values) > 1 else 0
            },
            'samples_count': len(self.system_metrics)
        }
    
    def benchmark_extraction_performance(self, dataset_sizes: List[int]) -> List[BenchmarkResult]:
        """Benchmark extraction performance with different dataset sizes"""
        results = []
        
        for size in dataset_sizes:
            self.logger.info(f"Benchmarking extraction performance with {size:,} records")
            
            # Clear cache before each test
            if self.cache_manager:
                self.cache_manager.clear()
            
            with self.resource_monitor():
                start_time = time.time()
                
                try:
                    # Find database
                    db_path = self.extractor.find_database()
                    if not db_path:
                        raise Exception("Database not found")
                    
                    # Perform extraction (limit to specified size for testing)
                    original_chunk_size = self.config.processing.chunk_size
                    self.config.processing.chunk_size = min(size, 100)  # Adjust chunk size for test
                    
                    extraction_result = self.extractor.extract_photos_with_optimization(db_path)
                    
                    # Restore original chunk size
                    self.config.processing.chunk_size = original_chunk_size
                    
                    end_time = time.time()
                    
                    # Calculate metrics
                    execution_time = end_time - start_time
                    photos_extracted = extraction_result.get('photos_extracted', 0)
                    errors = extraction_result.get('errors', 0)
                    total_records = extraction_result.get('total_records', size)
                    success_rate = (photos_extracted / total_records * 100) if total_records > 0 else 0
                    throughput = total_records / execution_time if execution_time > 0 else 0
                    
                    # Get resource summary
                    resource_summary = self.get_resource_summary()
                    
                    result = BenchmarkResult(
                        test_name=f"extraction_performance_{size}",
                        dataset_size=size,
                        execution_time=execution_time,
                        memory_usage_mb=resource_summary.get('memory_mb', {}).get('avg', 0),
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        photos_extracted=photos_extracted,
                        errors=errors,
                        success_rate=success_rate,
                        throughput=throughput,
                        metadata={
                            'method_used': extraction_result.get('method_used', 'unknown'),
                            'resource_summary': resource_summary,
                            'chunk_size': self.config.processing.chunk_size
                        }
                    )
                    
                    results.append(result)
                    
                    self.logger.info(f"Extraction benchmark completed: {execution_time:.2f}s, "
                                   f"{throughput:.1f} records/sec, {photos_extracted} photos")
                    
                except Exception as e:
                    self.logger.error(f"Extraction benchmark failed: {e}")
                    traceback.print_exc()
                    
                    # Create failed result
                    end_time = time.time()
                    execution_time = end_time - start_time
                    resource_summary = self.get_resource_summary()
                    
                    result = BenchmarkResult(
                        test_name=f"extraction_performance_{size}",
                        dataset_size=size,
                        execution_time=execution_time,
                        memory_usage_mb=resource_summary.get('memory_mb', {}).get('avg', 0),
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        photos_extracted=0,
                        errors=1,
                        success_rate=0.0,
                        throughput=0.0,
                        metadata={
                            'error': str(e),
                            'resource_summary': resource_summary
                        }
                    )
                    
                    results.append(result)
        
        return results
    
    def benchmark_cache_performance(self) -> List[BenchmarkResult]:
        """Benchmark cache performance"""
        results = []
        
        if not self.cache_manager:
            self.logger.warning("Cache manager not available, skipping cache benchmarks")
            return results
        
        self.logger.info("Benchmarking cache performance")
        
        # Test cache hit rates
        test_data = {f"test_key_{i}": f"test_value_{i}" for i in range(1000)}
        
        with self.resource_monitor():
            start_time = time.time()
            
            # Cache set operations
            set_operations = 0
            for key, value in test_data.items():
                if self.cache_manager.set(key, value, ttl_seconds=3600):
                    set_operations += 1
            
            # Cache get operations (first pass - cache misses)
            get_operations = 0
            hit_operations = 0
            for key in test_data.keys():
                result = self.cache_manager.get(key)
                get_operations += 1
                if result:
                    hit_operations += 1
            
            # Cache get operations (second pass - cache hits)
            hit_operations_second = 0
            for key in test_data.keys():
                result = self.cache_manager.get(key)
                if result:
                    hit_operations_second += 1
            
            end_time = time.time()
            
            # Calculate metrics
            execution_time = end_time - start_time
            total_operations = set_operations + get_operations * 2
            hit_rate = (hit_operations_second / get_operations * 100) if get_operations > 0 else 0
            throughput = total_operations / execution_time if execution_time > 0 else 0
            
            resource_summary = self.get_resource_summary()
            
            result = BenchmarkResult(
                test_name="cache_performance",
                dataset_size=len(test_data),
                execution_time=execution_time,
                memory_usage_mb=resource_summary.get('memory_mb', {}).get('avg', 0),
                cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                photos_extracted=0,  # Not applicable for cache test
                errors=0,
                success_rate=100.0,
                throughput=throughput,
                metadata={
                    'set_operations': set_operations,
                    'get_operations': get_operations * 2,
                    'hit_rate': hit_rate,
                    'cache_stats': self.cache_manager.get_stats(),
                    'resource_summary': resource_summary
                }
            )
            
            results.append(result)
            
            self.logger.info(f"Cache benchmark completed: {execution_time:.2f}s, "
                           f"{throughput:.1f} ops/sec, hit rate: {hit_rate:.1f}%")
        
        return results
    
    def benchmark_parallel_processing(self, worker_counts: List[int]) -> List[BenchmarkResult]:
        """Benchmark parallel processing with different worker counts"""
        results = []
        
        for workers in worker_counts:
            self.logger.info(f"Benchmarking parallel processing with {workers} workers")
            
            # Save original config
            original_workers = self.config.processing.max_workers
            self.config.processing.max_workers = workers
            
            # Create test data
            test_data = list(range(1000))  # 1000 test items
            
            def cpu_intensive_task(item):
                """Simulate CPU-intensive photo processing"""
                total = 0
                for i in range(1000):  # Simulate processing work
                    total += item * i
                return f"processed_{item}_{total}"
            
            with self.resource_monitor():
                start_time = time.time()
                
                try:
                    # Process with parallel processor
                    if self.performance_optimizer:
                        processed_results = self.performance_optimizer.process_tasks(
                            test_data, cpu_intensive_task, "parallel_benchmark"
                        )
                    else:
                        # Fallback to sequential processing
                        processed_results = [cpu_intensive_task(item) for item in test_data]
                    
                    end_time = time.time()
                    
                    # Calculate metrics
                    execution_time = end_time - start_time
                    success_count = len([r for r in processed_results if r is not None])
                    success_rate = (success_count / len(test_data) * 100) if test_data else 0
                    throughput = len(test_data) / execution_time if execution_time > 0 else 0
                    
                    resource_summary = self.get_resource_summary()
                    
                    result = BenchmarkResult(
                        test_name=f"parallel_processing_{workers}_workers",
                        dataset_size=len(test_data),
                        execution_time=execution_time,
                        memory_usage_mb=resource_summary.get('memory_mb', {}).get('avg', 0),
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        photos_extracted=success_count,  # Using as processed items
                        errors=len(test_data) - success_count,
                        success_rate=success_rate,
                        throughput=throughput,
                        metadata={
                            'workers': workers,
                            'processed_items': success_count,
                            'resource_summary': resource_summary
                        }
                    )
                    
                    results.append(result)
                    
                    self.logger.info(f"Parallel processing benchmark completed: {execution_time:.2f}s, "
                                   f"{throughput:.1f} items/sec, {workers} workers")
                
                except Exception as e:
                    self.logger.error(f"Parallel processing benchmark failed: {e}")
                    traceback.print_exc()
            
            # Restore original config
            self.config.processing.max_workers = original_workers
        
        return results
    
    def benchmark_memory_usage(self, dataset_sizes: List[int]) -> List[BenchmarkResult]:
        """Benchmark memory usage with different dataset sizes"""
        results = []
        
        for size in dataset_sizes:
            self.logger.info(f"Benchmarking memory usage with {size:,} records")
            
            # Clear cache before test
            if self.cache_manager:
                self.cache_manager.clear()
            
            # Get initial memory
            process = psutil.Process()
            initial_memory = process.memory_info().rss / (1024 * 1024)
            
            with self.resource_monitor():
                start_time = time.time()
                
                try:
                    # Create large dataset in memory
                    large_dataset = []
                    for i in range(size):
                        # Simulate photo data
                        photo_data = {
                            'id': f"record_{i}",
                            'photo': f"data:image/jpeg;base64,{'x' * 1000}",  # Simulate base64 data
                            'metadata': {'size': 1000, 'format': 'JPEG'}
                        }
                        large_dataset.append(photo_data)
                        
                        # Check memory usage periodically
                        if i % 1000 == 0:
                            current_memory = process.memory_info().rss / (1024 * 1024)
                            memory_growth = current_memory - initial_memory
                            
                            # Stop if memory usage gets too high
                            if memory_growth > 2000:  # 2GB limit
                                self.logger.warning(f"Memory usage too high: {memory_growth:.1f}MB, stopping test")
                                break
                    
                    end_time = time.time()
                    
                    # Calculate metrics
                    execution_time = end_time - start_time
                    final_memory = process.memory_info().rss / (1024 * 1024)
                    memory_usage_mb = final_memory - initial_memory
                    memory_per_record = memory_usage_mb / len(large_dataset) if large_dataset else 0
                    
                    resource_summary = self.get_resource_summary()
                    
                    result = BenchmarkResult(
                        test_name=f"memory_usage_{size}",
                        dataset_size=len(large_dataset),
                        execution_time=execution_time,
                        memory_usage_mb=memory_usage_mb,
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        photos_extracted=len(large_dataset),  # Using as created records
                        errors=0,
                        success_rate=100.0,
                        throughput=len(large_dataset) / execution_time if execution_time > 0 else 0,
                        metadata={
                            'initial_memory_mb': initial_memory,
                            'final_memory_mb': final_memory,
                            'memory_per_record_mb': memory_per_record,
                            'resource_summary': resource_summary
                        }
                    )
                    
                    results.append(result)
                    
                    self.logger.info(f"Memory benchmark completed: {memory_usage_mb:.1f}MB used, "
                                   f"{memory_per_record:.2f}MB per record")
                    
                    # Cleanup
                    del large_dataset
                    
                except Exception as e:
                    self.logger.error(f"Memory benchmark failed: {e}")
                    traceback.print_exc()
        
        return results
    
    def run_all_benchmarks(self) -> Dict[str, List[BenchmarkResult]]:
        """Run all benchmark tests"""
        self.logger.info("Starting comprehensive performance benchmarks")
        
        if not self.setup_components():
            raise Exception("Failed to setup components for benchmarking")
        
        all_results = {}
        
        # Define test parameters
        dataset_sizes = [100, 500, 1000, 5000]  # Different dataset sizes
        worker_counts = [1, 2, 4, 8]  # Different worker counts
        
        try:
            # 1. Extraction Performance Benchmarks
            self.logger.info("Running extraction performance benchmarks...")
            extraction_results = self.benchmark_extraction_performance(dataset_sizes)
            all_results['extraction_performance'] = extraction_results
            
            # 2. Cache Performance Benchmarks
            self.logger.info("Running cache performance benchmarks...")
            cache_results = self.benchmark_cache_performance()
            all_results['cache_performance'] = cache_results
            
            # 3. Parallel Processing Benchmarks
            self.logger.info("Running parallel processing benchmarks...")
            parallel_results = self.benchmark_parallel_processing(worker_counts)
            all_results['parallel_processing'] = parallel_results
            
            # 4. Memory Usage Benchmarks
            self.logger.info("Running memory usage benchmarks...")
            memory_results = self.benchmark_memory_usage(dataset_sizes)
            all_results['memory_usage'] = memory_results
            
            self.logger.info("All benchmarks completed successfully")
            
        except Exception as e:
            self.logger.error(f"Benchmark suite failed: {e}")
            traceback.print_exc()
        
        return all_results
    
    def save_results(self, results: Dict[str, List[BenchmarkResult]], filename: str = None):
        """Save benchmark results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        output_file = self.output_dir / filename
        
        # Convert results to serializable format
        serializable_results = {}
        for category, benchmark_results in results.items():
            serializable_results[category] = [asdict(result) for result in benchmark_results]
        
        # Add metadata
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'python_version': sys.version,
                'platform': sys.platform
            },
            'config': self.config.to_dict(),
            'results': serializable_results,
            'summary': self.generate_summary(results)
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Benchmark results saved to: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            return False
    
    def generate_summary(self, results: Dict[str, List[BenchmarkResult]]) -> Dict[str, Any]:
        """Generate summary statistics from benchmark results"""
        summary = {
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'categories': {}
        }
        
        for category, benchmark_results in results.items():
            category_summary = {
                'test_count': len(benchmark_results),
                'avg_execution_time': 0,
                'avg_throughput': 0,
                'avg_success_rate': 0,
                'avg_memory_usage': 0,
                'best_throughput': 0,
                'worst_throughput': float('inf')
            }
            
            if benchmark_results:
                execution_times = [r.execution_time for r in benchmark_results]
                throughputs = [r.throughput for r in benchmark_results]
                success_rates = [r.success_rate for r in benchmark_results]
                memory_usages = [r.memory_usage_mb for r in benchmark_results]
                
                category_summary.update({
                    'avg_execution_time': statistics.mean(execution_times),
                    'avg_throughput': statistics.mean(throughputs),
                    'avg_success_rate': statistics.mean(success_rates),
                    'avg_memory_usage': statistics.mean(memory_usages),
                    'best_throughput': max(throughputs),
                    'worst_throughput': min(throughputs)
                })
                
                # Count successful vs failed tests
                successful = len([r for r in benchmark_results if r.success_rate > 0])
                summary['successful_tests'] += successful
                summary['failed_tests'] += len(benchmark_results) - successful
            
            summary['categories'][category] = category_summary
            summary['total_tests'] += len(benchmark_results)
        
        return summary


def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(
        description="Performance Benchmarks for UNS-CLAUDEJP 5.4 Photo Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                                    # Run all benchmarks with default config
    %(prog)s --config custom_config.json          # Use custom configuration
    %(prog)s --output results/                   # Save to specific directory
    %(prog)s --verbose                          # Verbose output
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
        default='benchmark_results',
        help='Output directory for results (default: benchmark_results)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_path = args.config
        config = load_config(config_path)
        
        if args.verbose:
            config.logging.level = config.logging.DEBUG
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("UNS-CLAUDEJP 5.4 - Performance Benchmarks")
        print("=" * 60)
        print(f"Output directory: {output_dir}")
        print(f"Configuration: {config_path or 'default'}")
        print()
        
        # Run benchmarks
        benchmark = PerformanceBenchmark(config, output_dir)
        results = benchmark.run_all_benchmarks()
        
        # Save results
        success = benchmark.save_results(results)
        
        if success:
            print("\nBenchmarks completed successfully!")
            print(f"Results saved to: {output_dir}")
            
            # Print summary
            summary = benchmark.generate_summary(results)
            print(f"\nSummary:")
            print(f"  Total tests: {summary['total_tests']}")
            print(f"  Successful: {summary['successful_tests']}")
            print(f"  Failed: {summary['failed_tests']}")
            
            for category, cat_summary in summary['categories'].items():
                print(f"\n{category.replace('_', ' ').title()}:")
                print(f"  Tests: {cat_summary['test_count']}")
                print(f"  Avg throughput: {cat_summary['avg_throughput']:.1f} ops/sec")
                print(f"  Best throughput: {cat_summary['best_throughput']:.1f} ops/sec")
                print(f"  Avg success rate: {cat_summary['avg_success_rate']:.1f}%")
            
            return 0
        else:
            print("ERROR: Failed to save benchmark results")
            return 1
    
    except KeyboardInterrupt:
        print("\nBenchmarks interrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)