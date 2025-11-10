"""
Business Logic Services for UNS-ClaudeJP 5.2

This module exports all service classes for dependency injection.
Use: from app.services import AuthService, HybridOCRService

Services:
- AuthService: JWT authentication and user management
- AzureOCRService: Azure Computer Vision OCR integration
- EasyOCRService: Deep learning-based OCR (offline)
- FaceDetectionService: MediaPipe face detection for photo verification
- HybridOCRService: Multi-provider OCR orchestration
- ImportService: Excel/CSV data import utilities
- NotificationService: Email and LINE notifications
- PayrollService: Salary calculation and payroll processing
- ReportService: PDF report generation
"""

from app.services.auth_service import AuthService
from app.services.azure_ocr_service import AzureOCRService
from app.services.easyocr_service import EasyOCRService
from app.services.face_detection_service import FaceDetectionService
from app.services.hybrid_ocr_service import HybridOCRService
from app.services.import_service import ImportService
from app.services.notification_service import NotificationService
from app.services.payroll_service import PayrollService
from app.services.report_service import ReportService

__all__ = [
    "AuthService",
    "AzureOCRService",
    "EasyOCRService",
    "FaceDetectionService",
    "HybridOCRService",
    "ImportService",
    "NotificationService",
    "PayrollService",
    "ReportService",
]
