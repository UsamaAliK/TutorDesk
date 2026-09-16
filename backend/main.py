from fastapi import FastAPI,UploadFile,File
from backend.models.llm import model,lessonmodel
from backend.schemas.chat import ChatRequest
from backend.prompts.tutor import tutorprompt
from backend.prompts.lesson import lessonprompt
from backend.rag.rag_chain import ask_rag
from backend.rag.vector_store import create_vector_store






app=FastAPI(title="TutorDesk")


@app.get('/')
def health():
    return  {"message": "TutorDesk API is running"}

@app.post("/chat")
def chat(request:ChatRequest):
    chain=tutorprompt|model
    response=chain.invoke(
        {
            "message":request.query
        }
    )
    
    return {"response":response.content
            }

@app.post("/rag/chat")
def rag_chat(request:ChatRequest):
    response=ask_rag(request.query)
    return {
        "response":response
    }

@app.post("/lesson-plan")
def create_lesson_plan(requesst:ChatRequest):
    chain=lessonprompt|lessonmodel
    response=chain.invoke(
        {
           "request":requesst.query
        }
        )
    return response.model_dump()
@app.post("/upload")
async def upload_pdf(file:UploadFile=File(...)):
    file_path=f"backend/data/uploads/{file.filename}"
    with open(file_path,"wb") as buffer:
        buffer.write(await file.read())
    create_vector_store(file_path)
    return{
        "Filename":file.filename,
        "Message":"PDF UPLOADED AND INDEXED SUCCSESSFYLLY"
    }