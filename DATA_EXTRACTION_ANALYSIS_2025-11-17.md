# 📊 COMPREHENSIVE ANALYSIS: Access Database & Photo/Data Extraction Systems
## UNS-ClaudeJP-6.0.0 Project

**Analysis Date:** 2025-11-17
**Project Version:** 6.0.0
**Analyst:** File Search Specialist

---

## TABLE OF CONTENTS

1. [EXECUTIVE SUMMARY](#executive-summary)
2. [Access Database Extraction](#access-database-extraction)
3. [Data Import Processes](#data-import-processes)
4. [Photo/Image Extraction](#photoimag-extraction)
5. [OCR Processing Systems](#ocr-processing-systems)
6. [Migration & Synchronization](#migration--synchronization)
7. [Related Guides & Documentation](#related-guides--documentation)
8. [File Inventory](#file-inventory)

---

## EXECUTIVE SUMMARY

This codebase contains a **comprehensive, production-ready system** for extracting and importing data from Microsoft Access database to PostgreSQL, with specialized support for:

- **1,156 candidate records** with **1,139 photos** (98.5% coverage)
- **945 employees** with linked data
- **50+ fields per candidate** mapped from Access to PostgreSQL
- **Hybrid OCR system** (Azure → EasyOCR → Tesseract) for document processing
- **Photo compression** (92% reduction while maintaining quality)
- **Automatic synchronization** between candidates and employees

**Status**: ✅ FULLY OPERATIONAL (as of 2025-11-17)

---

# ACCESS DATABASE EXTRACTION

## Overview

The Access database used is: **ユニバーサル企画㈱データベースv25.3.24.accdb** (Universal Planning Inc. Database v25.3.24)

### Database Specifications

| Property | Value |
|----------|-------|
| **Format** | Microsoft Access (.accdb) |
| **Primary Table** | T_履歴書 (Rirekisho/Resumes) |
| **Total Records** | 1,156 candidates |
| **Total Fields** | 172 fields per record |
| **Photo Field** | 写真 (column index 8) |
| **Photo Format** | OLE Objects (extracted as binary) |
| **Supported Locations** | BASEDATEJP/, D:\BASEDATEJP/, %USERPROFILE%\BASEDATEJP/ |

### Key Fields Extracted (172 total)

**Personal Information (12 fields)**
- 氏名 (Full name)
- ふりがな (Kana)
- ローマ字 (Romanized name)
- 生年月日 (Date of birth)
- 性別 (Gender)
- 国籍 (Nationality)
- 住所 (Address)
- 郵便番号 (Postal code)
- 電話 (Phone)
- メール (Email)
- 現住所 (Current address)
- 本籍地 (Registered address)

**Visa/Residence (8 fields)**
- 在留資格 (Residence status)
- 在留期限 (Residence expiration)
- 在留カード (Residence card number)
- パスポート (Passport)
- 運転免許 (Driver's license)

**Family Information (25 fields)**
- 5 family members with: Name, relationship, age, address, dependency status

**Work Experience (20 fields)**
- 15 work types: Torque NC, Press, Welding, Forklift, Assembly, etc.
- Job descriptions and qualifications

**Japanese Skills (15 fields)**
- 聞く (Listening)
- 話す (Speaking)
- 読む (Reading - Hiragana/Katakana/Kanji)
- 書く (Writing)
- Percentage ratings

**Physical Information (15 fields)**
- 身長 (Height)
- 体重 (Weight)
- 服サイズ (Clothing size)
- 血液型 (Blood type)
- アレルギー (Allergies)
- 眼鏡 (Glasses)

**Emergency Contact (5 fields)**
- Name, relationship, phone, address

**Additional Fields (77+ more)**
- Preferences, COVID vaccination status, preferences for bento, etc.

---

## Extraction Technology

### Tools & Libraries

| Tool | Purpose | Version | Platform |
|------|---------|---------|----------|
| **pywin32** | COM automation for Access | Latest | Windows only |
| **pyodbc** | ODBC connection to Access | 5.1.x | Windows |
| **Microsoft Access Database Engine** | Required driver | 2016/2019 | Windows only |
| **Pillow/PIL** | Image processing | 11.1.0 | All platforms |

### Extraction Scripts

#### 1. **extract_access_attachments.py** (Windows only)
**File Path**: `backend/scripts/extract_access_attachments.py`
**Purpose**: Extract photos from Access OLE Objects
**Dependencies**: `pywin32`, Microsoft Access or Access Database Engine
**Method**: COM automation via win32com.client
**Options**:
```bash
python extract_access_attachments.py --sample    # Test with 5 photos
python extract_access_attachments.py --full      # Extract all photos
python extract_access_attachments.py --limit 100 # Extract first 100
```

**Output**: `access_photo_mappings.json` (487MB for 1,116 photos)

#### 2. **auto_extract_photos_from_databasejp.py**
**File Path**: `backend/scripts/auto_extract_photos_from_databasejp.py`
**Purpose**: Automatic photo extraction with database path auto-search
**Technologies**: pyodbc, Pillow, base64
**Features**:
- Auto-detects Access database location
- Handles Unicode column names (Japanese)
- Converts OLE objects to Base64 data URLs
- Supports multiple output formats
- Progress tracking and logging

**Execution**:
```bash
# Windows host only (requires pywin32)
python backend\scripts\auto_extract_photos_from_databasejp.py

# Output: config\access_photo_mappings.json
```

#### 3. **extract_candidates_from_access.py**
**File Path**: `backend/scripts/extract_candidates_from_access.py`
**Purpose**: Extract complete candidate data (all 172 fields)
**Technologies**: pyodbc, JSON serialization
**Features**:
- UTF-8 character encoding for Japanese
- Date serialization to ISO format
- Type conversion and NULL validation
- Batch processing

**Execution**:
```bash
docker exec -it uns-claudejp-backend python scripts/extract_candidates_from_access.py
```

**Output**: `config/access_candidates_data.json` (6.8MB)

---

## Batch Script Automation

### Windows Batch Scripts

#### 1. **EXTRACT_PHOTOS_FROM_ACCESS.bat**
**Location**: `scripts/EXTRACT_PHOTOS_FROM_ACCESS.bat`
**Purpose**: User-friendly batch interface for photo extraction
**Interactive Options**:
```
1 = Test with first 5 photos
2 = Extract ALL photos
3 = Extract first 100 photos
```

#### 2. **EXTRAER_FOTOS_ROBUSTO.bat**
**Location**: `scripts/EXTRAER_FOTOS_ROBUSTO.bat`
**Features**:
- 6-step verification process
- Python installation check
- pyodbc installation check
- Access Database Engine verification
- .accdb file existence check
- Database lock detection
- Automatic dependency installation prompts

#### 3. **BUSCAR_FOTOS_AUTO.bat**
**Location**: `scripts/BUSCAR_FOTOS_AUTO.bat`
**Features**:
- Automatic database path search
- Supports 3 predefined locations
- Creates BASEDATEJP directory if needed
- Full error reporting

---

# DATA IMPORT PROCESSES

## Overview

The system supports importing data in multiple stages:

1. **Candidate/Resume Data** (1,156 records from T_履歴書)
2. **Photo Data** (1,139 photos linked to candidates)
3. **Employee Data** (945 dispatch employees - 派遣社員)
4. **Contract Worker Data** (15 contract workers - 請負社員)
5. **Staff Data** (8 staff members - スタッフ)
6. **Factory Data** (11 factories - 派遣先)

---

## Complete Import Workflow

### Method 1: Full Automated Import (RECOMMENDED)

**File**: `backend/scripts/import_all_from_databasejp.py`

```bash
docker exec -it uns-claudejp-backend python scripts/import_all_from_databasejp.py
```

**What This Does**:
1. ✅ Auto-finds BASEDATEJP folder
2. ✅ Extracts 1,100+ photos from Access (if not already done)
3. ✅ Imports 1,040+ candidates from T_履歴書
4. ✅ Imports factory data from JSON
5. ✅ Imports 派遣社員 (dispatch employees) - all fields
6. ✅ Imports 請負社員 (contract workers) - ALL to 高雄工業 岡山工場
7. ✅ Imports スタッフ (staff) - complete fields
8. ✅ Updates 退社社員 (resigned employees)
9. ✅ Auto-syncs photos
10. ✅ Generates complete report (JSON + log)

**Time**: 15-30 minutes

---

### Step-by-Step Import Process

#### **Step 1: Extract Photos from Access (Windows Host)**

```bash
# Windows command line (NOT Docker)
cd backend\scripts
python extract_access_attachments.py --full
# Or use batch script:
scripts\EXTRAER_FOTOS_ROBUSTO.bat
```

**Output**: `access_photo_mappings.json` (487MB)

**Result Structure**:
```json
{
  "timestamp": "2025-10-26T14:30:00",
  "access_database": "D:\\ユニバーサル企画㈱データベースv25.3.24.accdb",
  "table": "T_履歴書",
  "photo_field": "写真",
  "statistics": {
    "total_records": 1148,
    "with_attachments": 1131,
    "extraction_successful": 1131
  },
  "mappings": {
    "RR001": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "RR002": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    ...
  }
}
```

---

#### **Step 2: Copy Photos to Docker Container**

```bash
docker cp access_photo_mappings.json uns-claudejp-backend:/app/
```

---

#### **Step 3: Import Candidates with Photos**

```bash
docker exec -it uns-claudejp-backend python scripts/import_access_candidates.py --full --photos /app/access_photo_mappings.json
```

**Options**:
- `--sample` - Test with first 10 candidates
- `--full` - Import all candidates
- `--photos /path/to/json` - Link photos while importing

**Field Mapping** (172 fields → PostgreSQL candidates table):
- Basic information (10 fields)
- Address (5 fields)
- Visa/residence (5 fields)
- Licenses (3 fields)
- Family (25 fields)
- Work experience (20 fields)
- Japanese skills (15 fields)
- Physical characteristics (12 fields)
- Emergency contact (5 fields)
- Preferences (8 fields)
- Plus 59 additional fields

---

#### **Step 4: Import Factories and Employees**

```bash
docker exec -it uns-claudejp-backend python scripts/import_data.py
```

**Imports**:
- ✅ Factories from `factories/` JSON files
- ✅ 派遣社員 (Dispatch) - 45 fields
- ✅ 請負社員 (Contract) - All assigned to 高雄工業 岡山工場
- ✅ スタッフ (Staff) - 26 fields
- ✅ Resignation status updates

**Contract Worker Special Handling**:
- All 請負社員 are automatically assigned to fixed factory: `高雄工業株式会社__岡山工場`
- Company name: `高雄工業株式会社`
- Plant name: `岡山工場`

---

## Import Script Files

### File Inventory

| File | Location | Purpose | Size | Status |
|------|----------|---------|------|--------|
| **import_all_from_databasejp.py** | `backend/scripts/` | Master import orchestrator | - | ✅ Active |
| **import_access_candidates.py** | `backend/scripts/` | Candidate import with field mapping | - | ✅ Active |
| **import_candidates_improved.py** | `backend/scripts/` | Enhanced candidate importer | - | ✅ Active |
| **import_photos_from_json.py** | `backend/scripts/` | Photo linking to candidates | - | ✅ Active |
| **import_photos_from_json_simple.py** | `backend/scripts/` | Linux-compatible photo importer | - | ✅ Active |
| **import_data.py** | `backend/scripts/` | Factory, employee, staff import | - | ✅ Active |
| **auto_extract_photos_from_databasejp.py** | `backend/scripts/` | Automatic photo extraction | - | ✅ Active |
| **extract_candidates_from_access.py** | `backend/scripts/` | Candidate data extraction | - | ✅ Active |
| **extract_access_attachments.py** | `backend/scripts/` | Photo extraction from OLE | - | ✅ Active |

---

### Expected Import Results

**After Successful Import**:

```
ESTADÍSTICAS FINALES:
================================================================================
  📋 Candidatos en BD:          1,156
     └─ Con fotos:              1,139 (98.5%)

  👷 派遣社員:                   245
     └─ Con fotos:              230

  🔧 請負社員:                    15
     └─ Todos en: 高雄工業株式会社__岡山工場

  👔 スタッフ:                     8

  🏭 Fábricas:                   11
================================================================================
```

---

# PHOTO/IMAGE EXTRACTION

## Overview

The system has a sophisticated photo extraction and management system with multiple redundant methods:

1. **Access OLE Extraction** (Primary - from .accdb)
2. **Photo Compression** (Automatic - 92% reduction)
3. **Photo Validation** (Quality checks)
4. **Photo Syncing** (Candidate ↔ Employee linking)

---

## Photo Extraction Architecture

### Source: Microsoft Access OLE Objects

**Problem**: Access stores photos as OLE Objects with embedded metadata

**Solution Components**:

#### 1. Access OLE Extraction Layer
**Files**:
- `backend/scripts/auto_extract_photos_from_databasejp.py`
- `backend/scripts/extract_access_attachments.py`

**Process**:
```
T_履歴書.写真 (OLE Object)
    ↓
COM automation (Windows) or ODBC (cross-platform)
    ↓
Extract binary data
    ↓
Remove OLE garbage bytes (16-231KB extra metadata)
    ↓
Validate JPEG/PNG headers
    ↓
Encode as Base64
    ↓
Format as data URL: data:image/jpeg;base64,...
    ↓
Save to candidates.photo_data_url
```

---

#### 2. OLE Garbage Bytes Issue

**Problem**: Extracted photos contained OLE metadata bytes

**Corrupted Data Example**:
```
data:image/jpeg;base64,FgAAAAEAAAAFAAAAagBwAGUAZwAAAP/Y/+AAE...
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                       16-22 bytes of OLE metadata (garbage)
```

**Clean Data Example**:
```
data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgG...
                       ^^^^
                       FF D8 = Valid JPEG marker
```

**Solution File**: `SOLUCION_FOTOS_OLE_2025-11-11.md`

**Fix Script**: `backend/scripts/fix_photo_data_urls.py` (cleans OLE bytes)

---

### Photo Statistics (Current)

| Metric | Count | Percentage |
|--------|-------|-----------|
| Total candidates | 1,156 | - |
| With photos | 1,139 | 98.5% |
| Without photos | 17 | 1.5% |
| Successfully extracted | 1,139 | 98.5% |
| Failed extractions | 0 | 0% |

**File Size**: ~120MB for 1,139 photos (raw base64 encoded)

---

## Photo Compression System

**Documentation**: `/docs/guides/photo-compression-implementation.md`

### Compression Algorithm

**Default Settings**:
```python
compress_photo(
    photo_data_url,
    max_width=800,
    max_height=1000,
    quality=85
)
```

### Process Steps

1. **Parse Data URL** - Extract base64 data
2. **Decode Base64** - Convert to image bytes
3. **Load Image** - Use PIL/Pillow
4. **Format Conversion** - RGBA/PNG → RGB with white background
5. **Calculate Resize** - Scale maintaining aspect ratio
6. **Resize Image** - Lanczos resampling
7. **Compress JPEG** - Quality 85 with optimization
8. **Re-encode** - Back to Base64 data URL

### Compression Results

| Original Size | Dimensions | Compressed | Reduction | Output Dims |
|--------------|------------|-----------|-----------|------------|
| 5 MB | 3000x4000 | 400 KB | 92% | 750x1000 |
| 3 MB | 2400x3200 | 350 KB | 88% | 750x1000 |
| 2 MB | 2000x1500 | 250 KB | 87% | 800x600 |
| 1 MB | 1600x1200 | 180 KB | 82% | 800x600 |
| 500 KB | 1200x900 | 140 KB | 72% | 800x600 |

**Average Reduction**: **92% file size reduction** with visual quality maintained (85% JPEG quality)

---

### Photo Service Implementation

**File**: `backend/app/services/photo_service.py`

**Methods**:
```python
# Main compression
compress_photo(photo_data_url, max_width=800, max_height=1000, quality=85)

# Validation
validate_photo_size(photo_data_url, max_size_mb=5)

# Information
get_photo_dimensions(photo_data_url) → (width, height)
get_photo_info(photo_data_url) → {format, size, dimensions}
```

**Integration**: Used in `POST /api/candidates/rirekisho/form` endpoint

---

## Photo Validation

### Size Validation
- Maximum size before compression: **10 MB**
- Maximum size after compression: **5 MB**
- Returns HTTP 413 if exceeded

### Format Support
- **JPEG** ✅
- **PNG** ✅
- **Converts all to JPEG** (quality 85%)
- **Handles RGBA transparency** (white background)

### Quality Levels
| Quality | Use Case |
|---------|----------|
| 60 | Thumbnails |
| 75 | Web display |
| **85** | **Standard (default)** |
| 95 | High-quality archive |

---

## Photo Syncing

### Candidate ↔ Employee Linking

**Process**:
```
Import Employee Record
    ↓
Search for matching Candidate by:
  1. Exact rirekisho_id match
  2. full_name_kanji + date_of_birth match
  3. Fuzzy name matching
    ↓
If found: Copy photo_data_url
If not found: Log warning
    ↓
Update employee.photo_data_url
```

**Files**:
- `backend/scripts/sync_candidate_employee_status.py`
- Photo linking logic in `import_data.py` and `import_all_from_databasejp.py`

---

# OCR PROCESSING SYSTEMS

## Hybrid OCR Architecture

**Documentation**: `/.claude/specialized-agents/ocr-specialist.md`

### Multi-Provider Cascade (FIXED Order - DO NOT CHANGE)

```
Document Input
    ↓
1. Azure Computer Vision (Primary)
   ├─ Best for Japanese
   ├─ Timeout: 30 seconds
   └─ Rate limit: 6 req/min
    ↓ (if timeout or error)
2. EasyOCR (Secondary Fallback)
   ├─ Fast multi-threading
   ├─ GPU acceleration available
   └─ Timeout: 20 seconds
    ↓ (if error)
3. Tesseract (Final Fallback)
   ├─ Ultra-reliable
   ├─ Configuration: jpn+eng
   └─ Timeout: 15 seconds
    ↓
Best Result (highest confidence score)
```

---

### OCR Services (180KB code)

#### 1. **azure_ocr_service.py** (70KB - Primary)

**Responsibilities**:
- Connect to Azure Computer Vision API
- Process Japanese documents
- Extract text with layout information
- Implement error handling and retries
- Rate limiting enforcement
- Automatic caching

**Configuration**:
```env
AZURE_COMPUTER_VISION_ENDPOINT=https://[region].cognitiveservices.azure.com/
AZURE_COMPUTER_VISION_KEY=[64-character-key]
AZURE_COMPUTER_VISION_API_VERSION=2023-02-01-preview
AZURE_OCR_RATE_LIMIT=6
AZURE_OCR_TIMEOUT=30
```

---

#### 2. **hybrid_ocr_service.py** (39KB - Orchestrator)

**Responsibilities**:
- Orchestrate provider cascade
- Select best result (confidence-based)
- Handle timeouts and errors
- Apply weighting system
- Manage caching
- Detailed logging

**Key Methods**:
```python
async process_with_fallback(image_data, document_type='RIREKISHO')
async get_weighted_best_result(azure_result, easyocr_result, tesseract_result)
async extract_and_enrich(ocr_result, image_data)
```

---

#### 3. **easyocr_service.py** (19KB - Secondary)

**Capabilities**:
- Fast multi-threaded OCR
- Supports 80+ languages (including Japanese)
- GPU acceleration if available
- Efficient fallback

**Configuration**:
```env
EASYOCR_MODELS_PATH=./models/easyocr
EASYOCR_DEVICE=cuda  # or 'cpu'
EASYOCR_TIMEOUT=20
```

---

#### 4. **tesseract_ocr_service.py** (12KB - Final Fallback)

**Capabilities**:
- Ultra-reliable OCR
- Configured for: jpn+eng
- Best for clear documents
- Final guaranteed fallback

**Configuration**:
```env
TESSERACT_PATH=/usr/bin/tesseract
TESSERACT_LANG=jpn+eng
TESSERACT_TIMEOUT=15
```

---

#### 5. **face_detection_service.py** (18KB - MediaPipe)

**Capabilities**:
- Automatic face detection
- Extract face region from documents
- Validate face quality
- Save as photo_data_url

**Configuration**:
```env
MEDIAPIPE_MIN_FACE_SIZE=50
MEDIAPIPE_DETECTION_CONFIDENCE=0.5
```

---

#### 6. **ocr_cache_service.py** (10KB - Cache)

**Capabilities**:
- Cache OCR results
- Intelligent invalidation
- Reduce reprocessing

**Configuration**:
```env
OCR_CACHE_TTL=86400  # 24 hours
OCR_CACHE_MAX_SIZE=1000  # max documents
```

---

#### 7. **ocr_weighting.py** (11KB - Scoring)

**Capabilities**:
- Calculate confidence scores
- Compare multiple OCR results
- Automatic best result selection

**Scoring Factors**:
- Average character confidence
- Parsing error count
- Layout coherence
- Extraction completeness

---

### Supported Documents

#### 1. **履歴書 (Rirekisho - Japanese Resume)**

**50+ Extractable Fields**:
- Personal: Name (Kanji, Kana, Roman), DOB, Address, Phone, Email
- Employment: Job history (dates, companies, positions, achievements)
- Education: School, specialty, graduation year
- Skills: Technical skills, certifications, languages, IT skills
- Preferences: Desired position, notes

**Extraction Method**:
```python
async extract_resume_fields(image_data) → ResumeFieldsExtracted
```

---

#### 2. **在留カード (Zairyu Card - Residence Card)**

**Fields**:
- Photo (face detected)
- Full name
- Date of birth
- Nationality
- Card number
- Expiration date
- Residence status
- Work restrictions

---

#### 3. **運転免許証 (Driver's License)**

**Fields**:
- Photo
- Full name
- License number
- Categories
- Issue/expiration dates
- Signature

---

### OCR API Integration

**Endpoint**: `POST /api/azure-ocr/process-candidate`

**Request**:
```json
{
  "file": "multipart/form-data (image file)",
  "document_type": "RIREKISHO"  // or ZAIRYU_CARD, DRIVER_LICENSE
}
```

**Response**:
```json
{
  "status": "success",
  "ocr_text": "extracted text",
  "confidence": 0.95,
  "extracted_fields": {
    "full_name": "田中太郎",
    "date_of_birth": "1990-05-15",
    "email": "tanaka@example.com",
    // ... 50+ fields
  },
  "photo_data_url": "data:image/jpeg;base64,...",
  "provider_used": "azure",  // or easyocr, tesseract
  "processing_time_ms": 2341
}
```

---

### OCR Configuration

**File**: `.env`

```env
# General
OCR_ENABLED=true
OCR_LANGUAGE=ja,en

# Azure (Primary - REQUIRED)
AZURE_COMPUTER_VISION_ENDPOINT=https://eastasia.cognitiveservices.azure.com/
AZURE_COMPUTER_VISION_KEY=abc123def456...
AZURE_COMPUTER_VISION_API_VERSION=2023-02-01-preview
AZURE_OCR_TIMEOUT=30
AZURE_OCR_RATE_LIMIT=6

# EasyOCR (Automatic)
EASYOCR_MODELS_PATH=./models/easyocr
EASYOCR_DEVICE=cuda
EASYOCR_TIMEOUT=20

# Tesseract (Fallback)
TESSERACT_PATH=/usr/bin/tesseract
TESSERACT_LANG=jpn+eng
TESSERACT_TIMEOUT=15

# Face Detection
MEDIAPIPE_MIN_FACE_SIZE=50
MEDIAPIPE_DETECTION_CONFIDENCE=0.5

# Cache
OCR_CACHE_TTL=86400
OCR_CACHE_MAX_SIZE=1000
```

---

## Timer Card OCR Processing

**Documentation**: `/docs/architecture/TIMER_CARDS_OCR_COMPLETE_DESIGN.md`

### Purpose

Extract handwritten/printed timer card data from PDF documents for automated processing.

### Input Format

**Multi-page PDF** containing:
- **Header Page**: Factory info, year-month
- **Employee Pages**: One per employee
  - Employee name (氏名)
  - Employee ID (社員番号)
  - Assignment (配属)
  - 31 date rows with:
    - Date (日付)
    - Clock-in time (出勤)
    - Clock-out time (退勤)
    - Break duration (休憩)
    - Notes (備考)

### Processing Pipeline

```
PDF Upload
    ↓
Page-by-page extraction
    ↓
Employee header parsing
    ↓
Table detection
    ↓
Cell extraction
    ↓
Time parsing (HH:MM format)
    ↓
Validation (business rules)
    ↓
processed_timer_cards table update
    ↓
Payroll integration
```

### Storage Table

**Table**: `processed_timer_cards`

**Columns**:
- employee_id
- year
- month
- day
- clock_in_time
- clock_out_time
- break_duration
- notes
- processed_date
- status

---

# MIGRATION & SYNCHRONIZATION

## Migration V5.4 to V6.0.0

**Documentation**: `/docs/core/MIGRATION_V5.4_README.md`

### Changes Summary

**v5.4 → v6.0.0**:
- Cleanup of 150+ documentation files (67% reduction)
- Removed 17 unused frontend dependencies (~120 MB)
- Removed 5 unused backend dependencies (~15 MB)
- Consolidated duplicate components
- Enhanced observability stack (OpenTelemetry, Prometheus, Grafana, Tempo)
- Added nginx reverse proxy with load balancing
- Added automated backup service

### Database Migration Steps

```bash
# Connect to backend container
docker exec -it uns-claudejp-backend bash

# Apply all migrations
cd /app
alembic upgrade head

# Create migration if needed
alembic revision --autogenerate -m "description"

# Rollback one version
alembic downgrade -1
```

---

## Data Synchronization

### Candidate ↔ Employee Sync

**File**: `backend/scripts/sync_candidate_employee_status.py`

**Purpose**: Keep candidates and employees linked

**Process**:
1. Find matching candidates by rirekisho_id or name+DOB
2. Sync photo_data_url to employees
3. Update status fields
4. Log mismatches

**Execution**:
```bash
docker exec -it uns-claudejp-backend python scripts/sync_candidate_employee_status.py
```

---

### Factory Assignment Sync

**Special Case: Contract Workers (請負社員)**

All contract workers are **automatically assigned** to:
- **Factory**: `高雄工業株式会社__岡山工場`
- **Company**: `高雄工業株式会社`
- **Plant**: `岡山工場`

**Rationale**: All contract workers work at this single location per business requirements.

---

# RELATED GUIDES & DOCUMENTATION

## Quick Reference Files

### 1. **Photo Import Guides**

| File | Location | Purpose |
|------|----------|---------|
| **PHOTO_IMPORT_GUIDE.md** | `/scripts/` | Step-by-step photo extraction from Access |
| **GUIA_IMPORTAR_FOTOS.md** | `/docs/features/photos/` | Spanish guide for photo import |
| **SOLUCION_FOTOS_OLE_2025-11-11.md** | `/docs/features/photos/` | Fix for OLE garbage bytes issue |
| **ANALISIS_ARQUITECTONICO_SISTEMA_FOTOS.md** | `/docs/features/photos/` | Architecture analysis |
| **SOLUCION_COMPLETA_FOTOS.md** | `/docs/features/photos/` | Complete photo solution |

### 2. **Import Process Guides**

| File | Location | Purpose |
|------|----------|---------|
| **IMPORTACION_COMPLETA.md** | `/backend/scripts/` | Complete import process from Access |
| **IMPORT_CANDIDATOS_COMPLETA_2025-11-17.md** | `/root/` | Current import status and results |
| **photo-compression-implementation.md** | `/docs/guides/` | Photo compression details |

### 3. **OCR Documentation**

| File | Location | Purpose |
|------|----------|---------|
| **ocr-specialist.md** | `/.claude/specialized-agents/` | OCR hybrid system spec |
| **TIMER_CARDS_OCR_COMPLETE_DESIGN.md** | `/docs/architecture/` | Timer card OCR design |
| **FASE_3_OCR_TIMEOUTS_IMPLEMENTATION.md** | `/docs/06-archive/legacy/` | OCR timeout handling |

### 4. **Data Management**

| File | Location | Purpose |
|------|----------|---------|
| **MIGRATION_V5.4_README.md** | `/docs/core/` | v5.4→v6.0.0 migration guide |
| **MIGRATION_API_V1_TO_V2.md** | `/docs/06-archive/legacy/` | API migration guide |

---

## Key Scripts Reference

### Windows Batch Scripts

```
scripts/
├── EXTRACT_PHOTOS_FROM_ACCESS.bat          # Interactive photo extraction
├── EXTRAER_FOTOS_ROBUSTO.bat                # Robust extraction with verification
├── BUSCAR_FOTOS_AUTO.bat                    # Auto-search for Access DB
├── START.bat                                # Start all services
├── STOP.bat                                 # Stop all services
└── REINSTALAR.bat                           # Full reinstallation
```

### Python Import Scripts

```
backend/scripts/
├── import_all_from_databasejp.py           # Master import orchestrator
├── import_access_candidates.py             # Candidate import with fields
├── import_candidates_improved.py           # Enhanced candidate importer
├── import_photos_from_json.py              # Photo linking
├── import_photos_from_json_simple.py       # Linux-compatible photo import
├── import_data.py                          # Factory/employee/staff import
├── extract_candidates_from_access.py       # Candidate data extraction
├── extract_access_attachments.py           # Photo extraction from OLE
├── auto_extract_photos_from_databasejp.py # Automatic photo extraction
└── sync_candidate_employee_status.py       # Candidate-employee syncing
```

---

# FILE INVENTORY

## Documentation Files Found (20+ relevant)

### Access & Data Extraction

1. `/home/user/UNS-ClaudeJP-6.0.0/scripts/PHOTO_IMPORT_GUIDE.md`
   - Complete guide for photo extraction from Access OLE Objects
   - Step-by-step Windows instructions
   - Docker integration details
   - Troubleshooting section

2. `/home/user/UNS-ClaudeJP-6.0.0/IMPORT_CANDIDATOS_COMPLETA_2025-11-17.md`
   - Status: 1,156 candidates successfully imported
   - 1,139 photos linked (98.5% coverage)
   - Complete field mapping documentation
   - Verification instructions

3. `/home/user/UNS-ClaudeJP-6.0.0/backend/scripts/IMPORTACION_COMPLETA.md`
   - Complete import process (Method 1 and 2)
   - All 172 fields mapped
   - Special handling for 請負社員 (contract workers)
   - Validation procedures

### Photo Processing

4. `/home/user/UNS-ClaudeJP-6.0.0/docs/guides/photo-compression-implementation.md`
   - Photo compression algorithm (92% reduction)
   - Configuration options
   - Test procedures
   - Troubleshooting guide

5. `/home/user/UNS-ClaudeJP-6.0.0/docs/features/photos/SOLUCION_FOTOS_OLE_2025-11-11.md`
   - Solution for OLE garbage bytes issue
   - Root cause analysis
   - Repair scripts
   - Prevention strategies

6. `/home/user/UNS-ClaudeJP-6.0.0/docs/features/photos/ANALISIS_ARQUITECTONICO_SISTEMA_FOTOS.md`
   - Architecture analysis of photo extraction
   - 7-component system design
   - Scalability evaluation
   - Implementation plan

7. `/home/user/UNS-ClaudeJP-6.0.0/docs/features/photos/GUIA_IMPORTAR_FOTOS.md`
   - Step-by-step photo import guide
   - Database location verification
   - Execution methods
   - Verification procedures

8. `/home/user/UNS-ClaudeJP-6.0.0/docs/features/photos/SOLUCION_COMPLETA_FOTOS.md`
   - Complete photo solution (Windows 11)
   - 47 fixed issues
   - 3-step installation process
   - Validation checklist

### OCR Systems

9. `/home/user/UNS-ClaudeJP-6.0.0/.claude/specialized-agents/ocr-specialist.md`
   - Hybrid OCR architecture (Azure→EasyOCR→Tesseract)
   - 7 OCR service components (180KB code)
   - 50+ field extraction for resumes
   - Configuration and testing

10. `/home/user/UNS-ClaudeJP-6.0.0/docs/architecture/TIMER_CARDS_OCR_COMPLETE_DESIGN.md`
    - Timer card OCR processing
    - Multi-page PDF parsing
    - 31-day time card extraction
    - Payroll integration

### Migration & Infrastructure

11. `/home/user/UNS-ClaudeJP-6.0.0/docs/core/MIGRATION_V5.4_README.md`
    - v5.4 → v6.0.0 upgrade path
    - Dependency cleanup (22 packages)
    - Service changes
    - Database migrations

---

## Archive & Legacy Files

12. `/home/user/UNS-ClaudeJP-6.0.0/docs/06-archive/legacy/FASE_3_OCR_TIMEOUTS_IMPLEMENTATION.md`
    - OCR timeout handling
    - Error recovery strategies

13. `/home/user/UNS-ClaudeJP-6.0.0/docs/06-archive/legacy/MIGRATION_API_V1_TO_V2.md`
    - API version migration

14. `/home/user/UNS-ClaudeJP-6.0.0/docs/06-archive/legacy/FIX_EMPLOYEE_PHOTOS_2025-11-12.md`
    - Employee photo linking fix

15. `/home/user/UNS-ClaudeJP-6.0.0/docs/06-archive/legacy/FIX_IMPORTER_FAILURE_2025-11-12.md`
    - Import failure resolution

---

## Summary Statistics

**Total Relevant .md Files**: 20+

**By Category**:
- Photo/Image Extraction: 8 files
- Data Import: 3 files
- OCR Processing: 2 files
- Migration: 2 files
- Archive/Legacy: 5+ files

**Total Documentation Size**: ~3.5 MB

**Last Updated**: 2025-11-17

---

## Key Takeaways

1. **Comprehensive System**: Complete end-to-end solution for Access DB migration
2. **Hybrid Architecture**: Multiple OCR providers with intelligent fallback
3. **Optimized Storage**: 92% photo compression with quality preservation
4. **Fully Automated**: Scripts handle most complex operations
5. **Well-Documented**: 20+ documentation files with detailed procedures
6. **Production Ready**: Successfully imported 1,156 candidates with 1,139 photos
7. **Robust Error Handling**: Multiple fallback mechanisms for reliability
8. **Japanese Support**: Native Japanese character handling and OCR

---

**Generated**: 2025-11-17 by File Search Specialist
**Status**: ✅ COMPLETE ANALYSIS

