"""
Advanced Photo Validation and Data Integrity Module
UNS-CLAUDEJP 5.4 - Advanced Photo Extraction System

This module provides comprehensive photo validation, data integrity checks,
corruption detection, and quality assessment for extracted photos.
"""

import base64
import hashlib
import imghdr
import io
import re
import struct
from typing import Dict, Any, List, Optional, Tuple, Union, BinaryIO
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import mimetypes

from PIL import Image, ImageStat
import magic

from ..config.photo_extraction_config import PhotoExtractionConfig, ValidationConfig
from ..utils.logging_utils import PhotoExtractionLogger


@dataclass
class ValidationResult:
    """Result of photo validation"""
    is_valid: bool
    error_messages: List[str] = field(default_factory=list)
    warning_messages: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    file_size_bytes: int = 0
    detected_format: str = ""
    expected_format: str = ""
    resolution: Tuple[int, int] = (0, 0)
    color_mode: str = ""
    has_transparency: bool = False
    is_corrupted: bool = False
    checksum: str = ""
    
    def add_error(self, message: str):
        """Add error message"""
        self.error_messages.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add warning message"""
        self.warning_messages.append(message)
    
    def get_severity(self) -> str:
        """Get validation severity"""
        if self.is_corrupted:
            return "CRITICAL"
        elif not self.is_valid:
            return "ERROR"
        elif self.warning_messages:
            return "WARNING"
        else:
            return "OK"


@dataclass
class PhotoMetadata:
    """Comprehensive photo metadata"""
    filename: str
    format: str
    mode: str
    size: Tuple[int, int]
    file_size_bytes: int
    color_depth: int
    has_transparency: bool
    is_animated: bool
    num_frames: int = 1
    dpi: Tuple[int, int] = (72, 72)
    compression: str = ""
    exif_data: Dict[str, Any] = field(default_factory=dict)
    checksum_md5: str = ""
    checksum_sha256: str = ""
    creation_time: Optional[datetime] = None
    modification_time: Optional[datetime] = None


class PhotoValidator:
    """Advanced photo validator with multiple validation strategies"""
    
    def __init__(self, config: PhotoExtractionConfig, logger: PhotoExtractionLogger):
        self.config = config
        self.logger = logger
        self.validation_config = config.validation
        
        # Compile regex patterns
        self.base64_pattern = re.compile(r'^data:image/([a-zA-Z]+);base64,')
        self.filename_pattern = re.compile(r'^filename:([^\s]+)$')
        
        # Supported formats
        self.supported_formats = set(self.validation_config.allowed_photo_formats)
        
        # Initialize magic for file type detection
        try:
            self.magic_detector = magic.Magic(mime=True)
        except Exception:
            self.magic_detector = None
            self.logger.warning("python-magic not available, using basic validation")
    
    def validate_photo_data(self, photo_data: str, record_id: str = "") -> ValidationResult:
        """Comprehensive photo data validation"""
        result = ValidationResult(is_valid=True)
        
        try:
            # Check if photo_data is empty
            if not photo_data:
                result.add_error("Photo data is empty")
                return result
            
            # Determine data type and extract actual data
            actual_data, data_type = self._extract_photo_data(photo_data)
            
            if not actual_data:
                result.add_error("Could not extract photo data")
                return result
            
            # Store metadata
            result.metadata['data_type'] = data_type
            result.metadata['record_id'] = record_id
            
            # Validate based on data type
            if data_type == "base64":
                self._validate_base64_photo(actual_data, result)
            elif data_type == "filename":
                self._validate_filename_reference(actual_data, result)
            else:
                result.add_error(f"Unknown photo data type: {data_type}")
            
            # Calculate checksum
            if result.is_valid and not result.is_corrupted:
                result.checksum = self._calculate_checksum(photo_data)
            
            # Calculate quality score
            result.quality_score = self._calculate_quality_score(result)
            
        except Exception as e:
            result.add_error(f"Validation error: {str(e)}")
            self.logger.error(f"Photo validation failed for record {record_id}: {e}")
        
        return result
    
    def _extract_photo_data(self, photo_data: str) -> Tuple[Optional[str], str]:
        """Extract actual photo data and determine type"""
        # Check for base64 data URL
        base64_match = self.base64_pattern.match(photo_data)
        if base64_match:
            format_type = base64_match.group(1).upper()
            return photo_data, "base64"
        
        # Check for filename reference
        filename_match = self.filename_pattern.match(photo_data)
        if filename_match:
            filename = filename_match.group(1)
            return filename, "filename"
        
        # Check if it's raw base64 without data URL
        try:
            # Try to decode as base64
            decoded = base64.b64decode(photo_data)
            # If successful and looks like image data, treat as base64
            if self._looks_like_image_data(decoded):
                return photo_data, "base64"
        except Exception:
            pass
        
        # Return as-is with unknown type
        return photo_data, "unknown"
    
    def _validate_base64_photo(self, photo_data: str, result: ValidationResult):
        """Validate base64-encoded photo"""
        try:
            # Extract base64 part
            comma_index = photo_data.find(',')
            if comma_index == -1:
                result.add_error("Invalid base64 data URL format")
                return
            
            base64_part = photo_data[comma_index + 1:]
            
            # Decode base64
            image_bytes = base64.b64decode(base64_part)
            
            # Validate image data
            self._validate_image_bytes(image_bytes, result)
            
            # Extract format from data URL
            format_match = self.base64_pattern.match(photo_data)
            if format_match:
                result.expected_format = format_match.group(1).upper()
            
        except base64.binascii.Error as e:
            result.add_error(f"Invalid base64 encoding: {e}")
            result.is_corrupted = True
        except Exception as e:
            result.add_error(f"Base64 validation error: {e}")
            result.is_corrupted = True
    
    def _validate_filename_reference(self, filename: str, result: ValidationResult):
        """Validate filename reference"""
        if not filename:
            result.add_error("Empty filename reference")
            return
        
        # Check filename length
        if len(filename) > 255:
            result.add_warning(f"Filename too long: {len(filename)} characters")
        
        # Check for invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            if char in filename:
                result.add_error(f"Invalid character in filename: {char}")
        
        # Check file extension
        ext = Path(filename).suffix.lower()
        if ext and ext[1:] not in [f.lower() for f in self.supported_formats]:
            result.add_warning(f"Unsupported file extension: {ext}")
        
        # Store metadata
        result.metadata['filename'] = filename
        result.metadata['extension'] = ext
        result.detected_format = "FILENAME"
    
    def _validate_image_bytes(self, image_bytes: bytes, result: ValidationResult):
        """Validate raw image bytes"""
        if not image_bytes:
            result.add_error("Empty image data")
            result.is_corrupted = True
            return
        
        # Check file size
        result.file_size_bytes = len(image_bytes)
        max_size_mb = self.validation_config.max_photo_size_mb
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if result.file_size_bytes > max_size_bytes:
            result.add_error(f"Image too large: {result.file_size_bytes / (1024*1024):.1f}MB (max: {max_size_mb}MB)")
        
        # Detect image format
        detected_format = self._detect_image_format(image_bytes)
        result.detected_format = detected_format
        
        if not detected_format:
            result.add_error("Could not detect image format")
            result.is_corrupted = True
            return
        
        # Validate format
        if detected_format not in self.supported_formats:
            result.add_error(f"Unsupported image format: {detected_format}")
        
        # Check for corruption
        if self.validation_config.detect_corrupted_files:
            self._check_image_corruption(image_bytes, result)
        
        # Extract image metadata
        if not result.is_corrupted:
            self._extract_image_metadata(image_bytes, result)
    
    def _detect_image_format(self, image_bytes: bytes) -> str:
        """Detect image format from bytes"""
        # Try python-magic first
        if self.magic_detector:
            try:
                mime_type = self.magic_detector.from_buffer(image_bytes)
                if mime_type.startswith('image/'):
                    format_name = mime_type.split('/')[1].upper()
                    if format_name in ['JPEG', 'PNG', 'JPG', 'GIF', 'BMP', 'TIFF']:
                        return format_name
            except Exception:
                pass
        
        # Fallback to imghdr
        format_name = imghdr.what(None, h=image_bytes)
        if format_name:
            format_map = {
                'jpeg': 'JPEG',
                'jpg': 'JPG',
                'png': 'PNG',
                'gif': 'GIF',
                'bmp': 'BMP',
                'tiff': 'TIFF'
            }
            return format_map.get(format_name.lower(), format_name.upper())
        
        # Try to detect from file signatures
        signatures = {
            b'\xFF\xD8\xFF': 'JPEG',
            b'\x89PNG\r\n\x1A\n': 'PNG',
            b'GIF87a': 'GIF',
            b'GIF89a': 'GIF',
            b'BM': 'BMP',
            b'II*\x00': 'TIFF',
            b'MM\x00*': 'TIFF'
        }
        
        for signature, format_name in signatures.items():
            if image_bytes.startswith(signature):
                return format_name
        
        return "UNKNOWN"
    
    def _check_image_corruption(self, image_bytes: bytes, result: ValidationResult):
        """Check for image corruption"""
        try:
            # Try to open with PIL
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Try to load the image data
                img.load()
                
                # Check for common corruption indicators
                if img.mode == 'P' and 'transparency' in img.info:
                    # Check if palette is valid
                    try:
                        img.convert('RGBA')
                    except Exception as e:
                        result.add_error(f"Corrupted palette: {e}")
                        result.is_corrupted = True
                
                # Check for truncated images
                try:
                    img.verify()
                except Exception as e:
                    result.add_error(f"Image verification failed: {e}")
                    result.is_corrupted = True
        
        except Exception as e:
            result.add_error(f"Cannot open image: {e}")
            result.is_corrupted = True
    
    def _extract_image_metadata(self, image_bytes: bytes, result: ValidationResult):
        """Extract comprehensive image metadata"""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Basic metadata
                result.resolution = img.size
                result.color_mode = img.mode
                result.has_transparency = self._has_transparency(img)
                
                # Store in metadata
                result.metadata.update({
                    'width': img.size[0],
                    'height': img.size[1],
                    'mode': img.mode,
                    'has_transparency': result.has_transparency,
                    'format': img.format,
                    'is_animated': getattr(img, 'is_animated', False),
                    'num_frames': getattr(img, 'n_frames', 1)
                })
                
                # DPI information
                if hasattr(img, 'info') and 'dpi' in img.info:
                    result.metadata['dpi'] = img.info['dpi']
                
                # Color depth
                result.metadata['color_depth'] = self._get_color_depth(img)
                
                # EXIF data (for JPEG)
                if img.format == 'JPEG' and hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        result.metadata['exif'] = self._parse_exif(exif)
                
                # Quality assessment
                quality_info = self._assess_image_quality(img)
                result.metadata.update(quality_info)
        
        except Exception as e:
            result.add_warning(f"Could not extract metadata: {e}")
    
    def _has_transparency(self, img: Image.Image) -> bool:
        """Check if image has transparency"""
        if img.mode in ('RGBA', 'LA', 'P'):
            return True
        
        if img.mode == 'P' and 'transparency' in img.info:
            return True
        
        return False
    
    def _get_color_depth(self, img: Image.Image) -> int:
        """Get color depth of image"""
        if img.mode == '1':
            return 1
        elif img.mode == 'L':
            return 8
        elif img.mode == 'P':
            return 8
        elif img.mode == 'RGB':
            return 24
        elif img.mode == 'RGBA':
            return 32
        elif img.mode == 'CMYK':
            return 32
        else:
            return 0  # Unknown
    
    def _parse_exif(self, exif_data: dict) -> Dict[str, Any]:
        """Parse EXIF data"""
        try:
            from PIL.ExifTags import TAGS
            
            parsed = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                parsed[tag_name] = value
            
            return parsed
        except Exception:
            return {}
    
    def _assess_image_quality(self, img: Image.Image) -> Dict[str, Any]:
        """Assess image quality"""
        quality_info = {}
        
        try:
            # Resolution assessment
            width, height = img.size
            min_width, min_height = self.validation_config.min_photo_resolution
            
            if width < min_width or height < min_height:
                quality_info['resolution_warning'] = f"Low resolution: {width}x{height} (min: {min_width}x{min_height})"
            
            # Aspect ratio check
            aspect_ratio = width / height
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                quality_info['aspect_ratio_warning'] = f"Unusual aspect ratio: {aspect_ratio:.2f}"
            
            # File size efficiency (compression quality)
            if img.format == 'JPEG':
                # Estimate uncompressed size
                uncompressed_size = width * height * 3  # RGB
                compression_ratio = len(img.tobytes()) / uncompressed_size if uncompressed_size > 0 else 0
                quality_info['compression_ratio'] = compression_ratio
                
                if compression_ratio > 0.5:  # Poor compression
                    quality_info['compression_warning'] = "Poor compression quality"
            
            # Color distribution (for basic quality assessment)
            if img.mode in ['RGB', 'RGBA']:
                stat = ImageStat.Stat(img.convert('RGB'))
                # Calculate standard deviation as a simple quality metric
                r_std, g_std, b_std = stat.stddev
                avg_std = (r_std + g_std + b_std) / 3
                quality_info['color_variance'] = avg_std
                
                if avg_std < 10:  # Very low variance might indicate low quality
                    quality_info['low_variance_warning'] = "Very low color variance"
        
        except Exception as e:
            quality_info['quality_assessment_error'] = str(e)
        
        return quality_info
    
    def _looks_like_image_data(self, data: bytes) -> bool:
        """Check if data looks like image data"""
        if len(data) < 10:
            return False
        
        # Check for common image signatures
        signatures = [
            b'\xFF\xD8\xFF',  # JPEG
            b'\x89PNG',        # PNG
            b'GIF87a',        # GIF
            b'GIF89a',        # GIF
            b'BM',             # BMP
            b'II*\x00',        # TIFF
            b'MM\x00*'         # TIFF
        ]
        
        return any(data.startswith(sig) for sig in signatures)
    
    def _calculate_checksum(self, data: str) -> str:
        """Calculate checksum for data"""
        return hashlib.md5(data.encode('utf-8')).hexdigest()
    
    def _calculate_quality_score(self, result: ValidationResult) -> float:
        """Calculate overall quality score (0-100)"""
        if result.is_corrupted or not result.is_valid:
            return 0.0
        
        score = 100.0
        
        # Deduct for errors
        score -= len(result.error_messages) * 20
        
        # Deduct for warnings
        score -= len(result.warning_messages) * 5
        
        # Deduct for corruption
        if result.is_corrupted:
            score -= 50
        
        # Bonus for good properties
        if result.resolution[0] > 0 and result.resolution[1] > 0:
            min_width, min_height = self.validation_config.min_photo_resolution
            if result.resolution[0] >= min_width and result.resolution[1] >= min_height:
                score += 5
        
        # Ensure score is within bounds
        return max(0.0, min(100.0, score))
    
    def validate_batch(self, photo_mappings: Dict[str, str]) -> Dict[str, ValidationResult]:
        """Validate a batch of photos"""
        results = {}
        
        self.logger.info(f"Starting batch validation of {len(photo_mappings)} photos")
        
        for record_id, photo_data in photo_mappings.items():
            result = self.validate_photo_data(photo_data, record_id)
            results[record_id] = result
        
        # Log summary
        valid_count = sum(1 for r in results.values() if r.is_valid)
        corrupted_count = sum(1 for r in results.values() if r.is_corrupted)
        total_errors = sum(len(r.error_messages) for r in results.values())
        total_warnings = sum(len(r.warning_messages) for r in results.values())
        
        self.logger.info(f"Batch validation completed: {valid_count}/{len(results)} valid, "
                        f"{corrupted_count} corrupted, {total_errors} errors, {total_warnings} warnings")
        
        return results
    
    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get validation summary statistics"""
        total_photos = len(results)
        valid_photos = sum(1 for r in results.values() if r.is_valid)
        corrupted_photos = sum(1 for r in results.values() if r.is_corrupted)
        
        # Format distribution
        format_counts = {}
        for result in results.values():
            fmt = result.detected_format
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        
        # Quality distribution
        quality_ranges = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
        for result in results.values():
            score = result.quality_score
            if score >= 80:
                quality_ranges['excellent'] += 1
            elif score >= 60:
                quality_ranges['good'] += 1
            elif score >= 40:
                quality_ranges['fair'] += 1
            else:
                quality_ranges['poor'] += 1
        
        # Size statistics
        sizes = [r.file_size_bytes for r in results.values() if r.file_size_bytes > 0]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        
        return {
            'total_photos': total_photos,
            'valid_photos': valid_photos,
            'corrupted_photos': corrupted_photos,
            'validity_rate': (valid_photos / total_photos * 100) if total_photos > 0 else 0,
            'corruption_rate': (corrupted_photos / total_photos * 100) if total_photos > 0 else 0,
            'format_distribution': format_counts,
            'quality_distribution': quality_ranges,
            'average_file_size_bytes': avg_size,
            'total_file_size_bytes': sum(sizes),
            'average_quality_score': sum(r.quality_score for r in results.values()) / total_photos if total_photos > 0 else 0
        }


