# File Validation Implementation Guide

## Overview

The new `FileValidator` module provides MIME type validation using magic bytes detection to prevent file upload attacks. This guide shows how to integrate it into file upload endpoints.

## Installation

Add python-magic to requirements.txt:
```bash
python-magic==0.4.27
```

Or on Ubuntu/Debian:
```bash
pip install python-magic
apt-get install libmagic1  # System library required for python-magic
```

## Usage in Endpoints

### Basic Example (Candidates API)

```python
from app.core.file_validator import validate_upload, FileValidationError, MAGIC_AVAILABLE

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_auth)
):
    # Read file content
    file_content = await file.read()

    # Validate file type using magic bytes
    try:
        check_image = file.filename.endswith(('.jpg', '.jpeg', '.png'))
        await validate_upload(
            file_content,
            file.filename,
            settings.ALLOWED_EXTENSIONS,
            check_image=check_image
        )
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save file...
```

### Endpoints That Need Updates

The following endpoints handle file uploads and should be updated:

1. **candidates.py**
   - `POST /{candidate_id}/upload` - Already updated ✓
   - `POST /{candidate_id}/upload_rirekisho` - Needs update

2. **timer_cards.py**
   - `POST /upload` - Handles Excel/CSV imports

3. **import_export.py**
   - `POST /import` - Bulk data import
   - `POST /import-employees` - Employee import

4. **database.py**
   - `POST /import` - Database management imports

5. **azure_ocr.py**
   - `POST /process` - Image OCR processing (lines 63, 148)

6. **employees.py**
   - `POST /upload-excel` - Employee Excel upload

7. **resilient_import.py**
   - Multiple import endpoints

## Magic Bytes Validation

The validator checks file content using "magic bytes" - the first few bytes of a file that identify its type, regardless of extension.

### Supported MIME Types

**Images:**
- `.jpg/.jpeg`: `image/jpeg`
- `.png`: `image/png`
- `.webp`: `image/webp`
- `.gif`: `image/gif`

**Documents:**
- `.pdf`: `application/pdf`

**Spreadsheets:**
- `.xlsx`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `.xls`: `application/vnd.ms-excel`
- `.csv`: `text/csv`

**Archives:**
- `.zip`: `application/zip`

## Security Benefits

### Prevents These Attacks

1. **Extension Spoofing**
   - Upload malware.exe renamed as malware.jpg
   - Validator detects actual file type

2. **MIME Type Mismatch**
   - Zip bomb with .pdf extension
   - Double extension files (file.php.jpg)

3. **Executable Uploads**
   - .exe, .bat, .ps1 files disguised as safe types

4. **Polyglot Files**
   - Files valid as multiple types
   - Validator rejects mismatches

## Configuration

### Environment Variables

No special env vars needed. The validator uses `settings.ALLOWED_EXTENSIONS` from config.py

### Fallback Behavior

If python-magic is not installed:
- Extension-only validation is performed
- Warning logged to indicate reduced security
- System remains functional but less secure

## Logging

File validation is logged at INFO level:
```
INFO: File validation passed for resume.pdf (magic: enabled)
WARNING: python-magic not available. Using extension-only validation
ERROR: File validation failed: File does not appear to be a valid PDF
```

## Testing

```python
from app.core.file_validator import FileValidator

# Test valid PDF
with open("valid.pdf", "rb") as f:
    is_valid, error = FileValidator.validate_file_type(
        f.read(),
        "test.pdf",
        ["pdf", "jpg"]
    )
    assert is_valid
    assert error is None

# Test spoofed file (malware renamed as PDF)
malware_as_pdf = b"MZ\x90\x00..."  # EXE header
is_valid, error = FileValidator.validate_file_type(
    malware_as_pdf,
    "virus.pdf",
    ["pdf"]
)
assert not is_valid
assert "content type mismatch" in error.lower()
```

## Performance Considerations

- Magic detection adds ~1-5ms per file
- Minimal overhead for typical use cases
- Validation happens before file is saved to disk
- Large files (>10MB) are rejected before validation

## Next Steps

1. Install python-magic in requirements.txt
2. Update remaining file upload endpoints (see list above)
3. Test with valid and spoofed files
4. Monitor logs for validation errors

## References

- python-magic docs: https://github.com/ahupp/python-magic
- File magic numbers: https://en.wikipedia.org/wiki/List_of_file_signatures
