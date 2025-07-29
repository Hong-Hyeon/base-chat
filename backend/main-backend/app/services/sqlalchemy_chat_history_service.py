from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from app.models.database_models import User, UserPreferences, ChatSession, Message
from app.models.user import UserCreate, UserResponse, UserUpdate
from app.models.chat_history import (
    ChatSessionCreate, ChatSessionUpdate, ChatMessageCreate,
    ChatHistoryRequest, ChatHistoryResponse
)
from app.services.sqlalchemy_service import get_session
from app.utils.logger import get_logger

logger = get_logger("sqlalchemy_chat_history_service")


class SQLAlchemyChatHistoryService:
    """SQLAlchemy-based chat history service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        try:
            # Check if user already exists
            existing_user = await self.session.execute(
                select(User).where(
                    (User.username == user_data.username) | 
                    (User.email == user_data.email)
                )
            )
            if existing_user.scalar_one_or_none():
                raise ValueError("User with this username or email already exists")
            
            # Create new user
            user = User(
                id=uuid4(),
                username=user_data.username,
                email=user_data.email,
                password_hash=user_data.password,  # Use password as password_hash
                is_active=True
            )
            
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            
            logger.info(f"Created user: {user.username}")
            return user
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create user: {str(e)}")
            raise
    
    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        try:
            result = await self.session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            raise
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            result = await self.session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {str(e)}")
            raise
    
    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        """Update user."""
        try:
            user = await self.get_user(user_id)
            if not user:
                return None
            
            # Update fields
            if user_data.username is not None:
                user.username = user_data.username
            if user_data.email is not None:
                user.email = user_data.email
            if user_data.is_active is not None:
                user.is_active = user_data.is_active
            
            user.updated_at = datetime.utcnow()
            
            await self.session.commit()
            await self.session.refresh(user)
            
            logger.info(f"Updated user: {user.username}")
            return user
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update user {user_id}: {str(e)}")
            raise
    
    async def create_session(self, session_data: ChatSessionCreate) -> ChatSession:
        """Create a new chat session."""
        try:
            session = ChatSession(
                id=uuid4(),
                user_id=session_data.user_id,
                title=session_data.title,
                model_type=session_data.model_type,
                model_name=session_data.model_name,
                is_active=True
            )
            
            self.session.add(session)
            await self.session.commit()
            await self.session.refresh(session)
            
            logger.info(f"Created chat session: {session.id}")
            return session
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create session: {str(e)}")
            raise
    
    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """Get chat session by ID."""
        try:
            result = await self.session.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            raise
    
    async def get_user_sessions(self, user_id: UUID, limit: int = 50) -> List[ChatSession]:
        """Get chat sessions for a user."""
        try:
            result = await self.session.execute(
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {str(e)}")
            raise
    
    async def update_session(self, session_id: UUID, session_data: ChatSessionUpdate) -> Optional[ChatSession]:
        """Update chat session."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return None
            
            # Update fields
            if session_data.title is not None:
                session.title = session_data.title
            if session_data.is_active is not None:
                session.is_active = session_data.is_active
            
            session.updated_at = datetime.utcnow()
            
            await self.session.commit()
            await self.session.refresh(session)
            
            logger.info(f"Updated session: {session.id}")
            return session
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update session {session_id}: {str(e)}")
            raise
    
    async def save_message(self, message_data: ChatMessageCreate) -> Message:
        """Save a chat message."""
        try:
            message = Message(
                id=uuid4(),
                session_id=message_data.session_id,
                role=message_data.role,
                content=message_data.content,
                tokens_used=message_data.tokens_used,
                model_used=message_data.model_used,
                mcp_tools_used=message_data.mcp_tools_used,
                meta_info=message_data.metadata  # Use metadata as meta_info
            )
            
            self.session.add(message)
            await self.session.commit()
            await self.session.refresh(message)
            
            logger.info(f"Saved message: {message.id}")
            return message
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save message: {str(e)}")
            raise
    
    async def get_session_messages(self, session_id: UUID, limit: int = 100) -> List[Message]:
        """Get messages for a session."""
        try:
            result = await self.session.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at.asc())
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {str(e)}")
            raise
    
    async def get_chat_history(self, request: ChatHistoryRequest) -> ChatHistoryResponse:
        """Get chat history for a user."""
        try:
            # Get user sessions
            sessions = await self.get_user_sessions(request.user_id, request.limit)
            
            # Get messages for each session
            sessions_with_messages = []
            for session in sessions:
                messages = await self.get_session_messages(session.id, request.message_limit)
                sessions_with_messages.append({
                    "session": session,
                    "messages": messages
                })
            
            return ChatHistoryResponse(
                user_id=request.user_id,
                sessions=sessions_with_messages,
                total_sessions=len(sessions_with_messages)
            )
            
        except Exception as e:
            logger.error(f"Failed to get chat history for user {request.user_id}: {str(e)}")
            raise
    
    async def get_user_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            # Count sessions
            sessions_result = await self.session.execute(
                select(ChatSession).where(ChatSession.user_id == user_id)
            )
            total_sessions = len(sessions_result.scalars().all())
            
            # Count messages
            messages_result = await self.session.execute(
                select(Message)
                .join(ChatSession)
                .where(ChatSession.user_id == user_id)
            )
            total_messages = len(messages_result.scalars().all())
            
            return {
                "user_id": str(user_id),
                "total_sessions": total_sessions,
                "total_messages": total_messages
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for user {user_id}: {str(e)}")
            raise


async def get_sqlalchemy_chat_history_service() -> SQLAlchemyChatHistoryService:
    """Get SQLAlchemy chat history service instance."""
    async for session in get_session():
        return SQLAlchemyChatHistoryService(session) 