"""
Database Models
SQLAlchemy models for storing voice assistant data
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, JSON
from sqlalchemy.sql import func
from .database import Base

class CallSession(Base):
    """Model for storing call session data"""
    __tablename__ = "call_sessions"
    
    id = Column(String, primary_key=True, index=True)
    client_id = Column(String, index=True)
    user_id = Column(String, index=True, nullable=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Float, default=0.0)
    total_interactions = Column(Integer, default=0)
    status = Column(String, default="active")  # active, ended, error
    conversation_history = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Interaction(Base):
    """Model for storing individual interactions"""
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_message = Column(Text)
    ai_response = Column(Text)
    confidence = Column(Float, default=1.0)
    intent = Column(String, nullable=True)
    question_category = Column(String, nullable=True)
    processing_time = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class ErrorLog(Base):
    """Model for storing error logs"""
    __tablename__ = "error_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    error_type = Column(String, index=True)
    error_message = Column(Text)
    stack_trace = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class PerformanceMetric(Base):
    """Model for storing performance metrics"""
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    metric_name = Column(String, index=True)
    metric_value = Column(Float)
    metric_unit = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class KnowledgeBase(Base):
    """Model for storing knowledge base entries"""
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    category = Column(String, index=True)
    entry_type = Column(String, index=True)  # faq, guideline, user_info
    user_id = Column(String, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserFeedback(Base):
    """Model for storing user feedback"""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(String, index=True, nullable=True)
    rating = Column(Integer)  # 1-5 scale
    feedback_text = Column(Text, nullable=True)
    feedback_type = Column(String)  # satisfaction, complaint, suggestion
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
