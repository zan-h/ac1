"""
OpenAI Realtime API Implementation

This module provides a complete implementation of the OpenAI Realtime API
for voice-based conversational AI applications.
"""

import os
import asyncio
import json
import base64
import uuid
import numpy as np
import websockets
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Union
from collections import defaultdict
import logging

from config.realtime_config import realtime_config


class AudioProcessor:
    """Handles audio processing utilities for the realtime API."""
    
    @staticmethod
    def convert_float32_to_pcm16(audio_data: np.ndarray) -> np.ndarray:
        """Convert float32 audio data to PCM16 format."""
        if audio_data.dtype == np.float32:
            # Clip values to [-1, 1] range and convert to int16
            clipped = np.clip(audio_data, -1.0, 1.0)
            return (clipped * 32767).astype(np.int16)
        return audio_data
    
    @staticmethod
    def decode_base64_audio(base64_str: str) -> np.ndarray:
        """Decode base64 audio string to numpy array."""
        try:
            audio_bytes = base64.b64decode(base64_str)
            return np.frombuffer(audio_bytes, dtype=np.uint8)
        except Exception as e:
            logging.error(f"Error decoding base64 audio: {e}")
            return np.array([])
    
    @staticmethod
    def encode_audio_to_base64(audio_data: Union[np.ndarray, bytes, bytearray]) -> str:
        """Encode audio data to base64 string."""
        try:
            if isinstance(audio_data, np.ndarray):
                if audio_data.dtype == np.float32:
                    audio_data = AudioProcessor.convert_float32_to_pcm16(audio_data)
                audio_bytes = audio_data.tobytes()
            elif isinstance(audio_data, (bytes, bytearray)):
                audio_bytes = bytes(audio_data)
            else:
                audio_bytes = bytes(audio_data)
            
            return base64.b64encode(audio_bytes).decode('utf-8')
        except Exception as e:
            logging.error(f"Error encoding audio to base64: {e}")
            return ""


class EventManager:
    """Manages event handlers for the realtime API."""
    
    def __init__(self):
        self.handlers = defaultdict(list)
        self.pending_events = {}
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register an event handler for a specific event type."""
        self.handlers[event_type].append(handler)
    
    def remove_handler(self, event_type: str, handler: Callable):
        """Remove a specific event handler."""
        if event_type in self.handlers:
            try:
                self.handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    def clear_handlers(self, event_type: Optional[str] = None):
        """Clear all handlers for a specific event type or all handlers."""
        if event_type:
            self.handlers[event_type].clear()
        else:
            self.handlers.clear()
    
    async def emit_event(self, event_type: str, event_data: Dict[str, Any]):
        """Emit an event to all registered handlers."""
        for handler in self.handlers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logging.error(f"Error in event handler for {event_type}: {e}")
    
    async def wait_for_event(self, event_type: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Wait for a specific event to occur."""
        future = asyncio.Future()
        
        def one_time_handler(event_data):
            if not future.done():
                future.set_result(event_data)
        
        self.register_handler(event_type, one_time_handler)
        
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        finally:
            self.remove_handler(event_type, one_time_handler)


class ConversationManager:
    """Manages conversation state and processing."""
    
    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self.reset()
    
    def reset(self):
        """Reset the conversation state."""
        self.items = []
        self.item_lookup = {}
        self.responses = []
        self.response_lookup = {}
        self.audio_queue = {}
        self.transcript_queue = {}
        self.pending_audio = None
    
    def add_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new conversation item."""
        item_id = item.get("id")
        if not item_id:
            return None
        
        # Initialize formatted content
        formatted_item = item.copy()
        formatted_item["formatted"] = {
            "audio": [],
            "text": "",
            "transcript": ""
        }
        
        # Process existing content
        if "content" in formatted_item:
            for content in formatted_item["content"]:
                if content.get("type") in ["text", "input_text"]:
                    formatted_item["formatted"]["text"] += content.get("text", "")
        
        # Add to lookup and items list
        self.item_lookup[item_id] = formatted_item
        self.items.append(formatted_item)
        
        return formatted_item
    
    def update_item_audio(self, item_id: str, audio_data: bytes) -> bool:
        """Update an item with audio data."""
        if item_id in self.item_lookup:
            self.item_lookup[item_id]["formatted"]["audio"].append(audio_data)
            return True
        return False
    
    def update_item_text(self, item_id: str, text_delta: str) -> bool:
        """Update an item with text content."""
        if item_id in self.item_lookup:
            self.item_lookup[item_id]["formatted"]["text"] += text_delta
            return True
        return False
    
    def update_item_transcript(self, item_id: str, transcript_delta: str) -> bool:
        """Update an item with transcript content."""
        if item_id in self.item_lookup:
            self.item_lookup[item_id]["formatted"]["transcript"] += transcript_delta
            return True
        return False
    
    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get an item by ID."""
        return self.item_lookup.get(item_id)
    
    def get_conversation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.items[-limit:] if limit > 0 else self.items.copy()


