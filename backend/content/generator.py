from backend.websearch.research import gather_context


def create_context_request(question: str, source: str = "auto") -> str:

    docs = gather_context(question, source)

    context = "\n\n---\n\n".join(
        f"SOURCE: {d['source']}\nCONTENT:\n{d['content']}"
        for d in docs
    )

    return f"""
    QUESTION:
    {question}

    RESEARCHED MATERIAL:
    {context} 
     """


def generate_content(question: str, prompt, model, source: str = "auto"):

    chain = prompt | model

    request = create_context_request(question, source)

    return chain.invoke({"request": request})