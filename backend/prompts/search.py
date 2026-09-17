from langchain_core.prompts import ChatPromptTemplate


queryprompt=ChatPromptTemplate([
    (
        "system",
        """
        You convert a teacher's question into a short, effective
        web-search query. Extract only the core topic.

        Rules:
        - Return ONLY the query string.
        - Max 6 words.
        - No question words (what/how/why/give me).
        """
    ),
    (
        "human",
        "{message}"
    )
])