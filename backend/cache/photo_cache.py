"""
Intelligent Photo Caching System
UNS-CLAUDEJP 5.4 - Advanced Photo Extraction System

This module provides intelligent caching with multiple backends (Redis, memory, file),
automatic invalidation, and performance optimization for photo extraction operations.
"""

import json
import pickle
import hashlib
import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, asdict
import sqlite3
import gzip

from ..config.photo_extraction_config import PhotoExtractionConfig, CacheConfig
from ..utils.logging_utils import PhotoExtractionLogger


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    checksum: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.last_accessed is None:
            self.last_accessed = datetime.now()
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self):
        """Update access information"""
        self.access_count += 1
        self.last_accessed = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'key': self.key,
            'value': self.value,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'size_bytes': self.size_bytes,
            'checksum': self.checksum,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary"""
        created_at = datetime.fromisoformat(data['created_at'])
        expires_at = None
        if data['expires_at']:
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        last_accessed = None
        if data['last_accessed']:
            last_accessed = datetime.fromisoformat(data['last_accessed'])
        
        return cls(
            key=data['key'],
            value=data['value'],
            created_at=created_at,
            expires_at=expires_at,
            access_count=data['access_count'],
            last_accessed=last_accessed,
            size_bytes=data['size_bytes'],
            checksum=data['checksum'],
            tags=data['tags']
        )


class CacheBackend(ABC):
    """Abstract base class for cache backends"""
    
    def __init__(self, config: CacheConfig, logger: PhotoExtractionLogger):
        self.config = config
        self.logger = logger
    
    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache"""
        pass
    
    @abstractmethod
    def set(self, entry: CacheEntry) -> bool:
        """Set entry in cache"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass
    
    def is_available(self) -> bool:
        """Check if backend is available"""
        return True


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend"""
    
    def __init__(self, config: CacheConfig, logger: PhotoExtractionLogger):
        super().__init__(config, logger)
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from memory cache"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats['misses'] += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                self._stats['evictions'] += 1
                return None
            
            entry.touch()
            self._stats['hits'] += 1
            return entry
    
    def set(self, entry: CacheEntry) -> bool:
        """Set entry in memory cache"""
        try:
            with self._lock:
                # Calculate size if not set
                if entry.size_bytes == 0:
                    entry.size_bytes = len(pickle.dumps(entry.value))
                
                # Calculate checksum if not set
                if not entry.checksum:
                    entry.checksum = self._calculate_checksum(entry.value)
                
                self._cache[entry.key] = entry
                self._stats['sets'] += 1
                return True
        except Exception as e:
            self.logger.error(f"Error setting cache entry: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete entry from memory cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats['deletes'] += 1
                return True
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._stats['clears'] = self._stats.get('clears', 0) + 1
            return True
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        import fnmatch
        with self._lock:
            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            total_entries = len(self._cache)
            
            stats = self._stats.copy()
            stats.update({
                'total_entries': total_entries,
                'total_size_bytes': total_size,
                'hit_rate': self._stats['hits'] / max(self._stats['hits'] + self._stats['misses'], 1),
                'backend_type': 'memory'
            })
            return stats
    
    def _calculate_checksum(self, value: Any) -> str:
        """Calculate checksum for value"""
        try:
            data = pickle.dumps(value)
            return hashlib.md5(data).hexdigest()
        except Exception:
            return hashlib.md5(str(value).encode()).hexdigest()


class RedisCacheBackend(CacheBackend):
    """Redis cache backend"""
    
    def __init__(self, config: CacheConfig, logger: PhotoExtractionLogger):
        super().__init__(config, logger)
        self._redis_client = None
        self._key_prefix = "photo_cache:"
        self._available = self._initialize_redis()
    
    def _initialize_redis(self) -> bool:
        """Initialize Redis connection"""
        try:
            import redis
            
            self._redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                decode_responses=False,  # Handle binary data
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self._redis_client.ping()
            self.logger.info(f"Connected to Redis at {self.config.redis_host}:{self.config.redis_port}")
            return True
        
        except ImportError:
            self.logger.warning("Redis not installed, falling back to memory cache")
            return False
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self._available and self._redis_client is not None
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from Redis"""
        if not self.is_available():
            return None
        
        try:
            redis_key = f"{self._key_prefix}{key}"
            data = self._redis_client.get(redis_key)
            
            if data is None:
                return None
            
            # Deserialize entry
            entry_data = pickle.loads(data)
            entry = CacheEntry.from_dict(entry_data)
            
            if entry.is_expired():
                self.delete(key)
                return None
            
            entry.touch()
            # Update access statistics in Redis
            self._redis_client.hset(f"{self._key_prefix}stats:{key}", mapping={
                'access_count': entry.access_count,
                'last_accessed': entry.last_accessed.isoformat()
            })
            
            return entry
        
        except Exception as e:
            self.logger.error(f"Error getting from Redis: {e}")
            return None
    
    def set(self, entry: CacheEntry) -> bool:
        """Set entry in Redis"""
        if not self.is_available():
            return False
        
        try:
            redis_key = f"{self._key_prefix}{entry.key}"
            
            # Calculate size and checksum if not set
            if entry.size_bytes == 0:
                entry.size_bytes = len(pickle.dumps(entry.value))
            
            if not entry.checksum:
                entry.checksum = self._calculate_checksum(entry.value)
            
            # Serialize entry
            entry_data = pickle.dumps(entry.to_dict())
            
            # Set with TTL if expiration is set
            if entry.expires_at:
                ttl_seconds = int((entry.expires_at - datetime.now()).total_seconds())
                if ttl_seconds > 0:
                    self._redis_client.setex(redis_key, ttl_seconds, entry_data)
                else:
                    # Already expired
                    return False
            else:
                self._redis_client.set(redis_key, entry_data)
            
            # Set metadata
            self._redis_client.hset(f"{self._key_prefix}meta:{entry.key}", mapping={
                'created_at': entry.created_at.isoformat(),
                'size_bytes': entry.size_bytes,
                'checksum': entry.checksum,
                'tags': json.dumps(entry.tags)
            })
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error setting to Redis: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete entry from Redis"""
        if not self.is_available():
            return False
        
        try:
            redis_key = f"{self._key_prefix}{key}"
            self._redis_client.delete(redis_key)
            self._redis_client.delete(f"{self._key_prefix}stats:{key}")
            self._redis_client.delete(f"{self._key_prefix}meta:{key}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting from Redis: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries"""
        if not self.is_available():
            return False
        
        try:
            pattern = f"{self._key_prefix}*"
            keys = self._redis_client.keys(pattern)
            if keys:
                self._redis_client.delete(*keys)
            return True
        except Exception as e:
            self.logger.error(f"Error clearing Redis: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        if not self.is_available():
            return []
        
        try:
            redis_pattern = f"{self._key_prefix}{pattern}"
            redis_keys = self._redis_client.keys(redis_pattern)
            # Remove prefix
            return [key.decode('utf-8')[len(self._key_prefix):] for key in redis_keys]
        except Exception as e:
            self.logger.error(f"Error getting keys from Redis: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        if not self.is_available():
            return {'backend_type': 'redis', 'available': False}
        
        try:
            info = self._redis_client.info()
            pattern = f"{self._key_prefix}*"
            keys = self._redis_client.keys(pattern)
            
            return {
                'backend_type': 'redis',
                'available': True,
                'total_entries': len(keys),
                'redis_memory_used': info.get('used_memory', 0),
                'redis_memory_human': info.get('used_memory_human', 'N/A'),
                'redis_connected_clients': info.get('connected_clients', 0),
                'redis_keyspace_hits': info.get('keyspace_hits', 0),
                'redis_keyspace_misses': info.get('keyspace_misses', 0),
            }
        except Exception as e:
            self.logger.error(f"Error getting Redis stats: {e}")
            return {'backend_type': 'redis', 'available': False, 'error': str(e)}
    
    def _calculate_checksum(self, value: Any) -> str:
        """Calculate checksum for value"""
        try:
            data = pickle.dumps(value)
            return hashlib.md5(data).hexdigest()
        except Exception:
            return hashlib.md5(str(value).encode()).hexdigest()


class FileCacheBackend(CacheBackend):
    """File-based cache backend with SQLite"""
    
    def __init__(self, config: CacheConfig, logger: PhotoExtractionLogger):
        super().__init__(config, logger)
        self.cache_dir = Path(config.file_cache_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize SQLite database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        value BLOB,
                        created_at TIMESTAMP,
                        expires_at TIMESTAMP,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP,
                        size_bytes INTEGER DEFAULT 0,
                        checksum TEXT,
                        tags TEXT
                    )
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)
                ''')
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error initializing file cache database: {e}")
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from file cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    'SELECT * FROM cache_entries WHERE key = ?', (key,)
                )
                row = cursor.fetchone()
                
                if row is None:
                    return None
                
                # Check expiration
                if row['expires_at']:
                    expires_at = datetime.fromisoformat(row['expires_at'])
                    if datetime.now() > expires_at:
                        self.delete(key)
                        return None
                
                # Deserialize value
                value = pickle.loads(row['value'])
                
                # Create entry
                entry = CacheEntry(
                    key=row['key'],
                    value=value,
                    created_at=datetime.fromisoformat(row['created_at']),
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    access_count=row['access_count'],
                    last_accessed=datetime.fromisoformat(row['last_accessed']) if row['last_accessed'] else None,
                    size_bytes=row['size_bytes'],
                    checksum=row['checksum'],
                    tags=json.loads(row['tags']) if row['tags'] else []
                )
                
                # Update access statistics
                entry.touch()
                self._update_access_stats(key, entry)
                
                return entry
        
        except Exception as e:
            self.logger.error(f"Error getting from file cache: {e}")
            return None
    
    def set(self, entry: CacheEntry) -> bool:
        """Set entry in file cache"""
        try:
            # Calculate size and checksum if not set
            if entry.size_bytes == 0:
                serialized_value = pickle.dumps(entry.value)
                entry.size_bytes = len(serialized_value)
            else:
                serialized_value = pickle.dumps(entry.value)
            
            if not entry.checksum:
                entry.checksum = self._calculate_checksum(entry.value)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO cache_entries 
                    (key, value, created_at, expires_at, access_count, last_accessed, size_bytes, checksum, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry.key,
                    serialized_value,
                    entry.created_at.isoformat(),
                    entry.expires_at.isoformat() if entry.expires_at else None,
                    entry.access_count,
                    entry.last_accessed.isoformat(),
                    entry.size_bytes,
                    entry.checksum,
                    json.dumps(entry.tags)
                ))
                conn.commit()
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error setting to file cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete entry from file cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting from file cache: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM cache_entries')
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error clearing file cache: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT key FROM cache_entries WHERE key LIKE ?', (pattern.replace('*', '%'),)
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting keys from file cache: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get file cache statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_entries,
                        SUM(size_bytes) as total_size,
                        AVG(access_count) as avg_access_count
                    FROM cache_entries
                ''')
                stats = cursor.fetchone()
                
                # Get database file size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return {
                    'backend_type': 'file',
                    'total_entries': stats[0] or 0,
                    'total_size_bytes': stats[1] or 0,
                    'database_size_bytes': db_size,
                    'avg_access_count': stats[2] or 0,
                }
        except Exception as e:
            self.logger.error(f"Error getting file cache stats: {e}")
            return {'backend_type': 'file', 'error': str(e)}
    
    def _update_access_stats(self, key: str, entry: CacheEntry):
        """Update access statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE cache_entries 
                    SET access_count = ?, last_accessed = ?
                    WHERE key = ?
                ''', (entry.access_count, entry.last_accessed.isoformat(), key))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error updating access stats: {e}")
    
    def _calculate_checksum(self, value: Any) -> str:
        """Calculate checksum for value"""
        try:
            data = pickle.dumps(value)
            return hashlib.md5(data).hexdigest()
        except Exception:
            return hashlib.md5(str(value).encode()).hexdigest()


class PhotoCacheManager:
    """Intelligent photo cache manager with multiple backends"""
    
    def __init__(self, config: PhotoExtractionConfig, logger: PhotoExtractionLogger):
        self.config = config
        self.logger = logger
        self.backends = self._initialize_backends()
        self.primary_backend = self._get_primary_backend()
    
    def _initialize_backends(self) -> Dict[str, CacheBackend]:
        """Initialize cache backends"""
        backends = {}
        
        # Always include memory backend as fallback
        backends['memory'] = MemoryCacheBackend(self.config.cache, self.logger)
        
        # Add Redis if available and enabled
        if self.config.cache.cache_backend in ['redis', 'auto'] and self.config.cache.enable_cache:
            redis_backend = RedisCacheBackend(self.config.cache, self.logger)
            if redis_backend.is_available():
                backends['redis'] = redis_backend
                self.logger.info("Redis cache backend initialized")
            else:
                self.logger.warning("Redis backend not available, using memory cache")
        
        # Add file backend if enabled
        if self.config.cache.cache_backend in ['file', 'auto'] and self.config.cache.enable_cache:
            backends['file'] = FileCacheBackend(self.config.cache, self.logger)
            self.logger.info("File cache backend initialized")
        
        return backends
    
    def _get_primary_backend(self) -> CacheBackend:
        """Get primary cache backend"""
        backend_priority = ['redis', 'file', 'memory']
        
        for backend_name in backend_priority:
            if backend_name in self.backends:
                return self.backends[backend_name]
        
        # Fallback to memory
        return self.backends['memory']
    
    def get(self, key: str, backend: Optional[str] = None) -> Optional[CacheEntry]:
        """Get entry from cache"""
        target_backend = self.backends.get(backend, self.primary_backend) if backend else self.primary_backend
        
        entry = target_backend.get(key)
        if entry:
            self.logger.debug(f"Cache hit: {key} from {target_backend.__class__.__name__}")
        else:
            self.logger.debug(f"Cache miss: {key} from {target_backend.__class__.__name__}")
        
        return entry
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
            tags: Optional[List[str]] = None, backend: Optional[str] = None) -> bool:
        """Set entry in cache"""
        target_backend = self.backends.get(backend, self.primary_backend) if backend else self.primary_backend
        
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        elif self.config.cache.cache_ttl_seconds > 0:
            expires_at = datetime.now() + timedelta(seconds=self.config.cache.cache_ttl_seconds)
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            tags=tags or []
        )
        
        success = target_backend.set(entry)
        if success:
            self.logger.debug(f"Cache set: {key} to {target_backend.__class__.__name__}")
        
        return success
    
    def delete(self, key: str, backend: Optional[str] = None) -> bool:
        """Delete entry from cache"""
        target_backend = self.backends.get(backend, self.primary_backend) if backend else self.primary_backend
        return target_backend.delete(key)
    
    def clear(self, backend: Optional[str] = None) -> bool:
        """Clear cache"""
        if backend:
            if backend in self.backends:
                return self.backends[backend].clear()
            return False
        else:
            # Clear all backends
            success = True
            for backend_obj in self.backends.values():
                success &= backend_obj.clear()
            return success
    
    def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate cache entries by tags"""
        invalidated = 0
        
        for backend in self.backends.values():
            try:
                keys = backend.keys()
                for key in keys:
                    entry = backend.get(key)
                    if entry and any(tag in entry.tags for tag in tags):
                        if backend.delete(key):
                            invalidated += 1
            except Exception as e:
                self.logger.error(f"Error invalidating tags in {backend.__class__.__name__}: {e}")
        
        self.logger.info(f"Invalidated {invalidated} cache entries by tags: {tags}")
        return invalidated
    
    def get_photo(self, rirekisho_id: str) -> Optional[str]:
        """Get photo data by rirekisho_id"""
        cache_key = f"photo:{rirekisho_id}"
        entry = self.get(cache_key)
        
        if entry:
            return entry.value
        
        return None
    
    def set_photo(self, rirekisho_id: str, photo_data: str, ttl_seconds: Optional[int] = None) -> bool:
        """Set photo data by rirekisho_id"""
        cache_key = f"photo:{rirekisho_id}"
        tags = ['photo', f'rirekisho:{rirekisho_id}']
        
        return self.set(cache_key, photo_data, ttl_seconds, tags)
    
    def get_database_metadata(self, db_path: str) -> Optional[Dict[str, Any]]:
        """Get database metadata from cache"""
        cache_key = f"db_metadata:{hashlib.md5(db_path.encode()).hexdigest()}"
        entry = self.get(cache_key)
        
        if entry:
            return entry.value
        
        return None
    
    def set_database_metadata(self, db_path: str, metadata: Dict[str, Any], 
                           ttl_seconds: Optional[int] = None) -> bool:
        """Set database metadata in cache"""
        cache_key = f"db_metadata:{hashlib.md5(db_path.encode()).hexdigest()}"
        tags = ['database', 'metadata']
        
        return self.set(cache_key, metadata, ttl_seconds, tags)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = {
            'backends': {},
            'primary_backend': self.primary_backend.__class__.__name__,
            'total_backends': len(self.backends)
        }
        
        for name, backend in self.backends.items():
            backend_stats = backend.get_stats()
            backend_stats['available'] = backend.is_available()
            stats['backends'][name] = backend_stats
        
        return stats
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries"""
        cleaned = 0
        
        for backend in self.backends.values():
            try:
                keys = backend.keys()
                for key in keys:
                    entry = backend.get(key)
                    if entry and entry.is_expired():
                        if backend.delete(key):
                            cleaned += 1
            except Exception as e:
                self.logger.error(f"Error cleaning up {backend.__class__.__name__}: {e}")
        
        self.logger.info(f"Cleaned up {cleaned} expired cache entries")
        return cleaned


def create_cache_manager(config: PhotoExtractionConfig, logger: PhotoExtractionLogger) -> PhotoCacheManager:
    """Factory function to create cache manager"""
    return PhotoCacheManager(config, logger)