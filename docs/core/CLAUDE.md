# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> ℹ️ **Note**: The automated flow described in `.claude/CLAUDE.md` is preserved as historical reference. It's not mandatory for human collaborators; use this file as the source of truth.

---

## 🚀 Quick Start (Development)

### Start Services (Windows)
```bash
cd scripts
START.bat          # Start all services
LOGS.bat           # View logs (interactive menu)
STOP.bat           # Stop services
```

### Start Services (Linux/macOS)
```bash
python generate_env.py
docker compose up -d
docker compose logs -f
docker compose down
```

### Access URLs
- **Frontend:** http://localhost:3000 (Next.js 16)
- **Backend API:** http://localhost:8000 (FastAPI)
- **API Docs:** http://localhost:8000/api/docs (Swagger)
- **Database UI:** http://localhost:8080 (Adminer)

**Default Login:** `admin` / `admin123`

---

## 📐 Project Overview

UNS-ClaudeJP 5.2 is a comprehensive HR management system for Japanese staffing agencies (人材派遣会社):

- **Backend**: FastAPI 0.115.6 (Python 3.11+) with SQLAlchemy 2.0.36 ORM and PostgreSQL 15
- **Frontend**: Next.js 16.0.0 with React 19.0.0, TypeScript 5.6 and Tailwind CSS 3.4 (App Router)
- **DevOps**: Docker Compose for orchestration

Manages the complete lifecycle of temporary workers: candidates (履歴書/Rirekisho), employees (派遣社員), factories (派遣先), attendance (タイムカード), payroll (給与), and requests (申請).

**Version 5.2**: 45+ functional pages across 8 core modules with advanced theming system (12 predefined themes + custom themes), template designer, and professional design tools.

---

## 🔧 Core Development Commands

### Backend (FastAPI + Python 3.11)

```bash
# Access backend container
docker exec -it uns-claudejp-backend bash

# Database migrations
cd /app
alembic upgrade head                    # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
alembic downgrade -1                    # Rollback one

# Admin & data
python scripts/create_admin_user.py     # Create/reset admin user
python scripts/import_data.py           # Import demo data
python scripts/verify_data.py           # Verify database

# Testing
pytest backend/tests/ -v                # Run tests with verbose
pytest backend/tests/test_auth.py -vs   # Run single test file
pytest -k "test_login" -vs              # Run tests matching pattern
```

**Key Backend Paths:**
- API endpoints: `backend/app/api/*.py` (24 routers)
- Database models: `backend/app/models/models.py` (13 tables)
- Business logic: `backend/app/services/*.py`
- Migrations: `backend/alembic/versions/`

### Frontend (Next.js 16 + React 19)

```bash
# Access frontend container
docker exec -it uns-claudejp-frontend bash

# Development
npm run dev                              # Dev server (already running)
npm run build                            # Build for production
npm run type-check                       # TypeScript validation
npm run lint                             # ESLint check
npm test                                 # Run unit tests with Vitest
npm run test:e2e                         # Run E2E tests with Playwright

# Dependencies
npm install <package-name>              # Install package
npm list                                # Show dependencies
```

**Key Frontend Paths:**
- Pages: `frontend/app/(dashboard)/*/page.tsx` (45+ pages)
- Components: `frontend/components/*.tsx`
- Themes: `frontend/lib/themes.ts` (12 predefined + custom)
- API client: `frontend/lib/api.ts`
- State: `frontend/stores/*.ts` (Zustand)

### Database (PostgreSQL 15)

```bash
# Access PostgreSQL directly
docker exec -it uns-claudejp-db psql -U uns_admin -d uns_claudejp

# Useful SQL commands
\dt                              # List tables
\d <table_name>                  # Describe table
SELECT * FROM users LIMIT 5;     # Query data

# Backup/restore
docker exec uns-claudejp-db pg_dump -U uns_admin uns_claudejp > backup.sql
cat backup.sql | docker exec -i uns-claudejp-db psql -U uns_admin uns_claudejp
```

---

## 📐 Architecture at a Glance

### Tech Stack (Fixed Versions - DO NOT CHANGE)

| Layer | Technology | Version |
|-------|-----------|---------|
| **Frontend** | Next.js | 16.0.0 |
| **UI Framework** | React | 19.0.0 |
| **Type Safety** | TypeScript | 5.6 |
| **Styling** | Tailwind CSS | 3.4 |
| **Backend** | FastAPI | 0.115.6 |
| **Language** | Python | 3.11+ |
| **ORM** | SQLAlchemy | 2.0.36 |
| **Database** | PostgreSQL | 15 |
| **DevOps** | Docker Compose | - |

