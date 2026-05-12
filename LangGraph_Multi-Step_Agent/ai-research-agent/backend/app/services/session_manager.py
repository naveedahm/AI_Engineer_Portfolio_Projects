from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import json
import logging
from app.api.models import Message, SessionInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage chat sessions and history"""
    
    def __init__(self):
        self._sessions: Dict[str, List[Message]] = defaultdict(list)
        self._session_metadata: Dict[str, SessionInfo] = {}
        self._lock = asyncio.Lock()
    
    async def add_message(self, thread_id: str, message: Message) -> None:
        """Add a message to a session"""
        async with self._lock:
            if thread_id not in self._sessions:
                self._create_session(thread_id)
            
            self._sessions[thread_id].append(message)
            
            # Trim history if needed
            if len(self._sessions[thread_id]) > settings.MAX_HISTORY_LENGTH:
                self._sessions[thread_id] = self._sessions[thread_id][-settings.MAX_HISTORY_LENGTH:]
            
            # Update metadata
            if thread_id in self._session_metadata:
                self._session_metadata[thread_id].last_updated = datetime.now()
                self._session_metadata[thread_id].message_count = len(self._sessions[thread_id])
    
    async def get_history(self, thread_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get message history for a session"""
        async with self._lock:
            messages = self._sessions.get(thread_id, [])
            if limit:
                messages = messages[-limit:]
            return messages.copy()
    
    async def get_session_info(self, thread_id: str) -> Optional[SessionInfo]:
        """Get session metadata"""
        async with self._lock:
            return self._session_metadata.get(thread_id)
    
    async def delete_session(self, thread_id: str) -> bool:
        """Delete a session"""
        async with self._lock:
            if thread_id in self._sessions:
                del self._sessions[thread_id]
                if thread_id in self._session_metadata:
                    del self._session_metadata[thread_id]
                logger.info(f"Deleted session: {thread_id}")
                return True
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        async with self._lock:
            now = datetime.now()
            expired = []
            
            for thread_id, info in self._session_metadata.items():
                if now - info.last_updated > timedelta(seconds=settings.SESSION_TTL):
                    expired.append(thread_id)
            
            for thread_id in expired:
                await self.delete_session(thread_id)
            
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")
            
            return len(expired)
    
    def _create_session(self, thread_id: str) -> None:
        """Create a new session"""
        self._session_metadata[thread_id] = SessionInfo(
            thread_id=thread_id,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            message_count=0,
            metadata={
                "session_ttl": settings.SESSION_TTL,
                "max_history": settings.MAX_HISTORY_LENGTH
            }
        )
        logger.info(f"Created new session: {thread_id}")


# Start cleanup task if needed
_session_manager = SessionManager()


async def start_cleanup_task():
    """Background task to clean up expired sessions"""
    while True:
        await asyncio.sleep(3600)  # Run every hour
        await _session_manager.cleanup_expired_sessions()


def get_session_manager() -> SessionManager:
    """Get session manager instance"""
    return _session_manager