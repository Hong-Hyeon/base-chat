from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from app.models.chat_history import (
    ChatSession, ChatSessionCreate, ChatSessionUpdate,
    ChatMessage, ChatMessageCreate, ChatHistoryRequest, ChatHistoryResponse,
    ChatWithHistoryRequest, ChatWithHistoryResponse
)
from app.models.user import User, UserCreate, UserResponse
from app.services.sqlalchemy_chat_history_service import get_sqlalchemy_chat_history_service
from app.services.llm_client import llm_client
from app.utils.logger import get_logger
from app.models.chat import ChatRequest, Message

router = APIRouter(prefix="/history", tags=["Chat History"])
logger = get_logger("history_api")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "chat_history"}


@router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    """Create a new user."""
    try:
        history_service = await get_sqlalchemy_chat_history_service()
        user = await history_service.create_user(user_data)
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            role="user",  # Default role
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID."""
    try:
        from uuid import UUID
        history_service = await get_sqlalchemy_chat_history_service()
        user = await history_service.get_user(UUID(user_id))
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at
        )
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user")


@router.post("/sessions", response_model=ChatSession)
async def create_session(session_data: ChatSessionCreate):
    """Create a new chat session."""
    try:
        history_service = await get_sqlalchemy_chat_history_service()
        session = await history_service.create_session(session_data)
        
        # Convert SQLAlchemy model to Pydantic model
        return ChatSession(
            id=str(session.id),
            user_id=str(session.user_id),
            title=session.title,
            model_type=session.model_type,
            model_name=session.model_name,
            is_active=session.is_active,
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(session_id: str):
    """Get chat session by ID."""
    try:
        from uuid import UUID
        history_service = await get_sqlalchemy_chat_history_service()
        session = await history_service.get_session(UUID(session_id))
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session")


@router.get("/users/{user_id}/sessions", response_model=List[ChatSession])
async def get_user_sessions(user_id: str, limit: int = Query(50, ge=1, le=100)):
    """Get chat sessions for a user."""
    try:
        from uuid import UUID
        history_service = await get_sqlalchemy_chat_history_service()
        sessions = await history_service.get_user_sessions(UUID(user_id), limit)
        
        # Convert SQLAlchemy models to Pydantic models
        return [
            ChatSession(
                id=str(session.id),
                user_id=str(session.user_id),
                title=session.title,
                model_type=session.model_type,
                model_name=session.model_name,
                is_active=session.is_active,
                created_at=session.created_at,
                updated_at=session.updated_at
            )
            for session in sessions
        ]
    except Exception as e:
        logger.error(f"Failed to get sessions for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user sessions")


@router.post("/messages", response_model=ChatMessage)
async def save_message(message_data: ChatMessage):
    """Save a chat message."""
    try:
        history_service = await get_sqlalchemy_chat_history_service()
        message = await history_service.save_message(message_data)
        
        # Convert SQLAlchemy model to Pydantic model
        return ChatMessage(
            id=str(message.id),
            session_id=str(message.session_id),
            role=message.role,
            content=message.content,
            tokens_used=message.tokens_used,
            model_used=message.model_used,
            mcp_tools_used=message.mcp_tools_used,
            metadata=message.meta_info,  # Convert meta_info to metadata
            created_at=message.created_at
        )
    except Exception as e:
        logger.error(f"Failed to save message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save message")


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_session_messages(session_id: str, limit: int = Query(100, ge=1, le=1000)):
    """Get messages for a session."""
    try:
        from uuid import UUID
        history_service = await get_sqlalchemy_chat_history_service()
        messages = await history_service.get_session_messages(UUID(session_id), limit)
        
        # Convert SQLAlchemy models to Pydantic models
        return [
            ChatMessage(
                id=str(message.id),
                session_id=str(message.session_id),
                role=message.role,
                content=message.content,
                tokens_used=message.tokens_used,
                model_used=message.model_used,
                mcp_tools_used=message.mcp_tools_used,
                metadata=message.meta_info,  # Convert meta_info to metadata
                created_at=message.created_at
            )
            for message in messages
        ]
    except Exception as e:
        logger.error(f"Failed to get messages for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session messages")


@router.post("/chat-history", response_model=ChatHistoryResponse)
async def get_chat_history(request: ChatHistoryRequest):
    """Get chat history for a user."""
    try:
        history_service = await get_sqlalchemy_chat_history_service()
        history = await history_service.get_chat_history(request)
        return history
    except Exception as e:
        logger.error(f"Failed to get chat history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get chat history")


@router.get("/users/{user_id}/stats")
async def get_user_stats(user_id: str):
    """Get user statistics."""
    try:
        from uuid import UUID
        history_service = await get_sqlalchemy_chat_history_service()
        stats = await history_service.get_user_stats(UUID(user_id))
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user stats")


@router.post("/chat/with-history", response_model=ChatWithHistoryResponse)
async def chat_with_history(request: ChatWithHistoryRequest):
    """Enhanced chat endpoint with history support."""
    try:
        history_service = await get_sqlalchemy_chat_history_service()

        # Get or create session
        session_id = request.session_id
        if not session_id and request.create_new_session:
            if not request.user_id:
                raise HTTPException(status_code=400, detail="user_id required to create new session")

            session_data = ChatSessionCreate(
                user_id=request.user_id,
                title=f"Chat Session {request.prompt[:50]}...",
                model_type=request.model_type,
                model_name=request.model_name or "gpt-3.5-turbo"
            )
            session = await history_service.create_session(session_data)
            session_id = session.id

        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required or create_new_session must be true")

        # Get session messages for context
        messages = []
        if session_id:
            session_messages = await history_service.get_session_messages(session_id, limit=20)
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in session_messages
            ]

        # Add current user message
        messages.append({"role": "user", "content": request.prompt})

        # Get LLM response
        # Convert messages to Message objects
        chat_messages = []
        for msg in messages:
            chat_messages.append(Message(
                role=msg["role"],
                content=msg["content"]
            ))
        
        chat_request = ChatRequest(
            messages=chat_messages,
            stream=False,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            model=request.model_name or "gpt-3.5-turbo"
        )
        
        llm_response_data = await llm_client.generate_text(chat_request)
        llm_response = llm_response_data.get("response", "")
        
        # Save user message
        user_message = ChatMessageCreate(
            session_id=session_id,
            role="user",
            content=request.prompt,
            model_used=request.model_name,
            metadata={"temperature": request.temperature, "max_tokens": request.max_tokens}
        )
        await history_service.save_message(user_message)

        # Save assistant message
        assistant_message = ChatMessageCreate(
            session_id=session_id,
            role="assistant",
            content=llm_response,
            model_used=request.model_name,
            metadata={"temperature": request.temperature, "max_tokens": request.max_tokens}
        )
        saved_message = await history_service.save_message(assistant_message)

        return ChatWithHistoryResponse(
            response=llm_response,
            session_id=session_id,
            message_id=saved_message.id,
            success=True,
            metadata={
                "model_used": request.model_name,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process chat with history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process chat with history") 