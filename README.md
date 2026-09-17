# TutorDesk

AI teaching assistant for teachers. Upload your own course material and ask questions grounded in it, or let TutorDesk research a topic from the web and turn it into structured teaching content.

## Core Modes

### 1. Course Material Mode (RAG)
- Upload a PDF → extract text (`PyPDFLoader`) → split into chunks (`RecursiveCharacterTextSplitter`, 1000/200) → embed with Gemini (`gemini-embedding-001`) → store in ChromaDB.
- Ask a question → retriever returns the top 4 relevant chunks → Gemini answers.
- The course material is the primary reference; TutorDesk may supplement with general knowledge, and defers to the material on conflict.

### 2. Research Mode
- Web search with **Tavily** (5 results) → keep the top 3 sources → fetch full webpages with **trafilatura** → clean the content (remove boilerplate/navigation).
- Cleaned multi-source content is fed to Gemini to generate structured educational output, avoiding reliance on shallow search snippets.

## Tech Stack
- Python / FastAPI / Pydantic / Uvicorn
- Google Gemini (`gemini-2.5-flash`) via `langchain-google-genai`
- LangChain (LCEL chains, prompts, structured output)
- RAG: PyMuPDF, `RecursiveCharacterTextSplitter`, Gemini embeddings, ChromaDB (`langchain-chroma`)
- Web research: `langchain-tavily`, trafilatura

## Project Structure
```
TutorDesk/
│
├── backend/
│   ├── agent/                # future agent orchestration (placeholder)
│   ├── rag/
│   │   ├── loader.py         # PDF → documents
│   │   ├── chunking.py       # text splitter
│   │   ├── embedding.py      # Gemini embeddings
│   │   ├── vector_store.py   # Chroma create/retrieve
│   │   └── rag_chain.py      # retriever → prompt → Gemini
│   ├── websearch/
│   │   ├── search.py         # Tavily web search
│   │   ├── fetcher.py        # trafilatura full-page fetch
│   │   ├── processed.py      # process_results / clean_documents / clean_text
│   │   ├── research.py       # research_topic: search → top 3 → fetch → clean
│   │   └── lecture.py        # research → lesson prompt → structured LessonPlan
│   ├── prompts/
│   │   ├── tutor.py          # basic chat prompt
│   │   ├── lesson.py         # lesson plan prompt
│   │   └── search.py         # query condenser prompt (test-only)
│   ├── models/
│   │   └── llm.py            # model + lessonmodel (structured output)
│   ├── schemas/
│   │   ├── chat.py           # ChatRequest
│   │   └── lesson.py         # LessonPlan (title, objectives, explanation, examples, activities, assessments)
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
| POST | `/chat`        | Basic chat (prompt → Gemini) |
| POST | `/upload`      | Upload PDF, index + embed into Chroma |
| POST | `/rag/chat`    | Grounded Q&A on uploaded material |
| POST | `/lesson-plan` | Structured lesson plan (`LessonPlan` schema) |

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
```

## Roadmap
1. **Phase 1 — Core RAG** ✅ PDF upload, chunking, embeddings, Chroma retrieval, grounded Q&A.
2. **Phase 2 — Research Mode** (current): Tavily search → source selection → full-page fetch → content cleaning → multi-source context → Gemini → structured lecture. Content selection of relevant context is the next step.
3. **Phase 3 — Teaching Engine**: quizzes, MCQs, assignments, difficulty adaptation, source citations on outputs.
4. **Phase 4 — Frontend**: HTML/CSS/JS upload, chat, research, and lesson-generation interfaces.
5. **Phase 5 — Production**: PostgreSQL, authentication, user/document isolation, background jobs & queues, rate limits, caching, logging, monitoring.
6. **Phase 6 — Agent**: tool calling (RAG / web search / teaching tools) so TutorDesk picks the right knowledge source for a request.

## Development Philosophy
Build → Test → Understand → Connect → Improve. Get a complete skeleton working end-to-end before adding production complexity.