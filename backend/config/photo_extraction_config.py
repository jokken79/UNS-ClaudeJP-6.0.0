"""
Configuration Module for Advanced Photo Extraction System
UNS-CLAUDEJP 5.4 - Optimized Photo Extraction

This module provides centralized configuration management for the photo extraction
system with environment-specific settings and validation.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ExtractionMethod(Enum):
    """Available extraction methods"""
    PYODBC = "pyodbc"
    PYWIN32 = "pywin32"
    PANDAS = "pandas"
    AUTO = "auto"  # Automatic selection with fallback


class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    access_db_paths: List[str] = field(default_factory=lambda: [
        "BASEDATEJP/ユニバーサル企画㈱データベースv25.3.24.accdb",
        "BASEDATEJP/ユニバーサル企画㈱データベース.accdb",
        "BASEDATEJP/ユニバーサル企画.accdb",
        "D:/BASEDATEJP/ユニバーサル企画㈱データベースv25.3.24.accdb",
    ])
    table_name: str = "T_履歴書"
    id_column_index: int = 0
    photo_column_index: int = 8
    connection_timeout: int = 30
    max_connections: int = 5
    connection_retry_attempts: int = 3
    connection_retry_delay: float = 1.0


@dataclass
class ProcessingConfig:
    """Data processing configuration"""
    chunk_size: int = 500
    max_workers: int = 4
    enable_parallel_processing: bool = True
    memory_limit_mb: int = 1024
    enable_resume: bool = True
    resume_checkpoint_interval: int = 100
    progress_report_interval: int = 50


@dataclass
class CacheConfig:
    """Caching configuration"""
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    cache_backend: str = "memory"  # memory, redis, file
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    file_cache_path: str = "./cache/photo_cache"


@dataclass
class ValidationConfig:
    """Data validation configuration"""
    enable_validation: bool = True
    validate_photo_integrity: bool = True
    max_photo_size_mb: int = 10
    allowed_photo_formats: List[str] = field(default_factory=lambda: ["JPEG", "PNG", "JPG"])
    min_photo_resolution: tuple = (50, 50)  # width, height
    detect_corrupted_files: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: LogLevel = LogLevel.INFO
    enable_file_logging: bool = True
    enable_console_logging: bool = True
    log_file_path: str = "./logs/photo_extraction"
    log_rotation_mb: int = 10
    log_backup_count: int = 5
    enable_performance_logging: bool = True
    enable_unicode_support: bool = True


@dataclass
class PerformanceConfig:
    """Performance optimization configuration"""
    enable_connection_pooling: bool = True
    enable_async_processing: bool = False  # Future feature
    enable_compression: bool = True
    compression_level: int = 6
    enable_batch_operations: bool = True
    batch_operation_size: int = 100


@dataclass
class PhotoExtractionConfig:
    """Main configuration class for photo extraction"""
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # General settings
    extraction_method: ExtractionMethod = ExtractionMethod.AUTO
    output_file_path: str = "./access_photo_mappings.json"
    backup_enabled: bool = True
    backup_path: str = "./backups"
    force_regenerate: bool = False
    dry_run: bool = False
    
    # Environment detection
    environment: str = "development"  # development, staging, production
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        self._validate_config()
        self._setup_directories()
    
    def _validate_config(self):
        """Validate configuration parameters"""
        if self.processing.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        
        if self.processing.max_workers <= 0:
            raise ValueError("max_workers must be positive")
        
        if self.validation.max_photo_size_mb <= 0:
            raise ValueError("max_photo_size_mb must be positive")
        
        if self.database.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")
    
    def _setup_directories(self):
        """Create necessary directories"""
        directories = [
            Path(self.output_file_path).parent,
            Path(self.logging.log_file_path).parent,
            Path(self.cache.file_cache_path),
            Path(self.backup_path),
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Could not create directory {directory}: {e}")
    
    @classmethod
    def from_file(cls, config_path: str) -> 'PhotoExtractionConfig':
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return cls.from_dict(config_data)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {config_path}: {e}")
            return cls()
    
    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> 'PhotoExtractionConfig':
        """Create configuration from dictionary"""
        # Extract sub-configurations
        database_config = DatabaseConfig(**config_data.get('database', {}))
        processing_config = ProcessingConfig(**config_data.get('processing', {}))
        cache_config = CacheConfig(**config_data.get('cache', {}))
        validation_config = ValidationConfig(**config_data.get('validation', {}))
        logging_config = LoggingConfig(**config_data.get('logging', {}))
        performance_config = PerformanceConfig(**config_data.get('performance', {}))
        
        # Handle enum conversion
        extraction_method = ExtractionMethod(
            config_data.get('extraction_method', 'auto')
        )
        logging_level = LogLevel(
            config_data.get('logging', {}).get('level', 'INFO')
        )
        logging_config.level = logging_level
        
        return cls(
            database=database_config,
            processing=processing_config,
            cache=cache_config,
            validation=validation_config,
            logging=logging_config,
            performance=performance_config,
            extraction_method=extraction_method,
            **{k: v for k, v in config_data.items() 
               if k not in ['database', 'processing', 'cache', 'validation', 'logging', 'performance', 'extraction_method']}
        )
    
    @classmethod
    def from_environment(cls) -> 'PhotoExtractionConfig':
        """Load configuration from environment variables"""
        config = cls()
        
        # Override with environment variables
        config.extraction_method = ExtractionMethod(
            os.environ.get('PHOTO_EXTRACTION_METHOD', 'auto')
        )
        config.processing.chunk_size = int(
            os.environ.get('PHOTO_CHUNK_SIZE', config.processing.chunk_size)
        )
        config.processing.max_workers = int(
            os.environ.get('PHOTO_MAX_WORKERS', config.processing.max_workers)
        )
        config.cache.enable_cache = os.environ.get(
            'PHOTO_ENABLE_CACHE', str(config.cache.enable_cache)
        ).lower() in ('1', 'true', 'yes')
        config.logging.level = LogLevel(
            os.environ.get('PHOTO_LOG_LEVEL', config.logging.level.value)
        )
        config.force_regenerate = os.environ.get(
            'FORCE_REGENERATE_PHOTOS', str(config.force_regenerate)
        ).lower() in ('1', 'true', 'yes')
        config.dry_run = os.environ.get(
            'PHOTO_DRY_RUN', str(config.dry_run)
        ).lower() in ('1', 'true', 'yes')
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'extraction_method': self.extraction_method.value,
            'output_file_path': self.output_file_path,
            'backup_enabled': self.backup_enabled,
            'backup_path': self.backup_path,
            'force_regenerate': self.force_regenerate,
            'dry_run': self.dry_run,
            'environment': self.environment,
            'database': {
                'access_db_paths': self.database.access_db_paths,
                'table_name': self.database.table_name,
                'id_column_index': self.database.id_column_index,
                'photo_column_index': self.database.photo_column_index,
                'connection_timeout': self.database.connection_timeout,
                'max_connections': self.database.max_connections,
                'connection_retry_attempts': self.database.connection_retry_attempts,
                'connection_retry_delay': self.database.connection_retry_delay,
            },
            'processing': {
                'chunk_size': self.processing.chunk_size,
                'max_workers': self.processing.max_workers,
                'enable_parallel_processing': self.processing.enable_parallel_processing,
                'memory_limit_mb': self.processing.memory_limit_mb,
                'enable_resume': self.processing.enable_resume,
                'resume_checkpoint_interval': self.processing.resume_checkpoint_interval,
                'progress_report_interval': self.processing.progress_report_interval,
            },
            'cache': {
                'enable_cache': self.cache.enable_cache,
                'cache_ttl_seconds': self.cache.cache_ttl_seconds,
                'cache_backend': self.cache.cache_backend,
                'redis_host': self.cache.redis_host,
                'redis_port': self.cache.redis_port,
                'redis_db': self.cache.redis_db,
                'file_cache_path': self.cache.file_cache_path,
            },
            'validation': {
                'enable_validation': self.validation.enable_validation,
                'validate_photo_integrity': self.validation.validate_photo_integrity,
                'max_photo_size_mb': self.validation.max_photo_size_mb,
                'allowed_photo_formats': self.validation.allowed_photo_formats,
                'min_photo_resolution': self.validation.min_photo_resolution,
                'detect_corrupted_files': self.validation.detect_corrupted_files,
            },
            'logging': {
                'level': self.logging.level.value,
                'enable_file_logging': self.logging.enable_file_logging,
                'enable_console_logging': self.logging.enable_console_logging,
                'log_file_path': self.logging.log_file_path,
                'log_rotation_mb': self.logging.log_rotation_mb,
                'log_backup_count': self.logging.log_backup_count,
                'enable_performance_logging': self.logging.enable_performance_logging,
                'enable_unicode_support': self.logging.enable_unicode_support,
            },
            'performance': {
                'enable_connection_pooling': self.performance.enable_connection_pooling,
                'enable_async_processing': self.performance.enable_async_processing,
                'enable_compression': self.performance.enable_compression,
                'compression_level': self.performance.compression_level,
                'enable_batch_operations': self.performance.enable_batch_operations,
                'batch_operation_size': self.performance.batch_operation_size,
            },
        }
    
    def save_to_file(self, config_path: str):
        """Save configuration to JSON file"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to: {config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {config_path}: {e}")
    
    def get_effective_config(self) -> 'PhotoExtractionConfig':
        """Get effective configuration considering environment overrides"""
        # Start with current config
        effective = self
        
        # Apply environment-specific overrides
        if self.environment == "production":
            effective.processing.chunk_size = max(effective.processing.chunk_size, 1000)
            effective.processing.max_workers = min(effective.processing.max_workers, 8)
            effective.cache.cache_ttl_seconds = 7200  # 2 hours
            effective.logging.level = LogLevel.WARNING
        elif self.environment == "staging":
            effective.processing.chunk_size = max(effective.processing.chunk_size, 500)
            effective.cache.cache_ttl_seconds = 1800  # 30 minutes
            effective.logging.level = LogLevel.INFO
        
        return effective