### Key Architecture Decisions

1. **Next.js App Router** (NOT Pages Router) - File-based routing under `app/`
2. **FastAPI with dependency injection** - Type-safe endpoints with auto-documentation
3. **SQLAlchemy ORM** - Never use raw SQL; always use the ORM
4. **PostgreSQL with 13 tables** - Full normalization with triggers for business logic
5. **Hybrid OCR** - Azure (primary) → EasyOCR (secondary) → Tesseract (fallback)
6. **Zustand + React Query** - Light state management + server state caching
7. **Shadcn/ui + Tailwind** - Component-driven design with CSS utilities

### Database (13 Tables)

**Personnel:** users, candidates, employees, contract_workers, staff
**Business:** factories, apartments, documents, contracts
**Operations:** timer_cards, salary_calculations, requests, audit_log

**Key relationships:**
- candidates ← employees (via `rirekisho_id`)
- employees → factories (via `factory_id`)
- employees → apartments (via `apartment_id`)

### User Role Hierarchy (Fixed - DO NOT MODIFY)

```
SUPER_ADMIN > ADMIN > COORDINATOR > KANRININSHA > EMPLOYEE > CONTRACT_WORKER
```

**Roles:**
- **SUPER_ADMIN** - Full system control
- **ADMIN** - Administrative access
- **COORDINATOR** - Coordination tasks
- **KANRININSHA** - Manager (管理人者)
- **EMPLOYEE** - Employee access
- **CONTRACT_WORKER** - Contract worker access

### OCR System (Hybrid Multi-Provider - Fixed Priority)

**Provider Cascade (DO NOT CHANGE ORDER):**
```
1. Azure Computer Vision (primary)
   ↓ (if fails)
2. EasyOCR (secondary)
   ↓ (if fails)
3. Tesseract (fallback)
```

