from fastapi import FastAPI
from backend.models.llm import model
from backend.schemas.chat import ChatRequest
from backend.prompts.tutor import prompt





app=FastAPI(title="TutorDesk")


@app.get('/')
def health():
    return  {"message": "TutorDesk API is running"}

@app.post("/chat")
def chat(request:ChatRequest):
    chain=prompt|model
    response=chain.invoke(
        {
            "message":request.query
        }
    )
    
    return {"response":response.content
            }
