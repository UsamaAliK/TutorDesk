from backend.models.llm import lessonmodel
from backend.prompts.lesson import lessonprompt
from backend.websearch.research import search_topic


def create_lecture_chain():

    chain = lessonprompt | lessonmodel

    return chain


def ask_with_search(question: str):

    docs = search_topic(question)

    context = "\n\n---\n\n".join(
        f"SOURCE: {d['source']}\nCONTENT:\n{d['content']}"
        for d in docs
    )

    request = f"""
    QUESTION:
    {question}

    RESEARCHED MATERIAL:
    {context} 

     """

    chain = create_lecture_chain()

    return chain.invoke({"request": request})