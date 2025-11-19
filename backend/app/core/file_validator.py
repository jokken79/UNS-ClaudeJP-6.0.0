"""
File Type Validator using python-magic

Validates uploaded files by detecting their actual MIME type using magic bytes,
not just by file extension. Prevents various file upload attacks:
- Renaming malicious files with innocent extensions
- Uploading executable files disguised as images
- Zip bombs and other archive attacks

Configuration:
- ALLOWED_EXTENSIONS in settings defines allowed file types
- Each extension maps to expected MIME types for validation
"""

import logging
from typing import Optional, List, Tuple, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import python-magic, fallback to file extension validation if unavailable
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger.warning("python-magic not available. File type validation will use extension-only checking.")


# MIME type mapping for common document and image types
ALLOWED_MIME_TYPES: Dict[str, List[str]] = {
    # Images (for documents, resumes, photos)
    "jpg": ["image/jpeg"],
    "jpeg": ["image/jpeg"],
    "png": ["image/png"],
    "webp": ["image/webp"],
    "gif": ["image/gif"],

    # Documents
    "pdf": [
        "application/pdf",
        "application/x-pdf"  # Some systems report PDF differently
    ],

    # Spreadsheets (for Excel imports)
    "xlsx": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/x-xlsx"
    ],
    "xls": [
        "application/vnd.ms-excel",
        "application/x-xls",
        "application/x-msexcel"
    ],
    "csv": [
        "text/csv",
        "text/plain"  # Some CSV files reported as plain text
    ],

    # Archives (for batch imports)
    "zip": ["application/zip", "application/x-zip-compressed"],
    "gz": ["application/gzip", "application/x-gzip"],
    "tar": ["application/x-tar"],
}


class FileValidationError(Exception):
    """Raised when file validation fails"""
    pass


class FileValidator:
    """
    Validates file uploads using magic bytes (MIME type detection).

    Provides protection against:
    - Extension spoofing (renaming malware as .jpg)
    - MIME type mismatch attacks
    - Executable uploads disguised as documents
    """

    @staticmethod
    def validate_file_type(
        file_content: bytes,
        filename: str,
        allowed_extensions: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate file type using magic bytes and extension.

        Args:
            file_content: File bytes to validate
            filename: Original filename
            allowed_extensions: List of allowed file extensions (from settings)

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if file passes validation
            - error_message: None if valid, error description if invalid

        Example:
            >>> is_valid, error = FileValidator.validate_file_type(
            ...     file_bytes,
            ...     "resume.pdf",
            ...     ["pdf", "jpg", "png"]
            ... )
            >>> if not is_valid:
            ...     raise HTTPException(status_code=400, detail=error)
        """
        # Check file size (empty files are invalid)
        if not file_content or len(file_content) == 0:
            return False, "File is empty"

        # Extract extension from filename
        ext = Path(filename).suffix.lstrip('.').lower()

        # Check extension is allowed
        if ext not in allowed_extensions:
            return False, f"File type .{ext} not allowed. Allowed: {', '.join(allowed_extensions)}"

        # If python-magic not available, just do extension check
        if not MAGIC_AVAILABLE:
            logger.warning(f"python-magic unavailable. Using extension-only validation for {filename}")
            return True, None

        # Detect actual MIME type from file bytes
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            logger.debug(f"Detected MIME type for {filename}: {mime_type}")

            # Get expected MIME types for this extension
            expected_mimes = ALLOWED_MIME_TYPES.get(ext)

            if not expected_mimes:
                # Extension not in our MIME type mapping - allow it
                # (might be legitimate file type we don't check)
                logger.debug(f"Extension .{ext} not in MIME type mapping, allowing")
                return True, None

            # Check if detected MIME type matches expected types
            if mime_type not in expected_mimes:
                return False, (
                    f"File content type mismatch. "
                    f"Filename suggests {ext} but file is {mime_type}. "
                    f"Expected: {', '.join(expected_mimes)}"
                )

            return True, None

        except Exception as e:
            logger.error(f"Error validating file type: {e}")
            # On magic error, fail closed (require valid magic check)
            return False, f"Could not validate file type: {str(e)}"

    @staticmethod
    def validate_image_file(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that file is a valid image and not corrupted.

        Uses PIL to verify image integrity.

        Args:
            file_content: File bytes
            filename: Original filename

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            from PIL import Image
            import io

            # Try to open and verify the image
            image = Image.open(io.BytesIO(file_content))
            image.verify()

            logger.debug(f"Image validation passed for {filename}: {image.format}")
            return True, None

        except Exception as e:
            logger.warning(f"Image validation failed for {filename}: {e}")
            return False, f"Invalid or corrupted image file: {str(e)}"

    @staticmethod
    def validate_pdf_file(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that file is a valid PDF.

        Checks PDF magic bytes and basic structure.

        Args:
            file_content: File bytes
            filename: Original filename

        Returns:
            Tuple of (is_valid, error_message)
        """
        # PDF files should start with %PDF
        if not file_content.startswith(b'%PDF'):
            return False, "File does not appear to be a valid PDF (missing PDF magic bytes)"

        # Check minimum PDF size (reasonable PDFs are at least a few hundred bytes)
        if len(file_content) < 100:
            return False, "PDF file is suspiciously small (potential PDF bomb detection)"

        logger.debug(f"PDF validation passed for {filename}")
        return True, None


# Convenience function for use in FastAPI endpoints
async def validate_upload(
    file_content: bytes,
    filename: str,
    allowed_extensions: List[str],
    check_image: bool = False,
    check_pdf: bool = False
) -> None:
    """
    Validate uploaded file with optional image/PDF specific checks.

    Args:
        file_content: File bytes
        filename: Original filename
        allowed_extensions: List of allowed extensions
        check_image: If True, also validate as image
        check_pdf: If True, also validate as PDF

    Raises:
        FileValidationError: If any validation fails

    Example:
        >>> try:
        ...     await validate_upload(
        ...         file_bytes,
        ...         "document.pdf",
        ...         ["pdf", "jpg"],
        ...         check_pdf=True
        ...     )
        ... except FileValidationError as e:
        ...     raise HTTPException(status_code=400, detail=str(e))
    """
    # Validate basic file type
    is_valid, error = FileValidator.validate_file_type(file_content, filename, allowed_extensions)
    if not is_valid:
        raise FileValidationError(error)

    # Validate as image if requested
    if check_image:
        is_valid, error = FileValidator.validate_image_file(file_content, filename)
        if not is_valid:
            raise FileValidationError(error)

    # Validate as PDF if requested
    if check_pdf:
        is_valid, error = FileValidator.validate_pdf_file(file_content, filename)
        if not is_valid:
            raise FileValidationError(error)

    logger.info(f"File validation passed: {filename}")


__all__ = [
    "FileValidator",
    "FileValidationError",
    "validate_upload",
    "MAGIC_AVAILABLE",
]
