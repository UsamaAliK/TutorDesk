# TutorDesk

TutorDesk helps teachers create lessons, quizzes, and assignments grounded in an uploaded PDF, web research, or both.

## Features

- Create and manage lessons, quizzes, and assignments.
- Upload PDFs and select a source for each material.
- Search the web with Tavily and show cited sources.
- Edit generated material, regenerate individual sections or questions, and export PDF or DOCX.
- Sign up and log in with JWT authentication.

## Tech stack

- FastAPI, Pydantic, Uvicorn, SQLAlchemy, and Alembic
- PostgreSQL with PGVector
- Gemini through `langchain-google-genai`
- PDF parsing with PyMuPDF and chunking with `langchain-text-splitters`
- Web research with Tavily and trafilatura
- Supabase Storage for uploaded PDFs

## Project structure

```text
backend/
  db/          Database setup and ORM models
  rag/         PDF loading, chunking, embeddings, and vector search
  schemas/     Auth and material request/response schemas
  services/    Material generation, source resolution, and exports
  websearch/   Tavily search and page processing
  main.py      FastAPI app and API endpoints
frontend/      Login, workspace, styles, and browser app
alembic/       Database migrations
tests/         Material tests
```

## API endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Login and signup page |
| `GET` | `/app` | Materials workspace |
| `GET` | `/health` | API health check |
| `POST` | `/signup` | Create an account |
| `POST` | `/login` | Authenticate and receive a token |
| `GET` | `/me` | Current authenticated user |
| `POST` | `/upload` | Upload and index a PDF |
| `GET` | `/uploads` | List the user's PDFs |
| `DELETE` | `/uploads/{id}` | Delete a PDF |
| `POST` | `/materials/lessons/generate` | Generate a lesson |
| `POST` | `/materials/quizzes/generate` | Generate a quiz |
| `POST` | `/materials/assignments/generate` | Generate an assignment |
| `GET` | `/materials` | List generated materials |
| `GET` | `/materials/{id}` | Get one material |
| `PATCH` | `/materials/{id}` | Update a material |
| `DELETE` | `/materials/{id}` | Delete a material |
| `POST` | `/materials/{id}/regenerate-item` | Regenerate an item |
| `GET` | `/materials/{id}/export` | Download PDF or DOCX |

All endpoints other than the public pages, health check, signup, and login require `Authorization: Bearer <token>`.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
alembic upgrade head
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000`. Interactive API docs are at `/docs`.

## Environment

Set these values in `.env`:

```text
GOOGLE_API_KEY=...
TAVILY_API_KEY=...
DATABASE_URL=postgresql+asyncpg://...
SECRET_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```
