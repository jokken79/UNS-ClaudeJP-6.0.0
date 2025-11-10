"""
Photo Extraction Strategies - Strategy Pattern Implementation
UNS-CLAUDEJP 5.4 - Advanced Photo Extraction System

This module implements the Strategy pattern for different photo extraction methods,
providing automatic fallback and method selection based on availability and performance.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Iterator
from pathlib import Path
from dataclasses import dataclass
from contextlib import contextmanager

from ..config.photo_extraction_config import PhotoExtractionConfig, ExtractionMethod

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of photo extraction operation"""
    success: bool
    total_records: int = 0
    photos_extracted: int = 0
    errors: int = 0
    mappings: Dict[str, str] = None
    execution_time: float = 0.0
    method_used: str = ""
    error_message: str = ""
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.mappings is None:
            self.mappings = {}
        if self.performance_metrics is None:
            self.performance_metrics = {}


@dataclass
class DatabaseInfo:
    """Database information for extraction"""
    path: Path
    table_name: str
    total_records: int
    has_photos: bool
    accessible: bool
    error_message: str = ""


class PhotoExtractionStrategy(ABC):
    """Abstract base class for photo extraction strategies"""
    
    def __init__(self, config: PhotoExtractionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this extraction method is available"""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get priority for method selection (lower number = higher priority)"""
        pass
    
    @abstractmethod
    def test_connection(self, db_path: Path) -> bool:
        """Test connection to database"""
        pass
    
    @abstractmethod
    def get_database_info(self, db_path: Path) -> DatabaseInfo:
        """Get database information"""
        pass
    
    @abstractmethod
    def extract_photos(self, db_path: Path, table_name: str, 
                     id_column: int, photo_column: int,
                     chunk_size: Optional[int] = None) -> ExtractionResult:
        """Extract photos from database"""
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Get supported database file extensions"""
        pass
    
    def validate_database(self, db_path: Path) -> Tuple[bool, str]:
        """Validate database file"""
        if not db_path.exists():
            return False, f"Database file not found: {db_path}"
        
        if not db_path.is_file():
            return False, f"Path is not a file: {db_path}"
        
        extension = db_path.suffix.lower()
        if extension not in self.get_supported_extensions():
            return False, f"Unsupported file extension: {extension}"
        
        return True, ""


class PyodbcExtractionStrategy(PhotoExtractionStrategy):
    """PyODBC-based extraction strategy"""
    
    def __init__(self, config: PhotoExtractionConfig):
        super().__init__(config)
        self._pyodbc_available = None
        self._connection_pool = {}
    
    def is_available(self) -> bool:
        """Check if pyodbc is available"""
        if self._pyodbc_available is None:
            try:
                import pyodbc
                # Check if Access driver is available
                drivers = [x for x in pyodbc.drivers() if x.startswith('Microsoft Access Driver')]
                self._pyodbc_available = len(drivers) > 0
                if self._pyodbc_available:
                    self.logger.info(f"Found Access drivers: {drivers}")
                else:
                    self.logger.warning("No Microsoft Access drivers found")
            except ImportError:
                self._pyodbc_available = False
                self.logger.warning("pyodbc not installed")
        
        return self._pyodbc_available
    
    def get_priority(self) -> int:
        """PyODBC has high priority due to Unicode support"""
        return 1
    
    def test_connection(self, db_path: Path) -> bool:
        """Test connection to Access database"""
        if not self.is_available():
            return False
        
        try:
            import pyodbc
            conn_str = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};"
            
            with self._get_connection(conn_str) as conn:
                cursor = conn.cursor()
                cursor.tables()
                return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_database_info(self, db_path: Path) -> DatabaseInfo:
        """Get database information"""
        if not self.is_available():
            return DatabaseInfo(db_path, "", 0, False, False, "PyODBC not available")
        
        is_valid, error_msg = self.validate_database(db_path)
        if not is_valid:
            return DatabaseInfo(db_path, "", 0, False, False, error_msg)
        
        try:
            import pyodbc
            conn_str = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};"
            
            with self._get_connection(conn_str) as conn:
                cursor = conn.cursor()
                
                # Get tables
                tables = [row.table_name for row in cursor.tables(tableType='TABLE')]
                
                # Find photo table
                photo_table = None
                for table in tables:
                    if self.config.database.table_name in table:
                        photo_table = table
                        break
                
                if not photo_table:
                    return DatabaseInfo(db_path, "", 0, False, True, "Photo table not found")
                
                # Get record count
                cursor.execute(f"SELECT COUNT(*) FROM [{photo_table}]")
                total_records = cursor.fetchone()[0]
                
                # Check if photo column has data
                cursor.execute(f"SELECT TOP 1 * FROM [{photo_table}]")
                columns = [column[0] for column in cursor.description]
                has_photos = len(columns) > self.config.database.photo_column_index
                
                return DatabaseInfo(
                    path=db_path,
                    table_name=photo_table,
                    total_records=total_records,
                    has_photos=has_photos,
                    accessible=True
                )
        
        except Exception as e:
            return DatabaseInfo(db_path, "", 0, False, False, str(e))
    
    def extract_photos(self, db_path: Path, table_name: str,
                     id_column: int, photo_column: int,
                     chunk_size: Optional[int] = None) -> ExtractionResult:
        """Extract photos using pyodbc"""
        start_time = time.time()
        
        if not self.is_available():
            return ExtractionResult(
                success=False,
                error_message="PyODBC not available",
                method_used="pyodbc"
            )
        
        is_valid, error_msg = self.validate_database(db_path)
        if not is_valid:
            return ExtractionResult(
                success=False,
                error_message=error_msg,
                method_used="pyodbc"
            )
        
        try:
            import pyodbc
            import base64
            
            conn_str = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};"
            
            with self._get_connection(conn_str) as conn:
                cursor = conn.cursor()
                
                # Get total records
                cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                total_records = cursor.fetchone()[0]
                
                # Extract data
                cursor.execute(f"SELECT * FROM [{table_name}]")
                
                mappings = {}
                photos_extracted = 0
                errors = 0
                processed = 0
                
                chunk_size = chunk_size or self.config.processing.chunk_size
                
                while True:
                    rows = cursor.fetchmany(chunk_size)
                    if not rows:
                        break
                    
                    for row in rows:
                        processed += 1
                        
                        try:
                            # Get ID from specified column
                            record_id = str(row[id_column]) if row[id_column] else f"record_{processed}"
                            
                            # Get photo data from specified column
                            photo_data = row[photo_column] if len(row) > photo_column else None
                            
                            if photo_data:
                                photos_extracted += 1
                                
                                # Handle different data types
                                if isinstance(photo_data, bytes):
                                    # Binary data - convert to base64
                                    base64_data = base64.b64encode(photo_data).decode('utf-8')
                                    mappings[record_id] = f"data:image/jpeg;base64,{base64_data}"
                                else:
                                    # Filename or text data
                                    mappings[record_id] = f"filename:{photo_data}"
                            
                            # Progress reporting
                            if processed % self.config.processing.progress_report_interval == 0:
                                self.logger.info(f"Processed {processed:,}/{total_records:,} records, extracted {photos_extracted:,} photos")
                        
                        except Exception as e:
                            errors += 1
                            self.logger.debug(f"Error processing record {processed}: {e}")
                
                execution_time = time.time() - start_time
                
                return ExtractionResult(
                    success=True,
                    total_records=total_records,
                    photos_extracted=photos_extracted,
                    errors=errors,
                    mappings=mappings,
                    execution_time=execution_time,
                    method_used="pyodbc",
                    performance_metrics={
                        "records_per_second": processed / execution_time if execution_time > 0 else 0,
                        "photos_per_second": photos_extracted / execution_time if execution_time > 0 else 0,
                        "error_rate": errors / processed if processed > 0 else 0
                    }
                )
        
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"PyODBC extraction failed: {e}")
            return ExtractionResult(
                success=False,
                error_message=str(e),
                execution_time=execution_time,
                method_used="pyodbc"
            )
    
    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions"""
        return ['.accdb', '.mdb']
    
    @contextmanager
    def _get_connection(self, conn_str: str):
        """Get database connection with connection pooling"""
        import pyodbc
        
        if self.config.performance.enable_connection_pooling:
            # Simple connection pooling implementation
            conn_key = hash(conn_str)
            
            if conn_key in self._connection_pool:
                conn = self._connection_pool[conn_key]
                try:
                    # Test if connection is still alive
                    conn.execute("SELECT 1")
                    yield conn
                    return
                except:
                    # Connection is dead, remove from pool
                    try:
                        conn.close()
                    except:
                        pass
                    del self._connection_pool[conn_key]
        
        # Create new connection
        conn = pyodbc.connect(conn_str, timeout=self.config.database.connection_timeout)
        
        if self.config.performance.enable_connection_pooling:
            self._connection_pool[conn_key] = conn
        
        try:
            yield conn
        finally:
            if not self.config.performance.enable_connection_pooling:
                conn.close()


class Pywin32ExtractionStrategy(PhotoExtractionStrategy):
    """PyWin32 COM-based extraction strategy"""
    
    def __init__(self, config: PhotoExtractionConfig):
        super().__init__(config)
        self._com_available = None
    
    def is_available(self) -> bool:
        """Check if COM automation is available"""
        if self._com_available is None:
            try:
                import win32com.client
                self._com_available = True
            except ImportError:
                self._com_available = False
                self.logger.warning("pywin32 not installed")
            except Exception as e:
                self._com_available = False
                self.logger.warning(f"COM not available: {e}")
        
        return self._com_available
    
    def get_priority(self) -> int:
        """COM has lower priority due to Unicode issues"""
        return 2
    
    def test_connection(self, db_path: Path) -> bool:
        """Test connection using COM"""
        if not self.is_available():
            return False
        
        try:
            import win32com.client
            engine = win32com.client.Dispatch("DAO.DBEngine.36")
            db = engine.OpenDatabase(str(db_path))
            db.Close()
            return True
        except Exception as e:
            self.logger.error(f"COM connection test failed: {e}")
            return False
    
    def get_database_info(self, db_path: Path) -> DatabaseInfo:
        """Get database information using COM"""
        if not self.is_available():
            return DatabaseInfo(db_path, "", 0, False, False, "COM not available")
        
        is_valid, error_msg = self.validate_database(db_path)
        if not is_valid:
            return DatabaseInfo(db_path, "", 0, False, False, error_msg)
        
        try:
            import win32com.client
            engine = win32com.client.Dispatch("DAO.DBEngine.36")
            db = engine.OpenDatabase(str(db_path))
            
            # Find photo table
            photo_table = None
            for table_def in db.TableDefs:
                if self.config.database.table_name in table_def.Name:
                    photo_table = table_def.Name
                    break
            
            if not photo_table:
                db.Close()
                return DatabaseInfo(db_path, "", 0, False, True, "Photo table not found")
            
            # Get record count
            recordset = db.OpenRecordset(photo_table)
            total_records = recordset.RecordCount
            has_photos = recordset.Fields.Count > self.config.database.photo_column_index
            recordset.Close()
            db.Close()
            
            return DatabaseInfo(
                path=db_path,
                table_name=photo_table,
                total_records=total_records,
                has_photos=has_photos,
                accessible=True
            )
        
        except Exception as e:
            return DatabaseInfo(db_path, "", 0, False, False, str(e))
    
    def extract_photos(self, db_path: Path, table_name: str,
                     id_column: int, photo_column: int,
                     chunk_size: Optional[int] = None) -> ExtractionResult:
        """Extract photos using COM"""
        start_time = time.time()
        
        if not self.is_available():
            return ExtractionResult(
                success=False,
                error_message="COM not available",
                method_used="pywin32"
            )
        
        is_valid, error_msg = self.validate_database(db_path)
        if not is_valid:
            return ExtractionResult(
                success=False,
                error_message=error_msg,
                method_used="pywin32"
            )
        
        try:
            import win32com.client
            import base64
            
            engine = win32com.client.Dispatch("DAO.DBEngine.36")
            db = engine.OpenDatabase(str(db_path))
            recordset = db.OpenRecordset(table_name)
            
            mappings = {}
            photos_extracted = 0
            errors = 0
            processed = 0
            total_records = recordset.RecordCount
            
            # Move to first record
            recordset.MoveFirst()
            
            while not recordset.EOF:
                processed += 1
                
                try:
                    # Get ID from specified field
                    record_id = str(recordset.Fields(id_column).Value) if recordset.Fields(id_column).Value else f"record_{processed}"
                    
                    # Get photo data from specified field
                    photo_field = recordset.Fields(photo_column)
                    photo_data = photo_field.Value if photo_field else None
                    
                    if photo_data:
                        photos_extracted += 1
                        
                        # Handle OLE objects
                        if hasattr(photo_data, 'GetValue'):
                            ole_data = photo_data.GetValue()
                            if isinstance(ole_data, bytes):
                                base64_data = base64.b64encode(ole_data).decode('utf-8')
                                mappings[record_id] = f"data:image/jpeg;base64,{base64_data}"
                            else:
                                mappings[record_id] = f"filename:{ole_data}"
                        else:
                            mappings[record_id] = f"filename:{photo_data}"
                    
                    # Progress reporting
                    if processed % self.config.processing.progress_report_interval == 0:
                        self.logger.info(f"Processed {processed:,}/{total_records:,} records, extracted {photos_extracted:,} photos")
                    
                    recordset.MoveNext()
                
                except Exception as e:
                    errors += 1
                    self.logger.debug(f"Error processing record {processed}: {e}")
                    recordset.MoveNext()
            
            recordset.Close()
            db.Close()
            
            execution_time = time.time() - start_time
            
            return ExtractionResult(
                success=True,
                total_records=total_records,
                photos_extracted=photos_extracted,
                errors=errors,
                mappings=mappings,
                execution_time=execution_time,
                method_used="pywin32",
                performance_metrics={
                    "records_per_second": processed / execution_time if execution_time > 0 else 0,
                    "photos_per_second": photos_extracted / execution_time if execution_time > 0 else 0,
                    "error_rate": errors / processed if processed > 0 else 0
                }
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"COM extraction failed: {e}")
            return ExtractionResult(
                success=False,
                error_message=str(e),
                execution_time=execution_time,
                method_used="pywin32"
            )
    
    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions"""
        return ['.accdb', '.mdb']


class PandasExtractionStrategy(PhotoExtractionStrategy):
    """Pandas-based extraction strategy (fallback option)"""
    
    def is_available(self) -> bool:
        """Check if pandas is available"""
        try:
            import pandas as pd
            import sqlalchemy
            return True
        except ImportError:
            self.logger.warning("pandas or sqlalchemy not installed")
            return False
    
    def get_priority(self) -> int:
        """Pandas has lowest priority (fallback only)"""
        return 3
    
    def test_connection(self, db_path: Path) -> bool:
        """Test connection using pandas"""
        if not self.is_available():
            return False
        
        try:
            import pandas as pd
            # Try to read a small sample
            df = pd.read_sql("SELECT TOP 1 * FROM information_schema.tables", 
                           f"access:///{db_path}")
            return True
        except Exception as e:
            self.logger.error(f"Pandas connection test failed: {e}")
            return False
    
    def get_database_info(self, db_path: Path) -> DatabaseInfo:
        """Get database information using pandas"""
        if not self.is_available():
            return DatabaseInfo(db_path, "", 0, False, False, "Pandas not available")
        
        # Implementation would be similar to other strategies
        # This is a placeholder for now
        return DatabaseInfo(db_path, "", 0, False, False, "Not implemented")
    
    def extract_photos(self, db_path: Path, table_name: str,
                     id_column: int, photo_column: int,
                     chunk_size: Optional[int] = None) -> ExtractionResult:
        """Extract photos using pandas"""
        # This would be implemented as a fallback method
        # For now, return failure
        return ExtractionResult(
            success=False,
            error_message="Pandas extraction not implemented yet",
            method_used="pandas"
        )
    
    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions"""
        return ['.accdb', '.mdb']


class PhotoExtractionContext:
    """Context class for managing extraction strategies"""
    
    def __init__(self, config: PhotoExtractionConfig):
        self.config = config
        self.strategies = self._initialize_strategies()
        self.logger = logging.getLogger(__name__)
    
    def _initialize_strategies(self) -> List[PhotoExtractionStrategy]:
        """Initialize all available strategies"""
        strategies = []
        
        # Add all available strategies
        strategies.append(PyodbcExtractionStrategy(self.config))
        strategies.append(Pywin32ExtractionStrategy(self.config))
        strategies.append(PandasExtractionStrategy(self.config))
        
        # Filter by availability and sort by priority
        available_strategies = [s for s in strategies if s.is_available()]
        available_strategies.sort(key=lambda s: s.get_priority())
        
        self.logger.info(f"Available extraction strategies: {[s.__class__.__name__ for s in available_strategies]}")
        
        return available_strategies
    
    def get_best_strategy(self, db_path: Path) -> Optional[PhotoExtractionStrategy]:
        """Get the best available strategy for the given database"""
        for strategy in self.strategies:
            if strategy.test_connection(db_path):
                self.logger.info(f"Selected strategy: {strategy.__class__.__name__}")
                return strategy
        
        self.logger.error("No suitable extraction strategy found")
        return None
    
    def extract_photos_with_fallback(self, db_path: Path, table_name: str,
                                  id_column: int, photo_column: int,
                                  chunk_size: Optional[int] = None) -> ExtractionResult:
        """Extract photos with automatic fallback"""
        last_error = ""
        
        for strategy in self.strategies:
            try:
                self.logger.info(f"Attempting extraction with {strategy.__class__.__name__}")
                
                if not strategy.test_connection(db_path):
                    self.logger.warning(f"Strategy {strategy.__class__.__name__} failed connection test")
                    continue
                
                result = strategy.extract_photos(db_path, table_name, id_column, photo_column, chunk_size)
                
                if result.success:
                    self.logger.info(f"Extraction successful with {strategy.__class__.__name__}")
                    return result
                else:
                    last_error = result.error_message
                    self.logger.warning(f"Strategy {strategy.__class__.__name__} failed: {last_error}")
            
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Strategy {strategy.__class__.__name__} threw exception: {last_error}")
        
        # All strategies failed
        return ExtractionResult(
            success=False,
            error_message=f"All extraction strategies failed. Last error: {last_error}",
            method_used="none"
        )
    
    def get_strategy_by_method(self, method: ExtractionMethod) -> Optional[PhotoExtractionStrategy]:
        """Get strategy by extraction method"""
        method_map = {
            ExtractionMethod.PYODBC: PyodbcExtractionStrategy,
            ExtractionMethod.PYWIN32: Pywin32ExtractionStrategy,
            ExtractionMethod.PANDAS: PandasExtractionStrategy,
        }
        
        strategy_class = method_map.get(method)
        if strategy_class:
            for strategy in self.strategies:
                if isinstance(strategy, strategy_class):
                    return strategy
        
        return None


def create_extraction_context(config: PhotoExtractionConfig) -> PhotoExtractionContext:
    """Factory function to create extraction context"""
    return PhotoExtractionContext(config)