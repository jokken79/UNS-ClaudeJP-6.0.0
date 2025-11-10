"""
Authentication Schemas
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from app.models.models import UserRole


class UserLogin(BaseModel):
    """Login request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserRegister(BaseModel):
    """User registration"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    role: UserRole = UserRole.EMPLOYEE


class Token(BaseModel):
    """Token response - includes both access and refresh tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data"""
    username: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="The refresh token to exchange for new access token")


class LogoutRequest(BaseModel):
    """Logout request"""
    refresh_token: str = Field(..., description="The refresh token to revoke")
    logout_all_devices: bool = Field(False, description="Revoke all refresh tokens for this user")


class UserResponse(BaseModel):
    """User response"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Update user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class PasswordChange(BaseModel):
    """Change password"""
    old_password: str
    new_password: str = Field(..., min_length=6)
