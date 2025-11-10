#!/usr/bin/env python3
"""
Data Quality Validation for UNS-CLAUDEJP 5.4 Photo Extraction System v2.0

This module provides comprehensive data quality validation to ensure
integrity, consistency, and accuracy of extracted photo data.

Usage:
    python data_quality_validation.py [--config PATH] [--output PATH] [--dataset PATH]
"""

import sys
import os
import json
import time
import hashlib
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import statistics
import base64
import imghdr
from PIL import Image, ImageStat
import io
import mimetypes

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config.photo_extraction_config import PhotoExtractionConfig, load_config
    from scripts.auto_extract_photos_from_databasejp_v2 import AdvancedPhotoExtractor
    from utils.logging_utils import create_logger
    from cache.photo_cache import create_cache_manager
    from validation.photo_validator import create_photo_validator, create_integrity_checker
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


@dataclass
class QualityValidationResult:
    """Result of data quality validation"""
    test_name: str
    total_records: int
    valid_records: int
    invalid_records: int
    quality_score: float  # 0-100
    error_types: Dict[str, int] = None
    warning_types: Dict[str, int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.error_types is None:
            self.error_types = {}
        if self.warning_types is None:
            self.warning_types = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PhotoQualityMetrics:
    """Detailed quality metrics for photos"""
    format_distribution: Dict[str, int]
    size_distribution: Dict[str, int]
    resolution_distribution: Dict[str, int]
    corruption_rate: float
    duplicate_rate: float
    completeness_rate: float
    consistency_score: float
    integrity_score: float
    overall_quality_score: float


class DataQualityValidator:
    """Comprehensive data quality validation suite"""
    
    def __init__(self, config: PhotoExtractionConfig, output_dir: Path = None):
        self.config = config
        self.output_dir = output_dir or Path("data_quality_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self.logger = create_logger("DataQualityValidator", config)
        
        # Initialize components
        self.extractor = None
        self.cache_manager = None
        self.photo_validator = None
        self.integrity_checker = None
        
        # Validation results
        self.results: List[QualityValidationResult] = []
        
        self.logger.info("Data quality validator initialized")
    
    def setup_components(self):
        """Setup system components for validation"""
        try:
            self.extractor = AdvancedPhotoExtractor(self.config)
            self.cache_manager = create_cache_manager(self.config, self.logger)
            self.photo_validator = create_photo_validator(self.config, self.logger)
            self.integrity_checker = create_integrity_checker(self.config, self.logger)
            
            self.logger.info("Components setup completed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup components: {e}")
            return False
    
    def load_photo_mappings(self, dataset_path: Path = None) -> Dict[str, str]:
        """Load photo mappings from dataset or extraction results"""
        if dataset_path and dataset_path.exists():
            # Load from specified dataset file
            self.logger.info(f"Loading photo mappings from: {dataset_path}")
            
            try:
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'mappings' in data:
                    return data['mappings']
                elif isinstance(data, dict):
                    return data
                else:
                    self.logger.error(f"Invalid dataset format: {dataset_path}")
                    return {}
            
            except Exception as e:
                self.logger.error(f"Failed to load dataset: {e}")
                return {}
        
        else:
            # Extract photos using the system
            self.logger.info("Extracting photos for validation...")
            
            try:
                # Find database
                db_path = self.extractor.find_database()
                if not db_path:
                    self.logger.error("Database not found")
                    return {}
                
                # Perform extraction
                extraction_result = self.extractor.extract_photos_with_optimization(db_path)
                
                if extraction_result['success']:
                    return extraction_result.get('mappings', {})
                else:
                    self.logger.error(f"Extraction failed: {extraction_result.get('error', 'Unknown error')}")
                    return {}
            
            except Exception as e:
                self.logger.error(f"Failed to extract photos: {e}")
                return {}
    
    def validate_photo_format(self, photo_data: str, record_id: str) -> Tuple[bool, List[str], List[str]]:
        """Validate photo format and structure"""
        errors = []
        warnings = []
        
        try:
            # Extract actual photo data
            if photo_data.startswith('data:image/'):
                # Base64 data URL
                comma_index = photo_data.find(',')
                if comma_index == -1:
                    errors.append("Invalid base64 data URL format")
                    return False, errors, warnings
                
                base64_part = photo_data[comma_index + 1:]
                image_bytes = base64.b64decode(base64_part)
                
                # Detect format
                format_name = imghdr.what(None, h=image_bytes)
                if not format_name:
                    errors.append("Could not detect image format")
                    return False, errors, warnings
                
                # Validate format
                supported_formats = ['jpeg', 'jpg', 'png', 'bmp', 'gif', 'tiff']
                if format_name.lower() not in supported_formats:
                    warnings.append(f"Unsupported image format: {format_name}")
                
                # Try to open with PIL
                try:
                    with Image.open(io.BytesIO(image_bytes)) as img:
                        # Basic validation
                        if img.size[0] < 10 or img.size[1] < 10:
                            warnings.append(f"Very small image: {img.size}")
                        
                        # Check for corruption
                        img.verify()
                        
                except Exception as e:
                    errors.append(f"Corrupted or invalid image: {e}")
                    return False, errors, warnings
                
            elif photo_data.startswith('filename:'):
                # Filename reference
                filename = photo_data[9:]  # Remove 'filename:' prefix
                if not filename.strip():
                    errors.append("Empty filename reference")
                    return False, errors, warnings
                
                # Check filename validity
                invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
                for char in invalid_chars:
                    if char in filename:
                        errors.append(f"Invalid character in filename: {char}")
                
            else:
                # Unknown format
                warnings.append("Unknown photo data format")
            
            return True, errors, warnings
        
        except Exception as e:
            errors.append(f"Format validation error: {e}")
            return False, errors, warnings
    
    def validate_photo_integrity(self, photo_data: str, record_id: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate photo integrity and calculate quality metrics"""
        errors = []
        metadata = {}
        
        try:
            # Extract actual photo data
            if photo_data.startswith('data:image/'):
                comma_index = photo_data.find(',')
                base64_part = photo_data[comma_index + 1:]
                image_bytes = base64.b64decode(base64_part)
                
                # Calculate checksum
                checksum_md5 = hashlib.md5(image_bytes).hexdigest()
                checksum_sha256 = hashlib.sha256(image_bytes).hexdigest()
                
                # Basic metadata
                metadata.update({
                    'size_bytes': len(image_bytes),
                    'checksum_md5': checksum_md5,
                    'checksum_sha256': checksum_sha256
                })
                
                # Try to open with PIL for detailed analysis
                try:
                    with Image.open(io.BytesIO(image_bytes)) as img:
                        metadata.update({
                            'format': img.format,
                            'mode': img.mode,
                            'size': img.size,
                            'has_transparency': img.mode in ('RGBA', 'LA', 'P') and 'transparency' in img.info
                        })
                        
                        # Quality assessment
                        if img.mode in ('RGB', 'RGBA'):
                            stat = ImageStat.Stat(img.convert('RGB'))
                            r_std, g_std, b_std = stat.stddev
                            avg_std = (r_std + g_std + b_std) / 3
                            metadata['color_variance'] = avg_std
                        
                        # Resolution check
                        min_width, min_height = self.config.validation.min_photo_resolution
                        if img.size[0] < min_width or img.size[1] < min_height:
                            errors.append(f"Low resolution: {img.size} (min: {min_width}x{min_height})")
                        
                        # File size check
                        max_size_mb = self.config.validation.max_photo_size_mb
                        max_size_bytes = max_size_mb * 1024 * 1024
                        if len(image_bytes) > max_size_bytes:
                            errors.append(f"Image too large: {len(image_bytes) / (1024*1024):.1f}MB (max: {max_size_mb}MB)")
                
                except Exception as e:
                    errors.append(f"Image analysis failed: {e}")
            
            elif photo_data.startswith('filename:'):
                filename = photo_data[9:]
                metadata.update({
                    'type': 'filename_reference',
                    'filename': filename,
                    'size_bytes': len(filename.encode('utf-8'))
                })
            
            return True, errors, metadata
        
        except Exception as e:
            errors.append(f"Integrity validation error: {e}")
            return False, errors, metadata
    
    def validate_data_completeness(self, photo_mappings: Dict[str, str]) -> QualityValidationResult:
        """Validate data completeness"""
        self.logger.info("Validating data completeness...")
        
        total_records = len(photo_mappings)
        complete_records = 0
        incomplete_records = 0
        error_types = {}
        warning_types = {}
        
        for record_id, photo_data in photo_mappings.items():
            is_complete = True
            record_errors = []
            record_warnings = []
            
            # Check for empty data
            if not photo_data or photo_data.strip() == '':
                is_complete = False
                record_errors.append("empty_photo_data")
            
            # Check for null/None values
            if photo_data is None:
                is_complete = False
                record_errors.append("null_photo_data")
            
            # Check for placeholder values
            placeholder_patterns = ['null', 'none', 'undefined', 'n/a', 'not available']
            if photo_data.lower() in placeholder_patterns:
                is_complete = False
                record_warnings.append("placeholder_photo_data")
            
            # Count errors and warnings
            for error in record_errors:
                error_types[error] = error_types.get(error, 0) + 1
            
            for warning in record_warnings:
                warning_types[warning] = warning_types.get(warning, 0) + 1
            
            if is_complete:
                complete_records += 1
            else:
                incomplete_records += 1
        
        # Calculate quality score
        completeness_rate = (complete_records / total_records * 100) if total_records > 0 else 0
        quality_score = completeness_rate  # Completeness is the primary factor
        
        result = QualityValidationResult(
            test_name="data_completeness",
            total_records=total_records,
            valid_records=complete_records,
            invalid_records=incomplete_records,
            quality_score=quality_score,
            error_types=error_types,
            warning_types=warning_types,
            metadata={
                'completeness_rate': completeness_rate,
                'error_details': error_types,
                'warning_details': warning_types
            }
        )
        
        self.logger.info(f"Data completeness validation completed: {completeness_rate:.1f}% complete")
        return result
    
    def validate_data_consistency(self, photo_mappings: Dict[str, str]) -> QualityValidationResult:
        """Validate data consistency"""
        self.logger.info("Validating data consistency...")
        
        total_records = len(photo_mappings)
        consistent_records = 0
        inconsistent_records = 0
        error_types = {}
        warning_types = {}
        
        # Analyze data patterns
        data_formats = {}
        format_examples = {}
        
        for record_id, photo_data in photo_mappings.items():
            # Categorize data format
            if photo_data.startswith('data:image/'):
                format_type = 'base64_image'
                # Extract image format
                if 'jpeg' in photo_data.lower():
                    format_subtype = 'base64_jpeg'
                elif 'png' in photo_data.lower():
                    format_subtype = 'base64_png'
                else:
                    format_subtype = 'base64_other'
            elif photo_data.startswith('filename:'):
                format_type = 'filename_reference'
                format_subtype = 'filename'
            else:
                format_type = 'unknown'
                format_subtype = 'unknown'
            
            data_formats[format_type] = data_formats.get(format_type, 0) + 1
            
            # Store examples for each format
            if format_subtype not in format_examples:
                format_examples[format_subtype] = photo_data[:100] + "..." if len(photo_data) > 100 else photo_data
        
        # Check consistency
        dominant_format = max(data_formats.keys(), key=lambda k: data_formats[k])
        dominant_count = data_formats[dominant_format]
        consistency_rate = (dominant_count / total_records * 100) if total_records > 0 else 0
        
        # Identify inconsistent records
        inconsistent_threshold = 0.1  # 10% threshold for consistency
        for record_id, photo_data in photo_mappings.items():
            is_consistent = True
            
            # Check if record uses dominant format
            if dominant_format == 'base64_image' and not photo_data.startswith('data:image/'):
                is_consistent = False
            elif dominant_format == 'filename_reference' and not photo_data.startswith('filename:'):
                is_consistent = False
            
            if not is_consistent:
                inconsistent_records += 1
                error_types['inconsistent_format'] = error_types.get('inconsistent_format', 0) + 1
            else:
                consistent_records += 1
        
        # Calculate quality score
        quality_score = consistency_rate
        
        result = QualityValidationResult(
            test_name="data_consistency",
            total_records=total_records,
            valid_records=consistent_records,
            invalid_records=inconsistent_records,
            quality_score=quality_score,
            error_types=error_types,
            warning_types=warning_types,
            metadata={
                'consistency_rate': consistency_rate,
                'data_formats': data_formats,
                'dominant_format': dominant_format,
                'format_examples': format_examples
            }
        )
        
        self.logger.info(f"Data consistency validation completed: {consistency_rate:.1f}% consistent")
        return result
    
    def validate_photo_quality(self, photo_mappings: Dict[str, str]) -> QualityValidationResult:
        """Validate photo quality metrics"""
        self.logger.info("Validating photo quality...")
        
        total_records = len(photo_mappings)
        high_quality_records = 0
        low_quality_records = 0
        error_types = {}
        warning_types = {}
        
        quality_metrics = {
            'formats': {},
            'sizes': [],
            'resolutions': [],
            'corrupted': 0,
            'valid': 0
        }
        
        for record_id, photo_data in photo_mappings.items():
            try:
                # Validate format and integrity
                is_valid, errors, metadata = self.validate_photo_integrity(photo_data, record_id)
                
                if is_valid:
                    quality_metrics['valid'] += 1
                    
                    # Collect quality metrics
                    if 'format' in metadata:
                        fmt = metadata['format']
                        quality_metrics['formats'][fmt] = quality_metrics['formats'].get(fmt, 0) + 1
                    
                    if 'size_bytes' in metadata:
                        quality_metrics['sizes'].append(metadata['size_bytes'])
                    
                    if 'size' in metadata:
                        quality_metrics['resolutions'].append(metadata['size'])
                    
                    # Assess quality
                    quality_score = self._assess_photo_quality(metadata)
                    if quality_score >= 70:  # 70% threshold for high quality
                        high_quality_records += 1
                    else:
                        low_quality_records += 1
                        warning_types['low_quality'] = warning_types.get('low_quality', 0) + 1
                
                else:
                    quality_metrics['corrupted'] += 1
                    low_quality_records += 1
                    
                    for error in errors:
                        error_types[error] = error_types.get(error, 0) + 1
            
            except Exception as e:
                error_types['validation_error'] = error_types.get('validation_error', 0) + 1
                low_quality_records += 1
        
        # Calculate quality score
        quality_rate = (high_quality_records / total_records * 100) if total_records > 0 else 0
        corruption_rate = (quality_metrics['corrupted'] / total_records * 100) if total_records > 0 else 0
        
        # Adjust quality score based on corruption
        quality_score = quality_rate - (corruption_rate * 2)  # Penalize corruption heavily
        quality_score = max(0, quality_score)  # Ensure non-negative
        
        # Calculate additional metrics
        size_stats = self._calculate_size_stats(quality_metrics['sizes'])
        resolution_stats = self._calculate_resolution_stats(quality_metrics['resolutions'])
        
        result = QualityValidationResult(
            test_name="photo_quality",
            total_records=total_records,
            valid_records=high_quality_records,
            invalid_records=low_quality_records,
            quality_score=quality_score,
            error_types=error_types,
            warning_types=warning_types,
            metadata={
                'quality_rate': quality_rate,
                'corruption_rate': corruption_rate,
                'format_distribution': quality_metrics['formats'],
                'size_stats': size_stats,
                'resolution_stats': resolution_stats,
                'valid_photos': quality_metrics['valid'],
                'corrupted_photos': quality_metrics['corrupted']
            }
        )
        
        self.logger.info(f"Photo quality validation completed: {quality_rate:.1f}% high quality, {corruption_rate:.1f}% corrupted")
        return result
    
    def validate_data_integrity(self, photo_mappings: Dict[str, str]) -> QualityValidationResult:
        """Validate overall data integrity"""
        self.logger.info("Validating data integrity...")
        
        total_records = len(photo_mappings)
        integrity_issues = 0
        error_types = {}
        warning_types = {}
        
        # Check for duplicates
        photo_values = list(photo_mappings.values())
        unique_values = set(photo_values)
        duplicate_count = len(photo_values) - len(unique_values)
        
        if duplicate_count > 0:
            error_types['duplicate_photos'] = duplicate_count
            integrity_issues += duplicate_count
        
        # Check for data corruption
        corrupted_count = 0
        for record_id, photo_data in photo_mappings.items():
            try:
                if photo_data.startswith('data:image/'):
                    # Try to decode and validate base64
                    comma_index = photo_data.find(',')
                    if comma_index != -1:
                        base64_part = photo_data[comma_index + 1:]
                        base64.b64decode(base64_part)
            except Exception:
                corrupted_count += 1
                error_types['corrupted_data'] = error_types.get('corrupted_data', 0) + 1
                integrity_issues += 1
        
        # Check for missing or invalid record IDs
        invalid_ids = 0
        for record_id in photo_mappings.keys():
            if not record_id or not str(record_id).strip():
                invalid_ids += 1
                error_types['invalid_record_id'] = error_types.get('invalid_record_id', 0) + 1
                integrity_issues += 1
        
        # Calculate integrity score
        integrity_rate = ((total_records - integrity_issues) / total_records * 100) if total_records > 0 else 0
        quality_score = integrity_rate
        
        result = QualityValidationResult(
            test_name="data_integrity",
            total_records=total_records,
            valid_records=total_records - integrity_issues,
            invalid_records=integrity_issues,
            quality_score=quality_score,
            error_types=error_types,
            warning_types=warning_types,
            metadata={
                'integrity_rate': integrity_rate,
                'duplicate_count': duplicate_count,
                'corrupted_count': corrupted_count,
                'invalid_id_count': invalid_ids,
                'unique_photos': len(unique_values)
            }
        )
        
        self.logger.info(f"Data integrity validation completed: {integrity_rate:.1f}% integrity")
        return result
    
    def _assess_photo_quality(self, metadata: Dict[str, Any]) -> float:
        """Assess photo quality based on metadata"""
        score = 100.0  # Start with perfect score
        
        # Size assessment
        if 'size_bytes' in metadata:
            size_mb = metadata['size_bytes'] / (1024 * 1024)
            if size_mb < 0.01:  # Very small
                score -= 20
            elif size_mb > 10:  # Very large
                score -= 10
        
        # Resolution assessment
        if 'size' in metadata:
            width, height = metadata['size']
            total_pixels = width * height
            
            if total_pixels < 10000:  # Very low resolution
                score -= 30
            elif total_pixels < 50000:  # Low resolution
                score -= 15
            elif total_pixels > 10000000:  # Very high resolution
                score -= 5
        
        # Color variance assessment
        if 'color_variance' in metadata:
            variance = metadata['color_variance']
            if variance < 5:  # Very low variance (possibly solid color)
                score -= 25
            elif variance < 15:  # Low variance
                score -= 10
        
        # Format assessment
        if 'format' in metadata:
            format_name = metadata['format'].lower()
            if format_name in ['jpeg', 'jpg']:
                score += 0  # Neutral
            elif format_name == 'png':
                score += 5  # Slightly better for quality
            else:
                score -= 5  # Less common formats
        
        return max(0, score)  # Ensure non-negative
    
    def _calculate_size_stats(self, sizes: List[int]) -> Dict[str, Any]:
        """Calculate size statistics"""
        if not sizes:
            return {}
        
        sizes_mb = [s / (1024 * 1024) for s in sizes]
        
        return {
            'count': len(sizes),
            'min_mb': min(sizes_mb),
            'max_mb': max(sizes_mb),
            'avg_mb': statistics.mean(sizes_mb),
            'median_mb': statistics.median(sizes_mb),
            'std_mb': statistics.stdev(sizes_mb) if len(sizes_mb) > 1 else 0
        }
    
    def _calculate_resolution_stats(self, resolutions: List[Tuple[int, int]]) -> Dict[str, Any]:
        """Calculate resolution statistics"""
        if not resolutions:
            return {}
        
        widths = [r[0] for r in resolutions]
        heights = [r[1] for r in resolutions]
        total_pixels = [w * h for w, h in resolutions]
        
        return {
            'count': len(resolutions),
            'min_width': min(widths),
            'max_width': max(widths),
            'avg_width': statistics.mean(widths),
            'min_height': min(heights),
            'max_height': max(heights),
            'avg_height': statistics.mean(heights),
            'min_pixels': min(total_pixels),
            'max_pixels': max(total_pixels),
            'avg_pixels': statistics.mean(total_pixels)
        }
    
    def run_all_validations(self, dataset_path: Path = None) -> List[QualityValidationResult]:
        """Run all data quality validations"""
        self.logger.info("Starting comprehensive data quality validation")
        
        if not self.setup_components():
            raise Exception("Failed to setup components for validation")
        
        # Load photo mappings
        photo_mappings = self.load_photo_mappings(dataset_path)
        
        if not photo_mappings:
            raise Exception("No photo data available for validation")
        
        self.logger.info(f"Loaded {len(photo_mappings):,} photo mappings for validation")
        
        all_results = []
        
        try:
            # 1. Data Completeness Validation
            completeness_result = self.validate_data_completeness(photo_mappings)
            all_results.append(completeness_result)
            
            # 2. Data Consistency Validation
            consistency_result = self.validate_data_consistency(photo_mappings)
            all_results.append(consistency_result)
            
            # 3. Photo Quality Validation
            quality_result = self.validate_photo_quality(photo_mappings)
            all_results.append(quality_result)
            
            # 4. Data Integrity Validation
            integrity_result = self.validate_data_integrity(photo_mappings)
            all_results.append(integrity_result)
            
            self.logger.info("All data quality validations completed successfully")
            
        except Exception as e:
            self.logger.error(f"Data quality validation suite failed: {e}")
            traceback.print_exc()
        
        return all_results
    
    def save_results(self, results: List[QualityValidationResult], filename: str = None):
        """Save validation results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_quality_results_{timestamp}.json"
        
        output_file = self.output_dir / filename
        
        # Convert results to serializable format
        serializable_results = [asdict(result) for result in results]
        
        # Add metadata
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'validation_summary': self.generate_summary(results),
            'results': serializable_results
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Data quality validation results saved to: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            return False
    
    def generate_summary(self, results: List[QualityValidationResult]) -> Dict[str, Any]:
        """Generate summary statistics from validation results"""
        if not results:
            return {}
        
        total_records = sum(r.total_records for r in results)
        total_valid = sum(r.valid_records for r in results)
        total_invalid = sum(r.invalid_records for r in results)
        
        # Calculate overall quality score
        quality_scores = [r.quality_score for r in results]
        overall_quality_score = statistics.mean(quality_scores) if quality_scores else 0
        
        # Collect all error and warning types
        all_error_types = {}
        all_warning_types = {}
        
        for result in results:
            for error_type, count in result.error_types.items():
                all_error_types[error_type] = all_error_types.get(error_type, 0) + count
            
            for warning_type, count in result.warning_types.items():
                all_warning_types[warning_type] = all_warning_types.get(warning_type, 0) + count
        
        return {
            'total_records_tested': total_records,
            'total_valid_records': total_valid,
            'total_invalid_records': total_invalid,
            'overall_validity_rate': (total_valid / total_records * 100) if total_records > 0 else 0,
            'overall_quality_score': overall_quality_score,
            'validation_categories': {
                result.test_name: {
                    'quality_score': result.quality_score,
                    'validity_rate': (result.valid_records / result.total_records * 100) if result.total_records > 0 else 0,
                    'error_count': len(result.error_types),
                    'warning_count': len(result.warning_types)
                }
                for result in results
            },
            'common_errors': dict(sorted(all_error_types.items(), key=lambda x: x[1], reverse=True)[:10]),
            'common_warnings': dict(sorted(all_warning_types.items(), key=lambda x: x[1], reverse=True)[:10])
        }


def main():
    """Main data quality validation execution"""
    parser = argparse.ArgumentParser(
        description="Data Quality Validation for UNS-CLAUDEJP 5.4 Photo Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                                    # Validate extracted photos
    %(prog)s --dataset photo_data.json          # Validate specific dataset
    %(prog)s --output results/                   # Save to specific directory
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--dataset',
        type=str,
        help='Dataset file path to validate (JSON format)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='data_quality_results',
        help='Output directory for results (default: data_quality_results)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_path = args.config
        config = load_config(config_path)
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get dataset path
        dataset_path = Path(args.dataset) if args.dataset else None
        
        print("UNS-CLAUDEJP 5.4 - Data Quality Validation")
        print("=" * 60)
        print(f"Output directory: {output_dir}")
        print(f"Dataset: {dataset_path or 'Extract from database'}")
        print(f"Configuration: {config_path or 'default'}")
        print()
        
        # Run validations
        validator = DataQualityValidator(config, output_dir)
        results = validator.run_all_validations(dataset_path)
        
        # Save results
        success = validator.save_results(results)
        
        if success:
            print("\nData quality validation completed successfully!")
            print(f"Results saved to: {output_dir}")
            
            # Print summary
            summary = validator.generate_summary(results)
            print(f"\nSummary:")
            print(f"  Total records tested: {summary['total_records_tested']:,}")
            print(f"  Overall validity rate: {summary['overall_validity_rate']:.1f}%")
            print(f"  Overall quality score: {summary['overall_quality_score']:.1f}/100")
            
            print(f"\nValidation Categories:")
            for category, cat_summary in summary['validation_categories'].items():
                print(f"  {category.replace('_', ' ').title()}:")
                print(f"    Quality Score: {cat_summary['quality_score']:.1f}/100")
                print(f"    Validity Rate: {cat_summary['validity_rate']:.1f}%")
                print(f"    Errors: {cat_summary['error_count']}")
                print(f"    Warnings: {cat_summary['warning_count']}")
            
            if summary['common_errors']:
                print(f"\nCommon Errors:")
                for error_type, count in list(summary['common_errors'].items())[:5]:
                    print(f"  {error_type}: {count}")
            
            if summary['common_warnings']:
                print(f"\nCommon Warnings:")
                for warning_type, count in list(summary['common_warnings'].items())[:5]:
                    print(f"  {warning_type}: {count}")
            
            return 0
        else:
            print("ERROR: Failed to save validation results")
            return 1
    
    except KeyboardInterrupt:
        print("\nData quality validation interrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)