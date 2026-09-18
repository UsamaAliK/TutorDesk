from backend.models.llm import lessonmodel
from backend.prompts.lesson import lessonprompt
from backend.websearch.research import research_topic


def create_lecture_chain():

    chain = lessonprompt | lessonmodel

    return chain


def ask_with_research(question: str):

    docs = research_topic(question)

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