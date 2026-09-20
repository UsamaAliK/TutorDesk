# TutorDesk

AI teaching assistant for teachers. Upload your own course material and ask questions grounded in it, or let TutorDesk research a topic from the web, then generate the educational content the teacher asks for.

## Core Modes

### 1. Course Material Mode (RAG)
- Upload a PDF → extract text (`PyPDFLoader`) → split into chunks (`RecursiveCharacterTextSplitter`, 800/130) → embed with Gemini (`gemini-embedding-001`) → store in ChromaDB.
- Ask a question → retriever returns the top 4 relevant chunks → Gemini answers.
- The course material is the primary reference; TutorDesk may supplement with general knowledge, and defers to the material on conflict.

### 2. Web Research Mode
- Web search with **Tavily** (5 results) → keep the top 3 sources → fetch full webpages with **trafilatura** → clean the content (remove boilerplate/navigation).
- The pipeline returns **research data + source URLs only** — no LLM, no generation inside the research path.
- The agent receives the research and decides what educational content to produce (lesson plan, explanation, MCQs, quiz, assignment, summary) based on what the teacher asked for.

## Tech Stack
- Python / FastAPI / Pydantic / Uvicorn
- Google Gemini (`gemini-2.5-flash`) via `langchain-google-genai`
- LangChain (agent tool calling, prompts)
- RAG: PyMuPDF, `RecursiveCharacterTextSplitter`, Gemini embeddings, ChromaDB (`langchain-chroma`)
- Web research: `langchain-tavily`, trafilatura

## Project Structure
```
TutorDesk/
│
├── backend/
│   ├── agent/                # agent orchestration (rag + search tools)
│   ├── rag/
│   │   ├── loader.py         # PDF → documents
│   │   ├── chunking.py       # text splitter
│   │   ├── embedding.py      # Gemini embeddings
│   │   └── vector_store.py   # Chroma create/retrieve
│   ├── websearch/
│   │   ├── search.py         # Tavily web search
│   │   ├── fetcher.py        # trafilatura full-page fetch
│   │   ├── processed.py      # process_results / clean_documents / clean_text / is_valid_doc
│   │   ├── research.py       # research_topic: search → top 3 → fetch → clean → research + sources (no LLM)
│   ├── llm/
│   │   └── model.py          # llm (Gemini)
│   ├── schemas/
│   │   ├── chat.py           # ChatRequest
│   │   └── auth.py           # SignupRequest / LoginRequest / TokenResponse
│   ├── data/
│   │   ├── uploads/
│   │   └── chroma_db/
│   ├── config.py
│   ├── main.py
│   └── requirements.txt
│
└── .env                     # GOOGLE_API_KEY, TAVILY_API_KEY
```

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET  | `/`            | Health check |
| POST | `/upload`      | Upload PDF, index + embed into Chroma |
| POST | `/ask`         | Agent — picks rag/search tool, then generates the requested content |
| POST | `/signup`      | Register (email + password) |
| POST | `/login`       | Authenticate → `access_token` |
| GET  | `/me`          | Current user (Bearer token) |

## Running
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```
Docs at `/docs`, ReDoc at `/redoc`.

## Environment
`backend/config.py` loads a `.env` with:
```
GOOGLE_API_KEY=...
TAVILY_API_KEY=...
DATABASE_URL=...
SECRET_KEY=...
```

## Roadmap
1. **Phase 1 — Core RAG** ✅ PDF upload, chunking, embeddings, Chroma retrieval, grounded Q&A.
2. **Phase 2 — Web Research** (current): Tavily search → source selection → full-page fetch → content cleaning → **research data + source URLs** (no LLM in the research path). Content selection of relevant context is the next step.
3. **Phase 3 — Teaching Engine**: agent-driven generation of lessons, quizzes, MCQs, assignments, difficulty adaptation — using research returned by the search tool, with source citations.
4. **Phase 4 — Frontend**: HTML/CSS/JS upload, chat, research, and lesson-generation interfaces.
5. **Phase 5 — Production**: PostgreSQL, authentication, user/document isolation, background jobs & queues, rate limits, caching, logging, monitoring.
6. **Phase 6 — Agent** ✅ (tool calling: RAG / web search) — TutorDesk picks the right knowledge source and then decides what content to generate.

## Development Philosophy
Build → Test → Understand → Connect → Improve. Get a complete skeleton working end-to-end before adding production complexity.