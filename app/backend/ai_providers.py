"""
AI provider integrations for multi-modal therapeutic assistance.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import json
import os
from dotenv import load_dotenv

from groq import AsyncGroq
from openai import AsyncOpenAI
import aiohttp

load_dotenv()

logger = logging.getLogger(__name__)

class AIProviderManager:
    """Manages multiple AI providers with fallback capabilities."""
    
    def __init__(self):
        self.groq_client = None
        self.openai_client = None
        self.together_api_key = os.getenv("TOGETHER_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        
    async def initialize(self):
        """Initialize all AI provider clients."""
        try:
            # Initialize Groq for fast text generation
            if os.getenv("GROQ_API_KEY"):
                self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
                logger.info("Groq client initialized")
            
            # Initialize OpenAI for fallback and embeddings
            if os.getenv("OPENAI_API_KEY"):
                self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                logger.info("OpenAI client initialized")
                
        except Exception as e:
            logger.error(f"Error initializing AI providers: {e}")
    
    async def check_health(self) -> Dict[str, str]:
        """Check health status of all providers."""
        status = {}
        
        # Check Groq
        try:
            if self.groq_client:
                # Simple health check - try to list models
                models = await self.groq_client.models.list()
                status["groq"] = "healthy"
            else:
                status["groq"] = "not_configured"
        except Exception as e:
            status["groq"] = f"error: {str(e)}"
        
        # Check OpenAI
        try:
            if self.openai_client:
                models = await self.openai_client.models.list()
                status["openai"] = "healthy"
            else:
                status["openai"] = "not_configured"
        except Exception as e:
            status["openai"] = f"error: {str(e)}"
        
        # Check Together AI
        status["together"] = "configured" if self.together_api_key else "not_configured"
        
        # Check Tavily
        status["tavily"] = "configured" if self.tavily_api_key else "not_configured"
        
        return status
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze emotional sentiment of user message."""
        prompt = f"""
        Analyze the emotional sentiment of this message from someone seeking therapeutic support.
        
        Message: "{text}"
        
        Respond with JSON only:
        {{
            "emotion": "primary emotion (anxious, motivated, overwhelmed, hopeful, frustrated, etc.)",
            "confidence": 0.0-1.0,
            "intensity": "low/medium/high", 
            "context": "brief explanation of what indicates this emotion",
            "supportive_response": "suggested therapeutic approach (validating, encouraging, grounding, etc.)"
        }}
        """
        
        try:
            # Try Groq first for speed
            if self.groq_client:
                response = await self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=300
                )
                result = json.loads(response.choices[0].message.content)
                return result
        except Exception as e:
            logger.warning(f"Groq sentiment analysis failed: {e}")
        
        try:
            # Fallback to OpenAI
            if self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=300
                )
                result = json.loads(response.choices[0].message.content)
                return result
        except Exception as e:
            logger.error(f"All sentiment analysis providers failed: {e}")
        
        # Default fallback
        return {
            "emotion": "unknown",
            "confidence": 0.1,
            "intensity": "unknown",
            "context": "Unable to analyze sentiment",
            "supportive_response": "validating"
        }
    
    async def extract_tasks(self, text: str) -> List[str]:
        """Extract actionable tasks and commitments from conversation."""
        prompt = f"""
        Extract specific, actionable tasks or commitments from this therapeutic conversation message.
        Only include tasks that the person explicitly mentions wanting to do or commit to.
        
        Message: "{text}"
        
        Return a JSON array of task strings:
        ["task 1", "task 2", ...]
        
        If no clear tasks are mentioned, return an empty array: []
        """
        
        try:
            # Try Groq first
            if self.groq_client:
                response = await self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=200
                )
                tasks = json.loads(response.choices[0].message.content)
                return tasks if isinstance(tasks, list) else []
        except Exception as e:
            logger.warning(f"Groq task extraction failed: {e}")
        
        try:
            # Fallback to OpenAI
            if self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=200
                )
                tasks = json.loads(response.choices[0].message.content)
                return tasks if isinstance(tasks, list) else []
        except Exception as e:
            logger.error(f"All task extraction providers failed: {e}")
        
        return []
    
    async def generate_insights(self, session_id: str, latest_message: str) -> str:
        """Generate therapeutic insights and guidance."""
        prompt = f"""
        As a supportive AI coach using motivational interviewing techniques, provide brief insights about this conversation moment.
        
        Latest message: "{latest_message}"
        Session ID: {session_id}
        
        Provide 1-2 sentences of therapeutic insight focusing on:
        - Acknowledging the person's feelings
        - Highlighting strengths or positive steps
        - Gentle guidance or reflection questions
        
        Keep response warm, non-judgmental, and empowering.
        """
        
        try:
            # Try Groq first
            if self.groq_client:
                response = await self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=150
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq insights generation failed: {e}")
        
        try:
            # Fallback to OpenAI
            if self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=150
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"All insight generation providers failed: {e}")
        
        return "I hear you and acknowledge what you're sharing."
    
    async def search_resources(self, query: str) -> List[Dict[str, str]]:
        """Search for relevant therapeutic resources using Tavily."""
        if not self.tavily_api_key:
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "api_key": self.tavily_api_key,
                    "query": f"therapy mental health resources {query}",
                    "search_depth": "basic",
                    "max_results": 3
                }
                
                async with session.post(
                    "https://api.tavily.com/search", 
                    json=payload
                ) as response:
                    data = await response.json()
                    
                    results = []
                    for result in data.get("results", []):
                        results.append({
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "snippet": result.get("content", "")[:200] + "..."
                        })
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []
    
    async def generate_motivational_image(self, prompt: str) -> Optional[str]:
        """Generate motivational imagery using Together AI."""
        if not self.together_api_key:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "black-forest-labs/FLUX.1.1-pro",
                    "prompt": f"Calming, motivational image: {prompt}. Soft colors, peaceful, encouraging atmosphere.",
                    "width": 512,
                    "height": 512,
                    "steps": 20,
                    "n": 1
                }
                
                headers = {
                    "Authorization": f"Bearer {self.together_api_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    "https://api.together.xyz/v1/images/generations",
                    json=payload,
                    headers=headers
                ) as response:
                    data = await response.json()
                    
                    if "data" in data and len(data["data"]) > 0:
                        return data["data"][0].get("url")
                    
        except Exception as e:
            logger.error(f"Together AI image generation failed: {e}")
        
        return None