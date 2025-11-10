"""
Advanced Logging and Error Handling Utilities
UNS-CLAUDEJP 5.4 - Advanced Photo Extraction System

This module provides structured logging with Unicode support,
error handling with retry mechanisms, and performance monitoring.
"""

import logging
import logging.handlers
import sys
import time
import traceback
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Union, Type
from dataclasses import dataclass, field
from contextlib import contextmanager
from functools import wraps
import json
import hashlib

from ..config.photo_extraction_config import PhotoExtractionConfig, LogLevel


@dataclass
class ErrorContext:
    """Context information for errors"""
    operation: str
    component: str
    record_id: Optional[str] = None
    chunk_id: Optional[int] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations"""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    records_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    memory_usage_mb: Optional[float] = None
    additional_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, records_processed: int = 0, success_count: int = 0, 
               error_count: int = 0, memory_usage_mb: Optional[float] = None,
               additional_metrics: Optional[Dict[str, Any]] = None):
        """Finish the operation and calculate duration"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.records_processed = records_processed
        self.success_count = success_count
        self.error_count = error_count
        self.memory_usage_mb = memory_usage_mb
        if additional_metrics:
            self.additional_metrics.update(additional_metrics)


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter with Unicode support"""
    
    def __init__(self, include_extra_fields: bool = True):
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if self.include_extra_fields and hasattr(record, '__dict__'):
            extra_fields = {k: v for k, v in record.__dict__.items() 
                          if k not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                                     'pathname', 'filename', 'module', 'lineno', 
                                     'funcName', 'created', 'msecs', 'relativeCreated', 
                                     'thread', 'threadName', 'processName', 'process',
                                     'getMessage', 'exc_info', 'exc_text', 'stack_info']}
            if extra_fields:
                log_data['extra'] = extra_fields
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class UnicodeSafeFormatter(logging.Formatter):
    """Unicode-safe formatter for console output"""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        if fmt is None:
            fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        if datefmt is None:
            datefmt = '%Y-%m-%d %H:%M:%S'
        super().__init__(fmt, datefmt)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format with Unicode safety"""
        try:
            message = super().format(record)
            # Ensure Unicode compatibility
            if isinstance(message, bytes):
                message = message.decode('utf-8', errors='replace')
            return message
        except Exception as e:
            return f"LOGGING ERROR: {e} - Original message: {record.getMessage()}"


