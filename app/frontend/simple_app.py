"""
Simple Chainlit frontend for AgencyCoachAI.
Focused on text-based therapeutic conversations for initial testing.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import os
from datetime import datetime

import chainlit as cl
from openai import AsyncOpenAI, AsyncAzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client (supports both OpenAI and Azure)
if os.getenv("AZURE_OPENAI_API_KEY"):
    openai_client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=f"https://{os.getenv('AZURE_OPENAI_URL')}",
        api_version="2024-10-01-preview"
    )
else:
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Session storage
user_sessions: Dict[str, Dict[str, Any]] = {}

def get_therapeutic_instructions() -> str:
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

@cl.on_chat_start
async def on_chat_start():
    """Initialize new therapeutic session."""
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Store session data
    user_sessions[session_id] = {
        "session_id": session_id,
        "start_time": datetime.now().isoformat(),
        "conversation_count": 0,
        "messages": []
    }
    
    # Store in Chainlit session
    cl.user_session.set("session_id", session_id)
    
    # Welcome message
    welcome_message = """
## Welcome to AgencyCoachAI! 🌟

I'm here to support you with gentle, motivational conversation. I use therapeutic techniques to help you:

- 🎯 **Explore your goals** - Talk about what you'd like to accomplish
- 💭 **Process your thoughts** - Work through feelings and challenges  
- 🤝 **Get encouragement** - Receive support and accountability
- ✨ **Take small steps** - Break down overwhelming tasks

**Important**: I'm an AI coach, not a licensed therapist. For serious mental health concerns, please seek professional help.

---

How are you feeling today? What would be helpful to talk about?
    """
    
    await cl.Message(content=welcome_message).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle messages from user."""
    session_id = cl.user_session.get("session_id")
    
    if not session_id:
        await cl.ErrorMessage(content="Session not initialized. Please refresh the page.").send()
        return
    
    # Update conversation count
    if session_id in user_sessions:
        user_sessions[session_id]["conversation_count"] += 1
        user_sessions[session_id]["messages"].append({
            "role": "user",
            "content": message.content,
            "timestamp": datetime.now().isoformat()
        })
    
    # Create conversation history for context
    conversation_history = [
        {"role": "system", "content": get_therapeutic_instructions()}
    ]
    
    # Add recent conversation history (last 10 messages for context)
    if session_id in user_sessions:
        recent_messages = user_sessions[session_id]["messages"][-10:]
        for msg in recent_messages:
            conversation_history.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Get AI response
    try:
        # Show typing indicator
        async with cl.Step(name="Thinking", type="run") as step:
            # Use Azure OpenAI with the realtime deployment for text
            if os.getenv("AZURE_OPENAI_API_KEY"):
                response = await openai_client.chat.completions.create(
                    model=os.getenv("OPENAI_DEPLOYMENT_NAME_REALTIME", "gpt-4"),
                    messages=conversation_history,
                    temperature=0.7,
                    max_tokens=300
                )
            else:
                response = await openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=conversation_history,
                    temperature=0.7,
                    max_tokens=300
                )
            
            assistant_response = response.choices[0].message.content
            step.output = "Response generated"
        
        # Store assistant response
        if session_id in user_sessions:
            user_sessions[session_id]["messages"].append({
                "role": "assistant", 
                "content": assistant_response,
                "timestamp": datetime.now().isoformat()
            })
        
        # Send response to user
        await cl.Message(
            content=assistant_response,
            author="AI Coach"
        ).send()
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await cl.ErrorMessage(
            content="I'm having trouble processing your message right now. Please try again in a moment."
        ).send()

@cl.on_chat_end
async def on_chat_end():
    """Clean up when session ends."""
    session_id = cl.user_session.get("session_id")
    
    # Log session end
    if session_id and session_id in user_sessions:
        user_sessions[session_id]["end_time"] = datetime.now().isoformat()
        conversation_count = user_sessions[session_id]["conversation_count"]
        logger.info(f"Session {session_id} ended after {conversation_count} exchanges")
    
    await cl.Message(
        content="Thank you for our session today. Remember, small steps forward are still progress. Take care of yourself! 💙",
        author="AI Coach"
    ).send()

@cl.action_callback("show_session_summary")
async def show_session_summary():
    """Show session summary and insights."""
    session_id = cl.user_session.get("session_id")
    
    if not session_id or session_id not in user_sessions:
        await cl.Message(content="No session data available.").send()
        return
    
    session_data = user_sessions[session_id]
    message_count = len(session_data.get("messages", []))
    conversation_count = session_data.get("conversation_count", 0)
    
    summary = f"""
## Session Summary

**Session ID**: {session_id}  
**Messages exchanged**: {message_count}  
**Duration**: Active session  

You've done meaningful work in our conversation today. Every step toward understanding yourself better counts as progress! 🌱

Remember:
- Small steps are still steps forward
- It's okay to have challenging days  
- You have the strength to navigate your goals
- Support is always available when you need it

Is there anything specific from our conversation you'd like to revisit?
    """
    
    await cl.Message(content=summary, author="AI Coach").send()

# Add an action button for session summary
@cl.on_chat_start
async def add_session_actions():
    """Add action buttons to the interface."""
    actions = [
        cl.Action(name="show_session_summary", value="summary", description="📊 Show Session Summary")
    ]
    
    await cl.Message(content="", actions=actions).send()

if __name__ == "__main__":
    # This allows running the app directly for testing
    pass