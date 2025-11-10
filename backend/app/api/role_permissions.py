"""
Role-Based Permissions API
Controls which pages each role can access (ADMIN, KEITOSAN, TANTOSHA, EMPLOYEE)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import RolePagePermission, User, UserRole
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/role-permissions", tags=["role-permissions"])

# ================================
# SCHEMAS (Pydantic Models)
# ================================

class PermissionResponse(BaseModel):
    """Response schema for a single permission"""
    role_key: str
    page_key: str
    is_enabled: bool
    created_at: str
    updated_at: str

class PermissionUpdate(BaseModel):
    """Request schema for updating a permission"""
    is_enabled: bool

class BulkPermissionUpdate(BaseModel):
    """Request schema for bulk updating permissions"""
    permissions: List[Dict[str, Any]]  # List of {page_key: str, is_enabled: bool}

class RolePermissionsResponse(BaseModel):
    """Response schema for all permissions of a role"""
    role_key: str
    permissions: List[PermissionResponse]
    total_pages: int
    enabled_pages: int

class UserPermissionsResponse(BaseModel):
    """Response schema for current user's permissions"""
    user_role: str
    permissions: List[str]  # List of page_keys user can access

class PageInfo(BaseModel):
    """Schema for page information"""
    key: str
    name: str
    name_en: Optional[str] = None
    description: Optional[str] = None

# ================================
# AVAILABLE PAGES CONSTANT
# ================================

AVAILABLE_PAGES = [
    {"key": "dashboard", "name": "ダッシュボード", "name_en": "Dashboard", "description": "Main dashboard"},
    {"key": "candidates", "name": "候補者", "name_en": "Candidates", "description": "Manage job candidates"},
    {"key": "employees", "name": "従業員", "name_en": "Employees", "description": "Manage employees"},
    {"key": "factories", "name": "派遣先", "name_en": "Factories", "description": "Client factories"},
    {"key": "apartments", "name": "アパート", "name_en": "Apartments", "description": "Employee housing"},
    {"key": "timer_cards", "name": "タイムカード", "name_en": "Time Cards", "description": "Attendance tracking"},
    {"key": "salary", "name": "給与", "name_en": "Salary", "description": "Payroll management"},
    {"key": "requests", "name": "申請", "name_en": "Requests", "description": "Leave requests"},
    {"key": "reports", "name": "レポート", "name_en": "Reports", "description": "Analytics and reports"},
    {"key": "design_system", "name": "デザインシステム", "name_en": "Design System", "description": "UI components"},
    {"key": "forms", "name": "フォーム", "name_en": "Forms", "description": "Form templates"},
    {"key": "support", "name": "サポート", "name_en": "Support", "description": "Help and support"},
    {"key": "help", "name": "ヘルプ", "name_en": "Help", "description": "Documentation"},
    {"key": "terms", "name": "利用規約", "name_en": "Terms", "description": "Terms of service"},
    {"key": "privacy", "name": "プライバシーポリシー", "name_en": "Privacy Policy", "description": "Privacy policy"},
]

# ================================
# AVAILABLE ROLES CONSTANT
# ================================

AVAILABLE_ROLES = [
    {"key": "ADMIN", "name": "アドミニストレーター", "name_en": "Administrator", "description": "Full access to all features"},
    {"key": "KEITOSAN", "name": "経理管理", "name_en": "Finance Manager", "description": "Finance and accounting access"},
    {"key": "TANTOSHA", "name": "担当者", "name_en": "Representative", "description": "HR and operations access"},
    {"key": "EMPLOYEE", "name": "従業員", "name_en": "Employee", "description": "Limited access to own data"},
]


# ================================
# ENDPOINTS
# ================================

@router.get("/roles", response_model=List[Dict[str, str]], summary="List available roles")
async def list_roles():
    """Get list of all available roles"""
    return AVAILABLE_ROLES


@router.get("/pages", response_model=List[PageInfo], summary="List available pages")
async def list_pages():
    """Get list of all available pages"""
    return AVAILABLE_PAGES


