from pydantic import BaseModel, EmailStr, Field, SecretStr
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    """Base user model with common attributes"""
    email: EmailStr = Field(..., description="User email address")


class UserCreate(UserBase):
    """Model for creating a new user"""
    password: SecretStr = Field(..., description="Plaintext password to be hashed on creation")


class UserLogin(UserBase):
    """Model for user login"""
    password: SecretStr = Field(..., description="Plaintext password for authentication")


class UserUpdate(BaseModel):
    """Model for updating user information"""
    email: Optional[EmailStr] = Field(default=None, description="New email address")
    password: Optional[SecretStr] = Field(default=None, description="New plaintext password to be hashed")


class UserResponse(UserBase):
    """Model for user response data (no sensitive info)"""
    id: str = Field(..., description="User identifier")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    class Config:
        from_attributes = True


class UserDetail(UserResponse):
    """Model for detailed user information (admin use)"""
    is_active: Optional[bool] = Field(default=True, description="Whether the user account is active")
    roles: Optional[List[str]] = Field(default_factory=list, description="List of role names")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")


class PasswordChangeRequest(BaseModel):
    """Model for password change request"""
    current_password: SecretStr = Field(..., description="Current plaintext password")
    new_password: SecretStr = Field(..., description="New plaintext password")


class TokenResponse(BaseModel):
    """Model for JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")