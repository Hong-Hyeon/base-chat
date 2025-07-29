from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
from .chat import Message


class ModelType(str, Enum):
    OPENAI = "openai"
    VLLM = "vllm"


class ChatSession(BaseModel):
    """Chat session model for organizing conversations."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: Optional[str] = Field(None, max_length=255)
    model_type: ModelType = Field(..., description="Type of LLM: openai or vllm")
    model_name: str = Field(..., description="Specific model name")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "My Chat Session",
                "model_type": "openai",
                "model_name": "gpt-3.5-turbo",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class ChatSessionCreate(BaseModel):
    """Model for creating a new chat session."""
    user_id: str
    title: Optional[str] = Field(None, max_length=255)
    model_type: ModelType = Field(default=ModelType.OPENAI)
    model_name: str = Field(default="gpt-3.5-turbo")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "New Chat Session",
                "model_type": "openai",
                "model_name": "gpt-3.5-turbo"
            }
        }


class ChatSessionUpdate(BaseModel):
    """Model for updating chat session."""
    title: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Chat Session Title",
                "is_active": True
            }
        }


class ChatMessage(BaseModel):
    """Extended message model with additional metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    tokens_used: Optional[int] = Field(None, ge=0)
    model_used: Optional[str] = Field(None, description="Model used for this message")
    mcp_tools_used: Optional[Dict[str, Any]] = Field(None, description="MCP tools usage record")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "session_id": "550e8400-e29b-41d4-a716-446655440001",
                "role": "user",
                "content": "Hello, how are you?",
                "tokens_used": 7,
                "model_used": "gpt-3.5-turbo",
                "mcp_tools_used": None,
                "metadata": {"temperature": 0.7, "max_tokens": 1000},
                "created_at": "2024-01-01T00:00:00Z"
            }
        }


class ChatMessageCreate(BaseModel):
    """Model for creating a new chat message."""
    session_id: str
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    tokens_used: Optional[int] = Field(None, ge=0)
    model_used: Optional[str] = Field(None)
    mcp_tools_used: Optional[Dict[str, Any]] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440001",
                "role": "user",
                "content": "Hello, how are you?",
                "tokens_used": 7,
                "model_used": "gpt-3.5-turbo",
                "mcp_tools_used": None,
                "metadata": {"temperature": 0.7}
            }
        }


class ChatHistoryRequest(BaseModel):
    """Request model for retrieving chat history."""
    session_id: Optional[str] = Field(None, description="Specific session ID")
    user_id: Optional[str] = Field(None, description="User ID for filtering sessions")
    limit: int = Field(default=50, ge=1, le=100, description="Number of items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    include_messages: bool = Field(default=True, description="Include messages in response")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "limit": 50,
                "offset": 0,
                "include_messages": True
            }
        }


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    sessions: List[ChatSession] = Field(default_factory=list)
    messages: List[ChatMessage] = Field(default_factory=list)
    total_sessions: int = Field(default=0)
    total_messages: int = Field(default=0)
    has_more: bool = Field(default=False)

    class Config:
        json_schema_extra = {
            "example": {
                "sessions": [],
                "messages": [],
                "total_sessions": 0,
                "total_messages": 0,
                "has_more": False
            }
        }


class ChatSessionWithMessages(BaseModel):
    """Chat session with its messages."""
    session: ChatSession
    messages: List[ChatMessage] = Field(default_factory=list)
    message_count: int = Field(default=0)

    class Config:
        json_schema_extra = {
            "example": {
                "session": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "My Chat Session",
                    "model_type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "messages": [],
                "message_count": 0
            }
        }


class ChatWithHistoryRequest(BaseModel):
    """Request model for chat with history support."""
    prompt: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Existing session ID")
    user_id: Optional[str] = Field(None, description="User ID")
    model_type: ModelType = Field(default=ModelType.OPENAI)
    model_name: Optional[str] = Field(None, description="Specific model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    create_new_session: bool = Field(default=False, description="Create new session if none provided")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Hello, how are you?",
                "session_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "model_type": "openai",
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
                "create_new_session": False
            }
        }


class ChatWithHistoryResponse(BaseModel):
    """Response model for chat with history."""
    response: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID")
    message_id: str = Field(..., description="New message ID")
    success: bool = Field(default=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "response": "Hello! I'm doing well, thank you for asking. How can I help you today?",
                "session_id": "550e8400-e29b-41d4-a716-446655440001",
                "message_id": "550e8400-e29b-41d4-a716-446655440002",
                "success": True,
                "timestamp": "2024-01-01T00:00:00Z",
                "metadata": {"tokens_used": 15, "model_used": "gpt-3.5-turbo"}
            }
        } 