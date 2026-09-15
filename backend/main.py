from fastapi import FastAPI
from backend.models.llm import model,lessonmodel
from backend.schemas.chat import ChatRequest
from backend.prompts.tutor import tutorprompt
from backend.prompts.lesson import lessonprompt
from backend.rag.rag_chain import ask_rag





app=FastAPI(title="TutorDesk")


@app.get('/')
def health():
    return  {"message": "TutorDesk API is running"}

@app.post("/chat")
def chat(request:ChatRequest):
    chain=tutorprompt|model
    response=chain.invoke(
        {
            "query":request.query
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