**Supported Documents:**
- 履歴書 (Rirekisho/Resume) - 50+ fields
- 在留カード (Zairyu Card) - Residence card
- 運転免許証 (Driver's License)

**Face Detection:**
- MediaPipe for automatic photo extraction from documents
- Photos stored in `photo_data_url` field

### Theme System (12 Predefined + Custom)

**12 Predefined Themes (Required):**
1. **default-light** - Default light theme
2. **default-dark** - Default dark theme
3. **uns-kikaku** - Corporate theme
4. **industrial** - Industrial corporate theme
5. **ocean-blue** - Nature theme
6. **mint-green** - Nature theme
7. **forest-green** - Nature theme
8. **sunset** - Nature theme
9. **royal-purple** - Premium theme
10. **vibrant-coral** - Vibrant theme
11. **monochrome** - Minimalist theme
12. **espresso** - Warm theme

**Theme Features:**
- Live preview with 500ms hover delay
- Favorites system
- Search and filter
- Custom theme builder
- Export/import JSON
- WCAG contrast validation
- Unlimited custom themes

**Theme Files:**
- Theme definitions: `frontend/lib/themes.ts`
- Customizer: `frontend/app/(dashboard)/themes/customizer/page.tsx`
- Theme gallery: `frontend/app/(dashboard)/themes/page.tsx`

### API Structure (24 Routers)

```
/api/
├── auth/                 # JWT login, token refresh, logout
├── candidates/           # CRUD + OCR processing (履歴書)
├── employees/            # CRUD + assignment (派遣社員)
├── factories/            # CRUD client sites (派遣先)
├── timer_cards/          # Attendance tracking (タイムカード)
├── payroll/              # Payroll calculations (給与)
├── requests/             # Leave workflows (申請)
├── dashboard/            # Analytics & stats
├── azure_ocr/            # OCR endpoints
├── import_export/        # Bulk data operations
├── notifications/        # Email/LINE alerts
├── reports/              # PDF generation
├── settings/             # System configuration
├── monitoring/           # Health checks
├── database/             # DB admin tools
├── apartments/           # Housing management
├── admin/                # Admin operations
├── role_permissions/     # RBAC management
├── salary/               # Salary management
├── pages/                # Static pages
├── resilient_import/     # Resilient data import
└── deps.py               # Dependency injection
```

---

## 🐛 Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| **Port already in use** | `lsof -ti:3000 \| xargs kill -9` (Mac/Linux) or `taskkill /PID <pid> /F` (Windows) |
| **Backend won't start** | Check `docker compose logs backend` for errors |
| **Frontend blank page** | Wait 1-2 min for compilation, check `docker compose logs frontend` |
| **Database connection error** | Run `alembic upgrade head` to apply migrations |
| **TypeScript errors** | Run `npm run type-check` to see all issues |
| **Docker not found** | Ensure Docker Desktop is running |
| **CORS errors** | Check `FRONTEND_URL` environment variable |
| **401 Unauthorized** | Verify JWT token in localStorage, check SECRET_KEY in backend |

**📖 For detailed troubleshooting, see:**
- `docs/04-troubleshooting/TROUBLESHOOTING.md`
- `docs/guides/development-patterns.md`

---

## 📁 File Organization

**DO NOT modify:**
- `scripts/*.bat` - System depends on these batch files
- `docker-compose.yml` - Service orchestration
- `.env` structure - Database connection, secrets
- `backend/alembic/versions/` - Migration history
- Locked dependency versions (see Tech Stack above)

**Safe to modify:**
- Add new routes in `backend/app/api/`
- Add new pages in `frontend/app/(dashboard)/`
- Update components in `frontend/components/`
- Add new services in `backend/app/services/`
- Database models in `backend/app/models/models.py` (then create migration)

---

## 🧪 Testing

### Backend Testing
```bash
# Run all backend tests
pytest backend/tests/ -v

# Run specific test file
pytest backend/tests/test_auth.py -vs

# Run tests with markers
pytest -m "not slow" -v

# Run with coverage
pytest --cov=app backend/tests/
```

### Frontend Testing
```bash
# Unit tests (Vitest)
npm test
npm test -- --watch

# E2E tests (Playwright)
npm run test:e2e
npm run test:e2e -- --headed

# Type checking
npm run type-check

# Linting
npm run lint
npm run lint:fix
```

---

## 🔄 RECONSTRUCCIÓN DEL SISTEMA (2025-10-31)

### 📄 Documentos de Reconstrucción

This project is being **reconstructed from scratch** to eliminate accumulated errors. If you're an AI working on this project, **you MUST read these documents in order**:

1. **`PROMPT_RECONSTRUCCION_COMPLETO.md`** ⭐ MAXIMUM AUTHORITY
   - Complete 25,000+ word specification
   - Includes ALL architecture, modules, example code

2. **`AI_RULES.md`** - Universal rules for all AIs

3. **`.cursorrules`** - Specific rules for Cursor AI

4. **`.windsurfrules`** - Specific rules for Windsurf

5. **This file (CLAUDE.md)** - Project context

### ⚠️ CRITICAL RULES

**BEFORE making ANY changes:**

1. ✅ Read `PROMPT_RECONSTRUCCION_COMPLETO.md` relevant section
2. ✅ Verify your implementation follows the specifications EXACTLY
3. ✅ NEVER change versions without approval (FastAPI 0.115.6, Next.js 16.0.0, etc.)
4. ✅ ALWAYS show code BEFORE creating files
5. ✅ ALWAYS test each module before continuing
6. ✅ ASK when in doubt

**LOCKED VERSIONS (DO NOT MODIFY):**
- FastAPI 0.115.6
- SQLAlchemy 2.0.36
- Next.js 16.0.0
- React 19.0.0
- TypeScript 5.6
- PostgreSQL 15

### 🚫 ABSOLUTE PROHIBITIONS

**DO NOT CHANGE VERSIONS (CRITICAL):**

**Backend - FIXED VERSIONS:**
```
fastapi==0.115.6
sqlalchemy==2.0.36
alembic==1.17.0
pydantic==2.10.5
python==3.11+
```

**Frontend - FIXED VERSIONS:**
```
next==16.0.0
react==19.0.0
typescript==5.6
tailwindcss==3.4
```

**If you need to change a version:**
1. STOP
2. ASK the user
3. JUSTIFY why it's necessary
4. WAIT for explicit approval

### 🗄️ MANDATORY DATABASE SPECIFICATIONS

**13 Required Tables:**
1. `users` - Authentication system
2. `candidates` - Candidates (履歴書)
3. `employees` - Employees (派遣社員)
4. `factories` - Factories/Clients (派遣先)
5. `apartments` - Housing (社宅)
6. `timer_cards` - Attendance (タイムカード)
7. `salary_calculations` - Payroll (給与)
8. `requests` - Requests (申請)
9. `contracts` - Contracts
10. `documents` - Documents
11. `audit_log` - Audit
12. `staff` - Staff
13. `contract_workers` - Contract workers

**Required Triggers:**
- `sync_employee_status()` - Sync current_status with is_active
- `check_visa_expiration()` - Automatic visa alerts
- `update_updated_at_column()` - Auto-update timestamps
- `audit_trigger_function()` - Automatic audit

**Candidate-Employee Relationship (CRITICAL):**
The relationship between candidates and employees must use this strategy (in order):
1. **Primary**: `full_name_roman` + `date_of_birth` (most reliable)
2. **Fallback**: `rirekisho_id` (when primary fails)
3. **Last resort**: Fuzzy matching by name only

---

## 🚨 NORMA #7 - .md FILE MANAGEMENT (MANDATORY FOR ALL AGENTS)

### 📋 GOLDEN RULES:
1. **🔍 SEARCH BEFORE CREATING**: Always check if a similar .md file exists
2. **📝 REUSE EXISTING**: If similar topic exists, add content with date
3. **📅 MANDATORY DATE FORMAT**: `## 📅 YYYY-MM-DD - [TITLE]`
4. **🚫 AVOID DUPLICATION**: Do NOT create `NEW_ANALYSIS.md` if `ANALYSIS.md` exists

### 📁 PRACTICAL EXAMPLES:
- ❌ **BAD**: Creating `PROBLEMA_TEMAS_2.md` when `PROBLEMA_TEMAS.md` exists
- ✅ **GOOD**: Edit `PROBLEMA_TEMAS.md` adding `## 📅 2025-10-21 - New problem found`

### 🎯 EXCEPTIONS:
Only create new .md if the topic is **completely different** and doesn't fit existing ones.

**Check existing documents**: `docs/`, `docs/archive/`, `docs/guides/`, `docs/sessions/`, etc.

---

## 📜 Windows Batch Scripts (System Critical)

**Location:** `scripts/`

**Essential Scripts (DO NOT MODIFY):**
- `START.bat` - Start all services
- `STOP.bat` - Stop all services
- `LOGS.bat` - View logs (interactive menu)
- `REINSTALAR.bat` - Complete reinstallation
- `BACKUP_DATOS.bat` - Database backup
- `RESTAURAR_DATOS.bat` - Restore database
- `HEALTH_CHECK_FUN.bat` - System health check
- `DIAGNOSTICO_FUN.bat` - System diagnostics
- `INSTALAR_FUN.bat` - Installation script
- `BUILD_BACKEND_FUN.bat` - Build backend
- `BUILD_FRONTEND_FUN.bat` - Build frontend

**Additional Utilities:**
- `FIX_ADMIN_LOGIN_FUN.bat` - Fix admin login issues
- `CREAR_RAMA_FUN.bat` - Create git branch
- `COPY_FACTORIES.ps1` - Copy factory data
- `DEBUG_ACCESS_NAMES.ps1` - Debug Access database names

**If you need to modify a script:**
1. Create new version with suffix (e.g., `START_v2.bat`)
2. DO NOT overwrite original
3. Document changes in README.md

**🚨 CRITICAL RULE: .bat Files Must NEVER Close Automatically**

When creating or modifying .bat files, they MUST ALWAYS stay open to show errors:

1. **ALWAYS add `pause >nul` at the END** of every .bat file
2. **NEVER use `exit /b 1` after `pause`** - this closes the window
3. **Remove ALL `exit /b 1`** that appear after `pause` commands
4. **To fix existing .bat files**, run: `scripts\FIX_NEVER_CLOSE_BATS.ps1`

**Example - WRONG:**
```bat
pause >nul
exit /b 1  # ❌ Window closes immediately
```

**Example - CORRECT:**
```bat
pause >nul  # ✅ Window stays open
```

This ensures users can always see error messages without windows closing.

---

## 🎯 Mandatory Development Workflow

### Before Writing Code

1. **Read Specification:**
   ```
   "I have read PROMPT_RECONSTRUCCION_COMPLETO.md
    Section [X] that covers this functionality"
   ```

2. **Confirm Scope:**
   ```
   "I will implement [feature]
    using [technology] as specified in the prompt.
    Should I proceed?"
   ```

3. **Wait for User Confirmation**

### During Implementation

**ALWAYS show code BEFORE creating files:**

```
User: "Implement the candidate module"

Claude: "I will create the following files
         according to PROMPT_RECONSTRUCCION_COMPLETO.md:

         1. backend/app/api/candidates.py
         2. backend/app/schemas/candidate.py
         3. frontend/app/(dashboard)/candidates/page.tsx

         First, let me show you the code for candidates.py:
         [SHOW COMPLETE CODE]

         Do you approve this code before creating the file?"

User: "Yes, approved"

Claude: [NOW create file]
```

### After Implementation

1. **Verify:**
   ```bash
   # Backend
   docker compose logs backend | tail -20
   curl http://localhost:8000/api/candidates

   # Frontend
   npm run type-check
   npm run build
   ```

2. **Report:**
   ```
   "Candidate module implemented:
    ✅ API endpoint working
    ✅ Frontend compiling without errors
    ✅ TypeScript types validated

    Next step: [description]
    Should I proceed?"
   ```

### Validation Checklists

**Before creating/modifying files, VERIFY:**

**Backend Checklist:**
- [ ] Uses exact versions from prompt?
- [ ] Follows specified folder structure?
- [ ] Has docstrings and type hints?
- [ ] Handles errors appropriately?
- [ ] Validates authentication/authorization?
- [ ] Uses ORM (no direct SQL)?

**Frontend Checklist:**
- [ ] Uses App Router (not Pages)?
- [ ] Uses Shadcn/ui components?
- [ ] Has validation with Zod?
- [ ] Handles loading/error states?
- [ ] Is responsive (mobile-first)?
- [ ] Passes TypeScript type-check?

**Docker Checklist:**
- [ ] Maintains the 5 services?
- [ ] Health checks configured?
- [ ] Volumes for persistence?
- [ ] Environment variables from .env?

---

## 🎯 User Preferences

**"claude poder"** = Run command in terminal:
```bash
claude --dangerously-skip-permissions
```

---

## 📚 Detailed Documentation

For detailed information, see these documents:

### Architecture & Structure
- **Frontend Structure**: `docs/architecture/frontend-structure.md`
- **Backend Structure**: `backend/app/` (see main README.md)
- **Database Schema**: `docs/architecture/database-schema.md`

### Development Guides
- **Development Patterns**: `docs/guides/development-patterns.md`
- **Theme System**: `docs/guides/themes.md`
- **Template System**: `docs/guides/templates.md`
- **Design Tools**: `docs/guides/design-tools.md`
- **OCR Integration**: `docs/guides/ocr-integration.md`
- **Authentication**: `docs/guides/authentication.md`

### Troubleshooting
- **Troubleshooting Guide**: `docs/04-troubleshooting/TROUBLESHOOTING.md`
- **Common Issues**: `docs/guides/common-issues.md`

---

## 🚨 Critical Development Rules

**NEVER DELETE OR MODIFY:**
1. **Batch scripts** in `scripts/` folder - System depends on these
2. **Orchestration files** in `.claude/agents/` - Agent delegation system
3. **Working code** - If it works, don't touch it; only add or enhance
4. **Migration history** in `backend/alembic/versions/` - Git conflicts can break the database
5. **Configuration files** - docker-compose.yml, .env structure, package.json

**WINDOWS COMPATIBILITY:**
- All scripts must work on any Windows PC with Docker Desktop
- Use Windows-style paths in batch files (`\` not `/`)
- PowerShell and cmd.exe compatible
- No WSL/Linux dependencies required

**BEFORE MAJOR CHANGES:**
- Suggest creating a Git branch
- Ask for confirmation before modifying existing code
- Maintain current coding style and conventions
- Verify changes don't break Docker orchestration

---

## 🌐 Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Next.js application |
| **Backend API** | http://localhost:8000 | FastAPI REST API |
| **API Docs** | http://localhost:8000/api/docs | Interactive Swagger UI |
| **ReDoc** | http://localhost:8000/api/redoc | Alternative API docs |
| **Adminer** | http://localhost:8080 | Database management UI |
| **Health Check** | http://localhost:8000/api/health | Backend health status |

---

## 🐳 Docker Services

The application runs 5 services via Docker Compose:

1. **db** - PostgreSQL 15 with persistent volume
2. **importer** - One-time data initialization (creates admin user, imports demo data)
3. **backend** - FastAPI application with hot reload
4. **frontend** - Next.js 16 application with hot reload (Turbopack default)
5. **adminer** - Database management UI

All services communicate via `uns-network` bridge network.

---

## 📖 Important Notes

- **Default credentials**: `admin` / `admin123` (CHANGE IN PRODUCTION!)
- **Docker required**: All services run in containers
- **Port requirements**: 3000, 8000, 5432, 8080
- **Japanese terminology**: Extensive use of Japanese HR terms (履歴書, 派遣社員, タイムカード, etc.)
- **v5.2 Upgrade**: Upgraded to Next.js 16 with React 19, Turbopack default bundler
- **Next.js**: Uses App Router (not Pages Router), Server Components by default
