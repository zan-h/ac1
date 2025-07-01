
# Product Requirements Document (PRD)

## 🚀 Product Overview
**Product Name:** (TBD — e.g. AgencyCoachAI)

A therapeutic AI web app that uses motivational interviewing techniques combined with body doubling to help users increase agency, complete daily tasks, and feel supported in a conversational, voice-based environment.

- Provides voice-based motivational interviewing using OpenAI's real-time API.
- Acts as a gentle accountability partner (body doubling) by staying with the user as they complete tasks.
- Stores reflections and progress for future encouragement.

---

## 🎯 Problem Statement
Many people struggle to complete daily tasks due to overwhelm, executive dysfunction (often ADHD), or low emotional regulation. Standard to-do apps don't address underlying motivational blocks.

**Goal:** Build an emotionally intelligent AI system that increases a person’s agency through therapeutic questioning, grounding, and micro-commitments.

---

## 👤 Target Users
- Neurodivergent individuals (ADHD, ASD, anxiety)
- Remote workers who lack coworking or external structure
- Students needing soft accountability
- Anyone seeking gentle, non-judgmental support to build habits

---

## 🔍 Key Features
- Voice-based open sessions (motivational interviewing style)
- Real-time reflection, summary, and small commitments
- Emotional tone mirroring
- Automatic session logging
- Option to generate gentle AI imagery as motivational "cards"
- Multi-provider redundancy to ensure reliability

---

## 🧑‍💻 Core Tech Stack
| Layer                    | Tech Choices                                      |
|---------------------------|--------------------------------------------------|
| Frontend                  | Chainlit 2.0 (React-based conversational UI)     |
| Backend                   | Python 3.12+, LangChain orchestration            |
| DB                        | SQLAlchemy ORM (SQLite for local, Postgres prod) |
| Voice Streaming           | OpenAI Realtime API over WebSocket, PCM16        |
| Text LLM                  | Groq (LLaMA-3.3-70B-Versatile)                   |
| Image Generation          | Together AI (FLUX.1.1-pro)                       |
| Web Search                | Tavily API                                       |
| Async & Concurrency       | asyncio/await                                    |
| Voice Fallback Providers  | Azure OpenAI                                     |

---

## 💡 Success Metrics
- Session completion rate
- % of users who report feeling more agency / task clarity
- Number of tasks completed after sessions
- Repeat session frequency

---

## ⚠️ Edge Cases & Considerations
- Handle silence, one-word responses, or emotional distress
- If latency exceeds 200ms, fallback to buffered / text input
- Ensure sensitive data is encrypted (possible PII)
- Provide disclaimers: "Not a replacement for licensed therapy"

---

## 🔜 Future Ideas
- Streak tracking
- Personalized daily check-in suggestions
- Audio output with voice cloning
- Journaling summaries emailed to user
