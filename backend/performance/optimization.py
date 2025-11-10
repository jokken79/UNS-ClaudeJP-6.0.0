"""
Performance Optimization Module
UNS-CLAUDEJP 5.4 - Advanced Photo Extraction System

This module provides performance optimization features including connection pooling,
parallel processing, memory optimization, and resource management.
"""

import threading
import time
import queue
import multiprocessing
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Callable, Iterator, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import psutil
import gc

from ..config.photo_extraction_config import PhotoExtractionConfig
from ..utils.logging_utils import PhotoExtractionLogger, PerformanceMetrics


@dataclass
class ResourceUsage:
    """Resource usage statistics"""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    open_files: int
    threads: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkerStats:
    """Worker statistics"""
    worker_id: int
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    avg_processing_time: float = 0.0
    memory_peak_mb: float = 0.0
    last_activity: Optional[datetime] = None


class ConnectionPool:
    """Generic connection pool with automatic cleanup"""
    
    def __init__(self, create_connection: Callable, max_connections: int = 5,
                 connection_timeout: float = 30.0, max_idle_time: float = 300.0):
        self.create_connection = create_connection
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.max_idle_time = max_idle_time
        
        self._pool = queue.Queue(maxsize=max_connections)
        self._active_connections = {}
        self._connection_stats = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        connection_id = None
        connection = None
        
        try:
            # Try to get existing connection
            try:
                connection_id, connection, created_time = self._pool.get(timeout=self.connection_timeout)
                
                # Check if connection is still valid and not too old
                if self._is_connection_valid(connection) and \
                   (time.time() - created_time) < self.max_idle_time:
                    with self._lock:
                        self._active_connections[connection_id] = (connection, time.time())
                    yield connection
                    return
                else:
                    # Connection is invalid or too old, discard it
                    self._close_connection(connection)
            
            except queue.Empty:
                pass
            
            # Create new connection if pool is not full
            if len(self._active_connections) < self.max_connections:
                connection = self.create_connection()
                connection_id = id(connection)
                
                with self._lock:
                    self._active_connections[connection_id] = (connection, time.time())
                    self._connection_stats[connection_id] = {
                        'created_at': time.time(),
                        'used_count': 0,
                        'last_used': time.time()
                    }
                
                yield connection
                return
            
            # Pool is full, wait for available connection
            connection_id, connection, created_time = self._pool.get(timeout=self.connection_timeout)
            
            with self._lock:
                self._active_connections[connection_id] = (connection, time.time())
                self._connection_stats[connection_id]['used_count'] += 1
                self._connection_stats[connection_id]['last_used'] = time.time()
            
            yield connection
        
        finally:
            # Return connection to pool
            if connection_id is not None and connection is not None:
                try:
                    with self._lock:
                        if connection_id in self._active_connections:
                            del self._active_connections[connection_id]
                    
                    self._pool.put((connection_id, connection, time.time()), timeout=5.0)
                except queue.Full:
                    # Pool is full, close connection
                    self._close_connection(connection)
                except Exception as e:
                    # Error returning connection to pool
                    self._close_connection(connection)
    
    def _is_connection_valid(self, connection) -> bool:
        """Check if connection is still valid"""
        try:
            # This should be implemented based on connection type
            # For database connections, try a simple query
            if hasattr(connection, 'execute'):
                connection.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def _close_connection(self, connection):
        """Close connection"""
        try:
            if hasattr(connection, 'close'):
                connection.close()
        except Exception:
            pass
    
    def cleanup_idle_connections(self):
        """Clean up idle connections"""
        current_time = time.time()
        
        if current_time - self._last_cleanup < 60:  # Cleanup every minute
            return
        
        with self._lock:
            # Remove idle connections from active list
            idle_connections = []
            for connection_id, (conn, last_used) in self._active_connections.items():
                if current_time - last_used > self.max_idle_time:
                    idle_connections.append((connection_id, conn))
            
            for connection_id, conn in idle_connections:
                del self._active_connections[connection_id]
                self._close_connection(conn)
        
        self._last_cleanup = current_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            return {
                'pool_size': self._pool.qsize(),
                'active_connections': len(self._active_connections),
                'max_connections': self.max_connections,
                'total_created': len(self._connection_stats),
                'connection_stats': self._connection_stats.copy()
            }


