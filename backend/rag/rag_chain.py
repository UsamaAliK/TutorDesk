from backend.models.llm import model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.rag.vector_store import get_vector_store


def create_rag_chain():
  
    prompt=ChatPromptTemplate.from_message(
        """ 
     You are TutorDesk, an AI teaching assistant.

    Answer the teacher's question using ONLY the provided
    course material.

    If the answer cannot be found in the course material,
    say that the information is not available in the
    uploaded material.
    
    COURSE MATERIAL:
    {context}
    TEACHER QUESTION:
    {question}

    """
    )
    retriever = get_vector_store().as_retriever(
        search_kwargs={"k": 4}
    )

    rag_chain=(
    {
        "context":retriever,
        "question":lambda x:x
    }
    |prompt
    |model
    |StrOutputParser
    )
    return rag_chain


def ask_rag(question:str):
    chain=create_rag_chain()
    return chain.invoke(question)


