"""
Chainlit frontend for AgencyCoachAI with real-time voice interaction.
Based on the Chainlit realtime assistant example, adapted for therapeutic use.
"""

import asyncio
import base64
import json
import logging
import uuid
from typing import Dict, Any, Optional
import os
from datetime import datetime

import chainlit as cl
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client (supports both OpenAI and Azure)
if os.getenv("AZURE_OPENAI_API_KEY"):
    from openai import AsyncAzureOpenAI
    openai_client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=f"https://{os.getenv('AZURE_OPENAI_URL')}",
        api_version="2024-10-01-preview"
    )
else:
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Session storage
user_sessions: Dict[str, Dict[str, Any]] = {}

class RealtimeClient:
    """
    Client for handling OpenAI Realtime API connections and therapeutic conversations.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.websocket = None
        self.conversation_history = []
        self.emotional_state = "neutral"
        self.tasks_identified = []
        
    async def connect(self):
        """Establish WebSocket connection to OpenAI Realtime API."""
        try:
            self.websocket = await openai_client.beta.realtime.connect()
            
            # Configure session for therapeutic conversations
            await self.websocket.send({
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": self._get_therapeutic_instructions(),
                    "voice": "alloy",
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
                    }
                }
            })
            
            logger.info(f"Realtime connection established for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Realtime API: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            logger.info(f"Realtime connection closed for session {self.session_id}")
    
    def _get_therapeutic_instructions(self) -> str:
        """Get therapeutic conversation instructions for the AI."""
        return """
        You are a supportive AI coach trained in motivational interviewing techniques. Your role is to help people increase their agency, complete tasks, and feel supported through gentle, non-judgmental conversation.

        CORE PRINCIPLES:
        - Use open-ended questions to encourage self-reflection
        - Reflect and validate emotions without judgment  
        - Help people discover their own motivations and solutions
        - Provide gentle accountability and encouragement
        - Focus on small, achievable steps rather than overwhelming goals

        CONVERSATION STYLE:
        - Speak naturally and conversationally, as if you're a caring friend
        - Keep responses concise (1-3 sentences usually)
        - Ask one thoughtful question at a time
        - Use "I" statements to share observations gently
        - Avoid giving direct advice unless specifically asked

        THERAPEUTIC TECHNIQUES:
        - Reflective listening: "It sounds like you're feeling..."
        - Scaling questions: "On a scale of 1-10, how motivated are you to..."
        - Exploring ambivalence: "What makes this important to you?"
        - Affirming strengths: "I notice you've already taken the step of..."
        - Rolling with resistance: Don't argue, explore the hesitation

        IMPORTANT:
        - You are not a licensed therapist or medical professional
        - Encourage seeking professional help for serious mental health concerns
        - Don't diagnose or provide medical advice
        - If someone expresses thoughts of self-harm, encourage them to contact emergency services

        Remember: Your goal is to help people feel heard, supported, and empowered to take small steps toward their goals.
        """
    
    async def send_audio_chunk(self, audio_chunk: bytes):
        """Send audio chunk to the Realtime API."""
        if self.websocket:
            audio_b64 = base64.b64encode(audio_chunk).decode('utf-8')
            await self.websocket.send({
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            })
    
    async def commit_audio(self):
        """Commit audio buffer and trigger response."""
        if self.websocket:
            await self.websocket.send({
                "type": "input_audio_buffer.commit"
            })
            await self.websocket.send({
                "type": "response.create"
            })
    
    async def handle_server_events(self):
        """Handle incoming events from OpenAI Realtime API."""
        if not self.websocket:
            return
        
        try:
            async for event in self.websocket:
                await self._process_server_event(event)
        except Exception as e:
            logger.error(f"Error handling server events: {e}")
    
    async def _process_server_event(self, event):
        """Process individual server events."""
        event_type = getattr(event, 'type', 'unknown')
        
        if event_type == "response.audio.delta":
            # Stream audio response back to client
            if hasattr(event, 'delta') and event.delta:
                await cl.context.emitter.send_audio_chunk(
                    base64.b64decode(event.delta)
                )
        
        elif event_type == "conversation.item.input_audio_transcription.completed":
            # User speech transcription completed
            transcript = event.transcript
            timestamp = datetime.now().isoformat()
            
            # Store in conversation history
            self.conversation_history.append({
                "speaker": "user",
                "message": transcript,
                "timestamp": timestamp
            })
            
            # Send transcription to UI
            await cl.Message(
                content=transcript,
                author="You",
                type="user_message"
            ).send()
            
            # Analyze emotional state (simplified for this demo)
            await self._analyze_emotional_state(transcript)
        
        elif event_type == "response.output_item.added":
            # Assistant response item added
            if hasattr(event, 'item') and event.item.type == "message":
                content = event.item.content
                if content and len(content) > 0:
                    text = content[0].get("text", "")
                    if text:
                        timestamp = datetime.now().isoformat()
                        
                        # Store in conversation history
                        self.conversation_history.append({
                            "speaker": "assistant",
                            "message": text,
                            "timestamp": timestamp
                        })
                        
                        # Send to UI
                        await cl.Message(
                            content=text,
                            author="AI Coach"
                        ).send()
        
        elif event_type == "error":
            error_message = getattr(event, 'error', {}).get('message', 'Unknown error')
            logger.error(f"Realtime API error: {error_message}")
            await cl.ErrorMessage(
                content=f"Connection error: {error_message}"
            ).send()
    
    async def _analyze_emotional_state(self, text: str):
        """Simple emotional state analysis (placeholder for backend integration)."""
        # This would typically call the backend for sophisticated analysis
        emotional_keywords = {
            "anxious": ["worry", "nervous", "scared", "anxious", "panic"],
            "frustrated": ["frustrated", "angry", "annoyed", "irritated"],
            "overwhelmed": ["overwhelmed", "too much", "can't handle", "exhausted"],
            "motivated": ["excited", "ready", "motivated", "determined"],
            "hopeful": ["hope", "optimistic", "positive", "looking forward"]
        }
        
        text_lower = text.lower()
        for emotion, keywords in emotional_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                self.emotional_state = emotion
                break
        
        # Update session data
        if self.session_id in user_sessions:
            user_sessions[self.session_id]["emotional_state"] = self.emotional_state

@cl.on_chat_start
async def on_chat_start():
    """Initialize new therapeutic session."""
    session_id = str(uuid.uuid4())
    
    # Store session data
    user_sessions[session_id] = {
        "session_id": session_id,
        "start_time": datetime.now().isoformat(),
        "emotional_state": "neutral",
        "tasks_identified": [],
        "conversation_count": 0
    }
    
    # Store in Chainlit session
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("realtime_client", None)
    
    # Welcome message
    welcome_message = """
    ## Welcome to your AgencyCoachAI session! 🌟

    I'm here to support you with gentle, motivational conversation. You can:
    
    - 🎤 **Use voice** - Click the microphone to have a natural conversation
    - 💬 **Type messages** - Share your thoughts in text
    - 🎯 **Explore goals** - Talk about what you'd like to accomplish
    - 🤝 **Get support** - I can provide body doubling and encouragement

    **Important**: I'm an AI coach, not a licensed therapist. For serious mental health concerns, please seek professional help.

    How are you feeling today? What would be helpful to talk about?
    """
    
    await cl.Message(content=welcome_message).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle text messages from user."""
    session_id = cl.user_session.get("session_id")
    
    if not session_id:
        await cl.ErrorMessage(content="Session not initialized").send()
        return
    
    # Update conversation count
    if session_id in user_sessions:
        user_sessions[session_id]["conversation_count"] += 1
    
    # For text messages, we can use a simpler OpenAI completion
    # In a full implementation, this would integrate with the backend
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": RealtimeClient("")._get_therapeutic_instructions()
                },
                {"role": "user", "content": message.content}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        assistant_response = response.choices[0].message.content
        
        await cl.Message(
            content=assistant_response,
            author="AI Coach"
        ).send()
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await cl.ErrorMessage(
            content="I'm having trouble processing your message. Please try again."
        ).send()

