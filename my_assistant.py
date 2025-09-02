"""
Voice-Enabled AI Assistant

A comprehensive voice assistant built with Chainlit and OpenAI's Realtime API,
providing natural conversation capabilities with integrated tools and functions.
"""

import os
import asyncio
import logging
from uuid import uuid4
from typing import Dict, Any, Optional
from datetime import datetime
import chainlit as cl
from chainlit.logger import logger

from realtime import RealtimeClient
from tools import tools
from utils.realtime_helpers import (
    session_manager, 
    performance_monitor, 
    error_handler
)
from config.realtime_config import realtime_config


class VoiceAssistantManager:
    """Manages the voice assistant's core functionality and state."""
    
    def __init__(self):
        self.realtime_client = None
        self.session_id = None
        self.audio_track_id = None
        self.is_initialized = False
        self.conversation_context = []
        
    async def initialize_assistant(self) -> bool:
        """Initialize the voice assistant with all necessary components."""
        try:
            # Create new session
            self.session_id = session_manager.create_session()
            self.audio_track_id = str(uuid4())
            
            # Initialize realtime client
            self.realtime_client = RealtimeClient()
            
            # Register event handlers
            self._register_event_handlers()
            
            # Register tools
            await self._register_tools()
            
            # Store in session
            cl.user_session.set("assistant_manager", self)
            cl.user_session.set("session_id", self.session_id)
            cl.user_session.set("audio_track_id", self.audio_track_id)
            
            self.is_initialized = True
            logger.info(f"Voice assistant initialized with session: {self.session_id}")
            
            # Record initialization metrics
            performance_monitor.record_connection_attempt(success=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Assistant initialization failed: {e}")
            performance_monitor.record_connection_attempt(success=False)
            performance_monitor.record_error("initialization_error")
            return False
    
    def _register_event_handlers(self):
        """Register all necessary event handlers for the realtime client."""
        
        # Handle conversation updates (audio streaming)
        self.realtime_client.on("conversation.updated", self._handle_conversation_updated)
        
        # Handle completed conversation items
        self.realtime_client.on("conversation.item.completed", self._handle_item_completed)
        
        # Handle conversation interruptions
        self.realtime_client.on("conversation.interrupted", self._handle_conversation_interrupted)
        
        # Handle errors
        self.realtime_client.on("error", self._handle_error)
        
        # Handle session events
        self.realtime_client.on("session.created", self._handle_session_created)
    
    async def _register_tools(self):
        """Register all available tools with the realtime client."""
        try:
            for tool_definition, tool_handler in tools:
                await self.realtime_client.add_tool(tool_definition, tool_handler)
            
            logger.info(f"Registered {len(tools)} tools with realtime client")
            
        except Exception as e:
            logger.error(f"Tool registration failed: {e}")
            raise
    
    async def _handle_conversation_updated(self, event: Dict[str, Any]):
        """Handle conversation update events, primarily for audio streaming."""
        try:
            item = event.get("item")
            delta = event.get("delta")
            
            if delta:
                # Handle audio output streaming
                if "audio" in delta:
                    audio_data = delta["audio"]
                    await cl.context.emitter.send_audio_chunk(
                        cl.OutputAudioChunk(
                            mimeType="pcm16",
                            data=audio_data,
                            track=self.audio_track_id,
                        )
                    )
                    performance_monitor.record_audio_chunk()
                
                # Handle transcript updates
                if "transcript" in delta:
                    transcript = delta["transcript"]
                    self._update_conversation_context("assistant", transcript)
                
                # Handle function call arguments
                if "arguments" in delta:
                    # Function arguments are being streamed
                    pass
            
            # Update session activity
            if self.session_id:
                session_manager.update_session_activity(self.session_id)
                
        except Exception as e:
            logger.error(f"Error handling conversation update: {e}")
            performance_monitor.record_error("conversation_update_error")
    
    async def _handle_item_completed(self, event: Dict[str, Any]):
        """Handle completed conversation items."""
        try:
            item = event.get("item")
            if item:
                # Update conversation context with completed item
                item_type = item.get("type", "")
                formatted_content = item.get("formatted", {})
                
                if item_type == "message":
                    role = item.get("role", "unknown")
                    text_content = formatted_content.get("text", "")
                    if text_content:
                        self._update_conversation_context(role, text_content)
                
                # Increment conversation count
                if self.session_id:
                    session_manager.increment_conversation_count(self.session_id)
            
        except Exception as e:
            logger.error(f"Error handling completed item: {e}")
    
    async def _handle_conversation_interrupted(self, event: Dict[str, Any]):
        """Handle conversation interruptions (user speaking while assistant is responding)."""
        try:
            # Generate new audio track ID to cancel previous audio
            self.audio_track_id = str(uuid4())
            cl.user_session.set("audio_track_id", self.audio_track_id)
            
            # Send audio interrupt signal
            await cl.context.emitter.send_audio_interrupt()
            
            logger.info("Conversation interrupted by user")
            
        except Exception as e:
            logger.error(f"Error handling conversation interrupt: {e}")
    
    async def _handle_error(self, event: Dict[str, Any]):
        """Handle error events from the realtime API."""
        error_info = event.get("error", {})
        error_message = error_info.get("message", "Unknown error")
        error_code = error_info.get("code", "unknown")
        
        logger.error(f"Realtime API error [{error_code}]: {error_message}")
        performance_monitor.record_error(f"realtime_api_{error_code}")
        
        # Optionally send error message to user interface
        if error_code in ["rate_limit_exceeded", "invalid_api_key"]:
            await cl.ErrorMessage(
                content=f"⚠️ Service temporarily unavailable: {error_message}"
            ).send()
    
    async def _handle_session_created(self, event: Dict[str, Any]):
        """Handle session creation events."""
        session_info = event.get("session", {})
        logger.info(f"Realtime session created: {session_info.get('id', 'unknown')}")
    
    def _update_conversation_context(self, role: str, content: str):
        """Update the conversation context for potential future use."""
        self.conversation_context.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 20 messages to prevent memory bloat
        if len(self.conversation_context) > 20:
            self.conversation_context = self.conversation_context[-20:]
    
    async def connect_realtime(self) -> bool:
        """Establish connection to the OpenAI Realtime API."""
        try:
            if not self.realtime_client:
                raise RuntimeError("Realtime client not initialized")
            
            # Attempt connection with retry logic
            success = await error_handler.with_retry(
                self.realtime_client.connect
            )
            
            if success:
                logger.info("Successfully connected to OpenAI Realtime API")
                return True
            else:
                logger.error("Failed to connect to Realtime API")
                return False
                
        except Exception as e:
            logger.error(f"Realtime connection error: {e}")
            performance_monitor.record_error("connection_error")
            return False
    
    async def send_text_message(self, message_content: str):
        """Send a text message through the realtime API."""
        try:
            if self.realtime_client and self.realtime_client.is_connected():
                await self.realtime_client.send_user_message_content([
                    {"type": "input_text", "text": message_content}
                ])
                
                # Update conversation context
                self._update_conversation_context("user", message_content)
                
                # Record metrics
                performance_monitor.record_message("sent")
                
                return True
            else:
                logger.warning("Cannot send message: Realtime client not connected")
                return False
                
        except Exception as e:
            logger.error(f"Error sending text message: {e}")
            performance_monitor.record_error("message_send_error")
            return False
    
    async def send_audio_data(self, audio_chunk: bytes):
        """Send audio data to the realtime API."""
        try:
            if self.realtime_client and self.realtime_client.is_connected():
                await self.realtime_client.append_input_audio(audio_chunk)
                
                # Estimate and record audio duration
                from utils.realtime_helpers import AudioValidator
                duration = AudioValidator.estimate_audio_duration(audio_chunk)
                if self.session_id:
                    session_manager.add_audio_duration(self.session_id, duration)
                
                return True
            else:
                logger.warning("Cannot send audio: Realtime client not connected")
                return False
                
        except Exception as e:
            logger.error(f"Error sending audio data: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the realtime API and cleanup."""
        try:
            if self.realtime_client and self.realtime_client.is_connected():
                await self.realtime_client.disconnect()
            
            # End session
            if self.session_id:
                session_manager.end_session(self.session_id)
            
            logger.info("Voice assistant disconnected")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")


@cl.on_chat_start
async def on_chat_start():
    """Initialize the voice assistant when a new chat session starts."""
    try:
        # Display welcome message
        welcome_message = """
# 🎙️ Voice Assistant Ready!

Welcome to your AI-powered voice assistant! Here's what you can do:

**Voice Mode**: Press `P` to talk or use the microphone button
**Text Mode**: Type your questions in the chat

**Available Features**:
- 🌐 Web search for current information
- 📈 Stock market data and charts
- 🎨 Image generation
- 🌤️ Weather information
- 📝 Task creation and management
- 💭 Sentiment analysis
- 🗄️ Database queries
- ⏰ Time and date information

Just start talking or typing to begin!
        """
        
        await cl.Message(content=welcome_message).send()
        
        # Initialize the assistant
        assistant_manager = VoiceAssistantManager()
        initialization_success = await assistant_manager.initialize_assistant()
        
        if not initialization_success:
            await cl.ErrorMessage(
                content="⚠️ Failed to initialize voice assistant. Some features may be limited."
            ).send()
        
    except Exception as e:
        logger.error(f"Chat start error: {e}")
        await cl.ErrorMessage(
            content="⚠️ Failed to start voice assistant. Please refresh and try again."
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming text messages."""
    try:
        assistant_manager: VoiceAssistantManager = cl.user_session.get("assistant_manager")
        
        if not assistant_manager:
            await cl.ErrorMessage(
                content="⚠️ Assistant not initialized. Please refresh the page."
            ).send()
            return
        
        # Send message through the realtime API if connected
        if assistant_manager.realtime_client and assistant_manager.realtime_client.is_connected():
            success = await assistant_manager.send_text_message(message.content)
            if not success:
                await cl.ErrorMessage(
                    content="⚠️ Failed to send message. Please try again or use voice mode."
                ).send()
        else:
            await cl.Message(
                content="🎙️ Please activate voice mode by pressing `P` or clicking the microphone button to start the conversation!"
            ).send()
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await cl.ErrorMessage(
            content="⚠️ Error processing your message. Please try again."
        ).send()


@cl.on_audio_start
async def on_audio_start():
    """Handle the start of audio input (voice mode activation)."""
    try:
        assistant_manager: VoiceAssistantManager = cl.user_session.get("assistant_manager")
        
        if not assistant_manager:
            await cl.ErrorMessage(
                content="⚠️ Assistant not initialized. Please refresh the page."
            ).send()
            return False
        
        # Connect to realtime API
        connection_success = await assistant_manager.connect_realtime()
        
        if connection_success:
            logger.info("Voice mode activated successfully")
            return True
        else:
            await cl.ErrorMessage(
                content="⚠️ Voice mode unavailable. Please check your connection and try again."
            ).send()
            return False
        
    except Exception as e:
        logger.error(f"Audio start error: {e}")
        await cl.ErrorMessage(
            content="⚠️ Failed to activate voice mode. Please try again."
        ).send()
        return False


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Handle incoming audio chunks during voice input."""
    try:
        assistant_manager: VoiceAssistantManager = cl.user_session.get("assistant_manager")
        
        if assistant_manager:
            await assistant_manager.send_audio_data(chunk.data)
        else:
            logger.warning("Received audio chunk but assistant not initialized")
        
    except Exception as e:
        logger.error(f"Audio chunk handling error: {e}")


@cl.on_audio_end
async def on_audio_end():
    """Handle the end of audio input."""
    try:
        assistant_manager: VoiceAssistantManager = cl.user_session.get("assistant_manager")
        
        if assistant_manager and assistant_manager.realtime_client:
            # Commit the audio buffer and request response
            await assistant_manager.realtime_client.commit_audio()
        
    except Exception as e:
        logger.error(f"Audio end handling error: {e}")


@cl.on_chat_end
@cl.on_stop
async def on_session_end():
    """Handle session end and cleanup."""
    try:
        assistant_manager: VoiceAssistantManager = cl.user_session.get("assistant_manager")
        
        if assistant_manager:
            await assistant_manager.disconnect()
        
        # Log session metrics
        metrics = performance_monitor.get_metrics_summary()
        logger.info(f"Session ended. Metrics: {metrics}")
        
    except Exception as e:
        logger.error(f"Session end error: {e}")


if __name__ == "__main__":
    # This allows the script to be run directly for testing
    logger.info("Voice Assistant initialized")
    print("Voice Assistant is ready. Run with: chainlit run my_assistant.py")