class PhotoExtractionLogger:
    """Advanced logger for photo extraction operations"""
    
    def __init__(self, name: str, config: PhotoExtractionConfig):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(name)
        self._setup_logger()
        self._performance_metrics: List[PerformanceMetrics] = []
        self._lock = threading.Lock()
    
    def _setup_logger(self):
        """Setup logger with handlers"""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set log level
        level = getattr(logging, self.config.logging.level.value)
        self.logger.setLevel(level)
        
        # Console handler
        if self.config.logging.enable_console_logging:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            
            if self.config.logging.enable_unicode_support:
                console_formatter = UnicodeSafeFormatter()
            else:
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # File handler with rotation
        if self.config.logging.enable_file_logging:
            log_dir = Path(self.config.logging.log_file_path)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f"photo_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            
            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.config.logging.log_rotation_mb * 1024 * 1024,
                backupCount=self.config.logging.log_backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            
            # Use structured formatter for file logs
            if self.config.logging.enable_performance_logging:
                file_formatter = StructuredFormatter()
            else:
                file_formatter = UnicodeSafeFormatter()
            
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def debug(self, message: str, **kwargs):
        """Log debug message with extra context"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with extra context"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with extra context"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with extra context"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with extra context"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with extra context"""
        extra = {}
        
        # Add structured context
        if 'operation' in kwargs:
            extra['operation'] = kwargs['operation']
        if 'component' in kwargs:
            extra['component'] = kwargs['component']
        if 'record_id' in kwargs:
            extra['record_id'] = kwargs['record_id']
        if 'chunk_id' in kwargs:
            extra['chunk_id'] = kwargs['chunk_id']
        
        # Add performance metrics if available
        if 'performance' in kwargs:
            extra['performance'] = kwargs['performance']
        
        # Log with extra context
        self.logger.log(level, message, extra=extra)
    
    def log_operation_start(self, operation: str, component: str, **kwargs):
        """Log the start of an operation"""
        self.info(f"Starting operation: {operation}", 
                 operation=operation, component=component, **kwargs)
    
    def log_operation_success(self, operation: str, component: str, 
                           metrics: PerformanceMetrics, **kwargs):
        """Log successful operation completion"""
        self.info(f"Operation completed successfully: {operation} "
                 f"(duration: {metrics.duration:.2f}s, "
                 f"records: {metrics.records_processed:,})",
                 operation=operation, component=component, 
                 performance=metrics.__dict__, **kwargs)
    
    def log_operation_error(self, operation: str, component: str, 
                          error: Exception, context: Optional[ErrorContext] = None, **kwargs):
        """Log operation error with context"""
        error_data = {
            'type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc()
        }
        
        if context:
            error_data['context'] = context.__dict__
        
        self.error(f"Operation failed: {operation} - {error}",
                  operation=operation, component=component,
                  error=error_data, **kwargs)
    
    def start_performance_tracking(self, operation: str) -> PerformanceMetrics:
        """Start tracking performance for an operation"""
        metrics = PerformanceMetrics(operation=operation, start_time=time.time())
        
        with self._lock:
            self._performance_metrics.append(metrics)
        
        return metrics
    
    def finish_performance_tracking(self, metrics: PerformanceMetrics, **kwargs):
        """Finish performance tracking"""
        metrics.finish(**kwargs)
        
        if self.config.logging.enable_performance_logging:
            self.info(f"Performance: {metrics.operation} - "
                     f"duration: {metrics.duration:.2f}s, "
                     f"records: {metrics.records_processed:,}, "
                     f"success_rate: {(metrics.success_count / max(metrics.records_processed, 1)) * 100:.1f}%",
                     operation=metrics.operation, component="performance",
                     performance=metrics.__dict__)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all performance metrics"""
        with self._lock:
            if not self._performance_metrics:
                return {}
            
            total_duration = sum(m.duration or 0 for m in self._performance_metrics)
            total_records = sum(m.records_processed for m in self._performance_metrics)
            total_successes = sum(m.success_count for m in self._performance_metrics)
            total_errors = sum(m.error_count for m in self._performance_metrics)
            
            operations = {}
            for metrics in self._performance_metrics:
                if metrics.operation not in operations:
                    operations[metrics.operation] = {
                        'count': 0,
                        'total_duration': 0,
                        'total_records': 0,
                        'total_successes': 0,
                        'total_errors': 0
                    }
                
                ops = operations[metrics.operation]
                ops['count'] += 1
                ops['total_duration'] += metrics.duration or 0
                ops['total_records'] += metrics.records_processed
                ops['total_successes'] += metrics.success_count
                ops['total_errors'] += metrics.error_count
            
            return {
                'summary': {
                    'total_operations': len(self._performance_metrics),
                    'total_duration': total_duration,
                    'total_records': total_records,
                    'total_successes': total_successes,
                    'total_errors': total_errors,
                    'overall_success_rate': (total_successes / max(total_records, 1)) * 100
                },
                'by_operation': operations
            }


class RetryHandler:
    """Advanced retry handler with exponential backoff"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt"""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add random jitter to avoid thundering herd
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def retry(self, exceptions: Union[Type[Exception], tuple] = Exception,
              on_retry: Optional[Callable[[int, Exception], None]] = None):
        """Decorator for retry logic"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(1, self.max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == self.max_attempts:
                            # Last attempt, re-raise the exception
                            raise e
                        
                        delay = self.calculate_delay(attempt)
                        
                        if on_retry:
                            on_retry(attempt, e)
                        
                        time.sleep(delay)
                
                # This should never be reached
                raise last_exception
            
            return wrapper
        return decorator
    
    @contextmanager
    def retry_context(self, operation: str, logger: PhotoExtractionLogger):
        """Context manager for retry operations"""
        attempt = 0
        last_exception = None
        
        while attempt < self.max_attempts:
            attempt += 1
            try:
                yield
                return
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_attempts:
                    logger.error(f"Operation '{operation}' failed after {attempt} attempts: {e}")
                    raise e
                
                delay = self.calculate_delay(attempt)
                logger.warning(f"Operation '{operation}' failed (attempt {attempt}/{self.max_attempts}): {e}. "
                            f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)


class ErrorHandler:
    """Centralized error handler"""
    
    def __init__(self, logger: PhotoExtractionLogger):
        self.logger = logger
        self.error_counts: Dict[str, int] = {}
        self.error_contexts: List[ErrorContext] = []
        self._lock = threading.Lock()
    
    def handle_error(self, error: Exception, context: ErrorContext, 
                    should_raise: bool = True) -> bool:
        """Handle an error with context"""
        with self._lock:
            # Count errors by type
            error_type = type(error).__name__
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            # Store error context
            self.error_contexts.append(context)
            
            # Keep only recent errors (last 100)
            if len(self.error_contexts) > 100:
                self.error_contexts = self.error_contexts[-100:]
        
        # Log the error
        self.logger.log_operation_error(context.operation, context.component, 
                                     error, context)
        
        if should_raise:
            raise error
        
        return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors"""
        with self._lock:
            return {
                'error_counts': self.error_counts.copy(),
                'total_errors': sum(self.error_counts.values()),
                'recent_errors': len(self.error_contexts),
                'error_types': list(self.error_counts.keys())
            }
    
    def reset_error_counts(self):
        """Reset error counts"""
        with self._lock:
            self.error_counts.clear()
            self.error_contexts.clear()