@router.get("/{role_key}", response_model=RolePermissionsResponse, summary="Get permissions for a role")
async def get_role_permissions(
    role_key: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all page permissions for a specific role
    Only ADMIN users can access this endpoint
    """
    # Validate role exists
    if role_key not in [r["key"] for r in AVAILABLE_ROLES]:
        raise HTTPException(status_code=404, detail=f"Role '{role_key}' not found")

    # Get all permissions for this role
    permissions = db.query(RolePagePermission).filter(
        RolePagePermission.role_key == role_key
    ).all()

    # Ensure all pages are represented (fill missing with default false)
    permission_dict = {p.page_key: p for p in permissions}
    result_permissions = []

    for page in AVAILABLE_PAGES:
        page_key = page["key"]
        if page_key in permission_dict:
            perm = permission_dict[page_key]
            result_permissions.append(PermissionResponse(
                role_key=role_key,
                page_key=page_key,
                is_enabled=perm.is_enabled,
                created_at=perm.created_at.isoformat(),
                updated_at=perm.updated_at.isoformat() if perm.updated_at else ""
            ))
        else:
            # Page not explicitly set, default to false
            result_permissions.append(PermissionResponse(
                role_key=role_key,
                page_key=page_key,
                is_enabled=False,
                created_at="",
                updated_at=""
            ))

    # Count enabled pages
    enabled_count = sum(1 for p in result_permissions if p.is_enabled)

    return RolePermissionsResponse(
        role_key=role_key,
        permissions=result_permissions,
        total_pages=len(result_permissions),
        enabled_pages=enabled_count
    )


@router.put("/{role_key}/{page_key}", response_model=PermissionResponse, summary="Update a single permission")
async def update_permission(
    role_key: str,
    page_key: str,
    permission: PermissionUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update a single page permission for a role
    Only ADMIN users can access this endpoint
    """
    # Validate role
    if role_key not in [r["key"] for r in AVAILABLE_ROLES]:
        raise HTTPException(status_code=404, detail=f"Role '{role_key}' not found")

    # Validate page
    if page_key not in [p["key"] for p in AVAILABLE_PAGES]:
        raise HTTPException(status_code=404, detail=f"Page '{page_key}' not found")

    # Get or create permission
    db_permission = db.query(RolePagePermission).filter(
        RolePagePermission.role_key == role_key,
        RolePagePermission.page_key == page_key
    ).first()

    if not db_permission:
        db_permission = RolePagePermission(
            role_key=role_key,
            page_key=page_key,
            is_enabled=permission.is_enabled
        )
        db.add(db_permission)
    else:
        db_permission.is_enabled = permission.is_enabled

    db.commit()
    db.refresh(db_permission)

    return PermissionResponse(
        role_key=role_key,
        page_key=page_key,
        is_enabled=db_permission.is_enabled,
        created_at=db_permission.created_at.isoformat(),
        updated_at=db_permission.updated_at.isoformat() if db_permission.updated_at else ""
    )


@router.post("/bulk-update/{role_key}", response_model=RolePermissionsResponse, summary="Bulk update permissions for a role")
async def bulk_update_permissions(
    role_key: str,
    bulk_update: BulkPermissionUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update multiple permissions for a role at once
    Only ADMIN users can access this endpoint
    """
    # Validate role
    if role_key not in [r["key"] for r in AVAILABLE_ROLES]:
        raise HTTPException(status_code=404, detail=f"Role '{role_key}' not found")

    # Process each permission update
    for perm_data in bulk_update.permissions:
        page_key = perm_data.get("page_key")
        is_enabled = perm_data.get("is_enabled")

        if not page_key or is_enabled is None:
            raise HTTPException(status_code=400, detail="Invalid permission data")

        # Validate page
        if page_key not in [p["key"] for p in AVAILABLE_PAGES]:
            raise HTTPException(status_code=404, detail=f"Page '{page_key}' not found")

        # Get or create permission
        db_permission = db.query(RolePagePermission).filter(
            RolePagePermission.role_key == role_key,
            RolePagePermission.page_key == page_key
        ).first()

        if not db_permission:
            db_permission = RolePagePermission(
                role_key=role_key,
                page_key=page_key,
                is_enabled=is_enabled
            )
            db.add(db_permission)
        else:
            db_permission.is_enabled = is_enabled

    db.commit()

    # Return updated permissions
    return await get_role_permissions(role_key, current_user, db)


@router.get("/check/{role_key}/{page_key}", summary="Check if a role has access to a page")
async def check_permission(
    role_key: str,
    page_key: str,
    db: Session = Depends(get_db)
):
    """
    Check if a role has access to a specific page
    This endpoint can be used by the frontend to verify access
    """
    # Validate role and page
    if role_key not in [r["key"] for r in AVAILABLE_ROLES]:
        return {"has_access": False, "reason": "Role not found"}

    if page_key not in [p["key"] for p in AVAILABLE_PAGES]:
        return {"has_access": False, "reason": "Page not found"}

    # Check permission
    permission = db.query(RolePagePermission).filter(
        RolePagePermission.role_key == role_key,
        RolePagePermission.page_key == page_key
    ).first()

    if not permission:
        # If no explicit permission set, default to false
        return {"has_access": False, "reason": "No permission set"}

    return {
        "has_access": permission.is_enabled,
        "role_key": role_key,
        "page_key": page_key
    }


@router.get("/user/{user_id}/permissions", response_model=UserPermissionsResponse, summary="Get current user's permissions")
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all permissions for the current user based on their role
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get permissions for user's role
    permissions = db.query(RolePagePermission).filter(
        RolePagePermission.role_key == user.role,
        RolePagePermission.is_enabled == True
    ).all()

    # Return list of page_keys user can access
    return UserPermissionsResponse(
        user_role=user.role,
        permissions=[p.page_key for p in permissions]
    )


@router.post("/reset/{role_key}", summary="Reset permissions to default for a role")
async def reset_permissions(
    role_key: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reset all permissions for a role to their default values
    Only ADMIN users can access this endpoint
    """
    # Validate role
    if role_key not in [r["key"] for r in AVAILABLE_ROLES]:
        raise HTTPException(status_code=404, detail=f"Role '{role_key}' not found")

    # Delete existing permissions
    db.query(RolePagePermission).filter(
        RolePagePermission.role_key == role_key
    ).delete()

    db.commit()

    # Return success message
    return {
        "message": f"Permissions reset for role '{role_key}'",
        "note": "Use the default permissions setup to restore specific values"
    }
