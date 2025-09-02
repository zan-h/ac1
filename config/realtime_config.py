"""
Realtime API Configuration Module

This module manages configuration settings for the OpenAI Realtime API,
including session parameters, voice settings, and connection details.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class RealtimeConfig:
    """Configuration manager for OpenAI Realtime API settings."""
    
    def __init__(self):
        self.load_environment_variables()
        self.setup_default_session_config()
        self.setup_connection_config()
    
    def load_environment_variables(self):
        """Load necessary environment variables."""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.use_azure = os.getenv("USE_AZURE", "false").lower() == "true"
        
        if self.use_azure:
            self.azure_endpoint = os.getenv("AZURE_OPENAI_URL") or os.getenv("AZURE_OPENAI_ENDPOINT")
            self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            self.azure_deployment = os.getenv("OPENAI_DEPLOYMENT_NAME_REALTIME") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini-realtime-preview")
            self.azure_api_version = os.getenv("AZURE_API_VERSION", "2024-10-01-preview")
    
    def setup_default_session_config(self):
        """Configure default session parameters."""
        self.session_config = {
            "modalities": ["text", "audio"],
            "voice": "alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "whisper-1"
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500
            },
            "tools": [],
            "tool_choice": "auto",
            "temperature": 0.7,
            "max_response_output_tokens": 4096
        }
    
    def setup_connection_config(self):
        """Configure connection parameters."""
        self.connection_config = {
            "model": "gpt-4o-realtime-preview-2024-10-01",
            "base_url": "wss://api.openai.com/v1/realtime",
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0
        }
        
        if self.use_azure:
            self.connection_config["base_url"] = f"wss://{self.azure_endpoint}/openai/realtime"
            self.connection_config["api_version"] = self.azure_api_version
            self.connection_config["deployment"] = self.azure_deployment
    
    def get_session_config(self) -> Dict[str, Any]:
        """Get the current session configuration."""
        return self.session_config.copy()
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get the current connection configuration."""
        return self.connection_config.copy()
    
    def update_session_config(self, updates: Dict[str, Any]):
        """Update session configuration with new values."""
        self.session_config.update(updates)
    
    def get_websocket_url(self) -> str:
        """Generate the WebSocket URL for connection."""
        if self.use_azure:
            return f"{self.connection_config['base_url']}?api-version={self.azure_api_version}&deployment={self.azure_deployment}"
        else:
            return f"{self.connection_config['base_url']}?model={self.connection_config['model']}"
    
    def get_headers(self) -> Dict[str, str]:
        """Generate headers for WebSocket connection."""
        if self.use_azure:
            return {
                "api-key": self.azure_api_key,
                "Content-Type": "application/json"
            }
        else:
            return {
                "Authorization": f"Bearer {self.openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
    
    def validate_config(self) -> bool:
        """Validate that all required configuration is present."""
        if self.use_azure:
            return all([
                self.azure_endpoint,
                self.azure_api_key,
                self.azure_deployment
            ])
        else:
            return bool(self.openai_api_key)


# Global configuration instance
realtime_config = RealtimeConfig()