def load_config(config_path: Optional[str] = None) -> PhotoExtractionConfig:
    """
    Load configuration from multiple sources with priority:
    1. Command line arguments (handled elsewhere)
    2. Environment variables
    3. Configuration file
    4. Default values
    """
    # Start with defaults
    config = PhotoExtractionConfig()
    
    # Load from file if provided
    if config_path and Path(config_path).exists():
        config = PhotoExtractionConfig.from_file(config_path)
    
    # Override with environment variables
    env_config = PhotoExtractionConfig.from_environment()
    
    # Merge configurations (environment takes precedence)
    config.extraction_method = env_config.extraction_method
    config.processing.chunk_size = env_config.processing.chunk_size
    config.processing.max_workers = env_config.processing.max_workers
    config.cache.enable_cache = env_config.cache.enable_cache
    config.logging.level = env_config.logging.level
    config.force_regenerate = env_config.force_regenerate
    config.dry_run = env_config.dry_run
    
    return config.get_effective_config()


# Default configuration file paths
DEFAULT_CONFIG_PATHS = [
    "./config/photo_extraction_config.json",
    "./photo_extraction_config.json",
    "../config/photo_extraction_config.json",
]

def find_config_file() -> Optional[str]:
    """Find configuration file in default locations"""
    for config_path in DEFAULT_CONFIG_PATHS:
        if Path(config_path).exists():
            return config_path
    return None