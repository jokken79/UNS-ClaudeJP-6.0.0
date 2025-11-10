#!/usr/bin/env python3
"""
Load and Stress Tests for UNS-CLAUDEJP 5.4 Photo Extraction System v2.0

This module provides comprehensive load and stress testing to validate system
behavior under extreme conditions and concurrent access patterns.

Usage:
    python load_tests.py [--config PATH] [--output PATH] [--duration SECONDS]
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
import queue
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
import statistics
import gc
import signal

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
class LoadTestResult:
    """Result of a load test"""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    timeout_requests: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    timeout_rate: float
    memory_usage_mb: float
    memory_peak_mb: float
    cpu_usage_percent: float
    concurrent_users: int
    errors: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StressTestResult:
    """Result of a stress test"""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    max_concurrent_users: int
    breaking_point_users: int  # Users at which system starts failing
    breaking_point_rps: int  # Requests per second at breaking point
    max_sustained_rps: int  # Maximum sustainable RPS
    system_degradation: float  # Performance degradation percentage
    recovery_time: float  # Time to recover after load
    memory_leak_detected: bool
    connection_errors: int
    timeout_errors: int
    system_errors: int
    avg_response_time_normal: float
    avg_response_time_stress: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LoadTestSuite:
    """Comprehensive load and stress testing suite"""
    
    def __init__(self, config: PhotoExtractionConfig, output_dir: Path = None):
        self.config = config
        self.output_dir = output_dir or Path("load_test_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self.logger = create_logger("LoadTest", config)
        
        # Initialize components
        self.extractor = None
        self.cache_manager = None
        self.performance_optimizer = None
        
        # Test control
        self.test_running = False
        self.test_stop_event = threading.Event()
        
        # Metrics collection
        self.request_times = queue.Queue()
        self.error_counts = {}
        self.system_metrics = []
        self.monitoring_active = False
        self.monitor_thread = None
        
        self.logger.info("Load test suite initialized")
    
    def setup_components(self):
        """Setup system components for testing"""
        try:
            self.extractor = AdvancedPhotoExtractor(self.config)
            self.cache_manager = create_cache_manager(self.config, self.logger)
            self.performance_optimizer = create_performance_optimizer(self.config, self.logger)
            
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
                    time.sleep(0.1)  # Sample every 100ms
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(0.5)
        
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
    
    def simulate_photo_extraction_request(self, user_id: int, request_id: int) -> Tuple[bool, float, str]:
        """Simulate a photo extraction request"""
        start_time = time.time()
        
        try:
            # Generate random record ID
            record_id = f"user_{user_id}_request_{request_id}_record_{random.randint(1, 10000)}"
            
            # Try to get from cache first
            if self.cache_manager:
                cached_data = self.cache_manager.get(f"photo_{record_id}")
                if cached_data:
                    response_time = time.time() - start_time
                    return True, response_time, "cache_hit"
            
            # Simulate database processing time
            processing_time = random.uniform(0.05, 0.5)  # 50-500ms
            time.sleep(processing_time)
            
            # Simulate photo data generation
            photo_size = random.randint(1000, 10000)  # 1KB to 10KB
            photo_data = ''.join(random.choices(string.ascii_letters + string.digits, k=photo_size))
            
            # Cache the result
            if self.cache_manager:
                cache_key = f"photo_{record_id}"
                photo_value = f"data:image/jpeg;base64,{photo_data}"
                self.cache_manager.set(cache_key, photo_value, ttl_seconds=3600)
            
            response_time = time.time() - start_time
            return True, response_time, "processed"
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Request failed: {str(e)}"
            self.logger.debug(f"User {user_id} request {request_id} failed: {e}")
            return False, response_time, error_msg
    
    def test_constant_load(self, concurrent_users: int, duration_seconds: int, 
                          requests_per_second: float) -> LoadTestResult:
        """Test system under constant load"""
        test_name = f"constant_load_{concurrent_users}_users_{requests_per_second}_rps"
        self.logger.info(f"Starting constant load test: {concurrent_users} users, {requests_per_second} RPS, {duration_seconds}s")
        
        start_time = datetime.now()
        self.test_running = True
        self.test_stop_event.clear()
        
        # Metrics
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        timeout_requests = 0
        request_times = []
        errors = []
        
        # Calculate request interval
        request_interval = 1.0 / requests_per_second if requests_per_second > 0 else 1.0
        
        def user_worker(user_id: int):
            """Worker function for a user"""
            nonlocal total_requests, successful_requests, failed_requests, timeout_requests, request_times, errors
            
            request_id = 0
            next_request_time = time.time()
            
            while self.test_running and not self.test_stop_event.is_set():
                current_time = time.time()
                
                # Wait until next request time
                if current_time < next_request_time:
                    time.sleep(next_request_time - current_time)
                
                # Check if test duration exceeded
                if (datetime.now() - start_time).total_seconds() >= duration_seconds:
                    break
                
                # Make request
                try:
                    success, response_time, result = self.simulate_photo_extraction_request(user_id, request_id)
                    
                    total_requests += 1
                    request_times.append(response_time)
                    
                    if success:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                        if "timeout" in result.lower():
                            timeout_requests += 1
                        errors.append(f"User {user_id}, Request {request_id}: {result}")
                    
                except Exception as e:
                    total_requests += 1
                    failed_requests += 1
                    errors.append(f"User {user_id}, Request {request_id}: Exception - {str(e)}")
                
                request_id += 1
                next_request_time += request_interval
        
        # Start monitoring
        self.start_monitoring()
        
        try:
            # Start user workers
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(user_worker, i) for i in range(concurrent_users)]
                
                # Wait for all workers to complete
                concurrent.futures.wait(futures, timeout=duration_seconds + 30)
                
                # Stop test
                self.test_running = False
                self.test_stop_event.set()
        
        finally:
            end_time = datetime.now()
            self.stop_monitoring()
        
        # Calculate metrics
        duration = (end_time - start_time).total_seconds()
        actual_rps = total_requests / duration if duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        timeout_rate = (timeout_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Response time statistics
        if request_times:
            avg_response_time = statistics.mean(request_times)
            max_response_time = max(request_times)
            min_response_time = min(request_times)
            p95_response_time = statistics.quantiles(request_times, n=20)[18] if len(request_times) >= 20 else max(request_times)
            p99_response_time = statistics.quantiles(request_times, n=100)[98] if len(request_times) >= 100 else max(request_times)
        else:
            avg_response_time = max_response_time = min_response_time = p95_response_time = p99_response_time = 0
        
        resource_summary = self.get_resource_summary()
        
        result = LoadTestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            timeout_requests=timeout_requests,
            avg_response_time=avg_response_time,
            max_response_time=max_response_time,
            min_response_time=min_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=actual_rps,
            error_rate=error_rate,
            timeout_rate=timeout_rate,
            memory_usage_mb=resource_summary.get('process_memory_mb', {}).get('avg', 0),
            memory_peak_mb=resource_summary.get('process_memory_mb', {}).get('peak', 0),
            cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
            concurrent_users=concurrent_users,
            errors=errors[:100],  # Limit error list size
            metadata={
                'target_rps': requests_per_second,
                'request_interval': request_interval,
                'resource_summary': resource_summary
            }
        )
        
        self.logger.info(f"Constant load test completed: {actual_rps:.1f} RPS, "
                       f"error rate: {error_rate:.1f}%, avg response: {avg_response_time*1000:.1f}ms")
        
        return result
    
    def test_ramp_up_load(self, max_users: int, ramp_duration_seconds: int, 
                         hold_duration_seconds: int) -> LoadTestResult:
        """Test system with ramping up load"""
        test_name = f"ramp_up_load_{max_users}_users"
        self.logger.info(f"Starting ramp-up load test: 0 to {max_users} users in {ramp_duration_seconds}s, hold {hold_duration_seconds}s")
        
        start_time = datetime.now()
        self.test_running = True
        self.test_stop_event.clear()
        
        # Metrics
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        timeout_requests = 0
        request_times = []
        errors = []
        active_workers = []
        
        def user_worker(user_id: int):
            """Worker function for a user"""
            nonlocal total_requests, successful_requests, failed_requests, timeout_requests, request_times, errors
            
            request_id = 0
            
            while self.test_running and not self.test_stop_event.is_set():
                # Make request with random interval
                try:
                    success, response_time, result = self.simulate_photo_extraction_request(user_id, request_id)
                    
                    total_requests += 1
                    request_times.append(response_time)
                    
                    if success:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                        if "timeout" in result.lower():
                            timeout_requests += 1
                        errors.append(f"User {user_id}, Request {request_id}: {result}")
                    
                except Exception as e:
                    total_requests += 1
                    failed_requests += 1
                    errors.append(f"User {user_id}, Request {request_id}: Exception - {str(e)}")
                
                request_id += 1
                
                # Random delay between requests (0.5-2 seconds)
                time.sleep(random.uniform(0.5, 2.0))
        
        # Start monitoring
        self.start_monitoring()
        
        try:
            # Ramp up phase
            self.logger.info("Starting ramp-up phase")
            ramp_start = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_users) as executor:
                futures = []
                
                # Gradually add users
                for user_id in range(max_users):
                    if not self.test_running:
                        break
                    
                    # Calculate when this user should start
                    elapsed = time.time() - ramp_start
                    if elapsed < ramp_duration_seconds:
                        # Calculate delay for this user
                        user_delay = (user_id / max_users) * ramp_duration_seconds
                        remaining_delay = user_delay - elapsed
                        
                        if remaining_delay > 0:
                            time.sleep(remaining_delay)
                    
                    # Start user worker
                    future = executor.submit(user_worker, user_id)
                    futures.append(future)
                    active_workers.append(future)
                    
                    self.logger.info(f"Started user {user_id + 1}/{max_users}")
                
                # Hold phase
                self.logger.info(f"Starting hold phase for {hold_duration_seconds}s")
                hold_start = time.time()
                
                while (time.time() - hold_start) < hold_duration_seconds and self.test_running:
                    time.sleep(1.0)
                
                # Stop test
                self.test_running = False
                self.test_stop_event.set()
        
        finally:
            end_time = datetime.now()
            self.stop_monitoring()
        
        # Calculate metrics
        duration = (end_time - start_time).total_seconds()
        actual_rps = total_requests / duration if duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        timeout_rate = (timeout_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Response time statistics
        if request_times:
            avg_response_time = statistics.mean(request_times)
            max_response_time = max(request_times)
            min_response_time = min(request_times)
            p95_response_time = statistics.quantiles(request_times, n=20)[18] if len(request_times) >= 20 else max(request_times)
            p99_response_time = statistics.quantiles(request_times, n=100)[98] if len(request_times) >= 100 else max(request_times)
        else:
            avg_response_time = max_response_time = min_response_time = p95_response_time = p99_response_time = 0
        
        resource_summary = self.get_resource_summary()
        
        result = LoadTestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            timeout_requests=timeout_requests,
            avg_response_time=avg_response_time,
            max_response_time=max_response_time,
            min_response_time=min_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=actual_rps,
            error_rate=error_rate,
            timeout_rate=timeout_rate,
            memory_usage_mb=resource_summary.get('process_memory_mb', {}).get('avg', 0),
            memory_peak_mb=resource_summary.get('process_memory_mb', {}).get('peak', 0),
            cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
            concurrent_users=max_users,
            errors=errors[:100],  # Limit error list size
            metadata={
                'ramp_duration': ramp_duration_seconds,
                'hold_duration': hold_duration_seconds,
                'resource_summary': resource_summary
            }
        )
        
        self.logger.info(f"Ramp-up load test completed: {actual_rps:.1f} RPS, "
                       f"error rate: {error_rate:.1f}%, avg response: {avg_response_time*1000:.1f}ms")
        
        return result
    
    def test_stress_load(self, max_users: int, step_users: int, step_duration_seconds: int = 60) -> StressTestResult:
        """Test system under increasing stress to find breaking point"""
        test_name = f"stress_load_{max_users}_max_users"
        self.logger.info(f"Starting stress test: up to {max_users} users, step {step_users}, {step_duration_seconds}s per step")
        
        start_time = datetime.now()
        self.test_running = True
        self.test_stop_event.clear()
        
        # Metrics
        breaking_point_users = 0
        breaking_point_rps = 0
        max_sustained_rps = 0
        system_degradation = 0
        recovery_time = 0
        memory_leak_detected = False
        connection_errors = 0
        timeout_errors = 0
        system_errors = 0
        
        # Response times for analysis
        normal_response_times = []
        stress_response_times = []
        
        # Memory tracking
        initial_memory = None
        peak_memory = 0
        
        def stress_test_step(current_users: int) -> Dict[str, Any]:
            """Execute a single stress test step"""
            step_start = time.time()
            
            # Metrics for this step
            step_requests = 0
            step_successful = 0
            step_failed = 0
            step_response_times = []
            step_errors = []
            
            def user_worker(user_id: int):
                """Worker function for stress test"""
                nonlocal step_requests, step_successful, step_failed, step_response_times, step_errors
                
                request_id = 0
                step_end = step_start + step_duration_seconds
                
                while time.time() < step_end and self.test_running:
                    try:
                        success, response_time, result = self.simulate_photo_extraction_request(user_id, request_id)
                        
                        step_requests += 1
                        step_response_times.append(response_time)
                        
                        if success:
                            step_successful += 1
                        else:
                            step_failed += 1
                            
                            # Categorize errors
                            if "connection" in result.lower():
                                connection_errors += 1
                            elif "timeout" in result.lower():
                                timeout_errors += 1
                            else:
                                system_errors += 1
                            
                            step_errors.append(f"User {user_id}: {result}")
                    
                    except Exception as e:
                        step_requests += 1
                        step_failed += 1
                        system_errors += 1
                        step_errors.append(f"User {user_id}: Exception - {str(e)}")
                    
                    request_id += 1
                    
                    # High frequency requests for stress test
                    time.sleep(random.uniform(0.01, 0.1))
            
            # Execute stress step
            with concurrent.futures.ThreadPoolExecutor(max_workers=current_users) as executor:
                futures = [executor.submit(user_worker, i) for i in range(current_users)]
                
                # Wait for completion
                concurrent.futures.wait(futures, timeout=step_duration_seconds + 10)
            
            step_end = time.time()
            step_duration = step_end - step_start
            
            # Calculate step metrics
            step_rps = step_requests / step_duration if step_duration > 0 else 0
            step_error_rate = (step_failed / step_requests * 100) if step_requests > 0 else 0
            step_avg_response = statistics.mean(step_response_times) if step_response_times else 0
            
            return {
                'users': current_users,
                'requests': step_requests,
                'successful': step_successful,
                'failed': step_failed,
                'rps': step_rps,
                'error_rate': step_error_rate,
                'avg_response_time': step_avg_response,
                'response_times': step_response_times,
                'errors': step_errors
            }
        
        # Start monitoring
        self.start_monitoring()
        
        try:
            # Baseline measurement with minimal load
            self.logger.info("Measuring baseline performance...")
            baseline_result = stress_test_step(1)
            normal_response_times = baseline_result['response_times']
            baseline_rps = baseline_result['rps']
            
            # Get initial memory
            if self.system_metrics:
                initial_memory = self.system_metrics[0]['process_memory_mb']
            
            # Stress test with increasing load
            step_results = []
            current_users = step_users
            
            while current_users <= max_users and self.test_running:
                self.logger.info(f"Testing with {current_users} users...")
                
                step_result = stress_test_step(current_users)
                step_results.append(step_result)
                
                # Track peak memory
                if self.system_metrics:
                    current_memory = max(m['process_memory_mb'] for m in self.system_metrics[-100:])  # Last 100 samples
                    peak_memory = max(peak_memory, current_memory)
                
                # Check for breaking point (error rate > 10% or response time > 5 seconds)
                if step_result['error_rate'] > 10 or step_result['avg_response_time'] > 5.0:
                    if breaking_point_users == 0:  # First breaking point
                        breaking_point_users = current_users
                        breaking_point_rps = step_result['rps']
                        self.logger.warning(f"Breaking point detected at {current_users} users: "
                                         f"error rate {step_result['error_rate']:.1f}%, "
                                         f"avg response {step_result['avg_response_time']:.2f}s")
                
                # Track maximum sustained RPS (error rate < 5%)
                if step_result['error_rate'] < 5:
                    max_sustained_rps = max(max_sustained_rps, step_result['rps'])
                
                # Collect stress response times
                stress_response_times.extend(step_result['response_times'])
                
                current_users += step_users
                
                # Small break between steps
                time.sleep(2.0)
            
            # Recovery test
            self.logger.info("Testing recovery after stress...")
            recovery_start = time.time()
            
            # Run with minimal load to test recovery
            recovery_result = stress_test_step(1)
            recovery_end = time.time()
            recovery_time = recovery_end - recovery_start
            
            # Calculate system degradation
            if normal_response_times and stress_response_times:
                normal_avg = statistics.mean(normal_response_times)
                stress_avg = statistics.mean(stress_response_times)
                system_degradation = ((stress_avg - normal_avg) / normal_avg) * 100 if normal_avg > 0 else 0
            
            # Check for memory leak
            if initial_memory and peak_memory:
                memory_growth = peak_memory - initial_memory
                memory_leak_detected = memory_growth > 500  # 500MB growth threshold
        
        finally:
            end_time = datetime.now()
            self.stop_monitoring()
        
        # Calculate final metrics
        duration = (end_time - start_time).total_seconds()
        
        # Response time averages
        avg_response_normal = statistics.mean(normal_response_times) if normal_response_times else 0
        avg_response_stress = statistics.mean(stress_response_times) if stress_response_times else 0
        
        resource_summary = self.get_resource_summary()
        
        result = StressTestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            max_concurrent_users=max_users,
            breaking_point_users=breaking_point_users,
            breaking_point_rps=breaking_point_rps,
            max_sustained_rps=max_sustained_rps,
            system_degradation=system_degradation,
            recovery_time=recovery_time,
            memory_leak_detected=memory_leak_detected,
            connection_errors=connection_errors,
            timeout_errors=timeout_errors,
            system_errors=system_errors,
            avg_response_time_normal=avg_response_normal,
            avg_response_time_stress=avg_response_stress,
            metadata={
                'step_users': step_users,
                'step_duration': step_duration_seconds,
                'baseline_rps': baseline_rps,
                'step_results': step_results,
                'resource_summary': resource_summary
            }
        )
        
        self.logger.info(f"Stress test completed: breaking point at {breaking_point_users} users, "
                       f"max sustained RPS: {max_sustained_rps:.1f}, "
                       f"system degradation: {system_degradation:.1f}%")
        
        return result
    
    def test_spike_load(self, baseline_users: int, spike_users: int, 
                      spike_duration_seconds: int, total_duration_seconds: int) -> LoadTestResult:
        """Test system with load spikes"""
        test_name = f"spike_load_{baseline_users}_baseline_{spike_users}_spike"
        self.logger.info(f"Starting spike load test: {baseline_users} baseline, {spike_users} spike, "
                       f"{spike_duration_seconds}s spikes, {total_duration_seconds}s total")
        
        start_time = datetime.now()
        self.test_running = True
        self.test_stop_event.clear()
        
        # Metrics
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        timeout_requests = 0
        request_times = []
        errors = []
        
        # Worker management
        baseline_workers = []
        spike_workers = []
        worker_id_counter = 0
        
        def user_worker(user_id: int, is_spike: bool = False):
            """Worker function for a user"""
            nonlocal total_requests, successful_requests, failed_requests, timeout_requests, request_times, errors
            
            request_id = 0
            
            while self.test_running and not self.test_stop_event.is_set():
                # Check if test duration exceeded
                if (datetime.now() - start_time).total_seconds() >= total_duration_seconds:
                    break
                
                try:
                    success, response_time, result = self.simulate_photo_extraction_request(user_id, request_id)
                    
                    total_requests += 1
                    request_times.append(response_time)
                    
                    if success:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                        if "timeout" in result.lower():
                            timeout_requests += 1
                        errors.append(f"User {user_id} ({'spike' if is_spike else 'baseline'}): {result}")
                    
                except Exception as e:
                    total_requests += 1
                    failed_requests += 1
                    errors.append(f"User {user_id} ({'spike' if is_spike else 'baseline'}): Exception - {str(e)}")
                
                request_id += 1
                
                # Different request rates for baseline vs spike
                if is_spike:
                    time.sleep(random.uniform(0.01, 0.05))  # High frequency for spike
                else:
                    time.sleep(random.uniform(0.5, 2.0))  # Normal frequency for baseline
        
        # Start monitoring
        self.start_monitoring()
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=baseline_users + spike_users) as executor:
                # Start baseline workers
                for i in range(baseline_users):
                    future = executor.submit(user_worker, worker_id_counter, False)
                    baseline_workers.append(future)
                    worker_id_counter += 1
                
                # Spike management
                spike_active = False
                next_spike_time = start_time.timestamp() + 5  # First spike after 5 seconds
                
                while self.test_running and not self.test_stop_event.is_set():
                    current_time = time.time()
                    
                    # Check if it's time for a spike
                    if current_time >= next_spike_time:
                        if not spike_active:
                            # Start spike
                            self.logger.info("Starting load spike")
                            spike_active = True
                            
                            # Start spike workers
                            for i in range(spike_users):
                                future = executor.submit(user_worker, worker_id_counter, True)
                                spike_workers.append(future)
                                worker_id_counter += 1
                        else:
                            # End spike
                            self.logger.info("Ending load spike")
                            spike_active = False
                            
                            # Wait for spike workers to finish
                            for future in spike_workers:
                                try:
                                    future.result(timeout=5.0)
                                except:
                                    pass
                            spike_workers.clear()
                        
                        # Schedule next spike
                        next_spike_time = current_time + spike_duration_seconds + 10  # 10s between spikes
                    
                    # Check if test duration exceeded
                    if (datetime.now() - start_time).total_seconds() >= total_duration_seconds:
                        break
                    
                    time.sleep(0.1)
                
                # Stop test
                self.test_running = False
                self.test_stop_event.set()
        
        finally:
            end_time = datetime.now()
            self.stop_monitoring()
        
        # Calculate metrics
        duration = (end_time - start_time).total_seconds()
        actual_rps = total_requests / duration if duration > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        timeout_rate = (timeout_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Response time statistics
        if request_times:
            avg_response_time = statistics.mean(request_times)
            max_response_time = max(request_times)
            min_response_time = min(request_times)
            p95_response_time = statistics.quantiles(request_times, n=20)[18] if len(request_times) >= 20 else max(request_times)
            p99_response_time = statistics.quantiles(request_times, n=100)[98] if len(request_times) >= 100 else max(request_times)
        else:
            avg_response_time = max_response_time = min_response_time = p95_response_time = p99_response_time = 0
        
        resource_summary = self.get_resource_summary()
        
        result = LoadTestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            timeout_requests=timeout_requests,
            avg_response_time=avg_response_time,
            max_response_time=max_response_time,
            min_response_time=min_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=actual_rps,
            error_rate=error_rate,
            timeout_rate=timeout_rate,
            memory_usage_mb=resource_summary.get('process_memory_mb', {}).get('avg', 0),
            memory_peak_mb=resource_summary.get('process_memory_mb', {}).get('peak', 0),
            cpu_usage_percent=resource_summary.get('cpu', {}).get('avg', 0),
            concurrent_users=baseline_users + spike_users,
            errors=errors[:100],  # Limit error list size
            metadata={
                'baseline_users': baseline_users,
                'spike_users': spike_users,
                'spike_duration': spike_duration_seconds,
                'resource_summary': resource_summary
            }
        )
        
        self.logger.info(f"Spike load test completed: {actual_rps:.1f} RPS, "
                       f"error rate: {error_rate:.1f}%, avg response: {avg_response_time*1000:.1f}ms")
        
        return result
    
    def run_all_load_tests(self) -> Dict[str, List]:
        """Run all load and stress tests"""
        self.logger.info("Starting comprehensive load and stress tests")
        
        if not self.setup_components():
            raise Exception("Failed to setup components for load testing")
        
        all_results = {}
        
        try:
            # 1. Constant Load Tests
            self.logger.info("Running constant load tests...")
            constant_load_results = [
                self.test_constant_load(10, 60, 5),    # 10 users, 5 RPS, 60s
                self.test_constant_load(25, 60, 10),   # 25 users, 10 RPS, 60s
                self.test_constant_load(50, 60, 20),   # 50 users, 20 RPS, 60s
            ]
            all_results['constant_load'] = constant_load_results
            
            # 2. Ramp-up Load Tests
            self.logger.info("Running ramp-up load tests...")
            ramp_up_results = [
                self.test_ramp_up_load(50, 30, 60),    # 0 to 50 users in 30s, hold 60s
                self.test_ramp_up_load(100, 60, 60),   # 0 to 100 users in 60s, hold 60s
            ]
            all_results['ramp_up_load'] = ramp_up_results
            
            # 3. Stress Tests
            self.logger.info("Running stress tests...")
            stress_results = [
                self.test_stress_load(100, 10, 30),    # Up to 100 users, step 10, 30s per step
                self.test_stress_load(200, 20, 30),    # Up to 200 users, step 20, 30s per step
            ]
            all_results['stress'] = stress_results
            
            # 4. Spike Load Tests
            self.logger.info("Running spike load tests...")
            spike_results = [
                self.test_spike_load(10, 50, 30, 180),   # 10 baseline, 50 spike, 30s spikes, 3min total
                self.test_spike_load(25, 100, 20, 120),  # 25 baseline, 100 spike, 20s spikes, 2min total
            ]
            all_results['spike_load'] = spike_results
            
            self.logger.info("All load and stress tests completed successfully")
            
        except Exception as e:
            self.logger.error(f"Load test suite failed: {e}")
            traceback.print_exc()
        
        return all_results
    
    def save_results(self, results: Dict[str, List], filename: str = None):
        """Save load test results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_results_{timestamp}.json"
        
        output_file = self.output_dir / filename
        
        # Convert results to serializable format
        serializable_results = {}
        for category, test_results in results.items():
            if category == 'stress':
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
            
            self.logger.info(f"Load test results saved to: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            return False
    
    def generate_summary(self, results: Dict[str, List]) -> Dict[str, Any]:
        """Generate summary statistics from load test results"""
        summary = {
            'total_tests': 0,
            'categories': {}
        }
        
        for category, test_results in results.items():
            category_summary = {
                'test_count': len(test_results),
                'avg_rps': 0,
                'max_rps': 0,
                'avg_error_rate': 0,
                'max_error_rate': 0,
                'avg_response_time': 0,
                'max_response_time': 0,
                'breaking_points': []
            }
            
            if test_results:
                if category == 'stress':
                    # Stress test results
                    rps_values = [r.max_sustained_rps for r in test_results]
                    error_rates = [((r.connection_errors + r.timeout_errors + r.system_errors) / 
                                 max(r.total_requests, 1)) * 100 for r in test_results]
                    response_times = [r.avg_response_time_stress for r in test_results]
                    breaking_points = [(r.breaking_point_users, r.breaking_point_rps) for r in test_results if r.breaking_point_users > 0]
                    
                    category_summary.update({
                        'avg_rps': statistics.mean(rps_values),
                        'max_rps': max(rps_values),
                        'avg_error_rate': statistics.mean(error_rates),
                        'max_error_rate': max(error_rates),
                        'avg_response_time': statistics.mean(response_times),
                        'max_response_time': max(response_times),
                        'breaking_points': breaking_points
                    })
                else:
                    # Load test results
                    rps_values = [r.requests_per_second for r in test_results]
                    error_rates = [r.error_rate for r in test_results]
                    response_times = [r.avg_response_time for r in test_results]
                    
                    category_summary.update({
                        'avg_rps': statistics.mean(rps_values),
                        'max_rps': max(rps_values),
                        'avg_error_rate': statistics.mean(error_rates),
                        'max_error_rate': max(error_rates),
                        'avg_response_time': statistics.mean(response_times),
                        'max_response_time': max(response_times)
                    })
            
            summary['categories'][category] = category_summary
            summary['total_tests'] += len(test_results)
        
        return summary


def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\nLoad tests interrupted by user")
    sys.exit(130)


def main():
    """Main load test execution"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(
        description="Load and Stress Tests for UNS-CLAUDEJP 5.4 Photo Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                                    # Run all load tests
    %(prog)s --config custom_config.json          # Use custom configuration
    %(prog)s --output results/                   # Save to specific directory
    %(prog)s --duration 120                      # Test duration in seconds
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
        default='load_test_results',
        help='Output directory for results (default: load_test_results)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Default test duration in seconds (default: 60)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_path = args.config
        config = load_config(config_path)
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("UNS-CLAUDEJP 5.4 - Load and Stress Tests")
        print("=" * 60)
        print(f"Output directory: {output_dir}")
        print(f"Default duration: {args.duration}s")
        print(f"Configuration: {config_path or 'default'}")
        print()
        
        # Run load tests
        test_suite = LoadTestSuite(config, output_dir)
        results = test_suite.run_all_load_tests()
        
        # Save results
        success = test_suite.save_results(results)
        
        if success:
            print("\nLoad and stress tests completed successfully!")
            print(f"Results saved to: {output_dir}")
            
            # Print summary
            summary = test_suite.generate_summary(results)
            print(f"\nSummary:")
            print(f"  Total tests: {summary['total_tests']}")
            
            for category, cat_summary in summary['categories'].items():
                print(f"\n{category.replace('_', ' ').title()}:")
                print(f"  Tests: {cat_summary['test_count']}")
                print(f"  Avg RPS: {cat_summary['avg_rps']:.1f}")
                print(f"  Max RPS: {cat_summary['max_rps']:.1f}")
                print(f"  Avg error rate: {cat_summary['avg_error_rate']:.1f}%")
                print(f"  Avg response time: {cat_summary['avg_response_time']*1000:.1f}ms")
                
                if cat_summary.get('breaking_points'):
                    print(f"  Breaking points: {cat_summary['breaking_points']}")
            
            return 0
        else:
            print("ERROR: Failed to save load test results")
            return 1
    
    except KeyboardInterrupt:
        print("\nLoad tests interrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)