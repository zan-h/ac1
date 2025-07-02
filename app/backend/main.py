"""
FastAPI backend for AgencyCoachAI with WebSocket support for real-time voice interaction.
"""

import asyncio
import logging
from typing import Dict, Any
import json
import base64

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

from database import init_db
from models import SessionManager
from ai_providers import AIProviderManager
from conversation import MotivationalInterviewingChain

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AgencyCoachAI API",
    description="Therapeutic AI backend with real-time voice support",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
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
session_manager = SessionManager()
ai_provider_manager = AIProviderManager()
mi_chain = MotivationalInterviewingChain()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.realtime_connections: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.realtime_connections:
            del self.realtime_connections[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(json.dumps(message))

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize database and AI providers on startup."""
    await init_db()
    await ai_provider_manager.initialize()
    logger.info("AgencyCoachAI backend started")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "AgencyCoachAI API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Detailed health check including AI provider status."""
    provider_status = await ai_provider_manager.check_health()
    return {
        "status": "healthy",
        "providers": provider_status,
        "database": "connected"
    }

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time voice interaction.
    Handles OpenAI Realtime API communication.
    """
    await manager.connect(websocket, session_id)
    
    try:
        # Initialize session in database
        db_session = await session_manager.create_session(session_id)
        
        # Create OpenAI Realtime connection
        realtime_ws = await openai_client.realtime.connect()
        manager.realtime_connections[session_id] = realtime_ws
        
        # Configure OpenAI Realtime session
        await realtime_ws.send({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": mi_chain.get_system_prompt(),
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                }
            }
        })
        
        # Handle bidirectional communication
        async def handle_client_messages():
            while True:
                try:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    if data["type"] == "audio_chunk":
                        # Forward audio chunk to OpenAI
                        await realtime_ws.send({
                            "type": "input_audio_buffer.append",
                            "audio": data["audio"]
                        })
                    elif data["type"] == "audio_end":
                        # Commit audio and trigger response
                        await realtime_ws.send({
                            "type": "input_audio_buffer.commit"
                        })
                        await realtime_ws.send({
                            "type": "response.create"
                        })
                    
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    break
        
        async def handle_openai_messages():
            while True:
                try:
                    response = await realtime_ws.receive()
                    
                    if response["type"] == "response.audio.delta":
                        # Forward audio response to client
                        await manager.send_message(session_id, {
                            "type": "audio_chunk",
                            "audio": response["delta"]
                        })
                    
                    elif response["type"] == "conversation.item.input_audio_transcription.completed":
                        # Log user transcription
                        transcript = response["transcript"]
                        await session_manager.log_user_message(session_id, transcript)
                        
                        # Send transcription to client
                        await manager.send_message(session_id, {
                            "type": "transcription",
                            "text": transcript,
                            "speaker": "user"
                        })
                    
                    elif response["type"] == "response.output_item.added":
                        if response["item"]["type"] == "message":
                            # Log assistant response
                            content = response["item"]["content"]
                            if content and len(content) > 0:
                                text = content[0].get("text", "")
                                await session_manager.log_assistant_message(session_id, text)
                                
                                # Send transcription to client
                                await manager.send_message(session_id, {
                                    "type": "transcription", 
                                    "text": text,
                                    "speaker": "assistant"
                                })
                                
                                # Analyze emotional state and generate insights
                                await analyze_and_respond(session_id, text)
                    
                except Exception as e:
                    logger.error(f"Error handling OpenAI message: {e}")
                    break
        
        # Run both handlers concurrently
        await asyncio.gather(
            handle_client_messages(),
            handle_openai_messages()
        )
        
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": "Connection error occurred"
        })
    finally:
        manager.disconnect(session_id)
        if session_id in manager.realtime_connections:
            await manager.realtime_connections[session_id].close()

async def analyze_and_respond(session_id: str, message: str):
    """
    Analyze user message for emotional state and generate supportive responses.
    """
    try:
        # Run analysis in parallel using AI providers
        tasks = [
            ai_provider_manager.analyze_sentiment(message),
            ai_provider_manager.extract_tasks(message),
            ai_provider_manager.generate_insights(session_id, message)
        ]
        
        sentiment, tasks, insights = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Store results in session
        await session_manager.update_session_analysis(
            session_id, sentiment, tasks, insights
        )
        
        # Send analysis results to client
        await manager.send_message(session_id, {
            "type": "analysis",
            "sentiment": sentiment if not isinstance(sentiment, Exception) else None,
            "tasks": tasks if not isinstance(tasks, Exception) else [],
            "insights": insights if not isinstance(insights, Exception) else None
        })
        
    except Exception as e:
        logger.error(f"Error in analysis for session {session_id}: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )