# AgencyCoachAI

A therapeutic AI web app that uses motivational interviewing techniques combined with body doubling to help users increase agency, complete daily tasks, and feel supported in a conversational, voice-based environment.

## Features

- Voice-based motivational interviewing using OpenAI's real-time API
- Acts as a gentle accountability partner (body doubling)
- Stores reflections and progress for future encouragement
- Multi-provider redundancy for reliability

## Tech Stack

- **Frontend**: Chainlit 2.0 (React-based conversational UI)
- **Backend**: Python 3.12+, FastAPI, LangChain
- **Database**: SQLAlchemy ORM (SQLite for local, Postgres for prod)
- **Voice**: OpenAI Realtime API over WebSocket
- **AI Providers**: Groq, Together AI, Tavily API

## Project Structure

```
/app
  /frontend     # Chainlit application
  /backend      # FastAPI + LangChain
  /migrations   # Database migrations
  /scripts      # Utility scripts
```

## Quick Start

See `docs/BUILD_GUIDE.md` for detailed setup instructions.

## Documentation

- `docs/Download PRD.md` - Product Requirements Document
- `docs/Download TODOS.md` - Development task list
- `docs/BUILD_GUIDE.md` - Step-by-step build guide