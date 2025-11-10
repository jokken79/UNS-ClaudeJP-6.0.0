#!/usr/bin/env python3
"""
Scalability Tests for UNS-CLAUDEJP 5.4 Photo Extraction System v2.0

This module provides comprehensive scalability testing to validate system behavior
under increasing load and dataset sizes.

Usage:
    python scalability_tests.py [--config PATH] [--output PATH] [--max-size SIZE]
"""

import sys
import os
import json
import time
import psutil
import traceback
import argparse
import threading
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
import statistics
import gc
import random
import string

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config.photo_extraction_config import PhotoExtractionConfig, load_config
    from scripts.auto_extract_photos_from_databasejp_v2 import AdvancedPhotoExtractor
    from utils.logging_utils import create_logger
    from cache.photo_cache import create_cache_manager
    from performance.optimization import create_performance_optimizer
    from processors.chunk_processor import create_chunk_processor
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


@dataclass
class ScalabilityTestResult:
    """Result of a scalability test"""
    test_name: str
    dataset_size: int
    execution_time: float
    memory_usage_mb: float
    memory_peak_mb: float
    cpu_usage_percent: float
    throughput: float  # records per second
    success_rate: float
    errors: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LoadTestResult:
    """Result of a load test"""
    test_name: str
    concurrent_users: int
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    requests_per_second: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ScalabilityTestSuite:
    """Comprehensive scalability testing suite"""
    
    def __init__(self, config: PhotoExtractionConfig, output_dir: Path = None):
        self.config = config
        self.output_dir = output_dir or Path("scalability_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self.logger = create_logger("ScalabilityTest", config)
        
        # Initialize components
        self.extractor = None
        self.cache_manager = None
        self.performance_optimizer = None
        self.chunk_processor = None
        
        # Test results
        self.results: List[ScalabilityTestResult] = []
        self.load_test_results: List[LoadTestResult] = []
        
        # Monitoring
        self.monitoring_active = False
        self.monitor_thread = None
        self.system_metrics = []
        
        self.logger.info("Scalability test suite initialized")
    
    def setup_components(self):
        """Setup system components for testing"""
        try:
            self.extractor = AdvancedPhotoExtractor(self.config)
            self.cache_manager = create_cache_manager(self.config, self.logger)
            self.performance_optimizer = create_performance_optimizer(self.config, self.logger)
            self.chunk_processor = create_chunk_processor(self.config)
            
            self.logger.info("Components setup completed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup components: {e}")
            return False
    
    def start_monitoring(self):
        """Start system resource monitoring"""
        self.monitoring_active = True
        self.system_metrics.clear()
        
        def monitor_loop():
            process = psutil.Process()
            while self.monitoring_active:
                try:
                    # Get system metrics
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    memory = psutil.virtual_memory()
                    process_memory = process.memory_info()
                    
                    metrics = {
                        'timestamp': datetime.now(),
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory.used / (1024 * 1024),
                        'memory_percent': memory.percent,
                        'process_memory_mb': process_memory.rss / (1024 * 1024),
                        'process_memory_peak_mb': process_memory.rss / (1024 * 1024)
                    }
                    
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
        
        cpu_values = [m['cpu_percent'] for m in self.system_metrics]
        memory_values = [m['memory_mb'] for m in self.system_metrics]
        process_memory_values = [m['process_memory_mb'] for m in self.system_metrics]
        process_memory_peak = max(m['process_memory_peak_mb'] for m in self.system_metrics)
        
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
            'process_memory_mb': {
                'avg': statistics.mean(process_memory_values),
                'max': max(process_memory_values),
                'min': min(process_memory_values),
                'peak': process_memory_peak
            },
            'samples_count': len(self.system_metrics)
        }
    
    def generate_test_dataset(self, size: int) -> List[Dict[str, Any]]:
        """Generate synthetic test dataset of specified size"""
        self.logger.info(f"Generating test dataset with {size:,} records")
        
        dataset = []
        for i in range(size):
            # Generate random photo data
            photo_size = random.randint(1000, 10000)  # 1KB to 10KB
            photo_data = ''.join(random.choices(string.ascii_letters + string.digits, k=photo_size))
            
            record = {
                'id': f"test_record_{i:06d}",
                'name': f"Test Employee {i}",
                'photo_data': f"data:image/jpeg;base64,{photo_data}",
                'metadata': {
                    'size': photo_size,
                    'format': 'JPEG',
                    'created_at': datetime.now().isoformat()
                }
            }
            dataset.append(record)
        
        self.logger.info(f"Generated {len(dataset):,} test records")
        return dataset
    
    def test_dataset_scalability(self, sizes: List[int]) -> List[ScalabilityTestResult]:
        """Test system scalability with different dataset sizes"""
        results = []
        
        for size in sizes:
            self.logger.info(f"Testing dataset scalability with {size:,} records")
            
            # Clear cache before each test
            if self.cache_manager:
                self.cache_manager.clear()
            
            # Force garbage collection
            gc.collect()
            
            # Generate test dataset
            test_dataset = self.generate_test_dataset(size)
            
            with self.start_monitoring():
                start_time = time.time()
                
                try:
                    # Test chunk processing scalability
                    original_chunk_size = self.config.processing.chunk_size
                    
                    # Adjust chunk size based on dataset size
                    if size <= 1000:
                        self.config.processing.chunk_size = 100
                    elif size <= 10000:
                        self.config.processing.chunk_size = 500
                    else:
                        self.config.processing.chunk_size = 1000
                    
                    # Process dataset in chunks
                    processed_count = 0
                    error_count = 0
                    
                    def process_chunk(chunk_data):
                        """Process a chunk of records"""
                        chunk_processed = 0
                        chunk_errors = 0
                        
                        for record in chunk_data:
                            try:
                                # Simulate photo extraction and validation
                                photo_data = record['photo_data']
                                
                                # Cache the photo data
                                if self.cache_manager:
                                    cache_key = f"photo_{record['id']}"
                                    self.cache_manager.set(cache_key, photo_data, ttl_seconds=3600)
                                
                                # Simulate processing time
                                time.sleep(0.001)  # 1ms per record
                                
                                chunk_processed += 1
                                
                            except Exception as e:
                                chunk_errors += 1
                                self.logger.debug(f"Error processing record {record['id']}: {e}")
                        
                        return chunk_processed, chunk_errors
                    
                    # Create chunks and process
                    chunks = self.chunk_processor.create_chunks(len(test_dataset))
                    
                    for chunk_info in chunks:
                        start_idx = chunk_info.start_index
                        end_idx = chunk_info.end_index
                        chunk_data = test_dataset[start_idx:end_idx]
                        
                        processed, errors = process_chunk(chunk_data)
                        processed_count += processed
                        error_count += errors
                    
                    end_time = time.time()
                    
                    # Restore original chunk size
                    self.config.processing.chunk_size = original_chunk_size
                    
                    # Calculate metrics
                    execution_time = end_time - start_time
                    success_rate = (processed_count / len(test_dataset) * 100) if test_dataset else 0
                    throughput = len(test_dataset) / execution_time if execution_time > 0 else 0
                    
                    resource_summary = self.get_resource_summary()
                    
                    result = ScalabilityTestResult(
                        test_name=f"dataset_scalability_{size}",
                        dataset_size=len(test_dataset),
                        execution_time=execution_time,
                        memory_usage_mb=resource_summary.get('process_memory_mb', {}).get('avg', 0),
                        memory_peak_mb=resource_summary.get('process_memory_mb', {}).get('peak', 0),
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        throughput=throughput,
                        success_rate=success_rate,
                        errors=[f"Processing errors: {error_count}"] if error_count > 0 else [],
                        metadata={
                            'chunk_size': self.config.processing.chunk_size,
                            'chunks_processed': len(chunks),
                            'processed_records': processed_count,
                            'error_records': error_count,
                            'resource_summary': resource_summary
                        }
                    )
                    
                    results.append(result)
                    
                    self.logger.info(f"Dataset scalability test completed: {execution_time:.2f}s, "
                                   f"{throughput:.1f} records/sec, success rate: {success_rate:.1f}%")
                    
                    # Cleanup
                    del test_dataset
                    gc.collect()
                    
                except Exception as e:
                    self.logger.error(f"Dataset scalability test failed: {e}")
                    traceback.print_exc()
                    
                    end_time = time.time()
                    execution_time = end_time - start_time
                    resource_summary = self.get_resource_summary()
                    
                    result = ScalabilityTestResult(
                        test_name=f"dataset_scalability_{size}",
                        dataset_size=size,
                        execution_time=execution_time,
                        memory_usage_mb=resource_summary.get('process_memory_mb', {}).get('avg', 0),
                        memory_peak_mb=resource_summary.get('process_memory_mb', {}).get('peak', 0),
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        throughput=0.0,
                        success_rate=0.0,
                        errors=[str(e)],
                        metadata={
                            'resource_summary': resource_summary
                        }
                    )
                    
                    results.append(result)
        
        return results
    
    def test_concurrent_load(self, concurrent_users: List[int], duration_seconds: int = 60) -> List[LoadTestResult]:
        """Test system under concurrent load"""
        results = []
        
        for users in concurrent_users:
            self.logger.info(f"Testing concurrent load with {users} users for {duration_seconds}s")
            
            # Clear cache before test
            if self.cache_manager:
                self.cache_manager.clear()
            
            with self.start_monitoring():
                start_time = time.time()
                
                try:
                    # Simulate concurrent users
                    total_requests = 0
                    successful_requests = 0
                    failed_requests = 0
                    response_times = []
                    
                    def simulate_user_request(user_id: int) -> Tuple[bool, float]:
                        """Simulate a single user request"""
                        request_start = time.time()
                        
                        try:
                            # Simulate photo extraction request
                            record_id = f"user_{user_id}_record_{random.randint(1, 1000)}"
                            
                            # Try to get from cache first
                            if self.cache_manager:
                                cached_data = self.cache_manager.get(f"photo_{record_id}")
                                if cached_data:
                                    request_time = time.time() - request_start
                                    return True, request_time
                            
                            # Simulate database query and processing
                            time.sleep(random.uniform(0.01, 0.1))  # 10-100ms processing time
                            
                            # Cache the result
                            if self.cache_manager:
                                photo_data = f"data:image/jpeg;base64,{'x' * 1000}"
                                self.cache_manager.set(f"photo_{record_id}", photo_data, ttl_seconds=3600)
                            
                            request_time = time.time() - request_start
                            return True, request_time
                            
                        except Exception as e:
                            request_time = time.time() - request_start
                            self.logger.debug(f"User {user_id} request failed: {e}")
                            return False, request_time
                    
                    def user_worker(user_id: int):
                        """Worker function for a user"""
                        nonlocal total_requests, successful_requests, failed_requests, response_times
                        
                        end_time = start_time + duration_seconds
                        
                        while time.time() < end_time:
                            success, response_time = simulate_user_request(user_id)
                            
                            total_requests += 1
                            response_times.append(response_time)
                            
                            if success:
                                successful_requests += 1
                            else:
                                failed_requests += 1
                            
                            # Small delay between requests
                            time.sleep(random.uniform(0.1, 0.5))
                    
                    # Start concurrent users
                    with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
                        futures = [executor.submit(user_worker, i) for i in range(users)]
                        
                        # Wait for all users to complete
                        concurrent.futures.wait(futures, timeout=duration_seconds + 10)
                    
                    end_time = time.time()
                    actual_duration = end_time - start_time
                    
                    # Calculate metrics
                    avg_response_time = statistics.mean(response_times) if response_times else 0
                    max_response_time = max(response_times) if response_times else 0
                    min_response_time = min(response_times) if response_times else 0
                    requests_per_second = total_requests / actual_duration if actual_duration > 0 else 0
                    error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
                    
                    resource_summary = self.get_resource_summary()
                    
                    result = LoadTestResult(
                        test_name=f"concurrent_load_{users}_users",
                        concurrent_users=users,
                        duration_seconds=actual_duration,
                        total_requests=total_requests,
                        successful_requests=successful_requests,
                        failed_requests=failed_requests,
                        avg_response_time=avg_response_time,
                        max_response_time=max_response_time,
                        min_response_time=min_response_time,
                        requests_per_second=requests_per_second,
                        error_rate=error_rate,
                        memory_usage_mb=resource_summary.get('process_memory_mb', {}).get('avg', 0),
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        errors=[]
                    )
                    
                    results.append(result)
                    
                    self.logger.info(f"Concurrent load test completed: {requests_per_second:.1f} req/sec, "
                                   f"avg response: {avg_response_time*1000:.1f}ms, error rate: {error_rate:.1f}%")
                    
                except Exception as e:
                    self.logger.error(f"Concurrent load test failed: {e}")
                    traceback.print_exc()
                    
                    end_time = time.time()
                    actual_duration = end_time - start_time
                    resource_summary = self.get_resource_summary()
                    
                    result = LoadTestResult(
                        test_name=f"concurrent_load_{users}_users",
                        concurrent_users=users,
                        duration_seconds=actual_duration,
                        total_requests=0,
                        successful_requests=0,
                        failed_requests=0,
                        avg_response_time=0,
                        max_response_time=0,
                        min_response_time=0,
                        requests_per_second=0,
                        error_rate=100.0,
                        memory_usage_mb=resource_summary.get('process_memory_mb', {}).get('avg', 0),
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        errors=[str(e)]
                    )
                    
                    results.append(result)
        
        return results
    
    def test_memory_scalability(self, sizes: List[int]) -> List[ScalabilityTestResult]:
        """Test memory usage scalability"""
        results = []
        
        for size in sizes:
            self.logger.info(f"Testing memory scalability with {size:,} records")
            
            # Clear cache and force garbage collection
            if self.cache_manager:
                self.cache_manager.clear()
            gc.collect()
            
            # Get initial memory
            process = psutil.Process()
            initial_memory = process.memory_info().rss / (1024 * 1024)
            
            with self.start_monitoring():
                start_time = time.time()
                
                try:
                    # Create large dataset and cache it
                    cached_items = 0
                    
                    for i in range(size):
                        # Generate photo data
                        photo_size = random.randint(1000, 5000)  # 1KB to 5KB
                        photo_data = ''.join(random.choices(string.ascii_letters + string.digits, k=photo_size))
                        
                        # Cache the data
                        if self.cache_manager:
                            cache_key = f"memory_test_{i:06d}"
                            if self.cache_manager.set(cache_key, photo_data, ttl_seconds=3600):
                                cached_items += 1
                        
                        # Check memory usage periodically
                        if i % 1000 == 0:
                            current_memory = process.memory_info().rss / (1024 * 1024)
                            memory_growth = current_memory - initial_memory
                            
                            # Stop if memory usage gets too high
                            if memory_growth > 1500:  # 1.5GB limit
                                self.logger.warning(f"Memory usage too high: {memory_growth:.1f}MB, stopping test")
                                break
                    
                    end_time = time.time()
                    
                    # Get final memory
                    final_memory = process.memory_info().rss / (1024 * 1024)
                    memory_usage_mb = final_memory - initial_memory
                    memory_per_item = memory_usage_mb / cached_items if cached_items > 0 else 0
                    
                    # Calculate metrics
                    execution_time = end_time - start_time
                    throughput = cached_items / execution_time if execution_time > 0 else 0
                    
                    resource_summary = self.get_resource_summary()
                    
                    result = ScalabilityTestResult(
                        test_name=f"memory_scalability_{size}",
                        dataset_size=cached_items,
                        execution_time=execution_time,
                        memory_usage_mb=memory_usage_mb,
                        memory_peak_mb=resource_summary.get('process_memory_mb', {}).get('peak', 0),
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        throughput=throughput,
                        success_rate=100.0,
                        errors=[],
                        metadata={
                            'initial_memory_mb': initial_memory,
                            'final_memory_mb': final_memory,
                            'memory_per_item_mb': memory_per_item,
                            'cache_stats': self.cache_manager.get_stats() if self.cache_manager else {},
                            'resource_summary': resource_summary
                        }
                    )
                    
                    results.append(result)
                    
                    self.logger.info(f"Memory scalability test completed: {memory_usage_mb:.1f}MB used, "
                                   f"{memory_per_item:.2f}MB per item, {cached_items} items cached")
                    
                    # Cleanup
                    if self.cache_manager:
                        self.cache_manager.clear()
                    gc.collect()
                    
                except Exception as e:
                    self.logger.error(f"Memory scalability test failed: {e}")
                    traceback.print_exc()
                    
                    end_time = time.time()
                    execution_time = end_time - start_time
                    resource_summary = self.get_resource_summary()
                    
                    result = ScalabilityTestResult(
                        test_name=f"memory_scalability_{size}",
                        dataset_size=size,
                        execution_time=execution_time,
                        memory_usage_mb=resource_summary.get('process_memory_mb', {}).get('avg', 0),
                        memory_peak_mb=resource_summary.get('process_memory_mb', {}).get('peak', 0),
                        cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
                        throughput=0.0,
                        success_rate=0.0,
                        errors=[str(e)],
                        metadata={
                            'resource_summary': resource_summary
                        }
                    )
                    
                    results.append(result)
        
        return results
    
    def run_all_scalability_tests(self) -> Dict[str, List]:
        """Run all scalability tests"""
        self.logger.info("Starting comprehensive scalability tests")
        
        if not self.setup_components():
            raise Exception("Failed to setup components for scalability testing")
        
        all_results = {}
        
        # Define test parameters
        dataset_sizes = [1000, 5000, 10000, 25000, 50000]  # Different dataset sizes
        concurrent_users = [1, 5, 10, 20, 50]  # Different concurrent user counts
        
        try:
            # 1. Dataset Scalability Tests
            self.logger.info("Running dataset scalability tests...")
            dataset_results = self.test_dataset_scalability(dataset_sizes)
            all_results['dataset_scalability'] = dataset_results
            
            # 2. Concurrent Load Tests
            self.logger.info("Running concurrent load tests...")
            load_results = self.test_concurrent_load(concurrent_users, duration_seconds=30)
            all_results['concurrent_load'] = load_results
            
            # 3. Memory Scalability Tests
            self.logger.info("Running memory scalability tests...")
            memory_results = self.test_memory_scalability(dataset_sizes)
            all_results['memory_scalability'] = memory_results
            
            self.logger.info("All scalability tests completed successfully")
            
        except Exception as e:
            self.logger.error(f"Scalability test suite failed: {e}")
            traceback.print_exc()
        
        return all_results
    
    def save_results(self, results: Dict[str, List], filename: str = None):
        """Save scalability test results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scalability_results_{timestamp}.json"
        
        output_file = self.output_dir / filename
        
        # Convert results to serializable format
        serializable_results = {}
        for category, test_results in results.items():
            if category == 'concurrent_load':
                serializable_results[category] = [asdict(result) for result in test_results]
            else:
                serializable_results[category] = [asdict(result) for result in test_results]
        
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
            
            self.logger.info(f"Scalability test results saved to: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            return False
    
    def generate_summary(self, results: Dict[str, List]) -> Dict[str, Any]:
        """Generate summary statistics from scalability test results"""
        summary = {
            'total_tests': 0,
            'successful_tests': 0,
            'categories': {}
        }
        
        for category, test_results in results.items():
            category_summary = {
                'test_count': len(test_results),
                'avg_throughput': 0,
                'max_throughput': 0,
                'avg_success_rate': 0,
                'max_memory_usage': 0,
                'scalability_factor': 0  # How well performance scales with size
            }
            
            if test_results:
                if category == 'concurrent_load':
                    # Load test results
                    throughputs = [r.requests_per_second for r in test_results]
                    success_rates = [100 - r.error_rate for r in test_results]
                    memory_usages = [r.memory_usage_mb for r in test_results]
                else:
                    # Scalability test results
                    throughputs = [r.throughput for r in test_results]
                    success_rates = [r.success_rate for r in test_results]
                    memory_usages = [r.memory_usage_mb for r in test_results]
                
                category_summary.update({
                    'avg_throughput': statistics.mean(throughputs),
                    'max_throughput': max(throughputs),
                    'avg_success_rate': statistics.mean(success_rates),
                    'max_memory_usage': max(memory_usages)
                })
                
                # Calculate scalability factor (performance degradation)
                if len(test_results) >= 2:
                    first_throughput = throughputs[0]
                    last_throughput = throughputs[-1]
                    if first_throughput > 0:
                        scalability_factor = last_throughput / first_throughput
                        category_summary['scalability_factor'] = scalability_factor
                
                # Count successful tests
                successful = len([r for r in test_results if r.success_rate > 50])  # At least 50% success
                summary['successful_tests'] += successful
            
            summary['categories'][category] = category_summary
            summary['total_tests'] += len(test_results)
        
        return summary


def main():
    """Main scalability test execution"""
    parser = argparse.ArgumentParser(
        description="Scalability Tests for UNS-CLAUDEJP 5.4 Photo Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                                    # Run all scalability tests
    %(prog)s --config custom_config.json          # Use custom configuration
    %(prog)s --output results/                   # Save to specific directory
    %(prog)s --max-size 25000                   # Maximum dataset size to test
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
        default='scalability_results',
        help='Output directory for results (default: scalability_results)'
    )
    
    parser.add_argument(
        '--max-size',
        type=int,
        default=50000,
        help='Maximum dataset size to test (default: 50000)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_path = args.config
        config = load_config(config_path)
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("UNS-CLAUDEJP 5.4 - Scalability Tests")
        print("=" * 60)
        print(f"Output directory: {output_dir}")
        print(f"Maximum dataset size: {args.max_size:,}")
        print(f"Configuration: {config_path or 'default'}")
        print()
        
        # Run scalability tests
        test_suite = ScalabilityTestSuite(config, output_dir)
        results = test_suite.run_all_scalability_tests()
        
        # Save results
        success = test_suite.save_results(results)
        
        if success:
            print("\nScalability tests completed successfully!")
            print(f"Results saved to: {output_dir}")
            
            # Print summary
            summary = test_suite.generate_summary(results)
            print(f"\nSummary:")
            print(f"  Total tests: {summary['total_tests']}")
            print(f"  Successful: {summary['successful_tests']}")
            
            for category, cat_summary in summary['categories'].items():
                print(f"\n{category.replace('_', ' ').title()}:")
                print(f"  Tests: {cat_summary['test_count']}")
                print(f"  Avg throughput: {cat_summary['avg_throughput']:.1f} ops/sec")
                print(f"  Max throughput: {cat_summary['max_throughput']:.1f} ops/sec")
                print(f"  Avg success rate: {cat_summary['avg_success_rate']:.1f}%")
                print(f"  Max memory usage: {cat_summary['max_memory_usage']:.1f}MB")
                
                if cat_summary.get('scalability_factor', 0) > 0:
                    print(f"  Scalability factor: {cat_summary['scalability_factor']:.2f}")
            
            return 0
        else:
            print("ERROR: Failed to save scalability test results")
            return 1
    
    except KeyboardInterrupt:
        print("\nScalability tests interrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)