class ParallelProcessor:
    """Advanced parallel processing with resource management"""
    
    def __init__(self, config: PhotoExtractionConfig, logger: PhotoExtractionLogger):
        self.config = config
        self.logger = logger
        self.max_workers = config.processing.max_workers
        self.memory_limit_mb = config.processing.memory_limit_mb
        
        self._worker_stats = {}
        self._resource_monitor = ResourceMonitor(logger)
        self._shutdown_event = threading.Event()
    
    def process_tasks_parallel(self, tasks: List[Any], process_func: Callable,
                             task_type: str = "general") -> List[Any]:
        """Process tasks in parallel with resource management"""
        if not tasks:
            return []
        
        # Choose execution strategy based on task type and configuration
        if self.config.processing.enable_parallel_processing and len(tasks) > 1:
            return self._process_with_thread_pool(tasks, process_func, task_type)
        else:
            return self._process_sequential(tasks, process_func, task_type)
    
    def _process_with_thread_pool(self, tasks: List[Any], process_func: Callable,
                                task_type: str) -> List[Any]:
        """Process tasks using thread pool"""
        results = []
        completed_tasks = 0
        
        # Adjust worker count based on system resources
        optimal_workers = self._calculate_optimal_workers()
        
        self.logger.info(f"Processing {len(tasks)} {task_type} tasks with {optimal_workers} workers")
        
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._wrap_task_function, process_func, task, i): i
                for i, task in enumerate(tasks)
            }
            
            # Process completed tasks
            for future in as_completed(future_to_task):
                task_index = future_to_task[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    completed_tasks += 1
                    
                    # Log progress
                    if completed_tasks % max(1, len(tasks) // 10) == 0:
                        progress_pct = (completed_tasks / len(tasks)) * 100
                        self.logger.info(f"Progress: {completed_tasks}/{len(tasks)} ({progress_pct:.1f}%)")
                
                except Exception as e:
                    self.logger.error(f"Task {task_index} failed: {e}")
                    results.append(None)
        
        # Sort results by original task order
        sorted_results = [None] * len(tasks)
        for i, result in enumerate(results):
            if result is not None:
                task_index = result.get('task_index', i)
                if 0 <= task_index < len(sorted_results):
                    sorted_results[task_index] = result
        
        return sorted_results
    
    def _process_sequential(self, tasks: List[Any], process_func: Callable,
                          task_type: str) -> List[Any]:
        """Process tasks sequentially"""
        results = []
        
        self.logger.info(f"Processing {len(tasks)} {task_type} tasks sequentially")
        
        for i, task in enumerate(tasks):
            try:
                result = self._wrap_task_function(process_func, task, i)
                results.append(result)
                
                # Log progress
                if (i + 1) % max(1, len(tasks) // 10) == 0:
                    progress_pct = ((i + 1) / len(tasks)) * 100
                    self.logger.info(f"Progress: {i + 1}/{len(tasks)} ({progress_pct:.1f}%)")
            
            except Exception as e:
                self.logger.error(f"Task {i} failed: {e}")
                results.append(None)
        
        return results
    
    def _wrap_task_function(self, process_func: Callable, task: Any, task_index: int) -> Dict[str, Any]:
        """Wrap task function with monitoring and error handling"""
        start_time = time.time()
        worker_id = threading.get_ident()
        
        # Initialize worker stats if not exists
        if worker_id not in self._worker_stats:
            self._worker_stats[worker_id] = WorkerStats(worker_id=worker_id)
        
        stats = self._worker_stats[worker_id]
        
        try:
            # Monitor memory before task
            memory_before = self._get_memory_usage()
            
            # Execute task
            result = process_func(task)
            
            # Monitor memory after task
            memory_after = self._get_memory_usage()
            memory_peak = max(memory_before, memory_after)
            
            # Update worker stats
            processing_time = time.time() - start_time
            stats.tasks_completed += 1
            stats.total_processing_time += processing_time
            stats.avg_processing_time = stats.total_processing_time / stats.tasks_completed
            stats.memory_peak_mb = max(stats.memory_peak_mb, memory_peak)
            stats.last_activity = datetime.now()
            
            return {
                'result': result,
                'task_index': task_index,
                'worker_id': worker_id,
                'processing_time': processing_time,
                'memory_peak_mb': memory_peak,
                'success': True
            }
        
        except Exception as e:
            # Update worker stats
            stats.tasks_failed += 1
            stats.last_activity = datetime.now()
            
            return {
                'result': None,
                'task_index': task_index,
                'worker_id': worker_id,
                'processing_time': time.time() - start_time,
                'error': str(e),
                'success': False
            }
    
    def _calculate_optimal_workers(self) -> int:
        """Calculate optimal number of workers based on system resources"""
        cpu_count = multiprocessing.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Base calculation on CPU cores
        optimal_workers = cpu_count
        
        # Adjust based on memory constraints
        if self.memory_limit_mb > 0:
            # Estimate memory per worker (conservative estimate)
            memory_per_worker = 100  # MB
            max_workers_by_memory = (memory_gb * 1024) // memory_per_worker
            optimal_workers = min(optimal_workers, max_workers_by_memory)
        
        # Consider task type and configuration
        optimal_workers = min(optimal_workers, self.max_workers)
        
        # Ensure at least 1 worker
        return max(1, optimal_workers)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        total_completed = sum(stats.tasks_completed for stats in self._worker_stats.values())
        total_failed = sum(stats.tasks_failed for stats in self._worker_stats.values())
        total_processing_time = sum(stats.total_processing_time for stats in self._worker_stats.values())
        
        return {
            'total_workers': len(self._worker_stats),
            'total_tasks_completed': total_completed,
            'total_tasks_failed': total_failed,
            'total_processing_time': total_processing_time,
            'success_rate': total_completed / max(total_completed + total_failed, 1),
            'avg_processing_time': total_processing_time / max(total_completed, 1),
            'worker_details': {
                str(worker_id): {
                    'tasks_completed': stats.tasks_completed,
                    'tasks_failed': stats.tasks_failed,
                    'avg_processing_time': stats.avg_processing_time,
                    'memory_peak_mb': stats.memory_peak_mb,
                    'last_activity': stats.last_activity.isoformat() if stats.last_activity else None
                }
                for worker_id, stats in self._worker_stats.items()
            }
        }


class ResourceMonitor:
    """System resource monitoring"""
    
    def __init__(self, logger: PhotoExtractionLogger, check_interval: float = 5.0):
        self.logger = logger
        self.check_interval = check_interval
        self._monitoring = False
        self._monitor_thread = None
        self._resource_history = []
        self._max_history_size = 1000
        self._lock = threading.Lock()
    
    def start_monitoring(self):
        """Start resource monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10.0)
        self.logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self):
        """Resource monitoring loop"""
        while self._monitoring:
            try:
                usage = self._get_current_usage()
                
                with self._lock:
                    self._resource_history.append(usage)
                    
                    # Keep only recent history
                    if len(self._resource_history) > self._max_history_size:
                        self._resource_history = self._resource_history[-self._max_history_size:]
                
                # Check for resource warnings
                self._check_resource_warnings(usage)
                
                time.sleep(self.check_interval)
            
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                time.sleep(self.check_interval)
    
    def _get_current_usage(self) -> ResourceUsage:
        """Get current system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1.0)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_io_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
            disk_io_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0
            
            # Network I/O
            network_io = psutil.net_io_counters()
            network_io_sent_mb = network_io.bytes_sent / (1024 * 1024) if network_io else 0
            network_io_recv_mb = network_io.bytes_recv / (1024 * 1024) if network_io else 0
            
            # Process-specific info
            process = psutil.Process()
            open_files = len(process.open_files())
            threads = process.num_threads()
            
            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_io_read_mb=disk_io_read_mb,
                disk_io_write_mb=disk_io_write_mb,
                network_io_sent_mb=network_io_sent_mb,
                network_io_recv_mb=network_io_recv_mb,
                open_files=open_files,
                threads=threads
            )
        
        except Exception as e:
            self.logger.error(f"Error getting resource usage: {e}")
            return ResourceUsage(
                cpu_percent=0.0, memory_mb=0.0, memory_percent=0.0,
                disk_io_read_mb=0.0, disk_io_write_mb=0.0,
                network_io_sent_mb=0.0, network_io_recv_mb=0.0,
                open_files=0, threads=0
            )
    
    def _check_resource_warnings(self, usage: ResourceUsage):
        """Check for resource warnings"""
        # CPU warning
        if usage.cpu_percent > 90:
            self.logger.warning(f"High CPU usage: {usage.cpu_percent:.1f}%")
        
        # Memory warning
        if usage.memory_percent > 90:
            self.logger.warning(f"High memory usage: {usage.memory_percent:.1f}% ({usage.memory_mb:.1f} MB)")
        
        # Thread warning
        if usage.threads > 100:
            self.logger.warning(f"High thread count: {usage.threads}")
    
    def get_current_usage(self) -> Optional[ResourceUsage]:
        """Get most recent resource usage"""
        with self._lock:
            return self._resource_history[-1] if self._resource_history else None
    
    def get_resource_history(self, limit: Optional[int] = None) -> List[ResourceUsage]:
        """Get resource usage history"""
        with self._lock:
            if limit:
                return self._resource_history[-limit:]
            return self._resource_history.copy()
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get resource usage summary"""
        with self._lock:
            if not self._resource_history:
                return {}
            
            recent_usage = self._resource_history[-10:]  # Last 10 measurements
            
            avg_cpu = sum(u.cpu_percent for u in recent_usage) / len(recent_usage)
            avg_memory = sum(u.memory_percent for u in recent_usage) / len(recent_usage)
            max_memory = max(u.memory_mb for u in recent_usage)
            
            return {
                'current': self._resource_history[-1].__dict__,
                'averages': {
                    'cpu_percent': avg_cpu,
                    'memory_percent': avg_memory,
                    'memory_mb': max_memory
                },
                'samples_count': len(self._resource_history),
                'monitoring_active': self._monitoring
            }


class MemoryOptimizer:
    """Memory optimization utilities"""
    
    def __init__(self, logger: PhotoExtractionLogger, memory_limit_mb: int = 1024):
        self.logger = logger
        self.memory_limit_mb = memory_limit_mb
        self._cleanup_callbacks = []
    
    def register_cleanup_callback(self, callback: Callable[[], None]):
        """Register cleanup callback"""
        self._cleanup_callbacks.append(callback)
    
    def check_memory_usage(self) -> float:
        """Check current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    def optimize_memory(self, force: bool = False) -> bool:
        """Optimize memory usage"""
        current_memory = self.check_memory_usage()
        
        if not force and current_memory < self.memory_limit_mb:
            return False
        
        self.logger.info(f"Memory optimization triggered: {current_memory:.1f} MB used (limit: {self.memory_limit_mb} MB)")
        
        # Run cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Error in cleanup callback: {e}")
        
        # Force garbage collection
        gc.collect()
        
        # Check memory after optimization
        new_memory = self.check_memory_usage()
        freed_memory = current_memory - new_memory
        
        self.logger.info(f"Memory optimization completed: {freed_memory:.1f} MB freed ({new_memory:.1f} MB total)")
        
        return freed_memory > 0
    
    def auto_optimize_if_needed(self) -> bool:
        """Auto-optimize if memory usage is high"""
        current_memory = self.check_memory_usage()
        
        if current_memory > self.memory_limit_mb * 0.8:  # 80% threshold
            return self.optimize_memory()
        
        return False


class PerformanceOptimizer:
    """Main performance optimization coordinator"""
    
    def __init__(self, config: PhotoExtractionConfig, logger: PhotoExtractionLogger):
        self.config = config
        self.logger = logger
        
        # Initialize components
        self.parallel_processor = ParallelProcessor(config, logger)
        self.resource_monitor = ResourceMonitor(logger)
        self.memory_optimizer = MemoryOptimizer(logger, config.processing.memory_limit_mb)
        
        # Connection pools
        self._connection_pools = {}
        
        # Performance metrics
        self._performance_metrics = []
    
    def start_optimization(self):
        """Start performance optimization"""
        if self.config.performance.enable_connection_pooling or \
           self.config.processing.enable_parallel_processing:
            self.resource_monitor.start_monitoring()
            self.logger.info("Performance optimization started")
    
    def stop_optimization(self):
        """Stop performance optimization"""
        self.resource_monitor.stop_monitoring()
        
        # Close all connection pools
        for pool in self._connection_pools.values():
            pool.cleanup_idle_connections()
        
        self.logger.info("Performance optimization stopped")
    
    def get_connection_pool(self, pool_name: str, create_connection: Callable,
                           max_connections: Optional[int] = None) -> ConnectionPool:
        """Get or create connection pool"""
        if pool_name not in self._connection_pools:
            max_conn = max_connections or self.config.database.max_connections
            self._connection_pools[pool_name] = ConnectionPool(
                create_connection=create_connection,
                max_connections=max_conn,
                connection_timeout=self.config.database.connection_timeout
            )
        
        return self._connection_pools[pool_name]
    
    def process_tasks(self, tasks: List[Any], process_func: Callable,
                     task_type: str = "general") -> List[Any]:
        """Process tasks with optimal strategy"""
        # Auto-optimize memory if needed
        self.memory_optimizer.auto_optimize_if_needed()
        
        # Process tasks
        results = self.parallel_processor.process_tasks_parallel(tasks, process_func, task_type)
        
        # Clean up if needed
        self.memory_optimizer.auto_optimize_if_needed()
        
        return results
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            'resource_usage': self.resource_monitor.get_resource_summary(),
            'worker_stats': self.parallel_processor.get_worker_stats(),
            'connection_pools': {
                name: pool.get_stats() for name, pool in self._connection_pools.items()
            },
            'memory_usage_mb': self.memory_optimizer.check_memory_usage(),
            'memory_limit_mb': self.memory_optimizer.memory_limit_mb
        }


def create_performance_optimizer(config: PhotoExtractionConfig, 
                            logger: PhotoExtractionLogger) -> PerformanceOptimizer:
    """Factory function to create performance optimizer"""
    return PerformanceOptimizer(config, logger)