def create_logger(name: str, config: PhotoExtractionConfig) -> PhotoExtractionLogger:
    """Factory function to create a photo extraction logger"""
    return PhotoExtractionLogger(name, config)


def create_retry_handler(max_attempts: int = 3, base_delay: float = 1.0,
                       max_delay: float = 60.0) -> RetryHandler:
    """Factory function to create a retry handler"""
    return RetryHandler(max_attempts, base_delay, max_delay)


def create_error_handler(logger: PhotoExtractionLogger) -> ErrorHandler:
    """Factory function to create an error handler"""
    return ErrorHandler(logger)


# Decorators for common patterns

def log_performance(logger: PhotoExtractionLogger, operation: str):
    """Decorator to log performance of functions"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metrics = logger.start_performance_tracking(operation)
            try:
                result = func(*args, **kwargs)
                
                # Try to extract metrics from result
                records_processed = 0
                success_count = 0
                error_count = 0
                
                if isinstance(result, dict):
                    records_processed = result.get('records_processed', 0)
                    success_count = result.get('success_count', 0)
                    error_count = result.get('error_count', 0)
                elif hasattr(result, '__dict__'):
                    records_processed = getattr(result, 'records_processed', 0)
                    success_count = getattr(result, 'success_count', 0)
                    error_count = getattr(result, 'error_count', 0)
                
                logger.finish_performance_tracking(metrics, 
                                               records_processed=records_processed,
                                               success_count=success_count,
                                               error_count=error_count)
                
                return result
            except Exception as e:
                logger.finish_performance_tracking(metrics, error_count=1)
                raise e
        
        return wrapper
    return decorator


def handle_errors(error_handler: ErrorHandler, operation: str, component: str,
                 should_raise: bool = True):
    """Decorator to handle errors consistently"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    operation=operation,
                    component=component,
                    additional_data={'args_count': len(args), 'kwargs_keys': list(kwargs.keys())}
                )
                error_handler.handle_error(e, context, should_raise)
        
        return wrapper
    return decorator