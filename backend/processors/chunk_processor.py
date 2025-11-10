"""
Chunk Processor with Resume Capability
UNS-CLAUDEJP 5.4 - Advanced Photo Extraction System

This module provides chunk-based processing with resume capability,
progress tracking, and memory optimization for large datasets.
"""

import json
import logging
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator, Callable, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import pickle
import hashlib

from ..config.photo_extraction_config import PhotoExtractionConfig

logger = logging.getLogger(__name__)


@dataclass
class ChunkInfo:
    """Information about a processing chunk"""
    chunk_id: int
    start_index: int
    end_index: int
    size: int
    processed: bool = False
    success: bool = False
    error_message: str = ""
    processing_time: float = 0.0
    records_processed: int = 0
    photos_extracted: int = 0
    errors: int = 0
    checksum: str = ""


@dataclass
class ProcessingState:
    """Complete processing state for resume capability"""
    job_id: str
    total_records: int
    chunk_size: int
    total_chunks: int
    processed_chunks: int
    successful_chunks: int
    failed_chunks: int
    start_time: datetime
    last_update_time: datetime
    chunks: List[ChunkInfo]
    current_mappings: Dict[str, str]
    total_photos_extracted: int
    total_errors: int
    is_completed: bool = False
    completion_time: Optional[datetime] = None
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage"""
        if self.total_chunks == 0:
            return 0.0
        return (self.processed_chunks / self.total_chunks) * 100.0
    
    def get_estimated_remaining_time(self) -> Optional[float]:
        """Estimate remaining time in seconds"""
        if self.processed_chunks == 0:
            return None
        
        elapsed = (self.last_update_time - self.start_time).total_seconds()
        avg_time_per_chunk = elapsed / self.processed_chunks
        remaining_chunks = self.total_chunks - self.processed_chunks
        
        return remaining_chunks * avg_time_per_chunk


class ProgressTracker:
    """Thread-safe progress tracking"""
    
    def __init__(self, total_chunks: int):
        self.total_chunks = total_chunks
        self.processed_chunks = 0
        self.current_chunk = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.callbacks: List[Callable[[int, int], None]] = []
    
    def add_callback(self, callback: Callable[[int, int], None]):
        """Add progress callback function"""
        self.callbacks.append(callback)
    
    def update_progress(self, current_chunk: int, processed_chunks: int):
        """Update progress and notify callbacks"""
        with self.lock:
            self.current_chunk = current_chunk
            self.processed_chunks = processed_chunks
            
            for callback in self.callbacks:
                try:
                    callback(current_chunk, processed_chunks)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information"""
        with self.lock:
            elapsed = time.time() - self.start_time
            progress_pct = (self.processed_chunks / self.total_chunks) * 100.0 if self.total_chunks > 0 else 0.0
            
            estimated_remaining = None
            if self.processed_chunks > 0:
                avg_time_per_chunk = elapsed / self.processed_chunks
                remaining_chunks = self.total_chunks - self.processed_chunks
                estimated_remaining = remaining_chunks * avg_time_per_chunk
            
            return {
                "current_chunk": self.current_chunk,
                "processed_chunks": self.processed_chunks,
                "total_chunks": self.total_chunks,
                "progress_percentage": progress_pct,
                "elapsed_time": elapsed,
                "estimated_remaining_time": estimated_remaining
            }


