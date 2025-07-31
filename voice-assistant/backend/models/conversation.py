"""
Conversation Models
Data models for managing conversation sessions and interactions
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import json

logger = logging.getLogger(__name__)

@dataclass
class ConversationSession:
    """Represents a conversation session with a user"""
    id: str
    client_id: str
    user_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: str = "active"  # active, ended, error
    total_interactions: int = 0
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_interaction(self, user_message: str, ai_response: str, confidence: float = 1.0):
        """Add an interaction to the conversation history"""
        self.conversation_history.extend([
            {
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat(),
                "confidence": confidence
            },
            {
                "role": "assistant", 
                "content": ai_response,
                "timestamp": datetime.now().isoformat()
            }
        ])
        self.total_interactions += 1
        
        # Keep only last 50 messages to manage memory
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
    
    def get_duration(self) -> float:
        """Get conversation duration in seconds"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for storage"""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "total_interactions": self.total_interactions,
            "conversation_history": self.conversation_history,
            "metadata": self.metadata,
            "duration": self.get_duration()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSession':
        """Create session from dictionary"""
        session = cls(
            id=data["id"],
            client_id=data["client_id"],
            user_id=data.get("user_id"),
            start_time=datetime.fromisoformat(data["start_time"]),
            status=data.get("status", "active"),
            total_interactions=data.get("total_interactions", 0),
            conversation_history=data.get("conversation_history", []),
            metadata=data.get("metadata", {})
        )
        
        if data.get("end_time"):
            session.end_time = datetime.fromisoformat(data["end_time"])
            
        return session

class ConversationManager:
    """Manages conversation sessions and their lifecycle"""
    
    def __init__(self):
        self.active_sessions: Dict[str, ConversationSession] = {}
        self.session_history: List[ConversationSession] = []
        self.max_active_sessions = 1000  # Prevent memory issues
        
    async def create_session(self, client_id: str, user_id: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        
        session = ConversationSession(
            id=session_id,
            client_id=client_id,
            user_id=user_id,
            metadata={
                "created_by": "voice_assistant",
                "version": "1.0"
            }
        )
        
        # Clean up old sessions if we're at the limit
        if len(self.active_sessions) >= self.max_active_sessions:
            await self._cleanup_old_sessions()
        
        self.active_sessions[client_id] = session
        logger.info(f"Created new session {session_id} for client {client_id}")
        
        return session
    
    async def get_session(self, client_id: str) -> Optional[ConversationSession]:
        """Get an active session by client ID"""
        return self.active_sessions.get(client_id)
    
    async def end_session(self, client_id: str) -> Optional[ConversationSession]:
        """End a conversation session"""
        session = self.active_sessions.get(client_id)
        
        if session:
            session.end_time = datetime.now()
            session.status = "ended"
            
            # Move to history
            self.session_history.append(session)
            del self.active_sessions[client_id]
            
            logger.info(f"Ended session {session.id} for client {client_id}")
            return session
        
        return None
    
    async def add_interaction(
        self, 
        client_id: str, 
        user_message: str, 
        ai_response: str, 
        confidence: float = 1.0
    ) -> bool:
        """Add an interaction to a session"""
        session = self.active_sessions.get(client_id)
        
        if session:
            session.add_interaction(user_message, ai_response, confidence)
            logger.debug(f"Added interaction to session {session.id}")
            return True
        
        logger.warning(f"No active session found for client {client_id}")
        return False
    
    async def get_session_analytics(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get analytics for a specific session"""
        session = self.active_sessions.get(client_id)
        
        if not session:
            # Check history
            for hist_session in self.session_history:
                if hist_session.client_id == client_id:
                    session = hist_session
                    break
        
        if session:
            return {
                "session_id": session.id,
                "client_id": session.client_id,
                "user_id": session.user_id,
                "duration": session.get_duration(),
                "total_interactions": session.total_interactions,
                "status": session.status,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "conversation_length": len(session.conversation_history),
                "average_confidence": self._calculate_average_confidence(session)
            }
        
        return None
    
    def _calculate_average_confidence(self, session: ConversationSession) -> float:
        """Calculate average confidence score for a session"""
        user_messages = [
            msg for msg in session.conversation_history 
            if msg["role"] == "user" and "confidence" in msg
        ]
        
        if not user_messages:
            return 0.0
        
        total_confidence = sum(msg["confidence"] for msg in user_messages)
        return total_confidence / len(user_messages)
    
    async def get_all_sessions_analytics(self) -> Dict[str, Any]:
        """Get analytics for all sessions"""
        all_sessions = list(self.active_sessions.values()) + self.session_history
        
        if not all_sessions:
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "completed_sessions": 0,
                "average_duration": 0.0,
                "total_interactions": 0,
                "average_interactions_per_session": 0.0
            }
        
        active_count = len(self.active_sessions)
        completed_count = len(self.session_history)
        total_duration = sum(session.get_duration() for session in all_sessions)
        total_interactions = sum(session.total_interactions for session in all_sessions)
        
        return {
            "total_sessions": len(all_sessions),
            "active_sessions": active_count,
            "completed_sessions": completed_count,
            "average_duration": total_duration / len(all_sessions),
            "total_interactions": total_interactions,
            "average_interactions_per_session": total_interactions / len(all_sessions) if all_sessions else 0
        }
    
    async def _cleanup_old_sessions(self):
        """Clean up old inactive sessions"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        for client_id, session in self.active_sessions.items():
            # Remove sessions older than 1 hour with no recent activity
            if (current_time - session.start_time).total_seconds() > 3600:
                sessions_to_remove.append(client_id)
        
        for client_id in sessions_to_remove:
            await self.end_session(client_id)
        
        logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
    
    async def export_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export session data for analysis or storage"""
        # Find session in active or history
        session = None
        
        for s in self.active_sessions.values():
            if s.id == session_id:
                session = s
                break
        
        if not session:
            for s in self.session_history:
                if s.id == session_id:
                    session = s
                    break
        
        if session:
            return session.to_dict()
        
        return None
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a specific user"""
        user_sessions = []
        
        # Check active sessions
        for session in self.active_sessions.values():
            if session.user_id == user_id:
                user_sessions.append(session.to_dict())
        
        # Check history
        for session in self.session_history:
            if session.user_id == user_id:
                user_sessions.append(session.to_dict())
        
        # Sort by start time (most recent first)
        user_sessions.sort(key=lambda x: x["start_time"], reverse=True)
        
        return user_sessions
