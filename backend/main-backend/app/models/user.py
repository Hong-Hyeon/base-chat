from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(BaseModel):
    """User model for authentication and management."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    is_active: bool = Field(default=True)
    role: UserRole = Field(default=UserRole.USER)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "testuser",
                "email": "test@example.com",
                "is_active": True,
                "role": "user",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class UserCreate(BaseModel):
    """Model for creating a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepassword123"
            }
        }


class UserLogin(BaseModel):
    """Model for user login."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "testuser",
                "password": "test123"
            }
        }


class UserPreferences(BaseModel):
    """User preferences for chat settings."""
    user_id: str
    default_model: str = Field(default="gpt-3.5-turbo")
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "default_model": "gpt-3.5-turbo",
                "default_temperature": 0.7,
                "max_tokens": 1000
            }
        }


class UserUpdate(BaseModel):
    """Model for updating user information."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "username": "updateduser",
                "email": "updated@example.com",
                "is_active": True
            }
        }


class UserResponse(BaseModel):
    """Response model for user data (without sensitive information)."""
    id: str
    username: str
    email: str
    is_active: bool
    role: UserRole
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "testuser",
                "email": "test@example.com",
                "is_active": True,
                "role": "user",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        } 