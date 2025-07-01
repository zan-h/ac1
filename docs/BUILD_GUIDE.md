
# Build Guide

Follow this guide to get the MVP running.

---

## 1️⃣ Scaffold the project

- Create repo structure:
```
/app
  /frontend (Chainlit)
  /backend (FastAPI + LangChain)
  /migrations
  /scripts
  README.md
```

---

## 2️⃣ Set up the backend

- Init Python venv, install packages:
```
pip install fastapi uvicorn langchain[all] sqlalchemy psycopg2 tavily groq-sdk together-sdk openai websockets
```
- Write ASGI app with WebSocket endpoint:
  - Accept PCM16 audio, decode Base64, stream to OpenAI Realtime
  - Handle <200ms response time
- Integrate LangChain for:
  - Motivational interviewing chains
  - Sentiment analysis → adjust tone
  - Calls to Tavily + Together AI

---

## 3️⃣ Set up database

- Configure SQLAlchemy with SQLite first.
- Design models:
  - `User`: id, email
  - `Session`: id, user_id, started_at, ended_at
  - `Task`: id, session_id, description, completed
  - `EmotionalNote`: session_id, emotion, confidence
- Run alembic migrations.

---

## 4️⃣ Build frontend (Chainlit)

- Set up Chainlit config with voice input:
```python
import chainlit as cl

@cl.on_message
async def handle(msg):
    # pass audio to backend API, get response
```
- Add UI for showing real-time transcriptions
- Include fallback text input if mic fails
- Style to match your brand

---

## 5️⃣ Implement redundancy

- Write LangChain chains that switch to Azure if OpenAI fails
- Use asyncio.gather to call Groq, Tavily, Together simultaneously.

---

## 6️⃣ Deploy locally & test

- Run backend with:
```
uvicorn app.main:app --reload
```
- Start Chainlit frontend:
```
chainlit run frontend.py
```
- Test full round trip with voice.

---

## 7️⃣ Polish & monitor

- Add logging (latency, error rates)
- Monitor WebSocket stability
- Encrypt session notes in DB
- Add disclaimers in UI: “Not medical advice.”

---

## 🎉 Done!
Your MVP is now ready to test with real users.
