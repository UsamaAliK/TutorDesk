import logging
import re
from contextlib import asynccontextmanager
import os
from uuid import uuid4
from pathlib import Path
from fastapi import FastAPI,UploadFile,File,Depends,HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.schemas.auth import SignupRequest,LoginRequest,TokenResponse
from backend.schemas.material import (
    LessonGenerateRequest,
    QuizGenerateRequest,
    AssignmentGenerateRequest,
    MaterialUpdateRequest,
    RegenerateItemRequest,
    MaterialResponse,
    MaterialListItem,
)
from backend.services.generator import (
    generate_lesson,
    generate_quiz,
    generate_assignment,
    regenerate_single_item,
)
from backend.services.export import export_to_pdf, export_to_docx
from backend.rag.vector_store import ingest_pdf, delete_pdf_embeddings
from backend.db.database import get_db, engine, Base
from backend.db.models import User, Upload, Material
from backend.security import hash_password,verify_password,create_access_token
from backend.auth import get_current_user
from supabase import create_async_client
from backend.config import settings


logger = logging.getLogger(__name__)




_storage_client = None


async def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = await create_async_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _storage_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="TutorDesk", lifespan=lifespan)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/img", StaticFiles(directory=FRONTEND_DIR / "img"), name="img")

@app.get('/')
def landing_page():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get('/app')
def app_page():
    return FileResponse(FRONTEND_DIR / "app.html")

@app.get('/health')
def health():
    return  {"message": "TutorDesk API is running"}