@cl.on_audio_start
async def on_audio_start():
    """Handle start of audio input - establish realtime connection."""
    session_id = cl.user_session.get("session_id")
    
    if not session_id:
        await cl.ErrorMessage(content="Session not initialized").send()
        return
    
    # Create and connect realtime client
    realtime_client = RealtimeClient(session_id)
    connected = await realtime_client.connect()
    
    if connected:
        cl.user_session.set("realtime_client", realtime_client)
        
        # Start handling server events in background
        asyncio.create_task(realtime_client.handle_server_events())
        
        await cl.Message(
            content="🎤 Voice session started. I'm listening...",
            author="System"
        ).send()
    else:
        await cl.ErrorMessage(
            content="Unable to establish voice connection. Please try text chat."
        ).send()

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.AudioChunk):
    """Handle incoming audio chunks."""
    realtime_client = cl.user_session.get("realtime_client")
    
    if realtime_client and realtime_client.websocket:
        await realtime_client.send_audio_chunk(chunk.data)

@cl.on_audio_end
async def on_audio_end():
    """Handle end of audio input."""
    realtime_client = cl.user_session.get("realtime_client")
    
    if realtime_client and realtime_client.websocket:
        await realtime_client.commit_audio()

@cl.on_chat_end
async def on_chat_end():
    """Clean up when session ends."""
    session_id = cl.user_session.get("session_id")
    realtime_client = cl.user_session.get("realtime_client")
    
    # Close realtime connection
    if realtime_client:
        await realtime_client.disconnect()
    
    # Log session end
    if session_id and session_id in user_sessions:
        user_sessions[session_id]["end_time"] = datetime.now().isoformat()
        logger.info(f"Session {session_id} ended")
    
    await cl.Message(
        content="Thank you for our session today. Take care of yourself! 💙",
        author="AI Coach"
    ).send()

# Additional utility functions
@cl.step(type="run")
async def show_session_summary():
    """Show session summary and insights."""
    session_id = cl.user_session.get("session_id")
    
    if not session_id or session_id not in user_sessions:
        return "No session data available"
    
    session_data = user_sessions[session_id]
    
    summary = f"""
    ## Session Summary
    
    **Duration**: {session_data.get('conversation_count', 0)} interactions
    **Emotional State**: {session_data.get('emotional_state', 'neutral')}
    **Tasks Identified**: {len(session_data.get('tasks_identified', []))}
    
    You've done meaningful work in our conversation today. Remember that small steps forward are still progress! 🌱
    """
    
    return summary

if __name__ == "__main__":
    # This allows running the app directly
    pass