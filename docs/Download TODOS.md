
# Project TODOS

## ✨ Frontend (Chainlit)
- [ ] Set up Chainlit project with voice enabled input
- [ ] Customize Chainlit UI with brand theme
- [ ] Display real-time transcriptions in conversational bubbles
- [ ] Handle microphone permissions
- [ ] Display fallback text box if voice fails
- [ ] Show motivational imagery after sessions
- [ ] Session summary view with "micro-commitments" listed
- [ ] Error state UI (disconnection, provider failover)
- [ ] Responsive UI for mobile

---

## 🚀 Backend (Python, LangChain)
- [ ] Set up FastAPI or simple ASGI app to host WebSocket endpoints
- [ ] Integrate LangChain with Groq for MI conversational chains
- [ ] Handle multi-provider orchestration (OpenAI ↔ Azure fallback)
- [ ] Integrate Tavily for gentle grounding search results
- [ ] Integrate Together AI for imagery
- [ ] Implement asyncio concurrency for parallel tasks (transcribe + reflect + enrich)
- [ ] Build emotional state parser (basic sentiment + prompt adapt)
- [ ] Store session logs + metadata to SQLAlchemy DB

---

## 🗄️ Database (SQLAlchemy)
- [ ] Design tables: Users, Sessions, Tasks, EmotionalNotes
- [ ] Implement alembic migrations
- [ ] Ensure encryption on sensitive columns (emotions, reflections)

---

## 🏗️ Full-stack
- [ ] Implement authentication (basic email or magic link)
- [ ] Wire up frontend voice outputs to backend via WebSocket
- [ ] Real-time push updates from backend to frontend
- [ ] Fallback strategy to switch from OpenAI → Azure → text
- [ ] Logging and monitoring (latency, API errors)
