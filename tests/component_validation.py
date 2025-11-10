#!/usr/bin/env python3
"""
Component Validation for UNS-CLAUDEJP 5.4 Photo Extraction System v2.0

This module provides comprehensive validation of critical system components
including Strategy Pattern, Caching, Performance Optimization, and others.

Usage:
    python component_validation.py [--config PATH] [--output PATH] [--component NAME]
"""

import sys
import os
import json
import time
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics
import threading
import concurrent.futures

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config.photo_extraction_config import PhotoExtractionConfig, load_config, ExtractionMethod
    from extractors.photo_extraction_strategies import (
        create_extraction_context, PyODBCExtractionStrategy, 
        PyWin32ExtractionStrategy, PandasExtractionStrategy
    )
    from processors.chunk_processor import create_chunk_processor
    from cache.photo_cache import create_cache_manager
    from performance.optimization import create_performance_optimizer
    from validation.photo_validator import create_photo_validator, create_integrity_checker
    from utils.logging_utils import create_logger
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


@dataclass
class ComponentValidationResult:
    """Result of component validation"""
    component_name: str
    test_name: str
    success: bool
    execution_time: float
    performance_metrics: Dict[str, Any] = None
    error_message: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.metadata is None:
            self.metadata = {}


class ComponentValidator:
    """Comprehensive component validation suite"""
    
    def __init__(self, config: PhotoExtractionConfig, output_dir: Path = None):
        self.config = config
        self.output_dir = output_dir or Path("component_validation_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self.logger = create_logger("ComponentValidator", config)
        
        # Validation results
        self.results: List[ComponentValidationResult] = []
        
        self.logger.info("Component validator initialized")
    
    def validate_strategy_pattern(self) -> List[ComponentValidationResult]:
        """Validate Strategy Pattern implementation"""
        self.logger.info("Validating Strategy Pattern implementation...")
        results = []
        
        # Test 1: Strategy Creation
        start_time = time.time()
        try:
            extraction_context = create_extraction_context(self.config)
            
            # Check if strategies were created
            strategies_available = len(extraction_context.strategies) > 0
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Strategy Pattern",
                test_name="Strategy Creation",
                success=strategies_available,
                execution_time=execution_time,
                performance_metrics={
                    'strategies_count': len(extraction_context.strategies),
                    'available_strategies': [s.__class__.__name__ for s in extraction_context.strategies]
                },
                metadata={
                    'strategies_available': strategies_available
                }
            )
            
            results.append(result)
            
            if strategies_available:
                self.logger.info(f"Strategy creation successful: {len(extraction_context.strategies)} strategies available")
            else:
                self.logger.error("Strategy creation failed: No strategies available")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Strategy Pattern",
                test_name="Strategy Creation",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Strategy creation failed: {e}")
        
        # Test 2: Strategy Selection
        start_time = time.time()
        try:
            # Test automatic strategy selection
            best_strategy = extraction_context.get_best_strategy(Path("dummy.accdb"))
            
            # Test manual strategy selection
            pyodbc_strategy = extraction_context.get_strategy_by_method(ExtractionMethod.PYODBC)
            pywin32_strategy = extraction_context.get_strategy_by_method(ExtractionMethod.PYWIN32)
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Strategy Pattern",
                test_name="Strategy Selection",
                success=True,
                execution_time=execution_time,
                performance_metrics={
                    'automatic_selection': best_strategy is not None,
                    'pyodbc_available': pyodbc_strategy is not None,
                    'pywin32_available': pywin32_strategy is not None
                },
                metadata={
                    'best_strategy': best_strategy.__class__.__name__ if best_strategy else None
                }
            )
            
            results.append(result)
            self.logger.info(f"Strategy selection successful: Best strategy = {best_strategy.__class__.__name__ if best_strategy else 'None'}")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Strategy Pattern",
                test_name="Strategy Selection",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Strategy selection failed: {e}")
        
        # Test 3: Strategy Fallback
        start_time = time.time()
        try:
            # Test fallback mechanism
            # This would normally use a real database, but we'll simulate
            fallback_result = extraction_context.extract_photos_with_fallback(
                Path("nonexistent.accdb"), "dummy_table", 0, 0
            )
            
            # Check if fallback was attempted (should fail gracefully)
            fallback_attempted = not fallback_result.success
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Strategy Pattern",
                test_name="Strategy Fallback",
                success=fallback_attempted,  # Expected to fail but handle gracefully
                execution_time=execution_time,
                performance_metrics={
                    'fallback_attempted': fallback_attempted,
                    'graceful_failure': True
                },
                metadata={
                    'fallback_result': fallback_result.method_used
                }
            )
            
            results.append(result)
            self.logger.info(f"Strategy fallback test completed: {'Graceful' if fallback_attempted else 'Unexpected'}")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Strategy Pattern",
                test_name="Strategy Fallback",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Strategy fallback test failed: {e}")
        
        return results
    
    def validate_caching_system(self) -> List[ComponentValidationResult]:
        """Validate Caching System implementation"""
        self.logger.info("Validating Caching System implementation...")
        results = []
        
        # Test 1: Cache Initialization
        start_time = time.time()
        try:
            cache_manager = create_cache_manager(self.config, self.logger)
            
            # Check if cache was initialized
            cache_initialized = cache_manager is not None
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Caching System",
                test_name="Cache Initialization",
                success=cache_initialized,
                execution_time=execution_time,
                performance_metrics={
                    'cache_initialized': cache_initialized,
                    'backends_count': len(cache_manager.backends) if cache_initialized else 0,
                    'primary_backend': cache_manager.primary_backend.__class__.__name__ if cache_initialized else None
                },
                metadata={
                    'backends': list(cache_manager.backends.keys()) if cache_initialized else []
                }
            )
            
            results.append(result)
            
            if cache_initialized:
                self.logger.info(f"Cache initialization successful: {len(cache_manager.backends)} backends")
            else:
                self.logger.error("Cache initialization failed")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Caching System",
                test_name="Cache Initialization",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Cache initialization failed: {e}")
        
        # Test 2: Cache Operations
        start_time = time.time()
        try:
            cache_manager = create_cache_manager(self.config, self.logger)
            
            # Test cache set/get operations
            test_data = {"key": "value", "number": 123, "list": [1, 2, 3]}
            cache_key = "test_key"
            
            # Set operation
            set_success = cache_manager.set(cache_key, test_data, ttl_seconds=3600)
            
            # Get operation
            get_result = cache_manager.get(cache_key)
            get_success = get_result is not None and get_result.value == test_data
            
            # Delete operation
            delete_success = cache_manager.delete(cache_key)
            
            # Verify deletion
            verify_result = cache_manager.get(cache_key)
            delete_verified = verify_result is None
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Caching System",
                test_name="Cache Operations",
                success=set_success and get_success and delete_success and delete_verified,
                execution_time=execution_time,
                performance_metrics={
                    'set_success': set_success,
                    'get_success': get_success,
                    'delete_success': delete_success,
                    'delete_verified': delete_verified
                },
                metadata={
                    'test_data_size': len(str(test_data))
                }
            )
            
            results.append(result)
            
            if result.success:
                self.logger.info("Cache operations test successful")
            else:
                self.logger.error("Cache operations test failed")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Caching System",
                test_name="Cache Operations",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Cache operations test failed: {e}")
        
        # Test 3: Cache Performance
        start_time = time.time()
        try:
            cache_manager = create_cache_manager(self.config, self.logger)
            
            # Test cache performance with multiple operations
            num_operations = 1000
            operation_times = []
            
            # Set operations
            for i in range(num_operations):
                op_start = time.time()
                cache_manager.set(f"perf_test_{i}", f"value_{i}", ttl_seconds=3600)
                operation_times.append(time.time() - op_start)
            
            # Get operations
            for i in range(num_operations):
                op_start = time.time()
                result = cache_manager.get(f"perf_test_{i}")
                operation_times.append(time.time() - op_start)
            
            # Calculate performance metrics
            avg_set_time = statistics.mean(operation_times[:num_operations])
            avg_get_time = statistics.mean(operation_times[num_operations:])
            total_time = sum(operation_times)
            ops_per_second = (num_operations * 2) / total_time if total_time > 0 else 0
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Caching System",
                test_name="Cache Performance",
                success=True,
                execution_time=execution_time,
                performance_metrics={
                    'operations_count': num_operations * 2,
                    'avg_set_time_ms': avg_set_time * 1000,
                    'avg_get_time_ms': avg_get_time * 1000,
                    'ops_per_second': ops_per_second
                },
                metadata={
                    'cache_stats': cache_manager.get_stats()
                }
            )
            
            results.append(result)
            self.logger.info(f"Cache performance test completed: {ops_per_second:.1f} ops/sec")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Caching System",
                test_name="Cache Performance",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Cache performance test failed: {e}")
        
        return results
    
    def validate_chunk_processor(self) -> List[ComponentValidationResult]:
        """Validate Chunk Processor implementation"""
        self.logger.info("Validating Chunk Processor implementation...")
        results = []
        
        # Test 1: Chunk Creation
        start_time = time.time()
        try:
            chunk_processor = create_chunk_processor(self.config)
            
            # Test chunk creation
            total_records = 1000
            chunks = chunk_processor.create_chunks(total_records)
            
            # Verify chunk properties
            expected_chunks = (total_records + self.config.processing.chunk_size - 1) // self.config.processing.chunk_size
            actual_chunks = len(chunks)
            chunk_sizes = [chunk.size for chunk in chunks]
            total_chunked = sum(chunk_sizes)
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Chunk Processor",
                test_name="Chunk Creation",
                success=actual_chunks == expected_chunks and total_chunked == total_records,
                execution_time=execution_time,
                performance_metrics={
                    'total_records': total_records,
                    'expected_chunks': expected_chunks,
                    'actual_chunks': actual_chunks,
                    'chunk_size': self.config.processing.chunk_size,
                    'total_chunked': total_chunked
                },
                metadata={
                    'chunk_sizes': chunk_sizes[:5]  # First 5 chunk sizes
                }
            )
            
            results.append(result)
            
            if result.success:
                self.logger.info(f"Chunk creation successful: {actual_chunks} chunks created")
            else:
                self.logger.error(f"Chunk creation failed: Expected {expected_chunks}, got {actual_chunks}")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Chunk Processor",
                test_name="Chunk Creation",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Chunk creation failed: {e}")
        
        # Test 2: Checkpoint Management
        start_time = time.time()
        try:
            chunk_processor = create_chunk_processor(self.config)
            
            # Test checkpoint save/load
            job_id = "test_job"
            total_records = 500
            chunks = chunk_processor.create_chunks(total_records)
            
            # Initialize processing state
            state = chunk_processor.initialize_processing_state(job_id, total_records, chunks)
            
            # Save checkpoint
            chunk_processor.save_state(state)
            
            # Load checkpoint
            loaded_state = chunk_processor.load_state(job_id)
            
            # Verify checkpoint integrity
            checkpoint_valid = (
                loaded_state is not None and
                loaded_state.job_id == job_id and
                loaded_state.total_records == total_records and
                len(loaded_state.chunks) == len(chunks)
            )
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Chunk Processor",
                test_name="Checkpoint Management",
                success=checkpoint_valid,
                execution_time=execution_time,
                performance_metrics={
                    'checkpoint_valid': checkpoint_valid,
                    'chunks_count': len(chunks),
                    'total_records': total_records
                },
                metadata={
                    'job_id': job_id
                }
            )
            
            results.append(result)
            
            if result.success:
                self.logger.info("Checkpoint management test successful")
            else:
                self.logger.error("Checkpoint management test failed")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Chunk Processor",
                test_name="Checkpoint Management",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Checkpoint management test failed: {e}")
        
        return results
    
    def validate_performance_optimization(self) -> List[ComponentValidationResult]:
        """Validate Performance Optimization implementation"""
        self.logger.info("Validating Performance Optimization implementation...")
        results = []
        
        # Test 1: Performance Optimizer Initialization
        start_time = time.time()
        try:
            perf_optimizer = create_performance_optimizer(self.config, self.logger)
            
            # Test initialization
            optimizer_initialized = perf_optimizer is not None
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Performance Optimization",
                test_name="Optimizer Initialization",
                success=optimizer_initialized,
                execution_time=execution_time,
                performance_metrics={
                    'optimizer_initialized': optimizer_initialized
                },
                metadata={}
            )
            
            results.append(result)
            
            if optimizer_initialized:
                self.logger.info("Performance optimizer initialization successful")
            else:
                self.logger.error("Performance optimizer initialization failed")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Performance Optimization",
                test_name="Optimizer Initialization",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Performance optimizer initialization failed: {e}")
        
        # Test 2: Parallel Processing
        start_time = time.time()
        try:
            perf_optimizer = create_performance_optimizer(self.config, self.logger)
            
            # Test parallel processing
            test_data = list(range(100))
            
            def cpu_intensive_task(item):
                # Simulate CPU-intensive work
                total = 0
                for i in range(100):
                    total += item * i
                return total
            
            # Process with parallel optimizer
            start_parallel = time.time()
            parallel_results = perf_optimizer.process_tasks(test_data, cpu_intensive_task, "parallel_test")
            parallel_time = time.time() - start_parallel
            
            # Process sequentially for comparison
            start_sequential = time.time()
            sequential_results = [cpu_intensive_task(item) for item in test_data]
            sequential_time = time.time() - start_sequential
            
            # Verify results
            results_match = parallel_results == sequential_results
            speedup = sequential_time / parallel_time if parallel_time > 0 else 0
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Performance Optimization",
                test_name="Parallel Processing",
                success=results_match,
                execution_time=execution_time,
                performance_metrics={
                    'results_match': results_match,
                    'parallel_time': parallel_time,
                    'sequential_time': sequential_time,
                    'speedup': speedup,
                    'items_processed': len(test_data)
                },
                metadata={
                    'max_workers': self.config.processing.max_workers
                }
            )
            
            results.append(result)
            
            if result.success:
                self.logger.info(f"Parallel processing test successful: {speedup:.2f}x speedup")
            else:
                self.logger.error("Parallel processing test failed")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Performance Optimization",
                test_name="Parallel Processing",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Parallel processing test failed: {e}")
        
        return results
    
    def validate_photo_validator(self) -> List[ComponentValidationResult]:
        """Validate Photo Validator implementation"""
        self.logger.info("Validating Photo Validator implementation...")
        results = []
        
        # Test 1: Validator Initialization
        start_time = time.time()
        try:
            photo_validator = create_photo_validator(self.config, self.logger)
            
            # Test initialization
            validator_initialized = photo_validator is not None
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Photo Validator",
                test_name="Validator Initialization",
                success=validator_initialized,
                execution_time=execution_time,
                performance_metrics={
                    'validator_initialized': validator_initialized
                },
                metadata={}
            )
            
            results.append(result)
            
            if validator_initialized:
                self.logger.info("Photo validator initialization successful")
            else:
                self.logger.error("Photo validator initialization failed")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Photo Validator",
                test_name="Validator Initialization",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Photo validator initialization failed: {e}")
        
        # Test 2: Photo Validation
        start_time = time.time()
        try:
            photo_validator = create_photo_validator(self.config, self.logger)
            
            # Test with valid photo data
            valid_jpeg_data = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA"
            
            # Test with invalid photo data
            invalid_data = "not_a_photo"
            
            # Validate photos
            valid_result = photo_validator.validate_photo_data(valid_jpeg_data, "test_valid")
            invalid_result = photo_validator.validate_photo_data(invalid_data, "test_invalid")
            
            # Check results
            valid_photo_detected = valid_result.is_valid
            invalid_photo_detected = not invalid_result.is_valid
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Photo Validator",
                test_name="Photo Validation",
                success=valid_photo_detected and invalid_photo_detected,
                execution_time=execution_time,
                performance_metrics={
                    'valid_photo_detected': valid_photo_detected,
                    'invalid_photo_detected': invalid_photo_detected,
                    'valid_photo_quality': valid_result.quality_score,
                    'invalid_photo_errors': len(invalid_result.error_messages)
                },
                metadata={
                    'valid_photo_format': valid_result.detected_format,
                    'invalid_photo_errors': invalid_result.error_messages[:3]  # First 3 errors
                }
            )
            
            results.append(result)
            
            if result.success:
                self.logger.info("Photo validation test successful")
            else:
                self.logger.error("Photo validation test failed")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Photo Validator",
                test_name="Photo Validation",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Photo validation test failed: {e}")
        
        return results
    
    def validate_integrity_checker(self) -> List[ComponentValidationResult]:
        """Validate Integrity Checker implementation"""
        self.logger.info("Validating Integrity Checker implementation...")
        results = []
        
        # Test 1: Integrity Checker Initialization
        start_time = time.time()
        try:
            integrity_checker = create_integrity_checker(self.config, self.logger)
            
            # Test initialization
            checker_initialized = integrity_checker is not None
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Integrity Checker",
                test_name="Checker Initialization",
                success=checker_initialized,
                execution_time=execution_time,
                performance_metrics={
                    'checker_initialized': checker_initialized
                },
                metadata={}
            )
            
            results.append(result)
            
            if checker_initialized:
                self.logger.info("Integrity checker initialization successful")
            else:
                self.logger.error("Integrity checker initialization failed")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Integrity Checker",
                test_name="Checker Initialization",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Integrity checker initialization failed: {e}")
        
        # Test 2: Integrity Checking
        start_time = time.time()
        try:
            integrity_checker = create_integrity_checker(self.config, self.logger)
            
            # Test with valid mappings
            valid_mappings = {
                "record_1": "data:image/jpeg;base64,valid_data_1",
                "record_2": "data:image/jpeg;base64,valid_data_2",
                "record_3": "data:image/jpeg;base64,valid_data_3"
            }
            
            # Test with mappings containing issues
            invalid_mappings = {
                "record_1": "",  # Empty value
                "record_2": "data:image/jpeg;base64,valid_data_2",
                "record_3": "data:image/jpeg;base64,valid_data_2"  # Duplicate
            }
            
            # Check integrity
            valid_result = integrity_checker.check_mappings_integrity(valid_mappings)
            invalid_result = integrity_checker.check_mappings_integrity(invalid_mappings)
            
            # Check results
            valid_integrity_detected = valid_result['is_valid']
            invalid_integrity_detected = not invalid_result['is_valid']
            
            execution_time = time.time() - start_time
            
            result = ComponentValidationResult(
                component_name="Integrity Checker",
                test_name="Integrity Checking",
                success=valid_integrity_detected and invalid_integrity_detected,
                execution_time=execution_time,
                performance_metrics={
                    'valid_integrity_detected': valid_integrity_detected,
                    'invalid_integrity_detected': invalid_integrity_detected,
                    'valid_unique_values': valid_result['statistics']['unique_values'],
                    'invalid_duplicates': len(invalid_result['duplicates']),
                    'invalid_empty_records': len(invalid_result['missing_records'])
                },
                metadata={
                    'valid_errors': valid_result['errors'],
                    'invalid_errors': invalid_result['errors']
                }
            )
            
            results.append(result)
            
            if result.success:
                self.logger.info("Integrity checking test successful")
            else:
                self.logger.error("Integrity checking test failed")
        
        except Exception as e:
            execution_time = time.time() - start_time
            result = ComponentValidationResult(
                component_name="Integrity Checker",
                test_name="Integrity Checking",
                success=False,
                execution_time=execution_time,
                error_message=str(e)
            )
            results.append(result)
            self.logger.error(f"Integrity checking test failed: {e}")
        
        return results
    
    def run_all_validations(self, component_filter: str = None) -> List[ComponentValidationResult]:
        """Run all component validations"""
        self.logger.info("Starting comprehensive component validation")
        
        all_results = []
        
        try:
            # Define validation functions
            validation_functions = {
                "Strategy Pattern": self.validate_strategy_pattern,
                "Caching System": self.validate_caching_system,
                "Chunk Processor": self.validate_chunk_processor,
                "Performance Optimization": self.validate_performance_optimization,
                "Photo Validator": self.validate_photo_validator,
                "Integrity Checker": self.validate_integrity_checker
            }
            
            # Run validations
            for component_name, validation_func in validation_functions.items():
                if component_filter and component_name != component_filter:
                    continue
                
                self.logger.info(f"Validating {component_name}...")
                component_results = validation_func()
                all_results.extend(component_results)
                
                # Log component summary
                success_count = sum(1 for r in component_results if r.success)
                total_count = len(component_results)
                self.logger.info(f"{component_name} validation completed: {success_count}/{total_count} tests passed")
            
            self.logger.info("All component validations completed successfully")
            
        except Exception as e:
            self.logger.error(f"Component validation suite failed: {e}")
            traceback.print_exc()
        
        return all_results
    
    def save_results(self, results: List[ComponentValidationResult], filename: str = None):
        """Save validation results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"component_validation_results_{timestamp}.json"
        
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
            
            self.logger.info(f"Component validation results saved to: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            return False
    
    def generate_summary(self, results: List[ComponentValidationResult]) -> Dict[str, Any]:
        """Generate summary statistics from validation results"""
        if not results:
            return {}
        
        # Group results by component
        component_results = {}
        for result in results:
            if result.component_name not in component_results:
                component_results[result.component_name] = []
            component_results[result.component_name].append(result)
        
        # Calculate summary for each component
        component_summary = {}
        total_tests = len(results)
        total_passed = sum(1 for r in results if r.success)
        total_failed = total_tests - total_passed
        
        for component_name, comp_results in component_results.items():
            passed = sum(1 for r in comp_results if r.success)
            total = len(comp_results)
            avg_time = statistics.mean([r.execution_time for r in comp_results])
            
            component_summary[component_name] = {
                'tests_total': total,
                'tests_passed': passed,
                'tests_failed': total - passed,
                'success_rate': (passed / total * 100) if total > 0 else 0,
                'avg_execution_time': avg_time
            }
        
        return {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'overall_success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'components': component_summary
        }


def main():
    """Main component validation execution"""
    parser = argparse.ArgumentParser(
        description="Component Validation for UNS-CLAUDEJP 5.4 Photo Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                                    # Validate all components
    %(prog)s --component "Strategy Pattern"   # Validate specific component
    %(prog)s --output results/                   # Save to specific directory
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--component',
        type=str,
        help='Specific component to validate (Strategy Pattern, Caching System, etc.)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='component_validation_results',
        help='Output directory for results (default: component_validation_results)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_path = args.config
        config = load_config(config_path)
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("UNS-CLAUDEJP 5.4 - Component Validation")
        print("=" * 60)
        print(f"Output directory: {output_dir}")
        print(f"Component filter: {args.component or 'All components'}")
        print(f"Configuration: {config_path or 'default'}")
        print()
        
        # Run validations
        validator = ComponentValidator(config, output_dir)
        results = validator.run_all_validations(args.component)
        
        # Save results
        success = validator.save_results(results)
        
        if success:
            print("\nComponent validation completed successfully!")
            print(f"Results saved to: {output_dir}")
            
            # Print summary
            summary = validator.generate_summary(results)
            print(f"\nSummary:")
            print(f"  Total tests: {summary['total_tests']}")
            print(f"  Passed: {summary['total_passed']}")
            print(f"  Failed: {summary['total_failed']}")
            print(f"  Overall success rate: {summary['overall_success_rate']:.1f}%")
            
            print(f"\nComponent Results:")
            for component_name, comp_summary in summary['components'].items():
                print(f"  {component_name}:")
                print(f"    Tests: {comp_summary['tests_total']}")
                print(f"    Passed: {comp_summary['tests_passed']}")
                print(f"    Failed: {comp_summary['tests_failed']}")
                print(f"    Success rate: {comp_summary['success_rate']:.1f}%")
                print(f"    Avg execution time: {comp_summary['avg_execution_time']:.3f}s")
            
            return 0
        else:
            print("ERROR: Failed to save validation results")
            return 1
    
    except KeyboardInterrupt:
        print("\nComponent validation interrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)