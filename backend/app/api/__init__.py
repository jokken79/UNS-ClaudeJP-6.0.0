"""
API routers package for UNS-ClaudeJP 5.2

This module exports all FastAPI router modules for easy importing in main.py.
Use: from app.api import auth, candidates, employees

API Modules (15 routers):
- auth: JWT authentication and user management
- candidates: Candidate (履歴書/Rirekisho) CRUD + OCR processing
- employees: Employee (派遣社員) management
- factories: Factory/client (派遣先) site management
- timer_cards: Attendance (タイムカード) tracking with shift types
- salary: Payroll (給与) calculations and management
- requests: Leave request (申請) workflow
- dashboard: Statistics and analytics
- database: Database management utilities
- azure_ocr: Azure Vision OCR integration
- import_export: Data import/export utilities
- monitoring: System health monitoring
- notifications: Email/LINE notification management
- reports: PDF report generation
- settings: Application settings management

Each module contains a 'router' variable (APIRouter instance).
"""

# Import all router modules for easy access
# Using relative imports to avoid circular import issues
from . import (
    auth,
    azure_ocr,
    candidates,
    dashboard,
    database,
    employees,
    factories,
    import_export,
    monitoring,
    notifications,
    reports,
    requests,
    salary,
    settings,
    timer_cards,
)

__all__ = [
    "auth",
    "azure_ocr",
    "candidates",
    "dashboard",
    "database",
    "employees",
    "factories",
    "import_export",
    "monitoring",
    "notifications",
    "reports",
    "requests",
    "salary",
    "settings",
    "timer_cards",
]
