"""
Tools and Functions for Realtime Voice Assistant

This module provides tool definitions and handlers for external API integrations,
database operations, and other functionality available to the AI assistant.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

from utils.common import logger, tavily_client, together_client
from utils.ai_models import get_llm
from config.database import db_connection


# Tool definitions for the realtime API
async def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web for current information using Tavily API.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
    
    Returns:
        Dictionary containing search results and metadata
    """
    try:
        logger.info(f"Web search initiated: {query}")
        
        # Use Tavily for web search
        search_response = tavily_client.search(
            query=query,
            max_results=max_results,
            include_answer=True,
            include_raw_content=False
        )
        
        results = {
            "query": query,
            "answer": search_response.get("answer", ""),
            "results": [],
            "search_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "tavily"
            }
        }
        
        # Process search results
        for item in search_response.get("results", []):
            result_item = {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score", 0)
            }
            results["results"].append(result_item)
        
        logger.info(f"Web search completed: {len(results['results'])} results found")
        return results
        
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return {
            "query": query,
            "error": f"Search failed: {str(e)}",
            "results": [],
            "search_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "tavily",
                "error": True
            }
        }


async def get_stock_data(symbol: str, period: str = "1mo") -> Dict[str, Any]:
    """
    Get stock market data for a given symbol.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
        period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
    
    Returns:
        Dictionary containing stock data and chart
    """
    try:
        logger.info(f"Fetching stock data for {symbol} ({period})")
        
        # Download stock data
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        info = stock.info
        
        if hist.empty:
            return {
                "symbol": symbol,
                "error": "No data found for this symbol",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Calculate basic statistics
        current_price = hist['Close'].iloc[-1]
        previous_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        price_change = current_price - previous_price
        price_change_percent = (price_change / previous_price) * 100 if previous_price != 0 else 0
        
        # Create chart
        fig = go.Figure(data=go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name=symbol
        ))
        
        fig.update_layout(
            title=f"{symbol} Stock Price ({period})",
            yaxis_title="Price ($)",
            xaxis_title="Date",
            template="plotly_white"
        )
        
        # Convert chart to JSON
        chart_json = json.dumps(fig, cls=PlotlyJSONEncoder)
        
        result = {
            "symbol": symbol,
            "period": period,
            "current_price": round(current_price, 2),
            "price_change": round(price_change, 2),
            "price_change_percent": round(price_change_percent, 2),
            "volume": int(hist['Volume'].iloc[-1]) if 'Volume' in hist else None,
            "high_52w": round(hist['High'].max(), 2),
            "low_52w": round(hist['Low'].min(), 2),
            "company_name": info.get("longName", symbol),
            "market_cap": info.get("marketCap"),
            "chart_data": chart_json,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Stock data retrieved for {symbol}: ${current_price}")
        return result
        
    except Exception as e:
        logger.error(f"Stock data error for {symbol}: {e}")
        return {
            "symbol": symbol,
            "error": f"Failed to fetch stock data: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment of given text using AI model.
    
    Args:
        text: Text to analyze
    
    Returns:
        Dictionary containing sentiment analysis results
    """
    try:
        logger.info("Analyzing sentiment")
        
        llm = get_llm("default")
        
        prompt = f"""
        Analyze the sentiment of the following text and provide:
        1. Overall sentiment (positive, negative, neutral)
        2. Confidence score (0-1)
        3. Key emotions detected
        4. Brief explanation
        
        Text: "{text}"
        
        Respond in JSON format:
        {{
            "sentiment": "positive|negative|neutral",
            "confidence": 0.85,
            "emotions": ["happy", "excited"],
            "explanation": "Brief explanation of the sentiment analysis"
        }}
        """
        
        response = await llm.ainvoke(prompt)
        
        try:
            # Try to parse JSON response
            result = json.loads(response.content)
            result["timestamp"] = datetime.utcnow().isoformat()
            result["original_text"] = text[:100] + "..." if len(text) > 100 else text
            
            logger.info(f"Sentiment analysis completed: {result.get('sentiment')}")
            return result
            
        except json.JSONDecodeError:
            # Fallback if response is not JSON
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "emotions": [],
                "explanation": response.content[:200] + "..." if len(response.content) > 200 else response.content,
                "timestamp": datetime.utcnow().isoformat(),
                "original_text": text[:100] + "..." if len(text) > 100 else text
            }
        
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return {
            "sentiment": "neutral",
            "confidence": 0.0,
            "emotions": [],
            "explanation": f"Analysis failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "original_text": text[:100] + "..." if len(text) > 100 else text,
            "error": True
        }


async def query_database(query: str) -> Dict[str, Any]:
    """
    Execute a database query and return results.
    
    Args:
        query: SQL query to execute
    
    Returns:
        Dictionary containing query results
    """
    try:
        logger.info(f"Executing database query: {query[:100]}...")
        
        # Execute the query
        result = db_connection.execute_query(query)
        
        if "error" in result:
            logger.error(f"Database query error: {result['error']}")
            return {
                "query": query,
                "error": result["error"],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Format results
        formatted_result = {
            "query": query,
            "columns": result.get("columns", []),
            "rows": result.get("rows", []),
            "row_count": len(result.get("rows", [])),
            "affected_rows": result.get("affected_rows"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Database query completed: {formatted_result['row_count']} rows returned")
        return formatted_result
        
    except Exception as e:
        logger.error(f"Database query error: {e}")
        return {
            "query": query,
            "error": f"Query execution failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def generate_image(prompt: str, style: str = "realistic") -> Dict[str, Any]:
    """
    Generate an image using Together AI's image generation models.
    
    Args:
        prompt: Description of the image to generate
        style: Style of the image (realistic, artistic, cartoon, etc.)
    
    Returns:
        Dictionary containing image generation results
    """
    try:
        logger.info(f"Generating image: {prompt[:50]}...")
        
        # Enhance prompt based on style
        enhanced_prompt = prompt
        if style == "realistic":
            enhanced_prompt = f"highly detailed, photorealistic, {prompt}"
        elif style == "artistic":
            enhanced_prompt = f"artistic, creative, beautiful, {prompt}"
        elif style == "cartoon":
            enhanced_prompt = f"cartoon style, animated, colorful, {prompt}"
        
        # Generate image using Together AI
        response = together_client.images.generate(
            prompt=enhanced_prompt,
            model="black-forest-labs/FLUX.1.1-pro",
            width=1024,
            height=768,
            steps=4,
            n=1,
            response_format="b64_json"
        )
        
        # Extract image data
        image_data = response.data[0]
        
        result = {
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "style": style,
            "image_b64": image_data.b64_json,
            "width": 1024,
            "height": 768,
            "model": "black-forest-labs/FLUX.1.1-pro",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("Image generation completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        return {
            "prompt": prompt,
            "style": style,
            "error": f"Image generation failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def get_weather_info(location: str) -> Dict[str, Any]:
    """
    Get weather information for a location using web search.
    
    Args:
        location: City, state, or country name
    
    Returns:
        Dictionary containing weather information
    """
    try:
        logger.info(f"Getting weather for: {location}")
        
        # Use web search to get weather information
        search_query = f"weather forecast {location} today"
        search_result = await search_web(search_query, max_results=3)
        
        # Extract weather information from search results
        weather_info = {
            "location": location,
            "search_query": search_query,
            "weather_summary": search_result.get("answer", ""),
            "sources": [
                {
                    "title": result.get("title", ""),
                    "content": result.get("content", "")[:200] + "..."
                }
                for result in search_result.get("results", [])[:2]
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Weather information retrieved for {location}")
        return weather_info
        
    except Exception as e:
        logger.error(f"Weather lookup error for {location}: {e}")
        return {
            "location": location,
            "error": f"Weather lookup failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def create_task(description: str, priority: str = "medium") -> Dict[str, Any]:
    """
    Create a new task for the user.
    
    Args:
        description: Description of the task
        priority: Priority level (low, medium, high)
    
    Returns:
        Dictionary containing task creation result
    """
    try:
        logger.info(f"Creating task: {description[:50]}...")
        
        # In a real implementation, this would save to database
        # For now, we'll simulate task creation
        import uuid
        task_id = str(uuid.uuid4())
        
        task = {
            "id": task_id,
            "description": description,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }
        
        logger.info(f"Task created: {task_id}")
        return {
            "success": True,
            "task": task,
            "message": f"Task created successfully with ID: {task_id}"
        }
        
    except Exception as e:
        logger.error(f"Task creation error: {e}")
        return {
            "success": False,
            "error": f"Task creation failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def get_current_time(timezone: str = "UTC") -> Dict[str, Any]:
    """
    Get the current time and date.
    
    Args:
        timezone: Timezone identifier (default: UTC)
    
    Returns:
        Dictionary containing current time information
    """
    try:
        # For simplicity, we'll handle UTC and basic timezone conversion
        if timezone.upper() == "UTC":
            current_time = datetime.utcnow()
            tz_name = "UTC"
        else:
            # Fallback to UTC if specific timezone handling is not available
            current_time = datetime.utcnow()
            tz_name = "UTC"
        
        result = {
            "datetime": current_time.isoformat(),
            "timezone": tz_name,
            "formatted_time": current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "day_of_week": current_time.strftime("%A"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Current time retrieved for {timezone}")
        return result
        
    except Exception as e:
        logger.error(f"Time lookup error: {e}")
        # Fallback to UTC
        current_time = datetime.utcnow()
        return {
            "datetime": current_time.isoformat(),
            "timezone": "UTC",
            "formatted_time": current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "day_of_week": current_time.strftime("%A"),
            "error": f"Timezone lookup failed: {str(e)}",
            "timestamp": current_time.isoformat()
        }


# Tool definitions for the OpenAI Realtime API
tools = [
    (
        {
            "name": "search_web",
            "description": "Search the web for current information on any topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        },
        search_web
    ),
    (
        {
            "name": "get_stock_data",
            "description": "Get stock market data and charts for a given stock symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, GOOGL, TSLA)"
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period for data",
                        "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
                        "default": "1mo"
                    }
                },
                "required": ["symbol"]
            }
        },
        get_stock_data
    ),
    (
        {
            "name": "analyze_sentiment",
            "description": "Analyze the sentiment and emotions in text",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to analyze for sentiment"
                    }
                },
                "required": ["text"]
            }
        },
        analyze_sentiment
    ),
    (
        {
            "name": "query_database",
            "description": "Execute SQL queries to retrieve information from the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute"
                    }
                },
                "required": ["query"]
            }
        },
        query_database
    ),
    (
        {
            "name": "generate_image",
            "description": "Generate an image based on a text description",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Description of the image to generate"
                    },
                    "style": {
                        "type": "string",
                        "description": "Style of the image",
                        "enum": ["realistic", "artistic", "cartoon"],
                        "default": "realistic"
                    }
                },
                "required": ["prompt"]
            }
        },
        generate_image
    ),
    (
        {
            "name": "get_weather_info",
            "description": "Get current weather information for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City, state, or country name"
                    }
                },
                "required": ["location"]
            }
        },
        get_weather_info
    ),
    (
        {
            "name": "create_task",
            "description": "Create a new task or reminder",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of the task"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority level",
                        "enum": ["low", "medium", "high"],
                        "default": "medium"
                    }
                },
                "required": ["description"]
            }
        },
        create_task
    ),
    (
        {
            "name": "get_current_time",
            "description": "Get the current time and date",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone identifier (e.g., UTC, America/New_York)",
                        "default": "UTC"
                    }
                },
                "required": []
            }
        },
        get_current_time
    )
]