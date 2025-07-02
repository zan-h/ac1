"""
Database models for AgencyCoachAI.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid

from database import Base, AsyncSessionLocal

class User(Base):
    """User model for storing user information."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    sessions = relationship("Session", back_populates="user")

class Session(Base):
    """Session model for tracking therapy sessions."""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    session_notes = Column(Text, nullable=True)
    emotional_summary = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    tasks = relationship("Task", back_populates="session")
    emotional_notes = relationship("EmotionalNote", back_populates="session")
    conversation_logs = relationship("ConversationLog", back_populates="session")

class Task(Base):
    """Task model for tracking commitments and goals."""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    description = Column(Text, nullable=False)
    completed = Column(Boolean, default=False)
    priority = Column(String, default="medium")  # low, medium, high
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="tasks")

class EmotionalNote(Base):
    """Emotional analysis and notes for sessions."""
    __tablename__ = "emotional_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    emotion = Column(String, nullable=False)  # e.g., "anxious", "motivated", "overwhelmed"
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    context = Column(Text, nullable=True)  # What triggered this emotion
    timestamp = Column(DateTime, default=func.now())
    
    # Relationships
    session = relationship("Session", back_populates="emotional_notes")

class ConversationLog(Base):
    """Log of conversation messages for analysis and continuity."""
    __tablename__ = "conversation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    speaker = Column(String, nullable=False)  # "user" or "assistant"
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    audio_duration = Column(Float, nullable=True)  # Duration in seconds for audio messages
    
    # Relationships
    session = relationship("Session", back_populates="conversation_logs")

class SessionManager:
    """Manager class for session operations."""
    
    async def create_session(self, session_id: str, user_id: Optional[int] = None) -> Session:
        """Create a new therapy session."""
        async with AsyncSessionLocal() as db:
            session = Session(id=session_id, user_id=user_id)
            db.add(session)
            await db.commit()
            await db.refresh(session)
            return session
    
    async def end_session(self, session_id: str) -> Session:
        """End a therapy session."""
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            if session:
                session.ended_at = datetime.utcnow()
                if session.started_at:
                    duration = session.ended_at - session.started_at
                    session.duration_seconds = int(duration.total_seconds())
                await db.commit()
                await db.refresh(session)
            return session
    
    async def log_user_message(self, session_id: str, message: str, audio_duration: Optional[float] = None):
        """Log a user message."""
        async with AsyncSessionLocal() as db:
            log = ConversationLog(
                session_id=session_id,
                speaker="user",
                message=message,
                audio_duration=audio_duration
            )
            db.add(log)
            await db.commit()
    
    async def log_assistant_message(self, session_id: str, message: str, audio_duration: Optional[float] = None):
        """Log an assistant message."""
        async with AsyncSessionLocal() as db:
            log = ConversationLog(
                session_id=session_id,
                speaker="assistant", 
                message=message,
                audio_duration=audio_duration
            )
            db.add(log)
            await db.commit()
    
    async def add_emotional_note(self, session_id: str, emotion: str, confidence: float, context: str = None):
        """Add an emotional analysis note."""
        async with AsyncSessionLocal() as db:
            note = EmotionalNote(
                session_id=session_id,
                emotion=emotion,
                confidence=confidence,
                context=context
            )
            db.add(note)
            await db.commit()
    
    async def add_task(self, session_id: str, description: str, priority: str = "medium") -> Task:
        """Add a task/commitment from the session."""
        async with AsyncSessionLocal() as db:
            task = Task(
                session_id=session_id,
                description=description,
                priority=priority
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)
            return task
    
    async def complete_task(self, task_id: int) -> Task:
        """Mark a task as completed."""
        async with AsyncSessionLocal() as db:
            task = await db.get(Task, task_id)
            if task:
                task.completed = True
                task.completed_at = datetime.utcnow()
                await db.commit()
                await db.refresh(task)
            return task
    
    async def update_session_analysis(self, session_id: str, sentiment: Dict, tasks: List[str], insights: str):
        """Update session with analysis results."""
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            if session:
                # Store sentiment as emotional note
                if sentiment and "emotion" in sentiment:
                    await self.add_emotional_note(
                        session_id, 
                        sentiment["emotion"], 
                        sentiment.get("confidence", 0.5),
                        sentiment.get("context", "")
                    )
                
                # Add extracted tasks
                for task_desc in tasks:
                    await self.add_task(session_id, task_desc)
                
                # Update session notes with insights
                if insights:
                    current_notes = session.session_notes or ""
                    session.session_notes = f"{current_notes}\n\nInsights: {insights}"
                    await db.commit()
    
    async def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """Get complete session history."""
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            if not session:
                return {}
            
            # Get conversation logs
            conversation = await db.execute(
                "SELECT * FROM conversation_logs WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            
            # Get tasks
            tasks = await db.execute(
                "SELECT * FROM tasks WHERE session_id = ?",
                (session_id,)
            )
            
            # Get emotional notes
            emotions = await db.execute(
                "SELECT * FROM emotional_notes WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            
            return {
                "session": session,
                "conversation": conversation.fetchall(),
                "tasks": tasks.fetchall(),
                "emotions": emotions.fetchall()
            }