class ChunkProcessor:
    """Advanced chunk processor with resume capability"""
    
    def __init__(self, config: PhotoExtractionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.state_file_path = Path(config.backup_path) / "processing_state.json"
        self.checkpoint_file_path = Path(config.backup_path) / "checkpoint.pkl"
        
    def create_chunks(self, total_records: int, chunk_size: Optional[int] = None) -> List[ChunkInfo]:
        """Create chunks for processing"""
        chunk_size = chunk_size or self.config.processing.chunk_size
        
        chunks = []
        for i in range(0, total_records, chunk_size):
            chunk_id = i // chunk_size
            start_index = i
            end_index = min(i + chunk_size, total_records)
            size = end_index - start_index
            
            chunk = ChunkInfo(
                chunk_id=chunk_id,
                start_index=start_index,
                end_index=end_index,
                size=size,
                checksum=self._calculate_chunk_checksum(start_index, end_index)
            )
            chunks.append(chunk)
        
        self.logger.info(f"Created {len(chunks)} chunks for {total_records} records (chunk size: {chunk_size})")
        return chunks
    
    def initialize_processing_state(self, job_id: str, total_records: int, 
                                  chunks: List[ChunkInfo]) -> ProcessingState:
        """Initialize processing state"""
        state = ProcessingState(
            job_id=job_id,
            total_records=total_records,
            chunk_size=self.config.processing.chunk_size,
            total_chunks=len(chunks),
            processed_chunks=0,
            successful_chunks=0,
            failed_chunks=0,
            start_time=datetime.now(),
            last_update_time=datetime.now(),
            chunks=chunks,
            current_mappings={},
            total_photos_extracted=0,
            total_errors=0
        )
        
        self.save_state(state)
        return state
    
    def load_state(self, job_id: str) -> Optional[ProcessingState]:
        """Load existing processing state"""
        try:
            if self.state_file_path.exists():
                with open(self.state_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data.get('job_id') == job_id:
                    # Convert chunks back to ChunkInfo objects
                    chunks = []
                    for chunk_data in data['chunks']:
                        chunk = ChunkInfo(**chunk_data)
                        chunks.append(chunk)
                    
                    # Convert datetime strings back to datetime objects
                    start_time = datetime.fromisoformat(data['start_time'])
                    last_update_time = datetime.fromisoformat(data['last_update_time'])
                    
                    completion_time = None
                    if data.get('completion_time'):
                        completion_time = datetime.fromisoformat(data['completion_time'])
                    
                    state = ProcessingState(
                        job_id=data['job_id'],
                        total_records=data['total_records'],
                        chunk_size=data['chunk_size'],
                        total_chunks=data['total_chunks'],
                        processed_chunks=data['processed_chunks'],
                        successful_chunks=data['successful_chunks'],
                        failed_chunks=data['failed_chunks'],
                        start_time=start_time,
                        last_update_time=last_update_time,
                        chunks=chunks,
                        current_mappings=data.get('current_mappings', {}),
                        total_photos_extracted=data.get('total_photos_extracted', 0),
                        total_errors=data.get('total_errors', 0),
                        is_completed=data.get('is_completed', False),
                        completion_time=completion_time
                    )
                    
                    self.logger.info(f"Loaded processing state for job {job_id}: {state.processed_chunks}/{state.total_chunks} chunks processed")
                    return state
            
            self.logger.info(f"No existing state found for job {job_id}")
            return None
        
        except Exception as e:
            self.logger.error(f"Error loading processing state: {e}")
            return None
    
    def save_state(self, state: ProcessingState):
        """Save processing state to file"""
        try:
            # Ensure backup directory exists
            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert state to serializable format
            state_data = {
                'job_id': state.job_id,
                'total_records': state.total_records,
                'chunk_size': state.chunk_size,
                'total_chunks': state.total_chunks,
                'processed_chunks': state.processed_chunks,
                'successful_chunks': state.successful_chunks,
                'failed_chunks': state.failed_chunks,
                'start_time': state.start_time.isoformat(),
                'last_update_time': state.last_update_time.isoformat(),
                'chunks': [asdict(chunk) for chunk in state.chunks],
                'current_mappings': state.current_mappings,
                'total_photos_extracted': state.total_photos_extracted,
                'total_errors': state.total_errors,
                'is_completed': state.is_completed,
                'completion_time': state.completion_time.isoformat() if state.completion_time else None
            }
            
            # Atomic write
            temp_file = self.state_file_path.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self.state_file_path)
            
        except Exception as e:
            self.logger.error(f"Error saving processing state: {e}")
    
    def create_checkpoint(self, state: ProcessingState, additional_data: Optional[Dict] = None):
        """Create checkpoint with additional data"""
        if not self.config.processing.enable_resume:
            return
        
        try:
            checkpoint_data = {
                'state': state,
                'additional_data': additional_data or {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Atomic write
            temp_file = self.checkpoint_file_path.with_suffix('.tmp')
            with open(temp_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            
            temp_file.replace(self.checkpoint_file_path)
            
        except Exception as e:
            self.logger.error(f"Error creating checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict]:
        """Load checkpoint data"""
        try:
            if self.checkpoint_file_path.exists():
                with open(self.checkpoint_file_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            self.logger.error(f"Error loading checkpoint: {e}")
        
        return None
    
    def get_pending_chunks(self, state: ProcessingState) -> List[ChunkInfo]:
        """Get chunks that haven't been processed yet"""
        return [chunk for chunk in state.chunks if not chunk.processed]
    
    def get_failed_chunks(self, state: ProcessingState) -> List[ChunkInfo]:
        """Get chunks that failed processing"""
        return [chunk for chunk in state.chunks if chunk.processed and not chunk.success]
    
    def update_chunk_result(self, state: ProcessingState, chunk_id: int, 
                           success: bool, mappings: Dict[str, str],
                           photos_extracted: int = 0, errors: int = 0,
                           processing_time: float = 0.0, 
                           error_message: str = "") -> bool:
        """Update chunk processing result"""
        try:
            # Find the chunk
            chunk = None
            for c in state.chunks:
                if c.chunk_id == chunk_id:
                    chunk = c
                    break
            
            if not chunk:
                self.logger.error(f"Chunk {chunk_id} not found")
                return False
            
            # Update chunk info
            chunk.processed = True
            chunk.success = success
            chunk.processing_time = processing_time
            chunk.records_processed = chunk.size
            chunk.photos_extracted = photos_extracted
            chunk.errors = errors
            chunk.error_message = error_message
            
            # Update state
            state.processed_chunks += 1
            if success:
                state.successful_chunks += 1
                state.current_mappings.update(mappings)
                state.total_photos_extracted += photos_extracted
            else:
                state.failed_chunks += 1
                state.total_errors += errors
            
            state.last_update_time = datetime.now()
            
            # Save state periodically
            if state.processed_chunks % self.config.processing.resume_checkpoint_interval == 0:
                self.save_state(state)
                self.create_checkpoint(state)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error updating chunk result: {e}")
            return False
    
    def mark_completed(self, state: ProcessingState):
        """Mark processing as completed"""
        state.is_completed = True
        state.completion_time = datetime.now()
        self.save_state(state)
        
        # Clean up checkpoint file
        if self.checkpoint_file_path.exists():
            try:
                self.checkpoint_file_path.unlink()
            except Exception as e:
                self.logger.warning(f"Could not clean up checkpoint file: {e}")
    
    def process_chunks_with_resume(self, job_id: str, total_records: int,
                                 process_function: Callable[[ChunkInfo], Tuple[bool, Dict[str, str], int, int]],
                                 force_restart: bool = False) -> ProcessingState:
        """Process chunks with resume capability"""
        
        # Create chunks
        chunks = self.create_chunks(total_records)
        
        # Load existing state or create new
        if not force_restart:
            existing_state = self.load_state(job_id)
            if existing_state and existing_state.total_records == total_records:
                state = existing_state
                self.logger.info(f"Resuming processing from chunk {state.processed_chunks}/{state.total_chunks}")
            else:
                state = self.initialize_processing_state(job_id, total_records, chunks)
        else:
            state = self.initialize_processing_state(job_id, total_records, chunks)
            self.logger.info("Starting fresh processing (force restart)")
        
        # Get pending chunks
        pending_chunks = self.get_pending_chunks(state)
        
        if not pending_chunks:
            if state.is_completed:
                self.logger.info("Processing already completed")
            else:
                self.logger.info("All chunks processed")
                self.mark_completed(state)
            return state
        
        # Create progress tracker
        progress_tracker = ProgressTracker(state.total_chunks)
        
        # Add progress callback
        def progress_callback(current_chunk: int, processed_chunks: int):
            progress_pct = (processed_chunks / state.total_chunks) * 100.0
            self.logger.info(f"Progress: {processed_chunks:,}/{state.total_chunks:,} chunks ({progress_pct:.1f}%)")
        
        progress_tracker.add_callback(progress_callback)
        
        # Process chunks
        for chunk in pending_chunks:
            try:
                self.logger.info(f"Processing chunk {chunk.chunk_id + 1}/{state.total_chunks} "
                               f"(records {chunk.start_index}-{chunk.end_index})")
                
                start_time = time.time()
                
                # Process chunk
                success, mappings, photos_extracted, errors = process_function(chunk)
                
                processing_time = time.time() - start_time
                
                # Update result
                if self.update_chunk_result(state, chunk.chunk_id, success, mappings,
                                         photos_extracted, errors, processing_time):
                    self.logger.info(f"Chunk {chunk.chunk_id} completed: "
                                   f"success={success}, photos={photos_extracted}, errors={errors}")
                else:
                    self.logger.error(f"Failed to update result for chunk {chunk.chunk_id}")
                
                # Update progress
                progress_tracker.update_progress(chunk.chunk_id, state.processed_chunks)
                
                # Memory optimization
                if self.config.processing.memory_limit_mb > 0:
                    self._check_memory_usage()
                
            except Exception as e:
                self.logger.error(f"Error processing chunk {chunk.chunk_id}: {e}")
                self.update_chunk_result(state, chunk.chunk_id, False, {}, 0, 1, 0.0, str(e))
        
        # Mark as completed
        self.mark_completed(state)
        
        # Log final statistics
        elapsed = (state.completion_time - state.start_time).total_seconds()
        self.logger.info(f"Processing completed in {elapsed:.2f} seconds")
        self.logger.info(f"Total photos extracted: {state.total_photos_extracted:,}")
        self.logger.info(f"Total errors: {state.total_errors:,}")
        self.logger.info(f"Success rate: {(state.successful_chunks / state.total_chunks) * 100:.1f}%")
        
        return state
    
    def _calculate_chunk_checksum(self, start_index: int, end_index: int) -> str:
        """Calculate checksum for chunk identification"""
        data = f"{start_index}-{end_index}-{self.config.processing.chunk_size}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _check_memory_usage(self):
        """Check memory usage and trigger cleanup if needed"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.config.processing.memory_limit_mb:
                self.logger.warning(f"Memory usage ({memory_mb:.1f} MB) exceeds limit "
                                  f"({self.config.processing.memory_limit_mb} MB)")
                
                # Trigger garbage collection
                import gc
                gc.collect()
                
                # Check again after cleanup
                memory_mb_after = process.memory_info().rss / 1024 / 1024
                self.logger.info(f"Memory after cleanup: {memory_mb_after:.1f} MB")
        
        except ImportError:
            # psutil not available, skip memory monitoring
            pass
        except Exception as e:
            self.logger.error(f"Error checking memory usage: {e}")
    
    def cleanup_old_states(self, max_age_days: int = 7):
        """Clean up old processing states"""
        try:
            if self.state_file_path.exists():
                stat = self.state_file_path.stat()
                age_days = (time.time() - stat.st_mtime) / (24 * 3600)
                
                if age_days > max_age_days:
                    self.state_file_path.unlink()
                    self.logger.info(f"Cleaned up old state file: {self.state_file_path}")
            
            if self.checkpoint_file_path.exists():
                stat = self.checkpoint_file_path.stat()
                age_days = (time.time() - stat.st_mtime) / (24 * 3600)
                
                if age_days > max_age_days:
                    self.checkpoint_file_path.unlink()
                    self.logger.info(f"Cleaned up old checkpoint file: {self.checkpoint_file_path}")
        
        except Exception as e:
            self.logger.error(f"Error cleaning up old states: {e}")


def create_chunk_processor(config: PhotoExtractionConfig) -> ChunkProcessor:
    """Factory function to create chunk processor"""
    return ChunkProcessor(config)