class RealtimeWebSocketClient:
    """WebSocket client for OpenAI Realtime API."""
    
    def __init__(self):
        self.websocket = None
        self.event_manager = EventManager()
        self.conversation = ConversationManager()
        self.session_created = False
        self.tools = {}
        self.session_config = realtime_config.get_session_config()
        self.audio_buffer = bytearray()
        self.connection_id = None
        
    def generate_event_id(self) -> str:
        """Generate a unique event ID."""
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        return f"evt_{timestamp}_{uuid.uuid4().hex[:8]}"
    
    async def connect(self) -> bool:
        """Establish WebSocket connection to OpenAI Realtime API."""
        try:
            url = realtime_config.get_websocket_url()
            headers = realtime_config.get_headers()
            
            logging.info(f"Connecting to: {url}")
            logging.info(f"Using headers: {headers}")
            
            self.websocket = await websockets.connect(url, additional_headers=headers)
            self.connection_id = str(uuid.uuid4())
            
            # Start message processing
            asyncio.create_task(self._process_messages())
            
            # Wait for session creation
            await self._wait_for_session()
            
            # Initialize session with configuration and any pre-registered tools
            await self.update_session()
            
            logging.info("Successfully connected to OpenAI Realtime API")
            return True
            
        except Exception as e:
            logging.error(f"Failed to connect to Realtime API: {e}")
            return False
    
    async def _process_messages(self):
        """Process incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    event = json.loads(message)
                    await self._handle_server_event(event)
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logging.error(f"Error processing message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logging.info("WebSocket connection closed")
        except Exception as e:
            logging.error(f"Error in message processing: {e}")
    
    async def _handle_server_event(self, event: Dict[str, Any]):
        """Handle server events."""
        event_type = event.get("type")
        
        if event_type == "session.created":
            self.session_created = True
            await self.event_manager.emit_event("session.created", event)
        
        elif event_type == "conversation.item.created":
            item = event.get("item")
            if item:
                formatted_item = self.conversation.add_item(item)
                await self.event_manager.emit_event("conversation.updated", {
                    "item": formatted_item,
                    "delta": None
                })
        
        elif event_type == "response.audio.delta":
            item_id = event.get("item_id")
            delta = event.get("delta")
            if item_id and delta:
                audio_data = AudioProcessor.decode_base64_audio(delta)
                self.conversation.update_item_audio(item_id, audio_data.tobytes())
                await self.event_manager.emit_event("conversation.updated", {
                    "item": self.conversation.get_item(item_id),
                    "delta": {"audio": audio_data.tobytes()}
                })
        
        elif event_type == "response.text.delta":
            item_id = event.get("item_id")
            delta = event.get("delta")
            if item_id and delta:
                self.conversation.update_item_text(item_id, delta)
                await self.event_manager.emit_event("conversation.updated", {
                    "item": self.conversation.get_item(item_id),
                    "delta": {"text": delta}
                })
        
        elif event_type == "response.audio_transcript.delta":
            item_id = event.get("item_id")
            delta = event.get("delta")
            if item_id and delta:
                self.conversation.update_item_transcript(item_id, delta)
                await self.event_manager.emit_event("conversation.updated", {
                    "item": self.conversation.get_item(item_id),
                    "delta": {"transcript": delta}
                })
        
        elif event_type == "input_audio_buffer.speech_started":
            await self.event_manager.emit_event("conversation.interrupted", event)
        
        elif event_type == "response.function_call_arguments.delta":
            await self._handle_function_call_delta(event)
        
        elif event_type == "response.output_item.done":
            await self._handle_output_item_done(event)
        
        elif event_type == "error":
            logging.error(f"Server error: {event}")
            await self.event_manager.emit_event("error", event)
        
        # Emit general event
        await self.event_manager.emit_event(f"server.{event_type}", event)
    
    async def _handle_function_call_delta(self, event: Dict[str, Any]):
        """Handle function call argument deltas."""
        item_id = event.get("item_id")
        delta = event.get("delta")
        
        if item_id and delta:
            item = self.conversation.get_item(item_id)
            if item and "formatted" in item:
                if "tool" not in item["formatted"]:
                    item["formatted"]["tool"] = {"arguments": ""}
                item["formatted"]["tool"]["arguments"] += delta
                
                await self.event_manager.emit_event("conversation.updated", {
                    "item": item,
                    "delta": {"arguments": delta}
                })
    
    async def _handle_output_item_done(self, event: Dict[str, Any]):
        """Handle completed output items."""
        item = event.get("item")
        if item:
            item_id = item.get("id")
            conversation_item = self.conversation.get_item(item_id)
            
            if conversation_item:
                conversation_item["status"] = "completed"
                await self.event_manager.emit_event("conversation.item.completed", {
                    "item": conversation_item
                })
                
                # Handle function calls
                if conversation_item.get("type") == "function_call":
                    await self._execute_function_call(conversation_item)
    
    async def _execute_function_call(self, item: Dict[str, Any]):
        """Execute a function call."""
        try:
            tool_info = item.get("formatted", {}).get("tool", {})
            function_name = item.get("name")
            call_id = item.get("call_id")
            
            if function_name in self.tools:
                tool_config = self.tools[function_name]
                handler = tool_config.get("handler")
                
                if handler and callable(handler):
                    # Parse arguments
                    args_str = tool_info.get("arguments", "{}")
                    try:
                        args = json.loads(args_str)
                        result = await handler(**args) if asyncio.iscoroutinefunction(handler) else handler(**args)
                        
                        # Send function result
                        await self.send_function_result(call_id, result)
                    except Exception as e:
                        await self.send_function_result(call_id, {"error": str(e)})
                else:
                    await self.send_function_result(call_id, {"error": "Function handler not found"})
            else:
                await self.send_function_result(call_id, {"error": f"Unknown function: {function_name}"})
                
        except Exception as e:
            logging.error(f"Error executing function call: {e}")
    
    async def send_function_result(self, call_id: str, result: Any):
        """Send function call result."""
        await self.send_event("conversation.item.create", {
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result)
            }
        })
        await self.send_event("response.create", {})
    
    async def _wait_for_session(self, timeout: float = 10.0):
        """Wait for session to be created."""
        start_time = datetime.utcnow().timestamp()
        while not self.session_created:
            if datetime.utcnow().timestamp() - start_time > timeout:
                raise TimeoutError("Session creation timeout")
            await asyncio.sleep(0.1)
    
    async def send_event(self, event_type: str, data: Dict[str, Any] = None):
        """Send an event to the server."""
        if not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        event = {
            "event_id": self.generate_event_id(),
            "type": event_type,
            **(data or {})
        }
        
        await self.websocket.send(json.dumps(event))
        await self.event_manager.emit_event(f"client.{event_type}", event)
    
    async def update_session(self, **kwargs):
        """Update session configuration."""
        self.session_config.update(kwargs)
        
        # Include tools in session config
        tools = [
            {**tool_config["definition"], "type": "function"}
            for tool_config in self.tools.values()
        ]
        
        session_data = {
            **self.session_config,
            "tools": tools
        }
        
        await self.send_event("session.update", {"session": session_data})
    
    async def send_text_message(self, text: str):
        """Send a text message."""
        await self.send_event("conversation.item.create", {
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}]
            }
        })
        await self.send_event("response.create", {})
    
    async def send_audio_data(self, audio_data: Union[bytes, bytearray, np.ndarray]):
        """Send audio data to the server."""
        base64_audio = AudioProcessor.encode_audio_to_base64(audio_data)
        if base64_audio:
            await self.send_event("input_audio_buffer.append", {
                "audio": base64_audio
            })
            self.audio_buffer.extend(audio_data)
    
    async def commit_audio(self):
        """Commit audio buffer and create response."""
        if self.audio_buffer:
            await self.send_event("input_audio_buffer.commit", {})
            self.conversation.pending_audio = bytes(self.audio_buffer)
            self.audio_buffer.clear()
        await self.send_event("response.create", {})
    
    async def add_tool(self, definition: Dict[str, Any], handler: Callable):
        """Add a tool/function to the session."""
        name = definition.get("name")
        if not name:
            raise ValueError("Tool definition must include a name")
        
        if name in self.tools:
            raise ValueError(f"Tool '{name}' already exists")
        
        self.tools[name] = {
            "definition": definition,
            "handler": handler
        }
        
        # Update session with new tool only if connected
        if self.is_connected():
            await self.update_session()
        
        return self.tools[name]
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler."""
        self.event_manager.register_handler(event_type, handler)
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.websocket is not None and hasattr(self.websocket, 'close')
    
    async def disconnect(self):
        """Disconnect from the server."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.session_created = False
        self.conversation.reset()
        self.audio_buffer.clear()
        logging.info("Disconnected from Realtime API")


# Main RealtimeClient class for external use
class RealtimeClient(RealtimeWebSocketClient):
    """Main client class for OpenAI Realtime API integration."""
    
    def __init__(self):
        super().__init__()
        self.instructions_loaded = False
        self._load_instructions()
    
    def _load_instructions(self):
        """Load instructions from configuration file."""
        try:
            instructions_path = os.path.join(os.path.dirname(__file__), "../config/realtime_instructions.txt")
            with open(instructions_path, "r", encoding="utf-8") as f:
                instructions = f.read().strip()
                self.session_config["instructions"] = instructions
                self.instructions_loaded = True
        except Exception as e:
            logging.warning(f"Could not load instructions: {e}")
            self.session_config["instructions"] = "You are a helpful AI assistant with voice capabilities."
    
    def on(self, event_type: str, handler: Callable):
        """Register an event handler (alias for register_event_handler)."""
        self.register_event_handler(event_type, handler)
    
    async def send_user_message_content(self, content: List[Dict[str, Any]]):
        """Send user message with content."""
        await self.send_event("conversation.item.create", {
            "item": {
                "type": "message",
                "role": "user",
                "content": content
            }
        })
        await self.send_event("response.create", {})
    
    async def append_input_audio(self, audio_data: Union[bytes, bytearray, np.ndarray]):
        """Append audio data to input buffer."""
        await self.send_audio_data(audio_data)
    
    async def create_response(self):
        """Create a response from the assistant."""
        await self.send_event("response.create", {})
