# TutorDesk

AI teaching assistant for teachers. Upload your own course material and ask questions grounded in it, or let TutorDesk research a topic from the web, then generate the educational content the teacher asks for.

## Core Modes

### 1. Course Material Mode (RAG)
- Upload a PDF → extract text (`PyMuPDF`) → split into chunks (`RecursiveCharacterTextSplitter`, 800/130) → embed with Gemini (`gemini-embedding-001`, 768 dims) → store in PostgreSQL via PGVector.
- Uploads are indexed per user (`user_id` in chunk metadata), so retrieval only ever returns that user's own material.
- Ask a question → retriever returns the top 4 relevant chunks → Gemini answers.
- The course material is the primary reference; TutorDesk may supplement with general knowledge, and defers to the material on conflict.

### 2. Web Research Mode
- Web search with **Tavily** (5 results) → keep the top 3 sources → skip YouTube URLs → fetch full webpages with **trafilatura** → clean the content (remove boilerplate/navigation) and drop invalid pages.
- The pipeline returns **research data + source URLs only** — no LLM, no generation inside the research path.
- The agent receives the research and decides what educational content to produce (lesson plan, explanation, MCQs, quiz, assignment, summary) based on what the teacher asked for.

### 3. Agent
- LangChain agent combining `rag_tool` (uploads) and `search_tool` (web research) as retrieval-only tools.
- The agent picks the right knowledge source per request (both if needed, neither for basic concepts) and generates the final educational content itself.
- Scoped to the authenticated user (`user_id` passed into tool config), so each person only retrieves their own uploads.

## Tech Stack
- Python / FastAPI / Pydantic / Uvicorn
- PostgreSQL (Supabase) with **PGVector** store, async SQLAlchemy, **Alembic** migrations
- Auth: JWT (PyJWT) + bcrypt (passlib), OAuth2 Bearer
- Google Gemini (`gemini-2.5-flash`) via `langchain-google-genai`
- LangChain (agent tool calling, prompts)
- RAG: PyMuPDF, `RecursiveCharacterTextSplitter`, Gemini embeddings, `langchain-postgres` PGVector
- Web research: `langchain-tavily`, trafilatura
- File storage: Supabase Storage (`uploads` bucket)

## Project Structure
```
TutorDesk/
│
├── backend/
│   ├── agent/                  # agent orchestration (rag + search tools)
│   │   ├── agent.py            # create_agent + system prompt
│   │   ├── tools.py            # rag_tool / search_tool (@tool)
│   │   └── response.py         # final_text / collect_sources helpers
│   ├── rag/
│   │   ├── loader.py           # PDF → documents
│   │   ├── chunking.py         # text splitter (800/130)
│   │   ├── embedding.py        # Gemini embeddings (768 dims)
│   │   └── vector_store.py     # PGVector ingest/retrieve (per-user)
│   ├── websearch/
│   │   ├── search.py           # Tavily web search
│   │   ├── fetcher.py          # trafilatura full-page fetch
│   │   ├── processed.py        # process_results / clean_text / is_valid_doc
│   │   └── research.py         # research_topic: search → top 3 → fetch → clean → {research, sources}
│   ├── llm/
│   │   └── model.py            # llm (Gemini)
│   ├── db/
│   │   ├── database.py         # async engine / SessionLocal / get_db
│   │   └── models.py           # User, Conversation, Message, Upload
│   ├── schemas/
│   │   ├── auth.py             # SignupRequest / LoginRequest / TokenResponse
│   │   └── chat.py             # ChatRequest / AskRequest / ConversationCreate
│   ├── auth.py                 # get_current_user (JWT)
│   ├── security.py             # hash/verify password, JWT create/decode
│   ├── config.py               # settings loader (.env)
│   ├── main.py                 # FastAPI app + endpoints
│   └── requirements.txt
│
├── alembic/                    # DB migrations
│   └── versions/               # create_initial_tables
│
├── frontend/                   # HTML/CSS/JS app (skeleton)
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
│
└── .env                        # GOOGLE_API_KEY, TAVILY_API_KEY, DATABASE_URL, ...
```

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/signup`                   | Register (email + password) → `user id` |
| POST | `/login`                    | Authenticate → `access_token` |
| GET  | `/me`                       | Current user (Bearer token) |
| GET  | `/`                         | Health check |
| POST | `/upload`                   | Upload PDF (max 20 MB), index + embed into PGVector |
| POST | `/ask`                      | Agent — picks rag/search tool, then generates content; `conversation_id` optional (omitted → new conversation) |
| POST | `/conversations`            | Create an empty conversation (title) |
| GET  | `/conversations`            | List current user's conversations |
| GET  | `/conversations/{id}/messages` | Messages in a conversation (owner only, else 404) |

All endpoints except health, signup, and login require `Authorization: Bearer <token>`. Conversations and uploads are strictly scoped to the authenticated user — accessing another user's `conversation_id` returns 404.

## Database
- Tables managed by **Alembic**: `users`, `conversations`, `messages`, `uploads`.
- Vector store (PGVector) lives in the same PostgreSQL database as `pgvector` extension (`create_extension=False` — enable the extension on Supabase yourself).
- Chunk metadata carries `user_id` for per-user retrieval isolation.

## Running
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
alembic upgrade head
uvicorn backend.main:app --reload
```
Docs at `/docs`, ReDoc at `/redoc`.

## Environment
`backend/config.py` loads a `.env`:
```
GOOGLE_API_KEY=...
TAVILY_API_KEY=...
DATABASE_URL=postgresql+asyncpg://...
SECRET_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

## Roadmap
1. **Phase 1 — Core RAG** ✅ PDF upload, chunking, embeddings, PGVector retrieval, grounded Q&A.
2. **Phase 2 — Web Research** ✅ Tavily search → top-3 source selection → full-page fetch → content cleaning → research data + source URLs (no LLM in the research path).
3. **Phase 3 — Agent** ✅ Tool calling (RAG / web search) + per-user scoping — TutorDesk picks the right knowledge source and then decides what content to generate.
4. **Phase 4 — Auth, Users, Conversations** ✅ JWT auth, signup/login, per-user conversation/messages/upload isolation.
5. **Phase 5 — Frontend** (current) HTML/CSS/JS chat UI — sidebar conversation list, message thread, new chat (`conversation_id` optional), upload.
6. **Phase 6 — Production hardening** Rate limits, caching, background jobs & queues, logging, monitoring, streaming.

## Development Philosophy
Build → Test → Understand → Connect → Improve. Get a complete skeleton working end-to-end before adding production complexity.