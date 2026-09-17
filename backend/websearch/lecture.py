from backend.models.llm import lessonmodel
from backend.prompts.lesson import lessonprompt
from backend.websearch.research import research_topic


def create_lecture_chain():
    chain=lessonprompt|lessonmodel
    return chain


def ask_with_research(question:str):
    docs=research_topic(question)
    context="\n\n---\n\n".join(d["content"] for d in docs)
    request=f"QUESTION: {question}\n\nRESEARCHED MATERIAL:\n{context}"
    chain=create_lecture_chain()
    return chain.invoke({"request":request})