@app.post("/signup", status_code=201)
async def signup(body:SignupRequest, db:AsyncSession=Depends(get_db)):
    existing=await db.execute(select(User).where(User.email==body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user=User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id":user.id, "email":user.email}


@app.post("/login", response_model=TokenResponse)
async def login(body:LoginRequest, db:AsyncSession=Depends(get_db)):
    result=await db.execute(select(User).where(User.email==body.email))
    user=result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/me")
async def me(user:User=Depends(get_current_user)):
    return {"id":user.id, "email":user.email}

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")

    upload_key = uuid4().hex
    safe_filename = os.path.basename(file.filename)
    storage_path = f"uploads/user_{user.id}/{upload_key}_{safe_filename}"
    client = await get_storage_client()
    await client.storage.from_(settings.STORAGE_BUCKET).upload(
        storage_path, data, {"content-type": "application/pdf", "upsert": "true"}
    )

    user_dir = f"backend/data/uploads/user_{user.id}"
    os.makedirs(user_dir, exist_ok=True)
    tmp_path = f"{user_dir}/{upload_key}_{safe_filename}"
    with open(tmp_path, "wb") as buffer:
        buffer.write(data)

    upload = Upload(
        user_id=user.id,
        filename=safe_filename,
        file_path=storage_path,
    )
    db.add(upload)
    try:
        await db.flush()
        await ingest_pdf(tmp_path, user.id, original_filename=safe_filename, upload_id=upload.id)
        await db.commit()
    except Exception:
        await db.rollback()
        try:
            await client.storage.from_(settings.STORAGE_BUCKET).remove([storage_path])
        except Exception:
            pass
        raise
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    await db.refresh(upload)

    return {
        "id": upload.id,
        "filename": upload.filename,
        "storage_path": upload.file_path,
        "created_at": upload.created_at,
        "message": "PDF uploaded and indexed successfully",
    }


@app.get("/uploads")
async def list_uploads(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Upload)
        .where(Upload.user_id == user.id)
        .order_by(Upload.created_at.desc(), Upload.id.desc())
    )
    return [
        {
            "id": u.id,
            "filename": u.filename,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in result.scalars().all()
    ]


@app.delete("/uploads/{upload_id}")
async def delete_upload(
    upload_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Upload).where(Upload.id == upload_id, Upload.user_id == user.id)
    )
    upload = result.scalar_one_or_none()
    if upload is None:
        raise HTTPException(status_code=404, detail="File not found")

    # 1. Delete embeddings from vector database
    await delete_pdf_embeddings(user.id, upload.filename, db, upload_id=upload.id)

    # 2. Delete file from Supabase storage
    try:
        client = await get_storage_client()
        await client.storage.from_(settings.STORAGE_BUCKET).remove([upload.file_path])
    except Exception:
        pass

    # 3. Delete record from database
    await db.delete(upload)
    await db.commit()

    return {"message": "File deleted successfully", "id": upload_id}


# ─────────────────────────────────────────────────────────────────────
# Guided Educational Content Generation Endpoints (/materials)
# ─────────────────────────────────────────────────────────────────────

@app.post("/materials/lessons/generate", response_model=MaterialResponse)
async def api_generate_lesson(
    body: LessonGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured, proportioned lesson plan."""
    return await generate_lesson(body, user.id, db)


@app.post("/materials/quizzes/generate", response_model=MaterialResponse)
async def api_generate_quiz(
    body: QuizGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a calibrated quiz with MCQs, short answers, and long answers."""
    return await generate_quiz(body, user.id, db)


@app.post("/materials/assignments/generate", response_model=MaterialResponse)
async def api_generate_assignment(
    body: AssignmentGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured assignment with problem tasks, rubric, and model answers."""
    return await generate_assignment(body, user.id, db)


@app.get("/materials", response_model=list[MaterialListItem])
async def list_materials(
    type: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all saved educational materials for the user."""
    stmt = select(Material).where(Material.user_id == user.id)
    if type:
        stmt = stmt.where(Material.type == type.lower())
    stmt = stmt.order_by(Material.created_at.desc(), Material.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/materials/{material_id}", response_model=MaterialResponse)
async def get_material(
    material_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single material by ID."""
    material = await _get_owned_material(db, material_id, user.id)
    return material


@app.patch("/materials/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: int,
    body: MaterialUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update title or content_json of a saved material."""
    material = await _get_owned_material(db, material_id, user.id)
    if body.title is not None:
        material.title = body.title
    if body.content_json is not None:
        material.content_json = body.content_json
    await db.commit()
    await db.refresh(material)
    return material


@app.delete("/materials/{material_id}")
async def delete_material(
    material_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved educational material."""
    material = await _get_owned_material(db, material_id, user.id)
    await db.delete(material)
    await db.commit()
    return {"message": "Material deleted successfully", "id": material_id}


@app.post("/materials/{material_id}/regenerate-item", response_model=MaterialResponse)
async def api_regenerate_item(
    material_id: int,
    body: RegenerateItemRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate a single question, section, or task within a material."""
    material = await _get_owned_material(db, material_id, user.id)
    return await regenerate_single_item(material, body, db)


@app.get("/materials/{material_id}/export")
async def export_material(
    material_id: int,
    format: str = "pdf",
    audience: str = "teacher",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export material as PDF or DOCX, configured for Student or Teacher."""
    material = await _get_owned_material(db, material_id, user.id)
    format = format.lower()
    audience = audience.lower()
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', material.title)[:40]

    if format == "pdf":
        try:
            file_bytes = export_to_pdf(material, audience=audience)
        except Exception as exc:
            logger.exception("PDF export failed for material %s", material_id)
            raise HTTPException(status_code=500, detail="PDF generation failed. Please try again or export as DOCX.") from exc
        filename = f"{safe_title}_{audience}.pdf"
        return Response(
            content=file_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    elif format in ("docx", "doc"):
        try:
            file_bytes = export_to_docx(material, audience=audience)
        except Exception as exc:
            logger.exception("DOCX export failed for material %s", material_id)
            raise HTTPException(status_code=500, detail="DOCX generation failed. Please try again or export as PDF.") from exc
        filename = f"{safe_title}_{audience}.docx"
        return Response(
            content=file_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    else:
        raise HTTPException(status_code=400, detail="Supported export formats are 'pdf' and 'docx'.")


async def _get_owned_material(db: AsyncSession, material_id: int, user_id: int) -> Material:
    material = (
        await db.execute(
            select(Material).where(
                Material.id == material_id,
                Material.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return material

