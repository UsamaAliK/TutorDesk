from backend.models.llm import model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.rag.vector_store import get_vector_store


def create_rag_chain():
  
    prompt=ChatPromptTemplate.from_messages([
        (
        "system",
        """
        You are TutorDesk, an AI teaching assistant.

        Use the provided course material as your primary reference.

        If the user asks for advice, suggestions, or explanations,
        you may also supplement with your general knowledge to help them.

        If the material conflicts with general knowledge, defer to
        the course material.
        """
    ),
    (
        "human",
        """
        COURSE MATERIAL:
        {context}

        TEACHER QUESTION:
        {question}
        """
    )
    ])
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
    |StrOutputParser()
    )
    return rag_chain


def ask_rag(question:str):
    chain=create_rag_chain()
    return chain.invoke(question)