class DataIntegrityChecker:
    """Data integrity checker for photo mappings"""
    
    def __init__(self, config: PhotoExtractionConfig, logger: PhotoExtractionLogger):
        self.config = config
        self.logger = logger
    
    def check_mappings_integrity(self, mappings: Dict[str, str]) -> Dict[str, Any]:
        """Check integrity of photo mappings"""
        integrity_report = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {},
            'duplicates': [],
            'missing_records': [],
            'invalid_formats': []
        }
        
        # Check for empty mappings
        if not mappings:
            integrity_report['errors'].append("No photo mappings found")
            integrity_report['is_valid'] = False
            return integrity_report
        
        # Check for duplicate values
        value_counts = {}
        for record_id, photo_data in mappings.items():
            if photo_data in value_counts:
                value_counts[photo_data].append(record_id)
            else:
                value_counts[photo_data] = [record_id]
        
        duplicates = {k: v for k, v in value_counts.items() if len(v) > 1}
        if duplicates:
            integrity_report['duplicates'] = duplicates
            integrity_report['warnings'].append(f"Found {len(duplicates)} duplicate photo values")
        
        # Check for empty or None values
        empty_records = [rid for rid, data in mappings.items() if not data or data.strip() == '']
        if empty_records:
            integrity_report['missing_records'] = empty_records
            integrity_report['errors'].append(f"Found {len(empty_records)} empty photo records")
            integrity_report['is_valid'] = False
        
        # Check record ID format
        invalid_ids = [rid for rid in mappings.keys() if not str(rid).strip()]
        if invalid_ids:
            integrity_report['errors'].append(f"Found {len(invalid_ids)} invalid record IDs")
            integrity_report['is_valid'] = False
        
        # Generate statistics
        integrity_report['statistics'] = {
            'total_mappings': len(mappings),
            'unique_values': len(set(mappings.values())),
            'duplicate_groups': len(duplicates),
            'empty_records': len(empty_records),
            'average_value_length': sum(len(str(v)) for v in mappings.values()) / len(mappings)
        }
        
        return integrity_report
    
    def verify_checksums(self, mappings: Dict[str, str], 
                        expected_checksums: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Verify checksums of photo data"""
        checksum_report = {
            'verified': True,
            'mismatches': [],
            'missing_checksums': [],
            'calculated_checksums': {}
        }
        
        if not expected_checksums:
            # Calculate checksums for all mappings
            for record_id, photo_data in mappings.items():
                checksum = hashlib.md5(str(photo_data).encode('utf-8')).hexdigest()
                checksum_report['calculated_checksums'][record_id] = checksum
            return checksum_report
        
        # Verify against expected checksums
        for record_id, photo_data in mappings.items():
            calculated = hashlib.md5(str(photo_data).encode('utf-8')).hexdigest()
            checksum_report['calculated_checksums'][record_id] = calculated
            
            if record_id in expected_checksums:
                expected = expected_checksums[record_id]
                if calculated != expected:
                    checksum_report['mismatches'].append({
                        'record_id': record_id,
                        'expected': expected,
                        'calculated': calculated
                    })
                    checksum_report['verified'] = False
            else:
                checksum_report['missing_checksums'].append(record_id)
        
        return checksum_report


def create_photo_validator(config: PhotoExtractionConfig, 
                        logger: PhotoExtractionLogger) -> PhotoValidator:
    """Factory function to create photo validator"""
    return PhotoValidator(config, logger)


def create_integrity_checker(config: PhotoExtractionConfig,
                         logger: PhotoExtractionLogger) -> DataIntegrityChecker:
    """Factory function to create integrity checker"""
    return DataIntegrityChecker(config, logger)