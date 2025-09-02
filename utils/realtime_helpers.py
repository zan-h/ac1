"""
Realtime API Helper Functions

This module provides utility functions specifically for the realtime API,
including audio processing, session management, and error handling.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

from utils.common import logger


class SessionManager:
    """Manages user sessions for the realtime API."""
    
    def __init__(self):
        self.active_sessions = {}
        self.session_history = {}
    
    def create_session(self, user_id: str = None) -> str:
        """Create a new session and return session ID."""
        import uuid
        session_id = str(uuid.uuid4())
        
        session_data = {
            "id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "conversation_count": 0,
            "total_audio_duration": 0,
            "metadata": {}
        }
        
        self.active_sessions[session_id] = session_data
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by ID."""
        return self.active_sessions.get(session_id)
    
    def update_session_activity(self, session_id: str):
        """Update last activity timestamp for a session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = datetime.utcnow()
    
    def increment_conversation_count(self, session_id: str):
        """Increment conversation count for a session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["conversation_count"] += 1
    
    def add_audio_duration(self, session_id: str, duration_seconds: float):
        """Add audio duration to session statistics."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["total_audio_duration"] += duration_seconds
    
    def end_session(self, session_id: str) -> bool:
        """End a session and move it to history."""
        if session_id in self.active_sessions:
            session_data = self.active_sessions.pop(session_id)
            session_data["ended_at"] = datetime.utcnow()
            session_data["duration"] = (
                session_data["ended_at"] - session_data["created_at"]
            ).total_seconds()
            
            self.session_history[session_id] = session_data
            logger.info(f"Ended session: {session_id}")
            return True
        return False
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up sessions older than specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        sessions_to_remove = []
        
        for session_id, session_data in self.active_sessions.items():
            if session_data["last_activity"] < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self.end_session(session_id)
        
        logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
        return len(sessions_to_remove)


class AudioValidator:
    """Validates and processes audio data for the realtime API."""
    
    @staticmethod
    def validate_audio_format(audio_data: Union[bytes, np.ndarray], 
                            expected_format: str = "pcm16") -> bool:
        """Validate audio format compatibility."""
        try:
            if expected_format == "pcm16":
                if isinstance(audio_data, bytes):
                    # Check if length is even (int16 requires 2 bytes per sample)
                    return len(audio_data) % 2 == 0
                elif isinstance(audio_data, np.ndarray):
                    return audio_data.dtype in [np.int16, np.float32]
            return False
        except Exception as e:
            logger.error(f"Audio validation error: {e}")
            return False
    
    @staticmethod
    def estimate_audio_duration(audio_data: Union[bytes, np.ndarray], 
                              sample_rate: int = 24000) -> float:
        """Estimate audio duration in seconds."""
        try:
            if isinstance(audio_data, bytes):
                # PCM16: 2 bytes per sample
                num_samples = len(audio_data) // 2
            elif isinstance(audio_data, np.ndarray):
                num_samples = len(audio_data)
            else:
                return 0.0
            
            return num_samples / sample_rate
        except Exception as e:
            logger.error(f"Duration estimation error: {e}")
            return 0.0
    
    @staticmethod
    def normalize_audio_volume(audio_data: np.ndarray, target_level: float = 0.7) -> np.ndarray:
        """Normalize audio volume to target level."""
        try:
            if audio_data.dtype == np.float32:
                # Find the maximum absolute value
                max_val = np.max(np.abs(audio_data))
                if max_val > 0:
                    # Scale to target level
                    scale_factor = target_level / max_val
                    return audio_data * scale_factor
            return audio_data
        except Exception as e:
            logger.error(f"Audio normalization error: {e}")
            return audio_data


class RealtimeErrorHandler:
    """Handles errors and provides retry logic for realtime API."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_counts = {}
    
    async def with_retry(self, operation, *args, **kwargs):
        """Execute operation with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_type = type(e).__name__
                
                # Track error counts
                self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
                
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Operation failed (attempt {attempt + 1}): {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Operation failed after {self.max_retries} retries: {e}")
        
        raise last_exception
    
    def get_error_statistics(self) -> Dict[str, int]:
        """Get error statistics."""
        return self.error_counts.copy()
    
    def reset_error_counts(self):
        """Reset error counters."""
        self.error_counts.clear()


class ConfigurationLoader:
    """Loads and validates configuration files."""
    
    @staticmethod
    def load_instructions(file_path: str = None) -> str:
        """Load instruction text from file."""
        if not file_path:
            # Default path
            current_dir = Path(__file__).parent.parent
            file_path = current_dir / "config" / "realtime_instructions.txt"
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                instructions = f.read().strip()
                logger.info(f"Loaded instructions from {file_path}")
                return instructions
        except FileNotFoundError:
            logger.warning(f"Instructions file not found: {file_path}")
            return "You are a helpful AI assistant with voice capabilities."
        except Exception as e:
            logger.error(f"Error loading instructions: {e}")
            return "You are a helpful AI assistant with voice capabilities."
    
    @staticmethod
    def validate_environment_variables() -> Dict[str, bool]:
        """Validate required environment variables."""
        required_vars = [
            "OPENAI_API_KEY",
        ]
        
        optional_vars = [
            "USE_AZURE",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT"
        ]
        
        results = {}
        
        # Check required variables
        for var in required_vars:
            results[var] = bool(os.getenv(var))
            if not results[var]:
                logger.warning(f"Required environment variable missing: {var}")
        
        # Check optional variables
        for var in optional_vars:
            results[var] = bool(os.getenv(var))
        
        # Special check for Azure configuration
        use_azure = os.getenv("USE_AZURE", "false").lower() == "true"
        if use_azure:
            azure_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]
            for var in azure_vars:
                if not results.get(var):
                    logger.warning(f"Azure is enabled but {var} is missing")
        
        return results


class PerformanceMonitor:
    """Monitors performance metrics for the realtime API."""
    
    def __init__(self):
        self.metrics = {
            "connection_attempts": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "audio_chunks_processed": 0,
            "average_response_time": 0,
            "response_times": [],
            "session_durations": [],
            "error_counts": {}
        }
        self.start_time = datetime.utcnow()
    
    def record_connection_attempt(self, success: bool = True):
        """Record a connection attempt."""
        self.metrics["connection_attempts"] += 1
        if success:
            self.metrics["successful_connections"] += 1
        else:
            self.metrics["failed_connections"] += 1
    
    def record_message(self, direction: str = "sent"):
        """Record a message sent or received."""
        if direction == "sent":
            self.metrics["messages_sent"] += 1
        elif direction == "received":
            self.metrics["messages_received"] += 1
    
    def record_audio_chunk(self):
        """Record an audio chunk processed."""
        self.metrics["audio_chunks_processed"] += 1
    
    def record_response_time(self, response_time: float):
        """Record response time."""
        self.metrics["response_times"].append(response_time)
        # Keep only last 100 response times for average calculation
        if len(self.metrics["response_times"]) > 100:
            self.metrics["response_times"] = self.metrics["response_times"][-100:]
        
        # Update average
        self.metrics["average_response_time"] = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
    
    def record_session_duration(self, duration: float):
        """Record session duration."""
        self.metrics["session_durations"].append(duration)
    
    def record_error(self, error_type: str):
        """Record an error occurrence."""
        self.metrics["error_counts"][error_type] = self.metrics["error_counts"].get(error_type, 0) + 1
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        summary = self.metrics.copy()
        summary.update({
            "uptime_seconds": uptime,
            "connection_success_rate": (
                self.metrics["successful_connections"] / max(self.metrics["connection_attempts"], 1)
            ),
            "average_session_duration": (
                sum(self.metrics["session_durations"]) / max(len(self.metrics["session_durations"]), 1)
            ),
            "messages_per_second": self.metrics["messages_sent"] / max(uptime, 1)
        })
        
        return summary
    
    def reset_metrics(self):
        """Reset all metrics."""
        for key in self.metrics:
            if isinstance(self.metrics[key], (int, float)):
                self.metrics[key] = 0
            elif isinstance(self.metrics[key], list):
                self.metrics[key] = []
            elif isinstance(self.metrics[key], dict):
                self.metrics[key] = {}
        
        self.start_time = datetime.utcnow()


# Global instances
session_manager = SessionManager()
error_handler = RealtimeErrorHandler()
performance_monitor = PerformanceMonitor()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    return session_manager


def get_error_handler() -> RealtimeErrorHandler:
    """Get the global error handler instance."""
    return error_handler


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return performance_monitor